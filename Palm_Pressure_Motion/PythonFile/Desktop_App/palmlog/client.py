"""Klien BLE NUS. Loop asyncio di thread sendiri, hasilnya lewat sinyal Qt."""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Signal

from palmlog.protocol import (
    MAX_CHUNK,
    NUS_RX,
    NUS_SERVICE,
    NUS_TX,
    OP_ACK_DELETE,
    OP_ACK_FORMAT,
    OP_ACK_STREAM,
    OP_ACK_TIME,
    OP_CHUNK,
    OP_GET_STATUS,
    OP_LIST,
    OP_LIST_BEGIN,
    OP_LIST_END,
    OP_LIST_ITEM,
    OP_SAMPLE,
    OP_STATUS,
    TARGET_NAME,
    ListItem,
    PacketFramer,
    build_delete,
    build_format,
    build_get_file,
    build_set_time,
    build_stream,
    chunk_result_text,
    delete_result_text,
    format_result_text,
    parse_chunk,
    parse_list_item,
    parse_sample,
    parse_status,
    parse_time_ack,
    stream_result_text,
    time_result_text,
)
from palmlog.storage import bin_path


def local_wall_unix_ms() -> int:
    """Jam dinding lokal, dikodekan seolah UTC. Sama dengan aplikasi Android."""
    now = datetime.now().replace(tzinfo=timezone.utc)
    return int(now.timestamp() * 1000)


class BleService(QObject):
    devices_found = Signal(object)
    state_changed = Signal(str, str)
    status_received = Signal(object)
    files_received = Signal(object)
    download_progress = Signal(str, int, int)
    download_finished = Signal(str, str)
    notice = Signal(str)
    stream_sample = Signal(object)
    stream_ack = Signal(int)
    busy_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.address = ""
        self.device_name = ""
        self.mtu = 0
        self.connected = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client = None
        self._framer = PacketFramer()
        self._waiters: list[tuple[set[int], asyncio.Future]] = []
        self._list_items: list[ListItem] = []
        self._list_future: asyncio.Future | None = None
        self._busy_n = 0
        self._chunk_limit = MAX_CHUNK
        self._ready = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_loop, name="palmlog-ble", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def shutdown(self) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
        self._loop.call_soon_threadsafe(self._loop.stop)

    def scan(self) -> None:
        self._spawn(self._scan())

    def connect_to(self, address: str, name: str) -> None:
        self._spawn(self._connect(address, name))

    def disconnect(self) -> None:
        self._spawn(self._disconnect())

    def refresh_status(self) -> None:
        self._spawn(self._status())

    def set_time_now(self) -> None:
        self._spawn(self._set_time())

    def list_files(self) -> None:
        self._spawn(self._list())

    def download(self, name: str, byte_size: int) -> None:
        self._spawn(self._download(name, byte_size))

    def delete_file(self, name: str) -> None:
        self._spawn(self._delete(name))

    def format_flash(self) -> None:
        self._spawn(self._format())

    def set_stream(self, enable: bool) -> None:
        self._spawn(self._stream(enable))

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()
        self._loop.close()

    def _spawn(self, coro) -> None:
        if self._loop is None:
            self.notice.emit("Layanan BLE belum jalan")
            coro.close()
            return
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        fut.add_done_callback(self._log_task_error)

    def _log_task_error(self, fut: asyncio.Future) -> None:
        try:
            fut.result()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self._busy_n = 0
            self.busy_changed.emit(False)
            self.notice.emit(str(exc))

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self._busy_n += 1
        else:
            self._busy_n = max(0, self._busy_n - 1)
        self.busy_changed.emit(self._busy_n > 0)

    async def _write(self, payload: bytes) -> None:
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("Board belum terhubung")
        try:
            await self._client.write_gatt_char(NUS_RX, payload, response=False)
        except Exception:
            await self._client.write_gatt_char(NUS_RX, payload, response=True)

    def _on_notify(self, _sender, data: bytearray) -> None:
        for pkt in self._framer.feed(bytes(data)):
            self._dispatch(pkt)

    def _dispatch(self, pkt: bytes) -> None:
        if not pkt:
            return
        op = pkt[0]
        if op == OP_SAMPLE:
            sample = parse_sample(pkt)
            if sample is not None:
                self.stream_sample.emit(sample)
            return
        if op == OP_LIST_BEGIN:
            self._list_items = []
            return
        if op == OP_LIST_ITEM:
            item = parse_list_item(pkt)
            if item is not None:
                self._list_items.append(item)
            return
        if op == OP_LIST_END:
            fut = self._list_future
            self._list_future = None
            if fut is not None and not fut.done():
                fut.set_result(list(self._list_items))
            return
        if op == OP_STATUS:
            status = parse_status(pkt)
            if status is not None:
                self.status_received.emit(status)
        if op == OP_ACK_STREAM:
            self.stream_ack.emit(pkt[1])
        self._resolve(op, pkt)

    def _resolve(self, op: int, pkt: bytes) -> None:
        for i, (ops, fut) in enumerate(self._waiters):
            if op in ops and not fut.done():
                fut.set_result(pkt)
                del self._waiters[i]
                return

    async def _expect(self, payload: bytes, ops: set[int], timeout: float) -> bytes:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._waiters.append((ops, fut))
        try:
            await self._write(payload)
            return await asyncio.wait_for(fut, timeout)
        except Exception:
            if not fut.done():
                self._waiters = [(o, f) for o, f in self._waiters if f is not fut]
            raise

    async def _scan(self) -> None:
        from bleak import BleakScanner

        self.state_changed.emit("scanning", "Mencari PalmLog20…")
        found: dict[str, tuple[str, str, int, bool]] = {}

        def _cb(device, adv) -> None:
            name = device.name or getattr(adv, "local_name", None) or ""
            uuids = [u.lower() for u in (adv.service_uuids or [])]
            target = name.startswith("PalmLog") or NUS_SERVICE in uuids
            rssi = int(getattr(adv, "rssi", 0) or 0)
            prev = found.get(device.address)
            if prev is None or rssi > prev[2] or (target and not prev[3]):
                found[device.address] = (name or "(tanpa nama)", device.address, rssi, target)

        scanner = BleakScanner(detection_callback=_cb)
        await scanner.start()
        try:
            await asyncio.sleep(5.0)
        finally:
            await scanner.stop()

        rows = sorted(found.values(), key=lambda r: (not r[3], -r[2], r[0]))
        self.devices_found.emit(rows)
        targets = sum(1 for r in rows if r[3])
        self.state_changed.emit(
            "connected" if self.connected else "idle",
            f"{len(rows)} perangkat, {targets} PalmLog/NUS",
        )

    async def _connect(self, address: str, name: str) -> None:
        from bleak import BleakClient

        await self._disconnect()
        self.state_changed.emit("connecting", address)
        self._framer.clear()
        client = BleakClient(address, timeout=20.0, disconnected_callback=self._on_disconnected)
        await client.connect()
        self._client = client
        self.address = address
        self.device_name = name or TARGET_NAME
        self.connected = True
        await client.start_notify(NUS_TX, self._on_notify)
        self.mtu = int(getattr(client, "mtu_size", 0) or 0)
        payload = max(20, (self.mtu - 3) if self.mtu else 244)
        self._chunk_limit = max(20, min(MAX_CHUNK, payload - 12))
        self.state_changed.emit("connected", f"{self.device_name}  {address}  MTU {self.mtu or '?'}")
        self.notice.emit(f"Terhubung. Potongan unduh {self._chunk_limit} B.")
        await self._status()

    def _on_disconnected(self, _client) -> None:
        self.connected = False
        self._client = None
        self._fail_waiters(RuntimeError("BLE terputus"))
        self.state_changed.emit("idle", "Terputus")
        self.stream_ack.emit(2)

    def _fail_waiters(self, exc: Exception) -> None:
        for _ops, fut in self._waiters:
            if not fut.done():
                fut.set_exception(exc)
        self._waiters.clear()
        if self._list_future is not None and not self._list_future.done():
            self._list_future.set_exception(exc)
        self._list_future = None

    async def _disconnect(self) -> None:
        client = self._client
        self._client = None
        self.connected = False
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass
        self.state_changed.emit("idle", "Tidak terhubung")

    async def _status(self) -> None:
        if not self.connected:
            return
        try:
            pkt = await self._expect(bytes([OP_GET_STATUS]), {OP_STATUS}, 3.0)
        except asyncio.TimeoutError:
            self.notice.emit("Status tidak dijawab")
            return
        status = parse_status(pkt)
        if status is not None:
            self.status_received.emit(status)

    async def _set_time(self) -> None:
        self._set_busy(True)
        try:
            unix_ms = local_wall_unix_ms()
            pkt = await self._expect(build_set_time(unix_ms), {OP_ACK_TIME}, 5.0)
            parsed = parse_time_ack(pkt)
            if parsed is None:
                self.notice.emit("Jawaban set waktu tidak dikenal")
                return
            code, _adjusted = parsed
            self.notice.emit(time_result_text(code))
            await self._status()
        except asyncio.TimeoutError:
            self.notice.emit("Set waktu habis waktu")
        finally:
            self._set_busy(False)

    async def _list(self) -> None:
        if not self.connected:
            self.notice.emit("Hubungkan board dulu")
            return
        self._set_busy(True)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._list_items = []
        self._list_future = fut
        try:
            await self._write(bytes([OP_LIST]))
            items = await asyncio.wait_for(fut, 10.0)
            self.files_received.emit(items)
            self.notice.emit(f"Daftar board: {len(items)} berkas")
        except asyncio.TimeoutError:
            items = list(self._list_items)
            self._list_future = None
            if items:
                self.files_received.emit(items)
                self.notice.emit(f"Daftar terpotong: {len(items)} berkas")
            else:
                self.notice.emit("Daftar berkas tidak dijawab")
        finally:
            self._set_busy(False)

    async def _download(self, name: str, byte_size: int) -> None:
        if not self.connected:
            self.notice.emit("Hubungkan board dulu")
            return
        self._set_busy(True)
        try:
            blob = bytearray()
            offset = 0
            total = byte_size
            while offset < total or total == 0:
                pkt = await self._chunk_at(name, offset)
                chunk = parse_chunk(pkt)
                if chunk is None:
                    raise RuntimeError("Potongan tidak dikenal")
                if chunk.result != 0:
                    raise RuntimeError(chunk_result_text(chunk.result))
                if chunk.file_size > 0:
                    total = chunk.file_size
                if not chunk.data:
                    break
                if chunk.offset != offset:
                    raise RuntimeError(f"Offset bergeser: minta {offset}, dapat {chunk.offset}")
                blob.extend(chunk.data)
                offset += len(chunk.data)
                self.download_progress.emit(name, offset, total)
                if total > 0 and offset >= total:
                    break
            dest = bin_path(self.address, name)
            dest.write_bytes(blob)
            self.download_finished.emit(name, str(dest))
            self.notice.emit(f"Tersimpan {dest.name}")
        except asyncio.TimeoutError:
            self.notice.emit(f"Unduh {name} habis waktu")
        finally:
            self._set_busy(False)

    async def _chunk_at(self, name: str, offset: int) -> bytes:
        payload = build_get_file(name, offset, self._chunk_limit)
        last_error: Exception | None = None
        for _ in range(3):
            try:
                return await self._expect(payload, {OP_CHUNK}, 3.0)
            except asyncio.TimeoutError as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    async def _delete(self, name: str) -> None:
        self._set_busy(True)
        try:
            pkt = await self._expect(build_delete(name), {OP_ACK_DELETE}, 5.0)
            self.notice.emit(delete_result_text(pkt[1]))
            if pkt[1] == 0:
                await self._list()
            await self._status()
        except asyncio.TimeoutError:
            self.notice.emit("Hapus berkas habis waktu")
        finally:
            self._set_busy(False)

    async def _format(self) -> None:
        self._set_busy(True)
        self.notice.emit("Format berjalan. Chip erase bisa 10–40 detik.")
        try:
            pkt = await self._expect(build_format(), {OP_ACK_FORMAT}, 70.0)
            self.notice.emit(format_result_text(pkt[1]))
            if pkt[1] == 0:
                await self._status()
                await self._list()
        except asyncio.TimeoutError:
            self.notice.emit("Format habis waktu (70 dtk)")
        finally:
            self._set_busy(False)

    async def _stream(self, enable: bool) -> None:
        try:
            pkt = await self._expect(build_stream(enable), {OP_ACK_STREAM}, 2.0)
            self.stream_ack.emit(pkt[1])
            self.notice.emit(stream_result_text(pkt[1]))
        except asyncio.TimeoutError:
            self.notice.emit("Perintah stream tidak dijawab. Firmware stream ada di v2.1.0.")

"""Unduh satu .bin lewat BLE (jika perlu) lalu cek loncatan t_rel_ms (PLG1 v4 / 26 B)."""

from __future__ import annotations

import argparse
import asyncio
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from palmlog.protocol import (  # noqa: E402
    MAX_CHUNK,
    NUS_RX,
    NUS_TX,
    OP_CHUNK,
    OP_LIST,
    OP_LIST_BEGIN,
    OP_LIST_END,
    OP_LIST_ITEM,
    PacketFramer,
    build_get_file,
    parse_chunk,
    parse_list_item,
)

HEADER = 256
RECORD = 26


async def download(name: str, dest: Path) -> Path:
    from bleak import BleakClient, BleakScanner

    print("Scan PalmLog20…")
    target = None
    devices = await BleakScanner.discover(timeout=5.0)
    for d in devices:
        if (d.name or "").startswith("PalmLog"):
            target = d
            break
    if target is None:
        raise RuntimeError("PalmLog20 tidak ditemukan (putuskan HP dulu jika masih connect)")

    framer = PacketFramer()
    chunk_q: asyncio.Queue[bytes] = asyncio.Queue()
    list_items: list = []
    list_done: asyncio.Future | None = None

    def on_notify(_s, data: bytearray) -> None:
        for pkt in framer.feed(bytes(data)):
            op = pkt[0]
            if op == OP_LIST_BEGIN:
                list_items.clear()
            elif op == OP_LIST_ITEM:
                item = parse_list_item(pkt)
                if item:
                    list_items.append(item)
            elif op == OP_LIST_END:
                if list_done is not None and not list_done.done():
                    list_done.set_result(list(list_items))
            elif op == OP_CHUNK:
                chunk_q.put_nowait(pkt)

    print(f"Hubungkan {target.address}…")
    async with BleakClient(target, timeout=20.0) as client:
        await client.start_notify(NUS_TX, on_notify)
        await asyncio.sleep(0.3)
        loop = asyncio.get_running_loop()
        list_done = loop.create_future()
        await client.write_gatt_char(NUS_RX, bytes([OP_LIST]), response=False)
        items = await asyncio.wait_for(list_done, 12.0)
        match = next((i for i in items if i.name.startswith(name.removesuffix(".bin"))), None)
        if match is None:
            raise RuntimeError(f"Berkas {name} tidak ada di board. Ada: {[i.name for i in items]}")
        print(f"Unduh {match.file_name}  {match.byte_size} B  {match.n_records} rekaman")

        blob = bytearray()
        offset = 0
        total = match.byte_size
        while offset < total:
            # buang sisa antrian lama
            while not chunk_q.empty():
                try:
                    chunk_q.get_nowait()
                except asyncio.QueueEmpty:
                    break
            chunk = None
            for attempt in range(6):
                payload = build_get_file(match.name, offset, 100)
                try:
                    await client.write_gatt_char(NUS_RX, payload, response=False)
                except Exception:
                    await client.write_gatt_char(NUS_RX, payload, response=True)
                try:
                    while True:
                        pkt = await asyncio.wait_for(chunk_q.get(), 4.0)
                        parsed = parse_chunk(pkt)
                        if parsed is None:
                            continue
                        if parsed.offset == offset or parsed.result != 0:
                            chunk = parsed
                            break
                except asyncio.TimeoutError:
                    print(f"\n  retry @{offset} attempt {attempt + 1}")
                    continue
                break
            if chunk is None:
                raise RuntimeError(f"Chunk timeout @ {offset}")
            if chunk.result != 0:
                raise RuntimeError(f"Chunk gagal @ {offset}: result={chunk.result}")
            if not chunk.data:
                break
            blob.extend(chunk.data)
            offset += len(chunk.data)
            if chunk.file_size:
                total = chunk.file_size
            if offset >= total:
                break
            print(f"\r  {offset}/{total}", end="", flush=True)
        print()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        print(f"Tersimpan {dest} ({len(blob)} B)")
        return dest


def analyze(path: Path) -> None:
    raw = path.read_bytes()
    print(f"\nFile: {path}")
    print(f"Ukuran file: {len(raw)} B")
    if len(raw) < HEADER:
        raise SystemExit("Terlalu pendek")
    magic = raw[:4]
    version, period, channels, rec_size = struct.unpack_from("<HHBB", raw, 4)
    start_ms = struct.unpack_from("<Q", raw, 22)[0]
    print(f"Header: magic={magic!r} version={version} period={period} ch={channels} rec={rec_size}")
    print(f"start_unix_ms={start_ms}")

    body = raw[HEADER:]
    use = rec_size if rec_size >= 26 else RECORD
    n = len(body) // use
    rem = len(body) % use
    print(f"Rekaman terurai: {n}  sisa byte: {rem}")
    print(f"Cek ukuran: 256 + {n}*{use} = {256 + n * use}  (file={len(raw)})")

    if n < 2:
        print("Terlalu sedikit rekaman untuk cek Δt")
        return

    t = [struct.unpack_from("<I", body, i * use)[0] for i in range(n)]
    dts = [((t[i] - t[i - 1]) & 0xFFFFFFFF) for i in range(1, n)]
    hist = Counter(dts)
    print(f"t_rel pertama={t[0]}  terakhir={t[-1]}  span={t[-1] - t[0]} ms")
    print(f"dt min={min(dts)}  max={max(dts)}  mean={sum(dts)/len(dts):.3f}")
    print("Histogram dt (ms -> jumlah):")
    for k in sorted(hist):
        print(f"  {k:5d}: {hist[k]}")

    period = period if period > 0 else 10
    jumps = [(i, dts[i - 1], t[i - 1], t[i]) for i in range(1, n) if dts[i - 1] > period + 5]
    zeros = [(i, t[i]) for i in range(1, n) if dts[i - 1] == 0]

    print(f"\nGap besar (dt > {period + 5} ms): {len(jumps)}")
    for i, dt, a, b in jumps[:30]:
        print(f"  antara index {i-1}->{i}: dt={dt}  t={a}->{b}")
    if len(jumps) > 30:
        print(f"  ... +{len(jumps) - 30} lagi")

    print(f"dt == 0 (catch-up / ms sama): {len(zeros)}")
    for i, tv in zeros[:15]:
        print(f"  index {i-1}->{i}: t={tv}")
    if len(zeros) > 15:
        print(f"  ... +{len(zeros) - 15} lagi")

    exact = hist.get(period, 0)
    print(f"dt tepat {period} ms: {exact} / {len(dts)} ({100.0 * exact / len(dts):.2f}%)")
    expected_nom = (n - 1) * period
    print(f"Span vs nominal (n-1)*{period}: terukur {t[-1] - t[0]}  nominal {expected_nom}  beda {(t[-1] - t[0]) - expected_nom}")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", default="261007181933")
    ap.add_argument("--file", type=Path, help="Analisa file lokal, tanpa BLE")
    ap.add_argument("--download", action="store_true", help="Paksa unduh BLE")
    args = ap.parse_args()
    name = args.name.removesuffix(".bin")
    local = args.file or (ROOT / "data" / "check" / f"{name}.bin")
    if args.file:
        analyze(Path(args.file))
        return
    if args.download or not local.is_file():
        local = await download(name, local)
    analyze(local)


if __name__ == "__main__":
    asyncio.run(main())

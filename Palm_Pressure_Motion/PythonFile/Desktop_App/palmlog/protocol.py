"""Parser/pembangun paket BLE PalmLog NUS — selaras FW 3.1.1 / PROTOCOL.md (PLG1 v4)."""

from __future__ import annotations

import struct
from dataclasses import dataclass

NUS_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

TARGET_NAME = "PalmLog20"
FLASH_SIZE = 4 * 1024 * 1024
DATA_START = 0x1000
HEADER_SIZE = 256
RECORD_SIZE = 26  # t_rel_ms u32 + 11×int16
CHANNELS = 11
SAMPLE_PERIOD_MS = 10
MAX_CHUNK = 100  # stabil seperti Android / check_trel
STREAM_SAMPLE_LEN = 29  # 0xB2 + seq u16 + SampleRec 26 B

OP_GET_STATUS = 0x10
OP_SET_TIME = 0x11
OP_LIST = 0x20
OP_GET_FILE = 0x21
OP_DELETE = 0x23
OP_FORMAT = 0x24
OP_STREAM = 0x30

OP_STATUS = 0x90
OP_ACK_TIME = 0x91
OP_LIST_BEGIN = 0xA0
OP_LIST_ITEM = 0xA1
OP_LIST_END = 0xA2
OP_ACK_DELETE = 0xA3
OP_ACK_FORMAT = 0xA4
OP_ACK_STREAM = 0xB0
OP_CHUNK = 0xB1
OP_SAMPLE = 0xB2

FORMAT_CONFIRM = 0xA5

_FIXED = {
    OP_ACK_TIME: 10,
    OP_LIST_BEGIN: 2,
    OP_LIST_ITEM: 26,
    OP_LIST_END: 2,
    OP_ACK_DELETE: 2,
    OP_ACK_FORMAT: 2,
    OP_ACK_STREAM: 2,
    OP_SAMPLE: STREAM_SAMPLE_LEN,
}


def name12(name: str) -> bytes:
    raw = name.removesuffix(".bin").strip().encode("ascii", errors="ignore")[:12]
    return raw.ljust(12, b"\x00")


def build_set_time(unix_ms: int) -> bytes:
    return bytes([OP_SET_TIME]) + struct.pack("<Q", unix_ms & 0xFFFFFFFFFFFFFFFF)


def build_get_file(name: str, offset: int, max_chunk: int = MAX_CHUNK) -> bytes:
    chunk = max(1, min(180, int(max_chunk)))
    return bytes([OP_GET_FILE]) + name12(name) + struct.pack("<IH", offset & 0xFFFFFFFF, chunk)


def build_delete(name: str) -> bytes:
    return bytes([OP_DELETE]) + name12(name)


def build_stream(enable: bool) -> bytes:
    return bytes([OP_STREAM, 1 if enable else 0])


def build_format() -> bytes:
    return bytes([OP_FORMAT, FORMAT_CONFIRM])


def physical_channel(channel_1based: int, raw: int) -> float:
    """Konversi mentah int16 → fisik (sama Android V2.x)."""
    v = float(raw)
    if 3 <= channel_1based <= 5:
        return v / 1000.0
    if 6 <= channel_1based <= 8:
        return v / 10.0
    return v


def unit_for(channel_1based: int) -> str:
    if 3 <= channel_1based <= 5:
        return "g"
    if 6 <= channel_1based <= 8:
        return "deg/s"
    if 9 <= channel_1based <= 11:
        return "uT"
    return ""


@dataclass
class Status:
    measure: bool
    rtc_ok: bool
    unix_s: int
    next_free: int
    file_count: int
    usb: bool
    pwr_save: bool
    battery_mv: int | None

    @property
    def free_bytes(self) -> int | None:
        if DATA_START <= self.next_free <= FLASH_SIZE:
            return FLASH_SIZE - self.next_free
        return None

    @property
    def free_seconds(self) -> float | None:
        free = self.free_bytes
        if free is None:
            return None
        return (free // RECORD_SIZE) * (SAMPLE_PERIOD_MS / 1000.0)


@dataclass
class ListItem:
    name: str
    flags: int
    n_records: int
    byte_size: int
    start: int

    @property
    def closed(self) -> bool:
        return self.flags == 1

    @property
    def open(self) -> bool:
        return self.flags == 2

    @property
    def file_name(self) -> str:
        return self.name if self.name.endswith(".bin") else f"{self.name}.bin"


@dataclass
class Chunk:
    result: int
    offset: int
    file_size: int
    data: bytes


@dataclass
class StreamSample:
    """Paket 0xB2: seq + SampleRec (t_rel + 11×int16)."""

    seq: int
    t_rel_ms: int
    channels: tuple[int, ...]  # 11 raw

    def physical_tuple(self) -> tuple[float, ...]:
        return tuple(physical_channel(i + 1, self.channels[i]) for i in range(CHANNELS))


def _u16(buf: bytes, i: int) -> int:
    return buf[i] | (buf[i + 1] << 8)


def _i16(buf: bytes, i: int) -> int:
    v = _u16(buf, i)
    return v - 0x10000 if v >= 0x8000 else v


def _u32(buf: bytes, i: int) -> int:
    return (
        buf[i]
        | (buf[i + 1] << 8)
        | (buf[i + 2] << 16)
        | (buf[i + 3] << 24)
    )


def parse_status(pkt: bytes) -> Status | None:
    if len(pkt) not in (14, 16) or pkt[0] != OP_STATUS:
        return None
    unix_s, next_free = struct.unpack_from("<II", pkt, 3)
    battery = _u16(pkt, 14) if len(pkt) >= 16 else None
    return Status(
        measure=pkt[1] != 0,
        rtc_ok=pkt[2] != 0,
        unix_s=unix_s,
        next_free=next_free,
        file_count=pkt[11],
        usb=pkt[12] != 0,
        pwr_save=pkt[13] != 0,
        battery_mv=battery,
    )


def parse_time_ack(pkt: bytes) -> tuple[int, int] | None:
    if len(pkt) != 10 or pkt[0] != OP_ACK_TIME:
        return None
    unix_ms = struct.unpack_from("<Q", pkt, 2)[0]
    return pkt[1], unix_ms


def parse_list_item(pkt: bytes) -> ListItem | None:
    if len(pkt) != 26 or pkt[0] != OP_LIST_ITEM:
        return None
    name = pkt[1:13].split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
    n_records, byte_size, start = struct.unpack_from("<III", pkt, 14)
    return ListItem(name, pkt[13], n_records, byte_size, start)


def parse_chunk(pkt: bytes) -> Chunk | None:
    if len(pkt) < 2 or pkt[0] != OP_CHUNK:
        return None
    result = pkt[1]
    if len(pkt) < 12:
        return Chunk(result, 0, 0, b"")
    offset, file_size, ln = struct.unpack_from("<IIH", pkt, 2)
    data = pkt[12 : 12 + ln]
    return Chunk(result, offset, file_size, data)


def parse_sample(pkt: bytes) -> StreamSample | None:
    if len(pkt) < STREAM_SAMPLE_LEN or pkt[0] != OP_SAMPLE:
        return None
    seq = _u16(pkt, 1)
    t_rel = _u32(pkt, 3)
    ch = tuple(_i16(pkt, 7 + i * 2) for i in range(CHANNELS))
    return StreamSample(seq=seq, t_rel_ms=t_rel, channels=ch)


def packet_length(buf: bytes | bytearray) -> int:
    """Panjang paket penuh, -1 jika belum cukup byte, 0 jika opcode asing (buang 1 byte)."""
    if not buf:
        return -1
    op = buf[0]
    if op == OP_STATUS:
        if len(buf) < 14:
            return -1
        if len(buf) >= 16:
            return 16
        return -1
    if op == OP_CHUNK:
        if len(buf) < 12:
            return -1
        ln = _u16(buf, 10)
        if ln > 180:
            return 0
        return 12 + ln
    if op in _FIXED:
        return _FIXED[op]
    return 0


class PacketFramer:
    """Menyusun notifikasi GATT yang terpecah atau tergabung menjadi satu paket opcode."""

    def __init__(self) -> None:
        self.buf = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        self.buf.extend(data)
        out: list[bytes] = []
        while self.buf:
            n = packet_length(self.buf)
            if n == 0:
                del self.buf[0]
                continue
            if n < 0 or len(self.buf) < n:
                break
            out.append(bytes(self.buf[:n]))
            del self.buf[:n]
        if len(self.buf) == 14 and self.buf[0] == OP_STATUS:
            out.append(bytes(self.buf))
            self.buf.clear()
        return out

    def clear(self) -> None:
        self.buf.clear()


def chunk_result_text(code: int) -> str:
    return {
        0: "OK",
        1: "Berkas tidak ada di board",
        2: "Berkas masih terbuka (measure jalan)",
        3: "Offset tidak valid",
    }.get(code, f"Kode {code}")


def delete_result_text(code: int) -> str:
    return {
        0: "Berkas dihapus dari daftar board",
        1: "Berkas tidak ada di board",
        2: "Measure masih jalan, berkas terbuka",
    }.get(code, f"Kode {code}")


def format_result_text(code: int) -> str:
    return {
        0: "Format selesai",
        1: "Hentikan measure dulu",
        2: "Format ditolak",
    }.get(code, f"Kode {code}")


def time_result_text(code: int) -> str:
    return {
        0: "Waktu board disetel",
        1: "RTC tidak ada",
        2: "Waktu di luar rentang",
    }.get(code, f"Kode {code}")


def stream_result_text(code: int) -> str:
    return {
        0: "Stream mulai",
        1: "Ditolak: measure mati",
        2: "Stream berhenti",
    }.get(code, f"Kode {code}")


def format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f} dtk"
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} jam {minutes} mnt"
    return f"{minutes} mnt {sec} dtk"

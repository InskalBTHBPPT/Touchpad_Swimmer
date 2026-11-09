"""Baca berkas PLG1 v4 (.bin) — 26 B/rekaman, t_rel_ms, 11 kanal."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from palmlog.protocol import CHANNELS, HEADER_SIZE, RECORD_SIZE

HEADER = HEADER_SIZE


@dataclass
class PlgFile:
    path: Path
    version: int
    period_ms: int
    channels: int
    record_size: int
    start_name: str
    start_unix_ms: int
    raw: np.ndarray  # int32 (n, 11)
    physical: np.ndarray  # float64 (n, 11)
    time_s: np.ndarray  # float64 dari t_rel_ms
    t_rel_ms: np.ndarray  # uint32/int64

    @property
    def values(self) -> np.ndarray:
        """Alias fisik untuk plot (kompat UI)."""
        return self.physical

    @property
    def count(self) -> int:
        return int(self.raw.shape[0])

    @property
    def has_absolute_time(self) -> bool:
        return self.version >= 2 and self.start_unix_ms != 0

    @property
    def start_text(self) -> str:
        if self.start_unix_ms <= 0:
            return self.start_name or "-"
        dt = datetime.fromtimestamp(self.start_unix_ms / 1000.0, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"

    @property
    def duration_s(self) -> float:
        if self.count < 2:
            return float(self.time_s[-1]) if self.count else 0.0
        return float(self.time_s[-1] - self.time_s[0])

    def stats(self, channel_0based: int) -> tuple[float, float, float]:
        col = self.physical[:, channel_0based]
        if col.size == 0:
            return 0.0, 0.0, 0.0
        return float(col.min()), float(col.max()), float(col.mean())


def parse_plg(path: Path | str) -> PlgFile:
    path = Path(path)
    raw_u8 = np.fromfile(path, dtype=np.uint8)
    if raw_u8.size < HEADER:
        raise ValueError("Berkas lebih pendek dari header 256 B")
    blob = raw_u8.tobytes()
    if blob[:4] != b"PLG1":
        raise ValueError("Bukan berkas PLG1")

    version, period_ms, channels, record_size = struct.unpack_from("<HHBB", blob, 4)
    start_name = bytes(raw_u8[10:22]).split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
    start_unix_ms = struct.unpack_from("<Q", blob, 22)[0]
    if period_ms <= 0:
        period_ms = 10

    if version < 4 or record_size != RECORD_SIZE or channels < CHANNELS:
        raise ValueError(
            f"Butuh PLG1 v4 (26 B, 11 kanal). Dapat v{version} rec={record_size} ch={channels}"
        )

    body = raw_u8[HEADER:]
    n = int(body.size // RECORD_SIZE)
    if n == 0:
        raw = np.zeros((0, CHANNELS), dtype=np.int32)
        physical = np.zeros((0, CHANNELS), dtype=np.float64)
        t_rel = np.zeros(0, dtype=np.int64)
        time_s = np.zeros(0, dtype=np.float64)
    else:
        rec = body[: n * RECORD_SIZE].reshape(n, RECORD_SIZE)
        t_rel = (
            rec[:, 0].astype(np.uint32)
            | (rec[:, 1].astype(np.uint32) << 8)
            | (rec[:, 2].astype(np.uint32) << 16)
            | (rec[:, 3].astype(np.uint32) << 24)
        ).astype(np.int64)
        raw = np.empty((n, CHANNELS), dtype=np.int32)
        for i in range(CHANNELS):
            off = 4 + i * 2
            raw[:, i] = _i16_col(rec[:, off], rec[:, off + 1])
        physical = raw.astype(np.float64)
        physical[:, 2:5] /= 1000.0  # accel mg → g
        physical[:, 5:8] /= 10.0  # gyro 0.1 °/s → °/s
        time_s = t_rel.astype(np.float64) / 1000.0

    return PlgFile(
        path=path,
        version=version,
        period_ms=period_ms,
        channels=channels,
        record_size=record_size,
        start_name=start_name,
        start_unix_ms=start_unix_ms,
        raw=raw,
        physical=physical,
        time_s=time_s,
        t_rel_ms=t_rel,
    )


def _u16_col(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    return lo.astype(np.uint16) | (hi.astype(np.uint16) << 8)


def _i16_col(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    u = _u16_col(lo, hi).astype(np.int32)
    u[u >= 0x8000] -= 0x10000
    return u


def export_csv(plg: PlgFile, dest: Path) -> None:
    header = "t_rel_ms,time_s," + ",".join(f"d{i}" for i in range(1, CHANNELS + 1))
    cols = [plg.t_rel_ms.astype(np.float64), plg.time_s]
    for i in range(CHANNELS):
        cols.append(plg.physical[:, i])
    data = np.column_stack(cols)
    fmt = ["%.0f", "%.4f"] + ["%.6f"] * CHANNELS
    np.savetxt(dest, data, delimiter=",", header=header, comments="", fmt=fmt)

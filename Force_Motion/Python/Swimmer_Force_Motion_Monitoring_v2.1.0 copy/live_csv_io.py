"""I/O CSV rekaman tab **Live** — header tetap dan parser untuk tab **Analisa**.

Modul ini dipakai bersama oleh:

- **``Swimmer_Force_Motion_Monitoring_v2.0.0.py``** — penulisan header baris data saat
  *logging* (impor ``LIVE_CSV_DATA_HEADER``) konsisten dengan parser.
- **``analyze_single_file_tab.py``** — ``parse_logged_csv`` memvalidasi prolog
  metadata + baris header, lalu mengembalikan nama perenang, gaya renang, dan
  empat deret float (TimeStamp, Force, Roll, Pitch).

Kontrak berkas: lihat manual ``UserManual_Force_Motion_v2.0.0.md`` (struktur CSV
``DataLog/``). Header data harus persis empat kolom seperti konstanta tuple di
modul ini (perbandingan case-insensitive, spasi sel antar kolom dijepit).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

# Header baris data persis seperti ditulis tab Live (toggle_logging)
LIVE_CSV_DATA_HEADER: tuple[str, ...] = (
    "TimeStamp(s)",
    "Force(Kg)",
    "Roll(Deg)",
    "Pitch(Deg)",
)


def parse_logged_csv(path: Path) -> tuple[str, str, list[float], list[float], list[float], list[float]]:
    """
    Baca CSV yang ditulis tab Live saja.

    Validasi:
    - Prolog wajib memuat baris metadata: Nama Perenang:, Gaya Renang:, Time:,
      (sama seperti urutan/kunci yang ditulis aplikasi).
    - Baris header data harus persis 4 kolom:
      TimeStamp(s), Force(Kg), Roll(Deg), Pitch(Deg) (perbandingan case-insensitive, spasi dijepit).
    """
    raw = path.read_text(encoding="utf-8-sig")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    swimmer = "—"
    stroke = "—"
    header_idx: int | None = None

    for idx, line in enumerate(lines):
        low = line.lower()
        if low.startswith("nama perenang"):
            if "," in line:
                swimmer = line.split(",", 1)[1].strip() or "—"
            continue
        if low.startswith("gaya renang"):
            if "," in line:
                stroke = line.split(",", 1)[1].strip() or "—"
            continue
        if low.startswith("time:") or low.startswith("time,"):
            continue

        try:
            row = next(csv.reader([line]))
        except StopIteration:
            continue
        cells = [c.strip() for c in row]
        if len(cells) < 4:
            continue
        if all(
            cells[i].lower() == LIVE_CSV_DATA_HEADER[i].lower()
            for i in range(4)
        ):
            header_idx = idx
            break

    if header_idx is None:
        raise ValueError(
            "Bukan file rekaman Live yang valid.\n"
            "Header data harus tepat: "
            "TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)"
        )

    prologue = lines[:header_idx]
    blob = "\n".join(p.lower() for p in prologue)
    if "nama perenang" not in blob:
        raise ValueError(
            'Bukan file rekaman Live: tidak ada baris "Nama Perenang:," di awal file.'
        )
    if "gaya renang" not in blob:
        raise ValueError(
            'Bukan file rekaman Live: tidak ada baris "Gaya Renang:," di awal file.'
        )
    if not any(
        p.lower().startswith("time:") or p.lower().startswith("time,")
        for p in prologue
    ):
        raise ValueError('Bukan file rekaman Live: tidak ada baris "Time:," sebelum data.')

    data_lines = "\n".join(lines[header_idx + 1 :])
    ts_list: list[float] = []
    f_list: list[float] = []
    r_list: list[float] = []
    p_list: list[float] = []
    reader = csv.reader(io.StringIO(data_lines))
    for row in reader:
        if len(row) < 4:
            continue
        try:
            ts_list.append(float(row[0].strip()))
            f_list.append(float(row[1].strip()))
            r_list.append(float(row[2].strip()))
            p_list.append(float(row[3].strip()))
        except ValueError:
            continue

    if not ts_list:
        raise ValueError("Tidak ada baris data numerik yang valid (4 kolom).")

    return swimmer, stroke, ts_list, f_list, r_list, p_list

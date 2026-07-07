"""
Parser berkas ekspor ``DataStatistik/`` dari tab Analisa (satu berkas).

Format selaras dengan ``AnalyzeSingleFileTab._write_statistik_csv``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


def _cell(row: list[str], idx: int) -> str:
    if idx >= len(row):
        return ""
    return row[idx].strip()


def _parse_float(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(text: str) -> int | None:
    v = _parse_float(text)
    if v is None:
        return None
    return int(round(v))


def _row_is_empty(row: list[str]) -> bool:
    return not row or all(not c.strip() for c in row)


@dataclass
class StatistikExportRecord:
    """Ringkasan satu berkas ``*_DataStatistik*.csv``."""

    swimmer: str = ""
    stroke: str = ""
    exported_at: str = ""
    source_file: str = ""
    segment_start_s: float | None = None
    segment_end_s: float | None = None
    zero_offset_applied: bool = False
    tether_angle_correction: bool = False
    tether_angle_deg: float | None = None
    force_raw_floor_correction: bool = False
    force_raw_floor_kg: float | None = None
    offset_mean_force_kg: float | None = None
    offset_mean_roll_deg: float | None = None
    offset_mean_pitch_deg: float | None = None
    timestamp_start_s: float | None = None
    timestamp_stop_s: float | None = None
    test_region_duration_s: float | None = None
    zero_offset_start_s: float | None = None
    zero_offset_stop_s: float | None = None
    zero_offset_duration_s: float | None = None
    force_stats_method: str | None = None
    force_stroke_count: int | None = None
    force_stats_fallback_global: bool = False
    andrade_filter_cutoff_hz: float | None = None
    force_peak_kg: float | None = None
    force_peak_t_s: float | None = None
    force_mean_kg: float | None = None
    force_impulse_kg_s: float | None = None
    force_t_peak_f_s: float | None = None
    force_dur_s: float | None = None
    force_rfd_kg_s: float | None = None
    force_df_pct: float | None = None
    force_fi_pct: float | None = None
    force_min_kg: float | None = None
    force_min_t_s: float | None = None
    roll_min_deg: float | None = None
    roll_min_t_s: float | None = None
    roll_max_deg: float | None = None
    roll_max_t_s: float | None = None
    pitch_min_deg: float | None = None
    pitch_min_t_s: float | None = None
    pitch_max_deg: float | None = None
    pitch_max_t_s: float | None = None
    dom_freq_force_hz: float | None = None
    dom_freq_roll_hz: float | None = None
    dom_freq_pitch_hz: float | None = None
    spectrum_method: str | None = None
    gap_method: str | None = None
    gap_dt_nominal_s: float | None = None
    gap_fs_hz: float | None = None
    gap_samples_actual: int | None = None
    gap_samples_expected: int | None = None
    gap_count: int | None = None
    gap_samples_lost: int | None = None
    gap_loss_pct: float | None = None
    extra_meta: dict[str, str] = field(default_factory=dict)


_META_KEY_MAP: dict[str, str] = {
    "Nama_Perenang": "swimmer",
    "Gaya_Renang": "stroke",
    "Waktu_Ekspor_Statistik": "exported_at",
    "Berkas_Sumber": "source_file",
    "Segmen_analisa_start (s)": "segment_start_s",
    "Segmen_analisa_finish (s)": "segment_end_s",
    "Zero_offset_start (s)": "zero_offset_start_s",
    "Zero_offset_stop (s)": "zero_offset_stop_s",
    "Timestampstart_uji (s)": "timestamp_start_s",
    "Timestampstop_uji (s)": "timestamp_stop_s",
    "Durasi_region_data_uji (s)": "test_region_duration_s",
    "Durasi_region_zero_offset (s)": "zero_offset_duration_s",
    "Metode_statistik_Force": "force_stats_method",
    "Rata_rata_offset_Force": "offset_mean_force_kg",
    "Rata_rata_offset_Roll": "offset_mean_roll_deg",
    "Rata_rata_offset_Pitch": "offset_mean_pitch_deg",
    "Sudut_tali_terhadap_air (deg)": "tether_angle_deg",
    "Batas_bawah_Force_mentah (Kg)": "force_raw_floor_kg",
}

_METRIC_ROW_MAP: dict[str, str] = {
    "Force_maksimum_peakF": "force_peak_kg",
    "Force_mean_meanF": "force_mean_kg",
    "Force_impulse_ImpF": "force_impulse_kg_s",
    "Force_TpeakF": "force_t_peak_f_s",
    "Force_DUR": "force_dur_s",
    "Force_RFD": "force_rfd_kg_s",
    "Force_dF": "force_df_pct",
    "Force_Fatigue_Index": "force_fi_pct",
    "Force_minimum_minF": "force_min_kg",
    "Roll_minimum": "roll_min_deg",
    "Roll_maksimum": "roll_max_deg",
    "Pitch_minimum": "pitch_min_deg",
    "Pitch_maksimum": "pitch_max_deg",
}

_DOM_FREQ_MAP: dict[str, str] = {
    "Force": "dom_freq_force_hz",
    "Roll": "dom_freq_roll_hz",
    "Pitch": "dom_freq_pitch_hz",
}

_GAP_KEY_MAP: dict[str, str] = {
    "Metode": "gap_method",
    "Delta_t_nominal": "gap_dt_nominal_s",
    "Laju_sampel_efektif": "gap_fs_hz",
    "Sampel_tercatat": "gap_samples_actual",
    "Sampel_diharapkan": "gap_samples_expected",
    "Jumlah_gap": "gap_count",
    "Sampel_hilang_estimasi": "gap_samples_lost",
    "Persen_hilang": "gap_loss_pct",
}


def _apply_meta_kv(rec: StatistikExportRecord, key: str, val: str) -> None:
    key = key.strip()
    val = val.strip()
    if not key:
        return
    if key == "Zero_offset_diterapkan":
        rec.zero_offset_applied = val.lower() in ("ya", "yes", "1", "true")
        return
    if key == "Koreksi_sudut_tali":
        rec.tether_angle_correction = val.lower() in ("ya", "yes", "1", "true")
        return
    if key == "Koreksi_batas_bawah_Force_mentah":
        rec.force_raw_floor_correction = val.lower() in ("ya", "yes", "1", "true")
        return
    if key == "Force_Andrade_fallback_global":
        rec.force_stats_fallback_global = val.lower() in ("ya", "yes", "1", "true")
        return
    if key == "Jumlah_siklus_Force_Andrade":
        rec.force_stroke_count = _parse_int(val)
        return
    if key == "Filter_Andrade_cutoff":
        rec.andrade_filter_cutoff_hz = _parse_float(val)
        return
    attr = _META_KEY_MAP.get(key)
    if attr is None:
        rec.extra_meta[key] = val
        return
    current = getattr(rec, attr)
    if isinstance(current, float) or current is None:
        if attr in (
            "segment_start_s",
            "segment_end_s",
            "zero_offset_start_s",
            "zero_offset_stop_s",
            "timestamp_start_s",
            "timestamp_stop_s",
            "test_region_duration_s",
            "zero_offset_duration_s",
            "offset_mean_force_kg",
            "offset_mean_roll_deg",
            "offset_mean_pitch_deg",
            "tether_angle_deg",
            "force_raw_floor_kg",
        ):
            setattr(rec, attr, _parse_float(val))
        else:
            setattr(rec, attr, val)
    else:
        setattr(rec, attr, val)


def _apply_metric_row(rec: StatistikExportRecord, row: list[str]) -> None:
    name = _cell(row, 0)
    if not name:
        return
    attr = _METRIC_ROW_MAP.get(name)
    if attr is None:
        return
    val = _parse_float(_cell(row, 1))
    t_s = _parse_float(_cell(row, 3))
    setattr(rec, attr, val)
    if name == "Force_maksimum_peakF":
        rec.force_peak_t_s = t_s
    elif name == "Force_minimum_minF":
        rec.force_min_t_s = t_s
    elif name == "Roll_minimum":
        rec.roll_min_t_s = t_s
    elif name == "Roll_maksimum":
        rec.roll_max_t_s = t_s
    elif name == "Pitch_minimum":
        rec.pitch_min_t_s = t_s
    elif name == "Pitch_maksimum":
        rec.pitch_max_t_s = t_s


def _apply_dom_freq_row(rec: StatistikExportRecord, row: list[str]) -> None:
    channel = _cell(row, 0)
    attr = _DOM_FREQ_MAP.get(channel)
    if attr is None:
        return
    setattr(rec, attr, _parse_float(_cell(row, 1)))
    method = _cell(row, 2)
    if method:
        rec.spectrum_method = method


def _apply_gap_row(rec: StatistikExportRecord, row: list[str]) -> None:
    key = _cell(row, 0)
    if key == "Metrik":
        return
    attr = _GAP_KEY_MAP.get(key)
    if attr is None:
        return
    raw = _cell(row, 1)
    if attr in ("gap_samples_actual", "gap_samples_expected", "gap_count", "gap_samples_lost"):
        setattr(rec, attr, _parse_int(raw))
    elif attr in ("gap_dt_nominal_s", "gap_fs_hz", "gap_loss_pct"):
        setattr(rec, attr, _parse_float(raw))
    else:
        setattr(rec, attr, raw)


def parse_datastatistik_csv(path: Path) -> StatistikExportRecord:
    """
    Baca berkas ekspor statistik tab Analisa.

    Raises:
        ValueError: format tidak dikenali atau bukan berkas DataStatistik.
        OSError: gagal membaca berkas.
    """
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if not rows:
        raise ValueError("Berkas kosong atau bukan format DataStatistik.")

    rec = StatistikExportRecord()
    section = "meta"

    for row in rows:
        if _row_is_empty(row):
            continue

        c0 = _cell(row, 0)

        if c0 == "Gap rekaman CSV (estimasi)":
            section = "gap"
            continue

        if c0 == "Metrik":
            c1 = _cell(row, 1)
            if "Frekuensi" in c1:
                section = "dom_freq"
            elif section != "gap":
                section = "metrics"
            continue

        if section == "meta":
            if len(row) >= 2 and row[0].strip():
                _apply_meta_kv(rec, row[0], row[1])
            continue

        if section == "metrics":
            _apply_metric_row(rec, row)
            continue

        if section == "dom_freq":
            _apply_dom_freq_row(rec, row)
            continue

        if section == "gap":
            _apply_gap_row(rec, row)
            continue

    if not rec.swimmer and not rec.source_file and rec.force_peak_kg is None:
        raise ValueError(
            "Berkas tidak dikenali sebagai ekspor DataStatistik "
            "(harus dari tab Analisa → Simpan statistik)."
        )

    return rec

"""
Tab **Analisa (satu berkas)** — ``AnalyzeSingleFileTab`` (PySide6 + pyqtgraph).

Fungsi utama
============
- **Load CSV** rekaman tab Live (parser ``live_csv_io.parse_logged_csv``): dialog
  buka berkas, default folder ``DataLog/``.
- **Plot waktu** penuh untuk Force, Roll, Pitch; **marker** titik ekstrem (min
  hijau / maks merah) dan label waktu pada plot.
- **Playback video** rekaman kamera tab Live (``.mp4`` pasangan basename CSV) di
  samping plot waktu; muat otomatis saat **Load CSV**. **Sinkron video:** garis
  vertikal playhead pada plot Force/Roll/Pitch mengikuti posisi video; memakai
  metadata ``SyncCsvT0`` di CSV jika ada (fallback kasar: ``ts_awal + video_t``).
- Metode **FFT** / **Welch PSD** untuk **frekuensi dominan** di kartu statistik
  (tanpa plot spektrum).
  kartu **gap rekaman CSV** (Metode A per gap / Metode B global, pilih radio).
- **Simpan statistik** — menulis ``DataStatistik/<nama_log>_DataStaistik.csv``
  (UTF-8): metadata, ``Timestampstart (s)``, tabel ekstremum, lalu blok frekuensi
  dominan per saluran + kolom metode.

Dependensi tambahan (selain GUI): ``numpy``, ``scipy``.

Fungsi modul ``make_three_stack_plots`` membangun tiga ``PlotWidget`` deret waktu
dengan gaya konsisten; dipakai jendela utama saat menyusun tab Live.

Tab **Analisa multifile** (hingga lima berkas) adalah tab terpisah; kelas ini
tetap fokus satu berkas tanpa mengubah kontraknya.
"""

from __future__ import annotations

import csv
import statistics
from collections.abc import Callable
from datetime import datetime
from html import escape
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from scipy import signal

from analyze_metrics_core import GAP_LOSS_TOLERANCE_FACTOR, GapLossStats, compute_gap_loss
from analyze_video_panel import AnalyzeVideoPanel
from live_csv_io import LogSyncMeta, parse_logged_csv


# Marker ekstremum: semua min hijau, semua max merah
MARKER_MIN_COLOR = "#22c55e"
MARKER_MAX_COLOR = "#ef4444"

_SEGMENT_BRUSH_FORCE = pg.mkBrush(56, 189, 248, 45)
_SEGMENT_PEN_FORCE = pg.mkPen("#38bdf8", width=1)
_SEGMENT_BRUSH_ROLL = pg.mkBrush(245, 158, 11, 35)
_SEGMENT_PEN_ROLL = pg.mkPen("#f59e0b", width=1)
_SEGMENT_BRUSH_PITCH = pg.mkBrush(167, 139, 250, 35)
_SEGMENT_PEN_PITCH = pg.mkPen("#a78bfa", width=1)


def _path_text_for_dialog(path: Path | str) -> str:
    s = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    if len(s) >= 3 and s[0].isalpha() and s[1] == ":" and s[2] == "/":
        s = s[:2] + "\u2060" + s[2:]
    return s


def _he(s: str) -> str:
    return escape(s, quote=False)


_STAT_ROW_STYLE = "color:#ffffff;padding:2px 0;line-height:1.35;font-weight:600;font-size:11px;"


def _html_load_field(label: str, value: str, *, monospace: bool = False, margin_top: int = 8) -> str:
    mono = (
        'font-family: Consolas, "Cascadia Mono", "Courier New", monospace; font-size: 11.5px;'
        if monospace
        else "font-size: 13px;"
    )
    return (
        f'<div style="margin-top:{margin_top}px;">'
        f'<div style="color:#e2e8f0;font-size:9px;font-weight:700;letter-spacing:0.12em;opacity:0.92;">'
        f"{_he(label.upper())}</div>"
        f'<div style="color:#f8fafc;font-weight:600;margin-top:3px;line-height:1.45;{mono}">'
        f"{_he(value)}</div>"
        f"</div>"
    )


def _html_load_block(
    swimmer: str, stroke: str, csv_filename: str, video_filename: str | None = None
) -> str:
    video_value = video_filename if video_filename else "— (tidak ditemukan)"
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:12px 14px;">'
        f"{_html_load_field('Nama perenang', swimmer, margin_top=0)}"
        f"{_html_load_field('Gaya renang', stroke)}"
        f"{_html_load_field('File CSV', csv_filename, monospace=True)}"
        f"{_html_load_field('File video', video_value, monospace=True)}"
        "</div>"
    )


def _html_load_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:14px 16px;">'
        '<p style="margin:0;color:#cbd5e1;font-size:11px;line-height:1.55;">'
        'Belum ada rekaman dimuat.<br/>'
        'Tekan <b style="color:#f1f5f9;">Load CSV…</b> untuk memilih file hasil tab Live '
        "(video <code>.mp4</code> pasangan dimuat otomatis jika ada)."
        "</p></div>"
    )


def _html_stat_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:12px 14px;">'
        '<p style="margin:0;color:#94a3b8;font-size:10px;line-height:1.55;">'
        "Muat CSV dari tab Live untuk menampilkan ringkasan ekstremum (force, roll, pitch)."
        "</p></div>"
    )


def _html_gap_loss_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:12px 14px;">'
        '<p style="margin:0;color:#94a3b8;font-size:10px;line-height:1.55;">'
        "Estimasi sampel hilang (gap timestamp CSV) — muat CSV untuk menghitung."
        "</p></div>"
    )


def _html_stat_gap_loss(stats: GapLossStats) -> str:
    dt_line = (
        f"Δt nominal: {_he(f'{stats.dt_nominal_s:.4g}')} s "
        f"({_he(f'{stats.fs_hz:.2f}')} Hz)"
    )
    lost_line = (
        f"Sampel hilang (estimasi): {_he(str(stats.samples_lost))} "
        f"({_he(f'{stats.loss_pct:.2f}')} %)"
    )
    actual_line = f"Sampel tercatat: {_he(str(stats.samples_actual))}"
    method_line = _he(stats.method_label)

    row_style = _STAT_ROW_STYLE
    extra = ""
    if stats.method_key == "A" and stats.gap_count is not None:
        extra = (
            f'<tr><td colspan="2" style="{row_style}">'
            f"Jumlah gap: {_he(str(stats.gap_count))}</td></tr>"
        )
    elif stats.method_key == "B" and stats.samples_expected is not None:
        extra = (
            f'<tr><td colspan="2" style="{row_style}">'
            f"Sampel diharapkan: {_he(str(stats.samples_expected))}</td></tr>"
        )

    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:8px;padding:8px 10px;">'
        '<div style="border-left:3px solid #64748b;padding-left:8px;">'
        '<div style="color:#94a3b8;font-weight:700;font-size:9px;letter-spacing:0.1em;">'
        "GAP REKAMAN CSV</div>"
        '<div style="color:#64748b;font-size:9px;margin-top:2px;line-height:1.3;">'
        "Estimasi kualitas rekaman (bukan diagnosis LoRa).</div>"
        '<table style="margin-top:4px;font-size:11px;color:#cbd5e1;width:100%;">'
        f'<tr><td colspan="2" style="{row_style}">{method_line}</td></tr>'
        f'<tr><td colspan="2" style="{row_style}">{dt_line}</td></tr>'
        f'<tr><td colspan="2" style="{row_style}">{actual_line}</td></tr>'
        f"{extra}"
        f'<tr><td colspan="2" style="{row_style}">{lost_line}</td></tr>'
        "</table></div></div>"
    )


def _html_tstart_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:12px 14px;">'
        '<p style="margin:0;color:#94a3b8;font-size:10px;line-height:1.55;">'
        "TimeStamp Start pada — s<br/>"
        "TimeStamp Stop pada — s"
        "</p></div>"
    )


def _html_stat_timestamp_range(t_start_s: float, t_stop_s: float) -> str:
    """Rentang waktu analisa (sampel pertama & terakhir dalam segmen terpilih)."""
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:8px;padding:8px 10px;">'
        '<div style="border-left:3px solid #64748b;padding-left:8px;">'
        '<div style="color:#f8fafc;font-size:11px;font-weight:600;line-height:1.45;">'
        f"TimeStamp Start pada {_he(f'{t_start_s:.2f}')} s<br/>"
        f"TimeStamp Stop pada {_he(f'{t_stop_s:.2f}')} s"
        "</div></div></div>"
    )


def _spectrum_peak_frequency_hz(y: list[float], fs_hz: float, *, use_welch: bool) -> float | None:
    if use_welch:
        fq, mag = _spectrum_welch_bins(y, fs_hz)
    else:
        fq, mag = _spectrum_fft_bins(y, fs_hz)
    if fq.size == 0:
        return None
    imax = int(np.argmax(mag))
    return float(fq[imax])


def _html_stat_freq_dominant(peak_hz: float | None, method_label: str) -> str:
    """Baris spektrum di kartu statistik: Frekuensi dominan: … Hz [metode]."""
    ml = _he(method_label)
    if peak_hz is not None:
        return f"Frekuensi dominan: {_he(f'{peak_hz:.2f}')} Hz [{ml}]"
    return f"Frekuensi dominan: — Hz [{ml}]"


def _html_stat_force(
    v_max: float,
    t_max: float,
    peak_hz: float | None,
    method_label: str,
) -> str:
    line1 = (
        f"Force Maksimum {_he(f'{v_max:.2f}')} Kg saat t = {_he(f'{t_max:.2f}')} s"
    )
    line2 = _html_stat_freq_dominant(peak_hz, method_label)
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:8px;padding:8px 10px;">'
        '<div style="border-left:3px solid #38bdf8;padding-left:8px;">'
        '<div style="color:#38bdf8;font-weight:700;font-size:9px;letter-spacing:0.1em;">FORCE</div>'
        '<table style="margin-top:4px;font-size:11px;color:#cbd5e1;width:100%;">'
        f'<tr><td colspan="2" style="{_STAT_ROW_STYLE}">{line1}</td></tr>'
        f'<tr><td colspan="2" style="{_STAT_ROW_STYLE}">{line2}</td></tr>'
        "</table></div></div>"
    )


def _html_stat_roll(
    v_min: float,
    t_min: float,
    v_max: float,
    t_max: float,
    peak_hz: float | None,
    method_label: str,
) -> str:
    line1 = (
        f"Roll Minimum {_he(f'{v_min:.2f}')}° saat t = {_he(f'{t_min:.2f}')} s"
    )
    line2 = (
        f"Roll Maksimum {_he(f'{v_max:.2f}')}° saat t = {_he(f'{t_max:.2f}')} s"
    )
    line3 = _html_stat_freq_dominant(peak_hz, method_label)
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:8px;padding:8px 10px;">'
        '<div style="border-left:3px solid #f59e0b;padding-left:8px;">'
        '<div style="color:#fbbf24;font-weight:700;font-size:9px;letter-spacing:0.1em;">ROLL</div>'
        '<table style="margin-top:4px;font-size:11px;color:#cbd5e1;width:100%;">'
        f'<tr><td colspan="2" style="{_STAT_ROW_STYLE}">{line1}</td></tr>'
        f'<tr><td colspan="2" style="{_STAT_ROW_STYLE}">{line2}</td></tr>'
        f'<tr><td colspan="2" style="{_STAT_ROW_STYLE}">{line3}</td></tr>'
        "</table></div></div>"
    )


def _html_stat_pitch(
    v_min: float,
    t_min: float,
    v_max: float,
    t_max: float,
    peak_hz: float | None,
    method_label: str,
) -> str:
    line1 = (
        f"Pitch Minimum {_he(f'{v_min:.2f}')}° saat t = {_he(f'{t_min:.2f}')} s"
    )
    line2 = (
        f"Pitch Maksimum {_he(f'{v_max:.2f}')}° saat t = {_he(f'{t_max:.2f}')} s"
    )
    line3 = _html_stat_freq_dominant(peak_hz, method_label)
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:8px;padding:8px 10px;">'
        '<div style="border-left:3px solid #a78bfa;padding-left:8px;">'
        '<div style="color:#c4b5fd;font-weight:700;font-size:9px;letter-spacing:0.1em;">PITCH</div>'
        '<table style="margin-top:4px;font-size:11px;color:#cbd5e1;width:100%;">'
        f'<tr><td colspan="2" style="{_STAT_ROW_STYLE}">{line1}</td></tr>'
        f'<tr><td colspan="2" style="{_STAT_ROW_STYLE}">{line2}</td></tr>'
        f'<tr><td colspan="2" style="{_STAT_ROW_STYLE}">{line3}</td></tr>'
        "</table></div></div>"
    )


def _configure_plot_widget_for_responsive_layout(
    plot: pg.PlotWidget,
    *,
    min_height: int = 100,
) -> None:
    """Izinkan plot menyusut agar jendela muat di layar 1080p (hindari min-height berlebihan)."""
    plot.setMinimumHeight(min_height)
    plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


_SCROLL_AREA_STYLE = """
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical {
    background: #1f2937;
    width: 10px;
    margin: 2px 0 2px 0;
}
QScrollBar::handle:vertical {
    background: #4b5563;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #1f2937;
    height: 10px;
    margin: 0 2px 0 2px;
}
QScrollBar::handle:horizontal {
    background: #4b5563;
    border-radius: 4px;
    min-width: 28px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


def wrap_in_scroll_area(content: QWidget, parent: QWidget | None = None) -> QScrollArea:
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet(_SCROLL_AREA_STYLE)
    scroll.setWidget(content)
    return scroll


def make_three_stack_plots() -> tuple[
    pg.PlotWidget,
    pg.PlotWidget,
    pg.PlotWidget,
    pg.PlotDataItem,
    pg.PlotDataItem,
    pg.PlotDataItem,
]:
    """Tiga plot vertikal (Force, Roll, Pitch) dengan gaya konsisten."""
    force_w = pg.PlotWidget()
    force_w.setLabel("left", "Force (Kg)", color="#e5e7eb", **{"font-size": "12pt"})
    force_w.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "12pt"})
    force_w.setTitle("Force Data (Kg)", color="#e5e7eb", size="12pt")
    force_w.setBackground("#1f2937")
    force_w.showGrid(x=False, y=False)
    force_w.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
    force_w.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
    force_w.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
    force_w.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
    force_c = force_w.plot(pen=pg.mkPen(color="#38bdf8", width=2))

    roll_w = pg.PlotWidget()
    roll_w.setLabel("left", "Angle (°)", color="#e5e7eb", **{"font-size": "11pt"})
    roll_w.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "11pt"})
    roll_w.setTitle("Roll Motion (Deg)", color="#e5e7eb", size="11pt")
    roll_w.setBackground("#1f2937")
    roll_w.showGrid(x=False, y=False)
    roll_w.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
    roll_w.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
    roll_w.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
    roll_w.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
    roll_c = roll_w.plot(pen=pg.mkPen(color="#f59e0b", width=2))

    pitch_w = pg.PlotWidget()
    pitch_w.setLabel("left", "Angle (°)", color="#e5e7eb", **{"font-size": "11pt"})
    pitch_w.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "11pt"})
    pitch_w.setTitle("Pitch Motion (Deg)", color="#e5e7eb", size="11pt")
    pitch_w.setBackground("#1f2937")
    pitch_w.showGrid(x=False, y=False)
    pitch_w.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
    pitch_w.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
    pitch_w.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
    pitch_w.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
    pitch_c = pitch_w.plot(pen=pg.mkPen(color="#a78bfa", width=2))

    for w in (force_w, roll_w, pitch_w):
        _configure_plot_widget_for_responsive_layout(w, min_height=64)

    return force_w, roll_w, pitch_w, force_c, roll_c, pitch_c


def _estimate_sample_rate_hz(ts: list[float]) -> float:
    """Perkiraan fs dari median Δt antar sampel (robust untuk jitter kecil)."""
    if len(ts) < 2:
        return 1.0
    dts: list[float] = []
    for i in range(len(ts) - 1):
        dt = float(ts[i + 1]) - float(ts[i])
        if dt > 1e-9:
            dts.append(dt)
    if not dts:
        return 1.0
    dt_med = statistics.median(dts)
    return 1.0 / dt_med if dt_med > 1e-12 else 1.0


def _spectrum_fft_bins(y: list[float], fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """Frekuensi (Hz) dan magnitudo satu sisi (DC dihilangkan dari plot)."""
    x = np.asarray(y, dtype=np.float64)
    n = int(x.size)
    if n < 2 or fs_hz <= 0:
        return np.array([]), np.array([])
    x = x - np.mean(x)
    win = np.hanning(n)
    xw = x * win
    spec = np.abs(np.fft.rfft(xw))
    freqs = np.fft.rfftfreq(n, d=1.0 / fs_hz)
    wsum = float(np.sum(win))
    if wsum > 1e-12:
        spec = spec / wsum
    if spec.size > 1:
        spec[1:-1] *= 2.0
    return freqs[1:], spec[1:]


def _spectrum_welch_bins(y: list[float], fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD (linear); skip f≈0 untuk plot."""
    x = np.asarray(y, dtype=np.float64)
    n = int(x.size)
    if n < 4 or fs_hz <= 0:
        return np.array([]), np.array([])
    x = x - np.mean(x)
    nperseg = min(max(8, n // 4), 1024, n)
    if nperseg > n:
        nperseg = n
    if nperseg < 4:
        return np.array([]), np.array([])
    nover = min(nperseg // 2, nperseg - 1)
    f, pxx = signal.welch(
        x,
        fs=fs_hz,
        window="hann",
        nperseg=nperseg,
        noverlap=nover,
        scaling="density",
        detrend=False,
    )
    if f.size > 1:
        return f[1:], pxx[1:]
    return np.array([]), np.array([])


# Tinggi minimum per plot waktu tab Analisa (bagi ruang vertikal secara merata)
_ANALYZE_PLOT_MIN_HEIGHT = 72


def make_analyze_time_plot(
    *,
    time_title: str,
    time_left: str,
    line_pen: str,
) -> tuple[pg.PlotWidget, pg.PlotDataItem]:
    """Satu plot waktu untuk tab Analisa."""
    time_w = pg.PlotWidget()
    time_w.setLabel("left", time_left, color="#e5e7eb", **{"font-size": "9pt"})
    time_w.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "9pt"})
    time_w.setTitle(time_title, color="#e5e7eb", size="9pt")
    time_w.setBackground("#1f2937")
    time_w.showGrid(x=False, y=False)
    time_w.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
    time_w.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
    time_w.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
    time_w.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
    time_c = time_w.plot(pen=pg.mkPen(color=line_pen, width=2))
    _configure_plot_widget_for_responsive_layout(time_w, min_height=_ANALYZE_PLOT_MIN_HEIGHT)
    return time_w, time_c


def make_analyze_time_spectrum_row(
    *,
    time_title: str,
    time_left: str,
    spectrum_title: str,
    line_pen: str,
    spectrum_pen: str,
) -> tuple[pg.PlotWidget, pg.PlotDataItem, pg.PlotWidget, pg.PlotDataItem]:
    """Legacy (v2.0–v2.2): plot waktu + spektrum per baris; tidak dipakai tab Analisa v2.3.0."""
    time_w = pg.PlotWidget()
    time_w.setLabel("left", time_left, color="#e5e7eb", **{"font-size": "9pt"})
    time_w.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "9pt"})
    time_w.setTitle(time_title, color="#e5e7eb", size="9pt")
    time_w.setBackground("#1f2937")
    time_w.showGrid(x=False, y=False)
    time_w.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
    time_w.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
    time_w.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
    time_w.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
    time_c = time_w.plot(pen=pg.mkPen(color=line_pen, width=2))

    spec_w = pg.PlotWidget()
    spec_w.setLabel("left", "|FFT|", color="#e5e7eb", **{"font-size": "9pt"})
    spec_w.setLabel("bottom", "Frequency (Hz)", color="#e5e7eb", **{"font-size": "9pt"})
    spec_w.setTitle(spectrum_title, color="#e5e7eb", size="9pt")
    spec_w.setBackground("#1f2937")
    spec_w.showGrid(x=False, y=False)
    spec_w.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
    spec_w.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
    spec_w.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
    spec_w.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
    spec_c = spec_w.plot(pen=pg.mkPen(color=spectrum_pen, width=2))

    for w in (time_w, spec_w):
        _configure_plot_widget_for_responsive_layout(w, min_height=_ANALYZE_PLOT_MIN_HEIGHT)

    return time_w, time_c, spec_w, spec_c


class AnalyzeSingleFileTab(QWidget):
    """Satu CSV rekaman; statistik & plot rekaman — pisahkan dari tab batch nanti."""

    def __init__(
        self,
        *,
        datalog_dir: Path,
        datastatistik_dir: Path,
        statistik_file_suffix: str,
        themed_stat_message: Callable[[QMessageBox.Icon, str, str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._datalog_dir = datalog_dir
        self._datastatistik_dir = datastatistik_dir
        self._statistik_suffix = statistik_file_suffix
        self._themed_stat_message = themed_stat_message

        self._loaded_ts: list[float] | None = None
        self._loaded_f: list[float] | None = None
        self._loaded_r: list[float] | None = None
        self._loaded_p: list[float] | None = None
        self._log_sync_meta: LogSyncMeta | None = None
        self._fs_hz: float = 1.0
        self._segment_region_force: pg.LinearRegionItem | None = None
        self._segment_region_roll: pg.LinearRegionItem | None = None
        self._segment_region_pitch: pg.LinearRegionItem | None = None
        self._segment_syncing = False

        root = QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        time_column = QWidget(self)
        time_column.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        time_layout = QVBoxLayout(time_column)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(4)

        self.force_plot_widget, self.force_curve = make_analyze_time_plot(
            time_title="Force (Kg) — rekaman",
            time_left="Force (Kg)",
            line_pen="#38bdf8",
        )
        self.roll_plot_widget, self.roll_curve = make_analyze_time_plot(
            time_title="Roll (°) — rekaman",
            time_left="Angle (°)",
            line_pen="#f59e0b",
        )
        self.pitch_plot_widget, self.pitch_curve = make_analyze_time_plot(
            time_title="Pitch (°) — rekaman",
            time_left="Angle (°)",
            line_pen="#a78bfa",
        )

        for tw in (self.force_plot_widget, self.roll_plot_widget, self.pitch_plot_widget):
            time_layout.addWidget(tw, 1)

        self._playhead_lines: list[pg.InfiniteLine] = []
        for plot in (
            self.force_plot_widget,
            self.roll_plot_widget,
            self.pitch_plot_widget,
        ):
            playhead = pg.InfiniteLine(
                pos=0,
                angle=90,
                movable=False,
                pen=pg.mkPen("#f472b6", width=2),
            )
            playhead.setZValue(25)
            playhead.setVisible(False)
            plot.addItem(playhead)
            self._playhead_lines.append(playhead)

        self.video_panel = AnalyzeVideoPanel(self)
        self.video_panel.setToolTip(
            "Sinkron dengan plot: garis vertikal pink = posisi video pada sumbu "
            "Time (s). Rekaman baru memakai metadata SyncCsvT0 di CSV; file lama "
            "memakai TimeStamp baris pertama + detik video."
        )
        self.video_panel.position_changed.connect(self._on_video_position_changed)

        video_scroll = wrap_in_scroll_area(self.video_panel, self)
        video_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        right_column = QWidget(self)
        right_column.setMinimumWidth(260)
        right_column.setMaximumWidth(380)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        load_group = QGroupBox("", self)
        load_group.setLayout(QVBoxLayout())
        load_group.layout().setContentsMargins(10, 10, 10, 10)
        load_group.layout().setSpacing(8)

        self.load_csv_btn = QPushButton("Load CSV…", self)
        self.load_csv_btn.clicked.connect(self.load_csv)
        load_group.layout().addWidget(self.load_csv_btn)

        self.load_video_btn = QPushButton("Load Video…", self)
        self.load_video_btn.setToolTip(
            "Muat berkas MP4 secara manual jika pasangan otomatis tidak ditemukan."
        )
        self.load_video_btn.clicked.connect(self.load_video)
        load_group.layout().addWidget(self.load_video_btn)

        self.meta_label = QLabel(self)
        self.meta_label.setObjectName("AnalyzeRichLabel")
        self.meta_label.setWordWrap(True)
        self.meta_label.setTextFormat(Qt.TextFormat.RichText)
        self.meta_label.setText(_html_load_placeholder())
        load_group.layout().addWidget(self.meta_label)

        settings_group = QGroupBox("Analisa Setting", self)
        settings_inner = QVBoxLayout(settings_group)
        settings_inner.setContentsMargins(10, 10, 10, 10)
        settings_inner.setSpacing(6)
        spectrum_method_row = QHBoxLayout()
        spectrum_method_row.setSpacing(10)
        spectrum_lbl = QLabel("Metode spektrum (statistik):", self)
        spectrum_lbl.setStyleSheet("color: #e5e7eb; font-size: 10pt;")
        spectrum_lbl.setToolTip(
            "Frekuensi dominan pada kartu statistik dan ekspor DataStatistik "
            "(plot spektrum tidak ditampilkan)."
        )
        self._spectrum_method_combo = QComboBox(self)
        self._spectrum_method_combo.addItem("FFT", userData=False)
        self._spectrum_method_combo.addItem("Welch PSD", userData=True)
        self._spectrum_method_combo.blockSignals(True)
        self._spectrum_method_combo.setCurrentIndex(0)
        self._spectrum_method_combo.blockSignals(False)
        self._spectrum_method_combo.setMinimumWidth(140)
        self._spectrum_method_combo.currentIndexChanged.connect(self._on_spectrum_method_changed)
        spectrum_method_row.addWidget(spectrum_lbl, 0)
        spectrum_method_row.addWidget(self._spectrum_method_combo, 0)
        spectrum_method_row.addStretch(1)
        settings_inner.addLayout(spectrum_method_row)

        segment_caption = QLabel("Segmen waktu (geser pada plot Force):", self)
        segment_caption.setStyleSheet("color: #e5e7eb; font-size: 10pt;")
        settings_inner.addWidget(segment_caption)
        self.segment_info_label = QLabel("Segmen analisa: —", self)
        self.segment_info_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        self.segment_info_label.setWordWrap(True)
        self.segment_info_label.setToolTip(
            "Geser tepi area biru pada plot Force untuk membatasi segmen analisa. "
            "Roll dan Pitch menampilkan area yang sama; statistik "
            "dihitung hanya pada sampel di dalam segmen."
        )
        settings_inner.addWidget(self.segment_info_label)

        gap_method_caption = QLabel("Metode gap rekaman CSV:", self)
        gap_method_caption.setStyleSheet("color: #e5e7eb; font-size: 10pt;")
        settings_inner.addWidget(gap_method_caption)

        self._gap_method_group = QButtonGroup(self)
        self._gap_method_a_radio = QRadioButton("Metode A — per gap (lokal)", self)
        self._gap_method_b_radio = QRadioButton("Metode B — global (ringkas)", self)
        self._gap_method_a_radio.setToolTip(
            "Jumlahkan sampel hilang per lubang Δt antar baris berurutan "
            f"(gap jika Δt > {GAP_LOSS_TOLERANCE_FACTOR:.1f}× median Δt)."
        )
        self._gap_method_b_radio.setToolTip(
            "Bandingkan jumlah baris aktual dengan perkiraan dari durasi ÷ median Δt."
        )
        for rb in (self._gap_method_a_radio, self._gap_method_b_radio):
            rb.setStyleSheet("color: #e5e7eb; font-size: 10pt;")
        self._gap_method_group.addButton(self._gap_method_a_radio, 0)
        self._gap_method_group.addButton(self._gap_method_b_radio, 1)
        self._gap_method_b_radio.setChecked(True)
        self._gap_method_group.idClicked.connect(self._on_gap_loss_method_changed)
        settings_inner.addWidget(self._gap_method_a_radio)
        settings_inner.addWidget(self._gap_method_b_radio)

        self.stats_group = QGroupBox("Statistik", self)
        stats_inner = QVBoxLayout(self.stats_group)
        stats_inner.setContentsMargins(10, 10, 10, 10)
        stats_inner.setSpacing(6)
        self.stat_tstart_label = QLabel(self)
        self.stat_force_label = QLabel(self)
        self.stat_roll_label = QLabel(self)
        self.stat_pitch_label = QLabel(self)
        self.stat_gap_loss_label = QLabel(self)
        for lb in (
            self.stat_tstart_label,
            self.stat_force_label,
            self.stat_roll_label,
            self.stat_pitch_label,
            self.stat_gap_loss_label,
        ):
            lb.setObjectName("AnalyzeRichLabel")
            lb.setWordWrap(True)
            lb.setTextFormat(Qt.TextFormat.RichText)
        self.stat_tstart_label.setText(_html_tstart_placeholder())
        self.stat_force_label.setText(_html_stat_placeholder())
        self.stat_roll_label.setText(_html_stat_placeholder())
        self.stat_pitch_label.setText(_html_stat_placeholder())
        self.stat_gap_loss_label.setText(_html_gap_loss_placeholder())

        stats_inner.addWidget(self.stat_tstart_label)
        stats_inner.addWidget(self.stat_force_label)
        stats_inner.addWidget(self.stat_roll_label)
        stats_inner.addWidget(self.stat_pitch_label)
        stats_inner.addWidget(self.stat_gap_loss_label)

        self.save_stats_btn = QPushButton("Simpan statistik…", self)
        self.save_stats_btn.setObjectName("SaveStatsButton")
        self.save_stats_btn.setToolTip(
            "Simpan langsung ke folder DataStatistik/ di samping DataLog: "
            "<nama_file_log>_DataStaistik.csv (UTF-8), tanpa dialog Save As."
        )
        self.save_stats_btn.setEnabled(False)
        self.save_stats_btn.clicked.connect(self.save_statistics_csv)
        stats_inner.addWidget(self.save_stats_btn)

        self._scatter_force: pg.ScatterPlotItem | None = None
        self._scatter_roll: pg.ScatterPlotItem | None = None
        self._scatter_pitch: pg.ScatterPlotItem | None = None
        self._stat_texts: list[tuple[pg.PlotWidget, pg.TextItem]] = []
        self._export_ctx: dict[str, str] | None = None
        self._stats_snapshot: dict[str, float | str | None] | None = None
        self._loaded_csv_path: Path | None = None

        right_layout.addWidget(load_group, 0)
        right_layout.addWidget(settings_group, 0)

        stats_scroll_body = QWidget(self)
        stats_scroll_body.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )
        stats_scroll_layout = QVBoxLayout(stats_scroll_body)
        stats_scroll_layout.setContentsMargins(0, 0, 0, 0)
        stats_scroll_layout.setSpacing(0)
        stats_scroll_layout.addWidget(self.stats_group)
        stats_scroll = wrap_in_scroll_area(stats_scroll_body, self)
        stats_scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(stats_scroll, 1)

        root.addWidget(time_column, 3)
        root.addWidget(video_scroll, 2)
        root.addWidget(right_column, 1)

    def _spectrum_use_welch(self) -> bool:
        """True jika metode spektrum = Welch PSD (dropdown)."""
        idx = self._spectrum_method_combo.currentIndex()
        if idx < 0:
            return False
        data = self._spectrum_method_combo.itemData(idx)
        return bool(data) if data is not None else False

    def _video_sec_to_csv_time(self, video_sec: float) -> float | None:
        """Detik media → sumbu Time (s) pada plot (metadata SyncCsvT0 atau fallback kasar)."""
        if video_sec < 0 or self._loaded_ts is None or self.video_panel.video_path() is None:
            return None
        t0 = self._loaded_ts[0]
        t1 = self._loaded_ts[-1]
        sync = self._log_sync_meta
        if sync is not None and sync.has_precise_sync and sync.sync_csv_t0 is not None:
            wall_offset = 0.0
            if sync.sync_log_wall_start is not None and sync.sync_first_sample_wall is not None:
                wall_offset = sync.sync_first_sample_wall - sync.sync_log_wall_start
            csv_t = sync.sync_csv_t0 + max(0.0, video_sec - wall_offset)
        else:
            csv_t = t0 + video_sec
        return min(t1, max(t0, csv_t))

    def _on_video_position_changed(self, video_sec: float) -> None:
        if video_sec < 0:
            for line in self._playhead_lines:
                line.setVisible(False)
            return
        csv_t = self._video_sec_to_csv_time(video_sec)
        if csv_t is None:
            for line in self._playhead_lines:
                line.setVisible(False)
            return
        for line in self._playhead_lines:
            line.setPos(csv_t)
            line.setVisible(True)

    def _segment_time_bounds(self) -> tuple[float, float] | None:
        if self._segment_region_force is not None:
            a, b = self._segment_region_force.getRegion()
            return min(a, b), max(a, b)
        if self._loaded_ts:
            return min(self._loaded_ts), max(self._loaded_ts)
        return None

    def _slice_loaded_segment(
        self,
    ) -> tuple[list[float], list[float], list[float], list[float]] | None:
        if (
            self._loaded_ts is None
            or self._loaded_f is None
            or self._loaded_r is None
            or self._loaded_p is None
        ):
            return None
        bounds = self._segment_time_bounds()
        if bounds is None:
            return None
        t_lo, t_hi = bounds
        ts_out: list[float] = []
        f_out: list[float] = []
        r_out: list[float] = []
        p_out: list[float] = []
        for t, fv, rv, pv in zip(
            self._loaded_ts, self._loaded_f, self._loaded_r, self._loaded_p
        ):
            if t_lo <= t <= t_hi:
                ts_out.append(t)
                f_out.append(fv)
                r_out.append(rv)
                p_out.append(pv)
        return ts_out, f_out, r_out, p_out

    def _setup_segment_regions(self, ts_list: list[float]) -> None:
        if not ts_list:
            return
        t_min = min(ts_list)
        t_max = max(ts_list)

        if self._segment_region_force is None:
            self._segment_region_force = pg.LinearRegionItem(
                values=[t_min, t_max],
                brush=_SEGMENT_BRUSH_FORCE,
                movable=True,
                pen=_SEGMENT_PEN_FORCE,
            )
            self._segment_region_force.setZValue(5)
            self._segment_region_force.sigRegionChanged.connect(
                self._on_segment_region_changed
            )
            self.force_plot_widget.addItem(self._segment_region_force)

            self._segment_region_roll = pg.LinearRegionItem(
                values=[t_min, t_max],
                brush=_SEGMENT_BRUSH_ROLL,
                movable=False,
                pen=_SEGMENT_PEN_ROLL,
            )
            self._segment_region_roll.setZValue(5)
            self.roll_plot_widget.addItem(self._segment_region_roll)

            self._segment_region_pitch = pg.LinearRegionItem(
                values=[t_min, t_max],
                brush=_SEGMENT_BRUSH_PITCH,
                movable=False,
                pen=_SEGMENT_PEN_PITCH,
            )
            self._segment_region_pitch.setZValue(5)
            self.pitch_plot_widget.addItem(self._segment_region_pitch)
        else:
            self._segment_syncing = True
            self._segment_region_force.blockSignals(True)
            self._segment_region_force.setRegion([t_min, t_max])
            self._segment_region_force.blockSignals(False)
            self._segment_syncing = False
            self._sync_mirror_segment_regions(t_min, t_max)

        self._update_segment_info_label(t_min, t_max)

    def _sync_mirror_segment_regions(self, t_lo: float, t_hi: float) -> None:
        lo, hi = min(t_lo, t_hi), max(t_lo, t_hi)
        for region in (self._segment_region_roll, self._segment_region_pitch):
            if region is not None:
                region.blockSignals(True)
                region.setRegion([lo, hi])
                region.blockSignals(False)

    def _update_segment_info_label(self, t_lo: float, t_hi: float) -> None:
        lo, hi = min(t_lo, t_hi), max(t_lo, t_hi)
        if self._loaded_ts:
            full_lo, full_hi = min(self._loaded_ts), max(self._loaded_ts)
            if abs(lo - full_lo) < 1e-6 and abs(hi - full_hi) < 1e-6:
                self.segment_info_label.setText("Segmen analisa: seluruh rekaman")
                return
        self.segment_info_label.setText(
            f"Segmen analisa: {lo:.2f} s — {hi:.2f} s (durasi {hi - lo:.2f} s)"
        )

    def _on_segment_region_changed(self) -> None:
        if self._segment_syncing or self._segment_region_force is None:
            return
        t_lo, t_hi = self._segment_region_force.getRegion()
        if self._loaded_ts:
            full_lo, full_hi = min(self._loaded_ts), max(self._loaded_ts)
            span = full_hi - full_lo
            eps = max(span * 1e-9, 1e-9)
            clamped_lo = max(full_lo, min(t_lo, full_hi))
            clamped_hi = max(full_lo, min(t_hi, full_hi))
            if clamped_hi - clamped_lo < eps:
                mid = (clamped_lo + clamped_hi) * 0.5
                clamped_lo = max(full_lo, mid - eps)
                clamped_hi = min(full_hi, mid + eps)
            if abs(clamped_lo - t_lo) > 1e-9 or abs(clamped_hi - t_hi) > 1e-9:
                self._segment_syncing = True
                self._segment_region_force.blockSignals(True)
                self._segment_region_force.setRegion([clamped_lo, clamped_hi])
                self._segment_region_force.blockSignals(False)
                self._segment_syncing = False
                t_lo, t_hi = clamped_lo, clamped_hi
        self._sync_mirror_segment_regions(t_lo, t_hi)
        self._update_segment_info_label(t_lo, t_hi)
        self._reanalyze_current_segment()

    def _reanalyze_current_segment(self) -> None:
        sliced = self._slice_loaded_segment()
        if sliced is None:
            return
        ts_list, f_list, r_list, p_list = sliced
        self._clear_stat_markers()
        if not ts_list:
            self._stats_snapshot = None
            self.save_stats_btn.setEnabled(False)
            self.stat_tstart_label.setText(_html_tstart_placeholder())
            self.stat_force_label.setText(_html_stat_placeholder())
            self.stat_roll_label.setText(_html_stat_placeholder())
            self.stat_pitch_label.setText(_html_stat_placeholder())
            self.stat_gap_loss_label.setText(_html_gap_loss_placeholder())
            return
        self._apply_statistics(ts_list, f_list, r_list, p_list)
        bounds = self._segment_time_bounds()
        if bounds is not None and self._stats_snapshot is not None:
            self._stats_snapshot["segment_start_s"] = float(bounds[0])
            self._stats_snapshot["segment_end_s"] = float(bounds[1])
        if ts_list:
            self._fs_hz = _estimate_sample_rate_hz(ts_list)

    def _gap_loss_method_key(self) -> str:
        """``A`` = per gap; ``B`` = global."""
        return "A" if self._gap_method_a_radio.isChecked() else "B"

    def _on_gap_loss_method_changed(self, _button_id: int) -> None:
        if self._loaded_ts is not None:
            self._reanalyze_current_segment()

    def _on_spectrum_method_changed(self, _index: int) -> None:
        self._reanalyze_current_segment()

    def _try_load_paired_video(self, csv_path: Path) -> str | None:
        video_path = csv_path.with_suffix(".mp4")
        if video_path.is_file() and self.video_panel.load_video(video_path):
            return video_path.name
        self.video_panel.clear()
        return None

    def _update_meta_label(self) -> None:
        if self._export_ctx is None:
            self.meta_label.setText(_html_load_placeholder())
            return
        video_name = (
            self.video_panel.video_path().name if self.video_panel.video_path() else None
        )
        self.meta_label.setText(
            _html_load_block(
                self._export_ctx["swimmer"],
                self._export_ctx["stroke"],
                self._export_ctx["source_file"],
                video_name,
            )
        )

    def load_video(self) -> None:
        start_dir = str(self._datalog_dir) if self._datalog_dir.is_dir() else ""
        if self._loaded_csv_path is not None:
            start_dir = str(self._loaded_csv_path.parent)
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Load video rekaman",
            start_dir,
            "Video MP4 (*.mp4);;Semua (*.*)",
        )
        if not path_str:
            return
        path = Path(path_str)
        if not self.video_panel.load_video(path):
            QMessageBox.warning(self, "Load Video", f"Tidak bisa membuka video:\n{path}")
            return
        self._update_meta_label()
        self._on_video_position_changed(self.video_panel.current_position_s())

    def load_csv(self) -> None:
        start_dir = str(self._datalog_dir) if self._datalog_dir.is_dir() else str(self._datalog_dir.parent)
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Load CSV rekaman",
            start_dir,
            "CSV (*.csv);;Semua (*.*)",
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            swimmer, stroke, ts_list, f_list, r_list, p_list, sync_meta = parse_logged_csv(path)
        except OSError as e:
            QMessageBox.critical(self, "Load CSV", f"Tidak bisa membaca file:\n{e}")
            return
        except ValueError as e:
            QMessageBox.warning(self, "Load CSV", str(e))
            return

        self.force_curve.setData(ts_list, f_list)
        self.roll_curve.setData(ts_list, r_list)
        self.pitch_curve.setData(ts_list, p_list)

        self._loaded_ts = ts_list
        self._loaded_f = f_list
        self._loaded_r = r_list
        self._loaded_p = p_list
        self._log_sync_meta = sync_meta
        self._loaded_csv_path = path

        video_name = self._try_load_paired_video(path)

        self._export_ctx = {
            "swimmer": swimmer,
            "stroke": stroke,
            "source_file": path.name,
        }
        self.meta_label.setText(_html_load_block(swimmer, stroke, path.name, video_name))

        self._setup_segment_regions(ts_list)
        self._reanalyze_current_segment()
        if video_name is None:
            self._on_video_position_changed(-1.0)
        else:
            self._on_video_position_changed(self.video_panel.current_position_s())

    def _clear_stat_markers(self) -> None:
        for plot, txt in self._stat_texts:
            plot.removeItem(txt)
        self._stat_texts.clear()

        for plot, attr in (
            (self.force_plot_widget, "_scatter_force"),
            (self.roll_plot_widget, "_scatter_roll"),
            (self.pitch_plot_widget, "_scatter_pitch"),
        ):
            sc = getattr(self, attr, None)
            if sc is not None:
                plot.removeItem(sc)
                setattr(self, attr, None)

    def _add_marker_label(
        self,
        plot: pg.PlotWidget,
        marker_x: float,
        marker_y: float,
        text: str,
        ts_min: float,
        ts_max: float,
    ) -> None:
        span = (ts_max - ts_min) or 1.0
        dx = max(span * 0.028, 1e-6)
        mid = (ts_min + ts_max) * 0.5
        if marker_x <= mid:
            lx = marker_x + dx
            anchor = (0.0, 0.5)
        else:
            lx = marker_x - dx
            anchor = (1.0, 0.5)

        ti = pg.TextItem(
            text,
            color="#f8fafc",
            anchor=anchor,
            border=pg.mkPen("#94a3b8", width=1),
            fill=pg.mkBrush(30, 41, 59, 230),
        )
        ti.setFont(QFont("Segoe UI", 9))
        ti.setZValue(11)
        ti.setPos(lx, marker_y)
        plot.addItem(ti)
        self._stat_texts.append((plot, ti))

    def _apply_statistics(
        self,
        ts_list: list[float],
        f_list: list[float],
        r_list: list[float],
        p_list: list[float],
    ) -> None:
        n = len(ts_list)
        if n == 0:
            self._stats_snapshot = None
            self.save_stats_btn.setEnabled(False)
            self.stat_tstart_label.setText(_html_tstart_placeholder())
            self.stat_force_label.setText(_html_stat_placeholder())
            self.stat_roll_label.setText(_html_stat_placeholder())
            self.stat_pitch_label.setText(_html_stat_placeholder())
            self.stat_gap_loss_label.setText(_html_gap_loss_placeholder())
            return

        def _argmin_first(vals: list[float]) -> int:
            return min(range(len(vals)), key=lambda i: vals[i])

        def _argmax_first(vals: list[float]) -> int:
            return max(range(len(vals)), key=lambda i: vals[i])

        i_fmax = _argmax_first(f_list)
        t_fmax = ts_list[i_fmax]
        v_fmax = f_list[i_fmax]

        i_rmin = _argmin_first(r_list)
        i_rmax = _argmax_first(r_list)
        i_pmin = _argmin_first(p_list)
        i_pmax = _argmax_first(p_list)

        ts_min = min(ts_list)
        ts_max = max(ts_list)
        t_start = ts_min
        t_stop = ts_max
        fs = _estimate_sample_rate_hz(ts_list)
        use_welch = self._spectrum_use_welch()
        method_label = "Welch PSD" if use_welch else "FFT"
        peak_f = _spectrum_peak_frequency_hz(f_list, fs, use_welch=use_welch)
        peak_r = _spectrum_peak_frequency_hz(r_list, fs, use_welch=use_welch)
        peak_p = _spectrum_peak_frequency_hz(p_list, fs, use_welch=use_welch)

        gap_stats = compute_gap_loss(ts_list, method=self._gap_loss_method_key())
        if gap_stats is not None:
            self.stat_gap_loss_label.setText(_html_stat_gap_loss(gap_stats))
        else:
            self.stat_gap_loss_label.setText(_html_gap_loss_placeholder())

        self.stat_tstart_label.setText(_html_stat_timestamp_range(t_start, t_stop))
        self.stat_force_label.setText(
            _html_stat_force(v_fmax, t_fmax, peak_f, method_label)
        )
        self.stat_roll_label.setText(
            _html_stat_roll(
                r_list[i_rmin],
                ts_list[i_rmin],
                r_list[i_rmax],
                ts_list[i_rmax],
                peak_r,
                method_label,
            )
        )
        self.stat_pitch_label.setText(
            _html_stat_pitch(
                p_list[i_pmin],
                ts_list[i_pmin],
                p_list[i_pmax],
                ts_list[i_pmax],
                peak_p,
                method_label,
            )
        )

        self._scatter_force = pg.ScatterPlotItem(
            pos=[(t_fmax, v_fmax)],
            size=14,
            symbol="o",
            pen=pg.mkPen("#f8fafc", width=2),
            brush=pg.mkBrush(MARKER_MAX_COLOR),
        )
        self._scatter_force.setZValue(10)
        self.force_plot_widget.addItem(self._scatter_force)
        self._add_marker_label(
            self.force_plot_widget,
            t_fmax,
            v_fmax,
            f"t: {t_fmax:.2f} s\nmax: {v_fmax:.2f} Kg",
            ts_min,
            ts_max,
        )

        self._scatter_roll = pg.ScatterPlotItem(
            pos=[
                (ts_list[i_rmin], r_list[i_rmin]),
                (ts_list[i_rmax], r_list[i_rmax]),
            ],
            size=14,
            symbol="o",
            pen=pg.mkPen("#0f172a", width=2),
            brush=[pg.mkBrush(MARKER_MIN_COLOR), pg.mkBrush(MARKER_MAX_COLOR)],
        )
        self._scatter_roll.setZValue(10)
        self.roll_plot_widget.addItem(self._scatter_roll)
        tr_min, vr_min = ts_list[i_rmin], r_list[i_rmin]
        tr_max, vr_max = ts_list[i_rmax], r_list[i_rmax]
        self._add_marker_label(
            self.roll_plot_widget,
            tr_min,
            vr_min,
            f"t: {tr_min:.2f} s\nmin: {vr_min:.2f}°",
            ts_min,
            ts_max,
        )
        self._add_marker_label(
            self.roll_plot_widget,
            tr_max,
            vr_max,
            f"t: {tr_max:.2f} s\nmax: {vr_max:.2f}°",
            ts_min,
            ts_max,
        )

        self._scatter_pitch = pg.ScatterPlotItem(
            pos=[
                (ts_list[i_pmin], p_list[i_pmin]),
                (ts_list[i_pmax], p_list[i_pmax]),
            ],
            size=14,
            symbol="o",
            pen=pg.mkPen("#0f172a", width=2),
            brush=[pg.mkBrush(MARKER_MIN_COLOR), pg.mkBrush(MARKER_MAX_COLOR)],
        )
        self._scatter_pitch.setZValue(10)
        self.pitch_plot_widget.addItem(self._scatter_pitch)
        tp_min, vp_min = ts_list[i_pmin], p_list[i_pmin]
        tp_max, vp_max = ts_list[i_pmax], p_list[i_pmax]
        self._add_marker_label(
            self.pitch_plot_widget,
            tp_min,
            vp_min,
            f"t: {tp_min:.2f} s\nmin: {vp_min:.2f}°",
            ts_min,
            ts_max,
        )
        self._add_marker_label(
            self.pitch_plot_widget,
            tp_max,
            vp_max,
            f"t: {tp_max:.2f} s\nmax: {vp_max:.2f}°",
            ts_min,
            ts_max,
        )

        self._stats_snapshot = {
            "timestamp_start_s": float(t_start),
            "timestamp_stop_s": float(t_stop),
            "force_max_kg": float(v_fmax),
            "force_max_t_s": float(t_fmax),
            "roll_min_deg": float(r_list[i_rmin]),
            "roll_min_t_s": float(ts_list[i_rmin]),
            "roll_max_deg": float(r_list[i_rmax]),
            "roll_max_t_s": float(ts_list[i_rmax]),
            "pitch_min_deg": float(p_list[i_pmin]),
            "pitch_min_t_s": float(ts_list[i_pmin]),
            "pitch_max_deg": float(p_list[i_pmax]),
            "pitch_max_t_s": float(ts_list[i_pmax]),
            "dominant_hz_force": peak_f,
            "dominant_hz_roll": peak_r,
            "dominant_hz_pitch": peak_p,
            "spectrum_method": method_label,
            "gap_loss_method": gap_stats.method_label if gap_stats else "",
            "gap_dt_nominal_s": gap_stats.dt_nominal_s if gap_stats else None,
            "gap_fs_hz": gap_stats.fs_hz if gap_stats else None,
            "gap_samples_actual": gap_stats.samples_actual if gap_stats else None,
            "gap_samples_lost": gap_stats.samples_lost if gap_stats else None,
            "gap_loss_pct": gap_stats.loss_pct if gap_stats else None,
            "gap_count": gap_stats.gap_count if gap_stats else None,
            "gap_samples_expected": gap_stats.samples_expected if gap_stats else None,
        }
        self.save_stats_btn.setEnabled(self._export_ctx is not None)

    @staticmethod
    def _csv_dominant_hz_cell(v: float | str | None) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return f"{float(v):.6g}"

    @staticmethod
    def _write_statistik_csv(
        path: Path, ctx: dict[str, str], snap: dict[str, float | str | None]
    ) -> None:
        exported_at = datetime.now().isoformat(timespec="seconds")
        swimmer = ctx["swimmer"]
        stroke = ctx["stroke"]
        source_file = ctx["source_file"]
        method = str(snap["spectrum_method"])

        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Nama_Perenang", swimmer])
            w.writerow(["Gaya_Renang", stroke])
            w.writerow(["Waktu_Ekspor_Statistik", exported_at])
            w.writerow(["Berkas_Sumber", source_file])
            seg_lo = snap.get("segment_start_s")
            seg_hi = snap.get("segment_end_s")
            if seg_lo is not None and seg_hi is not None:
                w.writerow(
                    [
                        "Segmen_analisa_start (s)",
                        f"{float(seg_lo):.6g}",
                    ]
                )
                w.writerow(
                    [
                        "Segmen_analisa_finish (s)",
                        f"{float(seg_hi):.6g}",
                    ]
                )
            w.writerow([])
            w.writerow(
                ["Timestampstart (s)", f"{float(snap['timestamp_start_s']):.6g}"]
            )
            w.writerow(
                ["Timestampstop (s)", f"{float(snap['timestamp_stop_s']):.6g}"]
            )
            w.writerow([])
            w.writerow(["Metrik", "Nilai", "Satuan", "Waktu (s)"])
            w.writerow(
                [
                    "Force_maksimum",
                    f"{snap['force_max_kg']:.6g}",
                    "Kg",
                    f"{snap['force_max_t_s']:.6g}",
                ]
            )
            w.writerow(
                [
                    "Roll_minimum",
                    f"{snap['roll_min_deg']:.6g}",
                    "deg",
                    f"{snap['roll_min_t_s']:.6g}",
                ]
            )
            w.writerow(
                [
                    "Roll_maksimum",
                    f"{snap['roll_max_deg']:.6g}",
                    "deg",
                    f"{snap['roll_max_t_s']:.6g}",
                ]
            )
            w.writerow(
                [
                    "Pitch_minimum",
                    f"{snap['pitch_min_deg']:.6g}",
                    "deg",
                    f"{snap['pitch_min_t_s']:.6g}",
                ]
            )
            w.writerow(
                [
                    "Pitch_maksimum",
                    f"{snap['pitch_max_deg']:.6g}",
                    "deg",
                    f"{snap['pitch_max_t_s']:.6g}",
                ]
            )
            w.writerow([])
            w.writerow([])
            w.writerow(["Metrik", "Frekuensi Dominan (Hz)", "Metode"])
            w.writerow(
                [
                    "Force",
                    AnalyzeSingleFileTab._csv_dominant_hz_cell(snap["dominant_hz_force"]),
                    method,
                ]
            )
            w.writerow(
                [
                    "Roll",
                    AnalyzeSingleFileTab._csv_dominant_hz_cell(snap["dominant_hz_roll"]),
                    method,
                ]
            )
            w.writerow(
                [
                    "Pitch",
                    AnalyzeSingleFileTab._csv_dominant_hz_cell(snap["dominant_hz_pitch"]),
                    method,
                ]
            )
            w.writerow([])
            w.writerow(["Gap rekaman CSV (estimasi)"])
            w.writerow(["Metrik", "Nilai"])
            w.writerow(["Metode", str(snap.get("gap_loss_method", ""))])
            if snap.get("gap_dt_nominal_s") is not None:
                w.writerow(
                    [
                        "Delta_t_nominal",
                        f"{float(snap['gap_dt_nominal_s']):.6g}",
                        "s",
                    ]
                )
                w.writerow(
                    [
                        "Laju_sampel_efektif",
                        f"{float(snap['gap_fs_hz']):.6g}",
                        "Hz",
                    ]
                )
            if snap.get("gap_samples_actual") is not None:
                w.writerow(
                    [
                        "Sampel_tercatat",
                        str(int(snap["gap_samples_actual"])),
                        "baris",
                    ]
                )
            if snap.get("gap_samples_expected") is not None:
                w.writerow(
                    [
                        "Sampel_diharapkan",
                        str(int(snap["gap_samples_expected"])),
                        "baris",
                    ]
                )
            if snap.get("gap_count") is not None:
                w.writerow(
                    [
                        "Jumlah_gap",
                        str(int(snap["gap_count"])),
                        "kejadian",
                    ]
                )
            if snap.get("gap_samples_lost") is not None:
                w.writerow(
                    [
                        "Sampel_hilang_estimasi",
                        str(int(snap["gap_samples_lost"])),
                        "sampel",
                    ]
                )
            if snap.get("gap_loss_pct") is not None:
                w.writerow(
                    [
                        "Persen_hilang",
                        f"{float(snap['gap_loss_pct']):.4g}",
                        "%",
                    ]
                )

    def save_statistics_csv(self) -> None:
        if self._export_ctx is None or self._stats_snapshot is None:
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Simpan statistik",
                "Belum ada data analisa. Muat file CSV di tab Analisa terlebih dahulu.",
            )
            return

        ctx = self._export_ctx
        snap = self._stats_snapshot

        try:
            self._datastatistik_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._themed_stat_message(
                QMessageBox.Icon.Critical,
                "Simpan statistik",
                f"Tidak bisa membuat folder DataStatistik:\n{e}",
            )
            return

        src_name = Path(ctx["source_file"])
        suffix = src_name.suffix if src_name.suffix else ".csv"
        out_name = f"{src_name.stem}{self._statistik_suffix}{suffix}"
        path = self._datastatistik_dir / out_name
        try:
            self._write_statistik_csv(path, ctx, snap)
        except OSError as e:
            self._themed_stat_message(
                QMessageBox.Icon.Critical,
                "Simpan statistik",
                f"Tidak bisa menulis file:\n{e}",
            )
            return

        self._themed_stat_message(
            QMessageBox.Icon.Information,
            "Simpan statistik",
            f"Tersimpan:\n{_path_text_for_dialog(path)}",
        )

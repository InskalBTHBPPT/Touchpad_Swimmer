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
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from scipy import signal

from analyze_metrics_core import GAP_LOSS_TOLERANCE_FACTOR, GapLossStats, compute_gap_loss
from analyze_video_panel import AnalyzeVideoPanel, _ANALYZE_TRANSPORT_BUTTON_STYLE
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

_ZERO_OFFSET_DEFAULT_DURATION_S = 2.0
_ZERO_OFFSET_TEST_GAP_S = 2.0
_OFFSET_BRUSH_FORCE = pg.mkBrush(34, 197, 94, 42)
_OFFSET_PEN_FORCE = pg.mkPen("#22c55e", width=1)
_OFFSET_BRUSH_ROLL = pg.mkBrush(34, 197, 94, 30)
_OFFSET_PEN_ROLL = pg.mkPen("#22c55e", width=1)
_OFFSET_BRUSH_PITCH = pg.mkBrush(34, 197, 94, 30)
_OFFSET_PEN_PITCH = pg.mkPen("#22c55e", width=1)
_BOUNDS_EPS_S = 1e-3


def _path_text_for_dialog(path: Path | str) -> str:
    s = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    if len(s) >= 3 and s[0].isalpha() and s[1] == ":" and s[2] == "/":
        s = s[:2] + "\u2060" + s[2:]
    return s


def _analyze_meta_block(
    title: str,
    parent: QWidget,
    *,
    monospace: bool = False,
) -> tuple[QLabel, QWidget]:
    """Judul statis di atas, nilai dinamis di bawah (header kolom plot)."""
    block = QWidget(parent)
    block.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    lay = QVBoxLayout(block)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    title_lbl = QLabel(title, block)
    title_lbl.setStyleSheet(
        "color: #9ca3af; font-size: 9pt; font-weight: 600; letter-spacing: 0.06em;"
    )
    value_lbl = QLabel("—", block)
    mono_css = (
        "font-family: Consolas, 'Cascadia Mono', 'Courier New', monospace;"
        if monospace
        else ""
    )
    value_lbl.setStyleSheet(
        f"color: #f8fafc; font-size: 12pt; font-weight: 600; {mono_css}"
    )
    value_lbl.setWordWrap(True)
    lay.addWidget(title_lbl)
    lay.addWidget(value_lbl)
    return value_lbl, block


_STATS_TABLE_STYLE = """
QTableWidget {
    background-color: #111827;
    alternate-background-color: #111827;
    color: #e5e7eb;
    gridline-color: #374151;
    border: 1px solid #374151;
    border-radius: 8px;
    font-size: 10pt;
}
QTableWidget::item {
    background-color: #111827;
    color: #e5e7eb;
    padding: 4px 6px;
}
QHeaderView::section {
    background-color: #374151;
    color: #e5e7eb;
    border: none;
    border-bottom: 1px solid #4b5563;
    padding: 6px 8px;
    font-weight: 600;
}
"""

_STATS_COL_FORCE = "#38bdf8"
_STATS_COL_ROLL = "#f59e0b"
_STATS_COL_PITCH = "#a78bfa"

_STATS_MATRIX_ROW_LABELS = (
    "TimeStamp Start (s)",
    "TimeStamp Stop (s)",
    "Zero offset start (s)",
    "Zero offset stop (s)",
    "Rata-rata offset",
    "Maksimum",
    "t @ maks (s)",
    "Minimum",
    "t @ min (s)",
    "Frekuensi dominan (Hz)",
    "Metode spektrum",
    "Gap — metode",
    "Gap — Δt nominal (s)",
    "Gap — sampel tercatat",
    "Gap — sampel hilang",
    "Gap — hilang (%)",
    "Gap — jumlah / diharapkan",
)

_STATS_MERGED_VALUE_ROWS = frozenset({
    _STATS_MATRIX_ROW_LABELS.index("Metode spektrum"),
    _STATS_MATRIX_ROW_LABELS.index("Gap — metode"),
    _STATS_MATRIX_ROW_LABELS.index("Gap — Δt nominal (s)"),
    _STATS_MATRIX_ROW_LABELS.index("Gap — sampel tercatat"),
    _STATS_MATRIX_ROW_LABELS.index("Gap — sampel hilang"),
    _STATS_MATRIX_ROW_LABELS.index("Gap — hilang (%)"),
    _STATS_MATRIX_ROW_LABELS.index("Gap — jumlah / diharapkan"),
})


def _stats_table_text(value: float | str | None, *, unit: str = "", decimals: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        return value if value else "—"
    fmt = f"{{:.{decimals}f}}"
    text = fmt.format(float(value))
    return f"{text} {unit}".strip() if unit else text


def _configure_stats_matrix_table(table: QTableWidget) -> None:
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["Parameter", "Force", "Roll", "Pitch"])
    table.setRowCount(len(_STATS_MATRIX_ROW_LABELS))
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setStyleSheet(_STATS_TABLE_STYLE)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    for col in (1, 2, 3):
        table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
    for row, label in enumerate(_STATS_MATRIX_ROW_LABELS):
        param_item = QTableWidgetItem(label)
        param_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        param_item.setForeground(QBrush(QColor("#9ca3af")))
        table.setItem(row, 0, param_item)
    channel_colors = ("", _STATS_COL_FORCE, _STATS_COL_ROLL, _STATS_COL_PITCH)
    for col, color in enumerate(channel_colors):
        if col == 0:
            continue
        header_item = table.horizontalHeaderItem(col)
        if header_item is not None:
            header_item.setForeground(QBrush(QColor(color)))


def _set_stats_matrix_cell(
    table: QTableWidget,
    row: int,
    col: int,
    text: str,
    *,
    accent: str | None = None,
) -> None:
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    if accent:
        item.setForeground(QBrush(QColor(accent)))
    table.setItem(row, col, item)


def _set_stats_matrix_merged_row(table: QTableWidget, row: int, text: str) -> None:
    _set_stats_matrix_cell(table, row, 1, text)
    table.setSpan(row, 1, 1, 3)


def _clear_stats_matrix_table(table: QTableWidget) -> None:
    table.clearSpans()
    accents = ("", _STATS_COL_FORCE, _STATS_COL_ROLL, _STATS_COL_PITCH)
    for row in range(len(_STATS_MATRIX_ROW_LABELS)):
        for col in range(1, 4):
            _set_stats_matrix_cell(table, row, col, "—", accent=accents[col])


def _fill_stats_matrix_table(
    table: QTableWidget,
    snap: dict[str, float | str | None],
) -> None:
    table.clearSpans()
    accents = ("", _STATS_COL_FORCE, _STATS_COL_ROLL, _STATS_COL_PITCH)
    t_start = float(snap["timestamp_start_s"])
    t_stop = float(snap["timestamp_stop_s"])
    method = str(snap["spectrum_method"])

    def peak_hz_text(v: float | str | None) -> str:
        if v is None:
            return "—"
        if isinstance(v, str):
            return v
        return f"{float(v):.2f}"

    row_values: list[tuple[str, str, str, str]] = [
        (
            _stats_table_text(t_start),
            _stats_table_text(t_start),
            _stats_table_text(t_start),
        ),
        (
            _stats_table_text(t_stop),
            _stats_table_text(t_stop),
            _stats_table_text(t_stop),
        ),
        (
            _stats_table_text(snap.get("zero_offset_start_s")),
            _stats_table_text(snap.get("zero_offset_start_s")),
            _stats_table_text(snap.get("zero_offset_start_s")),
        ),
        (
            _stats_table_text(snap.get("zero_offset_stop_s")),
            _stats_table_text(snap.get("zero_offset_stop_s")),
            _stats_table_text(snap.get("zero_offset_stop_s")),
        ),
        (
            _stats_table_text(snap.get("offset_mean_force_kg"), unit="Kg"),
            _stats_table_text(snap.get("offset_mean_roll_deg"), unit="°"),
            _stats_table_text(snap.get("offset_mean_pitch_deg"), unit="°"),
        ),
        (
            _stats_table_text(snap["force_max_kg"], unit="Kg"),
            _stats_table_text(snap["roll_max_deg"], unit="°"),
            _stats_table_text(snap["pitch_max_deg"], unit="°"),
        ),
        (
            _stats_table_text(snap["force_max_t_s"]),
            _stats_table_text(snap["roll_max_t_s"]),
            _stats_table_text(snap["pitch_max_t_s"]),
        ),
        (
            "—",
            _stats_table_text(snap["roll_min_deg"], unit="°"),
            _stats_table_text(snap["pitch_min_deg"], unit="°"),
        ),
        (
            "—",
            _stats_table_text(snap["roll_min_t_s"]),
            _stats_table_text(snap["pitch_min_t_s"]),
        ),
        (
            peak_hz_text(snap["dominant_hz_force"]),
            peak_hz_text(snap["dominant_hz_roll"]),
            peak_hz_text(snap["dominant_hz_pitch"]),
        ),
        (method, method, method),
        (str(snap.get("gap_loss_method") or "—"), "—", "—"),
        (
            _stats_table_text(snap.get("gap_dt_nominal_s"), decimals=4)
            + (
                f" ({_stats_table_text(snap.get('gap_fs_hz'), decimals=2)} Hz)"
                if snap.get("gap_fs_hz") is not None
                else ""
            ),
            "—",
            "—",
        ),
        (
            _stats_table_text(snap.get("gap_samples_actual"), decimals=0),
            "—",
            "—",
        ),
        (
            (
                f"{_stats_table_text(snap.get('gap_samples_lost'), decimals=0)}"
                f" ({_stats_table_text(snap.get('gap_loss_pct'), decimals=2)} %)"
                if snap.get("gap_samples_lost") is not None
                and snap.get("gap_loss_pct") is not None
                else "—"
            ),
            "—",
            "—",
        ),
        (
            _stats_table_text(snap.get("gap_loss_pct"), decimals=2) + " %"
            if snap.get("gap_loss_pct") is not None
            else "—",
            "—",
            "—",
        ),
        ("—", "—", "—"),
    ]

    gap_extra = "—"
    if snap.get("gap_count") is not None:
        gap_extra = f"Jumlah gap: {int(snap['gap_count'])}"
    elif snap.get("gap_samples_expected") is not None:
        gap_extra = f"Sampel diharapkan: {int(snap['gap_samples_expected'])}"
    row_values[-1] = (gap_extra, "—", "—")

    for row, (f_val, r_val, p_val) in enumerate(row_values):
        if row in _STATS_MERGED_VALUE_ROWS:
            _set_stats_matrix_merged_row(table, row, f_val)
            continue
        for col, text in enumerate((f_val, r_val, p_val), start=1):
            _set_stats_matrix_cell(table, row, col, text, accent=accents[col])


def _spectrum_peak_frequency_hz(y: list[float], fs_hz: float, *, use_welch: bool) -> float | None:
    if use_welch:
        fq, mag = _spectrum_welch_bins(y, fs_hz)
    else:
        fq, mag = _spectrum_fft_bins(y, fs_hz)
    if fq.size == 0:
        return None
    imax = int(np.argmax(mag))
    return float(fq[imax])


def _configure_plot_widget_for_responsive_layout(
    plot: pg.PlotWidget,
    *,
    min_height: int = 100,
) -> None:
    """Izinkan plot menyusut agar jendela muat di layar 1080p (hindari min-height berlebihan)."""
    plot.setMinimumHeight(min_height)
    plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


_SCROLL_AREA_STYLE = """
QScrollArea { background-color: #1f2937; border: none; }
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
    scroll.viewport().setStyleSheet("background-color: #1f2937;")
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


_ANALYZE_SETTINGS_DIALOG_STYLESHEET = """
QDialog { background-color: #1f2937; }
QDialog QLabel { color: #e5e7eb; }
QDialog QCheckBox { color: #e5e7eb; spacing: 8px; }
QDialog QComboBox {
    background: #374151;
    color: #e5e7eb;
    border: 1px solid #4b5563;
    padding: 6px;
    border-radius: 8px;
}
QDialog QRadioButton { color: #e5e7eb; spacing: 8px; }
"""


class AnalyzeSettingsDialog(QDialog):
    """Jendela terpisah untuk pengaturan analisa (spektrum, segmen, gap CSV)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Analisa Setting")
        self.setModal(False)
        self.setMinimumSize(400, 320)
        self.setStyleSheet(_ANALYZE_SETTINGS_DIALOG_STYLESHEET)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)
        self._content_layout = outer

    def set_content(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)


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
        self._raw_ts: list[float] | None = None
        self._raw_f: list[float] | None = None
        self._raw_r: list[float] | None = None
        self._raw_p: list[float] | None = None
        self._log_sync_meta: LogSyncMeta | None = None
        self._fs_hz: float = 1.0
        self._offset_region_force: pg.LinearRegionItem | None = None
        self._offset_region_roll: pg.LinearRegionItem | None = None
        self._offset_region_pitch: pg.LinearRegionItem | None = None
        self._segment_region_force: pg.LinearRegionItem | None = None
        self._segment_region_roll: pg.LinearRegionItem | None = None
        self._segment_region_pitch: pg.LinearRegionItem | None = None
        self._offset_syncing = False
        self._segment_syncing = False
        self._offset_applied = False
        self._offset_stale = False
        self._offset_applied_bounds: tuple[float, float] | None = None
        self._offset_mean_f = 0.0
        self._offset_mean_r = 0.0
        self._offset_mean_p = 0.0

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

        plot_header = QWidget(time_column)
        plot_header.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        plot_header_layout = QVBoxLayout(plot_header)
        plot_header_layout.setContentsMargins(0, 0, 0, 2)
        plot_header_layout.setSpacing(4)

        meta_row1 = QHBoxLayout()
        meta_row1.setSpacing(16)
        meta_row1.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.load_csv_btn = QPushButton("Load CSV…", self)
        self.load_csv_btn.setStyleSheet(_ANALYZE_TRANSPORT_BUTTON_STYLE)
        self.load_csv_btn.clicked.connect(self.load_csv)
        meta_row1.addWidget(self.load_csv_btn, 0)

        self._swimmer_meta_label, swimmer_meta_block = _analyze_meta_block("Perenang", self)
        meta_row1.addWidget(swimmer_meta_block, 0)

        self._stroke_meta_label, stroke_meta_block = _analyze_meta_block("Gaya", self)
        meta_row1.addWidget(stroke_meta_block, 0)

        self._file_meta_label, file_meta_block = _analyze_meta_block(
            "File", self, monospace=True
        )
        meta_row1.addWidget(file_meta_block, 0)
        meta_row1.addStretch(1)

        plot_header_layout.addLayout(meta_row1)
        time_layout.addWidget(plot_header, 0)

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
        self.video_panel.load_video_requested.connect(self.load_video)

        video_scroll = wrap_in_scroll_area(self.video_panel, self)
        video_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        settings_group = QWidget(self)
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

        self._zero_offset_checkbox = QCheckBox("Zero Offset", self)
        self._zero_offset_checkbox.setStyleSheet("color: #e5e7eb; font-size: 10pt;")
        self._zero_offset_checkbox.setToolTip(
            "Tampilkan region offset (hijau) di awal plot dan region data uji setelah "
            f"jeda {_ZERO_OFFSET_TEST_GAP_S:.0f} s. Gunakan tombol Zero Offset untuk "
            "mengurangi rata-rata region offset dari seluruh data."
        )
        self._zero_offset_checkbox.toggled.connect(self._on_zero_offset_checkbox_changed)
        settings_inner.addWidget(self._zero_offset_checkbox)

        self._offset_info_label = QLabel("Region offset: —", self)
        self._offset_info_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        self._offset_info_label.setWordWrap(True)
        settings_inner.addWidget(self._offset_info_label)

        segment_caption = QLabel("Region data uji (geser pada plot Force):", self)
        segment_caption.setStyleSheet("color: #e5e7eb; font-size: 10pt;")
        settings_inner.addWidget(segment_caption)
        self.segment_info_label = QLabel("Region data uji: —", self)
        self.segment_info_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        self.segment_info_label.setWordWrap(True)
        self.segment_info_label.setToolTip(
            "Geser tepi area berwarna pada plot Force untuk membatasi region data uji. "
            "Roll dan Pitch menampilkan area yang sama; statistik "
            "dihitung hanya pada sampel di dalam region."
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

        self.stats_group = QGroupBox("", self)
        stats_inner = QVBoxLayout(self.stats_group)
        stats_inner.setContentsMargins(10, 10, 10, 10)
        stats_inner.setSpacing(6)

        stats_actions = QHBoxLayout()
        stats_actions.setSpacing(8)
        self.settings_btn = QPushButton("Setting…", self)
        self.settings_btn.setStyleSheet(_ANALYZE_TRANSPORT_BUTTON_STYLE)
        self.settings_btn.setToolTip(
            "Buka pengaturan analisa: metode spektrum, segmen waktu, metode gap CSV."
        )
        self.settings_btn.clicked.connect(self._show_analyze_settings)
        stats_actions.addWidget(self.settings_btn, 0)

        self.zero_offset_btn = QPushButton("Zero Offset", self)
        self.zero_offset_btn.setStyleSheet(_ANALYZE_TRANSPORT_BUTTON_STYLE)
        self.zero_offset_btn.setEnabled(False)
        self.zero_offset_btn.setToolTip(
            "Kurangi rata-rata tiap saluran pada region offset hijau dari seluruh data, "
            "lalu hitung ulang statistik pada region data uji."
        )
        self.zero_offset_btn.clicked.connect(self._on_zero_offset_button_clicked)
        stats_actions.addWidget(self.zero_offset_btn, 0)
        stats_actions.addStretch(1)

        self.save_stats_btn = QPushButton("Simpan statistik…", self)
        self.save_stats_btn.setStyleSheet(_ANALYZE_TRANSPORT_BUTTON_STYLE)
        self.save_stats_btn.setToolTip(
            "Simpan langsung ke folder DataStatistik/ di samping DataLog: "
            "<nama_file_log>_DataStaistik.csv (UTF-8), tanpa dialog Save As."
        )
        self.save_stats_btn.setEnabled(False)
        self.save_stats_btn.clicked.connect(self.save_statistics_csv)
        stats_actions.addWidget(self.save_stats_btn, 0)
        stats_inner.addLayout(stats_actions)

        self._offset_stale_label = QLabel("", self)
        self._offset_stale_label.setStyleSheet("color: #fbbf24; font-size: 9pt;")
        self._offset_stale_label.setWordWrap(True)
        self._offset_stale_label.setVisible(False)
        stats_inner.addWidget(self._offset_stale_label)

        self.stats_table = QTableWidget(self.stats_group)
        _configure_stats_matrix_table(self.stats_table)
        _clear_stats_matrix_table(self.stats_table)
        self.stats_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        stats_inner.addWidget(self.stats_table, 1)

        self._settings_dialog = AnalyzeSettingsDialog(self)
        self._settings_dialog.set_content(settings_group)

        self._scatter_force: pg.ScatterPlotItem | None = None
        self._scatter_roll: pg.ScatterPlotItem | None = None
        self._scatter_pitch: pg.ScatterPlotItem | None = None
        self._stat_texts: list[tuple[pg.PlotWidget, pg.TextItem]] = []
        self._export_ctx: dict[str, str] | None = None
        self._stats_snapshot: dict[str, float | str | None] | None = None
        self._loaded_csv_path: Path | None = None

        self.stats_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # Kanan: atas (video) + bawah (statistik)
        right_top = QWidget(self)
        right_top.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        right_top_layout = QHBoxLayout(right_top)
        right_top_layout.setContentsMargins(0, 0, 0, 0)
        right_top_layout.setSpacing(6)
        right_top_layout.addWidget(video_scroll, 1)

        right_bottom = QWidget(self)
        right_bottom.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        right_bottom_layout = QHBoxLayout(right_bottom)
        right_bottom_layout.setContentsMargins(0, 0, 0, 0)
        right_bottom_layout.setSpacing(6)
        right_bottom_layout.addWidget(self.stats_group, 1)

        right_side = QWidget(self)
        right_side.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        right_side_layout = QVBoxLayout(right_side)
        right_side_layout.setContentsMargins(0, 0, 0, 0)
        right_side_layout.setSpacing(6)
        right_side_layout.addWidget(right_top, 1)
        right_side_layout.addWidget(right_bottom, 1)

        root.addWidget(time_column, 1)
        root.addWidget(right_side, 1)

    def _refresh_stats_table(self) -> None:
        if self._stats_snapshot is None:
            _clear_stats_matrix_table(self.stats_table)
            return
        _fill_stats_matrix_table(self.stats_table, self._stats_snapshot)

    def _show_analyze_settings(self) -> None:
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

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

    @staticmethod
    def _bounds_equal(
        a: tuple[float, float] | None, b: tuple[float, float] | None, *, eps: float = _BOUNDS_EPS_S
    ) -> bool:
        if a is None or b is None:
            return False
        return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps

    def _store_raw_copy(self) -> None:
        if self._loaded_ts is None:
            self._raw_ts = None
            self._raw_f = None
            self._raw_r = None
            self._raw_p = None
            return
        self._raw_ts = list(self._loaded_ts)
        self._raw_f = list(self._loaded_f)  # type: ignore[arg-type]
        self._raw_r = list(self._loaded_r)  # type: ignore[arg-type]
        self._raw_p = list(self._loaded_p)  # type: ignore[arg-type]

    def _restore_raw_to_loaded(self) -> None:
        if self._raw_ts is None:
            return
        self._loaded_ts = list(self._raw_ts)
        self._loaded_f = list(self._raw_f)  # type: ignore[arg-type]
        self._loaded_r = list(self._raw_r)  # type: ignore[arg-type]
        self._loaded_p = list(self._raw_p)  # type: ignore[arg-type]

    def _replot_loaded_curves(self) -> None:
        if self._loaded_ts is None:
            return
        self.force_curve.setData(self._loaded_ts, self._loaded_f)
        self.roll_curve.setData(self._loaded_ts, self._loaded_r)
        self.pitch_curve.setData(self._loaded_ts, self._loaded_p)

    def _zero_offset_mode(self) -> bool:
        return self._zero_offset_checkbox.isChecked()

    def _offset_time_bounds(self) -> tuple[float, float] | None:
        if self._offset_region_force is None or not self._zero_offset_mode():
            return None
        a, b = self._offset_region_force.getRegion()
        return min(a, b), max(a, b)

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

    @staticmethod
    def _means_in_bounds(
        ts_list: list[float],
        f_list: list[float],
        r_list: list[float],
        p_list: list[float],
        t_lo: float,
        t_hi: float,
    ) -> tuple[float, float, float] | None:
        lo, hi = min(t_lo, t_hi), max(t_lo, t_hi)
        f_vals: list[float] = []
        r_vals: list[float] = []
        p_vals: list[float] = []
        for t, fv, rv, pv in zip(ts_list, f_list, r_list, p_list):
            if lo <= t <= hi:
                f_vals.append(fv)
                r_vals.append(rv)
                p_vals.append(pv)
        if not f_vals:
            return None
        return (
            float(statistics.mean(f_vals)),
            float(statistics.mean(r_vals)),
            float(statistics.mean(p_vals)),
        )

    def _offset_means_for_snapshot(self) -> tuple[float | None, float | None, float | None]:
        if not self._zero_offset_mode():
            return None, None, None
        if self._offset_applied:
            return self._offset_mean_f, self._offset_mean_r, self._offset_mean_p
        if (
            self._raw_ts is None
            or self._raw_f is None
            or self._raw_r is None
            or self._raw_p is None
        ):
            return None, None, None
        bounds = self._offset_time_bounds()
        if bounds is None:
            return None, None, None
        means = self._means_in_bounds(
            self._raw_ts,
            self._raw_f,
            self._raw_r,
            self._raw_p,
            bounds[0],
            bounds[1],
        )
        if means is None:
            return None, None, None
        return means

    def _ensure_plot_regions(self) -> None:
        if self._segment_region_force is None:
            self._offset_region_force = pg.LinearRegionItem(
                values=[0.0, 1.0],
                brush=_OFFSET_BRUSH_FORCE,
                movable=True,
                pen=_OFFSET_PEN_FORCE,
            )
            self._offset_region_force.setZValue(6)
            self._offset_region_force.sigRegionChanged.connect(
                self._on_offset_region_changed
            )
            self.force_plot_widget.addItem(self._offset_region_force)

            self._offset_region_roll = pg.LinearRegionItem(
                values=[0.0, 1.0],
                brush=_OFFSET_BRUSH_ROLL,
                movable=False,
                pen=_OFFSET_PEN_ROLL,
            )
            self._offset_region_roll.setZValue(6)
            self.roll_plot_widget.addItem(self._offset_region_roll)

            self._offset_region_pitch = pg.LinearRegionItem(
                values=[0.0, 1.0],
                brush=_OFFSET_BRUSH_PITCH,
                movable=False,
                pen=_OFFSET_PEN_PITCH,
            )
            self._offset_region_pitch.setZValue(6)
            self.pitch_plot_widget.addItem(self._offset_region_pitch)

            self._segment_region_force = pg.LinearRegionItem(
                values=[0.0, 1.0],
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
                values=[0.0, 1.0],
                brush=_SEGMENT_BRUSH_ROLL,
                movable=False,
                pen=_SEGMENT_PEN_ROLL,
            )
            self._segment_region_roll.setZValue(5)
            self.roll_plot_widget.addItem(self._segment_region_roll)

            self._segment_region_pitch = pg.LinearRegionItem(
                values=[0.0, 1.0],
                brush=_SEGMENT_BRUSH_PITCH,
                movable=False,
                pen=_SEGMENT_PEN_PITCH,
            )
            self._segment_region_pitch.setZValue(5)
            self.pitch_plot_widget.addItem(self._segment_region_pitch)

        self._set_offset_regions_visible(self._zero_offset_mode())

    def _set_offset_regions_visible(self, visible: bool) -> None:
        for region in (
            self._offset_region_force,
            self._offset_region_roll,
            self._offset_region_pitch,
        ):
            if region is not None:
                region.setVisible(visible)

    def _default_offset_bounds(self, t_min: float, t_max: float) -> tuple[float, float]:
        span = max(t_max - t_min, 1e-9)
        dur = min(_ZERO_OFFSET_DEFAULT_DURATION_S, span)
        off_lo = t_min
        off_hi = min(t_max, t_min + dur)
        if off_hi - off_lo < _BOUNDS_EPS_S:
            off_hi = min(t_max, off_lo + max(span * 0.05, _BOUNDS_EPS_S))
        return off_lo, off_hi

    def _default_test_bounds(
        self, t_min: float, t_max: float, offset_hi: float
    ) -> tuple[float, float]:
        span = max(t_max - t_min, 1e-9)
        eps = max(span * 1e-9, _BOUNDS_EPS_S)
        test_lo = min(t_max, offset_hi + _ZERO_OFFSET_TEST_GAP_S)
        if test_lo >= t_max - eps:
            test_lo = max(t_min, t_max - max(span * 0.1, eps))
        test_hi = t_max
        if test_hi - test_lo < eps:
            test_lo = max(t_min, test_hi - eps)
        return test_lo, test_hi

    def _layout_regions_full_recording(self, t_min: float, t_max: float) -> None:
        self._segment_syncing = True
        if self._segment_region_force is not None:
            self._segment_region_force.blockSignals(True)
            self._segment_region_force.setRegion([t_min, t_max])
            self._segment_region_force.blockSignals(False)
        self._segment_syncing = False
        self._sync_mirror_segment_regions(t_min, t_max)
        self._update_segment_info_label(t_min, t_max)
        self._update_offset_info_label(None, None)

    def _layout_regions_zero_offset_mode(self, t_min: float, t_max: float) -> None:
        off_lo, off_hi = self._default_offset_bounds(t_min, t_max)
        test_lo, test_hi = self._default_test_bounds(t_min, t_max, off_hi)
        self._offset_syncing = True
        if self._offset_region_force is not None:
            self._offset_region_force.blockSignals(True)
            self._offset_region_force.setRegion([off_lo, off_hi])
            self._offset_region_force.blockSignals(False)
        self._offset_syncing = False
        self._sync_mirror_offset_regions(off_lo, off_hi)
        self._update_offset_info_label(off_lo, off_hi)

        self._segment_syncing = True
        if self._segment_region_force is not None:
            self._segment_region_force.blockSignals(True)
            self._segment_region_force.setRegion([test_lo, test_hi])
            self._segment_region_force.blockSignals(False)
        self._segment_syncing = False
        self._sync_mirror_segment_regions(test_lo, test_hi)
        self._update_segment_info_label(test_lo, test_hi)

    def _setup_segment_regions(self, ts_list: list[float]) -> None:
        if not ts_list:
            return
        t_min = min(ts_list)
        t_max = max(ts_list)
        self._ensure_plot_regions()
        if self._zero_offset_mode():
            self._layout_regions_zero_offset_mode(t_min, t_max)
        else:
            self._layout_regions_full_recording(t_min, t_max)

    def _sync_mirror_offset_regions(self, t_lo: float, t_hi: float) -> None:
        lo, hi = min(t_lo, t_hi), max(t_lo, t_hi)
        for region in (self._offset_region_roll, self._offset_region_pitch):
            if region is not None:
                region.blockSignals(True)
                region.setRegion([lo, hi])
                region.blockSignals(False)

    def _sync_mirror_segment_regions(self, t_lo: float, t_hi: float) -> None:
        lo, hi = min(t_lo, t_hi), max(t_lo, t_hi)
        for region in (self._segment_region_roll, self._segment_region_pitch):
            if region is not None:
                region.blockSignals(True)
                region.setRegion([lo, hi])
                region.blockSignals(False)

    def _update_segment_info_label(self, t_lo: float, t_hi: float) -> None:
        lo, hi = min(t_lo, t_hi), max(t_lo, t_hi)
        if self._loaded_ts and not self._zero_offset_mode():
            full_lo, full_hi = min(self._loaded_ts), max(self._loaded_ts)
            if abs(lo - full_lo) < 1e-6 and abs(hi - full_hi) < 1e-6:
                self.segment_info_label.setText("Region data uji: seluruh rekaman")
                return
        self.segment_info_label.setText(
            f"Region data uji: {lo:.2f} s — {hi:.2f} s (durasi {hi - lo:.2f} s)"
        )

    def _update_offset_info_label(
        self, t_lo: float | None, t_hi: float | None
    ) -> None:
        if t_lo is None or t_hi is None or not self._zero_offset_mode():
            self._offset_info_label.setText("Region offset: —")
            return
        lo, hi = min(t_lo, t_hi), max(t_lo, t_hi)
        self._offset_info_label.setText(
            f"Region offset: {lo:.2f} s — {hi:.2f} s (durasi {hi - lo:.2f} s)"
        )

    def _clamp_region_to_recording(
        self, t_lo: float, t_hi: float
    ) -> tuple[float, float]:
        if not self._loaded_ts:
            return min(t_lo, t_hi), max(t_lo, t_hi)
        full_lo, full_hi = min(self._loaded_ts), max(self._loaded_ts)
        span = full_hi - full_lo
        eps = max(span * 1e-9, _BOUNDS_EPS_S)
        clamped_lo = max(full_lo, min(t_lo, full_hi))
        clamped_hi = max(full_lo, min(t_hi, full_hi))
        if clamped_hi - clamped_lo < eps:
            mid = (clamped_lo + clamped_hi) * 0.5
            clamped_lo = max(full_lo, mid - eps)
            clamped_hi = min(full_hi, mid + eps)
        return clamped_lo, clamped_hi

    def _min_test_start(self) -> float | None:
        if not self._zero_offset_mode():
            return None
        off = self._offset_time_bounds()
        if off is None or not self._loaded_ts:
            return None
        return min(max(self._loaded_ts), off[1] + _ZERO_OFFSET_TEST_GAP_S)

    def _apply_test_region_clamp(self, t_lo: float, t_hi: float) -> tuple[float, float]:
        t_lo, t_hi = self._clamp_region_to_recording(t_lo, t_hi)
        min_start = self._min_test_start()
        if min_start is not None and t_lo < min_start - _BOUNDS_EPS_S:
            span = t_hi - t_lo
            t_lo = min_start
            if self._loaded_ts:
                t_hi = max(t_lo + _BOUNDS_EPS_S, min(t_hi, max(self._loaded_ts)))
                if t_hi - t_lo < _BOUNDS_EPS_S:
                    t_hi = min(max(self._loaded_ts), t_lo + _BOUNDS_EPS_S)
        return t_lo, t_hi

    def _push_test_region_after_offset(self) -> None:
        if not self._zero_offset_mode() or self._segment_region_force is None:
            return
        off = self._offset_time_bounds()
        if off is None:
            return
        t_lo, t_hi = self._segment_region_force.getRegion()
        if self._loaded_ts is None:
            return
        full_hi = max(self._loaded_ts)
        new_lo = min(full_hi, off[1] + _ZERO_OFFSET_TEST_GAP_S)
        if new_lo > t_lo + _BOUNDS_EPS_S:
            t_lo = new_lo
            t_lo, t_hi = self._apply_test_region_clamp(t_lo, t_hi)
            self._segment_syncing = True
            self._segment_region_force.blockSignals(True)
            self._segment_region_force.setRegion([t_lo, t_hi])
            self._segment_region_force.blockSignals(False)
            self._segment_syncing = False
            self._sync_mirror_segment_regions(t_lo, t_hi)
            self._update_segment_info_label(t_lo, t_hi)

    def _update_zero_offset_ui(self) -> None:
        has_data = self._raw_ts is not None
        mode = self._zero_offset_mode()
        self.zero_offset_btn.setEnabled(has_data and mode)
        if not has_data or not mode:
            self.zero_offset_btn.setText("Zero Offset")
            self._offset_stale_label.setVisible(False)
            return
        if self._offset_applied and not self._offset_stale:
            self.zero_offset_btn.setText("Reset Offset")
        else:
            self.zero_offset_btn.setText("Zero Offset")
        stale_visible = self._offset_applied and self._offset_stale
        self._offset_stale_label.setVisible(stale_visible)
        if stale_visible:
            self._offset_stale_label.setText(
                "Region offset berubah — terapkan ulang Zero Offset."
            )

    def _mark_offset_stale_if_needed(self) -> None:
        if not self._offset_applied:
            return
        current = self._offset_time_bounds()
        if not self._bounds_equal(current, self._offset_applied_bounds):
            self._offset_stale = True
        self._update_zero_offset_ui()

    def _patch_snapshot_offset_bounds(self) -> None:
        if self._stats_snapshot is None:
            return
        if self._zero_offset_mode():
            bounds = self._offset_time_bounds()
            if bounds is not None:
                self._stats_snapshot["zero_offset_start_s"] = float(bounds[0])
                self._stats_snapshot["zero_offset_stop_s"] = float(bounds[1])
            else:
                self._stats_snapshot["zero_offset_start_s"] = None
                self._stats_snapshot["zero_offset_stop_s"] = None
        else:
            self._stats_snapshot["zero_offset_start_s"] = None
            self._stats_snapshot["zero_offset_stop_s"] = None
        self._stats_snapshot["zero_offset_applied"] = (
            self._offset_applied and not self._offset_stale
        )
        self._refresh_stats_table()

    def _on_offset_region_changed(self) -> None:
        if self._offset_syncing or self._offset_region_force is None:
            return
        t_lo, t_hi = self._offset_region_force.getRegion()
        t_lo, t_hi = self._clamp_region_to_recording(t_lo, t_hi)
        if self._offset_region_force is not None:
            cur_lo, cur_hi = self._offset_region_force.getRegion()
            if abs(cur_lo - t_lo) > 1e-9 or abs(cur_hi - t_hi) > 1e-9:
                self._offset_syncing = True
                self._offset_region_force.blockSignals(True)
                self._offset_region_force.setRegion([t_lo, t_hi])
                self._offset_region_force.blockSignals(False)
                self._offset_syncing = False
        self._sync_mirror_offset_regions(t_lo, t_hi)
        self._update_offset_info_label(t_lo, t_hi)
        self._push_test_region_after_offset()
        was_stale = self._offset_stale
        self._mark_offset_stale_if_needed()
        if self._offset_applied and (self._offset_stale or was_stale):
            self._patch_snapshot_offset_bounds()
            return
        self._reanalyze_current_segment()

    def _on_segment_region_changed(self) -> None:
        if self._segment_syncing or self._segment_region_force is None:
            return
        t_lo, t_hi = self._segment_region_force.getRegion()
        t_lo, t_hi = self._apply_test_region_clamp(t_lo, t_hi)
        cur_lo, cur_hi = self._segment_region_force.getRegion()
        if abs(cur_lo - t_lo) > 1e-9 or abs(cur_hi - t_hi) > 1e-9:
            self._segment_syncing = True
            self._segment_region_force.blockSignals(True)
            self._segment_region_force.setRegion([t_lo, t_hi])
            self._segment_region_force.blockSignals(False)
            self._segment_syncing = False
        self._sync_mirror_segment_regions(t_lo, t_hi)
        self._update_segment_info_label(t_lo, t_hi)
        self._reanalyze_current_segment()

    def _reset_zero_offset_state(self, *, replot: bool = True) -> None:
        self._offset_applied = False
        self._offset_stale = False
        self._offset_applied_bounds = None
        self._offset_mean_f = 0.0
        self._offset_mean_r = 0.0
        self._offset_mean_p = 0.0
        self._restore_raw_to_loaded()
        if replot:
            self._replot_loaded_curves()
        self._update_zero_offset_ui()

    def _apply_zero_offset(self) -> bool:
        if (
            self._raw_ts is None
            or self._raw_f is None
            or self._raw_r is None
            or self._raw_p is None
        ):
            return False
        bounds = self._offset_time_bounds()
        if bounds is None:
            return False
        means = self._means_in_bounds(
            self._raw_ts, self._raw_f, self._raw_r, self._raw_p, bounds[0], bounds[1]
        )
        if means is None:
            QMessageBox.warning(
                self,
                "Zero Offset",
                "Tidak ada sampel pada region offset untuk menghitung rata-rata.",
            )
            return False
        self._offset_mean_f, self._offset_mean_r, self._offset_mean_p = means
        self._loaded_f = [v - self._offset_mean_f for v in self._raw_f]
        self._loaded_r = [v - self._offset_mean_r for v in self._raw_r]
        self._loaded_p = [v - self._offset_mean_p for v in self._raw_p]
        self._loaded_ts = list(self._raw_ts)
        self._offset_applied = True
        self._offset_stale = False
        self._offset_applied_bounds = bounds
        self._replot_loaded_curves()
        self._update_zero_offset_ui()
        self._reanalyze_current_segment()
        return True

    def _on_zero_offset_button_clicked(self) -> None:
        if self._offset_applied and not self._offset_stale:
            self._reset_zero_offset_state()
            self._reanalyze_current_segment()
            return
        self._apply_zero_offset()

    def _on_zero_offset_checkbox_changed(self, checked: bool) -> None:
        self._set_offset_regions_visible(checked)
        if not checked:
            self._reset_zero_offset_state(replot=True)
            if self._loaded_ts:
                t_min, t_max = min(self._loaded_ts), max(self._loaded_ts)
                self._layout_regions_full_recording(t_min, t_max)
            self._reanalyze_current_segment()
            return
        if self._loaded_ts:
            t_min, t_max = min(self._loaded_ts), max(self._loaded_ts)
            self._layout_regions_zero_offset_mode(t_min, t_max)
        self._update_zero_offset_ui()
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
            self._refresh_stats_table()
            return
        self._apply_statistics(ts_list, f_list, r_list, p_list)
        bounds = self._segment_time_bounds()
        if bounds is not None and self._stats_snapshot is not None:
            self._stats_snapshot["segment_start_s"] = float(bounds[0])
            self._stats_snapshot["segment_end_s"] = float(bounds[1])
            if self._zero_offset_mode():
                off = self._offset_time_bounds()
                if off is not None:
                    self._stats_snapshot["zero_offset_start_s"] = float(off[0])
                    self._stats_snapshot["zero_offset_stop_s"] = float(off[1])
                else:
                    self._stats_snapshot["zero_offset_start_s"] = None
                    self._stats_snapshot["zero_offset_stop_s"] = None
            else:
                self._stats_snapshot["zero_offset_start_s"] = None
                self._stats_snapshot["zero_offset_stop_s"] = None
            self._stats_snapshot["zero_offset_applied"] = (
                self._offset_applied and not self._offset_stale
            )
            mean_f, mean_r, mean_p = self._offset_means_for_snapshot()
            self._stats_snapshot["offset_mean_force_kg"] = mean_f
            self._stats_snapshot["offset_mean_roll_deg"] = mean_r
            self._stats_snapshot["offset_mean_pitch_deg"] = mean_p
        if ts_list:
            self._fs_hz = _estimate_sample_rate_hz(ts_list)
        self._update_zero_offset_ui()
        self._refresh_stats_table()

    def _gap_loss_method_key(self) -> str:
        """``A`` = per gap; ``B`` = global."""
        return "A" if self._gap_method_a_radio.isChecked() else "B"

    def _on_gap_loss_method_changed(self, _button_id: int) -> None:
        if self._loaded_ts is not None:
            self._reanalyze_current_segment()

    def _on_spectrum_method_changed(self, _index: int) -> None:
        self._reanalyze_current_segment()

    def _try_load_paired_video(self, csv_path: Path) -> None:
        video_path = csv_path.with_suffix(".mp4")
        if video_path.is_file() and self.video_panel.load_video(video_path):
            return
        self.video_panel.clear()

    def _update_meta_labels(self) -> None:
        if self._export_ctx is None:
            self._swimmer_meta_label.setText("—")
            self._stroke_meta_label.setText("—")
            self._file_meta_label.setText("—")
            return
        self._swimmer_meta_label.setText(self._export_ctx["swimmer"])
        self._stroke_meta_label.setText(self._export_ctx["stroke"])
        self._file_meta_label.setText(self._export_ctx["source_file"])

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
        self._store_raw_copy()
        self._reset_zero_offset_state(replot=False)
        self._zero_offset_checkbox.blockSignals(True)
        self._zero_offset_checkbox.setChecked(False)
        self._zero_offset_checkbox.blockSignals(False)
        self._set_offset_regions_visible(False)
        self._log_sync_meta = sync_meta
        self._loaded_csv_path = path

        self._try_load_paired_video(path)

        self._export_ctx = {
            "swimmer": swimmer,
            "stroke": stroke,
            "source_file": path.name,
        }
        self._update_meta_labels()

        self._setup_segment_regions(ts_list)
        self._update_zero_offset_ui()
        self._reanalyze_current_segment()
        if self.video_panel.video_path() is None:
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
            self._refresh_stats_table()
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
            z_lo = snap.get("zero_offset_start_s")
            z_hi = snap.get("zero_offset_stop_s")
            if z_lo is not None and z_hi is not None:
                w.writerow(
                    [
                        "Zero_offset_start (s)",
                        f"{float(z_lo):.6g}",
                    ]
                )
                w.writerow(
                    [
                        "Zero_offset_stop (s)",
                        f"{float(z_hi):.6g}",
                    ]
                )
            if snap.get("zero_offset_applied"):
                w.writerow(["Zero_offset_diterapkan", "Ya"])
            if snap.get("offset_mean_force_kg") is not None:
                w.writerow(
                    [
                        "Rata_rata_offset_Force",
                        f"{float(snap['offset_mean_force_kg']):.6g}",
                        "Kg",
                    ]
                )
            if snap.get("offset_mean_roll_deg") is not None:
                w.writerow(
                    [
                        "Rata_rata_offset_Roll",
                        f"{float(snap['offset_mean_roll_deg']):.6g}",
                        "deg",
                    ]
                )
            if snap.get("offset_mean_pitch_deg") is not None:
                w.writerow(
                    [
                        "Rata_rata_offset_Pitch",
                        f"{float(snap['offset_mean_pitch_deg']):.6g}",
                        "deg",
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

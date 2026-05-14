"""
Tab **Analisa (satu berkas)** — muat satu CSV rekaman Live, plot waktu + spektrum frekuensi,
ekstremum, ekspor statistik.

Spektrum: **FFT** (NumPy) atau **Welch PSD** (SciPy). Dependensi tambahan: ``numpy``, ``scipy``.

Nanti analisis banyak berkas dapat ditambahkan sebagai tab terpisah tanpa mempengaruhi kelas ini.
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
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
from scipy import signal

from live_csv_io import parse_logged_csv


# Marker ekstremum: semua min hijau, semua max merah
MARKER_MIN_COLOR = "#22c55e"
MARKER_MAX_COLOR = "#ef4444"


def _path_text_for_dialog(path: Path | str) -> str:
    s = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    if len(s) >= 3 and s[0].isalpha() and s[1] == ":" and s[2] == "/":
        s = s[:2] + "\u2060" + s[2:]
    return s


def _he(s: str) -> str:
    return escape(s, quote=False)


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


def _html_load_block(swimmer: str, stroke: str, filename: str) -> str:
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:12px 14px;">'
        f"{_html_load_field('Nama perenang', swimmer, margin_top=0)}"
        f"{_html_load_field('Gaya renang', stroke)}"
        f"{_html_load_field('Nama file', filename, monospace=True)}"
        "</div>"
    )


def _html_load_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:14px 16px;">'
        '<p style="margin:0;color:#cbd5e1;font-size:11px;line-height:1.55;">'
        'Belum ada rekaman dimuat.<br/>'
        'Tekan <b style="color:#f1f5f9;">Load CSV…</b> untuk memilih file hasil tab Live.'
        "</p></div>"
    )


def _html_stat_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:12px 14px;">'
        '<p style="margin:0;color:#94a3b8;font-size:10px;line-height:1.55;">'
        "Muat CSV dari tab Live untuk menampilkan ringkasan ekstremum (force, roll, pitch)."
        "</p></div>"
    )


def _html_tstart_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:12px 14px;">'
        '<p style="margin:0;color:#94a3b8;font-size:10px;line-height:1.55;">'
        "TimeStamp Start pada — s"
        "</p></div>"
    )


def _html_stat_tstart(t_start_s: float) -> str:
    """Waktu paling awal di kolom TimeStamp CSV (min), satu baris dalam kartu strip."""
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:10px 12px 12px 12px;">'
        '<div style="border-left:3px solid #64748b;padding-left:10px;">'
        '<div style="color:#f8fafc;font-size:13px;font-weight:600;line-height:1.5;">'
        f"TimeStamp Start pada {_he(f'{t_start_s:.2f}')} s"
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
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:10px 12px 12px 12px;">'
        '<div style="border-left:3px solid #38bdf8;padding-left:10px;">'
        '<div style="color:#38bdf8;font-weight:700;font-size:10px;letter-spacing:0.12em;">FORCE</div>'
        '<table style="margin-top:8px;font-size:12px;color:#cbd5e1;width:100%;">'
        f'<tr><td colspan="2" style="color:#ffffff;padding:4px 0;line-height:1.5;font-weight:600;">{line1}</td></tr>'
        f'<tr><td colspan="2" style="color:#94a3b8;padding:8px 0 0 0;font-size:11px;line-height:1.45;">{line2}</td></tr>'
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
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:10px 12px 12px 12px;">'
        '<div style="border-left:3px solid #f59e0b;padding-left:10px;">'
        '<div style="color:#fbbf24;font-weight:700;font-size:10px;letter-spacing:0.12em;">ROLL</div>'
        '<table style="margin-top:8px;font-size:12px;color:#cbd5e1;width:100%;">'
        f'<tr><td colspan="2" style="color:#ffffff;padding:4px 0;line-height:1.5;font-weight:600;">{line1}</td></tr>'
        f'<tr><td colspan="2" style="color:#ffffff;padding:4px 0 0 0;line-height:1.5;font-weight:600;">{line2}</td></tr>'
        f'<tr><td colspan="2" style="color:#94a3b8;padding:8px 0 0 0;font-size:11px;line-height:1.45;">{line3}</td></tr>'
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
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:10px 12px 12px 12px;">'
        '<div style="border-left:3px solid #a78bfa;padding-left:10px;">'
        '<div style="color:#c4b5fd;font-weight:700;font-size:10px;letter-spacing:0.12em;">PITCH</div>'
        '<table style="margin-top:8px;font-size:12px;color:#cbd5e1;width:100%;">'
        f'<tr><td colspan="2" style="color:#ffffff;padding:4px 0;line-height:1.5;font-weight:600;">{line1}</td></tr>'
        f'<tr><td colspan="2" style="color:#ffffff;padding:4px 0 0 0;line-height:1.5;font-weight:600;">{line2}</td></tr>'
        f'<tr><td colspan="2" style="color:#94a3b8;padding:8px 0 0 0;font-size:11px;line-height:1.45;">{line3}</td></tr>'
        "</table></div></div>"
    )


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


def make_analyze_time_spectrum_row(
    *,
    time_title: str,
    time_left: str,
    spectrum_title: str,
    line_pen: str,
    spectrum_pen: str,
) -> tuple[pg.PlotWidget, pg.PlotDataItem, pg.PlotWidget, pg.PlotDataItem]:
    """Satu baris tab Analisa: plot waktu (kiri) + plot spektrum (kanan)."""
    time_w = pg.PlotWidget()
    time_w.setLabel("left", time_left, color="#e5e7eb", **{"font-size": "11pt"})
    time_w.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "11pt"})
    time_w.setTitle(time_title, color="#e5e7eb", size="11pt")
    time_w.setBackground("#1f2937")
    time_w.showGrid(x=False, y=False)
    time_w.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
    time_w.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
    time_w.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
    time_w.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
    time_c = time_w.plot(pen=pg.mkPen(color=line_pen, width=2))

    spec_w = pg.PlotWidget()
    spec_w.setLabel("left", "|FFT|", color="#e5e7eb", **{"font-size": "10pt"})
    spec_w.setLabel("bottom", "Frequency (Hz)", color="#e5e7eb", **{"font-size": "10pt"})
    spec_w.setTitle(spectrum_title, color="#e5e7eb", size="10pt")
    spec_w.setBackground("#1f2937")
    spec_w.showGrid(x=False, y=False)
    spec_w.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
    spec_w.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
    spec_w.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
    spec_w.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
    spec_c = spec_w.plot(pen=pg.mkPen(color=spectrum_pen, width=2))

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
        self._fs_hz: float = 1.0

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        plots_panel = QWidget(self)
        plots_layout = QVBoxLayout(plots_panel)
        plots_layout.setContentsMargins(0, 0, 0, 0)

        self.force_plot_widget, self.force_curve, self.force_spec_plot_widget, self.force_spec_curve = (
            make_analyze_time_spectrum_row(
                time_title="Force (Kg) — rekaman",
                time_left="Force (Kg)",
                spectrum_title="Force — spektrum",
                line_pen="#38bdf8",
                spectrum_pen="#7dd3fc",
            )
        )
        self.roll_plot_widget, self.roll_curve, self.roll_spec_plot_widget, self.roll_spec_curve = (
            make_analyze_time_spectrum_row(
                time_title="Roll (°) — rekaman",
                time_left="Angle (°)",
                spectrum_title="Roll — spektrum",
                line_pen="#f59e0b",
                spectrum_pen="#fcd34d",
            )
        )
        self.pitch_plot_widget, self.pitch_curve, self.pitch_spec_plot_widget, self.pitch_spec_curve = (
            make_analyze_time_spectrum_row(
                time_title="Pitch (°) — rekaman",
                time_left="Angle (°)",
                spectrum_title="Pitch — spektrum",
                line_pen="#a78bfa",
                spectrum_pen="#c4b5fd",
            )
        )

        for tw, sw in (
            (self.force_plot_widget, self.force_spec_plot_widget),
            (self.roll_plot_widget, self.roll_spec_plot_widget),
            (self.pitch_plot_widget, self.pitch_spec_plot_widget),
        ):
            row = QHBoxLayout()
            row.setSpacing(6)
            row.addWidget(tw, 3)
            row.addWidget(sw, 2)
            plots_layout.addLayout(row, 1)

        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        load_group = QGroupBox("", self)
        load_group.setLayout(QVBoxLayout())
        load_group.layout().setContentsMargins(12, 14, 12, 14)
        load_group.layout().setSpacing(10)

        self.load_csv_btn = QPushButton("Load CSV…", self)
        self.load_csv_btn.clicked.connect(self.load_csv)
        load_group.layout().addWidget(self.load_csv_btn)

        self.meta_label = QLabel(self)
        self.meta_label.setObjectName("AnalyzeRichLabel")
        self.meta_label.setWordWrap(True)
        self.meta_label.setTextFormat(Qt.TextFormat.RichText)
        self.meta_label.setText(_html_load_placeholder())
        load_group.layout().addWidget(self.meta_label)

        settings_group = QGroupBox("", self)
        settings_inner = QVBoxLayout(settings_group)
        settings_inner.setContentsMargins(12, 14, 12, 14)
        settings_inner.setSpacing(8)
        settings_caption = QLabel("Metode spektrum frekuensi:", self)
        settings_caption.setStyleSheet("color: #94a3b8; font-size: 10pt;")
        settings_inner.addWidget(settings_caption)
        self._radio_fft = QRadioButton("FFT", self)
        self._radio_welch = QRadioButton("Welch PSD", self)
        self._radio_fft.setChecked(True)
        self._spectrum_method_group = QButtonGroup(self)
        self._spectrum_method_group.setExclusive(True)
        self._spectrum_method_group.addButton(self._radio_fft, 0)
        self._spectrum_method_group.addButton(self._radio_welch, 1)
        self._spectrum_method_group.idClicked.connect(self._on_spectrum_method_changed)
        radios_row = QHBoxLayout()
        radios_row.setSpacing(16)
        radios_row.addWidget(self._radio_fft)
        radios_row.addWidget(self._radio_welch)
        radios_row.addStretch(1)
        settings_inner.addLayout(radios_row)

        self.stats_group = QGroupBox("", self)
        stats_inner = QVBoxLayout(self.stats_group)
        stats_inner.setContentsMargins(12, 14, 12, 14)
        stats_inner.setSpacing(10)
        self.stat_tstart_label = QLabel(self)
        self.stat_force_label = QLabel(self)
        self.stat_roll_label = QLabel(self)
        self.stat_pitch_label = QLabel(self)
        for lb in (
            self.stat_tstart_label,
            self.stat_force_label,
            self.stat_roll_label,
            self.stat_pitch_label,
        ):
            lb.setObjectName("AnalyzeRichLabel")
            lb.setWordWrap(True)
            lb.setTextFormat(Qt.TextFormat.RichText)
        self.stat_tstart_label.setText(_html_tstart_placeholder())
        self.stat_force_label.setText(_html_stat_placeholder())
        self.stat_roll_label.setText(_html_stat_placeholder())
        self.stat_pitch_label.setText(_html_stat_placeholder())

        stats_inner.addWidget(self.stat_tstart_label)
        stats_inner.addWidget(self.stat_force_label)
        stats_inner.addWidget(self.stat_roll_label)
        stats_inner.addWidget(self.stat_pitch_label)

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
        self._spec_peak_artists: list[tuple[pg.PlotWidget, pg.ScatterPlotItem, pg.TextItem]] = []
        self._export_ctx: dict[str, str] | None = None
        self._stats_snapshot: dict[str, float] | None = None

        right_layout.addWidget(load_group, 0)
        right_layout.addWidget(settings_group, 0)
        right_layout.addWidget(self.stats_group, 0)
        right_layout.addStretch(1)

        root.addWidget(plots_panel, 4)
        root.addWidget(right_panel, 1)

        self._clear_spectrum_plots()

    def _clear_spectrum_peak_markers(self) -> None:
        for plot, sc, ti in self._spec_peak_artists:
            plot.removeItem(sc)
            plot.removeItem(ti)
        self._spec_peak_artists.clear()

    def _clear_spectrum_plots(self) -> None:
        self._clear_spectrum_peak_markers()
        self.force_spec_curve.setData([], [])
        self.roll_spec_curve.setData([], [])
        self.pitch_spec_curve.setData([], [])

    def _add_spectrum_peak_marker(
        self,
        plot: pg.PlotWidget,
        fq: np.ndarray,
        mag: np.ndarray,
        *,
        use_welch: bool,
    ) -> None:
        """Marker pada bin magnitudo / PSD maksimum; label f (Hz) dan Y sesuai metode."""
        if fq.size == 0 or mag.size == 0:
            return
        imax = int(np.argmax(mag))
        fx = float(fq[imax])
        my = float(mag[imax])
        f_min = float(fq[0])
        f_max = float(fq[-1])
        y_name = "PSD" if use_welch else "|FFT|"
        text = f"f = {fx:.4f} Hz\n{y_name} = {my:.4g}"

        span = (f_max - f_min) or 1.0
        dx = max(span * 0.028, 1e-6)
        mid = (f_min + f_max) * 0.5
        if fx <= mid:
            lx = fx + dx
            anchor = (0.0, 0.5)
        else:
            lx = fx - dx
            anchor = (1.0, 0.5)

        sc = pg.ScatterPlotItem(
            pos=[(fx, my)],
            size=12,
            symbol="o",
            pen=pg.mkPen("#f8fafc", width=2),
            brush=pg.mkBrush(MARKER_MAX_COLOR),
        )
        sc.setZValue(10)
        plot.addItem(sc)
        ti = pg.TextItem(
            text,
            color="#f8fafc",
            anchor=anchor,
            border=pg.mkPen("#94a3b8", width=1),
            fill=pg.mkBrush(30, 41, 59, 230),
        )
        ti.setFont(QFont("Segoe UI", 9))
        ti.setZValue(11)
        ti.setPos(lx, my)
        plot.addItem(ti)
        self._spec_peak_artists.append((plot, sc, ti))

    def _on_spectrum_method_changed(self, _id: int) -> None:
        self._refresh_spectrum_plots()
        if (
            self._loaded_ts is not None
            and self._loaded_f is not None
            and self._loaded_r is not None
            and self._loaded_p is not None
        ):
            self._clear_stat_markers()
            self._apply_statistics(
                self._loaded_ts, self._loaded_f, self._loaded_r, self._loaded_p
            )

    def _refresh_spectrum_plots(self) -> None:
        self._clear_spectrum_peak_markers()
        if self._loaded_ts is None or self._loaded_f is None:
            self.force_spec_curve.setData([], [])
            self.roll_spec_curve.setData([], [])
            self.pitch_spec_curve.setData([], [])
            return
        ts = self._loaded_ts
        fs = _estimate_sample_rate_hz(ts)
        self._fs_hz = fs
        use_welch = self._radio_welch.isChecked()
        y_left = "PSD (lin.)" if use_welch else "|FFT| (norm.)"
        for sw in (
            self.force_spec_plot_widget,
            self.roll_spec_plot_widget,
            self.pitch_spec_plot_widget,
        ):
            sw.setLabel("left", y_left, color="#e5e7eb", **{"font-size": "10pt"})

        def compute(y: list[float]) -> tuple[np.ndarray, np.ndarray]:
            if use_welch:
                return _spectrum_welch_bins(y, fs)
            return _spectrum_fft_bins(y, fs)

        channels: list[tuple[pg.PlotWidget, pg.PlotDataItem, list[float]]] = [
            (self.force_spec_plot_widget, self.force_spec_curve, self._loaded_f),
            (self.roll_spec_plot_widget, self.roll_spec_curve, self._loaded_r),
            (self.pitch_spec_plot_widget, self.pitch_spec_curve, self._loaded_p),
        ]
        for plot, curve, ydata in channels:
            fq, mag = compute(ydata)
            if fq.size == 0:
                curve.setData([], [])
                continue
            curve.setData(fq, mag)
            self._add_spectrum_peak_marker(plot, fq, mag, use_welch=use_welch)

        for sw in (
            self.force_spec_plot_widget,
            self.roll_spec_plot_widget,
            self.pitch_spec_plot_widget,
        ):
            sw.getViewBox().autoRange()

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
            swimmer, stroke, ts_list, f_list, r_list, p_list = parse_logged_csv(path)
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
        self._refresh_spectrum_plots()

        self.meta_label.setText(_html_load_block(swimmer, stroke, path.name))

        self._export_ctx = {
            "swimmer": swimmer,
            "stroke": stroke,
            "source_file": path.name,
        }

        self._clear_stat_markers()
        self._apply_statistics(ts_list, f_list, r_list, p_list)

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
        fs = _estimate_sample_rate_hz(ts_list)
        use_welch = self._radio_welch.isChecked()
        method_label = "Welch PSD" if use_welch else "FFT"
        peak_f = _spectrum_peak_frequency_hz(f_list, fs, use_welch=use_welch)
        peak_r = _spectrum_peak_frequency_hz(r_list, fs, use_welch=use_welch)
        peak_p = _spectrum_peak_frequency_hz(p_list, fs, use_welch=use_welch)

        self.stat_tstart_label.setText(_html_stat_tstart(t_start))
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
        }
        self.save_stats_btn.setEnabled(self._export_ctx is not None)

    @staticmethod
    def _write_statistik_csv(path: Path, ctx: dict[str, str], snap: dict[str, float]) -> None:
        exported_at = datetime.now().isoformat(timespec="seconds")
        swimmer = ctx["swimmer"]
        stroke = ctx["stroke"]
        source_file = ctx["source_file"]

        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Nama_Perenang", swimmer])
            w.writerow(["Gaya_Renang", stroke])
            w.writerow(["Waktu_Ekspor_Statistik", exported_at])
            w.writerow(["Berkas_Sumber", source_file])
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

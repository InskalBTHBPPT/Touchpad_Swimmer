"""
Swimmer Force Motion Monitoring

Ringkasan:
- Dashboard PySide6 untuk monitoring gaya renang / beban (force) dan gerakan (roll, pitch) real-time.
- Membaca serial CSV UTF-8: 4 kolom per baris (newline-terminated).

Format data serial (ESP32 Generate_TimeSeries_3_Random_data):
1) TimeStamp(s)   — waktu relatif dari firmware (detik)
2) Force (Kg)     — kolom 2 serial (RandomData1)
3) Roll (Deg)     — kolom 3 serial (RandomData2)
4) Pitch (Deg)    — kolom 4 serial (RandomData3)

Catatan:
- Tab Live: tiga plot time-series vertikal (Force, Roll, Pitch masing-masing satu baris).
- Tab Analisa: panel kanan (load + statistik) kartu HTML tanpa judul grup; marker dengan label waktu jelas.
- Plot mempertahankan maksimal 100 titik (~10 detik jika ~10 sampel/detik).
- Rekaman CSV ke folder DataLog/ di samping file ini (tanpa dialog Save As).
"""

from __future__ import annotations

import csv
import io
import re
import sys
from datetime import datetime
from pathlib import Path

from html import escape

import pyqtgraph as pg
import serial
from serial.tools import list_ports
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


SCRIPT_DIR = Path(__file__).resolve().parent
DATALOG_DIR = SCRIPT_DIR / "DataLog"

STROKE_STYLES = [
    "Gaya Bebas",
    "Kupu-kupu",
    "Dada",
    "Punggung",
    "Ganti kategori (medley)",
    "Lainnya",
]

# Header baris data persis seperti ditulis tab Live (toggle_logging)
LIVE_CSV_DATA_HEADER: tuple[str, ...] = (
    "TimeStamp(s)",
    "Force(Kg)",
    "Roll(Deg)",
    "Pitch(Deg)",
)

# Marker ekstremum tab Analisa: semua min hijau, semua max merah
ANALYZE_MARKER_MIN_COLOR = "#22c55e"
ANALYZE_MARKER_MAX_COLOR = "#ef4444"


def _he(s: str) -> str:
    return escape(s, quote=False)


def _html_analyze_load_field(label: str, value: str, *, monospace: bool = False, margin_top: int = 8) -> str:
    """Satu blok meta rekaman (judul kecil + nilai tebal)."""
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


def _html_analyze_load_block(swimmer: str, stroke: str, filename: str) -> str:
    """Satu kartu HTML untuk panel Data rekaman."""
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:12px 14px;">'
        f"{_html_analyze_load_field('Nama perenang', swimmer, margin_top=0)}"
        f"{_html_analyze_load_field('Gaya renang', stroke)}"
        f"{_html_analyze_load_field('Nama file', filename, monospace=True)}"
        "</div>"
    )


def _html_analyze_load_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:14px 16px;">'
        '<p style="margin:0;color:#cbd5e1;font-size:11px;line-height:1.55;">'
        'Belum ada rekaman dimuat.<br/>'
        'Tekan <b style="color:#f1f5f9;">Load CSV…</b> untuk memilih file hasil tab Live.'
        "</p></div>"
    )


def _html_analyze_stat_force(v_max: float, t_max: float) -> str:
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:10px 12px 12px 12px;">'
        '<div style="border-left:3px solid #38bdf8;padding-left:10px;">'
        '<div style="color:#38bdf8;font-weight:700;font-size:10px;letter-spacing:0.12em;">FORCE</div>'
        '<table style="margin-top:8px;font-size:11px;color:#cbd5e1;width:100%;">'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 4px 0;vertical-align:middle;">Maksimum</td>'
        f'<td style="font-weight:700;color:#fca5a5;font-size:13px;">{_he(f"{v_max:.2f} Kg")}</td></tr>'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 0 0;">Waktu saat Force maksimum</td>'
        f'<td style="color:#e2e8f0;">{_he(f"{t_max:.2f} s")}</td></tr>'
        "</table></div></div>"
    )


def _html_analyze_stat_roll(v_min: float, t_min: float, v_max: float, t_max: float) -> str:
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:10px 12px 12px 12px;">'
        '<div style="border-left:3px solid #f59e0b;padding-left:10px;">'
        '<div style="color:#fbbf24;font-weight:700;font-size:10px;letter-spacing:0.12em;">ROLL</div>'
        '<table style="margin-top:8px;font-size:11px;color:#cbd5e1;width:100%;">'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 4px 0;vertical-align:middle;">Minimum</td>'
        f'<td style="font-weight:700;color:#86efac;font-size:13px;">{_he(f"{v_min:.2f}°")}</td></tr>'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 4px 0;">Waktu saat Roll minimum</td>'
        f'<td style="color:#e2e8f0;">{_he(f"{t_min:.2f} s")}</td></tr>'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 4px 0;vertical-align:middle;">Maksimum</td>'
        f'<td style="font-weight:700;color:#fca5a5;font-size:13px;">{_he(f"{v_max:.2f}°")}</td></tr>'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 0 0;">Waktu saat Roll maksimum</td>'
        f'<td style="color:#e2e8f0;">{_he(f"{t_max:.2f} s")}</td></tr>'
        "</table></div></div>"
    )


def _html_analyze_stat_pitch(v_min: float, t_min: float, v_max: float, t_max: float) -> str:
    return (
        '<div style="background:#0c1222;border:1px solid #273449;border-radius:10px;padding:10px 12px 12px 12px;">'
        '<div style="border-left:3px solid #a78bfa;padding-left:10px;">'
        '<div style="color:#c4b5fd;font-weight:700;font-size:10px;letter-spacing:0.12em;">PITCH</div>'
        '<table style="margin-top:8px;font-size:11px;color:#cbd5e1;width:100%;">'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 4px 0;vertical-align:middle;">Minimum</td>'
        f'<td style="font-weight:700;color:#86efac;font-size:13px;">{_he(f"{v_min:.2f}°")}</td></tr>'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 4px 0;">Waktu saat Pitch minimum</td>'
        f'<td style="color:#e2e8f0;">{_he(f"{t_min:.2f} s")}</td></tr>'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 4px 0;vertical-align:middle;">Maksimum</td>'
        f'<td style="font-weight:700;color:#fca5a5;font-size:13px;">{_he(f"{v_max:.2f}°")}</td></tr>'
        f'<tr><td style="color:#94a3b8;padding:4px 10px 0 0;">Waktu saat Pitch minimum maksimum</td>'
        f'<td style="color:#e2e8f0;">{_he(f"{t_max:.2f} s")}</td></tr>'
        "</table></div></div>"
    )


def _html_analyze_stat_placeholder() -> str:
    return (
        '<div style="background:#0c1222;border:1px dashed #334155;border-radius:10px;padding:12px 14px;">'
        '<p style="margin:0;color:#94a3b8;font-size:10px;line-height:1.55;">'
        "Muat CSV dari tab Live untuk menampilkan ringkasan ekstremum (force, roll, pitch)."
        "</p></div>"
    )


def _safe_filename_part(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s or "TanpaNama"


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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Swimmer Force Motion Monitoring")
        self.resize(1100, 720)

        self.ser: serial.Serial | None = None
        self.serial_timer = QTimer(self)
        self.serial_timer.timeout.connect(self.poll_serial)

        self.serial_buffer = b""

        self.log_file_path: Path | None = None
        self.log_file = None
        self.log_buffer: list[str] = []
        self.log_timer = QTimer(self)
        self.log_timer.setInterval(400)
        self.log_timer.timeout.connect(self.flush_log_buffer)
        self._log_header_time_str = ""

        # ~10 detik jendela tampilan pada laju ~10 baris/detik (mis. ESP timerInterval 100 ms)
        self.max_points = 100

        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        live_tab = QWidget(self)
        live_layout = QHBoxLayout(live_tab)
        live_layout.setContentsMargins(8, 8, 8, 8)

        # ---------- Kiri: plots Live ----------
        plots_panel = QWidget(self)
        plots_layout = QVBoxLayout(plots_panel)
        plots_layout.setContentsMargins(0, 0, 0, 0)

        (
            self.force_plot_widget,
            self.roll_plot_widget,
            self.pitch_plot_widget,
            self.force_curve,
            self.roll_curve,
            self.pitch_curve,
        ) = make_three_stack_plots()

        plots_layout.addWidget(self.force_plot_widget, 1)
        plots_layout.addWidget(self.roll_plot_widget, 1)
        plots_layout.addWidget(self.pitch_plot_widget, 1)

        self.force_time_data: list[float] = []
        self.force_data: list[float] = []
        self.roll_time_data: list[float] = []
        self.roll_data: list[float] = []
        self.pitch_time_data: list[float] = []
        self.pitch_data: list[float] = []

        # ---------- Kanan: kontrol ----------
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        controls = QGroupBox("", self)
        controls.setLayout(QVBoxLayout())
        controls.layout().setContentsMargins(12, 12, 12, 12)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        port_label = QLabel("Port:")
        self.port_combo = QComboBox(self)
        self.refresh_ports()
        self.refresh_btn = QPushButton("Refresh Ports", self)
        self.refresh_btn.clicked.connect(self.refresh_ports)

        baud_label = QLabel("Baud:")
        self.baud_combo = QComboBox(self)
        self.baud_combo.addItems(["115200", "57600", "38400", "19200", "9600", "230400"])
        self.baud_combo.setCurrentText("115200")

        name_label = QLabel("Nama Perenang:")
        self.swimmer_name_edit = QLineEdit(self)
        self.swimmer_name_edit.setPlaceholderText("Nama pemain")

        stroke_label = QLabel("Gaya renang:")
        self.stroke_combo = QComboBox(self)
        self.stroke_combo.addItems(STROKE_STYLES)

        grid.addWidget(port_label, 0, 0)
        grid.addWidget(self.port_combo, 0, 1)
        grid.addWidget(self.refresh_btn, 0, 2)
        grid.addWidget(baud_label, 1, 0)
        grid.addWidget(self.baud_combo, 1, 1)
        grid.addWidget(name_label, 2, 0)
        grid.addWidget(self.swimmer_name_edit, 2, 1, 1, 2)
        grid.addWidget(stroke_label, 3, 0)
        grid.addWidget(self.stroke_combo, 3, 1, 1, 2)

        controls.layout().addLayout(grid)

        file_name_caption = QLabel("Nama file:", self)
        file_name_caption.setStyleSheet("color: #9ca3af; font-size: 10pt; font-weight: 600;")
        self.log_filename_label = QLabel("—", self)
        self.log_filename_label.setWordWrap(True)
        self.log_filename_label.setStyleSheet(
            "color: #d1d5db; font-size: 10pt; font-family: Consolas, 'Courier New', monospace;"
        )
        controls.layout().addWidget(file_name_caption)
        controls.layout().addWidget(self.log_filename_label)

        row_btn = QHBoxLayout()
        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.log_btn = QPushButton("Start Log", self)
        self.log_btn.setCheckable(True)
        self.log_btn.clicked.connect(self.toggle_logging)
        self.log_btn.setEnabled(False)
        row_btn.addWidget(self.connect_btn)
        row_btn.addWidget(self.log_btn)
        controls.layout().addLayout(row_btn)

        indicators = QGroupBox("Nilai terakhir", self)
        ind_outer = QVBoxLayout(indicators)
        self.force_label = QLabel("0.00 Kg")
        self.roll_label = QLabel("0.00°")
        self.pitch_label = QLabel("0.00°")
        for w in (self.force_label, self.roll_label, self.pitch_label):
            w.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt;")

        def _pair(title: str, value_label: QLabel) -> QWidget:
            box = QWidget(self)
            lay = QVBoxLayout(box)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(QLabel(title))
            lay.addWidget(value_label)
            return box

        ind_outer.addWidget(_pair("Force (Kg)", self.force_label))
        ind_outer.addWidget(_pair("Roll Motion (Deg)", self.roll_label))
        ind_outer.addWidget(_pair("Pitch Motion (Deg)", self.pitch_label))

        right_layout.addWidget(controls, 0)
        right_layout.addWidget(indicators, 1)

        live_layout.addWidget(plots_panel, 4)
        live_layout.addWidget(right_panel, 1)

        # ---------- Tab Analisa ----------
        analyze_tab = QWidget(self)
        analyze_layout = QHBoxLayout(analyze_tab)
        analyze_layout.setContentsMargins(8, 8, 8, 8)

        analyze_plots_panel = QWidget(self)
        analyze_plots_layout = QVBoxLayout(analyze_plots_panel)
        analyze_plots_layout.setContentsMargins(0, 0, 0, 0)

        (
            self.analyze_force_plot_widget,
            self.analyze_roll_plot_widget,
            self.analyze_pitch_plot_widget,
            self.analyze_force_curve,
            self.analyze_roll_curve,
            self.analyze_pitch_curve,
        ) = make_three_stack_plots()
        self.analyze_force_plot_widget.setTitle("Force Data (Kg) — rekaman", color="#e5e7eb", size="12pt")
        self.analyze_roll_plot_widget.setTitle("Roll Motion (Deg) — rekaman", color="#e5e7eb", size="11pt")
        self.analyze_pitch_plot_widget.setTitle("Pitch Motion (Deg) — rekaman", color="#e5e7eb", size="11pt")

        analyze_plots_layout.addWidget(self.analyze_force_plot_widget, 1)
        analyze_plots_layout.addWidget(self.analyze_roll_plot_widget, 1)
        analyze_plots_layout.addWidget(self.analyze_pitch_plot_widget, 1)

        analyze_right_panel = QWidget(self)
        analyze_right_layout = QVBoxLayout(analyze_right_panel)
        analyze_right_layout.setContentsMargins(0, 0, 0, 0)

        analyze_load_group = QGroupBox("", self)
        analyze_load_group.setLayout(QVBoxLayout())
        analyze_load_group.layout().setContentsMargins(12, 14, 12, 14)
        analyze_load_group.layout().setSpacing(10)

        self.load_csv_btn = QPushButton("Load CSV…", self)
        self.load_csv_btn.clicked.connect(self.load_analyze_csv)
        analyze_load_group.layout().addWidget(self.load_csv_btn)

        self.analyze_meta_label = QLabel(self)
        self.analyze_meta_label.setObjectName("AnalyzeRichLabel")
        self.analyze_meta_label.setWordWrap(True)
        self.analyze_meta_label.setTextFormat(Qt.TextFormat.RichText)
        self.analyze_meta_label.setText(_html_analyze_load_placeholder())
        analyze_load_group.layout().addWidget(self.analyze_meta_label)

        self.analyze_stats_group = QGroupBox("", self)
        stats_inner = QVBoxLayout(self.analyze_stats_group)
        stats_inner.setContentsMargins(12, 14, 12, 14)
        stats_inner.setSpacing(10)
        self.stat_force_label = QLabel(self)
        self.stat_roll_label = QLabel(self)
        self.stat_pitch_label = QLabel(self)
        for lb in (self.stat_force_label, self.stat_roll_label, self.stat_pitch_label):
            lb.setObjectName("AnalyzeRichLabel")
            lb.setWordWrap(True)
            lb.setTextFormat(Qt.TextFormat.RichText)
            lb.setText(_html_analyze_stat_placeholder())

        stats_inner.addWidget(self.stat_force_label)
        stats_inner.addWidget(self.stat_roll_label)
        stats_inner.addWidget(self.stat_pitch_label)

        self._analyze_scatter_force: pg.ScatterPlotItem | None = None
        self._analyze_scatter_roll: pg.ScatterPlotItem | None = None
        self._analyze_scatter_pitch: pg.ScatterPlotItem | None = None
        self._analyze_stat_texts: list[tuple[pg.PlotWidget, pg.TextItem]] = []

        analyze_right_layout.addWidget(analyze_load_group, 0)
        analyze_right_layout.addWidget(self.analyze_stats_group, 0)
        analyze_right_layout.addStretch(1)

        analyze_layout.addWidget(analyze_plots_panel, 4)
        analyze_layout.addWidget(analyze_right_panel, 1)

        self.tab_widget.addTab(live_tab, "Live")
        self.tab_widget.addTab(analyze_tab, "Analisa")

        self._apply_styles(controls, indicators)

    def _apply_styles(self, controls: QGroupBox, indicators: QGroupBox) -> None:
        self.setStyleSheet(
            """
            QWidget { font-family: 'Segoe UI', Arial; font-size: 11pt; }
            QGroupBox { border: 1px solid #374151; border-radius: 10px; margin-top: 10px; background: #1f2937; }
            QGroupBox::title { color: #e5e7eb; }
            QLabel { color: #e5e7eb; }
            QComboBox { background: #374151; color: #e5e7eb; border: 1px solid #4b5563; padding: 6px; border-radius: 8px; }
            QComboBox:disabled { background: #2d3643; color: #9ca3af; }
            QLineEdit { background: #374151; color: #e5e7eb; border: 1px solid #4b5563; padding: 6px; border-radius: 8px; }
            QLineEdit:disabled { background: #2d3643; color: #9ca3af; }
            QPushButton { padding: 8px 12px; background-color: #3b82f6; color: #fff; border: none; border-radius: 8px; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:checked { background-color: #ef4444; }
            QPushButton:disabled { background-color: #6b7280; color: #d1d5db; }
            QTabWidget::pane {
                border: 1px solid #374151;
                border-radius: 8px;
                background: #0f172a;
                margin-top: 4px;
            }
            QTabBar::tab {
                background: #1f2937;
                color: #d1d5db;
                padding: 8px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected { background: #3b82f6; color: #fff; }
            QTabBar::tab:hover:!selected { background: #374151; }
            QLabel#AnalyzeRichLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
            """
        )

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText() if self.port_combo.count() else ""
        self.port_combo.clear()
        items = [p.device for p in list_ports.comports()]
        self.port_combo.addItems(items)
        if current and current in items:
            self.port_combo.setCurrentText(current)
        elif len(items) == 1:
            self.port_combo.setCurrentIndex(0)

    @staticmethod
    def _parse_logged_csv(path: Path) -> tuple[str, str, list[float], list[float], list[float], list[float]]:
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

    def load_analyze_csv(self) -> None:
        start_dir = str(DATALOG_DIR) if DATALOG_DIR.is_dir() else str(SCRIPT_DIR)
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
            swimmer, stroke, ts_list, f_list, r_list, p_list = self._parse_logged_csv(path)
        except OSError as e:
            QMessageBox.critical(self, "Load CSV", f"Tidak bisa membaca file:\n{e}")
            return
        except ValueError as e:
            QMessageBox.warning(self, "Load CSV", str(e))
            return

        self.analyze_force_curve.setData(ts_list, f_list)
        self.analyze_roll_curve.setData(ts_list, r_list)
        self.analyze_pitch_curve.setData(ts_list, p_list)

        self.analyze_meta_label.setText(_html_analyze_load_block(swimmer, stroke, path.name))

        self._clear_analyze_stat_markers()
        self._apply_analyze_statistics(ts_list, f_list, r_list, p_list)

    def _clear_analyze_stat_markers(self) -> None:
        for plot, txt in self._analyze_stat_texts:
            plot.removeItem(txt)
        self._analyze_stat_texts.clear()

        for plot, attr in (
            (self.analyze_force_plot_widget, "_analyze_scatter_force"),
            (self.analyze_roll_plot_widget, "_analyze_scatter_roll"),
            (self.analyze_pitch_plot_widget, "_analyze_scatter_pitch"),
        ):
            sc = getattr(self, attr, None)
            if sc is not None:
                plot.removeItem(sc)
                setattr(self, attr, None)

    def _add_analyze_marker_label(
        self,
        plot: pg.PlotWidget,
        marker_x: float,
        marker_y: float,
        text: str,
        ts_min: float,
        ts_max: float,
    ) -> None:
        """
        Label dua baris di samping marker (bukan di atas) supaya baris ``t:`` tidak terpotong
        di tepi atas plot.

        Aturan horizontal (berdasarkan posisi waktu dalam rentang CSV):
        - titik di separuh kiri rentang waktu → label di kanan marker (teks menjauh ke kanan);
        - titik di separuh kanan → label di kiri marker (teks menjauh ke kiri).
        Vertikal: tengah teks sejajar dengan titik (anchor y = 0.5).
        """
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
        self._analyze_stat_texts.append((plot, ti))

    def _apply_analyze_statistics(
        self,
        ts_list: list[float],
        f_list: list[float],
        r_list: list[float],
        p_list: list[float],
    ) -> None:
        """Hitung ekstremum, isi label Statistik, dan tampilkan marker di plot Analisa."""
        n = len(ts_list)
        if n == 0:
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

        self.stat_force_label.setText(_html_analyze_stat_force(v_fmax, t_fmax))
        self.stat_roll_label.setText(
            _html_analyze_stat_roll(
                r_list[i_rmin], ts_list[i_rmin], r_list[i_rmax], ts_list[i_rmax]
            )
        )
        self.stat_pitch_label.setText(
            _html_analyze_stat_pitch(
                p_list[i_pmin], ts_list[i_pmin], p_list[i_pmax], ts_list[i_pmax]
            )
        )

        self._analyze_scatter_force = pg.ScatterPlotItem(
            pos=[(t_fmax, v_fmax)],
            size=14,
            symbol="o",
            pen=pg.mkPen("#f8fafc", width=2),
            brush=pg.mkBrush(ANALYZE_MARKER_MAX_COLOR),
        )
        self._analyze_scatter_force.setZValue(10)
        self.analyze_force_plot_widget.addItem(self._analyze_scatter_force)
        self._add_analyze_marker_label(
            self.analyze_force_plot_widget,
            t_fmax,
            v_fmax,
            f"Waktu maksimum\n{t_fmax:.2f} s\nMaksimum\n{v_fmax:.2f} Kg",
            ts_min,
            ts_max,
        )

        self._analyze_scatter_roll = pg.ScatterPlotItem(
            pos=[
                (ts_list[i_rmin], r_list[i_rmin]),
                (ts_list[i_rmax], r_list[i_rmax]),
            ],
            size=14,
            symbol="o",
            pen=pg.mkPen("#0f172a", width=2),
            brush=[pg.mkBrush(ANALYZE_MARKER_MIN_COLOR), pg.mkBrush(ANALYZE_MARKER_MAX_COLOR)],
        )
        self._analyze_scatter_roll.setZValue(10)
        self.analyze_roll_plot_widget.addItem(self._analyze_scatter_roll)
        tr_min, vr_min = ts_list[i_rmin], r_list[i_rmin]
        tr_max, vr_max = ts_list[i_rmax], r_list[i_rmax]
        self._add_analyze_marker_label(
            self.analyze_roll_plot_widget,
            tr_min,
            vr_min,
            f"Waktu minimum\n{tr_min:.2f} s\nMinimum\n{vr_min:.2f}°",
            ts_min,
            ts_max,
        )
        self._add_analyze_marker_label(
            self.analyze_roll_plot_widget,
            tr_max,
            vr_max,
            f"Waktu maksimum\n{tr_max:.2f} s\nMaksimum\n{vr_max:.2f}°",
            ts_min,
            ts_max,
        )

        self._analyze_scatter_pitch = pg.ScatterPlotItem(
            pos=[
                (ts_list[i_pmin], p_list[i_pmin]),
                (ts_list[i_pmax], p_list[i_pmax]),
            ],
            size=14,
            symbol="o",
            pen=pg.mkPen("#0f172a", width=2),
            brush=[pg.mkBrush(ANALYZE_MARKER_MIN_COLOR), pg.mkBrush(ANALYZE_MARKER_MAX_COLOR)],
        )
        self._analyze_scatter_pitch.setZValue(10)
        self.analyze_pitch_plot_widget.addItem(self._analyze_scatter_pitch)
        tp_min, vp_min = ts_list[i_pmin], p_list[i_pmin]
        tp_max, vp_max = ts_list[i_pmax], p_list[i_pmax]
        self._add_analyze_marker_label(
            self.analyze_pitch_plot_widget,
            tp_min,
            vp_min,
            f"Waktu minimum\n{tp_min:.2f} s\nMinimum\n{vp_min:.2f}°",
            ts_min,
            ts_max,
        )
        self._add_analyze_marker_label(
            self.analyze_pitch_plot_widget,
            tp_max,
            vp_max,
            f"Waktu maksimum\n{tp_max:.2f} s\nMaksimum\n{vp_max:.2f}°",
            ts_min,
            ts_max,
        )

    def toggle_connection(self, checked: bool) -> None:
        if checked:
            if not self.connect_serial():
                self.connect_btn.setChecked(False)
        else:
            self.disconnect_serial()

    def connect_serial(self) -> bool:
        port = self.port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "Serial", "Pilih port COM terlebih dahulu.")
            return False
        try:
            baud = int(self.baud_combo.currentText())
        except ValueError:
            baud = 115200
        try:
            self.ser = serial.Serial(port, baudrate=baud, timeout=0.1)
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            self.serial_buffer = b""
            self.clear_all_plots()
            self.serial_timer.start(50)
            self.connect_btn.setText("Disconnect")
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.log_btn.setEnabled(True)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Serial", f"Gagal koneksi:\n{e}")
            self.ser = None
            return False

    def disconnect_serial(self) -> None:
        try:
            if self.serial_timer.isActive():
                self.serial_timer.stop()
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        finally:
            self.ser = None
            self.connect_btn.setText("Connect")
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            if self.log_btn.isChecked():
                self.log_btn.setChecked(False)
                self.stop_logging()
            self.log_btn.setEnabled(False)

    def clear_all_plots(self) -> None:
        for lst in (
            self.force_time_data,
            self.force_data,
            self.roll_time_data,
            self.roll_data,
            self.pitch_time_data,
            self.pitch_data,
        ):
            lst.clear()
        self.force_curve.setData([], [])
        self.roll_curve.setData([], [])
        self.pitch_curve.setData([], [])

    def poll_serial(self) -> None:
        if not self.ser:
            return
        try:
            n = self.ser.in_waiting
            chunk = self.ser.read(n or 1)
            if not chunk:
                return
            self.serial_buffer += chunk
            while b"\n" in self.serial_buffer:
                line, self.serial_buffer = self.serial_buffer.split(b"\n", 1)
                text = line.decode("utf-8", errors="replace").strip()
                if not text or text.startswith("#"):
                    continue
                parts = [p.strip() for p in text.split(",")]
                if len(parts) != 4:
                    continue
                try:
                    ts = float(parts[0])
                    force_kg = float(parts[1])
                    roll_deg = float(parts[2])
                    pitch_deg = float(parts[3])
                except ValueError:
                    continue
                self.update_live(ts, force_kg, roll_deg, pitch_deg)
                if self.log_file is not None:
                    self.log_buffer.append(
                        f"{ts:.2f},{force_kg:.2f},{roll_deg:.2f},{pitch_deg:.2f}\n"
                    )
        except Exception as e:
            print(f"[SERIAL] Read error: {e}")

    def update_live(
        self,
        ts: float,
        force_kg: float,
        roll_deg: float,
        pitch_deg: float,
    ) -> None:
        self.force_label.setText(f"{force_kg:.2f} Kg")
        self.roll_label.setText(f"{roll_deg:.2f}°")
        self.pitch_label.setText(f"{pitch_deg:.2f}°")

        self.force_time_data.append(ts)
        self.force_data.append(force_kg)
        self.roll_time_data.append(ts)
        self.roll_data.append(roll_deg)
        self.pitch_time_data.append(ts)
        self.pitch_data.append(pitch_deg)

        for series in (
            (self.force_time_data, self.force_data),
            (self.roll_time_data, self.roll_data),
            (self.pitch_time_data, self.pitch_data),
        ):
            tx, y = series
            while len(tx) > self.max_points:
                tx.pop(0)
                y.pop(0)

        self.force_curve.setData(self.force_time_data, self.force_data)
        self.roll_curve.setData(self.roll_time_data, self.roll_data)
        self.pitch_curve.setData(self.pitch_time_data, self.pitch_data)

    def toggle_logging(self, checked: bool) -> None:
        if checked:
            if not self.ser or not self.ser.is_open:
                self.log_btn.setChecked(False)
                return
            name = self.swimmer_name_edit.text().strip() or "TanpaNama"
            stroke = self.stroke_combo.currentText()
            try:
                DATALOG_DIR.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "DataLog", f"Tidak bisa membuat folder DataLog:\n{e}")
                self.log_btn.setChecked(False)
                return

            now = datetime.now()
            self._log_header_time_str = now.strftime("%d%m%y-%H%M")
            fn = (
                f"{_safe_filename_part(name)}_{_safe_filename_part(stroke)}_"
                f"{self._log_header_time_str}.csv"
            )
            path = DATALOG_DIR / fn
            try:
                self.log_file_path = path
                self.log_file = open(path, "w", buffering=1, encoding="utf-8")
                self.log_file.write(f"Nama Perenang:,{name}\n")
                self.log_file.write(f"Gaya Renang:,{stroke}\n")
                self.log_file.write(f"Time:,{self._log_header_time_str}\n")
                self.log_file.write("TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)\n")
                self.log_buffer.clear()
                self.log_timer.start()
                self.log_btn.setText("Stop Log")
                self.swimmer_name_edit.setEnabled(False)
                self.stroke_combo.setEnabled(False)
                self.connect_btn.setEnabled(False)
                self.log_filename_label.setText(path.name)
            except Exception as e:
                QMessageBox.critical(self, "Log", f"Gagal membuka file:\n{e}")
                self.log_file = None
                self.log_file_path = None
                self.log_btn.setChecked(False)
                self.log_filename_label.setText("—")
        else:
            self.stop_logging()

    def stop_logging(self) -> None:
        try:
            self.log_timer.stop()
            self.flush_log_buffer()
            if self.log_file:
                self.log_file.close()
        except Exception:
            pass
        finally:
            self.log_file = None
            self.log_file_path = None
            if self.log_btn:
                self.log_btn.setText("Start Log")
            self.swimmer_name_edit.setEnabled(True)
            self.stroke_combo.setEnabled(True)
            if self.connect_btn:
                self.connect_btn.setEnabled(True)
            self.log_filename_label.setText("—")

    def flush_log_buffer(self) -> None:
        if not self.log_file or not self.log_buffer:
            return
        try:
            self.log_file.writelines(self.log_buffer)
            self.log_buffer.clear()
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self.disconnect_serial()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())

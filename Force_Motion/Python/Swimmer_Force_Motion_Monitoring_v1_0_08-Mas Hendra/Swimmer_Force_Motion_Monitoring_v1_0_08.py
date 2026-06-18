"""
Swimmer Force and Motion Monitoring
===================================

Aplikasi desktop PySide6 untuk memantau beban (force, kg) dan orientasi
gerak (roll & pitch, derajat) secara real-time dari perangkat sensor via
port serial USB, merekam data ke CSV, serta menganalisis rekaman dengan
statistik ekstremum dan analisa FFT pada sinyal force.

Versi  : 1.0.08  (``APP_VERSION``)
Berkas : Swimmer_Force_Motion_Monitoring_v1_0_08.py

Fitur utama:
    - Tab **Live**: koneksi serial, plot waktu-nyata (jendela 10 s),
      indikator baterai (kolom ke-5 opsional), rekaman CSV.
    - Tab **Analisa**: muat CSV log, plot penuh + marker min/max,
      FFT force (frekuensi dominan, stroke rate, RMS), ekspor statistik.

Format serial (UTF-8, satu baris per sampel, dipisah koma):
    TimeStamp(s), Force(Kg), Roll(Deg), Pitch(Deg) [, Battery(%)]

Dependensi:
    pip install PySide6 pyqtgraph pyserial numpy

Manual pengguna:
    UserManual_Force_Motion_v1.0.08.md / .pdf (mode skrip Python)
    UserManual_Force_Motion_v1.0.08-e.md / .pdf (mode executable, di-bundle)
"""

import sys
import os
import csv
import math
import time
import datetime
import re
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit,
    QCheckBox, QGroupBox, QSplitter, QTextEdit, QFileDialog,
    QMessageBox, QDialog, QScrollArea, QSizePolicy, QFrame,
    QGridLayout, QSpacerItem,
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap

import pyqtgraph as pg
import serial
import serial.tools.list_ports

# ─────────────────────────────────────────────
#  Konstanta aplikasi
# ─────────────────────────────────────────────
APP_NAME    = "Swimmer Force and Motion Monitoring"
APP_VERSION = "1.0.08"
EXE_NAME    = f"Swimmer_Force_Motion_Monitoring_v{APP_VERSION}.exe"
CSV_HEADER_BAT     = "TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg),Battery(%)"
SERIAL_BAUD_DEFAULT = 115200
MAX_POINTS  = 1000          # titik maks buffer live plot (safety cap)
LIVE_WINDOW_S = 10.0       # lebar jendela waktu sumbu-X live plot (detik)
POLL_INTERVAL_MS   = 50   # ms – interval timer baca serial
FLUSH_INTERVAL_MS  = 500  # ms – interval flush buffer log ke disk
CSV_HEADER         = "TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)"
SWIMSTYLES         = ["Bebas", "Dada", "Punggung", "Kupu-kupu", "Monofin","Bifins"]


def is_frozen() -> bool:
    """True jika dijalankan sebagai executable PyInstaller."""
    return getattr(sys, "frozen", False)


def resource_dir() -> str:
    """Folder aset read-only (manual); ``sys._MEIPASS`` saat frozen."""
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def app_dir() -> str:
    """Folder aplikasi untuk data tulis (``DataLog``, ``DataStatistik``)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def data_log_dir() -> str:
    """Path absolut folder rekaman CSV."""
    return os.path.join(app_dir(), "DataLog")


def stat_log_dir() -> str:
    """Path absolut folder ekspor statistik."""
    return os.path.join(app_dir(), "DataStatistik")


def user_manual_basename() -> str:
    """Nama dasar manual: suffix ``-e`` untuk executable."""
    suffix = "-e" if is_frozen() else ""
    return f"UserManual_Force_Motion_v{APP_VERSION}{suffix}"


def logo_path(filename: str) -> str:
    """Path logo BRIN/UNNES: bundle exe, folder skrip, atau ``Force_Motion/Image/``."""
    bundled = os.path.join(resource_dir(), filename)
    if os.path.isfile(bundled):
        return bundled
    image_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Image")
    )
    shared = os.path.join(image_dir, filename)
    if os.path.isfile(shared):
        return shared
    return bundled

# ─────────────────────────────────────────────
#  Palette & style
# ─────────────────────────────────────────────
DARK_BG      = "#0d1117"
PANEL_BG     = "#161b22"
ACCENT_BLUE  = "#1f6feb"
ACCENT_CYAN  = "#39d0f5"
ACCENT_GREEN = "#2ea043"
ACCENT_RED   = "#f85149"
ACCENT_GOLD  = "#e3b341"
TEXT_PRIMARY = "#e6edf3"
TEXT_MUTED   = "#8b949e"
BORDER_COLOR = "#30363d"

GLOBAL_QSS = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER_COLOR};
    background: {PANEL_BG};
    border-radius: 4px;
}}
QTabBar::tab {{
    background: {DARK_BG};
    color: {TEXT_MUTED};
    padding: 8px 20px;
    border: 1px solid {BORDER_COLOR};
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    font-weight: bold;
    font-size: 12px;
    letter-spacing: 1px;
}}
QTabBar::tab:selected {{
    background: {PANEL_BG};
    color: {ACCENT_CYAN};
    border-top: 2px solid {ACCENT_CYAN};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY};
    background: #1c2128;
}}
QGroupBox {{
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    margin-top: 14px;
    padding: 8px 6px 6px 6px;
    font-weight: bold;
    color: {TEXT_MUTED};
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}}
QLabel {{
    color: {TEXT_PRIMARY};
}}
QLineEdit, QComboBox {{
    background: {DARK_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    padding: 4px 8px;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT_BLUE};
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {ACCENT_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {PANEL_BG};
    border: 1px solid {BORDER_COLOR};
    selection-background-color: {ACCENT_BLUE};
    color: {TEXT_PRIMARY};
}}
QPushButton {{
    background: #21262d;
    border: 1px solid {BORDER_COLOR};
    border-radius: 5px;
    padding: 6px 14px;
    color: {TEXT_PRIMARY};
    font-weight: bold;
    letter-spacing: 0.5px;
}}
QPushButton:hover {{
    background: #30363d;
    border-color: {ACCENT_BLUE};
}}
QPushButton:pressed {{
    background: #0d1117;
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: #21262d;
}}
QPushButton#btn_connect {{
    background: #0e4429;
    border-color: {ACCENT_GREEN};
    color: #3fb950;
}}
QPushButton#btn_connect:hover {{
    background: #196634;
}}
QPushButton#btn_disconnect {{
    background: #3d1f1f;
    border-color: {ACCENT_RED};
    color: {ACCENT_RED};
}}
QPushButton#btn_disconnect:hover {{
    background: #5a2020;
}}
QPushButton#btn_startlog {{
    background: #0a3069;
    border-color: {ACCENT_BLUE};
    color: #79c0ff;
}}
QPushButton#btn_startlog:hover {{
    background: #1158c7;
}}
QPushButton#btn_stoplog {{
    background: #3d2800;
    border-color: {ACCENT_GOLD};
    color: {ACCENT_GOLD};
}}
QPushButton#btn_stoplog:hover {{
    background: #5a3d00;
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    background: {DARK_BG};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
}}
QTextEdit {{
    background: {DARK_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    color: {TEXT_MUTED};
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10px;
    padding: 4px;
}}
QScrollBar:vertical {{
    background: {DARK_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #30363d;
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_BLUE};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QSplitter::handle {{
    background: {BORDER_COLOR};
}}
"""

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def ensure_dir(path: str):
    """Buat folder ``path`` jika belum ada (tidak error jika sudah ada)."""
    os.makedirs(path, exist_ok=True)


def safe_filename(name: str) -> str:
    """Ganti karakter tidak aman untuk nama berkas."""
    return re.sub(r'[\\/*?:"<>| ]', '_', name.strip()) or "Unknown"


def value_label(value: float | None, unit: str = "", decimals: int = 2) -> str:
    """Format angka untuk label UI; kembalikan em-dash jika ``value`` None."""
    if value is None:
        return "—"
    return f"{value:.{decimals}f} {unit}".strip()


# ─────────────────────────────────────────────
#  Widget indikator nilai (LCD-style card)
# ─────────────────────────────────────────────
class ValueCard(QFrame):
    """Kartu indikator nilai bergaya LCD (judul, angka besar, satuan)."""

    def __init__(self, title: str, unit: str, accent: str = ACCENT_CYAN, parent=None):
        super().__init__(parent)
        self.unit   = unit
        self.accent = accent
        self.setMinimumWidth(100)
        self.setFixedHeight(74)
        self.setStyleSheet(f"""
            QFrame {{
                background: {PANEL_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; letter-spacing:2px;")
        self.lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_value = QLabel("—")
        self.lbl_value.setStyleSheet(
            f"color:{accent}; font-size:22px; font-weight:bold; font-family:'Consolas','Courier New',monospace;"
        )
        self.lbl_value.setAlignment(Qt.AlignCenter)

        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px;")
        self.lbl_unit.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_value)
        lay.addWidget(self.lbl_unit)

    def update_value(self, val: float | None, decimals: int = 2):
        """Perbarui angka tampilan; tampilkan em-dash jika ``val`` None."""
        if val is None:
            self.lbl_value.setText("—")
        else:
            self.lbl_value.setText(f"{val:.{decimals}f}")


# ─────────────────────────────────────────────
#  Status bar sederhana
# ─────────────────────────────────────────────
class StatusBar(QLabel):
    """Bar status bawah jendela dengan metode ``info``, ``ok``, ``warn``, ``err``."""

    def __init__(self, parent=None):
        super().__init__("Siap.", parent)
        self.setStyleSheet(
            f"background:{DARK_BG}; color:{TEXT_MUTED}; padding:3px 8px;"
            f"border-top:1px solid {BORDER_COLOR}; font-size:10px;"
        )
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def info(self, msg: str):
        self.setStyleSheet(
            f"background:{DARK_BG}; color:{TEXT_MUTED}; padding:3px 8px;"
            f"border-top:1px solid {BORDER_COLOR}; font-size:10px;"
        )
        self.setText(msg)

    def ok(self, msg: str):
        self.setStyleSheet(
            f"background:{DARK_BG}; color:{ACCENT_GREEN}; padding:3px 8px;"
            f"border-top:1px solid {BORDER_COLOR}; font-size:10px;"
        )
        self.setText(msg)

    def warn(self, msg: str):
        self.setStyleSheet(
            f"background:{DARK_BG}; color:{ACCENT_GOLD}; padding:3px 8px;"
            f"border-top:1px solid {BORDER_COLOR}; font-size:10px;"
        )
        self.setText(msg)

    def err(self, msg: str):
        self.setStyleSheet(
            f"background:{DARK_BG}; color:{ACCENT_RED}; padding:3px 8px;"
            f"border-top:1px solid {BORDER_COLOR}; font-size:10px;"
        )
        self.setText(msg)


# ─────────────────────────────────────────────
#  Widget indikator baterai
# ─────────────────────────────────────────────
class BatteryWidget(QWidget):
    """Icon baterai bergaya + label persen di sebelahnya."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level: int | None = None          # 0-100 atau None = tidak ada data
        self.setFixedSize(90, 30)
        self.setToolTip("Battery level (%)")

    def set_level(self, level: int | None):
        self._level = None if level is None else max(0, min(100, int(level)))
        self.update()   # trigger paintEvent

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QFont
        from PySide6.QtCore import QRect, Qt

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W, H = self.width(), self.height()

        # ── Ukuran komponen ikon baterai ─────────────────
        body_w = 42
        body_h = 20
        tip_w  = 4
        tip_h  = 8
        bx = 2
        by = (H - body_h) // 2

        # ── Warna level ──────────────────────────────────
        if self._level is None:
            bar_color = QColor(TEXT_MUTED)
        elif self._level > 50:
            bar_color = QColor(ACCENT_GREEN)
        elif self._level > 20:
            bar_color = QColor(ACCENT_GOLD)
        else:
            bar_color = QColor(ACCENT_RED)

        border_color = QColor(TEXT_MUTED) if self._level is None else bar_color

        # ── Gambar body baterai ──────────────────────────
        pen = QPen(border_color, 1.5)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(bx, by, body_w, body_h, 3, 3)

        # ── Gambar tonjolan kutub + ──────────────────────
        tip_x = bx + body_w
        tip_y = by + (body_h - tip_h) // 2
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(border_color))
        p.drawRoundedRect(tip_x, tip_y, tip_w, tip_h, 2, 2)

        # ── Gambar bar level isi ─────────────────────────
        if self._level is not None and self._level > 0:
            margin  = 3
            fill_w_max = body_w - margin * 2
            fill_w  = int(fill_w_max * self._level / 100)
            fill_h  = body_h - margin * 2
            p.setBrush(QBrush(bar_color))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(bx + margin, by + margin, fill_w, fill_h, 2, 2)

        # ── Teks persentase di sebelah kanan ─────────────
        txt = "—%" if self._level is None else f"{self._level}%"
        font = QFont("Consolas", 10, QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(bar_color if self._level is not None else QColor(TEXT_MUTED)))
        text_rect = QRect(bx + body_w + tip_w + 5, 0, W - bx - body_w - tip_w - 5, H)
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, txt)

        p.end()


# ═══════════════════════════════════════════════════════════
#  TAB LIVE
# ═══════════════════════════════════════════════════════════
class LiveTab(QWidget):
    """Tab pemantauan real-time: serial, plot geser, logging CSV, baterai."""

    status_message  = Signal(str, str)   # (level, teks) → StatusBar
    battery_update  = Signal(int)        # battery % → MainWindow BatteryWidget

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── state ──────────────────────────────────────────
        self.serial_port : serial.Serial | None = None
        self.is_logging  : bool = False
        self.log_file    = None
        self.log_buffer  : list[str] = []
        self.log_t0      : float | None = None   # referensi waktu sesi log

        self.t_buf  : list[float] = []
        self.f_buf  : list[float] = []
        self.r_buf  : list[float] = []
        self.p_buf  : list[float] = []
        self.serial_remainder = b""

        # ── timer ──────────────────────────────────────────
        self.timer_poll  = QTimer(self)
        self.timer_poll.setInterval(POLL_INTERVAL_MS)
        self.timer_poll.timeout.connect(self.poll_serial)

        self.timer_flush = QTimer(self)
        self.timer_flush.setInterval(FLUSH_INTERVAL_MS)
        self.timer_flush.timeout.connect(self.flush_log_buffer)

        self._build_ui()

    # ─── UI ────────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── panel kiri ────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(260)
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 0, 0)
        llay.setSpacing(8)

        # — Koneksi Serial —
        grp_serial = QGroupBox("Koneksi Serial")
        gs_lay = QGridLayout(grp_serial)
        gs_lay.setSpacing(5)
        gs_lay.addWidget(QLabel("Port:"), 0, 0)
        self.cmb_port = QComboBox()
        gs_lay.addWidget(self.cmb_port, 0, 1)
        gs_lay.addWidget(QLabel("Baud:"), 1, 0)
        self.cmb_baud = QComboBox()
        for b in ["9600","19200","38400","57600","115200","230400","460800"]:
            self.cmb_baud.addItem(b)
        self.cmb_baud.setCurrentText(str(SERIAL_BAUD_DEFAULT))
        gs_lay.addWidget(self.cmb_baud, 1, 1)

        btn_refresh = QPushButton("⟳ Refresh")
        btn_refresh.clicked.connect(self.refresh_ports)
        gs_lay.addWidget(btn_refresh, 2, 0, 1, 2)

        self.btn_connect    = QPushButton("▶  Connect")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.clicked.connect(self.connect_serial)
        self.btn_disconnect = QPushButton("■  Disconnect")
        self.btn_disconnect.setObjectName("btn_disconnect")
        self.btn_disconnect.clicked.connect(self.disconnect_serial)
        self.btn_disconnect.setEnabled(False)
        gs_lay.addWidget(self.btn_connect,    3, 0)
        gs_lay.addWidget(self.btn_disconnect, 3, 1)
        llay.addWidget(grp_serial)

        # — Info Perenang —
        grp_info = QGroupBox("Info Perenang")
        gi_lay = QGridLayout(grp_info)
        gi_lay.setSpacing(5)
        gi_lay.addWidget(QLabel("Nama:"), 0, 0)
        self.edt_nama = QLineEdit("Atlet")
        gi_lay.addWidget(self.edt_nama, 0, 1)
        gi_lay.addWidget(QLabel("Gaya:"), 1, 0)
        self.cmb_gaya = QComboBox()
        for s in SWIMSTYLES:
            self.cmb_gaya.addItem(s)
        gi_lay.addWidget(self.cmb_gaya, 1, 1)
        llay.addWidget(grp_info)

        # — Logging —
        grp_log = QGroupBox("Rekaman Log")
        gl_lay = QVBoxLayout(grp_log)
        gl_lay.setSpacing(5)
        self.chk_zero_ts = QCheckBox("TimeStamp CSV set to 0")
        self.chk_zero_ts.setChecked(True)
        gl_lay.addWidget(self.chk_zero_ts)

        hlog = QHBoxLayout()
        self.btn_startlog = QPushButton("▶ Start Log")
        self.btn_startlog.setObjectName("btn_startlog")
        self.btn_startlog.clicked.connect(self.start_logging)
        self.btn_startlog.setEnabled(False)
        self.btn_stoplog  = QPushButton("■ Stop Log")
        self.btn_stoplog.setObjectName("btn_stoplog")
        self.btn_stoplog.clicked.connect(self.stop_logging)
        self.btn_stoplog.setEnabled(False)
        hlog.addWidget(self.btn_startlog)
        hlog.addWidget(self.btn_stoplog)
        gl_lay.addLayout(hlog)

        self.lbl_logfile = QLabel(" ")
        self.lbl_logfile.setWordWrap(True)
        self.lbl_logfile.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px;")
        gl_lay.addWidget(self.lbl_logfile)
        llay.addWidget(grp_log)

        # — Plot Settings —
        grp_plot = QGroupBox("Plot")
        gp_lay = QGridLayout(grp_plot)
        gp_lay.setSpacing(5)
        gp_lay.addWidget(QLabel("Max Titik:"), 0, 0)
        self.edt_maxpts = QLineEdit(str(MAX_POINTS))
        gp_lay.addWidget(self.edt_maxpts, 0, 1)
        btn_apply = QPushButton("Terapkan")
        btn_apply.clicked.connect(self._apply_maxpoints)
        gp_lay.addWidget(btn_apply, 1, 0, 1, 2)
        llay.addWidget(grp_plot)

        llay.addStretch()

        # — Logo BRIN + UNNES + Copyright —
        logo_frame = QFrame()
        logo_frame.setStyleSheet(
            f"background:{PANEL_BG}; border:none solid {BORDER_COLOR}; border-radius:6px;"
        )
        logo_lay = QHBoxLayout(logo_frame)
        logo_lay.setContentsMargins(8, 6, 8, 6)
        logo_lay.setSpacing(10)
        logo_lay.setAlignment(Qt.AlignVCenter)

        LOGO_H = 36

        def _load_logo(filename: str, fallback_text: str) -> QLabel:
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignCenter)
            path = logo_path(filename)
            if os.path.isfile(path):
                pix = QPixmap(path).scaledToHeight(LOGO_H, Qt.SmoothTransformation)
                lbl.setPixmap(pix)
                lbl.setToolTip(fallback_text)
            else:
                lbl.setText(fallback_text)
                lbl.setStyleSheet(
                    f"color:{ACCENT_CYAN}; font-size:9px; font-weight:bold;"
                    f"letter-spacing:1px; padding:2px 5px;"
                    f"border:none solid {BORDER_COLOR}; border-radius:4px;"
                )
                lbl.setFixedHeight(LOGO_H)
            return lbl

        lbl_brin  = _load_logo("logo_brin.png",  "BRIN")
        lbl_unnes = _load_logo("logo_unnes.png", "UNNES")

        lbl_copy = QLabel("© Copyright 2026")
        lbl_copy.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lbl_copy.setStyleSheet(
            f"color:{TEXT_MUTED}; font-size:11px; letter-spacing:1px; border:none;"
        )
        lbl_copy.setWordWrap(True)

        logo_lay.addWidget(lbl_brin)
        logo_lay.addWidget(lbl_unnes)
        logo_lay.addWidget(lbl_copy, stretch=1)
        llay.addWidget(logo_frame)

        # — Tombol About / Help —
        btn_about = QPushButton("ℹ  About")
        btn_about.clicked.connect(self.show_about)
        btn_help  = QPushButton("?  Help")
        btn_help.clicked.connect(self.show_help)
        hbtn = QHBoxLayout()
        hbtn.addWidget(btn_about)
        hbtn.addWidget(btn_help)
        llay.addLayout(hbtn)

        root.addWidget(left)

        # ── panel kanan: plot + value cards ───────────────
        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)
        rlay.setSpacing(6)

        # plots
        pg.setConfigOption('background', PANEL_BG)
        pg.setConfigOption('foreground', TEXT_MUTED)

        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground(PANEL_BG)

        self._pw_force = self.plot_widget.addPlot(row=0, col=0, title="Grafik Force")
        self._pw_roll  = self.plot_widget.addPlot(row=1, col=0, title="Grafik Roll")
        self._pw_pitch = self.plot_widget.addPlot(row=2, col=0, title="Grafik Pitch")

        for pw, ylabel in [
            (self._pw_force, "Force (Kg)"),
            (self._pw_roll,  "Roll (°)"),
            (self._pw_pitch, "Pitch (°)"),
        ]:
            pw.showGrid(x=True, y=True, alpha=0.15)
            pw.setLabel('left',   ylabel,      color=TEXT_PRIMARY, **{'font-size': '9pt'})
            pw.setLabel('bottom', 'Time (s)',  color=TEXT_PRIMARY, **{'font-size': '9pt'})
            pw.getAxis('bottom').setStyle(tickFont=QFont("Consolas", 8))
            pw.getAxis('left').setStyle(tickFont=QFont("Consolas", 8))
            pw.getAxis('bottom').setPen(pg.mkPen(BORDER_COLOR))
            pw.getAxis('left').setPen(pg.mkPen(BORDER_COLOR))

        self.curve_force = self._pw_force.plot(pen=pg.mkPen(ACCENT_CYAN,  width=1.5))
        self.curve_roll  = self._pw_roll.plot( pen=pg.mkPen(ACCENT_GOLD,  width=1.5))
        self.curve_pitch = self._pw_pitch.plot(pen=pg.mkPen("#c792ea", width=1.5))

        rlay.addWidget(self.plot_widget, stretch=1)

        # log konsol
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(70)
        rlay.addWidget(self.log_console)

        root.addWidget(right, stretch=1)
        self.refresh_ports()
    
    # ─── port refresh ──────────────────────────────────────
    def refresh_ports(self):
        """Isi ulang combo port dari daftar COM yang terdeteksi sistem."""
        self.cmb_port.clear()
        ports = serial.tools.list_ports.comports()
        for p in sorted(ports, key=lambda x: x.device):
            self.cmb_port.addItem(f"{p.device}  [{p.description[:30]}]", p.device)
        if not ports:
            self.cmb_port.addItem("— tidak ada port —", "")
        self._log_console("Port serial diperbarui.")
    
    # ─── koneksi ───────────────────────────────────────────
    def connect_serial(self):
        """Buka port serial terpilih dan mulai timer polling data."""
        port = self.cmb_port.currentData()
        if not port:
            self.status_message.emit("err", "Tidak ada port dipilih.")
            return
        baud = int(self.cmb_baud.currentText())
        try:
            self.serial_port = serial.Serial(port, baud, timeout=0)
            self.serial_remainder = b""
            self.timer_poll.start()
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.btn_startlog.setEnabled(True)
            self.status_message.emit("ok", f"Terhubung ke {port} @ {baud} baud.")
            self._log_console(f"▶ Connected: {port} @ {baud}")
        except serial.SerialException as e:
            QMessageBox.critical(self, "Gagal Connect", str(e))
            self.status_message.emit("err", f"Gagal connect: {e}")

    def disconnect_serial(self):
        """Hentikan logging (jika aktif), tutup port, dan kosongkan plot."""
        if self.is_logging:
            self.stop_logging()
        self.timer_poll.stop()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_startlog.setEnabled(False)
        self.clear_charts()
        self.status_message.emit("info", "Terputus dari serial.")
        self._log_console("■ Disconnected.")

    def clear_charts(self):
        """Reset semua buffer data dan bersihkan tampilan grafik live."""
        self.t_buf.clear()
        self.f_buf.clear()
        self.r_buf.clear()
        self.p_buf.clear()
        self.serial_remainder = b""
        self.curve_force.setData([], [])
        self.curve_roll.setData([], [])
        self.curve_pitch.setData([], [])
        for pw in (self._pw_force, self._pw_roll, self._pw_pitch):
            pw.enableAutoRange()
            pw.setXRange(0, LIVE_WINDOW_S, padding=0)

    # ─── polling serial ────────────────────────────────────
    def poll_serial(self):
        """Baca byte dari buffer serial, pecah per baris, parse tiap sampel."""
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            waiting = self.serial_port.in_waiting
            if waiting <= 0:
                return
            raw = self.serial_remainder + self.serial_port.read(waiting)
            lines = raw.split(b'\n')
            self.serial_remainder = lines[-1]
            for line in lines[:-1]:
                self._parse_line(line)
        except (serial.SerialException, OSError) as e:
            self.status_message.emit("err", f"Serial error: {e}")
            self.disconnect_serial()

    def _parse_line(self, raw: bytes):
        """Decode satu baris CSV serial; update plot, log, dan indikator baterai."""
        try:
            txt = raw.decode("utf-8", errors="replace").strip()
        except Exception:
            return
        if not txt or txt.startswith("#"):
            return
        parts = txt.split(",")
        if len(parts) < 4:
            return
        try:
            ts, fv, rv, pv = [float(x) for x in parts[:4]]
        except ValueError:
            return

        # Baca battery (kolom ke-5, opsional)
        bat: int | None = None
        if len(parts) >= 5:
            try:
                bat = int(float(parts[4].strip()))
            except ValueError:
                pass

        # Update indikator baterai di header (via MainWindow)
        if bat is not None:
            self._emit_battery(bat)

        # tambah data baru ke buffer
        self.t_buf.append(ts)
        self.f_buf.append(fv)
        self.r_buf.append(rv)
        self.p_buf.append(pv)

        # hitung jendela tampilan terlebih dahulu
        if ts < LIVE_WINDOW_S:
            x_min, x_max = 0.0, LIVE_WINDOW_S
        else:
            x_max = ts
            x_min = x_max - LIVE_WINDOW_S

        # buffer geser — buang titik di luar jendela tampilan
        while self.t_buf and self.t_buf[0] < x_min:
            self.t_buf.pop(0)
            self.f_buf.pop(0)
            self.r_buf.pop(0)
            self.p_buf.pop(0)

        # safety cap agar buffer tidak terlalu besar
        max_pts = self._max_points()
        if len(self.t_buf) > max_pts:
            self.t_buf  = self.t_buf[-max_pts:]
            self.f_buf  = self.f_buf[-max_pts:]
            self.r_buf  = self.r_buf[-max_pts:]
            self.p_buf  = self.p_buf[-max_pts:]

        # update plot
        self.curve_force.setData(self.t_buf, self.f_buf)
        self.curve_roll.setData( self.t_buf, self.r_buf)
        self.curve_pitch.setData(self.t_buf, self.p_buf)

        # terapkan range sumbu-X
        for pw in (self._pw_force, self._pw_roll, self._pw_pitch):
            pw.setXRange(x_min, x_max, padding=0)

        # logging
        if self.is_logging:
            log_ts = ts
            if self.chk_zero_ts.isChecked() and self.log_t0 is not None:
                log_ts = ts - self.log_t0
            self.log_buffer.append(f"{log_ts:.4f},{fv:.4f},{rv:.4f},{pv:.4f}\n")

    def _max_points(self) -> int:
        """Baca batas titik buffer dari field UI; minimal 10."""
        try:
            v = int(self.edt_maxpts.text())
            return max(10, v)
        except ValueError:
            return MAX_POINTS

    def _apply_maxpoints(self):
        v = self._max_points()
        self.status_message.emit("info", f"Safety cap buffer diset ke {v} titik (window: {LIVE_WINDOW_S:.0f} detik).")

    # ─── logging ───────────────────────────────────────────
    def start_logging(self):
        """Buat file CSV di ``DataLog/`` dan mulai menulis sampel ke buffer."""
        if self.is_logging:
            return
        nama_raw = self.edt_nama.text().strip() or "Atlet"
        gaya     = self.cmb_gaya.currentText()
        ts_str   = datetime.datetime.now().strftime("%d%m%y-%H%M")
        nama_safe = safe_filename(nama_raw)
        gaya_safe = safe_filename(gaya)
        filename = f"{nama_safe}_{gaya_safe}_{ts_str}.csv"

        ensure_dir(data_log_dir())
        filepath = os.path.join(data_log_dir(), filename)

        try:
            self.log_file = open(filepath, "w", encoding="utf-8", newline="")
        except OSError as e:
            QMessageBox.critical(self, "Gagal Buka File", str(e))
            return

        # reset referensi waktu sesi
        if self.t_buf:
            self.log_t0 = self.t_buf[-1]
        else:
            self.log_t0 = None

        # tulis metadata
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"Nama Perenang: {nama_raw}\n")
        self.log_file.write(f"Gaya Renang: {gaya}\n")
        self.log_file.write(f"Time: {now}\n")
        self.log_file.write(f"{CSV_HEADER}\n")
        self.log_file.flush()

        self.is_logging = True
        self.log_buffer = []
        self.timer_flush.start()
        self.btn_startlog.setEnabled(False)
        self.btn_stoplog.setEnabled(True)
        self.lbl_logfile.setText(filename)
        self.status_message.emit("ok", f"Merekam → {filename}")
        self._log_console(f"● Log dimulai: {filepath}")

    def stop_logging(self):
        """Flush buffer tersisa, tutup file log, dan reset state rekaman."""
        if not self.is_logging:
            return
        self.is_logging = False
        self.timer_flush.stop()
        self.flush_log_buffer()
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.btn_startlog.setEnabled(True)
        self.btn_stoplog.setEnabled(False)
        self.status_message.emit("info", "Log dihentikan.")
        self._log_console("■ Log dihentikan.")

    def flush_log_buffer(self):
        """Tulis baris tertunda dari ``log_buffer`` ke disk (timer periodik)."""
        if self.log_file and self.log_buffer:
            self.log_file.writelines(self.log_buffer)
            self.log_file.flush()
            self.log_buffer.clear()

    def _emit_battery(self, level: int):
        self.battery_update.emit(level)

    # ─── konsol ────────────────────────────────────────────
    def _log_console(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{ts}] {msg}")

    # ─── About / Help ──────────────────────────────────────
    def show_about(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("About")
        dlg.setTextFormat(Qt.RichText)
        dlg.setText(
            f"<b style='color:{ACCENT_CYAN}'>{APP_NAME}</b><br>"
            f"<span style='color:{TEXT_MUTED}'>Versi {APP_VERSION}</span><br><br>"
            "Memantau beban (force, kg) dan orientasi gerak<br>"
            "(roll &amp; pitch, derajat) secara <i>real-time</i><br>"
            "via port serial USB.<br><br>"
            f"<span style='color:{TEXT_MUTED}'>Dependensi: PySide6 · pyqtgraph · pyserial</span>"
        )
        dlg.setStyleSheet(GLOBAL_QSS)
        dlg.exec()

    def show_help(self):
        """Buka manual PDF (bundle saat exe); fallback dialog teks dari file MD."""
        base = user_manual_basename()
        pdf_path = os.path.join(resource_dir(), f"{base}.pdf")
        md_path  = os.path.join(resource_dir(), f"{base}.md")
        if os.path.isfile(pdf_path):
            import subprocess, platform
            try:
                if platform.system() == "Windows":
                    os.startfile(pdf_path)
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", pdf_path])
                else:
                    subprocess.Popen(["xdg-open", pdf_path])
                return
            except Exception:
                pass
        # fallback: tampilkan teks bantuan singkat
        dlg = HelpDialog(md_path, self)
        dlg.setStyleSheet(GLOBAL_QSS)
        dlg.exec()

    def closeEvent(self, event):
        self.disconnect_serial()
        super().closeEvent(event)


# ─── Dialog bantuan fallback ───────────────────────────────
class HelpDialog(QDialog):
    """Dialog fallback bantuan: tampilkan isi file Markdown manual jika PDF tidak ada."""

    def __init__(self, md_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help – Panduan Singkat")
        self.resize(560, 420)
        lay = QVBoxLayout(self)
        txt = QTextEdit()
        txt.setReadOnly(True)
        if os.path.isfile(md_path):
            with open(md_path, encoding="utf-8") as f:
                txt.setPlainText(f.read())
        else:
            txt.setPlainText(
                "=== Panduan Singkat ===\n\n"
                "1. Pilih port serial dan baud rate sesuai perangkat.\n"
                "2. Klik 'Connect' untuk mulai menerima data.\n"
                "3. Isi Nama Perenang dan Gaya Renang.\n"
                "4. Klik 'Start Log' untuk merekam data ke CSV.\n"
                "5. Klik 'Stop Log' untuk mengakhiri rekaman.\n"
                "6. Buka tab 'Analisa' untuk memuat dan menganalisa file log.\n\n"
                "Format data serial (4 kolom, dipisah koma):\n"
                "  TimeStamp(s), Force(Kg), Roll(Deg), Pitch(Deg)\n\n"
                f"File manual tidak ditemukan: {md_path}\n"
            )
        lay.addWidget(txt)
        btn_ok = QPushButton("Tutup")
        btn_ok.clicked.connect(self.accept)
        lay.addWidget(btn_ok, alignment=Qt.AlignRight)


# ═══════════════════════════════════════════════════════════
#  TAB ANALISA
# ═══════════════════════════════════════════════════════════
class AnalisaTab(QWidget):
    """Tab analisis CSV: plot waktu penuh, statistik, FFT force, ekspor statistik."""

    status_message = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._csv_path   : str | None = None
        self._meta       : dict = {}
        self._t_data     : list[float] = []
        self._f_data     : list[float] = []
        self._r_data     : list[float] = []
        self._p_data     : list[float] = []
        self._extrema    : dict = {}
        self._build_ui()

    # ─── UI ────────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── panel kiri ────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(240)
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 0, 0)
        llay.setSpacing(8)

        grp_file = QGroupBox("File Log")
        gf_lay = QVBoxLayout(grp_file)
        self.lbl_file = QLabel("—")
        self.lbl_file.setWordWrap(True)
        self.lbl_file.setStyleSheet(f"color:{ACCENT_CYAN}; font-size:9px;")
        gf_lay.addWidget(self.lbl_file)
        btn_muat = QPushButton("📂  Muat CSV Log...")
        btn_muat.clicked.connect(self.load_csv)
        gf_lay.addWidget(btn_muat)
        llay.addWidget(grp_file)

        # Metadata
        grp_meta = QGroupBox("Metadata")
        gm_lay = QGridLayout(grp_meta)
        gm_lay.setSpacing(4)
        self.lbl_meta_nama = QLabel("—")
        self.lbl_meta_gaya = QLabel("—")
        self.lbl_meta_time = QLabel("—")
        self.lbl_meta_pts  = QLabel("—")
        for row, (key, lbl) in enumerate([
            ("Nama", self.lbl_meta_nama),
            ("Gaya", self.lbl_meta_gaya),
            ("Waktu", self.lbl_meta_time),
            ("Sampel", self.lbl_meta_pts),
        ]):
            gm_lay.addWidget(QLabel(f"{key}:"), row, 0)
            lbl.setStyleSheet(f"color:{TEXT_MUTED};")
            gm_lay.addWidget(lbl, row, 1)
        llay.addWidget(grp_meta)

        # Statistik
        grp_stat = QGroupBox("Statistik Ekstremum")
        gs_lay = QGridLayout(grp_stat)
        gs_lay.setSpacing(4)
        self._stat_labels: dict[str, QLabel] = {}
        metrics = [
            ("Force Min", "force_min", ACCENT_CYAN),
            ("Force Max", "force_max", ACCENT_CYAN),
            ("Force Mean", "force_mean", ACCENT_CYAN),
            ("Roll Min",  "roll_min",  ACCENT_GOLD),
            ("Roll Max",  "roll_max",  ACCENT_GOLD),
            ("Pitch Min", "pitch_min", "#c792ea"),
            ("Pitch Max", "pitch_max", "#c792ea"),
        ]
        for row, (label, key, color) in enumerate(metrics):
            gs_lay.addWidget(QLabel(f"{label}:"), row, 0)
            lbl = QLabel("—")
            lbl.setStyleSheet(f"color:{color}; font-weight:bold;")
            lbl.setAlignment(Qt.AlignRight)
            gs_lay.addWidget(lbl, row, 1)
            self._stat_labels[key] = lbl
        llay.addWidget(grp_stat)

        # Statistik FFT
        grp_fft = QGroupBox("Analisa FFT — Force")
        gff_lay = QGridLayout(grp_fft)
        gff_lay.setSpacing(4)
        self._fft_labels: dict[str, QLabel] = {}
        fft_metrics = [
            ("Freq. Dominan", "fft_dom_freq",    ACCENT_CYAN),
            ("Amplitudo Maks", "fft_dom_amp",    ACCENT_CYAN),
            ("Periode",        "fft_period",     ACCENT_CYAN),
            ("Stroke Rate",    "fft_stroke_rate",ACCENT_GREEN),
            ("Bandwidth",      "fft_bandwidth",  TEXT_MUTED),
            ("RMS Force",      "fft_rms",        ACCENT_GOLD),
        ]
        for row, (label, key, color) in enumerate(fft_metrics):
            gff_lay.addWidget(QLabel(f"{label}:"), row, 0)
            lbl = QLabel("—")
            lbl.setStyleSheet(f"color:{color}; font-weight:bold;")
            lbl.setAlignment(Qt.AlignRight)
            gff_lay.addWidget(lbl, row, 1)
            self._fft_labels[key] = lbl
        llay.addWidget(grp_fft)

        llay.addStretch()
        self.btn_save_stat = QPushButton("💾  Simpan Statistik")
        self.btn_save_stat.clicked.connect(self.save_statistics)
        self.btn_save_stat.setEnabled(False)
        llay.addWidget(self.btn_save_stat)

        root.addWidget(left)

        # ── panel kanan: plot ──────────────────────────────
        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)
        rlay.setSpacing(6)

        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground(PANEL_BG)

        self._aw_force = self.plot_widget.addPlot(row=0, col=0, title="Grafik Force")
        self._aw_roll  = self.plot_widget.addPlot(row=1, col=0, title="Grafik Roll")
        self._aw_pitch = self.plot_widget.addPlot(row=2, col=0, title="Grafik Pitch")
        self._aw_fft   = self.plot_widget.addPlot(row=3, col=0, title="FFT Force — Spektrum Frekuensi")

        for pw, ylabel in [
            (self._aw_force, "Force (Kg)"),
            (self._aw_roll,  "Roll (°)"),
            (self._aw_pitch, "Pitch (°)"),
        ]:
            pw.showGrid(x=True, y=True, alpha=0.15)
            pw.setLabel('left',   ylabel,      color=TEXT_PRIMARY, **{'font-size': '9pt'})
            pw.setLabel('bottom', 'Time (s)',  color=TEXT_PRIMARY, **{'font-size': '9pt'})
            pw.getAxis('bottom').setStyle(tickFont=QFont("Consolas", 8))
            pw.getAxis('left').setStyle(tickFont=QFont("Consolas", 8))
            pw.getAxis('bottom').setPen(pg.mkPen(BORDER_COLOR))
            pw.getAxis('left').setPen(pg.mkPen(BORDER_COLOR))

        # Styling grafik FFT
        self._aw_fft.showGrid(x=True, y=True, alpha=0.15)
        self._aw_fft.setLabel('left',   'Amplitudo',    color=TEXT_PRIMARY, **{'font-size': '9pt'})
        self._aw_fft.setLabel('bottom', 'Frekuensi (Hz)', color=TEXT_PRIMARY, **{'font-size': '9pt'})
        self._aw_fft.getAxis('bottom').setStyle(tickFont=QFont("Consolas", 8))
        self._aw_fft.getAxis('left').setStyle(tickFont=QFont("Consolas", 8))
        self._aw_fft.getAxis('bottom').setPen(pg.mkPen(BORDER_COLOR))
        self._aw_fft.getAxis('left').setPen(pg.mkPen(BORDER_COLOR))

        self.acurve_force = self._aw_force.plot(pen=pg.mkPen(ACCENT_CYAN,  width=1.5))
        self.acurve_roll  = self._aw_roll.plot( pen=pg.mkPen(ACCENT_GOLD,  width=1.5))
        self.acurve_pitch = self._aw_pitch.plot(pen=pg.mkPen("#c792ea", width=1.5))

        # Kurva FFT: spektrum (fill) + garis dominan
        self.acurve_fft   = self._aw_fft.plot(
            pen=pg.mkPen(ACCENT_CYAN, width=1.2),
            fillLevel=0, brush=pg.mkBrush(57, 208, 245, 40),
        )
        self._fft_peak_line = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(ACCENT_RED, width=1.5, style=Qt.DashLine),
        )
        self._aw_fft.addItem(self._fft_peak_line)
        self._fft_peak_line.setVisible(False)

        # scatter markers ekstremum
        self._markers: list = []

        rlay.addWidget(self.plot_widget)
        root.addWidget(right, stretch=1)

    # ─── muat CSV ──────────────────────────────────────────
    def load_csv(self):
        """Pilih file CSV log, parse metadata/data, hitung statistik dan FFT."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih file CSV Log", data_log_dir(),
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        self._csv_path = path
        try:
            self._parse_csv(path)
        except Exception as e:
            QMessageBox.critical(self, "Gagal Muat", str(e))
            self.status_message.emit("err", f"Gagal muat: {e}")
            return
        self._update_plot()
        self._compute_stats()
        self._compute_fft()
        self._update_stat_panel()
        self._update_fft_panel()
        self._update_fft_plot()
        self.btn_save_stat.setEnabled(True)
        self.lbl_file.setText(os.path.basename(path))
        self.status_message.emit("ok", f"File dimuat: {os.path.basename(path)}")

    def _parse_csv(self, path: str):
        """Baca metadata baris ``key: value`` lalu baris data empat kolom numerik."""
        self._meta  = {}
        self._t_data, self._f_data, self._r_data, self._p_data = [], [], [], []
        header_found = False
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if not header_found:
                    # cek metadata key:value
                    if ":" in line and not line.startswith(CSV_HEADER.split(",")[0]):
                        k, _, v = line.partition(":")
                        self._meta[k.strip()] = v.strip()
                    if line == CSV_HEADER:
                        header_found = True
                    continue
                parts = line.split(",")
                if len(parts) != 4:
                    continue
                try:
                    ts, fv, rv, pv = [float(x) for x in parts]
                    self._t_data.append(ts)
                    self._f_data.append(fv)
                    self._r_data.append(rv)
                    self._p_data.append(pv)
                except ValueError:
                    continue

        if not header_found:
            raise ValueError("Header CSV tidak ditemukan. Pastikan file berasal dari tab Live.")
        if not self._t_data:
            raise ValueError("Tidak ada data numerik dalam file.")

        # metadata panel
        self.lbl_meta_nama.setText(self._meta.get("Nama Perenang", "—"))
        self.lbl_meta_gaya.setText(self._meta.get("Gaya Renang", "—"))
        self.lbl_meta_time.setText(self._meta.get("Time", "—"))
        self.lbl_meta_pts.setText(str(len(self._t_data)))

    # ─── plot analisa ──────────────────────────────────────
    def _update_plot(self):
        """Gambar ulang kurva waktu dan scatter marker min/max per kanal."""
        # hapus marker lama
        for m in self._markers:
            m.getViewBox().removeItem(m) if m.scene() else None
        self._markers.clear()

        self.acurve_force.setData(self._t_data, self._f_data)
        self.acurve_roll.setData( self._t_data, self._r_data)
        self.acurve_pitch.setData(self._t_data, self._p_data)

        # ─── tambah marker min/max ──────────────────────────
        def add_marker(pw, t_list, v_list, color):
            if not v_list:
                return
            i_max = v_list.index(max(v_list))
            i_min = v_list.index(min(v_list))
            for i, sym in [(i_max, 't'), (i_min, 'd')]:
                sc = pg.ScatterPlotItem(
                    [t_list[i]], [v_list[i]],
                    symbol=sym, size=10,
                    pen=pg.mkPen('w', width=1),
                    brush=pg.mkBrush(color),
                )
                pw.addItem(sc)
                self._markers.append(sc)

        add_marker(self._aw_force, self._t_data, self._f_data, ACCENT_CYAN)
        add_marker(self._aw_roll,  self._t_data, self._r_data, ACCENT_GOLD)
        add_marker(self._aw_pitch, self._t_data, self._p_data, "#c792ea")

    # ─── statistik ─────────────────────────────────────────
    def _compute_stats(self):
        """Hitung min, max, mean untuk force, roll, dan pitch beserta waktu kejadian."""
        e = {}
        def _stats(vals, times, prefix):
            if not vals:
                return
            mx = max(vals); mn = min(vals)
            i_max = vals.index(mx); i_min = vals.index(mn)
            e[f"{prefix}_max"]       = mx
            e[f"{prefix}_max_t"]     = times[i_max]
            e[f"{prefix}_min"]       = mn
            e[f"{prefix}_min_t"]     = times[i_min]
            e[f"{prefix}_mean"]      = sum(vals) / len(vals)

        _stats(self._f_data, self._t_data, "force")
        _stats(self._r_data, self._t_data, "roll")
        _stats(self._p_data, self._t_data, "pitch")
        self._extrema = e

    # ─── FFT ───────────────────────────────────────────────
    def _compute_fft(self):
        """Hitung FFT force (window Hanning): frekuensi dominan, SPM, RMS, bandwidth."""
        self._fft_result: dict = {}
        n = len(self._f_data)
        if n < 8:
            return

        f_arr = np.array(self._f_data, dtype=float)
        t_arr = np.array(self._t_data, dtype=float)

        # estimasi sample rate dari rata-rata interval waktu
        dt_arr = np.diff(t_arr)
        dt = float(np.median(dt_arr)) if len(dt_arr) > 0 else 1.0
        if dt <= 0:
            dt = 1.0
        fs = 1.0 / dt   # sample rate (Hz)

        # FFT dengan window Hanning untuk mengurangi spectral leakage
        window  = np.hanning(n)
        f_win   = (f_arr - np.mean(f_arr)) * window   # hilangkan DC offset
        fft_mag = np.abs(np.fft.rfft(f_win))
        freqs   = np.fft.rfftfreq(n, d=dt)

        # normalisasi amplitudo (2/N karena rfft, kecuali DC)
        amp = (2.0 / n) * fft_mag
        amp[0] = amp[0] / 2.0   # DC tidak dikali 2

        # cari frekuensi dominan (abaikan DC bin ke-0)
        if len(amp) > 1:
            idx_peak  = int(np.argmax(amp[1:]) + 1)
        else:
            idx_peak  = 0

        dom_freq = float(freqs[idx_peak])
        dom_amp  = float(amp[idx_peak])
        period   = (1.0 / dom_freq) if dom_freq > 0 else 0.0
        stroke_rate = dom_freq * 60.0    # stroke per menit (SPM)

        # bandwidth: setengah-kekuatan (-3 dB) di sekitar puncak
        half_pow = dom_amp / math.sqrt(2.0)
        left_idx  = idx_peak
        right_idx = idx_peak
        while left_idx > 1 and amp[left_idx] > half_pow:
            left_idx -= 1
        while right_idx < len(amp) - 1 and amp[right_idx] > half_pow:
            right_idx += 1
        bandwidth = float(freqs[right_idx] - freqs[left_idx])

        # RMS seluruh sinyal force
        rms = float(np.sqrt(np.mean(f_arr ** 2)))

        self._fft_result = {
            "freqs":       freqs,
            "amp":         amp,
            "dom_freq":    dom_freq,
            "dom_amp":     dom_amp,
            "period":      period,
            "stroke_rate": stroke_rate,
            "bandwidth":   bandwidth,
            "rms":         rms,
            "fs":          fs,
        }

    def _update_fft_panel(self):
        r = self._fft_result
        def _set(key, text):
            lbl = self._fft_labels.get(key)
            if lbl:
                lbl.setText(text)

        if not r:
            for lbl in self._fft_labels.values():
                lbl.setText("—")
            return

        _set("fft_dom_freq",    f"{r['dom_freq']:.4f} Hz")
        _set("fft_dom_amp",     f"{r['dom_amp']:.4f} Kg")
        _set("fft_period",      f"{r['period']:.3f} s")
        _set("fft_stroke_rate", f"{r['stroke_rate']:.2f} SPM")
        _set("fft_bandwidth",   f"{r['bandwidth']:.4f} Hz")
        _set("fft_rms",         f"{r['rms']:.4f} Kg")

    def _update_fft_plot(self):
        r = self._fft_result
        if not r or len(r.get("freqs", [])) == 0:
            self.acurve_fft.setData([], [])
            self._fft_peak_line.setVisible(False)
            return

        freqs = r["freqs"]
        amp   = r["amp"]

        # Batasi tampilan sampai 5 Hz (relevan untuk gerakan renang)
        max_disp_hz = min(5.0, float(freqs[-1]))
        mask = freqs <= max_disp_hz
        self.acurve_fft.setData(freqs[mask], amp[mask])

        # garis merah vertikal di frekuensi dominan
        dom_freq = r["dom_freq"]
        if 0 < dom_freq <= max_disp_hz:
            self._fft_peak_line.setValue(dom_freq)
            self._fft_peak_line.setVisible(True)

            # label teks di puncak
            for item in self._aw_fft.items[:]:
                if isinstance(item, pg.TextItem):
                    self._aw_fft.removeItem(item)
            txt = pg.TextItem(
                f"  {dom_freq:.3f} Hz\n  {r['stroke_rate']:.1f} SPM",
                color=ACCENT_RED,
                anchor=(0, 1),
            )
            txt.setFont(QFont("Consolas", 8))
            txt.setPos(dom_freq, float(amp[np.argmax(amp[1:]) + 1]))
            self._aw_fft.addItem(txt)
        else:
            self._fft_peak_line.setVisible(False)

    def _update_stat_panel(self):
        e = self._extrema
        for key, lbl in self._stat_labels.items():
            val = e.get(key)
            if val is None:
                lbl.setText("—")
            else:
                t = e.get(key.replace("_min","_min_t").replace("_max","_max_t").replace("_mean",""), None)
                suffix = f" @ {t:.2f}s" if t is not None and "mean" not in key else ""
                lbl.setText(f"{val:.3f}{suffix}")

    # ─── simpan statistik ──────────────────────────────────
    def save_statistics(self):
        """Ekspor ringkasan ekstremum + hasil FFT ke ``DataStatistik/<nama>_DataStaistik.csv``."""
        if not self._csv_path or not self._extrema:
            return
        ensure_dir(stat_log_dir())
        base = os.path.splitext(os.path.basename(self._csv_path))[0]
        out_path = os.path.join(stat_log_dir(), f"{base}_DataStaistik.csv")
        try:
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                f.write(f"Nama Perenang: {self._meta.get('Nama Perenang','')}\n")
                f.write(f"Gaya Renang: {self._meta.get('Gaya Renang','')}\n")
                f.write(f"Time: {self._meta.get('Time','')}\n")
                f.write(f"Source: {os.path.basename(self._csv_path)}\n")
                f.write(f"Tanggal Analisa: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("Metric,Value,Unit,TimeStamp(s)\n")
                rows = [
                    ("Force Min",       self._extrema.get("force_min"),  "Kg",  self._extrema.get("force_min_t")),
                    ("Force Max",       self._extrema.get("force_max"),  "Kg",  self._extrema.get("force_max_t")),
                    ("Force Mean",      self._extrema.get("force_mean"), "Kg",  None),
                    ("Roll Min",        self._extrema.get("roll_min"),   "Deg", self._extrema.get("roll_min_t")),
                    ("Roll Max",        self._extrema.get("roll_max"),   "Deg", self._extrema.get("roll_max_t")),
                    ("Roll Mean",       self._extrema.get("roll_mean"),  "Deg", None),
                    ("Pitch Min",       self._extrema.get("pitch_min"),  "Deg", self._extrema.get("pitch_min_t")),
                    ("Pitch Max",       self._extrema.get("pitch_max"),  "Deg", self._extrema.get("pitch_max_t")),
                    ("Pitch Mean",      self._extrema.get("pitch_mean"), "Deg", None),
                ]
                if self._fft_result:
                    r = self._fft_result
                    f.write("\n--- Analisa FFT Force ---\n")
                    fft_rows = [
                        ("FFT Freq Dominan",   r.get("dom_freq"),    "Hz",  None),
                        ("FFT Amplitudo Maks", r.get("dom_amp"),     "Kg",  None),
                        ("FFT Periode",        r.get("period"),      "s",   None),
                        ("FFT Stroke Rate",    r.get("stroke_rate"), "SPM", None),
                        ("FFT Bandwidth",      r.get("bandwidth"),   "Hz",  None),
                        ("FFT RMS Force",      r.get("rms"),         "Kg",  None),
                        ("FFT Sample Rate",    r.get("fs"),          "Hz",  None),
                    ]
                    rows = rows + fft_rows
                for metric, val, unit, t in rows:
                    v_str = f"{val:.4f}" if val is not None else ""
                    t_str = f"{t:.4f}"   if t   is not None else ""
                    f.write(f"{metric},{v_str},{unit},{t_str}\n")
        except OSError as e:
            QMessageBox.critical(self, "Gagal Simpan", str(e))
            self.status_message.emit("err", str(e))
            return
        QMessageBox.information(self, "Tersimpan", f"Statistik disimpan:\n{out_path}")
        self.status_message.emit("ok", f"Statistik → {out_path}")


# ═══════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    """Jendela utama: header (judul, baterai), tab Live/Analisa, status bar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.resize(1100, 720)
        self.setMinimumSize(800, 560)

        # ── header bar ──────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(46)
        header.setStyleSheet(f"background:{PANEL_BG}; border-bottom:1px solid {BORDER_COLOR};")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(14, 0, 14, 0)

        title_lbl = QLabel(f"<b style='color:{ACCENT_CYAN};font-size:14px;letter-spacing:2px;'>"
                           f"SWIMMER FORCE AND MOTION MONITORING</b>")
        title_lbl.setTextFormat(Qt.RichText)
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")

        self.battery_widget = BatteryWidget()

        hlay.addWidget(title_lbl)
        hlay.addStretch()
        hlay.addWidget(self.battery_widget)
        hlay.addSpacing(12)
        hlay.addWidget(ver_lbl)

        # ── tabs ────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tab_live    = LiveTab()
        self.tab_analisa = AnalisaTab()
        self.tabs.addTab(self.tab_live,    "  Live  ")
        self.tabs.addTab(self.tab_analisa, "  Analisa  ")

        # ── status bar ──────────────────────────────────────
        self.status_bar = StatusBar()

        # ── layout utama ────────────────────────────────────
        central = QWidget()
        clay = QVBoxLayout(central)
        clay.setContentsMargins(0, 0, 0, 0)
        clay.setSpacing(0)
        clay.addWidget(header)
        clay.addWidget(self.tabs)
        clay.addWidget(self.status_bar)
        self.setCentralWidget(central)

        # ── sinyal status ───────────────────────────────────
        self.tab_live.status_message.connect(self._on_status)
        self.tab_analisa.status_message.connect(self._on_status)
        self.tab_live.battery_update.connect(self.battery_widget.set_level)

    def _on_status(self, level: str, msg: str):
        fn = getattr(self.status_bar, level, self.status_bar.info)
        fn(msg)

    def closeEvent(self, event):
        self.tab_live.disconnect_serial()
        super().closeEvent(event)


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════
def main():
    """Inisialisasi Qt, tema gelap, folder output, dan jalankan event loop."""
    # Pastikan folder output ada
    ensure_dir(data_log_dir())
    ensure_dir(stat_log_dir())

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Palette gelap
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(DARK_BG))
    palette.setColor(QPalette.WindowText,      QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Base,            QColor(PANEL_BG))
    palette.setColor(QPalette.AlternateBase,   QColor(DARK_BG))
    palette.setColor(QPalette.ToolTipBase,     QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ToolTipText,     QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Text,            QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Button,          QColor(PANEL_BG))
    palette.setColor(QPalette.ButtonText,      QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.BrightText,      QColor(ACCENT_CYAN))
    palette.setColor(QPalette.Link,            QColor(ACCENT_BLUE))
    palette.setColor(QPalette.Highlight,       QColor(ACCENT_BLUE))
    palette.setColor(QPalette.HighlightedText, QColor(TEXT_PRIMARY))
    app.setPalette(palette)
    app.setStyleSheet(GLOBAL_QSS)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

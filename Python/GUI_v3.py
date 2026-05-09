"""
GUI_v2.0.py — NI DAQ Monitor for Touchpad Swimmer
===================================================
Aplikasi desktop real-time untuk akuisisi dan analisis data tekanan
dari dua sensor touchpad (Pad 1 / Pad 2) menggunakan perangkat
NI Data Acquisition (NI DAQ).

Fitur Utama
-----------
* Akuisisi kontinu dua channel analog (AI0, AI1) via NI-DAQmx.
* Visualisasi real-time dengan pyqtgraph (10 detik jendela tampil, ~10 FPS).
* Deteksi sentuhan otomatis per channel menggunakan Schmitt trigger
  (threshold + hysteresis) dengan anti-debounce hold-time.
* Tabel hasil deteksi (10 baris per pad) dengan auto-scroll.
* Export log mentah ke CSV (semua sampel) dan tabel ringkas ke CSV.
* Konfigurasi parameter disimpan/dimuat dari config.json secara otomatis.
* Tema Light/Dark yang dapat diubah kapan saja.

Struktur Kelas
--------------
ChannelDetector  — State machine Schmitt trigger per channel.
CsvWriter        — Penulis CSV asinkron berbasis queue/thread.
DaqWorker        — Thread akuisisi NI-DAQmx (non-blocking terhadap GUI).
ParameterDialog  — Dialog modal untuk konfigurasi parameter & detektor.
MainWindow       — Jendela utama aplikasi (PySide6 QMainWindow).

Dependensi
----------
Python  >= 3.11
PySide6 >= 6.5
pyqtgraph >= 0.13
numpy
nidaqmx  (NI-DAQmx Python driver)

Cara Menjalankan
----------------
    python GUI_v2.0.py

Penulis  : Tim Pengujian Touchpad Swimmer
Versi    : 2.0
"""

import collections
import csv
import datetime as dt
import json
import pathlib
import queue
import sys
import threading
from typing import Literal

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QFont, QPalette, QColor, QBrush
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QButtonGroup,
    QHeaderView,
    QRadioButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration
from nidaqmx.errors import DaqFunctionNotSupportedError

# ─── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_CH0 = "Dev2/ai0"
DEFAULT_CH1 = "Dev2/ai1"
DEFAULT_RATE = 500.0
DEFAULT_BUFFER = 100_000
DEFAULT_SAMPLES_PER_LOOP = 50
DEFAULT_TERMINAL = "DIFF"
DEFAULT_TS_SET = "Manual (A)"
DEFAULT_TS_DISPLAY = "Relative"

PLOT_WINDOW_SEC = 10.0   # detik data yang ditampilkan di chart
PLOT_REFRESH_MS = 100    # refresh rate chart (ms) → ~10 FPS

TERMINAL_MAP: dict[str, TerminalConfiguration] = {
    "DIFF": TerminalConfiguration.DIFF,
    "RSE": TerminalConfiguration.RSE,
    "NRSE": TerminalConfiguration.NRSE,
}

# (min_val, max_val) dalam Volt untuk add_ai_voltage_chan
# Differential mode: 8 pilihan range
VOLTAGE_RANGE_DIFF: dict[str, tuple[float, float]] = {
    "±1 V":    (-1.0,    1.0),
    "±1.25 V": (-1.25,   1.25),
    "±2 V":    (-2.0,    2.0),
    "±2.5 V":  (-2.5,    2.5),
    "±4 V":    (-4.0,    4.0),
    "±5 V":    (-5.0,    5.0),
    "±10 V":   (-10.0,  10.0),
    "±20 V":   (-20.0,  20.0),
}
# Single-Ended (RSE / NRSE): hanya satu pilihan
VOLTAGE_RANGE_SE: dict[str, tuple[float, float]] = {
    "±10 V": (-10.0, 10.0),
}
VOLTAGE_RANGE_MAP = VOLTAGE_RANGE_DIFF  # alias untuk DaqWorker lookup gabungan
DEFAULT_VOLTAGE_RANGE_DIFF = "±10 V"
DEFAULT_VOLTAGE_RANGE_SE   = "±10 V"

# ─── Theme definitions ────────────────────────────────────────────────────────
# Setiap theme menyimpan: warna plot background, warna foreground (axis/text),
# warna kurva AI0 & AI1, stylesheet Qt untuk widget.
def _btn_ss(bg: str, hover: str, checked: str = "") -> str:
    """Buat stylesheet ringkas untuk satu QPushButton."""
    base = (
        f"QPushButton {{ background:{bg}; color:#ffffff; border:none;"
        f" border-radius:4px; padding:4px 8px; }}"
        f" QPushButton:hover {{ background:{hover}; }}"
    )
    if checked:
        base += f" QPushButton:checked {{ background:{checked}; color:#ffffff; }}"
    return base


_THEMES: dict[str, dict] = {
    "Light": {
        "pg_bg": "w",
        "pg_fg": "k",
        "curve_ai0": (30, 144, 255),
        "curve_ai1": (220, 80, 0),
        "qt_stylesheet": "",
        "btn_styles": {
            "start":     _btn_ss("#388e3c", "#43a047", "#b71c1c"),
            "save":      _btn_ss("#1976d2", "#1e88e5"),
            "set_param": _btn_ss("#455a64", "#546e7a"),
            "theme":     _btn_ss("#512da8", "#5e35b1"),
        },
    },
    "Dark": {
        "pg_bg": "#1e1e1e",
        "pg_fg": "#cccccc",
        "curve_ai0": (100, 180, 255),
        "curve_ai1": (255, 140, 60),
        "qt_stylesheet": """
            QWidget          { background-color: #2b2b2b; color: #dddddd; }
            QGroupBox        { border: 1px solid #555; border-radius: 4px;
                               margin-top: 6px; color: #cccccc; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px;
                               padding: 0 4px; }
            QLineEdit        { background: #3c3c3c; border: 1px solid #555;
                               border-radius: 3px; color: #dddddd; padding: 2px 4px; }
            QComboBox        { background: #3c3c3c; border: 1px solid #555;
                               border-radius: 3px; color: #dddddd; padding: 2px 4px; }
            QComboBox QAbstractItemView { background: #3c3c3c; color: #dddddd;
                                          selection-background-color: #555; }
            QPushButton      { background: #3c3f41; border: 1px solid #666;
                               border-radius: 4px; color: #dddddd; padding: 4px 8px; }
            QPushButton:hover   { background: #4c5052; }
            QLabel           { color: #cccccc; }
        """,
        "btn_styles": {
            "start":     _btn_ss("#2e7d32", "#388e3c", "#b71c1c"),
            "save":      _btn_ss("#1565c0", "#1976d2"),
            "set_param": _btn_ss("#37474f", "#455a64"),
            "theme":     _btn_ss("#4527a0", "#512da8"),
        },
    },
}


DEFAULT_CSV_PREFIX = "Swimming"
DEFAULT_CSV_FOLDER = str(pathlib.Path(__file__).parent / "DataLog")
DEFAULT_TABLE_FOLDER = str(pathlib.Path(__file__).parent / "DataTable")

N_COLLECT = 50          # jumlah sampel yang dirata-rata setelah trigger
TABLE_ROWS = 10         # baris data pada tabel
DEFAULT_HOLD_TIME = 10.0  # detik minimum di state HOLD sebelum bisa re-arm

DEFAULT_THRESHOLD  = "0.05"
DEFAULT_HYSTERESIS = "0.005"
DEFAULT_SCALE      = "1.00"

CONFIG_PATH = pathlib.Path(__file__).parent / "config.json"

# Jarak valid per gaya renang (sesuai standar kompetisi)
STROKE_DISTANCES: dict[str, list[str]] = {
    "Bebas":      ["50m", "100m", "200m", "400m", "800m", "1500m"],
    "Punggung":   ["50m", "100m", "200m"],
    "Dada":       ["50m", "100m", "200m"],
    "Kupu-kupu":  ["50m", "100m", "200m"],
    "Gaya Ganti": ["200m", "400m"],
}


# ─── Config persistence ───────────────────────────────────────────────────────
def _load_config() -> dict | None:
    """Baca config.json. Return None jika file tidak ada atau format salah."""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_config(cfg: dict) -> None:
    """Tulis dict parameter ke config.json."""
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ─── Channel Detector (Schmitt Trigger) ──────────────────────────────────────
class ChannelDetector:
    """Deteksi rising-edge dengan hysteresis (Schmitt trigger) + hold time.

    State machine:
        ARMED      → sinyal naik ke >= lower_trip               → COLLECTING
        COLLECTING → kumpulkan n_collect sampel                 → HOLD
        HOLD       → hold_time selesai AND sinyal < lower_trip  → ARMED

    Hold time berfungsi sebagai anti-debounce: meskipun sinyal
    sesaat turun/noise selama hold_time, sistem tidak re-arm
    hingga hold_time habis DAN sinyal benar-benar turun.
    """

    def __init__(
        self,
        threshold: float,
        hysteresis: float,
        scale: float,
        n_collect: int = N_COLLECT,
        hold_time: float = DEFAULT_HOLD_TIME,
    ) -> None:
        self.threshold = threshold
        self.hysteresis = hysteresis
        self.scale = scale
        self.n_collect = n_collect
        self.hold_time = hold_time
        self._state = "ARMED"
        self._buf: list[float] = []
        self._t0 = 0.0
        self._t_hold_start = 0.0  # timestamp saat masuk HOLD

    @property
    def lower_trip(self) -> float:
        return self.threshold - self.hysteresis

    def reset(self) -> None:
        self._state = "ARMED"
        self._buf = []
        self._t0 = 0.0
        self._t_hold_start = 0.0

    def process(self, value: float, timestamp: float) -> tuple[float, float] | None:
        """Proses satu sampel.

        Returns (t0_s, pressure_scaled) saat deteksi selesai, else None.
        """
        if self._state == "ARMED":
            if value >= self.lower_trip:
                self._state = "COLLECTING"
                self._t0 = timestamp
                self._buf = [value]

        elif self._state == "COLLECTING":
            self._buf.append(value)
            if len(self._buf) >= self.n_collect:
                pressure = (sum(self._buf) / self.n_collect) * self.scale
                self._t_hold_start = timestamp
                self._state = "HOLD"
                self._buf = []
                return (self._t0, pressure)

        elif self._state == "HOLD":
            hold_elapsed = timestamp - self._t_hold_start
            if hold_elapsed >= self.hold_time and value < self.lower_trip:
                self._state = "ARMED"

        return None


# ─── CSV Writer ───────────────────────────────────────────────────────────────
class CsvWriter:
    """Menulis data ke CSV di background thread menggunakan queue.

    Alur:
      write_chunk() → queue.put() (non-blocking, O(1) di GUI/DAQ thread)
      _worker_loop() → queue.get() → tulis baris CSV (di thread sendiri)
    """

    _SENTINEL = None  # sinyal untuk menghentikan worker loop

    def __init__(self, filepath: pathlib.Path, dt_sample: float) -> None:
        self._filepath = filepath
        self._dt_sample = dt_sample
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self) -> None:
        with self._filepath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_s", "ai0_V", "ai1_V"])
            while True:
                item = self._queue.get()
                if item is self._SENTINEL:
                    break
                ai0_chunk, ai1_chunk, offset = item
                for i in range(len(ai0_chunk)):
                    ts = (offset + i) * self._dt_sample
                    writer.writerow([f"{ts:.6f}", ai0_chunk[i], ai1_chunk[i]])
                f.flush()

    def write_chunk(
        self, ai0: list, ai1: list, offset: int
    ) -> None:
        self._queue.put((ai0, ai1, offset))

    def close(self) -> None:
        """Flush semua data yang tersisa lalu tutup file."""
        self._queue.put(self._SENTINEL)
        self._thread.join(timeout=10)

    @property
    def filepath(self) -> pathlib.Path:
        return self._filepath


# ─── Parameter Dialog ─────────────────────────────────────────────────────────
class ParameterDialog(QDialog):
    """Modal dialog untuk mengubah parameter akuisisi dan detektor.

    Behaviour:
      Set As Default   → simpan nilai dialog ke config.json + apply ke MainWindow
      Reset to Saved   → isi dialog dari config.json (tidak auto-apply)
      Reset to Factory → isi dialog dari DEFAULT_* hardcoded (tidak auto-apply)
      Apply            → terapkan nilai dialog ke MainWindow, dialog tetap terbuka
      Cancel / X       → tutup tanpa mengubah apapun di MainWindow
    """

    def __init__(self, main_window: "MainWindow", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set Parameter")
        self.setModal(True)
        self.setMinimumWidth(460)
        self._mw = main_window

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(self._build_param_group())
        layout.addWidget(self._build_detector_group())
        layout.addLayout(self._build_button_row())

        self._load_from_main()

    # ── Parameter Setting group ───────────────────────────────────────────────
    def _build_param_group(self) -> QGroupBox:
        group = QGroupBox("Parameter Setting")
        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(10, 14, 10, 10)

        self._d_ch0    = QLineEdit()
        self._d_ch1    = QLineEdit()
        self._d_rate   = QLineEdit()
        self._d_buffer = QLineEdit()
        self._d_spl    = QLineEdit()

        self._d_terminal = QComboBox()
        self._d_terminal.addItems(["DIFF", "RSE", "NRSE"])
        self._d_terminal.currentTextChanged.connect(self._on_terminal_changed)

        self._d_vrange = QComboBox()
        self._d_vrange.addItems(list(VOLTAGE_RANGE_DIFF.keys()))

        self._d_ts_set = QComboBox()
        self._d_ts_set.addItems(["Manual (A)", "Waveform (B)"])

        self._d_ts_display = QComboBox()
        self._d_ts_display.addItems(["Relative", "ISO"])

        form.addRow("Device Ch 0:",       self._d_ch0)
        form.addRow("Device Ch 1:",       self._d_ch1)
        form.addRow("Rate (Hz):",         self._d_rate)
        form.addRow("Buffer Size:",       self._d_buffer)
        form.addRow("Samples / Loop:",    self._d_spl)
        form.addRow("Terminal:",          self._d_terminal)
        form.addRow("Input Range:",       self._d_vrange)
        form.addRow("Timestamp Set:",     self._d_ts_set)
        form.addRow("Timestamp Display:", self._d_ts_display)

        group.setLayout(form)
        return group

    # ── Detector Parameters group ─────────────────────────────────────────────
    def _build_detector_group(self) -> QGroupBox:
        group = QGroupBox("Detector Parameters")
        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(10, 14, 10, 10)

        dbl = QDoubleValidator()
        dbl.setNotation(QDoubleValidator.Notation.StandardNotation)
        small = QFont()
        small.setPointSize(8)

        col_headers = [
            "Threshold\n(Volt)", "Hysteresis\n(Volt)",
            "Scale\n(Kg/Volt)", "Delay Time\n(s)",
        ]
        for col, text in enumerate(col_headers):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(small)
            grid.addWidget(lbl, 0, col + 1)

        self._d_thresh: list[QLineEdit] = []
        self._d_hyst:   list[QLineEdit] = []
        self._d_scale:  list[QLineEdit] = []
        self._d_hold:   list[QLineEdit] = []

        for dev_idx in range(2):
            row = dev_idx + 1
            dev_lbl = QLabel(f"Dev. {dev_idx}")
            dev_lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            grid.addWidget(dev_lbl, row, 0)

            def _inp() -> QLineEdit:
                le = QLineEdit()
                le.setValidator(dbl)
                le.setAlignment(Qt.AlignmentFlag.AlignCenter)
                return le

            t, h, s, d = _inp(), _inp(), _inp(), _inp()
            self._d_thresh.append(t)
            self._d_hyst.append(h)
            self._d_scale.append(s)
            self._d_hold.append(d)

            grid.addWidget(t, row, 1)
            grid.addWidget(h, row, 2)
            grid.addWidget(s, row, 3)
            grid.addWidget(d, row, 4)

        grid.setColumnStretch(0, 0)
        for c in range(1, 5):
            grid.setColumnStretch(c, 1)

        group.setLayout(grid)
        return group

    # ── Button row ────────────────────────────────────────────────────────────
    def _build_button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self._btn_set_as_default = QPushButton("💾  Set As Default")
        self._btn_set_as_default.setMinimumHeight(32)
        self._btn_set_as_default.clicked.connect(self._on_set_as_default)

        self._btn_reset_saved = QPushButton("↩  Reset to Saved")
        self._btn_reset_saved.setMinimumHeight(32)
        self._btn_reset_saved.setEnabled(CONFIG_PATH.exists())
        self._btn_reset_saved.clicked.connect(self._on_reset_to_saved)

        btn_reset_factory = QPushButton("↺  Reset to Factory")
        btn_reset_factory.setMinimumHeight(32)
        btn_reset_factory.clicked.connect(self._on_reset_to_factory)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumHeight(32)
        btn_cancel.clicked.connect(self.reject)

        btn_apply = QPushButton("Apply")
        btn_apply.setMinimumHeight(32)
        bold = QFont()
        bold.setBold(True)
        btn_apply.setFont(bold)
        btn_apply.clicked.connect(self._on_apply)

        row.addWidget(self._btn_set_as_default)
        row.addWidget(self._btn_reset_saved)
        row.addWidget(btn_reset_factory)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(btn_apply)
        return row

    # ── Slots ─────────────────────────────────────────────────────────────────
    def _on_terminal_changed(self, text: str) -> None:
        if text == "DIFF":
            items = list(VOLTAGE_RANGE_DIFF.keys())
            default = DEFAULT_VOLTAGE_RANGE_DIFF
        else:
            items = list(VOLTAGE_RANGE_SE.keys())
            default = DEFAULT_VOLTAGE_RANGE_SE
        self._d_vrange.blockSignals(True)
        self._d_vrange.clear()
        self._d_vrange.addItems(items)
        self._d_vrange.setCurrentText(default)
        self._d_vrange.blockSignals(False)

    def _load_from_main(self) -> None:
        mw = self._mw
        self._d_ch0.setText(mw._inp_ch0.text())
        self._d_ch1.setText(mw._inp_ch1.text())
        self._d_rate.setText(mw._inp_rate.text())
        self._d_buffer.setText(mw._inp_buffer.text())
        self._d_spl.setText(mw._inp_spl.text())

        self._d_terminal.blockSignals(True)
        self._d_terminal.setCurrentText(mw._dd_terminal.currentText())
        self._d_terminal.blockSignals(False)
        self._on_terminal_changed(mw._dd_terminal.currentText())
        self._d_vrange.setCurrentText(mw._dd_vrange.currentText())

        self._d_ts_set.setCurrentText(mw._dd_ts_set.currentText())
        self._d_ts_display.setCurrentText(mw._dd_ts_display.currentText())

        self._d_thresh[0].setText(mw._inp_thresh0.text())
        self._d_hyst[0].setText(mw._inp_hyst0.text())
        self._d_scale[0].setText(mw._inp_scale0.text())
        self._d_hold[0].setText(mw._inp_hold0.text())

        self._d_thresh[1].setText(mw._inp_thresh1.text())
        self._d_hyst[1].setText(mw._inp_hyst1.text())
        self._d_scale[1].setText(mw._inp_scale1.text())
        self._d_hold[1].setText(mw._inp_hold1.text())

    def _build_config_dict(self) -> dict:
        """Bangun dict dari nilai-nilai dialog saat ini."""
        return {
            "ch0":        self._d_ch0.text(),
            "ch1":        self._d_ch1.text(),
            "rate":       self._d_rate.text(),
            "buffer":     self._d_buffer.text(),
            "spl":        self._d_spl.text(),
            "terminal":   self._d_terminal.currentText(),
            "vrange":     self._d_vrange.currentText(),
            "ts_set":     self._d_ts_set.currentText(),
            "ts_display": self._d_ts_display.currentText(),
            "dev0": {
                "threshold":  self._d_thresh[0].text(),
                "hysteresis": self._d_hyst[0].text(),
                "scale":      self._d_scale[0].text(),
                "hold":       self._d_hold[0].text(),
            },
            "dev1": {
                "threshold":  self._d_thresh[1].text(),
                "hysteresis": self._d_hyst[1].text(),
                "scale":      self._d_scale[1].text(),
                "hold":       self._d_hold[1].text(),
            },
        }

    def _fill_dialog_from_config(self, cfg: dict) -> None:
        """Isi semua field dialog dari dict config."""
        self._d_ch0.setText(cfg.get("ch0", DEFAULT_CH0))
        self._d_ch1.setText(cfg.get("ch1", DEFAULT_CH1))
        self._d_rate.setText(cfg.get("rate", str(DEFAULT_RATE)))
        self._d_buffer.setText(cfg.get("buffer", str(DEFAULT_BUFFER)))
        self._d_spl.setText(cfg.get("spl", str(DEFAULT_SAMPLES_PER_LOOP)))
        self._d_terminal.blockSignals(True)
        self._d_terminal.setCurrentText(cfg.get("terminal", DEFAULT_TERMINAL))
        self._d_terminal.blockSignals(False)
        self._on_terminal_changed(cfg.get("terminal", DEFAULT_TERMINAL))
        self._d_vrange.setCurrentText(cfg.get("vrange", DEFAULT_VOLTAGE_RANGE_DIFF))
        self._d_ts_set.setCurrentText(cfg.get("ts_set", DEFAULT_TS_SET))
        self._d_ts_display.setCurrentText(cfg.get("ts_display", DEFAULT_TS_DISPLAY))
        d0 = cfg.get("dev0", {})
        self._d_thresh[0].setText(d0.get("threshold",  DEFAULT_THRESHOLD))
        self._d_hyst[0].setText(d0.get("hysteresis",   DEFAULT_HYSTERESIS))
        self._d_scale[0].setText(d0.get("scale",       DEFAULT_SCALE))
        self._d_hold[0].setText(d0.get("hold",         str(DEFAULT_HOLD_TIME)))
        d1 = cfg.get("dev1", {})
        self._d_thresh[1].setText(d1.get("threshold",  DEFAULT_THRESHOLD))
        self._d_hyst[1].setText(d1.get("hysteresis",   DEFAULT_HYSTERESIS))
        self._d_scale[1].setText(d1.get("scale",       DEFAULT_SCALE))
        self._d_hold[1].setText(d1.get("hold",         str(DEFAULT_HOLD_TIME)))

    def _apply_to_main(self) -> None:
        mw = self._mw
        mw._inp_ch0.setText(self._d_ch0.text())
        mw._inp_ch1.setText(self._d_ch1.text())
        mw._inp_rate.setText(self._d_rate.text())
        mw._inp_buffer.setText(self._d_buffer.text())
        mw._inp_spl.setText(self._d_spl.text())
        # Set terminal dahulu agar _on_terminal_changed memperbarui opsi vrange di main
        mw._dd_terminal.setCurrentText(self._d_terminal.currentText())
        mw._dd_vrange.setCurrentText(self._d_vrange.currentText())
        mw._dd_ts_set.setCurrentText(self._d_ts_set.currentText())
        mw._dd_ts_display.setCurrentText(self._d_ts_display.currentText())
        mw._inp_thresh0.setText(self._d_thresh[0].text())
        mw._inp_hyst0.setText(self._d_hyst[0].text())
        mw._inp_scale0.setText(self._d_scale[0].text())
        mw._inp_hold0.setText(self._d_hold[0].text())
        mw._inp_thresh1.setText(self._d_thresh[1].text())
        mw._inp_hyst1.setText(self._d_hyst[1].text())
        mw._inp_scale1.setText(self._d_scale[1].text())
        mw._inp_hold1.setText(self._d_hold[1].text())

    def _on_set_as_default(self) -> None:
        """Simpan nilai dialog ke config.json lalu apply ke MainWindow."""
        cfg = self._build_config_dict()
        try:
            _save_config(cfg)
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Gagal menyimpan config:\n{exc}")
            return
        self._apply_to_main()
        self._btn_reset_saved.setEnabled(True)
        QMessageBox.information(self, "Tersimpan", "Parameter berhasil disimpan sebagai default.")

    def _on_reset_to_saved(self) -> None:
        """Isi dialog dari config.json (tidak auto-apply ke MainWindow)."""
        cfg = _load_config()
        if cfg is None:
            QMessageBox.warning(self, "Tidak Ada", "File config.json belum tersedia.")
            return
        self._fill_dialog_from_config(cfg)

    def _on_reset_to_factory(self) -> None:
        """Isi dialog dari nilai DEFAULT_* hardcoded (tidak auto-apply ke MainWindow)."""
        factory: dict = {
            "ch0": DEFAULT_CH0, "ch1": DEFAULT_CH1,
            "rate": str(DEFAULT_RATE), "buffer": str(DEFAULT_BUFFER),
            "spl": str(DEFAULT_SAMPLES_PER_LOOP),
            "terminal": DEFAULT_TERMINAL, "vrange": DEFAULT_VOLTAGE_RANGE_DIFF,
            "ts_set": DEFAULT_TS_SET, "ts_display": DEFAULT_TS_DISPLAY,
            "dev0": {"threshold": DEFAULT_THRESHOLD, "hysteresis": DEFAULT_HYSTERESIS,
                     "scale": DEFAULT_SCALE, "hold": str(DEFAULT_HOLD_TIME)},
            "dev1": {"threshold": DEFAULT_THRESHOLD, "hysteresis": DEFAULT_HYSTERESIS,
                     "scale": DEFAULT_SCALE, "hold": str(DEFAULT_HOLD_TIME)},
        }
        self._fill_dialog_from_config(factory)

    def _on_apply(self) -> None:
        self._apply_to_main()


# ─── DAQ Worker Thread ────────────────────────────────────────────────────────
class DaqWorker(QThread):
    """Thread akuisisi data dari NI DAQ agar GUI tidak freeze.

    Menjalankan loop pembacaan nidaqmx di QThread terpisah dan mengirim
    data ke GUI melalui Qt signal ``data_ready``.

    Signals
    -------
    data_ready(ai0, ai1, offset)
        Dipancarkan setiap loop baca selesai.
        ai0/ai1: list float (Volt), offset: indeks sampel awal.
    error_occurred(msg)
        Dipancarkan jika terjadi exception pada NI-DAQmx task.
    warning_occurred(msg)
        Dipancarkan jika read_waveform tidak didukung (fallback ke read()).

    Parameters
    ----------
    ch0, ch1 : str
        Nama channel NI DAQ, mis. "Dev2/ai0".
    rate : float
        Sample rate dalam Hz.
    buffer_size : int
        Ukuran buffer hardware (samples per channel).
    samples_per_loop : int
        Jumlah sampel yang dibaca per iterasi loop.
    terminal_config : TerminalConfiguration
        Konfigurasi terminal (DIFF / RSE / NRSE).
    read_mode : "A" | "B"
        "A" = task.read() manual, "B" = task.read_waveform() (butuh driver baru).
    min_val, max_val : float
        Rentang tegangan input (Volt).
    """

    data_ready = Signal(list, list, int)   # ai0_chunk, ai1_chunk, sample_offset
    error_occurred = Signal(str)
    warning_occurred = Signal(str)

    def __init__(
        self,
        ch0: str,
        ch1: str,
        rate: float,
        buffer_size: int,
        samples_per_loop: int,
        terminal_config: TerminalConfiguration,
        read_mode: Literal["A", "B"],
        min_val: float = -10.0,
        max_val: float = 10.0,
    ) -> None:
        super().__init__()
        self.ch0 = ch0
        self.ch1 = ch1
        self.rate = rate
        self.buffer_size = buffer_size
        self.samples_per_loop = samples_per_loop
        self.terminal_config = terminal_config
        self.read_mode = read_mode
        self.min_val = min_val
        self.max_val = max_val
        self._running = False

    def run(self) -> None:
        """Jalankan loop akuisisi. Dipanggil otomatis oleh QThread.start()."""
        self._running = True
        sample_offset = 0
        use_waveform = self.read_mode == "B"
        fallback_warned = False

        try:
            with nidaqmx.Task() as task:
                for ch in (self.ch0, self.ch1):
                    task.ai_channels.add_ai_voltage_chan(
                        ch,
                        terminal_config=self.terminal_config,
                        min_val=self.min_val,
                        max_val=self.max_val,
                    )
                task.timing.cfg_samp_clk_timing(
                    rate=self.rate,
                    sample_mode=AcquisitionType.CONTINUOUS,
                    samps_per_chan=self.buffer_size,
                )
                task.start()

                while self._running:
                    if self.read_mode == "A" or not use_waveform:
                        raw = task.read(
                            number_of_samples_per_channel=self.samples_per_loop
                        )
                        ai0 = list(raw[0])
                        ai1 = list(raw[1])
                        self.data_ready.emit(ai0, ai1, sample_offset)
                        sample_offset += len(ai0)

                    elif use_waveform:
                        try:
                            wfms = task.read_waveform(
                                number_of_samples_per_channel=self.samples_per_loop
                            )
                            y0 = [float(x) for x in wfms[0].scaled_data]
                            y1 = [float(x) for x in wfms[1].scaled_data]
                            self.data_ready.emit(y0, y1, sample_offset)
                            sample_offset += len(y0)
                        except DaqFunctionNotSupportedError:
                            if not fallback_warned:
                                self.warning_occurred.emit(
                                    "read_waveform tidak didukung driver ini. "
                                    "Fallback ke read() Manual. "
                                    "Upgrade NI-DAQmx: ni.com/downloads"
                                )
                                fallback_warned = True
                            use_waveform = False

                task.stop()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def stop(self) -> None:
        """Minta loop akuisisi berhenti pada iterasi berikutnya."""
        self._running = False


# ─── Main Window ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    """Jendela utama aplikasi NI DAQ Monitor.

    Layout terdiri dari dua panel:
    - Tengah : dua PlotWidget real-time (Channel AI0 dan AI1).
    - Kanan  : kontrol CSV export, tombol Start/Stop, tabel hasil deteksi,
               dan tombol utilitas (Set Parameter, tema).

    Alur data
    ---------
    DaqWorker.data_ready → _on_data_ready()
        → buffer deque (plot) + ChannelDetector (deteksi) + CsvWriter (log)
    QTimer (100 ms) → _refresh_plot()
        → update kurva pyqtgraph dari buffer deque
    ChannelDetector.process() → _append_table_row()
        → tulis hasil deteksi ke QTableWidget
    """

    def __init__(self) -> None:
        """Inisialisasi MainWindow: buat semua widget dan load config.json."""
        super().__init__()
        self.setWindowTitle("Swimmer Monitor")
        self.resize(1280, 640)

        self._worker: DaqWorker | None = None
        self._csv_writer: CsvWriter | None = None
        self._is_running = False
        self._rate = DEFAULT_RATE
        self._dt_sample = 1.0 / DEFAULT_RATE
        self._t0_nominal: dt.datetime | None = None
        self._current_theme = "Light"
        self._detector0: ChannelDetector | None = None
        self._detector1: ChannelDetector | None = None
        self._table_next_row = [2, 2]  # [pad0, pad1] – baris 0-1 adalah header

        max_pts = int(DEFAULT_RATE * PLOT_WINDOW_SEC)
        self._buf_x: collections.deque[float] = collections.deque(maxlen=max_pts)
        self._buf_ai0: collections.deque[float] = collections.deque(maxlen=max_pts)
        self._buf_ai1: collections.deque[float] = collections.deque(maxlen=max_pts)

        self._build_param_panel()

        # ── Tab Widget ────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # Tab 1: Live Data
        live_tab = QWidget()
        live_layout = QHBoxLayout(live_tab)
        live_layout.setContentsMargins(10, 10, 10, 10)
        live_layout.setSpacing(14)
        live_layout.addWidget(self._build_chart_panel(), stretch=1)
        live_layout.addWidget(self._build_table_panel(), stretch=0)
        self._tabs.addTab(live_tab, "Live Data")

        # Tab 2: Analisa Data (kosong — akan diisi di versi berikutnya)
        analisa_tab = QWidget()
        self._tabs.addTab(analisa_tab, "Analisa Data")

        # Load config.json setelah semua widget selesai dibuat
        cfg = _load_config()
        if cfg is not None:
            self._apply_config(cfg)

        self._plot_timer = QTimer(self)
        self._plot_timer.setInterval(PLOT_REFRESH_MS)
        self._plot_timer.timeout.connect(self._refresh_plot)

        self._apply_theme("Dark")

    # ── Hidden parameter widgets (tidak ditampilkan, diakses via ParameterDialog) ─
    def _build_param_panel(self) -> None:
        group = QGroupBox("Parameter Setting")

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(10, 14, 10, 10)

        self._inp_ch0 = QLineEdit(DEFAULT_CH0)
        self._inp_ch1 = QLineEdit(DEFAULT_CH1)
        self._inp_rate = QLineEdit(str(DEFAULT_RATE))
        self._inp_buffer = QLineEdit(str(DEFAULT_BUFFER))
        self._inp_spl = QLineEdit(str(DEFAULT_SAMPLES_PER_LOOP))

        self._dd_terminal = QComboBox()
        self._dd_terminal.addItems(["DIFF", "RSE", "NRSE"])
        self._dd_terminal.setCurrentText(DEFAULT_TERMINAL)

        self._dd_vrange = QComboBox()
        self._dd_vrange.addItems(list(VOLTAGE_RANGE_DIFF.keys()))
        self._dd_vrange.setCurrentText(DEFAULT_VOLTAGE_RANGE_DIFF)

        # Saat terminal berubah, sesuaikan pilihan input range
        self._dd_terminal.currentTextChanged.connect(self._on_terminal_changed)

        self._dd_ts_set = QComboBox()
        self._dd_ts_set.addItems(["Manual (A)", "Waveform (B)"])
        self._dd_ts_set.setCurrentText(DEFAULT_TS_SET)

        self._dd_ts_display = QComboBox()
        self._dd_ts_display.addItems(["Relative", "ISO"])
        self._dd_ts_display.setCurrentText(DEFAULT_TS_DISPLAY)

        form.addRow("Device Ch 0:", self._inp_ch0)
        form.addRow("Device Ch 1:", self._inp_ch1)
        form.addRow("Rate (Hz):", self._inp_rate)
        form.addRow("Buffer Size:", self._inp_buffer)
        form.addRow("Samples / Loop:", self._inp_spl)
        form.addRow("Terminal:", self._dd_terminal)
        form.addRow("Input Range:", self._dd_vrange)
        form.addRow("Timestamp Set:", self._dd_ts_set)
        form.addRow("Timestamp Display:", self._dd_ts_display)

        group.setLayout(form)
        # Simpan referensi agar Qt tidak men-GC widget anak (inp_ch0, dll.)
        self._hidden_param_group = group

    def _apply_config(self, cfg: dict) -> None:
        """Terapkan dict config ke hidden parameter widgets."""
        self._inp_ch0.setText(cfg.get("ch0", DEFAULT_CH0))
        self._inp_ch1.setText(cfg.get("ch1", DEFAULT_CH1))
        self._inp_rate.setText(cfg.get("rate", str(DEFAULT_RATE)))
        self._inp_buffer.setText(cfg.get("buffer", str(DEFAULT_BUFFER)))
        self._inp_spl.setText(cfg.get("spl", str(DEFAULT_SAMPLES_PER_LOOP)))
        self._dd_terminal.setCurrentText(cfg.get("terminal", DEFAULT_TERMINAL))
        self._dd_vrange.setCurrentText(cfg.get("vrange", DEFAULT_VOLTAGE_RANGE_DIFF))
        self._dd_ts_set.setCurrentText(cfg.get("ts_set", DEFAULT_TS_SET))
        self._dd_ts_display.setCurrentText(cfg.get("ts_display", DEFAULT_TS_DISPLAY))
        d0 = cfg.get("dev0", {})
        self._inp_thresh0.setText(d0.get("threshold",  DEFAULT_THRESHOLD))
        self._inp_hyst0.setText(d0.get("hysteresis",   DEFAULT_HYSTERESIS))
        self._inp_scale0.setText(d0.get("scale",       DEFAULT_SCALE))
        self._inp_hold0.setText(d0.get("hold",         str(DEFAULT_HOLD_TIME)))
        d1 = cfg.get("dev1", {})
        self._inp_thresh1.setText(d1.get("threshold",  DEFAULT_THRESHOLD))
        self._inp_hyst1.setText(d1.get("hysteresis",   DEFAULT_HYSTERESIS))
        self._inp_scale1.setText(d1.get("scale",       DEFAULT_SCALE))
        self._inp_hold1.setText(d1.get("hold",         str(DEFAULT_HOLD_TIME)))

    # ── Chart panel ──────────────────────────────────────────────────────────
    def _build_chart_panel(self) -> QWidget:
        def _make_plot_widget(title: str) -> tuple[pg.PlotWidget, pg.PlotDataItem]:
            pw = pg.PlotWidget(title=title)
            pi: pg.PlotItem = pw.getPlotItem()
            pi.setLabel("left", "Voltage", units="V")
            pi.setLabel("bottom", "Time", units="s")
            pi.showGrid(x=True, y=True, alpha=0.3)
            pi.setDownsampling(auto=True, mode="peak")
            pi.setClipToView(True)
            return pw, pi.plot()

        self._pw_ai0, self._curve_ai0 = _make_plot_widget("AI 0")
        self._pw_ai1, self._curve_ai1 = _make_plot_widget("AI 1")

        # Hubungkan sumbu X agar zoom/pan bergerak bersamaan
        self._pw_ai0.setXLink(self._pw_ai1)

        grp_ai0 = QGroupBox("Channel AI 0")
        lay0 = QVBoxLayout(grp_ai0)
        lay0.setContentsMargins(4, 4, 4, 4)
        lay0.addWidget(self._pw_ai0)

        grp_ai1 = QGroupBox("Channel AI 1")
        lay1 = QVBoxLayout(grp_ai1)
        lay1.setContentsMargins(4, 4, 4, 4)
        lay1.addWidget(self._pw_ai1)

        self._status_label = QLabel("Status: Stopped")
        self._status_label.setStyleSheet("color: gray; padding: 2px 4px;")

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)
        vbox.addWidget(grp_ai0, stretch=1)
        vbox.addWidget(grp_ai1, stretch=1)
        vbox.addWidget(self._status_label, stretch=0)

        container = QWidget()
        container.setLayout(vbox)
        return container

    # ── CSV helpers ───────────────────────────────────────────────────────────
    def _on_browse_csv_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Pilih Folder Simpan CSV", self._inp_csv_folder.text()
        )
        if folder:
            self._inp_csv_folder.setText(folder)
            self._update_csv_preview()

    def _on_stroke_changed(self, stroke: str) -> None:
        """Perbarui pilihan jarak sesuai gaya yang dipilih, pertahankan jika masih valid."""
        valid = STROKE_DISTANCES.get(stroke, [])
        current = self._dd_distance.currentText()
        self._dd_distance.blockSignals(True)
        self._dd_distance.clear()
        self._dd_distance.addItems(valid)
        if current in valid:
            self._dd_distance.setCurrentText(current)
        self._dd_distance.blockSignals(False)
        self._update_prefix_from_swimmer()

    def _update_prefix_from_swimmer(self) -> None:
        """Perbarui prefix CSV otomatis dari nama, gaya, dan jarak perenang."""
        if not hasattr(self, "_inp_csv_prefix"):
            return
        name = self._inp_swimmer_name.text().strip().replace(" ", "_")
        stroke = self._dd_stroke.currentText()
        distance = self._dd_distance.currentText()
        base = name if name else DEFAULT_CSV_PREFIX
        self._inp_csv_prefix.setText(f"{base}_{stroke}_{distance}")

    def _update_csv_preview(self) -> None:
        prefix = self._inp_csv_prefix.text().strip() or "DAQ"
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._lbl_csv_preview.setText(f"{prefix}_{ts}.csv")

    def _build_csv_filepath(self, start_time: dt.datetime) -> pathlib.Path:
        prefix = self._inp_csv_prefix.text().strip() or "DAQ"
        ts = start_time.strftime("%Y%m%d_%H%M%S")
        folder = pathlib.Path(self._inp_csv_folder.text())
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{prefix}_{ts}.csv"

    # ── Table panel ──────────────────────────────────────────────────────────
    def _build_table_panel(self) -> QWidget:
        group = QGroupBox("Table")

        NUM_DATA_ROWS = 10
        COLS = 4

        self._data_table = QTableWidget(2 + NUM_DATA_ROWS, COLS)
        self._data_table.horizontalHeader().hide()
        self._data_table.verticalHeader().hide()
        self._data_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._data_table.setSelectionMode(
            QTableWidget.SelectionMode.NoSelection
        )
        self._data_table.setShowGrid(True)

        # "Pad 1" span 2 kolom, "Pad 2" span 2 kolom
        self._data_table.setSpan(0, 0, 1, 2)
        self._data_table.setSpan(0, 2, 1, 2)

        row0_labels = {0: "Pad 1", 2: "Pad 2"}
        row1_labels = {0: "Time", 1: "Press (Kg)", 2: "Time", 3: "Press (Kg)"}

        bold = QFont()
        bold.setBold(True)

        for col, text in row0_labels.items():
            item = QTableWidgetItem(text)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            item.setFont(bold)
            self._data_table.setItem(0, col, item)

        for col, text in row1_labels.items():
            item = QTableWidgetItem(text)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            item.setFont(bold)
            self._data_table.setItem(1, col, item)

        for row in range(2, 2 + NUM_DATA_ROWS):
            for col in range(COLS):
                item = QTableWidgetItem("")
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                self._data_table.setItem(row, col, item)

        # Stretch semua kolom agar mengisi penuh lebar container
        self._data_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._data_table.setRowHeight(0, 26)
        self._data_table.setRowHeight(1, 22)
        for row in range(2, 2 + NUM_DATA_ROWS):
            self._data_table.setRowHeight(row, 22)

        self._update_table_header_colors()

        # ── Parameter di atas tabel ──────────────────────────────────────────
        dbl = QDoubleValidator()
        dbl.setNotation(QDoubleValidator.Notation.StandardNotation)

        def _make_param_input(default: str) -> QLineEdit:
            le = QLineEdit(default)
            le.setValidator(dbl)
            le.setFixedWidth(90)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return le

        param_grid = QGridLayout()
        param_grid.setSpacing(4)
        param_grid.setContentsMargins(0, 0, 0, 6)

        col_headers = [
            "Threshold\n(Volt)", "Hysteresis\n(Volt)",
            "Scale\n(Kg/Volt)", "Delay Time\n(s)"
        ]
        for col, text in enumerate(col_headers):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            small = QFont()
            small.setPointSize(8)
            lbl.setFont(small)
            param_grid.addWidget(lbl, 0, col + 1)

        for dev_idx in range(2):
            row_base = dev_idx * 2 + 1
            dev_lbl = QLabel(f"Dev. {dev_idx}")
            dev_lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            param_grid.addWidget(dev_lbl, row_base, 0)

            inp_thresh = _make_param_input(DEFAULT_THRESHOLD)
            inp_hyst   = _make_param_input(DEFAULT_HYSTERESIS)
            inp_scale  = _make_param_input(DEFAULT_SCALE)
            inp_hold   = _make_param_input(str(DEFAULT_HOLD_TIME))
            param_grid.addWidget(inp_thresh, row_base, 1)
            param_grid.addWidget(inp_hyst,   row_base, 2)
            param_grid.addWidget(inp_scale,  row_base, 3)
            param_grid.addWidget(inp_hold,   row_base, 4)

            if dev_idx == 0:
                self._inp_thresh0 = inp_thresh
                self._inp_hyst0   = inp_hyst
                self._inp_scale0  = inp_scale
                self._inp_hold0   = inp_hold
            else:
                self._inp_thresh1 = inp_thresh
                self._inp_hyst1   = inp_hyst
                self._inp_scale1  = inp_scale
                self._inp_hold1   = inp_hold

        param_grid.setColumnStretch(0, 0)
        for c in range(1, 5):
            param_grid.setColumnStretch(c, 1)

        # ── Time format radio buttons ────────────────────────────────────────
        self._rb_seconds = QRadioButton("Seconds")
        self._rb_mmss    = QRadioButton("MM:SS.sss")
        self._rb_seconds.setChecked(True)

        self._rb_group = QButtonGroup(self)
        self._rb_group.addButton(self._rb_seconds)
        self._rb_group.addButton(self._rb_mmss)
        self._rb_group.buttonClicked.connect(
            lambda _: self._reformat_table_times()
        )

        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(10)
        fmt_lbl = QLabel("Time Format:")
        fmt_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        fmt_row.addWidget(fmt_lbl)
        fmt_row.addWidget(self._rb_seconds)
        fmt_row.addWidget(self._rb_mmss)
        fmt_row.addStretch()

        # ── Save table to CSV ────────────────────────────────────────────────
        table_folder_row = QWidget()
        table_folder_lay = QHBoxLayout(table_folder_row)
        table_folder_lay.setContentsMargins(0, 0, 0, 0)
        table_folder_lay.setSpacing(4)

        self._inp_table_folder = QLineEdit(DEFAULT_TABLE_FOLDER)
        self._inp_table_folder.setReadOnly(True)
        btn_browse_table = QPushButton("…")
        btn_browse_table.setFixedWidth(28)
        btn_browse_table.clicked.connect(self._on_browse_table_folder)
        table_folder_lay.addWidget(self._inp_table_folder)
        table_folder_lay.addWidget(btn_browse_table)

        folder_form = QHBoxLayout()
        folder_lbl = QLabel("Folder:")
        folder_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        folder_form.addWidget(folder_lbl)
        folder_form.addWidget(table_folder_row)

        self._btn_save_table = QPushButton("💾  Save Table to CSV")
        self._btn_save_table.setMinimumHeight(32)
        self._btn_save_table.clicked.connect(self._on_save_table_csv)

        self._btn_set_param = QPushButton("⚙️  Set Parameter")
        self._btn_set_param.setMinimumHeight(32)
        self._btn_set_param.clicked.connect(self._on_open_param_dialog)

        # ── Info Perenang ────────────────────────────────────────────────────
        swimmer_group = QGroupBox("Info Perenang")
        swimmer_form = QFormLayout()
        swimmer_form.setSpacing(6)
        swimmer_form.setContentsMargins(10, 12, 10, 10)

        self._inp_swimmer_name = QLineEdit()
        self._inp_swimmer_name.setPlaceholderText("Nama perenang...")

        self._dd_stroke = QComboBox()
        self._dd_stroke.addItems(list(STROKE_DISTANCES.keys()))

        self._dd_distance = QComboBox()
        self._dd_distance.addItems(STROKE_DISTANCES["Bebas"])

        swimmer_form.addRow("Nama:", self._inp_swimmer_name)
        swimmer_form.addRow("Gaya:", self._dd_stroke)
        swimmer_form.addRow("Jarak:", self._dd_distance)
        swimmer_group.setLayout(swimmer_form)

        self._inp_swimmer_name.textChanged.connect(self._update_prefix_from_swimmer)
        self._dd_stroke.currentTextChanged.connect(self._on_stroke_changed)
        self._dd_distance.currentTextChanged.connect(self._update_prefix_from_swimmer)

        # ── Export CSV (dipindah dari panel kiri) ────────────────────────────
        csv_group = QGroupBox("Export Log to CSV")
        csv_form = QFormLayout()
        csv_form.setSpacing(6)
        csv_form.setContentsMargins(10, 12, 10, 10)

        self._chk_csv = QCheckBox("Record CSV saat Start")
        self._chk_csv.setChecked(False)

        self._inp_csv_prefix = QLineEdit(DEFAULT_CSV_PREFIX)

        csv_folder_row = QWidget()
        csv_folder_lay = QHBoxLayout(csv_folder_row)
        csv_folder_lay.setContentsMargins(0, 0, 0, 0)
        csv_folder_lay.setSpacing(4)
        self._inp_csv_folder = QLineEdit(DEFAULT_CSV_FOLDER)
        self._inp_csv_folder.setReadOnly(True)
        btn_browse_csv = QPushButton("…")
        btn_browse_csv.setFixedWidth(28)
        btn_browse_csv.clicked.connect(self._on_browse_csv_folder)
        csv_folder_lay.addWidget(self._inp_csv_folder)
        csv_folder_lay.addWidget(btn_browse_csv)

        self._lbl_csv_preview = QLabel("")
        self._lbl_csv_preview.setWordWrap(True)
        self._lbl_csv_preview.setStyleSheet("font-size: 10px; color: gray;")

        csv_form.addRow(self._chk_csv)
        csv_form.addRow("Prefix:", self._inp_csv_prefix)
        csv_form.addRow("Folder:", csv_folder_row)
        csv_form.addRow("File:", self._lbl_csv_preview)
        csv_group.setLayout(csv_form)

        self._inp_csv_prefix.textChanged.connect(self._update_csv_preview)
        self._update_csv_preview()

        # ── Start/Stop (dipindah dari panel kiri) ───────────────────────────
        self._btn_start_stop = QPushButton("▶  Start")
        self._btn_start_stop.setCheckable(True)
        bold_start = QFont()
        bold_start.setBold(True)
        self._btn_start_stop.setFont(bold_start)
        self._btn_start_stop.setMinimumHeight(44)
        self._btn_start_stop.clicked.connect(self._on_start_stop)

        # ── Theme toggle (dipindah dari panel kiri) ──────────────────────────
        self._btn_theme = QPushButton("🌙  Dark")
        self._btn_theme.setMinimumHeight(32)
        self._btn_theme.clicked.connect(self._on_toggle_theme)

        # Layout dalam QGroupBox("Table") — hanya elemen tabel
        table_vbox = QVBoxLayout()
        table_vbox.setContentsMargins(8, 8, 8, 8)
        table_vbox.setSpacing(6)
        table_vbox.addLayout(fmt_row)
        table_vbox.addWidget(self._data_table)
        table_vbox.addLayout(folder_form)
        table_vbox.addWidget(self._btn_save_table)
        group.setLayout(table_vbox)

        # Layout container luar — semua elemen berurutan
        btn_bottom_row = QHBoxLayout()
        btn_bottom_row.setSpacing(6)
        btn_bottom_row.addWidget(self._btn_set_param)
        btn_bottom_row.addWidget(self._btn_theme)

        outer_vbox = QVBoxLayout()
        outer_vbox.setContentsMargins(0, 0, 0, 0)
        outer_vbox.setSpacing(6)
        outer_vbox.addWidget(swimmer_group)
        outer_vbox.addWidget(csv_group)
        outer_vbox.addWidget(self._btn_start_stop)
        outer_vbox.addWidget(group, stretch=1)
        outer_vbox.addLayout(btn_bottom_row)

        container = QWidget()
        container.setFixedWidth(360)
        container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        container.setLayout(outer_vbox)
        return container

    def _update_table_header_colors(self) -> None:
        """Sesuaikan warna background sel header dengan tema aktif."""
        if not hasattr(self, "_data_table"):
            return
        if self._current_theme == "Dark":
            bg = QColor("#4a4d51")
            fg = QColor("#dddddd")
        else:
            bg = QColor("#d6d9df")
            fg = QColor("#1a1a1a")
        header_cells = [(0, 0), (0, 2), (1, 0), (1, 1), (1, 2), (1, 3)]
        for row, col in header_cells:
            item = self._data_table.item(row, col)
            if item:
                item.setBackground(QBrush(bg))
                item.setForeground(QBrush(fg))

    # ── Save table ────────────────────────────────────────────────────────────
    def _on_browse_table_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Pilih Folder Simpan Table CSV", self._inp_table_folder.text()
        )
        if folder:
            self._inp_table_folder.setText(folder)

    def _on_open_param_dialog(self) -> None:
        dlg = ParameterDialog(self, parent=self)
        dlg.exec()

    def _on_save_table_csv(self) -> None:
        """Simpan isi tabel (Pad 1 & Pad 2) ke file CSV."""
        prefix = self._inp_csv_prefix.text().strip() or "DAQ"
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = pathlib.Path(self._inp_table_folder.text())
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Gagal membuat folder:\n{exc}")
            return

        filepath = folder / f"{prefix}_table_{ts}.csv"
        try:
            with filepath.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["No", "Time_Pad1", "Pressure_Pad1(Kg)", "Time_Pad2", "Pressure_Pad2(Kg)"]
                )
                for idx, row in enumerate(range(2, 2 + TABLE_ROWS), start=1):
                    t1 = self._data_table.item(row, 0)
                    p1 = self._data_table.item(row, 1)
                    t2 = self._data_table.item(row, 2)
                    p2 = self._data_table.item(row, 3)
                    t1_val = t1.text() if t1 else ""
                    p1_val = p1.text() if p1 else ""
                    t2_val = t2.text() if t2 else ""
                    p2_val = p2.text() if p2 else ""
                    if t1_val or p1_val or t2_val or p2_val:
                        writer.writerow([idx, t1_val, p1_val, t2_val, p2_val])
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Gagal menyimpan file:\n{exc}")
            return

        QMessageBox.information(
            self, "Tersimpan", f"Tabel berhasil disimpan ke:\n{filepath}"
        )

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _on_toggle_theme(self) -> None:
        next_theme = "Dark" if self._current_theme == "Light" else "Light"
        self._apply_theme(next_theme)

    def _apply_theme(self, theme_name: str) -> None:
        """Terapkan tema "Light" atau "Dark" ke seluruh aplikasi.

        Mengubah: Qt stylesheet global, warna background/foreground pyqtgraph,
        warna kurva AI0/AI1, warna header tabel, warna tombol aksi, dan label
        tombol tema.
        """
        theme = _THEMES[theme_name]
        self._current_theme = theme_name

        # Qt stylesheet untuk semua widget
        QApplication.instance().setStyleSheet(theme["qt_stylesheet"])

        # pyqtgraph: background & foreground
        for pw in (self._pw_ai0, self._pw_ai1):
            pw.setBackground(theme["pg_bg"])
            pi: pg.PlotItem = pw.getPlotItem()
            for axis_name in ("left", "bottom", "top", "right"):
                axis = pi.getAxis(axis_name)
                if axis is not None:
                    axis.setPen(pg.mkPen(color=theme["pg_fg"]))
                    axis.setTextPen(pg.mkPen(color=theme["pg_fg"]))
            title_item = pi.titleLabel
            if title_item is not None:
                title_item.setText(
                    title_item.text,
                    color=theme["pg_fg"],
                )

        # Warna kurva
        self._curve_ai0.setPen(pg.mkPen(color=theme["curve_ai0"], width=1))
        self._curve_ai1.setPen(pg.mkPen(color=theme["curve_ai1"], width=1))

        # Warna header tabel
        self._update_table_header_colors()

        # Warna tombol aksi
        bs = theme["btn_styles"]
        self._btn_start_stop.setStyleSheet(bs["start"])
        self._btn_save_table.setStyleSheet(bs["save"])
        self._btn_set_param.setStyleSheet(bs["set_param"])
        self._btn_theme.setStyleSheet(bs["theme"])

        # Label tombol tema
        if theme_name == "Dark":
            self._btn_theme.setText("☀️  Light")
        else:
            self._btn_theme.setText("🌙  Dark")

    # ── Start / Stop ─────────────────────────────────────────────────────────
    def _on_start_stop(self, checked: bool) -> None:
        if checked:
            self._start_daq()
        else:
            self._stop_daq()

    def _start_daq(self) -> None:
        """Mulai akuisisi: validasi input, buat DaqWorker & ChannelDetector, mulai timer plot."""
        try:
            rate = float(self._inp_rate.text())
            buffer_size = int(self._inp_buffer.text())
            spl = int(self._inp_spl.text())
        except ValueError as exc:
            self._set_status(f"Input tidak valid: {exc}", error=True)
            self._btn_start_stop.setChecked(False)
            return

        terminal = TERMINAL_MAP.get(
            self._dd_terminal.currentText(), TerminalConfiguration.DIFF
        )
        read_mode: Literal["A", "B"] = (
            "B" if "B" in self._dd_ts_set.currentText() else "A"
        )

        self._rate = rate
        self._dt_sample = 1.0 / rate
        self._t0_nominal = dt.datetime.now().astimezone()

        # Buat detector dari nilai parameter saat ini
        def _safe_float(text: str, default: float) -> float:
            try:
                return float(text)
            except ValueError:
                return default

        self._detector0 = ChannelDetector(
            threshold=_safe_float(self._inp_thresh0.text(), 0.05),
            hysteresis=_safe_float(self._inp_hyst0.text(),  0.005),
            scale=_safe_float(self._inp_scale0.text(),      1.0),
            hold_time=_safe_float(self._inp_hold0.text(),   DEFAULT_HOLD_TIME),
        )
        self._detector1 = ChannelDetector(
            threshold=_safe_float(self._inp_thresh1.text(), 0.05),
            hysteresis=_safe_float(self._inp_hyst1.text(),  0.005),
            scale=_safe_float(self._inp_scale1.text(),      1.0),
            hold_time=_safe_float(self._inp_hold1.text(),   DEFAULT_HOLD_TIME),
        )

        # Reset tabel: hapus isi baris data (baris 0-1 adalah header)
        self._table_next_row = [2, 2]
        for row in range(2, 2 + TABLE_ROWS):
            for col in range(self._data_table.columnCount()):
                item = self._data_table.item(row, col)
                if item:
                    item.setText("")

        # Buka CSV writer jika checkbox aktif
        self._csv_writer = None
        if self._chk_csv.isChecked():
            csv_path = self._build_csv_filepath(self._t0_nominal)
            self._csv_writer = CsvWriter(csv_path, self._dt_sample)

        max_pts = int(rate * PLOT_WINDOW_SEC)
        self._buf_x = collections.deque(maxlen=max_pts)
        self._buf_ai0 = collections.deque(maxlen=max_pts)
        self._buf_ai1 = collections.deque(maxlen=max_pts)

        vrange_key = self._dd_vrange.currentText()
        all_ranges = {**VOLTAGE_RANGE_DIFF, **VOLTAGE_RANGE_SE}
        vmin, vmax = all_ranges[vrange_key]

        self._worker = DaqWorker(
            ch0=self._inp_ch0.text().strip(),
            ch1=self._inp_ch1.text().strip(),
            rate=rate,
            buffer_size=buffer_size,
            samples_per_loop=spl,
            terminal_config=terminal,
            read_mode=read_mode,
            min_val=vmin,
            max_val=vmax,
        )
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error_occurred.connect(self._on_worker_error)
        self._worker.warning_occurred.connect(self._on_worker_warning)
        self._worker.finished.connect(self._on_worker_finished)

        self._set_param_inputs_enabled(False)
        self._chk_csv.setEnabled(False)
        self._inp_csv_prefix.setEnabled(False)
        self._worker.start()
        self._plot_timer.start()
        self._btn_start_stop.setText("■  Stop")
        if self._csv_writer:
            self._set_status(
                f"Status: Running  |  Rec → {self._csv_writer.filepath.name}",
                running=True,
            )
        else:
            self._set_status("Status: Running", running=True)
        self._is_running = True

    def _stop_daq(self) -> None:
        """Hentikan akuisisi: stop worker thread, flush CSV, reset UI state."""
        self._plot_timer.stop()
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
        saved_msg = ""
        if self._csv_writer:
            self._csv_writer.close()
            saved_msg = f"  |  Saved: {self._csv_writer.filepath.name}"
            self._csv_writer = None
        self._detector0 = None
        self._detector1 = None
        self._set_param_inputs_enabled(True)
        self._chk_csv.setEnabled(True)
        self._inp_csv_prefix.setEnabled(True)
        self._btn_start_stop.setText("▶  Start")
        self._set_status(f"Status: Stopped{saved_msg}")
        self._is_running = False

    # ── Slots ─────────────────────────────────────────────────────────────────
    def _on_data_ready(self, ai0: list, ai1: list, offset: int) -> None:
        """Terima chunk data dari DaqWorker.

        Setiap sampel dimasukkan ke buffer plot, diproses oleh ChannelDetector,
        dan (opsional) ditulis ke CSV melalui CsvWriter.

        Parameters
        ----------
        ai0, ai1 : list[float]
            Tegangan (Volt) per sampel untuk masing-masing channel.
        offset : int
            Indeks sampel pertama di chunk ini (untuk menghitung timestamp relatif).
        """
        for i in range(len(ai0)):
            x_val = (offset + i) * self._dt_sample
            self._buf_x.append(x_val)
            self._buf_ai0.append(ai0[i])
            self._buf_ai1.append(ai1[i])

            # Proses detector per sampel
            if self._detector0 is not None:
                result0 = self._detector0.process(ai0[i], x_val)
                if result0 is not None:
                    self._append_table_row(result0[0], result0[1], channel=0)

            if self._detector1 is not None:
                result1 = self._detector1.process(ai1[i], x_val)
                if result1 is not None:
                    self._append_table_row(result1[0], result1[1], channel=1)

        if self._csv_writer is not None:
            self._csv_writer.write_chunk(ai0, ai1, offset)

        # ── Print ke terminal (dicomment secara default) ───────────────────
        # ts_display = self._dd_ts_display.currentText()
        # for i in range(len(ai0)):
        #     rel_s = (offset + i) * self._dt_sample
        #     if ts_display == "ISO" and self._t0_nominal is not None:
        #         ts_str = (
        #             self._t0_nominal + dt.timedelta(seconds=rel_s)
        #         ).isoformat()
        #     else:
        #         ts_str = f"{rel_s:g}"
        #     print(ts_str, float(ai0[i]), float(ai1[i]))

    def _fmt_time(self, seconds: float) -> str:
        """Format waktu sesuai pilihan radio button."""
        if self._rb_mmss.isChecked():
            total_ms = int(round(seconds * 1000))
            mins, rem_ms = divmod(total_ms, 60_000)
            secs, ms = divmod(rem_ms, 1000)
            return f"{mins:02d}:{secs:02d}.{ms:03d}"
        return f"{seconds:.3f}"

    def _reformat_table_times(self) -> None:
        """Reformat semua sel Time di tabel tanpa mengubah data."""
        for row in range(2, 2 + TABLE_ROWS):
            for col in (0, 2):
                item = self._data_table.item(row, col)
                if item:
                    val = item.data(Qt.ItemDataRole.UserRole)
                    if val is not None:
                        item.setText(self._fmt_time(val))

    def _append_table_row(self, t0: float, pressure: float, channel: int) -> None:
        """Tulis satu hasil deteksi ke tabel.

        channel=0 → kolom 0 (Time Pad1) & 1 (Pressure Pad1)
        channel=1 → kolom 2 (Time Pad2) & 3 (Pressure Pad2)
        Setiap channel memiliki row counter sendiri agar baris masing-masing pad
        tidak saling menggeser. Saat baris penuh, geser ke atas (scroll up).
        """
        col_time = channel * 2       # 0 atau 2
        col_press = channel * 2 + 1  # 1 atau 3

        if self._table_next_row[channel] >= 2 + TABLE_ROWS:
            # Geser semua baris ke atas satu langkah (text + UserRole)
            for row in range(2, 2 + TABLE_ROWS - 1):
                src_t = self._data_table.item(row + 1, col_time)
                dst_t = self._data_table.item(row, col_time)
                src_p = self._data_table.item(row + 1, col_press)
                dst_p = self._data_table.item(row, col_press)
                if dst_t and src_t:
                    dst_t.setText(src_t.text())
                    dst_t.setData(Qt.ItemDataRole.UserRole,
                                  src_t.data(Qt.ItemDataRole.UserRole))
                if dst_p and src_p:
                    dst_p.setText(src_p.text())
            self._table_next_row[channel] = 2 + TABLE_ROWS - 1

        row = self._table_next_row[channel]
        t_item = self._data_table.item(row, col_time)
        p_item = self._data_table.item(row, col_press)
        if t_item:
            t_item.setData(Qt.ItemDataRole.UserRole, t0)   # simpan float asli
            t_item.setText(self._fmt_time(t0))
        if p_item:
            p_item.setText(f"{pressure:.4f}")
        self._table_next_row[channel] += 1

    def _refresh_plot(self) -> None:
        """Update kurva pyqtgraph dari buffer deque. Dipanggil tiap 100 ms oleh QTimer."""
        if not self._buf_x:
            return
        x = np.fromiter(self._buf_x, dtype=np.float64)
        y0 = np.fromiter(self._buf_ai0, dtype=np.float64)
        y1 = np.fromiter(self._buf_ai1, dtype=np.float64)
        self._curve_ai0.setData(x, y0)
        self._curve_ai1.setData(x, y1)

    def _on_worker_error(self, msg: str) -> None:
        self._plot_timer.stop()
        self._set_param_inputs_enabled(True)
        self._btn_start_stop.setChecked(False)
        self._btn_start_stop.setText("▶  Start")
        self._is_running = False
        self._set_status(f"Error: {msg}", error=True)

    def _on_worker_warning(self, msg: str) -> None:
        self._set_status(f"Peringatan: {msg}")

    def _on_worker_finished(self) -> None:
        if self._is_running:
            self._stop_daq()
            self._btn_start_stop.setChecked(False)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _set_status(
        self,
        text: str,
        error: bool = False,
        running: bool = False,
    ) -> None:
        """Perbarui label status di bawah chart.

        Warna: merah (error), hijau (running), abu-abu (stopped/info).
        """
        self._status_label.setText(text)
        if error:
            color = "red"
        elif running:
            color = "#4caf50"
        else:
            color = "gray"
        self._status_label.setStyleSheet(f"color: {color}; padding: 2px 4px;")

    def _on_set_defaults(self) -> None:
        """Kembalikan semua input Parameter Setting dan detector ke nilai default."""
        # Parameter Setting
        self._inp_ch0.setText(DEFAULT_CH0)
        self._inp_ch1.setText(DEFAULT_CH1)
        self._inp_rate.setText(str(DEFAULT_RATE))
        self._inp_buffer.setText(str(DEFAULT_BUFFER))
        self._inp_spl.setText(str(DEFAULT_SAMPLES_PER_LOOP))
        self._dd_terminal.setCurrentText(DEFAULT_TERMINAL)
        self._dd_vrange.setCurrentText(DEFAULT_VOLTAGE_RANGE_DIFF)
        self._dd_ts_set.setCurrentText(DEFAULT_TS_SET)
        self._dd_ts_display.setCurrentText(DEFAULT_TS_DISPLAY)

        # Threshold / Hysteresis / Scale / Hold Time – Dev 0
        self._inp_thresh0.setText(DEFAULT_THRESHOLD)
        self._inp_hyst0.setText(DEFAULT_HYSTERESIS)
        self._inp_scale0.setText(DEFAULT_SCALE)
        self._inp_hold0.setText(str(DEFAULT_HOLD_TIME))

        # Threshold / Hysteresis / Scale / Hold Time – Dev 1
        self._inp_thresh1.setText(DEFAULT_THRESHOLD)
        self._inp_hyst1.setText(DEFAULT_HYSTERESIS)
        self._inp_scale1.setText(DEFAULT_SCALE)
        self._inp_hold1.setText(str(DEFAULT_HOLD_TIME))

    def _on_terminal_changed(self, text: str) -> None:
        """Sesuaikan pilihan input range sesuai mode terminal."""
        if text == "DIFF":
            items = list(VOLTAGE_RANGE_DIFF.keys())
            default = DEFAULT_VOLTAGE_RANGE_DIFF
        else:
            items = list(VOLTAGE_RANGE_SE.keys())
            default = DEFAULT_VOLTAGE_RANGE_SE

        self._dd_vrange.blockSignals(True)
        self._dd_vrange.clear()
        self._dd_vrange.addItems(items)
        self._dd_vrange.setCurrentText(default)
        self._dd_vrange.blockSignals(False)

    def _set_param_inputs_enabled(self, enabled: bool) -> None:
        """Enable/disable semua input parameter saat akuisisi berjalan/berhenti."""
        for widget in (
            self._inp_ch0,
            self._inp_ch1,
            self._inp_rate,
            self._inp_buffer,
            self._inp_spl,
            self._dd_terminal,
            self._dd_vrange,
            self._dd_ts_set,
            self._inp_thresh0, self._inp_hyst0, self._inp_scale0, self._inp_hold0,
            self._inp_thresh1, self._inp_hyst1, self._inp_scale1, self._inp_hold1,
        ):
            widget.setEnabled(enabled)

    def closeEvent(self, event) -> None:
        """Pastikan DaqWorker dan CsvWriter dihentikan dengan benar sebelum app tutup."""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)
        if self._csv_writer:
            self._csv_writer.close()
            self._csv_writer = None
        event.accept()


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

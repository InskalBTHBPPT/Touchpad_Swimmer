import collections
import csv
import datetime as dt
import pathlib
import queue
import sys
import threading
from typing import Literal

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
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

# ─── Theme definitions ────────────────────────────────────────────────────────
# Setiap theme menyimpan: warna plot background, warna foreground (axis/text),
# warna kurva AI0 & AI1, stylesheet Qt untuk widget.
_THEMES: dict[str, dict] = {
    "Light": {
        "pg_bg": "w",
        "pg_fg": "k",
        "curve_ai0": (30, 144, 255),
        "curve_ai1": (220, 80, 0),
        "qt_stylesheet": "",
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
            QPushButton:checked { background: #8b1a1a; color: #ffffff; }
            QLabel           { color: #cccccc; }
        """,
    },
}


DEFAULT_CSV_PREFIX = "Swimming"
DEFAULT_CSV_FOLDER = str(pathlib.Path.home() / "Documents")


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


# ─── DAQ Worker Thread ────────────────────────────────────────────────────────
class DaqWorker(QThread):
    """Menjalankan nidaqmx.read() di thread terpisah agar GUI tidak freeze."""

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
    ) -> None:
        super().__init__()
        self.ch0 = ch0
        self.ch1 = ch1
        self.rate = rate
        self.buffer_size = buffer_size
        self.samples_per_loop = samples_per_loop
        self.terminal_config = terminal_config
        self.read_mode = read_mode
        self._running = False

    def run(self) -> None:
        self._running = True
        sample_offset = 0
        use_waveform = self.read_mode == "B"
        fallback_warned = False

        try:
            with nidaqmx.Task() as task:
                for ch in (self.ch0, self.ch1):
                    task.ai_channels.add_ai_voltage_chan(
                        ch, terminal_config=self.terminal_config
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
        self._running = False


# ─── Main Window ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NI DAQ Monitor")
        self.resize(1280, 640)

        self._worker: DaqWorker | None = None
        self._csv_writer: CsvWriter | None = None
        self._is_running = False
        self._rate = DEFAULT_RATE
        self._dt_sample = 1.0 / DEFAULT_RATE
        self._t0_nominal: dt.datetime | None = None
        self._current_theme = "Light"

        max_pts = int(DEFAULT_RATE * PLOT_WINDOW_SEC)
        self._buf_x: collections.deque[float] = collections.deque(maxlen=max_pts)
        self._buf_ai0: collections.deque[float] = collections.deque(maxlen=max_pts)
        self._buf_ai1: collections.deque[float] = collections.deque(maxlen=max_pts)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(14)

        root.addWidget(self._build_param_panel(), stretch=0)
        root.addWidget(self._build_chart_panel(), stretch=1)

        self._plot_timer = QTimer(self)
        self._plot_timer.setInterval(PLOT_REFRESH_MS)
        self._plot_timer.timeout.connect(self._refresh_plot)

        self._apply_theme("Light")

    # ── Parameter panel ──────────────────────────────────────────────────────
    def _build_param_panel(self) -> QWidget:
        group = QGroupBox("Parameter Setting")
        group.setFixedWidth(270)

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
        form.addRow("Timestamp Set:", self._dd_ts_set)
        form.addRow("Timestamp Display:", self._dd_ts_display)

        group.setLayout(form)

        # ── CSV export group ──────────────────────────────────────────────
        csv_group = QGroupBox("Export CSV")
        csv_group.setFixedWidth(270)
        csv_form = QFormLayout()
        csv_form.setSpacing(6)
        csv_form.setContentsMargins(10, 12, 10, 10)

        self._chk_csv = QCheckBox("Record CSV saat Start")
        self._chk_csv.setChecked(False)

        self._inp_csv_prefix = QLineEdit(DEFAULT_CSV_PREFIX)

        folder_row = QWidget()
        folder_lay = QHBoxLayout(folder_row)
        folder_lay.setContentsMargins(0, 0, 0, 0)
        folder_lay.setSpacing(4)
        self._inp_csv_folder = QLineEdit(DEFAULT_CSV_FOLDER)
        self._inp_csv_folder.setReadOnly(True)
        btn_browse = QPushButton("…")
        btn_browse.setFixedWidth(28)
        btn_browse.clicked.connect(self._on_browse_csv_folder)
        folder_lay.addWidget(self._inp_csv_folder)
        folder_lay.addWidget(btn_browse)

        self._lbl_csv_preview = QLabel("")
        self._lbl_csv_preview.setWordWrap(True)
        self._lbl_csv_preview.setStyleSheet("font-size: 10px; color: gray;")

        csv_form.addRow(self._chk_csv)
        csv_form.addRow("Prefix:", self._inp_csv_prefix)
        csv_form.addRow("Folder:", folder_row)
        csv_form.addRow("File:", self._lbl_csv_preview)
        csv_group.setLayout(csv_form)

        self._inp_csv_prefix.textChanged.connect(self._update_csv_preview)
        self._update_csv_preview()

        self._btn_start_stop = QPushButton("▶  Start")
        self._btn_start_stop.setCheckable(True)
        bold = QFont()
        bold.setBold(True)
        self._btn_start_stop.setFont(bold)
        self._btn_start_stop.setMinimumHeight(44)
        self._btn_start_stop.clicked.connect(self._on_start_stop)

        self._btn_theme = QPushButton("🌙  Dark")
        self._btn_theme.setMinimumHeight(32)
        self._btn_theme.clicked.connect(self._on_toggle_theme)

        vbox = QVBoxLayout()
        vbox.setSpacing(8)
        vbox.addWidget(group)
        vbox.addWidget(csv_group)
        vbox.addWidget(self._btn_start_stop)
        vbox.addWidget(self._btn_theme)
        vbox.addStretch()

        container = QWidget()
        container.setLayout(vbox)
        container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        return container

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

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _on_toggle_theme(self) -> None:
        next_theme = "Dark" if self._current_theme == "Light" else "Light"
        self._apply_theme(next_theme)

    def _apply_theme(self, theme_name: str) -> None:
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

        # Label tombol
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

        # Buka CSV writer jika checkbox aktif
        self._csv_writer = None
        if self._chk_csv.isChecked():
            csv_path = self._build_csv_filepath(self._t0_nominal)
            self._csv_writer = CsvWriter(csv_path, self._dt_sample)

        max_pts = int(rate * PLOT_WINDOW_SEC)
        self._buf_x = collections.deque(maxlen=max_pts)
        self._buf_ai0 = collections.deque(maxlen=max_pts)
        self._buf_ai1 = collections.deque(maxlen=max_pts)

        self._worker = DaqWorker(
            ch0=self._inp_ch0.text().strip(),
            ch1=self._inp_ch1.text().strip(),
            rate=rate,
            buffer_size=buffer_size,
            samples_per_loop=spl,
            terminal_config=terminal,
            read_mode=read_mode,
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
        self._plot_timer.stop()
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
        saved_msg = ""
        if self._csv_writer:
            self._csv_writer.close()
            saved_msg = f"  |  Saved: {self._csv_writer.filepath.name}"
            self._csv_writer = None
        self._set_param_inputs_enabled(True)
        self._chk_csv.setEnabled(True)
        self._inp_csv_prefix.setEnabled(True)
        self._btn_start_stop.setText("▶  Start")
        self._set_status(f"Status: Stopped{saved_msg}")
        self._is_running = False

    # ── Slots ─────────────────────────────────────────────────────────────────
    def _on_data_ready(self, ai0: list, ai1: list, offset: int) -> None:
        for i in range(len(ai0)):
            x_val = (offset + i) * self._dt_sample
            self._buf_x.append(x_val)
            self._buf_ai0.append(ai0[i])
            self._buf_ai1.append(ai1[i])

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

    def _refresh_plot(self) -> None:
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
        self._status_label.setText(text)
        if error:
            color = "red"
        elif running:
            color = "#4caf50"
        else:
            color = "gray"
        self._status_label.setStyleSheet(f"color: {color}; padding: 2px 4px;")

    def _set_param_inputs_enabled(self, enabled: bool) -> None:
        for widget in (
            self._inp_ch0,
            self._inp_ch1,
            self._inp_rate,
            self._inp_buffer,
            self._inp_spl,
            self._dd_terminal,
            self._dd_ts_set,
        ):
            widget.setEnabled(enabled)

    def closeEvent(self, event) -> None:
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

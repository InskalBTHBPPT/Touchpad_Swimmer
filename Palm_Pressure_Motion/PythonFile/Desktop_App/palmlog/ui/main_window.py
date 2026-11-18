"""Jendela PalmLog laptop: board, berkas, stream, analisa .bin."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from palmlog import __version__
from palmlog.attitude import attitude_rpy_deg
from palmlog.client import BleService
from palmlog.plg import export_calculated_csv, export_csv, parse_plg
from palmlog.protocol import (
    FLASH_SIZE,
    format_bytes,
    format_duration,
)
from palmlog.storage import DATA, bin_path

CHANNEL_COLORS = (
    "#10b981",
    "#38bdf8",
    "#f59e0b",
    "#f43f5e",
    "#8b5cf6",
    "#06b6d4",
    "#fb923c",
    "#ec4899",
    "#a78bfa",
    "#2dd4bf",
    "#f472b6",
)
N_CHANNELS = 11
# d1/d2 = 0,001 kg, angka tabel sudah dalam gram. d3..d5 = g gravitasi.
CHANNEL_UNITS = ("gram", "gram", "g", "g", "g", "°/s", "°/s", "°/s", "µT", "µT", "µT")
CHANNEL_NAMES = (
    "d1 (Force_1)",
    "d2 (Force_2)",
    "d3 (accel_X)",
    "d4 (accel_Y)",
    "d5 (accel_Z)",
    "d6 (gyro_X)",
    "d7 (gyro_Y)",
    "d8 (gyro_Z)",
    "d9 (mag_X)",
    "d10 (mag_Y)",
    "d11 (mag_Z)",
)
CALC_NAMES = ("Force_1", "Force_2", "roll", "pitch", "yaw")
CALC_UNITS = ("gram", "gram", "derajat", "derajat", "derajat")

STYLE = """
QWidget { background: #0f172a; color: #e2e8f0; font-size: 13px; }
QGroupBox {
    border: 1px solid #334155; border-radius: 8px; margin-top: 14px; padding: 8px;
    font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #94a3b8; }
QPushButton {
    background: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background: #334155; }
QPushButton:disabled { color: #64748b; background: #0f172a; }
QPushButton#primary { background: #0369a1; border-color: #0284c7; }
QPushButton#danger { background: #7f1d1d; border-color: #b91c1c; }
QTableWidget, QListWidget, QPlainTextEdit {
    background: #1e293b; border: 1px solid #334155; border-radius: 6px;
    gridline-color: #334155; alternate-background-color: #172033;
}
QHeaderView::section { background: #1e293b; color: #94a3b8; border: none; padding: 4px; }
QTabWidget::pane { border: 1px solid #334155; }
QTabBar::tab { background: #1e293b; padding: 8px 16px; margin-right: 2px; }
QTabBar::tab:selected { background: #0369a1; }
QProgressBar {
    border: 1px solid #334155; border-radius: 4px; text-align: center; background: #1e293b;
}
QProgressBar::chunk { background: #0284c7; }
QLabel#card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 8px; }
QSplitter::handle { background: #334155; }
QComboBox {
    background: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 4px 8px;
    min-width: 88px;
}
QComboBox:disabled { color: #64748b; background: #0f172a; }
QComboBox QAbstractItemView {
    background: #1e293b; color: #e2e8f0; selection-background-color: #0369a1;
}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"PalmLog Laptop {__version__}")
        self.resize(1100, 760)
        self.setStyleSheet(STYLE)
        pg.setConfigOptions(antialias=False, background="#0f172a", foreground="#cbd5e1")

        self.ble = BleService(self)
        self.connected = False
        self.busy = False
        self.measure = False
        self.streaming = False
        self.status = None
        self.files: list = []
        self.plg = None
        self.rpy_deg = None
        self.rpy_error = ""
        self._rpy_cache: dict[tuple[str, int], np.ndarray] = {}
        self._stream_q: deque[tuple[float, ...]] = deque(maxlen=800)
        self._stream_pending: list[tuple[float, ...]] = []

        tabs = QTabWidget()
        tabs.addTab(self._build_board(), "Board")
        tabs.addTab(self._build_files(), "Berkas")
        tabs.addTab(self._build_stream(), "Stream")
        tabs.addTab(self._build_analysis(), "Analisa")
        self.setCentralWidget(tabs)
        self.tabs = tabs

        self.ble.devices_found.connect(self._on_devices)
        self.ble.state_changed.connect(self._on_state)
        self.ble.status_received.connect(self._on_status)
        self.ble.files_received.connect(self._on_files)
        self.ble.download_progress.connect(self._on_progress)
        self.ble.download_finished.connect(self._on_downloaded)
        self.ble.notice.connect(self._log)
        self.ble.stream_sample.connect(self._on_stream_sample)
        self.ble.stream_ack.connect(self._on_stream_ack)
        self.ble.busy_changed.connect(self._on_busy)
        self.ble.start()

        self.poll = QTimer(self)
        self.poll.setInterval(2000)
        self.poll.timeout.connect(self._poll_status)
        self.poll.start()

        self.stream_timer = QTimer(self)
        self.stream_timer.setInterval(80)
        self.stream_timer.timeout.connect(self._flush_stream)
        self.stream_timer.start()

        self._log("Siap. Scan mencari PalmLog20, lalu Hubungkan.")
        self._refresh_local_bins()
        self._sync_buttons()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.ble.shutdown()
        super().closeEvent(event)

    def _build_board(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        left = QVBoxLayout()
        row = QHBoxLayout()
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setObjectName("primary")
        self.btn_scan.clicked.connect(self.ble.scan)
        self.btn_connect = QPushButton("Hubungkan")
        self.btn_connect.clicked.connect(self._connect_selected)
        self.btn_disconnect = QPushButton("Putuskan")
        self.btn_disconnect.clicked.connect(self.ble.disconnect)
        row.addWidget(self.btn_scan)
        row.addWidget(self.btn_connect)
        row.addWidget(self.btn_disconnect)
        self.device_list = QListWidget()
        self.device_list.itemDoubleClicked.connect(lambda _i: self._connect_selected())
        self.device_list.currentItemChanged.connect(lambda *_: self._sync_buttons())
        left.addLayout(row)
        left.addWidget(self.device_list, 1)

        right = QVBoxLayout()
        self.state_label = QLabel("Tidak terhubung")
        self.state_label.setWordWrap(True)
        right.addWidget(self.state_label)

        grid = QGridLayout()
        self.card_measure = QLabel("Measure\n—")
        self.card_power = QLabel("Daya\n—")
        self.card_rtc = QLabel("RTC\n—")
        self.card_files = QLabel("Berkas\n—")
        self.card_free = QLabel("Sisa kapasitas\n—")
        self.card_time = QLabel("Jam board\n—")
        for i, card in enumerate(
            (self.card_measure, self.card_power, self.card_rtc, self.card_files, self.card_free, self.card_time)
        ):
            card.setObjectName("card")
            card.setMinimumHeight(72)
            card.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(card, i // 2, i % 2)
        right.addLayout(grid)

        actions = QHBoxLayout()
        self.btn_status = QPushButton("Segarkan status")
        self.btn_status.clicked.connect(self.ble.refresh_status)
        self.btn_time = QPushButton("Setel waktu laptop")
        self.btn_time.setObjectName("primary")
        self.btn_time.clicked.connect(self.ble.set_time_now)
        actions.addWidget(self.btn_status)
        actions.addWidget(self.btn_time)
        right.addLayout(actions)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(200)
        self.log.setPlaceholderText("Log BLE")
        right.addWidget(self.log, 1)

        split = QSplitter()
        lw = QWidget()
        lw.setLayout(left)
        rw = QWidget()
        rw.setLayout(right)
        split.addWidget(lw)
        split.addWidget(rw)
        split.setStretchFactor(1, 1)
        root.addWidget(split)
        return page

    def _build_files(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        row = QHBoxLayout()
        self.btn_list = QPushButton("Muat daftar")
        self.btn_list.setObjectName("primary")
        self.btn_list.clicked.connect(self.ble.list_files)
        self.btn_download = QPushButton("Unduh")
        self.btn_download.clicked.connect(self._download_selected)
        self.btn_delete = QPushButton("Hapus di board")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_format = QPushButton("Format flash")
        self.btn_format.setObjectName("danger")
        self.btn_format.clicked.connect(self._confirm_format)
        row.addWidget(self.btn_list)
        row.addWidget(self.btn_download)
        row.addWidget(self.btn_delete)
        row.addWidget(self.btn_format)
        row.addStretch(1)
        lay.addLayout(row)

        self.capacity_label = QLabel(
            "Sisa kapasitas dihitung dari ujung alokasi (next_free). Hapus di tengah tidak mengembalikan ruang. "
            "Ruang penuh kembali setelah Format flash."
        )
        self.capacity_label.setWordWrap(True)
        self.capacity_label.setStyleSheet("color: #94a3b8;")
        lay.addWidget(self.capacity_label)

        self.file_table = QTableWidget(0, 5)
        self.file_table.setHorizontalHeaderLabels(["Nama", "Status", "Rekaman", "Ukuran", "Di laptop"])
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.itemSelectionChanged.connect(self._sync_buttons)
        lay.addWidget(self.file_table, 1)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("Tidak ada unduhan")
        lay.addWidget(self.progress)
        return page

    def _build_stream(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        row = QHBoxLayout()
        self.stream_measure = QLabel("Measure: —")
        self.stream_measure.setObjectName("card")
        self.btn_stream = QPushButton("Mulai stream")
        self.btn_stream.setObjectName("primary")
        self.btn_stream.clicked.connect(self._toggle_stream)
        row.addWidget(self.stream_measure, 1)
        row.addWidget(self.btn_stream)
        lay.addLayout(row)

        warn = QLabel(
            "Peringatan: Stream hanya untuk uji sensor. Jangan dipakai saat perekaman data "
            "sebenarnya — stream memperlambat tulis ke flash dan bisa membuat sampel hilang (drop)."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet(
            "background: #451a03; color: #fbbf24; border: 1px solid #f59e0b; "
            "border-radius: 8px; padding: 8px;"
        )
        lay.addWidget(warn)

        hint = QLabel(
            "FW 3.1.1 · paket 0xB2 = 29 B (seq + t_rel + d1…d11). "
            "Semua kanal digambar. Klik legend untuk menampilkan atau menyembunyikan. "
            "Hanya jika measure ON. Stop stream ≠ stop measure."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #94a3b8;")
        lay.addWidget(hint)

        self.stream_plot = pg.PlotWidget()
        self.stream_plot.showGrid(x=True, y=True, alpha=0.25)
        self.stream_plot.setLabel("bottom", "Sampel buffer", units="idx")
        self.stream_plot.setLabel("left", self._joined_units(CHANNEL_UNITS))
        self.stream_plot.addLegend(offset=(8, 8))
        self.stream_plot.plotItem.legend.sigSampleClicked.connect(self._on_stream_legend)
        self.stream_curves = []
        for i, color in enumerate(CHANNEL_COLORS):
            curve = self.stream_plot.plot(pen=pg.mkPen(color, width=1.6), name=CHANNEL_NAMES[i])
            self.stream_curves.append(curve)
        lay.addWidget(self.stream_plot, 1)
        return page

    def _build_analysis(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        row = QHBoxLayout()
        self.btn_open_bin = QPushButton("Buka .bin")
        self.btn_open_bin.setObjectName("primary")
        self.btn_open_bin.clicked.connect(self._open_bin)
        self.btn_folder = QPushButton("Pilih folder")
        self.btn_folder.clicked.connect(self._pick_folder)
        self.btn_reload_bins = QPushButton("Muat ulang daftar")
        self.btn_reload_bins.clicked.connect(self._refresh_local_bins)
        self.btn_csv = QPushButton("Ekspor CSV")
        self.btn_csv.clicked.connect(self._export_csv)
        self.mode_raw = QRadioButton("Raw data")
        self.mode_calc = QRadioButton("Calculated data")
        self.mode_raw.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.mode_raw)
        mode_group.addButton(self.mode_calc)
        self.filter_label = QLabel("Filter")
        self.filter_box = QComboBox()
        self.filter_box.addItem("Madgwick", "madgwick")
        self.filter_box.addItem("EKF", "ekf")
        self.axis_label = QLabel("Axis")
        self.axis_box = QComboBox()
        self.axis_box.addItem("6", 6)
        self.axis_box.addItem("9", 9)
        self.filter_box.currentIndexChanged.connect(self._on_attitude_option)
        self.axis_box.currentIndexChanged.connect(self._on_attitude_option)
        row.addWidget(self.btn_open_bin)
        row.addWidget(self.btn_folder)
        row.addWidget(self.btn_reload_bins)
        row.addWidget(self.btn_csv)
        row.addWidget(self.mode_raw)
        row.addWidget(self.mode_calc)
        row.addWidget(self.filter_label)
        row.addWidget(self.filter_box)
        row.addWidget(self.axis_label)
        row.addWidget(self.axis_box)
        row.addStretch(1)
        lay.addLayout(row)

        self.folder_label = QLabel(str(DATA))
        self.folder_label.setStyleSheet("color: #94a3b8;")
        self.analysis_root = DATA
        lay.addWidget(self.folder_label)

        split = QSplitter()
        side_split = QSplitter(Qt.Orientation.Vertical)
        side_split.setChildrenCollapsible(False)
        side_split.setHandleWidth(6)
        self.bin_list = QListWidget()
        self.bin_list.setMinimumHeight(80)
        self.bin_list.itemClicked.connect(self._open_listed_bin)
        side_split.addWidget(self.bin_list)
        self.bin_info = QLabel("Belum ada berkas.")
        self.bin_info.setWordWrap(True)
        self.bin_info.setObjectName("card")
        self.bin_info.setMinimumHeight(48)
        side_split.addWidget(self.bin_info)

        self.stats_table = QTableWidget(N_CHANNELS, 5)
        self.stats_table.setHorizontalHeaderLabels(["Kanal", "Unit", "Min", "Max", "Rata-rata"])
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stats_table.setMinimumHeight(80)
        side_split.addWidget(self.stats_table)
        side_split.setStretchFactor(0, 1)
        side_split.setSizes([420, 110, 260])
        split.addWidget(side_split)

        plot_side = QWidget()
        plot_lay = QVBoxLayout(plot_side)
        plot_lay.setContentsMargins(0, 0, 0, 0)
        self.analysis_plot = pg.PlotWidget()
        self.analysis_plot.showGrid(x=True, y=True, alpha=0.25)
        self.analysis_plot.setLabel("bottom", "t_rel", units="s")
        self.analysis_plot.setLabel("left", self._joined_units(CHANNEL_UNITS))
        self.analysis_plot.addLegend(offset=(8, 8))
        plot_item = self.analysis_plot.plotItem
        self.analysis_right = pg.ViewBox()
        plot_item.showAxis("right")
        plot_item.scene().addItem(self.analysis_right)
        right_axis = plot_item.getAxis("right")
        right_axis.linkToView(self.analysis_right)
        right_axis.setLabel("derajat", color="#e2e8f0")
        right_axis.setPen(pg.mkPen("#e2e8f0"))
        right_axis.setTextPen(pg.mkPen("#e2e8f0"))
        self.analysis_right.setXLink(plot_item)
        plot_item.hideAxis("right")
        plot_item.vb.sigResized.connect(self._sync_right_axis)
        self.analysis_curves = []
        for i, color in enumerate(CHANNEL_COLORS):
            curve = self.analysis_plot.plot(
                pen=pg.mkPen(color, width=1.4),
                autoDownsample=True,
                downsampleMethod="peak",
                clipToView=True,
                skipFiniteCheck=True,
            )
            self.analysis_curves.append(curve)
        self.calc_force_curves = []
        for i in range(2):
            curve = self.analysis_plot.plot(
                pen=pg.mkPen(CHANNEL_COLORS[i], width=1.6),
                autoDownsample=True,
                downsampleMethod="peak",
                clipToView=True,
                skipFiniteCheck=True,
            )
            curve.setVisible(False)
            self.calc_force_curves.append(curve)
        self.calc_angle_curves = []
        for i in range(3):
            curve = pg.PlotDataItem(
                pen=pg.mkPen(CHANNEL_COLORS[i + 2], width=1.4),
                autoDownsample=True,
                downsampleMethod="peak",
                clipToView=True,
                skipFiniteCheck=True,
            )
            curve.setVisible(False)
            self.analysis_right.addItem(curve)
            self.calc_angle_curves.append(curve)
        plot_item.legend.sigSampleClicked.connect(self._on_analysis_legend)
        self.mode_raw.toggled.connect(self._on_data_mode)
        self.mode_calc.toggled.connect(self._on_data_mode)
        self._apply_analysis_mode()
        self._fill_stats()
        plot_lay.addWidget(self.analysis_plot, 1)
        split.addWidget(plot_side)
        split.setStretchFactor(1, 1)
        lay.addWidget(split, 1)
        return page

    def _log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.appendPlainText(f"{stamp}  {text}")
        self.statusBar().showMessage(text, 8000)

    def _sync_buttons(self) -> None:
        if not hasattr(self, "btn_csv"):
            return
        online = self.connected and not self.busy
        self.btn_scan.setEnabled(not self.connected and not self.busy)
        self.btn_connect.setEnabled(not self.connected and not self.busy and self.device_list.currentItem() is not None)
        self.btn_disconnect.setEnabled(self.connected and not self.busy)
        self.btn_status.setEnabled(online)
        self.btn_time.setEnabled(online)
        self.btn_list.setEnabled(online)
        has_row = self.file_table.currentRow() >= 0
        self.btn_download.setEnabled(online and has_row)
        self.btn_delete.setEnabled(online and has_row)
        self.btn_format.setEnabled(online and not self.measure)
        can_stream = online and (self.measure or self.streaming)
        self.btn_stream.setEnabled(can_stream)
        self.btn_stream.setText("Stop stream" if self.streaming else "Mulai stream")
        self.btn_csv.setEnabled(self.plg is not None)

    def _on_busy(self, busy: bool) -> None:
        self.busy = busy
        self._sync_buttons()

    def _on_state(self, state: str, detail: str) -> None:
        self.connected = state == "connected"
        if not self.connected:
            self.streaming = False
            self._stream_pending.clear()
            self._stream_q.clear()
        self.state_label.setText(detail or state)
        if state == "scanning":
            self._log(detail)
        self._sync_buttons()

    def _on_devices(self, rows: list) -> None:
        self.device_list.clear()
        for name, address, rssi, target in rows:
            mark = "PalmLog" if target else "lain"
            item = QListWidgetItem(f"{name}    {address}    {rssi} dBm    {mark}")
            item.setData(Qt.ItemDataRole.UserRole, address)
            item.setData(Qt.ItemDataRole.UserRole + 1, name)
            if target:
                item.setForeground(Qt.GlobalColor.cyan)
            self.device_list.addItem(item)
        if self.device_list.count():
            self.device_list.setCurrentRow(0)
        self._log(f"Scan selesai, {self.device_list.count()} perangkat.")
        self._sync_buttons()

    def _connect_selected(self) -> None:
        item = self.device_list.currentItem()
        if item is None:
            return
        address = item.data(Qt.ItemDataRole.UserRole)
        name = item.data(Qt.ItemDataRole.UserRole + 1) or ""
        self.ble.connect_to(address, name)

    def _on_status(self, status) -> None:
        self.status = status
        self.measure = status.measure
        if not status.measure and self.streaming:
            self.streaming = False
            self._log("Measure berhenti, stream ikut berhenti.")
        self.card_measure.setText(f"Measure\n{'AKTIF' if status.measure else 'BERHENTI'}")
        if status.usb:
            power = "USB (selalu ON)"
        elif status.battery_mv is None:
            power = "Baterai"
        else:
            power = f"Baterai · {status.battery_mv / 1000:.2f} V"
        self.card_power.setText(f"Daya\n{power}")
        self.card_rtc.setText(f"RTC\n{'OK' if status.rtc_ok else 'tidak siap'}")
        self.card_files.setText(f"Berkas di board\n{status.file_count}")
        free = status.free_bytes
        if free is None:
            free_text = "—"
        else:
            free_text = f"{format_bytes(free)}\n{format_duration(status.free_seconds or 0)} ukur"
        self.card_free.setText(f"Sisa kapasitas\n{free_text}")
        if status.unix_s:
            dt = datetime.fromtimestamp(status.unix_s, tz=timezone.utc)
            clock = dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            clock = "—"
        self.card_time.setText(f"Jam board\n{clock}")
        self.stream_measure.setText(
            f"Measure: {'AKTIF' if status.measure else 'BERHENTI'}    "
            f"next_free 0x{status.next_free:X}    flash {format_bytes(FLASH_SIZE)}"
        )
        if free is None:
            self.capacity_label.setText("Kapasitas belum diketahui. Segarkan status.")
        else:
            self.capacity_label.setText(
                f"Berkas di board: {status.file_count}. Sisa {format_bytes(free)} "
                f"({format_duration(status.free_seconds or 0)} pada 26 B / 10 ms, PLG1 v4). "
                "Angka ini hanya ekor setelah next_free, bukan lubang hapus di tengah."
            )
        self._sync_buttons()

    def _poll_status(self) -> None:
        if self.connected and not self.busy:
            self.ble.refresh_status()

    def _on_files(self, items: list) -> None:
        self.files = list(items)
        self.file_table.setRowCount(len(items))
        for row, item in enumerate(items):
            local = bin_path(self.ble.address, item.name) if self.ble.address else None
            present = "ada" if local is not None and local.is_file() else "—"
            flag = "terbuka" if item.open else "tertutup" if item.closed else f"0x{item.flags:02X}"
            values = [item.file_name, flag, str(item.n_records), format_bytes(item.byte_size), present]
            for col, text in enumerate(values):
                self.file_table.setItem(row, col, QTableWidgetItem(text))
        self.file_table.resizeColumnsToContents()
        self._sync_buttons()

    def _selected_file(self):
        row = self.file_table.currentRow()
        if row < 0 or row >= len(self.files):
            return None
        return self.files[row]

    def _download_selected(self) -> None:
        item = self._selected_file()
        if item is None:
            return
        if item.open:
            self._log("Berkas masih terbuka. Hentikan measure di board dulu.")
            return
        self.progress.setFormat(f"Mengunduh {item.file_name} %p%")
        self.progress.setValue(0)
        self.ble.download(item.name, item.byte_size)

    def _on_progress(self, name: str, got: int, total: int) -> None:
        pct = int(got * 100 / total) if total else 0
        self.progress.setValue(min(100, pct))
        self.progress.setFormat(f"{name}  {format_bytes(got)} / {format_bytes(total)}")

    def _on_downloaded(self, name: str, path: str) -> None:
        self.progress.setValue(100)
        self.progress.setFormat(f"Selesai {Path(path).name}")
        self._on_files(self.files)
        self.analysis_root = Path(path).parent
        self.folder_label.setText(str(self.analysis_root))
        self._refresh_local_bins()

    def _delete_selected(self) -> None:
        item = self._selected_file()
        if item is None:
            return
        answer = QMessageBox.question(
            self,
            "Hapus di board",
            f"Hapus {item.file_name} dari daftar flash?\n\n"
            "Salinan di laptop tidak ikut terhapus.\n"
            "Kapasitas flash tidak kembali, kecuali berkas ini tepat di ujung alokasi. "
            "Ruang penuh kembali hanya setelah Format flash.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.ble.delete_file(item.name)

    def _confirm_format(self) -> None:
        answer = QMessageBox.warning(
            self,
            "Format flash",
            "Seluruh isi W25Q32 akan dihapus (chip erase, sekitar 10–40 detik).\n"
            "Berkas yang sudah diunduh di laptop tetap ada.\n\nLanjutkan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.progress.setFormat("Format berjalan…")
            self.ble.format_flash()

    def _toggle_stream(self) -> None:
        if not self.streaming and not self.measure:
            self._log("Measure mati. Stream ditolak sampai measure ON.")
            return
        self.ble.set_stream(not self.streaming)

    def _on_stream_ack(self, code: int) -> None:
        if code == 0:
            self.streaming = True
            self._stream_q.clear()
            self._stream_pending.clear()
        elif code == 2:
            self.streaming = False
        self._sync_buttons()

    def _on_stream_sample(self, sample) -> None:
        self._stream_pending.append(sample.physical_tuple())

    def _flush_stream(self) -> None:
        if not self._stream_pending:
            return
        self._stream_q.extend(self._stream_pending)
        self._stream_pending.clear()
        arr = np.asarray(self._stream_q, dtype=np.float64)
        x = np.arange(arr.shape[0], dtype=np.float64)
        for i, curve in enumerate(self.stream_curves):
            curve.setData(x, arr[:, i])

    def _joined_units(self, units: tuple[str, ...]) -> str:
        seen: list[str] = []
        for unit in units:
            if unit not in seen:
                seen.append(unit)
        return ", ".join(seen)

    def _visible_units(self, curves, units: tuple[str, ...]) -> str:
        seen: list[str] = []
        for curve, unit in zip(curves, units):
            if curve.isVisible() and unit not in seen:
                seen.append(unit)
        return ", ".join(seen)

    def _on_stream_legend(self, _item) -> None:
        self.stream_plot.setLabel("left", self._visible_units(self.stream_curves, CHANNEL_UNITS))
        self.stream_plot.enableAutoRange(axis="y")

    def _pick_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Folder berkas .bin", str(self.analysis_root))
        if not chosen:
            return
        self.analysis_root = Path(chosen)
        self.folder_label.setText(str(self.analysis_root))
        self._refresh_local_bins()

    def _refresh_local_bins(self) -> None:
        self.bin_list.clear()
        root = self.analysis_root
        if not root.exists():
            return
        found: list[Path] = []
        if root.is_file() and root.suffix.lower() == ".bin":
            found = [root]
        else:
            for path in root.rglob("*.bin"):
                found.append(path)
                if len(found) >= 400:
                    break
        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for path in found:
            item = QListWidgetItem(str(path.relative_to(root) if path.is_relative_to(root) else path))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.bin_list.addItem(item)

    def _open_bin(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Buka berkas PLG1", str(self.analysis_root), "PalmLog bin (*.bin)"
        )
        if chosen:
            self.analysis_root = Path(chosen).parent
            self.folder_label.setText(str(self.analysis_root))
            self._refresh_local_bins()
            self._load_plg(Path(chosen))

    def _open_listed_bin(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self._load_plg(Path(path))

    def _load_plg(self, path: Path) -> None:
        try:
            self.plg = parse_plg(path)
        except Exception as exc:
            self.plg = None
            self.rpy_deg = None
            self.rpy_error = ""
            self._rpy_cache.clear()
            self.bin_info.setText(str(exc))
            self._push_plot_data()
            self._fill_stats()
            self._sync_buttons()
            return
        self._rpy_cache.clear()
        self._compute_rpy()
        self._show_bin_info()
        self._push_plot_data()
        self._fill_stats()
        self._sync_buttons()
        self._log(f"Analisa {self.plg.path.name}: {self.plg.count} rekaman")

    def _attitude_choice(self) -> tuple[str, int]:
        return str(self.filter_box.currentData()), int(self.axis_box.currentData())

    def _attitude_note(self) -> str:
        if self.rpy_error:
            return f"Sudut tidak dihitung: {self.rpy_error}"
        method, axes = self._attitude_choice()
        label = "EKF" if method == "ekf" else "Madgwick"
        if axes == 9:
            yaw = "Yaw memakai magnetometer mentah."
        else:
            yaw = "Yaw relatif, bukan kompas."
        return f"Calculated data: {label}, {axes} sumbu. {yaw}"

    def _show_bin_info(self) -> None:
        plg = self.plg
        if plg is None:
            return
        self.bin_info.setText(
            f"{plg.path.name}\n"
            f"PLG1 v{plg.version} · {plg.channels} kanal · {plg.record_size} B/rekaman · periode {plg.period_ms} ms\n"
            f"Mulai: {plg.start_text}\n"
            f"{plg.count} rekaman · {plg.duration_s:.2f} dtk\n"
            f"{self._attitude_note()}"
        )

    def _compute_rpy(self) -> None:
        plg = self.plg
        if plg is None or plg.count == 0:
            self.rpy_deg = None
            self.rpy_error = ""
            return
        key = self._attitude_choice()
        cached = self._rpy_cache.get(key)
        if cached is not None:
            self.rpy_deg = cached
            self.rpy_error = ""
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.rpy_deg = attitude_rpy_deg(
                plg.time_s,
                plg.physical[:, 2:5],
                plg.physical[:, 5:8],
                plg.physical[:, 8:11],
                method=key[0],
                axes=key[1],
            )
            self.rpy_error = ""
            self._rpy_cache[key] = self.rpy_deg
        except Exception as exc:
            self.rpy_deg = np.full((plg.count, 3), np.nan)
            self.rpy_error = str(exc)
        finally:
            QApplication.restoreOverrideCursor()

    def _on_data_mode(self, checked: bool) -> None:
        if not checked:
            return
        self._apply_analysis_mode()
        self._fill_stats()

    def _sync_right_axis(self) -> None:
        view = self.analysis_plot.plotItem.vb
        self.analysis_right.setGeometry(view.sceneBoundingRect())
        self.analysis_right.linkedViewChanged(view, self.analysis_right.XAxis)

    def _set_legend(self, curves, names: tuple[str, ...]) -> None:
        legend = self.analysis_plot.plotItem.legend
        legend.clear()
        for curve, name in zip(curves, names):
            legend.addItem(curve, name)

    def _apply_analysis_mode(self) -> None:
        raw = self.mode_raw.isChecked()
        plot_item = self.analysis_plot.plotItem
        if raw:
            for curve in self.analysis_curves:
                curve.setVisible(True)
            for curve in self.calc_force_curves + self.calc_angle_curves:
                curve.setVisible(False)
            plot_item.hideAxis("right")
            self._set_legend(self.analysis_curves, CHANNEL_NAMES)
            self.analysis_plot.setLabel("left", self._visible_units(self.analysis_curves, CHANNEL_UNITS))
        else:
            for curve in self.analysis_curves:
                curve.setVisible(False)
            for curve in self.calc_force_curves + self.calc_angle_curves:
                curve.setVisible(True)
            plot_item.showAxis("right")
            self._sync_right_axis()
            self._set_legend(self.calc_force_curves + self.calc_angle_curves, CALC_NAMES)
            self.analysis_plot.setLabel("left", "gram")
            plot_item.getAxis("right").setLabel("derajat", color="#e2e8f0")
        self.analysis_plot.enableAutoRange()
        self.analysis_right.enableAutoRange(axis="y")
        self._sync_attitude_options()

    def _sync_attitude_options(self) -> None:
        enabled = self.mode_calc.isChecked()
        self.filter_label.setEnabled(enabled)
        self.filter_box.setEnabled(enabled)
        self.axis_label.setEnabled(enabled)
        self.axis_box.setEnabled(enabled)

    def _on_attitude_option(self) -> None:
        if self.plg is None or not self.mode_calc.isChecked():
            return
        self._compute_rpy()
        self._show_bin_info()
        self._push_plot_data()
        self._fill_stats()

    def _on_analysis_legend(self, _item) -> None:
        if self.mode_raw.isChecked():
            self.analysis_plot.setLabel(
                "left", self._visible_units(self.analysis_curves, CHANNEL_UNITS)
            )
        self.analysis_plot.enableAutoRange(axis="y")
        self.analysis_right.enableAutoRange(axis="y")

    def _push_plot_data(self) -> None:
        plg = self.plg
        curves = self.analysis_curves + self.calc_force_curves + self.calc_angle_curves
        if plg is None or plg.count == 0:
            for curve in curves:
                curve.setData([], [])
            return
        time_s = plg.time_s
        for i, curve in enumerate(self.analysis_curves):
            curve.setData(time_s, plg.physical[:, i])
        for i, curve in enumerate(self.calc_force_curves):
            curve.setData(time_s, plg.physical[:, i])
        if self.rpy_deg is None:
            for curve in self.calc_angle_curves:
                curve.setData([], [])
        else:
            for i, curve in enumerate(self.calc_angle_curves):
                curve.setData(time_s, self.rpy_deg[:, i])
        self.analysis_plot.enableAutoRange()
        self.analysis_right.enableAutoRange(axis="y")

    def _fill_stats(self) -> None:
        calculated = self.mode_calc.isChecked()
        if calculated:
            names, units = CALC_NAMES, CALC_UNITS
            columns = None
            if self.plg is not None and self.rpy_deg is not None:
                columns = [
                    self.plg.physical[:, 0],
                    self.plg.physical[:, 1],
                    self.rpy_deg[:, 0],
                    self.rpy_deg[:, 1],
                    self.rpy_deg[:, 2],
                ]
        else:
            names, units = CHANNEL_NAMES, CHANNEL_UNITS
            columns = None
            if self.plg is not None and self.plg.count:
                columns = [self.plg.physical[:, i] for i in range(N_CHANNELS)]
        self.stats_table.setRowCount(len(names))
        for i, name in enumerate(names):
            self.stats_table.setItem(i, 0, QTableWidgetItem(name))
            self.stats_table.setItem(i, 1, QTableWidgetItem(units[i]))
            lo, hi, avg = self._format_column(None if columns is None else columns[i])
            self.stats_table.setItem(i, 2, QTableWidgetItem(lo))
            self.stats_table.setItem(i, 3, QTableWidgetItem(hi))
            self.stats_table.setItem(i, 4, QTableWidgetItem(avg))
        self.stats_table.resizeColumnToContents(0)

    @staticmethod
    def _format_column(values) -> tuple[str, str, str]:
        if values is None or len(values) == 0:
            return "—", "—", "—"
        finite = np.asarray(values, dtype=np.float64)
        finite = finite[np.isfinite(finite)]
        if finite.size == 0:
            return "—", "—", "—"
        return f"{finite.min():.4g}", f"{finite.max():.4g}", f"{finite.mean():.4g}"

    def _export_csv(self) -> None:
        if self.plg is None:
            return
        calculated = self.mode_calc.isChecked()
        if calculated:
            suggested = str(self.plg.path.with_name(self.plg.path.stem + "_calculated.csv"))
        else:
            suggested = str(self.plg.path.with_suffix(".csv"))
        dest, _ = QFileDialog.getSaveFileName(self, "Ekspor CSV", suggested, "CSV (*.csv)")
        if not dest:
            return
        if calculated:
            if self.rpy_deg is None:
                QMessageBox.warning(self, "Ekspor CSV", "Sudut belum tersedia untuk berkas ini.")
                return
            export_calculated_csv(self.plg, self.rpy_deg, Path(dest))
        else:
            export_csv(self.plg, Path(dest))
        self._log(f"CSV tersimpan {dest}")

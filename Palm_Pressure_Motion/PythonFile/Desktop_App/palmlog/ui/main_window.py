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
    QCheckBox,
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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from palmlog import __version__
from palmlog.client import BleService
from palmlog.plg import export_csv, parse_plg
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

        chips = QHBoxLayout()
        self.stream_checks: list[QCheckBox] = []
        for i in range(N_CHANNELS):
            box = QCheckBox(f"d{i + 1}")
            box.setChecked(i == 0)
            box.toggled.connect(self._apply_stream_visibility)
            self.stream_checks.append(box)
            chips.addWidget(box)
        all_btn = QPushButton("Semua")
        all_btn.clicked.connect(lambda: self._set_checks(self.stream_checks, True))
        one_btn = QPushButton("d1 saja")
        one_btn.clicked.connect(lambda: self._set_checks(self.stream_checks, False))
        chips.addWidget(all_btn)
        chips.addWidget(one_btn)
        lay.addLayout(chips)

        hint = QLabel(
            "FW 3.1.1 · paket 0xB2 = 29 B (seq + t_rel + d1…d11). "
            "Y = nilai fisik (g / °/s / µT). Hanya jika measure ON. Stop stream ≠ stop measure."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #94a3b8;")
        lay.addWidget(hint)

        self.stream_plot = pg.PlotWidget()
        self.stream_plot.showGrid(x=True, y=True, alpha=0.25)
        self.stream_plot.setLabel("bottom", "Sampel buffer", units="idx")
        self.stream_plot.setLabel("left", "Fisik")
        self.stream_plot.addLegend(offset=(8, 8))
        self.stream_curves = []
        for i, color in enumerate(CHANNEL_COLORS):
            curve = self.stream_plot.plot(pen=pg.mkPen(color, width=1.6), name=f"d{i + 1}")
            curve.setVisible(i == 0)
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
        row.addWidget(self.btn_open_bin)
        row.addWidget(self.btn_folder)
        row.addWidget(self.btn_reload_bins)
        row.addWidget(self.btn_csv)
        row.addStretch(1)
        lay.addLayout(row)

        self.folder_label = QLabel(str(DATA))
        self.folder_label.setStyleSheet("color: #94a3b8;")
        self.analysis_root = DATA
        lay.addWidget(self.folder_label)

        split = QSplitter()
        side = QWidget()
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(0, 0, 0, 0)
        self.bin_list = QListWidget()
        self.bin_list.itemClicked.connect(self._open_listed_bin)
        side_lay.addWidget(self.bin_list, 1)
        self.bin_info = QLabel("Belum ada berkas.")
        self.bin_info.setWordWrap(True)
        self.bin_info.setObjectName("card")
        side_lay.addWidget(self.bin_info)

        self.stats_table = QTableWidget(N_CHANNELS, 5)
        self.stats_table.setHorizontalHeaderLabels(["Kanal", "Unit", "Min", "Max", "Rata-rata"])
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stats_table.setMaximumHeight(320)
        units = ["", "", "g", "g", "g", "°/s", "°/s", "°/s", "µT", "µT", "µT"]
        for i in range(N_CHANNELS):
            self.stats_table.setItem(i, 0, QTableWidgetItem(f"d{i + 1}"))
            self.stats_table.setItem(i, 1, QTableWidgetItem(units[i]))
        side_lay.addWidget(self.stats_table)
        split.addWidget(side)

        plot_side = QWidget()
        plot_lay = QVBoxLayout(plot_side)
        plot_lay.setContentsMargins(0, 0, 0, 0)
        chips = QHBoxLayout()
        self.analysis_checks: list[QCheckBox] = []
        for i in range(N_CHANNELS):
            box = QCheckBox(f"d{i + 1}")
            box.setChecked(i == 0)
            box.toggled.connect(self._redraw_analysis)
            self.analysis_checks.append(box)
            chips.addWidget(box)
        chips.addWidget(self._mini_button("Semua", lambda: self._set_checks(self.analysis_checks, True)))
        chips.addWidget(self._mini_button("d1 saja", lambda: self._set_checks(self.analysis_checks, False)))
        plot_lay.addLayout(chips)
        self.analysis_plot = pg.PlotWidget()
        self.analysis_plot.showGrid(x=True, y=True, alpha=0.25)
        self.analysis_plot.setLabel("bottom", "t_rel", units="s")
        self.analysis_plot.setLabel("left", "Fisik")
        self.analysis_plot.addLegend(offset=(8, 8))
        self.analysis_curves = []
        for i, color in enumerate(CHANNEL_COLORS):
            curve = self.analysis_plot.plot(
                pen=pg.mkPen(color, width=1.4),
                name=f"d{i + 1}",
                autoDownsample=True,
                downsampleMethod="peak",
                clipToView=True,
                skipFiniteCheck=True,
            )
            curve.setVisible(i == 0)
            self.analysis_curves.append(curve)
        plot_lay.addWidget(self.analysis_plot, 1)
        split.addWidget(plot_side)
        split.setStretchFactor(1, 1)
        lay.addWidget(split, 1)
        return page

    def _mini_button(self, text: str, handler) -> QPushButton:
        btn = QPushButton(text)
        btn.clicked.connect(handler)
        return btn

    def _set_checks(self, boxes: list[QCheckBox], all_on: bool) -> None:
        for i, box in enumerate(boxes):
            box.setChecked(True if all_on else i == 0)

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

    def _apply_stream_visibility(self) -> None:
        for box, curve in zip(self.stream_checks, self.stream_curves):
            curve.setVisible(box.isChecked())

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
            self.bin_info.setText(str(exc))
            self._sync_buttons()
            return
        plg = self.plg
        self.bin_info.setText(
            f"{plg.path.name}\n"
            f"PLG1 v{plg.version} · {plg.channels} kanal · {plg.record_size} B/rekaman · periode {plg.period_ms} ms\n"
            f"Mulai: {plg.start_text}\n"
            f"{plg.count} rekaman · {plg.duration_s:.2f} dtk"
        )
        for i in range(N_CHANNELS):
            lo, hi, avg = plg.stats(i)
            self.stats_table.setItem(i, 2, QTableWidgetItem(f"{lo:.4g}"))
            self.stats_table.setItem(i, 3, QTableWidgetItem(f"{hi:.4g}"))
            self.stats_table.setItem(i, 4, QTableWidgetItem(f"{avg:.4g}"))
        self._redraw_analysis()
        self._sync_buttons()
        self._log(f"Analisa {plg.path.name}: {plg.count} rekaman")

    def _redraw_analysis(self) -> None:
        plg = self.plg
        if plg is None or plg.count == 0:
            for curve in self.analysis_curves:
                curve.setData([], [])
            return
        for i, (box, curve) in enumerate(zip(self.analysis_checks, self.analysis_curves)):
            curve.setVisible(box.isChecked())
            if box.isChecked():
                curve.setData(plg.time_s, plg.physical[:, i])
            else:
                curve.setData([], [])

    def _export_csv(self) -> None:
        if self.plg is None:
            return
        suggested = str(self.plg.path.with_suffix(".csv"))
        dest, _ = QFileDialog.getSaveFileName(self, "Ekspor CSV", suggested, "CSV (*.csv)")
        if not dest:
            return
        export_csv(self.plg, Path(dest))
        self._log(f"CSV tersimpan {dest}")

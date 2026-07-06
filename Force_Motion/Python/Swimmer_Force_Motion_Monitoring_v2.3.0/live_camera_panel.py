"""
Panel kamera tab Live: preview dan rekam video (v2.3.0).

Pemindaian dan pemilihan kamera lewat dialog **Setting → Live → Camera**.
Rekam ``.mp4`` ke ``DataLog/`` (basename sama dengan CSV) saat **Start Log** jika
preview aktif; berhenti saat **Stop Log``. Modul ``live_camera_core`` menangani
probe OpenCV (MSMF/DSHOW) dan penekanan log.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import cv2
from PySide6.QtCore import QMutex, QMutexLocker, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from live_camera_core import (
    CameraInfo,
    CameraScanWorker,
    configure_capture_resolution,
    quiet_opencv,
)

_CAMERA_TABLE_ROW_HEIGHT = 32
_CAMERA_TABLE_MIN_ROWS = 3
_CAMERA_TABLE_DIALOG_ROWS = 6
_CAMERA_TABLE_HEADER_MIN = 34
_LIVE_PRIMARY_BUTTON_STYLE = """
QPushButton {
    padding: 8px 12px;
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:disabled {
    background-color: #6b7280;
    color: #d1d5db;
}
"""
_STATUS_BAR_STYLE = (
    "color: #9ca3af; font-size: 9pt; font-family: Consolas, 'Courier New', monospace;"
    " padding: 4px 2px;"
)
_DIALOG_STYLE = """
QDialog {
    background-color: #111827;
}
QLabel { color: #e5e7eb; }
QTableWidget {
    background: #1f2937;
    color: #e5e7eb;
    gridline-color: #374151;
    border: 1px solid #374151;
    border-radius: 8px;
}
QHeaderView::section {
    background: #374151;
    color: #e5e7eb;
    padding: 6px;
    border: none;
}
"""


def _frame_to_qimage(frame) -> QImage:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    return QImage(rgb.copy(), w, h, ch * w, QImage.Format.Format_RGB888)


def _camera_table_viewport_height(table: QTableWidget, visible_rows: int) -> int:
    """Tinggi widget agar ``visible_rows`` baris isi tampil penuh (tanpa terpotong)."""
    header = table.horizontalHeader()
    header_h = max(header.height(), header.sizeHint().height(), _CAMERA_TABLE_HEADER_MIN)
    row_h = table.verticalHeader().defaultSectionSize()
    if row_h <= 0:
        row_h = _CAMERA_TABLE_ROW_HEIGHT
    frame = table.frameWidth() * 2
    return header_h + visible_rows * row_h + frame + 4


def _section_widget(parent: QWidget | None = None) -> tuple[QWidget, QVBoxLayout]:
    box = QWidget(parent)
    box.setStyleSheet(
        "background: #1f2937; border: 1px solid #374151; border-radius: 10px;"
    )
    layout = QVBoxLayout(box)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)
    return box, layout


class PreviewAspectContainer(QWidget):
    """Bingkai preview dengan rasio lebar:tinggi tetap 16:9."""

    _ASPECT = 16.0 / 9.0

    def __init__(
        self,
        preview: QLabel,
        parent: QWidget | None = None,
        *,
        on_layout: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._preview = preview
        self._on_layout = on_layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(preview, 0, Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        avail_w = max(self.width(), 1)
        avail_h = max(self.height(), 1)
        w = avail_w
        h = int(round(w / self._ASPECT))
        if h > avail_h:
            h = avail_h
            w = int(round(h * self._ASPECT))
        w = max(w, 1)
        h = max(h, 1)
        self._preview.setFixedSize(w, h)
        if self._on_layout is not None:
            self._on_layout()


class CameraCaptureThread(QThread):
    """Baca frame kamera di thread terpisah; tulis ke VideoWriter saat rekam."""

    frame_ready = Signal(QImage)
    opened = Signal(bool)
    stream_info = Signal(int, int, float)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._mutex = QMutex()
        self._camera: CameraInfo | None = None
        self._stop = False
        self._recording = False
        self._record_path: Path | None = None
        self._writer: cv2.VideoWriter | None = None
        self._writer_size: tuple[int, int] | None = None
        self._writer_fps = 30.0

    def request_stop(self) -> None:
        with QMutexLocker(self._mutex):
            self._stop = True

    def set_camera(self, camera: CameraInfo | None) -> None:
        with QMutexLocker(self._mutex):
            self._camera = camera

    def start_recording(self, path: Path) -> None:
        with QMutexLocker(self._mutex):
            self._record_path = path
            self._recording = True

    def stop_recording(self) -> None:
        with QMutexLocker(self._mutex):
            self._recording = False
            self._record_path = None

    def _release_writer(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        self._writer_size = None

    def _ensure_writer(self, frame, path: Path, fps: float) -> bool:
        h, w = frame.shape[:2]
        if self._writer is not None and self._writer_size == (w, h):
            return True
        self._release_writer()
        writer_fps = fps if fps > 1.0 else 30.0
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(path), fourcc, writer_fps, (w, h))
        if not writer.isOpened():
            writer.release()
            return False
        self._writer = writer
        self._writer_size = (w, h)
        self._writer_fps = writer_fps
        return True

    def run(self) -> None:
        cap: cv2.VideoCapture | None = None
        active_index: int | None = None
        active_backend: int | None = None

        while True:
            with QMutexLocker(self._mutex):
                if self._stop:
                    break
                camera = self._camera
                want_record = self._recording
                record_path = self._record_path

            if camera is None or not camera.active:
                if cap is not None:
                    cap.release()
                    cap = None
                    active_index = None
                    self._release_writer()
                    self.opened.emit(False)
                self.msleep(80)
                continue

            if cap is None or active_index != camera.index or active_backend != camera.backend:
                if cap is not None:
                    cap.release()
                with quiet_opencv():
                    cap = cv2.VideoCapture(camera.index, camera.backend)
                if cap is None or not cap.isOpened():
                    if cap is not None:
                        cap.release()
                    cap = None
                    active_index = None
                    self._release_writer()
                    self.opened.emit(False)
                    self.error.emit(f"Kamera [{camera.index}] {camera.name} tidak bisa dibuka.")
                    self.msleep(500)
                    continue
                with quiet_opencv():
                    width, height, fps = configure_capture_resolution(cap)
                camera.fps = fps
                camera.width = width
                camera.height = height
                self.stream_info.emit(width, height, fps)
                active_index = camera.index
                active_backend = camera.backend
                self.opened.emit(True)

            ok, frame = cap.read()
            if not ok:
                self.msleep(30)
                continue

            if want_record and record_path is not None:
                fps = camera.fps if camera.fps > 1.0 else 30.0
                if not self._ensure_writer(frame, record_path, fps):
                    self.error.emit(f"Gagal memulai rekam video:\n{record_path}")
                    with QMutexLocker(self._mutex):
                        self._recording = False
                        self._record_path = None
                elif self._writer is not None:
                    self._writer.write(frame)

            if not want_record and self._writer is not None:
                self._release_writer()

            self.frame_ready.emit(_frame_to_qimage(frame))
            self.msleep(1)

        if cap is not None:
            cap.release()
        self._release_writer()


class LiveCameraSettingsDialog(QDialog):
    """Dialog pindai dan pilih kamera aktif untuk tab Live."""

    def __init__(self, panel: LiveCameraPanel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._panel = panel
        self.setWindowTitle("Kamera Live")
        self.setStyleSheet(_DIALOG_STYLE)
        self.setMinimumSize(640, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(panel.build_scan_section(self), 1)

        self._active_label = QLabel(self)
        self._active_label.setWordWrap(True)
        self._active_label.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        root.addWidget(self._active_label, 0)

        panel.camera_selection_changed.connect(self._update_active_label)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._panel.apply_camera_table_height(_CAMERA_TABLE_DIALOG_ROWS)
        self._sync_table_selection()
        self._update_active_label()

    def set_scan_controls_enabled(self, enabled: bool) -> None:
        self._panel.set_scan_controls_enabled(enabled)

    def _sync_table_selection(self) -> None:
        cam = self._panel.selected_camera()
        if cam is None:
            return
        for row, item in enumerate(self._panel.cameras):
            if item.index == cam.index and item.backend == cam.backend:
                self._panel.camera_table.blockSignals(True)
                self._panel.camera_table.selectRow(row)
                self._panel.camera_table.blockSignals(False)
                break

    def _update_active_label(self) -> None:
        cam = self._panel.selected_camera()
        if cam is None:
            self._active_label.setText(
                "Kamera aktif: belum dipilih. Pindai perangkat lalu pilih baris berstatus AKTIF."
            )
            return
        self._active_label.setText(f"Kamera aktif: [{cam.index}] {cam.name}")


class LiveCameraPanel(QWidget):
    """Preview live kamera dan rekam saat Start Log; pemilihan lewat dialog Setting."""

    camera_selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cameras: list[CameraInfo] = []
        self._active_camera: CameraInfo | None = None
        self._scan_worker: CameraScanWorker | None = None
        self._logging_active = False
        self._record_path: Path | None = None
        self._live_width = 0
        self._live_height = 0
        self._live_fps = 0.0
        self._selected_cam_name = ""
        self._selected_cam_index: int | str = "?"
        self._last_frame: QImage | None = None
        self._settings_dialog: LiveCameraSettingsDialog | None = None

        self._scan_btn: QPushButton | None = None
        self._scan_status: QLabel | None = None
        self._table: QTableWidget | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        view_box, view_layout = _section_widget(self)

        self._preview_label = QLabel("Belum ada kamera dipilih.", self)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(160, 90)
        self._preview_label.setStyleSheet(
            "background: #111827; color: #6b7280; border-radius: 8px; font-size: 10pt;"
        )
        self._preview_aspect = PreviewAspectContainer(
            self._preview_label,
            self,
            on_layout=self._apply_frame_to_preview,
        )
        view_layout.addWidget(self._preview_aspect, 1)

        self._status_bar = QLabel(
            "Atur kamera: menu Setting → Live → Camera.",
            self,
        )
        self._status_bar.setWordWrap(True)
        self._status_bar.setStyleSheet(_STATUS_BAR_STYLE)
        view_layout.addWidget(self._status_bar, 0)

        root.addWidget(view_box, 1)

        self.setMinimumWidth(260)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._capture_thread = CameraCaptureThread()
        self._capture_thread.frame_ready.connect(self._on_frame)
        self._capture_thread.opened.connect(self._on_camera_opened)
        self._capture_thread.stream_info.connect(self._on_stream_info)
        self._capture_thread.error.connect(self._on_capture_error)
        self._capture_thread.start()

    @property
    def cameras(self) -> list[CameraInfo]:
        return self._cameras

    @property
    def camera_table(self) -> QTableWidget:
        if self._table is None:
            raise RuntimeError("Tabel kamera belum dibuat; buka dialog Setting → Live → Camera.")
        return self._table

    def build_scan_section(self, parent: QWidget) -> QWidget:
        """Widget pindai + tabel; dipasang di dialog Setting → Live → Camera."""
        if self._table is not None:
            return self._table.parentWidget() or self._table

        scan_box, scan_layout = _section_widget(parent)

        scan_btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("Pindai Kamera", parent)
        self._scan_btn.setStyleSheet(_LIVE_PRIMARY_BUTTON_STYLE)
        self._scan_btn.clicked.connect(self.start_scan)
        scan_btn_row.addWidget(self._scan_btn)
        self._scan_status = QLabel("Klik «Pindai Kamera» untuk memulai.", parent)
        self._scan_status.setWordWrap(True)
        self._scan_status.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        scan_btn_row.addWidget(self._scan_status, 1)
        scan_layout.addLayout(scan_btn_row)

        self._table = QTableWidget(0, 5, parent)
        self._table.setHorizontalHeaderLabels(
            ["Indeks", "Nama", "Status", "Resolusi", "Catatan"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.verticalHeader().setDefaultSectionSize(_CAMERA_TABLE_ROW_HEIGHT)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scan_layout.addWidget(self._table)
        QTimer.singleShot(0, lambda: self.apply_camera_table_height(_CAMERA_TABLE_DIALOG_ROWS))

        return scan_box

    def show_settings_dialog(self) -> None:
        if self._settings_dialog is None:
            self._settings_dialog = LiveCameraSettingsDialog(self, parent=self.window())
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def apply_camera_table_height(self, visible_rows: int = _CAMERA_TABLE_MIN_ROWS) -> None:
        if self._table is None:
            return
        h = _camera_table_viewport_height(self._table, visible_rows)
        self._table.setFixedHeight(h)

    def set_scan_controls_enabled(self, enabled: bool) -> None:
        if self._scan_btn is not None:
            self._scan_btn.setEnabled(enabled)
        if self._table is not None:
            self._table.setEnabled(enabled)

    def selected_camera(self) -> CameraInfo | None:
        return self._active_camera

    def is_preview_active(self) -> bool:
        return self._active_camera is not None

    def set_logging_active(self, active: bool) -> None:
        self._logging_active = active
        self.set_scan_controls_enabled(not active)
        if self._settings_dialog is not None:
            self._settings_dialog.set_scan_controls_enabled(not active)

    def _update_status_bar(self, *, error: str | None = None) -> None:
        if error:
            self._status_bar.setText(f"⚠ Kamera: {error}")
            return

        if self._record_path is not None:
            mode = "● REKAM"
            video_part = f"  ·  {self._record_path.name}"
        elif self._live_width > 0 and self._active_camera is not None:
            mode = "● LIVE"
            video_part = ""
        else:
            mode = "○ Preview"
            video_part = ""

        cam = self._active_camera
        if cam is not None:
            name_part = f"  [{cam.index}] {cam.name}"
        elif self._selected_cam_name:
            name_part = f"  [{self._selected_cam_index}] {self._selected_cam_name}"
        else:
            name_part = ""

        if self._live_width > 0 and self._live_height > 0:
            fps_text = f"{self._live_fps:.0f}" if self._live_fps > 1.0 else "?"
            res_part = f"  ·  {self._live_width}×{self._live_height} @ {fps_text} fps"
        else:
            res_part = ""

        text = f"{mode}{name_part}{res_part}{video_part}".strip()
        if not name_part and not res_part and not video_part and mode == "○ Preview":
            text = "Atur kamera: menu Setting → Live → Camera."
        self._status_bar.setText(text)

    def _clear_preview(self, message: str) -> None:
        self._last_frame = None
        self._live_width = 0
        self._live_height = 0
        self._live_fps = 0.0
        self._preview_label.clear()
        self._preview_label.setText(message)

    def _apply_frame_to_preview(self) -> None:
        if self._last_frame is None:
            return
        label_w = max(self._preview_label.width(), 1)
        label_h = max(self._preview_label.height(), 1)
        pixmap = QPixmap.fromImage(self._last_frame).scaled(
            label_w,
            label_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(pixmap)

    def start_scan(self) -> None:
        if self._logging_active or (self._scan_worker and self._scan_worker.isRunning()):
            return
        if self._scan_btn is not None:
            self._scan_btn.setEnabled(False)
        if self._scan_status is not None:
            self._scan_status.setText("Memindai kamera…")
        if self._table is not None:
            self._table.setRowCount(0)
        self._scan_worker = CameraScanWorker()
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_finished(self, cameras: list[CameraInfo]) -> None:
        if not self._logging_active and self._scan_btn is not None:
            self._scan_btn.setEnabled(True)
        self._cameras = cameras
        active = [c for c in cameras if c.active]

        if self._table is None:
            return

        self._table.setRowCount(len(cameras))
        for row, cam in enumerate(cameras):
            resolution = (
                f"{cam.width}×{cam.height}" if cam.width > 0 and cam.height > 0 else "—"
            )
            status = "AKTIF" if cam.active else "Tidak aktif"
            values = [str(cam.index), cam.name, status, resolution, cam.note]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col == 2 and cam.active:
                    item.setForeground(Qt.GlobalColor.darkGreen)
                elif col == 2:
                    item.setForeground(Qt.GlobalColor.darkRed)
                self._table.setItem(row, col, item)

        if self._scan_status is not None:
            if not cameras:
                self._scan_status.setText("Tidak ada perangkat kamera terdeteksi.")
            else:
                self._scan_status.setText(
                    f"{len(cameras)} perangkat, {len(active)} aktif. Pilih baris untuk preview."
                )

        if active:
            for row, cam in enumerate(cameras):
                if cam.active:
                    self._table.selectRow(row)
                    break
        else:
            self._apply_camera_selection(None)

        QTimer.singleShot(0, lambda: self.apply_camera_table_height(_CAMERA_TABLE_DIALOG_ROWS))

    def _on_selection_changed(self) -> None:
        if self._logging_active or self._table is None:
            return
        row = self._table.currentRow()
        if row < 0 or row >= len(self._cameras):
            self._apply_camera_selection(None)
            return
        cam = self._cameras[row]
        self._apply_camera_selection(cam if cam.active else None)

    def _apply_camera_selection(self, cam: CameraInfo | None) -> None:
        self._active_camera = cam
        if cam is None:
            row = self._table.currentRow() if self._table is not None else -1
            if row >= 0:
                self._capture_thread.set_camera(None)
                self._clear_preview("Kamera tidak aktif atau belum dipilih.")
                self._update_status_bar()
            else:
                self._capture_thread.set_camera(None)
                self._clear_preview("Belum ada kamera dipilih.")
                self._update_status_bar()
            self.camera_selection_changed.emit()
            return

        self._clear_preview("Membuka kamera…")
        self._selected_cam_name = cam.name
        self._selected_cam_index = cam.index
        self._update_status_bar()
        self._capture_thread.set_camera(cam)
        self.camera_selection_changed.emit()

    def _on_stream_info(self, width: int, height: int, fps: float) -> None:
        self._live_width = width
        self._live_height = height
        self._live_fps = fps
        self._update_status_bar()

    def _on_camera_opened(self, ok: bool) -> None:
        if not ok and not self._logging_active:
            self._clear_preview("Gagal membuka kamera.")

    def _on_capture_error(self, message: str) -> None:
        self._update_status_bar(error=message)

    def _on_frame(self, image: QImage) -> None:
        self._last_frame = image
        self._live_width = image.width()
        self._live_height = image.height()
        self._apply_frame_to_preview()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._last_frame is not None:
            self._apply_frame_to_preview()

    def start_recording(self, video_path: Path) -> bool:
        cam = self.selected_camera()
        if cam is None:
            return False
        self._record_path = video_path
        self._capture_thread.start_recording(video_path)
        self._update_status_bar()
        return True

    def stop_recording(self) -> None:
        self._capture_thread.stop_recording()
        self._record_path = None
        self._update_status_bar()

    def shutdown(self) -> None:
        self._capture_thread.stop_recording()
        self._capture_thread.request_stop()
        self._capture_thread.wait(3000)

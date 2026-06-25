"""
Panel kamera tab Live: pindai perangkat, preview, dan rekam video (v2.3.0).
"""

from __future__ import annotations

from pathlib import Path

import cv2
from PySide6.QtCore import QMutex, QMutexLocker, Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from live_camera_core import CameraInfo, CameraScanWorker, quiet_opencv


def _frame_to_qimage(frame) -> QImage:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    return QImage(rgb.copy(), w, h, ch * w, QImage.Format.Format_RGB888)


class CameraCaptureThread(QThread):
    """Baca frame kamera di thread terpisah; tulis ke VideoWriter saat rekam."""

    frame_ready = Signal(QImage)
    opened = Signal(bool)
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


class LiveCameraPanel(QWidget):
    """Dua grup: pindai/pilih kamera dan tampilan live (+ rekam saat Start Log)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cameras: list[CameraInfo] = []
        self._scan_worker: CameraScanWorker | None = None
        self._logging_active = False
        self._record_path: Path | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        scan_group = QGroupBox("Pindai & pilih kamera", self)
        scan_layout = QVBoxLayout(scan_group)

        self._scan_status = QLabel("Klik «Pindai Kamera» untuk memulai.", self)
        self._scan_status.setWordWrap(True)
        self._scan_status.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        scan_layout.addWidget(self._scan_status)

        scan_btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("Pindai Kamera", self)
        self._scan_btn.clicked.connect(self.start_scan)
        scan_btn_row.addWidget(self._scan_btn)
        scan_btn_row.addStretch()
        scan_layout.addLayout(scan_btn_row)

        self._table = QTableWidget(0, 5, self)
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
        scan_layout.addWidget(self._table, 1)

        root.addWidget(scan_group, 2)

        view_group = QGroupBox("Tampilan kamera", self)
        view_layout = QVBoxLayout(view_group)

        self._preview_label = QLabel("Belum ada kamera dipilih.", self)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumHeight(180)
        self._preview_label.setStyleSheet(
            "background: #111827; color: #6b7280; border-radius: 8px; font-size: 10pt;"
        )
        view_layout.addWidget(self._preview_label, 1)

        self._view_status = QLabel("Preview: —", self)
        self._view_status.setWordWrap(True)
        self._view_status.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        view_layout.addWidget(self._view_status)

        self._video_name_label = QLabel("Video: —", self)
        self._video_name_label.setWordWrap(True)
        self._video_name_label.setStyleSheet(
            "color: #d1d5db; font-size: 9pt; font-family: Consolas, 'Courier New', monospace;"
        )
        view_layout.addWidget(self._video_name_label)

        root.addWidget(view_group, 3)

        self._capture_thread = CameraCaptureThread()
        self._capture_thread.frame_ready.connect(self._on_frame)
        self._capture_thread.opened.connect(self._on_camera_opened)
        self._capture_thread.error.connect(self._on_capture_error)
        self._capture_thread.start()

    def selected_camera(self) -> CameraInfo | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._cameras):
            return None
        cam = self._cameras[row]
        return cam if cam.active else None

    def is_preview_active(self) -> bool:
        return self.selected_camera() is not None

    def set_logging_active(self, active: bool) -> None:
        self._logging_active = active
        self._scan_btn.setEnabled(not active)
        self._table.setEnabled(not active)

    def start_scan(self) -> None:
        if self._logging_active or (self._scan_worker and self._scan_worker.isRunning()):
            return
        self._scan_btn.setEnabled(False)
        self._scan_status.setText("Memindai kamera…")
        self._table.setRowCount(0)
        self._scan_worker = CameraScanWorker()
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_finished(self, cameras: list[CameraInfo]) -> None:
        if not self._logging_active:
            self._scan_btn.setEnabled(True)
        self._cameras = cameras
        active = [c for c in cameras if c.active]

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
            self._capture_thread.set_camera(None)
            self._preview_label.setText("Tidak ada kamera aktif.")
            self._view_status.setText("Preview: —")

    def _on_selection_changed(self) -> None:
        if self._logging_active:
            return
        cam = self.selected_camera()
        if cam is None:
            row = self._table.currentRow()
            if row >= 0:
                self._capture_thread.set_camera(None)
                self._preview_label.setText("Kamera tidak aktif atau belum dipilih.")
                self._view_status.setText("Preview: —")
            return
        self._preview_label.setText("Membuka kamera…")
        self._view_status.setText(f"Preview: [{cam.index}] {cam.name}")
        self._capture_thread.set_camera(cam)

    def _on_camera_opened(self, ok: bool) -> None:
        if not ok and not self._logging_active:
            self._preview_label.setText("Gagal membuka kamera.")

    def _on_capture_error(self, message: str) -> None:
        self._view_status.setText(f"Kamera: {message}")

    def _on_frame(self, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image).scaled(
            self._preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(pixmap)

    def start_recording(self, video_path: Path) -> bool:
        cam = self.selected_camera()
        if cam is None:
            return False
        self._record_path = video_path
        self._capture_thread.start_recording(video_path)
        self._video_name_label.setText(f"Video: {video_path.name}")
        self._view_status.setText(f"Rekam: [{cam.index}] {cam.name}")
        return True

    def stop_recording(self) -> None:
        self._capture_thread.stop_recording()
        self._record_path = None
        self._video_name_label.setText("Video: —")
        cam = self.selected_camera()
        if cam is not None:
            self._view_status.setText(f"Preview: [{cam.index}] {cam.name}")
        else:
            self._view_status.setText("Preview: —")

    def shutdown(self) -> None:
        self._capture_thread.stop_recording()
        self._capture_thread.request_stop()
        self._capture_thread.wait(3000)

"""
Detektor perangkat kamera aktif di laptop.

Memindai indeks kamera via OpenCV, menampilkan nama perangkat (DirectShow di Windows),
dan menguji apakah setiap kamera bisa dibuka serta membaca frame.
"""

from __future__ import annotations

import contextlib
import os
import platform
import sys
from dataclasses import dataclass

# Tekan log OpenCV sebelum modul videoio dipakai.
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

MAX_PROBE_INDEX = 10


def _configure_opencv_logging() -> None:
    for setter in (
        lambda: cv2.setLogLevel(cv2.LOG_LEVEL_SILENT),
        lambda: cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT),
    ):
        try:
            setter()
            return
        except AttributeError:
            continue


@contextlib.contextmanager
def _quiet_opencv():
    previous = None
    try:
        previous = cv2.getLogLevel()
        cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
    except AttributeError:
        pass
    try:
        yield
    finally:
        if previous is not None:
            try:
                cv2.setLogLevel(previous)
            except AttributeError:
                pass


_configure_opencv_logging()


BACKEND_LABELS = {
    cv2.CAP_DSHOW: "DirectShow",
    cv2.CAP_MSMF: "Media Foundation",
    cv2.CAP_ANY: "Auto",
    cv2.CAP_AVFOUNDATION: "AVFoundation",
    cv2.CAP_V4L2: "V4L2",
}


@dataclass
class CameraInfo:
    index: int
    name: str
    active: bool
    width: int
    height: int
    fps: float
    note: str
    backend: int = cv2.CAP_ANY


def _probe_backends() -> list[tuple[int, str]]:
    """Urutan backend untuk Windows: MSMF dulu (DroidCam/virtual cam), lalu DSHOW."""
    if platform.system() == "Windows":
        return [
            (cv2.CAP_MSMF, BACKEND_LABELS[cv2.CAP_MSMF]),
            (cv2.CAP_DSHOW, BACKEND_LABELS[cv2.CAP_DSHOW]),
        ]
    if platform.system() == "Darwin":
        return [(cv2.CAP_AVFOUNDATION, BACKEND_LABELS[cv2.CAP_AVFOUNDATION])]
    return [(cv2.CAP_V4L2, BACKEND_LABELS[cv2.CAP_V4L2])]


def list_camera_names() -> list[str]:
    if platform.system() != "Windows":
        return []
    try:
        from pygrabber.dshow_graph import FilterGraph

        return list(FilterGraph().get_input_devices())
    except Exception:
        return []


def _try_probe(index: int, name: str, backend: int, backend_label: str) -> CameraInfo:
    with _quiet_opencv():
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            cap.release()
            return CameraInfo(
                index, name, False, 0, 0, 0.0, f"Gagal buka ({backend_label})", backend
            )

        ok, _frame = cap.read()
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        cap.release()

    if not ok:
        return CameraInfo(
            index,
            name,
            False,
            width,
            height,
            fps,
            f"Terbuka, gagal baca frame ({backend_label})",
            backend,
        )

    note = f"Aktif via {backend_label}"
    if width <= 0 or height <= 0:
        note = f"Aktif via {backend_label} (resolusi tidak terbaca)"
    return CameraInfo(index, name, True, width, height, fps, note, backend)


def probe_camera(index: int, name: str) -> CameraInfo:
    last = CameraInfo(index, name, False, 0, 0, 0.0, "Tidak bisa dibuka")
    for backend, backend_label in _probe_backends():
        info = _try_probe(index, name, backend, backend_label)
        if info.active:
            return info
        last = info
    return last


def scan_cameras(max_index: int = MAX_PROBE_INDEX) -> list[CameraInfo]:
    names = list_camera_names()
    if names:
        indices = range(len(names))
    else:
        indices = range(max_index)

    results: list[CameraInfo] = []
    with _quiet_opencv():
        for index in indices:
            name = names[index] if index < len(names) else f"Perangkat #{index}"
            info = probe_camera(index, name)
            if info.active or index < len(names):
                results.append(info)

    return results


class ScanWorker(QThread):
    finished = Signal(list)

    def __init__(self, max_index: int = MAX_PROBE_INDEX) -> None:
        super().__init__()
        self.max_index = max_index

    def run(self) -> None:
        self.finished.emit(scan_cameras(self.max_index))


class CameraPreviewWindow(QMainWindow):
    def __init__(
        self,
        index: int,
        name: str,
        backend: int = cv2.CAP_ANY,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.index = index
        backend_label = BACKEND_LABELS.get(backend, "Auto")
        self.setWindowTitle(f"Preview — [{index}] {name} ({backend_label})")
        self.resize(960, 540)

        self._label = QLabel("Memuat kamera…")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: #111; color: #ccc;")
        self.setCentralWidget(self._label)

        self._cap = cv2.VideoCapture(index, backend)
        if not self._cap.isOpened():
            QMessageBox.warning(self, "Kamera", f"Kamera indeks {index} tidak bisa dibuka.")
            self.close()
            return

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        self._timer.start(33)

    def _update_frame(self) -> None:
        ok, frame = self._cap.read()
        if not ok:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self._label.setPixmap(
            QPixmap.fromImage(image).scaled(
                self._label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._cap.release()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Detektor Kamera Aktif")
        self.resize(900, 420)

        self._preview_windows: list[CameraPreviewWindow] = []
        self._worker: ScanWorker | None = None
        self._last_cameras: list[CameraInfo] = []

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        header = QLabel(
            "Pindai perangkat video yang terdeteksi sistem dan uji akses via OpenCV. "
            "Kamera virtual (mis. DroidCam) sering hanya berfungsi lewat backend Media Foundation, "
            "bukan DirectShow."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        self._status = QLabel("Klik «Pindai Kamera» untuk memulai.")
        layout.addWidget(self._status)

        btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("Pindai Kamera")
        self._scan_btn.clicked.connect(self.start_scan)
        btn_row.addWidget(self._scan_btn)

        self._preview_btn = QPushButton("Preview Kamera Terpilih")
        self._preview_btn.setEnabled(False)
        self._preview_btn.clicked.connect(self.open_preview)
        btn_row.addWidget(self._preview_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Indeks", "Nama Perangkat", "Status", "Resolusi", "FPS", "Catatan"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._table)

        os_name = platform.system()
        backend_list = ", ".join(label for _, label in _probe_backends())
        footer = QLabel(f"Sistem: {os_name}  |  Urutan uji backend: {backend_list}")
        layout.addWidget(footer)

    def start_scan(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        self._scan_btn.setEnabled(False)
        self._preview_btn.setEnabled(False)
        self._status.setText("Memindai kamera… mohon tunggu.")
        self._table.setRowCount(0)

        self._worker = ScanWorker()
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.start()

    def _on_scan_finished(self, cameras: list[CameraInfo]) -> None:
        self._scan_btn.setEnabled(True)
        self._last_cameras = cameras
        active = [c for c in cameras if c.active]

        self._table.setRowCount(len(cameras))
        for row, cam in enumerate(cameras):
            resolution = (
                f"{cam.width} × {cam.height}"
                if cam.width > 0 and cam.height > 0
                else "—"
            )
            fps_text = f"{cam.fps:.1f}" if cam.fps > 0 else "—"
            status = "AKTIF" if cam.active else "Tidak aktif"

            values = [str(cam.index), cam.name, status, resolution, fps_text, cam.note]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col == 2 and cam.active:
                    item.setForeground(Qt.GlobalColor.darkGreen)
                elif col == 2:
                    item.setForeground(Qt.GlobalColor.darkRed)
                self._table.setItem(row, col, item)

        if not cameras:
            self._status.setText("Tidak ada perangkat kamera yang terdeteksi.")
        else:
            self._status.setText(
                f"Ditemukan {len(cameras)} perangkat, {len(active)} aktif (bisa dibuka & baca frame)."
            )

        if active:
            for row, cam in enumerate(cameras):
                if cam.active:
                    self._table.selectRow(row)
                    break

    def _on_selection_changed(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            self._preview_btn.setEnabled(False)
            return
        status_item = self._table.item(row, 2)
        self._preview_btn.setEnabled(status_item is not None and status_item.text() == "AKTIF")

    def open_preview(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        index = int(self._table.item(row, 0).text())
        name = self._table.item(row, 1).text()
        cam_index = next(
            (i for i, c in enumerate(self._last_cameras) if c.index == index and c.active),
            None,
        )
        backend = (
            self._last_cameras[cam_index].backend
            if cam_index is not None
            else cv2.CAP_ANY
        )
        preview = CameraPreviewWindow(index, name, backend, self)
        preview.show()
        self._preview_windows.append(preview)

    def closeEvent(self, event) -> None:
        for window in self._preview_windows:
            window.close()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

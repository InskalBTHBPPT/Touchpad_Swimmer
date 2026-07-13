"""
Detektor perangkat kamera aktif — **v2.0**.

Memindai indeks kamera via OpenCV, menampilkan nama perangkat (DirectShow di Windows),
menguji akses lokal, serta **stream RTSP** (FFmpeg) — termasuk bawaan
``rtsp://10.45.0.71:8557/h264``.
"""

from __future__ import annotations

import contextlib
import os
import platform
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

# Tekan log OpenCV / FFmpeg sebelum modul videoio dipakai.
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ.setdefault("AV_LOG_LEVEL", "-8")

import cv2
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

APP_VERSION = "2.0"
MAX_PROBE_INDEX = 10
RTSP_INDEX = -1
DEFAULT_RTSP_URL = "rtsp://10.45.0.71:8557/h264"
DEFAULT_RTSP_URLS = (DEFAULT_RTSP_URL,)
# TCP + buffer kecil: lebih stabil di LAN; mengurangi artefak decode saat join stream.
RTSP_FFMPEG_OPTIONS = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay"
RTSP_WARMUP_READS = 20


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


@contextlib.contextmanager
def _quiet_ffmpeg_stderr():
    """
    Redam log decoder H.264 FFmpeg ke stderr.

    Pesan seperti ``error while decoding MB`` / ``cabac decode`` bukan dari OpenCV
    melainkan libavcodec; sering muncul saat join stream di tengah GOP atau ada
    packet loss ringan — preview tetap bisa jalan.
    """
    stderr_fd = None
    devnull_fd = None
    try:
        stderr_fd = os.dup(2)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, 2)
        yield
    except OSError:
        yield
    finally:
        if stderr_fd is not None:
            try:
                os.dup2(stderr_fd, 2)
                os.close(stderr_fd)
            except OSError:
                pass
        if devnull_fd is not None:
            try:
                os.close(devnull_fd)
            except OSError:
                pass


def _apply_rtsp_ffmpeg_env() -> None:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = RTSP_FFMPEG_OPTIONS


def _open_rtsp_capture(url: str) -> cv2.VideoCapture:
    _apply_rtsp_ffmpeg_env()
    with _quiet_ffmpeg_stderr(), _quiet_opencv():
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if cap.isOpened():
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
    return cap


_configure_opencv_logging()


BACKEND_LABELS = {
    cv2.CAP_DSHOW: "DirectShow",
    cv2.CAP_MSMF: "Media Foundation",
    cv2.CAP_ANY: "Auto",
    cv2.CAP_AVFOUNDATION: "AVFoundation",
    cv2.CAP_V4L2: "V4L2",
    cv2.CAP_FFMPEG: "FFmpeg",
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
    url: str | None = None

    @property
    def is_rtsp(self) -> bool:
        return self.url is not None


def _rtsp_display_name(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or url
    path = parsed.path.strip("/")
    if path:
        return f"RTSP {host}/{path}"
    return f"RTSP {host}"


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


def _read_frame_props(
    cap: cv2.VideoCapture,
) -> tuple[bool, int, int, float]:
    ok, _frame = cap.read()
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    return ok, width, height, fps


def _read_rtsp_frame_props(cap: cv2.VideoCapture) -> tuple[bool, int, int, float]:
    """Baca frame RTSP; buang beberapa frame awal (sering corrupt sebelum keyframe)."""
    ok = False
    for _ in range(RTSP_WARMUP_READS):
        with _quiet_ffmpeg_stderr():
            ok, _frame = cap.read()
        if ok:
            break
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    return ok, width, height, fps


def _try_probe(index: int, name: str, backend: int, backend_label: str) -> CameraInfo:
    with _quiet_opencv():
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            cap.release()
            return CameraInfo(
                index, name, False, 0, 0, 0.0, f"Gagal buka ({backend_label})", backend
            )

        ok, width, height, fps = _read_frame_props(cap)
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


def probe_rtsp(url: str, *, display_name: str | None = None) -> CameraInfo:
    """Uji stream RTSP via backend FFmpeg OpenCV."""
    url = url.strip()
    name = display_name or _rtsp_display_name(url)
    if not url.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
        return CameraInfo(
            RTSP_INDEX,
            name,
            False,
            0,
            0,
            0.0,
            "URL stream tidak valid (harus rtsp://, rtsps://, http://, atau https://)",
            cv2.CAP_FFMPEG,
            url=url,
        )

    with _quiet_ffmpeg_stderr(), _quiet_opencv():
        cap = _open_rtsp_capture(url)
        if not cap.isOpened():
            cap.release()
            return CameraInfo(
                RTSP_INDEX,
                name,
                False,
                0,
                0,
                0.0,
                "Gagal buka stream (FFmpeg / jaringan)",
                cv2.CAP_FFMPEG,
                url=url,
            )

        ok, width, height, fps = _read_rtsp_frame_props(cap)
        cap.release()

    if not ok:
        return CameraInfo(
            RTSP_INDEX,
            name,
            False,
            width,
            height,
            fps,
            "Stream terbuka, gagal baca frame",
            cv2.CAP_FFMPEG,
            url=url,
        )

    note = "Aktif via FFmpeg (RTSP/TCP)"
    if width <= 0 or height <= 0:
        note = "Aktif via FFmpeg (resolusi tidak terbaca)"
    return CameraInfo(
        RTSP_INDEX, name, True, width, height, fps, note, cv2.CAP_FFMPEG, url=url
    )


def scan_cameras(
    max_index: int = MAX_PROBE_INDEX,
    *,
    rtsp_urls: tuple[str, ...] = DEFAULT_RTSP_URLS,
) -> list[CameraInfo]:
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

    for url in rtsp_urls:
        url = url.strip()
        if not url:
            continue
        results.append(probe_rtsp(url))

    return results


class ScanWorker(QThread):
    finished = Signal(list)

    def __init__(
        self,
        max_index: int = MAX_PROBE_INDEX,
        *,
        rtsp_urls: tuple[str, ...] = DEFAULT_RTSP_URLS,
    ) -> None:
        super().__init__()
        self.max_index = max_index
        self.rtsp_urls = rtsp_urls

    def run(self) -> None:
        self.finished.emit(scan_cameras(self.max_index, rtsp_urls=self.rtsp_urls))


class CameraPreviewWindow(QMainWindow):
    def __init__(self, cam: CameraInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cam = cam
        self._is_rtsp = cam.is_rtsp
        if cam.is_rtsp:
            self.setWindowTitle(f"Preview — {cam.name}")
        else:
            backend_label = BACKEND_LABELS.get(cam.backend, "Auto")
            self.setWindowTitle(f"Preview — [{cam.index}] {cam.name} ({backend_label})")
        self.resize(960, 540)

        self._label = QLabel("Memuat kamera…")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: #111; color: #ccc;")
        self.setCentralWidget(self._label)

        with _quiet_opencv():
            if cam.is_rtsp and cam.url:
                self._cap = _open_rtsp_capture(cam.url)
            else:
                self._cap = cv2.VideoCapture(cam.index, cam.backend)

        if not self._cap.isOpened():
            QMessageBox.warning(
                self,
                "Kamera",
                "Sumber video tidak bisa dibuka.",
            )
            self.close()
            return

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        self._timer.start(33)

    def _update_frame(self) -> None:
        if self._is_rtsp:
            with _quiet_ffmpeg_stderr():
                ok, frame = self._cap.read()
        else:
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
        self.setWindowTitle(f"Detektor Kamera Aktif v{APP_VERSION}")
        self.resize(960, 520)

        self._preview_windows: list[CameraPreviewWindow] = []
        self._worker: ScanWorker | None = None
        self._last_cameras: list[CameraInfo] = []

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        header = QLabel(
            "Pindai perangkat video lokal (OpenCV) dan uji stream RTSP via FFmpeg. "
            "Kamera virtual (mis. DroidCam) sering hanya berfungsi lewat Media Foundation. "
            f"Stream bawaan: {DEFAULT_RTSP_URL}"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        self._status = QLabel("Klik «Pindai Kamera» untuk memulai.")
        layout.addWidget(self._status)

        rtsp_row = QHBoxLayout()
        rtsp_row.addWidget(QLabel("URL stream:"))
        self._rtsp_edit = QLineEdit(DEFAULT_RTSP_URL)
        self._rtsp_edit.setPlaceholderText("rtsp://host:port/path")
        rtsp_row.addWidget(self._rtsp_edit, 1)
        self._rtsp_btn = QPushButton("Uji RTSP")
        self._rtsp_btn.clicked.connect(self.test_rtsp_url)
        rtsp_row.addWidget(self._rtsp_btn)
        layout.addLayout(rtsp_row)

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

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Indeks", "Nama Perangkat", "Status", "Resolusi", "FPS", "Catatan", "URL"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnHidden(6, True)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._table)

        os_name = platform.system()
        backend_list = ", ".join(label for _, label in _probe_backends())
        footer = QLabel(
            f"Sistem: {os_name}  |  Backend lokal: {backend_list}  |  "
            f"Stream jaringan: FFmpeg (RTSP/TCP)"
        )
        layout.addWidget(footer)

    def _current_rtsp_url(self) -> str:
        return self._rtsp_edit.text().strip()

    def _populate_table(self, cameras: list[CameraInfo]) -> None:
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
            index_text = "RTSP" if cam.is_rtsp else str(cam.index)
            url_text = cam.url or ""

            values = [
                index_text,
                cam.name,
                status,
                resolution,
                fps_text,
                cam.note,
                url_text,
            ]
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
                f"Ditemukan {len(cameras)} sumber, {len(active)} aktif "
                "(bisa dibuka & baca frame)."
            )

        if active:
            for row, cam in enumerate(cameras):
                if cam.active:
                    self._table.selectRow(row)
                    break

    def start_scan(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        self._scan_btn.setEnabled(False)
        self._rtsp_btn.setEnabled(False)
        self._preview_btn.setEnabled(False)
        self._status.setText("Memindai kamera… mohon tunggu.")
        self._table.setRowCount(0)

        rtsp_urls = DEFAULT_RTSP_URLS
        custom = self._current_rtsp_url()
        if custom and custom not in rtsp_urls:
            rtsp_urls = (*rtsp_urls, custom)

        self._worker = ScanWorker(rtsp_urls=rtsp_urls)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.start()

    def test_rtsp_url(self) -> None:
        url = self._current_rtsp_url()
        if not url:
            QMessageBox.warning(self, "RTSP", "Masukkan URL stream terlebih dahulu.")
            return

        self._rtsp_btn.setEnabled(False)
        self._status.setText(f"Menguji stream: {url}")

        info = probe_rtsp(url)
        merged = list(self._last_cameras)
        replaced = False
        for i, existing in enumerate(merged):
            if existing.url == url:
                merged[i] = info
                replaced = True
                break
        if not replaced:
            merged.append(info)

        self._last_cameras = merged
        self._populate_table(merged)
        self._rtsp_btn.setEnabled(True)

        if not info.active:
            QMessageBox.warning(
                self,
                "RTSP",
                f"Stream tidak aktif:\n{info.note}\n\nURL: {url}",
            )

    def _on_scan_finished(self, cameras: list[CameraInfo]) -> None:
        self._scan_btn.setEnabled(True)
        self._rtsp_btn.setEnabled(True)
        self._last_cameras = cameras
        self._populate_table(cameras)

    def _on_selection_changed(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            self._preview_btn.setEnabled(False)
            return
        status_item = self._table.item(row, 2)
        self._preview_btn.setEnabled(status_item is not None and status_item.text() == "AKTIF")

    def _selected_camera(self) -> CameraInfo | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._last_cameras):
            return None
        return self._last_cameras[row]

    def open_preview(self) -> None:
        cam = self._selected_camera()
        if cam is None or not cam.active:
            return
        preview = CameraPreviewWindow(cam, self)
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

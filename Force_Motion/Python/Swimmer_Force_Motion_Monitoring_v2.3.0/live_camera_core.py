"""
Pemindaian dan probe kamera untuk tab Live (v2.3.0).

Logika backend MSMF/DSHOW diadaptasi dari ``Camera_Device_Detector``.
Di Windows, MSMF dicoba lebih dulu (cocok untuk DroidCam). ``pygrabber`` dipakai
untuk nama perangkat DirectShow jika tersedia.
"""

from __future__ import annotations

import contextlib
import os
import platform
from dataclasses import dataclass

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2
from PySide6.QtCore import QThread, Signal

MAX_PROBE_INDEX = 10

# Resolusi yang dicoba (tertinggi dulu); driver virtual cam (mis. DroidCam) mungkin
# hanya mendukung subset — ukuran aktual dibaca dari frame setelah set.
PREFERRED_CAPTURE_SIZES: tuple[tuple[int, int], ...] = (
    (1920, 1080),
    (1280, 720),
    (960, 540),
    (854, 480),
    (640, 480),
)


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
def quiet_opencv():
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


def probe_backends() -> list[tuple[int, str]]:
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


def _read_actual_frame(cap: cv2.VideoCapture) -> tuple[int, int] | None:
    ok, frame = cap.read()
    if ok and frame is not None:
        h, w = frame.shape[:2]
        return w, h
    return None


def _request_capture_size(
    cap: cv2.VideoCapture,
    width: int,
    height: int,
    *,
    mjpeg: bool = False,
) -> tuple[int, int] | None:
    if mjpeg:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    return _read_actual_frame(cap)


def configure_capture_resolution(cap: cv2.VideoCapture) -> tuple[int, int, float]:
    """
    Coba resolusi dari tertinggi ke terendah; kembalikan ukuran frame aktual terbaik.

    Beberapa webcam USB (mis. 1080p) membutuhkan FOURCC MJPEG agar driver menerima
    resolusi tinggi. Setiap permintaan diverifikasi dengan membaca satu frame — bukan
    hanya ``cap.get()`` — karena OpenCV/MSMF sering melaporkan nilai salah.
    """
    best_pixels = 0
    best_actual = (0, 0)
    best_request = (0, 0)
    best_mjpeg = False
    best_fps = 30.0

    for width, height in PREFERRED_CAPTURE_SIZES:
        for mjpeg in (False, True):
            actual = _request_capture_size(cap, width, height, mjpeg=mjpeg)
            if actual is None:
                continue
            actual_w, actual_h = actual
            pixels = actual_w * actual_h
            if pixels > best_pixels:
                best_pixels = pixels
                best_actual = actual
                best_request = (width, height)
                best_mjpeg = mjpeg
                fps = float(cap.get(cv2.CAP_PROP_FPS))
                best_fps = fps if fps > 1.0 else 30.0
            if actual_w >= width - 2 and actual_h >= height - 2:
                _request_capture_size(cap, width, height, mjpeg=mjpeg)
                fps = float(cap.get(cv2.CAP_PROP_FPS))
                return actual_w, actual_h, fps if fps > 1.0 else 30.0

    if best_pixels > 0:
        _request_capture_size(
            cap, best_request[0], best_request[1], mjpeg=best_mjpeg
        )
        return best_actual[0], best_actual[1], best_fps

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    width = max(0, int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    height = max(0, int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    if fps <= 1.0:
        fps = 30.0
    return width, height, fps


def _try_probe(index: int, name: str, backend: int, backend_label: str) -> CameraInfo:
    with quiet_opencv():
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            cap.release()
            return CameraInfo(
                index, name, False, 0, 0, 0.0, f"Gagal buka ({backend_label})", backend
            )

        width, height, fps = configure_capture_resolution(cap)
        cap.release()

    if width <= 0 or height <= 0:
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
    return CameraInfo(index, name, True, width, height, fps, note, backend)


def probe_camera(index: int, name: str) -> CameraInfo:
    best: CameraInfo | None = None
    last = CameraInfo(index, name, False, 0, 0, 0.0, "Tidak bisa dibuka")
    for backend, backend_label in probe_backends():
        info = _try_probe(index, name, backend, backend_label)
        if not info.active:
            last = info
            continue
        if best is None or (info.width * info.height) > (best.width * best.height):
            best = info
        last = info
    return best if best is not None else last


def scan_cameras(max_index: int = MAX_PROBE_INDEX) -> list[CameraInfo]:
    names = list_camera_names()
    indices = range(len(names)) if names else range(max_index)

    results: list[CameraInfo] = []
    with quiet_opencv():
        for index in indices:
            name = names[index] if index < len(names) else f"Perangkat #{index}"
            info = probe_camera(index, name)
            if info.active or index < len(names):
                results.append(info)

    return results


class CameraScanWorker(QThread):
    finished = Signal(list)

    def __init__(self, max_index: int = MAX_PROBE_INDEX) -> None:
        super().__init__()
        self.max_index = max_index

    def run(self) -> None:
        self.finished.emit(scan_cameras(self.max_index))

"""
Pemindaian dan probe kamera untuk tab Live (v2.3.0).

Logika backend MSMF/DSHOW diadaptasi dari ``Camera_Device_Detector``.
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


def configure_capture_resolution(cap: cv2.VideoCapture) -> tuple[int, int, float]:
    """
    Minta resolusi setinggi mungkin ke driver, lalu baca satu frame untuk ukuran aktual.
    """
    for width, height in PREFERRED_CAPTURE_SIZES:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    ok, frame = cap.read()
    if ok and frame is not None:
        actual_h, actual_w = frame.shape[:2]
        if fps <= 1.0:
            fps = 30.0
        return actual_w, actual_h, fps

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
    last = CameraInfo(index, name, False, 0, 0, 0.0, "Tidak bisa dibuka")
    for backend, backend_label in probe_backends():
        info = _try_probe(index, name, backend, backend_label)
        if info.active:
            return info
        last = info
    return last


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

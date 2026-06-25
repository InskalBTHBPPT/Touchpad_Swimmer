"""
Panel playback video rekaman tab Live untuk tab Analisa (v2.3.0).

Playback sinkron kasar dengan plot CSV: ``position_changed`` mengirim detik media
(``csv_t ≈ ts_awal + video_t`` di tab Analisa).
"""

from __future__ import annotations

from pathlib import Path

import cv2
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from live_camera_core import quiet_opencv


def _frame_to_qimage(frame) -> QImage:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    return QImage(rgb.copy(), w, h, ch * w, QImage.Format.Format_RGB888)


def _format_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    whole = int(seconds)
    frac = int(round((seconds - whole) * 10))
    if frac >= 10:
        whole += 1
        frac = 0
    return f"{whole // 60:02d}:{whole % 60:02d}.{frac}"


class AnalyzeVideoPanel(QGroupBox):
    """Pemutar video MP4 hasil rekaman kamera tab Live."""

    position_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Rekaman video", parent)
        self._video_path: Path | None = None
        self._cap: cv2.VideoCapture | None = None
        self._playing = False
        self._fps = 30.0
        self._total_frames = 0
        self._current_frame = 0
        self._slider_dragging = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)

        self._preview = QLabel("Muat CSV untuk memuat video pasangan (.mp4).", self)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(140)
        self._preview.setMaximumHeight(320)
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._preview.setStyleSheet(
            "background: #111827; color: #6b7280; border-radius: 8px; font-size: 10pt;"
        )
        layout.addWidget(self._preview, 1)

        self._info_label = QLabel("Video: —", self)
        self._info_label.setWordWrap(True)
        self._info_label.setStyleSheet(
            "color: #9ca3af; font-size: 9pt; font-family: Consolas, 'Courier New', monospace;"
        )
        layout.addWidget(self._info_label)

        transport = QHBoxLayout()
        self._play_btn = QPushButton("▶ Play", self)
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self._toggle_play)
        transport.addWidget(self._play_btn)

        self._time_label = QLabel("00:00.0 / 00:00.0", self)
        self._time_label.setStyleSheet("color: #d1d5db; font-size: 9pt;")
        transport.addWidget(self._time_label)
        transport.addStretch()
        layout.addLayout(transport)

        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._slider.setEnabled(False)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def _release_capture(self) -> None:
        self._timer.stop()
        self._playing = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._play_btn.setText("▶ Play")

    def clear(self) -> None:
        self._release_capture()
        self._video_path = None
        self._total_frames = 0
        self._current_frame = 0
        self._slider.setEnabled(False)
        self._slider.setValue(0)
        self._play_btn.setEnabled(False)
        self._preview.setText("Tidak ada video dimuat.")
        self._preview.setPixmap(QPixmap())
        self._info_label.setText("Video: —")
        self._time_label.setText("00:00.0 / 00:00.0")
        self.position_changed.emit(-1.0)

    def load_video(self, path: Path) -> bool:
        self.clear()
        if not path.is_file():
            return False

        with quiet_opencv():
            cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            cap.release()
            return False

        self._cap = cap
        self._video_path = path
        self._fps = float(cap.get(cv2.CAP_PROP_FPS))
        if self._fps <= 1.0:
            self._fps = 30.0
        self._total_frames = max(0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        self._current_frame = 0

        self._slider.blockSignals(True)
        self._slider.setMaximum(max(0, self._total_frames - 1))
        self._slider.setValue(0)
        self._slider.setEnabled(self._total_frames > 1)
        self._slider.blockSignals(False)

        self._play_btn.setEnabled(True)
        self._info_label.setText(f"Video: {path.name}")
        self._show_frame(0)
        self._update_time_label()
        self._emit_position()
        return True

    def video_path(self) -> Path | None:
        return self._video_path

    def current_position_s(self) -> float:
        if self._fps <= 0:
            return 0.0
        return self._current_frame / self._fps

    def duration_s(self) -> float:
        return self._duration_s()

    def shutdown(self) -> None:
        self.clear()

    def _duration_s(self) -> float:
        if self._total_frames <= 0 or self._fps <= 0:
            return 0.0
        return self._total_frames / self._fps

    def _update_time_label(self) -> None:
        pos_s = self._current_frame / self._fps if self._fps > 0 else 0.0
        self._time_label.setText(
            f"{_format_time(pos_s)} / {_format_time(self._duration_s())}"
        )

    def _show_frame(self, frame_index: int) -> None:
        if self._cap is None or not self._cap.isOpened():
            return
        frame_index = max(0, min(frame_index, max(0, self._total_frames - 1)))
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = self._cap.read()
        if not ok:
            return
        self._current_frame = frame_index
        image = _frame_to_qimage(frame)
        pixmap = QPixmap.fromImage(image).scaled(
            self._preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(pixmap)

    def _emit_position(self) -> None:
        self.position_changed.emit(self.current_position_s())

    def _toggle_play(self) -> None:
        if self._cap is None:
            return
        if self._playing:
            self._playing = False
            self._timer.stop()
            self._play_btn.setText("▶ Play")
            return
        if self._current_frame >= self._total_frames - 1 and self._total_frames > 0:
            self._seek_frame(0)
        self._playing = True
        self._play_btn.setText("⏸ Pause")
        interval = max(1, int(1000 / self._fps))
        self._timer.start(interval)

    def _on_tick(self) -> None:
        if self._cap is None or self._slider_dragging:
            return
        next_frame = self._current_frame + 1
        if self._total_frames > 0 and next_frame >= self._total_frames:
            self._seek_frame(self._total_frames - 1)
            self._playing = False
            self._timer.stop()
            self._play_btn.setText("▶ Play")
            return
        self._seek_frame(next_frame)

    def _seek_frame(self, frame_index: int) -> None:
        self._show_frame(frame_index)
        if not self._slider_dragging:
            self._slider.blockSignals(True)
            self._slider.setValue(self._current_frame)
            self._slider.blockSignals(False)
        self._update_time_label()
        self._emit_position()

    def _on_slider_pressed(self) -> None:
        self._slider_dragging = True
        if self._playing:
            self._playing = False
            self._timer.stop()
            self._play_btn.setText("▶ Play")

    def _on_slider_released(self) -> None:
        self._slider_dragging = False
        self._seek_frame(self._slider.value())

    def _on_slider_changed(self, value: int) -> None:
        if self._slider_dragging:
            self._seek_frame(value)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._cap is not None and self._current_frame >= 0:
            self._show_frame(self._current_frame)

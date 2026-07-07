"""
Dialog pengaturan port serial tab Live (Setting → Live → Serial Port).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


_DIALOG_STYLE = """
QDialog {
    background-color: #111827;
}
QLabel { color: #e5e7eb; }
QComboBox {
    background: #374151;
    color: #e5e7eb;
    border: 1px solid #4b5563;
    padding: 6px;
    border-radius: 8px;
}
QComboBox:disabled { background: #2d3643; color: #9ca3af; }
QPushButton {
    padding: 8px 12px;
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
}
QPushButton:hover { background-color: #2563eb; }
QPushButton:disabled { background-color: #6b7280; color: #d1d5db; }
"""


class LiveSerialSettingsDialog(QDialog):
    """Pilih port COM dan baud rate untuk koneksi serial tab Live."""

    def __init__(self, main_window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._main = main_window
        self.setWindowTitle("Serial Port")
        self.setStyleSheet(_DIALOG_STYLE)
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        hint = QLabel(
            "Pilih port dan baud rate sebelum Connect di tab Live. "
            "Port tidak bisa diubah saat sudah terhubung.",
            self,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        root.addWidget(hint)

        form = QWidget(self)
        grid = QGridLayout(form)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(10)

        mw = main_window
        grid.addWidget(QLabel("Port:", form), 0, 0)
        grid.addWidget(mw.port_combo, 0, 1)
        refresh_row = QHBoxLayout()
        refresh_row.addWidget(mw.refresh_btn)
        refresh_row.addStretch(1)
        grid.addLayout(refresh_row, 0, 2)
        grid.addWidget(QLabel("Baud:", form), 1, 0)
        grid.addWidget(mw.baud_combo, 1, 1, 1, 2)

        root.addWidget(form)
        root.addStretch(1)

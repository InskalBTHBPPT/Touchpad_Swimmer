"""Tema tooltip aplikasi — latar terang, teks gelap (Windows + widget gelap)."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

APP_QTOOLTIP_STYLESHEET = """
QToolTip {
    color: #0f172a;
    background-color: #f8fafc;
    border: 1px solid #64748b;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 10pt;
}
QToolTip QLabel {
    color: #0f172a;
    background-color: transparent;
}
"""


def apply_app_tooltip_theme(app) -> None:
    """Palette tooltip eksplisit — di Windows teks tooltip bisa mewarisi warna widget."""
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#f8fafc"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#0f172a"))
    app.setPalette(palette)


def tooltip_text(*lines: str) -> str:
    return "\n".join(lines)

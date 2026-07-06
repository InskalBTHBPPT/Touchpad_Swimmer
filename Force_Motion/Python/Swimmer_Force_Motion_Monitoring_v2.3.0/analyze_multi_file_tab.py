"""
Tab **Analisa multifile** — bandingkan hingga lima berkas ``DataStatistik/`` dalam
satu tabel (``QTableWidget``). **Add file** menambah kolom; **Clear tabel** menghapus
kolom terpilih. **Plot data** membuka jendela perbandingan metrik (pyqtgraph).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from parse_datastatistik_csv import StatistikExportRecord, parse_datastatistik_csv

MAX_FILES = 5
HEADER_ROWS = 6
EMPTY_CELL = "—"
DATA_COLUMN_WIDTH_PX = 252
_DATA_COL_WIDTH_REF_PX = 168
_HEADER_WRAP_CHARS_REF = 22
HEADER_WRAP_CHARS = max(
    12,
    round(DATA_COLUMN_WIDTH_PX / _DATA_COL_WIDTH_REF_PX * _HEADER_WRAP_CHARS_REF),
)
HEADER_ROW_DEFAULT_HEIGHT = 28
HEADER_ROW_FILENAME = 2
HEADER_ROW_SOURCE = 4

GROUP_REGION = "region"
GROUP_OFFSET = "offset"
GROUP_CORRECTION = "correction"
GROUP_FORCE = "force"
GROUP_ROLL = "roll"
GROUP_PITCH = "pitch"
GROUP_SPECTRUM = "spectrum"
GROUP_GAP = "gap"


@dataclass(frozen=True)
class _GroupStyle:
    accent: str
    header_bg: str
    row_bg: str


_GROUP_STYLES: dict[str, _GroupStyle] = {
    GROUP_REGION: _GroupStyle("#cbd5e1", "#334155", "#1e293b"),
    GROUP_OFFSET: _GroupStyle("#22c55e", "#14532d", "#0c1a12"),
    GROUP_CORRECTION: _GroupStyle("#60a5fa", "#1e3a5f", "#0c1520"),
    GROUP_FORCE: _GroupStyle("#38bdf8", "#0c4a6e", "#0b1220"),
    GROUP_ROLL: _GroupStyle("#f59e0b", "#78350f", "#1a1208"),
    GROUP_PITCH: _GroupStyle("#a78bfa", "#4c1d95", "#120f1f"),
    GROUP_SPECTRUM: _GroupStyle("#34d399", "#065f46", "#0a1512"),
    GROUP_GAP: _GroupStyle("#94a3b8", "#475569", "#151a22"),
}


@dataclass(frozen=True)
class _TableRowSpec:
    kind: str
    group: str
    label: str
    getter: Callable[[StatistikExportRecord], str] | None = None


def _force_method_text(rec: StatistikExportRecord) -> str:
    label = (rec.force_stats_method or "").strip()
    if not label:
        return EMPTY_CELL
    if rec.force_stroke_count is not None and rec.force_stroke_count > 0:
        label += f" · n={rec.force_stroke_count}"
    if rec.force_stats_fallback_global:
        label += " · fallback global"
    return label


def _fmt_cell(v: float | int | str | None) -> str:
    if v is None:
        return EMPTY_CELL
    if isinstance(v, str):
        return v.strip() if v.strip() else EMPTY_CELL
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _fmt_bool(v: bool) -> str:
    return "Ya" if v else "Tidak"


def _wrap_header_text(text: str, *, width: int = HEADER_WRAP_CHARS) -> str:
    """Pecah teks panjang (nama berkas) menjadi beberapa baris untuk header kolom."""
    if not text or text == EMPTY_CELL or len(text) <= width:
        return text
    lines: list[str] = []
    rest = text
    while rest:
        if len(rest) <= width:
            lines.append(rest)
            break
        chunk = rest[:width]
        break_at = max(chunk.rfind("_"), chunk.rfind("-"), chunk.rfind("."))
        if break_at > width // 3:
            lines.append(rest[: break_at + 1])
            rest = rest[break_at + 1 :]
        else:
            lines.append(chunk)
            rest = rest[width:]
    return "\n".join(lines)


def _build_table_row_specs() -> list[_TableRowSpec]:
    specs: list[_TableRowSpec] = []

    def grp(title: str, group: str) -> None:
        specs.append(_TableRowSpec("group", group, title, None))

    def met(group: str, label: str, fn: Callable[[StatistikExportRecord], str]) -> None:
        specs.append(_TableRowSpec("metric", group, label, fn))

    grp("Region uji", GROUP_REGION)
    met(GROUP_REGION, "Segmen analisa start (s)", lambda r: _fmt_cell(r.segment_start_s))
    met(GROUP_REGION, "Segmen analisa finish (s)", lambda r: _fmt_cell(r.segment_end_s))
    met(GROUP_REGION, "Timestamp start uji (s)", lambda r: _fmt_cell(r.timestamp_start_s))
    met(GROUP_REGION, "Timestamp stop uji (s)", lambda r: _fmt_cell(r.timestamp_stop_s))
    met(GROUP_REGION, "Durasi region data uji (s)", lambda r: _fmt_cell(r.test_region_duration_s))

    grp("Zero offset", GROUP_OFFSET)
    met(GROUP_OFFSET, "Zero offset diterapkan", lambda r: _fmt_bool(r.zero_offset_applied))
    met(GROUP_OFFSET, "Zero offset start (s)", lambda r: _fmt_cell(r.zero_offset_start_s))
    met(GROUP_OFFSET, "Zero offset stop (s)", lambda r: _fmt_cell(r.zero_offset_stop_s))
    met(
        GROUP_OFFSET,
        "Durasi region zero offset (s)",
        lambda r: _fmt_cell(r.zero_offset_duration_s),
    )
    met(
        GROUP_OFFSET,
        "Rata-rata offset Force (Kg)",
        lambda r: _fmt_cell(r.offset_mean_force_kg),
    )
    met(
        GROUP_OFFSET,
        "Rata-rata offset Roll (deg)",
        lambda r: _fmt_cell(r.offset_mean_roll_deg),
    )
    met(
        GROUP_OFFSET,
        "Rata-rata offset Pitch (deg)",
        lambda r: _fmt_cell(r.offset_mean_pitch_deg),
    )

    grp("Koreksi", GROUP_CORRECTION)
    met(
        GROUP_CORRECTION,
        "Koreksi sudut tali",
        lambda r: _fmt_bool(r.tether_angle_correction),
    )
    met(
        GROUP_CORRECTION,
        "Sudut tali terhadap air (deg)",
        lambda r: _fmt_cell(r.tether_angle_deg),
    )
    met(
        GROUP_CORRECTION,
        "Koreksi batas bawah Force mentah",
        lambda r: _fmt_bool(r.force_raw_floor_correction),
    )
    met(
        GROUP_CORRECTION,
        "Batas bawah Force mentah (Kg)",
        lambda r: _fmt_cell(r.force_raw_floor_kg),
    )

    grp("Force", GROUP_FORCE)
    met(GROUP_FORCE, "Metode statistik Force", _force_method_text)
    met(GROUP_FORCE, "Jumlah siklus Andrade (n)", lambda r: _fmt_cell(r.force_stroke_count))
    met(GROUP_FORCE, "Filter Andrade cutoff (Hz)", lambda r: _fmt_cell(r.andrade_filter_cutoff_hz))
    met(GROUP_FORCE, "peakF (Kg)", lambda r: _fmt_cell(r.force_peak_kg))
    met(GROUP_FORCE, "Timestamp peakF (s)", lambda r: _fmt_cell(r.force_peak_t_s))
    met(GROUP_FORCE, "meanF (Kg)", lambda r: _fmt_cell(r.force_mean_kg))
    met(GROUP_FORCE, "ImpF (Kg·s)", lambda r: _fmt_cell(r.force_impulse_kg_s))
    met(GROUP_FORCE, "TpeakF (s)", lambda r: _fmt_cell(r.force_t_peak_f_s))
    met(GROUP_FORCE, "DUR (s)", lambda r: _fmt_cell(r.force_dur_s))
    met(GROUP_FORCE, "RFD (Kg/s)", lambda r: _fmt_cell(r.force_rfd_kg_s))
    met(GROUP_FORCE, "dF (%)", lambda r: _fmt_cell(r.force_df_pct))
    met(GROUP_FORCE, "Fatigue Index FI (%)", lambda r: _fmt_cell(r.force_fi_pct))
    met(GROUP_FORCE, "minF (Kg)", lambda r: _fmt_cell(r.force_min_kg))
    met(GROUP_FORCE, "Timestamp minF (s)", lambda r: _fmt_cell(r.force_min_t_s))
    met(GROUP_FORCE, "Frekuensi dominan (Hz)", lambda r: _fmt_cell(r.dom_freq_force_hz))

    grp("Roll", GROUP_ROLL)
    met(GROUP_ROLL, "Minimum (Deg)", lambda r: _fmt_cell(r.roll_min_deg))
    met(GROUP_ROLL, "Timestamp minimum (s)", lambda r: _fmt_cell(r.roll_min_t_s))
    met(GROUP_ROLL, "Maksimum (Deg)", lambda r: _fmt_cell(r.roll_max_deg))
    met(GROUP_ROLL, "Timestamp maksimum (s)", lambda r: _fmt_cell(r.roll_max_t_s))
    met(GROUP_ROLL, "Frekuensi dominan (Hz)", lambda r: _fmt_cell(r.dom_freq_roll_hz))

    grp("Pitch", GROUP_PITCH)
    met(GROUP_PITCH, "Minimum (Deg)", lambda r: _fmt_cell(r.pitch_min_deg))
    met(GROUP_PITCH, "Timestamp minimum (s)", lambda r: _fmt_cell(r.pitch_min_t_s))
    met(GROUP_PITCH, "Maksimum (Deg)", lambda r: _fmt_cell(r.pitch_max_deg))
    met(GROUP_PITCH, "Timestamp maksimum (s)", lambda r: _fmt_cell(r.pitch_max_t_s))
    met(GROUP_PITCH, "Frekuensi dominan (Hz)", lambda r: _fmt_cell(r.dom_freq_pitch_hz))

    grp("Metode spektrum", GROUP_SPECTRUM)
    met(GROUP_SPECTRUM, "Metode", lambda r: _fmt_cell(r.spectrum_method))

    grp("Gap rekaman CSV", GROUP_GAP)
    met(GROUP_GAP, "Metode", lambda r: _fmt_cell(r.gap_method))
    met(GROUP_GAP, "Δt nominal (s)", lambda r: _fmt_cell(r.gap_dt_nominal_s))
    met(GROUP_GAP, "Laju sampel efektif (Hz)", lambda r: _fmt_cell(r.gap_fs_hz))
    met(GROUP_GAP, "Sampel tercatat", lambda r: _fmt_cell(r.gap_samples_actual))
    met(GROUP_GAP, "Sampel diharapkan", lambda r: _fmt_cell(r.gap_samples_expected))
    met(GROUP_GAP, "Jumlah gap", lambda r: _fmt_cell(r.gap_count))
    met(GROUP_GAP, "Sampel hilang estimasi", lambda r: _fmt_cell(r.gap_samples_lost))
    met(GROUP_GAP, "Persen hilang (%)", lambda r: _fmt_cell(r.gap_loss_pct))

    return specs


TABLE_ROWS = _build_table_row_specs()
DATA_ROWS = len(TABLE_ROWS)
TOTAL_ROWS = HEADER_ROWS + DATA_ROWS

PLOT_STYLE_BAR = "bar"
PLOT_STYLE_LINE = "line"
PLOT_STYLE_SCATTER = "scatter"

PLOT_METRIC_SPECS: list[
    tuple[str, str, Callable[[StatistikExportRecord], float | None]]
] = [
    ("peakF (Kg)", "Force (Kg)", lambda r: r.force_peak_kg),
    ("meanF (Kg)", "Force (Kg)", lambda r: r.force_mean_kg),
    ("minF (Kg)", "Force (Kg)", lambda r: r.force_min_kg),
    ("ImpF (Kg·s)", "Impulse (Kg·s)", lambda r: r.force_impulse_kg_s),
    ("Roll maksimum (°)", "Roll (°)", lambda r: r.roll_max_deg),
    ("Roll minimum (°)", "Roll (°)", lambda r: r.roll_min_deg),
    ("Pitch maksimum (°)", "Pitch (°)", lambda r: r.pitch_max_deg),
    ("Pitch minimum (°)", "Pitch (°)", lambda r: r.pitch_min_deg),
    ("Frekuensi dominan Force (Hz)", "f (Hz)", lambda r: r.dom_freq_force_hz),
    ("Frekuensi dominan Roll (Hz)", "f (Hz)", lambda r: r.dom_freq_roll_hz),
    ("Frekuensi dominan Pitch (Hz)", "f (Hz)", lambda r: r.dom_freq_pitch_hz),
]


def _plot_point_tip(y_value: float | None, filename: str) -> str:
    if y_value is None:
        y_text = "—"
    else:
        y_text = f"{float(y_value):.6g}"
    return f"Value: {y_text}\nNama file: {filename}"


def _scatter_hover_tip(x: float, y: float, data: object) -> str:
    """Callback ``tip`` untuk ``ScatterPlotItem`` (pyqtgraph memanggil dengan x, y, data)."""
    del x, y
    if not isinstance(data, dict):
        return ""
    y_val = data.get("y_raw")
    filename = str(data.get("filename") or "")
    if y_val is None:
        return _plot_point_tip(None, filename)
    return _plot_point_tip(float(y_val), filename)


def _group_style(group: str) -> _GroupStyle:
    return _GROUP_STYLES.get(group, _GROUP_STYLES[GROUP_REGION])


class AnalyzeMultiFileTab(QWidget):
    """Tabel perbandingan berkas DataStatistik (maks. ``MAX_FILES``)."""

    def __init__(
        self,
        *,
        datastatistik_dir: Path,
        themed_stat_message: Callable[..., None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._datastatistik_dir = datastatistik_dir
        self._themed_stat_message = themed_stat_message

        self._entries: list[dict[str, object]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        row1 = QHBoxLayout()
        self.add_btn = QPushButton("Add file", self)
        self.add_btn.setToolTip(
            f"Tambah berkas DataStatistik (maks. {MAX_FILES}). "
            "Setiap berkas menambah satu kolom di tabel."
        )
        self.add_btn.clicked.connect(self._on_add_file)
        row1.addWidget(self.add_btn)
        self.plot_btn = QPushButton("Plot data", self)
        self.plot_btn.setObjectName("PlotDataGreenButton")
        self.plot_btn.setEnabled(False)
        self.plot_btn.setToolTip(
            "Buka jendela plot: pilih metrik dan gaya diagram (batang / garis / titik)."
        )
        self.plot_btn.clicked.connect(self._on_plot_data)
        row1.addWidget(self.plot_btn)
        row1.addStretch(1)
        row1.addWidget(QLabel("Hapus kolom:", self))
        self._clear_target_combo = QComboBox(self)
        for k in range(1, MAX_FILES + 1):
            self._clear_target_combo.addItem(f"Kolom {k}", userData=k)
        self._clear_target_combo.addItem("Semua kolom", userData=0)
        self._clear_target_combo.setMinimumWidth(140)
        self._clear_target_combo.setToolTip(
            "Pilih kolom data (1 = berkas pertama, …) atau semua; lalu tekan Clear tabel."
        )
        row1.addWidget(self._clear_target_combo)
        self.clear_btn = QPushButton("Clear tabel", self)
        self.clear_btn.setObjectName("ClearTableDangerButton")
        self.clear_btn.setToolTip("Hapus kolom terpilih dari tabel (berkas dikeluarkan dari daftar).")
        self.clear_btn.clicked.connect(self._on_clear_table)
        row1.addWidget(self.clear_btn)
        root.addLayout(row1)

        self.table = QTableWidget(self)
        self.table.setColumnCount(1)
        self.table.setRowCount(TOTAL_ROWS)
        self.table.setHorizontalHeaderLabels([""])
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._refresh_table()
        root.addWidget(self.table, 1)

        self.setStyleSheet(
            """
            QLabel { color: #e5e7eb; }
            QPushButton {
                padding: 8px 14px;
                background-color: #3b82f6;
                color: #fff;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled {
                background-color: #4b5563;
                color: #9ca3af;
            }
            QPushButton#ClearTableDangerButton {
                padding: 8px 14px;
                background-color: #dc2626;
                color: #fff;
                border: none;
                border-radius: 8px;
            }
            QPushButton#ClearTableDangerButton:hover { background-color: #b91c1c; }
            QPushButton#ClearTableDangerButton:pressed { background-color: #991b1b; }
            QPushButton#PlotDataGreenButton {
                padding: 8px 14px;
                background-color: #16a34a;
                color: #fff;
                border: none;
                border-radius: 8px;
            }
            QPushButton#PlotDataGreenButton:hover { background-color: #15803d; }
            QPushButton#PlotDataGreenButton:pressed { background-color: #166534; }
            QPushButton#PlotDataGreenButton:disabled {
                background-color: #4b5563;
                color: #9ca3af;
            }
            QComboBox {
                background: #374151;
                color: #e5e7eb;
                border: 1px solid #4b5563;
                padding: 6px;
                border-radius: 8px;
            }
            QTableWidget {
                background: #0f172a;
                color: #e5e7eb;
                gridline-color: #334155;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QTableCornerButton::section { background: #14532d; }
            """
        )

    def _on_clear_table(self) -> None:
        if not self._entries:
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Clear tabel",
                "Tabel sudah kosong (belum ada berkas yang dimuat).",
            )
            return
        raw = self._clear_target_combo.currentData()
        clear_all = raw == 0
        if clear_all:
            self._entries.clear()
            self._refresh_table()
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Clear tabel",
                "Semua kolom data telah dihapus.",
            )
            return
        col_1based = int(raw) if raw is not None else 1
        if not (1 <= col_1based <= MAX_FILES):
            return
        idx = col_1based - 1
        if idx >= len(self._entries):
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Clear tabel",
                f"Tidak ada data pada kolom {col_1based} (hanya {len(self._entries)} berkas terpasang).",
            )
            return
        del self._entries[idx]
        self._refresh_table()
        self._themed_stat_message(
            QMessageBox.Icon.Information,
            "Clear tabel",
            f"Kolom {col_1based} dihapus (satu berkas dikeluarkan).",
        )

    def _on_plot_data(self) -> None:
        if not self._entries:
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Plot data",
                "Tambah setidaknya satu berkas DataStatistik (Add file) sebelum memplot.",
            )
            return
        dlg = MultiFilePlotDialog(self)
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dlg.show()

    def _make_item(
        self,
        text: str,
        *,
        header: bool = False,
        value_header: bool = False,
        tooltip: str | None = None,
    ) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        f = QFont("Segoe UI", 10)
        if header or value_header:
            f.setBold(True)
        it.setFont(f)
        if tooltip:
            it.setToolTip(tooltip)
        if header:
            it.setBackground(QColor("#bbf7d0"))
            it.setForeground(QColor("#14532d"))
            it.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )
        elif value_header:
            it.setBackground(QColor("#bae6fd"))
            it.setForeground(QColor("#0c4a6e"))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            it.setForeground(QColor("#e5e7eb"))
            it.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )
        return it

    def _make_group_header_item(self, text: str, style: _GroupStyle) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        f = QFont("Segoe UI", 10)
        f.setBold(True)
        it.setFont(f)
        it.setBackground(QBrush(QColor(style.header_bg)))
        it.setForeground(QBrush(QColor(style.accent)))
        align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        it.setTextAlignment(align)
        return it

    def _make_param_item(self, text: str, style: _GroupStyle) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        it.setBackground(QBrush(QColor(style.row_bg)))
        it.setForeground(QBrush(QColor("#9ca3af")))
        it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return it

    def _make_value_item(self, text: str, style: _GroupStyle) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        it.setBackground(QBrush(QColor(style.row_bg)))
        it.setForeground(QBrush(QColor(style.accent)))
        it.setTextAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        return it

    def _on_add_file(self) -> None:
        if len(self._entries) >= MAX_FILES:
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Analisa multifile",
                f"Sudah mencapai batas maksimum {MAX_FILES} berkas.",
            )
            return
        start_dir = (
            str(self._datastatistik_dir)
            if self._datastatistik_dir.is_dir()
            else str(self._datastatistik_dir.parent)
        )
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih CSV DataStatistik",
            start_dir,
            "CSV DataStatistik (*_DataStatistik*.csv);;CSV (*.csv);;Semua (*.*)",
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            record = parse_datastatistik_csv(path)
        except OSError as e:
            QMessageBox.critical(self, "Load CSV", f"Tidak bisa membaca file:\n{e}")
            return
        except ValueError as e:
            QMessageBox.warning(self, "Load CSV", str(e))
            return

        self._entries.append(
            {
                "path": path,
                "record": record,
                "swimmer": record.swimmer or EMPTY_CELL,
                "stroke": record.stroke or EMPTY_CELL,
                "filename": path.name,
                "exported_at": record.exported_at or EMPTY_CELL,
                "source_file": record.source_file or EMPTY_CELL,
            }
        )
        self._refresh_table()

    def _refresh_table(self) -> None:
        n = len(self._entries)
        cols = 1 if n == 0 else 1 + n
        self.table.clear()
        self.table.setColumnCount(cols)
        self.table.setRowCount(TOTAL_ROWS)
        self.table.setItem(0, 0, self._make_item("Metrik", header=True))
        self.table.setSpan(0, 0, HEADER_ROWS, 1)
        for i, spec in enumerate(TABLE_ROWS):
            row = HEADER_ROWS + i
            style = _group_style(spec.group)
            if spec.kind == "group":
                for c in range(cols):
                    label = spec.label if c == 0 else ""
                    self.table.setItem(row, c, self._make_group_header_item(label, style))
            else:
                self.table.setItem(row, 0, self._make_param_item(spec.label, style))
        for j, ent in enumerate(self._entries, start=1):
            self._set_column_headers(
                j,
                str(ent["swimmer"]),
                str(ent["stroke"]),
                str(ent["filename"]),
                str(ent["exported_at"]),
                str(ent["source_file"]),
            )
            rec = ent["record"]
            assert isinstance(rec, StatistikExportRecord)
            self._fill_metrics_column(j, rec)
        self.plot_btn.setEnabled(n > 0)
        self._apply_table_column_layout()
        self._apply_header_row_heights()

    def _apply_table_column_layout(self) -> None:
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for c in range(1, self.table.columnCount()):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(c, DATA_COLUMN_WIDTH_PX)
        self.table.resizeColumnToContents(0)

    def _apply_header_row_heights(self) -> None:
        for row in range(HEADER_ROWS):
            if row in (HEADER_ROW_FILENAME, HEADER_ROW_SOURCE):
                self.table.resizeRowToContents(row)
            else:
                self.table.setRowHeight(row, HEADER_ROW_DEFAULT_HEIGHT)

    def _set_column_headers(
        self,
        col: int,
        swimmer: str,
        stroke: str,
        filename: str,
        exported_at: str,
        source_file: str,
    ) -> None:
        self.table.setItem(0, col, self._make_item(swimmer, header=True))
        self.table.setItem(1, col, self._make_item(stroke, header=True))
        self.table.setItem(
            2,
            col,
            self._make_item(
                _wrap_header_text(filename),
                header=True,
                tooltip=filename,
            ),
        )
        self.table.setItem(3, col, self._make_item(exported_at, header=True))
        self.table.setItem(
            4,
            col,
            self._make_item(
                _wrap_header_text(source_file),
                header=True,
                tooltip=source_file,
            ),
        )
        self.table.setItem(5, col, self._make_item("Value", value_header=True))

    def _fill_metrics_column(self, col: int, rec: StatistikExportRecord) -> None:
        for i, spec in enumerate(TABLE_ROWS):
            if spec.kind != "metric" or spec.getter is None:
                continue
            row = HEADER_ROWS + i
            style = _group_style(spec.group)
            text = spec.getter(rec)
            self.table.setItem(row, col, self._make_value_item(text, style))

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_table_column_layout()
        self._apply_header_row_heights()


class MultiFilePlotDialog(QDialog):
    """Jendela plot perbandingan metrik dari berkas DataStatistik yang dimuat."""

    def __init__(self, source_tab: AnalyzeMultiFileTab, parent: QWidget | None = None) -> None:
        super().__init__(parent or source_tab)
        self._tab = source_tab
        self.setWindowTitle("Plot perbandingan berkas")
        self.resize(840, 580)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Metrik:", self))
        self._metric_combo = QComboBox(self)
        for title, _yl, _fn in PLOT_METRIC_SPECS:
            self._metric_combo.addItem(title)
        self._metric_combo.setMinimumWidth(240)
        ctrl.addWidget(self._metric_combo)
        ctrl.addSpacing(18)
        ctrl.addWidget(QLabel("Gaya plot:", self))
        self._style_combo = QComboBox(self)
        self._style_combo.addItem("Garis + penanda", userData=PLOT_STYLE_LINE)
        self._style_combo.addItem("Diagram batang", userData=PLOT_STYLE_BAR)
        self._style_combo.addItem("Titik saja", userData=PLOT_STYLE_SCATTER)
        self._style_combo.setMinimumWidth(170)
        ctrl.addWidget(self._style_combo)
        ctrl.addStretch(1)
        outer.addLayout(ctrl)

        self._pw = pg.PlotWidget()
        self._pw.setBackground("#1f2937")
        for ax_name in ("left", "bottom"):
            ax = self._pw.getAxis(ax_name)
            ax.setPen(pg.mkPen("#94a3b8"))
            ax.setTextPen(pg.mkPen("#e5e7eb"))
        self._pw.showGrid(x=False, y=True, alpha=0.25)
        self._pw.setLabel(
            "bottom",
            "Nomor kolom",
            color="#e5e7eb",
            **{"font-size": "10pt"},
        )
        outer.addWidget(self._pw, 1)

        self._footnote_lbl = QLabel("", self)
        self._footnote_lbl.setWordWrap(True)
        self._footnote_lbl.setStyleSheet("color:#94a3b8;font-size:10pt;padding-top:4px;")
        outer.addWidget(self._footnote_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("Tutup", self)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        outer.addLayout(btn_row)

        self._metric_combo.currentIndexChanged.connect(self._on_plot_control_changed)
        self._style_combo.currentIndexChanged.connect(self._on_plot_control_changed)

        self.setStyleSheet(
            """
            QDialog { background-color: #111827; }
            QLabel { color: #e5e7eb; }
            QComboBox {
                background: #374151;
                color: #e5e7eb;
                border: 1px solid #4b5563;
                padding: 6px;
                border-radius: 8px;
                min-height: 22px;
            }
            QPushButton {
                padding: 8px 16px;
                background: #3b82f6;
                color: #fff;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background: #2563eb; }
            """
        )

        self._redraw()

    def _on_plot_control_changed(self, _index: int) -> None:
        self._redraw()

    def _gather_series(
        self,
    ) -> tuple[list[str], list[float | None], list[str], str, str]:
        entries = self._tab._entries
        ix = self._metric_combo.currentIndex()
        if ix < 0 or ix >= len(PLOT_METRIC_SPECS):
            ix = 0
        title_combo, y_axis_label, extractor = PLOT_METRIC_SPECS[ix]
        x_labels: list[str] = []
        y_raw: list[float | None] = []
        filenames: list[str] = []
        for col_idx, ent in enumerate(entries, start=1):
            rec = ent["record"]
            assert isinstance(rec, StatistikExportRecord)
            v = extractor(rec)
            x_labels.append(str(col_idx))
            filenames.append(str(ent["filename"]))
            y_raw.append(float(v) if v is not None else None)
        return x_labels, y_raw, filenames, y_axis_label, title_combo

    def _add_hover_markers(
        self,
        x: np.ndarray,
        y_plot: np.ndarray,
        y_raw: list[float | None],
        filenames: list[str],
    ) -> None:
        spots: list[dict[str, object]] = []
        for i in range(len(y_plot)):
            spots.append(
                {
                    "pos": (float(x[i]), float(y_plot[i])),
                    "size": 18,
                    "brush": pg.mkBrush(0, 0, 0, 0),
                    "pen": pg.mkPen(None),
                    "data": {
                        "y_raw": y_raw[i],
                        "filename": filenames[i],
                    },
                }
            )

        hover = pg.ScatterPlotItem(hoverable=True, pxMode=True, tip=_scatter_hover_tip)
        hover.addPoints(spots)
        hover.setZValue(100)
        self._pw.addItem(hover)
        self._pw.setMouseTracking(True)

    def _redraw(self) -> None:
        x_labels, y_raw, filenames, y_axis_label, title_combo = self._gather_series()
        n = len(y_raw)
        self._pw.clear()
        self.setWindowTitle(f"Plot — {title_combo}")

        if n == 0:
            self._pw.setLabel("left", "—", color="#e5e7eb", **{"font-size": "11pt"})
            self._footnote_lbl.setText(
                "Tidak ada berkas di tabel. Tutup jendela ini lalu tambah berkas di tab."
            )
            return

        if all(x is None for x in y_raw):
            self._pw.setLabel("left", y_axis_label, color="#e5e7eb", **{"font-size": "11pt"})
            self._footnote_lbl.setText("Semua nilai kosong untuk metrik ini.")
            return

        if any(x is None for x in y_raw):
            self._footnote_lbl.setText(
                "Catatan: nilai yang tidak tersedia ditampilkan sebagai 0 pada diagram. "
                "Arahkan kursor ke penanda/batang untuk nilai asli dan nama file."
            )
        else:
            self._footnote_lbl.setText(
                "Arahkan kursor ke penanda/batang untuk melihat nilai dan nama file. "
                "Nilai dari ekspor DataStatistik tab Analisa."
            )

        y_plot = np.array([0.0 if x is None else float(x) for x in y_raw], dtype=np.float64)
        x = np.arange(n, dtype=float)
        raw_style = self._style_combo.currentData()
        style = raw_style if isinstance(raw_style, str) else PLOT_STYLE_LINE

        self._pw.setLabel("left", y_axis_label, color="#e5e7eb", **{"font-size": "11pt"})
        tick_specs = [(float(i), x_labels[i]) for i in range(n)]
        self._pw.getAxis("bottom").setTicks([tick_specs])

        green_pen = pg.mkPen("#22c55e", width=2)
        sym_brush = pg.mkBrush("#86efac")
        sym_pen = pg.mkPen("#14532d", width=1)

        if style == PLOT_STYLE_BAR:
            self._pw.addItem(
                pg.BarGraphItem(
                    x=x,
                    height=y_plot,
                    width=0.62,
                    brush=pg.mkBrush("#22c55e"),
                    pen=pg.mkPen("#14532d", width=1),
                    base=0.0,
                )
            )
        elif style == PLOT_STYLE_LINE:
            self._pw.plot(
                x,
                y_plot,
                pen=green_pen,
                symbol="o",
                symbolSize=10,
                symbolBrush=sym_brush,
                symbolPen=sym_pen,
            )
        else:
            self._pw.plot(
                x,
                y_plot,
                pen=None,
                symbol="o",
                symbolSize=12,
                symbolBrush=sym_brush,
                symbolPen=sym_pen,
            )

        self._add_hover_markers(x, y_plot, y_raw, filenames)

        vb = self._pw.getViewBox()
        vb.setLimits(xMin=-0.6, xMax=max(float(n - 1) + 0.6, 0.6))
        self._pw.enableAutoRange()

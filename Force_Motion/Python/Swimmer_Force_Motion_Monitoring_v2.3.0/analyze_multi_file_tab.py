"""
Tab **Analisa multifile** — bandingkan hingga lima berkas ``DataStatistik/`` dalam
satu tabel (``QTableWidget``). **Add file** menambah kolom; **Clear tabel** menghapus
kolom terpilih. Simpan tabel dan plot perbandingan — belum diaktifkan.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
DATA_COLUMN_WIDTH_PX = 168
HEADER_WRAP_CHARS = 22
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

TABLE_MULTIFILE_DIRNAME = "TableMultiFile"
TABLE_MULTIFILE_SUFFIX = "_TableMultiFile"


def _path_text_for_dialog(path: Path | str) -> str:
    s = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    if len(s) >= 3 and s[0].isalpha() and s[1] == ":" and s[2] == "/":
        s = s[:2] + "\u2060" + s[2:]
    return s


def _group_style(group: str) -> _GroupStyle:
    return _GROUP_STYLES.get(group, _GROUP_STYLES[GROUP_REGION])


class AnalyzeMultiFileTab(QWidget):
    """Tabel perbandingan berkas DataStatistik (maks. ``MAX_FILES``)."""

    def __init__(
        self,
        *,
        datastatistik_dir: Path,
        table_multi_file_dir: Path,
        themed_stat_message: Callable[..., None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._datastatistik_dir = datastatistik_dir
        self._table_multi_file_dir = table_multi_file_dir
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
        self.save_btn = QPushButton("Simpan tabel ke CSV", self)
        self.save_btn.setObjectName("SaveTableGrayButton")
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Segera hadir — ekspor tabel multifile belum diaktifkan.")
        self.save_btn.clicked.connect(self._on_save_csv)
        row1.addWidget(self.add_btn)
        row1.addWidget(self.save_btn)
        self.plot_btn = QPushButton("Plot data", self)
        self.plot_btn.setObjectName("PlotDataGreenButton")
        self.plot_btn.setEnabled(False)
        self.plot_btn.setToolTip("Segera hadir — plot perbandingan belum diaktifkan.")
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
            QPushButton#SaveTableGrayButton {
                padding: 8px 14px;
                background-color: #6b7280;
                color: #ffffff;
                border: none;
                border-radius: 8px;
            }
            QPushButton#SaveTableGrayButton:hover { background-color: #4b5563; }
            QPushButton#SaveTableGrayButton:pressed { background-color: #374151; }
            QPushButton#SaveTableGrayButton:disabled {
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
        self._themed_stat_message(
            QMessageBox.Icon.Information,
            "Plot data",
            "Fitur plot perbandingan belum diaktifkan.",
        )

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

    def _on_save_csv(self) -> None:
        self._themed_stat_message(
            QMessageBox.Icon.Information,
            "Simpan tabel",
            "Fitur simpan tabel multifile belum diaktifkan.",
        )

    def _cell_text(self, row: int, col: int) -> str:
        it = self.table.item(row, col)
        return it.text() if it is not None else ""

    def _write_table_csv(self, path: Path) -> None:
        """Simpan isi tabel baris-per-baris (header multi-baris sesuai tampilan)."""
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for r in range(rows):
                w.writerow([self._cell_text(r, c) for c in range(cols)])

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_table_column_layout()
        self._apply_header_row_heights()


class MultiFilePlotDialog(QDialog):
    """Jendela plot perbandingan — belum dihubungkan ke DataStatistik (reserved)."""

    def __init__(self, source_tab: AnalyzeMultiFileTab, parent: QWidget | None = None) -> None:
        super().__init__(parent or source_tab)
        self._tab = source_tab
        self.setWindowTitle("Plot perbandingan berkas")
        self.resize(840, 580)
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("Plot perbandingan belum diaktifkan.", self))

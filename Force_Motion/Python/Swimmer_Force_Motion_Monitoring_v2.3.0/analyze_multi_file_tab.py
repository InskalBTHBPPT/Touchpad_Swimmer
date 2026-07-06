"""
Tab **Analisa multifile** — bandingkan hingga lima berkas ``DataStatistik/`` dalam
satu tabel (``QTableWidget``). **Add file** menambah kolom; **Clear tabel** menghapus
kolom terpilih. Simpan tabel dan plot perbandingan — belum diaktifkan.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
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
DATA_ROWS = 32
TOTAL_ROWS = HEADER_ROWS + DATA_ROWS

METRIC_LABELS = [
    "Metode statistik Force",
    "Timestamp start uji (s)",
    "Timestamp stop uji (s)",
    "Durasi region data uji (s)",
    "Jumlah siklus Andrade (n)",
    "Filter Andrade cutoff (Hz)",
    "Force peakF (Kg)",
    "Timestamp Force peakF (s)",
    "Force meanF (Kg)",
    "Force ImpF (Kg·s)",
    "Force TpeakF (s)",
    "Force DUR (s)",
    "Force RFD (Kg/s)",
    "Force dF (%)",
    "Fatigue Index FI (%)",
    "Force minF (Kg)",
    "Timestamp Force minF (s)",
    "Roll minimum (Deg)",
    "Timestamp Roll minimum (s)",
    "Roll maksimum (Deg)",
    "Timestamp Roll maksimum (s)",
    "Pitch minimum (Deg)",
    "Timestamp Pitch minimum (s)",
    "Pitch maksimum (Deg)",
    "Timestamp Pitch maksimum (s)",
    "Frekuensi dominan Force (Hz)",
    "Frekuensi dominan Roll (Hz)",
    "Frekuensi dominan Pitch (Hz)",
    "Metode spektrum",
    "Gap — metode",
    "Gap — Δt nominal (s)",
    "Gap — sampel hilang (%)",
]

TABLE_MULTIFILE_DIRNAME = "TableMultiFile"
TABLE_MULTIFILE_SUFFIX = "_TableMultiFile"
EMPTY_CELL = "—"


def _path_text_for_dialog(path: Path | str) -> str:
    s = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    if len(s) >= 3 and s[0].isalpha() and s[1] == ":" and s[2] == "/":
        s = s[:2] + "\u2060" + s[2:]
    return s


def _fmt_cell(v: float | int | str | None) -> str:
    if v is None:
        return EMPTY_CELL
    if isinstance(v, str):
        return v.strip() if v.strip() else EMPTY_CELL
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _force_method_text(rec: StatistikExportRecord) -> str:
    label = (rec.force_stats_method or "").strip()
    if not label:
        return EMPTY_CELL
    if rec.force_stroke_count is not None and rec.force_stroke_count > 0:
        label += f" · n={rec.force_stroke_count}"
    if rec.force_stats_fallback_global:
        label += " · fallback global"
    return label


def _statistik_to_cells(rec: StatistikExportRecord) -> list[str]:
    return [
        _force_method_text(rec),
        _fmt_cell(rec.timestamp_start_s),
        _fmt_cell(rec.timestamp_stop_s),
        _fmt_cell(rec.test_region_duration_s),
        _fmt_cell(rec.force_stroke_count),
        _fmt_cell(rec.andrade_filter_cutoff_hz),
        _fmt_cell(rec.force_peak_kg),
        _fmt_cell(rec.force_peak_t_s),
        _fmt_cell(rec.force_mean_kg),
        _fmt_cell(rec.force_impulse_kg_s),
        _fmt_cell(rec.force_t_peak_f_s),
        _fmt_cell(rec.force_dur_s),
        _fmt_cell(rec.force_rfd_kg_s),
        _fmt_cell(rec.force_df_pct),
        _fmt_cell(rec.force_fi_pct),
        _fmt_cell(rec.force_min_kg),
        _fmt_cell(rec.force_min_t_s),
        _fmt_cell(rec.roll_min_deg),
        _fmt_cell(rec.roll_min_t_s),
        _fmt_cell(rec.roll_max_deg),
        _fmt_cell(rec.roll_max_t_s),
        _fmt_cell(rec.pitch_min_deg),
        _fmt_cell(rec.pitch_min_t_s),
        _fmt_cell(rec.pitch_max_deg),
        _fmt_cell(rec.pitch_max_t_s),
        _fmt_cell(rec.dom_freq_force_hz),
        _fmt_cell(rec.dom_freq_roll_hz),
        _fmt_cell(rec.dom_freq_pitch_hz),
        _fmt_cell(rec.spectrum_method),
        _fmt_cell(rec.gap_method),
        _fmt_cell(rec.gap_dt_nominal_s),
        _fmt_cell(rec.gap_loss_pct),
    ]


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

    def _make_item(self, text: str, *, header: bool = False, value_header: bool = False) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        f = QFont("Segoe UI", 10)
        if header or value_header:
            f.setBold(True)
        it.setFont(f)
        if header:
            it.setBackground(QColor("#bbf7d0"))
            it.setForeground(QColor("#14532d"))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
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
        for i, label in enumerate(METRIC_LABELS):
            self.table.setItem(HEADER_ROWS + i, 0, self._make_item(label))
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
        self.table.resizeColumnsToContents()

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
        self.table.setItem(2, col, self._make_item(filename, header=True))
        self.table.setItem(3, col, self._make_item(exported_at, header=True))
        self.table.setItem(4, col, self._make_item(source_file, header=True))
        self.table.setItem(5, col, self._make_item("Value", value_header=True))

    def _fill_metrics_column(self, col: int, rec: StatistikExportRecord) -> None:
        cells = _statistik_to_cells(rec)
        for i, text in enumerate(cells):
            row = HEADER_ROWS + i
            self.table.setItem(row, col, self._make_item(text))

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
        self.table.resizeColumnsToContents()


class MultiFilePlotDialog(QDialog):
    """Jendela plot perbandingan — belum dihubungkan ke DataStatistik (reserved)."""

    def __init__(self, source_tab: AnalyzeMultiFileTab, parent: QWidget | None = None) -> None:
        super().__init__(parent or source_tab)
        self._tab = source_tab
        self.setWindowTitle("Plot perbandingan berkas")
        self.resize(840, 580)
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("Plot perbandingan belum diaktifkan.", self))

"""
Tab **Analisa multifile** — bandingkan hingga lima rekaman CSV Live dalam satu tabel.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
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

from analyze_metrics_core import RecordingMetrics, compute_recording_metrics
from live_csv_io import parse_logged_csv


MAX_FILES = 5
HEADER_ROWS = 4
DATA_ROWS = 15
TOTAL_ROWS = HEADER_ROWS + DATA_ROWS

METRIC_LABELS = [
    "Timestamp start (s)",
    "Force Maksimum (Kg)",
    "Timestamp Force Maksimum (s)",
    "Frekuensi Dominan Force (Hz)",
    "Roll Maksimum (Deg)",
    "Timestamp Roll Maksimum (s)",
    "Roll Minimum (Deg)",
    "Timestamp Roll Minimum (s)",
    "Frekuensi Dominan Roll (Hz)",
    "Pitch Maksimum (Deg)",
    "Timestamp Pitch Maksimum (s)",
    "Pitch Minimum (Deg)",
    "Timestamp Pitch Minimum (s)",
    "Frekuensi Dominan Pitch (Hz)",
    "Metode Spektrum Frekuensi",
]

TABLE_MULTIFILE_DIRNAME = "TableMultiFile"
TABLE_MULTIFILE_SUFFIX = "_TableMultiFile"


def _path_text_for_dialog(path: Path | str) -> str:
    s = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    if len(s) >= 3 and s[0].isalpha() and s[1] == ":" and s[2] == "/":
        s = s[:2] + "\u2060" + s[2:]
    return s


def _fmt_num(v: float | None, *, empty: str = "") -> str:
    if v is None:
        return empty
    return f"{float(v):.6g}"


def _metrics_to_cells(m: RecordingMetrics) -> list[str]:
    return [
        _fmt_num(m.timestamp_start_s),
        _fmt_num(m.force_max_kg),
        _fmt_num(m.force_max_t_s),
        _fmt_num(m.dom_freq_force_hz),
        _fmt_num(m.roll_max_deg),
        _fmt_num(m.roll_max_t_s),
        _fmt_num(m.roll_min_deg),
        _fmt_num(m.roll_min_t_s),
        _fmt_num(m.dom_freq_roll_hz),
        _fmt_num(m.pitch_max_deg),
        _fmt_num(m.pitch_max_t_s),
        _fmt_num(m.pitch_min_deg),
        _fmt_num(m.pitch_min_t_s),
        _fmt_num(m.dom_freq_pitch_hz),
        m.spectrum_method_label,
    ]


class AnalyzeMultiFileTab(QWidget):
    """Tabel perbandingan beberapa berkas log (maks. ``MAX_FILES``)."""

    def __init__(
        self,
        *,
        datalog_dir: Path,
        table_multi_file_dir: Path,
        themed_stat_message: Callable[..., None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._datalog_dir = datalog_dir
        self._table_multi_file_dir = table_multi_file_dir
        self._themed_stat_message = themed_stat_message

        self._entries: list[dict[str, object]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        row1 = QHBoxLayout()
        self.add_btn = QPushButton("Add file", self)
        self.add_btn.setToolTip(f"Tambah berkas log (maks. {MAX_FILES}).")
        self.add_btn.clicked.connect(self._on_add_file)
        self.save_btn = QPushButton("Simpan tabel ke CSV", self)
        self.save_btn.setToolTip(
            f"Simpan ke folder {TABLE_MULTIFILE_DIRNAME}/ dengan sufiks {TABLE_MULTIFILE_SUFFIX}.csv"
        )
        self.save_btn.clicked.connect(self._on_save_csv)
        row1.addWidget(self.add_btn)
        row1.addWidget(self.save_btn)
        row1.addStretch(1)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Metode spektrum:", self))
        self._spectrum_method_combo = QComboBox(self)
        self._spectrum_method_combo.addItem("FFT", userData=False)
        self._spectrum_method_combo.addItem("Welch PSD", userData=True)
        self._spectrum_method_combo.setMinimumWidth(140)
        self._spectrum_method_combo.blockSignals(True)
        self._spectrum_method_combo.setCurrentIndex(0)
        self._spectrum_method_combo.blockSignals(False)
        self._spectrum_method_combo.currentIndexChanged.connect(self._on_spectrum_method_changed)
        row2.addWidget(self._spectrum_method_combo)
        row2.addStretch(1)
        root.addLayout(row2)

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

    def _spectrum_use_welch(self) -> bool:
        i = self._spectrum_method_combo.currentIndex()
        v = self._spectrum_method_combo.itemData(i)
        return bool(v) if v is not None else False

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
        return it

    def _on_add_file(self) -> None:
        if len(self._entries) >= MAX_FILES:
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Analisa multifile",
                f"Sudah mencapai batas maksimum {MAX_FILES} berkas.",
            )
            return
        start_dir = str(self._datalog_dir) if self._datalog_dir.is_dir() else str(self._datalog_dir.parent)
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih CSV rekaman",
            start_dir,
            "CSV (*.csv);;Semua (*.*)",
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            swimmer, stroke, ts_list, f_list, r_list, p_list = parse_logged_csv(path)
        except OSError as e:
            QMessageBox.critical(self, "Load CSV", f"Tidak bisa membaca file:\n{e}")
            return
        except ValueError as e:
            QMessageBox.warning(self, "Load CSV", str(e))
            return

        self._entries.append(
            {
                "path": path,
                "swimmer": swimmer,
                "stroke": stroke,
                "filename": path.name,
                "ts_list": ts_list,
                "f_list": f_list,
                "r_list": r_list,
                "p_list": p_list,
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
        use_welch = self._spectrum_use_welch()
        for j, ent in enumerate(self._entries, start=1):
            self._set_column_headers(
                j,
                str(ent["swimmer"]),
                str(ent["stroke"]),
                str(ent["filename"]),
            )
            m = compute_recording_metrics(
                list(ent["ts_list"]),
                list(ent["f_list"]),
                list(ent["r_list"]),
                list(ent["p_list"]),
                use_welch=use_welch,
            )
            self._fill_metrics_column(j, m)
        self.table.resizeColumnsToContents()

    def _set_column_headers(self, col: int, swimmer: str, stroke: str, filename: str) -> None:
        self.table.setItem(0, col, self._make_item(swimmer, header=True))
        self.table.setItem(1, col, self._make_item(stroke, header=True))
        self.table.setItem(2, col, self._make_item(filename, header=True))
        self.table.setItem(3, col, self._make_item("Value", value_header=True))

    def _fill_metrics_column(self, col: int, m: RecordingMetrics) -> None:
        cells = _metrics_to_cells(m)
        for i, text in enumerate(cells):
            row = HEADER_ROWS + i
            self.table.setItem(row, col, self._make_item(text))

    def _on_spectrum_method_changed(self, _index: int) -> None:
        if not self._entries:
            return
        self._refresh_table()

    def _on_save_csv(self) -> None:
        if not self._entries:
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Simpan tabel",
                "Belum ada berkas yang dimuat. Gunakan Add file terlebih dahulu.",
            )
            return
        try:
            self._table_multi_file_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._themed_stat_message(
                QMessageBox.Icon.Critical,
                "Simpan tabel",
                f"Tidak bisa membuat folder:\n{e}",
            )
            return
        stamp = datetime.now().strftime("%d%m%y_%H%M%S")
        out_name = f"{stamp}{TABLE_MULTIFILE_SUFFIX}.csv"
        path = self._table_multi_file_dir / out_name
        try:
            self._write_table_csv(path)
        except OSError as e:
            self._themed_stat_message(
                QMessageBox.Icon.Critical,
                "Simpan tabel",
                f"Tidak bisa menulis file:\n{e}",
            )
            return
        self._themed_stat_message(
            QMessageBox.Icon.Information,
            "Simpan tabel",
            f"Tersimpan:\n{_path_text_for_dialog(path)}",
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

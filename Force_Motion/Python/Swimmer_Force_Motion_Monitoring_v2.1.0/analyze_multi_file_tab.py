"""
Tab **Analisa multifile** — bandingkan hingga lima rekaman CSV Live dalam satu tabel,
opsi hapus kolom, dan **plot perbandingan** di jendela terpisah (pyqtgraph).
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np
import pyqtgraph as pg
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

# (teks combo, label sumbu Y, ekstraktor nilai dari RecordingMetrics)
PLOT_METRIC_SPECS: list[
    tuple[str, str, Callable[[RecordingMetrics], float | None]]
] = [
    ("Force maksimum (Kg)", "Force (Kg)", lambda m: m.force_max_kg),
    ("Roll maksimum (°)", "Roll (°)", lambda m: m.roll_max_deg),
    ("Roll minimum (°)", "Roll (°)", lambda m: m.roll_min_deg),
    ("Pitch maksimum (°)", "Pitch (°)", lambda m: m.pitch_max_deg),
    ("Pitch minimum (°)", "Pitch (°)", lambda m: m.pitch_min_deg),
    ("Frekuensi dominan Force (Hz)", "f (Hz)", lambda m: m.dom_freq_force_hz),
    ("Frekuensi dominan Roll (Hz)", "f (Hz)", lambda m: m.dom_freq_roll_hz),
    ("Frekuensi dominan Pitch (Hz)", "f (Hz)", lambda m: m.dom_freq_pitch_hz),
]

PLOT_STYLE_BAR = "bar"
PLOT_STYLE_LINE = "line"
PLOT_STYLE_SCATTER = "scatter"


def _short_label(s: str, max_len: int = 16) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


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
        self.save_btn.setObjectName("SaveTableGrayButton")
        self.save_btn.setToolTip(
            f"Simpan ke folder {TABLE_MULTIFILE_DIRNAME}/ dengan sufiks {TABLE_MULTIFILE_SUFFIX}.csv"
        )
        self.save_btn.clicked.connect(self._on_save_csv)
        row1.addWidget(self.add_btn)
        row1.addWidget(self.save_btn)
        self.plot_btn = QPushButton("Plot data", self)
        self.plot_btn.setObjectName("PlotDataGreenButton")
        self.plot_btn.setToolTip(
            "Buka jendela plot: pilih metrik dan gaya diagram di dalam jendela tersebut."
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
        self.clear_btn.setToolTip("Hapus data kolom terpilih dari tabel (berkas dikeluarkan dari daftar).")
        self.clear_btn.clicked.connect(self._on_clear_table)
        row1.addWidget(self.clear_btn)
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
            QPushButton#SaveTableGrayButton {
                padding: 8px 14px;
                background-color: #6b7280;
                color: #ffffff;
                border: none;
                border-radius: 8px;
            }
            QPushButton#SaveTableGrayButton:hover { background-color: #4b5563; }
            QPushButton#SaveTableGrayButton:pressed { background-color: #374151; }
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

    def _spectrum_use_welch(self) -> bool:
        i = self._spectrum_method_combo.currentIndex()
        v = self._spectrum_method_combo.itemData(i)
        return bool(v) if v is not None else False

    def _on_plot_data(self) -> None:
        if not self._entries:
            self._themed_stat_message(
                QMessageBox.Icon.Information,
                "Plot data",
                "Tambah setidaknya satu berkas (Add file) sebelum memplot.",
            )
            return
        dlg = MultiFilePlotDialog(self)
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dlg.show()

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


class MultiFilePlotDialog(QDialog):
    """Jendela plot: pilihan metrik dan gaya diagram; data mengikuti tab Analisa multifile."""

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
        self._metric_combo.setMinimumWidth(220)
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
        self._pw.setLabel("bottom", "Urutan kolom (berkas dimuat)", color="#e5e7eb", **{"font-size": "10pt"})
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
    ) -> tuple[list[str], list[float | None], str, str, str]:
        entries = self._tab._entries
        ix = self._metric_combo.currentIndex()
        if ix < 0 or ix >= len(PLOT_METRIC_SPECS):
            ix = 0
        title_combo, y_axis_label, extractor = PLOT_METRIC_SPECS[ix]
        use_welch = self._tab._spectrum_use_welch()
        x_labels: list[str] = []
        y_raw: list[float | None] = []
        for ent in entries:
            m = compute_recording_metrics(
                list(ent["ts_list"]),
                list(ent["f_list"]),
                list(ent["r_list"]),
                list(ent["p_list"]),
                use_welch=use_welch,
            )
            v = extractor(m)
            sw = str(ent["swimmer"]).strip()
            fn = str(ent["filename"])
            lab = sw if sw and sw not in ("—", "-") else fn
            x_labels.append(_short_label(lab, 22))
            y_raw.append(float(v) if v is not None else None)
        method = "Welch PSD" if use_welch else "FFT"
        return x_labels, y_raw, y_axis_label, title_combo, method

    def _redraw(self) -> None:
        x_labels, y_raw, y_axis_label, title_combo, method = self._gather_series()
        n = len(y_raw)
        self._pw.clear()

        self.setWindowTitle(f"Plot — {title_combo} ({method})")

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
                "Catatan: nilai yang tidak tersedia (mis. frekuensi dominan kosong) "
                "ditampilkan sebagai 0 pada diagram."
            )
        else:
            self._footnote_lbl.setText("")

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

        vb = self._pw.getViewBox()
        vb.setLimits(xMin=-0.6, xMax=max(float(n - 1) + 0.6, 0.6))
        self._pw.enableAutoRange()

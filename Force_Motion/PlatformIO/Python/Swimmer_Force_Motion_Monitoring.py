"""
Swimmer Force Motion Monitoring

Ringkasan:
- Dashboard PySide6 untuk monitoring gaya renang / beban (force) dan gerakan (roll, pitch) real-time.
- Membaca serial CSV UTF-8: 4 kolom per baris (newline-terminated).

Format data serial (ESP32 Generate_TimeSeries_3_Random_data):
1) TimeStamp(s)   — waktu relatif dari firmware (detik)
2) Force (Kg)     — kolom 2 serial (RandomData1)
3) Roll (Deg)     — kolom 3 serial (RandomData2)
4) Pitch (Deg)    — kolom 4 serial (RandomData3)

Catatan:
- Tab Live: tiga plot time-series (Force atas; Roll kiri & Pitch kanan di baris bawah).
- Rekaman CSV ke folder DataLog/ di samping file ini (tanpa dialog Save As).
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import pyqtgraph as pg
import serial
from serial.tools import list_ports
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


SCRIPT_DIR = Path(__file__).resolve().parent
DATALOG_DIR = SCRIPT_DIR / "DataLog"

STROKE_STYLES = [
    "Gaya Bebas",
    "Kupu-kupu",
    "Dada",
    "Punggung",
    "Ganti kategori (medley)",
    "Lainnya",
]


def _safe_filename_part(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s or "TanpaNama"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Swimmer Force Motion Monitoring")
        self.resize(1100, 720)

        self.ser: serial.Serial | None = None
        self.serial_timer = QTimer(self)
        self.serial_timer.timeout.connect(self.poll_serial)

        self.serial_buffer = b""

        self.log_file_path: Path | None = None
        self.log_file = None
        self.log_buffer: list[str] = []
        self.log_timer = QTimer(self)
        self.log_timer.setInterval(400)
        self.log_timer.timeout.connect(self.flush_log_buffer)
        self._log_header_time_str = ""

        self.max_points = 400

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        # ---------- Kiri: plots ----------
        plots_panel = QWidget(self)
        plots_layout = QVBoxLayout(plots_panel)
        plots_layout.setContentsMargins(0, 0, 0, 0)

        self.force_plot_widget = pg.PlotWidget()
        self.force_plot_widget.setLabel("left", "Force", color="#e5e7eb", **{"font-size": "12pt"})
        self.force_plot_widget.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "12pt"})
        self.force_plot_widget.setTitle("Force Data (Kg)", color="#e5e7eb", size="12pt")
        self.force_plot_widget.setBackground("#1f2937")
        self.force_plot_widget.showGrid(x=False, y=False)
        self.force_plot_widget.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
        self.force_plot_widget.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
        self.force_plot_widget.getAxis("left").setTextPen(pg.mkPen(color="#e5e7eb"))
        self.force_plot_widget.getAxis("bottom").setTextPen(pg.mkPen(color="#e5e7eb"))
        self.force_curve = self.force_plot_widget.plot(pen=pg.mkPen(color="#38bdf8", width=2))

        bottom_row = QWidget(self)
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.roll_plot_widget = pg.PlotWidget()
        self.roll_plot_widget.setLabel("left", "Angle (°)", color="#e5e7eb", **{"font-size": "11pt"})
        self.roll_plot_widget.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "11pt"})
        self.roll_plot_widget.setTitle("Roll Motion (Deg)", color="#e5e7eb", size="11pt")
        self.roll_plot_widget.setBackground("#1f2937")
        self.roll_plot_widget.showGrid(x=False, y=False)
        self.roll_plot_widget.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
        self.roll_plot_widget.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
        self.roll_curve = self.roll_plot_widget.plot(pen=pg.mkPen(color="#f59e0b", width=2))

        self.pitch_plot_widget = pg.PlotWidget()
        self.pitch_plot_widget.setLabel("left", "Angle (°)", color="#e5e7eb", **{"font-size": "11pt"})
        self.pitch_plot_widget.setLabel("bottom", "Time (s)", color="#e5e7eb", **{"font-size": "11pt"})
        self.pitch_plot_widget.setTitle("Pitch Motion (Deg)", color="#e5e7eb", size="11pt")
        self.pitch_plot_widget.setBackground("#1f2937")
        self.pitch_plot_widget.showGrid(x=False, y=False)
        self.pitch_plot_widget.getAxis("left").setPen(pg.mkPen(color="#e5e7eb", width=1))
        self.pitch_plot_widget.getAxis("bottom").setPen(pg.mkPen(color="#e5e7eb", width=1))
        self.pitch_curve = self.pitch_plot_widget.plot(pen=pg.mkPen(color="#a78bfa", width=2))

        bottom_layout.addWidget(self.roll_plot_widget, 1)
        bottom_layout.addWidget(self.pitch_plot_widget, 1)

        plots_layout.addWidget(self.force_plot_widget, 1)
        plots_layout.addWidget(bottom_row, 1)

        self.force_time_data: list[float] = []
        self.force_data: list[float] = []
        self.roll_time_data: list[float] = []
        self.roll_data: list[float] = []
        self.pitch_time_data: list[float] = []
        self.pitch_data: list[float] = []

        # ---------- Kanan: kontrol ----------
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        controls = QGroupBox("", self)
        controls.setLayout(QVBoxLayout())
        controls.layout().setContentsMargins(12, 12, 12, 12)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        port_label = QLabel("Port:")
        self.port_combo = QComboBox(self)
        self.refresh_ports()
        self.refresh_btn = QPushButton("Refresh Ports", self)
        self.refresh_btn.clicked.connect(self.refresh_ports)

        baud_label = QLabel("Baud:")
        self.baud_combo = QComboBox(self)
        self.baud_combo.addItems(["115200", "57600", "38400", "19200", "9600", "230400"])
        self.baud_combo.setCurrentText("115200")

        name_label = QLabel("Nama Perenang:")
        self.swimmer_name_edit = QLineEdit(self)
        self.swimmer_name_edit.setPlaceholderText("Nama pemain")

        stroke_label = QLabel("Gaya renang:")
        self.stroke_combo = QComboBox(self)
        self.stroke_combo.addItems(STROKE_STYLES)

        grid.addWidget(port_label, 0, 0)
        grid.addWidget(self.port_combo, 0, 1)
        grid.addWidget(self.refresh_btn, 0, 2)
        grid.addWidget(baud_label, 1, 0)
        grid.addWidget(self.baud_combo, 1, 1)
        grid.addWidget(name_label, 2, 0)
        grid.addWidget(self.swimmer_name_edit, 2, 1, 1, 2)
        grid.addWidget(stroke_label, 3, 0)
        grid.addWidget(self.stroke_combo, 3, 1, 1, 2)

        controls.layout().addLayout(grid)

        row_btn = QHBoxLayout()
        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.log_btn = QPushButton("Start Log", self)
        self.log_btn.setCheckable(True)
        self.log_btn.clicked.connect(self.toggle_logging)
        self.log_btn.setEnabled(False)
        row_btn.addWidget(self.connect_btn)
        row_btn.addWidget(self.log_btn)
        controls.layout().addLayout(row_btn)

        indicators = QGroupBox("Nilai terakhir", self)
        ind_outer = QVBoxLayout(indicators)
        self.force_label = QLabel("0.00 Kg")
        self.roll_label = QLabel("0.00°")
        self.pitch_label = QLabel("0.00°")
        for w in (self.force_label, self.roll_label, self.pitch_label):
            w.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt;")

        def _pair(title: str, value_label: QLabel) -> QWidget:
            box = QWidget(self)
            lay = QVBoxLayout(box)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(QLabel(title))
            lay.addWidget(value_label)
            return box

        ind_outer.addWidget(_pair("Force (Kg)", self.force_label))
        ind_outer.addWidget(_pair("Roll Motion (Deg)", self.roll_label))
        ind_outer.addWidget(_pair("Pitch Motion (Deg)", self.pitch_label))

        right_layout.addWidget(controls, 0)
        right_layout.addWidget(indicators, 1)

        root.addWidget(plots_panel, 4)
        root.addWidget(right_panel, 1)

        self._apply_styles(controls, indicators)

    def _apply_styles(self, controls: QGroupBox, indicators: QGroupBox) -> None:
        self.setStyleSheet(
            """
            QWidget { font-family: 'Segoe UI', Arial; font-size: 11pt; }
            QGroupBox { border: 1px solid #374151; border-radius: 10px; margin-top: 10px; background: #1f2937; }
            QGroupBox::title { color: #e5e7eb; }
            QLabel { color: #e5e7eb; }
            QComboBox { background: #374151; color: #e5e7eb; border: 1px solid #4b5563; padding: 6px; border-radius: 8px; }
            QComboBox:disabled { background: #2d3643; color: #9ca3af; }
            QLineEdit { background: #374151; color: #e5e7eb; border: 1px solid #4b5563; padding: 6px; border-radius: 8px; }
            QLineEdit:disabled { background: #2d3643; color: #9ca3af; }
            QPushButton { padding: 8px 12px; background-color: #3b82f6; color: #fff; border: none; border-radius: 8px; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:checked { background-color: #ef4444; }
            QPushButton:disabled { background-color: #6b7280; color: #d1d5db; }
            """
        )

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText() if self.port_combo.count() else ""
        self.port_combo.clear()
        items = [p.device for p in list_ports.comports()]
        self.port_combo.addItems(items)
        if current and current in items:
            self.port_combo.setCurrentText(current)
        elif len(items) == 1:
            self.port_combo.setCurrentIndex(0)

    def toggle_connection(self, checked: bool) -> None:
        if checked:
            if not self.connect_serial():
                self.connect_btn.setChecked(False)
        else:
            self.disconnect_serial()

    def connect_serial(self) -> bool:
        port = self.port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "Serial", "Pilih port COM terlebih dahulu.")
            return False
        try:
            baud = int(self.baud_combo.currentText())
        except ValueError:
            baud = 115200
        try:
            self.ser = serial.Serial(port, baudrate=baud, timeout=0.1)
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            self.serial_buffer = b""
            self.clear_all_plots()
            self.serial_timer.start(50)
            self.connect_btn.setText("Disconnect")
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.log_btn.setEnabled(True)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Serial", f"Gagal koneksi:\n{e}")
            self.ser = None
            return False

    def disconnect_serial(self) -> None:
        try:
            if self.serial_timer.isActive():
                self.serial_timer.stop()
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        finally:
            self.ser = None
            self.connect_btn.setText("Connect")
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            if self.log_btn.isChecked():
                self.log_btn.setChecked(False)
                self.stop_logging()
            self.log_btn.setEnabled(False)

    def clear_all_plots(self) -> None:
        for lst in (
            self.force_time_data,
            self.force_data,
            self.roll_time_data,
            self.roll_data,
            self.pitch_time_data,
            self.pitch_data,
        ):
            lst.clear()
        self.force_curve.setData([], [])
        self.roll_curve.setData([], [])
        self.pitch_curve.setData([], [])

    def poll_serial(self) -> None:
        if not self.ser:
            return
        try:
            n = self.ser.in_waiting
            chunk = self.ser.read(n or 1)
            if not chunk:
                return
            self.serial_buffer += chunk
            while b"\n" in self.serial_buffer:
                line, self.serial_buffer = self.serial_buffer.split(b"\n", 1)
                text = line.decode("utf-8", errors="replace").strip()
                if not text or text.startswith("#"):
                    continue
                parts = [p.strip() for p in text.split(",")]
                if len(parts) != 4:
                    continue
                try:
                    ts = float(parts[0])
                    force_kg = float(parts[1])
                    roll_deg = float(parts[2])
                    pitch_deg = float(parts[3])
                except ValueError:
                    continue
                self.update_live(ts, force_kg, roll_deg, pitch_deg)
                if self.log_file is not None:
                    self.log_buffer.append(
                        f"{ts:.2f},{force_kg:.2f},{roll_deg:.2f},{pitch_deg:.2f}\n"
                    )
        except Exception as e:
            print(f"[SERIAL] Read error: {e}")

    def update_live(
        self,
        ts: float,
        force_kg: float,
        roll_deg: float,
        pitch_deg: float,
    ) -> None:
        self.force_label.setText(f"{force_kg:.2f} Kg")
        self.roll_label.setText(f"{roll_deg:.2f}°")
        self.pitch_label.setText(f"{pitch_deg:.2f}°")

        self.force_time_data.append(ts)
        self.force_data.append(force_kg)
        self.roll_time_data.append(ts)
        self.roll_data.append(roll_deg)
        self.pitch_time_data.append(ts)
        self.pitch_data.append(pitch_deg)

        for series in (
            (self.force_time_data, self.force_data),
            (self.roll_time_data, self.roll_data),
            (self.pitch_time_data, self.pitch_data),
        ):
            tx, y = series
            while len(tx) > self.max_points:
                tx.pop(0)
                y.pop(0)

        self.force_curve.setData(self.force_time_data, self.force_data)
        self.roll_curve.setData(self.roll_time_data, self.roll_data)
        self.pitch_curve.setData(self.pitch_time_data, self.pitch_data)

    def toggle_logging(self, checked: bool) -> None:
        if checked:
            if not self.ser or not self.ser.is_open:
                self.log_btn.setChecked(False)
                return
            name = self.swimmer_name_edit.text().strip() or "TanpaNama"
            stroke = self.stroke_combo.currentText()
            try:
                DATALOG_DIR.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "DataLog", f"Tidak bisa membuat folder DataLog:\n{e}")
                self.log_btn.setChecked(False)
                return

            now = datetime.now()
            self._log_header_time_str = now.strftime("%d%m%y-%H%M")
            fn = (
                f"{_safe_filename_part(name)}_{_safe_filename_part(stroke)}_"
                f"{self._log_header_time_str}.csv"
            )
            path = DATALOG_DIR / fn
            try:
                self.log_file_path = path
                self.log_file = open(path, "w", buffering=1, encoding="utf-8")
                self.log_file.write(f"Nama Perenang:,{name}\n")
                self.log_file.write(f"Gaya Renang:,{stroke}\n")
                self.log_file.write(f"Time:,{self._log_header_time_str}\n")
                self.log_file.write("TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)\n")
                self.log_buffer.clear()
                self.log_timer.start()
                self.log_btn.setText("Stop Log")
                self.swimmer_name_edit.setEnabled(False)
                self.stroke_combo.setEnabled(False)
                self.connect_btn.setEnabled(False)
            except Exception as e:
                QMessageBox.critical(self, "Log", f"Gagal membuka file:\n{e}")
                self.log_file = None
                self.log_file_path = None
                self.log_btn.setChecked(False)
        else:
            self.stop_logging()

    def stop_logging(self) -> None:
        try:
            self.log_timer.stop()
            self.flush_log_buffer()
            if self.log_file:
                self.log_file.close()
        except Exception:
            pass
        finally:
            self.log_file = None
            self.log_file_path = None
            if self.log_btn:
                self.log_btn.setText("Start Log")
            self.swimmer_name_edit.setEnabled(True)
            self.stroke_combo.setEnabled(True)
            if self.connect_btn:
                self.connect_btn.setEnabled(True)

    def flush_log_buffer(self) -> None:
        if not self.log_file or not self.log_buffer:
            return
        try:
            self.log_file.writelines(self.log_buffer)
            self.log_buffer.clear()
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self.disconnect_serial()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())

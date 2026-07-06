"""
Swimmer Force Motion Monitoring — aplikasi desktop (PySide6 + pyqtgraph).

Versi modul ini: **2.3.0** (nama berkas ``Swimmer_Force_Motion_Monitoring_v2.3.0.py``).

Changelog (2.2.0 → 2.3.0)
==========================
- **Tab Live — kamera** — preview live di samping tiga plot; pindai & pilih perangkat
  lewat menu **Setting → Live → Camera**; rekam ``.mp4`` ke ``DataLog/`` dengan
  basename sama seperti CSV saat **Start Log**; berhenti saat **Stop Log**.
  Modul ``live_camera_core.py``, ``live_camera_panel.py``.
- **Tab Analisa** — tiga plot FFT diganti **playback video** pasangan CSV (auto-load
  ``.mp4``); frekuensi dominan tetap di statistik. Modul ``analyze_video_panel.py``.
- **Sinkron video ↔ plot** — metadata di CSV (``VideoFile``, ``LogWallStartEpoch``,
  footer ``SyncCsvT0`` / ``SyncLogWallStart`` / ``SyncFirstSampleWall``); playhead
  memakai titik acuan rekaman (fallback ke sinkron kasar untuk CSV lama).
- **Tab Analisa — koreksi & region** — region biru (data uji) / hijau (zero offset);
  checkbox Zero Offset; koreksi sudut tali (default 7°); batas bawah Force mentah
  (−1 Kg).
- **Tab Analisa — statistik gaya tethered** — Metode A global (peakF, meanF, minF,
  ImpF, FI) dan Metode B per siklus Andrade (TpeakF, DUR, RFD, dF); modul
  ``analyze_tethered_force_metrics.py``.
- **Tab Analisa — tooltip** — baris tabel statistik dan tombol video; modul
  ``ui_tooltip.py``.
- **Ekspor ``DataStatistik/``** — blok zero offset dan gap selalu lengkap; snapshot
  disegarkan sebelum simpan; cap waktu ``_DataStatistik_<ddmmyy-HHMMSS>.csv``.
- **Tab Analisa multifile** — muat hingga lima berkas ``DataStatistik/`` (parser
  ``parse_datastatistik_csv.py``); tabel berkelompok; **Plot data** aktif
  (peakF/meanF/minF/ImpF, roll/pitch, frekuensi dominan; sumbu X = nomor kolom;
  tooltip hover); tanpa ekspor ``TableMultiFile/``.

Changelog (2.1.0 → 2.2.0)
==========================
- **Tab Live — baterai** — terima kolom kelima ``Baterai(%)`` dari serial (mis. LoRa
  Receiver, 115200 baud); tampilkan di grup **Nilai terakhir**; **tidak** ditulis ke
  CSV rekaman (``DataLog/`` tetap empat kolom data).
- **Tab Live — serial** — parser menerima baris **empat atau lima** kolom; sumber
  empat kolom (uji/generator) tetap didukung.
- **Tab Analisa — gap rekaman CSV** — estimasi sampel hilang dari kolom ``TimeStamp(s)``
  (bukan diagnosis LoRa, hanya indikator kualitas rekaman). Radio di **Analisa Setting**:
  **Metode A** (per gap: jumlahkan ``round(Δt/Δt_nom)−1`` jika Δt > 1,5× median Δt)
  dan **Metode B** (global: ``n_diharapkan − n_tercatat``). Kartu **GAP REKAMAN CSV**
  di panel statistik; blok yang sama diekspor ke ``DataStatistik/``.
- **Modul** — ``analyze_metrics_core.py`` ditambah ``compute_gap_loss``, ``GapLossStats``,
  ``median_dt_s``; ``estimate_sample_rate_hz`` memakai median Δt bersama.

Changelog (2.0.0 → 2.1.0)
==========================
- **Tab Analisa multifile** — hingga **lima** berkas CSV dalam **tabel** (header
  multi-baris: nama perenang, gaya, nama file, *Value*); isi angka **rata tengah**
  pada sel data.
- **Kontrol baris pertama** — **Plot data** (hijau); blok **Hapus kolom** + combo +
  **Clear tabel** (merah); tambah berkas lewat menu **File → Analisa MultiFile → Add File**.
- **Jendela plot** (``MultiFilePlotDialog``, non-modal) — pilihan **Metrik** dan
  **Gaya plot** di dalam jendela: diagram batang, **garis + penanda** (default),
  atau titik saja (pyqtgraph).
- **Modul** — ``analyze_metrics_core.py`` (``compute_recording_metrics`` + spektrum);
  ``analyze_multi_file_tab.py`` (tabel + dialog plot).
- **Ekspor** — folder ``TableMultiFile/``, berkas ``…_TableMultiFile.csv`` mengikuti
  baris tabel (header multi-baris).

Changelog (v1.0.0 → v2.0.0)
==============================
- **Modularisasi kode:** logika CSV rekaman dipindah ke ``live_csv_io.py`` (konstanta
  ``LIVE_CSV_DATA_HEADER`` + ``parse_logged_csv``); tab **Analisa** dipindah ke
  ``analyze_single_file_tab.py`` (kelas ``AnalyzeSingleFileTab`` + bantu plot).
- **Tab Analisa:** selain plot waktu penuh + marker ekstremum, ditambah **tiga plot
  spektrum** (Force / Roll / Pitch), pemilihan metode **FFT** atau **Welch PSD**
  (``numpy`` / ``scipy``), marker puncak spektrum, dan **frekuensi dominan** pada
  kartu statistik (selaras dengan metode yang dipilih).
- **Ekspor ``DataStatistik/``:** CSV mencakup baris ``Timestampstart (s)`` (waktu
  awal deret) serta blok tambahan **Frekuensi Dominan (Hz)** per saluran dengan
  kolom **Metode** (FFT / Welch PSD).
- **Antarmuka:** dialog *themed* untuk pesan simpan statistik / About; referensi
  manual pengguna memakai berkas **v2.0.0** (lihat konstanta ``USER_MANUAL_*`` di
  folder ``Swimmer_Force_Motion_Monitoring_v2.0.0/``).

Ringkasan fungsi
==================
Aplikasi memantau **beban (force, kg)** dan **orientasi gerak (roll & pitch, derajat)**
secara *real-time* dari perangkat keras yang mengirim data lewat **port serial USB**
dalam format **teks CSV**: satu baris per sampel, empat kolom numerik dipisahkan koma.

Satu tab **Live** dan dua tab **Analisa** (satu berkas + multifile):

1. **Live** — koneksi serial, plot tiga deret waktu, indikator nilai terakhir (force,
   roll, pitch, **baterai %** jika dikirim perangkat), panel **kamera** (preview;
   atur perangkat lewat **Setting → Live → Camera**), rekam ``.mp4`` ke ``DataLog/``
   saat **Start Log**), rekaman ke berkas CSV
   di folder ``DataLog/`` (empat kolom data saja), opsi menggeser kolom waktu di CSV
   ke nol per sesi **Start Log**.
2. **Analisa** — muat satu CSV hasil tab Live, plot waktu dengan marker ekstremum,
   **playback video** pasangan (playhead pink; sinkron dari metadata CSV atau fallback
   kasar), region data uji (biru) dan zero offset (hijau), koreksi sudut tali /
   batas bawah Force mentah, statistik gaya tethered **Metode A/B** (peakF, meanF,
   ImpF, TpeakF, DUR, RFD, dF, FI), frekuensi dominan FFT/Welch **tanpa plot spektrum
   visual**, **gap rekaman CSV** Metode A/B, tooltip per baris statistik, ekspor ke
   ``DataStatistik/``.
3. **Analisa multifile** — hingga lima berkas ekspor ``DataStatistik/``; tabel
   perbandingan berkelompok; **plot perbandingan** di jendela terpisah (11 metrik,
   sumbu X nomor kolom, tooltip hover); **Clear tabel** per kolom atau semua.

Arsitektur ringkas
===================
- **GUI**: ``QMainWindow`` + ``QTabWidget``; plot memakai **pyqtgraph** (performa baik
  untuk deret waktu).
- **Serial**: ``serial.Serial`` + ``QTimer`` periodik (``poll_serial``) membaca buffer
  byte, memecah per ``\\n``, mendekode UTF-8, mem-parse empat kolom float wajib
  (kolom kelima baterai opsional, hanya tampilan Live).
- **Live plot**: tiga ``PlotDataItem``; tiap kanal menyimpan maksimal ``max_points``
  titik (default 100) — jendela geser ~10 s jika laju ~10 sampel/detik.
- **Logging**: ``toggle_logging`` membuka berkas teks UTF-8; baris data di-buffer
  dan di-flush periodik lewat ``QTimer`` terpisah agar I/O disk tidak memblokir
  pembacaan serial setiap tick. Jika kamera aktif, ``.mp4`` direkam paralel; metadata
  sinkron ditulis ke header/footer CSV (lihat format berkas di bawah).
- **Kamera**: ``live_camera_panel`` + ``live_camera_core`` — probe OpenCV (MSMF/DSHOW),
  preview di thread terpisah, rekam MP4 saat logging.

Format baris serial (wajib)
============================
Satu baris (tanpa komentar ``#`` di depan), **empat atau lima** nilai dipisahkan koma.
Contoh empat kolom (CSV rekaman)::

    12.34, 5.6, -1.2, 3.4

Contoh lima kolom (LoRa Receiver — kolom kelima hanya tampilan Live, tidak di-log)::

    12.34, 5.6, -1.2, 3.4, 87

Urutan kolom (empat pertama sama dengan header CSV rekaman):

1. **TimeStamp(s)** — skala detik; biasanya dari *timer* firmware (bukan jam PC).
2. **Force(Kg)** — beban / gaya (satuan sesuai kalibrasi perangkat).
3. **Roll(Deg)** — sudut roll.
4. **Pitch(Deg)** — sudut pitch.
5. **Baterai(%)** — opsional; persentase baterai transmitter (tab Live saja).

Firmware referensi: PlatformIO ``Lora_Receiver_Ori`` (ESP32, 115200 baud) mengirim
lima kolom; ``Generate_TimeSeries_3_Random_data`` mengirim empat kolom untuk uji.

Format berkas CSV rekaman (tab Live)
=====================================
Disimpan di ``DataLog/`` (folder sejajar skrip Python). Nama berkas memuat nama
perenang aman, gaya renang, dan cap waktu ``ddmmyy-HHMM``.

Struktur:

- Beberapa baris **metadata** (``Nama Perenang:``, ``Gaya Renang:``, ``Time:``).
- Opsional jika kamera aktif saat **Start Log**: ``VideoFile:``, ``LogWallStartEpoch(s):``.
- Satu baris **header data** persis:
  ``TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)``
- Baris data numerik empat kolom.
- Opsional di footer saat **Stop Log** (sinkron video ↔ plot):
  ``SyncCsvT0(s):``, ``SyncLogWallStart(s):``, ``SyncFirstSampleWall(s):``.

Berkas video ``.mp4`` (basename sama dengan CSV) di ``DataLog/`` jika kamera aktif
saat Start Log.

Opsi **TimeStamp CSV mulai 0 saat Start Log**: jika dicentang, kolom waktu yang
ditulis ke CSV adalah ``waktu_serial - waktu_sampel_pertama_sesi_log`` sehingga
baris pertama data ≈ ``0`` detik. **Connect** tidak mengatur ulang referensi ini;
hanya **Start Log** yang memulai sesi baru. Plot Live tetap memakai waktu mentah
dari serial.

Analisa & statistik (satu berkas)
==================================
Tab **Analisa** diimplementasikan sebagai ``AnalyzeSingleFileTab`` di berkas
``analyze_single_file_tab.py``: satu CSV rekaman, plot waktu, playback video
(``analyze_video_panel.py``), ekstremum, ekspor. Parsing format CSV Live ada di
``live_csv_io.parse_logged_csv`` (mengembalikan ``LogSyncMeta`` untuk sinkron
opsional). **Analisa multifile** di ``analyze_multi_file_tab.py``.

**Sinkron playhead video ↔ plot:**

- Rekaman baru: ``csv_t = SyncCsvT0 + max(0, video_sec − (SyncFirstSampleWall − SyncLogWallStart))``
  (metadata footer CSV).
- CSV lama tanpa metadata: ``csv_t ≈ TimeStamp baris pertama + video_sec`` (sinkron kasar).

Tombol **Simpan statistik** (menu **File → Analisa SingleFile → Simpan Statistik**) menulis CSV ke ``DataStatistik/`` dengan nama
``<nama_file_log>_DataStatistik_<ddmmyy-HHMMSS>.csv`` (cap waktu ekspor lokal;
tanpa dialog Save As), berisi metadata (termasuk zero offset, koreksi, segmen),
tabel metrik (termasuk **Metode_statistik_Force**, peakF, meanF, ImpF, TpeakF,
DUR, RFD, dF, FI sesuai metode aktif), blok frekuensi dominan per saluran, lalu
blok **Gap rekaman CSV** lengkap (semua baris; nilai kosong jika tidak berlaku).
Snapshot statistik disegarkan dari UI sebelum menulis.

**Analisa multifile** (``analyze_multi_file_tab.py``) memuat berkas
``DataStatistik/`` via ``parse_datastatistik_csv.py`` — bukan rekaman ``DataLog/``.
Tabel membandingkan metrik yang sudah diekspor; plot memakai nilai tersebut
langsung.

Statistik gaya tethered (tab Analisa)
========================================
Modul ``analyze_tethered_force_metrics.py``; UI di ``analyze_single_file_tab.py``.

- **Metode A (global):** peakF, meanF, minF, ImpF (∫F·dt trapesium), FI (≥ 15 s);
  TpeakF, DUR, RFD, dF = tidak berlaku.
- **Metode B (Andrade):** filter Butterworth orde 4 (cutoff default 7 Hz), deteksi
  valley → siklus → rata-rata peakF, meanF, minF, ImpF, TpeakF, DUR, RFD, dF;
  FI global pada region uji.
- Perhitungan pada **region data uji** (biru) setelah koreksi aktif (zero offset,
  sudut tali, batas bawah Force mentah).

Gap rekaman CSV (tab Analisa)
==============================
Fungsi ``compute_gap_loss`` di ``analyze_metrics_core.py``; UI di
``analyze_single_file_tab.py`` (radio **Metode A — per gap** / **Metode B — global**).

- ``Δt_nominal`` = median selisih ``TimeStamp(s)`` antar baris berurutan (sama dasar
  dengan estimasi laju sampel untuk spektrum).
- **Metode A:** untuk setiap pasangan baris, jika ``Δt > 1,5 × Δt_nominal``, tambahkan
  ``max(0, round(Δt/Δt_nominal) − 1)`` ke total sampel hilang; tampilkan **jumlah gap**.
- **Metode B:** ``n_diharapkan = round((ts_akhir − ts_awal) / Δt_nominal) + 1``;
  ``n_hilang = max(0, n_diharapkan − len(ts))``; tampilkan **sampel diharapkan**.

Tujuan: mengetahui kualitas rekaman CSV (lubang timestamp), bukan diagnosis LoRa.

Dependensi Python
==================
- ``PySide6`` — antarmuka Qt6.
- ``pyqtgraph`` — plot deret waktu.
- ``pyserial`` — komunikasi serial.
- ``numpy``, ``scipy`` — perhitungan frekuensi dominan (FFT / Welch) di statistik.
- ``opencv-python`` — capture/preview/rekam kamera dan playback video.
- ``pygrabber`` — nama perangkat kamera di Windows (opsional, fallback jika tidak ada).

Berkas terkait di folder yang sama
===================================
- ``live_csv_io.py`` — header + parser CSV rekaman Live + ``LogSyncMeta``.
- ``analyze_single_file_tab.py`` — widget tab Analisa (satu berkas).
- ``analyze_metrics_core.py`` — metrik rekaman, spektrum, **gap rekaman CSV**
  (``compute_gap_loss``; tab Analisa).
- ``parse_datastatistik_csv.py`` — parser ekspor ``DataStatistik/`` (tab multifile).
- ``analyze_multi_file_tab.py`` — widget tab Analisa multifile (tabel + plot).
- ``live_camera_core.py`` — pemindaian kamera (probe MSMF/DSHOW).
- ``live_camera_panel.py`` — preview kamera tab Live + dialog Setting → Live → Camera.
- ``analyze_video_panel.py`` — playback video rekaman di tab Analisa.
- ``analyze_tethered_force_metrics.py`` — metrik gaya tethered (Metode A/B).
- ``ui_tooltip.py`` — tema dan teks tooltip aplikasi.
- ``UserManual_Force_Motion_v2.3.0.md`` — manual pengguna (Markdown).
- ``UserManual_Force_Motion_v2.3.0.pdf`` — manual pengguna (PDF; dihasilkan dari MD).
- ``md_to_pdf_Force_Motion.py`` — skrip bantu konversi MD → PDF (``markdown`` +
  ``xhtml2pdf``), berada di folder induk ``Force_Motion/Python`` (bukan di folder
  skrip v2 ini); pola sama seperti proyek Touchpad_Timer_Pressure.

Lihat juga
==========
Menu **Help** membuka PDF manual jika berkas ada; **Tentang**
menampilkan ringkasan versi dan tujuan aplikasi.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pyqtgraph as pg
import serial
from serial.tools import list_ports
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from analyze_multi_file_tab import AnalyzeMultiFileTab
from ui_tooltip import APP_QTOOLTIP_STYLESHEET, apply_app_tooltip_theme
from analyze_single_file_tab import (
    AnalyzeSingleFileTab,
    make_three_stack_plots,
    wrap_in_scroll_area,
)
from live_camera_panel import LiveCameraPanel
from live_serial_settings_dialog import LiveSerialSettingsDialog
from live_csv_io import LIVE_CSV_DATA_HEADER


SCRIPT_DIR = Path(__file__).resolve().parent
DATALOG_DIR = SCRIPT_DIR / "DataLog"
DATASTATISTIK_DIR = SCRIPT_DIR / "DataStatistik"
# Sufiks nama file ekspor statistik: <nama_file_log>_DataStatistik_<ddmmyy-HHMMSS>.csv
STATISTIK_FILE_SUFFIX = "_DataStatistik"

APP_NAME = "Swimmer Force Motion Monitoring"
APP_VERSION = "2.3.0"
USER_MANUAL_MD = SCRIPT_DIR / "UserManual_Force_Motion_v2.3.0.md"
USER_MANUAL_PDF = SCRIPT_DIR / "UserManual_Force_Motion_v2.3.0.pdf"
CHANGELOG_MD = SCRIPT_DIR.parent / "Changelog.md"

STROKE_STYLES = [
    "Gaya Bebas",
    "Kupu-kupu",
    "Dada",
    "Punggung",
    "Ganti kategori (medley)",
    "Lainnya",
]

TAB_LIVE = 0
TAB_ANALYZE = 1
TAB_MULTI_FILE = 2

# Dialog Simpan statistik / About-Help: QDialog vertikal (ikon atas, teks bawah).
THEMED_STATISTIK_DIALOG_STYLESHEET = """
QDialog { background-color: #1f2937; }
QDialog QLabel#StatDialogMessage {
    color: #e5e7eb;
    font-size: 11pt;
    min-width: 360px;
    max-width: 520px;
}
QDialog QPushButton {
    padding: 8px 18px;
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    min-width: 72px;
    font-size: 11pt;
}
QDialog QPushButton:hover { background-color: #2563eb; }
QDialog QPushButton:pressed { background-color: #1d4ed8; }
QDialog QPushButton:focus { outline: none; }
"""


def _path_text_for_dialog(path: Path | str) -> str:
    """
    Teks path untuk dialog: hindari wrap aneh setelah huruf drive.

    Di Windows, layout teks sering memutus baris di ``:`` (``D:`` dianggap satu
    segmen), sehingga path tampil sebagai ``D:`` lalu ``\\Pengujian\\...`` di
    baris berikutnya. Menyisipkan U+2060 WORD JOINER setelah ``:`` drive
    menggabungkan ``D:`` dengan sisa path.
    """
    s = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    if len(s) >= 3 and s[0].isalpha() and s[1] == ":" and s[2] == "/":
        s = s[:2] + "\u2060" + s[2:]
    return s


def _safe_filename_part(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s or "TanpaNama"


_LIVE_METRIC_GAP_Y = 8  # px jeda vertikal sebelum & sesudah tiap parameter


def _live_metric_block(title: str, parent: QWidget) -> tuple[QLabel, QWidget]:
    """Judul statis di atas, nilai dinamis di bawah (satu kolom vertikal)."""
    block = QWidget(parent)
    block.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    lay = QVBoxLayout(block)
    lay.setContentsMargins(0, _LIVE_METRIC_GAP_Y, 0, _LIVE_METRIC_GAP_Y)
    lay.setSpacing(2)
    title_lbl = QLabel(title, block)
    title_lbl.setStyleSheet("color: #9ca3af; font-size: 15pt; font-weight: 600;")
    title_lbl.setFixedHeight(24)
    value_lbl = QLabel("—", block)
    value_lbl.setStyleSheet(
        "color: #f9fafb; font-size: 36pt; font-weight: 700;"
        " font-family: Consolas, 'Courier New', monospace;"
    )
    value_lbl.setFixedHeight(50)
    lay.addWidget(title_lbl)
    lay.addWidget(value_lbl)
    return value_lbl, block


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        app = QApplication.instance()
        if app is not None:
            apply_app_tooltip_theme(app)
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1280, 700)

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
        self._log_timestamp_t0: float | None = None
        self._log_wall_start_epoch: float | None = None
        self._sync_first_csv_ts: float | None = None
        self._sync_first_sample_wall: float | None = None

        # ~10 detik jendela tampilan pada laju ~10 baris/detik (mis. ESP timerInterval 100 ms)
        self.max_points = 100

        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        live_tab = QWidget(self)
        live_layout = QHBoxLayout(live_tab)
        live_layout.setContentsMargins(8, 8, 8, 8)

        # ---------- Kiri: plots Live ----------
        plots_panel = QWidget(self)
        plots_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        plots_layout = QVBoxLayout(plots_panel)
        plots_layout.setContentsMargins(0, 0, 0, 0)

        (
            self.force_plot_widget,
            self.roll_plot_widget,
            self.pitch_plot_widget,
            self.force_curve,
            self.roll_curve,
            self.pitch_curve,
        ) = make_three_stack_plots()

        plots_layout.addWidget(self.force_plot_widget, 1)
        plots_layout.addWidget(self.roll_plot_widget, 1)
        plots_layout.addWidget(self.pitch_plot_widget, 1)

        self.force_time_data: list[float] = []
        self.force_data: list[float] = []
        self.roll_time_data: list[float] = []
        self.roll_data: list[float] = []
        self.pitch_time_data: list[float] = []
        self.pitch_data: list[float] = []

        # ---------- Kanan: atas (indikator + kontrol) + bawah (kamera) ----------
        right_panel = QWidget(self)
        right_panel.setMinimumWidth(420)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        right_top = QWidget(self)
        right_top_layout = QHBoxLayout(right_top)
        right_top_layout.setContentsMargins(0, 0, 0, 0)
        right_top_layout.setSpacing(8)

        indicators = QGroupBox("Nilai terakhir", self)
        indicators.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        ind_outer = QVBoxLayout(indicators)
        ind_outer.setContentsMargins(10, 10, 10, 10)
        ind_outer.setSpacing(4)

        metrics_grid = QGridLayout()
        metrics_grid.setContentsMargins(0, 0, 0, 0)
        metrics_grid.setHorizontalSpacing(12)
        metrics_grid.setVerticalSpacing(4)

        self.force_label, force_block = _live_metric_block("Force (Kg)", indicators)
        self.roll_label, roll_block = _live_metric_block("Roll (°)", indicators)
        self.pitch_label, pitch_block = _live_metric_block("Pitch (°)", indicators)
        self.battery_label, battery_block = _live_metric_block("Baterai (%)", indicators)
        metrics_grid.addWidget(force_block, 0, 0)
        metrics_grid.addWidget(roll_block, 0, 1)
        metrics_grid.addWidget(pitch_block, 1, 0)
        metrics_grid.addWidget(battery_block, 1, 1)
        metrics_grid.setColumnStretch(0, 1)
        metrics_grid.setColumnStretch(1, 1)
        ind_outer.addLayout(metrics_grid)

        controls = QGroupBox("Kontrol sesi", self)
        controls.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        controls.setLayout(QVBoxLayout())
        controls.layout().setContentsMargins(12, 12, 12, 12)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self._init_serial_port_widgets()
        self._serial_settings_dialog: LiveSerialSettingsDialog | None = None

        name_label = QLabel("Nama Perenang:")
        self.swimmer_name_edit = QLineEdit(self)
        self.swimmer_name_edit.setPlaceholderText("Nama Perenang")

        stroke_label = QLabel("Gaya renang:")
        self.stroke_combo = QComboBox(self)
        self.stroke_combo.addItems(STROKE_STYLES)

        grid.addWidget(name_label, 0, 0)
        grid.addWidget(self.swimmer_name_edit, 0, 1)
        grid.addWidget(stroke_label, 1, 0)
        grid.addWidget(self.stroke_combo, 1, 1)

        controls.layout().addLayout(grid)

        file_name_caption = QLabel("Nama file:", self)
        file_name_caption.setStyleSheet("color: #9ca3af; font-size: 10pt; font-weight: 600;")
        self.log_filename_label = QLabel("—", self)
        self.log_filename_label.setWordWrap(True)
        self.log_filename_label.setStyleSheet(
            "color: #d1d5db; font-size: 10pt; font-family: Consolas, 'Courier New', monospace;"
        )
        controls.layout().addWidget(file_name_caption)
        controls.layout().addWidget(self.log_filename_label)

        # Preferensi dormant: TimeStamp CSV mulai 0 saat Start Log (tidak ditampilkan di UI).
        self.log_ts_zero_checkbox = QCheckBox(self)
        self.log_ts_zero_checkbox.setChecked(False)
        self.log_ts_zero_checkbox.setToolTip(
            "Jika dicentang, kolom TimeStamp(s) di file CSV = waktu serial dikurangi "
            "timestamp sampel pertama setelah Anda menekan Start Log (bukan saat Connect). "
            "Baris pertama data ≈ 0 s; plot Live tetap memakai waktu dari perangkat."
        )
        self.log_ts_zero_checkbox.hide()

        row_btn = QHBoxLayout()
        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.setObjectName("LivePrimaryButton")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.log_btn = QPushButton("Start Log", self)
        self.log_btn.setCheckable(True)
        self.log_btn.clicked.connect(self.toggle_logging)
        self.log_btn.setEnabled(False)
        row_btn.addWidget(self.connect_btn)
        row_btn.addWidget(self.log_btn)
        controls.layout().addLayout(row_btn)

        right_top_layout.addWidget(indicators, 3)
        right_top_layout.addWidget(controls, 2)

        self.camera_panel = LiveCameraPanel(self)
        self.camera_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        camera_group = QGroupBox("Kamera", self)
        camera_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        camera_group_layout = QVBoxLayout(camera_group)
        camera_group_layout.setContentsMargins(8, 8, 8, 8)
        camera_group_layout.addWidget(self.camera_panel)

        # Atas ~38% / bawah ~62% — preview kamera butuh ruang vertikal lebih besar.
        right_layout.addWidget(right_top, 2)
        right_layout.addWidget(camera_group, 3)

        plots_scroll = wrap_in_scroll_area(plots_panel, self)
        plots_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        live_layout.addWidget(plots_scroll, 3)
        live_layout.addWidget(right_panel, 2)

        # ---------- Tab Analisa (satu berkas) + tab Analisa multifile ----------
        self.analyze_single_file_tab = AnalyzeSingleFileTab(
            datalog_dir=DATALOG_DIR,
            datastatistik_dir=DATASTATISTIK_DIR,
            statistik_file_suffix=STATISTIK_FILE_SUFFIX,
            themed_stat_message=self._show_statistik_message_box,
            on_save_stats_enabled_changed=self._on_analyze_save_stats_enabled_changed,
            parent=self,
        )

        self.analyze_multi_file_tab = AnalyzeMultiFileTab(
            datastatistik_dir=DATASTATISTIK_DIR,
            themed_stat_message=self._show_statistik_message_box,
            parent=self,
        )

        self.tab_widget.addTab(live_tab, "Live")
        self.tab_widget.addTab(self.analyze_single_file_tab, "Analisa")
        self.tab_widget.addTab(self.analyze_multi_file_tab, "Analisa Multifile")

        self._setup_menu_bar()
        self._apply_styles(controls, indicators)

    def _setup_menu_bar(self) -> None:
        self._setup_file_menu()
        self._setup_view_menu()
        self._setup_settings_menu()
        self._setup_help_menu()

    def _setup_file_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        analyze_menu = file_menu.addMenu("Analisa SingleFile")

        load_csv_action = QAction("Load csv", self)
        load_csv_action.setStatusTip("Muat berkas CSV rekaman tab Live")
        load_csv_action.triggered.connect(self._file_menu_load_csv)
        analyze_menu.addAction(load_csv_action)

        load_video_action = QAction("Load Video", self)
        load_video_action.setStatusTip("Muat berkas video pasangan untuk sinkronisasi")
        load_video_action.triggered.connect(self._file_menu_load_video)
        analyze_menu.addAction(load_video_action)

        self._file_save_stats_action = QAction("Simpan Statistik", self)
        self._file_save_stats_action.setEnabled(False)
        self._file_save_stats_action.setStatusTip(
            "Simpan ringkasan statistik ke folder DataStatistik/"
        )
        self._file_save_stats_action.triggered.connect(self._file_menu_save_statistics)
        analyze_menu.addAction(self._file_save_stats_action)

        multifile_menu = file_menu.addMenu("Analisa MultiFile")

        add_file_action = QAction("Add File", self)
        add_file_action.setStatusTip("Tambah berkas DataStatistik ke tabel perbandingan")
        add_file_action.triggered.connect(self._file_menu_add_multifile)
        multifile_menu.addAction(add_file_action)

    def _file_menu_load_csv(self) -> None:
        self._show_view_tab(TAB_ANALYZE)
        self.analyze_single_file_tab.load_csv()

    def _file_menu_load_video(self) -> None:
        self._show_view_tab(TAB_ANALYZE)
        self.analyze_single_file_tab.load_video()

    def _file_menu_save_statistics(self) -> None:
        self._show_view_tab(TAB_ANALYZE)
        self.analyze_single_file_tab.save_statistics_csv()

    def _file_menu_add_multifile(self) -> None:
        self._show_view_tab(TAB_MULTI_FILE)
        self.analyze_multi_file_tab._on_add_file()

    def _on_analyze_save_stats_enabled_changed(self, enabled: bool) -> None:
        if hasattr(self, "_file_save_stats_action"):
            self._file_save_stats_action.setEnabled(enabled)

    def _setup_settings_menu(self) -> None:
        settings_menu = self.menuBar().addMenu("&Setting")

        analyze_menu = settings_menu.addMenu("Analisa SingleFile")

        stats_setting_action = QAction("Statistik Setting", self)
        stats_setting_action.setStatusTip(
            "Buka pengaturan analisa: koreksi, region, metode spektrum, statistik Force, gap CSV"
        )
        stats_setting_action.triggered.connect(self._settings_menu_analyze_stats)
        analyze_menu.addAction(stats_setting_action)

        live_menu = settings_menu.addMenu("Live")

        camera_action = QAction("Camera", self)
        camera_action.setStatusTip("Pindai dan pilih kamera aktif untuk preview tab Live")
        camera_action.triggered.connect(self._settings_menu_live_camera)
        live_menu.addAction(camera_action)

        serial_action = QAction("Serial Port", self)
        serial_action.setStatusTip("Atur port COM dan baud rate koneksi serial")
        serial_action.triggered.connect(self._settings_menu_live_serial)
        live_menu.addAction(serial_action)

    def _settings_menu_analyze_stats(self) -> None:
        self._show_view_tab(TAB_ANALYZE)
        self.analyze_single_file_tab.show_analyze_settings()

    def _settings_menu_live_camera(self) -> None:
        self._show_view_tab(TAB_LIVE)
        self.camera_panel.show_settings_dialog()

    def _settings_menu_live_serial(self) -> None:
        self._show_view_tab(TAB_LIVE)
        self.show_serial_settings_dialog()

    def _setup_view_menu(self) -> None:
        view_menu = self.menuBar().addMenu("&View")
        self._view_action_group = QActionGroup(self)
        self._view_action_group.setExclusive(True)
        self._view_actions: list[QAction] = []

        for label, index, shortcut in (
            ("Live", TAB_LIVE, "Ctrl+1"),
            ("Analisa SingleFile", TAB_ANALYZE, "Ctrl+2"),
            ("Analisa MultiFile", TAB_MULTI_FILE, "Ctrl+3"),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.setShortcut(shortcut)
            action.setStatusTip(f"Tampilkan tampilan {label}")
            action.triggered.connect(
                lambda _checked=False, tab_index=index: self._show_view_tab(tab_index)
            )
            self._view_action_group.addAction(action)
            view_menu.addAction(action)
            self._view_actions.append(action)

        self.tab_widget.tabBar().hide()
        self.tab_widget.currentChanged.connect(self._on_view_tab_changed)
        self._view_actions[TAB_LIVE].setChecked(True)

    def _show_view_tab(self, index: int) -> None:
        if self.tab_widget.currentIndex() != index:
            self.tab_widget.setCurrentIndex(index)

    def _on_view_tab_changed(self, index: int) -> None:
        if 0 <= index < len(self._view_actions):
            self._view_actions[index].setChecked(True)

    def _setup_help_menu(self) -> None:
        help_menu = self.menuBar().addMenu("&Help")

        manual_action = QAction("Manual", self)
        manual_action.setShortcut("F1")
        manual_action.setStatusTip(f"Buka manual PDF ({USER_MANUAL_PDF.name})")
        manual_action.triggered.connect(self.open_user_manual_pdf)
        help_menu.addAction(manual_action)

        about_action = QAction("Tentang", self)
        about_action.setStatusTip("Informasi aplikasi dan versi")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        changelog_action = QAction("Changelog", self)
        changelog_action.setStatusTip("Riwayat perubahan versi aplikasi")
        changelog_action.triggered.connect(self.show_changelog_dialog)
        help_menu.addAction(changelog_action)

    def _apply_styles(self, controls: QGroupBox, indicators: QGroupBox) -> None:
        self.setStyleSheet(
            """
            QWidget { font-family: 'Segoe UI', Arial; font-size: 11pt; }
            QMenuBar { background-color: #111827; color: #e5e7eb; }
            QMenuBar::item { background: transparent; padding: 6px 10px; }
            QMenuBar::item:selected { background-color: #374151; }
            QMenu { background-color: #1f2937; color: #e5e7eb; border: 1px solid #4b5563; }
            QMenu::item { padding: 6px 28px 6px 20px; }
            QMenu::item:selected { background-color: #374151; }
            QTabWidget::pane { border: none; top: 0; }
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
            QPushButton#LivePrimaryButton {
                padding: 8px 12px;
                background-color: #3b82f6;
                color: #fff;
                border: none;
                border-radius: 8px;
            }
            QPushButton#LivePrimaryButton:hover { background-color: #2563eb; }
            QPushButton#LivePrimaryButton:checked { background-color: #ef4444; }
            QPushButton#LivePrimaryButton:disabled {
                background-color: #6b7280;
                color: #d1d5db;
            }
            QCheckBox { color: #e5e7eb; spacing: 8px; }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #4b5563;
                background: #374151;
            }
            QCheckBox::indicator:checked {
                background: #3b82f6;
                border-color: #60a5fa;
            }
            QCheckBox::indicator:disabled { background: #2d3643; border-color: #4b5563; }
            QTableWidget {
                background: #111827;
                color: #e5e7eb;
                gridline-color: #374151;
                border: 1px solid #374151;
                border-radius: 8px;
            }
            QTableWidget::item:selected { background: #1d4ed8; }
            QHeaderView::section {
                background: #1f2937;
                color: #9ca3af;
                border: none;
                padding: 4px;
            }
            QRadioButton { color: #e5e7eb; spacing: 8px; }
            QTabWidget::pane {
                border: 1px solid #374151;
                border-radius: 8px;
                background: #0f172a;
                margin-top: 4px;
            }
            QTabBar::tab {
                background: #1f2937;
                color: #d1d5db;
                padding: 8px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected { background: #3b82f6; color: #fff; }
            QTabBar::tab:hover:!selected { background: #374151; }
            QLabel#AnalyzeRichLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
            """
            + APP_QTOOLTIP_STYLESHEET
        )

    def _init_serial_port_widgets(self) -> None:
        self.port_combo = QComboBox(self)
        self.refresh_btn = QPushButton("Refresh Ports", self)
        self.refresh_btn.setObjectName("LivePrimaryButton")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.baud_combo = QComboBox(self)
        self.baud_combo.addItems(["115200", "57600", "38400", "19200", "9600", "230400"])
        self.baud_combo.setCurrentText("115200")
        self.refresh_ports()

    def show_serial_settings_dialog(self) -> None:
        if self._serial_settings_dialog is None:
            self._serial_settings_dialog = LiveSerialSettingsDialog(self, parent=self)
        self._serial_settings_dialog.show()
        self._serial_settings_dialog.raise_()
        self._serial_settings_dialog.activateWindow()

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText() if self.port_combo.count() else ""
        self.port_combo.clear()
        items = [p.device for p in list_ports.comports()]
        self.port_combo.addItems(items)
        if current and current in items:
            self.port_combo.setCurrentText(current)
        elif len(items) == 1:
            self.port_combo.setCurrentIndex(0)

    def _show_statistik_message_box(
        self,
        icon: QMessageBox.Icon,
        title: str,
        text: str,
    ) -> None:
        """
        Dialog ringkas tema gelap: ikon di baris sendiri (atas), teks di bawah,
        tombol OK — bukan layout horizontal QMessageBox (ikon kiri / teks kanan).
        """
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setModal(True)
        root = QVBoxLayout(dlg)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 18)

        app = QApplication.instance()
        pixmap = None
        if app is not None:
            st = app.style()
            if icon == QMessageBox.Icon.Critical:
                sp = QStyle.StandardPixmap.SP_MessageBoxCritical
            elif icon == QMessageBox.Icon.Warning:
                sp = QStyle.StandardPixmap.SP_MessageBoxWarning
            else:
                sp = QStyle.StandardPixmap.SP_MessageBoxInformation
            pixmap = st.standardPixmap(sp, None, dlg)

        if pixmap is not None and not pixmap.isNull():
            icon_lbl = QLabel(dlg)
            icon_lbl.setPixmap(pixmap)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            root.addWidget(icon_lbl)

        msg = QLabel(text, dlg)
        msg.setObjectName("StatDialogMessage")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        ok_btn = QPushButton("OK", dlg)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        dlg.setStyleSheet(THEMED_STATISTIK_DIALOG_STYLESHEET)
        dlg.exec()

    def show_about_dialog(self) -> None:
        """Dialog ringkas: nama aplikasi, versi, tujuan, rujukan manual."""
        text = (
            f"{APP_NAME}\n"
            f"Versi {APP_VERSION}\n\n"
            "Monitoring beban (kg) dan orientasi roll/pitch (°) dari perangkat serial "
            "dalam format CSV empat kolom per baris.\n\n"
            "Rekaman sesi disimpan ke folder DataLog; ringkasan statistik rekaman "
            "bisa diekspor dari tab Analisa ke folder DataStatistik.\n\n"
            f"Bantuan lengkap: menu Help → Manual membuka\n{USER_MANUAL_PDF.name}\n"
            "(PDF di folder yang sama dengan aplikasi, jika sudah dibuat)."
        )
        self._show_statistik_message_box(QMessageBox.Icon.Information, "Tentang", text)

    def open_user_manual_pdf(self) -> None:
        """Buka manual pengguna PDF dengan aplikasi bawaan sistem."""
        pdf = USER_MANUAL_PDF.resolve()
        if not pdf.is_file():
            self._show_statistik_message_box(
                QMessageBox.Icon.Warning,
                "Help",
                "Berkas manual PDF tidak ditemukan:\n"
                f"{_path_text_for_dialog(pdf)}\n\n"
                "Untuk membuat PDF dari Markdown, dari folder Force_Motion/Python jalankan:\n"
                "  python md_to_pdf_Force_Motion.py "
                f"-i Swimmer_Force_Motion_Monitoring_v2.3.0/{USER_MANUAL_MD.name} "
                f"-o Swimmer_Force_Motion_Monitoring_v2.3.0/{USER_MANUAL_PDF.name}\n\n"
                f"(Sesuaikan -i/-o jika Anda menjalankan skrip dari lokasi lain.)",
            )
            return
        url = QUrl.fromLocalFile(str(pdf))
        if not QDesktopServices.openUrl(url):
            self._show_statistik_message_box(
                QMessageBox.Icon.Critical,
                "Help",
                "Tidak dapat membuka PDF dengan aplikasi default sistem.\n"
                f"{_path_text_for_dialog(pdf)}",
            )

    def show_changelog_dialog(self) -> None:
        """Tampilkan isi ``Force_Motion/Python/Changelog.md`` dalam jendela baca-saja."""
        path = CHANGELOG_MD.resolve()
        if not path.is_file():
            self._show_statistik_message_box(
                QMessageBox.Icon.Warning,
                "Changelog",
                "Berkas changelog tidak ditemukan:\n"
                f"{_path_text_for_dialog(path)}",
            )
            return
        try:
            body = path.read_text(encoding="utf-8")
        except OSError as e:
            self._show_statistik_message_box(
                QMessageBox.Icon.Critical,
                "Changelog",
                f"Tidak bisa membaca changelog:\n{e}",
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Changelog")
        dlg.resize(720, 520)
        root = QVBoxLayout(dlg)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        editor = QTextEdit(dlg)
        editor.setReadOnly(True)
        editor.setPlainText(body)
        editor.setFont(QFont("Consolas", 10))
        editor.setStyleSheet(
            "QTextEdit { background: #0f172a; color: #e5e7eb; border: 1px solid #374151; }"
        )
        root.addWidget(editor, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("Tutup", dlg)
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        dlg.setStyleSheet(THEMED_STATISTIK_DIALOG_STYLESHEET)
        dlg.exec()

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
        self._reset_live_indicators()

    def _reset_live_indicators(self) -> None:
        self.force_label.setText("—")
        self.roll_label.setText("—")
        self.pitch_label.setText("—")
        self.battery_label.setText("—")

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
                if len(parts) not in (4, 5):
                    continue
                try:
                    ts = float(parts[0])
                    force_kg = float(parts[1])
                    roll_deg = float(parts[2])
                    pitch_deg = float(parts[3])
                    battery_pct = float(parts[4]) if len(parts) == 5 else None
                except ValueError:
                    continue
                self.update_live(ts, force_kg, roll_deg, pitch_deg, battery_pct)
                if self.log_file is not None:
                    ts_log = ts
                    if self.log_ts_zero_checkbox.isChecked():
                        if self._log_timestamp_t0 is None:
                            self._log_timestamp_t0 = ts
                        ts_log = ts - self._log_timestamp_t0
                    if self._sync_first_csv_ts is None:
                        self._sync_first_csv_ts = ts_log
                        self._sync_first_sample_wall = time.time()
                    self.log_buffer.append(
                        f"{ts_log:.2f},{force_kg:.2f},{roll_deg:.2f},{pitch_deg:.2f}\n"
                    )
        except Exception as e:
            print(f"[SERIAL] Read error: {e}")

    def update_live(
        self,
        ts: float,
        force_kg: float,
        roll_deg: float,
        pitch_deg: float,
        battery_pct: float | None = None,
    ) -> None:
        self.force_label.setText(f"{force_kg:.2f} Kg")
        self.roll_label.setText(f"{roll_deg:.2f}°")
        self.pitch_label.setText(f"{pitch_deg:.2f}°")
        if battery_pct is not None:
            self.battery_label.setText(f"{battery_pct:.0f} %")

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
            video_path = path.with_suffix(".mp4")
            video_will_record = self.camera_panel.is_preview_active()
            try:
                self.log_file_path = path
                self.log_file = open(path, "w", buffering=1, encoding="utf-8")
                self.log_file.write(f"Nama Perenang:,{name}\n")
                self.log_file.write(f"Gaya Renang:,{stroke}\n")
                self.log_file.write(f"Time:,{self._log_header_time_str}\n")
                if video_will_record:
                    self.log_file.write(f"VideoFile:,{video_path.name}\n")
                self._log_wall_start_epoch = time.time()
                self.log_file.write(
                    f"LogWallStartEpoch(s):,{self._log_wall_start_epoch:.6f}\n"
                )
                self.log_file.write(",".join(LIVE_CSV_DATA_HEADER) + "\n")
                self.log_buffer.clear()
                self._log_timestamp_t0 = None
                self._sync_first_csv_ts = None
                self._sync_first_sample_wall = None
                self.log_timer.start()
                self.log_btn.setText("Stop Log")
                self.swimmer_name_edit.setEnabled(False)
                self.stroke_combo.setEnabled(False)
                self.log_ts_zero_checkbox.setEnabled(False)
                self.connect_btn.setEnabled(False)
                self.log_filename_label.setText(path.name)
                self.camera_panel.set_logging_active(True)
                if video_will_record:
                    if not self.camera_panel.start_recording(video_path):
                        QMessageBox.warning(
                            self,
                            "Video",
                            "CSV dimulai, tetapi rekam video gagal.\n"
                            "Pastikan kamera aktif dipilih sebelum Start Log.",
                        )
            except Exception as e:
                QMessageBox.critical(self, "Log", f"Gagal membuka file:\n{e}")
                self.log_file = None
                self.log_file_path = None
                self.log_btn.setChecked(False)
                self.log_filename_label.setText("—")
        else:
            self.stop_logging()

    def stop_logging(self) -> None:
        try:
            self.log_timer.stop()
            self.flush_log_buffer()
            if self.log_file:
                if self._sync_first_csv_ts is not None:
                    self.log_file.write(
                        f"SyncCsvT0(s):,{self._sync_first_csv_ts:.6f}\n"
                    )
                    if self._log_wall_start_epoch is not None:
                        self.log_file.write(
                            f"SyncLogWallStart(s):,{self._log_wall_start_epoch:.6f}\n"
                        )
                    if self._sync_first_sample_wall is not None:
                        self.log_file.write(
                            f"SyncFirstSampleWall(s):,{self._sync_first_sample_wall:.6f}\n"
                        )
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
            self.log_ts_zero_checkbox.setEnabled(True)
            if self.connect_btn:
                self.connect_btn.setEnabled(True)
            self.log_filename_label.setText("—")
            self._log_timestamp_t0 = None
            self._log_wall_start_epoch = None
            self._sync_first_csv_ts = None
            self._sync_first_sample_wall = None
            self.camera_panel.stop_recording()
            self.camera_panel.set_logging_active(False)

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
        self.camera_panel.shutdown()
        super().closeEvent(event)


def _present_main_window(win: QMainWindow) -> None:
    """Tampilkan jendela utama memenuhi area kerja layar (maximized)."""
    win.setMinimumSize(720, 480)
    win.showMaximized()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_app_tooltip_theme(app)
    win = MainWindow()
    _present_main_window(win)
    sys.exit(app.exec())

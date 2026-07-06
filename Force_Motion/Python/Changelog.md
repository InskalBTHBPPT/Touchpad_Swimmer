# Changelog — Swimmer Force Motion Monitoring

Catatan perubahan antar versi aplikasi **Swimmer Force Motion Monitoring** (folder `Swimmer_Force_Motion_Monitoring_v*`). Entri terbaru di atas.

---

## [2.3.0] — 2026-06-25

Bandingan dengan **v2.2.0** (`Swimmer_Force_Motion_Monitoring_v2.2.0/`).

### Ditambahkan

- **Tab Live — kamera** — panel pindai/pilih perangkat video, preview live, rekam `.mp4` ke `DataLog/` (basename sama dengan CSV) saat **Start Log**; modul `live_camera_core.py`, `live_camera_panel.py`.
- **Tab Analisa — video** — tiga plot spektrum diganti panel **playback video** (auto-load `.mp4` pasangan CSV); frekuensi dominan FFT/Welch tetap di **kartu statistik** (tanpa plot spektrum visual); modul `analyze_video_panel.py`.
- **Sinkron video ↔ plot** — metadata di CSV (`VideoFile`, `LogWallStartEpoch`, footer `SyncCsvT0` / `SyncLogWallStart` / `SyncFirstSampleWall`); playhead memakai titik acuan rekaman; CSV lama fallback sinkron kasar (`TimeStamp` baris pertama + detik video).
- **Tab Analisa — koreksi & region** — region **biru** (data uji) dan **hijau** (zero offset) pada plot; checkbox **Zero Offset**; **Koreksi sudut tali** (default 7°); **Koreksi batas bawah Force mentah** (−1 Kg, default aktif).
- **Tab Analisa — statistik gaya tethered** — **Metode A** global (peakF, meanF, minF, ImpF, FI) dan **Metode B** per siklus Andrade (Butterworth orde 4, cutoff default 7 Hz): TpeakF, DUR, RFD, **dF** (Morouço); modul `analyze_tethered_force_metrics.py`.
- **Tab Analisa — tooltip** — penjelasan singkat per baris tabel statistik dan tombol video; modul `ui_tooltip.py` (tema latar terang).
- **`LogSyncMeta`** di `live_csv_io.py` — parser metadata sinkron opsional.
- **Dependensi** — `opencv-python`, `pygrabber` (`requirements.txt`).
- **Manual v2.3.0** — `UserManual_Force_Motion_v2.3.0.md` / `.pdf` di folder `Swimmer_Force_Motion_Monitoring_v2.3.0/` (§4.3–4.6a: metrik Force, dF, FI, koreksi, tooltip).

### Diubah

- **Tab Analisa** — layout: plot waktu | panel video | panel kanan; tidak ada plot spektrum visual; pengaturan analisa di dialog **Setting…** (koreksi, metode Force, spektrum, gap).
- **Gap rekaman CSV** — perhitungan memakai **seluruh deret timestamp CSV** (bukan hanya region uji biru).
- **Ekspor `DataStatistik/`** — kolom metrik Force diperluas (Metode A/B, Filter Andrade, TpeakF, DUR, RFD, dF, FI, zero offset, koreksi); nama file memuat cap waktu ekspor (`_DataStatistik_<ddmmyy-HHMMSS>.csv`) agar tidak menimpa ekspor sebelumnya.
- **Docstring** modul utama v2.3.0, `analyze_single_file_tab.py`, manual, dan modul kamera/video/metrik diselaraskan dengan fitur di atas.

### Kompatibilitas

- CSV dan MP4 rekaman lama tetap bisa dimuat di tab Analisa; tanpa metadata sinkron, playhead memakai sinkron kasar.

---

## [2.2.0] — 2026-06-23

Bandingan dengan **v2.1.0** (`Swimmer_Force_Motion_Monitoring_v2.1.0/`).

### Ditambahkan

- **Tab Live — baterai** — parser serial menerima baris **empat atau lima** kolom; kolom kelima `Baterai(%)` (mis. dari LoRa Receiver ESP32) ditampilkan di grup **Nilai terakhir**; **tidak** disimpan ke CSV `DataLog/` (rekaman tetap empat kolom data).
- **Tab Analisa — gap rekaman CSV** — estimasi sampel hilang dari kolom `TimeStamp(s)` sebagai indikator kualitas rekaman (bukan diagnosis LoRa). Radio **Metode A — per gap (lokal)** dan **Metode B — global (ringkas)** di grup **Analisa Setting**; kartu statistik **GAP REKAMAN CSV**; diekspor ke `DataStatistik/` bersama statistik lain.
- **`analyze_metrics_core.py`** — `compute_gap_loss`, `GapLossStats`, `median_dt_s`, `consecutive_deltas_s`; toleransi gap Metode A: `Δt > 1,5 × median(Δt)`.
- **Manual v2.2.0** — `UserManual_Force_Motion_v2.2.0.md` / `.pdf` di folder `Swimmer_Force_Motion_Monitoring_v2.2.0/`.

### Diubah

- **Docstring** modul utama v2.2.0 — format serial lima kolom, gap rekaman, changelog 2.1.0 → 2.2.0.
- **Ekspor `DataStatistik/`** — blok tambahan **Gap rekaman CSV (estimasi)** (metode, Δt nominal, laju efektif, sampel tercatat/hilang, persen; Metode A: jumlah gap; Metode B: sampel diharapkan).

---

## [2.1.0] — 2026-05-14

Bandingan dengan **v2.0.0** (`Swimmer_Force_Motion_Monitoring_v2.0.0/`).

### Ditambahkan

- **Tab Analisa multifile** — hingga **5** berkas CSV Live; **tabel** perbandingan dengan header multi-baris (nama perenang, gaya, nama file, *Value*); teks sel data **rata tengah**.
- **Baris kontrol** — *Add file*; *Simpan tabel ke CSV* (tombol abu-abu); *Plot data* (hijau) di samping simpan; *Hapus kolom* + combo + *Clear tabel* (merah); baris **Metode spektrum** (FFT / Welch) memuat ulang semua kolom.
- **Jendela plot** (`MultiFilePlotDialog`) — non-modal; dropdown **Metrik** dan **Gaya plot** di dalam jendela (diagram batang, **garis + penanda** default, titik saja; pyqtgraph).
- **Folder `TableMultiFile/`** — ekspor `ddmmyy_HHMM_TableMultiFile.csv` (UTF-8), struktur baris mengikuti tabel.
- **Modul** `analyze_metrics_core.py`, `analyze_multi_file_tab.py`; manual **v2.1.0** (MD/PDF).

---

## [2.0.0] — 2026-05-14

Bandingan dengan **v1.0.0** (`Swimmer_Force_Motion_Monitoring_v1.0.0.py`).

### Ditambahkan

- **Modul `live_csv_io.py`** — konstanta `LIVE_CSV_DATA_HEADER` dan fungsi `parse_logged_csv` untuk membaca CSV rekaman tab Live dengan validasi metadata + header (dipakai tab Analisa dan konsisten dengan penulisan log).
- **Modul `analyze_single_file_tab.py`** — tab **Analisa** terpisah: kelas `AnalyzeSingleFileTab`, plot waktu penuh, marker ekstremum, **tiga plot spektrum** (Force / Roll / Pitch), pemilihan metode **FFT** atau **Welch PSD** (`numpy`, `scipy`), marker puncak pada spektrum, kartu statistik dengan **TimeStamp Start** dan **frekuensi dominan** per saluran.
- **Ekspor statistik diperluas** — berkas `DataStatistik/<nama_log>_DataStaistik.csv` mencakup baris `Timestampstart (s)` serta blok **Frekuensi Dominan (Hz)** untuk Force / Roll / Pitch dengan kolom **Metode** (FFT / Welch PSD).
- **Manual pengguna v2.0.0** — `UserManual_Force_Motion_v2.0.0.md` / `.pdf` di folder `Swimmer_Force_Motion_Monitoring_v2.0.0/`.
- **Dependensi** — `numpy` dan `scipy` untuk perhitungan spektrum di tab Analisa.

### Diubah

- **Struktur proyek** — logika analisa dan CSV tidak lagi monolit di satu berkas utama; berkas aplikasi v2: `Swimmer_Force_Motion_Monitoring_v2.0.0.py` mengimpor modul di atas.
- **Dialog bantuan** — tombol Help mengarah ke `UserManual_Force_Motion_v2.0.0.pdf`; instruksi pembuatan PDF memakai `md_to_pdf_Force_Motion.py` dengan opsi `-i` / `-o` ke path manual v2 (skrip tetap di folder `Force_Motion/Python`).
- **Gaya pesan** — dialog untuk simpan statistik / About memakai stylesheet *themed* konsisten.

### Dokumentasi

- Docstring modul utama v2, `live_csv_io.py`, dan `analyze_single_file_tab.py` diperbarui; bagian *Changelog* ringkas juga ada di docstring `Swimmer_Force_Motion_Monitoring_v2.0.0.py`.
- `md_to_pdf_Force_Motion.py` — docstring memuat contoh pembuatan PDF untuk manual v2.0.0.

---

## [1.0.0]

Rilis awal yang didokumentasikan di repositori ini: satu berkas `Swimmer_Force_Motion_Monitoring_v1.0.0.py` dengan tab **Live** (serial, plot geser, rekaman `DataLog/`) dan tab **Analisa** (muat CSV, plot penuh, marker ekstremum, ekspor statistik dasar ke `DataStatistik/`), tanpa plot spektrum dan tanpa modul `live_csv_io` / `analyze_single_file_tab` terpisah.

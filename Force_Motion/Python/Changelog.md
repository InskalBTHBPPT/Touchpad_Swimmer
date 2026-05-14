# Changelog — Swimmer Force Motion Monitoring

Catatan perubahan antar versi aplikasi **Swimmer Force Motion Monitoring** (folder `Swimmer_Force_Motion_Monitoring_v*`). Entri terbaru di atas.

---

## [2.1.0] — 2026-05-14

Bandingan dengan **v2.0.0** (`Swimmer_Force_Motion_Monitoring_v2.0.0/`).

### Ditambahkan

- **Tab Analisa multifile** — hingga **5** berkas CSV Live sekaligus; tampilan **tabel** (bukan plot) dengan header multi-baris (nama perenang, gaya, nama file, baris *Value*).
- **Tombol** *Add file* / *Simpan tabel ke CSV*; **dropdown metode spektrum** (FFT / Welch PSD) mengisi ulang semua kolom saat diganti.
- **Folder `TableMultiFile/`** — ekspor tabel `ddmmyy_HHMM_TableMultiFile.csv` (UTF-8), struktur baris mengikuti tampilan tabel.
- **Modul** `analyze_metrics_core.py`, `analyze_multi_file_tab.py`.

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

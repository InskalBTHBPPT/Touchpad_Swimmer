# Manual Pengguna — Swimmer Force Motion Monitoring v2.1.0

Dokumen ini menjelaskan pemakaian aplikasi desktop **Swimmer Force Motion Monitoring** (berkas utama: `Swimmer_Force_Motion_Monitoring_v2.1.0.py`) untuk memantau beban dan orientasi (roll, pitch) perenang melalui koneksi serial, merekam data ke CSV, serta menganalisis rekaman dengan **spektrum frekuensi**, **perbandingan multi-berkas** dalam tabel, dan ekspor statistik yang diperluas.

---

## 1. Persyaratan

| Komponen | Keterangan |
|----------|------------|
| Python | Disarankan 3.10 atau lebih baru |
| Paket | `PySide6`, `pyqtgraph`, `pyserial`, `numpy`, `scipy` |
| Perangkat | Mikrokontroler / sensor yang mengirim **satu baris CSV per sampel** lewat USB serial (UTF-8) |
| Sistem | Windows (uji utama); Linux/macOS seharusnya kompatibel selama driver serial tersedia |

Instalasi contoh:

```text
pip install PySide6 pyqtgraph pyserial numpy scipy
```

Jalankan aplikasi dari folder `Swimmer_Force_Motion_Monitoring_v2.1.0` (atau dengan path penuh):

```text
python Swimmer_Force_Motion_Monitoring_v2.1.0.py
```

---

## 2. Ringkasan antarmuka

Aplikasi memiliki **tiga tab**:

- **Live** — koneksi serial, plot waktu-nyata, indikator nilai terakhir, rekaman CSV, opsi timestamp CSV, tombol **About** dan **Help**.
- **Analisa** — muat **satu** file CSV hasil rekaman Live, plot waktu penuh dengan marker ekstremum, **tiga plot spektrum** (FFT atau Welch PSD), kartu statistik (termasuk **frekuensi dominan** per kanal), ekspor ringkasan ke `DataStatistik/`.
- **Analisa multifile** — hingga **lima** berkas CSV sekaligus; hasil ringkasan metrik ditampilkan dalam **tabel** (bukan plot); simpan tabel ke folder `TableMultiFile/`; metode spektrum (FFT / Welch) mengisi ulang semua kolom.

Modul pendukung di folder yang sama:

- `live_csv_io.py` — header data CSV dan `parse_logged_csv` untuk tab Analisa (format sama dengan rekaman Live).
- `analyze_single_file_tab.py` — implementasi tab Analisa (satu berkas).
- `analyze_metrics_core.py` — perhitungan metrik + spektrum (dipakai tab multifile).
- `analyze_multi_file_tab.py` — implementasi tab Analisa multifile.

---

## 3. Tab Live

### 3.1 Port dan baud

1. Pilih **Port** COM yang sesuai dengan perangkat (tombol **Refresh Ports** memperbarui daftar).
2. Pilih **Baud** (default umum: `115200`).
3. Isi **Nama Perenang** dan **Gaya renang** (dipakai untuk nama file log dan metadata CSV).

### 3.2 Connect

- Tekan **Connect** untuk membuka port serial.
- Saat terhubung, teks tombol berubah (mode *toggle*); plot dan indikator **Nilai terakhir** akan terisi jika data valid masuk.
- **Disconnect** dengan menekan tombol yang sama saat dalam keadaan terhubung.

### 3.3 Format data serial

Setiap baris (diakhiri baris baru `\n`) berisi **tepat empat nilai** dipisahkan koma:

| Kolom | Nama di CSV | Contoh |
|-------|-------------|--------|
| 1 | TimeStamp(s) | `12.34` |
| 2 | Force(Kg) | `5.67` |
| 3 | Roll(Deg) | `-1.2` |
| 4 | Pitch(Deg) | `3.4` |

Baris yang diawali `#` diabaikan. Baris yang tidak memiliki empat kolom numerik valid dilewati.

### 3.4 Plot Live

Tiga plot vertikal: **Force**, **Roll**, **Pitch** terhadap waktu (sumbu X: detik). Jumlah titik ditampung terbatas (jendela geser) agar tampilan tetap ringan.

### 3.5 Start Log / Stop Log

- **Start Log** hanya aktif jika serial sudah terhubung.
- Rekaman ditulis ke folder **`DataLog/`** (otomatis dibuat di samping skrip), tanpa dialog *Save As*.
- Nama file memuat nama perenang, gaya renang, dan cap waktu (format `ddmmyy-HHMM`).
- Saat log berjalan, beberapa field (nama, gaya, checkbox timestamp) dikunci; **Stop Log** menghentikan rekaman dan menutup file.

Struktur awal file CSV rekaman:

1. Baris metadata: `Nama Perenang:`, `Gaya Renang:`, `Time:`
2. Header data: `TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)`
3. Baris data numerik

### 3.6 Checkbox “TimeStamp CSV mulai 0 saat Start Log”

- **Default:** tidak dicentang → kolom waktu di CSV sama dengan nilai dari perangkat.
- **Dicentang:** kolom waktu di CSV = waktu serial **dikurangi** timestamp **sampel pertama setelah Start Log** (bukan saat Connect). Baris pertama data mendekati `0` s.
- Plot Live tetap memakai waktu mentah dari serial.

### 3.7 About dan Help

- **About** — menampilkan dialog informasi aplikasi dan versi (**2.1.0**).
- **Help** — membuka berkas **`UserManual_Force_Motion_v2.1.0.pdf`** dengan aplikasi PDF bawaan sistem. Jika PDF belum ada, dialog menjelaskan cara membuatnya (lihat bagian 7).

---

## 4. Tab Analisa

### 4.1 Load CSV

- Tekan **Load CSV…** dan pilih file rekaman dari folder `DataLog/` (atau lokasi lain).
- File harus memiliki metadata dan header data yang sesuai format tab Live (lihat §3.5). Parser memakai `live_csv_io.parse_logged_csv`.

### 4.2 Plot waktu dan statistik

Setelah berhasil dimuat:

- Tiga plot menampilkan rekaman penuh.
- Marker menandai titik ekstrem (force maksimum; roll/pitch min dan max) dengan label waktu.
- Panel kanan menampilkan ringkasan angka yang konsisten dengan marker, baris **TimeStamp Start** (waktu minimum deret), serta **frekuensi dominan** (Hz) per kanal beserta label metode spektrum (**FFT** atau **Welch PSD**).

### 4.3 Metode spektrum

- Pilih **FFT** atau **Welch PSD** pada kontrol di area pengaturan Analisa.
- Perubahan metode memperbarui plot spektrum, marker puncak, dan angka frekuensi dominan pada kartu statistik.

### 4.4 Plot spektrum

- Tiga plot di bawah plot waktu menampilkan spektrum **satu sisi** (komponen DC tidak ditampilkan pada sumbu frekuensi positif).
- Sumbu Y menyesuaikan label (FFT ternormalisasi vs PSD linear, sesuai implementasi).

### 4.5 Simpan statistik

- Tombol **Simpan statistik** menulis file CSV ke folder **`DataStatistik/`** tanpa dialog penyimpanan.
- Nama file: `<nama_file_csv_yang_dimuat>_DataStaistik.csv` (sufiks persis seperti di aplikasi).
- Isi ringkas:
  - Metadata (nama perenang, gaya renang, waktu ekspor, nama berkas sumber).
  - Baris **`Timestampstart (s)`** + nilai (waktu awal deret, sama dengan yang ditampilkan di panel statistik).
  - Tabel **`Metrik, Nilai, Satuan, Waktu (s)`** untuk ekstremum (force maksimum; roll min/maks; pitch min/maks).
  - Setelah blok tersebut, dua baris kosong, lalu tabel **`Metrik, Frekuensi Dominan (Hz), Metode`** dengan baris **Force**, **Roll**, **Pitch** (metode sama untuk ketiga saluran pada satu ekspor).

---

## 5. Tab Analisa multifile

### 5.1 Add file dan batas berkas

- Tombol **Add file** membuka dialog pilih CSV rekaman (default folder `DataLog/`).
- Maksimum **5** berkas; setiap berkas valid menambah **satu kolom** baru di kanan tabel.
- Parser sama dengan tab Analisa (`live_csv_io.parse_logged_csv`).

### 5.2 Metode spektrum

- Dropdown **Metode spektrum** (FFT / Welch PSD) sama maknanya dengan di tab Analisa satu berkas.
- Mengganti metode menghitung ulang **semua kolom** yang sudah dimuat.

### 5.3 Isi tabel

- Empat baris paling atas setiap kolom data: nama perenang, gaya renang, nama file, lalu baris label **Value**.
- Kolom pertama (**Metrik**) memuat label baris: timestamp start, ekstremum force/roll/pitch beserta timestamp, frekuensi dominan per saluran, serta baris **Metode spektrum frekuensi**.

### 5.4 Simpan tabel ke CSV

- Tombol **Simpan tabel ke CSV** menulis berkas ke folder **`TableMultiFile/`** (tanpa dialog *Save As*).
- Nama file: `ddmmyy_HHMM_TableMultiFile.csv` (cap waktu lokal + sufiks `_TableMultiFile`).
- Isi CSV mengikuti **tampilan tabel** (termasuk header multi-baris sebagai beberapa baris awal berkas).

---

## 6. Folder kerja

| Folder / berkas | Fungsi |
|-----------------|--------|
| `DataLog/` | Rekaman CSV dari tab Live (diabaikan Git sesuai `.gitignore` proyek) |
| `DataStatistik/` | Ekspor statistik dari tab Analisa |
| `TableMultiFile/` | Ekspor tabel tab Analisa multifile |
| `live_csv_io.py` | Header + parser CSV rekaman |
| `analyze_single_file_tab.py` | Tab Analisa (plot + statistik + ekspor) |
| `analyze_metrics_core.py` | Metrik rekaman + spektrum (multifile) |
| `analyze_multi_file_tab.py` | Tab Analisa multifile |
| `UserManual_Force_Motion_v2.1.0.md` | Manual ini (Markdown) |
| `UserManual_Force_Motion_v2.1.0.pdf` | Manual ini (PDF, opsional) |
| `../md_to_pdf_Force_Motion.py` | Skrip konversi MD → PDF (folder induk `Force_Motion/Python`) |

---

## 7. Membuat / memperbarui PDF manual

Aplikasi **Help** membuka PDF. PDF dihasilkan dari Markdown dengan skrip `md_to_pdf_Force_Motion.py` (pustaka **markdown** dan **xhtml2pdf**), berada di folder **`Force_Motion/Python`**.

Dari folder `Force_Motion/Python`:

```text
pip install markdown xhtml2pdf
python md_to_pdf_Force_Motion.py -i Swimmer_Force_Motion_Monitoring_v2.1.0/UserManual_Force_Motion_v2.1.0.md -o Swimmer_Force_Motion_Monitoring_v2.1.0/UserManual_Force_Motion_v2.1.0.pdf
```

Tanpa opsi, skrip bawaan masih mengarah ke manual **v1.0.0** di folder yang sama; untuk v2.1.0 gunakan `-i` dan `-o` seperti di atas.

---

## 8. Pemecahan masalah

| Gejala | Tindakan |
|---------|----------|
| Port tidak muncul | Cabut/colok USB, klik **Refresh Ports**, periksa driver (mis. CP210x, CH340). |
| Connect gagal | Pastikan port tidak dipakai program lain; coba baud yang sesuai firmware. |
| Plot kosong | Periksa format baris (empat angka, koma); pastikan firmware mengirim newline. |
| Load CSV gagal di Analisa | Pastikan file dari tab Live yang sama (metadata + header persis). |
| Help tidak membuka PDF | Jalankan §7; pastikan `UserManual_Force_Motion_v2.1.0.pdf` ada di folder aplikasi v2.1.0. |
| Error import `numpy` / `scipy` | Instal dependensi (lihat §1). |

---

## 9. Versi dokumen

- **Manual:** selaras dengan aplikasi **v2.1.0**.
- Ringkasan perubahan antar versi ada di `Force_Motion/Python/Changelog.md` dan docstring `Swimmer_Force_Motion_Monitoring_v2.1.0.py`.

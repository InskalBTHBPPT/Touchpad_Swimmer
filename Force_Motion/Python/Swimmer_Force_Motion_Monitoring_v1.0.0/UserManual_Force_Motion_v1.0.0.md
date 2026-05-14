# Manual Pengguna — Swimmer Force Motion Monitoring v1.0.0

Dokumen ini menjelaskan pemakaian aplikasi desktop **Swimmer Force Motion Monitoring** (berkas utama: `Swimmer_Force_Motion_Monitoring_v1.0.0.py`) untuk memantau beban dan orientasi (roll, pitch) perenang melalui koneksi serial, merekam data ke CSV, serta menganalisis rekaman.

---

## 1. Persyaratan

| Komponen | Keterangan |
|----------|------------|
| Python | Disarankan 3.10 atau lebih baru |
| Paket | `PySide6`, `pyqtgraph`, `pyserial` |
| Perangkat | Mikrokontroler / sensor yang mengirim **satu baris CSV per sampel** lewat USB serial (UTF-8) |
| Sistem | Windows (uji utama); Linux/macOS seharusnya kompatibel selama driver serial tersedia |

Instalasi contoh:

```text
pip install PySide6 pyqtgraph pyserial
```

Jalankan aplikasi dari folder `Force_Motion/Python`:

```text
python Swimmer_Force_Motion_Monitoring_v1.0.0.py
```

---

## 2. Ringkasan antarmuka

Aplikasi memiliki **dua tab**:

- **Live** — koneksi serial, plot waktu-nyata, indikator nilai terakhir, rekaman CSV, opsi timestamp CSV, tombol **About** dan **Help**.
- **Analisa** — muat file CSV hasil rekaman Live, plot dengan marker ekstremum, kartu statistik, ekspor ringkasan statistik.

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

- **About** — menampilkan dialog informasi aplikasi dan versi.
- **Help** — membuka berkas **`UserManual_Force_Motion_v1.0.0.pdf`** dengan aplikasi PDF bawaan sistem. Jika PDF belum ada, dialog menjelaskan cara membuatnya (lihat bagian 6).

---

## 4. Tab Analisa

### 4.1 Load CSV

- Tekan **Load CSV…** dan pilih file rekaman dari folder `DataLog/` (atau lokasi lain).
- File harus memiliki metadata dan header data yang sesuai format tab Live (lihat §3.5).

### 4.2 Plot dan statistik

Setelah berhasil dimuat:

- Tiga plot menampilkan rekaman penuh.
- Marker menandai titik ekstrem (force maksimum; roll/pitch min dan max) dengan label waktu.
- Panel kanan menampilkan ringkasan angka yang konsisten dengan marker.

### 4.3 Simpan statistik

- Tombol **Simpan statistik…** menulis file CSV ke folder **`DataStatistik/`** tanpa dialog penyimpanan.
- Nama file: `<nama_file_csv_yang_dimuat>_DataStaistik.csv` (sufiks persis seperti di aplikasi).
- Isi mencakup metadata (nama, gaya, waktu ekspor, nama berkas sumber) dan tabel metrik ekstremum.

---

## 5. Folder kerja

| Folder / berkas | Fungsi |
|-----------------|--------|
| `DataLog/` | Rekaman CSV dari tab Live (diabaikan Git sesuai `.gitignore` proyek) |
| `DataStatistik/` | Ekspor statistik dari tab Analisa |
| `UserManual_Force_Motion_v1.0.0.md` | Manual ini (Markdown) |
| `UserManual_Force_Motion_v1.0.0.pdf` | Manual ini (PDF, opsional) |
| `md_to_pdf_Force_Motion.py` | Skrip untuk menghasilkan PDF dari Markdown |

---

## 6. Membuat / memperbarui PDF manual

Aplikasi **Help** membuka PDF. PDF dihasilkan dari Markdown dengan skrip yang mengikuti pola proyek *Touchpad_Timer_Pressure* (`md_to_pdf_xhtml2pdf.py`): memakai pustaka **markdown** dan **xhtml2pdf**.

Dari folder `Force_Motion/Python`:

```text
pip install markdown xhtml2pdf
python md_to_pdf_Force_Motion.py
```

Secara default, masukan = `UserManual_Force_Motion_v1.0.0.md`, keluaran = `UserManual_Force_Motion_v1.0.0.pdf`. Opsi baris perintah:

```text
python md_to_pdf_Force_Motion.py -i UserManual_Force_Motion_v1.0.0.md -o UserManual_Force_Motion_v1.0.0.pdf
```

---

## 7. Pemecahan masalah

| Gejala | Tindakan |
|---------|----------|
| Port tidak muncul | Cabut/colok USB, klik **Refresh Ports**, periksa driver (mis. CP210x, CH340). |
| Connect gagal | Pastikan port tidak dipakai program lain; coba baud yang sesuai firmware. |
| Plot kosong | Periksa format baris (empat angka, koma); pastikan firmware mengirim newline. |
| Load CSV gagal di Analisa | Pastikan file dari tab Live yang sama (metadata + header persis). |
| Help tidak membuka PDF | Jalankan §6; pastikan `UserManual_Force_Motion_v1.0.0.pdf` ada di folder skrip. |

---

## 8. Versi dokumen

- **Manual:** selaras dengan aplikasi **v1.0.0**.
- Untuk perubahan besar fitur, perbarui nomor versi pada nama berkas aplikasi, MD, PDF, dan konstanta versi di dalam skrip.

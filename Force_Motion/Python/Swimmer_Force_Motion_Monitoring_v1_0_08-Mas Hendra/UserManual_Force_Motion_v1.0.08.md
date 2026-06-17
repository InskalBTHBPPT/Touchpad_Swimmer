# Manual Pengguna — Swimmer Force and Motion Monitoring v1.0.08

Dokumen ini menjelaskan pemakaian aplikasi desktop **Swimmer Force and Motion Monitoring** v1.0.08 (berkas: `Swimmer_Force_Motion_Monitoring_v1_0_08.py`) untuk memantau beban (force) dan orientasi (roll, pitch) perenang melalui koneksi serial USB, merekam data ke CSV, serta menganalisis rekaman dengan statistik ekstremum dan analisa FFT pada sinyal force.

---

## 1. Persyaratan

| Komponen | Keterangan |
|----------|------------|
| Python | Disarankan 3.10 atau lebih baru |
| Paket | `PySide6`, `pyqtgraph`, `pyserial`, `numpy` |
| Perangkat | Mikrokontroler / sensor yang mengirim **satu baris CSV per sampel** lewat USB serial (UTF-8) |
| Sistem | Windows (uji utama); Linux/macOS seharusnya kompatibel selama driver serial tersedia |

Instalasi contoh:

```text
pip install PySide6 pyqtgraph pyserial numpy
```

Jalankan aplikasi dari folder yang berisi berkas skrip:

```text
python Swimmer_Force_Motion_Monitoring_v1_0_08.py
```

Folder output otomatis dibuat di **direktori kerja saat aplikasi dijalankan** (biasanya folder skrip):

- `DataLog/` — file CSV rekaman sesi Live
- `DataStatistik/` — ringkasan statistik hasil tab Analisa

---

## 2. Ringkasan antarmuka

Aplikasi memiliki **dua tab**:

| Tab | Fungsi |
|-----|--------|
| **Live** | Koneksi serial, plot waktu-nyata (jendela 10 detik), indikator baterai di header, rekaman CSV, konsol log |
| **Analisa** | Muat satu file CSV log, plot waktu penuh + marker min/max, FFT force, ekspor statistik |

Header jendela menampilkan judul aplikasi, **ikon baterai** (jika perangkat mengirim kolom ke-5), dan nomor versi.

Panel kiri tab Live juga menampilkan logo BRIN / UNNES (jika berkas `logo_brin.png` dan `logo_unnes.png` ada di folder skrip) serta tombol **About** dan **Help**.

---

## 3. Tab Live

### 3.1 Koneksi serial

1. Pilih **Port** COM dari dropdown (tombol **⟳ Refresh** memperbarui daftar port).
2. Pilih **Baud** (default: `115200`).
3. Klik **▶ Connect** untuk membuka port serial.
4. Klik **■ Disconnect** untuk menutup koneksi (logging aktif akan dihentikan otomatis).

### 3.2 Info perenang

| Field | Keterangan |
|-------|------------|
| **Nama** | Nama atlet (default: `Atlet`); dipakai untuk nama file log |
| **Gaya** | Pilihan: Bebas, Dada, Punggung, Kupu-kupu, Monofin, Bifins |

### 3.3 Format data serial

Setiap baris (diakhiri `\n`) berisi **minimal empat nilai** dipisahkan koma:

| Kolom | Nama | Satuan | Wajib |
|-------|------|--------|-------|
| 1 | TimeStamp | detik | Ya |
| 2 | Force | Kg | Ya |
| 3 | Roll | derajat | Ya |
| 4 | Pitch | derajat | Ya |
| 5 | Battery | % | Tidak (opsional) |

Contoh:

```text
12.3400,5.6700,-1.2000,3.4000,87
```

- Baris kosong atau diawali `#` diabaikan.
- Baris dengan kurang dari empat kolom numerik valid dilewati.
- Kolom baterai (jika ada) memperbarui ikon di header; **tidak** ditulis ke file CSV log.

### 3.4 Plot Live

Tiga grafik vertikal menampilkan **Force**, **Roll**, dan **Pitch** terhadap waktu:

- Sumbu X menampilkan jendela geser **10 detik** terakhir.
- Buffer data dibatasi oleh **Max Titik** (default 1000) sebagai safety cap.

### 3.5 Rekaman log (Start Log / Stop Log)

- **Start Log** hanya aktif setelah serial terhubung.
- File disimpan otomatis ke `DataLog/` dengan pola nama:

  `{Nama}_{Gaya}_{ddmmyy-HHMM}.csv`

- **Stop Log** menghentikan rekaman, men-flush buffer, dan menutup file.

Struktur file CSV:

1. Baris metadata: `Nama Perenang:`, `Gaya Renang:`, `Time:`
2. Header data: `TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)`
3. Baris data numerik (empat kolom)

### 3.6 Checkbox “TimeStamp CSV set to 0”

- **Default:** dicentang → waktu di CSV = timestamp serial **dikurangi** timestamp sampel terakhir saat Start Log ditekan.
- **Tidak dicentang:** waktu di CSV sama dengan nilai mentah dari perangkat.
- Plot Live selalu memakai waktu mentah dari serial.

### 3.7 Pengaturan plot

Field **Max Titik** mengatur batas maksimum titik di buffer internal (minimal 10). Klik **Terapkan** setelah mengubah nilai.

### 3.8 About dan Help

- **About** — dialog informasi aplikasi dan versi.
- **Help** — membuka `UserManual_Force_Motion_v1.0.08.pdf` di folder skrip. Jika PDF tidak ada, dialog menampilkan isi file Markdown manual.

---

## 4. Tab Analisa

### 4.1 Muat CSV log

1. Klik **📂 Muat CSV Log...**
2. Pilih file dari `DataLog/` (atau lokasi lain).
3. File harus memiliki metadata dan header data sesuai format rekaman Live (lihat §3.5).

Panel **Metadata** menampilkan nama perenang, gaya, waktu rekaman, dan jumlah sampel.

### 4.2 Plot waktu dan marker

Empat plot vertikal:

| Plot | Isi |
|------|-----|
| Force | Kurva force vs waktu + marker min (◇) dan max (△) |
| Roll | Kurva roll vs waktu + marker min/max |
| Pitch | Kurva pitch vs waktu + marker min/max |
| FFT Force | Spektrum frekuensi force (0–5 Hz) dengan garis puncak dominan |

### 4.3 Statistik ekstremum

Panel **Statistik Ekstremum** menampilkan:

- Force Min / Max / Mean
- Roll Min / Max
- Pitch Min / Max

Nilai min/max disertai waktu kejadian (`@ X.XXs`).

### 4.4 Analisa FFT — Force

Perhitungan menggunakan **FFT** dengan window Hanning pada sinyal force (DC dihilangkan):

| Metrik | Keterangan |
|--------|------------|
| Freq. Dominan | Frekuensi puncak spektrum (Hz) |
| Amplitudo Maks | Amplitudo pada frekuensi dominan (Kg) |
| Periode | Kecepatan balik frekuensi dominan (s) |
| Stroke Rate | Frekuensi dominan × 60 (SPM — stroke per menit) |
| Bandwidth | Lebar setengah daya (-3 dB) di sekitar puncak (Hz) |
| RMS Force | Root mean square seluruh deret force (Kg) |

Plot FFT dibatasi tampilan hingga **5 Hz** (relevan untuk gerakan renang).

### 4.5 Simpan statistik

Tombol **💾 Simpan Statistik** menulis file ke `DataStatistik/`:

- Nama: `<nama_file_csv>_DataStaistik.csv`
- Isi: metadata, tabel `Metric,Value,Unit,TimeStamp(s)`, dan blok **Analisa FFT Force**

---

## 5. Struktur folder

```text
(folder skrip)/
├── Swimmer_Force_Motion_Monitoring_v1_0_08.py
├── UserManual_Force_Motion_v1.0.08.md
├── UserManual_Force_Motion_v1.0.08.pdf
├── logo_brin.png          (opsional)
├── logo_unnes.png         (opsional)
├── DataLog/               (dibuat saat runtime)
└── DataStatistik/         (dibuat saat runtime)
```

---

## 6. Pemecahan masalah

| Gejala | Kemungkinan penyebab | Solusi |
|--------|---------------------|--------|
| Port tidak muncul | Driver USB belum terpasang | Pasang driver CH340/CP210x; klik Refresh |
| Connect gagal | Port dipakai aplikasi lain | Tutup Serial Monitor / aplikasi lain |
| Plot kosong | Format data salah | Pastikan 4 kolom numerik per baris, dipisah koma |
| Baterai tidak tampil | Perangkat tidak kirim kolom ke-5 | Normal; fitur opsional |
| Gagal muat CSV | File bukan dari aplikasi ini | Pastikan header `TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)` ada |
| Help tidak buka PDF | PDF belum dibuat | Jalankan perintah di §7 |

---

## 7. Membuat ulang manual PDF

Dari folder yang berisi berkas manual (`.md`):

```text
python ../md_to_pdf_Force_Motion.py -i UserManual_Force_Motion_v1.0.08.md -o UserManual_Force_Motion_v1.0.08.pdf
```

Dependensi konversi:

```text
pip install markdown xhtml2pdf
```

---

## 8. Informasi lisensi dan kontak

© Copyright 2026 — BRIN / UNNES

Aplikasi ini dikembangkan untuk keperluan monitoring force dan motion pada atlet renang. Untuk pertanyaan teknis, hubungi tim pengembang di institusi terkait.

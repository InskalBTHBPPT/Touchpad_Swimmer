# Manual Pengguna — Swimmer Force and Motion Monitoring v1.0.08 (Executable)

Dokumen ini menjelaskan pemakaian **Swimmer Force and Motion Monitoring** versi **executable** v1.0.08 untuk memantau beban (force) dan orientasi (roll, pitch) perenang melalui koneksi serial USB, merekam data ke CSV, serta menganalisis rekaman dengan statistik ekstremum dan analisa FFT pada sinyal force.

**Berkas aplikasi:** `Swimmer_Force_Motion_Monitoring_v1.0.08.exe`  
**Tidak perlu Python** — cukup jalankan file `.exe` di Windows.

---

## 1. Persyaratan

| Komponen | Keterangan |
|----------|------------|
| Sistem | Windows 10/11 (64-bit) |
| Perangkat | Mikrokontroler / sensor yang mengirim **satu baris CSV per sampel** lewat USB serial (UTF-8) |
| Driver USB | Driver serial untuk chip USB-UART (mis. CH340, CP210x) — unduh dari produsen adapter/perangkat |

---

## 2. Instalasi dan menjalankan

1. Salin `Swimmer_Force_Motion_Monitoring_v1.0.08.exe` ke folder tujuan (mis. Desktop atau `C:\SwimmerMonitoring\`).
2. (Opsional) Salin manual PDF ini ke folder yang sama jika ingin dibaca di luar aplikasi.
3. **Double-click** file `.exe` untuk membuka aplikasi.
4. Saat pertama kali dijalankan, Windows Defender atau antivirus mungkin menampilkan peringatan — izinkan aplikasi jika Anda mempercayai sumber berkas.

**Penting:** Jangan pindahkan atau hapus folder `DataLog/` dan `DataStatistik/` setelah ada data rekaman — folder tersebut dibuat otomatis **di samping file `.exe`**.

---

## 3. Ringkasan antarmuka

Aplikasi memiliki **dua tab**:

| Tab | Fungsi |
|-----|--------|
| **Live** | Koneksi serial, plot waktu-nyata (jendela 10 detik), indikator baterai di header, rekaman CSV, konsol log |
| **Analisa** | Muat satu file CSV log, plot waktu penuh + marker min/max, FFT force, ekspor statistik |

Header jendela menampilkan judul aplikasi, **ikon baterai** (jika perangkat mengirim kolom ke-5), dan nomor versi.

Panel kiri tab Live memiliki tombol **About** dan **Help**. Tombol **Help** membuka manual PDF yang sudah di-bundle dalam aplikasi.

---

## 4. Tab Live

### 4.1 Koneksi serial

1. Pilih **Port** COM dari dropdown (tombol **⟳ Refresh** memperbarui daftar port).
2. Pilih **Baud** (default: `115200`).
3. Klik **▶ Connect** untuk membuka port serial.
4. Klik **■ Disconnect** untuk menutup koneksi (logging aktif akan dihentikan otomatis).

### 4.2 Info perenang

| Field | Keterangan |
|-------|------------|
| **Nama** | Nama atlet (default: `Atlet`); dipakai untuk nama file log |
| **Gaya** | Pilihan: Bebas, Dada, Punggung, Kupu-kupu, Monofin, Bifins |

### 4.3 Format data serial

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

### 4.4 Plot Live

Tiga grafik vertikal menampilkan **Force**, **Roll**, dan **Pitch** terhadap waktu:

- Sumbu X menampilkan jendela geser **10 detik** terakhir.
- Buffer data dibatasi oleh **Max Titik** (default 1000) sebagai safety cap.

### 4.5 Rekaman log (Start Log / Stop Log)

- **Start Log** hanya aktif setelah serial terhubung.
- File disimpan otomatis ke folder **`DataLog/`** (di samping `.exe`) dengan pola nama:

  `{Nama}_{Gaya}_{ddmmyy-HHMM}.csv`

- **Stop Log** menghentikan rekaman, men-flush buffer, dan menutup file.

Struktur file CSV:

1. Baris metadata: `Nama Perenang:`, `Gaya Renang:`, `Time:`
2. Header data: `TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)`
3. Baris data numerik (empat kolom)

### 4.6 Checkbox “TimeStamp CSV set to 0”

- **Default:** dicentang → waktu di CSV = timestamp serial **dikurangi** timestamp sampel terakhir saat Start Log ditekan.
- **Tidak dicentang:** waktu di CSV sama dengan nilai mentah dari perangkat.
- Plot Live selalu memakai waktu mentah dari serial.

### 4.7 Pengaturan plot

Field **Max Titik** mengatur batas maksimum titik di buffer internal (minimal 10). Klik **Terapkan** setelah mengubah nilai.

### 4.8 About dan Help

- **About** — dialog informasi aplikasi dan versi.
- **Help** — membuka manual PDF (`UserManual_Force_Motion_v1.0.08-e.pdf`) dari bundle aplikasi. Jika PDF tidak dapat dibuka, dialog menampilkan teks manual.

---

## 5. Tab Analisa

### 5.1 Muat CSV log

1. Klik **📂 Muat CSV Log...**
2. Pilih file dari folder `DataLog/` (di samping `.exe`) atau lokasi lain.
3. File harus memiliki metadata dan header data sesuai format rekaman Live (lihat §4.5).

Panel **Metadata** menampilkan nama perenang, gaya, waktu rekaman, dan jumlah sampel.

### 5.2 Plot waktu dan marker

Empat plot vertikal:

| Plot | Isi |
|------|-----|
| Force | Kurva force vs waktu + marker min (◇) dan max (△) |
| Roll | Kurva roll vs waktu + marker min/max |
| Pitch | Kurva pitch vs waktu + marker min/max |
| FFT Force | Spektrum frekuensi force (0–5 Hz) dengan garis puncak dominan |

### 5.3 Statistik ekstremum

Panel **Statistik Ekstremum** menampilkan Force Min/Max/Mean, Roll Min/Max, dan Pitch Min/Max. Nilai min/max disertai waktu kejadian (`@ X.XXs`).

### 5.4 Analisa FFT — Force

Perhitungan menggunakan **FFT** dengan window Hanning pada sinyal force:

| Metrik | Keterangan |
|--------|------------|
| Freq. Dominan | Frekuensi puncak spektrum (Hz) |
| Amplitudo Maks | Amplitudo pada frekuensi dominan (Kg) |
| Periode | Kecepatan balik frekuensi dominan (s) |
| Stroke Rate | Frekuensi dominan × 60 (SPM) |
| Bandwidth | Lebar setengah daya (-3 dB) di sekitar puncak (Hz) |
| RMS Force | Root mean square seluruh deret force (Kg) |

### 5.5 Simpan statistik

Tombol **💾 Simpan Statistik** menulis file ke folder **`DataStatistik/`** (di samping `.exe`):

- Nama: `<nama_file_csv>_DataStaistik.csv`
- Isi: metadata, tabel metrik, dan blok **Analisa FFT Force**

---

## 6. Struktur folder setelah pemakaian

```text
(folder tempat .exe)/
├── Swimmer_Force_Motion_Monitoring_v1.0.08.exe
├── UserManual_Force_Motion_v1.0.08-e.pdf   (opsional, salinan eksternal)
├── DataLog/                                 (dibuat otomatis)
└── DataStatistik/                           (dibuat otomatis)
```

---

## 7. Pemecahan masalah

| Gejala | Kemungkinan penyebab | Solusi |
|--------|---------------------|--------|
| Exe tidak terbuka | Antivirus memblokir | Tambahkan pengecualian; unduh ulang dari sumber tepercaya |
| Port tidak muncul | Driver USB belum terpasang | Pasang driver CH340/CP210x; klik Refresh |
| Connect gagal | Port dipakai aplikasi lain | Tutup Serial Monitor / aplikasi lain |
| Plot kosong | Format data salah | Pastikan 4 kolom numerik per baris, dipisah koma |
| Baterai tidak tampil | Perangkat tidak kirim kolom ke-5 | Normal; fitur opsional |
| Log tidak ditemukan | Exe dipindah tanpa folder data | Cari `DataLog/` di lokasi lama, atau rekam ulang |
| Help tidak buka PDF | Penampil PDF default bermasalah | Baca salinan PDF manual di folder yang sama dengan exe |

---

## 8. Informasi lisensi dan kontak

© Copyright 2026 — BRIN / UNNES

Aplikasi ini dikembangkan untuk keperluan monitoring force dan motion pada atlet renang. Untuk pertanyaan teknis, hubungi tim pengembang di institusi terkait.

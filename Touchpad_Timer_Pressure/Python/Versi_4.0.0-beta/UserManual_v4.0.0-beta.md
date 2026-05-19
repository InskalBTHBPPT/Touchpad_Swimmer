# User Manual — NI DAQ Monitor (Touchpad Swimmer)
**Versi:** 4.0.0-beta  
**File Aplikasi:** `Swimmer_Touchpad_Monitor_v4.0.0-beta.py`  
**Platform:** Windows 10/11  
**Terakhir diperbarui:** Mei 2026

---

## Daftar Isi

1. [Pendahuluan](#1-pendahuluan)
2. [Persyaratan Sistem](#2-persyaratan-sistem)
3. [Instalasi](#3-instalasi)
4. [Menjalankan Aplikasi](#4-menjalankan-aplikasi)
5. [Antarmuka Pengguna — Tab Live Data](#5-antarmuka-pengguna--tab-live-data)
6. [Info Perenang](#6-info-perenang)
7. [Konfigurasi Parameter](#7-konfigurasi-parameter)
8. [Memulai Akuisisi Data](#8-memulai-akuisisi-data)
9. [Rekaman Log CSV](#9-rekaman-log-csv)
10. [Tabel Hasil Deteksi](#10-tabel-hasil-deteksi)
11. [Penyimpanan Tabel ke CSV (Otomatis)](#11-penyimpanan-tabel-ke-csv-otomatis)
12. [Format File Output (dengan Metadata)](#12-format-file-output-dengan-metadata)
13. [Manajemen Default Parameter](#13-manajemen-default-parameter)
14. [Tema Tampilan](#14-tema-tampilan)
15. [Tab Analisa Data](#15-tab-analisa-data)
16. [Nilai Default Pabrik](#16-nilai-default-pabrik)
17. [Penjelasan Teknis Detektor](#17-penjelasan-teknis-detektor)
18. [Pemecahan Masalah](#18-pemecahan-masalah)

---

## 1. Pendahuluan

**NI DAQ Monitor Swimmer Touchpad Monitor v4.0.0-beta** adalah aplikasi desktop untuk **akuisisi dan analisis data** dari dua sensor touchpad (**Pad 1** / **Pad 2**) yang terhubung ke perangkat **NI Data Acquisition (NI-DAQ)**. Masing-masing touchpad dipasang pada **garis lintasan** kolam renang: satu di sisi **dekat blok start** dan satu di sisi **jauh** (ujung berlawanan pada lintasan yang sama), sehingga data merekam interaksi perenang di kedua titik tersebut.

Aplikasi membaca **tegangan keluaran** touchpad dari NI-DAQ, lalu pada jalur Live mengonversi data tersebut secara langsung menjadi **tekanan dalam kilogram (Kg)** menggunakan **faktor skala (Kg/Volt)**. Grafik Live, deteksi sentuhan, tabel hasil, dan CSV Log menggunakan nilai tekanan yang sudah diskalakan.

Aplikasi mendukung **pengujian touchpad perenang** (*swimmer touchpad testing*) dengan menggabungkan **kualitas sentuhan dan gaya dorong** (tekanan) serta **metrik waktu di lintasan**—misalnya **waktu antar-pad** (*split time*) dan analisis pasca-rekaman—sehingga relevan untuk evaluasi **timing race**, tempo putaran, dan latihan berulang, tidak hanya untuk mendeskripsikan fase dorong di satu titik. Fitur utama meliputi:

- Visualisasi tekanan real-time dua channel analog (AI0 & AI1) dalam Kg
- Deteksi sentuhan otomatis (Schmitt region: upper/lower trip, rata-rata di puncak ±100 sampel, hold 10 s)
- Pencatatan waktu dan tekanan setiap sentuhan ke tabel
- Ekspor data tekanan ke CSV dengan metadata perenang (Nama, Gaya, Jarak)
- Analisis data pasca-rekaman: overlay plot CSV Log dan analisis split time

**Perubahan utama v4.0.0-beta (detektor):**
- Masuk region saat tekanan **≥ threshold + hysteresis** (upper trip).
- Tutup region saat tekanan **≤ threshold − hysteresis** (lower trip, inklusif), atau **paksa tutup setelah 5 detik**.
- Tekanan tercatat = rata-rata hingga **201 sampel** (±100) di sekitar **puncak** dalam region.
- Waktu di tabel = saat **pertama** melewati upper trip.
- **Delay Time (hold) 10 detik** tetap: deteksi berikutnya hanya setelah hold selesai dan sinyal turun di bawah lower trip.

**Perubahan v3.1.0 (tetap berlaku):**
- Data Live dikonversi dari Volt ke Kg segera setelah pembacaan DAQ menggunakan nilai **Scale (Kg/Volt)** per channel.
- Threshold dan hysteresis tetap diinput/disimpan dalam Volt, tetapi dikonversi ke Kg saat runtime sebelum dibandingkan dengan data Live.
- CSV Log menggunakan header `timestamp_s,ai0_kg,ai1_kg` dan menyimpan data tekanan dalam Kg.
- Plot Live dan overlay CSV Log di tab Analisa menggunakan sumbu Y **Pressure (Kg)**.
- Loader CSV Log tab Analisa mengharapkan format header v3.1.0.

---

## 2. Persyaratan Sistem

| Komponen | Spesifikasi Minimum |
|---|---|
| OS | Windows 10 64-bit atau lebih baru |
| Python | 3.11 atau lebih baru |
| NI-DAQmx Driver | Direkomendasikan driver yang kompatibel dengan perangkat Anda (rilis NI yang didukung). **Sudah diuji dengan driver versi 20.0.** |
| RAM | 4 GB |
| Perangkat DAQ | NI DAQ (mis. NI USB-6009, NI USB-6210, dsb.) |

### Dependensi Python

```
PySide6 >= 6.5
pyqtgraph >= 0.13
numpy
nidaqmx
```

Instalasi dependensi:

```bash
pip install PySide6 pyqtgraph numpy nidaqmx
```

---

## 3. Instalasi

1. Install **NI-DAQmx driver** dari [halaman unduhan NI-DAQmx](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html#590033)
2. Install Python 3.11+
3. Install dependensi Python (lihat bagian 2)
4. Salin folder proyek ke direktori kerja Anda

Struktur folder:

```
Touchpad_Timer_Pressure/Python/
├── Versi_4.0.0-beta/
│   ├── Swimmer_Touchpad_Monitor_v4.0.0-beta.py ← File aplikasi utama
│   ├── config.json                             ← Konfigurasi tersimpan
│   ├── UserManual_v4.0.0-beta.md               ← Dokumen ini
│   ├── UserManual_v4.0.0-beta.pdf              ← Versi PDF dokumen ini
│   ├── DataLog/                                ← Folder default log CSV
│   └── DataTable/                              ← Folder default tabel CSV
```

---

## 4. Menjalankan Aplikasi

Buka terminal / command prompt, arahkan ke folder `Python/Versi_4.0.0-beta/`, lalu jalankan:

```bash
python Swimmer_Touchpad_Monitor_v4.0.0-beta.py
```

Atau klik dua kali file `Swimmer_Touchpad_Monitor_v4.0.0-beta.py` jika Python sudah terkait dengan ekstensi `.py`.

### Regenerasi PDF manual (opsional)

Dari folder `Python/Misc/`, setelah mengubah file `.md` ini:

```bash
pip install markdown xhtml2pdf
python md_to_pdf_xhtml2pdf.py -i ../Versi_4.0.0-beta/UserManual_v4.0.0-beta.md -o ../Versi_4.0.0-beta/UserManual_v4.0.0-beta.pdf
```

---

## 5. Antarmuka Pengguna — Tab Live Data

Tampilan aplikasi terdiri dari dua tab utama. Tab **Live Data** berisi:

```
┌──────────────────────────────────────────────────────────────────┐
│  [Live Data]  [Analisa Data]                                     │
├───────────────────────────┬──────────────────────────────────────┤
│   Panel Chart (kiri)      │   Panel Kontrol (kanan)              │
│                           │  ┌─ Info Perenang ─────────────────┐ │
│  ┌─ Channel AI 0 ──────┐  │  │ Nama: [________________]        │ │
│  │  [Graf real-time]   │  │  │ Gaya: [Bebas ▼]                 │ │
│  └─────────────────────┘  │  │ Jarak:[50m ▼]                   │ │
│                           │  └─────────────────────────────────┘ │
│  ┌─ Channel AI 1 ──────┐  │  ┌─ Export Log to CSV ─────────────┐ │
│  │  [Graf real-time]   │  │  │ ☑ Record CSV Log saat Start     │ │
│  └─────────────────────┘  │  │ Prefix: [Ahmad_Bebas_50m]       │ │
│                           │  │ Folder: [DataLog/]  […]         │ │
│  Status: Stopped          │  │ File:   Ahmad_Bebas_50m_xxx.csv │ │
│                           │  └─────────────────────────────────┘ │
│                           │  ┌─ Table ─────────────────────────┐ │
│                           │  │ Time Format: ● MM:SS.ss ○ Seconds│ │
│                           │  │ [Tabel Pad1      | Tabel Pad2]  │ │
│                           │  │ Folder: [DataTable/]  […]       │ │
│                           │  │ File: [prefix_table_..._session]│ │
│                           │  └─────────────────────────────────┘ │
│                           │  [▶▶▶▶▶▶▶▶  Start  ▶▶▶▶▶▶▶▶▶▶▶] │
│                           │  [⚙️ Set Parameter]  [🌙 Dark]     │
└───────────────────────────┴──────────────────────────────────────┘
```

---

## 6. Info Perenang

Group **Info Perenang** di panel kanan digunakan untuk mengidentifikasi sesi rekaman.

| Field | Keterangan |
|---|---|
| **Nama Perenang** | Input teks nama perenang |
| **Gaya Renang** | Dropdown: Bebas / Punggung / Dada / Kupu-kupu / Gaya Ganti |
| **Jarak** | Dropdown: pilihan jarak disesuaikan otomatis per gaya |

### Jarak Valid per Gaya

| Gaya | Jarak yang Tersedia |
|---|---|
| Bebas | 50m, 100m, 200m, 400m, 800m, 1500m |
| Punggung | 50m, 100m, 200m |
| Dada | 50m, 100m, 200m |
| Kupu-kupu | 50m, 100m, 200m |
| Gaya Ganti | 200m, 400m |

### Prefix CSV Otomatis

Saat Nama, Gaya, atau Jarak diubah, field **Prefix** pada group Export Log otomatis diperbarui:

```
[Ahmad] + [Bebas] + [100m]  →  Prefix: "Ahmad_Bebas_100m"
Nama file: Ahmad_Bebas_100m_20260509_183000.csv
```

---

## 7. Konfigurasi Parameter

Tekan tombol **⚙️ Set Parameter** untuk membuka jendela konfigurasi.

### 7.1 Parameter Setting

| Parameter | Keterangan | Nilai Default |
|---|---|---|
| **Device Ch 0** | Nama channel NI DAQ untuk Pad 1 | `Dev2/ai0` |
| **Device Ch 1** | Nama channel NI DAQ untuk Pad 2 | `Dev2/ai1` |
| **Rate (Hz)** | Frekuensi sampling | `500` Hz |
| **Buffer Size** | Ukuran buffer hardware | `100000` |
| **Samples / Loop** | Jumlah sampel per iterasi | `50` |
| **Terminal** | Mode koneksi terminal sensor | `DIFF` |
| **Input Range** | Rentang tegangan input | `±10 V` |
| **Timestamp Set** | Metode timestamp | `Manual (A)` |
| **Timestamp Display** | Format tampilan waktu | `Relative` |

**Mode Terminal:** `DIFF` / `RSE` / `NRSE`

### 7.2 Detector Parameters

| Parameter | Keterangan | Nilai Default |
|---|---|---|
| **Threshold (Volt)** | Ambang referensi deteksi (pusat Schmitt) | `0.05` V |
| **Hysteresis (Volt)** | Selisih untuk upper/lower trip | `0.005` V |
| **Scale (Kg/Volt)** | Faktor konversi tegangan → tekanan | `1.00` |
| **Delay Time (s)** | Waktu hold minimum (anti-debounce) | `10.0` detik |

> **Catatan:** Parameter detektor bisa diatur berbeda untuk Dev. 0 (Pad 1) dan Dev. 1 (Pad 2).
> Threshold dan Hysteresis dimasukkan sebagai Volt, lalu dikonversi ke Kg saat Start.
> Masuk region: **≥ threshold + hysteresis**; tutup/re-arm: **≤ / < threshold − hysteresis**.

### 7.3 Tombol di Jendela Set Parameter

| Tombol | Fungsi |
|---|---|
| **💾 Set As Default** | Simpan nilai saat ini ke `config.json` dan terapkan ke sistem |
| **↩ Reset to Saved** | Kembalikan nilai ke yang tersimpan di `config.json` |
| **↺ Reset to Factory** | Kembalikan nilai ke default pabrik hardcoded |
| **Apply** | Terapkan nilai ke sistem (dialog tetap terbuka) |
| **Cancel / ✕** | Tutup dialog tanpa perubahan |

---

## 8. Memulai Akuisisi Data

1. Isi **Info Perenang** (Nama, Gaya, Jarak)
2. Pastikan perangkat NI DAQ terhubung
3. Konfigurasi parameter via **⚙️ Set Parameter**
4. Pastikan **☑ Record CSV Log saat Start** tercentang (default: aktif)
5. Tekan **▶ Start** (berwarna hijau)
6. Grafik menampilkan tekanan real-time dalam Kg, status bar: `Status: Running`
7. Tekan **■ Stop** untuk menghentikan akuisisi

> **Penting:** Parameter tidak dapat diubah selama akuisisi berjalan.

---

## 9. Rekaman Log CSV

### Mengaktifkan Rekaman

1. Centang **☑ Record CSV Log saat Start**
2. Prefix nama file diisi otomatis dari Info Perenang
3. Pilih folder tujuan dengan tombol **[…]**
4. Nama file pratinjau ditampilkan di baris **File:**

### Format File Log CSV (dengan Metadata)

```csv
# Nama Perenang,Ahmad Syafii
# Gaya,Bebas
# Jarak,100m
# Tanggal,2026-05-09 18:30:00
timestamp_s,ai0_kg,ai1_kg
0.000000,0.123450,0.098760
0.002000,0.132100,0.101230
...
```

Baris dimulai dengan `#` adalah metadata — dapat diabaikan saat import ke pandas dengan parameter `comment='#'`. Kolom `ai0_kg` dan `ai1_kg` berisi data tekanan yang sudah dikalikan Scale, bukan tegangan mentah.

---

## 10. Tabel Hasil Deteksi

Setiap sentuhan yang terdeteksi dicatat otomatis di tabel:

| Kolom | Keterangan |
|---|---|
| **Time (Pad 1)** | Waktu saat tekanan pertama kali ≥ threshold + hysteresis (Pad 1) |
| **Press (Kg) Pad 1** | Rata-rata tekanan di ±100 sampel sekitar puncak regional (Kg) |
| **Time (Pad 2)** | Waktu saat tekanan pertama kali ≥ threshold + hysteresis (Pad 2) |
| **Press (Kg) Pad 2** | Rata-rata tekanan di ±100 sampel sekitar puncak regional (Kg) |

Tabel menampung **10 baris** per pad. Jika penuh, baris lama digeser ke atas.

### Format Waktu

- **MM:SS.ss** *(default)* — `00:12.34`
- **Seconds** — `12.345`

---

## 11. Penyimpanan Tabel ke CSV (Otomatis)

1. Pilih folder tujuan di baris **Folder:** pada group Table.
2. Aplikasi akan membuat file tabel sesi otomatis saat ada penambahan data sentuhan.
3. Nama file mengikuti pola: `[Prefix]_table_[timestamp]_session.csv`.
4. Saat tombol **■ Stop** ditekan, file tabel sesi ditulis ulang (final snapshot) lalu
   dialog ringkasan ditampilkan.

> **Catatan UI:** Tombol **💾 Save Table to CSV** saat ini disembunyikan dari antarmuka,
> namun fungsi internalnya tetap ada untuk kebutuhan aktivasi ulang di masa depan.

### Format File Tabel CSV (dengan Metadata)

```csv
# Nama Perenang,Ahmad Syafii
# Gaya,Bebas
# Jarak,100m
# Tanggal,2026-05-09 18:32:00
No,Time_Pad1,Pressure_Pad1(Kg),Time_Pad2,Pressure_Pad2(Kg)
1,15.848,4.1368,10.368,5.022
2,84.152,4.598,77.878,5.544
...
```

---

## 12. Format File Output (dengan Metadata)

### Log CSV (`DataLog/[Prefix]_YYYYMMDD_HHMMSS.csv`)

```csv
# Nama Perenang,Ahmad Syafii
# Gaya,Bebas
# Jarak,100m
# Tanggal,2026-05-09 18:30:00
timestamp_s,ai0_kg,ai1_kg
0.000000,0.1240,0.0890
```

### Tabel CSV Sesi (`DataTable/[Prefix]_table_YYYYMMDD_HHMMSS_session.csv`)

```csv
# Nama Perenang,Ahmad Syafii
# Gaya,Bebas
# Jarak,100m
# Tanggal,2026-05-09 18:32:00
No,Time_Pad1,Pressure_Pad1(Kg),Time_Pad2,Pressure_Pad2(Kg)
1,15.848,4.1368,10.368,5.022
```

### Membaca dengan pandas

```python
import pandas as pd

# Log CSV
df_log = pd.read_csv("Ahmad_Bebas_100m_20260509.csv", comment="#")

# Table CSV
df_table = pd.read_csv("Ahmad_Bebas_100m_table_20260509_183200_session.csv", comment="#")
```

---

## 13. Manajemen Default Parameter

Konfigurasi disimpan di **`config.json`** (folder Python/).

### Alur Kerja

```
Aplikasi Start
  └── config.json ada?  → Muat parameter dari config.json
                tidak?  → Gunakan nilai default pabrik (hardcoded)

[💾 Set As Default] ditekan
  └── Simpan nilai saat ini → config.json
      Terapkan ke sistem

[↩ Reset to Saved] ditekan
  └── Muat nilai dari config.json ke dialog (perlu tekan Apply untuk terapkan)

[↺ Reset to Factory] ditekan
  └── Muat nilai default pabrik ke dialog (perlu tekan Apply untuk terapkan)
```

---

## 14. Tema Tampilan

Tekan **☀️ Light** / **🌙 Dark** di sudut kanan bawah panel kontrol untuk beralih tema.

| Tema | Keterangan |
|---|---|
| **Dark** (default) | Latar gelap, cocok untuk ruangan redup |
| **Light** | Latar terang, cocok untuk ruangan terang |

---

## 15. Tab Analisa Data

Tab **Analisa Data** digunakan untuk memvisualisasikan dan menganalisis file CSV hasil rekaman sesi sebelumnya — tanpa perlu perangkat DAQ terhubung.

```
┌──────────────────────────────────────────────┬────────────────────────────┐
│  CSV Log Pressure Overlay (multi-file)       │  ┌─ CSV Log ─────────────┐ │
│                                              │  │ [📂 Load CSV Log]     │ │
│                                              │  │ ■■ file1.csv          │ │
│                                              │  │ Nama: Ahmad           │ │
│                                              │  │ Gaya: Bebas           │ │
├──────────────────────────────────────────────│  │ Jarak: 100m           │ │
│  Split Time & Tekanan per Sentuhan           │  └───────────────────────┘ │
│  ┌────────────────────────────────────────┐  │  ┌─ CSV Table ───────────┐ │
│  │ Δ Time (s) ↑        ↑ Pressure (Kg)   │  │  │ [📂 Load CSV Table]  │ │
│  │            │  biru/merah  □hijau/kuning│  │  │ file_table.csv        │ │
│  │            └────────────────────────── │  │  │ Nama: Ahmad           │ │
│  │            Sentuhan ke-                │  │  │ Gaya: Bebas           │ │
│  └────────────────────────────────────────┘  │  │ Jarak: 100m           │ │
│                                              │  │ ┌─ Data Table ──────┐ │ │
│                                              │  │ │ No|Pad1|Pad2|...  │ │ │
│                                              │  │ └───────────────────┘ │ │
│                                              │  └───────────────────────┘ │
│                                              │  [🗑 Clear All]            │
└──────────────────────────────────────────────┴────────────────────────────┘
```

### 15.1 Load CSV Log (Overlay)

1. Tekan **📂 Load CSV Log**
2. Pilih satu atau lebih file CSV Log
3. File harus memiliki header `timestamp_s,ai0_kg,ai1_kg`
4. Setiap file ditampilkan sebagai dua kurva pressure overlay:
   - **AI0** = tekanan Pad 1 dalam Kg
   - **AI1** = tekanan Pad 2 dalam Kg
5. Info Perenang dari file terakhir ditampilkan di panel kanan
6. Daftar file dimuat ditampilkan dengan kotak warna per file

### 15.2 Load CSV Table

1. Tekan **📂 Load CSV Table**
2. Pilih satu file CSV Table
3. Data ditampilkan di **Data Table** (panel kanan bawah)
4. Info Perenang terbaca dari metadata CSV
5. Plot **"Split Time & Tekanan per Sentuhan"** diperbarui otomatis

### 15.3 Plot Split Time & Tekanan per Sentuhan

Plot dual Y-axis yang menampilkan dua informasi dalam satu grafik:

**Sumbu X:** Nomor sentuhan (Sentuhan ke-)

**Sumbu Y Kiri (Δ Time):**
- ● **Biru** = sentuhan menuju Pad2 (dinding jauh / outbound)
- ● **Merah** = sentuhan menuju Pad1 (dinding start / return)
- Label dua baris per titik:
  - `t:xx.xxs` = waktu absolut dari awal rekaman
  - `dt:xx.xxs` = durasi split (waktu dari sentuhan sebelumnya)

**Sumbu Y Kanan (Pressure):**
- ■ **Hijau neon** = tekanan Pad1 (dinding start)
- ■ **Kuning** = tekanan Pad2 (dinding jauh)

**Algoritma Delta Time:**

```
Urutan event (diurutkan berdasarkan waktu):
  T[0] = t2[0]  (sentuhan Pad2 pertama)
  T[1] = t1[0]  (sentuhan Pad1 pertama)
  T[2] = t2[1]  (sentuhan Pad2 kedua)
  T[3] = t1[1]  (sentuhan Pad1 kedua)
  ...

Delta:
  dt[0] = T[0]            → waktu start ke Pad2 pertama (50m pertama)
  dt[k] = T[k] - T[k-1]  → durasi setiap segmen 50m berikutnya
```

> **Asumsi:** Perenang mulai dari jump block (bukan dari sentuhan Pad1). Pad2 berada di dinding jauh, Pad1 di dinding start.

### 15.4 Clear All

Tekan **🗑 Clear All** untuk menghapus semua data yang dimuat dan mereset seluruh plot.

---

## 16. Nilai Default Pabrik

| Parameter | Nilai Default |
|---|---|
| Device Ch 0 | `Dev2/ai0` |
| Device Ch 1 | `Dev2/ai1` |
| Rate | `500.0` Hz |
| Buffer Size | `100000` samples |
| Samples/Loop | `50` samples |
| Terminal | `DIFF` |
| Input Range | `±10 V` |
| Timestamp Set | `Manual (A)` |
| Timestamp Display | `Relative` |
| Threshold | `0.05` V |
| Hysteresis | `0.005` V |
| Scale | `1.00` Kg/V |
| Hold Time | `10.0` detik |
| Plot Window | `10.0` detik |
| Plot Refresh | `100` ms (~10 FPS) |
| Peak window (kode) | ±`100` sampel (hingga 201) di sekitar puncak |
| Maks durasi region (kode) | `5.0` detik |

---

## 17. Penjelasan Teknis Detektor

Detektor menggunakan **Schmitt dua ambang** + **region buffer** + state machine 3 kondisi:

```
         ┌──────────────┐  pressure_kg ≥ upper_trip (= threshold_kg + hysteresis_kg)
         │    ARMED     │ ─────────────────────────────────► IN_REGION
         └──────────────┘
               ▲
               │ hold_time selesai AND pressure_kg < lower_trip
         ┌──────────────┐                    ▼
         │     HOLD     │  ◄──────── IN_REGION: buffer sampel;
         └──────────────┘         tutup jika ≤ lower_trip ATAU ≥ 5 s;
                                  argmax → mean ±100 sampel → catat tabel
```

**Rumus runtime v4.0.0-beta:**
- `threshold_kg = threshold_volt × scale`
- `hysteresis_kg = hysteresis_volt × scale`
- `upper_trip_kg = threshold_kg + hysteresis_kg` — **masuk** region
- `lower_trip_kg = threshold_kg − hysteresis_kg` — **tutup** region & syarat re-arm
- `time_table = timestamp` sampel pertama `≥ upper_trip`
- `pressure = mean(buffer[j−100 : j+100])` dengan `j = argmax(buffer)` (dipotong di tepi region)
- Jika region > **5 detik** tanpa turun ke lower trip: region **dipaksa tutup** (tetap hitung pressure)

**Contoh pengaturan** untuk sensor 0.1 V/Kg dengan noise ±0.003 V:

| Parameter | Nilai | Alasan |
|---|---|---|
| Threshold | `0.05` V | Ambang referensi sentuhan |
| Hysteresis | `0.005` V | Upper trip 0,055 V; lower trip 0,045 V |
| Scale | `10.0` Kg/V | Konversi 1/sensitivitas |
| Hold Time | `10.0` s | Jarak minimum antar deteksi setelah region selesai |

---

## 18. Pemecahan Masalah

### Aplikasi tidak mau start

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| `ModuleNotFoundError: nidaqmx` | Package belum terinstal | `pip install nidaqmx` dan install NI-DAQmx driver |
| `ModuleNotFoundError: PySide6` | PySide6 belum terinstal | `pip install PySide6` |

### Error saat Start akuisisi

| Pesan Error | Kemungkinan Penyebab | Solusi |
|---|---|---|
| `DAQmx Error: Physical channel not found` | Nama channel salah | Cek nama device di NI MAX |
| `DAQmx Error: Requested operation is not supported` | Kombinasi terminal + range tidak valid | Ganti ke DIFF atau ubah Input Range |
| `Input tidak valid` | Nilai Rate / Buffer bukan angka | Perbaiki di Set Parameter |

### Data tidak terdeteksi di tabel

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| Sinyal tampil di grafik tapi tabel kosong | Threshold terlalu tinggi | Turunkan nilai Threshold |
| Deteksi terus-menerus | Hold Time terlalu kecil | Naikkan Hold Time (min. 5 detik) |
| Nilai tekanan tidak realistis | Scale salah | Kalibrasi dan sesuaikan Scale |

### Plot Analisa tidak tampil setelah Load CSV Table

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| Data Table kosong | File bukan format CSV Table yang benar | Gunakan file dari `DataTable/` |
| Plot delta kosong | Kolom Time_Pad1 / Time_Pad2 semua kosong | Pastikan akuisisi berjalan saat rekaman |

### Performa grafik lambat

- Kurangi **Rate (Hz)** (mis. dari 500 ke 200 Hz)
- Kurangi **Buffer Size**
- Tutup aplikasi lain yang berat

### config.json corrupt

Hapus file `config.json` dan jalankan ulang. Sistem akan menggunakan nilai default pabrik.

---

*Dokumen ini dibuat untuk `Swimmer_Touchpad_Monitor_v4.0.0-beta.py` — NI DAQ Monitor Touchpad Swimmer v4.0.0-beta*

# User Manual — NI DAQ Monitor (Touchpad Swimmer)
**Versi:** 3.0  
**File Aplikasi:** `GUI_v3.py`  
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
11. [Menyimpan Tabel ke CSV](#11-menyimpan-tabel-ke-csv)
12. [Format File Output (dengan Metadata)](#12-format-file-output-dengan-metadata)
13. [Manajemen Default Parameter](#13-manajemen-default-parameter)
14. [Tema Tampilan](#14-tema-tampilan)
15. [Tab Analisa Data](#15-tab-analisa-data)
16. [Nilai Default Pabrik](#16-nilai-default-pabrik)
17. [Penjelasan Teknis Detektor](#17-penjelasan-teknis-detektor)
18. [Pemecahan Masalah](#18-pemecahan-masalah)

---

## 1. Pendahuluan

**NI DAQ Monitor v3** adalah aplikasi desktop untuk akuisisi dan analisis data tekanan secara real-time dari dua sensor touchpad (Pad 1 / Pad 2) yang terhubung ke perangkat **NI Data Acquisition (NI DAQ)**.

Aplikasi dirancang untuk pengujian gaya dorong perenang (*swimmer touchpad testing*) dengan fitur utama:

- Visualisasi tegangan real-time dua channel analog (AI0 & AI1)
- Deteksi sentuhan otomatis menggunakan algoritma Schmitt trigger
- Pencatatan waktu dan tekanan setiap sentuhan ke tabel
- Ekspor data ke CSV dengan metadata perenang (Nama, Gaya, Jarak)
- Analisis data pasca-rekaman: overlay plot CSV Log dan analisis split time

**Perubahan dari v2.0:**
- Penambahan input Info Perenang (Nama, Gaya, Jarak) sebagai prefix CSV
- Metadata perenang ditulis di header CSV untuk traceability
- Antarmuka bertab: **Live Data** dan **Analisa Data**
- Tab Analisa Data untuk visualisasi dan analisis file CSV hasil rekaman

---

## 2. Persyaratan Sistem

| Komponen | Spesifikasi Minimum |
|---|---|
| OS | Windows 10 64-bit atau lebih baru |
| Python | 3.11 atau lebih baru |
| NI-DAQmx Driver | 21.0 atau lebih baru |
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

1. Install **NI-DAQmx driver** dari [ni.com/downloads](https://www.ni.com/downloads)
2. Install Python 3.11+
3. Install dependensi Python (lihat bagian 2)
4. Salin folder proyek ke direktori kerja Anda

Struktur folder:

```
Touchpad_Swimmer/
├── Python/
│   ├── GUI_v3.py              ← File aplikasi utama
│   ├── config.json            ← Konfigurasi tersimpan (dibuat otomatis)
│   ├── UserManual_v3.md       ← Dokumen ini
│   ├── UserManual_v3.pdf      ← Versi PDF dokumen ini
│   ├── DataLog/               ← Folder default log CSV
│   └── DataTable/             ← Folder default tabel CSV
```

---

## 4. Menjalankan Aplikasi

Buka terminal / command prompt, arahkan ke folder `Python/`, lalu jalankan:

```bash
python GUI_v3.py
```

Atau klik dua kali file `GUI_v3.py` jika Python sudah terkait dengan ekstensi `.py`.

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
│  │  [Graf real-time]   │  │  │ ☑ Record CSV saat Start         │ │
│  └─────────────────────┘  │  │ Prefix: [Ahmad_Bebas_50m]       │ │
│                           │  │ Folder: [DataLog/]  […]         │ │
│  Status: Stopped          │  │ File:   Ahmad_Bebas_50m_xxx.csv │ │
│                           │  └─────────────────────────────────┘ │
│                           │  [▶▶▶▶▶▶▶▶  Start  ▶▶▶▶▶▶▶▶▶▶▶] │
│                           │  ┌─ Table ─────────────────────────┐ │
│                           │  │ Time Format: ○ Seconds ○ MM:SS  │ │
│                           │  │ [Tabel Pad1      | Tabel Pad2]  │ │
│                           │  │ Folder: [DataTable/]  […]       │ │
│                           │  │ [💾 Save Table to CSV]          │ │
│                           │  └─────────────────────────────────┘ │
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
| **Threshold (Volt)** | Tegangan minimum untuk memulai deteksi | `0.05` V |
| **Hysteresis (Volt)** | Selisih threshold untuk re-arm | `0.005` V |
| **Scale (Kg/Volt)** | Faktor konversi tegangan → tekanan | `1.00` |
| **Delay Time (s)** | Waktu hold minimum (anti-debounce) | `10.0` detik |

> **Catatan:** Parameter detektor bisa diatur berbeda untuk Dev. 0 (Pad 1) dan Dev. 1 (Pad 2).

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
4. Pastikan **☑ Record CSV saat Start** tercentang (default: aktif)
5. Tekan **▶ Start** (berwarna hijau)
6. Grafik menampilkan data real-time, status bar: `Status: Running`
7. Tekan **■ Stop** untuk menghentikan akuisisi

> **Penting:** Parameter tidak dapat diubah selama akuisisi berjalan.

---

## 9. Rekaman Log CSV

### Mengaktifkan Rekaman

1. Centang **☑ Record CSV saat Start**
2. Prefix nama file diisi otomatis dari Info Perenang
3. Pilih folder tujuan dengan tombol **[…]**
4. Nama file pratinjau ditampilkan di baris **File:**

### Format File Log CSV (dengan Metadata)

```csv
# Nama Perenang,Ahmad Syafii
# Gaya,Bebas
# Jarak,100m
# Tanggal,2026-05-09 18:30:00
timestamp_s,ai0_V,ai1_V
0.000000,0.012345,0.009876
0.002000,0.013210,0.010123
...
```

Baris dimulai dengan `#` adalah metadata — dapat diabaikan saat import ke pandas dengan parameter `comment='#'`.

---

## 10. Tabel Hasil Deteksi

Setiap sentuhan yang terdeteksi dicatat otomatis di tabel:

| Kolom | Keterangan |
|---|---|
| **Time (Pad 1)** | Waktu saat sentuhan Pad 1 terdeteksi |
| **Press (Kg) Pad 1** | Nilai tekanan Pad 1 (rata-rata 50 sampel × Scale) |
| **Time (Pad 2)** | Waktu saat sentuhan Pad 2 terdeteksi |
| **Press (Kg) Pad 2** | Nilai tekanan Pad 2 |

Tabel menampung **10 baris** per pad. Jika penuh, baris lama digeser ke atas.

### Format Waktu

- **Seconds** — `12.345`
- **MM:SS.sss** — `00:12.345`

---

## 11. Menyimpan Tabel ke CSV

1. Pilih folder tujuan di baris **Folder:** dalam group Table
2. Tekan **💾 Save Table to CSV**
3. File disimpan: `[Prefix]_table_[timestamp].csv`

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
timestamp_s,ai0_V,ai1_V
0.000000,0.0124,0.0089
```

### Tabel CSV (`DataTable/[Prefix]_table_YYYYMMDD_HHMMSS.csv`)

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
df_table = pd.read_csv("Ahmad_Bebas_100m_table_20260509.csv", comment="#")
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
│  CSV Log Overlay (plot overlay multi-file)   │  ┌─ CSV Log ─────────────┐ │
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
3. Setiap file ditampilkan sebagai dua kurva overlay:
   - **AI0** = warna solid
   - **AI1** = warna berbeda (pasangan warna per file)
4. Info Perenang dari file terakhir ditampilkan di panel kanan
5. Daftar file dimuat ditampilkan dengan kotak warna per file

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
| Sampel Averaging | `50` sampel |

---

## 17. Penjelasan Teknis Detektor

Detektor menggunakan algoritma **Schmitt Trigger** dengan state machine 3 kondisi:

```
         ┌──────────────┐  sinyal ≥ (threshold − hysteresis)
         │    ARMED     │ ─────────────────────────────────► COLLECTING
         └──────────────┘
               ▲
               │ hold_time selesai AND sinyal < lower_trip
         ┌──────────────┐                    ▼
         │     HOLD     │  ◄──────── COLLECTING: kumpulkan n sampel
         └──────────────┘         lalu hitung rata-rata → hasil deteksi
```

**Rumus:**
- `lower_trip = threshold − hysteresis`
- `pressure = rata-rata(n_collect sampel) × scale`

**Contoh pengaturan** untuk sensor 0.1 V/Kg dengan noise ±0.003 V:

| Parameter | Nilai | Alasan |
|---|---|---|
| Threshold | `0.05` V | Tegangan minimum sentuhan valid |
| Hysteresis | `0.005` V | Lebih besar dari noise (0.003 V) |
| Scale | `10.0` Kg/V | Konversi 1/sensitivitas |
| Hold Time | `10.0` s | Waktu minimum antar sentuhan |

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

*Dokumen ini dibuat untuk GUI_v3.py — NI DAQ Monitor Touchpad Swimmer v3.0*

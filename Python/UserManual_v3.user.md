# User Manual — NI DAQ Monitor (Touchpad Swimmer) — **User Edition**
**Versi:** 3.0-user  
**File Aplikasi:** `GUI_v3.user.py`  
**Platform:** Windows 10/11  
**Terakhir diperbarui:** Mei 2026  

Edisi ini mendokumentasikan **GUI_v3.user.py** (mode operator/perenang). Untuk versi riset/tester lengkap dengan grafik live dan pengaturan parameter dari antarmuka, gunakan `GUI_v3.py` dan `UserManual_v3.md`.

---

## Daftar Isi

1. [Pendahuluan](#1-pendahuluan)
2. [Persyaratan Sistem](#2-persyaratan-sistem)
3. [Instalasi](#3-instalasi)
4. [Menjalankan Aplikasi](#4-menjalankan-aplikasi)
5. [Antarmuka Pengguna — Tab Live Data](#5-antarmuka-pengguna--tab-live-data)
6. [Info Perenang](#6-info-perenang)
7. [Konfigurasi Parameter (file config.json)](#7-konfigurasi-parameter-file-configjson)
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

**NI DAQ Monitor v3 — User Edition** adalah aplikasi desktop untuk akuisisi dan analisis data tekanan secara real-time dari dua sensor touchpad (Pad 1 / Pad 2) yang terhubung ke perangkat **NI Data Acquisition (NI DAQ)**.

Aplikasi dirancang untuk pengujian gaya dorong perenang (*swimmer touchpad testing*) dengan fitur utama:

- **Tanpa grafik tegangan real-time di tab Live Data** — fokus pada tabel deteksi dan split time (ringkas, mudah dibaca di kolam)
- Deteksi sentuhan otomatis menggunakan algoritma Schmitt trigger
- Pencatatan waktu dan tekanan setiap sentuhan ke tabel; **tabel Split Time** di tab Live untuk urutan sentuhan
- Ekspor data ke CSV dengan metadata perenang (Nama, Gaya, Jarak)
- Analisis pasca-rekaman di tab **Analisa Data**: overlay CSV Log, plot split time & tekanan

**Karakteristik User Edition (dibanding `GUI_v3.py`):**
- Parameter DAQ dan detektor **tidak dapat diubah dari antarmuka** — nilai diambil dari `config.json` yang disiapkan tim riset/uji.
- Tombol **Set Parameter** tidak ditampilkan.
- Tab **Live Data** menempatkan **tabel hasil deteksi** dan **Split Time** pada area utama (lebih lebar).

**Perubahan dari v2.0 (warisan bersama v3):**
- Input Info Perenang (Nama, Gaya, Jarak) sebagai prefix CSV
- Metadata perenang di header CSV
- Antarmuka bertab: **Live Data** dan **Analisa Data**

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

1. Install **NI-DAQmx driver** dari [halaman unduhan NI-DAQmx](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html#590033)
2. Install Python 3.11+
3. Install dependensi Python (lihat bagian 2)
4. Salin folder proyek ke direktori kerja Anda

Struktur folder:

```
Touchpad_Swimmer/
├── Python/
│   ├── GUI_v3.user.py         ← File aplikasi utama (User Edition)
│   ├── config.json            ← Parameter DAQ/detektor (disiapkan tim / dari instalasi)
│   ├── UserManual_v3.user.md  ← Dokumen ini
│   ├── UserManual_v3.user.pdf ← Versi PDF (hasil generate; lihat skrip di repo)
│   ├── DataLog/               ← Folder default log CSV
│   └── DataTable/             ← Folder default tabel CSV
```

---

## 4. Menjalankan Aplikasi

Buka terminal / command prompt, arahkan ke folder `Python/`, lalu jalankan:

```bash
python GUI_v3.user.py
```

Atau klik dua kali file `GUI_v3.user.py` jika Python sudah terkait dengan ekstensi `.py`.

---

## 5. Antarmuka Pengguna — Tab Live Data

Tampilan aplikasi terdiri dari dua tab utama. Pada **User Edition**, tab **Live Data** **tidak menampilkan grafik** AI0/AI1; yang ditampilkan adalah status, **tabel Pad Detection**, **tabel Split Time** (live), serta kontrol di panel kanan.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  [Live Data]  [Analisa Data]                                               │
├─────────────────────────────────────────────┬──────────────────────────────┤
│  Status: Stopped                            │  ┌─ Info Perenang ─────────┐ │
│  ┌─ Table ────────┐  ┌─ Split Time ──────┐  │  │ Nama / Gaya / Jarak    │ │
│  │ Pad 1 | Pad 2  │  │ 50m ke- Touchpad  │  │  └────────────────────────┘ │
│  │ Time  Press    │  │ t(s)   Δt(s)      │  │  ┌─ Export Log to CSV ─────┐ │
│  │ ...            │  │ ...               │  │  │ ☑ Record · Prefix · …   │ │
│  └────────────────┘  └───────────────────┘  │  └────────────────────────┘ │
│  Folder: [DataTable/] […]  [💾 Save Table]   │  [▶ Start / ■ Stop]          │
│                                             │  [🌙 / ☀️ Tema]              │
└─────────────────────────────────────────────┴──────────────────────────────┘
```

Header tabel Pad Detection memakai **dua baris**: baris pertama menggabungkan judul **Pad 1** dan **Pad 2** (masing-masing dua kolom); baris kedua **Time** dan **Press (Kg)** per pad — sama seperti struktur di tab Analisa saat memuat **CSV Table** (ditambah kolom **No** di Analisa).

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

## 7. Konfigurasi Parameter (file `config.json`)

Pada **User Edition**, pengguna **tidak** membuka dialog pengaturan di aplikasi. Semua parameter teknis DAQ dan detektor dibaca dari file **`config.json`** di folder yang sama dengan `GUI_v3.user.py` saat aplikasi dimulai.

- Jika `config.json` **ada** → nilai di dalamnya dipakai.
- Jika **tidak ada** atau bermasalah → aplikasi memakai **nilai default pabrik** (hardcoded).

Untuk mengubah channel DAQ, sampling rate, threshold, skala Kg/Volt, dan lainnya, mintakan tim riset/uji untuk menyediakan atau mengedit `config.json` yang sesuai perangkat Anda.

### 7.1 Referensi Parameter Setting

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

### 7.2 Referensi Detector Parameters

| Parameter | Keterangan | Nilai Default |
|---|---|---|
| **Threshold (Volt)** | Tegangan minimum untuk memulai deteksi | `0.05` V |
| **Hysteresis (Volt)** | Selisih threshold untuk re-arm | `0.005` V |
| **Scale (Kg/Volt)** | Faktor konversi tegangan → tekanan | `1.00` |
| **Delay Time (s)** | Waktu hold minimum (anti-debounce) | `10.0` detik |

> **Catatan:** Nilai detektor dapat dibedakan untuk Pad 1 dan Pad 2 melalui struktur di `config.json` (sesuai versi aplikasi yang Anda pakai).

---

## 8. Memulai Akuisisi Data

1. Isi **Info Perenang** (Nama, Gaya, Jarak)
2. Pastikan perangkat NI DAQ terhubung dan `config.json` sudah sesuai (disiapkan tim)
3. Pastikan **☑ Record CSV saat Start** tercentang jika Anda ingin log otomatis (default: aktif)
4. Tekan **▶ Start** (berwarna hijau)
5. Pantau **Status** dan isi **tabel Pad Detection** serta **Split Time**; tidak ada grafik live di edisi ini
6. Tekan **■ Stop** untuk menghentikan akuisisi

> **Penting:** Parameter DAQ/detektor tidak dapat diubah dari aplikasi selama sesi (dan umumnya hanya lewat `config.json` + restart).

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

Pada User Edition, satu-satunya sumber konfigurasi persisten untuk parameter teknis adalah file **`config.json`** di folder aplikasi.

### Alur Kerja

```
Aplikasi Start
  └── config.json ada dan valid?  → Muat parameter dari config.json
                          tidak?   → Gunakan nilai default pabrik (hardcoded)
```

Pengguna akhir biasanya **tidak** mengedit file ini; tim teknis menyalin file yang sudah dikalibrasi untuk perangkat/kolam Anda. Jika file rusak atau salah format, hapus `config.json` dan jalankan ulang aplikasi — sistem akan kembali ke default pabrik (atau mintakan file baru ke tim uji).

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
│                                              │  │ │ No + header 2 brs │ │ │
│                                              │  │ │ (spt tab Live)    │ │ │
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
3. Data ditampilkan di **Data Table** (panel kanan bawah). Header tabel mengikuti **tab Live**: baris pertama **No** (merge vertikal), **Pad 1**, **Pad 2**; baris kedua **Time** / **Press (Kg)** untuk masing-masing pad — konsisten dengan tampilan Pad Detection di lapangan.
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
| `Input tidak valid` | Nilai di `config.json` tidak valid | Mintakan file `config.json` yang benar ke tim teknis |

### Data tidak terdeteksi di tabel

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| Akuisisi jalan (status Running) tetapi tabel kosong | Threshold terlalu tinggi di `config.json` | Mintakan penyesuaian threshold/hold time ke tim teknis |
| Deteksi terus-menerus | Hold Time terlalu kecil | Sesuaikan hold time di `config.json` |
| Nilai tekanan tidak realistis | Scale salah | Kalibrasi dan sesuaikan Scale di `config.json` |

### Plot Analisa tidak tampil setelah Load CSV Table

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| Data Table kosong | File bukan format CSV Table yang benar | Gunakan file dari `DataTable/` |
| Plot delta kosong | Kolom Time_Pad1 / Time_Pad2 semua kosong | Pastikan akuisisi berjalan saat rekaman |

### Performa PC terasa berat

- Tutup aplikasi lain yang berat
- Tim teknis dapat menurunkan **Rate (Hz)** atau **Buffer Size** di `config.json` jika perlu

### config.json corrupt

Hapus file `config.json` dan jalankan ulang. Sistem akan menggunakan nilai default pabrik.

---

*Dokumen ini dibuat untuk `GUI_v3.user.py` — NI DAQ Monitor Touchpad Swimmer **v3.0-user***  

**PDF:** `UserManual_v3.user.pdf` dapat dibuat dari `UserManual_v3.user.md` dengan skrip `Python/md_to_pdf_xhtml2pdf.py` (memakai paket **Markdown** + **xhtml2pdf**).

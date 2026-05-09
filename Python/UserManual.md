# User Manual — NI DAQ Monitor (Touchpad Swimmer)
**Versi:** 2.0  
**Platform:** Windows 10/11  
**Terakhir diperbarui:** Mei 2026

---

## Daftar Isi

1. [Pendahuluan](#1-pendahuluan)
2. [Persyaratan Sistem](#2-persyaratan-sistem)
3. [Instalasi](#3-instalasi)
4. [Menjalankan Aplikasi](#4-menjalankan-aplikasi)
5. [Antarmuka Pengguna](#5-antarmuka-pengguna)
6. [Konfigurasi Parameter](#6-konfigurasi-parameter)
7. [Memulai Akuisisi Data](#7-memulai-akuisisi-data)
8. [Rekaman Log CSV](#8-rekaman-log-csv)
9. [Tabel Hasil Deteksi](#9-tabel-hasil-deteksi)
10. [Menyimpan Tabel ke CSV](#10-menyimpan-tabel-ke-csv)
11. [Manajemen Default Parameter](#11-manajemen-default-parameter)
12. [Tema Tampilan](#12-tema-tampilan)
13. [Nilai Default Pabrik](#13-nilai-default-pabrik)
14. [Penjelasan Teknis Detektor](#14-penjelasan-teknis-detektor)
15. [Format File Output](#15-format-file-output)
16. [Pemecahan Masalah](#16-pemecahan-masalah)

---

## 1. Pendahuluan

**NI DAQ Monitor** adalah aplikasi desktop untuk akuisisi dan analisis data tekanan secara real-time dari dua sensor touchpad (Pad 1 / Pad 2) yang terhubung ke perangkat **NI Data Acquisition (NI DAQ)**.

Aplikasi ini dirancang untuk pengujian gaya dorong perenang (*swimmer touchpad testing*) dengan fitur:

- Visualisasi tegangan real-time dua channel analog (AI0 & AI1)
- Deteksi sentuhan otomatis menggunakan algoritma Schmitt trigger
- Pencatatan waktu dan tekanan setiap sentuhan ke tabel
- Ekspor data ke file CSV (log mentah dan tabel ringkas)
- Penyimpanan konfigurasi pengguna secara persisten

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
│   ├── GUI_v2.0.py        ← File aplikasi utama
│   ├── config.json        ← Konfigurasi tersimpan (dibuat otomatis)
│   ├── UserManual.md      ← Dokumen ini
│   ├── DataLog/           ← Folder default log CSV
│   └── DataTable/         ← Folder default tabel CSV
```

---

## 4. Menjalankan Aplikasi

Buka terminal / command prompt, arahkan ke folder `Python/`, lalu jalankan:

```bash
python GUI_v2.0.py
```

Atau klik dua kali file `GUI_v2.0.py` jika Python sudah terkait dengan ekstensi `.py`.

---

## 5. Antarmuka Pengguna

Tampilan aplikasi terdiri dari dua area utama:

```
┌──────────────────────────────────────────────────────────────┐
│                   NI DAQ Monitor                             │
├───────────────────────────┬──────────────────────────────────┤
│   Panel Chart (tengah)    │   Panel Kontrol (kanan)          │
│                           │  ┌─ Export Log to CSV ─────────┐ │
│  ┌─ Channel AI 0 ──────┐  │  │  ☐ Record CSV saat Start    │ │
│  │  [Graf real-time]   │  │  │  Prefix: [__________]       │ │
│  └─────────────────────┘  │  │  Folder: [__________] […]   │ │
│                           │  │  File:   Swimming_xxx.csv   │ │
│  ┌─ Channel AI 1 ──────┐  │  └─────────────────────────────┘ │
│  │  [Graf real-time]   │  │  [▶▶▶▶▶  Start  ▶▶▶▶▶▶▶▶▶▶] │
│  └─────────────────────┘  │  ┌─ Table ─────────────────────┐ │
│                           │  │  Time Format: ○ Sec ○ MM:SS │ │
│  Status: Stopped          │  │  [Tabel Pad1 | Tabel Pad2]  │ │
│                           │  │  Folder: [__________] […]   │ │
│                           │  │  [💾 Save Table to CSV]     │ │
│                           │  └─────────────────────────────┘ │
│                           │  [⚙️ Set Parameter] [☀️ Light] │
└───────────────────────────┴──────────────────────────────────┘
```

### Komponen Panel Chart

| Komponen | Keterangan |
|---|---|
| **Channel AI 0** | Grafik real-time tegangan Pad 1 (10 detik terakhir) |
| **Channel AI 1** | Grafik real-time tegangan Pad 2 (10 detik terakhir) |
| **Status Bar** | Status sistem: Stopped / Running / Error |

> **Tip:** Sumbu X kedua grafik tersinkronisasi. Zoom atau pan salah satu akan menggerakkan keduanya.

---

## 6. Konfigurasi Parameter

Tekan tombol **⚙️ Set Parameter** untuk membuka jendela konfigurasi.

### 6.1 Parameter Setting

| Parameter | Keterangan | Nilai Default |
|---|---|---|
| **Device Ch 0** | Nama channel NI DAQ untuk Pad 1 | `Dev2/ai0` |
| **Device Ch 1** | Nama channel NI DAQ untuk Pad 2 | `Dev2/ai1` |
| **Rate (Hz)** | Frekuensi sampling | `500` Hz |
| **Buffer Size** | Ukuran buffer hardware (samples/channel) | `100000` |
| **Samples / Loop** | Jumlah sampel yang dibaca per iterasi | `50` |
| **Terminal** | Mode koneksi terminal sensor | `DIFF` |
| **Input Range** | Rentang tegangan input | `±10 V` |
| **Timestamp Set** | Metode timestamp (Manual / Waveform) | `Manual (A)` |
| **Timestamp Display** | Format tampilan waktu di terminal | `Relative` |

**Mode Terminal:**
- `DIFF` (Differential) — Lebih tahan noise, cocok untuk sinyal lemah
- `RSE` (Referenced Single-Ended) — Ground mengacu ke AIGND
- `NRSE` (Non-Referenced Single-Ended) — Ground mengacu ke AISENSE

**Input Range (mode DIFF):** ±1 V / ±1.25 V / ±2 V / ±2.5 V / ±4 V / ±5 V / ±10 V / ±20 V  
**Input Range (RSE/NRSE):** ±10 V (tetap)

### 6.2 Detector Parameters

Parameter detektor mengontrol kapan sentuhan Pad dianggap valid.

| Parameter | Keterangan | Nilai Default |
|---|---|---|
| **Threshold (Volt)** | Tegangan minimum untuk memulai deteksi | `0.05` V |
| **Hysteresis (Volt)** | Selisih threshold untuk re-arm | `0.005` V |
| **Scale (Kg/Volt)** | Faktor konversi tegangan → tekanan | `1.00` |
| **Delay Time (s)** | Waktu hold minimum (anti-debounce) | `10.0` detik |

> **Catatan:** Parameter detektor bisa diatur berbeda untuk Dev. 0 (Pad 1) dan Dev. 1 (Pad 2).

### 6.3 Tombol di Jendela Set Parameter

| Tombol | Fungsi |
|---|---|
| **💾 Set As Default** | Simpan nilai saat ini ke `config.json` dan terapkan ke sistem |
| **↩ Reset to Saved** | Kembalikan nilai ke yang tersimpan di `config.json` |
| **↺ Reset to Factory** | Kembalikan nilai ke default pabrik hardcoded |
| **Apply** | Terapkan nilai yang diubah ke sistem (dialog tetap terbuka) |
| **Cancel / ✕** | Tutup dialog tanpa perubahan |

> **Catatan:** Tombol **Reset to Saved** akan berwarna abu-abu (disabled) jika `config.json` belum pernah dibuat.

---

## 7. Memulai Akuisisi Data

1. Pastikan perangkat NI DAQ terhubung ke komputer
2. Konfigurasi parameter sesuai kebutuhan via **⚙️ Set Parameter**
3. Tekan tombol **▶ Start** (berwarna hijau)
4. Grafik mulai menampilkan data real-time
5. Status bar menampilkan: `Status: Running`
6. Tekan **■ Stop** (berwarna merah) untuk menghentikan akuisisi

> **Penting:** Parameter tidak dapat diubah selama akuisisi berjalan. Hentikan akuisisi terlebih dahulu.

---

## 8. Rekaman Log CSV

### Mengaktifkan Rekaman

1. Centang **☐ Record CSV saat Start** sebelum menekan Start
2. Ubah **Prefix** nama file jika perlu (default: `Swimming`)
3. Pilih folder tujuan dengan tombol **[…]**
4. Nama file ditampilkan di baris **File:** (mis. `Swimming_20260509_170057.csv`)

### Format File Log CSV

Setiap sesi akuisisi menghasilkan satu file CSV dengan format:

```
timestamp_s,ai0_V,ai1_V
0.000000,0.012345,0.009876
0.002000,0.013210,0.010123
...
```

| Kolom | Keterangan |
|---|---|
| `timestamp_s` | Waktu relatif dari start akuisisi (detik) |
| `ai0_V` | Tegangan Channel AI0 / Pad 1 (Volt) |
| `ai1_V` | Tegangan Channel AI1 / Pad 2 (Volt) |

---

## 9. Tabel Hasil Deteksi

Selama akuisisi berjalan, setiap sentuhan yang terdeteksi akan otomatis dicatat di tabel:

| Kolom | Keterangan |
|---|---|
| **Time (Pad 1)** | Waktu saat sentuhan Pad 1 terdeteksi |
| **Press (Kg) Pad 1** | Nilai tekanan Pad 1 (rata-rata 50 sampel × Scale) |
| **Time (Pad 2)** | Waktu saat sentuhan Pad 2 terdeteksi |
| **Press (Kg) Pad 2** | Nilai tekanan Pad 2 |

Tabel menampung **10 baris** per pad. Jika penuh, baris lama otomatis digeser ke atas (*scroll up*) agar data terbaru selalu terlihat.

### Format Waktu

Gunakan radio button di atas tabel untuk mengubah format:

- **Seconds** — Waktu dalam detik (mis. `12.345`)
- **MM:SS.sss** — Format menit:detik.milidetik (mis. `00:12.345`)

> Format dapat diubah kapan saja, termasuk saat akuisisi berjalan.

---

## 10. Menyimpan Tabel ke CSV

1. Pilih folder tujuan di baris **Folder:** dalam group Table
2. Tekan **💾 Save Table to CSV**
3. File disimpan dengan nama: `[Prefix]_table_[timestamp].csv`

### Format File Tabel CSV

```
No,Time_Pad1,Pressure_Pad1(Kg),Time_Pad2,Pressure_Pad2(Kg)
1,0.520,0.0523,,
2,1.034,0.0511,1.035,0.0498
...
```

---

## 11. Manajemen Default Parameter

Konfigurasi parameter disimpan secara persisten di file **`config.json`** di folder yang sama dengan script.

### Alur Kerja

```
Aplikasi Start
  └── config.json ada?  → Muat parameter dari config.json
                tidak?  → Gunakan nilai default pabrik (hardcoded)

[💾 Set As Default] ditekan
  └── Simpan nilai saat ini → config.json
      Terapkan ke sistem
      Aktifkan tombol [↩ Reset to Saved]

[↩ Reset to Saved] ditekan
  └── Muat nilai dari config.json ke dialog
      (belum diterapkan ke sistem — perlu tekan Apply)

[↺ Reset to Factory] ditekan
  └── Muat nilai default pabrik ke dialog
      (belum diterapkan ke sistem — perlu tekan Apply)
```

> **config.json** dapat diedit secara manual menggunakan teks editor jika diperlukan.

---

## 12. Tema Tampilan

Tekan tombol **☀️ Light** / **🌙 Dark** di sudut kanan bawah untuk beralih tema.

| Tema | Keterangan |
|---|---|
| **Dark** (default) | Latar belakang gelap, cocok untuk ruangan redup |
| **Light** | Latar belakang terang, cocok untuk ruangan terang |

---

## 13. Nilai Default Pabrik

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

## 14. Penjelasan Teknis Detektor

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

**Contoh pengaturan** untuk sensor dengan sensitivitas 0.1 V/Kg dan noise ±0.003 V:

| Parameter | Nilai | Alasan |
|---|---|---|
| Threshold | `0.05` V | Tegangan minimum sentuhan valid |
| Hysteresis | `0.005` V | Lebih besar dari noise (0.003 V) |
| Scale | `10.0` Kg/V | Konversi 1/sensitivitas |
| Hold Time | `10.0` s | Waktu minimum antar sentuhan |

---

## 15. Format File Output

### Log CSV (`DataLog/Swimming_YYYYMMDD_HHMMSS.csv`)

```csv
timestamp_s,ai0_V,ai1_V
0.000000,0.0124,0.0089
0.002000,0.0135,0.0091
```

### Tabel CSV (`DataTable/Swimming_table_YYYYMMDD_HHMMSS.csv`)

```csv
No,Time_Pad1,Pressure_Pad1(Kg),Time_Pad2,Pressure_Pad2(Kg)
1,3.142,0.5231,3.155,0.4987
```

### Config JSON (`Python/config.json`)

```json
{
  "ch0": "Dev2/ai0",
  "ch1": "Dev2/ai1",
  "rate": "500.0",
  "buffer": "100000",
  "spl": "50",
  "terminal": "DIFF",
  "vrange": "±10 V",
  "ts_set": "Manual (A)",
  "ts_display": "Relative",
  "dev0": {
    "threshold": "0.05",
    "hysteresis": "0.005",
    "scale": "1.00",
    "hold": "10.0"
  },
  "dev1": {
    "threshold": "0.05",
    "hysteresis": "0.005",
    "scale": "1.00",
    "hold": "10.0"
  }
}
```

---

## 16. Pemecahan Masalah

### Aplikasi tidak mau start

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| `ModuleNotFoundError: nidaqmx` | NI-DAQmx driver atau package Python belum terinstal | Install `pip install nidaqmx` dan NI-DAQmx driver |
| `ModuleNotFoundError: PySide6` | PySide6 belum terinstal | `pip install PySide6` |

### Error saat Start akuisisi

| Pesan Error | Kemungkinan Penyebab | Solusi |
|---|---|---|
| `DAQmx Error: Physical channel not found` | Nama channel salah atau perangkat tidak terdeteksi | Cek nama device di NI MAX (mis. `Dev2` → `Dev1`) |
| `DAQmx Error: Requested operation is not supported` | Kombinasi terminal + range tidak valid | Ganti ke DIFF atau ubah Input Range |
| `Input tidak valid` | Nilai Rate / Buffer / Samples bukan angka | Perbaiki nilai di Set Parameter |

### Data tidak terdeteksi di tabel

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| Sinyal tampil di grafik tapi tabel kosong | Threshold terlalu tinggi | Turunkan nilai Threshold |
| Deteksi terus-menerus (spam) | Hold Time terlalu kecil | Naikkan Hold Time (min. 5 detik) |
| Nilai tekanan tidak realistis | Scale salah | Kalibrasi dan sesuaikan nilai Scale |

### Performa grafik lambat

- Kurangi **Rate (Hz)** (mis. dari 500 ke 200 Hz)
- Kurangi **Buffer Size**
- Tutup aplikasi lain yang berat

### config.json corrupt / error load

Hapus file `config.json` dan jalankan ulang aplikasi. Sistem akan menggunakan nilai default pabrik.

---

*Dokumen ini dibuat otomatis bersama GUI_v2.0.py — NI DAQ Monitor Touchpad Swimmer*

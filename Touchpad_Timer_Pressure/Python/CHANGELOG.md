# Change Log — Swimmer Touchpad Monitor (Python)

Dokumen ini menggabungkan **Change Log** dari docstring berbagai rilis aplikasi di folder `Touchpad_Timer_Pressure/Python/`. Change log di file `.py` masing-masing versi **tetap ada** (tidak dihapus); file ini hanya ringkasan terpusat.

**Rilis aktif (disarankan):** `Versi_4.1.0` → `Versi_4.0.0` → `Versi_3.1.0`

| Folder | File aplikasi utama | Versi |
|--------|---------------------|-------|
| `Versi_4.1.0/` | `Swimmer_Touchpad_Monitor_v4.1.0.py` | 4.1.0 |
| `Versi_4.0.0/` | `Swimmer_Touchpad_Monitor_v4.0.0.py` | 4.0.0 |
| `Versi_3.1.0/` | `Swimmer_Touchpad_Monitor_v3.1.0.py` | 3.1.0 |
| `Versi_3.0.3/` | `Swimmer_Monitor_v3.0.3.py` | 3.0.3 |
| `Versi_3.0.2/` | `GUI_v3.0.2.py` | 3.0.2 |
| `Versi_3.0.1/` | `GUI_v3.0.1.py` | 3.0.1 |
| `Versi_3/` | `GUI_v3.user.py` (edisi user) | 3.x user |
| `Old/` | `GUI v1.0.py`, `GUI_v2.0.py`, … | arsip |

---

## 4.1.0 (dari 4.0.0)

**Sumber:** `Versi_4.1.0/Swimmer_Touchpad_Monitor_v4.1.0.py`

- CSV Log opsional kolom tegangan mentah: checkbox «Sertakan AI0/AI1 raw (Volt) di CSV Log» (default nonaktif).
- Jika aktif saat Start: header `timestamp_s,ai0_kg,ai1_kg,ai0_volt,ai1_volt`.
- Load CSV Log tab Analisa: file 3 atau 5 kolom dikenali; plot overlay tetap Kg.
- Manual aplikasi: `UserManual_v4.1.0.md/.pdf`.

---

## 4.0.0 (dari 3.1.0)

**Sumber:** `Versi_4.0.0/Swimmer_Touchpad_Monitor_v4.0.0.py`, `Versi_4.1.0/Swimmer_Touchpad_Monitor_v4.1.0.py`

- Konversi Volt → Kg: regresi linier y = scale × V + intercept (default intercept 0.00 Kg).
- Parameter Intercept (Kg) per channel di Set Parameter dan config.json.
- Threshold (Volt) → Kg: threshold_volt × scale + intercept; hysteresis (Volt) → Kg: × scale saja.
- ChannelDetector: region Schmitt (upper/lower trip), timeout region 5 s, tekanan = rata-rata ±100 sampel di puncak regional.
- Waktu di tabel = timestamp sampel pertama saat melewati upper_trip.
- Hold Time 10 detik dan re-arm di bawah lower_trip tetap seperti v3.1.0.
- Dialog Set Parameter: konfirmasi OK/Cancel (Set As Default, Reset to Default, Reset to Factory, Apply). «Reset to Saved» diganti «Reset to Default».
- Tab baru «Analisa multifile» (CSV Table saja; label development).
- Tab Analisa Data: layout QSplitter; tabel di samping plot split time.
- Load CSV Log: satu file per load (mengganti tampilan), bukan multi-file overlay.
- Refactor panel analisis tabel (_TableAnalysisPanel) untuk Analisa & multifile.
- Nama file: `Swimmer_Touchpad_Monitor_v4.0.0.py`.
- Manual aplikasi: `UserManual_v4.0.0.md/.pdf`.

---

## 3.1.0 (dari 3.0.3)

**Sumber:** `Versi_3.1.0/Swimmer_Touchpad_Monitor_v3.1.0.py` (docstring asli rilis 3.1.0)

- Jalur Live mengonversi data DAQ dari Volt ke Kg segera setelah pembacaan berdasarkan parameter Scale (Kg/Volt) per channel.
- Threshold dan hysteresis tetap dimuat/disimpan sebagai Volt, lalu dikonversi ke Kg saat Start sebelum dibandingkan dengan data Live.
- ChannelDetector tidak lagi mengalikan Scale; hasil deteksi adalah rata-rata sampel yang sudah dalam Kg.
- CSV Log memakai header `timestamp_s,ai0_kg,ai1_kg` dan menyimpan data Kg.
- Plot Live dan overlay CSV Log pada tab Analisa memakai sumbu Y Pressure (Kg).
- Manual aplikasi diperbarui ke `UserManual_v3.1.0.md/.pdf`.

> **Catatan (ringkasan di v4.x):** v3.1.0 belum memakai **intercept**; konversi live adalah `Kg = scale × V`. Intercept ditambahkan di v4.0.0.

---

## 3.0.3 (dari 3.0.2)

**Sumber:** `Versi_3.0.3/Swimmer_Monitor_v3.0.3.py` (header CSV Log masih Volt di docstring rilis itu)

- Dialog "Load CSV Log" diarahkan ke folder DataLog, sedangkan "Load CSV Table" diarahkan ke folder DataTable.
- Handler kedua tombol load CSV memvalidasi header file sebelum parsing:
  - CSV Log harus memiliki header `timestamp_s,ai0_V,ai1_V` *(sesuai docstring v3.0.3)*.
  - CSV Table harus memiliki header `No,Time_Pad1,Pressure_Pad1(Kg),Time_Pad2,Pressure_Pad2(Kg)`.
  - Jika file tidak sesuai, aplikasi menampilkan notifikasi "File Tidak Sesuai" dan proses load dibatalkan.
- Limit sumbu Y sekunder (Pressure/Kg) pada plot analisa dibuat otomatis mengikuti nilai pressure yang sedang diplot.

**Sumber (rantai docstring v3.1.0 / v4.x):** setelah v3.1.0, header CSV Log distandarkan ke `timestamp_s,ai0_kg,ai1_kg`.

---

## 3.0.2

**Sumber:** `Versi_3.0.2/GUI_v3.0.2.py`

Tidak ada blok **Change Log** formal di docstring. Fitur utama rilis ini (dari docstring):

- Tab Live Data dan Analisa Data.
- Overlay multi-file CSV Log; plot split time & tekanan (dual Y).
- Deteksi Schmitt trigger + hold-time; autosave tabel sesi; metadata perenang di CSV.

---

## Versi lain (tanpa Change Log terstruktur di docstring)

| Lokasi | Keterangan |
|--------|------------|
| `Versi_3.0.1/GUI_v3.0.1.py` | Tidak ada Change Log di docstring; lihat `UserManual_v3.0.1.md`. |
| `Versi_3/GUI_v3.user.py` | Edisi user (tanpa Set Parameter di UI); lihat `UserManual_v3.user.md`. |
| `Old/` | Arsip GUI v1.0 / v2.0; lihat `Old/UserManual.md` jika ada. |

---

## Cara memperbarui dokumen ini

1. Setelah mengubah **Change Log** di docstring file `.py` versi terbaru, salin bagian baru ke atas file ini (versi terbaru di urutan teratas).
2. Regenerasi PDF manual per versi (jika ada): dari `Python/Misc/` jalankan `md_to_pdf_xhtml2pdf.py` dengan path `UserManual_vX.Y.Z.md` yang sesuai.

*Terakhir diselaraskan dengan docstring `Swimmer_Touchpad_Monitor_v4.1.0.py` — Mei 2026.*

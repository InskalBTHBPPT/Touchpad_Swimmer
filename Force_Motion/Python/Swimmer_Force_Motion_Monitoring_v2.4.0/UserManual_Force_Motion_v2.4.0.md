# Manual Pengguna — Swimmer Force Motion Monitoring v2.4.0

Dokumen ini menjelaskan pemakaian aplikasi desktop **Swimmer Force Motion Monitoring** (berkas utama: `Swimmer_Force_Motion_Monitoring_v2.4.0.py`) untuk memantau beban dan orientasi (roll, pitch) perenang melalui koneksi serial, merekam data ke CSV dan **video kamera** (opsional), menampilkan **baterai transmitter** (opsional) di tab Live, serta menganalisis rekaman dengan **playback video** (sinkron playhead), **statistik gaya tethered** (Metode A/B, dF, FI), **koreksi & region** (zero offset, sudut tali), **frekuensi dominan** (FFT/Welch di statistik), **estimasi gap rekaman CSV**, **perbandingan multi-berkas** dalam tabel, dan ekspor statistik yang diperluas.

---

## 1. Persyaratan

| Komponen | Keterangan |
|----------|------------|
| Python | Disarankan 3.10 atau lebih baru |
| Paket | `PySide6`, `pyqtgraph`, `pyserial`, `numpy`, `scipy`, `opencv-python`, `pygrabber` |
| Kamera (opsional) | Webcam, DroidCam, atau perangkat video lain yang dikenali OpenCV (uji utama: backend MSMF di Windows) |
| Perangkat | Mikrokontroler / sensor yang mengirim **satu baris CSV per sampel** lewat USB serial (UTF-8) |
| Sistem | Windows (uji utama); Linux/macOS seharusnya kompatibel selama driver serial tersedia |

Instalasi contoh:

```text
pip install PySide6 pyqtgraph pyserial numpy scipy opencv-python pygrabber
```

Jalankan aplikasi dari folder `Swimmer_Force_Motion_Monitoring_v2.4.0` (atau dengan path penuh):

```text
python Swimmer_Force_Motion_Monitoring_v2.4.0.py
```

---

## 2. Ringkasan antarmuka

Aplikasi memakai **menu bar** (bilah tab disembunyikan; pindah tampilan lewat menu **View**):

| Menu | Isi |
|------|-----|
| **File** | **Analisa SingleFile** → Load csv, Load Video, Simpan Statistik · **Analisa MultiFile** → Add File |
| **View** | Live (`Ctrl+1`), Analisa SingleFile (`Ctrl+2`), Analisa MultiFile (`Ctrl+3`) |
| **Setting** | **Analisa SingleFile** → Statistik Setting · **Live** → Camera, Serial Port |
| **Help** | Manual (`F1`), Tentang, Changelog |

Tiga tampilan utama (setara tab):

- **Live** — plot waktu-nyata (kiri); kanan atas **Nilai terakhir** (grid 2×2) + **Kontrol sesi**; kanan bawah **preview kamera**; rekaman CSV dan video opsional.
- **Analisa SingleFile** — muat CSV/video lewat **File**; plot waktu, playback video, statistik, ekspor `DataStatistik/`.
- **Analisa MultiFile** — tambah berkas lewat **File → Add File**; tabel perbandingan hingga lima kolom; plot perbandingan.

Modul pendukung di folder yang sama:

- `live_csv_io.py` — header data CSV, `parse_logged_csv`, dan `LogSyncMeta` (metadata sinkron video).
- `live_camera_core.py` — pemindaian/probe kamera (OpenCV, MSMF/DSHOW).
- `live_camera_panel.py` — preview kamera tab Live + dialog **Setting → Live → Camera**.
- `live_serial_settings_dialog.py` — dialog **Setting → Live → Serial Port**.
- `analyze_video_panel.py` — pemutar video MP4 di tab Analisa.
- `analyze_single_file_tab.py` — implementasi Analisa SingleFile.
- `analyze_tethered_force_metrics.py` — metrik gaya tethered (Metode A global / Metode B Andrade).
- `analyze_metrics_core.py` — perhitungan metrik + spektrum + **gap rekaman CSV** (`compute_gap_loss`).
- `parse_datastatistik_csv.py` — parser berkas ekspor `DataStatistik/` (Analisa MultiFile).
- `analyze_multi_file_tab.py` — implementasi Analisa MultiFile (tabel + plot).
- `ui_tooltip.py` — tema tooltip aplikasi (latar terang, teks gelap).

---

## 3. Tab Live

### 3.1 Tata letak

```
┌─────────────────────┬──────────────────────────────────┐
│  Plot Force         │  Nilai terakhir (2×2) │ Kontrol  │
│  Plot Roll          │  sesi                 │ sesi     │
│  Plot Pitch         ├──────────────────────────────────┤
│                     │  Kamera (preview + status)       │
└─────────────────────┴──────────────────────────────────┘
        ~50%                        ~50%
```

- **Kiri:** tiga plot vertikal (Force, Roll, Pitch) — data real-time dari serial (~100 titik terakhir).
- **Kanan atas (~25% tinggi):** grup **Nilai terakhir** (Force, Roll, Pitch, Baterai dalam grid 2×2) dan **Kontrol sesi** (nama perenang, gaya, nama file, Connect, Start Log).
- **Kanan bawah (~75% tinggi):** grup **Kamera** — preview live (rasio mengikuti resolusi stream) dan status bar.

### 3.2 Port dan baud

Menu **Setting → Live → Serial Port** membuka dialog:

1. Pilih **Port** COM (tombol **Refresh Ports** memperbarui daftar).
2. Pilih **Baud** (default umum: `115200`).

Port dan baud tidak dapat diubah saat serial sudah **Connect**.

### 3.3 Kontrol sesi

Di grup **Kontrol sesi** (kanan atas):

1. Isi **Nama Perenang** dan **Gaya renang** (dipakai untuk nama file log dan metadata CSV).
2. Tekan **Connect** untuk membuka port serial (tombol *toggle* → Disconnect).
3. Tekan **Start Log** / **Stop Log** untuk rekaman (hanya aktif setelah Connect).

Label **Nama file** menampilkan berkas CSV aktif saat logging.

### 3.4 Format data serial

Setiap baris (diakhiri baris baru `\n`) berisi **empat atau lima** nilai dipisahkan koma. Empat kolom pertama wajib; kolom kelima opsional.

| Kolom | Nama | Contoh | Catatan |
|-------|------|--------|---------|
| 1 | TimeStamp(s) | `12.34` | Waktu dari perangkat (detik) |
| 2 | Force(Kg) | `5.67` | Beban / gaya |
| 3 | Roll(Deg) | `-1.2` | Sudut roll |
| 4 | Pitch(Deg) | `3.4` | Sudut pitch |
| 5 | Baterai(%) | `87` | Opsional; hanya tampilan Live, **tidak** di-log CSV |

Contoh empat kolom (generator uji):

```text
12.34,5.67,-1.2,3.4
```

Contoh lima kolom (LoRa Receiver, PlatformIO `Lora_Receiver_Ori`):

```text
12.34,5.6,-1.2,3.4,87
```

Baris yang diawali `#` diabaikan. Baris dengan kolom selain empat atau lima, atau yang tidak bisa di-parse sebagai angka, dilewati. Baris teks status dari firmware (mis. pesan error) juga diabaikan.

### 3.5 Plot Live

Tiga plot vertikal: **Force**, **Roll**, **Pitch** terhadap waktu (sumbu X: detik). Jumlah titik ditampung terbatas (jendela geser) agar tampilan tetap ringan.

### 3.6 Indikator baterai (opsional)

Grup **Nilai terakhir** menampilkan **Force**, **Roll**, **Pitch**, dan **Baterai (%)**. Kolom baterai hanya terisi jika firmware mengirim **lima** kolom per baris. Nilai baterai **tidak** disimpan ke file CSV rekaman (`DataLog/`).

### 3.7 Start Log / Stop Log

- **Start Log** hanya aktif jika serial sudah terhubung.
- Rekaman ditulis ke folder **`DataLog/`** (otomatis dibuat di samping skrip), tanpa dialog *Save As*.
- Nama file memuat nama perenang, gaya renang, dan cap waktu (format `ddmmyy-HHMM`).
- Saat log berjalan, beberapa field (nama, gaya) dikunci; **Stop Log** menghentikan rekaman dan menutup file.

Struktur awal file CSV rekaman:

1. Baris metadata: `Nama Perenang:`, `Gaya Renang:`, `Time:`
2. Opsional (jika kamera aktif saat Start Log): `VideoFile:`, `LogWallStartEpoch(s):`
3. Header data: `TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)`
4. Baris data numerik
5. Opsional (ditulis saat Stop Log): `SyncCsvT0(s):`, `SyncLogWallStart(s):`, `SyncFirstSampleWall(s):` — dipakai tab Analisa untuk menyelaraskan playhead video dengan plot

Rekaman video `.mp4` (basename sama dengan CSV) disimpan di `DataLog/` jika kamera aktif saat **Start Log**.

### 3.8 Kamera (opsional)

Menu **Setting → Live → Camera** membuka dialog pindai dan pilih perangkat. Preview tampil di grup **Kamera** (bawah kanan tab Live).

1. Tekan **Pindai Kamera** untuk memuat daftar perangkat video (OpenCV; di Windows backend **MSMF** dicoba lebih dulu).
2. Pilih baris berstatus **AKTIF** pada tabel — preview langsung aktif di tab Live.
3. Saat **Start Log** dengan kamera aktif, aplikasi merekam `.mp4` ke `DataLog/` — **basename sama** dengan file CSV.
4. **Stop Log** menghentikan rekaman CSV dan video.

Tanpa kamera aktif, **Start Log** hanya menulis CSV. Metadata sinkron video (lihat §3.7) hanya ditulis jika kamera aktif saat Start Log.

### 3.9 Bantuan

Menu **Help** — **Manual** (`F1`, membuka `UserManual_Force_Motion_v2.4.0.pdf`), **Tentang**, **Changelog**.

- **Tentang** — menampilkan dialog informasi aplikasi dan versi (**2.4.0**), beserta logo mitra BRIN dan UNNES (`image/logo_brin.png`, `image/logo_unnes.png`) jika berkas tersedia.
- **Changelog** — membaca `Force_Motion/Python/Changelog.md` dalam jendela baca-saja.

---

## 4. Analisa SingleFile

### 4.1 Load CSV dan video

- **File → Analisa SingleFile → Load csv** — pilih file rekaman dari `DataLog/` (atau lokasi lain). Parser: `live_csv_io.parse_logged_csv`.
- **File → Analisa SingleFile → Load Video** — pilih MP4 secara manual.
- File `.mp4` pasangan (basename sama) dimuat otomatis saat Load csv jika ada di folder yang sama.

### 4.1a Sinkron playhead video ↔ plot

- Panel **Rekaman video** di tengah tab menampilkan playback MP4 hasil rekaman kamera tab Live.
- Garis vertikal pink pada plot Force, Roll, dan Pitch mengikuti posisi pemutar video.
- **Rekaman baru (v2.3.0):** posisi sumbu waktu dihitung dari metadata `SyncCsvT0(s)` di footer CSV, dengan koreksi jeda antara Start Log dan sampel serial pertama (`SyncFirstSampleWall` − `SyncLogWallStart`).
- **File CSV lama** tanpa metadata sinkron: fallback `TimeStamp` baris pertama + detik video (sinkron kasar).

### 4.2 Plot waktu, video, dan statistik

Setelah berhasil dimuat:

- **Kiri:** tiga plot rekaman penuh (Force, Roll, Pitch).
- **Tengah:** panel **Rekaman video** — playback MP4 (lihat §4.1a). Tombol **Play** memiliki tooltip bantuan.
- **Kanan:** tabel statistik (tanpa tombol Setting — gunakan **Setting → Analisa SingleFile → Statistik Setting**).
- Marker menandai titik ekstrem pada plot (force maksimum; roll/pitch min dan max) dengan label waktu.
- Panel kanan menampilkan ringkasan angka yang konsisten dengan marker, baris **TimeStamp Start/Stop Uji**, **Metode gaya Force**, **Mean (meanF)**, **Impulse (ImpF)**, **TpeakF**, **DUR**, **RFD**, **dF**, **Fatigue Index (FI)** (kolom Force; dF dan temporal hanya Metode B; FI global), dan ekstremum gaya (**Maksimum** = peakF, **Minimum** = minF) pada kolom Force, **frekuensi dominan** (Hz) per kanal, serta kartu **GAP REKAMAN CSV** (lihat §4.4 dan §4.6). **Tooltip:** arahkan kursor ke nama baris di kolom **Parameter** untuk penjelasan singkat; panduan awam lengkap di §4.6a.
- **Setting → Analisa SingleFile → Statistik Setting** membuka dialog pengaturan: koreksi & region, metode statistik Force, spektrum, gap CSV (lihat §4.2a dan §4.3).

### 4.2a Koreksi & region (Statistik Setting)

Grup **Koreksi & region** mengatur data yang dipakai statistik dan tampilan plot:

| Kontrol | Fungsi |
|---------|--------|
| **Region biru** (plot) | Batas **data uji** — geser ujung region pada plot Force/Roll/Pitch. Hanya data di dalam region inilah yang dipakai statistik gaya dan sudut (kecuali gap CSV). |
| **Zero Offset** (checkbox) | Menampilkan region **hijau** (baseline) dan mengurangi rata-rata Force/Roll/Pitch di region hijau dari seluruh deret. Region data uji (biru) dimulai setelah jeda **2 s** dari akhir region hijau. |
| **Koreksi sudut tali** | Jika dicentang: gaya horizontal = Force terukur × cos(sudut). Sudut diukur di atas permukaan air (horizontal = 0°); default **7,00°**. |
| **Koreksi batas bawah Force mentah (−1 Kg)** | Default aktif. Nilai Force mentah di bawah −1 Kg dibatasi menjadi −1 Kg sebelum koreksi lain dan statistik. |

Baris tabel **Zero offset start/stop**, **Durasi region zero offset**, dan **Rata-rata offset** selalu ditampilkan; nilai terisi saat Zero Offset aktif (selain itu **—**).

### 4.3 Analisa Setting — metode spektrum dan statistik Force

- Pilih **FFT** atau **Welch PSD** pada dropdown **Metode spektrum (statistik)**.
- Perubahan metode memperbarui **angka frekuensi dominan** pada kartu statistik (v2.4.0 tidak menampilkan plot spektrum visual).

Grup **Statistik Force (peakF / meanF / ImpF / temporal)** — radio pemilihan cara menghitung parameter gaya pada kolom Force (region data uji):

| Pilihan | Makna singkat |
|---------|----------------|
| **Metode A — global (Amaro / Carrasco-Poyatos)** | Default. **peakF**, **meanF**, **minF** global region uji; **ImpF** = ∫F·dt trapesium seluruh region. **TpeakF**, **DUR**, **RFD**, **dF** = **—**. **FI** dihitung jika durasi region ≥ 15 s. Baris **t @ maks** / **t @ min** berisi timestamp; marker merah pada plot = peakF. |
| **Metode B — per siklus (Andrade)** | Sinyal Force difilter **Butterworth low-pass orde 4** (default cutoff **7 Hz**, dapat diatur pada spinbox **Filter Butterworth (Andrade)**). Valley (minF lokal) → segmentasi per kayuhan → peakF, meanF, minF, **ImpF**, **TpeakF**, **DUR**, **RFD**, **dF** per siklus → rata-rata antar siklus. **ImpF** per siklus = ∫F·dt antar dua minF. **t @ maks/min** Force = **—**. **FI** dihitung global pada region uji (≥ 15 s). Fallback global jika siklus tidak terdeteksi. |

Spinbox **Filter Butterworth (Andrade)** hanya aktif pada Metode B; rentang **0,5–30 Hz** (langkah 0,5 Hz). Nilai default **7 Hz** mengikuti Andrade et al. (2018).

Baris **Metode gaya Force** pada tabel statistik menampilkan pilihan aktif; pada Metode B yang berhasil, ditambah **· n=…** (jumlah siklus).

### 4.4 Gap rekaman CSV

Grup **Analisa Setting** juga berisi radio **Metode gap rekaman CSV**:

| Pilihan | Makna singkat |
|---------|----------------|
| **Metode A — per gap (lokal)** | Untuk setiap pasangan baris berurutan: jika selisih timestamp `Δt` lebih besar dari **1,5 × median(Δt)**, estimasi sampel hilang = `round(Δt / Δt_nominal) − 1`. Menampilkan **jumlah gap** (berapa kali lubang terdeteksi). |
| **Metode B — global (ringkas)** | Default. `n_diharapkan = round(durasi / Δt_nominal) + 1`; `n_hilang = max(0, n_diharapkan − n_tercatat)`. Menampilkan **sampel diharapkan**. |

- Perhitungan gap memakai **seluruh deret `TimeStamp(s)` dari CSV yang dimuat** (rekaman penuh), **bukan** region data uji (biru). Geser region uji atau aktifkan Zero Offset **tidak** mengubah angka gap.
- `Δt_nominal` gap = **median** selisih `TimeStamp(s)` antar baris pada **rekaman penuh** (bisa berbeda dari laju sampel spektrum yang dihitung di region uji).
- Kartu **GAP REKAMAN CSV** menampilkan metode, Δt nominal, laju efektif (Hz), sampel tercatat, sampel hilang (estimasi), dan persen hilang.
- **Tujuan:** mengetahui kualitas rekaman CSV (lubang timestamp), **bukan** diagnosis LoRa atau transfer nirkabel.
- Mengganti radio langsung menghitung ulang kartu (tanpa reload CSV).

### 4.5 Simpan statistik

- **File → Analisa SingleFile → Simpan Statistik** menulis file CSV ke folder **`DataStatistik/`** tanpa dialog penyimpanan (nonaktif sampai CSV dimuat dan statistik tersedia).
- Nama file: `<nama_file_csv_yang_dimuat>_DataStatistik_<ddmmyy-HHMMSS>.csv` — cap waktu **saat tombol ditekan** (lokal); setiap ekspor menghasilkan berkas baru (tidak menimpa ekspor Metode A/B atau pengaturan lain sebelumnya).
- Isi ringkas:
  - Metadata (nama perenang, gaya renang, waktu ekspor, nama berkas sumber, segmen analisa).
  - Blok **zero offset** — selalu diekspor: `Zero_offset_diterapkan` (Ya/Tidak), start/stop, rata-rata offset Force/Roll/Pitch, durasi region zero offset (kosong jika tidak berlaku).
  - Blok **koreksi** — koreksi sudut tali, sudut (deg), koreksi batas bawah Force mentah, batas (Kg) jika aktif.
  - Baris **`Timestampstart (s)`** / **`Timestampstop (s)`** + durasi region data uji.
  - Tabel **`Metrik, Nilai, Satuan, Waktu (s)`** untuk metode dan metrik Force (**Metode_statistik_Force**, opsional **Filter_Andrade_cutoff**, **Force_maksimum_peakF**, **Force_mean_meanF**, **Force_impulse_ImpF**, opsional **Force_TpeakF**, **Force_DUR**, **Force_RFD**, **Force_dF** (Metode B), opsional **Force_Fatigue_Index**, **Force_minimum_minF**; roll/pitch min/maks) — lihat §4.6.
  - Dua baris kosong, lalu tabel **`Metrik, Frekuensi Dominan (Hz), Metode`** dengan baris **Force**, **Roll**, **Pitch** (metode sama untuk ketiga saluran pada satu ekspor).
  - Blok **`Gap rekaman CSV (estimasi)`** — selalu lengkap: metode, Δt nominal, laju sampel efektif, sampel tercatat, sampel diharapkan, jumlah gap, sampel hilang estimasi, persen hilang (baris yang tidak berlaku untuk metode gap dipilih dibiarkan kosong).
- Sebelum menulis, aplikasi menyegarkan snapshot statistik dari pengaturan UI terakhir (region, zero offset, metode).

### 4.6 Parameter gaya tethered — peakF, meanF, minF, ImpF, TpeakF, DUR, RFD, dF, FI (kolom Force)

Parameter ini hanya dihitung pada **saluran Force**, pada **region data uji** (region biru), dari deret yang sudah melalui koreksi aktif di **Analisa Setting** (batas bawah Force mentah, zero offset, koreksi sudut tali jika dicentang). Satuan gaya: **Kg**; impuls: **Kg·s**; waktu: **s**; laju perubahan gaya: **Kg/s**; indeks variasi/kelelahan: **%** (literatur sering memakai **N·s**, **N/s**, atau **N** — konversi dengan × *g* jika diperlukan).

Cara perhitungan dipilih di **Statistik Force** (§4.3): **Metode A (global)** atau **Metode B (per siklus, Andrade)**.

| Baris tabel | Simbol | Metode A (global) | Metode B (Andrade) |
|-------------|--------|-------------------|---------------------|
| **Maksimum** | peakF | Maksimum global region uji | Rata-rata peakF per siklus |
| **Mean (meanF)** | meanF | Rata-rata semua sampel | Rata-rata meanF per siklus |
| **Impulse (ImpF)** | ImpF | ∫F·dt trapesium, seluruh region uji | Rata-rata ∫F·dt per siklus (minF→minF) |
| **TpeakF (s)** | TpeakF | **—** | Rata-rata \(t_{\mathrm{peak}} - t_{\mathrm{minF\_awal}}\) per siklus |
| **DUR (s)** | DUR | **—** | Rata-rata \(t_{\mathrm{minF}_{i+1}} - t_{\mathrm{minF}_i}\) per siklus |
| **RFD (Kg/s)** | RFD | **—** | Rata-rata \((\mathrm{peakF} - \mathrm{minF}) / \mathrm{TpeakF}\) per siklus |
| **dF (%)** | dF | **—** | Rata-rata variasi intrasiklus gaya per siklus (Morouço 2018) |
| **Fatigue Index (FI) (%)** | FI | Penurunan gaya akhir vs awal region | Sama (global, tidak per siklus) |
| **Minimum** | minF | Minimum global region uji | Rata-rata minF (valley) per siklus |
| **t @ maks / t @ min** | — | Timestamp peakF / minF global | **—** (agregat) |
| **Metode gaya Force** | — | Label metode + opsi **n** siklus | |

Baris **Roll** dan **Pitch** pada **Maksimum** / **Minimum** tetap ekstremum sudut, tidak terpengaruh pilihan metode Force.

#### Metode A — global (Amaro / Carrasco-Poyatos)

**peakF, meanF, minF** — seperti §4.6 versi sebelumnya (ekstremum dan rata-rata global).

**ImpF (Impulse):** \(I = \int F(t)\,dt\) pada seluruh region uji, dihitung dengan **aturan trapesium** (`numpy.trapezoid`) pada pasangan `(TimeStamp(s), Force)`.

**Referensi:**

- Carrasco-Poyatos, M., et al. (2024). *Variables and protocols of the tethered swimming method: a systematic review.* **Sport Sciences for Health**. https://doi.org/10.1007/s11332-023-01140-1
- Amaro, N., Marinho, D. A., Batalha, N., Marques, M. C., & Morouço, P. (2014). *Reliability of tethered swimming evaluation in age group swimmers.* **Journal of Human Kinetics**, 41, 155–162. https://doi.org/10.2478/hukin-2014-0043

#### Metode B — per siklus (Andrade)

1. **Filter** deret Force dengan **Butterworth low-pass orde 4** (`scipy.signal.butter` + `sosfiltfilt`); cutoff default **7 Hz** (dapat diubah di Analisa Setting).
2. Deteksi **minimum lokal** (*valley*) = penanda **minF** tiap kayuhan pada sinyal terfilter.
3. Segmentasi antar dua minF berurutan = satu siklus.
4. Per siklus pada sinyal terfilter: **peakF**, **meanF**, **minF**, **ImpF** (= ∫F·dt trapesium dalam segmen), **TpeakF** = waktu dari minF awal ke peakF, **DUR** = waktu antar dua minF berurutan, **RFD** = (peakF − minF) / TpeakF (siklus dengan TpeakF ≈ 0 diabaikan), **dF** = variasi intrasiklus gaya (Persamaan Morouço 2018/2024).
5. Nilai di tabel = **rata-rata** parameter antar siklus terdeteksi.

Jika valley tidak cukup, nilai **fallback global** (Metode A) dengan catatan di baris metode.

**Referensi:**

- Andrade, R. M., Figueira, A. J., Metz, V., Amadio, A. C., & Cerca, J. (2018). *Interpretation of propulsive force in tethered swimming through principal component analysis.* **Revista Brasileira de Medicina do Esporte**, 24(3), 206–210. https://doi.org/10.1590/1517-869220182403175155

#### dF — Intracyclic Variation of Force (Metode B)

**dF** mengukur seberapa **bergelombang** kurva F(t) **dalam satu siklus kayuhan** — indikator kemampuan menerapkan gaya secara kontinyu di air. Nilai **lebih tinggi** umumnya berkorelasi dengan performa renang bebas **lebih rendah** (Morouço et al., 2018).

\[
dF = \frac{\sqrt{\sum_i (F_i - \bar{F})^2 / n}}{\bar{F}} \times 100 \quad [\%]
\]

dengan \(F_i\) = gaya instan dalam segmen siklus, \(\bar{F}\) = meanF siklus, \(n\) = jumlah sampel siklus. Aplikasi menghitung **dF per siklus** lalu **merata-rata** antar siklus (Metode B). Metode A menampilkan **—**.

**Referensi:**

- Morouço, P. G., Barbosa, T. M., Arellano, R., & Vilas-Boas, J. P. (2018). *Intracyclic variation of force and swimming performance.* **International Journal of Sports Physiology and Performance**, 13(7), 897–902. https://doi.org/10.1123/ijspp.2017-0223
- Morouço, P., Tavares, D., & Silva, H. P. (2024). *Tethered Swimming: Historical Notes and Future Prospects.* **Encyclopedia**, 4(3), 1044–1061. https://doi.org/10.3390/encyclopedia4030067

#### FI — Fatigue Index (global, kedua metode)

**FI** mengevaluasi **penurunan gaya relatif** dari awal ke akhir region uji — indikator kapasitas anaerobik / kelelahan pada tes all-out (protokol umum: 30 s).

\[
FI = \left(\frac{F_{\mathrm{akhir}}}{F_{\mathrm{awal}}} - 1\right) \times 100 \quad [\%]
\]

- \(F_{\mathrm{awal}}\) = meanF pada jendela **awal** region (default **10 s** pertama, atau sepertiga durasi jika region lebih pendek).
- \(F_{\mathrm{akhir}}\) = meanF pada jendela **akhir** region (10 s terakhir, atau sepertiga durasi).
- Region uji harus **≥ 15 s** agar FI dihitung; jika lebih pendek, baris FI = **—**.
- **FI positif** = gaya menurun (kelelahan); **FI negatif** = gaya akhir lebih tinggi dari awal.

FI dihitung pada deret Force terkoreksi di region uji, **independen** dari pilihan Metode A/B.

**Referensi:**

- Morouço, P. G., Vilas-Boas, J. P., & Fernandes, R. J. (2012). *Evaluation of adolescent swimmers through a 30-s tethered test.* **Pediatric Exercise Science**, 24(2), 312–321. https://doi.org/10.1123/pes.24.2.312
- Morouço, P., Tavares, D., & Silva, H. P. (2024). *Tethered Swimming: Historical Notes and Future Prospects.* **Encyclopedia**, 4(3), 1044–1061. https://doi.org/10.3390/encyclopedia4030067

#### Hubungan ImpF dengan meanF (Metode A)

Kira-kira \(I \approx \overline{F} \times T\) untuk sampling reguler, dengan \(\overline{F}\) = meanF dan \(T\) = durasi region uji; trapesium pada Δt tidak seragam memberi perbedaan kecil.

#### Ekspor DataStatistik

Blok metrik Force mencantumkan **Metode_statistik_Force**, opsional **Jumlah_siklus_Force_Andrade**, opsional **Filter_Andrade_cutoff** (Hz), serta **Force_maksimum_peakF**, **Force_mean_meanF**, **Force_impulse_ImpF**, opsional **Force_TpeakF**, **Force_DUR**, **Force_RFD**, opsional **Force_dF** (Metode B), opsional **Force_Fatigue_Index**, dan **Force_minimum_minF** sesuai metode aktif.

### 4.6a Panduan awam — membaca tabel statistik

Arahkan kursor ke **nama baris** di kolom **Parameter** pada tabel statistik untuk melihat penjelasan singkat (tooltip). Bagian ini memberi penjelasan lebih panjang dalam bahasa sehari-hari.

#### Region uji dan zero offset

- **TimeStamp Start / Stop Uji** — Batas waktu region **biru** pada plot. Hanya data di dalam region inilah yang dipakai menghitung statistik gaya dan sudut (kecuali gap CSV, yang memakai seluruh file).
- **Durasi region data uji** — Berapa lama tes yang Anda analisis (detik). Geser ujung region biru untuk memperpendek atau memperpanjang analisis.
- **Zero offset** — Region **hijau** dipakai menghitung “nol” sensor sebelum renang intens. **Rata-rata offset** adalah nilai baseline Force/Roll/Pitch yang dikurangkan saat Zero Offset aktif.

#### Gaya Force — yang perlu dipahami pelatih

| Istilah | Arti awam | Kapan dipakai |
|---------|-----------|---------------|
| **peakF (Maksimum)** | Puncak gaya terkuat | Menilai kekuatan dorong maksimal |
| **meanF (Mean)** | Gaya rata-rata | Gambaran umum intensitas renang |
| **minF (Minimum)** | Titik gaya terlemah dalam siklus/region | Biasanya saat transisi antar fase kayuhan |
| **ImpF (Impulse)** | Total “dorongan” (gaya × waktu) | Lebih mirip “berapa banyak tenaga didorong” daripada sekadar puncak |
| **TpeakF** | Lama naik dari lemah ke puncak (per kayuhan) | Metode B — kecepatan membangun gaya |
| **DUR** | Lama satu kayuhan penuh | Metode B — ritme / durasi siklus |
| **RFD** | Kecepatan kenaikan gaya (Kg/s) | Metode B — “ledakan” gaya di awal dorongan |
| **dF** | Seberapa bergelombang gaya per kayuhan (%) | Metode B — makin tinggi, gaya kurang halus/kontinyu |
| **FI** | Penurunan gaya awal→akhir tes (%) | Kelelahan anaerobik; butuh region ≥ 15 s |

**Metode A** menjawab: “Berapa nilai global di seluruh region?” — cocok untuk ringkasan cepat.

**Metode B** menjawab: “Bagaimana rata-rata tiap kayuhan?” — cocok untuk teknik renang, karena menghitung per siklus lalu dirata-rata.

#### Roll dan Pitch

- **Maksimum / Minimum** — Sudut tubuh tertinggi dan terendah yang tercatat (derajat).
- **Frekuensi dominan** — Frekuensi utama osilasi/ayunan tubuh pada saluran tersebut (Hz), dari analisis FFT atau Welch.

#### Gap rekaman CSV

Bukan metrik performa perenang, melainkan **kualitas file data**:

- **Sampel hilang** — Estimasi berapa banyak titik data yang “hilang” karena jeda timestamp di CSV.
- **Persen hilang** — Semakin besar, semakin hati-hati menafsirkan statistik (data mungkin tidak kontinu).

Jika gap besar, pertimbangkan ulang rekaman atau periksa koneksi/logging sebelum membandingkan antar sesi.

#### Tips membaca angka

1. Bandingkan **meanF** dan **ImpF** bersama — impuls tinggi dengan mean sedang bisa berarti gaya terjaga lebih lama.
2. **dF** rendah + **peakF** tinggi sering diinginkan pada jarak pendek (gaya kuat dan relatif stabil per kayuhan).
3. **FI** positif besar pada tes 30 s all-out menandakan penurunan gaya yang jelas — normal pada tes maksimal, berguna memantau perkembangan anaerobik.
4. Baris **—** bukan error: artinya parameter tidak berlaku untuk metode atau durasi region saat ini.

---

## 5. Analisa MultiFile

Tab ini membandingkan hingga **lima** berkas ekspor statistik dari Analisa SingleFile (`DataStatistik/*_DataStatistik*.csv`), bukan berkas rekaman mentah `DataLog/`.

### 5.1 Batang alat

- **Baris kontrol:** **Plot data** (hijau) → *ruang fleksibel* → label **Hapus kolom** + combo + **Clear tabel** (merah).
- Tambah berkas: **File → Analisa MultiFile → Add File**.
- **Plot data** aktif setelah ada minimal satu berkas dimuat.

### 5.2 Add File dan batas berkas

- **File → Analisa MultiFile → Add File** membuka dialog pilih CSV (default folder `DataStatistik/`).
- Filter dialog: `*_DataStatistik*.csv`.
- Maksimum **5** berkas; parser `parse_datastatistik_csv.py` memvalidasi format ekspor tab Analisa.

### 5.3 Isi tabel

- **Kolom pertama (Metrik):** label parameter, dikelompokkan dengan warna:
  - **Region uji** — segmen analisa, timestamp start/stop uji, durasi region data uji.
  - **Zero offset** — diterapkan (Ya/Tidak), start/stop, durasi, rata-rata offset Force/Roll/Pitch.
  - **Koreksi** — sudut tali, batas bawah Force mentah.
  - **Force** — metode statistik, peakF, meanF, ImpF, TpeakF, DUR, RFD, dF, FI, minF, frekuensi dominan.
  - **Roll / Pitch** — minimum, maksimum, frekuensi dominan.
  - **Metode spektrum** — FFT atau Welch (dari ekspor).
  - **Gap rekaman CSV** — metode, Δt nominal, laju sampel, sampel tercatat/diharapkan, jumlah gap, sampel hilang, persen hilang.
- **Header kolom data** (enam baris atas): nama perenang, gaya renang, nama file DataStatistik (di-wrap sesuai lebar kolom; tooltip = nama lengkap), waktu ekspor, berkas sumber log, baris **Value**.
- Nilai kosong ditampilkan sebagai **—**.
- Lebar kolom data tetap (~252 px); kolom Metrik menyesuaikan isi.

### 5.4 Hapus kolom

- Pilih **Kolom 1** … **Kolom 5** atau **Semua kolom**, lalu **Clear tabel** (tombol merah) untuk mengeluarkan berkas dari daftar dan memperbarui tabel.

### 5.5 Plot perbandingan

- Tombol hijau **Plot data** membuka **jendela terpisah** (non-modal).
- Dropdown **Metrik** (11 pilihan):
  - Force: **peakF**, **meanF**, **minF**, **ImpF**
  - Roll / Pitch: **minimum**, **maksimum**
  - Frekuensi dominan: **Force**, **Roll**, **Pitch**
- Dropdown **Gaya plot:** **Garis + penanda** (default), **Diagram batang**, atau **Titik saja**.
- **Sumbu X** = **nomor kolom** (1, 2, 3, …) sesuai urutan berkas dimuat — bukan nama file.
- **Tooltip hover:** arahkan kursor ke penanda/batang; menampilkan **Value** (nilai metrik; **—** jika kosong di ekspor) dan **Nama file** DataStatistik lengkap.
- Nilai diambil langsung dari ekspor `DataStatistik/` (tidak dihitung ulang dari `DataLog/`).
- Mengganti metrik atau gaya memperbarui gambar secara langsung.

---

## 6. Folder kerja

| Folder / berkas | Fungsi |
|-----------------|--------|
| `DataLog/` | Rekaman CSV dan video `.mp4` dari tab Live (diabaikan Git sesuai `.gitignore` proyek) |
| `DataStatistik/` | Ekspor statistik dari tab Analisa (`*_DataStatistik_<ddmmyy-HHMMSS>.csv`) |
| `parse_datastatistik_csv.py` | Parser ekspor DataStatistik (tab multifile) |
| `live_csv_io.py` | Header + parser CSV rekaman + `LogSyncMeta` |
| `live_camera_core.py` | Pemindaian kamera |
| `live_camera_panel.py` | Preview kamera tab Live + dialog Setting → Live → Camera |
| `live_serial_settings_dialog.py` | Dialog Setting → Live → Serial Port |
| `analyze_video_panel.py` | Pemutar video tab Analisa |
| `analyze_single_file_tab.py` | Tab Analisa (plot + video + statistik + ekspor) |
| `analyze_tethered_force_metrics.py` | Metrik gaya tethered (Metode A/B) |
| `analyze_metrics_core.py` | Metrik rekaman + spektrum + gap (tab Analisa) |
| `analyze_multi_file_tab.py` | Tab Analisa multifile |
| `ui_tooltip.py` | Tema dan teks tooltip |
| `requirements.txt` | Daftar dependensi Python (termasuk OpenCV) |
| `image/logo_brin.png`, `image/logo_unnes.png` | Logo mitra di dialog Tentang |
| `UserManual_Force_Motion_v2.4.0.md` | Manual ini (Markdown) |
| `UserManual_Force_Motion_v2.4.0.pdf` | Manual ini (PDF, opsional) |
| `../md_to_pdf_Force_Motion.py` | Skrip konversi MD → PDF (folder induk `Force_Motion/Python`) |

---

## 7. Membuat / memperbarui PDF manual

Aplikasi **Help** membuka PDF. PDF dihasilkan dari Markdown dengan skrip `md_to_pdf_Force_Motion.py` (pustaka **markdown** dan **xhtml2pdf**), berada di folder **`Force_Motion/Python`**.

Dari folder `Force_Motion/Python`:

```text
pip install markdown xhtml2pdf
python md_to_pdf_Force_Motion.py -i Swimmer_Force_Motion_Monitoring_v2.4.0/UserManual_Force_Motion_v2.4.0.md -o Swimmer_Force_Motion_Monitoring_v2.4.0/UserManual_Force_Motion_v2.4.0.pdf
```

Tanpa opsi, skrip bawaan masih mengarah ke manual **v1.0.0** di folder yang sama; untuk v2.4.0 gunakan `-i` dan `-o` seperti di atas.

---

## 8. Pemecahan masalah

| Gejala | Tindakan |
|---------|----------|
| Port tidak muncul | Buka **Setting → Live → Serial Port**; cabut/colok USB, klik **Refresh Ports**, periksa driver. |
| Connect gagal | Pastikan port tidak dipakai program lain; coba baud yang sesuai firmware. |
| Plot kosong | Periksa format baris (empat atau lima angka, koma); pastikan firmware mengirim newline. |
| Baterai tampil `—` | Perangkat mungkin hanya mengirim empat kolom; LoRa Receiver mengirim lima kolom. |
| Load CSV gagal di Analisa | **File → Load csv**; pastikan file dari tab Live (metadata + header persis). |
| Load gagal di Analisa MultiFile | Gunakan berkas dari **Simpan Statistik** (`*_DataStatistik*.csv`), bukan `DataLog/`. |
| Video tidak dimuat otomatis | Pastikan `.mp4` ada di folder yang sama dengan CSV; atau **File → Load Video**. |
| Rekam video gagal saat Start Log | Pilih kamera aktif lewat **Setting → Live → Camera** sebelum Start Log; periksa `opencv-python`. |
| Kamera tidak terdeteksi | **Setting → Live → Camera** → **Pindai Kamera** ulang; di Windows pastikan DroidCam kompatibel MSMF. |
| Help tidak membuka PDF | Jalankan §7; pastikan `UserManual_Force_Motion_v2.4.0.pdf` ada di folder aplikasi v2.4.0. |
| Error import `numpy` / `scipy` / `cv2` | Instal dependensi (lihat §1 atau `requirements.txt`). |

---

## 9. Versi dokumen

- **Manual:** selaras dengan aplikasi **v2.4.0** (menu bar File/View/Setting/Help; tata letak Live 50:50; dialog kamera & serial; muat/simpan lewat menu File; Statistik Setting lewat menu Setting; dialog Tentang dengan logo mitra; kamera Live, video Analisa, sinkron playhead, baterai, statistik gaya tethered, dF, FI, zero offset, koreksi, tooltip, gap CSV; ekspor DataStatistik; Analisa MultiFile dengan tabel berkelompok dan plot perbandingan).
- Ringkasan perubahan antar versi ada di `Force_Motion/Python/Changelog.md` dan docstring `Swimmer_Force_Motion_Monitoring_v2.4.0.py`.

---

## 10. Referensi

- [NotebookLM — Swimmer Force Motion Monitoring](https://notebooklm.google.com/notebook/cbd512b8-4457-4a1f-937f-a022df17f8e5?authuser=1) — materi referensi tambahan terkait aplikasi dan analisa force/motion (memerlukan akun Google untuk membuka).
- [1080Motion — Swimming performance and monitoring training with new technologies](https://www.1080motion.com/webinars/swimming-performance-and-monitoring-training-with-new-technologies) — webinar tentang teknologi pemantauan performa dan latihan renang di lingkungan air (Bjørn Harald Olstad, Norwegian School of Sport Sciences, 2020).

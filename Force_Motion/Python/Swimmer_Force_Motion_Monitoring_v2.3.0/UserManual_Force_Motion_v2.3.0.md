# Manual Pengguna — Swimmer Force Motion Monitoring v2.3.0

Dokumen ini menjelaskan pemakaian aplikasi desktop **Swimmer Force Motion Monitoring** (berkas utama: `Swimmer_Force_Motion_Monitoring_v2.3.0.py`) untuk memantau beban dan orientasi (roll, pitch) perenang melalui koneksi serial, merekam data ke CSV dan **video kamera** (opsional), menampilkan **baterai transmitter** (opsional) di tab Live, serta menganalisis rekaman dengan **playback video** (sinkron playhead), **frekuensi dominan** (FFT/Welch di statistik), **estimasi gap rekaman CSV**, **perbandingan multi-berkas** dalam tabel, dan ekspor statistik yang diperluas.

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

Jalankan aplikasi dari folder `Swimmer_Force_Motion_Monitoring_v2.3.0` (atau dengan path penuh):

```text
python Swimmer_Force_Motion_Monitoring_v2.3.0.py
```

---

## 2. Ringkasan antarmuka

Aplikasi memiliki **tiga tab**:

- **Live** — koneksi serial, plot waktu-nyata, indikator nilai terakhir (force, roll, pitch, **baterai %** jika perangkat mengirim kolom kelima), panel **kamera** (pindai, preview, rekam `.mp4` saat **Start Log**), rekaman CSV empat kolom, opsi timestamp CSV, tombol **About** dan **Help**.
- **Analisa** — muat **satu** file CSV hasil rekaman Live, tiga plot waktu penuh dengan marker ekstremum, **playback video** pasangan (playhead pink pada plot), kartu statistik (frekuensi dominan FFT/Welch **tanpa plot spektrum visual**, **gap rekaman CSV** Metode A/B), ekspor ringkasan ke `DataStatistik/`.
- **Analisa multifile** — hingga **lima** berkas CSV sekaligus; ringkasan metrik dalam **tabel**; **plot perbandingan** (jendela terpisah, pyqtgraph); simpan tabel ke `TableMultiFile/`; metode spektrum (FFT / Welch) mengisi ulang semua kolom.

Modul pendukung di folder yang sama:

- `live_csv_io.py` — header data CSV, `parse_logged_csv`, dan `LogSyncMeta` (metadata sinkron video).
- `live_camera_core.py` — pemindaian/probe kamera (OpenCV, MSMF/DSHOW).
- `live_camera_panel.py` — panel kamera tab Live (preview + rekam).
- `analyze_video_panel.py` — pemutar video MP4 di tab Analisa.
- `analyze_single_file_tab.py` — implementasi tab Analisa (satu berkas).
- `analyze_metrics_core.py` — perhitungan metrik + spektrum + **gap rekaman CSV** (`compute_gap_loss`).
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

### 3.4 Plot Live

Tiga plot vertikal: **Force**, **Roll**, **Pitch** terhadap waktu (sumbu X: detik). Jumlah titik ditampung terbatas (jendela geser) agar tampilan tetap ringan.

### 3.5 Indikator baterai (opsional)

Grup **Nilai terakhir** menampilkan **Force**, **Roll**, **Pitch**, dan **Baterai (%)**. Kolom baterai hanya terisi jika firmware mengirim **lima** kolom per baris. Nilai baterai **tidak** disimpan ke file CSV rekaman (`DataLog/`).

### 3.6 Start Log / Stop Log

- **Start Log** hanya aktif jika serial sudah terhubung.
- Rekaman ditulis ke folder **`DataLog/`** (otomatis dibuat di samping skrip), tanpa dialog *Save As*.
- Nama file memuat nama perenang, gaya renang, dan cap waktu (format `ddmmyy-HHMM`).
- Saat log berjalan, beberapa field (nama, gaya, checkbox timestamp) dikunci; **Stop Log** menghentikan rekaman dan menutup file.

Struktur awal file CSV rekaman:

1. Baris metadata: `Nama Perenang:`, `Gaya Renang:`, `Time:`
2. Opsional (jika kamera aktif saat Start Log): `VideoFile:`, `LogWallStartEpoch(s):`
3. Header data: `TimeStamp(s),Force(Kg),Roll(Deg),Pitch(Deg)`
4. Baris data numerik
5. Opsional (ditulis saat Stop Log): `SyncCsvT0(s):`, `SyncLogWallStart(s):`, `SyncFirstSampleWall(s):` — dipakai tab Analisa untuk menyelaraskan playhead video dengan plot

Rekaman video `.mp4` (basename sama dengan CSV) disimpan di `DataLog/` jika kamera aktif saat **Start Log**.

### 3.7 Checkbox “TimeStamp CSV mulai 0 saat Start Log”

- **Default:** tidak dicentang → kolom waktu di CSV sama dengan nilai dari perangkat.
- **Dicentang:** kolom waktu di CSV = waktu serial **dikurangi** timestamp **sampel pertama setelah Start Log** (bukan saat Connect). Baris pertama data mendekati `0` s.
- Plot Live tetap memakai waktu mentah dari serial.

### 3.8 About dan Help

- **About** — menampilkan dialog informasi aplikasi dan versi (**2.3.0**).
- **Help** — membuka berkas **`UserManual_Force_Motion_v2.3.0.pdf`** dengan aplikasi PDF bawaan sistem. Jika PDF belum ada, dialog menjelaskan cara membuatnya (lihat bagian 7).

### 3.9 Kamera (opsional)

Panel **Kamera** di tab Live (di samping plot) memungkinkan preview dan rekaman video bersamaan dengan log CSV.

1. Tekan **Pindai kamera** untuk memuat daftar perangkat video yang terdeteksi (OpenCV; di Windows backend **MSMF** dicoba lebih dulu, cocok untuk DroidCam).
2. Pilih perangkat dari dropdown, lalu **Mulai preview** untuk menampilkan gambar live.
3. Saat **Start Log** dengan preview aktif, aplikasi merekam `.mp4` ke `DataLog/` — **basename sama** dengan file CSV (mis. `Ridwan_Bebas_240625-1105.mp4`).
4. **Stop Log** menghentikan rekaman CSV dan video.

Tanpa kamera aktif, **Start Log** hanya menulis CSV (perilaku sama seperti v2.2.0). Metadata sinkron video (lihat §3.6) hanya ditulis jika kamera aktif saat Start Log.

---

## 4. Tab Analisa

### 4.1 Load CSV

- Tekan **Load CSV…** dan pilih file rekaman dari folder `DataLog/` (atau lokasi lain).
- File harus memiliki metadata dan header data yang sesuai format tab Live (lihat §3.6). Parser memakai `live_csv_io.parse_logged_csv`.
- File `.mp4` pasangan (basename sama) dimuat otomatis jika ada di folder yang sama; gunakan **Load Video…** untuk memilih video lain.

### 4.1a Sinkron playhead video ↔ plot

- Panel **Rekaman video** di tengah tab menampilkan playback MP4 hasil rekaman kamera tab Live.
- Garis vertikal pink pada plot Force, Roll, dan Pitch mengikuti posisi pemutar video.
- **Rekaman baru (v2.3.0):** posisi sumbu waktu dihitung dari metadata `SyncCsvT0(s)` di footer CSV, dengan koreksi jeda antara Start Log dan sampel serial pertama (`SyncFirstSampleWall` − `SyncLogWallStart`).
- **File CSV lama** tanpa metadata sinkron: fallback `TimeStamp` baris pertama + detik video (sinkron kasar).

### 4.2 Plot waktu, video, dan statistik

Setelah berhasil dimuat:

- **Kiri:** tiga plot menampilkan rekaman penuh (Force, Roll, Pitch).
- **Tengah:** panel **Rekaman video** — playback MP4 (lihat §4.1a untuk sinkron playhead).
- **Kanan:** panel statistik dan pengaturan.
- Marker menandai titik ekstrem pada plot (force maksimum; roll/pitch min dan max) dengan label waktu.
- Panel kanan menampilkan ringkasan angka yang konsisten dengan marker, baris **TimeStamp Start/Stop Uji**, **Metode gaya Force**, **Mean (meanF)**, **Impulse (ImpF)**, dan ekstremum gaya (**Maksimum** = peakF, **Minimum** = minF) pada kolom Force, **frekuensi dominan** (Hz) per kanal, serta kartu **GAP REKAMAN CSV** (lihat §4.4 dan §4.6).

### 4.3 Analisa Setting — metode spektrum dan statistik Force

- Pilih **FFT** atau **Welch PSD** pada dropdown **Metode spektrum (statistik)**.
- Perubahan metode memperbarui **angka frekuensi dominan** pada kartu statistik (v2.3.0 tidak menampilkan plot spektrum visual).

Grup **Statistik Force (peakF / meanF / minF / ImpF)** — radio pemilihan cara menghitung parameter gaya pada kolom Force (region data uji):

| Pilihan | Makna singkat |
|---------|----------------|
| **Metode A — global (Amaro / Carrasco-Poyatos)** | Default. **peakF**, **meanF**, **minF** global region uji; **ImpF** = ∫F·dt trapesium seluruh region. Baris **t @ maks** / **t @ min** berisi timestamp; marker merah pada plot = peakF. |
| **Metode B — per siklus (Andrade)** | Valley (minF lokal) → segmentasi per kayuhan → peakF, meanF, minF, **ImpF** per siklus → rata-rata antar siklus. **ImpF** per siklus = ∫F·dt antar dua minF. **t @ maks/min** Force = **—**. Fallback global jika siklus tidak terdeteksi. |

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

- Tombol **Simpan statistik** menulis file CSV ke folder **`DataStatistik/`** tanpa dialog penyimpanan.
- Nama file: `<nama_file_csv_yang_dimuat>_DataStaistik.csv` (sufiks persis seperti di aplikasi).
- Isi ringkas:
  - Metadata (nama perenang, gaya renang, waktu ekspor, nama berkas sumber).
  - Baris **`Timestampstart (s)`** + nilai (waktu awal deret, sama dengan yang ditampilkan di panel statistik).
  - Tabel **`Metrik, Nilai, Satuan, Waktu (s)`** untuk metode dan metrik Force (**Metode_statistik_Force**, **Force_maksimum_peakF**, **Force_mean_meanF**, **Force_impulse_ImpF**, **Force_minimum_minF**; roll/pitch min/maks) — lihat §4.6.
  - Dua baris kosong, lalu tabel **`Metrik, Frekuensi Dominan (Hz), Metode`** dengan baris **Force**, **Roll**, **Pitch** (metode sama untuk ketiga saluran pada satu ekspor).
  - Blok **`Gap rekaman CSV (estimasi)`** — metode yang dipilih, Δt nominal, laju sampel efektif, sampel tercatat, sampel hilang, persen hilang; Metode A menyertakan jumlah gap; Metode B menyertakan sampel diharapkan.

### 4.6 Parameter gaya tethered — peakF, meanF, minF, ImpF (kolom Force)

Parameter ini hanya dihitung pada **saluran Force**, pada **region data uji** (region biru), dari deret yang sudah melalui koreksi aktif di **Analisa Setting** (batas bawah Force mentah, zero offset, koreksi sudut tali jika dicentang). Satuan gaya: **Kg**; impuls: **Kg·s** (literatur sering memakai **N·s** — konversi dengan × *g* jika diperlukan).

Cara perhitungan dipilih di **Statistik Force** (§4.3): **Metode A (global)** atau **Metode B (per siklus, Andrade)**.

| Baris tabel | Simbol | Metode A (global) | Metode B (Andrade) |
|-------------|--------|-------------------|---------------------|
| **Maksimum** | peakF | Maksimum global region uji | Rata-rata peakF per siklus |
| **Mean (meanF)** | meanF | Rata-rata semua sampel | Rata-rata meanF per siklus |
| **Impulse (ImpF)** | ImpF | ∫F·dt trapesium, seluruh region uji | Rata-rata ∫F·dt per siklus (minF→minF) |
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

1. Deteksi **minimum lokal** (*valley*) = penanda **minF** tiap kayuhan.
2. Segmentasi antar dua minF berurutan = satu siklus.
3. Per siklus: **peakF**, **meanF**, **minF**, dan **ImpF** (= ∫F·dt trapesium dalam segmen).
4. Nilai di tabel = **rata-rata** keempat parameter antar siklus terdeteksi.

Jika valley tidak cukup, nilai **fallback global** (Metode A) dengan catatan di baris metode.

**Referensi:**

- Andrade, R. M., Figueira, A. J., Metz, V., Amadio, A. C., & Cerca, J. (2018). *Interpretation of propulsive force in tethered swimming through principal component analysis.* **Revista Brasileira de Medicina do Esporte**, 24(3), 206–210. https://doi.org/10.1590/1517-869220182403175155

#### Hubungan ImpF dengan meanF (Metode A)

Kira-kira \(I \approx \overline{F} \times T\) untuk sampling reguler, dengan \(\overline{F}\) = meanF dan \(T\) = durasi region uji; trapesium pada Δt tidak seragam memberi perbedaan kecil.

#### Ekspor DataStatistik

Blok metrik Force mencantumkan **Metode_statistik_Force**, opsional **Jumlah_siklus_Force_Andrade**, serta **Force_maksimum_peakF**, **Force_mean_meanF**, **Force_impulse_ImpF**, **Force_minimum_minF** sesuai metode aktif.

---

## 5. Tab Analisa multifile

### 5.0 Batang alat

- **Baris pertama** (kiri ke kanan): **Add file** (biru) → **Simpan tabel ke CSV** (abu-abu) → **Plot data** (hijau) → *ruang fleksibel* → label **Hapus kolom** + combo + **Clear tabel** (merah).
- **Baris kedua:** **Metode spektrum** (FFT / Welch PSD); mengubahnya menghitung ulang semua kolom tabel.

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

### 5.4 Hapus kolom

- Pilih **Kolom 1** … **Kolom 5** atau **Semua kolom**, lalu **Clear tabel** (tombol merah) untuk mengeluarkan berkas dari daftar dan memperbarui tabel.

### 5.5 Plot perbandingan

- Tombol hijau **Plot data** membuka **jendela terpisah** (non-modal).
- Di jendela tersebut: dropdown **Metrik** (force/roll/pitch ekstremum dan frekuensi dominan per saluran), dropdown **Gaya plot** — **Garis + penanda** (default), **Diagram batang**, atau **Titik saja**.
- Sumbu X = urutan kolom/berkas (label tick mengikuti nama perenang atau nama file); data selalu mengikuti **Metode spektrum** yang dipilih di tab (FFT / Welch).
- Mengganti metrik atau gaya memperbarui gambar secara langsung.

### 5.6 Simpan tabel ke CSV

- Tombol **Simpan tabel ke CSV** menulis berkas ke folder **`TableMultiFile/`** (tanpa dialog *Save As*).
- Nama file: `ddmmyy_HHMM_TableMultiFile.csv` (cap waktu lokal + sufiks `_TableMultiFile`).
- Isi CSV mengikuti **tampilan tabel** (termasuk header multi-baris sebagai beberapa baris awal berkas).

---

## 6. Folder kerja

| Folder / berkas | Fungsi |
|-----------------|--------|
| `DataLog/` | Rekaman CSV dan video `.mp4` dari tab Live (diabaikan Git sesuai `.gitignore` proyek) |
| `DataStatistik/` | Ekspor statistik dari tab Analisa |
| `TableMultiFile/` | Ekspor tabel tab Analisa multifile |
| `live_csv_io.py` | Header + parser CSV rekaman + `LogSyncMeta` |
| `live_camera_core.py` | Pemindaian kamera |
| `live_camera_panel.py` | Panel kamera tab Live |
| `analyze_video_panel.py` | Pemutar video tab Analisa |
| `analyze_single_file_tab.py` | Tab Analisa (plot + video + statistik + ekspor) |
| `analyze_metrics_core.py` | Metrik rekaman + spektrum (multifile) |
| `analyze_multi_file_tab.py` | Tab Analisa multifile |
| `requirements.txt` | Daftar dependensi Python (termasuk OpenCV) |
| `UserManual_Force_Motion_v2.3.0.md` | Manual ini (Markdown) |
| `UserManual_Force_Motion_v2.3.0.pdf` | Manual ini (PDF, opsional) |
| `../md_to_pdf_Force_Motion.py` | Skrip konversi MD → PDF (folder induk `Force_Motion/Python`) |

---

## 7. Membuat / memperbarui PDF manual

Aplikasi **Help** membuka PDF. PDF dihasilkan dari Markdown dengan skrip `md_to_pdf_Force_Motion.py` (pustaka **markdown** dan **xhtml2pdf**), berada di folder **`Force_Motion/Python`**.

Dari folder `Force_Motion/Python`:

```text
pip install markdown xhtml2pdf
python md_to_pdf_Force_Motion.py -i Swimmer_Force_Motion_Monitoring_v2.3.0/UserManual_Force_Motion_v2.3.0.md -o Swimmer_Force_Motion_Monitoring_v2.3.0/UserManual_Force_Motion_v2.3.0.pdf
```

Tanpa opsi, skrip bawaan masih mengarah ke manual **v1.0.0** di folder yang sama; untuk v2.3.0 gunakan `-i` dan `-o` seperti di atas.

---

## 8. Pemecahan masalah

| Gejala | Tindakan |
|---------|----------|
| Port tidak muncul | Cabut/colok USB, klik **Refresh Ports**, periksa driver (mis. CP210x, CH340). |
| Connect gagal | Pastikan port tidak dipakai program lain; coba baud yang sesuai firmware. |
| Plot kosong | Periksa format baris (empat atau lima angka, koma); pastikan firmware mengirim newline. |
| Baterai tampil `—` | Perangkat mungkin hanya mengirim empat kolom; LoRa Receiver mengirim lima kolom. |
| Load CSV gagal di Analisa | Pastikan file dari tab Live yang sama (metadata + header persis). |
| Video tidak dimuat otomatis | Pastikan `.mp4` ada di folder yang sama dengan CSV dan basename cocok; atau gunakan **Load Video…**. |
| Rekam video gagal saat Start Log | Aktifkan **Mulai preview** kamera sebelum Start Log; periksa instalasi `opencv-python`. |
| Kamera tidak terdeteksi | Coba **Pindai kamera** ulang; di Windows pastikan DroidCam memakai mode yang kompatibel MSMF. |
| Help tidak membuka PDF | Jalankan §7; pastikan `UserManual_Force_Motion_v2.3.0.pdf` ada di folder aplikasi v2.3.0. |
| Error import `numpy` / `scipy` / `cv2` | Instal dependensi (lihat §1 atau `requirements.txt`). |

---

## 9. Versi dokumen

- **Manual:** selaras dengan aplikasi **v2.3.0** (kamera Live, video Analisa, sinkron playhead, baterai Live, gap rekaman CSV Metode A/B; frekuensi dominan di statistik tanpa plot spektrum visual).
- Ringkasan perubahan antar versi ada di `Force_Motion/Python/Changelog.md` dan docstring `Swimmer_Force_Motion_Monitoring_v2.3.0.py`.

---

## 10. Referensi

- [NotebookLM — Swimmer Force Motion Monitoring](https://notebooklm.google.com/notebook/cbd512b8-4457-4a1f-937f-a022df17f8e5?authuser=1) — materi referensi tambahan terkait aplikasi dan analisa force/motion (memerlukan akun Google untuk membuka).
- [1080Motion — Swimming performance and monitoring training with new technologies](https://www.1080motion.com/webinars/swimming-performance-and-monitoring-training-with-new-technologies) — webinar tentang teknologi pemantauan performa dan latihan renang di lingkungan air (Bjørn Harald Olstad, Norwegian School of Sport Sciences, 2020).

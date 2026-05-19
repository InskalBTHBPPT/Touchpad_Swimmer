# Estimasi harga pengembangan software (referensi internal)

Dokumen ini merangkum **pertanyaan yang diajukan** terkait penagihan ke klien untuk pengembangan aplikasi sejenis proyek di repositori ini, beserta **jawaban dan dasar penalaran** yang dipakai. Angka bersifat **perkiraan pasar Indonesia untuk software custom laboratorium / instrumentasi**, bukan penawaran resmi dan bukan jaminan harga final.

---

## 1. Pertanyaan awal (dirangkum ulang secara eksplisit)

**Konteks yang Anda tunjuk:**

- Folder / versi aplikasi: `Touchpad_Timer_Pressure/Python/Versi_3.1.0`  
  - Aplikasi desktop pemantauan sentuhan touchpad perenang dengan akuisisi data melalui **NI Data Acquisition (NI-DAQmx)**, visualisasi real-time, deteksi sentuhan, pencatatan CSV, dan tab analisis.
- Folder / versi aplikasi: `Force_Motion/Python/Swimmer_Force_Motion_Monitoring_v2.1.0`  
  - Aplikasi desktop pemantauan **gaya (force)** dan **orientasi gerak (roll/pitch)** lewat **port serial USB**, rekaman CSV, analisis deret waktu, analisis spektral (FFT / Welch), serta mode analisis **multi-file** dengan tabel dan plot perbandingan.

**Pertanyaan Anda (inti):**

1. Untuk **mengembangkan aplikasi dengan ruang lingkup dan kedalaman teknis seperti kedua contoh di atas**, berapa **perkiraan harga dalam Rupiah (IDR)** yang **wajar ditagihkan ke klien**?
2. **Apa dasar** rekomendasi tersebut (mengapa rentangnya demikian, faktor apa yang memengaruhi)?

**Implisit yang perlu dijawab agar penawaran tidak salah tafsir:**

- Estimasi ini mengacu pada **pekerjaan software** (rekayasa aplikasi, integrasi driver/API yang relevan di sisi PC, antarmuka, alur data, validasi format file, dokumentasi pengguna), **bukan** pengadaan sensor, DAQ, mikrokontroler, atau infrastruktur fisik lainnya — kecuali disepakati lain secara kontrak.

---

## 2. Jawaban singkat (angka perkiraan)

Berikut **rentang kasar** yang masuk akal di pasar Indonesia untuk **proyek custom** dengan kompleksitas setara (dibangun dari awal dengan requirement jelas–sedang, pengujian di Windows, dan manual pengguna), **hanya software**:

| Ruang lingkup | Rentang IDR (indikatif) |
|----------------|-------------------------|
| **Satu** aplikasi setara **Touchpad Monitor v3.1.0** (NI DAQ + live + deteksi + logging + tab analisis + proteksi format CSV + manual) | **Rp 18.000.000 – Rp 55.000.000** |
| **Satu** aplikasi setara **Force Motion Monitoring v2.1.0** (serial + live + logging + analisis satu file + spektrum + analisis multi-file + ekspor tabel + manual) | **Rp 15.000.000 – Rp 45.000.000** |
| **Keduanya** sebagai dua produk / dua jalur fitur terpisah, termasuk stabilisasi, dokumentasi, dan serah terima yang wajar | **Rp 35.000.000 – Rp 95.000.000** |

**Cara membaca rentang:**

- **Ujung bawah** biasanya realistis bila: spesifikasi sudah matang, sedikit perubahan desain selama proyek, perangkat keras dan driver di sisi klien sudah stabil, minim kunjungan lapangan, dan iterasi pasca–UAT terbatas.
- **Ujung atas** biasanya realistis bila: requirement bergerak, integrasi di banyak varian PC/OS, debugging intensif dengan perangkat nyata, pelatihan pengguna, garansi bugfix beberapa bulan, atau tuntutan dokumentasi/formalitas tambahan.

Angka ini **bukan** kuotasi tetap; tarif final harus mengikuti **kebijakan Anda** (jam engineer, margin risiko, overhead organisasi, dan pajak).

---

## 3. Klarifikasi penting: hanya software (di luar hardware)

**Pertanyaan lanjutan Anda:** apakah estimasi tersebut **di luar hardware**, yaitu **hanya software**?

**Jawaban:** **Ya.** Rentang di atas dimaksudkan untuk **jasa / produk software** pada sisi aplikasi desktop (kode, build/paket distribusi sederhana jika ada, pengujian fungsional, dokumentasi).

**Secara eksplisit biasanya *tidak* termasuk** (kecuali ditulis di kontrak):

- Pembelian atau penyewaan **perangkat keras** (mis. modul NI DAQ, sensor tekanan, ESP32, kabel, mechanical fixture).
- **Lisensi pihak ketiga** yang dibebankan ke proyek (mis. komponen lisensi NI tertentu jika berbayar menurut kebijakan NI dan entitas pembeli).
- **PC khusus** atau upgrade workstation klien.
- Kalibrasi metrologi resmi **di laboratorium akreditasi** (jika klien membutuhkan sertifikat traceable — itu sering proyek terpisah).

**Yang “software” tetapi sering jadi add-on berbayar** (transparankan di penawaran):

- **Kunjungan instalasi** di lokasi klien, jam pelatihan tambahan, atau integrasi dengan jaringan/kebijakan IT klien.
- **Periode dukungan** (mis. 3/6/12 bulan bugfix minor) di luar garansi singkat.
- **Fitur baru** setelah baseline disetujui (change request).

**Kalimat contoh untuk lampiran penawaran:**

> *Harga mencakup pengembangan, pengujian, dan serah terima aplikasi sesuai lampiran ruang lingkup. Harga tidak termasuk perangkat keras, lisensi pihak ketiga, infrastruktur jaringan, serta kalibrasi perangkat ukur di luar lingkup software.*

---

## 4. Dasar rekomendasi (mengapa rentangnya masuk akal)

Bagian ini menjelaskan **logika estimasi** agar bisa dipertahankan dalam diskusi dengan klien atau manajemen internal.

### 4.1 Indikator ukuran dan struktur kode (proxy kompleksitas)

Perkiraan ukuran berkas Python di folder referensi (perkiraan dari penghitungan baris pada snapshot repositori saat estimasi dibuat):

| Lokasi | Berkas utama / modul | Keterangan |
|--------|----------------------|------------|
| `Touchpad_Timer_Pressure/Python/Versi_3.1.0/` | `Swimmer_Monitor_v3.1.0.py` (dan varian nama terkait) | Satu modul besar aplikasi lengkap (~**2.700+** baris per berkas inti) — GUI, worker DAQ, deteksi, CSV, analisis. |
| `Force_Motion/Python/Swimmer_Force_Motion_Monitoring_v2.1.0/` | `Swimmer_Force_Motion_Monitoring_v2.1.0.py`, `analyze_single_file_tab.py`, `analyze_multi_file_tab.py`, `analyze_metrics_core.py`, `live_csv_io.py` | Total urutan **~2.800+** baris tersebar di **beberapa modul** — pemisahan tanggung jawab (live vs analisis vs utilitas). |

**Interpretasi:** Ini bukan skrip sekali pakai, melainkan **aplikasi desktop** dengan banyak layar/logika, alur file, dan cabang fitur. Proxy baris kode **bukan** pengganti estimasi jam resmi, tetapi membantu menjelaskan bahwa ini setara **banyak minggu** kerja engineer berpengalaman jika dibangun dari nol.

### 4.2 Faktor teknis yang menaikkan biaya (risiko dan jam kerja)

1. **Real-time dan konkurensi**  
   - Akuisisi data tidak boleh memblokir GUI. Pola umum: **thread / worker** untuk DAQ atau pembacaan serial berkala, **queue** untuk penulisan disk, **timer** untuk refresh plot.  
   - Bug pada area ini sering **intermittent** (race condition, backpressure buffer), sehingga debugging memakan waktu.

2. **Integrasi perangkat di sisi PC**  
   - **NI-DAQmx:** pemilihan channel, terminal configuration, range tegangan, sampling rate, penanganan error driver, perilaku berbeda antar kartu/OS.  
   - **Serial:** parsing baris, encoding, reconnect, variasi baud/format firmware.  
   Keduanya menambah **risiko integrasi** yang harus dihargai dalam penawaran atau buffer waktu.

3. **Logika domain pengukuran**  
   - Contoh: deteksi sentuhan dengan **Schmitt / hysteresis**, konversi **Volt → Kg** dengan skala per kanal, konsistensi antara **live** dan **analisis offline** dari CSV.  
   Kesalahan di sini bukan sekadar “UI jelek”, tetapi bisa berarti **kesimpulan penelitian salah**.

4. **Fitur analitik lanjutan**  
   - Pada Force Motion: **FFT / Welch**, ringkasan statistik, **multi-file** dengan tabel dan dialog plot — ini menambah dependensi numerik (`numpy`/`scipy`), validasi input, dan edge case (file pendek, sampling tidak seragam, NaN).

5. **Kualitas “produk” untuk pengguna akhir**  
   - Tab terpisah (Live vs Analisa), folder output (`DataLog/`, `DataStatistik/`, dll.), validasi header CSV, dialog About/Help, **manual pengguna (Markdown/PDF)**.  
   Ini meningkatkan **jam kerja non-fitur-inti** yang tetap bernilai bagi klien.

### 4.3 Cara menghitung ke IDR (metode yang bisa dijelaskan ke klien)

Salah satu pendekatan yang paling mudah diaudit:

1. **Estimasi jam** untuk membangun ulang ruang lingkup serupa dari nol (desain, implementasi, uji, perbaikan, dokumentasi).  
   - Contoh urutan besar untuk **dua** aplikasi sejenis: **~150–400 jam** total, sangat tergantung pengalaman tim, reusabilitas internal, dan seberapa “beku” spesifikasi.
2. **Kalikan tarif jam** yang Anda tetapkan (mis. biaya internal vs harga jual, peran senior/junior).  
3. **Tambahkan margin risiko** (mis. 15–35%) untuk integrasi hardware nyata, perubahan requirement, dan dukungan pasca-UAT singkat.

Contoh ilustrasi numerik (bukan rekomendasi tarif):

- 250 jam × Rp 150.000/jam = **Rp 37.500.000**  
- 250 jam × Rp 250.000/jam = **Rp 62.500.000**  

Dengan margin risiko dan dokumentasi, mudah mencapai rentang yang tercantum di bagian 2.

### 4.4 Faktor yang menurunkan atau menaikkan harga relatif rentang

**Dapat menurunkan harga:**

- Klien membeli **lisensi / kustomisasi** dari basis kode yang **sudah ada** (bukan greenfield penuh).  
- Tidak perlu spektrum / multi-file / proteksi CSV ketat — ruang lingkup dipangkas.  
- Satu engineer senior dengan template internal (plot, serial, struktur tab) sehingga jam turun drastis.

**Dapat menaikkan harga:**

- Validasi formal, SOP, atau **tanda tangan** persetujuan dari pihak ketiga.  
- **Multi-site deployment**, kebijakan keamanan ketat, atau build installer bertanda tangan.  
- **Maintenance tahunan** dengan SLA respons cepat.

---

## 5. Checklist ruang lingkup untuk menghindari salah ekspektasi

Sebelum memberi angka pasti ke klien, sebaiknya jawaban berikut sudah jelas:

- [ ] Apakah target OS hanya **Windows 10/11** 64-bit?  
- [ ] Versi Python / cara distribusi (installer, zip, conda, internal saja)?  
- [ ] Daftar perangkat uji (tipe DAQ / firmware serial) yang menjadi **definisi “selesai”**.  
- [ ] Format CSV final (header, metadata) dan contoh file emas (golden files).  
- [ ] Apakah **pelatihan** termasuk (berapa jam, online/offline)?  
- [ ] Periode **garansi bugfix** dan apa yang dianggap bug vs permintaan fitur baru (lihat **Bagian 6**).  
- [ ] Untuk **add-on** setelah baseline, gunakan **Bagian 7** sebagai acuan order-of-magnitude sebelum memberi penawaran resmi.

---

## 6. Pasca penyerahan & pembayaran: fitur tambahan vs perbaikan bug

### 6.1 Pertanyaan (dirangkum)

Setelah aplikasi **diserahkan** dan **dibayar**, klien meminta **tambahan fitur**. Apakah penanganannya **tergantung seberapa kompleks** fitur barunya? Sebagai kebijakan internal, **perbaikan bug** dianggap **gratis** (tidak ditagih terpisah).

### 6.2 Jawaban prinsipil

| Jenis permintaan | Umumnya | Catatan |
|------------------|---------|---------|
| **Fitur baru / perluasan fungsi** | **Berbayar** (change request / amendment kontrak / penawaran tambahan) | Bukan kelanjutan otomatis dari proyek baseline; membutuhkan estimasi jam, uji regresi, dan seringnya pembaruan manual. |
| **Perbaikan bug** | Menurut kebijakan Anda: **boleh gratis** dalam batas wajar | Agar “gratis” tidak membuka lubang tanpa batas, tetapkan definisi **bug** vs **bukan bug** dan **jendela waktu** garansi (opsional). |

**Apakah harga fitur tambahan tergantung kompleksitas?** **Ya, secara langsung.** Kompleksitas memengaruhi **jam kerja**, **risiko regresi** (fitur lama ikut rusak), **pengujian**, dan **dokumentasi**. Praktik yang rapi: sama seperti proyek awal — pecah menjadi tugas, estimasi jam, kalikan tarif, tambahkan margin jika ada ketidakpastian (mis. integrasi perangkat atau format file baru).

### 6.3 Mengapa fitur tambahan sebaiknya tidak “dibundel gratis” dengan proyek lama

- **Baseline kontrak** biasanya mengunci **ruang lingkup** (fitur, alur, format file, definisi selesai / UAT). Fitur di luar itu adalah **perubahan produk**, bukan penyelesaian utang deliverable.
- Setiap penambahan kode meningkatkan **biaya pemeliharaan** di masa depan (dua cabang logika, lebih banyak kasus uji).
- Jika semua permintaan pasca-bayar diperlakukan sama dengan bugfix gratis, tim akan **kehabisan kapasitas** tanpa pendanaan yang jelas.

### 6.4 Membedakan “bug” vs “bukan bug” (agar kebijakan “bugfix gratis” tetap adil)

**Bug (kandidat gratis, sesuai garansi yang Anda tetapkan):** perilaku aplikasi **tidak sesuai** dengan **spesifikasi / SOW / UAT** yang sudah disetujui pada saat serah terima, dan dapat **direproduksi** dengan langkah yang jelas pada lingkungan yang disepakati (OS, versi aplikasi, contoh data).

**Bukan bug — biasanya diperlakukan sebagai fitur atau konsultasi berbayar:**

- “Kami ingin **grafik lain**”, “**export** ke format baru”, “**filter** tambahan”, “**laporan** ringkas otomatis” — itu **peningkatan produk**.
- “Dulu kami **kira** begini” padahal tidak tertulis di ruang lingkup — itu **klarifikasi requirement**, bukan bug.
- Permintaan kompatibilitas dengan **OS / driver / perangkat keras baru** yang **tidak** ada di daftar dukungan kontrak asli.
- Perbaikan akibat **data atau prosedur** di sisi klien yang tidak sesuai asumsi (kecuali aplikasi seharusnya menolak dengan pesan jelas dan itu belum ada — bagian kedua bisa masuk bug UX kecil).

Dokumentasikan definisi ini di **email penawaran** atau **lampiran SOW** agar tidak ada perdebatan subjektif.

### 6.5 Kebijakan “bugfix gratis” yang tetap sehat untuk bisnis

Kebijakan Anda: **bugfix dianggap gratis** — itu **bisa dilakukan** dan sering meningkatkan kepercayaan klien, asalkan dibatasi agar tidak menjadi **dukungan tanpa akhir**.

**Rekomendasi praktis (pilih yang cocok dengan budaya Anda):**

1. **Jendela garansi waktu** — misalnya **30 / 60 / 90 hari** atau **3–6 bulan** setelah serah terima & pembayaran, hanya untuk bug terhadap baseline yang ditandatangani. Setelah itu, bugfix bisa **retainer** atau **per tiket**.
2. **Cakupan “gratis”** — perbaikan **di dalam codebase yang diserahkan**, tanpa fitur baru. Jika perbaikan membutuhkan **refactor besar** karena klien mengubah lingkungan, negosiasikan add-on atau jam khusus.
3. **Antrian** — bugfix gratis boleh **tidak** mendahului proyek berbayar lain; komunikasikan ETA yang wajar.
4. **Versi rilis** — setelah bugfix, beri **nomor versi** (semver) agar jejak perubahan jelas.

Jika Anda ingin **bugfix gratis tanpa batas waktu**, itu masih mungkin secara moral untuk hubungan kecil, tetapi secara komersial berisiko; alternatifnya adalah **kontrak pemeliharaan tahunan** (nominal tetap per bulan/tahun) yang secara eksplisit mencakup bug minor + jam konsultasi terbatas.

### 6.6 Alur bisnis yang sederhana untuk fitur tambahan

1. Klien mengirim permintaan tertulis (email/tiket).  
2. Anda klasifikasi: **bug** vs **fitur** vs **dukungan/pelatihan**.  
3. Untuk **fitur**: balas dengan **estimasi jam + harga + dampak jadwal**; minta persetujuan tertulis sebelum coding.  
4. Setelah disetujui: kerjakan, uji regresi singkat pada modul terkait, serah terima catatan rilis (changelog).

---

## 7. Indikatif harga add-on (pasca-baseline): UI, analisis, ekspor, dll.

Bagian ini menjawab kebutuhan praktis: **“kalau cuma UI kecil / nambah alur analisis / export baru, kira-kira berapa?”** Angka di bawah adalah **order-of-magnitude untuk change request setelah proyek utama selesai**, dengan asumsi codebase sudah ada dan tim sudah familier dengannya. **Bukan harga tetap** — selalu konversi ke **estimasi jam × tarif jam Anda ± margin risiko**.

### 7.1 Asumsi di balik angka (agar tidak salah pakai)

- Tarif implisit pada rentang di bawah mengacu pada pasar **freelance / lab kecil–menengah Indonesia** pada urutan **~Rp 150.000 – Rp 350.000 per jam engineering** untuk pekerjaan Python/Qt/pyqtgraph; tarif perusahaan atau specialist NI/DAQ bisa lebih tinggi.
- Rentang memasukkan sedikit **uji regresi** dan **komunikasi**; tidak termasuk kunjungan fisik multi-kota atau formalitas audit berat.
- **“Gratis”** untuk UI sangat kecil adalah **kebijakan niaga** (goodwill / hubungan jangka panjang), **bukan** standar industri wajib — jika diberikan, sebaiknya **dibatasi** (mis. maksimal **1–2 jam** kerja equivalent per kuartal, atau hanya untuk klien dengan kontrak pemeliharaan).

### 7.2 UI dan pengalaman pengguna (post-delivery)

| Kelas perubahan | Contoh konkret | Umumnya gratis? | Indikatif add-on (IDR) |
|-----------------|------------------|-----------------|-------------------------|
| **Mikro** | Perbaikan typo label, tooltip, judul jendela, ikon sederhana, default lebar kolom tabel | Boleh **gratis** sebagai goodwill **jika** sangat kecil dan jarang; atau masuk **retainer** | Jika ditagih formal: **Rp 0 – Rp 2.000.000** |
| **Kecil** | Penambahan 1–2 field input + simpan ke `config.json`; pengaturan font/warna; satu tombol yang memanggil aksi sederhana yang sudah ada | **Biasanya berbayar** (sudah “fitur”, bukan bug) | **Rp 2.000.000 – Rp 8.000.000** |
| **Menengah** | Satu **panel/grup** UI baru di tab yang ada; reflow layout besar; tema gelap/terang; validasi input baru yang menyentuh banyak widget | Berbayar | **Rp 8.000.000 – Rp 20.000.000** |
| **Besar** | **Tab baru** kosong + navigasi; redesain struktur menu; aksesibilitas menyeluruh; multi-bahasa (i18n) tahap pertama | Berbayar | **Rp 20.000.000 – Rp 45.000.000+** |

### 7.3 Alur analisis & logika pengolahan data

| Kelas perubahan | Contoh konkret | Indikatif add-on (IDR) |
|-----------------|------------------|-------------------------|
| **Ringan** | Satu **metrik turunan** dari data yang sudah ada; satu plot tambahan memakai pipeline yang sama; filter sederhana pada tabel yang sudah ada | **Rp 5.000.000 – Rp 15.000.000** |
| **Menengah** | **Alur analisis baru** di tab yang ada (mis. blok statistik tambahan, satu jenis overlay plot baru dengan opsi UI); parser CSV untuk **varian header** terbatas | **Rp 15.000.000 – Rp 35.000.000** |
| **Berat** | Tab **Analisa** baru dengan interaksi penuh; **multi-file** dengan aturan baru; penambahan opsi **spektrum** (windowing, detrend, dsb.) + validasi; sinkronisasi metrik antara live dan offline | **Rp 30.000.000 – Rp 75.000.000** |
| **Sangat berat** | Mesin analisis yang **mengubah model data** (format sesi, timestamp, kalibrasi global), migrasi file lama, atau risiko **inkompatibilitas** dengan data historis klien | **Rp 50.000.000 – Rp 120.000.000+** (sering perlu fase discovery) |

### 7.4 Ekspor, laporan, dan interoperabilitas

| Kelas perubahan | Contoh | Indikatif add-on (IDR) |
|-----------------|--------|-------------------------|
| **Ringan** | Ekspor **CSV** tambahan dengan kolom tetap; menyalin tabel ke clipboard | **Rp 3.000.000 – Rp 10.000.000** |
| **Menengah** | Template **Excel** (.xlsx) dengan beberapa sheet; gambar **PNG/SVG** plot resolusi tinggi otomatis | **Rp 10.000.000 – Rp 28.000.000** |
| **Berat** | **PDF laporan** bergaya (kop surat, footer, batch multi-sesi); integrasi **REST API** ke server klien (auth, error handling) | **Rp 25.000.000 – Rp 70.000.000+** |

### 7.5 Akuisisi data & perangkat (sisi PC)

| Kelas perubahan | Contoh | Indikatif add-on (IDR) |
|-----------------|--------|-------------------------|
| **Ringan** | Opsi baud/port tambahan; preset nama perangkat; logging interval flush baru | **Rp 3.000.000 – Rp 12.000.000** |
| **Menengah** | Dukungan **perangkat serial kedua** paralel; parser format baris alternatif (satu firmware) | **Rp 12.000.000 – Rp 30.000.000** |
| **Berat** | Jalur akuisisi **NI-DAQ** tambahan (kanal/rate berbeda) + UI konfigurasi + pengujian di hardware | **Rp 25.000.000 – Rp 65.000.000+** |

### 7.6 Dokumentasi, pelatihan, dan serah terima ulang

| Item | Indikatif (IDR) |
|------|-----------------|
| Pembaruan **manual pengguna** singkat (1–3 halaman setara) mengikuti fitur kecil | **Rp 1.500.000 – Rp 6.000.000** |
| Revisi manual **menyeluruh** + tangkapan layar baru | **Rp 6.000.000 – Rp 18.000.000** |
| **Sesi pelatihan online** per jam (di luar paket awal) | **Rp 750.000 – Rp 2.500.000 / jam** (tergantung senioritas) |

### 7.7 Konversi cepat dari jam kerja ke IDR (untuk kalkulator internal)

Gunakan tabel ini jika Anda lebih nyaman mengestimasi **jam** dulu:

| Jam engineer (per CR) | @ Rp 200.000/jam | @ Rp 300.000/jam |
|-------------------------|------------------|------------------|
| 4 jam | Rp 800.000 | Rp 1.200.000 |
| 16 jam | Rp 3.200.000 | Rp 4.800.000 |
| 40 jam | Rp 8.000.000 | Rp 12.000.000 |
| 100 jam | Rp 20.000.000 | Rp 30.000.000 |

Lalu tambahkan **margin risiko** (mis. +15–30%) jika CR menyentuh thread real-time, driver, atau format data historis.

---

## 8. Penutup

Dokumen ini menyatukan **pertanyaan Anda** tentang estimasi penagihan untuk software sejenis **Touchpad v3.1.0** dan **Force Motion v2.1.0**, jawaban rentang IDR, penegasan **software-only**, **dasar teknis dan komersial**, **kebijakan pasca-serah terima** (fitur tambahan berbayar menurut kompleksitas; bugfix gratis dengan batas definisi dan waktu yang disarankan), serta **indikatif add-on** per kategori (**Bagian 7**). Sesuaikan angka dengan **tarif internal**, **pajak**, dan **risiko proyek** Anda sebelum dikirim sebagai penawaran resmi.

*Dibuat sebagai catatan referensi di root repositori `Swimmer_Monitoring`.*

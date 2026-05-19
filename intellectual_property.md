# Kekayaan intelektual (KI) untuk aplikasi desktop di repositori ini — kerangka Indonesia

**Nama berkas:** `intellectual_property.md` (ejaan baku *intellectual*; bukan *intelectual*).

**Peringatan penting:** isi dokumen ini adalah **ringkasan edukatif umum**, bukan **nasihat hukum** (bukan pengganti konsultasi dengan **advokat / konsultan HKI** yang berwenang di Indonesia). Putusan konkret bergantung pada fakta (siapa yang membuat, kontrak kerja, kontrak dengan klien, apakah ada rahasia dagang, dsb.).

**Konteks produk:** dua aplikasi desktop Python (PySide6, pyqtgraph, dsb.) untuk pemantauan/merekam data laboratorium — **Touchpad / NI-DAQ** dan **Force–Motion / serial + analisis** — seperti yang ada di folder proyek terkait di repositori ini.

---

## 1. Jawaban singkat: “masuknya ke apa?”

Untuk **kode sumber, struktur program, antarmuka pengguna sebagai ekspresi karya**, serta **dokumentasi teknis/manual** yang bersifat karya tulis, **penggolongan utama** di sistem hukum Indonesia biasanya adalah:

| Jenis perlindungan | Apakah relevan untuk kedua aplikasi ini? | Catatan singkat |
|--------------------|------------------------------------------|------------------|
| **Hak cipta** (*copyright*) | **Ya — ini yang paling utama** | Program komputer di Indonesia diperlindungi sebagai **ciptaan** (karya). Hak timbul **otomatis** saat ciptaan diwujudkan (tanpa wajib daftar), meski **pendaftaran** tetap berguna sebagai **alat bukti**. |
| **Paten** | **Umumnya tidak** untuk “aplikasi utuh” semacam ini | Paten untuk **penemuan** yang baru, mengandung langkah inventif, dan dapat diterapkan di industri. **Software “sebagai kode/UI”** jarang memenuhi syarat paten kecuali ada **klaim penemuan teknis** yang sangat spesifik dan memenuhi uji paten. |
| **Rahasia dagang** | **Bisa — pelengkap**, untuk know-how | Alur kalibrasi internal, parameter bisnis, data klien, atau metode yang **sengaja tidak dipublikasikan** dan dilindungi prosedur kerahasiaan. |
| **Merek** | **Bisa — untuk nama/logo produk**, bukan untuk kode | Melindungi tanda pembeda barang/jasa (nama aplikasi, logo) agar tidak disalahgunakan pihak lain di kelas jasa tertentu. |
| **Desain industri** | **Hampir tidak relevan** untuk software | Lebih ke bentuk produk fisik/penampilan produk. |

Jadi, dalam percakapan sehari-hari: **kedua aplikasi itu “masuk hak cipta”** (sebagai **program komputer** dan sering kali juga **dokumentasi** sebagai karya tulis). **Paten** hanya masuk pertimbangan jika ada **inti teknis penemuan** terpisah yang ingin didaftarkan secara khusus — jangan asumsikan seluruh aplikasi otomatis “bisa paten”.

---

## 2. Dasar hukum (Indonesia) — level referensi

### 2.1 Hak cipta

- **Undang-Undang Hak Cipta** (yang berlaku per pembaruan terakhir yang Anda pakai sebagai acuan bisnis — umumnya di lingkungan praktik merujuk ke **UU Hak Cipta** yang mengatur ciptaan, termasuk ketentuan tentang **program komputer**).
- Program komputer diperlindungi sebagai **ciptaan**; yang dilindungi antara lain **ekspresi** kode/dokumentasi, bukan ide/gagasan abstrak atau algoritma dalam arti murni “ide saja” (pembatasan ini sejalan dengan doktrin umum hak cipta: perlindungan pada **wujud**, bukan pada ide bebas).

**Implikasi praktis untuk repo Anda:**

- Berkas `.py`, skema GUI, teks manual, grafik yang dibuat sebagai karya, dapat menjadi objek **hak cipta**.
- **Lisensi** (proprietary, internal lab, MIT, dsb.) mengatur **siapa boleh menyalin/memodifikasi/mendistribusikan**.

### 2.2 Paten

- **Undang-Undang Paten** (peraturan paten yang berlaku saat ini di Indonesia mengatur persyaratan **baru**, **langkah inventif**, **dapat diterapkan di industri**, dan larangan subjek tertentu).
- Banyak yurisdiksi membatasi paten untuk “program komputer **sebagai such**”; di Indonesia, praktiknya **paten software** sering terkait **klaim teknis** yang benar-benar penemuan perangkat/proses — bukan sekadar menampilkan grafik dari sensor.

**Contoh yang *mungkin* masuk ranah paten (hanya ilustrasi, bukan analisis untuk kasus Anda):**

- Metode pengukuran/kalibrasi **baru** dengan bukti kebaruan dan inventif yang kuat, diiklaim sebagai **proses** atau **sistem** teknis tertentu.

**Yang biasanya *tidak* layak paten sendiri:**

- Tumpukan teknologi umum: baca serial, plot time series, FFT/Welch standar, thread GUI, format CSV — kecuali ada **pemecahan teknis** yang benar-benar novel dan dapat dibuktikan.

### 2.3 Rahasia dagang

- Diatur dalam **peraturan perundang-undangan** tentang **transmisi data elektronik / rahasia dagang** (istilah dan nomor UU dapat diperbarui; pastikan dengan ahli hukum versi terkini).
- Cocok untuk **informasi rahasia** yang memiliki nilai ekonomi dan ditangani dengan kerahasiaan (NDA, kontrol akses repo, dsb.).

### 2.4 Merek

- **Undang-Undang Merek** (UU Merek yang berlaku).
- Berguna jika nama aplikasi dipasarkan dan ingin dicegah pihak ketiga memakai tanda serupa untuk jasa/software sejenis.

---

## 3. Memetakan ke dua aplikasi di repositori ini (secara konsep)

| Aspek | Touchpad / NI-DAQ | Force–Motion / serial |
|--------|-------------------|------------------------|
| **Hak cipta** | Kode Python, layout UI, integrasi `nidaqmx`, logika deteksi **sebagai ekspresi tertulis** dalam kode | Sama: kode, modul analisis, parser CSV, UI tab |
| **Paten** | Hanya jika ada **penemuan** terpisah yang didaftarkan; bukan default untuk seluruh aplikasi | Sama |
| **Rahasia dagang** | Parameter bisnis, SOP internal, konfigurasi rahasia klien | Kalibrasi/prosedur internal yang tidak dipublikasikan |
| **Merek** | Nama produk yang dipasarkan | Sama |

---

## 4. Hal yang sering salah paham

1. **“Sudah saya buat sendiri, otomatis bebas paten orang lain”** — tidak selalu. Hak cipta orang lain (pustaka, ikon berlisensi, cuplikan kode) tetap harus dipatuhi lisensinya.  
2. **“Daftar hak cipta wajib agar punya hak”** — di Indonesia, hak cipta timbul pada umumnya **tanpa** wajib daftar; pendaftaran membantu **pembuktian**.  
3. **“Satu paten untuk seluruh aplikasi”** — jarang realistis; paten adalah dokumen klaim yang sempit dan teknis.  
4. **Hubungan dengan klien/pemberi kerja** — siapa pemegang hak sering diatur **kontrak** (perjanjian kerja, SOW, perjanjian lisensi). Tanpa kontrak jelas, risiko sengketa meningkat.

---

## 5. Langkah praktis (bukan nasihat hukum)

- **Dokumentasikan** penulis, tanggal rilis, dan changelog (jejak karya).  
- **Perjanjian tertulis** dengan klien/karyawan tentang **pengalihan** atau **lisensi** hak cipta.  
- **Pilih lisensi** untuk dependensi (hati-hati GPL vs proprietary).  
- Jika ada merek dagang: pertimbangkan **pendaftaran merek** dengan konsultan.  
- Jika ada inti algoritme yang benar-benar novel dan bernilai strategis: diskusikan **kelayakan paten** dengan **konsultan paten**.

---

## 6. Lisensi pustaka vs “daftar HAKI” — apakah diperbolehkan?

**Peringatan:** bagian ini tetap **bukan nasihat hukum**. Verifikasi teks lisensi resmi setiap versi paket yang Anda pakai, plus **Syarat Penggunaan / EULA** untuk perangkat lunak **proprietary** (mis. driver/SDK vendor).

### 6.1 Rapikan dulu istilah “HAKI”

Di percakapan sehari-hari, “**HAKI**” dipakai sebagai payung besar. Di **lembaga / praktik administrasi** di Indonesia, yang umum dimaksud pengusaha adalah salah satu dari:

| Yang didaftarkan | Uraian singkat | Hubungannya dengan lisensi pustaka |
|------------------|----------------|-------------------------------------|
| **Hak cipta** (mis. program komputer) | Pendaftaran sebagai **alat bukti** pemegang hak atas **ciptaan Anda** | Bukan “izin” dari pustaka; **tetap** harus patuh lisensi pustaka untuk **distribusi** aplikasi. |
| **Merek** | Nama/logo dagang | Umumnya **tidak ditentukan** oleh lisensi open source pustaka (kecuali aturan merek pihak ketiga, mis. penggunaan logo **Qt**). |
| **Paten** | Penemuan teknis | **Terpisah** dari lisensi hak cipta pustaka; aturan paten dan **patent grant** di beberapa lisensi (mis. Apache 2.0) relevan jika Anda mempatenkan sesuatu yang bentrok dengan ekosistem — ini ranah konsultan paten. |

Jadi pertanyaan Anda perlu dipecah: **“daftar hak cipta atas aplikasi/kode kami”** vs **“daftar merek”** vs **“daftar paten”**.

### 6.2 Jawaban prinsipil untuk **pendaftaran hak cipta** atas aplikasi/kode Anda

Pada umumnya, **lisensi open source standar** (BSD, MIT, Apache, LGPL, dsb.) **tidak melarang** Anda untuk:

- memiliki **hak cipta** atas **ekspresi kode asli** yang Anda tulis; dan  
- **mendaftarkan** ciptaan tersebut di administrasi KI (mis. **hak cipta program komputer**), **selama** pengajuan tidak menyangkal kenyataan bahwa bagian tertentu adalah **karya pihak ketiga** yang tetap tunduk pada lisensinya.

Yang dilarang atau dibatasi oleh lisensi biasanya berkaitan dengan:

- **menyalin/memodifikasi/mendistribusikan** pustaka itu sendiri tanpa memenuhi syarat (atribusi, menyertakan teks lisensi, **kewajiban copyleft** pada turunan, dsb.);  
- **menggabungkan** (linking) dengan kode **GPL** lalu mendistribusikan binari **proprietary** tanpa memenuhi GPL — ini masalah **kepatuhan distribusi**, bukan secara otomatis larangan “mendaftar hak cipta” atas kode Anda, tetapi bisa membuat model bisnis/produk Anda **celah hukum** jika tidak dirancang benar.

**Inti:** pendaftaran hak cipta atas **karya Anda** ≠ “mendaftarkan PySide/numpy sebagai milik saya”. Dokumen pengajuan sebaiknya **jujur** tentang komposisi karya (deposit berupa snapshot repo / sumber yang disepakati mengikuti prosedur lembaga).

### 6.3 Dependensi yang tampak di proyek ini (ringkas, bukan audit lengkap)

**Force Motion `requirements.txt` (v2.1.0):** `PySide6`, `pyqtgraph`, `pyserial`, `numpy`, `scipy`.

| Pustaka | Pola lisensi yang umum | Implikasi kasar untuk “daftar HC aplikasi kita” |
|---------|-------------------------|--------------------------------------------------|
| **numpy**, **scipy** | Permisif (BSD-style) | Biasanya **tidak** menjadi penghalang pendaftaran hak cipta atas aplikasi Anda; tetap hormati teks lisensi & atribusi. |
| **pyqtgraph**, **pyserial** | Permisif | Sama. |
| **PySide6** / Qt | **LGPL** (lihat teks resmi versi yang Anda pakai) | Mendistribusikan aplikasi tertutup umumnya **boleh** dengan **kepatuhan LGPL** (cara linking, penyediaan sumber Qt jika diminta, dsb.) — ini **tanggung jawab distribusi**, terpisah dari pertanyaan pendaftaran HC atas kode Anda. |

**Touchpad / NI-DAQ:** selain stack Qt/pyqtgraph/numpy serupa, ada **`nidaqmx`** dan ekosistem **NI** — itu biasanya **perjanjian penggunaan / lisensi proprietary** National Instruments, **bukan** lisensi open source.

- Anda biasanya **tidak** “memiliki hak cipta” atas isi driver/SDK NI.  
- **Pendaftaran hak cipta** atas **aplikasi Anda** (kode integrasi, UI, logika) pada umumnya **tetap bisa dibicarakan**, tetapi **redistribusi** runtime NI dan syarat lisensi NI harus dipatuhi terpisah.

### 6.4 Yang *bukan* diatur lisensi pustaka (tetap perlu dipikirkan)

- **Kontrak dengan klien** (siapa pemegang hak cipta hasil kerja).  
- **Aset non-kode**: font berbayar, ikon, foto manual, merek dagang pihak lain.  
- **Branding Qt / NI**: larangan penyalahgunaan merek dalam materi promosi.

### 6.5 Ringkasan satu kalimat

**Lisensi pustaka pada umumnya tidak bertujuan melarang Anda mendaftarkan hak cipta atas kode asli aplikasi Anda** di lembaga KI; yang harus dipenuhi adalah **kepatuhan lisensi** saat **menggunakan dan mendistribusikan** pustaka tersebut, plus **kejujuran** dalam klaim kepemilikan karya.

---

## 7. Penutup

Berdasarkan kerangka **hukum KI Indonesia** pada umumnya, **kedua aplikasi desktop** di repositori ini paling natural diklasifikasi sebagai objek **hak cipta** (program komputer dan dokumentasi terkait). **Paten** bukan label default untuk aplikasi semacam itu kecuali ada **penemuan teknis** terpisah yang memenuhi syarat undang-undang paten. **Rahasia dagang** dan **merek** bisa menjadi **pelengkap strategi**, bukan pengganti hak cipta untuk kode.

Untuk dokumen resmi (perjanjian klien, pengalihan hak, atau gugatan), libatkan **advokat HKI** yang berpraktik di Indonesia.

*Dokumen referensi internal di root repositori `Swimmer_Monitoring`.*

# Test log — Palm Pressure Motion

Uji bersama companion Android dan firmware logger di carrier skema 1.1.

## 2026-11-09 14:07 (WIB)

| Komponen | Versi | Catatan |
|---|---|---|
| `Android_App` | **1.1.0** | Tag `PalmLog_Android_v1.1.0` |
| `PlatformIO/Log_Session_Bin` | **2.1.0** | Tag `Log_Session_Bin_v2.1.0`, advertising `PalmLog1` |

Hasil: **lulus** untuk RTC (sync waktu), flash, dan baterai.

| Area | Cek | Hasil |
|---|---|---|
| RTC | Sync waktu HP → board (BLE `0x11` / `0x91`) | OK |
| Flash | W25Q128 16 MB, FS PLG1, kapasitas menurut profil `PalmLog1` | OK |
| Baterai | `vbat_mV` dari ADC P0.31 (bukan dummy) di status BLE / UI | OK |

Belum masuk sesi ini: IMU / magnetometer (masih dummy di firmware), stream lapangan, format chip erase penuh.

## 2026-11-09 — Komparasi Euler RPY, EKF dan Madgwick Palm vs EST Unix 3DM-GX5-25

Berkas di `PythonFile/Komparasi_Euler_Angle_PalmSensor_3DM-GX5-25/`:

- `EKF/Komparasi_EulerRPY_1949_EKF-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `EKF/Komparasi_EulerRPY_1949_EKF-IMU-MAG-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `EKF/Komparasi_EulerRPY_1954_EKF-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `EKF/Komparasi_EulerRPY_1954_EKF-IMU-MAG-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Madgwick/Komparasi_EulerRPY_1949_Madgwick-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Madgwick/Komparasi_EulerRPY_1954_Madgwick-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`

Resume EKF: `.../EKF/Komparasi_EulerRPY_Resume_EKF-Palm_vs_EST-UNIX-3DM-GX5-25.md` dan `.pdf`.

Resume Madgwick IMU, tanpa magnetometer: `.../Madgwick/Komparasi_EulerRPY_Resume_Madgwick-Palm_vs_EST-UNIX-3DM-GX5-25.md` dan `.pdf`.

Cara hitung sama untuk semua. Sumbu: X tetap, Y dan Z dibalik (accel, gyro, dan mag). Z Palm setelah remap ≈ −1 g. Filter `ahrs` memakai acuan NED `[0, 0, +1]`, jadi tanda akselerasi dibalik hanya sebelum filter. Gyro dan mag tidak ikut dibalik. Madgwick IMU memakai gain bawaan 0,033, tanpa magnetometer. Mag EKF mentah dalam µT, tanpa kalibrasi hard-iron/soft-iron. Jam header Palm adalah WIB yang tersimpan sebagai angka Unix; EST adalah UTC. Waktu Palm digeser −7 jam, lalu sisa offset dicari di ±5 s.

### Sesi 1949

Palm `261109194905.bin`, 8617 sampel, 100 Hz. EST `SensorConnectData_EST_Unix_1949.csv`. Sisa offset **−0,110 s** (EKF) dan **−0,100 s** (Madgwick). Seluruh sampel Palm masuk jendela EST.

| Filter | Sumbu | Korelasi | MAE | MAE setelah bias dihilangkan |
|---|---|---:|---:|---:|
| EKF IMU | Roll | 0,999 | 1,13° | 0,30° |
| EKF IMU | Pitch | 0,999 | 1,93° | 0,21° |
| EKF IMU | Yaw | 0,927 | 88,4° | 3,30° |
| Madgwick IMU | Roll | 0,999 | 0,99° | 0,25° |
| Madgwick IMU | Pitch | 0,999 | 1,72° | 0,31° |
| Madgwick IMU | Yaw | 0,935 | 88,7° | 3,30° |
| EKF IMU+Mag | Roll | 0,988 | 15,9° | 1,02° |
| EKF IMU+Mag | Pitch | 0,717 | 6,76° | 5,98° |
| EKF IMU+Mag | Yaw | −0,502 | 155° | 114° |

### Sesi 1954

Palm `261109195407.bin`, 7527 sampel, 100 Hz. EST `SensorConnectData_EST_Unix_1954.csv`. Sisa offset **−0,160 s** (EKF IMU dan Madgwick) dan **−0,170 s** (EKF IMU+Mag). Seluruh sampel Palm masuk jendela EST.

| Filter | Sumbu | Korelasi | MAE | MAE setelah bias dihilangkan |
|---|---|---:|---:|---:|
| EKF IMU | Roll | 0,994 | 1,14° | 1,01° |
| EKF IMU | Pitch | 0,994 | 1,88° | 0,57° |
| EKF IMU | Yaw | 0,852 | 79,2° | 3,43° |
| Madgwick IMU | Roll | 0,995 | 1,03° | 0,92° |
| Madgwick IMU | Pitch | 0,992 | 1,61° | 0,64° |
| Madgwick IMU | Yaw | 0,901 | 76,0° | 2,41° |
| EKF IMU+Mag | Roll | 0,979 | 14,7° | 1,82° |
| EKF IMU+Mag | Pitch | 0,738 | 10,7° | 5,30° |
| EKF IMU+Mag | Yaw | −0,147 | 141° | 50,4° |

Hasil: EKF IMU dan Madgwick IMU mengikuti roll dan pitch EST di kedua sesi. Yaw keduanya mengikuti bentuk gerak, dengan offset heading sekitar +88° sampai +89° (1949) dan +76° sampai +79° (1954). Magnetometer mentah menggeser roll sekitar 15° dan tidak memperbaiki yaw.

## 2026-11-10 — Power measurement PalmLog1 (`test_power_1`)

Alat: SDM3065X-SC, DC Current, interval 200 ms. Berkas: `Test_Power/test_power_1.csv`, plot `Test_Power/test_power_1_plot.png`, analisa lengkap `Test_Power/test_power_1_analisis.md`.

Urutan zona (setelah koreksi): OFF → Advertising → Connected → Measure ON → Connected → Sync → Connected → Measure ON → Stream+Measure → Measure ON → Connected → OFF.

| Mode (agregat) | \(I\) rata-rata | Catatan |
|---|---:|---|
| OFF | 0,62 mA | Awal median ~0,33 mA; akhir ~0,73 mA |
| Advertising | 7,46 mA | |
| Connected | 7,40 mA | Hampir sama dengan measure |
| Measure ON (stream OFF) | 7,57 mA | Spike besar (p95 ~8,6–9,0 mA) |
| Sync | 7,70 mA | |
| Stream + Measure | 5,41 mA | Mean turun; fluktuasi besar — uji-only |

Estimasi masa pakai (usable \(0{,}8\cdot C/I\)); LIR2032 ≈ 40 mAh (interpretasi LIR3202):

| Skenario | LIR2032 40 mAh | LiPo 140 mAh | LiPo 300 mAh | LiPo 400 mAh |
|---|---:|---:|---:|---:|
| Measure ON ~7,57 mA | ~4,2 jam | ~15 jam | ~32 jam | ~42 jam |
| Connected ~7,40 mA | ~4,3 jam | ~15 jam | ~32 jam | ~43 jam |
| Mix 20% measure / 80% connected | ~4,3 jam | ~15 jam | ~32 jam | ~43 jam |
| OFF ~0,62 mA | ~51 jam | ~7,5 hari | ~16 hari | ~21 hari |

Spike kecil non-measure: paling mungkin LED heartbeat. Spike besar saat measure: tulis flash SPI (+ LED). Stream tidak dipakai untuk estimasi lapangan.

## 2026-11-18 — HX711_One, serial monitor

Firmware `PlatformIO/HX711_One`. USB 115200. Board sudah menyala sekitar 203 s saat cuplikan dimulai. 817 sampel, `t_ms` 203510–213069 (9,56 s). Jarak sampel median 11 ms.

Perintah yang tersimpan di cuplikan hanya `ch,1`. Tidak ada `ch,2`. Angka sebelum perintah adalah kanal yang sedang berjalan saat log dimulai. Setelah `ch,1` kanalnya HX711-1 (SCK P0.06, DT P0.08). Jeda 418 ms di antara dua segmen sama dengan 400 ms yang dibuang firmware setelah kanal dipilih.

Fase beban yang diam tidak ada. Yang terlihat hanya ekor penurunan 392 ms (35 sampel), dari 1.328.985 ke 813.219, lalu nilai menempel. Rata-rata di lereng itu 1.159.982, tetapi itu bukan level beban.

| Segmen | Kanal | Fase | n | Durasi | Rata-rata | Simpangan | Min | Max |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Sebelum `ch,1` | tidak tercatat di cuplikan | diam, setelah penurunan | 420 | 4,82 s | 797.712 | 2.017 | 792.721 | 805.494 |
| Sesudah `ch,1` | HX711-1 | diam, beban tidak berubah | 362 | 3,92 s | 5.367 | 122 | 4.949 | 5.681 |

Lompatan 797.712 → 5.367 terjadi tepat setelah perintah `1`, jadi itu ganti kanal / hidup ulang chip, bukan perubahan beban.

## 2026-11-18 — HX711_Dual, serial monitor

Firmware `PlatformIO/HX711_Dual`. USB 115200. Baris `t_ms,raw1,raw2`. 940 sampel, `t_ms` 1491–12295 (10,80 s). Kedua kanal dibebani terpisah, tidak bersamaan.

Beban adalah ayunan tekan-lepas, bukan beban yang ditahan rata. Rata-rata seluruh ayunan ikut menghitung jalan naik dan jalan turun. Baris "menempel" adalah bagian yang tinggal di dekat puncak.

| Kanal | Fase | n | Durasi | Rata-rata | Simpangan | Min | Max |
|---|---|---:|---:|---:|---:|---:|---:|
| HX711-1 | diam, awal | 212 | 2,43 s | 5.386 | 133 | 5.065 | 5.740 |
| HX711-1 | beban 1, seluruh ayunan | 199 | 2,28 s | 521.377 | 288.470 | 541 | 777.712 |
| HX711-1 | beban 1, di atas 700.000 | 96 | 1,09 s | 750.462 | 21.526 | 701.277 | 777.712 |
| HX711-1 | diam, antara dua beban | 268 | 3,07 s | 5.233 | 161 | 4.693 | 5.955 |
| HX711-1 | beban 2, seluruh ayunan | 89 | 1,01 s | 306.498 | 152.155 | 2.833 | 463.446 |
| HX711-1 | diam, akhir | 172 | 1,97 s | 5.483 | 117 | 5.125 | 5.803 |
| HX711-2 | diam, sebelum beban | 473 | 5,43 s | 798.187 | 5.777 | 778.389 | 813.508 |
| HX711-2 | beban, seluruh ayunan | 163 | 1,86 s | 1.382.514 | 262.318 | 819.753 | 1.588.987 |
| HX711-2 | beban, di atas 1.500.000 | 96 | 1,09 s | 1.558.059 | 17.552 | 1.501.949 | 1.588.987 |
| HX711-2 | diam, sesudah beban | 304 | 3,49 s | 810.536 | 2.378 | 805.788 | 817.762 |

HX711-1 diam memakai pita 4.500–6.500. Ekor lepas yang jatuh di bawah pita itu masih dihitung sebagai beban. HX711-2 dihitung beban saat hitungan melewati 819.000. Selama diam, HX711-2 tetap naik pelan: 778.389 di awal cuplikan, 813.508 tepat sebelum beban, lalu 805.788–817.762 sesudah beban. HX711-1 beban 2 lebih pendek dan tidak punya bagian yang menempel seperti beban 1.

## 2026-11-18 — HX711_Dual, skala kg

Anak timbangan pada satu kanal. Kanal yang tidak dibebani tetap diam. Angka di bawah adalah level bagian yang menempel, bukan rata-rata jalan naik dan turun.

### HX711-2 — urutan 3 kg, 1 kg, tanpa beban

HX711-1 tetap di sekitar 5.600–6.000.

| Fase | Hitungan |
|---|---:|
| 3 kg | 2.178.500 |
| 1 kg | 1.307.400 |
| tanpa beban | 870.900 |

Dari 0 ke 1 kg naik 436.500 hitungan. Dari 1 ke 3 kg naik 871.000 hitungan, yaitu 435.500 hitungan tiap kg. Faktor **436.000 hitungan/kg**, nol **871.000**.

```text
kg = (raw2 − 871000) / 436000
```

Balik ke 1 kg dan 3 kg, sisa sekitar 1 gram.

### HX711-1 — urutan 1 kg, 3 kg, 1 kg, tanpa beban

HX711-2 tetap di sekitar 859.000.

| Fase | Hitungan | Setara |
|---|---:|---:|
| diam awal | 441.300 | 1 kg |
| diam di puncak | 1.312.100 | 3 kg |
| diam lagi | 441.300 | 1 kg |
| diam akhir | 5.800 | tanpa beban |

Naik 441.300 → 1.312.100 adalah 870.800 hitungan, pas 2 kg. Turun ke 5.800 adalah 1 kg. Faktor **435.500 hitungan/kg**, nol **5.800**.

```text
kg = (raw1 − 5800) / 435500
```

Di antara dua penahanan 1 kg ada sentuhan singkat ke 448.000, kira-kira 16 gram, lalu nilai kembali. Faktor kanal 1 dan kanal 2 beda sekitar 500 hitungan/kg.

## 2026-11-18 13:02 — coba firmware 2.3.0

Di-flash dari salinan `D:\Pengujian\Log_Session_Bin_230` (tag `Log_Session_Bin_v2.3.0`). Serial COM12 menampilkan `Log_Session_Bin 2.3.0`. RTC awalnya tahun di bawah 2020, lalu ponsel mengirim waktu dan `BLE SET_TIME OK`.

| Cek | Hasil |
|---|---|
| IMU | `IMU OK LSM6DSOX+LIS3MDL` |
| Baterai | `vbat_mV=4092` |
| Rekaman | `261118130252.bin`, 3086 rekaman, 80492 byte, `prod=3086`, `drop=0` |
| Ponsel | BLE connected, `LIST` 8 berkas, `GET` berkas baru dan `261110090147` selesai |

Rekaman dan koneksi ke ponsel oke. `d1..d2` masih 0, sesuai firmware 2.3.0. Daya 3,3 V ke kedua HX711 tetap tersambung selama uji ini.

## 2026-11-18 — firmware 2.4.1, beban dan IMU

CSV di `Log_Session_Bin_2.4/`. Satuan `d1` dan `d2` adalah 0,001 kg. USB tetap tersambung. Jarak rekaman 9–10 ms, tidak ada lubang.

### `261118132908.csv` — 4595 rekaman, 44,9 s

Dua kanal dibebani bergantian, lalu IMU diputar. Beban tidak ditahan datar.

| Waktu | Kejadian |
|---|---|
| 0–3,0 s | Diam. HX711-1 ≈ 0 kg, HX711-2 ≈ −0,11 kg |
| 3,0–5,8 s | HX711-2. Median naik sampai sekitar 2,9 kg, puncak 4,7 kg |
| 7,6–11,2 s | HX711-1. Median sekitar 4,3 kg, puncak halus 7,1 kg |
| 14,4–26,7 s | IMU diputar. Gyro rata-rata 32 °/s, puncak 73 °/s. Accel tetap dekat 1 g |

Satu sampel rusak pada 39,70 s: `d2 = −16427`. Tetangganya −0,12 kg.

### `261118143507.csv` — 4781 rekaman, 46,7 s

HX711-2 ditahan 1 kg, kemudian HX711-1 ditahan 2 kg, lalu IMU diputar.

| Waktu | Kejadian |
|---|---|
| 6,5–12,3 s | HX711-2 rata-rata **0,977 kg** (beban 1 kg). HX711-1 tetap 0,001 kg |
| 18,2–22,4 s | HX711-1 rata-rata **2,036 kg** (beban 2 kg). HX711-2 tetap 0,004 kg |
| 26,5–36,4 s | IMU diputar. Gyro rata-rata 55 °/s, puncak 126 °/s |

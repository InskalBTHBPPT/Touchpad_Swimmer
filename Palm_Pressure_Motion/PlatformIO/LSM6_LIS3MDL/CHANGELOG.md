# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-11-06

Cetak serial hanya nilai yang sudah diskalakan. Hitungan mentah register tidak lagi dikirim.

- Satu sampel satu baris: accel dalam g, gyro dalam dps, magnetometer dalam G.
- Jarak sampel tetap 10 ms. LSM6DSOX tetap 104 Hz, LIS3MDL tetap 155 Hz.

## [1.1.0] - 2026-11-06

Cetak ketiga sensor mendekati 100 Hz.

- LSM6DSOX tetap 104 Hz. Chip ini tidak punya ODR tepat 100 Hz.
- LIS3MDL naik dari 10 Hz ke 155 Hz lewat `FAST_ODR` dan mode ultra-high performance. Itu laju terdekat di atas 100 Hz.
- Baris serial dan delapan sampel `TEST` diambil tiap 10 ms. Format baris tidak berubah.
- Vonis gyro menunggu 80 ms setelah sensor dinyalakan. Tanpa jeda itu, keluaran gyro masih puluhan dps dan tes diam gagal.

## [1.0.0] - 2026-11-06

Rilis pertama untuk membaca gerak U4 LSM6DSOX dan medan magnet U3 LIS3MDL.

- I2C SDA P1.04, SCL P1.06. LSM6DSOX `0x6A`, LIS3MDL `0x1C`. INT dan DRDY tidak dipakai.
- LSM6: 104 Hz, accel ±2 g, gyro ±250 dps, BDU nyala. Skala 0,061 mg/LSB dan 8,75 mdps/LSB.
- LIS3: 10 Hz, ±4 gauss, ultra-high performance, mode kontinu. Skala 6842 LSB/gauss. Auto-increment lewat bit 7 alamat register.
- Lulus jika WHO_AM_I cocok, magnitudo accel 0,7–1,3 g, gyro diam di bawah 20 dps, dan medan magnet tidak nol serta tidak jenuh.

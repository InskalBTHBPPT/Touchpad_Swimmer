# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-06

Rilis pertama untuk membaca gerak U4 LSM6DSOX dan medan magnet U3 LIS3MDL.

- I2C SDA P1.04, SCL P1.06. LSM6DSOX `0x6A`, LIS3MDL `0x1C`. INT dan DRDY tidak dipakai.
- LSM6: 104 Hz, accel ±2 g, gyro ±250 dps, BDU nyala. Skala 0,061 mg/LSB dan 8,75 mdps/LSB.
- LIS3: 10 Hz, ±4 gauss, ultra-high performance, mode kontinu. Skala 6842 LSB/gauss. Auto-increment lewat bit 7 alamat register.
- Lulus jika WHO_AM_I cocok, magnitudo accel 0,7–1,3 g, gyro diam di bawah 20 dps, dan medan magnet tidak nol serta tidak jenuh.

# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-06

Rilis pertama untuk memeriksa tiga IC I2C pada carrier skema 1.1.

- Bus I2C default: SDA P1.04, SCL P1.06, 100 kHz. Pull-up 10 kΩ sudah ada di carrier.
- U4 LSM6DSOX `0x6A`, lulus jika WHO_AM_I `0x0F` = `0x6C`.
- U3 LIS3MDL `0x1C`, lulus jika WHO_AM_I `0x0F` = `0x3D`.
- U2 RV-3032 `0x51`, lulus jika ACK (tidak ada register WHO_AM_I).
- Setelah itu memindai `0x08`–`0x77`. Perintah `SCAN` mengulang pemeriksaan.
- Sudah diuji di hardware: ketiga IC OK, dan hanya ketiga alamat itu yang muncul.

# PlatformIO

Setiap project di folder ini punya `CHANGELOG.md` sendiri.

Project yang sudah ada dianggap rilis **1.0.0**:

- `Flash_W25Q128` — uji SPI flash 16 MB
- `I2C_Detect` — deteksi U2, U3, dan U4 di bus I2C
- `Timer_RV3032` — jam RV-3032 lewat `bb_rtc` yang sudah disesuaikan manual
- `Timer_RV3032_Kinetic` — jam RV-3032 lewat library KineticLabs yang sudah disesuaikan manual
- `LSM6_LIS3MDL` — accel dan gyro LSM6DSOX plus magnetometer LIS3MDL

## Project baru

Salin blok di bawah ke `CHANGELOG.md` di root project. Versi awal tetap **1.0.0**. Naikkan versi hanya ketika perilaku firmware berubah:

- **MAJOR** jika perintah serial, format data, atau pin yang dipakai tidak lagi cocok dengan rilis sebelumnya
- **MINOR** jika ada perintah atau fitur baru yang tetap cocok dengan rilis sebelumnya
- **PATCH** jika perbaikan tanpa mengubah cara pakai

```markdown
# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.0.0] - YYYY-MM-DD

Rilis pertama.

- ...
```

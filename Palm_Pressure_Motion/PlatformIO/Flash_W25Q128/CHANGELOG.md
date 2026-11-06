# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-06

Rilis pertama untuk board baru (skema 1.1, flash W25Q128 16 MB).

- Uji SPI ke U1 W25Q128JVSIQ: CS P0.10, SCK P1.11, MOSI P1.13, MISO P1.15.
- `ID` menerima JEDEC `EF 40 18`. `EF 40 16` (W25Q32 4 MB) ditandai peringatan.
- `TEST` menghapus 4 KB, menulis 16 byte, lalu membaca balik di `0xFF0000`. Dibatalkan jika ID bukan `EF 40 18`.
- `READ` menolak alamat di luar 16 MB.
- Sudah diuji di hardware: `JEDEC EF 40 18 OK` dan `TEST OK`.

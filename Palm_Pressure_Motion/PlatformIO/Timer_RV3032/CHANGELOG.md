# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-06

Rilis pertama untuk menyetel dan menampilkan jam U2 RV-3032.

- Library `bitbank2/bb_rtc`, alamat `0x51`, SDA P1.04, SCL P1.06.
- `SET YYYY-MM-DD HH:MM:SS` menulis jam. Waktu dicetak setiap 1 detik, plus perintah `NOW`.
- Trickle charger tidak dinyalakan. Backup hanya switchover ke VBACKUP.

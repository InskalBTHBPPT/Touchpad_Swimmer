# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-11-06

`lib/bb_rtc` tidak lagi memakai deteksi upstream.

- ACK di `0x51` langsung dianggap RV-3032. Tidak ada tulis `0x55` ke `0x17` dan tidak ada tulis `0xAA` ke `0x03` (register jam).
- EEPROM PMU `0xC0` tidak ditulis. Trickle charger tetap default pabrik, yaitu mati.
- `setTime` / `getTime` tetap lewat register `0x01`–`0x07`. Weekday `0x04` disimpan sebagai angka 0–6.

## [1.0.0] - 2026-11-06

Rilis pertama untuk menyetel dan menampilkan jam U2 RV-3032.

- Library `bitbank2/bb_rtc`, alamat `0x51`, SDA P1.04, SCL P1.06.
- `SET YYYY-MM-DD HH:MM:SS` menulis jam. Waktu dicetak setiap 1 detik, plus perintah `NOW`.
- Trickle charger tidak dinyalakan. Backup hanya switchover ke VBACKUP.

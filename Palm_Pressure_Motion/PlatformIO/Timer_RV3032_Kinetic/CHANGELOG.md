# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-06

Rilis pertama. Library KineticLabs, disesuaikan dengan manual RV-3032-C7 rev 1.3.

- `begin()` hanya memeriksa ACK di `0x51`.
- `setTime` menulis BCD ke register `0x01`–`0x07`.
- Register weekday `0x04` disimpan sebagai angka 0–6. Salinan upstream memakai bitmask RV-8803 (`1 << hari`); itu diubah.
- Tampilan jam dipaksa 24 jam. Default library adalah 12 jam, sehingga 15:00 terbaca 03:00. Chip RV-3032 sendiri tidak punya mode 12 jam.
- EEPROM PMU dan trickle charger tidak ditulis.

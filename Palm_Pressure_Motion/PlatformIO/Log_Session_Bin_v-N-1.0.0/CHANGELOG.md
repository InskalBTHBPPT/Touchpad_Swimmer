# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-09

Rilis pertama untuk carrier Palm skema 1.1 (bukan board logger W25Q32 + DS3231).

- Dari `Log_Session_Bin_v3.1.1`: PLG1 v4, 26 B/rekaman, 100 Hz timer+ring, BLE NUS, sensor tetap dummy.
- Flash **W25Q128** 16 MB, JEDEC `EF 40 18`. `FORMAT` tetap chip erase penuh.
- RTC **RV-3032** lewat `lib/bb_rtc` lokal (ACK `0x51` saja). Tidak memakai RTClib/DS3231.
- Advertising BLE: **`PalmLog1`**.

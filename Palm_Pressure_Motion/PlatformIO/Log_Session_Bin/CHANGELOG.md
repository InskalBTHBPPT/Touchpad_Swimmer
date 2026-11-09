# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [2.1.0] - 2026-11-09

Status baterai memakai ADC Bat(+), bukan angka acak. Paket `0x90` tetap 16 byte.

- P0.31, pembagi 1 MΩ/1 MΩ, `Vbat = Vpin × 2 × 0,9726`, rata-rata 16 sampel. Sama dengan `VBAT_ADC` 1.1.1.
- Hasil di-cache 1 detik. `vbat_mV` di serial dan byte 14..15 status BLE memakai cache itu.

## [2.0.0] - 2026-11-09

Tombol pindah pin. Board yang masih memasang tombol di P0.17 tidak lagi cocok dengan firmware ini.

- Deteksi tombol, termasuk bangun dari System OFF, memakai **P0.24** ke GND (`INPUT_PULLUP`). Sebelumnya P0.17.

## [1.0.0] - 2026-11-09

Rilis pertama untuk carrier Palm skema 1.1 (bukan board logger W25Q32 + DS3231).

- Folder proyek: `Log_Session_Bin` (versi hanya di changelog / README / banner, bukan di nama folder).
- Dari `Log_Session_Bin_v3.1.1`: PLG1 v4, 26 B/rekaman, 100 Hz timer+ring, BLE NUS, sensor tetap dummy.
- Flash **W25Q128** 16 MB, JEDEC `EF 40 18`. `FORMAT` tetap chip erase penuh.
- RTC **RV-3032** lewat `lib/bb_rtc` lokal (ACK `0x51` saja). Tidak memakai RTClib/DS3231.
- Advertising BLE: **`PalmLog1`**.

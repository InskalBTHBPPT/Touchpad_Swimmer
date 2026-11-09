# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [2.3.0] - 2026-11-09

Timing tombol dan heartbeat LED disesuaikan untuk pemakaian lapangan.

- Tombol: **&lt; 2 s** diabaikan; **2…5 s** lepas = Start/Stop measure; **≥ 5 s** tahan = System OFF / ON dari tidur.
- LED idle: **4 kedip** (ON 100 ms, OFF antar kedip 250 ms), lalu tunggu **5 s**.
- LED measure: tetap **2 kedip** ON/OFF 100 ms, lalu tunggu **5 s**.
- Auto System OFF tanpa USB/peer tetap **3 menit**.

## [2.2.0] - 2026-11-09

Sampel measure/stream memakai IMU dan magnetometer nyata. Format PLG1 v4 tidak berubah.

- Port dari `LSM6_LIS3MDL` 2.0.0: LSM6DSOX `0x6A` (±2 g / ±250 dps, 104 Hz) dan LIS3MDL `0x1C` (±4 G, 155 Hz).
- Timer 10 ms mengisi `d3..d5` (mg), `d6..d8` (0,1 °/s), `d9..d11` (µT). `d1..d2` tetap 0.
- `STATUS` menampilkan `imu=OK|NO`. Paket BLE status tetap 16 byte.

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

# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi aplikasi mengikuti [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-11-09

Satu aplikasi membaca dua sistem board dari nama advertising.

- `PalmLog20` memakai flash 4 MB dan timeout format 65 detik.
- `PalmLog1` memakai flash 16 MB dan timeout format 120 detik.
- Nama diambil dari hasil scan. Nama yang tidak dikenali tidak diberi tebakan ukuran flash.

## [1.0.0] - 2026-11-09

Rilis pertama companion Android di `Palm_Pressure_Motion`. Versi hanya ada di changelog, README, dan `versionName`, bukan di nama folder.

- Disalin dari `NRF52840/AndroidApp/V2.1.0`: protokol PLG1 v4, rekaman 26 B, stream 29 B.
- Scan BLE tanpa filter nama hardware. Board diterima jika namanya diawali `PalmLog` (`PalmLog1`, `PalmLog20`, dan seterusnya).
- `applicationId` `com.aistudio.palmlog`, `versionCode` 1, `versionName` 1.0.0. Terpasang berdampingan dengan aplikasi PalmLog20 lama.

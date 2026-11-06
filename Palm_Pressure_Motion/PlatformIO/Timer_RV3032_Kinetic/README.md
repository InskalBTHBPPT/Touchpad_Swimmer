# Timer RV-3032 — KineticLabs

Versi **1.0.0**. Riwayat ada di `CHANGELOG.md`.

Library: salinan [KineticLabs25/RV-3032-C7](https://github.com/KineticLabs25/RV-3032-C7) di `lib/RV3032`. Weekday mengikuti manual (`0x04` = 0–6), bukan bitmask RV-8803.

Perintah serial 115200 sama dengan `Timer_RV3032`: cetak tiap detik, `NOW`, `SET YYYY-MM-DD HH:MM:SS`.

```text
cd Palm_Pressure_Motion/PlatformIO/Timer_RV3032_Kinetic
pio run -t upload
```

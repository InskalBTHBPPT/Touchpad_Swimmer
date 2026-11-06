# LSM6DSOX + LIS3MDL — nRF52840 (Arduino / PlatformIO)

Versi **2.0.0**. Riwayat ada di `CHANGELOG.md`. Hasil uji hardware ada di `TEST_LOG.md`.

Board: SuperMini nRF52840 di carrier skema 1.1.  
SDA **P1.04**, SCL **P1.06**.

| Chip | Alamat | Peran |
|---|---|---|
| U4 LSM6DSOX | `0x6A` | accel ±2 g, gyro ±250 dps, 104 Hz |
| U3 LIS3MDL | `0x1C` | magnetometer ±4 gauss, 155 Hz |

INT1 dan DRDY tidak disambungkan ke firmware ini. Pembacaan lewat register, tanpa library ST/Adafruit.

## Perintah Serial (115200)

Saat boot, firmware mengambil 8 sampel tiap 10 ms lalu memberi vonis. Setelah itu satu baris nilai terskala dicetak tiap 10 ms (100 Hz). LSM6 jalan di 104 Hz dan LIS3MDL di 155 Hz, karena keduanya tidak punya ODR tepat 100 Hz. Hitungan mentah register tidak dicetak.

| Perintah | Fungsi |
|---|---|
| (otomatis) | Cetak accel, gyro, dan mag |
| `TEST` | Ulangi 8 sampel dan vonis |
| `HELP` | Bantuan |

Lulus bila WHO_AM_I cocok, `|a|` ada di 0,7–1,3 g, gyro tiap sumbu di bawah 20 dps, dan `|m|` ada di 0,05–3,8 gauss.

```text
cd Palm_Pressure_Motion/PlatformIO/LSM6_LIS3MDL
pio run -t upload
pio device monitor
```

# Flash W25Q128 — nRF52840 (Arduino / PlatformIO)

Versi **1.0.0**. Riwayat ada di `CHANGELOG.md`.

Project: `Palm_Pressure_Motion/PlatformIO/Flash_W25Q128`  
Clone dari `Flash_W25Q32`. Board dan pin SPI **sama**.

Chip: **W25Q128JVSIQ** SOIC-8 **208 mil**. SPI NOR **16 MB**.  
JEDEC yang benar: **`EF 40 18`**. (`EF 40 16` = W25Q32 4 MB.)

Pin (sama W25Q32): SCK **P1.11**, MOSI **P1.13**, MISO **P1.15**, CS **P0.10**.  
`/WP` dan `/HOLD` pull-up **10 kΩ** ke 3,3 V. Decap dekat VCC.

## Perintah Serial (115200)

| Perintah | Fungsi |
|---|---|
| `ID` | JEDEC `9Fh` — harus `EF 40 18` |
| `TEST` | Erase 4 KB @ `0xFF0000`, tulis 16 byte, baca balik |
| `READ FF0000 16` | Baca hex (alamat hex, panjang 1…64) |
| `HELP` | Bantuan |

`TEST` dibatalkan jika chip bukan W25Q128, supaya firmware 16 MB tidak menulis ke chip 4 MB di alamat di luar kapasitasnya.

```text
cd Palm_Pressure_Motion/PlatformIO/Flash_W25Q128
pio run -t upload
pio device monitor
```

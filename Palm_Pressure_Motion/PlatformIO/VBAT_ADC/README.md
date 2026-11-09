# VBAT ADC — nRF52840 (Arduino / PlatformIO)

Versi **1.1.1**. Riwayat ada di `CHANGELOG.md`. Hasil uji hardware ada di `TEST_LOG.md`.

Board: SuperMini nRF52840 di carrier skema 1.1.

```text
Bat(+) —— R5 1 MΩ ——+—— P0.31 (AIN7)
                    |
                   R6 1 MΩ
                    |
                   AGND
                    |
                   C4 100 nF
```

`V_bat = V_pin × 2 × 0,9726`. Faktor dari dua titik DMM Siglent di B+: 4,154 V dan 4,102 V. ADC pin penuh skala 3,6 V; sel LiPo 1S (~3,0–4,2 V) aman.

## Perintah Serial (115200)

| Perintah | Fungsi |
|---|---|
| (otomatis) | Cetak raw, V_pin, V_bat, VDDH tiap 1 detik |
| `NOW` | Cetak sekali |
| `TEST` | Rata-rata 16 sampel dan vonis |
| `HELP` | Bantuan |

```text
cd Palm_Pressure_Motion/PlatformIO/VBAT_ADC
pio run -t upload
pio device monitor
```

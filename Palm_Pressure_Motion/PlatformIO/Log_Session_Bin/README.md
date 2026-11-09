# Log Session Binary — PalmLog1

Versi **2.2.0**. Riwayat ada di `CHANGELOG.md`. Hasil uji hardware ada di `TEST_LOG.md`.

Firmware logger untuk **SuperMini nRF52840 di carrier skema 1.1**.  
Port dari `Log_Session_Bin_v3.1.1` (PalmLog20 / W25Q32 / DS3231).

| Item | Nilai |
|---|---|
| Versi FW | **2.2.0** |
| Advertising BLE | `PalmLog1` |
| Format berkas | **PLG1 version 4** |
| Rekaman | **26 B** = `t_rel_ms` u32 LE + 11×int16 |
| Sampling | **100 Hz** (`period_ms = 10`) |
| Flash | **W25Q128** 16 MB SPI, JEDEC `EF 40 18` |
| RTC | **RV-3032** I2C `0x51` lewat `lib/bb_rtc` lokal |
| Sensor | **LSM6DSOX** accel/gyro + **LIS3MDL** mag (d1..d2 = 0) |
| Battery di status | **P0.31**, `Vbat = Vpin × 2 × 0,9726` (sama `VBAT_ADC` 1.1.1) |

`FORMAT` = chip erase **penuh** 16 MB (tipikal ~40 s). Setelah itu append tanpa sector erase (Solusi B).

## Pin (skema 1.1)

| Fungsi | Pin |
|---|---|
| Tombol | P0.24 |
| Bat(+) ADC | P0.31 |
| LED | P0.15 |
| EXT_VCC | P0.13 |
| Flash CS/SCK/MOSI/MISO | P0.10 / P1.11 / P1.13 / P1.15 |
| I2C SDA/SCL | P1.04 / P1.06 |

## Build

```text
cd Palm_Pressure_Motion/PlatformIO/Log_Session_Bin
pio run -t upload
pio device monitor
```

Protokol opcode: `GoogleAIStudio/PROTOCOL.md`. Timing: `GoogleAIStudio/TIMING.md`. Riwayat: `CHANGELOG.md`.

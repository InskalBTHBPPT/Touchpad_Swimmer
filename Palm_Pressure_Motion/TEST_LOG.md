# Test log — Palm Pressure Motion

Uji bersama companion Android dan firmware logger di carrier skema 1.1.

## 2026-11-09 14:07 (WIB)

| Komponen | Versi | Catatan |
|---|---|---|
| `Android_App` | **1.1.0** | Tag `PalmLog_Android_v1.1.0` |
| `PlatformIO/Log_Session_Bin` | **2.1.0** | Tag `Log_Session_Bin_v2.1.0`, advertising `PalmLog1` |

Hasil: **lulus** untuk RTC (sync waktu), flash, dan baterai.

| Area | Cek | Hasil |
|---|---|---|
| RTC | Sync waktu HP → board (BLE `0x11` / `0x91`) | OK |
| Flash | W25Q128 16 MB, FS PLG1, kapasitas menurut profil `PalmLog1` | OK |
| Baterai | `vbat_mV` dari ADC P0.31 (bukan dummy) di status BLE / UI | OK |

Belum masuk sesi ini: IMU / magnetometer (masih dummy di firmware), stream lapangan, format chip erase penuh.

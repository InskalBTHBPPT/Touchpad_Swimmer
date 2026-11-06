# Timer RV-3032 — nRF52840 (Arduino / PlatformIO)

Versi **1.0.1**. Riwayat ada di `CHANGELOG.md`.

Board: SuperMini nRF52840 di carrier skema 1.1.  
U2 **RV-3032-C7**, alamat **`0x51`**, SDA **P1.04**, SCL **P1.06**.

Library: salinan **bb_rtc 1.3.1** di `lib/bb_rtc`. Deteksi upstream yang menulis `0xAA` ke register jam dimatikan. ACK di `0x51` cukup. EEPROM PMU tidak ditulis.

## Perintah Serial (115200)

| Perintah | Fungsi |
|---|---|
| (otomatis) | Cetak `RTC YYYY-MM-DD HH:MM:SS` setiap 1 detik |
| `NOW` | Cetak waktu sekali |
| `SET YYYY-MM-DD HH:MM:SS` | Tulis jam |
| `HELP` | Bantuan |

```text
cd Palm_Pressure_Motion/PlatformIO/Timer_RV3032
pio run -t upload
pio device monitor
```

Jam laptop:

```text
python tools/sync_time.py COM12
```

Tutup Serial Monitor dulu. Skrip memakai jam lokal Windows.

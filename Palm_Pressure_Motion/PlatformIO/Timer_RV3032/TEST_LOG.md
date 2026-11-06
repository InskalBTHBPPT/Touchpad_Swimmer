# Test log — Timer_RV3032

Versi firmware yang diuji: **1.0.1** (bb_rtc lokal, ACK saja di `0x51`)

## 2026-11-06 — COM12

Compile dan upload `pio run -t upload` berhasil. DFU lewat COM13, firmware aktif kembali di COM12.

| | |
|---|---|
| RAM | 9044 / 248832 (3,6%) |
| Flash | 66080 / 815104 (8,1%) |
| Upload | SUCCESS |

Serial 115200. Port dibuka segera setelah DFU. Jam laptop dikirim pada batas detik.

```text
KIRIM SET 2026-11-06 15:15:55

Timer RV-3032 boot
Timer RV-3032  addr=0x51  I2C SDA=P1.04 SCL=P1.06
...
Jam saat boot: 2000-01-01 00:15:38
RTC 2000-01-01 00:15:38
RTC 2000-01-01 00:15:39
RTC 2000-01-01 00:15:40
OK ditulis 2026-11-06 15:15:55
RTC 2026-11-06 15:15:55
RTC 2026-11-06 15:15:56
RTC 2026-11-06 15:15:57
RTC 2026-11-06 15:15:58
RTC 2026-11-06 15:15:59
```

Hasil: lulus. Chip ACK di `0x51`. Sebelum SET, jam masih epoch pabrik (`2000-01-01`) dan detiknya naik. Setelah SET, tanggal dan jam sama dengan laptop, lalu naik 55 → 59.

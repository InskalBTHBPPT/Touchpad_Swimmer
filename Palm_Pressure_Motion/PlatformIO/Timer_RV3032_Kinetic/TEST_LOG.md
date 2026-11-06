# Test log — Timer_RV3032_Kinetic

Versi firmware yang diuji: **1.0.0** (KineticLabs lokal, weekday 0–6, tampilan 24 jam)

## 2026-11-06 — COM12, percobaan pertama (tampilan 12 jam)

Upload berhasil (flash 60296 / 815104). SET laptop `2026-11-06 15:16:27` tercetak sebagai `03:16:27`. Detik naik 27 → 30, tanggal benar.

Penyebab: default library `_isTwelveHour = true`, jadi `getHours()` mengurangi 12 bila jam > 12. Register jam di chip tetap BCD 24 jam. Percobaan ini tidak lulus untuk jam.

## 2026-11-06 — COM12, setelah `rtc.set24Hour()`

Compile dan upload `pio run -t upload` berhasil. DFU lewat COM13, firmware aktif kembali di COM12.

| | |
|---|---|
| RAM | 9012 / 248832 (3,6%) |
| Flash | 60312 / 815104 (7,4%) |
| Upload | SUCCESS |

Serial 115200. Port dibuka segera setelah DFU. Jam laptop dikirim pada batas detik.

```text
KIRIM SET 2026-11-06 15:17:20

Timer RV-3032 KineticLabs boot
Timer RV-3032 KineticLabs  addr=0x51  SDA=P1.04 SCL=P1.06
...
Jam saat boot: RTC 2026-11-06 15:17:16
RTC 2026-11-06 15:17:16
RTC 2026-11-06 15:17:17
RTC 2026-11-06 15:17:18
RTC 2026-11-06 15:17:19
OK ditulis RTC 2026-11-06 15:17:20
RTC 2026-11-06 15:17:20
RTC 2026-11-06 15:17:21
RTC 2026-11-06 15:17:22
RTC 2026-11-06 15:17:23
```

Hasil: lulus. Jam boot sudah `15:17` (sisa tulis dari percobaan sebelumnya, sekarang tampil 24 jam). SET menempel, detik naik 20 → 23. Peringatan kompilasi `COUNTDOWN_TIMER_FREQUENCY_1/60_HZ` tetap ada dan tidak memengaruhi tes jam.

Firmware yang tertinggal di board adalah image KineticLabs ini.

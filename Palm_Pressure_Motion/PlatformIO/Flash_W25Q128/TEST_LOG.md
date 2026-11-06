# Test log — Flash_W25Q128

Versi firmware yang diuji: **1.0.0**

## 2026-11-06 — COM12

Compile dan upload `pio run -t upload` berhasil. DFU lewat COM13, firmware aktif kembali di COM12.

| | |
|---|---|
| RAM | 8840 / 248832 (3,6%) |
| Flash | 57436 / 815104 (7,0%) |
| Upload | SUCCESS |

Serial 115200. Perintah dikirim setelah port terbuka.

```text
--- kirim: ID ---
JEDEC EF 40 18  OK W25Q128

--- kirim: TEST ---
Erase 4K @ 0xFF0000
Page program 16 byte...
READ A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 AA AB AC AD AE AF
TEST OK

--- kirim: READ FF0000 16 ---
READ 0xFF0000: A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 AA AB AC AD AE AF
```

Hasil: **lulus**. JEDEC `EF 40 18`, dan 16 byte `A0`–`AF` terbaca balik di `0xFF0000`.

# Test log — I2C_Detect

Versi firmware yang diuji: **1.0.0**

## 2026-11-06 — COM12

Compile dan upload `pio run -t upload` berhasil. DFU lewat COM13, firmware aktif kembali di COM12.

| | |
|---|---|
| RAM | 8968 / 248832 (3,6%) |
| Flash | 55352 / 815104 (6,8%) |
| Upload | SUCCESS |

Serial 115200. Baris pertama muncul saat port terbuka (tes boot). `SCAN` mengulang pemeriksaan yang sama.

```text
--- saat port dibuka ---
I2C SDA P1.04  SCL P1.06
U4 LSM6DSOX 0x6A  WHO=0x6C  OK
U3 LIS3MDL  0x1C  WHO=0x3D  OK
U2 RV-3032   0x51  OK
Scan 0x08..0x77:
  0x1C
  0x51
  0x6A
Ketik SCAN lalu Enter untuk ulang.

--- kirim: SCAN ---
I2C SDA P1.04  SCL P1.06
U4 LSM6DSOX 0x6A  WHO=0x6C  OK
U3 LIS3MDL  0x1C  WHO=0x3D  OK
U2 RV-3032   0x51  OK
Scan 0x08..0x77:
  0x1C
  0x51
  0x6A
Ketik SCAN lalu Enter untuk ulang.
```

Hasil: **lulus**. Ketiga IC ada di alamat skema, WHO_AM_I cocok, dan scan hanya menemukan `0x1C`, `0x51`, dan `0x6A`.

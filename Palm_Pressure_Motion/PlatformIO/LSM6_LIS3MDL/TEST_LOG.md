# Test log — LSM6_LIS3MDL

Versi firmware yang diuji: **1.0.0**

## 2026-11-06 — COM12

Compile dan upload `pio run -t upload` berhasil. DFU lewat COM13, firmware aktif kembali di COM12.

| | |
|---|---|
| RAM | 8960 / 248832 (3,6%) |
| Flash | 59512 / 815104 (7,3%) |
| Upload | SUCCESS |

Serial 115200. Port dibuka segera setelah DFU. Board tidak digerakkan.

```text
IMU LSM6+LIS3 boot

IMU SDA P1.04  SCL P1.06
U4 LSM6DSOX 0x6A WHO=0x6C OK
U3 LIS3MDL  0x1C WHO=0x3D OK
A -249 106 16632  G 11 0 -22  M -1178 87 2868
  -0.015 0.006 1.015 g | 0.10 0.00 -0.19 dps | -0.172 0.013 0.419 G
A -239 91 16650  G 8 -1 -25  M -1167 81 2881
  -0.015 0.006 1.016 g | 0.07 -0.01 -0.22 dps | -0.171 0.012 0.421 G
A -254 89 16666  G 6 -2 -18  M -1181 126 2950
  -0.015 0.005 1.017 g | 0.05 -0.02 -0.16 dps | -0.173 0.018 0.431 G
...
ACCEL |a|=1.017 g OK
GYRO |w|max=0.22 dps OK
MAG |m|=0.458 G OK
TEST OK
```

Hasil: lulus. Accel sumbu Z sekitar 1,02 g, X dan Y dekat nol, jadi chip hampir datar dengan +Z ke atas. Gyro diam di bawah 0,3 dps. Medan magnet 0,46 G, masuk rentang medan Bumi, tidak jenuh. Baris live setelah vonis tetap di angka yang sama.

Folder proyek kemudian diganti dari `IMU_LSM6` menjadi `LSM6_LIS3MDL`, dan firmware diunggah ulang. Banner serial menjadi `LSM6 + LIS3MDL boot`. Vonis tetap lulus: `|a|=1.021 g`, `|w|max=0.21 dps`, `|m|=0.450 G`.

## 2026-11-06 — COM12, versi 1.1.0

Upload `pio run -t upload` berhasil. Flash 59592 / 815104 (7,3%), RAM 8960 / 248832 (3,6%).

```text
LSM6 + LIS3MDL boot 1.1.0
LSM6 104 Hz, LIS3MDL 155 Hz, cetak 100 Hz
ACCEL |a|=1.021 g OK
GYRO |w|max=0.20 dps OK
MAG |m|=0.445 G OK
TEST OK
```

Cetak setelah vonis: 205 baris `A` dalam 2,046 s = 100,2 Hz. Image yang tertinggal di board adalah 1.1.0.

# I2C Detect — tiga IC carrier skema 1.1

Board: SuperMini nRF52840 di header H1/H2.  
Bus: **SDA P1.04**, **SCL P1.06** (pull-up sudah di carrier).

| IC | Alamat | Lulus |
|---|---|---|
| U4 LSM6DSOX | `0x6A` | ACK + WHO_AM_I `0x6C` |
| U3 LIS3MDL | `0x1C` | ACK + WHO_AM_I `0x3D` |
| U2 RV-3032 | `0x51` | ACK |

```text
cd Palm_Pressure_Motion/PlatformIO/I2C_Detect
pio run -t upload
pio device monitor
```

Serial 115200. Setelah boot firmware mencetak hasil. Ketik `SCAN` untuk mengulang.

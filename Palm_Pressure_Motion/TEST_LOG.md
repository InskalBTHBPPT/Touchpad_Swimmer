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

## 2026-11-09 — Komparasi Euler RPY, EKF dan Madgwick Palm vs EST Unix 3DM-GX5-25

Notebook di `PythonFile/`:

- `Komparasi_EulerRPY_1949_EKF-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Komparasi_EulerRPY_1949_Madgwick-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Komparasi_EulerRPY_1949_EKF-IMU-MAG-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Komparasi_EulerRPY_1954_EKF-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Komparasi_EulerRPY_1954_Madgwick-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Komparasi_EulerRPY_1954_EKF-IMU-MAG-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`

Resume: `PythonFile/Komparasi_EulerRPY_Resume_EKF-Palm_vs_EST-UNIX-3DM-GX5-25.md` dan `.pdf`.

Cara hitung sama untuk semua. Sumbu: X tetap, Y dan Z dibalik (accel, gyro, dan mag). Z Palm setelah remap ≈ −1 g. Filter `ahrs` memakai acuan NED `[0, 0, +1]`, jadi tanda akselerasi dibalik hanya sebelum filter. Gyro dan mag tidak ikut dibalik. Madgwick IMU memakai gain bawaan 0,033, tanpa magnetometer. Mag EKF mentah dalam µT, tanpa kalibrasi hard-iron/soft-iron. Jam header Palm adalah WIB yang tersimpan sebagai angka Unix; EST adalah UTC. Waktu Palm digeser −7 jam, lalu sisa offset dicari di ±5 s.

### Sesi 1949

Palm `261109194905.bin`, 8617 sampel, 100 Hz. EST `SensorConnectData_EST_Unix_1949.csv`. Sisa offset **−0,110 s** (EKF) dan **−0,100 s** (Madgwick). Seluruh sampel Palm masuk jendela EST.

| Filter | Sumbu | Korelasi | MAE | MAE setelah bias dihilangkan |
|---|---|---:|---:|---:|
| EKF IMU | Roll | 0,999 | 1,13° | 0,30° |
| EKF IMU | Pitch | 0,999 | 1,93° | 0,21° |
| EKF IMU | Yaw | 0,927 | 88,4° | 3,30° |
| Madgwick IMU | Roll | 0,999 | 0,99° | 0,25° |
| Madgwick IMU | Pitch | 0,999 | 1,72° | 0,31° |
| Madgwick IMU | Yaw | 0,935 | 88,7° | 3,30° |
| EKF IMU+Mag | Roll | 0,988 | 15,9° | 1,02° |
| EKF IMU+Mag | Pitch | 0,717 | 6,76° | 5,98° |
| EKF IMU+Mag | Yaw | −0,502 | 155° | 114° |

### Sesi 1954

Palm `261109195407.bin`, 7527 sampel, 100 Hz. EST `SensorConnectData_EST_Unix_1954.csv`. Sisa offset **−0,160 s** (EKF IMU dan Madgwick) dan **−0,170 s** (EKF IMU+Mag). Seluruh sampel Palm masuk jendela EST.

| Filter | Sumbu | Korelasi | MAE | MAE setelah bias dihilangkan |
|---|---|---:|---:|---:|
| EKF IMU | Roll | 0,994 | 1,14° | 1,01° |
| EKF IMU | Pitch | 0,994 | 1,88° | 0,57° |
| EKF IMU | Yaw | 0,852 | 79,2° | 3,43° |
| Madgwick IMU | Roll | 0,995 | 1,03° | 0,92° |
| Madgwick IMU | Pitch | 0,992 | 1,61° | 0,64° |
| Madgwick IMU | Yaw | 0,901 | 76,0° | 2,41° |
| EKF IMU+Mag | Roll | 0,979 | 14,7° | 1,82° |
| EKF IMU+Mag | Pitch | 0,738 | 10,7° | 5,30° |
| EKF IMU+Mag | Yaw | −0,147 | 141° | 50,4° |

Hasil: EKF IMU dan Madgwick IMU mengikuti roll dan pitch EST di kedua sesi. Yaw keduanya mengikuti bentuk gerak, dengan offset heading sekitar +88° sampai +89° (1949) dan +76° sampai +79° (1954). Magnetometer mentah menggeser roll sekitar 15° dan tidak memperbaiki yaw.

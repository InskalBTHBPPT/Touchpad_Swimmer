# Resume komparasi Euler RPY

**EKF Palm vs EST Unix 3DM-GX5-25**

Tanggal data: 9 November 2026. Dua sesi, 19:49 dan 19:54 WIB.

## Tujuan

Membandingkan roll, pitch, dan yaw Palm terhadap estimasi orientasi 3DM-GX5-25. Palm belum menyimpan Euler, jadi sudut dihitung di Python dengan `ahrs` 0.4.

Dua filter diuji pada masing-masing sesi:

- EKF IMU: akselerometer dan giroskop.
- EKF IMU+Mag: akselerometer, giroskop, dan magnetometer mentah.

## Data

| Sesi | Palm | 3DM-GX5-25 EST | Sampel Palm | Laju |
|---|---|---|---:|---:|
| 1949 | `261109194905.bin` | `SensorConnectData_EST_Unix_1949.csv` | 8617 | 100 Hz |
| 1954 | `261109195407.bin` | `SensorConnectData_EST_Unix_1954.csv` | 7527 | 100 Hz |

Format Palm adalah PLG1 v4. Rekaman 26 byte: waktu relatif, lalu accel (mg), gyro (0,1 °/s), dan mag (µT). Sudut EST sudah dalam radian.

Notebook ada di folder yang sama:

- `Komparasi_EulerRPY_1949_EKF-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Komparasi_EulerRPY_1949_EKF-IMU-MAG-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Komparasi_EulerRPY_1954_EKF-IMU-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`
- `Komparasi_EulerRPY_1954_EKF-IMU-MAG-Palm_vs_EST-UNIX-3DM-GX5-25.ipynb`

## Cara hitung

Sumbu mengikuti catatan uji: X tetap, Y dan Z dibalik, untuk accel, gyro, dan mag. Setelah remap, Z Palm sekitar −1 g, sama seperti gaya spesifik 3DM.

`ahrs` pada kerangka NED membandingkan akselerometer dengan acuan `[0, 0, +1]`. Karena sensor membaca gaya spesifik, tanda akselerasi dibalik hanya sebelum masuk EKF. Gyro dan mag tidak ikut dibalik.

Magnetometer dipakai mentah, tanpa kalibrasi hard-iron atau soft-iron. Acuan medan magnet adalah bawaan `ahrs`. Besar medan rata-rata 48,9 µT (sesi 1949) dan 47,6 µT (sesi 1954), tetapi vektornya menumpuk di sumbu Z.

Jam di header Palm adalah jam dinding WIB yang tersimpan sebagai angka Unix. EST SensorConnect adalah Unix UTC, selisih 7 jam. Waktu Palm digeser −7 jam, lalu sisa offset dicari pada rentang ±5 detik agar korelasi pitch maksimum. Seluruh sampel Palm masuk jendela EST.

Selisih sudut dibungkus ke (−180°, 180°]. Baris “setelah bias” mengurangi rata-rata selisih itu.

## Sesi 1949

Sisa offset waktu **−0,110 detik** untuk kedua filter.

| Filter | Sumbu | Korelasi | MAE | RMSE | Bias | MAE setelah bias |
|---|---|---:|---:|---:|---:|---:|
| EKF IMU | Roll | 0,999 | 1,13° | 1,21° | +1,11° | 0,30° |
| EKF IMU | Pitch | 0,999 | 1,93° | 1,96° | −1,93° | 0,21° |
| EKF IMU | Yaw | 0,927 | 88,4° | 88,6° | +88,4° | 3,30° |
| EKF IMU+Mag | Roll | 0,988 | 15,9° | 16,0° | −15,9° | 1,02° |
| EKF IMU+Mag | Pitch | 0,717 | 6,76° | 7,73° | −3,43° | 5,98° |
| EKF IMU+Mag | Yaw | −0,502 | 155° | 156° | +53,2° | 114° |

## Sesi 1954

Sisa offset waktu **−0,160 detik** (EKF IMU) dan **−0,170 detik** (EKF IMU+Mag).

| Filter | Sumbu | Korelasi | MAE | RMSE | Bias | MAE setelah bias |
|---|---|---:|---:|---:|---:|---:|
| EKF IMU | Roll | 0,994 | 1,14° | 1,37° | +0,37° | 1,01° |
| EKF IMU | Pitch | 0,994 | 1,88° | 2,02° | −1,83° | 0,57° |
| EKF IMU | Yaw | 0,852 | 79,2° | 79,3° | +79,2° | 3,43° |
| EKF IMU+Mag | Roll | 0,979 | 14,7° | 15,0° | −14,7° | 1,82° |
| EKF IMU+Mag | Pitch | 0,738 | 10,7° | 11,8° | −9,87° | 5,30° |
| EKF IMU+Mag | Yaw | −0,147 | 141° | 143° | +92,2° | 50,4° |

## Kesimpulan

EKF IMU mengikuti roll dan pitch EST di kedua sesi. MAE roll dan pitch sekitar 1–2°. Setelah bias konstan dihilangkan, sisa roll dan pitch di sesi 1949 di bawah 0,3°.

Yaw EKF IMU mengikuti bentuk gerak. Korelasi 0,927 (1949) dan 0,852 (1954). Offset heading sekitar +88° pada sesi 1949 dan +79° pada sesi 1954. Setelah offset itu dihilangkan, MAE yaw turun ke sekitar 3,3–3,4°.

Magnetometer mentah tidak memperbaiki yaw. Korelasi yaw menjadi negatif atau mendekati nol, dan roll bergeser sekitar 15°. Heading dari mag belum dapat dipakai sebelum kalibrasi hard-iron/soft-iron dan pemeriksaan arah sumbu magnetometer.

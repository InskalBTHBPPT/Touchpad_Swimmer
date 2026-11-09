# Test log — VBAT_ADC

Versi firmware yang diuji: **1.0.0**

## 2026-11-09 — COM12

Compile dan upload `pio run -t upload` berhasil. DFU lewat COM13, firmware aktif kembali di COM12.

| | |
|---|---|
| RAM | 8784 / 248832 (3,5%) |
| Flash | 56920 / 815104 (7,0%) |
| Upload | SUCCESS |

Serial 115200. Port dibuka segera setelah DFU. USB terpasang.

```text
VBAT ADC boot 1.0.0

VBAT SENSE  pin=P0.31  divider=x2  ADC=12bit/3.6V
RAW 2445  Vpin 2.149 V  Vbat 4.299 V  VDDH 4.752 V
TEST OK
RAW 2443  Vpin 2.148 V  Vbat 4.295 V  VDDH 4.699 V
RAW 2443  Vpin 2.148 V  Vbat 4.295 V  VDDH 4.738 V
```

Hasil: lulus. Pembagi di P0.31 hidup. `Vpin ≈ 2,15 V` → `Vbat ≈ 4,30 V` (×2), masuk rentang LiPo 1S yang sedang diisi / penuh. `VDDH ≈ 4,7 V` lebih tinggi dari Bat(+), wajar saat USB menyuplai rail charger. Bacaan stabil antar detik.

Firmware yang tertinggal di board adalah image `VBAT_ADC` ini.

## 2026-11-09 — kalibrasi vs voltmeter (sebelum faktor)

USB terpasang. Dua baterai diukur bergantian. Bacaan awal kasar, lalu diganti DMM Siglent.

| Baterai | Meter kasar | DMM Siglent | Firmware mentah (`×2` saja) |
|---|---:|---:|---:|
| 1 | 4,17 V | **4,154 V** | ≈ 4,299 V |
| 2 | 4,09 V | **4,102 V** | ≈ 4,190 V |

Bacaan baterai 2 di serial (belum dikalibrasi):

```text
RAW 2381  Vpin 2.093 V  Vbat 4.186 V  VDDH 4.774 V
RAW 2383  Vpin 2.095 V  Vbat 4.190 V  VDDH 4.765 V
RAW 2385  Vpin 2.097 V  Vbat 4.193 V  VDDH 4.769 V
RAW 2383  Vpin 2.095 V  Vbat 4.190 V  VDDH 4.734 V
```

Firmware mentah lebih tinggi ≈ 0,10–0,15 V daripada DMM.

## 2026-11-09 — COM12, versi 1.1.0 (cal=0.973)

Upload berhasil. Flash 56952 / 815104. Baterai 2 masih terpasang.

```text
VBAT ADC boot 1.1.0
RAW 2402  Vpin 2.112 V  Vbat 4.109 V  VDDH 4.813 V
TEST OK
```

## 2026-11-09 — COM12, versi 1.1.1 (cal=0.9726, acuan Siglent)

Faktor dihitung ulang: `(4,154/4,299 + 4,102/4,190) / 2 = 0,9726`. Upload berhasil. Flash 56960 / 815104. Baterai 2 terpasang (Siglent 4,102 V).

```text
VBAT ADC boot 1.1.1
VBAT SENSE  pin=P0.31  divider=x2  cal=0.9726  ADC=12bit/3.6V
RAW 2398  Vpin 2.108 V  Vbat 4.101 V  VDDH 4.818 V
TEST OK
RAW 2431  Vpin 2.137 V  Vbat 4.157 V  VDDH 4.791 V
RAW 2409  Vpin 2.118 V  Vbat 4.120 V  VDDH 4.804 V
RAW 2408  Vpin 2.117 V  Vbat 4.118 V  VDDH 4.796 V
RAW 2398  Vpin 2.108 V  Vbat 4.101 V  VDDH 4.800 V
```

Hasil: lulus. Bacaan awal **4,101 V** hampir sama dengan Siglent **4,102 V**. Image di board: 1.1.1.

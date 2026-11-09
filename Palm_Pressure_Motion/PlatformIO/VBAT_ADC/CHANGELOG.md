# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/). Versi firmware mengikuti [Semantic Versioning](https://semver.org/).

## [1.1.1] - 2026-11-09

Titik kalibrasi diganti ke bacaan DMM Siglent.

- `Vbat = Vpin × 2 × 0,9726`. Titik: 4,154/4,299 dan 4,102/4,190.
- Sisa galat skala-saja sekitar ±0,03 V pada dua titik itu.

## [1.1.0] - 2026-11-09

Faktor kalibrasi terhadap voltmeter di pad Bat(+).

- `Vbat = Vpin × 2 × 0,973`. Angka 0,973 adalah rata-rata dari dua titik: 4,17/4,30 dan 4,09/4,19.
- Format baris serial tidak berubah. `Vpin` tetap sebelum kalibrasi; yang dikoreksi hanya `Vbat`.

## [1.0.0] - 2026-11-09

Rilis pertama untuk membaca tegangan Bat(+) di carrier skema 1.1.

- Pin ADC **P0.31**. Pembagi R5/R6 **1 MΩ / 1 MΩ**, C4 **100 nF** ke AGND. Faktor skala **×2**.
- ADC 12 bit, rentang penuh pin **3,6 V**. Satu baris tiap 1 detik: raw, V_pin, V_bat, dan VDDH/5.
- `TEST` merata-ratakan 16 sampel. Lulus jika `V_bat` ada di 2,5–4,5 V.

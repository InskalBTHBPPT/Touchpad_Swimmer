# HX711 — catatan pin (belum dipasang)

Tanggal: 2026-11-17  
Untuk proyek HX711 berikutnya. Belum masuk skema dan belum masuk firmware `Log_Session_Bin`.

Dua chip, masing-masing DOUT (DT) dan SCK sendiri.

| Chip | Sinyal | GPIO | Warna kabel |
|---|---|---|---|
| HX711-1 | SCK | P0.06 | kuning |
| HX711-1 | DT | P0.08 | hijau |
| HX711-2 | SCK | P0.20 | hijau lumut |
| HX711-2 | DT | P0.17 | orange |

P0.06 = TX dan P0.08 = RX hanya label `Serial1`. Firmware sekarang memakai USB, jadi kedua pin ini GPIO kosong. P0.17 dan P0.20 ada di header carrier dan tidak tersambung ke chip lain.

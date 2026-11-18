# Analisa pemakaian arus — `test_power_1`

**Tanggal rekaman:** 10 November 2026, ~08:55:55–09:03:50 WIB  
**Alat:** Siglent SDM3065X-SC, DC Current, interval **200 ms**  
**Sumber:** `test_power_1.csv`  
**Plot zona (dikoreksi):** `test_power_1_plot.png`  
**Board:** PalmLog1 / `Log_Session_Bin` (carrier 1.1), ukur di jalur baterai (bukan USB)

## Metode

- Zona waktu mengikuti plot yang sudah dikoreksi.
- **Mean / median / p95 / max** dari sampel arus (mA).
- **Muatan** dihitung integral trapesium \(\int I_+(t)\,dt\) (arus negatif OFF awal dibuang ke 0), lalu dibagi 3600 → **mAh**.
- Estimasi baterai: \(t_\mathrm{jam} = 0{,}8 \cdot C_\mathrm{mAh} / I_\mathrm{mA}\) (faktor 0,8 untuk sisa kapasitas / tegangan potong).

Catatan: sampling 200 ms menghaluskan burst pendek (<200 ms). Peak sesungguhnya bisa lebih tinggi.

## Zona (setelah koreksi)

| Zona | Waktu | Durasi | Mean | Median | p95 | Max | Muatan |
|---|---|---:|---:|---:|---:|---:|---:|
| OFF (awal) | 08:55:55–08:57:05 | 69,2 s | 0,50 mA | 0,33 mA | 0,90 | 4,51 | 0,0104 mAh |
| Advertising | 08:57:05–08:57:35 | 28,8 s | 7,46 mA | 7,73 mA | 7,96 | 7,98 | 0,0612 mAh |
| Connected | 08:57:35–08:58:42,5 | 67,2 s | 7,40 mA | 7,34 mA | 7,67 | 7,89 | 0,1380 mAh |
| Measure ON | 08:58:42,5–08:59:42 | 58,8 s | 7,49 mA | 7,36 mA | 8,65 | 9,09 | 0,1225 mAh |
| Connected | 08:59:42–09:00:33 | 50,7 s | 7,39 mA | 7,35 mA | 7,58 | 7,64 | 0,1041 mAh |
| Sync | 09:00:33–09:01:30 | 56,1 s | 7,70 mA | 7,69 mA | 7,91 | 8,00 | 0,1199 mAh |
| Connected | 09:01:30–09:01:45 | 14,4 s | 7,44 mA | 7,35 mA | 7,67 | 7,83 | 0,0297 mAh |
| Measure ON | 09:01:45–09:01:55 | 9,6 s | 7,88 mA | 7,57 mA | 8,95 | 8,99 | 0,0212 mAh |
| Stream + Measure | 09:01:55–09:02:18 | 22,3 s | **5,41 mA** | 5,08 mA | 6,90 | 8,03 | 0,0333 mAh |
| Measure ON | 09:02:18–09:02:48 | 29,4 s | 7,62 mA | 7,34 mA | 8,75 | 8,97 | 0,0622 mAh |
| Connected | 09:02:48–09:03:05 | 16,6 s | 7,44 mA | 7,45 mA | 7,62 | 7,66 | 0,0343 mAh |
| OFF (akhir) | 09:03:05–09:03:50 | 44,9 s | 0,81 mA | 0,73 mA | 1,02 | 4,05 | 0,0099 mAh |

### Agregat (mean berbobot durasi)

| Mode | Durasi total | \(I\) rata-rata | Muatan sesi |
|---|---:|---:|---:|
| OFF | 114 s | **0,62 mA** | 0,020 mAh |
| Advertising | 29 s | **7,46 mA** | 0,061 mAh |
| Connected | 149 s | **7,40 mA** | 0,306 mAh |
| Measure ON | 98 s | **7,57 mA** | 0,206 mAh |
| Sync | 56 s | **7,70 mA** | 0,120 mAh |
| Stream + Measure | 22 s | **5,41 mA** | 0,033 mAh |

**Temuan utama:** saat board ON (adv / connected / measure / sync), arus dasar hampir sama (**~7,4–7,7 mA**). Measure hampir tidak menambah mean dibanding Connected (~+0,17 mA). **Stream + Measure justru lebih rendah** di mean (~5,4 mA), dengan fluktuasi besar.

OFF awal punya mean 0,50 mA (median 0,33 mA) dengan spike sesekali; OFF akhir ~0,73–0,81 mA — keduanya bukan ≈0 mA absolut seperti sampel pertama System OFF penuh.

## Estimasi masa pakai baterai

Asumsi: \(t = 0{,}8 \cdot C / I\).  
**LIR2032** dipakai sebagai interpretasi “LIR3202” (koin rechargeable ~40 mAh, 3,6 V). Kapasitas pasti cek datasheet sel yang dipakai.

| Skenario | \(I\) (mA) | LIR2032 40 mAh | LiPo 140 mAh | LiPo 300 mAh | LiPo 400 mAh |
|---|---:|---:|---:|---:|---:|
| OFF | 0,62 | ~51 jam (2,1 hari) | ~180 jam (7,5 hari) | ~385 jam (16 hari) | ~513 jam (21 hari) |
| Advertising | 7,46 | ~4,3 jam | ~15 jam | ~32 jam | ~43 jam |
| Connected | 7,40 | ~4,3 jam | ~15 jam | ~32 jam | ~43 jam |
| Measure ON (stream OFF) | 7,57 | ~4,2 jam | ~15 jam | ~32 jam | ~42 jam |
| Stream + Measure | 5,41 | ~5,9 jam | ~21 jam | ~44 jam | ~59 jam |
| Sync | 7,70 | ~4,2 jam | ~15 jam | ~31 jam | ~42 jam |
| Mix 50% measure / 50% connected | 7,49 | ~4,3 jam | ~15 jam | ~32 jam | ~43 jam |
| Mix 20% measure / 80% connected | 7,44 | ~4,3 jam | ~15 jam | ~32 jam | ~43 jam |

Untuk lapangan (measure ON, stream OFF), **LiPo 140 mAh ≈ 15 jam**, **300 mAh ≈ 32 jam**, **400 mAh ≈ 42 jam**. LIR2032 hanya praktis jika hampir selalu OFF atau duty sangat rendah; continuous ON hanya ~4 jam.

Stream tidak dipakai untuk estimasi lapangan (kebijakan uji-only).

## Apa penyebab spike?

### Spike kecil di non-measure (Connected / Advertising / OFF)

Paling masuk akal **LED heartbeat**:

- Idle / measure OFF: **4 kedip**, ON 100 ms / OFF 250 ms, lalu tunggu 5 s.
- Sampling 200 ms sering “kena” sebagian pulse LED → tonjolan kecil di atas baseline ~7,3–7,4 mA, atau di OFF spike jarang hingga ~4 mA saat tombol/wake.

Penyebab sekunder: aktivitas BLE advertising/connection event singkat (biasanya di bawah resolusi 200 ms kecuali kebetulan tertangkap).

### Spike besar saat Measure ON (p95 ~8,6–9,0 mA)

Gabungan yang paling masuk akal:

1. **Tulis flash SPI (W25Q128)** — page program / load buffer tiap burst rekaman 100 Hz; arus flash + MCU naik sesaat.
2. **LED measure** — 2 kedip ON/OFF 100 ms tiap ~5 s, bertumpuk dengan tulis flash.
3. **I2C IMU + mag** di callback 10 ms — kontribusi lebih halus; kurang menjelaskan puncak ~9 mA sendirian.

Jadi spike besar ≈ **flash + LED (+ radio jika ada notifikasi)**; bukan karena “measure” mengubah baseline mean secara besar (mean tetap ~7,5 mA).

### Drop mean saat Stream + Measure (~5,4 mA)

Tidak berarti hemat daya sejati. Pola di plot: baseline turun tapi bergigi. Kemungkinan: beban BLE notify mengubah scheduling (lebih banyak tunggu radio / kurang burst flash serentak), atau aliasing 200 ms. Peak tetap ada (max ~8 mA). Jangan dipakai sebagai angka hemat untuk desain baterai.

## Ringkas

1. Board ON ≈ **7,4–7,7 mA** hampir tidak peduli Connected vs Measure.  
2. OFF ≈ **0,3–0,8 mA** (bukan selalu 0).  
3. Stream menurunkan mean terukur, bukan pilihan lapangan.  
4. Baterai lapangan: utamakan \(I \approx 7{,}5\,\mathrm{mA}\) → LiPo 140/300/400 mAh ≈ **15 / 32 / 42 jam**.  
5. Spike kecil ≈ LED; spike besar measure ≈ flash (+ LED).

# Resume: Tethered Swimming (Renang Terikat)

**Disusun berdasarkan literatur 1990–2024**  
**Folder referensi:** `Force_Motion/Paper/Download`

---

## a. Apa itu Tethered Swimming?

**Tethered swimming (TS)** — dalam bahasa Indonesia sering disebut *renang terikat* atau *renang dengan tali tetap* — adalah metode evaluasi dan latihan di mana perenang diikat ke titik tetap di kolam renang melalui tali/kabel yang hampir tidak elastis, sementara gaya dorong diukur oleh sensor gaya (*load cell* atau *strain gauge*). Perenang berenang di tempat (tanpa perpindahan horizontal), tetapi pola gerakan tetap dilakukan di lingkungan air yang sama dengan kompetisi (Morouço et al., 2024; Amaro et al., 2014).

Istilah "tethered swimming" diperkenalkan Magel (1970), berdasarkan ide Karpovich (1939) dan Mosterd (~1959) tentang pengukuran gaya dorong langsung di air (Morouço et al., 2024).

**Varian utama:**
| Jenis | Deskripsi | Referensi |
|-----|-----------|-----------|
| **Full tethered** | Perenang diam di tempat; seluruh gaya ke tali | Morouço et al., 2014 |
| **Semi-tethered** | Sebagian gaya ke tali, sebagian mengatasi drag aktif | Cortesi et al., 2024 |
| **Tethered in flume** | Tali + arus air (kolam berarus) | Ruiz-Navarro et al., 2020 |

TS dianggap **ergometer paling spesifik** untuk renang karena dilakukan di air dengan aktivasi otot yang mirip renang bebas, berbeda dari tes darat (bench, isokinetic) (Santos et al., 2017; Morouço et al., 2024).

---

## b. Latar Belakang Filsafat, Fisika & Matematika

### Prinsip fisika dasar

Pada renang bebas dengan kecepatan konstan, gaya dorong (propulsif) seimbang dengan hambatan hidrodinamik (drag):

$$F_P + F_D = 0 \quad \Rightarrow \quad F_P = -F_D$$

(Morouço et al., 2024; Cortesi et al., 2024)

Dengan mempertimbangkan massa tubuh dan massa air yang digerakkan:

$$F_P = F_D + (m_b + m_w) \cdot a$$

di mana \(F_P\) = gaya propulsif, \(F_D\) = drag, \(m_b\) = massa tubuh, \(m_w\) = massa air, \(a\) = percepatan (Morouço et al., 2024).

### Full tethered swimming

Saat kecepatan = 0 (tidak ada perpindahan), **tidak ada drag hidrodinamik**; seluruh gaya propulsif dialirkan ke tali:

$$F_P = F_T$$

(Cortesi et al., 2024)

### Semi-tethered swimming (metode residual thrust)

Gaya propulsif terbagi antara mengatasi beban tali dan mengatasi drag aktif:

$$F_P = F_{ST} + (-F_D) \quad \Rightarrow \quad F_D = F_P - F_{ST}$$

Drag aktif dihitung:

$$D_{a,ST} = F_T - F_{ST}$$

Koefisien drag spesifik kecepatan:

$$k_a = D_a / v^2$$

Metode planimetrik (perbandingan):

$$D_{a,PL} = k_p \cdot 1.5 \cdot v^2$$

Hasil empiris: **drag aktif ≈ 1,5× drag pasif** (Cortesi et al., 2024; Gatta et al., 2016).

### Koreksi geometri tali

Jika tali tidak horizontal (mis. dari starting block), gaya horizontal:

$$F_x = F \cdot \cos(\alpha)$$

(Morouço et al., 2024)

### Impuls mekanik

Impuls gaya selama siklus ayunan:

$$I = \int_{t_1}^{t_2} F(t)\,dt$$

Impuls lebih informatif daripada peak force tunggal karena memperhitungkan magnitude, durasi, dan arah gaya (Morouço et al., 2024; Dopsaj et al., 2000; Taylor et al., 2001).

### Hubungan gaya–kecepatan

Hubungan antara gaya tethered dan kecepatan renang **tidak selalu linear**; Keskinen et al. (1989) memodelkan hubungan polinomial orde-2, konsisten dengan kurva force–velocity (Morouço et al., 2024).

### Efisiensi propulsi

$$\eta_p = F_P / F_{TOT}$$

di mana \(F_{TOT}\) = total gaya yang dapat dihasilkan otot; \(\eta_p \approx 0{,}4\) pada full tethered dan renang bebas (Gatta et al., 2018; Cortesi et al., 2024).

---

## c. Metode Pengukuran (Hardware & Software)

### Peralatan hardware

| Komponen | Spesifikasi umum | Referensi |
|----------|------------------|-----------|
| **Load cell / strain gauge** | Submersible S-beam; kapasitas 100–500 kgf | Morouço et al., 2024; Gatta et al., 2016 |
| **Kabel/tali** | Baja 2,5–7 m, elastisitas dapat diabaikan | Morouço et al., 2024; Andrade et al., 2024 |
| **Sabuk pinggang** | Di pinggang atau pergelangan kaki (arms-only) | Morouço et al., 2015 |
| **Posisi sensor** | Starting block (umum) atau dinding langit-langit | Morouço et al., 2024 |
| **Frekuensi sampling** | 100–1000 Hz | Morouço et al., 2024; Andrade et al., 2024 |
| **DAQ** | USB acquisition board, amplifier analog | Andrade et al., 2024 |
| **Alternatif** | Swim-Spektro (semi-tethered), flume berarus, Smartpaddle IMU | Cortesi et al., 2024; Ruiz-Navarro et al., 2020 |

**Kalibrasi:** protokol beban bertingkat (0,1–10 kg) sebelum setiap sesi; estimasi error hysteresis, linearity, sensitivity < 1% (Morouço et al., 2011).

### Protokol pengujian

| Parameter | Nilai umum | Referensi |
|-----------|------------|-----------|
| **Durasi** | 10, 15, 20, 25, 30, 55 s; 1–3 min; 10–20 siklus lengkap | Carrasco-Poyatos et al., 2024 |
| **Intensitas** | All-out (maksimal) | Amaro et al., 2014 |
| **Pemanasan** | 500–1000 m + 2–3 siklus rendah intensitas | Morouço et al., 2024 |
| **Posisi awal** | Horizontal, tali penuh terentang | Morouço et al., 2024 |
| **Mulai akuisisi** | Setelah ayunan lengan pertama (hindari efek inersia tali) | Morouço et al., 2024 |
| **Suhu air** | 26–27 °C | Morouço et al., 2014 |

### Software & pemrosesan sinyal

1. **Akuisisi:** SENSIT, Globus software, Biopac AcqKnowledge, MATLAB
2. **Filter:** Butterworth low-pass orde-4; cutoff 4,5 Hz (residual analysis) (Morouço et al., 2024; Gatta et al., 2016)
3. **Koreksi sudut tali:** \(F_x = F \cdot \cos\alpha\)
4. **Ekspor:** format .txt → MATLAB/Python untuk analisis

### Variabel yang diukur

| Variabel | Definisi | Frekuensi penggunaan* |
|----------|----------|----------------------|
| Peak force (\(F_{peak}\)) | Gaya maksimum pada kurva F–t | 41/55 studi |
| Mean force (\(F_{mean}\)) | Rata-rata gaya selama uji | 39/55 |
| Impulse (\(I\)) | ∫F·dt per siklus atau total | 21/55 |
| Fatigue index | Penurunan gaya akhir vs awal | 11/55 |
| Rate of force development | Laju kenaikan gaya | 5/55 |
| VO₂, lactate, HR | Respons fisiologis | 6–10/55 |

*Carrasco-Poyatos et al. (2024), tinjauan sistematis 55 artikel.

---

## d. Metode Analisis Data & Statistik

### Parameter biomekanik dari kurva F–t

- **\(F_{peak}\):** nilai tertinggi kurva gaya–waktu
- **\(F_{mean}\):** rata-rata semua titik data selama durasi uji
- **Impulse per stroke:** integral gaya per siklus ayunan
- **Intra-cyclic force variation (dF):** variasi gaya antar siklus (Ruiz-Navarro et al., 2020)
- **Bilateral asymmetry index:** perbandingan gaya sisi kiri vs kanan (Santos et al., 2017)
- **Kontribusi lengan vs kaki:** perbandingan uji whole-body, arms-only, legs-only (Morouço et al., 2015)

### Analisis statistik umum

| Uji | Penggunaan | Contoh referensi |
|-----|------------|------------------|
| **Test–retest reliability** | ICC, CV, Cronbach's α | Amaro et al., 2014 (α = 0,970–0,995) |
| **Bland–Altman** | Kesepakatan antara metode | Cortesi et al., 2024 |
| **Pearson/Spearman correlation** | Hubungan gaya vs kecepatan | Morouço et al., 2014 (r = 0,91 impulse vs speed) |
| **Multiple regression** | Prediktor performa | Morouço et al., 2014 (impulse + SR → 84% varian 50 m) |
| **Repeated measures ANOVA** | Perbandingan kondisi beban | Cortesi et al., 2024 |
| **Bonferroni post-hoc** | Perbandingan berpasang | Cortesi et al., 2024 |
| **Effect size (η²)** | Magnitudo perbedaan | Cortesi et al., 2024 |
| **Shapiro–Wilk** | Normalitas data | Cortesi et al., 2024 |

### Temuan reliabilitas utama

- **30 detik all-out:** sangat reliabel untuk perenang dewasa dan remaja (Amaro et al., 2014; Nagle et al., 2016)
- **Impulse of force:** parameter paling reliabel dan berkorelasi linear dengan kecepatan (Carrasco-Poyatos et al., 2024; Amaro et al., 2014)
- **10 vs 30 detik:** keduanya reliabel pada perenang terlatih (IJSPP, 2025)

### Kualitas metodologis literatur

Tinjauan sistematis 55 artikel: skor kualitas Downs & Black 35,7–85,7% (rata-rata 65,7 ± 13,3%) (Carrasco-Poyatos et al., 2024).

---

## e. Manfaat untuk Performa Perenang

### 1. Evaluasi gaya spesifik di air
TS mengukur kapasitas menghasilkan gaya propulsif dalam kondisi ekologis, tidak dapat digantikan sepenuhnya oleh tes darat (Santos et al., 2017; Morouço et al., 2024).

### 2. Prediksi performa jarak pendek
- Korelasi kuat impulse maksimum per siklus vs kecepatan 50 m: **r = 0,91** (Morouço et al., 2014)
- Model regresi: impulse + stroke rate menjelaskan **84%** varian performa 50 m (Morouço et al., 2014)
- Hubungan lebih kuat untuk 50–100 m vs 200 m (Cortesi et al., 2024)

### 3. Identifikasi asimetri bilateral
TS memungkinkan kuantifikasi asimetri gaya kanan–kiri yang terkait performa 200 m, lebih valid daripada tes darat saja (Santos et al., 2017).

### 4. Kontribusi lengan vs kaki
- Lengan: ~66–70% gaya total (pria); kaki: ~30–33% (Morouço et al., 2015)
- Informasi untuk program latihan kekuatan spesifik segmen tubuh

### 5. Evaluasi kapasitas anaerob/aerob
- Protokol 30 s all-out sebagai adaptasi **Wingate test** untuk renang (Morouço et al., 2012, 2024)
- Dapat memantau lactate, HR, RPE tanpa perbedaan signifikan vs renang bebas durasi sama (Morouço et al., 2014)

### 6. Estimasi drag aktif & efisiensi hidrodinamik
Semi-tethered + full tethered memungkinkan estimasi drag aktif di kolam dengan instrumen dasar (Cortesi et al., 2024) — penting untuk menilai efek latihan teknik.

### 7. Monitoring progres latihan
- Test–retest reliabel untuk memantau perkembangan gaya dari musim ke musim (Amaro et al., 2014; Nagle Zera et al., 2021)
- Mendukung periodisasi: zona intensitas berbasis gaya kritis (*critical force*) (Keskinen et al., 2007)

### 8. Validitas ekologis vs renang bebas
Samson et al. (2018, 2024): gaya propulsif tangan pada tethered dan free swimming serupa (kecuali pace sprint maksimal). Perbedaan kecil pada kinematik tidak menghilangkan nilai prediktif TS.

### 9. Aplikasi praktis pelatih
- Prosedur sederhana, biaya relatif rendah, hemat waktu (Morouço, 2012 thesis; Morouço et al., 2024)
- Dapat dilakukan di kolam latihan rutin tanpa perlu trek panjang
- Semi-tethered dalam flume lebih prediktif performa daripada stationary tethered (Ruiz-Navarro et al., 2020)

---

## Kesimpulan Singkat

Tethered swimming adalah metode **valid, reliabel, dan spesifik** untuk menilai produksi gaya perenang di air. Secara fisik, pada full tethered seluruh gaya propulsif terukur di tali (\(F_P = F_T\)); pada semi-tethered gaya residual mengestimasi drag aktif. Parameter **impulse of force** dan **mean force** paling sering digunakan dan paling prediktif terhadap performa jarak pendek. Metode ini memberikan manfaat langsung bagi pelatih: evaluasi kekuatan spesifik air, deteksi asimetri, estimasi kontribusi lengan/kaki, dan monitoring perkembangan anaerob–aerob.

---

## Referensi utama (kutipan dalam teks)

1. Morouço, P., Tavares, D., & Silva, H. P. (2024). Tethered Swimming: Historical Notes and Future Prospects. *Encyclopedia*, 4(3), 1044–1061. https://doi.org/10.3390/encyclopedia4030067
2. Amaro, N., Marinho, D. A., Batalha, N., Marques, M. C., & Morouço, P. (2014). Reliability of tethered swimming evaluation in age group swimmers. *J Hum Kinet*, 41, 155–162. https://doi.org/10.2478/hukin-2014-0043
3. Morouço, P. G., Marinho, D. A., Keskinen, K. L., Badillo, J. J., & Marques, M. C. (2014). Tethered swimming can be used to evaluate force contribution for short-distance swimming performance. *J Strength Cond Res*, 28(11), 3093–3099. https://doi.org/10.1519/JSC.0000000000000509
4. Cortesi, M., Gatta, G., Carmigniani, R., & Zamparo, P. (2024). Estimating Active Drag Based on Full and Semi-Tethered Swimming Tests. *J Sports Sci Med*, 23, 17–24. https://doi.org/10.52082/jssm.2024.17
5. Carrasco-Poyatos, M., et al. (2024). Variables and protocols of the tethered swimming method: a systematic review. *Sport Sciences for Health*. https://doi.org/10.1007/s11332-023-01140-1
6. Gatta, G., Cortesi, M., & Zamparo, P. (2016). The relationship between power generated by thrust and power to overcome drag in elite short distance swimmers. *PLoS ONE*, 11(9), e0162387. https://doi.org/10.1371/journal.pone.0162387
7. Morouço, P. G., et al. (2015). Relative contribution of arms and legs in 30 s fully tethered front crawl swimming. *Biomed Res Int*, 2015, 563206. https://doi.org/10.1155/2015/563206
8. Santos, K. B., et al. (2017). Front crawl swimming performance and bi-lateral force asymmetry during land-based and tethered swimming tests. *Front Physiol*, 8, 342. https://doi.org/10.3389/fphys.2017.00342
9. Ruiz-Navarro, J. J., Morouço, P. G., & Arellano, R. (2020). Relationship between tethered swimming in a flume and swimming performance. *Int J Sports Physiol Perform*, 15(8), 1087–1094. https://doi.org/10.1123/ijspp.2019-0466
10. Samson, M., et al. (2018). Comparative study between fully tethered and free swimming at different paces. *Sports Biomechanics*, 18(6), 571–586. https://doi.org/10.1080/14763141.2018.1443492
11. Yeater, R. A., Martin, R. B., White, M. K., & Gilson, K. H. (1981). Tethered swimming forces in the crawl, breast and back strokes. *J Biomech*, 14(8), 527–537. https://doi.org/10.1016/0021-9290(81)90002-6
12. Keskinen, K. L., Tilli, L. J., & Komi, P. V. (1989). Maximum velocity swimming: stroking characteristics, force production and anthropometric variables. *Scand J Sport Sci*, 11, 87–92.

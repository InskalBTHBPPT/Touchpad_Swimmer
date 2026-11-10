# QnA — Decoupling nRF52840: SuperMini NoLogo / nice!nano v2 vs Seeed XIAO

Catatan ringkas dari diskusi desain (2026-11-10). Dimulai dari pin **DEC2 / A18**.

## Board yang dibandingkan

| Board | Sumber |
|---|---|
| SuperMini Pro Micro **NoLogo** | `Datasheet/Supermini_Promicro_NoLogo/schematic.png` (klon nice!nano v2) |
| nice!nano v2 | [schematic_nice_nano_v2.png](https://nicekeyboards.com/static/511ae101870d00c265b84f35d5f39eda/61100/schematic_nice_nano_v2.png) |
| Seeed XIAO nRF52840 Sense/Plus | PDF interaktif + `Seeed_XIAO_nRF52840_Plus/` |
| Referensi pabrikan Nordic | `D:\NonPengujian\NRF52840\Referensi\nordic` |

---

## Q1. DEC2 (A18) di NoLogo/nice!nano = NC, di XIAO ada C40=DNP. Maksudnya?

**A:** Pin **DEC2 (A18)** harus **floating** — tidak boleh dipasangi kapasitor eksternal (sesuai Nordic DevZone / reference).

| Notasi | Artinya | Di PCB | Elektrik |
|---|---|---|---|
| **NC** (NoLogo / nice!nano) | Tidak di-wire | Biasanya tidak ada pad C | Pin mengambang |
| **C40 = DNP** (XIAO) | *Do Not Place* | Ada footprint, part **tidak diisi** | Pin juga mengambang |

Hasilnya sama. Seeed (dan Nordic reference) sering tetap menggambar placeholder C sebagai N.C./DNP supaya jelas “jangan isi”, dan opsional cadangan layout. Nordic: kapasitor di DEC2 **jangan dipasang**; placeholder boleh dihapus dari PCB jika hemat ruang.

---

## Q2. VDD di NoLogo/nice!nano vs XIAO beda bagaimana?

**A:**

### NoLogo / nice!nano v2 (dekat referensi Nordic)
Semua pin **VDD** diikat ke satu net (`VDDNRF` / `VDD`), lalu bank kapasitor **paralel campuran**:

- 3× **100 nF**
- 1× **4,7 µF**
- 1× **1,0 µF**

Nordic tipikal: 4× 100 nF dekat pin VDD + 4,7 µF bulk + 1,0 µF — pola yang sama (satu rail + HF kecil + bulk).

### Seeed XIAO
Masing-masing pin VDD mendapat bypass lokal sekitar **1× 2,2 µF**. Net VDD biasanya tetap short di copper, tetapi **nilai per-pin** diganti 2,2 µF, bukan bank 100 nF + 4,7 µF + 1 µF.

| | NoLogo / nano v2 | XIAO |
|---|---|---|
| Net VDD | Semua short | Semua short (umumnya) |
| Decoupling | Bank campuran | Banyak 2,2 µF lokal |
| vs Nordic | Sangat dekat | Deviasi nilai; utamakan layout lokal |

---

## Q3. Nilai kapasitor total bank campuran NoLogo/nano berapa?

**A:** **6,0 µF** (nominal, parallel).

| Kapasitor | Nilai |
|---|---:|
| 3 × 100 nF | 0,30 µF |
| 1 × 4,7 µF | 4,70 µF |
| 1 × 1,0 µF | 1,00 µF |
| **Total** | **6,00 µF** |

Catatan: C efektif di board lebih kecil karena DC bias (X5R/X7R), terutama pada 4,7 µF dan 1 µF.

---

## Referensi cepat

- Nordic DevZone: *nRF52840 DEC2 Capacitor* — jangan pasang C di DEC2; ikuti reference (C N.C.).
- Nordic DevZone: placeholder C10/C13 di DEC2 boleh dihilangkan dari PCB; tujuannya menandai pin floating.
- Nordic PS / reference circuitry: VDD decoupling = 100 nF pada pin terkait + 4,7 µF (+ 1,0 µF sesuai config).

## Lanjutan

Perbandingan pin lengkap (daya/DEC/RF/USB vs Nordic **Config 4**):  
[`Perbandingan_Pin_nRF52840_NoLogo_nice-nano_XIAO.md`](Perbandingan_Pin_nRF52840_NoLogo_nice-nano_XIAO.md)

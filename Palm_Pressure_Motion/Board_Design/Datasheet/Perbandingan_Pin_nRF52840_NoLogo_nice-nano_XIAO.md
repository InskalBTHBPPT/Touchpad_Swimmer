# Perbandingan pin nRF52840: NoLogo · nice!nano v2 · Seeed XIAO (+ Nordic Config 4)

Tanggal: 2026-11-10  
Paket: **aQFN-73 / QIAA** (kecuali catatan).

## Referensi Nordic yang dipakai

Untuk **baterai + USB + DC/DC REG0 & REG1**, cocoknya:

| Config | VDDH | VDD | EXTSUPPLY | DCDCEN0 | DCDCEN1 | USB | NFC |
|---|---|---|---|---|---|---|---|
| **Config 4** | Battery / Ext. | N/A (dari REG0) | Yes | Yes | Yes | Yes | No |
| **Config 7** | sama | sama | sama | sama | sama | sama | No |

**Config 4 = referensi daya.** Config 7 hampir sama, beda utama: **RF match 4 komponen** (untuk TX ≥ 5 dBm).  
Sumber lokal: `D:\NonPengujian\NRF52840\Referensi\nordic\...\nrf52840_qiaa_config4_schematic.pdf`

NoLogo / nice!nano ≈ Config 4 (HV mode lewat VDDH + DCDC).  
XIAO Plus **menyimpang**: `VDDH` diikat ke rail **3V3** (mode praktis VDD≈VDDH), **DCCH = NC** (REG0 DCDC tidak dipakai).

---

## Sumber board

| Board | Sumber |
|---|---|
| SuperMini **NoLogo** | `Supermini_Promicro_NoLogo/promicro.kicad_sch`, `schematic.png` |
| **nice!nano v2** | [schematic](https://nicekeyboards.com/static/511ae101870d00c265b84f35d5f39eda/61100/schematic_nice_nano_v2.png) |
| **Seeed XIAO** nRF52840 Plus | PDF + `Seeed_XIAO_nRF52840_Plus/` |
| Nordic | Config 4 QIAA |

Singkatan: **NC** = tidak terhubung · **DNP / N.C.** = footprint ada, part tidak dipasang · **bank** = kapasitor paralel pada net bersama.

---

## 1. Ringkasan topologi daya

| Aspek | Nordic C4 | NoLogo | nice!nano v2 | XIAO Plus |
|---|---|---|---|---|
| Mode utama | **HV**: bat/ext → **VDDH** | HV: bat/USB → **VDDH** | HV: power-path charger → **VDDH** | **LV praktis**: LDO 3V3 → **VDD = VDDH** |
| Charger | — (external) | **TP4054** (LTH7R) + PMOS/dioda OR | Power-path (BQ2405x-class; clone sering BQ24057) | **BQ25100** + PMOS/dioda |
| REG0 (DCCH) | L **10 µH** → VDD | L **3,3 µH** → VDD | L **~10 µH** → VDD | **NC** |
| REG1 (DCC) | 10 µH + 15 nH → DEC4/6 | 10 µH + 15 nH → DEC4/6 | 10 µH + 15 nH → DEC4/6 | **10 µH saja** → DEC4-6 |
| LDO 3V3 eksternal | — | **ME6217** → EXTVCC (bukan VDD nRF) | **XC6220** → EXT_VCC | **U6 3V3** → mencatu **VDD+VDDH** nRF |
| VDD decoupling | 100 nF per pin + 4,7 µF + 1 µF | Bank campuran **6,0 µF** | Bank campuran mirip NoLogo | **2,2 µF lokal** per pin |

Detail power-path NoLogo: USB+ → TP4054 + Schottky ke VDDH; BAT → PMOS (gate dari USB+) → VDDH. Lihat juga `Desain_Alternative_Charging_Battery.md`.

---

## 2. Pin daya & DEC (inti perbandingan)

| Ball | Nama | Nordic Config 4 | NoLogo | nice!nano v2 | XIAO Plus |
|---|---|---|---|---|---|
| **B1** | VDD | VDD_nRF + **C14 1,0 µF** | `VDD` → bank | `VDD_NRF` → bank | `3V3` + **C41 2,2 µF** |
| **A22** | VDD | + **C12 100 nF** | bank | bank | + **C39 2,2 µF** |
| **AD14** | VDD | + **C7 100 nF** | bank | bank | `3V3` (tanpa C lokal jelas di BOM) |
| **AD23** | VDD | + **C8 100 nF** | bank | bank | + **C29 2,2 µF** |
| **W1** | VDD | + **C6 4,7 µF** (juga VEXT) | bank | bank | + **C6 2,2 µF** |
| **Y2** | VDDH | VDD_HV + **C19 4,7 µF** | `VDDH` + C bulk (≈4,7…10 µF) | `VDDH` dari OUT charger | **diikat `3V3`** |
| **AD2** | VBUS | **C21 4,7 µF** | **C24 ≈4,7 µF** | **≈4,7 µF** | **C25 2,2 µF** |
| **C1** | DEC1 | **C5 100 nF** | **≈100 nF** | **≈100 nF** | **C24 100 nF** |
| **A18** | DEC2 | **N.C.** (placeholder) | **NC** | **NC** | **C40 = DNP** (elektrik floating) |
| **D23** | DEC3 | **C11 100 pF** | **≈100 pF** | **≈100 pF** | **C35 100 pF** |
| **B5** | DEC4 | net DEC4_6: **1 µF + 47 nF** (+ C N.C.) | **1 µF + 47 nF** | **1 µF + 47 nF** | net DEC4-6: **C42 2,2 µF** |
| **E24** | DEC6 | diikat DEC4 | diikat DEC4 | diikat DEC4 | diikat DEC4 + **C34 100 nF** |
| **N24** | DEC5 | **C9 820 pF** (opsional Fxx+) | **≈820 pF** | **≈820 pF** | **C31 820 pF** |
| **AC5** | DECUSB | **C20 4,7 µF** | **≈4,7 µF** | **≈4,7 µF** | **C22 2,2 µF** |
| **B3** | DCC | **L2 10 µH → L3 15 nH → DEC4_6** | **10 µH → 15 nH → DEC4** | sama pola | **L3 10 µH → DEC4-6** (tanpa 15 nH) |
| **AB2** | DCCH | **L4 10 µH → VDD** | **L3 3u3 → VDD** | **≈10 µH → VDD** | **NC** |
| **B7** | VSS | GND | GND | GND | GND |
| **F23** | VSS_PA | GND (dekat RF shunt) | GND | GND / VSS_PA | GND |
| **EP** | GND pad | GND | GND | GND | GND (`VSS_PAD`) |

### Bank VDD NoLogo / nice!nano (nominal)

| | Nilai | Jumlah |
|---|---:|---:|
| | 100 nF | ×3 |
| | 4,7 µF | ×1 |
| | 1,0 µF | ×1 |
| **Total** | | **6,0 µF** |

Nordic menaruh 100 nF **dekat tiap pin VDD** + bulk; NoLogo/nano menggabungkan ke satu net (efek mirip jika via/trace pendek).

---

## 3. RF, kristal, USB data, SWD, reset

| Ball | Nama | Nordic C4 | NoLogo | nice!nano v2 | XIAO |
|---|---|---|---|---|---|
| **H23** | ANT | 0,8 pF – 4,7 nH – 0,5 pF (+ C N.C.) | **sama Nordic** (0,8 pF / 4,7 nH / 0,5 pF + DNP) | match beda (nilai C/L/R berbeda; antenna PCB) | **0,8 pF – 4,7 nH – 0,5 pF** → chip ant AN3216 |
| **B24** | XC1 | X1 32 MHz + **12 pF** | 32 MHz + **15 pF** | 32 MHz + **≈12 pF** | 32 MHz + **15 pF** |
| **A23** | XC2 | **12 pF** | **15 pF** | **≈12 pF** | **15 pF** |
| **D2/F2** | XL1/XL2 | opsional 32,768 + 12 pF | **ada** + ≈12 pF | **ada** + ≈12 pF | **ada** + **10 pF** |
| **AA24** | SWDCLK | header | header / TP | pad SWC | TP |
| **AC24** | SWDIO | header | header / TP | pad SWD | TP |
| **AD6** | D+ | langsung | **27 Ω** + ESD | langsung ke USB-C | **33 Ω** (tanpa ESD di BOM) |
| **AD4** | D− | langsung | **27 Ω** + ESD | langsung | **33 Ω** |
| **AC13** | P0.18 RESET | pin reset | ke header | ke header | **10 kΩ** pull-up + **100 nF** + tombol |

USB-C CC: NoLogo / nano / XIAO umumnya **5,1 kΩ** pull-down (UFP).

---

## 4. Apa yang “sama Nordic” vs “beda”

| Topik | Paling dekat Nordic C4 | Menyimpang |
|---|---|---|
| DEC2 (A18) | NoLogo / nano = NC; XIAO = DNP → **semua OK** | — |
| DEC1/3/5 | Ketiga board ≈ Nordic | — |
| DEC4/6 | NoLogo / nano = 1 µF+47 nH | XIAO = 2,2 µF (+100 nF di DEC6) |
| VDD caps | NoLogo / nano bank campuran | XIAO 2,2 µF/pin |
| REG1 DCDC | NoLogo / nano (+15 nH) | XIAO tanpa 15 nH |
| REG0 DCDC | NoLogo (L 3,3 µH!) / nano (~10 µH) | **XIAO NC** |
| VDDH | NoLogo / nano = HV dari bat/charger | **XIAO = 3V3** |
| RF match | NoLogo & XIAO ≈ C4 | nice!nano nilai beda |
| Charger | — | NoLogo TP4054; nano power-path; XIAO BQ25100 |

**Catatan NoLogo:** induktor **DCCH = 3,3 µH** (bukan 10 µH Nordic) — tetap DCDC REG0, tapi nilai L menyimpang dari reference.

---

## 5. GPIO / fitur board (ringkas, bukan pin-ball penuh)

GPIO mapping **sangat beda** antar form-factor; di sini hanya perbedaan penting:

| | NoLogo / nice!nano | XIAO Plus |
|---|---|---|
| Form | Pro Micro 2×13 | 23 pad half-hole XIAO |
| Power GPIO | P0.13 sering **POWER** (gate LDO EXTVCC) | P0.13 HICHG charger, P0.14 READ_BAT, P0.31 BAT sense |
| Extra | — | IMU LSM6DS3, mic PDM, RGB, QSPI footprint (U7 DNP) |

Untuk pinout header lengkap: lihat silk NoLogo / docs nice!nano / pinout XIAO.

---

## 6. QnA terkait (sudah ada)

Lihat juga: [`QnA_nRF52840_Decoupling_NoLogo_vs_XIAO.md`](QnA_nRF52840_Decoupling_NoLogo_vs_XIAO.md)  
(DEC2 A18 NC vs DNP · bank VDD 6 µF · XIAO 2,2 µF).

---

## Tingkat keyakinan

| Bagian | Keyakinan |
|---|---|
| Nordic Config 4 BOM/pin | Tinggi (PDF resmi) |
| NoLogo (KiCad) | Tinggi |
| XIAO (PDF+BOM) | Tinggi |
| nice!nano v2 (PNG skema) | Sedang–tinggi; P/N charger pastikan dari BOM resmi jika kritis |
| Nilai silkscreen C “≈” | Sedang jika hanya dari OCR gambar |

Jika nanti ada BOM nice!nano resmi, update baris charger dan C-designator nano di tabel ini.

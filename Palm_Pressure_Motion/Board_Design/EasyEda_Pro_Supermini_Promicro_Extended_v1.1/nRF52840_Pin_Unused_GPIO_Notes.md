# nRF52840 — Pin terpakai, kosong, & inner-row (QIAA aQFN73)

Catatan Palm-logger / nice!nano v2 (EasyEDA Pro).  
Simbol/footprint: LCSC **C1851953** / **C190794** (nRF52840-QIAA).  
Konvensi net skema: `104B` / `011B` → GPIO **P1.04** / **P0.11** (angka saja).

Sumber cek: skema Power_USB + Chip + Sensor (screenshot 2026-09), plus file ini sebelumnya.

---

## Ringkas audit

| Pertanyaan | Hasil |
|---|---|
| Apakah notes lama lengkap? | **Tidak.** Hanya mencatat `P0.13`; banyak pin proyek belum didokumentasikan. |
| Pin inner-row yang **sudah dipakai**? | **P0.07, P0.11, P0.12, P1.11, P1.12**, plus **P0.18 (nRESET)** & **DECUSB (AC5)** |
| Grup sensor pakai inner? | Ya — INT/DRDY/RTC INT + 2 pin SPI flash (lihat alternatif outer di bawah) |

---

## Semua pin nRF yang dipakai di proyek ini

### GPIO / sinyal digital

| GPIO | Net skema | Pad QIAA | Baris | Fungsi |
|---|---|---|---|---|
| **P0.02** | `002` | A12 | Outer | `Sen_AI1` (ADC filter) |
| **P0.04** | `004` | J1 | Outer* | ADC `VBAT` (divider R15/R16) |
| **P0.07** | `007` / `007B` | M2 | **Inner** | RTC `INT#` (RV-8263) |
| **P0.11** | `011` / `011B` | T2 | **Inner** | LSM6DSOX `INT1` |
| **P0.12** | `012` / `012B` | U1 | **Inner** | LIS3MDL `DRDY` |
| **P0.13** | `POWER_PIN` | AD8 | Outer | CE LDO → `EXT_VCC` |
| **P0.15** | `BLED` | AD10 | Outer | LED status |
| **P0.17** | (WKUP) | AD12 | Outer | Tombol wake PowerSave |
| **P0.18** | nRESET | AC13 | **Inner** | Reset (bukan GPIO biasa) |
| **P1.04** | `104` / `104B` | U24 | Outer | I2C SDA (IMU/mag/RTC) |
| **P1.06** | `106` / `106B` | R24 | Outer | I2C SCL |
| **P1.11** | `111` / `111B` | B19 | **Inner** | Flash SPI CLK |
| **P1.12** | `112` / `112B` | B17 | **Inner** | Flash SPI CS# |
| **P1.13** | `113` / `113B` | A16 | Outer | Flash SPI DI (MOSI) |
| **P1.15** | `115` / `115B` | A14 | Outer | Flash SPI DO (MISO) |

\*J1 di tepi kiri; escape biasanya masih Top tanpa via-in-pad (beda dengan kolom AC).

### Khusus USB / RF / kristal / power (bukan GPIO aplikasi)

| Pad / nama | Fungsi |
|---|---|
| AD2 `VBUS`, AD4 `D-`, AD6 `D+` | USB |
| AC5 `DECUSB` | Decap USB 3.3 V (**inner**) |
| D2/F2 `XL1/XL2` | Kristal 32.768 kHz |
| A23/B24 `XC2/XC1` | Kristal 32 MHz |
| H23 `ANT`, F23 `VSS_PA` | RF |
| B3 `DCC`, B5 `DEC4`, … | DC/DC & DEC |
| VDD / VDDH / VSS / EP | Power & ground |

### Catatan wiring sensor (bukan pin nRF)

- LIS3MDL **SDO/SA1 → GND** (alamat I2C `0x1C`), **CS → EXT_VCC** (mode I2C).  
- Jangan salah baca net `104B` pada SA1.

---

## Inner row QIAA (aQFN73)

Definisi layout: pad **baris kedua** (biasanya butuh via / channel sempit).  
- Sisi USB: kolom **AC** = inner, **AD** = outer  
- Sisi atas: baris **B** = inner, **A** = outer  
- Sisi kiri: pad `*2` + beberapa `*1` baris dalam (lihat tabel)

### GPIO inner — daftar lengkap (20 pin)

| GPIO | Pad | Catatan |
|---|---|---|
| **P0.05** | K2 | AIN3; NC / kosong |
| **P0.07** | M2 | RTC INT → diganti outer |
| **P0.11** | T2 | LSM INT1 → diganti outer |
| **P0.12** | U1 | LIS DRDY → diganti outer |
| **P0.14** | AC9 | NC / kosong |
| **P0.16** | AC11 | NC / kosong |
| **P0.18** | AC13 | **nRESET** (bukan GPIO aplikasi) |
| **P0.19** | AC15 | NC / kosong |
| **P0.21** | AC17 | NC / kosong |
| **P0.23** | AC19 | NC / kosong |
| **P0.25** | AC21 | NC / kosong |
| **P0.27** | H2 | NC / kosong |
| **P0.03** | B13 | AIN1; LF | | NC / kosong |
| **P0.28** | B11 | AIN4; LF | | NC / kosong |
| **P0.30** | B9 | AIN6; LF | | NC / kosong |
| **P1.08** | P2 | LF only | | NC / kosong |
| **P1.09** | R1 | NC / kosong |
| **P1.11** | B19 | Flash CLK → diganti outer |
| **P1.12** | B17 | Flash CS → diganti outer |
| **P1.14** | B15 | LF only | | NC / kosong |

### Non-GPIO di baris inner (penting)

| Nama | Pad |
|---|---|
| **DECUSB** | AC5 |
| **SWDIO** | AC24 |
| **DCC** | B3 |
| **DEC4** | B5 |
| **VSS** | B7 |
| **DEC1** | C1 |
| (+ DEC lain / VDD di baris B bila ada) | |

> Escape inner: jejak tipis keluar channel **atau** via di **luar** pad-field (bukan via 0,4/0,2 di dalam pad ≈0,27 mm).

**Catatan audit:** Versi notes sebelumnya **belum lengkap** (kurang **P0.05, P0.27, P1.09**; `P0.18` hanya di bagian reset). Tabel GPIO inner di atas sekarang **20/20**.
---

## Outer GPIO — setelah remap dari inner

### Sudah terpakai karena pindahan dari inner

| GPIO | Pad | Diganti dari (inner) | Fungsi |
|---|---|---|---|
| **P0.20** | AD16 | P0.11 (T2) | LSM6 INT1 |
| **P0.22** | AD18 | P0.12 (U1) | LIS3 DRDY |
| **P0.24** | AD20 | P0.07 (M2) | RTC INT# |
| **P1.00** | AD22 | P1.11 (B19) | Flash CLK |
| **P0.06** | L1 | P1.12 (B17) | Flash CS# |

### Outer yang masih kosong

| GPIO | Pad | Catatan |
|---|---|---|
| **P0.08** | N1 | — |
| **P0.26** | G1 | — |
| **P0.29** | A10 | AIN5 |
| **P0.31** | A8 | AIN7 |
| **P1.01** | Y23 | — |
| **P1.02** | W24 | — |
| **P1.03** | V23 | — |
| **P1.05** | T23 | LF |
| **P1.07** | P23 | LF |
| **P1.10** | A20 | LF |
| **P0.09 / P0.10** | L24 / J24 | NFC — GPIO hanya jika NFC off |

### Outer yang sudah terpakai dari awal (bukan hasil pindah)

**Jangan** anggap kosong: **P0.02, P0.04, P0.13, P0.15, P0.17, P1.04, P1.06, P1.13, P1.15**.

---

## Grup sensor — inner → outer (1 pin = 1 fungsi, tanpa bentrok)

Kolom AD hanya punya **4** outer kosong (`P0.20/22/24` + `P1.00`), sementara yang dipindah **5** sinyal → CS harus ke outer lain di luar AD.

### Remap yang disarankan (unik)

| Fungsi | Dari (inner) | Ke (outer) | Pad |
|---|---|---|---|
| LSM6 **INT1** | P0.11 | **P0.20** | AD16 |
| LIS3 **DRDY** | P0.12 | **P0.22** | AD18 |
| RTC **INT#** | P0.07 | **P0.24** | AD20 |
| Flash **CLK** | P1.11 | **P1.00** | AD22 |
| Flash **CS#** | P1.12 | **P0.06** | L1 |

Alternatif CS jika `P0.06` tidak ingin dipakai: **P1.01**, **P1.02**, **P0.05**, **P0.29**, **P0.31** (semua masih kosong / outer atau mudah escape).

Yang **sudah outer** (jangan dipindah): I2C **P1.04 / P1.06**, Flash **P1.13 / P1.15**.

Update `variant.h` / pin map firmware setelah ganti.

---

## Koreksi notes lama (“list tidak dipakai”)

Pin berikut **bukan** cadangan lagi (sudah terpakai):

| Pin | Dipakai untuk |
|---|---|
| **P0.04** | ADC VBAT |
| **P0.07** | RTC INT (bukan TRACE bebas) |
| **P0.11** | LSM INT1 |
| **P0.12** | LIS DRDY |
| **P0.15** | BLED |
| **P1.11 / P1.13 / P1.15** | Flash SCK / MOSI / MISO (header nice!nano) |
| **P0.06** | Flash CS# (firmware). P1.12 hanya pad dalam skema lama, tidak di header |
| **P1.04 / P1.06** | I2C |
| **P0.02** | Sen_AI1 |

Label TRACE tetap **boleh** jadi GPIO jika Trace/SWO off — tapi di board ini P0.07 / P0.11 / P0.12 **sudah di-assign**.

---

## Bukan GPIO — jangan dipakai sebagai I/O

| Pin | Catatan |
|---|---|
| **DEC2** | Power/decoupling; nice!nano = NC |
| **DEC\***, **DCC**, **VDD**, **VDDH**, **VBUS**, **ANT**, … | Power / RF |
| **P0.00 / P0.01** | XL1/XL2 |
| **P0.09 / P0.10** | NFC (GPIO hanya setelah disable NFC) |
| **P0.18** | nRESET |

---

## Referensi

- Product Spec: `Referensi/nordic/nRF52840_PS_v1.11.pdf` §7.1 QIAA / aQFN73  
- Datasheet LCSC: `SCH_PCB_Design/Easyeda_Pro/Datasheet/C190794_NRF52840-QIAA-R.pdf`  
- nice!nano schematic: [nicekeyboards](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/)  
- Sensor pin I2C: `SCH_PCB_Design/Easyeda_Standard/NanoNicev2/STEP_BY_STEP.md`

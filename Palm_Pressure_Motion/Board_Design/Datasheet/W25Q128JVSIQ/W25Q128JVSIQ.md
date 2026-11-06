# U1 W25Q128JVSIQ — pinout dan rangkaian minimum

Padanan 16 MB dari catatan breakout `NRF52840/SCH_PCB_Design/Flash_W25Q32JVSSIQ/W25Q32JVSSIQ_Breakout.md`.  
Di board ini chip **sudah terpasang sebagai U1** skema 1.1, bukan modul proto terpisah. Rangkaian minimum di bawah adalah yang sudah ada di PCB.

Datasheet: [`U1_W25Q128JVSIQ_C113767.pdf`](U1_W25Q128JVSIQ_C113767.pdf) — Winbond **W25Q128JV** Rev E (3 V, Dual/Quad SPI).  
LCSC **C113767**. Marking atas: **25Q128JVSQ**.

| Kode | Arti |
|---|---|
| W25Q128JV | 128 Mbit = **16 Mbyte** NOR SPI |
| **S** | SOIC-8 **208 mil**, pitch 1,27 mm |
| **I** | Industrial −40…+85 °C |
| **Q** | Green/RoHS; bit **QE = 1** dari pabrik (Quad IO2/IO3 aktif). Fungsi `/HOLD` mati |

Pinout **identik** W25Q32JVSSIQ (`SOIC-8_L5.3-W5.3-P1.27-LS8.0`). Listrik drop-in; yang beda hanya densitas dan JEDEC.

JEDEC ID (`9Fh`): **`EF 40 18`**. (`EF 40 16` = W25Q32 4 MB.)

Peta alamat: [`address-sector.md`](address-sector.md). Gambar hierarki: [`w25q128-hierarchy.png`](w25q128-hierarchy.png).

---

## Apa yang benar-benar wajib

Tanpa ini chip tidak merespons SPI:

| Item | Pin | Syarat |
|---|---|---|
| **VCC** | 8 | **2,7–3,6 V**. Di carrier: **3,3 V**. Decap **100 nF** menempel pin 8–4. Bulk **1 µF** di rail VCC. |
| **GND** | 4 | Ground (AGND, satu ground dengan SuperMini). |
| **/CS** | 1 | GPIO MCU, idle **HIGH**. Pull-up **10 kΩ** ke 3,3 V. |
| **DO (IO1)** | 2 | MISO ← MCU |
| **DI (IO0)** | 5 | MOSI → MCU |
| **CLK** | 6 | SCK |
| **/WP (IO2)** | 3 | **Jangan mengambang.** SPI 1-bit: pull-up 10 kΩ ke 3,3 V. |
| **/HOLD (IO3)** | 7 | **Jangan mengambang.** SPI 1-bit: pull-up 10 kΩ ke 3,3 V. |

Tidak perlu: kristal, LDO khusus, QSPI 4 kabel, level shifter (keduanya 3,3 V).

Suffix **Q**: pabrik menyetel **QE = 1**. Standard SPI (CLK `/CS` DI DO) **tetap jalan**. Pin 3 dan 7 jadi IO2/IO3 — di skema diikat ke 3,3 V lewat resistor.

---

## Pinout SOIC-8 208 mil (atas, pin 1 kiri atas)

```
        ┌──── W25Q128JVSIQ ────┐
   /CS │1                    8│ VCC
DO IO1 │2                    7│ /HOLD or /RESET (IO3)
/WP IO2│3                    6│ CLK
   GND │4                    5│ DI (IO0)
        └──────────────────────┘
```

| Pin | Nama | SPI 1-bit (dipakai board) | Quad (opsional, tidak di skema) |
|---|---|---|---|
| 1 | **/CS** | P0.10, pull-up 10 kΩ | sama |
| 2 | **DO (IO1)** | MISO P1.15 | IO1 |
| 3 | **/WP (IO2)** | pull-up 10 kΩ | IO2 ke MCU |
| 4 | **GND** | AGND | GND |
| 5 | **DI (IO0)** | MOSI P1.13 | IO0 |
| 6 | **CLK** | SCK P1.11 | SCK |
| 7 | **/HOLD (IO3)** | pull-up 10 kΩ | IO3 ke MCU |
| 8 | **VCC** | 3,3 V + 100 nF + 1 µF | sama |

---

## Rangkaian di skema 1.1

```
                         3V3
                          │
                 ┌────────┼────────────┬──────────┬──────────┐
                 │        │            │          │          │
               100 nF    10 k        10 k       10 k        │
               + 1 µF   (/CS)       (/WP)     (/HOLD)       │
                 │        │            │          │          │
                 │8 VCC   │1 /CS       │3         │7         │
              ┌──┴────────┴────────────┴──────────┴──┐       │
              │            W25Q128JVSIQ              │       │
 P1.13 MOSI ──┤5 DI (IO0)                            │       │
 P1.15 MISO ──┤2 DO (IO1)                            │       │
 P1.11 SCK  ──┤6 CLK                                 │       │
 P0.10 CS#  ──┤1 (sudah ke pull-up)                  │       │
 AGND ────────┤4 GND                                 │       │
              └──────────────────────────────────────┘       │
```

| Net flash | Header SuperMini | Pin nRF | Fungsi |
|---|---|---|---|
| CLK | **D14** | **P1.11** | SCK |
| DI | **D15** | **P1.13** | MOSI |
| DO | **D18** | **P1.15** | MISO |
| /CS | **D16** | **P0.10** | Chip select, idle HIGH |

SPI Mode **0 atau 3**. Uji `Flash_W25Q128` memakai Mode 0, 8 MHz.  
Alamat 24-bit: `0x000000` … `0xFFFFFF` (16 MB). Jangan pakai batas 4 MB (`0x3FFFFF`) dari catatan W25Q32.

Perintah uji: `9Fh` → `EF 40 18`. Baca: `03h` + 3 byte alamat. Tulis: `06h` (WREN) lalu `02h` page program (maks 256 B, tidak boleh melewati batas page). Hapus sektor 4 KB: `20h`.

Deep power-down `B9h` (typ. < 1 µA); bangun `ABh`.

---

## BOM yang relevan (skema 1.1)

| Ref | Nilai | Fungsi |
|---|---|---|
| U1 | W25Q128JVSIQ, C113767 | Flash 16 MB |
| C dekat VCC | 100 nF + 1 µF | Decap pin 8 |
| R `/CS`, `/WP`, `/HOLD` | 10 kΩ × 3 | Pull-up ke 3,3 V |

---

## Firmware

| Project | Status terhadap chip ini |
|---|---|
| `Palm_Pressure_Motion/PlatformIO/Flash_W25Q128` 1.0.0 | Menguji chip ini. `ID` harus `EF 40 18`. `TEST` di `0xFF0000`. Sudah lulus, lihat `TEST_LOG.md` |
| `Log_Session_Bin` dan `Log_Session_Bin_v3.1.1` | Masih mengharapkan W25Q32 (`EF 40 16`, 4 MB). Belum diporting |

---

## Cek setelah solder

1. VCC 3,3 V; `/CS` HIGH saat idle.
2. `9Fh` → `EF 40 18`.
3. Bukan `EF 40 16` (itu W25Q32).
4. `/WP` dan `/HOLD` ≈ 3,3 V.

Logging 100 Hz: **SPI 1-bit cukup**. Quad hanya jika butuh throughput jauh lebih tinggi (sambungkan IO2/IO3 ke GPIO, jangan hanya pull-up).

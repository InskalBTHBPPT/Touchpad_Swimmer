# Pin nRF52840 — power & charge (skematik Palm)

Daftar pin nRF yang terlihat terpakai dari dua blok skematik:

1. Charger BQ25100 + konektor `VB` / `CHG` + sense baterai
2. Power-path PMOS + LDO `EXT_VCC_3V3`

Hanya pin/net yang menyentuh nRF (GPIO atau power IC). Net board lain dicantumkan sebagai konteks.

## GPIO / analog

| Pin nRF | Net di skematik | Arah | Fungsi |
|---|---|---|---|
| **P0.13** | `P0.13_3V3_EN` | Output | Enable LDO TLV73333 (`U6`). EN juga di-pull ke `VDDH` lewat **R100 10 MΩ**. HIGH = `EXT_VCC_3V3` ON; LOW = LDO OFF (System OFF). |
| **P0.17** | `P0.17_CHG` | Input | Status charge dari pin **PRE-TERM** BQ25100 (`U2`). |
| **P0.31** | `P0.31_AIN7_BAT` | Analog in (AIN7) | Sense tegangan baterai lewat pembagi **R16 1 MΩ** + **R17 510 kΩ** dari `VBAT` ke GND. |

## Pin power nRF

| Pin nRF | Net di skematik | Fungsi |
|---|---|---|
| **VDDH** | `VDDH` | Mode HV. Disuplai dari power-path: `VBUS` lewat **D1**, atau `VBAT` lewat **Q1** (SL3139KL). Bypass saat ini **C4 2,2 µF** (disarankan naik ke **4,7 µF**). |
| **VBUS** | `VBUS` | Pin USB detect / USB regulator nRF (paket AQFN: **AD2**). Sambungkan ke net `VBUS` yang sama dengan anoda D1, gate Q1, R9, dan D2→IN BQ. Bypass tipikal **4,7 µF** di dekat pin + **DECUSB**. Belum digambar di dua blok power/charge, tapi wajib jika USB data dipakai (UF2/serial). |
| **GND** | `GND` | Ground bersama charger, LDO, konektor, dan sense. |

Belum digambar di dua blok ini (tetap diperlukan untuk gaya NoLogo/nano):

| Pin nRF | Catatan |
|---|---|
| **VDD** | Output REG0 internal di mode HV. Jangan diikat ke `EXT_VCC_3V3`. Bypass tipikal **4,7 µF** dekat pin. |
| **DECUSB** | Decoupling regulator USB internal; tipikal **4,7 µF** (NoLogo/nano). |

## Net terkait (bukan pin GPIO nRF)

| Net | Sumber / tujuan |
|---|---|
| `VBAT` | OUT BQ25100 → konektor `VB` + Drain path Q1 + pembagi R16/R17 |
| `VBUS` | USB 5 V → D1/Q1 gate/R9 + D2 ke IN BQ |
| `CHG` (konektor) | ALT 5 V charge-only → D3 → IN BQ (tidak menghidupi `VDDH` langsung) |
| `CE` | Net enable BQ25100 (bukan GPIO nRF di gambar ini); TS lewat **R20 10 kΩ** |
| `EXT_VCC_3V3` | OUT TLV73333 → peripheral saja |
| `Out_R12` | Cabang ISET / JP1 charge-boost (**R12** / **R18** 2,7 kΩ) |

## Ringkas pemakaian pin

```text
P0.13  → EN LDO EXT_VCC_3V3
P0.17  → status CHG (PRE-TERM BQ25100)
P0.31  → ADC baterai (AIN7)

VDDH   ← power-path (VBAT / VBUS)
VBUS   ← net VBUS USB 5 V (sama dengan D1 / gate Q1 / D2)
GND    ← ground sistem
```

## Catatan singkat dari skematik

- Mode power mengikuti **NoLogo / nice!nano**: `VDDH` dari baterai/USB, LDO eksternal hanya untuk peripheral.
- `CHG` hanya untuk mengisi baterai lewat BQ; board hidup dari `VBAT` atau `VBUS`.
- Konektor `VB` dan `CHG`: JST SH right-angle `SM02B-SRSS-TB` (C160402).

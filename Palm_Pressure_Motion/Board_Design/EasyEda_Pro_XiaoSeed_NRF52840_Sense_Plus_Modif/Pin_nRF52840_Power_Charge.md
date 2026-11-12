# Pin nRF52840 — power, charge, RTC, flash (skematik Palm)

Daftar pin nRF yang terpakai di desain EasyEDA Pro (modif XIAO Sense Plus), dicek terhadap firmware `PlatformIO/Log_Session_Bin` (board `nicenano`).

Sumber skematik:

1. Charger BQ25100 + konektor `VB` / `CHG` + sense baterai
2. Power-path PMOS + LDO `EXT_VCC_3V3`
3. RTC RV-3032 + pull-up I2C
4. Flash W25Q128JVSIQ

## Cocok dengan Log_Session_Bin?

**Ya — pin Flash, RTC/I2C, EXT_VCC, dan CS sudah selaras** dengan komentar firmware dan `boards/nicenano/variant.h`.

| Fungsi | Skematik | Firmware / variant | Status |
|---|---|---|---|
| Flash SCK | `P111_CLK` → **P1.11** | `PIN_SPI_SCK` = 43 (`PIN_111`) | OK |
| Flash MOSI (DI) | `P113_D1` → **P1.13** | `PIN_SPI_MOSI` = 45 (`PIN_113`) | OK |
| Flash MISO (DO) | `P115_DO` → **P1.15** | `PIN_SPI_MISO` = 47 (`PIN_115`) | OK |
| Flash CS | `P010_CS` → **P0.10** | `PIN_FLASH_CS` = `PIN_010` | OK |
| I2C SDA (RTC/IMU) | `P104_SDA` → **P1.04** | `PIN_WIRE_SDA` = 36 (`PIN_104`) | OK |
| I2C SCL (RTC/IMU) | `P106_SCL` → **P1.06** | `PIN_WIRE_SCL` = 38 (`PIN_106`) | OK |
| EXT_VCC enable | `P0.13_3V3_EN` → **P0.13** | `PIN_EXT_VCC` = `PIN_013` | OK |
| VBAT ADC | `P0.31_AIN7_BAT` → **P0.31** | `PIN_VBAT` = `PIN_031` | OK pin |

Catatan ketidaksesuaian non-pin:

| Item | Skematik | Firmware | Tindakan |
|---|---|---|---|
| Pembagi VBAT | **R16 1 MΩ + R17 510 kΩ** (rasio ≠ 2) | Asumsi **1 MΩ / 1 MΩ**, `VBAT_DIVIDER = 2.0` | Ubah resistor ke 1M/1M, atau ubah rumus firmware |
| `P0.17_CHG` | Ada (PRE-TERM BQ) | Belum dipakai di `Log_Session_Bin` | Boleh tetap; firmware nanti |

Pin firmware lain yang belum terlihat di cuplikan skematik ini: **P0.24** (tombol), **P0.15** (LED).

---

## GPIO / analog — power & charge

| Pin nRF | Net di skematik | Arah | Fungsi |
|---|---|---|---|
| **P0.13** | `P0.13_3V3_EN` | Output | Enable LDO TLV73333 (`U6`). EN juga di-pull ke `VDDH` lewat **R100 10 MΩ**. |
| **P0.17** | `P0.17_CHG` | Input | Status charge dari **PRE-TERM** BQ25100 (`U2`). Belum dibaca firmware. |
| **P0.31** | `P0.31_AIN7_BAT` | Analog (AIN7) | Sense `VBAT` lewat R16/R17. |

## GPIO — Flash W25Q128 (`U4`)

| Pin nRF | Net | Arah | Fungsi |
|---|---|---|---|
| **P0.10** | `P010_CS` | Output | `CS#` + pull-up **R109 10 kΩ** ke `EXT_VCC_3V3` |
| **P1.11** | `P111_CLK` | Output | SPI SCK |
| **P1.13** | `P113_D1` | Output | SPI MOSI → `DI(IO0)` (nama net = DI) |
| **P1.15** | `P115_DO` | Input | SPI MISO ← `DO(IO1)` |

Lain di flash (bukan GPIO nRF):

- `WP#(IO2)` → pull-up **R108 10 kΩ** ke `EXT_VCC_3V3`
- `HOLD#/RESET#(IO3)` → pull-up **R110 10 kΩ** ke `EXT_VCC_3V3`
- `VCC` → `EXT_VCC_3V3`
- Decap: **C104 100 nF** + **C103 1 µF** ke GND (boleh footprint 0402/0603)

## GPIO — RTC RV-3032 (`U3`) + I2C

| Pin nRF | Net | Arah | Fungsi |
|---|---|---|---|
| **P1.04** | `P104_SDA` | I2C | SDA RTC (+ IMU di firmware) |
| **P1.06** | `P106_SCL` | I2C | SCL RTC (+ IMU di firmware) |

Lain di RTC:

| Pin RTC | Sambungan |
|---|---|
| VDD | `EXT_VCC_3V3` + **C101 100 nF** |
| VBACKUP | `VBAT` |
| VSS | GND |
| EVI | pull-up **R107 10 kΩ** ke `EXT_VCC_3V3` |
| INT# / CLKOUT | NC (OK untuk firmware sekarang) |

Pull-up bus I2C:

| Ref | Nilai | Net |
|---|---|---|
| **R104** | 10 kΩ | `EXT_VCC_3V3` → `P104_SDA` |
| **R106** | 10 kΩ | `EXT_VCC_3V3` → `P106_SCL` |

Pakai **10 kΩ 0201 `C473048`** (sudah di mapping BOM). Pull-up harus ke `EXT_VCC_3V3`, bukan `VDDH`.

---

## Pin power nRF

| Pin nRF | Net | Fungsi |
|---|---|---|
| **VDDH** | `VDDH` | Mode HV dari power-path (`VBUS`/D1 atau `VBAT`/Q1). Bypass saat ini C4 2,2 µF → disarankan **4,7 µF**. |
| **VBUS** | `VBUS` | Pin USB nRF (AD2). Sambung ke net `VBUS` yang sama dengan D1 / gate Q1 / D2. + ~4,7 µF dan **DECUSB**. |
| **GND** | `GND` | Ground bersama. |
| **VDD** | (belum di blok ini) | Output REG0 HV. Hanya bypass **4,7 µF**; jangan ke `EXT_VCC_3V3`. |

---

## Net terkait (bukan GPIO)

| Net | Sumber / tujuan |
|---|---|
| `VBAT` | OUT BQ → konektor `VB` + Q1 + pembagi + `VBACKUP` RTC |
| `VBUS` | USB 5 V → D1 / Q1 gate / R9 / D2→IN BQ / pin VBUS nRF |
| `CHG` | ALT 5 V charge-only → D3 → IN BQ |
| `EXT_VCC_3V3` | OUT TLV73333 → RTC, flash, pull-up, (IMU) |
| `CE` | Enable BQ (bukan GPIO nRF di gambar) |
| `Out_R12` | Cabang ISET / JP1 (**R12** / **R18** 2,7 kΩ) |

---

## Ringkas pemakaian pin

```text
Power / charge
  P0.13  → EN LDO EXT_VCC_3V3
  P0.17  → status CHG (PRE-TERM)   [firmware belum pakai]
  P0.31  → ADC baterai

Flash W25Q128
  P0.10  → CS#
  P1.11  → SCK
  P1.13  → MOSI (DI)
  P1.15  → MISO (DO)

RTC / I2C
  P1.04  → SDA
  P1.06  → SCL

Power pins nRF
  VDDH   ← power-path
  VBUS   ← net VBUS USB 5 V
  VDD    ← bypass saja (HV)
  GND    ← ground
```

## Checklist wiring nRF yang masih perlu

- [ ] Semua net di atas sudah diikat ke pin footprint nRF (kamu bilang belum semua)
- [ ] `VDD` bypass 4,7 µF (bukan ke LDO)
- [ ] `VBUS` nRF + DECUSB
- [ ] Tombol **P0.24**, LED **P0.15** (firmware)
- [ ] Putuskan/ sesuaikan pembagi VBAT vs `VBAT_DIVIDER` di firmware

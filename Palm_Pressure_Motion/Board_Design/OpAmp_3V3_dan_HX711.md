# Op-amp 3,3 V dan HX711 (Palm)

Catatan singkat untuk frontend sensor tekanan / load cell pada board Palm (rail **`EXT_VCC_3V3`** / 3,3 V).

## Op-amp yang bisa disuplai 3,3 V

Banyak op-amp modern jalan di 3,3 V. Pilih yang **rail-to-rail** (idealnya input + output) dan Vsupply minimum ≤ 3,3 V.

| Part | Supply tipikal | Catatan | LCSC / cari |
|---|---|---|---|
| **MCP6001 / MCP6002** | 1,8–6 V | Murah, RRIO, single/dual | `MCP6001` / `MCP6002` |
| **TLV9001 / TLV9002** | 1,8–5,5 V | RRIO, cukup quiet | `TLV9001` / `TLV9002` |
| **LMV321 / LMV358** | 2,7–5,5 V | Umum, single/dual | `LMV321` / `LMV358` |
| **OPA333** | 1,8–5,5 V | Precision, low offset | `OPA333` |

**Aturan pakai di Palm**

- Suplai dari **`EXT_VCC_3V3`** (+ decap 100 nF dekat pin V+).
- Output op-amp jangan melebihi 3,3 V ke pin ADC/GPIO nRF.
- Untuk sinyal jembatan (mV), op-amp biasa sering kurang; pertimbangkan **INA** (instrumentation) atau **HX711**.

## HX711 — bukan sekadar op-amp

**HX711** = **ADC 24-bit + PGA** khusus load cell / strain gauge (Wheatstone bridge).

| Blok di dalam HX711 | Fungsi |
|---|---|
| PGA | Gain tetap **32 / 64 / 128** |
| ADC | 24-bit, keluaran serial |
| Interface | **DOUT** + **SCK** (bukan keluaran analog) |

Supply tipikal **2,6–5,5 V** → **3,3 V aman** (boleh dari `EXT_VCC_3V3`).

```text
Load cell (bridge)
    │
    ▼
 HX711 (PGA + ADC 24-bit)
    │  DOUT / SCK
    ▼
 nRF52840 (GPIO / soft SPI)
```

## Kapan pakai apa

| Sensor / sinyal | Pilihan |
|---|---|
| Load cell / strain (jembatan, mV) | **HX711** (atau ADC eksternal + INA) |
| Sudah 0–~3 V analog | Op-amp buffer/gain + **ADC nRF** (atau ADC eksternal) |
| Perlu gain akurat + differential | INA (mis. INA333) @ 3,3 V, lalu ADC |

## Catatan board Palm

- `EXT_VCC_3V3` bisa **mati** saat System OFF (`P0.13` LOW). Sensor + HX711/op-amp ikut mati — biasanya OK untuk logger.
- Jangan suplai HX711 dari `VDDH` (3,7–5 V) ke pin data 3,3 V tanpa level care; lebih sederhana satu rail **3,3 V**.
- Decap: **100 nF** (+ boleh 1–10 µF bulk) dekat pin VCC HX711 / op-amp.

## Referensi terkait

- Power rail: `EasyEda_Pro_XiaoSeed_NRF52840_Sense_Plus_Modif/Pin_nRF52840_Power_Charge.md`
- Charge alternatif: `Desain_Alternative_Charging_Battery.md`

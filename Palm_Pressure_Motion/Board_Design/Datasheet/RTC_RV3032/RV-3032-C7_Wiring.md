# RV-3032-C7 — datasheet & wiring

LCSC **C5127802** — `RV-3032-C7-32.768kHz-2.5PPM-TA-QC`  
Paket: **SMD3215-8P** (3,2 × 1,5 × 0,8 mm). Kristal 32,768 kHz + TCXO di dalam.

## Dokumen (lokal + resmi)

| Dokumen | Lokal | Online |
|---|---|---|
| Datasheet | [`../Easyeda_Pro/Datasheet/RV-3032-C7.pdf`](../Easyeda_Pro/Datasheet/RV-3032-C7.pdf) | [microcrystal.com](https://www.microcrystal.com/fileadmin/Media/Products/RTC/Datasheet/RV-3032-C7.pdf) |
| Application Manual (register, wiring detail) | [`../Easyeda_Pro/Datasheet/RV-3032-C7_App-Manual.pdf`](../Easyeda_Pro/Datasheet/RV-3032-C7_App-Manual.pdf) | [App Manual](https://www.microcrystal.com/fileadmin/Media/Products/RTC/App.Manual/RV-3032-C7_App-Manual.pdf) |
| Demo board | [`../Easyeda_Pro/Datasheet/RV-3032-C7_Demo-Board.pdf`](../Easyeda_Pro/Datasheet/RV-3032-C7_Demo-Board.pdf) | [Demo Board](https://www.microcrystal.com/fileadmin/Media/Products/RTC/Demoboard/RV-3032-C7_Demo-Board.pdf) |
| LCSC | — | [C5127802](https://www.lcsc.com/product-detail/C5127802.html) |

Alamat I2C 7-bit: **`0x51`** (write `0xA2`, read `0xA3`) — sama dengan RV-8263.

---

## Pinout (pandangan atas)

```
        ┌──── RV-3032-C7 ────┐
 VBACKUP│1                 8│SCL
     SDA│2                 7│CLKOUT
     INT│3                 6│VDD
     EVI│4                 5│VSS
        └────────────────────┘
```

| Pin | Nama | Tipe | Wajib / catatan |
|---|---|---|---|
| 1 | **VBACKUP** | Power backup | Baterai/superkap **atau** ke VSS lewat **10 kΩ** jika tidak dipakai |
| 2 | **SDA** | OD I2C | Pull-up ke VDD |
| 3 | **INT** | OD, active LOW | Pull-up ke VDD jika dipakai; tetap aktif saat mode VBACKUP |
| 4 | **EVI** | Input event | **Jangan floating.** Tidak dipakai: pull ke VDD (atau GND sesuai EHL default). **Jangan** ke VBACKUP |
| 5 | **VSS** | GND | GND |
| 6 | **VDD** | Power | 1,3–5,5 V (nRF: **3,3 V**) + decap **100 nF** dekat pin |
| 7 | **CLKOUT** | Push-pull | Tidak dipakai: **NC / floating**. Jangan ke VDD atau GND |
| 8 | **SCL** | I2C clock | Pull-up ke VDD |

---

## Skema minimum (PalmLog / SuperMini)

Bus I2C (ada di header SuperMini / Pro Micro): **SDA P1.04 (`104`)**, **SCL P1.06 (`106`)**.  
Pull-up 10 kΩ: ada di **PCB carrier** → jangan dobel di modul; di breadboard / SuperMini polos → pasang sendiri.

**INT — jangan pakai P0.07 di SuperMini.** Pin itu hanya di board QIAA/NiceNano-style (inner, silk `007`), **tidak** keluar di header SuperMini.

| Platform | Pin INT RTC | Catatan |
|---|---|---|
| SuperMini + proto | **NC** (cukup I2C) atau GPIO header kosong | **Bukan P0.17** — itu tombol ukur (`D2` / silk `017`) di firmware 3.1.x |
| Carrier remap (outer) | **P0.24** (disarankan) | Pengganti P0.07 dari skema QIAA lama |
| Board QIAA lama | P0.07 | Hanya jika pad `007` memang di-route |

### A) Tanpa baterai backup (VDD selalu hidup)

```
  3V3 ──┬── 100 nF ── GND
        │
        ├── VDD (6)
        │
        ├── Rpu 10k ── SDA (2) ──→ P1.04   } skip Rpu jika host sudah punya
        ├── Rpu 10k ── SCL (8) ──→ P1.06
        │
        ├── Rpu 10k ── INT (3) ──→ P0.24 (carrier) / NC (SuperMini proto)
        │
        ├── EVI (4) ── R 10k ── 3V3        (jika EVI tidak dipakai)
        │
  VBACKUP (1) ── R 10k ── GND              (backup off — wajib per App Manual)
  CLKOUT (7) ── NC
  VSS (5) ── GND
```

### B) Dengan coin cell / superkap (jam jalan saat 3V3 mati)

```
  3V3 ── 100 nF ── GND ──→ VDD (6)
  Bat+ / CeraCharge+ ──→ VBACKUP (1)
  Bat− / C− ── GND

  SDA/SCL/INT/EVI/CLKOUT sama seperti A
```

- Trickle charger **bisa diaktifkan lewat register EEPROM** — jangan charge CR2032 primer kecuali sudah set mode yang aman (lihat App Manual § Power Management). Default aman: charger **off**, sel primer ke VBACKUP saja.
- Saat VDD mati, I2C **mati**; waktu tetap jalan dari VBACKUP. INT masih bisa aktif (kecuali EVI).

---

## Perbedaan penting vs RV-8263 (U6)

| | RV-3032-C7 | RV-8263-C8 |
|---|---|---|
| Footprint | **3,2 × 1,5** (C7) | **2,0 × 1,2** (C8) — **bukan drop-in** |
| Pin 1 | **VBACKUP** | (pinout C8 beda — lihat datasheet 8263) |
| Backup | saklar otomatis di chip | tidak ada |
| CLKOUT | push-pull → **jangan** ke GND/VDD | mengikuti App Manual 8263 |
| EVI | ada; jangan floating | — |

Jangan ganti nomor part di footprint U6 RV-8263. Layout ulang pad C7.

---

## Checklist PCB

1. Decap 100 nF VDD–VSS sedekat mungkin.
2. VBACKUP: baterai **atau** 10 kΩ ke GND — tidak floating.
3. EVI: pull 10 kΩ ke 3V3 jika tidak dipakai; jangan ke VBACKUP.
4. CLKOUT: NC jika tidak dipakai.
5. Pull-up SDA/SCL/INT ke **3V3** (bukan VBACKUP).
6. Alamat `0x51` — bentrok jika RV-8263 masih di bus yang sama.

---

## Firmware (ringkas)

Bukan RTClib/DS3231. Opsi: **bb_rtc**, RTC_I2C, atau fork KineticLabs (dari RV-8803).  
PalmLog 3.1.1 saat ini pakai DS3231 → perlu adapter driver jika ganti ke RV-3032.

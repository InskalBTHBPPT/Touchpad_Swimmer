# Desain alternatif charging baterai (OR ke USB+/VBUS)

Catatan desain untuk PalmLog / SuperMini Pro Micro (nRF52840): menambah port charge alternatif selain USB-C, tanpa mengubah jalur charger dan power-path yang sudah ada di modul.

Referensi skema modul: `Datasheet/Supermini_Promicro_NoLogo/schematic.png` (dan `promicro.kicad_sch`).

## Ringkasan

| Item | Pilihan |
|---|---|
| Titik injeksi | Net **`USB+`** (di KiCad sering **`VBUS`**) |
| Metode | **Diode-OR** dari USB-C VBUS dan port alternatif |
| Tegangan alternatif | ~**5 V** (rentang charge USB / TP4054) |
| Jangan injeksi ke | `BAT`, `VDDH`, `EXTVCC` |

Dengan OR ke `USB+`, sumber mana pun yang aktif akan:

1. Mengisi baterai lewat **TP4045/TP4054** (pin VCC)
2. Menarik gate P-FET power-path → memutus jalur bat → sistem
3. Menyuplai sistem lewat Schottky existing (`NBD1`) ke **`VDDH`**
4. Menghidupkan LED CHRG (jika di-drive dari `USB+`)

## Power path SuperMini (existing)

```text
USB-C VBUS ──► USB+ ──┬──► TP4054 VCC ──► BAT (sel)
                      │
                      ├──► gate P-FET (mati saat USB+ high)
                      │
                      └──► Schottky NBD1 ──► VDDH ──► LDO ──► EXTVCC (3V3)

BAT ──► P-FET (ON saat USB+ low) ──► VDDH
```

Arus charge diatur resistor **PROG** (mis. 10k ≈ 100 mA; pad 2k diisi ≈ ~500 mA).

## Desain alternatif: diode-OR

### Skema usulan

```text
                         Schottky D1
USB-C VBUS ─────────────►|──────────┐
                                    │
                                    ├── USB+ / VBUS ──► TP4054 VCC
                                    │                └─► gate FET + NBD1 → VDDH
                         Schottky D2│
ALT CHARGE (+5 V) ──────►|──────────┘

GND USB ────────────────────────────┬── GND board / GND ALT
GND ALT ────────────────────────────┘
```

### Perilaku

| Kondisi | Hasil |
|---|---|
| Hanya USB | `USB+` dari USB; D2 reverse → ALT tidak ke-backfeed |
| Hanya ALT | `USB+` dari ALT; D1 reverse → host USB tidak ke-backfeed |
| Keduanya | Sumber dengan tegangan lebih tinggi “menang”; yang lain terblokir diodanya |

### Mengapa tidak langsung parallel (tanpa dioda)

```text
USB-C VBUS ────┐
               ├── USB+   ← berbahaya: 5 V ALT bisa masuk ke host USB
ALT 5V ────────┘
```

## Titik net: boleh vs tidak

| Net | Fungsi | Alternatif charge? |
|---|---|---|
| **`USB+` / `VBUS`** | Input charger + kontrol power-path | **Ya — OR di sini** |
| `BAT` | Keluaran charger + sel | **Tidak** — bypass limit & terminasi charge |
| `VDDH` | Rail sistem setelah FET/dioda | **Tidak** — board hidup, baterai tidak ter-charge benar |
| `EXTVCC` | 3V3 LDO | **Tidak** |

## Komponen praktis

- Dioda: Schottky (mis. **BAT60**, **SS14**, atau sejenis) — drop ~0,2–0,4 V agar `USB+` tetap cukup untuk TP4054.
- Port ALT: pogo / magnetic / DC jack / connector dock — hanya **+5 V** dan **GND**.
- Polaritas: pastikan tidak reverse; opsional fuse / PTC di jalur ALT.
- Capacitor: biasanya cukup yang sudah ada di `BAT` / VCC charger; tambah lokal di connector ALT bila kabel panjang.

### Opsi lebih sederhana

Jika ALT **hanya** dipakai saat USB dicabut (mis. dock pogo):

- Minimal: **satu Schottky di jalur ALT** saja ke `USB+`.
- Tetap lebih aman: dioda di **kedua** sumber (USB dan ALT).

Catatan: Schottky `NBD1` di board (**USB+ → VDDH**) adalah power-path sistem, **bukan** OR antar sumber charge. OR sumber ditambah **sebelum** net `USB+`.

## Syarat listrik

- Tegangan ALT: **~4,5–5,5 V** (target 5 V). Jangan 3,7 V sel langsung ke `USB+`.
- Arus charge tetap dari `PROG` IC, bukan dari ukuran kabel ALT.
- Common ground wajib.
- Saat `USB+` high, sistem disuplai dari sumber charge lewat `NBD1`; beban besar bisa membuat baterai ikut menyumbang jika desain power-path/limit charger tidak mencukupi (perilaku known SuperMini / reverse-eng notes).

## Implementasi di PCB Palm (usulan)

1. Breakout pad / connector **ALT_5V** dan **GND** di carrier / extended board.
2. D1 dari USB-C VBUS modul → net internal `USB+_OR` (atau tap pad VBUS modul jika di-mod).
3. D2 dari ALT_5V → net yang sama.
4. Net hasil OR diikat ke pin/`USB+` yang masuk charger modul (titik yang sama dengan VBUS USB-C setelah connector).

Untuk board yang memakai modul SuperMini sebagai daughter:

- Ideal: OR di **carrier**, lalu satu net 5 V masuk ke pad VBUS modul (jika diekspos), **atau**
- Mod modul: potong jejak VBUS connector → OR eksternal → sambung lagi ke net `USB+` charger.

## Checklist verifikasi

- [ ] ALT 5 V saja → LED CHRG aktif, `BAT` naik / charge current terukur
- [ ] USB saja → charge normal
- [ ] ALT on + USB host terhubung → tidak ada arus balik signifikan ke host
- [ ] ALT dicabut → board tetap jalan dari baterai (`VDDH` ≈ VBAT via FET)
- [ ] Tidak ada short `BAT` langsung ke sumber 5 V

## Referensi

- Skema SuperMini: `Datasheet/Supermini_Promicro_NoLogo/schematic.png`
- KiCad: `Datasheet/Supermini_Promicro_NoLogo/promicro.kicad_sch`
- Reverse engineering notes di folder datasheet yang sama (power path / VDDH vs charge)

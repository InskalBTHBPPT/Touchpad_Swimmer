# Timing — PalmLog FW 3.1.1

## Dua jam yang dipakai

| Jam | Sumber | Dipakai untuk |
|---|---|---|
| Wall-clock ms | HP → `SET_TIME` (`0x11`) unix_ms u64 | Anchor MCU + `start_unix_ms` di header file |
| Relatif ms | `millis()` MCU sejak Start | Field **`t_rel_ms`** tiap rekaman |

Board **tidak** menulis jam absolut di setiap baris. Absolut rekonstruksi:

```text
unix_ms ≈ start_unix_ms + t_rel_ms
```

(hanya valid jika `start_unix_ms ≠ 0` dan Sync waktu berhasil sebelum Start).

## Anchor setelah SET_TIME

1. HP mengirim wall-clock lokal sebagai epoch ms dengan offset UTC = 0 (lihat companion Android).
2. Board menyimpan:
   - `t_anchor_unix_ms` = nilai yang disetel
   - `t_anchor_millis` = `millis()` saat set
3. `nowUnixMs()` ≈ `t_anchor_unix_ms + (millis() − t_anchor_millis)`.
4. Saat **Start measure**, header file mendapat `start_unix_ms = nowUnixMs()`; `sampleEpochMs = millis()`.

## Sampling 100 Hz

- Timer period **10 ms** (`SAMPLE_PERIOD_MS`).
- Tiap tick: `t_rel_ms = millis() − sampleEpochMs` (bukan `index × 10`).
- Jitter normal MCU: Δt antar baris sering **9 atau 10 ms** (bukan bug).
- Lonjakan Δt ≈ **20 ms** (atau kelipatan): biasanya **drop ring** (beban SPI/BLE), bukan sector erase (di 3.1.1 erase sudah dipisah/bypass).
- Lonjakan Δt ≈ **60 ms** tiap ~4 KB: pola FW lama (erase di jalur sampling) — seharusnya **hilang** setelah FORMAT + timer ring.

## Serial STOP

```text
prod=P   # sampel di-capture timer
records=R  # tertulis flash (= panjang body/26)
drop=D   # P − yang sempat masuk ring (overrun)
```

Ideal perekaman lapangan: `drop=0`, `R ≈ P`.

## Stream

`0xB2` membawa `seq` + SampleRec lengkap (termasuk `t_rel_ms`). Stream **tidak** menggantikan flash; justru menambah beban. Untuk uji sensor saja.

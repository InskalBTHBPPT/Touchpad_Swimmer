# Protokol BLE — PalmLog v3.1.1

Advertising: **`PalmLog20`** · Service: **Nordic UART Service (NUS)**

| UUID | Peran |
|---|---|
| `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` | Service |
| `6E400002-…` | RX (HP → board, write) |
| `6E400003-…` | TX (board → HP, notify) |

Layout berkas: rekaman **26 B** = `t_rel_ms` u32 + 11×int16. Header PLG1 **version 4**.

**FW v3.1.1:** sampling `SoftwareTimer` 10 ms + ring; tulis flash di `loop()`. Setelah **FORMAT**, sector erase di-bypass saat append (`erasedUntil = FLASH_SIZE`).

Timing ms (anchor + `start_unix_ms`): **`TIMING.md`**.

---

## Fase A — status

| Arah | Opcode | Payload |
|---|---|---|
| HP → board | `0x10` GET_STATUS | — (1 B) |
| board → HP | `0x90` ACK_STATUS | **16 B** |

### ACK_STATUS (16 B)

| Off | Field |
|---|---|
| 0 | `0x90` |
| 1 | measure u8 (0/1) |
| 2 | rtc_ok u8 |
| 3…6 | unix_time u32 LE (**detik**, 0 jika rtc_ok=0) |
| 7…10 | next_free u32 LE |
| 11 | file_count u8 (0…48) |
| 12 | usb u8 |
| 13 | pwr_save u8 |
| 14…15 | vbat_mV u16 LE |

---

## Fase B — sync waktu (unix **ms**)

| Arah | Opcode | Payload |
|---|---|---|
| HP → board | `0x11` SET_TIME | `unix_ms` **u64 LE** (total **9** B) |
| board → HP | `0x91` ACK_SET_TIME | `result` u8 + `unix_ms` u64 LE (**10** B) |

`result`: `0`=OK, `1`=no RTC, `2`=bad range.

---

## Fase C — LIST + download `.bin`

| Arah | Opcode | Ukuran | Keterangan |
|---|---|---|---|
| HP → board | `0x20` LIST | 1 | Mulai enumerasi |
| board → HP | `0xA0` LIST_BEGIN | 2 | total_files |
| board → HP | `0xA1` LIST_ITEM | 26 | name[12], flags, n_records, byte_size, start_addr |
| board → HP | `0xA2` LIST_END | 2 | sent_count |
| HP → board | `0x21` GET_FILE | 19 | name[12] + offset u32 + max_chunk u16 |
| board → HP | `0xB1` CHUNK | ≥12 | result, offset, file_size, len, data |

`flags` LIST_ITEM: `1`=CLOSED/OK, `2`=OPEN (sedang measure).  
CHUNK `result`: `0`=OK, `1`=not found, `2`=busy OPEN, `3`=bad offset.  
`max_chunk` praktis ≤ **100…180** (app sering memakai 100 untuk stabilitas).

### Header file PLG1 (version 4)

| Off | Field | Keterangan |
|---|---|---|
| 0 | magic `PLG1` | 4 B |
| 4 | version u16 LE | **4** |
| 6 | period_ms u16 LE | 10 (jadwal nominal) |
| 8 | channels u8 | **11** |
| 9 | record_size u8 | **26** |
| 10 | start_name[12] | `YYMMDDHHMMSS` |
| 22 | **start_unix_ms** u64 LE | absolut ms saat Start |
| 30 | reserved[2] | 0 |
| 32…255 | pad | 0 |
| 256… | records **26 B** | lihat bawah |

### Layout rekaman (26 B, little-endian)

| Off | Field | Tipe | Makna |
|---|---|---|---|
| 0 | **t_rel_ms** | u32 | `millis() − millis_saat_Start` |
| 4 | d1, d2 | int16 | general −1000…1000 (dummy) |
| 8 | d3…d5 | int16 | accel **mg** −8000…8000 |
| 14 | d6…d8 | int16 | gyro **0,1 °/s** −20000…20000 |
| 20 | d9…d11 | int16 | mag **µT** −4900…4900 |

Verifikasi timing dari file:

- Nominal: `t_nom = index × period_ms`
- Terukur: `Δt = t_rel[i] − t_rel[i−1]` (sering 9 atau 10)
- Absolut: `unix_ms ≈ start_unix_ms + t_rel_ms`

Throughput flash: 100 Hz × 26 B = **2600 B/s**.

---

## Fase D — delete / format

| Arah | Opcode | Payload |
|---|---|---|
| HP → board | `0x23` DELETE | name[12] ASCII (tanpa `.bin`) |
| board → HP | `0xA3` | result: 0=OK, 1=not found, 2=OPEN/measure |
| HP → board | `0x24` FORMAT | wajib byte1 = **`0xA5`** |
| board → HP | `0xA4` | result: 0=OK, 1=stop measure dulu, 2=ditolak |

FORMAT = chip erase 4 MB (bisa 10–40+ s). Setelah sukses: direktori kosong, `erasedUntil = FLASH_SIZE`.

FS version **4** — boot dari image lama (version ≠ 4) menginisialisasi ulang direktori.

---

## Stream

| Arah | Opcode | Payload |
|---|---|---|
| HP → board | `0x30` STREAM | `enable` u8 (`1`=start, `0`=stop) |
| board → HP | `0xB0` | `result` u8: `0`=mulai, `1`=measure mati, `2`=stop |
| board → HP | `0xB2` | `seq` u16 LE + **SampleRec 26 B** (total **29** B) |

Syarat: measure ON + peer connected. Satu kali tulis NUS; jika TX penuh sampel stream dibuang (flash tetap prioritas di `sampleTick`, tapi beban stream bisa menyebabkan **ring drop**).

**Kebijakan produk:** stream untuk uji sensor saja; perekaman lapangan tanpa stream.

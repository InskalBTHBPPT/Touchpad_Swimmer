# PalmLog Android Companion — **1.0.0**

Aplikasi pendamping (**Kotlin + Jetpack Compose**) untuk board logger yang meng-advertise nama berawalan **`PalmLog`** (`PalmLog1`, `PalmLog20`, dan seterusnya). Format berkas **PLG1 v4**.

Komunikasi: **BLE Nordic UART Service (NUS)**. Scan tidak memakai filter nama hardware; aplikasi menerima perangkat yang namanya diawali `PalmLog`.

| Item | Nilai |
|---|---|
| `versionName` | **1.0.0** |
| `versionCode` | **1** |
| `applicationId` | `com.aistudio.palmlog` |
| Asal kode | `NRF52840/AndroidApp/V2.1.0` |
| Target FW | `PlatformIO/Log_Session_Bin` **1.0.0** (`PalmLog1`, PLG1 v4, rekaman 26 B, stream 29 B) |
| Min SDK | 31 |

Riwayat ada di `CHANGELOG.md`. `applicationId` berbeda dari aplikasi PalmLog20 lama, jadi keduanya bisa terpasang berdampingan.

---

## Daftar isi

1. [Perilaku yang dibawa dari V2.1.0](#perilaku-yang-dibawa-dari-v210)
2. [Fitur per tab](#fitur-per-tab)
3. [Format PLG1 v4 & kanal](#format-plg1-v4--kanal)
4. [Stream — kebijakan pemakaian](#stream--kebijakan-pemakaian)
5. [Protokol BLE (ringkas)](#protokol-ble-ringkas)
6. [Penyimpanan lokal](#penyimpanan-lokal)
7. [Build & install](#build--install)
8. [Struktur kode](#struktur-kode)
9. [FAQ multi-board](#faq-multi-board)

---

## Perilaku yang dibawa dari V2.1.0

Perubahan rilis **1.0.0** (scan awalan `PalmLog`) ada di `CHANGELOG.md`. Tabel ini hanya menjelaskan perilaku yang sudah ada di sumber kodenya.

| Area | V2.0.0 | Sumber V2.1.0 |
|---|---|---|
| Plot berkas PLG1 v4 (11 kanal, fisik, 4 grup) | ya | sama |
| Estimasi sisa flash /26 B | ya | sama |
| Stream `0xB2` | masih parser **19 B** (lama) | **29 B** = seq + SampleRec 26 B |
| UI Stream | d1…d8 mentah | **4 grup** Umum/Accel/Gyro/Mag, Y fisik |
| Peringatan Stream | — | banner: **hanya untuk uji**, jangan saat rekam lapangan |

---

## Fitur per tab

### Status

- Scan / auto-connect (1 board) atau Device Picker (multi-board)
- MTU 247, NUS notify
- `GET_STATUS` (`0x10` / `0x90` 16 B): measure, RTC, next_free, file_count, USB, pwr_save, vbat
- `SET_TIME` (`0x11` / `0x91`): sync wall-clock ms
- Putuskan / Ganti Board

### File

- `LIST` / unduh chunk `GET_FILE` (max_chunk praktis 100 B)
- Sync batch berkas CLOSED yang belum ada lokal
- Storage per MAC: `…/Download/PalmLog/<MAC>/`
- Hapus lokal / hapus board (`0x23`) / FORMAT (`0x24`+`0xA5`)
- **Plot:** grup Umum · Accel · Gyro · Mag; X = `t_rel_ms`; Y = nilai fisik; statistik min/max/avg
- Hanya berkas **PLG1 v4** (26 B, 11 kanal); berkas lama ditolak dengan pesan jelas

### Stream

- Start/Stop lewat `0x30` (hanya jika measure ON di board)
- Overlay live per grup kanal, skala fisik
- Banner peringatan (lihat bawah)
- Metadata baris: `seq`, `t_rel`, jumlah buffer

### Panduan

- Ringkasan operasi + catatan Stream

---

## Format PLG1 v4 & kanal

Header 256 B + rekaman:

```text
t_rel_ms u32 LE | d1..d11 int16 LE   (= 26 B)
```

| Grup UI | Kanal | Fisik di plot/stream |
|---|---|---|
| Umum | d1, d2 | mentah |
| Accel | d3…d5 | mg → **g** (/1000) |
| Gyro | d6…d8 | 0,1 °/s → **°/s** (/10) |
| Mag | d9…d11 | **µT** |

Absolut waktu (jika Sync OK): `unix_ms ≈ start_unix_ms + t_rel_ms`.

Spek board: `ProMicro/.../Log_Session_Bin_v3.1.1/GoogleAIStudio/PROTOCOL.md`.

---

## Stream — kebijakan pemakaian

Board dirancang **standalone**: Start/Stop measure dari **tombol**, data ke **flash**. Sinyal BLE di lapangan sering hilang — itu normal.

Stream BLE memakai CPU/loop yang sama dengan drain flash. Uji nyata: measure + stream → `drop>0` dan gap `t_rel` ~19–20 ms; tanpa stream → `drop=0`.

**Gunakan Stream hanya untuk cek sensor / uji lab.**  
**Jangan Stream saat perekaman data sebenarnya.**

Teks di UI (ringkas):

> Peringatan: Stream hanya untuk uji sensor. Jangan dipakai saat perekaman data sebenarnya — stream memperlambat tulis ke flash dan bisa membuat sampel hilang (drop).

Mode hipotetis “stream-only, simpan di HP, tanpa flash” **tidak** diimplementasikan; tidak cocok untuk lingkungan tanpa jaminan BLE.

---

## Protokol BLE (ringkas)

| Opcode | Arah | Keterangan |
| :---: | :---: | :--- |
| `0x10` / `0x90` | ↔ | Status 16 B |
| `0x11` / `0x91` | ↔ | Set time ms |
| `0x20` / `0xA0`–`0xA2` | ↔ | LIST |
| `0x21` / `0xB1` | ↔ | GET_FILE / CHUNK |
| `0x23` / `0xA3` | ↔ | DELETE |
| `0x24`+`0xA5` / `0xA4` | ↔ | FORMAT |
| `0x30` / `0xB0` / `0xB2` | ↔ | STREAM; sampel **29 B** |

NUS UUID standar Nordic (lihat kode `BleConstants.kt`).

---

## Penyimpanan lokal

```text
/sdcard/Android/data/com.aistudio.palmlog/files/Download/PalmLog/<MAC-dengan-strip>/
```

Riwayat board (MAC dikenal) di SharedPreferences via `BoardHistoryStore`.

---

## Build & install

```text
cd Palm_Pressure_Motion/Android_App
gradlew.bat assembleDebug
```

APK:

```text
app/build/outputs/apk/debug/app-debug.apk
```

```text
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

Catatan: `applicationId` `com.aistudio.palmlog` tidak menimpa aplikasi PalmLog20 (`com.aistudio.palmlog20.v210`).

Unit test: `gradlew.bat testDebugUnitTest`.

---

## Struktur kode

| Path | Peran |
|---|---|
| `ble/BleConstants.kt` | Opcode, ukuran paket, PLG1 v4 constants |
| `ble/PalmLogBleManager.kt` | GATT, parse notify, stream 29 B |
| `ble/StatusParser.kt` | Status, LIST, CHUNK, **parsePlgFile v4** |
| `model/PalmLogModels.kt` | Status, PlgRecord, PlotSensorGroup, StreamSample |
| `ui/PalmLogViewModel.kt` | State & perintah |
| `ui/components/FileTabContent.kt` | Daftar / sync / sisa flash |
| `ui/components/MultiChannelPlotDialog.kt` | Plot berkas 4 grup |
| `ui/components/StreamTabContent.kt` | Stream live + peringatan |
| `storage/BoardStorage.kt` | Path per MAC, hitung rekaman /26 |

---

## FAQ multi-board

**Koneksi simultan ke 2 board?** Tidak. Satu GATT NUS; ganti board lewat picker.

**1 board di sekitar:** auto-connect setelah scan stabil ~2 s.  
**>1 board:** dialog pilih MAC + RSSI.

---

## Tombol & LED board (referensi)

| Aksi | Tombol board |
|---|---|
| Start/Stop measure | Hold 3…10 s, lepas |
| Power OFF/ON | Hold ≥10 s (baterai) |

LED: idle 3×/10 s · measure 2×/5 s.

---

## Lisensi / catatan

Kode companion untuk proyek laboratorium PalmLog. Sensor di FW masih dummy random hingga hardware sensor diintegrasikan; layout kanal sudah final untuk v4.

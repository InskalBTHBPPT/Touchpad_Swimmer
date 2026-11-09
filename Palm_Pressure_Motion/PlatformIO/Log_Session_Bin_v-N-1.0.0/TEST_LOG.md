# Test log — Log_Session_Bin_v-N-1.0.0

Versi firmware yang diuji: **v-N-1.0.0** (`PalmLog1`)

## 2026-11-09 — COM12, flash + RTC (tanpa HP)

Compile dan upload `pio run -t upload` berhasil. DFU lewat COM13, firmware aktif kembali di COM12.

| | |
|---|---|
| RAM | 19392 / 248832 (7,8%) |
| Flash program | 162792 / 815104 (20,0%) |
| Upload | SUCCESS |
| BLE/HP | tidak diuji |

### Boot

Tidak ada `ERR flash bukan W25Q128 (EF 40 18)`. JEDEC lulus.  
Ada `WARN RTC tahun < 2020` — wajar sebelum `SET`.

```text
Log_Session_Bin v-N-1.0.0  PalmLog1  PLG1 v4  W25Q128+RV3032  timer+ring + stream
board=ON  ble=PalmLog1/adv  usb=Y  ...  rtc=OK  files=0  next_free=0x1000
```

### Flash

| Cek | Hasil |
|---|---|
| JEDEC W25Q128 | OK (tidak ada error boot) |
| FS PLG1 | `next_free=0x1000`, `files=0` |
| `LIST` | `(kosong)` |
| `FORMAT` chip erase 16 MB | tidak dijalankan di sesi ini |

### RTC

```text
>>> NOW
RTC 2000-01-01 00:42:13.000  anchor=N
>>> SET 2026-11-09 11:05:37
OK 2026-11-09 11:05:37.000  anchor=Y
>>> NOW
RTC 2026-11-09 11:05:38.660  anchor=Y
```

Hasil: lulus. `SET` menempel, `NOW` naik ~1,7 s dengan anchor aktif. `STATUS` tetap `rtc=OK`, advertising `PalmLog1/adv`.

Firmware yang tertinggal di board adalah image logger ini.

# PalmLog Laptop **1.0.0**

Companion desktop (**PySide6** + **Bleak** + **pyqtgraph**) di
`Palm_Pressure_Motion/PythonFile/Desktop_App` (clone dari `NRF52840/PythonFile/V1.0.0`).

Target firmware asal: `Log_Session_Bin` **3.1.1** / advertising `PalmLog20`.
Board Palm baru (`PalmLog1`, flash 16 MB) belum diprofil di app ini.

| Item | Nilai |
|---|---|
| Versi app | **1.0.0** |
| Target FW | **3.1.1** |
| Format berkas | **PLG1 v4** — 11 kanal, **26 B**/rekaman (`t_rel_ms` + d1…d11) |
| Stream | `0xB2` **29 B** (seq + SampleRec) |
| Advertising | `PalmLog20` |

Arsip app lama (8 kanal / 16 B): `../v0.1.0/`.

---

## Fitur

- **Board:** scan, connect, status 16 B, sync waktu ms, sisa kapasitas (÷26 B)
- **Berkas:** LIST, unduh chunk (max 100 B), hapus, format flash, simpan per MAC di `data/<MAC>/`
- **Stream:** live 11 kanal fisik + **peringatan uji-only** (jangan saat rekam lapangan)
- **Analisa:** buka `.bin` v4, plot X=`t_rel`, Y fisik, statistik, ekspor CSV
- **tools/check_trel.py:** unduh + histogram Δt `t_rel_ms`

---

## Kanal (fisik)

| Kanal | Makna | Tersimpan | Ditampilkan |
|---|---|---|---|
| d1, d2 | general | int16 | mentah |
| d3…d5 | accel | mg | **g** (/1000) |
| d6…d8 | gyro | 0,1 °/s | **°/s** (/10) |
| d9…d11 | mag | µT | **µT** |

---

## Menjalankan

```text
cd Palm_Pressure_Motion\PythonFile\Desktop_App
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Tes:

```text
python -m unittest discover -s tests -v
```

Cek timing satu berkas:

```text
python tools\check_trel.py 261007212354 --download
# atau lokal:
python tools\check_trel.py --file data\check\nama.bin
```

Putuskan koneksi BLE dari HP sebelum unduh dari laptop.

---

## Stream — kebijakan

Sama Android V2.1.0: stream membebani loop FW → `drop` / gap `t_rel`.  
Gunakan hanya untuk **uji sensor**. Perekaman lapangan: measure tombol board, **stream OFF**.

---

## Struktur

```text
Desktop_App/
  main.py
  requirements.txt
  palmlog/
    protocol.py   # opcode, framer, stream 29 B, RECORD_SIZE=26
    plg.py        # parser PLG1 v4
    client.py     # BLE Qt service
    storage.py
    ui/main_window.py
  tools/check_trel.py
  tests/
  data/           # unduhan lokal (di-.gitignore)
```

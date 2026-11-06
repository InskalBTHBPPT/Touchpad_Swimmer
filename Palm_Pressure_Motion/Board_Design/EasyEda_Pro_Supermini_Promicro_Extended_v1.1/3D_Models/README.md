# Model 3D (STEP) — U3 / U4

Sumber: [KiCad kicad-packages3D](https://github.com/KiCad/kicad-packages3D) (`Package_LGA.3dshapes`).  
Ini model **paket generik** (ukuran benar), bukan branding resmi ST.

| File | Untuk | Paket |
|---|---|---|
| `LIS3MDLTR_LGA-12_2x2mm_P0.5mm.step` | **U3** LIS3MDLTR | LGA-12, **2×2 mm**, pitch 0.5 |
| `LSM6DSOXTR_LGA-14_3x2.5mm_P0.5mm.step` | **U4** LSM6DSOXTR | LGA-14, **3×2.5 mm** (= 2.5×3), pitch 0.5 |
| `LSM6DSOXTR_LGA-14_Bosch_3x2.5mm_P0.5mm.step` | alternatif U4 | sama, varian Bosch layout |

## Bind di EasyEDA Pro

1. **File → New → 3D Model** → unit **mm** → pilih file `.step` → OK.  
2. PCB: **Tools → 3D Model Manager** → pilih U3 / U4 → bind model → **Auto** → sesuaikan rotasi (LSM6 sering perlu putar 90° karena 3×2.5 vs silk 2.5×3).  
3. Preview 3D lagi — warning “3D model was not bound” hilang.

## Unduhan resmi (pakai login)

- ST CAD: [LSM6DSOX](https://www.st.com/en/mems-and-sensors/lsm6dsox.html) · [LIS3MDL](https://www.st.com/en/mems-and-sensors/lis3mdl.html) → Ultra Librarian / SamacSys  
- [Component Search Engine](https://componentsearchengine.com/) (gratis, perlu akun)  
- [Ultra Librarian LSM6DSOXTR](https://app.ultralibrarian.com/details/24dffb05-0063-11ea-a124-0ad2c9526b44/STMicroelectronics/LSM6DSOXTR)  
- Digi-Key CAD models: [LIS3MDLTR](https://www.digikey.com/en/models/4309733)

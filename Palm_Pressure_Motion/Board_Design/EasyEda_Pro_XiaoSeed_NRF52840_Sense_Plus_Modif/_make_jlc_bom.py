# -*- coding: utf-8 -*-
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

src = Path(
    r"D:\NonPengujian\NRF52840\Referensi\devboard\seeed-xiao-nrf52840-sense"
    r"\Sense Plus\BOM_Seeed Studio XIAO nRF52840 v1.1_Seeed Studio XIAO nRF52840 v1.1_2026-11-11--.xlsx"
)
out_dir = Path(
    r"D:\Pengujian\Swimmer_Monitoring\Palm_Pressure_Motion\Board_Design"
    r"\EasyEda_Pro_XiaoSeed_NRF52840_Sense_Plus_Modif"
)
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / "BOM_XIAO_nRF52840_Sense_Plus_JLCPCB.xlsx"

# Curated JLCPCB matches: package + voltage first
MAP = {
    ("SEEDSTUDIO-SCH-MODLIST", ""): dict(
        jlc="", mpn="", pkg="", v="", lib="",
        note="Mechanical/doc only — skip PCBA", conf="N/A", ok="skip",
    ),
    ("ANTENNA-AN3216", "ANT"): dict(
        jlc="search AN3216", mpn="AN3216 / chip ant 3.2x1.6x1.04",
        pkg="ANT-SMD 3P 3.2x1.6x1.04", v="RF", lib="Extended/rare",
        note="PCB FP: ANT-SMD3P-3.2X1.6X1.04MM. Rare on JLC — often hand place",
        conf="low", ok="manual?",
    ),
    ("TEST-POINT'4080'", "TP-80"): dict(
        jlc="", mpn="", pkg="TP", v="", lib="",
        note="Test point — copper pad only", conf="N/A", ok="skip",
    ),
    ("100nF", "C0201"): dict(
        jlc="C307380", mpn="CL03A104KO3NNNC", pkg="0201", v="16V X5R",
        lib="Extended", note="Alt C467016 (YAGEO 16V). OK for 3V3 rails",
        conf="high", ok="yes",
    ),
    ("10pF", "C0201"): dict(
        jlc="C5142552", mpn="TCC0201COG100J500ZT", pkg="0201", v="50V C0G",
        lib="Extended", note="XL crystal load; C0G/NP0 required",
        conf="high", ok="yes",
    ),
    ("2.2uF", "C0201"): dict(
        jlc="C335106", mpn="GRM033R61A225KE47D", pkg="0201", v="10V X5R",
        lib="Extended",
        note="Use >=10V (VBUS/VIN). Alt C386031. Derating high on 0201",
        conf="high", ok="yes",
    ),
    ("1nF", "C0402"): dict(
        jlc="C338101", mpn="CGA2B2C0G1H102JT0Y0F", pkg="0402", v="50V C0G",
        lib="Extended", note="Keep C0G", conf="high", ok="yes",
    ),
    ("820pF", "C0201"): dict(
        jlc="C3886377", mpn="GRM0335C1H821GE01D", pkg="0201", v="50V C0G",
        lib="Extended", note="DEC5; C0G preferred", conf="med", ok="yes",
    ),
    ("15pF", "C0201"): dict(
        jlc="C277480", mpn="CC0201JRNPO9BN150", pkg="0201", v="50V NP0",
        lib="Extended", note="32MHz load caps XC1/XC2", conf="high", ok="yes",
    ),
    ("100pF", "C0201"): dict(
        jlc="C62550", mpn="0201CG101J500NT", pkg="0201", v="50V C0G",
        lib="Extended", note="DEC3", conf="high", ok="yes",
    ),
    ("0.8pF", "C0201"): dict(
        jlc="C285040", mpn="0201CG0R8B500NT", pkg="0201", v="50V C0G",
        lib="Extended", note="RF match; tolerance critical", conf="high", ok="yes",
    ),
    ("0.5pF", "C0201"): dict(
        jlc="C285087", mpn="0201CG0R5B500NT", pkg="0201", v="50V C0G",
        lib="Extended", note="RF match; tolerance critical", conf="high", ok="yes",
    ),
    ("4.7nH", "L0201"): dict(
        jlc="C271759", mpn="HKQ0603S4N7C-T", pkg="0201", v="RF L",
        lib="Extended",
        note="RF series L (Murata 0201). Do NOT use 0603 HF L here",
        conf="high", ok="yes",
    ),
    ("DNP", "C0201"): dict(
        jlc="", mpn="", pkg="0201", v="", lib="",
        note="C40 DEC2 — Do Not Place", conf="N/A", ok="DNP",
    ),
    ("RED", "LED-0402"): dict(
        jlc="C264407", mpn="16-213/R6C-AQ2R2B/3T", pkg="0402", v="~2.0V LED",
        lib="Extended", note="CHG LED red 0402", conf="med", ok="yes",
    ),
    ("DIODE'0603'", "SOD-523"): dict(
        jlc="C81572", mpn="BAT54XV2T1G", pkg="SOD-523", v="30V Schottky",
        lib="Extended", note="Power-path OR. Alt C8524 RB751S-40",
        conf="high", ok="yes",
    ),
    ("GND", "TP-80"): dict(
        jlc="", mpn="", pkg="TP", v="", lib="",
        note="Test point pad only", conf="N/A", ok="skip",
    ),
    ("BUTTON-4P", "SW4"): dict(
        jlc="search TS-1187A / 2.6x1.6", mpn="tact 2.6x1.6x0.53",
        pkg="SW4 2.6x1.6x0.53", v="", lib="Extended",
        note="PCB FP exact: SW4-SMD-2.8-2.6X1.6X0.53MM",
        conf="low", ok="verify",
    ),
    ("10uH", "L0603"): dict(
        jlc="C778459", mpn="CMLM1608C100MIT", pkg="0603", v="10uH 100mA",
        lib="Extended",
        note="REG1 DCDC. JANGAN C1035 (hanya 3mA). Nordic min ~50-80mA",
        conf="med", ok="yes*",
    ),
    ("MSM261D3526H1CPM", "MIC"): dict(
        jlc="", mpn="MSM261D3526H1CPM", pkg="MIC6P 3.5x2.65x0.94",
        v="1.8-3.6V", lib="Rare/none",
        note="PCB FP: MIC6P-3.5X2.65X0.94MM. PDM mic — usually NOT on JLC",
        conf="low", ok="manual",
    ),
    ("PMOS_1.00.60.35MM", "PMOS"): dict(
        jlc="C48392752", mpn="SL3139KL", pkg="DFN1006-3 1.0x0.6x0.35",
        v="20V P-ch ~980mA", lib="Extended",
        note="Ganti C669004 (SI3139KL3-TP OOS). Alt: C22365398 MS3139KDFN / C54740791 LW3139BDA. Cek pin S-G-D",
        conf="med", ok="verify",
    ),
    ("5.1k", "R0201"): dict(
        jlc="C270344", mpn="0201WMF5101TEE", pkg="0201", v="25V 50mW",
        lib="Extended", note="USB CC 5.1k", conf="high", ok="yes",
    ),
    ("2.2k", "R0201"): dict(
        jlc="C473508", mpn="0201WMF2201TEE", pkg="0201", v="25V 50mW",
        lib="Extended", note="", conf="high", ok="yes",
    ),
    ("10k", "R0201"): dict(
        jlc="C473048", mpn="0201WMF1002TEE", pkg="0201", v="25V 50mW",
        lib="Extended",
        note="10k R4/R13/R14/R15/R20. JANGAN C270353 (=24k 0201WMF2402TEE)",
        conf="high", ok="yes",
    ),
    ("DNP", "R0201"): dict(
        jlc="", mpn="", pkg="0201", v="", lib="",
        note="R8 DNP", conf="N/A", ok="DNP",
    ),
    ("100k", "R0201"): dict(
        jlc="C270364", mpn="0201WMF1003TEE", pkg="0201", v="25V 50mW",
        lib="Extended", note="", conf="high", ok="yes",
    ),
    ("33R", "R0201"): dict(
        jlc="C320843", mpn="RC-01W33R0FT", pkg="0201", v="25V 50mW",
        lib="Extended", note="USB series R", conf="high", ok="yes",
    ),
    ("2.7k", "R0201"): dict(
        jlc="C423624", mpn="0201WMF2701TEE", pkg="0201", v="25V 50mW",
        lib="Extended",
        note="2.7k ISET/HICHG. JANGAN C270347 (=4.02k 0201WMF4021TEE)",
        conf="high", ok="yes",
    ),
    ("1M_1%", "R0201"): dict(
        jlc="C295786", mpn="RC0201FR-071ML", pkg="0201", v="25V 50mW",
        lib="Extended", note="1%", conf="high", ok="yes",
    ),
    ("499k_1%", "R0201"): dict(
        jlc="C295805", mpn="RC0201FR-07510KL", pkg="0201",
        v="25V 50mW", lib="Extended",
        note="BOM xlsx=499k, PCB PDF fab=510k_1% → pakai 510k C295805 (ref PCB 2026-11-06)",
        conf="high", ok="yes",
    ),
    ("510k_1%", "R0201"): dict(
        jlc="C295805", mpn="RC0201FR-07510KL", pkg="0201",
        v="25V 50mW", lib="Extended",
        note="Sesuai PCB PDF Sense Plus BOM page; BQ BAT divider",
        conf="high", ok="yes",
    ),
    ("RGB", "4P1010"): dict(
        jlc="search 1010 RGB", mpn="RGB 1.0x1.0 4P", pkg="1010", v="",
        lib="Extended",
        note="Common 1010 RGB on JLC; match pinout R/G/B/C",
        conf="low", ok="verify",
    ),
    ("TEST-POINT'4545'", "TP-D45"): dict(
        jlc="", mpn="", pkg="TP", v="", lib="",
        note="Pad only", conf="N/A", ok="skip",
    ),
    ("NRF52840_QF", "AQFN"): dict(
        jlc="C1851953", mpn="NRF52840-QIAA-R7",
        pkg="AQFN50P 7x7x0.85 HS-74N",
        v="1.7-5.5V", lib="Extended",
        note="PCB FP: AQFN50P700X700X85_HS-74N. Alt F-R7 C3606858",
        conf="high", ok="yes",
    ),
    ("BQ25100", "BQ25101"): dict(
        jlc="C206119", mpn="BQ25100AYFPT", pkg="DSBGA-6",
        v="IN 3.5-28V / 4.2Vchg", lib="Extended",
        note="PCB FP: BQ25101_DSBGA_6. Alt reel C2871910",
        conf="high", ok="yes",
    ),
    ("LSM6DS3TR-C", "LGA14"): dict(
        jlc="C967633", mpn="LSM6DS3TR-C", pkg="LGA14 2.5x3x0.86",
        v="1.71-3.6V", lib="Extended",
        note="PCB FP: LGA14-0.5-2.5X3X0.86MM",
        conf="high", ok="yes",
    ),
    ("XIAO-HALF-HOLE-23P", "MOUDLE"): dict(
        jlc="", mpn="", pkg="edge", v="", lib="",
        note="Board outline / castellated edge — not a bought part",
        conf="N/A", ok="skip",
    ),
    ("3.3V", "X2SON"): dict(
        jlc="C471048", mpn="TLV73333PDQNR", pkg="X2SON-4 1x1",
        v="VIN<=5.5V / OUT 3.3V", lib="Extended",
        note="Matches Seeed TLV733P. Confirm EN pin wiring",
        conf="high", ok="yes",
    ),
    ("DNP", "USON2X3"): dict(
        jlc="", mpn="W25Qxx (DNP)", pkg="USON-8 2x3", v="", lib="",
        note="U7 flash DNP on Sense Plus BOM", conf="N/A", ok="DNP",
    ),
    ("USB2.0-TYPE-C", "USB"): dict(
        jlc="search USB-C 16P", mpn="USB4105 / TYPE-C 16P SMT",
        pkg="USB-C 16P", v="VBUS 5V", lib="Extended",
        note="Search JLC USB Type-C 16P — match mid-mount footprint carefully",
        conf="low", ok="verify",
    ),
    ("32.768KHz", "X2-SMD"): dict(
        jlc="search 32.768 1610", mpn="32.768kHz 1.6x1.0x0.5 Cl~7-9pF",
        pkg="X2-SMD 1.6x1.0x0.5", v="", lib="Extended",
        note="PCB FP: X2-SMD-L1.6X1.0X0.5MM + C2/C7=10pF",
        conf="med", ok="verify",
    ),
    ("32MHz", "4P1612"): dict(
        jlc="search 32MHz 1612 Cl=8", mpn="32MHz 1612 Cl=8pF",
        pkg="4P1612", v="", lib="Extended",
        note="PCB FP: 4P1612; loads C32/C33=15pF — keep Cl pair consistent",
        conf="med", ok="verify",
    ),
}


def fp_key(fp):
    if not fp:
        return ""
    f2 = fp.split(":")[-1].upper()
    if "ANT-" in f2:
        return "ANT"
    if "TP-80" in f2:
        return "TP-80"
    if f2.endswith("C0201") or f2 == "C0201":
        return "C0201"
    if "C0402" in f2:
        return "C0402"
    if "L0201" in f2:
        return "L0201"
    if "LED-0402" in f2:
        return "LED-0402"
    if "SOD-523" in f2:
        return "SOD-523"
    if "SW4" in f2:
        return "SW4"
    if "L0603" in f2:
        return "L0603"
    if "MIC" in f2:
        return "MIC"
    if "PMOS" in f2:
        return "PMOS"
    if "R0201" in f2:
        return "R0201"
    if "4P1010" in f2:
        return "4P1010"
    if "TP-D45" in f2:
        return "TP-D45"
    if "AQFN" in f2:
        return "AQFN"
    if "BQ25101" in f2:
        return "BQ25101"
    if "LGA14" in f2:
        return "LGA14"
    if "MOUDLE" in f2 or "HALF-HOLE" in f2:
        return "MOUDLE"
    if "X2SON" in f2:
        return "X2SON"
    if "USON" in f2:
        return "USON2X3"
    if "USB" in f2:
        return "USB"
    if "X2-SMD" in f2 or "1.6X1.0" in f2:
        return "X2-SMD"
    if "4P1612" in f2 or "1612" in f2:
        return "4P1612"
    return f2[:12]


wb_src = openpyxl.load_workbook(src, data_only=True)
ws_src = wb_src.active
rows = list(ws_src.iter_rows(values_only=True))
header = list(rows[0])

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "BOM_JLCPCB"

new_header = header + [
    "JLCPCB Part #",
    "Suggested MPN",
    "JLC Package",
    "Voltage / rating",
    "JLC Library",
    "Footprint/Voltage OK?",
    "Confidence",
    "Assembly notes",
]
ws.append(new_header)

hdr_fill = PatternFill("solid", fgColor="1F4E79")
hdr_font = Font(color="FFFFFF", bold=True)
yes_fill = PatternFill("solid", fgColor="C6EFCE")
ver_fill = PatternFill("solid", fgColor="FFEB9C")
skip_fill = PatternFill("solid", fgColor="D9D9D9")
no_fill = PatternFill("solid", fgColor="FFC7CE")
thin = Border(
    left=Side(style="thin", color="B0B0B0"),
    right=Side(style="thin", color="B0B0B0"),
    top=Side(style="thin", color="B0B0B0"),
    bottom=Side(style="thin", color="B0B0B0"),
)

for cell in ws[1]:
    cell.fill = hdr_fill
    cell.font = hdr_font
    cell.alignment = Alignment(wrap_text=True, vertical="center")

for row in rows[1:]:
    if not row or row[0] in (None, ""):
        continue
    padded = list(row) + [None] * 10
    no_, qty, comment, desig, fp, val, mfrp, mfr, supp, supplier = padded[:10]
    val_s = (val or "").strip()
    desig_s = (desig or "").strip()
    fk = fp_key(fp or "")

    key = (val_s, fk)
    m = MAP.get(key)
    if m is None and val_s == "DNP":
        if desig_s.startswith("C"):
            m = MAP[("DNP", "C0201")]
        elif desig_s.startswith("R"):
            m = MAP[("DNP", "R0201")]
        elif desig_s.startswith("U"):
            m = MAP[("DNP", "USON2X3")]
        else:
            m = dict(
                jlc="", mpn="", pkg="", v="", lib="",
                note="DNP", conf="N/A", ok="DNP",
            )
    if m is None:
        for (v0, _f0), mm in MAP.items():
            if v0 == val_s:
                m = mm
                break
    if m is None:
        m = dict(
            jlc="", mpn="", pkg="", v="", lib="",
            note="Not mapped — search JLC manually",
            conf="low", ok="verify",
        )

    out_row = [
        no_, qty, comment, desig, fp, val, mfrp, mfr, supp, supplier,
        m.get("jlc", ""), m.get("mpn", ""), m.get("pkg", ""), m.get("v", ""),
        m.get("lib", ""), m.get("ok", ""), m.get("conf", ""), m.get("note", ""),
    ]
    ws.append(out_row)
    r_idx = ws.max_row
    ok = m.get("ok", "")
    if ok in ("yes", "yes*"):
        fill = yes_fill
    elif ok in ("verify", "manual", "manual?"):
        fill = ver_fill
    elif ok in ("DNP", "skip"):
        fill = skip_fill
    elif ok == "no":
        fill = no_fill
    else:
        fill = skip_fill
    for c in ws[r_idx]:
        c.border = thin
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for col in (16, 17):
        ws.cell(r_idx, col).fill = fill

ws2 = wb.create_sheet("NOTES_JLCPCB")
notes = [
    "BOM JLCPCB mapping — Seeed XIAO nRF52840 Sense Plus v1.1",
    "Prioritas: package/footprint match + voltage rating + ketersediaan library JLCPCB.",
    "",
    "Referensi footprint/layout:",
    "- PCB_Seeed Studio XIAO nRF52840 v1.1_2026-11-06.pdf (fab BOM + top/bottom + stackup 4-layer).",
    "- Jika conflict nilai: PCB PDF > BOM xlsx. Contoh: R17 PDF=510k_1%, xlsx=499k_1% → pakai 510k C295805.",
    "",
    "Footprint exact dari PCB PDF (penting JLCPCB):",
    "- ANT1: ANT-SMD3P-3.2X1.6X1.04MM",
    "- Passives: C0201 / R0201 (mayoritas); C10=C0402; L3=L0603; C38=L0201 4.7nH",
    "- D1: SOD-523 | CHG0: LED-0402 | RGB6: 4P1010",
    "- K1: SW4-SMD-2.8-2.6X1.6X0.53MM",
    "- MIC1: MIC6P-3.5X2.65X0.94MM | Q1: PMOS_1.0*0.6*0.35MM",
    "- U1: AQFN50P700X700X85_HS-74N | U2: BQ25101_DSBGA_6 | U3: LGA14-0.5-2.5X3X0.86MM",
    "- U6: X2SON-4 | U7: USON2X3_8 DNP | USB1: USB2.0-TYPE-C",
    "- X1: X2-SMD-L1.6X1.0X0.5MM | X2: 4P1612",
    "- Stackup 4L: L1 GTL / L2 GND / L3 POWER / L4 GBL; impedance 50/90/100ohm +/-10%",
    "",
    "Voltage guidance:",
    "- Rail 3V3 / DEC / sensor: MLCC >=6.3V (lebih aman 10-16V).",
    "- VBUS / VIN / charger input: MLCC >=10V (0201 2.2uF pakai 10V).",
    "- RF / crystal C: wajib C0G/NP0 50V.",
    "",
    "JANGAN pakai:",
    "- C1035 10uH Basic untuk L3 DCDC (hanya 3mA) -> pakai C778459 (~100mA) atau power inductor setara.",
    "- X5R untuk C RF 0.5/0.8pF.",
    "",
    "Part sering HARUS manual / verify footprint:",
    "- MIC1 MSM261D3526H1CPM, ANT1 AN3216, USB-C exact mid-mount, switch K1, crystals 1610/1612, RGB 1010 pinout.",
    "",
    "IC inti (ada di JLC Extended):",
    "- U1 NRF52840-QIAA-R7 = C1851953 (atau -F-R7 C3606858)",
    "- U2 BQ25100AYFPT = C206119",
    "- U3 LSM6DS3TR-C = C967633",
    "- U6 TLV73333PDQNR = C471048",
    "",
    "Kolom Footprint/Voltage OK?: yes = cocok JLC; verify = cek footprint/stok; manual = sulit SMT JLC; DNP/skip = tidak dipasang.",
    "Sumber: BOM xlsx 2026-11-11 + PCB PDF 2026-11-06.",
]
for i, line in enumerate(notes, 1):
    ws2.cell(i, 1, line)
    if i == 1:
        ws2.cell(i, 1).font = Font(bold=True, size=14)

widths = [5, 8, 28, 28, 36, 14, 14, 12, 12, 10, 14, 28, 14, 16, 12, 12, 10, 48]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.row_dimensions[1].height = 32
ws2.column_dimensions["A"].width = 110
ws.auto_filter.ref = f"A1:R{ws.max_row}"
ws.freeze_panes = "A2"

wb.save(out)
print("saved", out)
print("rows", ws.max_row - 1)

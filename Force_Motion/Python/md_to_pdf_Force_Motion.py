#!/usr/bin/env python3
"""
Konversi Markdown → HTML → PDF (paket ``markdown`` + ``xhtml2pdf``),
mengikuti pola ``Touchpad_Timer_Pressure/Python/md_to_pdf_xhtml2pdf.py``.

Default untuk manual Swimmer Force Motion Monitoring v1.0.0:

  UserManual_Force_Motion_v1.0.0.md  →  UserManual_Force_Motion_v1.0.0.pdf

Contoh:

  python md_to_pdf_Force_Motion.py
  python md_to_pdf_Force_Motion.py -i UserManual_Force_Motion_v1.0.0.md -o out.pdf
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import markdown
from xhtml2pdf import pisa


def _default_paths() -> tuple[pathlib.Path, pathlib.Path]:
    base = pathlib.Path(__file__).resolve().parent
    return (
        base / "UserManual_Force_Motion_v1.0.0.md",
        base / "UserManual_Force_Motion_v1.0.0.pdf",
    )


def md_to_pdf(md_path: pathlib.Path, pdf_path: pathlib.Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8"/>
<style>
@page {{ size: A4; margin: 18mm 16mm; }}
body {{
  font-family: Helvetica, Arial, sans-serif;
  font-size: 10pt;
  line-height: 1.38;
  color: #111;
}}
h1 {{ font-size: 17pt; margin-top: 0; color: #0f172a; border-bottom: 2px solid #1e3a5f; padding-bottom: 4px; }}
h2 {{ font-size: 12.5pt; margin-top: 14pt; border-bottom: 1px solid #999; padding-bottom: 2px; color: #1e3a5f; }}
h3 {{ font-size: 11pt; margin-top: 10pt; }}
code {{
  font-family: Consolas, "Courier New", monospace;
  font-size: 9pt;
  background: #f2f2f2;
  padding: 1px 4px;
}}
pre {{
  font-family: Consolas, "Courier New", monospace;
  font-size: 8.5pt;
  background: #f5f5f5;
  border: 1px solid #ddd;
  padding: 8px;
  white-space: pre-wrap;
  word-break: break-word;
}}
pre code {{ background: transparent; padding: 0; }}
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 9.5pt;
}}
th, td {{
  border: 1px solid #444;
  padding: 4px 6px;
  vertical-align: top;
}}
th {{ background: #eaeaea; }}
hr {{ border: none; border-top: 1px solid #ccc; margin: 12px 0; }}
blockquote {{
  margin: 8px 0;
  padding-left: 10px;
  border-left: 3px solid #bbb;
}}
ul, ol {{ margin: 6px 0; padding-left: 22px; }}
li {{ margin: 2px 0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with pdf_path.open("wb") as out:
        status = pisa.CreatePDF(
            src=html,
            dest=out,
            encoding="utf-8",
        )
    if status.err:
        print(f"PDF: ada error/peringatan dari mesin render (err={status.err}).", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    d_md, d_pdf = _default_paths()
    p = argparse.ArgumentParser(description="MD → PDF (xhtml2pdf) — manual Force Motion")
    p.add_argument("-i", "--input", type=pathlib.Path, default=d_md, help="File Markdown masukan")
    p.add_argument("-o", "--output", type=pathlib.Path, default=d_pdf, help="File PDF keluaran")
    args = p.parse_args()

    if not args.input.is_file():
        print(f"Tidak ditemukan: {args.input}", file=sys.stderr)
        sys.exit(1)

    md_to_pdf(args.input, args.output)
    print(f"OK: {args.output}")


if __name__ == "__main__":
    main()

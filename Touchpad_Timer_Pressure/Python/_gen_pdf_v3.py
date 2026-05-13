"""Skrip bantu: konversi UserManual_v3.md -> UserManual_v3.pdf"""
import pathlib, sys

md_path = pathlib.Path(__file__).parent / "UserManual_v3.md"
pdf_path = md_path.with_suffix(".pdf")

try:
    import markdown
    from xhtml2pdf import pisa
except ImportError as e:
    print("Missing library:", e)
    sys.exit(1)

md_text = md_path.read_text(encoding="utf-8")
html_body = markdown.markdown(
    md_text, extensions=["tables", "fenced_code", "nl2br"]
)

CSS = """
@page { margin: 20mm; }
body { font-family: Arial, sans-serif; font-size: 10pt; color: #222; }
h1 { font-size: 18pt; color: #003366; border-bottom: 2px solid #003366; padding-bottom: 4px; }
h2 { font-size: 14pt; color: #003366; border-bottom: 1px solid #cccccc;
     padding-bottom: 2px; margin-top: 18px; }
h3 { font-size: 11pt; color: #333; margin-top: 12px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9pt; }
th { background: #003366; color: white; padding: 5px 8px; text-align: left; }
td { border: 1px solid #ccc; padding: 4px 8px; }
tr:nth-child(even) td { background: #f4f7fa; }
pre { background: #f4f4f4; padding: 8px; font-size: 8pt;
      border-left: 3px solid #003366; }
code { font-family: Courier New, monospace; font-size: 8.5pt;
       background: #f0f0f0; padding: 1px 3px; }
blockquote { border-left: 3px solid #003366; margin-left: 0;
             padding-left: 12px; color: #555; font-style: italic; }
hr { border: none; border-top: 1px solid #ccc; margin: 12px 0; }
ul, ol { margin: 4px 0; padding-left: 20px; }
"""

HTML = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    "<style>" + CSS + "</style></head><body>"
    + html_body
    + "</body></html>"
)

with open(pdf_path, "wb") as f:
    result = pisa.CreatePDF(HTML, dest=f)

if result.err:
    print("xhtml2pdf errors:", result.err)
    sys.exit(1)

print("PDF berhasil:", pdf_path)

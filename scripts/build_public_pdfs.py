"""
Convert data/sample_docs/*.txt into PDFs under frontend/public/.

Each output has predictable pagination (~35 lines per page) so mock chunks
can reference stable page numbers. Uses PyMuPDF (already in requirements)
so no extra dependencies are needed.
"""
from pathlib import Path
import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "data" / "sample_docs"
OUT_DIR = ROOT / "frontend" / "public"

LINES_PER_PAGE = 35
FONT_SIZE = 10
MARGIN = 54  # 0.75"
PAGE_W, PAGE_H = fitz.paper_size("letter")

TXT_TO_OUT = {
    "GDPR_Sample.txt": "GDPR.pdf",
    "HIPAA_Sample.txt": "HIPAA.pdf",
    "SOC2_Sample.txt": "SOC2.pdf",
}


def txt_to_pdf(txt_path: Path, pdf_path: Path) -> None:
    lines = txt_path.read_text(encoding="utf-8").splitlines()

    doc = fitz.open()
    for start in range(0, len(lines), LINES_PER_PAGE):
        chunk = lines[start:start + LINES_PER_PAGE]
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        rect = fitz.Rect(MARGIN, MARGIN, PAGE_W - MARGIN, PAGE_H - MARGIN)
        page.insert_textbox(
            rect,
            "\n".join(chunk),
            fontsize=FONT_SIZE,
            fontname="helv",
            align=0,
        )

    doc.save(pdf_path, deflate=True)
    doc.close()
    print(f"  {pdf_path.name}: {(len(lines) + LINES_PER_PAGE - 1) // LINES_PER_PAGE} pages")


def dump_page_summary(pdf_path: Path) -> None:
    """Print first line of each page — helps map mock chunks to real page numbers."""
    doc = fitz.open(pdf_path)
    print(f"\n{pdf_path.name} table of pages:")
    for i, page in enumerate(doc, 1):
        text = page.get_text().strip().splitlines()
        first = next((ln for ln in text if ln.strip()), "(blank)")
        print(f"  p.{i}: {first[:80]}")
    doc.close()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing PDFs to {OUT_DIR}")
    for src_name, out_name in TXT_TO_OUT.items():
        src = SRC_DIR / src_name
        if not src.exists():
            print(f"  skip: {src} missing")
            continue
        out = OUT_DIR / out_name
        txt_to_pdf(src, out)
        dump_page_summary(out)


if __name__ == "__main__":
    main()

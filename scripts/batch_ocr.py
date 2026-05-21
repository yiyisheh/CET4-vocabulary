"""Batch OCR all scanned CET PDFs via Qwen — whole PDF per request."""
import re
import time
import concurrent.futures
from pathlib import Path
import fitz

from qwen_ocr import ocr_images, PROMPT_PAPER, PROMPT_ANS

ROOT = Path(__file__).parent.parent
CORPUS = ROOT / "corpus"
PAGES = ROOT / "_pages"
PAGES.mkdir(exist_ok=True)
(CORPUS / "papers").mkdir(parents=True, exist_ok=True)
(CORPUS / "listening").mkdir(parents=True, exist_ok=True)

DPI = 150
JPG_QUALITY = 80
EMPTY = re.compile(r"^\s*[（(]?\s*空字符串\s*[）)]?\s*$")


def render_pdf(pdf: Path) -> list[Path]:
    """Render each page to a grayscale JPEG (small payload for the API)."""
    cache = PAGES / pdf.stem
    cache.mkdir(exist_ok=True)
    doc = fitz.open(pdf)
    out = []
    for i in range(doc.page_count):
        p = cache / f"p_{i+1:02d}.jpg"
        if not p.exists():
            pix = doc[i].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pix.save(p, jpg_quality=JPG_QUALITY)
        out.append(p)
    doc.close()
    return out


def is_scanned(pdf: Path) -> bool:
    doc = fitz.open(pdf)
    total = sum(len(p.get_text()) for p in doc)
    doc.close()
    return total < 500


def ocr_one(pdf: Path, prompt: str, out_path: Path) -> None:
    if out_path.exists():
        print(f"  skip (exists): {out_path.name}")
        return
    pages = render_pdf(pdf)
    print(f"  -> {pdf.name} ({len(pages)}p) ...")
    t0 = time.time()
    txt = ocr_images(pages, prompt, max_tokens=16384)
    if EMPTY.match(txt.strip()):
        txt = ""
    out_path.write_text(txt)
    print(f"     {len(txt)} chars in {time.time()-t0:.0f}s -> {out_path.name}")


def main(workers: int = 4):
    pdfs = sorted(ROOT.glob("CET/cet4_*/cet4_*.pdf"))
    paper_pdfs = [p for p in pdfs if not p.stem.endswith("_ans") and is_scanned(p)]
    ans_pdfs = [p for p in pdfs if p.stem.endswith("_ans")]
    print(f"真题 to OCR: {len(paper_pdfs)}, ans to OCR: {len(ans_pdfs)}")

    tasks = []
    for p in paper_pdfs:
        tasks.append((p, PROMPT_PAPER, CORPUS / "papers" / f"{p.stem}.txt"))
    for p in ans_pdfs:
        tasks.append((p, PROMPT_ANS, CORPUS / "listening" / f"{p.stem}.txt"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda t: ocr_one(*t), tasks))


if __name__ == "__main__":
    main()

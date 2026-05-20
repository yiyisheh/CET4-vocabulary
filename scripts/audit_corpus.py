"""Audit OCR corpus: cross-check每份 PDF 页数 vs OCR 输出字符数, flag anomalies."""
from pathlib import Path
import fitz

ROOT = Path(__file__).parent.parent
CORPUS = ROOT / "corpus"


def page_count(pdf: Path) -> int:
    doc = fitz.open(pdf)
    n = doc.page_count
    doc.close()
    return n


def main():
    rows = []
    for pdf in sorted(ROOT.glob("cet4_*/cet4_*.pdf")):
        is_ans = pdf.stem.endswith("_ans")
        sub = "listening" if is_ans else "papers"
        txt = CORPUS / sub / f"{pdf.stem}.txt"
        pages = page_count(pdf)
        chars = len(txt.read_text()) if txt.exists() else -1
        rows.append((pdf.stem, is_ans, pages, chars))

    print(f"{'file':<28} {'kind':<6} {'pages':>5} {'chars':>8}  flag")
    print("-" * 60)
    for stem, is_ans, pages, chars in rows:
        kind = "ans" if is_ans else "paper"
        flag = ""
        if chars < 0:
            flag = "MISSING txt"
        elif is_ans:
            # _3 sets have no listening -> empty is fine
            if stem.replace("_ans", "").endswith("_3"):
                flag = "ok (no listening set)" if chars < 200 else "ok"
            elif chars < 1500:
                flag = "!! SUSPICIOUS (ans should have listening)"
        else:
            if pages <= 2 and chars < 3000:
                flag = "!! INCOMPLETE source PDF"
            elif chars < 8000:
                flag = "!! SUSPICIOUS (paper too short)"
        print(f"{stem:<28} {kind:<6} {pages:>5} {chars:>8}  {flag}")


if __name__ == "__main__":
    main()

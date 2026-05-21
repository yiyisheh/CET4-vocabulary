"""Extract English content from text-extractable PDFs.

For 真题 PDFs (`*_N.pdf`): keep all English, drop Part IV (Chinese translation prompt).
For ans PDFs (`*_ans.pdf`): keep only English listening transcripts.
"""
import re
from pathlib import Path
import fitz

ROOT = Path(__file__).parent.parent
OUT_PAPERS = ROOT / "corpus" / "papers"
OUT_LISTEN = ROOT / "corpus" / "listening"

# Section headers seen in ans PDF (used to slice listening transcripts)
LISTEN_HEADER = re.compile(r"听力原文")
NEXT_HEADERS = re.compile(
    r"答案详解|题干译文|答案解析|概览|全文翻译|重难点单词|难词译注|参考译文|"
    r"译点精析|审题|参考范文|范文译文|亮点词汇|写作句型|解析"
)


def strip_chinese_lines(text: str) -> str:
    out = []
    for line in text.splitlines():
        cn = sum(1 for c in line if "一" <= c <= "鿿")
        if line.strip() and cn / max(len(line), 1) < 0.2:
            out.append(line)
    return "\n".join(out)


def strip_parenthetical_cn(text: str) -> str:
    # Remove (圆柱体) / （有弹性的） annotations
    return re.sub(r"[(（][^)）]*[一-鿿]+[^)）]*[)）]", "", text)


def extract_paper(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    text = "\n".join(p.get_text() for p in doc)
    doc.close()
    text = re.split(r"Part\s+IV", text)[0]
    text = strip_parenthetical_cn(text)
    text = strip_chinese_lines(text)
    return text


def extract_listening(ans_path: Path) -> str:
    doc = fitz.open(ans_path)
    text = "\n".join(p.get_text() for p in doc)
    doc.close()

    chunks = []
    # Split into segments at every LISTEN_HEADER; each captured group is body until next header.
    parts = LISTEN_HEADER.split(text)
    # parts[0] is before first 听力原文 (skip); the rest are post-header bodies.
    for body in parts[1:]:
        # Cut off at next non-listening header
        cut = NEXT_HEADERS.split(body, maxsplit=1)[0]
        cut = strip_parenthetical_cn(cut)
        cut = strip_chinese_lines(cut)
        chunks.append(cut)
    return "\n".join(chunks)


def main() -> None:
    n_paper = n_listen = 0
    for pdf in sorted(ROOT.glob("CET/cet4_*/cet4_*.pdf")):
        is_ans = pdf.stem.endswith("_ans")
        # Check if extractable
        doc = fitz.open(pdf)
        text_len = sum(len(p.get_text()) for p in doc)
        doc.close()
        if text_len < 500:
            continue  # scanned, will OCR separately

        if is_ans:
            content = extract_listening(pdf)
            if content.strip():
                (OUT_LISTEN / f"{pdf.stem}.txt").write_text(content)
                n_listen += 1
        else:
            content = extract_paper(pdf)
            (OUT_PAPERS / f"{pdf.stem}.txt").write_text(content)
            n_paper += 1

    print(f"Extracted: {n_paper} papers, {n_listen} listening files")


if __name__ == "__main__":
    main()

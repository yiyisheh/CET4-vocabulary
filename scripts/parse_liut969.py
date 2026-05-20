"""Parse liut969's reference PDF into structured per-word dictionary data.

Extracts 音标(英/美) / 释义 / 变形 for each of his 1250 headwords.
Output: intermediate/liut969_dict.json  ->  {word: {uk, us, def, forms}}
"""
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).parent.parent
REF_PDF = ROOT / "CET-main" / "英语四级真题高频词汇.pdf"

HEADWORD_RE = re.compile(r"^[a-zA-Z][a-zA-Z'\-]*$")


def main():
    doc = fitz.open(REF_PDF)
    text = "\n".join(p.get_text() for p in doc)
    doc.close()
    lines = text.splitlines()

    # entry start = a lone word line whose next non-empty line begins with 英[
    starts = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or not HEADWORD_RE.match(s):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and lines[j].strip().startswith("英["):
            starts.append(i)
    print(f"entries found: {len(starts)}")

    result = {}
    for k, st in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        word = lines[st].strip().lower()
        blob = " ".join(x.strip() for x in lines[st + 1:end])

        uk = re.search(r"英\[([^\]]*)\]", blob)
        us = re.search(r"美\[([^\]]*)\]", blob)

        def field(label, blob):
            m = re.search(rf"{label}[:：]\s*(.*?)(?=(变形[:：]|例句[:：]|释义[:：]|$))",
                          blob)
            return m.group(1).strip() if m else ""

        result[word] = {
            "uk": uk.group(1).strip() if uk else "",
            "us": us.group(1).strip() if us else "",
            "def": field("释义", blob),
            "forms": field("变形", blob),
        }

    (ROOT / "intermediate" / "liut969_dict.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1))
    print(f"-> intermediate/liut969_dict.json ({len(result)} words)")
    for w in ["the", "people", "more", "study", "abandon"]:
        print(f"  {w}: {result.get(w)}")


if __name__ == "__main__":
    main()

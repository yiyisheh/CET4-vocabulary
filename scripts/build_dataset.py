"""Assemble the single source-of-truth dataset for the optimized PDF and the
iPad HTML app.

Combines:
  output/high_freq_cet4_df.txt   (rank, word, ipa, def, example)  -- 变形/词频 dropped
  intermediate/roots.json        (词根/词缀 breakdown)
  intermediate/core.json         (核心意象 for polysemous short words; merge_core.py)
  intermediate/senses.json       (真题义项: new def / ex / 常见短语; merge_senses.py)
  pyphen en_US                   (syllabification: com-po-si-tion)

senses.json overrides def and ex where it has them and adds phr; the word list's
original 释义 / 例句 stay in entries_full.json as def0 / ex0 (not shipped to the app).

Outputs:
  intermediate/entries_full.json  (list of entry dicts, section-tagged)

That JSON is the only output: the HTML app gets its data injected straight into
window.CET4 by build_html.py (there is no web/data.js).
"""
import json
import re
from pathlib import Path

import pyphen

ROOT = Path(__file__).parent.parent
SRC = ROOT / "output" / "high_freq_cet4_df.txt"
ROOTS = json.loads((ROOT / "intermediate" / "roots.json").read_text())
_CORE = ROOT / "intermediate" / "core.json"
CORE = json.loads(_CORE.read_text()) if _CORE.exists() else {}
_SENSES = ROOT / "intermediate" / "senses.json"
SENSES = json.loads(_SENSES.read_text()) if _SENSES.exists() else {}
OUT_JSON = ROOT / "intermediate" / "entries_full.json"
WEB = ROOT / "web"
WEB.mkdir(exist_ok=True)

DIC = pyphen.Pyphen(lang="en_US")
ENTRY_RE = re.compile(r"^\[(\d+)\]\s+(.+)$")
SECTION_RE = re.compile(r"——+\s*Section\s*(\d+)\s*——+")
IPA_RE = re.compile(r"英\[(.*?)\]\s*美\[(.*?)\]")


def syllables(word: str) -> str:
    """dictionary-style dotted form, e.g. com·po·si·tion. Empty if single syllable."""
    if not word.isalpha():
        return ""
    dotted = DIC.inserted(word).replace("-", "·")
    return dotted if "·" in dotted else ""


def parse():
    lines = SRC.read_text().splitlines()
    entries, cur, section = [], None, 1
    for raw in lines:
        s = raw.strip()
        sm = SECTION_RE.search(s)
        if sm:
            section = int(sm.group(1))
            continue
        m = ENTRY_RE.match(s)
        if m:
            cur = {"rank": int(m.group(1)), "word": m.group(2).strip(),
                   "section": section, "uk": "", "us": "", "def": "",
                   "ex_label": "例句", "ex": ""}
            entries.append(cur)
            continue
        if cur is None:
            continue
        im = IPA_RE.search(s)
        if im:
            cur["uk"], cur["us"] = im.group(1), im.group(2)
        elif s.startswith("释义"):
            cur["def"] = s.split(":", 1)[-1].split("：", 1)[-1].strip()
        elif s.startswith("例句"):
            cur["ex_label"] = "例句（自编）" if "自编" in s[:6] else "例句"
            # strip ONLY the leading "例句[（自编）]:" label. The old double-split also cut
            # at the first fullwidth colon INSIDE the sentence ("W: Oh…"→"女：…",
            # "Directions: …"→"说明：…"), leaving Chinese-only examples. Anchor to the label.
            m = re.match(r"例句(?:（自编）)?\s*[:：]\s*(.*)$", s)
            cur["ex"] = m.group(1).strip() if m else ""
        # 词频 / 变形 lines intentionally dropped
    return entries


def main():
    entries = parse()
    for e in entries:
        e["syl"] = syllables(e["word"])
        r = ROOTS.get(e["word"], {})
        parts = r.get("parts") or []
        e["root"] = {"parts": parts, "summary": r.get("summary", "")} if parts else None
        e["core"] = CORE.get(e["word"])
        e["def0"], e["ex0"] = e["def"], e["ex"]
        s = SENSES.get(e["word"]) or {}
        if s.get("def"):
            e["def"] = s["def"]
        if s.get("ex"):
            e["ex"], e["ex_label"] = s["ex"], "例句"
        e["phr"] = s.get("phr") or []

    OUT_JSON.write_text(json.dumps(entries, ensure_ascii=False, indent=1))

    n_root = sum(1 for e in entries if e["root"])
    n_core = sum(1 for e in entries if e["core"])
    n_syl = sum(1 for e in entries if e["syl"])
    n_def = sum(1 for e in entries if e["def"] != e["def0"])
    n_ex = sum(1 for e in entries if e["ex"] != e["ex0"])
    n_phr = sum(1 for e in entries if e["phr"])
    print(f"{len(entries)} entries -> {OUT_JSON.name}")
    print(f"  {n_root} with 词根, {n_core} with 核心意象, {n_syl} with 分词")
    print(f"  真题义项: {n_def} 释义 / {n_ex} 例句 replaced, {n_phr} with 常见短语")


if __name__ == "__main__":
    main()

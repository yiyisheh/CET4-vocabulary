"""Merge the 词根/词缀/合成 data into intermediate/roots.json.

Sources (in priority order; first non-empty wins per word):
  intermediate/root_chunks/out_*.json    -- 14 Claude sub-agents, full 1250 words (pass 1)
  intermediate/recall_chunks/out_*.json   -- recall pass over pass-1 empties
  intermediate/recall_manual.json         -- hand-curated affix recoveries
  intermediate/compounds.json             -- hand-curated compound words (type "词")

The 词根 breakdowns were produced by Claude sub-agents (native-level English
etymology), NOT by an external API. build_roots.py (DeepSeek) is kept only as an
API fallback and is no longer part of the final pipeline.

Every part is validated to have type in {前缀, 词根, 后缀, 词} and a non-empty text.
"""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
INT = ROOT / "intermediate"
OUT = INT / "roots.json"
VALID_TYPES = {"前缀", "词根", "后缀", "词"}


def load_words():
    import re
    src = ROOT / "output" / "high_freq_cet4_df.txt"
    ENTRY = re.compile(r"^\[(\d+)\]\s+(.+)$")
    return [ENTRY.match(s.strip()).group(2).strip()
            for s in src.read_text().splitlines()
            if ENTRY.match(s.strip())]


def _norm(t):
    return t.replace("-", "").replace("·", "").replace("(", "").replace(")", "").lower().strip()


def clean(v, word=None):
    if not isinstance(v, dict):
        return None
    parts = [p for p in (v.get("parts") or [])
             if isinstance(p, dict) and p.get("type") in VALID_TYPES and p.get("text")]
    # drop circular "root = the word itself" entries (e.g. part = 部分) — adds nothing
    if word and len(parts) == 1 and _norm(parts[0]["text"]) == word.lower():
        return None
    return {"parts": parts, "summary": v.get("summary", "") if parts else ""} if parts else None


def main():
    words = load_words()
    result = {w: {"parts": [], "summary": ""} for w in words}

    sources = (sorted(glob.glob(str(INT / "root_chunks" / "out_*.json")))
               + sorted(glob.glob(str(INT / "recall_chunks" / "out_*.json")))
               + [str(INT / "recall_manual.json"), str(INT / "compounds.json")])

    for f in sources:
        if not Path(f).exists():
            continue
        data = json.loads(Path(f).read_text())
        for w, v in data.items():
            if w in result and not result[w]["parts"]:
                c = clean(v, w)
                if c:
                    result[w] = c

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    n = sum(1 for v in result.values() if v["parts"])
    print(f"{len(result)} words -> {OUT.name}; {n} with 词根/词缀/合成 ({n*100//len(result)}%)")


if __name__ == "__main__":
    main()

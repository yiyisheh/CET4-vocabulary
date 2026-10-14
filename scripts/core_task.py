"""核心意象 v2: rewrite every card against the new 真题义项 (intermediate/senses.json).

The v1 cards (core_manual.json + core_chunks/out_*.json) were written for the old
dictionary-style 释义 and may explain senses that are gone (take 乘坐 is still
there, mean 吝啬 is not). A word with a card now shows at most CORE_MAX senses in
its 释义 (merge_senses.py); the card's derive line has to cover ALL of them, so
each word gets its own card (no same_as: took has other senses than take).

    python scripts/core_task.py make            -> core_chunks/v2_in_XX.json
    python scripts/core_task.py check v2_03     validates core_chunks/v2_out_03.json (agent runs this)

Candidates: words that have a card in core.json now (vetoes and rooted words are
already out) and still have >= 2 senses in senses.json "all"; a word down to one
sense loses its card. merge_core.py switches to the v2 outputs once v2_in files exist.
(brief: intermediate/core_chunks/PROMPT_v2.md)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
INT = ROOT / "intermediate"
CC = INT / "core_chunks"
BUDGET = 28          # words per task
POS = re.compile(r"^(modal v\.|aux\.|prep\.|conj\.|pron\.|det\.|art\.|adj\.|adv\.|num\.|int\.|n\.|v\.)?")


def terms(sense):
    """the Chinese words a derive line has to mention for this sense (any one of them)"""
    zh = POS.sub("", sense)
    zh = re.sub(r"（[^）]*）|\([^)]*\)", "", zh)
    return [t.strip("…… .") for t in re.split(r"[，；、,;]", zh) if t.strip("…… .")]


def mentions(derive, term):
    """「习惯于……的」 counts as mentioned when its longest piece (习惯于) is there"""
    return max(re.split(r"…+", term), key=len) in derive


def make():
    senses = json.loads((INT / "senses.json").read_text())
    core = json.loads((INT / "core.json").read_text())
    ranks = {e["word"]: e["rank"] for e in json.loads((INT / "entries_full.json").read_text())}
    recs, lost = [], []
    for w, card in core.items():
        allx = (senses.get(w) or {}).get("all") or []
        if len(allx) < 2:
            lost.append(w)
            continue
        recs.append({"rank": ranks[w], "word": w, "senses": allx,
                     "shown_in_def": senses[w]["shown"], "old": card})
    recs.sort(key=lambda r: r["rank"])
    for f in CC.glob("v2_in_*.json"):
        f.unlink()
    n = (len(recs) + BUDGET - 1) // BUDGET
    for k in range(n):
        (CC / f"v2_in_{k:02d}.json").write_text(json.dumps(recs[k::n], ensure_ascii=False, indent=1))
    print(f"{len(recs)} cards -> {n} tasks; {len(lost)} words down to <= 1 sense lose the card: {lost}")


def check(task):
    k = task.split("_")[-1]
    recs = json.loads((CC / f"v2_in_{k}.json").read_text())
    out = json.loads((CC / f"v2_out_{k}.json").read_text())
    errs = []
    if set(out) != {r["word"] for r in recs}:
        errs.append(f"keys differ: missing {sorted({r['word'] for r in recs} - set(out))}, "
                    f"extra {sorted(set(out) - {r['word'] for r in recs})}")
    for r in recs:
        v = out.get(r["word"], "missing")
        if v is None or v == "missing":
            continue
        if not isinstance(v, dict) or set(v) != {"image", "derive"} or not v["image"].strip() or not v["derive"].strip():
            errs.append(f'{r["word"]}: must be null or {{"image": ..., "derive": ...}}, both non-empty')
            continue
        for s in r["senses"]:
            ts = terms(s)
            if ts and not any(mentions(v["derive"], t) for t in ts):
                errs.append(f'{r["word"]}: derive does not mention sense 「{s}」 (write one of: {" / ".join(ts)})')
    print("\n".join(errs) if errs else f"OK {task}: {sum(1 for v in out.values() if v)} cards, "
                                         f"{sum(1 for v in out.values() if v is None)} null")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    if sys.argv[1:2] == ["make"]:
        make()
    elif sys.argv[1:2] == ["check"] and len(sys.argv) == 3:
        check(sys.argv[2])
    else:
        raise SystemExit(__doc__)

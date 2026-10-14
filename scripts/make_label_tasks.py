"""Stage C of the 真题义项 annotation: label every in-window sentence that has no
label yet, for every word that already has a 义项表 in sense_store.json.

That covers both cases with one rule:
  - round 1: the big words' sentences beyond the first BIG (stage B fixed their 义项表)
  - a later window (e.g. 2026 added): only the new year's sentences
One word may span several tasks. Run after every A/B task of the round is ingested.

    python scripts/make_label_tasks.py ROUND   -> intermediate/sense_chunks/C_ROUND_XX.json
                                                  + C_ROUND_XX.txt (what the agent reads, c_task.py)
(brief: intermediate/sense_chunks/PROMPT_C.md)
"""
import json
import sys
from collections import Counter

from c_task import render
from extract_sense_contexts import BUDGET
from sense_store import SC, ingest, sid


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    rnd = sys.argv[1]
    if list(SC.glob(f"C_{rnd}_*.json")):
        raise SystemExit(f"round {rnd} already has C tasks")
    store, _, _, pending = ingest()
    ab = [n for n in pending if n[0] in "AB"]
    if ab:
        raise SystemExit(f"A/B tasks not finished yet: {ab}")
    ctx = json.loads((SC / "contexts.json").read_text())

    pieces = []
    for w, c in ctx.items():
        ent = store.get(w)
        if not ent or not ent.get("senses"):
            continue
        todo = [s for s in c["sents"] if sid(s["text"]) not in ent["labels"]]
        seen = Counter(l[2:] for l in ent["labels"].values() if isinstance(l, str) and l.startswith("P:"))
        for i in range(0, len(todo), BUDGET):
            pieces.append({"word": w, "def": c["def"], "senses": ent["senses"],
                           "phrases_seen": [p for p, _ in seen.most_common(40)],
                           "notes": ent.get("notes") or [],
                           "sents": todo[i:i + BUDGET]})

    files, cur, size = [], [], 0
    for p in pieces:
        if cur and size + len(p["sents"]) > BUDGET:
            files.append(cur); cur, size = [], 0
        cur.append(p); size += len(p["sents"])
    if cur:
        files.append(cur)
    for i, f in enumerate(files):
        (SC / f"C_{rnd}_{i:02d}.json").write_text(json.dumps(f, ensure_ascii=False, indent=1))
    print(f"{sum(len(p['sents']) for p in pieces)} unlabelled sentences -> {len(files)} C tasks")
    render(rnd)


if __name__ == "__main__":
    main()

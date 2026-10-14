"""Collect EVERY real exam sentence (inside corpus/window.json) each headword
appears in, and cut the 真题义项 annotation into sub-agent tasks
(brief: intermediate/sense_chunks/PROMPT.md).

For every entry (exact surface form, case-insensitive: `took` matches only `took`)
the in-window papers + listening transcripts are split into sentences; identical
sentences (exam boilerplate repeats in every paper) are kept once with
multiplicity `n`. Sentences are ordered round-robin across papers, so the first
BIG of a word are a balanced sample.

    python scripts/extract_sense_contexts.py ROUND      e.g. r1, 2026
    -> intermediate/sense_chunks/contexts.json           {word: {rank, def, total, sents:[{id,text,n,src}]}}
       intermediate/sense_chunks/A_ROUND_XX.json         new small words (<= BIG sentences): full job
       intermediate/sense_chunks/B_ROUND_XX.json         new big words: first BIG sentences -> 义项表 + labels

contexts.json always reflects the CURRENT window and is what merge_senses.py
counts against. Words that already have a 义项表 in sense_store.json get no A/B
task: their new in-window sentences are labelled by stage C
(make_label_tasks.py ROUND). So adding 2026 / dropping a year = edit
corpus/window.json, rerun this, label only what's new.
"""
import json
import re
import sys
from collections import defaultdict

import corpus_window
from sense_store import ROOT, SC, load

BIG = 80          # words with more unique sentences than this go through stages B + C
BUDGET = 600      # sentences per sub-agent task (small, so an interrupted task loses little)

SPLIT = re.compile(r"(?<=[.!?])[\"”’)]*\s+(?=[\"“‘(]*[A-Z0-9])|\n+")
NOISE = re.compile(r"^\s*(?:[A-D]\)|\d+\.|\(\d+\))\s*")

# 题干 = the exam's own instructions (Directions blocks, Part/Section headings,
# "Questions 1 and 2 are based on…", answer-sheet boilerplate). They are shown
# like any other usage but never decide a word's primary sense (merge_senses.py).
DIRECTIONS = re.compile(r"^\s*Direct[il1]ons?\b", re.I)
STRUCT = re.compile(r"^\s*(?:Part\b|Section\b|Passage\b|Questions?\s+\d|\d+\s*\.|[A-D]\))", re.I)
STEM = re.compile(
    r"^(?:part\s+\S+\s+(?:writing|listening|reading|translation)|section\s+[abc]\b|passage\s+(?:one|two)\b"
    r"|questions?\s+\d+\s+(?:and|to)\s+\S+\s+(?:are|is)\s+based|\(\s*\d+\s*minutes\s*\))"
    r"|answer\s+sheet|single\s+line\s+through|corresponding\s+letter|choices?\s+marked|spoken\s+only\s+once"
    r"|word\s+bank|choice\s+in\s+the\s+bank|ten\s+(?:blanks|statements)|statement\s+given\s+below"
    r"|you\s+(?:will|are\s+going\s+to)\s+(?:hear|read)\b|you\s+(?:should|must)\s+(?:write|choose|decide)"
    r"|you\s+are\s+(?:allowed|required|now\s+to\s+write)|you\s+will\s+have\s+\d+\s+minutes"
    r"|no\s+more\s+than\s+\d+\s+words|write\s+at\s+least|translate\s+a\s+passage"
    r"|^each\s+(?:passage|statement|paragraph|choice)\b|identify\s+the\s+paragraph|you\s+may\s+(?:not\s+)?(?:choose|use)"
    r"|read\s+the\s+passage\s+through|for\s+each\s+of\s+them\s+there\s+are", re.I)
END = re.compile(r"[.!?][\"”’)]*\s*$")       # a Directions block runs on only while its line is unfinished
STEM_SITTINGS = 3  # identical sentence in this many exam sittings = boilerplate


def pieces(text):
    for s in SPLIT.split(text):
        s = NOISE.sub("", " ".join(s.split()))
        if 3 <= len(s.split()) <= 60:
            yield s


def sentences():
    """-> list of (src, sentence) from the in-window corpus"""
    out = []
    for sub in ("papers", "listening"):
        for f in corpus_window.files(sub):
            src = f.stem.replace("_ans", "") + ("·听力" if sub == "listening" else "")
            out += [(src, s) for s in pieces(f.read_text())]
    return out


def stem_texts():
    """-> set of in-window sentence texts that are 题干 (see STEM above)"""
    stems, sittings = set(), defaultdict(set)
    for src, s in sentences():
        sittings[s].add(src[:12])                     # cet4_YYYY_MM
        if STEM.search(s):
            stems.add(s)
    stems |= {s for s, v in sittings.items() if len(v) >= STEM_SITTINGS}
    for sub in ("papers", "listening"):               # whole Directions blocks, incl. wrapped lines
        for f in corpus_window.files(sub):
            inside = False
            for line in f.read_text().splitlines():
                if DIRECTIONS.match(line):
                    inside = True
                elif not line.strip() or STRUCT.match(line):
                    inside = False
                if inside:
                    stems.update(pieces(line))
                    inside = not END.search(line)
    return stems


def collect(entries):
    sents = sentences()
    ctx = {}
    for e in entries:
        pat = re.compile(r"(?<![A-Za-z'’-])" + re.escape(e["word"]) + r"(?![A-Za-z-])", re.I)
        uniq, by_src, total = {}, defaultdict(list), 0
        for src, s in sents:
            k = len(pat.findall(s))
            if not k:
                continue
            total += k
            if s not in uniq:
                uniq[s] = {"text": s, "n": 0, "src": src}
                by_src[src].append(s)
            uniq[s]["n"] += 1
        order, queues = [], [list(v) for _, v in sorted(by_src.items())]
        while any(queues):
            for q in queues:
                if q:
                    order.append(q.pop(0))
        ctx[e["word"]] = {"rank": e["rank"], "def": e["def"], "total": total,
                          "sents": [{"id": i, **uniq[s]} for i, s in enumerate(order)]}
    return ctx


def pack(items, prefix):
    """items: [(sentence_count, record)] -> files of ~BUDGET sentences each"""
    files, cur, size = [], [], 0
    for n, rec in items:
        if cur and size + n > BUDGET:
            files.append(cur); cur, size = [], 0
        cur.append(rec); size += n
    if cur:
        files.append(cur)
    for i, f in enumerate(files):
        (SC / f"{prefix}_{i:02d}.json").write_text(json.dumps(f, ensure_ascii=False, indent=1))
    return len(files)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    rnd = sys.argv[1]
    if list(SC.glob(f"[AB]_{rnd}_*.json")):
        raise SystemExit(f"round {rnd} already has A/B tasks; pick a new round name")
    data = json.loads((ROOT / "intermediate" / "entries_full.json").read_text())
    SC.mkdir(parents=True, exist_ok=True)
    ctx = collect(data)
    (SC / "contexts.json").write_text(json.dumps(ctx, ensure_ascii=False))

    store = load()[0]
    small, big = [], []
    for w, c in ctx.items():
        if store.get(w, {}).get("senses") or not c["sents"]:
            continue
        rec = {"rank": c["rank"], "word": w, "def": c["def"], "total": c["total"],
               "uniq": len(c["sents"]), "sents": c["sents"][:BIG]}
        (big if len(c["sents"]) > BIG else small).append((len(rec["sents"]), rec))
    na, nb = pack(small, f"A_{rnd}"), pack(big, f"B_{rnd}")
    print(f"window {sorted(corpus_window.YEARS)}: {len(ctx)} words, {sum(len(c['sents']) for c in ctx.values())} unique sentences")
    print(f"  A: {len(small)} new small words -> {na} tasks;  B: {len(big)} new big words -> {nb} tasks")
    print(f"  no sentence in window (old def kept): {[w for w, c in ctx.items() if not c['sents']]}")
    print(f"  next: label A/B, then `make_label_tasks.py {rnd}` for the rest")


if __name__ == "__main__":
    main()

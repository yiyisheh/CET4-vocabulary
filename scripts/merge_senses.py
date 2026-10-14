"""Count the 真题义项 labels against the CURRENT window and produce the new 释义,
例句 and 常见短语 (plus the stand-alone phrase table for the next stage).

Counts are recomputed every run from contexts.json (= corpus/window.json) and
the window-independent sense_store.json, so changing the window only needs
re-extraction + labelling the new sentences. Nothing here is cached per window.

    python scripts/merge_senses.py ROUND
      1. ingest finished tasks; refuse while A/B/C tasks are unfinished
      2. if some word's example no longer shows its primary sense (or left the
         window) -> write E_ROUND_XX tasks; if some phrase has no gloss -> D_ROUND_XX
         tasks; stop. Run those, then run this again.
      3. otherwise write intermediate/senses.json, intermediate/phrases.json
         and tmp/senses_review.md

Keep rule: a sense is shown iff it labels >= 2 distinct sentences, or the word
has <= SMALL sentences in the window and the sense labels one. Senses absent from
the exams are dropped entirely. Order: POS groups by their strongest sense,
senses inside a group by weight (= Σ n) in the exam MATERIAL counting at most
PAPER_CAP per paper (one article repeating a word can't make its sense the primary
one -- leave 「休假」 was 27 sentences from a single paper; ranking by the bare
number of papers was tried and is too coarse: building → 「建立」, head → 「首领」),
then by the plain Σ n; 题干 (the
exam's own instructions, extract_sense_contexts.stem_texts) never decide the
order or the example -- a sense seen only in 题干 is still shown, after the others.
Function words (primary sense prep./conj./pron./...) show at most FUNC_MAX senses;
the rest are collocations, left to the 常见短语 line and to reading. A word with a
核心意象 card (intermediate/core.json) shows at most CORE_MAX senses in its 释义;
the card's derive line covers the full list, written to senses.json as "all"
(take: 13 senses -> 5 in the 释义, all 13 on the card).
Irregular forms get "take 的过去式." in front (except no_form_prefix: could ≠ "can
的过去式" for a learner); regular forms get "(study 的复数)" after the POS group
the form belongs to (means: the v. group only -- the n. 方法 is not "mean 的三单").

intermediate/sense_overrides.json is the hand-made layer on top of the labels:
merge duplicate senses, promote the core sense to primary where the exam counts
are thin or led by a derived sense (run 跑, not 经营), drop / demote a sense, keep
core senses the window missed (fit v.适合), and patch D-stage phrase glosses.
See its "_说明".
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from extract_sense_contexts import stem_texts
from sense_store import INT, ROOT, SC, ingest, norm_phrase, sid

OUT, PHRASES, REVIEW = INT / "senses.json", INT / "phrases.json", ROOT / "tmp" / "senses_review.md"
OVERRIDES = INT / "sense_overrides.json"
SMALL = 10         # words this rare in the window keep single-sentence senses
PAPER_CAP = 3      # ranking counts a sense at most this many times per paper
PHRASE_MIN = 3     # phrases shown on a word card need this many occurrences
PHRASE_MAX = 5     # at most this many phrases per card
FUNC_POS = {"", "prep.", "conj.", "pron.", "det.", "art.", "aux.", "modal v."}   # "" = to 的不定式
FUNC_MAX = 6       # senses shown for a word whose primary sense is one of FUNC_POS (5 lost to's from 1 to 10)
CORE_MAX = 5       # senses shown in the 释义 of a (non-function) word with a 核心意象 card
CORE = INT / "core.json"
FORM_POS = (("复数", ("n.",)), ("第三人称单数", ("v.",)), ("过去式", ("v.",)), ("过去分词", ("v.", "adj.")),
            ("现在分词", ("v.",)), ("比较级", ("adj.", "adv.")), ("最高级", ("adj.", "adv.")))
E_BUDGET, D_BUDGET = 40, 80   # words / phrases per E / D task


def labels_of(lab):
    return lab if isinstance(lab, list) else [lab]


def load_overrides(store):
    """-> {word: {remap: {i: j}, promote, drop, demote, keep: {i}}}, no_form_prefix words, {raw phrase: patch}"""
    raw = json.loads(OVERRIDES.read_text())
    per = defaultdict(lambda: {"remap": {}, "promote": set(), "drop": set(), "demote": set(), "keep": set()})

    def idx(w, name):
        ids = [i for i, s in enumerate(store[w]["senses"]) if s["pos"] + s["zh"] == name]
        if len(ids) != 1:
            raise SystemExit(f"{OVERRIDES.name}: {w}: {name!r} matches {len(ids)} senses")
        return ids[0]
    for w, m in raw["merge"].items():
        for a, b in m.items():
            per[w]["remap"][idx(w, a)] = idx(w, b)
    for kind in ("promote", "drop", "demote", "keep"):
        for w, names in raw[kind].items():
            per[w][kind] |= {idx(w, n) for n in names}
    return per, set(raw["no_form_prefix"]), raw["phrases"]


def count_word(c, ent, stems, ov):
    """-> weight Counter of (material Σn, 题干 Σn), hits Counter, per-sense sentences
    (material ones first), phrase sids {raw: [sid]}, per-sense {paper: material Σn}"""
    weight, hits, by_sense, phr = defaultdict(lambda: [0, 0]), Counter(), defaultdict(list), defaultdict(list)
    papers = defaultdict(Counter)
    for s in c["sents"]:
        k, stem = sid(s["text"]), s["text"] in stems
        seen = set()
        for lab in labels_of(ent["labels"].get(k)):
            if isinstance(lab, int):
                lab = ov["remap"].get(lab, lab)
                if lab in ov["drop"] or lab in seen:
                    continue
                seen.add(lab)
                weight[lab][stem] += s["n"]; hits[lab] += 1; by_sense[lab].append(s)
                if not stem:
                    papers[lab][s["src"].split("·")[0]] += s["n"]
            elif isinstance(lab, str) and lab.startswith("P:"):
                phr[norm_phrase(lab[2:])].append(s)
    for ss in by_sense.values():
        ss.sort(key=lambda s: s["text"] in stems)
    return weight, hits, by_sense, phr, papers


def rank_key(weight, papers, promote, demote):
    return lambda i: (i not in promote, i in demote, -sum(min(n, PAPER_CAP) for n in papers[i].values()),
                      -weight[i][0], -weight[i][1], i)


def primary(weight, key):
    return min(weight, key=key) if weight else None


def with_form(groups, form):
    """groups {pos: text} -> the 释义 line, "(study 的复数)" after the group(s) the form belongs to"""
    if form and not any(form in t for t in groups.values()):
        poss = {p for k, ps in FORM_POS if k in form for p in ps}
        target = ([p for p in groups if p in poss] or list(groups))[-1]
        groups = {**groups, target: f"{groups[target]}({form})"}
    return " ".join(f"{pos}{t}." for pos, t in groups.items())


def write_tasks(kind, rnd, recs, budget):
    """numbered after the existing KIND_RND_NN tasks, so finished ones are never overwritten"""
    used = [int(f.name.split(".")[0].rsplit("_", 1)[1]) for f in SC.glob(f"{kind}_{rnd}_*.json")]
    start = max(used, default=-1) + 1
    for i in range(0, len(recs), budget):
        (SC / f"{kind}_{rnd}_{start + i // budget:02d}.json").write_text(
            json.dumps(recs[i:i + budget], ensure_ascii=False, indent=1))
    return (len(recs) + budget - 1) // budget


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    rnd = sys.argv[1]
    store, examples, gloss, pending = ingest()
    if pending:
        raise SystemExit(f"unfinished tasks: {pending}")
    ctx = json.loads((SC / "contexts.json").read_text())
    stems = stem_texts()
    entries = {e["word"]: e for e in json.loads((INT / "entries_full.json").read_text())}
    overrides, no_prefix, patches = load_overrides(store)
    core = {w for w, v in json.loads(CORE.read_text()).items() if v}
    unknown = set(patches) - set(gloss)
    if unknown:
        raise SystemExit(f"{OVERRIDES.name}: phrases not in phrase_gloss.json: {sorted(unknown)}")
    gloss = {raw: {**g, **patches.get(raw, {})} for raw, g in gloss.items()}

    counted, e_tasks = {}, []
    phrase_sents, phrase_heads = defaultdict(dict), defaultdict(set)
    for w, c in ctx.items():
        ent = store.get(w)
        if not ent or not c["sents"]:
            continue
        unl = [s for s in c["sents"] if sid(s["text"]) not in ent["labels"]]
        if unl:
            raise SystemExit(f"{w}: {len(unl)} in-window sentences unlabelled -> run make_label_tasks.py first")
        ov = overrides[w]
        weight, hits, by_sense, phr, papers = count_word(c, ent, stems, ov)
        key = rank_key(weight, papers, ov["promote"], ov["demote"])
        counted[w] = (weight, hits, phr, papers, key)
        for raw, ss in phr.items():
            for s in ss:
                phrase_sents[raw][sid(s["text"])] = s
            phrase_heads[raw].add(w)
        p = primary(weight, key)
        if p is None:
            continue
        ex = examples.get(w)
        pool = [s for s in by_sense[p] if s["text"] not in stems] or by_sense[p]   # 题干 only as a last resort
        win = {sid(s["text"]) for s in pool}
        if not ex or ex["sid"] not in win:
            cands = sorted(pool, key=lambda s: len(s["text"]))[:40]
            e_tasks.append({"word": w, "def": c["def"], "sense": ent["senses"][p], "sents": cands})

    d_tasks, groups = [], defaultdict(list)
    for raw in phrase_sents:
        if raw not in gloss:
            groups[raw].append(raw)
    for raw, variants in groups.items():
        ss = sorted(phrase_sents[raw].values(), key=lambda s: len(s["text"]))[:20]
        d_tasks.append({"phrase": raw, "count": sum(s["n"] for s in phrase_sents[raw].values()),
                        "headwords": sorted(phrase_heads[raw]), "variants": variants,
                        "sents": [{"id": i, "text": s["text"], "n": s["n"]} for i, s in enumerate(ss)]})

    if e_tasks or d_tasks:
        for old in list(SC.glob(f"E_{rnd}_*.json")) + list(SC.glob(f"D_{rnd}_*.json")):
            if not old.name.endswith(".out.json") and not old.with_name(old.stem + ".out.json").exists():
                raise SystemExit(f"{old.name} exists but is unfinished/uningested; run it first")
        for t in e_tasks:     # E tasks need task-local ids too
            t["sents"] = [{"id": i, "text": s["text"], "n": s["n"]} for i, s in enumerate(t["sents"])]
        ne = write_tasks("E", rnd, e_tasks, E_BUDGET)
        nd = write_tasks("D", rnd, d_tasks, D_BUDGET)
        print(f"need {len(e_tasks)} examples -> {ne} E tasks; {len(d_tasks)} unglossed phrases -> {nd} D tasks. "
              f"Run them, then rerun merge_senses.py {rnd}.")
        return

    # ---- phrase table (canonical) ----
    table = {}
    for raw, sents in phrase_sents.items():
        g = gloss[raw]
        if not g["valid"]:
            continue
        t = table.setdefault(g["canonical"], {"pos": g["pos"], "zh": g["zh"], "example": g["example"],
                                              "sids": {}, "headwords": set()})
        t["sids"].update(sents)
        t["headwords"] |= phrase_heads[raw]
        if not t["example"] and g["example"]:
            t["example"] = g["example"]
    phrases = {k: {"pos": v["pos"], "zh": v["zh"], "count": sum(s["n"] for s in v["sids"].values()),
                   "headwords": sorted(v["headwords"]),
                   "example": ({"en": v["example"]["en"], "zh": v["example"]["zh"]} if v["example"] else None)}
               for k, v in table.items()}
    phrases = dict(sorted(phrases.items(), key=lambda kv: -kv[1]["count"]))
    PHRASES.write_text(json.dumps(phrases, ensure_ascii=False, indent=1))

    # ---- per-word 释义 / 例句 / 常见短语 ----
    result, lines = {}, []
    for w, (weight, hits, phr, papers, key) in counted.items():
        ent, c, ov = store[w], ctx[w], overrides[w]
        senses = ent["senses"]
        keep = sorted((i for i in range(len(senses)) if i not in ov["drop"] and i not in ov["remap"]
                       and (hits[i] >= 2 or (hits[i] >= 1 and len(c["sents"]) <= SMALL))), key=key)
        func = bool(keep) and senses[keep[0]]["pos"] in FUNC_POS
        if func:
            keep = keep[:FUNC_MAX]
        keep = sorted(set(keep) | ov["keep"], key=key)
        shown = keep if func or w not in core else keep[:CORE_MAX]
        groups = {}
        for i in shown:
            groups.setdefault(senses[i]["pos"], []).append(senses[i]["zh"])
        groups = {pos: "; ".join(zs) for pos, zs in groups.items()}
        body = None
        if groups and ent.get("form") and ent.get("irregular"):
            body = with_form(groups, None) if w in no_prefix else f'{ent["form"]}. {with_form(groups, None)}'
        elif groups:
            body = with_form(groups, ent.get("form"))
        ex = examples.get(w)
        canon = Counter()
        for raw in phr:
            g = gloss.get(raw)
            if g and g["valid"] and g["canonical"] in phrases:
                canon[g["canonical"]] = phrases[g["canonical"]]["count"]
        phr_show = [{"p": k, "zh": phrases[k]["zh"]} for k, n in canon.most_common() if n >= PHRASE_MIN][:PHRASE_MAX]
        if not body and canon:          # the word only ever occurs inside a phrase (according -> according to)
            top = canon.most_common(1)[0][0]
            body, ex = f'{top} {phrases[top]["zh"]}', phrases[top]["example"]
            phr_show = [p for p in phr_show if p["p"] != top]
        result[w] = {"def": body, "ex": f'{ex["en"]}({ex["zh"]})' if ex and body else None,
                     "phr": phr_show,
                     "all": [f'{senses[i]["pos"]}{senses[i]["zh"]}' for i in keep], "shown": len(shown),
                     "counts": {f'{senses[i]["pos"]}{senses[i]["zh"]}': [*weight[i], len(papers[i])]
                                for i in sorted(weight, key=key)},
                     "dropped": [f'{s["pos"]}{s["zh"]}' for i, s in enumerate(senses) if i not in keep]}
        old = entries[w]
        r = result[w]
        old_def, old_ex = old.get("def0", old["def"]), old.get("ex0", old["ex"])   # def0/ex0: word-list originals
        lines += [f'### {old["rank"]}. {w}  （真题 {c["total"]} 次 / {len(c["sents"])} 句）',
                  f'- 旧释义：{old_def}',
                  f'- **新释义：{r["def"] or "（无义项出现，保留旧释义）"}**',
                  f'- 计数（材料／题干 · 材料出现的卷数）：{"；".join(f"{k} ×{a}" + (f"／{b}" if b else "") + f" · {p}套" for k, (a, b, p) in r["counts"].items()) or "—"}',
                  f'- 去掉：{"；".join(r["dropped"]) or "—"}',
                  f'- 常见短语：{"；".join(p["p"] + " " + p["zh"] for p in phr_show) or "—"}',
                  f'- 旧例句：{old_ex}',
                  f'- **新例句：{r["ex"] or "（保留旧例句）"}**']
        lines += [f"- ⚠ {n}" for n in ent.get("notes") or []]
        lines.append("")
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    REVIEW.parent.mkdir(exist_ok=True)
    REVIEW.write_text("# 真题义项重做 · 复核表\n\n" + "\n".join(lines))
    print(f"{len(result)} words -> {OUT.name}; {len(phrases)} phrases -> {PHRASES.name}; review -> {REVIEW.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

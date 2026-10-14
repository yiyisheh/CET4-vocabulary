"""Window-independent store of the 真题义项 annotation.

Sub-agent tasks (intermediate/sense_chunks/{A,B,C,D,E}_*.json) carry task-local
integer sentence ids; ingest() re-keys every label by the sentence's TEXT HASH
(sid), so labels survive any change of the corpus window: a dropped year's
sentences simply stop being counted, a new year's sentences are the only ones
left to label (see make_label_tasks.py). Nothing here depends on corpus/window.json.

  intermediate/sense_store.json   {word: {senses:[{pos,zh}], labels:{sid: label},
                                          form, irregular, notes:[...]}}
  intermediate/sense_examples.json {word: {sid, en, zh}}        candidate example per word
  intermediate/phrase_gloss.json   {raw phrase: {canonical, pos, zh, example:{sid,en,zh}, valid, note}}

label = int | [int, ...] | "P:phrase" | "X"
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "intermediate"
SC = INT / "sense_chunks"
STORE, EXAMPLES, GLOSS = INT / "sense_store.json", INT / "sense_examples.json", INT / "phrase_gloss.json"


def sid(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def _load(p):
    return json.loads(p.read_text()) if p.exists() else {}


def load():
    return _load(STORE), _load(EXAMPLES), _load(GLOSS)


def save(store, examples, gloss):
    STORE.write_text(json.dumps(store, ensure_ascii=False, indent=1))
    EXAMPLES.write_text(json.dumps(examples, ensure_ascii=False, indent=1))
    GLOSS.write_text(json.dumps(gloss, ensure_ascii=False, indent=1))


def norm_phrase(p: str) -> str:
    return re.sub(r"\s+", " ", p.strip().lower().strip(".,;:!?\"'“”‘’"))


def _example(ex, id2sid):
    if not isinstance(ex, dict) or str(ex.get("id")) not in id2sid or not ex.get("en") or not ex.get("zh"):
        return None
    if any(c in ex["en"] for c in "(（"):        # 网页/配音都在第一个括号处切开英/中
        return None
    return {"sid": id2sid[str(ex["id"])], "en": ex["en"].strip(), "zh": ex["zh"].strip()}


def tasks():
    return [f for f in sorted(SC.glob("[ABCDE]_*.json")) if not f.name.endswith(".out.json")]


def check(fin):
    """-> None if fin's output is complete, else the reason it isn't ("missing" if absent).
    Tasks are sized to finish in one go; an incomplete output is deleted and the task re-run."""
    fout = fin.with_name(fin.stem + ".out.json")
    if not fout.exists():
        return "missing"
    try:
        out = json.loads(fout.read_text())
    except ValueError as e:
        return f"bad JSON: {e}"
    stage, recs = fin.name[0], json.loads(fin.read_text())
    key = "phrase" if stage == "D" else "word"
    if {r[key] for r in recs} != set(out):
        return f"keys differ ({len(out)}/{len(recs)})"
    if stage in "ABC":
        for r in recs:
            ann = out[r["word"]]
            if not isinstance(ann, dict) or not isinstance(ann.get("labels"), dict):
                return f"{r['word']}: no labels"
            if {str(s["id"]) for s in r["sents"]} != set(map(str, ann["labels"])):
                return f"{r['word']}: labels cover {len(ann['labels'])}/{len(r['sents'])} sentences"
            n = len(ann.get("senses") or r.get("senses") or [])
            m = len(ann.get("new_senses") or [])
            for lab in ann["labels"].values():
                for x in (lab if isinstance(lab, list) else [lab]):
                    if isinstance(x, int) and not 0 <= x < n:
                        return f"{r['word']}: label {x} out of range"
                    if isinstance(x, str) and not (x == "X" or x.startswith("P:")
                                                   or (stage == "C" and x[:1] == "N" and x[1:].isdigit() and int(x[1:]) < m)):
                        return f"{r['word']}: bad label {x!r}"
    return None


def ingest():
    """Fold every COMPLETE task (X_*.json + valid X_*.out.json) into the stores. Idempotent.
    -> (store, examples, gloss, {task name: reason} for tasks not ingested)"""
    store, examples, gloss = load()
    pending = {}
    for fin in tasks():
        why = check(fin)
        if why:
            pending[fin.name] = why
            continue
        fout = fin.with_name(fin.stem + ".out.json")
        stage, recs, out = fin.name[0], json.loads(fin.read_text()), json.loads(fout.read_text())
        if stage in "ABC":
            for rec in recs:
                w = rec["word"]
                ann = out[w]
                id2sid = {str(s["id"]): sid(s["text"]) for s in rec["sents"]}
                ent = store.setdefault(w, {"senses": [], "labels": {}, "form": None, "irregular": False, "notes": []})
                remap = {}
                if stage in "AB":
                    if not ent["senses"]:
                        ent["senses"] = ann["senses"]
                    ent["form"], ent["irregular"] = ann.get("form"), bool(ann.get("irregular"))
                    ex = _example(ann.get("example"), id2sid)
                    if ex and w not in examples:
                        examples[w] = ex
                else:
                    for j, s in enumerate(ann.get("new_senses") or []):
                        key = (s["pos"], s["zh"])
                        idx = next((i for i, t in enumerate(ent["senses"]) if (t["pos"], t["zh"]) == key), None)
                        if idx is None:
                            ent["senses"].append(s); idx = len(ent["senses"]) - 1
                        remap[f"N{j}"] = idx
                for i, lab in ann["labels"].items():
                    if isinstance(lab, str) and lab in remap:
                        lab = remap[lab]
                    elif isinstance(lab, list):
                        lab = [remap.get(x, x) if isinstance(x, str) else x for x in lab]
                    ent["labels"][id2sid[str(i)]] = lab
                if ann.get("note") and ann["note"] not in ent["notes"]:
                    ent["notes"].append(ann["note"])
        elif stage == "D":
            for rec in recs:
                id2sid = {str(s["id"]): sid(s["text"]) for s in rec["sents"]}
                for raw in rec["variants"]:
                    g = out.get(rec["phrase"]) or {}
                    gloss[norm_phrase(raw)] = {"canonical": norm_phrase(g.get("canonical") or rec["phrase"]),
                                               "pos": g.get("pos", ""), "zh": g.get("zh", ""),
                                               "example": _example(g.get("example"), id2sid),
                                               "valid": g.get("valid", True) is not False, "note": g.get("note", "")}
        elif stage == "E":
            for rec in recs:
                id2sid = {str(s["id"]): sid(s["text"]) for s in rec["sents"]}
                ex = _example(out.get(rec["word"]), id2sid)
                if ex:
                    examples[rec["word"]] = ex
    save(store, examples, gloss)
    return store, examples, gloss, pending


def reset(names):
    """Redo whole A/B tasks: delete their outputs and forget their words' 义项表, labels
    and examples (ingest keeps an existing 义项表, so a redo must start from nothing)."""
    store, examples, gloss = load()
    for name in names:
        fin = SC / (name if name.endswith(".json") else name + ".json")
        if fin.name[0] not in "AB" or not fin.exists():
            raise SystemExit(f"{fin.name}: not an A/B task")
        for rec in json.loads(fin.read_text()):
            store.pop(rec["word"], None)
            examples.pop(rec["word"], None)
        fin.with_name(fin.stem + ".out.json").unlink(missing_ok=True)
        print(f"reset {fin.name}")
    save(store, examples, gloss)


if __name__ == "__main__":
    # status: python scripts/sense_store.py   (ingests finished tasks, lists the rest)
    # redo:   python scripts/sense_store.py --reset B_r1_00 B_r1_08
    import sys
    if sys.argv[1:2] == ["--reset"]:
        reset(sys.argv[2:])
    _, _, _, pend = ingest()
    allt = tasks()
    print(f"{len(allt) - len(pend)}/{len(allt)} tasks ingested")
    for name, why in pend.items():
        print(f"  {name}: {why}")

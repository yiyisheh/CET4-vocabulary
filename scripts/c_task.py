"""Stage C, sub-agent side: what the agent reads, what it writes, and the check that
turns its answer into the C_*.out.json that sense_store.py ingests (format unchanged).

C exists only to COUNT senses (which survive, which is first) and phrases. So the agent
gets a reading list, not raw JSON:
  - one block per word: 义项表 with the B-sample count and one B-sample sentence per sense,
    the phrases already seen, the notes; then the sentences as plain lines, the word
    marked 【】, sorted by what follows it (same usages sit together), hints appended:
    ?P:… = a phrase someone already labelled P appears around the word here;
    ?X   = capitalised mid-sentence (name?)
  - mode 找例外: the B sample is >= DOMINANT one sense -> the agent still reads every line
    but writes only the lines that are NOT that sense; unlisted lines count as it.
    mode 全标: every line gets a label.

    python scripts/c_task.py render ROUND            -> C_ROUND_XX.txt next to each C_ROUND_XX.json
    python scripts/c_task.py check C_r1_05           C_r1_05.labels.txt -> C_r1_05.out.json (agent runs this)
    python scripts/c_task.py ctx C_r1_05 WORD ID     the sentence in its original paper (agent runs this)

C_*.labels.txt (written by the agent):
    # take                      start of a word's section (every word of the task must have one)
    N0 | v. | 服用（药）          a sense missing from the 义项表; label it N0, N1, ...
    note: ...                   optional, one per word
    4124 P:take place           id + label: 2 / P:phrase / X / N0 / several joined by ";" (0; P:at least)
(brief: intermediate/sense_chunks/PROMPT_C.md)
"""
import json
import re
import sys
from collections import Counter

from sense_store import ROOT, SC, check as store_check, load, sid

DOMINANT = 0.9      # B-sample share of one sense at which a word goes to mode 找例外

IRREGULAR = {
    "be": "am is are was were been being", "have": "has had having", "do": "does did done doing",
    "go": "goes went gone going", "take": "took taken", "give": "gave given", "get": "got gotten",
    "come": "came", "make": "made", "find": "found", "keep": "kept", "bring": "brought",
    "think": "thought", "run": "ran", "break": "broke broken", "grow": "grew grown", "hold": "held",
    "lead": "led", "leave": "left", "pay": "paid", "say": "said", "see": "saw seen", "tell": "told",
    "feel": "felt", "know": "knew known", "stand": "stood", "win": "won", "lose": "lost",
    "fall": "fell fallen", "buy": "bought", "catch": "caught", "teach": "taught", "spend": "spent",
    "build": "built", "send": "sent", "mean": "meant", "meet": "met", "begin": "began begun",
    "write": "wrote written", "speak": "spoke spoken", "drive": "drove driven",
    "choose": "chose chosen", "wear": "wore worn", "rise": "rose risen", "shake": "shook shaken",
    "hear": "heard", "sit": "sat", "fight": "fought", "throw": "threw thrown", "draw": "drew drawn",
    "show": "shown", "wake": "woke woken", "stick": "stuck", "hang": "hung", "spin": "spun",
    "light": "lit", "sell": "sold", "understand": "understood", "become": "became",
}
POSS = r"(?:my|your|his|her|its|our|their|one's|someone's|\S+['’]s)"
GAPS = {"...": 4, "sb": 3, "sth": 3}     # placeholders; "or something", "have something to do with" are literal


def word_re(w):
    # same boundaries as extract_sense_contexts.collect()
    return re.compile(r"(?<![A-Za-z'’-])" + re.escape(w) + r"(?![A-Za-z-])", re.I)


def _forms(t):
    if len(t) < 3 or not t.isalpha():
        return [re.escape(t)]
    fs = {t, t + "s", t + "es", t + "d", t + "ed", t + "ing", t + t[-1] + "ed", t + t[-1] + "ing"}
    if t.endswith("e"):
        fs.add(t[:-1] + "ing")
    if t.endswith("y"):
        fs |= {t[:-1] + "ies", t[:-1] + "ied"}
    fs |= set(IRREGULAR.get(t, "").split())
    return ["(?:" + "|".join(sorted(map(re.escape, fs), key=len, reverse=True)) + ")"]


def phrase_re(p):
    """'take sth into account' -> regex over a sentence, inflections and gaps allowed"""
    rx, gap, words = "", 0, 0
    for tok in re.sub(r"\.{2,}|…", " ... ", p).split():
        tl = tok.lower().strip(",;")
        if not tl:
            continue
        if tl in GAPS:
            gap = max(gap, GAPS[tl]) if rx else 0
            continue
        piece = POSS if tl in ("one's", "sb's") else _forms(tl)[0]
        words += piece != POSS
        rx += (r"\s+" + (r"(?:\S+\s+){0,%d}?" % gap if gap else "") if rx else "") + piece
        gap = 0
    if words < 2:                                   # "sth up" would flag every "up"
        return None
    return re.compile(r"(?<![A-Za-z'’-])" + rx + r"(?![A-Za-z-])", re.I)


def phrase_index(store):
    seen = Counter()
    for ent in store.values():
        for lab in ent["labels"].values():
            for x in (lab if isinstance(lab, list) else [lab]):
                if isinstance(x, str) and x.startswith("P:"):
                    seen[x[2:].strip()] += 1
    out = []
    for p in seen:
        rx = phrase_re(p)
        if rx:
            out.append((p, rx))
    return out


def hints(word, text, spans, phrases):
    hs = []
    for p, rx in phrases:
        for m in rx.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in spans):
                hs.append(p)
                break
    hs = sorted(set(hs), key=len, reverse=True)[:3]
    out = [f"?P:{p}" for p in hs]
    if word != "i":
        for s, _ in spans:
            before = text[:s].rstrip()
            if text[s].isupper() and before and before[-1] not in ".!?:\"“‘(—–-)]":   # J) / [21] / (12) start a sentence
                out.append("?X")
                break
    return out


def b_sample(ent, ctx_sents):
    """-> (Counter of labels over the A/B-labelled sentences, {label: shortest sentence})"""
    text = {sid(s["text"]): s["text"] for s in ctx_sents}
    cnt, ex = Counter(), {}
    for h, lab in ent["labels"].items():
        for x in (lab if isinstance(lab, list) else [lab]):
            cnt[x if isinstance(x, int) else str(x)] += 1
            t = text.get(h)
            k = x if isinstance(x, int) else str(x)
            if t and (k not in ex or len(t) < len(ex[k])):
                ex[k] = t
    return cnt, ex


def mode(ent):
    """-> default sense index for mode 找例外, or None for mode 全标"""
    ints = Counter(l for l in ent["labels"].values() if isinstance(l, int))
    if not ints:
        return None
    top, c = ints.most_common(1)[0]
    return top if c / len(ent["labels"]) >= DOMINANT else None


def modes_file(rnd):
    # frozen at the first render: ingesting C labels later shifts the shares, check() must not follow
    return SC / f"modes_C_{rnd}.json"


def render_task(fin, store, ctx, phrases, modes):
    recs = json.loads(fin.read_text())
    out = [f"# 任务 {fin.stem}：{len(recs)} 个词，{sum(len(r['sents']) for r in recs)} 句。"
           f"按 intermediate/sense_chunks/PROMPT_C.md 标注，写入 {fin.stem}.labels.txt", ""]
    for r in recs:
        w, ent = r["word"], store[r["word"]]
        d = modes.setdefault(w, mode(ent))
        cnt, ex = b_sample(ent, ctx[w]["sents"])
        nb = len(ent["labels"])
        out.append("=" * 60)
        out.append(f"## 词：{w}    本段 {len(r['sents'])} 句    "
                   + (f"模式：找例外（默认义项 {d}：只写不是 {d} 的句子）" if d is not None else "模式：全标（每句都写）"))
        out.append(f"原释义：{r['def']}")
        out.append(f"义项表（下标就是标签；B 样本 = 已标的 {nb} 句里各义项的句数）：")
        for i, s in enumerate(r["senses"]):
            line = f"  {i}  {s['pos']} {s['zh']}    B 样本 {cnt.get(i, 0)}"
            if i in ex:
                line += f"    例：{ex[i]}"
            out.append(line)
        ph = [(k[2:], c) for k, c in cnt.most_common() if isinstance(k, str) and k.startswith("P:")]
        if ph:
            out.append("已标过的短语：" + "；".join(f"{p}（{c}）" for p, c in ph[:40]))
        if cnt.get("X"):
            out.append(f"已标 X：{cnt['X']} 句" + (f"，如：{ex['X']}" if "X" in ex else ""))
        if r.get("notes"):
            out.append("口径说明（照此执行）：")
            out += [f"  - {n}" for n in r["notes"]]
        out.append("句子：")
        rx, lines = word_re(w), []
        for s in r["sents"]:
            t = s["text"]
            spans = [m.span() for m in rx.finditer(t)]
            marked, last = "", 0
            for a, b in spans:
                marked += t[last:a] + "【" + t[a:b] + "】"
                last = b
            marked += t[last:]
            after = t[spans[0][1]:].lower() if spans else t.lower()
            key = re.sub(r"[^a-z' ]", " ", after).split()[:4]
            tail = hints(w, t, spans, phrases) if spans else ["?未找到词形"]
            lines.append((key, s["id"], f"{s['id']} | {marked}" + ("    " + " ".join(tail) if tail else "")))
        out += [l for _, _, l in sorted(lines)]
        out.append("")
    fin.with_suffix(".txt").write_text("\n".join(out))


def render(rnd):
    store, _, _ = load()
    ctx = json.loads((SC / "contexts.json").read_text())
    phrases = phrase_index(store)
    mf = modes_file(rnd)
    modes = json.loads(mf.read_text()) if mf.exists() else {}
    fs = sorted(f for f in SC.glob(f"C_{rnd}_*.json") if not f.name.endswith(".out.json"))
    for fin in fs:
        render_task(fin, store, ctx, phrases, modes)
    mf.write_text(json.dumps(modes, ensure_ascii=False, indent=1))
    ex = [w for w, d in modes.items() if d is not None]
    print(f"{len(fs)} C tasks rendered ({len(phrases)} phrase patterns); 找例外 {len(ex)} words, 全标 {len(modes) - len(ex)}")


def _label(tok, n, m):
    """'0' / 'P:at least' / 'X' / 'N0' -> label, or raise ValueError"""
    tok = tok.strip()
    if re.fullmatch(r"\d+", tok):
        if int(tok) >= n:
            raise ValueError(f"义项下标 {tok} 超出范围（0–{n - 1}）")
        return int(tok)
    if tok == "X":
        return "X"
    if tok.startswith("P:") and tok[2:].strip():
        return "P:" + tok[2:].strip()
    if re.fullmatch(r"N\d+", tok):
        if int(tok[1:]) >= m:
            raise ValueError(f"{tok} 没有在本词段里用 'N{tok[1:]} | 词性 | 中文' 定义")
        return tok
    raise ValueError(f"看不懂的标签 {tok!r}")


def check(name):
    fin = SC / (name if name.endswith(".json") else name + ".json")
    flab = fin.with_name(fin.stem + ".labels.txt")
    if not flab.exists():
        raise SystemExit(f"找不到 {flab.name}")
    modes = json.loads(modes_file(fin.stem.split("_")[1]).read_text())
    recs = {r["word"]: r for r in json.loads(fin.read_text())}
    secs, cur, errs = {}, None, []
    for ln, raw in enumerate(flab.read_text().splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            cur = line[1:].strip()
            if cur not in recs:
                errs.append(f"第 {ln} 行：本任务没有词 {cur!r}")
                cur = None
            elif cur in secs:
                errs.append(f"第 {ln} 行：词 {cur} 出现了两个段")
            else:
                secs[cur] = {"new": [], "note": "", "lines": []}
            continue
        if cur is None:
            errs.append(f"第 {ln} 行：不在任何 '# 词' 段里")
            continue
        sec = secs[cur]
        if re.match(r"N\d+\s*\|", line):
            k, pos, zh = (p.strip() for p in (line.split("|", 2) + ["", ""])[:3])
            if k != f"N{len(sec['new'])}" or not zh:
                errs.append(f"第 {ln} 行：新义项要按 N0、N1… 顺序写成 'N0 | 词性 | 中文'")
            sec["new"].append({"pos": pos, "zh": zh})
        elif line.startswith("note:"):
            sec["note"] = line[5:].strip()
        elif re.match(r"\d+\s", line + " "):
            sec["lines"].append((ln,) + tuple(line.split(None, 1) + [""])[:2])
        else:
            errs.append(f"第 {ln} 行：看不懂 {line[:60]!r}")
    for w in recs:
        if w not in secs:
            errs.append(f"缺少词段 '# {w}'（找例外模式没有例外也要写这一行）")

    out = {}
    for w, sec in secs.items():
        r, d = recs[w], modes[w]
        n, m = len(r["senses"]), len(sec["new"])
        ids = {str(s["id"]) for s in r["sents"]}
        labels = {}
        for ln, i, body in sec["lines"]:
            if i not in ids:
                errs.append(f"第 {ln} 行：{w} 没有句子 {i}")
                continue
            if i in labels:
                errs.append(f"第 {ln} 行：{w} 的句子 {i} 写了两次")
                continue
            try:
                labs = [_label(t, n, m) for t in body.split(";") if t.strip()]
            except ValueError as e:
                errs.append(f"第 {ln} 行：{e}")
                continue
            if not labs:
                errs.append(f"第 {ln} 行：句子 {i} 没写标签")
                continue
            uniq = list(dict.fromkeys(labs))
            labels[i] = uniq[0] if len(uniq) == 1 else uniq
        missing = sorted(ids - set(labels), key=int)
        if d is None and missing:
            errs.append(f"{w} 是全标模式，还有 {len(missing)} 句没标：{' '.join(missing[:30])}"
                        + (" …" if len(missing) > 30 else ""))
        for i in missing:
            labels[i] = d
        out[w] = {"labels": labels, "new_senses": sec["new"], "note": sec["note"]}
    if errs:
        print(f"{flab.name} 有 {len(errs)} 处问题，未生成 {fin.stem}.out.json：")
        print("\n".join("  " + e for e in errs[:60]))
        raise SystemExit(1)
    fout = fin.with_name(fin.stem + ".out.json")
    fout.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    why = store_check(fin)
    if why:
        fout.unlink()
        raise SystemExit(f"内部校验失败（{why}），未生成 out 文件")
    print(f"通过：写出 {fout.name}")
    for w, a in out.items():
        c = Counter(str(x) for l in a["labels"].values() for x in (l if isinstance(l, list) else [l]))
        print(f"  {w}（{len(a['labels'])} 句）：" + "，".join(f"{k}×{v}" for k, v in c.most_common(12)))


def ctx_of(name, word, i):
    fin = SC / (name if name.endswith(".json") else name + ".json")
    r = next((r for r in json.loads(fin.read_text()) if r["word"] == word), None)
    s = r and next((s for s in r["sents"] if str(s["id"]) == str(i)), None)
    if not s:
        raise SystemExit(f"{fin.stem} 里没有 {word} 的句子 {i}")
    src = s["src"]
    f = (ROOT / "corpus" / "listening" / (src.replace("·听力", "") + "_ans.txt")) if "·听力" in src \
        else ROOT / "corpus" / "papers" / (src + ".txt")
    flat = " ".join(f.read_text().split())
    head = " ".join(s["text"].split()[:8])
    k = flat.find(head)
    print(f"[{f.relative_to(ROOT)}]")
    print(flat[max(0, k - 700):k + len(s["text"]) + 700] if k >= 0 else f"原卷里没找到这句的开头：{head}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["render"] and len(a) == 2:
        render(a[1])
    elif a[:1] == ["check"] and len(a) == 2:
        check(a[1])
    elif a[:1] == ["ctx"] and len(a) == 4:
        ctx_of(*a[1:])
    else:
        raise SystemExit(__doc__)

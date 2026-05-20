"""Parse all formatted entries (30 hand-written + DeepSeek batches) into
structured records, then render the final vocabulary tables.

Outputs:
  high_freq_cet4_v2.txt   — v2-A: full 1250, all DeepSeek/hand formatted
  intermediate/entries_v2.json    — structured records for downstream use (v2-B)
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

HEADWORD_RE = re.compile(r"^[A-Za-z][A-Za-z'\- ]*$")


def split_blocks(text: str) -> list[str]:
    """Structural split: entry = headword line + a following 英[ line."""
    lines = text.splitlines()
    starts = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("-") or "英[" in s or ":" in s or "：" in s:
            continue
        if not HEADWORD_RE.match(s):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and lines[j].strip().startswith("英["):
            starts.append(i)
    blocks = []
    for k, st in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        block = "\n".join(lines[st:end]).strip()
        block = re.sub(r"\n\s*-{3,}\s*$", "", block).strip()
        if block:
            blocks.append(block)
    return blocks


def parse_entry(block: str) -> dict:
    """Parse one entry block into structured fields."""
    lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
    rec = {"word": lines[0].strip().lower(), "uk": "", "us": "",
           "freq": "", "def": "", "forms": "", "ex_label": "例句",
           "ex_text": "", "raw": block}
    body = "\n".join(lines[1:])
    m = re.search(r"英\[([^\]]*)\]", body)
    if m:
        rec["uk"] = m.group(1).strip()
    m = re.search(r"美\[([^\]]*)\]", body)
    if m:
        rec["us"] = m.group(1).strip()
    m = re.search(r"词频[:：]\s*(\d+)", body)
    if m:
        rec["freq"] = m.group(1)
    m = re.search(r"释义[:：]\s*(.*?)(?=\n(变形|例句|英\[)|\Z)", body, re.S)
    if m:
        rec["def"] = " ".join(m.group(1).split())
    m = re.search(r"变形[:：]\s*(.*?)(?=\n(例句|英\[)|\Z)", body, re.S)
    if m:
        rec["forms"] = " ".join(m.group(1).split())
    m = re.search(r"例句(（自编）|\(自编\))?[:：]\s*(.*?)\Z", body, re.S)
    if m:
        rec["ex_label"] = "例句（自编）" if m.group(1) else "例句"
        rec["ex_text"] = " ".join(m.group(2).split())
    return rec


def render_entry(rec: dict) -> str:
    out = [rec["word"]]
    out.append(f"英[{rec['uk']}]  美[{rec['us']}]")
    out.append(f"词频: {rec['freq']} 次")
    out.append(f"释义: {rec['def']}")
    if rec["forms"]:
        out.append(f"变形: {rec['forms']}")
    out.append(f"{rec['ex_label']}: {rec['ex_text']}")
    return "\n".join(out)


def main():
    batch_dir = ROOT / "intermediate" / (sys.argv[1] if len(sys.argv) > 1 else "ds_batches")
    out_name = sys.argv[2] if len(sys.argv) > 2 else "high_freq_cet4_v2.txt"

    rows = list(csv.DictReader((OUT / "high_freq_surface.csv").open()))[:1250]
    rank_of = {r["word"]: int(r["rank"]) for r in rows}

    records: dict[str, dict] = {}

    # 30 hand-written
    for b in re.split(r"\n\s*\n", (Path(__file__).parent / "examples_30_template.txt").read_text()):
        if b.strip():
            rec = parse_entry(b.strip())
            records[rec["word"]] = rec
    n_hand = len(records)

    # DeepSeek batches
    for f in sorted(batch_dir.glob("batch_*.txt")):
        for b in split_blocks(f.read_text()):
            rec = parse_entry(b)
            if rec["word"] not in records:
                records[rec["word"]] = rec
    print(f"hand-written: {n_hand}, total parsed: {len(records)}")

    missing = [r["word"] for r in rows if r["word"] not in records]
    if missing:
        print(f"!! MISSING {len(missing)}: {missing[:30]}")

    ordered = sorted((rank_of[w], records[w]) for w in records if w in rank_of)

    # structured json
    (ROOT / "intermediate" / "entries_v2.json").write_text(json.dumps(
        {str(rank): rec for rank, rec in ordered}, ensure_ascii=False, indent=1))

    # v2-A text
    selfmade = sum(1 for _, r in ordered if r["ex_label"].startswith("例句（自编"))
    lines = ["英语四级真题高频词汇（2021-2025 · 词形原样版）",
             f"共 {len(ordered)} 词，按真题出现频次排序",
             f"例句来源：真题原句 {len(ordered)-selfmade} 条 / DeepSeek 自编 {selfmade} 条",
             "=" * 42]
    for i, (rank, rec) in enumerate(ordered):
        if i % 50 == 0:
            lines.append(f"\n———— Section {i // 50 + 1} ————\n")
        lines.append(f"[{rank}] {render_entry(rec)}\n")
    (OUT / out_name).write_text("\n".join(lines))
    print(f"-> {out_name} ({len(ordered)} entries, "
          f"{selfmade} self-composed examples)")


if __name__ == "__main__":
    main()

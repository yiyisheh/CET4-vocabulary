"""v2-B: reuse liut969's dictionary data (音标/释义/变形) for words that
overlap with his list; keep our frequency + our example sentence.
Words unique to our 2021-2025 list keep the DeepSeek entry.

Outputs:
  high_freq_cet4_v2b.txt         — v2-B
  high_freq_cet4_v2b_marked.txt  — v2-B with our-unique words marked ★
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
from assemble_final import render_entry

entries = json.loads((ROOT / "intermediate" / "entries_v2.json").read_text())
liut = json.loads((ROOT / "intermediate" / "liut969_dict.json").read_text())


def main():
    ordered = sorted(entries.items(), key=lambda kv: int(kv[0]))
    n_reuse = n_unique = 0

    plain, marked = [], []
    header = ["英语四级真题高频词汇（2021-2025）",
              f"共 {len(ordered)} 词，按真题出现频次排序",
              "音标/释义/变形：重合词复用 liut969 词典；★ = 本表独有的新高频词",
              "=" * 42]
    plain += header
    marked += header

    for i, (rank, rec) in enumerate(ordered):
        word = rec["word"]
        rec_b = dict(rec)
        if word in liut:
            d = liut[word]
            # reuse his dictionary fields when present
            rec_b["uk"] = d["uk"] or rec["uk"]
            rec_b["us"] = d["us"] or rec["us"]
            rec_b["def"] = d["def"] or rec["def"]
            rec_b["forms"] = d["forms"] or rec["forms"]
            n_reuse += 1
            mark = ""
        else:
            n_unique += 1
            mark = " ★"

        if i % 50 == 0:
            sec = f"\n———— Section {i // 50 + 1} ————\n"
            plain.append(sec)
            marked.append(sec)
        body = render_entry(rec_b)
        plain.append(f"[{rank}] {body}\n")
        marked.append(f"[{rank}]{mark} {body}\n")

    (OUT / "high_freq_cet4_v2b.txt").write_text("\n".join(plain))
    (OUT / "high_freq_cet4_v2b_marked.txt").write_text("\n".join(marked))
    print(f"reused liut969 dict: {n_reuse} words")
    print(f"our-unique (new) words: {n_unique}")
    print("-> high_freq_cet4_v2b.txt")
    print("-> high_freq_cet4_v2b_marked.txt")


if __name__ == "__main__":
    main()

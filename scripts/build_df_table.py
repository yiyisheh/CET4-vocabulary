"""Build the document-frequency (DF) ordered vocabulary book.

Reuses the formatted entries from the TF table (entries_v2.json); generates
DeepSeek entries only for DF-top-1250 words not already covered.
Ordered by DF rank; the 词频 line shows both document and term frequency.
"""
import csv
import concurrent.futures
import json
import re
from pathlib import Path

from deepseek_format import call_deepseek, build_user_msg, BATCH
from assemble_final import split_blocks, parse_entry, render_entry

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
DF_BATCH_DIR = ROOT / "intermediate" / "ds_batches_df"
DF_BATCH_DIR.mkdir(parents=True, exist_ok=True)
TOP_N = 1250


def main():
    df_rows = list(csv.DictReader((OUT / "high_freq_surface_df.csv").open()))[:TOP_N]
    examples = json.loads((ROOT / "intermediate" / "examples.json").read_text())
    entries = {rec["word"]: rec
               for rec in json.loads((ROOT / "intermediate" / "entries_v2.json").read_text()).values()}

    missing = [r for r in df_rows if r["word"] not in entries]
    print(f"DF top-{TOP_N}: reuse {len(df_rows)-len(missing)}, "
          f"generate {len(missing)}")

    # generate missing entries via DeepSeek
    todo = [(int(r["rank"]), r["word"], int(r["term_freq"]),
             examples.get(r["word"], "")) for r in missing]
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]

    def run(idx_batch):
        idx, batch = idx_batch
        out = DF_BATCH_DIR / f"batch_{idx:03d}.txt"
        if out.exists() and out.stat().st_size > 40:
            return idx, "cached"
        out.write_text(call_deepseek(build_user_msg(batch)))
        return idx, "done"

    if batches:
        if not (DF_BATCH_DIR / "batch_000.txt").exists():
            run((0, batches[0]))
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            for idx, status in ex.map(run, list(enumerate(batches))):
                print(f"  df batch {idx:03d}: {status}")

    for f in sorted(DF_BATCH_DIR.glob("batch_*.txt")):
        for b in split_blocks(f.read_text()):
            rec = parse_entry(b)
            entries.setdefault(rec["word"], rec)

    # render DF-ordered table
    selfmade = 0
    lines = ["英语四级真题高频词汇（2021-2025 · 文档频率 DF 排序版）",
             f"共 {len(df_rows)} 词，按"
             "『出现在多少套真题中』排序（31 套完整真题）",
             "词频行：见于 D/31 套 · 全部真题中共出现 T 次",
             "=" * 44]
    for i, r in enumerate(df_rows):
        word, dfreq, tfreq = r["word"], r["doc_freq"], r["term_freq"]
        rec = dict(entries[word])
        rec_lines = render_entry(rec).splitlines()
        # replace the 词频 line with DF + TF info
        rec_lines[2] = f"词频: 见于 {dfreq}/31 套真题，共 {tfreq} 次"
        if rec["ex_label"].startswith("例句（自编"):
            selfmade += 1
        if i % 50 == 0:
            lines.append(f"\n———— Section {i // 50 + 1} ————\n")
        lines.append(f"[{r['rank']}] " + "\n".join(rec_lines) + "\n")

    out = OUT / "high_freq_cet4_df.txt"
    out.write_text("\n".join(lines))
    print(f"-> {out} ({len(df_rows)} entries, {selfmade} self-composed examples)")


if __name__ == "__main__":
    main()

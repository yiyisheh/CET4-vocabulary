"""Validation: does the global 80%-cutoff high-frequency list also cover
~80% of EACH individual exam paper?

For each corpus file, compute coverage = (tokens whose word is in the global
high-freq list) / (total tokens in that file). Done for both the lemma list
and the surface list. Output a bar chart + stats.
"""
import csv
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import spacy

from build_frequency import clean, cumulative_cutoff, DROP_POS, WORD_RE

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
CORPUS = ROOT / "corpus"


def load_topset(path: Path, n: int) -> set[str]:
    rows = list(csv.DictReader(path.open()))
    return {r["word"] for r in rows[:n]}


def file_tokens(nlp, text: str) -> tuple[list[str], list[str]]:
    """Return (surface_tokens, lemma_tokens) for one file."""
    doc = nlp(clean(text))
    surf, lem = [], []
    for tok in doc:
        if tok.pos_ in DROP_POS:
            continue
        s, l = tok.text.lower(), tok.lemma_.lower()
        if WORD_RE.match(s):
            surf.append(s)
        if WORD_RE.match(l):
            lem.append(l)
    return surf, lem


def main():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    nlp.max_length = 8_000_000

    # Global cutoffs (recompute to stay in sync with the CSVs)
    lemma_rows = list(csv.DictReader((OUT / "high_freq_lemma.csv").open()))
    surf_rows = list(csv.DictReader((OUT / "high_freq_surface.csv").open()))
    lemma_counter = Counter({r["word"]: int(r["count"]) for r in lemma_rows})
    surf_counter = Counter({r["word"]: int(r["count"]) for r in surf_rows})
    lemma_cut = cumulative_cutoff(lemma_counter)
    surf_cut = cumulative_cutoff(surf_counter)
    lemma_top = set(list(lemma_counter)[:lemma_cut])
    surf_top = set(list(surf_counter)[:surf_cut])
    print(f"Global 80% lists: lemma top-{lemma_cut}, surface top-{surf_cut}")

    files = sorted(CORPUS.glob("papers/*.txt")) + sorted(CORPUS.glob("listening/*.txt"))
    names, lemma_cov, surf_cov, kinds = [], [], [], []
    for f in files:
        text = f.read_text()
        if len(text.strip()) < 200:
            continue  # skip dedup-stub files
        surf, lem = file_tokens(nlp, text)
        if not surf or not lem:
            continue
        l_c = sum(1 for t in lem if t in lemma_top) / len(lem)
        s_c = sum(1 for t in surf if t in surf_top) / len(surf)
        name = f.stem.replace("cet4_", "").replace("_ans", "*")
        names.append(name)
        lemma_cov.append(l_c * 100)
        surf_cov.append(s_c * 100)
        kinds.append("listening" if f.parent.name == "listening" else "paper")
        print(f"  {name:<16} {f.parent.name:<10} lemma={l_c:.1%}  surface={s_c:.1%}")

    def stats(label, vals):
        print(f"{label}: mean={sum(vals)/len(vals):.1f}%  "
              f"min={min(vals):.1f}%  max={max(vals):.1f}%")
    print()
    stats("Lemma coverage  ", lemma_cov)
    stats("Surface coverage", surf_cov)

    # Chart
    x = range(len(names))
    fig, ax = plt.subplots(figsize=(16, 7))
    w = 0.4
    ax.bar([i - w / 2 for i in x], lemma_cov, w, label=f"Lemma (top-{lemma_cut})",
           color="#2a7fb8")
    ax.bar([i + w / 2 for i in x], surf_cov, w, label=f"Surface (top-{surf_cut})",
           color="#e08a3c")
    ax.axhline(80, color="red", ls="--", lw=1, label="80% (global target)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=90, fontsize=7)
    ax.set_ylabel("Coverage of this file's tokens (%)")
    ax.set_title("Per-paper coverage by the global 80%-cutoff high-frequency list\n"
                 "(* = listening transcript file)")
    ax.legend()
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT / "coverage_chart.png"
    fig.savefig(out, dpi=130)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()

"""Compare TF-ranked vs DF-ranked high-frequency lists.

For each corpus file, measure what fraction of its tokens are covered by:
  - the TF (term-frequency) top-N list
  - the DF (document-frequency) top-N list
using the same N for a fair comparison. Two panels: lemma and surface.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import spacy

from build_frequency import clean, cumulative_cutoff, DROP_POS, WORD_RE
from collections import Counter

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
CORPUS = ROOT / "corpus"
FIX = {"ca": "can", "wo": "will", "n't": "not", "sha": "shall"}


def top_words(path: Path, n: int, col: str = "word") -> list[str]:
    return [r[col] for r in list(csv.DictReader(path.open()))[:n]]


def file_tokens(nlp, text):
    doc = nlp(clean(text))
    surf, lem = [], []
    for tok in doc:
        if tok.pos_ in DROP_POS:
            continue
        s = FIX.get(tok.text.lower(), tok.text.lower())
        l = tok.lemma_.lower()
        if WORD_RE.match(s):
            surf.append(s)
        if WORD_RE.match(l):
            lem.append(l)
    return surf, lem


def main():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    nlp.max_length = 8_000_000

    # N = TF 80% cutoff for each version
    tf_lemma = list(csv.DictReader((OUT / "high_freq_lemma.csv").open()))
    tf_surf = list(csv.DictReader((OUT / "high_freq_surface.csv").open()))
    n_lemma = cumulative_cutoff(Counter({r["word"]: int(r["count"]) for r in tf_lemma}))
    n_surf = cumulative_cutoff(Counter({r["word"]: int(r["count"]) for r in tf_surf}))
    print(f"list size N: lemma={n_lemma}, surface={n_surf}")

    tf_lemma_set = set(top_words(OUT / "high_freq_lemma.csv", n_lemma))
    tf_surf_set = set(top_words(OUT / "high_freq_surface.csv", n_surf))
    df_lemma_set = set(top_words(OUT / "high_freq_lemma_df.csv", n_lemma))
    df_surf_set = set(top_words(OUT / "high_freq_surface_df.csv", n_surf))

    print(f"TF vs DF top-{n_lemma} (lemma):   "
          f"overlap {len(tf_lemma_set & df_lemma_set)} "
          f"({len(tf_lemma_set & df_lemma_set)/n_lemma:.1%})")
    print(f"TF vs DF top-{n_surf} (surface): "
          f"overlap {len(tf_surf_set & df_surf_set)} "
          f"({len(tf_surf_set & df_surf_set)/n_surf:.1%})")

    files = sorted(CORPUS.glob("papers/*.txt")) + sorted(CORPUS.glob("listening/*.txt"))
    names = []
    cov = {"lemma_tf": [], "lemma_df": [], "surf_tf": [], "surf_df": []}
    for f in files:
        text = f.read_text()
        if len(text.strip()) < 3000:        # skip dedup stubs
            continue
        surf, lem = file_tokens(nlp, text)
        if not surf or not lem:
            continue
        names.append(f.stem.replace("cet4_", "").replace("_ans", "*"))
        cov["lemma_tf"].append(100 * sum(t in tf_lemma_set for t in lem) / len(lem))
        cov["lemma_df"].append(100 * sum(t in df_lemma_set for t in lem) / len(lem))
        cov["surf_tf"].append(100 * sum(t in tf_surf_set for t in surf) / len(surf))
        cov["surf_df"].append(100 * sum(t in df_surf_set for t in surf) / len(surf))

    def mean(v):
        return sum(v) / len(v)
    print(f"\nLemma   coverage: TF mean={mean(cov['lemma_tf']):.1f}%  "
          f"DF mean={mean(cov['lemma_df']):.1f}%")
    print(f"Surface coverage: TF mean={mean(cov['surf_tf']):.1f}%  "
          f"DF mean={mean(cov['surf_df']):.1f}%")

    x = range(len(names))
    fig, axes = plt.subplots(2, 1, figsize=(17, 12))
    for ax, (lab, tf_k, df_k, n) in zip(axes, [
            ("Lemma version (lemmatized)", "lemma_tf", "lemma_df", n_lemma),
            ("Surface version (raw forms)", "surf_tf", "surf_df", n_surf)]):
        w = 0.4
        ax.bar([i - w / 2 for i in x], cov[tf_k], w,
               label=f"TF top-{n} (term frequency)", color="#2a7fb8")
        ax.bar([i + w / 2 for i in x], cov[df_k], w,
               label=f"DF top-{n} (document frequency)", color="#5cb85c")
        ax.axhline(80, color="red", ls="--", lw=1)
        ax.set_xticks(list(x))
        ax.set_xticklabels(names, rotation=90, fontsize=7)
        ax.set_ylabel("Coverage of file tokens (%)")
        ax.set_title(f"{lab}: per-paper coverage, TF-ranked vs DF-ranked list")
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT / "coverage_tf_vs_df.png"
    fig.savefig(out, dpi=120)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

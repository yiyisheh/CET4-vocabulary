"""Document-frequency (DF) version of the high-frequency lists.

Instead of counting every occurrence (term frequency, TF), count how many
distinct exam SETS each word appears in. One exam set = one 真题 paper plus
its listening transcript, combined; 34 sets total (2021-2025).

A word that appears 10x in one paper contributes 1 to its DF, not 10.
Ranking: DF descending, ties broken by TF descending.

Outputs: high_freq_lemma_df.csv, high_freq_surface_df.csv
         columns: rank, word, doc_freq, term_freq
"""
import csv
from collections import Counter
from pathlib import Path

import spacy

from build_frequency import clean, WORD_RE, DROP_POS, ROMAN_JUNK

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
CORPUS = ROOT / "corpus"
FIX = {"ca": "can", "wo": "will", "n't": "not", "sha": "shall"}


def set_key(path: Path) -> str:
    """papers/cet4_2022_06_1.txt & listening/cet4_2022_06_1_ans.txt -> 2022_06_1"""
    return path.stem.replace("cet4_", "").replace("_ans", "")


def main():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    nlp.max_length = 8_000_000

    # group corpus files into exam sets
    sets: dict[str, list[Path]] = {}
    for sub in ("papers", "listening"):
        for f in sorted((CORPUS / sub).glob("*.txt")):
            sets.setdefault(set_key(f), []).append(f)
    print(f"exam sets: {len(sets)}")

    lemma_df: Counter[str] = Counter()
    surface_df: Counter[str] = Counter()
    lemma_tf: Counter[str] = Counter()
    surface_tf: Counter[str] = Counter()

    # exclude publisher-deduplicated stub sets (only a writing prompt, no
    # listening/reading) — they are not representative full papers.
    full_sets = {k: v for k, v in sets.items()
                 if sum(len(f.read_text()) for f in v) >= 3000}
    skipped = sorted(set(sets) - set(full_sets))
    print(f"full sets used: {len(full_sets)}  (skipped stubs: {skipped})")
    sets = full_sets

    for key, files in sorted(sets.items()):
        text = clean("\n".join(f.read_text() for f in files))
        doc = nlp(text)
        seen_lemma, seen_surface = set(), set()
        for tok in doc:
            if tok.pos_ in DROP_POS:
                continue
            surf = FIX.get(tok.text.lower(), tok.text.lower())
            lem = tok.lemma_.lower()
            if WORD_RE.match(surf) and surf not in ROMAN_JUNK:
                surface_tf[surf] += 1
                seen_surface.add(surf)
            if WORD_RE.match(lem) and lem not in ROMAN_JUNK:
                lemma_tf[lem] += 1
                seen_lemma.add(lem)
        for w in seen_lemma:
            lemma_df[w] += 1
        for w in seen_surface:
            surface_df[w] += 1

    n_sets = len(sets)

    def write(path, df, tf):
        ordered = sorted(df.items(), key=lambda kv: (-kv[1], -tf[kv[0]], kv[0]))
        with path.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rank", "word", "doc_freq", "term_freq"])
            for i, (word, d) in enumerate(ordered, 1):
                w.writerow([i, word, d, tf[word]])
        full = [w for w, d in ordered if d == n_sets]
        print(f"  {path.name}: {len(ordered)} words, "
              f"{len(full)} appear in all {n_sets} sets")
        return ordered

    print("Document-frequency lists:")
    write(OUT / "high_freq_lemma_df.csv", lemma_df, lemma_tf)
    write(OUT / "high_freq_surface_df.csv", surface_df, surface_tf)


if __name__ == "__main__":
    main()

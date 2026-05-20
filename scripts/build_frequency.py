"""Build CET-4 high-frequency word lists from the OCR'd corpus.

Produces two rankings (no stopword filter — function words kept, per the
reference list's philosophy):
  - high_freq_lemma.csv   : words merged by lemma (studies/studied -> study)
  - high_freq_surface.csv : raw surface forms (liut969-style: is/are/be separate)

Both drop punctuation / numbers / symbols and option markers (A) B) C) D)).
"""
import csv
import re
from collections import Counter
from pathlib import Path

import spacy

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
CORPUS = ROOT / "corpus"

# A valid word token: 2+ letters with optional internal ' or - (don't, well-known),
# or the single-letter real words "a" / "i".
WORD_RE = re.compile(r"^[a-z][a-z'-]*[a-z]$|^[ai]$")

OPTION_MARK = re.compile(r"(?:^|\s)[A-D][\)\.]")
Q_NUM = re.compile(r"^\s*\d+\.\s*", flags=re.MULTILINE)
BRACKET_NUM = re.compile(r"\[\d+\]|\(\d+(?:-\d+)?\)")  # (1) (3-1) [12]
PART_IV = re.compile(r"Part\s+IV.*$", re.DOTALL | re.IGNORECASE)
CURLY = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
DROP_POS = {"PUNCT", "SPACE", "SYM", "NUM", "X"}
# Roman-numeral artifacts from "Part II / Part III" headers — not real words.
ROMAN_JUNK = {"ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii"}


def clean(text: str) -> str:
    text = text.translate(CURLY)
    text = PART_IV.sub("", text)
    text = OPTION_MARK.sub(" ", text)
    text = BRACKET_NUM.sub(" ", text)
    text = Q_NUM.sub("", text)
    return text


def load_corpus() -> str:
    parts: list[str] = []
    for sub in ("papers", "listening"):
        for f in sorted((CORPUS / sub).glob("*.txt")):
            parts.append(clean(f.read_text()))
    return "\n\n".join(parts)


def cumulative_cutoff(counter: Counter, ratio: float = 0.80) -> int:
    total = sum(counter.values())
    run = 0
    for i, (_, c) in enumerate(counter.most_common(), 1):
        run += c
        if run / total >= ratio:
            return i
    return len(counter)


def write_csv(path: Path, counter: Counter) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "word", "count"])
        for i, (word, c) in enumerate(counter.most_common(), 1):
            w.writerow([i, word, c])


def main():
    print("Loading spaCy ...")
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    nlp.max_length = 8_000_000

    text = load_corpus()
    print(f"Corpus: {len(text):,} chars")

    # spaCy splits contractions: can't -> ca + n't, won't -> wo + n't.
    # Normalize those fragments back to real words for surface counting.
    fix = {"ca": "can", "wo": "will", "n't": "not", "sha": "shall"}

    doc = nlp(text)
    lemma_c: Counter[str] = Counter()
    surface_c: Counter[str] = Counter()
    for tok in doc:
        if tok.pos_ in DROP_POS:
            continue
        surface = fix.get(tok.text.lower(), tok.text.lower())
        lemma = tok.lemma_.lower()
        if WORD_RE.match(surface) and surface not in ROMAN_JUNK:
            surface_c[surface] += 1
        if WORD_RE.match(lemma) and lemma not in ROMAN_JUNK:
            lemma_c[lemma] += 1

    print(f"\nLemma counting:   {len(lemma_c):,} unique, "
          f"{sum(lemma_c.values()):,} tokens, "
          f"80% cutoff = top-{cumulative_cutoff(lemma_c)}")
    print(f"Surface counting: {len(surface_c):,} unique, "
          f"{sum(surface_c.values()):,} tokens, "
          f"80% cutoff = top-{cumulative_cutoff(surface_c)}")

    write_csv(OUT / "high_freq_lemma.csv", lemma_c)
    write_csv(OUT / "high_freq_surface.csv", surface_c)
    print("\n-> high_freq_lemma.csv")
    print("-> high_freq_surface.csv")

    print("\nTop 25 (lemma):")
    for i, (w, c) in enumerate(lemma_c.most_common(25), 1):
        print(f"  {i:2}. {w:<14} {c}")


if __name__ == "__main__":
    main()

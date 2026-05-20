"""For each top-N surface word, pick one example sentence from the corpus.

Preference: a complete sentence containing the exact word, 8-22 words long,
mostly ASCII, no leftover option markers.
"""
import csv
import json
import re
from pathlib import Path

import spacy

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
CORPUS = ROOT / "corpus"
from build_frequency import clean

TOP_N = 1250


OPTION_FRAG = re.compile(r"\b[A-O]\)")


def good_sentence(s: str) -> bool:
    n = len(s.split())
    if not (7 <= n <= 24):
        return False
    if any("一" <= c <= "鿿" for c in s):
        return False
    if not s[0].isupper():
        return False
    if any(c.isdigit() for c in s):        # drop question-number leftovers
        return False
    if OPTION_FRAG.search(s):              # drop leftover option markers (N) etc.)
        return False
    if not s.rstrip().endswith((".", "!", "?")):
        return False
    return True


def main():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer", "tagger"])
    nlp.add_pipe("sentencizer")
    nlp.max_length = 8_000_000

    text = clean("\n".join(
        f.read_text() for sub in ("papers", "listening")
        for f in sorted((CORPUS / sub).glob("*.txt"))
    ))
    doc = nlp(text)
    sentences = []
    for sent in doc.sents:
        s = " ".join(sent.text.split())
        if good_sentence(s):
            sentences.append(s)
    print(f"clean sentences: {len(sentences)}")

    # targets = union of TF top-1250 and DF top-1250 (surface)
    tf = [r["word"] for r in list(csv.DictReader(
        (OUT / "high_freq_surface.csv").open()))[:TOP_N]]
    df_path = OUT / "high_freq_surface_df.csv"
    df = ([r["word"] for r in list(csv.DictReader(df_path.open()))[:TOP_N]]
          if df_path.exists() else [])
    targets = list(dict.fromkeys(tf + df))
    tset = set(targets)

    word_sents: dict[str, list[str]] = {w: [] for w in targets}
    for s in sentences:
        toks = set(re.findall(r"[a-z']+", s.lower()))
        for w in toks & tset:
            if len(word_sents[w]) < 6:
                word_sents[w].append(s)

    # pick the shortest available sentence per word
    chosen = {}
    missing = []
    for w in targets:
        cands = word_sents[w]
        if cands:
            chosen[w] = min(cands, key=len)
        else:
            missing.append(w)
            chosen[w] = ""
    print(f"words with example: {sum(1 for v in chosen.values() if v)}/{len(targets)}")
    print(f"missing: {len(missing)} -> {missing[:20]}")

    (ROOT / "intermediate" / "examples.json").write_text(
        json.dumps(chosen, ensure_ascii=False, indent=1))
    print("-> intermediate/examples.json")


if __name__ == "__main__":
    main()

"""The ONE place that decides which exam papers are "in" (corpus/window.json).

Every script that reads corpus/ goes through files(): adding 2026 / dropping an
old year is a one-line edit of window.json, not a code change.
Paper files are named cet4_YYYY_MM_N[_ans].txt (listening transcripts carry _ans).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
YEARS = set(json.loads((CORPUS / "window.json").read_text())["years"])
_YEAR = re.compile(r"cet4_(\d{4})_")


def year(path) -> int:
    m = _YEAR.match(Path(path).name)
    if not m:
        raise ValueError(f"unexpected corpus file name: {path}")
    return int(m.group(1))


def files(sub):
    """sorted corpus/<sub>/*.txt inside the window (sub = "papers" | "listening")"""
    return [f for f in sorted((CORPUS / sub).glob("*.txt")) if year(f) in YEARS]

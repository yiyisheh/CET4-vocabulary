"""Inline dataset + EMBEDDED offline audio into web/template.html.

Produces a single self-contained 英语四级单词背诵.html:
  - __DATA__      : the 1250 entries (word/ipa/def/example/root/syllables)
  - __AUDIO_US__  : {word: base64 mp3}  US pronunciation (Youdao), fully offline
  - __AUDIO_UK__  : {word: base64 mp3}  UK pronunciation

Audio is stored as JSON inside <script type="application/json"> blocks (not executed;
parsed lazily by the app), so the reader stays interactive. Large file by design —
the whole thing works with no network.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = json.loads((ROOT / "intermediate" / "entries_full.json").read_text())
AUD = ROOT / "intermediate" / "audio"
TPL = (ROOT / "web" / "template.html").read_text()
OUT = ROOT / "英语四级单词背诵.html"

slim = [{
    "rank": e["rank"], "word": e["word"], "syl": e["syl"],
    "uk": e["uk"], "us": e["us"], "def": e["def"],
    "ex_label": e["ex_label"], "ex": e["ex"], "root": e["root"],
} for e in DATA]


def audio_json(accent):
    out = {}
    d = AUD / accent
    for e in DATA:
        f = d / f"{e['rank']}.mp3"
        if f.exists() and f.stat().st_size > 500:
            out[e["word"]] = base64.b64encode(f.read_bytes()).decode("ascii")
    return json.dumps(out, ensure_ascii=False, separators=(",", ":")), len(out)


us_json, n_us = audio_json("us")
uk_json, n_uk = audio_json("uk")

# multi-device sync config: web/supabase-config.json if present, else null (sync disabled)
cfg_path = ROOT / "web" / "supabase-config.json"
sync_config = cfg_path.read_text().strip() if cfg_path.exists() else "null"

html = (TPL
        .replace("__DATA__", json.dumps(slim, ensure_ascii=False, separators=(",", ":")))
        .replace("__AUDIO_US__", us_json)
        .replace("__AUDIO_UK__", uk_json)
        .replace("__SYNC_CONFIG__", sync_config))
OUT.write_text(html)
print(f"-> {OUT}  ({OUT.stat().st_size//1024//1024} MB, {len(slim)} entries, "
      f"audio US={n_us} UK={n_uk})")

# also emit the hosted PWA copy into docs/ (GitHub Pages source)
import shutil
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)
(DOCS / "index.html").write_text(html)
for f in (ROOT / "web" / "pwa").iterdir():
    shutil.copy2(f, DOCS / f.name)
print(f"-> {DOCS}/  (index.html + PWA: manifest, sw.js, icons)")


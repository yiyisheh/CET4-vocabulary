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


def audio_ex_json():
    """Example-sentence clips (edge-tts, one male voice each), keyed by rank."""
    out = {}
    d = AUD / "ex"
    for e in DATA:
        f = d / f"{e['rank']}.mp3"
        if f.exists() and f.stat().st_size > 300:
            out[str(e["rank"])] = base64.b64encode(f.read_bytes()).decode("ascii")
    return json.dumps(out, ensure_ascii=False, separators=(",", ":")), len(out)


us_json, n_us = audio_json("us")
ex_json, n_ex = audio_ex_json()
# UK dropped: US-only keeps the page light enough for iPad WebKit (89MB page killed the tab).

# multi-device sync config: web/supabase-config.json if present, else null (sync disabled)
cfg_path = ROOT / "web" / "supabase-config.json"
sync_config = cfg_path.read_text().strip() if cfg_path.exists() else "null"

import hashlib
import shutil
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

# expected offline-package size (bytes) for the settings-page cache-progress readout:
# everything the service worker precaches = index.html + manifest + 3 icons.
PWA_DIR = ROOT / "web" / "pwa"
assets_bytes = sum((PWA_DIR / n).stat().st_size for n in
                   ("manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png"))

html = (TPL
        .replace("__DATA__", json.dumps(slim, ensure_ascii=False, separators=(",", ":")))
        .replace("__AUDIO_US__", us_json)
        .replace("__AUDIO_EX__", ex_json)
        .replace("__SYNC_CONFIG__", sync_config))
# CACHE_BYTES depends on the final html length; html length doesn't depend on it (fixed-width
# is unnecessary — the JS just reads whatever number is here), so inject after building the body.
cache_bytes = len(html.encode()) + assets_bytes
html = html.replace("__CACHE_BYTES__", str(cache_bytes))

OUT.write_text(html)
print(f"-> {OUT}  ({OUT.stat().st_size//1024//1024} MB, {len(slim)} entries, "
      f"audio US={n_us} EX={n_ex}, cache≈{cache_bytes//1024//1024} MB)")

# also emit the hosted PWA copy into docs/ (GitHub Pages source)
(DOCS / "index.html").write_text(html)

# content hash of the built app -> sw.js CACHE name, so the service worker's bytes
# change (and clients auto-update) exactly when the app changes, no manual version bump.
build_hash = hashlib.sha256(html.encode()).hexdigest()[:12]
for f in (ROOT / "web" / "pwa").iterdir():
    if f.name == "sw.js":
        (DOCS / f.name).write_text(f.read_text().replace("__BUILD__", build_hash))
    else:
        shutil.copy2(f, DOCS / f.name)
print(f"-> {DOCS}/  (index.html + PWA: manifest, sw.js@{build_hash}, icons)")


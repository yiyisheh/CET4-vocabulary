"""Build the two shipping shapes of the app from web/template.html.

1) SINGLE FILE  ->  英语四级单词背诵.html
   Everything inlined, audio as base64 in <script type="application/json"> blocks. ~49MB.
   This is the AirDrop-it-and-it-works copy; it never touches the network.

2) HOSTED (PWA) ->  docs/
   index.html      the shell: layout + logic + all 1250 entries of TEXT, ~560KB
   audio-us.<h>.bin  raw mp3 bytes of the 1250 word clips, concatenated
   audio-ex.<h>.bin  same for the example sentences
   sw.js / manifest / icons

   Why split: inlined, the reader can't show a single word until all 49MB has arrived, and any
   one-line CSS change forces every user to re-download all of it. Split, the shell arrives in a
   moment and the audio streams in behind it with a real progress bar. The pack file names carry
   a hash of their CONTENT, so changed audio is guaranteed to be re-fetched (new URL) and
   unchanged audio is guaranteed not to be (same URL, already cached).

   base64 is dropped in the hosted shape — it exists only to survive inside HTML and costs a
   flat +33%. It is a lossless byte<->text mapping, so this changes size, never quality.
"""
import base64
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = json.loads((ROOT / "intermediate" / "entries_full.json").read_text())
AUD = ROOT / "intermediate" / "audio"
TPL = (ROOT / "web" / "template.html").read_text()
OUT = ROOT / "英语四级单词背诵.html"
DOCS = ROOT / "docs"
PWA_DIR = ROOT / "web" / "pwa"
CACHE_NAME = "cet4-1250"          # must match web/pwa/sw.js
MIN_BYTES = {"us": 500, "ex": 300}

slim = [{
    "rank": e["rank"], "word": e["word"], "syl": e["syl"],
    "uk": e["uk"], "us": e["us"], "def": e["def"],
    "ex_label": e["ex_label"], "ex": e["ex"], "root": e["root"],
} for e in DATA]


def clips(kind):
    """[(key, bytes)] for one audio set. us is keyed by word (what speak() has), ex by rank."""
    out = []
    for e in DATA:
        f = AUD / kind / f"{e['rank']}.mp3"
        if f.exists() and f.stat().st_size > MIN_BYTES[kind]:
            key = e["word"] if kind == "us" else str(e["rank"])
            out.append((key, f.read_bytes()))
    return out


def inline_json(items):
    return json.dumps({k: base64.b64encode(b).decode("ascii") for k, b in items},
                      ensure_ascii=False, separators=(",", ":"))


def pack(items):
    """Concatenate the clips and index them -> (blob, {key: [offset, length]})."""
    blob, index, off = bytearray(), {}, 0
    for k, b in items:
        blob += b
        index[k] = [off, len(b)]
        off += len(b)
    return bytes(blob), index


us_items, ex_items = clips("us"), clips("ex")
cfg = ROOT / "web" / "supabase-config.json"
sync_config = cfg.read_text().strip() if cfg.exists() else "null"

# ---------- shared: build a filled template, given the audio-carrying bits ----------
def render(audio_us, audio_ex, audio_index):
    return (TPL
            .replace("__DATA__", json.dumps(slim, ensure_ascii=False, separators=(",", ":")))
            .replace("__AUDIO_US__", audio_us)
            .replace("__AUDIO_EX__", audio_ex)
            .replace("__AUDIO_INDEX__", audio_index)
            .replace("__CACHE_NAME__", CACHE_NAME)
            .replace("__SYNC_CONFIG__", sync_config))


def stamp(html, build_hash, build_time):
    return html.replace("__BUILD_INFO__",
                        json.dumps({"v": build_hash, "t": build_time}, ensure_ascii=False))


# ---------- hosted: shell + packs ----------
us_blob, us_index = pack(us_items)
ex_blob, ex_index = pack(ex_items)
us_name = f"audio-us.{hashlib.sha256(us_blob).hexdigest()[:10]}.bin"
ex_name = f"audio-ex.{hashlib.sha256(ex_blob).hexdigest()[:10]}.bin"

audio_index = json.dumps({
    "us": {"file": us_name, "bytes": len(us_blob), "index": us_index},
    "ex": {"file": ex_name, "bytes": len(ex_blob), "index": ex_index},
}, ensure_ascii=False, separators=(",", ":"))

shell = render("", "", audio_index)
# Version = content hash of the shell. The pack file names live inside it, so changed audio
# changes the version too. Computed BEFORE stamping build info, so it ignores the timestamp:
# an identical rebuild keeps the same version and doesn't push a pointless update to clients.
build_hash = hashlib.sha256(shell.encode()).hexdigest()[:12]
build_time = datetime.now().strftime("%Y-%m-%d %H:%M")
shell = stamp(shell, build_hash, build_time)

DOCS.mkdir(exist_ok=True)
for old in DOCS.glob("audio-*.bin"):              # sweep packs from previous builds
    if old.name not in (us_name, ex_name):
        old.unlink()
(DOCS / "index.html").write_text(shell)
(DOCS / us_name).write_bytes(us_blob)
(DOCS / ex_name).write_bytes(ex_blob)

# "./" is deliberately absent: it and "./index.html" are the same bytes, and listing both makes
# addAll fetch and store the shell twice. Navigations to "./" are answered from "./index.html"
# by the fetch handler in sw.js.
precache = ["./index.html", "./manifest.webmanifest",
            "./icon-180.png", "./icon-192.png", "./icon-512.png"]
keep = precache + ["./" + us_name, "./" + ex_name]
for f in PWA_DIR.iterdir():
    if f.name == "sw.js":
        # BUILD_HASH is what makes sw.js differ after a shell-only change; without it the browser
        # sees identical bytes, installs nothing, and keeps serving the cached shell forever.
        (DOCS / f.name).write_text(f.read_text()
                                   .replace("__PRECACHE__", json.dumps(precache))
                                   .replace("__KEEP__", json.dumps(keep))
                                   .replace("__BUILD_HASH__", build_hash))
    else:
        shutil.copy2(f, DOCS / f.name)

shell_kb = (DOCS / "index.html").stat().st_size // 1024
print(f"-> {DOCS}/  shell {shell_kb} KB + {us_name} ({len(us_blob)//1048576} MB) "
      f"+ {ex_name} ({len(ex_blob)//1048576} MB) + sw.js/manifest/icons, ver={build_hash} @ {build_time}")

# ---------- single file: everything inline ----------
single = stamp(render(inline_json(us_items), inline_json(ex_items), "null"), build_hash, build_time)
OUT.write_text(single)
print(f"-> {OUT}  ({OUT.stat().st_size//1048576} MB, {len(slim)} entries, "
      f"audio US={len(us_items)} EX={len(ex_items)})")

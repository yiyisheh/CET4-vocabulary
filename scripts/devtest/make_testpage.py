"""Build a tiny, fast-loading test page from web/template.html.

The real build (英语四级单词背诵.html / docs/index.html) is 52MB because of the
embedded base64 audio — fine for the iPad, painful for iterating on layout or
interactions. This fills the same placeholders with the FIRST N real entries and
EMPTY audio maps, giving a ~100KB page that opens instantly and behaves
identically for everything except sound.

    python scripts/devtest/make_testpage.py [N] [OFFSET]   # default 120 entries from rank 1
    -> tmp/devtest/testpage.html      (output goes to tmp/, which is gitignored)

Use OFFSET to reach words that actually have 词根词缀卡 (the top-100 are function
words with none), e.g. `python scripts/devtest/make_testpage.py 120 400`.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
OFF = int(sys.argv[2]) if len(sys.argv) > 2 else 0

tpl = (ROOT / "web" / "template.html").read_text()
data = json.loads((ROOT / "intermediate" / "entries_full.json").read_text())
slim = [{k: e[k] for k in
         ("rank", "word", "syl", "uk", "us", "def", "ex_label", "ex", "root")}
        for e in data[OFF:OFF + N]]

html = (tpl
        .replace("__DATA__", json.dumps(slim, ensure_ascii=False))
        .replace("__AUDIO_US__", "{}")          # no audio: keeps the page tiny
        .replace("__AUDIO_EX__", "{}")
        .replace("__SYNC_CONFIG__", "null")     # no sync in tests
        .replace("__CACHE_BYTES__", "1000")
        .replace("__BUILD_INFO__", '{"v":"testpage","t":"dev"}'))

out = ROOT / "tmp" / "devtest" / "testpage.html"     # generated artifact -> tmp/ (gitignored)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html)
print(f"-> {out}  ({out.stat().st_size // 1024} KB, {len(slim)} entries, no audio)")

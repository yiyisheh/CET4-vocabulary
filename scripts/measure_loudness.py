"""Measure the loudness of every audio clip -> intermediate/audio/loudness.json

The word clips come from several sources whose levels differ by up to ~8 dB (Youdao's main
voice ≈ -16 LUFS, its 24k/32k group ≈ -24, the edge-tts Ava replacements ≈ -20.5, the example
sentences ≈ -21). We do NOT rewrite the mp3s to fix that: re-encoding would cost quality (the
24k/32k group is already low-bitrate) and change the pack hashes, forcing every user to
re-download ~36MB. Instead this script measures each clip once (EBU R128 integrated loudness +
true peak), build_html.py turns that into a per-clip gain, and the page applies the gain to the
PCM it already decodes before playback (see playClip in web/template.html).

    python scripts/measure_loudness.py      # incremental: only (re)measures clips whose bytes changed

Output: {"us": {rank: {"sha": .., "I": LUFS, "tp": dBTP}}, "ex": {...}}. Needs ffmpeg.
"""
import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent.parent
AUD = ROOT / "intermediate" / "audio"
OUT = AUD / "loudness.json"


def sha(p):
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12]


def ebur(p):
    """(integrated LUFS, true peak dBTP) via ffmpeg's ebur128 filter."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p),
                          "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summ = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+|-inf) LUFS", summ).group(1)
    tp = re.search(r"Peak:\s*(-?[\d.]+|-inf) dBFS", summ).group(1)
    return (None if i == "-inf" else float(i)), (-120.0 if tp == "-inf" else float(tp))


old = json.loads(OUT.read_text()) if OUT.exists() else {}
res, jobs = {}, []
for kind in ("us", "ex"):
    res[kind] = {}
    for p in sorted((AUD / kind).glob("*.mp3"), key=lambda q: int(q.stem)):
        h, prev = sha(p), old.get(kind, {}).get(p.stem)
        if prev and prev.get("sha") == h:
            res[kind][p.stem] = prev
        else:
            jobs.append((kind, p, h))


def one(job):
    kind, p, h = job
    i, tp = ebur(p)
    return kind, p.stem, {"sha": h, "I": i, "tp": tp}


with ThreadPoolExecutor(8) as pool:
    for kind, stem, row in pool.map(one, jobs):
        res[kind][stem] = row

for kind in res:                                      # stable order: by rank
    res[kind] = dict(sorted(res[kind].items(), key=lambda kv: int(kv[0])))
OUT.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")))
print(f"-> {OUT}  measured {len(jobs)}, reused {sum(len(v) for v in res.values()) - len(jobs)}")

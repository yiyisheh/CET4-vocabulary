"""Classify each example-sentence clip in intermediate/audio/ex/ by speaker pitch.

The two edge-tts male voices (Andrew / Brian) differ mainly in median F0, so we
decode each mp3 to 16 kHz mono PCM, run a plain autocorrelation pitch tracker,
and take the median F0 over voiced frames. Two clean clusters fall out.

  python scripts/devtest/classify_ex_voice.py            -> tmp/devtest/ex_f0.json
  python scripts/devtest/classify_ex_voice.py 94 96 99   -> just print those ranks
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent.parent
EX = ROOT / "intermediate" / "audio" / "ex"
SR = 16000
FMIN, FMAX = 60, 320          # male speech range, generous


def pcm(path: Path) -> np.ndarray:
    out = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", str(path), "-t", "8",
         "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True).stdout
    return np.frombuffer(out, dtype=np.float32)


def median_f0(x: np.ndarray) -> float:
    win, hop = 1024, 256
    lo, hi = SR // FMAX, SR // FMIN
    f0s = []
    for i in range(0, max(0, len(x) - win), hop):
        f = x[i:i + win].astype(np.float64)
        if np.sqrt((f * f).mean()) < 0.02:      # unvoiced / silence
            continue
        f -= f.mean()
        ac = np.correlate(f, f, "full")[win - 1:]
        if ac[0] <= 0:
            continue
        seg = ac[lo:hi]
        k = int(np.argmax(seg)) + lo
        if ac[k] / ac[0] < 0.35:                # not periodic enough
            continue
        f0s.append(SR / k)
    return float(np.median(f0s)) if len(f0s) >= 8 else 0.0


def rank_f0(rank: int):
    return rank, round(median_f0(pcm(EX / f"{rank}.mp3")), 1)


def main():
    args = [int(a) for a in sys.argv[1:]]
    ranks = args or sorted(int(p.stem) for p in EX.glob("*.mp3") if p.stem.isdigit())
    with ThreadPoolExecutor(8) as pool:
        res = dict(pool.map(rank_f0, ranks))
    if args:
        for r in args:
            print(r, res[r])
        return
    out = ROOT / "tmp" / "devtest" / "ex_f0.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({str(k): v for k, v in sorted(res.items())}, indent=0))
    vals = np.array([v for v in res.values() if v])
    print(f"{len(res)} clips, {len(vals)} with usable F0 -> {out}")
    print("percentiles:", {p: round(float(np.percentile(vals, p)), 1)
                           for p in (5, 25, 40, 50, 60, 75, 95)})


if __name__ == "__main__":
    main()

"""Download Youdao TTS mp3 for every word (US + UK) for OFFLINE embedding.

Saves to intermediate/audio/{us,uk}/{rank}.mp3  (rank = stable filename).
Resumable (skips existing non-empty files), concurrent, with retries.
"""
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES = json.loads((ROOT / "intermediate" / "entries_full.json").read_text())
AUD = ROOT / "intermediate" / "audio"
ACCENTS = {"us": 2, "uk": 1}          # Youdao type=2 美, type=1 英
WORKERS = 12

for a in ACCENTS:
    (AUD / a).mkdir(parents=True, exist_ok=True)


def url(word, t):
    from urllib.parse import quote
    return f"https://dict.youdao.com/dictvoice?type={t}&audio={quote(word)}"


def fetch(rank, word, accent):
    t = ACCENTS[accent]
    out = AUD / accent / f"{rank}.mp3"
    if out.exists() and out.stat().st_size > 500:
        return (accent, rank, "skip", out.stat().st_size)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url(word, t), headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=30).read()
            if len(data) < 500:
                raise ValueError("too small")
            out.write_bytes(data)
            return (accent, rank, "ok", len(data))
        except Exception as e:
            if attempt == 3:
                return (accent, rank, f"FAIL {e}", 0)
            time.sleep(1.5 * (attempt + 1))


def main():
    jobs = [(e["rank"], e["word"], a) for e in ENTRIES for a in ACCENTS]
    print(f"{len(jobs)} downloads ({len(ENTRIES)} words × {len(ACCENTS)} accents)")
    done = fail = skip = total_bytes = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(fetch, r, w, a) for r, w, a in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            acc, rank, status, size = fut.result()
            total_bytes += size
            if status == "ok":
                done += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
                print(f"  ! {acc}/{rank}: {status}", file=sys.stderr)
            if i % 250 == 0:
                print(f"  {i}/{len(jobs)}  ok={done} skip={skip} fail={fail}")
    print(f"done. ok={done} skip={skip} fail={fail}  total={total_bytes//1024//1024}MB")
    if fail:
        print("re-run to retry failed files (resumable).")


if __name__ == "__main__":
    main()

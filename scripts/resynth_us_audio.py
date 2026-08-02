"""Replace unwanted 有道 word-audio voices with an edge-tts voice.

有道 dictvoice serves each word from one of several source libraries, and the
encoding parameters are a reliable fingerprint of which one (sample rate + bit
rate cluster cleanly, verified by ear against ranks 1-100). A few of those
sources are a different speaker from the main one; this script re-synthesizes
just those ranks with edge-tts and writes them back into intermediate/audio/us/
so the whole book sounds like at most two voices.

Targets are selected by encoding fingerprint, NOT by a hard-coded rank list, so
re-running after a fresh fetch_audio.py picks up the same clips.

  python scripts/resynth_us_audio.py --dry-run     list what would be replaced
  python scripts/resynth_us_audio.py               do it

Originals are copied to intermediate/audio_orig_backup/us/ first (gitignored);
--restore puts them back. Every replaced rank is recorded in
intermediate/audio/us/voices.json so the mixed origin stays traceable.

⚠️ fetch_audio.py skips ranks whose mp3 already exists, so it will NOT clobber
these replacements — but deleting intermediate/audio/us/ and re-downloading
would. Re-run this script after any such re-download.
"""
import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import edge_tts

ROOT = Path(__file__).parent.parent
US = ROOT / "intermediate" / "audio" / "us"
BACKUP = ROOT / "intermediate" / "audio_orig_backup" / "us"
MANIFEST = US / "voices.json"
ENTRIES = ROOT / "intermediate" / "entries_full.json"

VOICE = "en-US-AvaMultilingualNeural"
# (sample_rate, bit_rate) of the 有道 source libraries to replace.
# 44100/128000 (79 clips) = the higher-pitched female the user dislikes;
# 24000/160000 (7 clips)  = another odd one out.
TARGET_FORMATS = {("44100", "128000"), ("24000", "160000")}
# Re-encode to match the dominant 有道 source so nothing stands out.
OUT_RATE, OUT_BITRATE = "48000", "64k"
TRIM_AF = "silenceremove=start_periods=1:start_silence=0:start_threshold=-45dB"
CONCURRENCY = 6


def probe(path: Path):
    """-> (sample_rate, bit_rate) as strings, or None if unreadable."""
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "a:0",
         "-show_entries", "stream=sample_rate,bit_rate", "-of", "json", str(path)],
        capture_output=True).stdout
    try:
        s = json.loads(out)["streams"][0]
        return s["sample_rate"], s.get("bit_rate")
    except Exception:
        return None


def targets(words):
    """Ranks whose current mp3 came from one of the unwanted source libraries."""
    out = []
    for rank in sorted(words):
        p = US / f"{rank}.mp3"
        if p.exists() and probe(p) in TARGET_FORMATS:
            out.append(rank)
    return out


async def synth(rank, word, sem, stats):
    raw = US / f"{rank}.raw.mp3"
    dst = US / f"{rank}.mp3"
    async with sem:
        for attempt in range(4):
            try:
                await edge_tts.Communicate(word, VOICE).save(str(raw))
                if raw.stat().st_size < 300:
                    raise ValueError("too small")
                break
            except Exception as exc:
                if attempt == 3:
                    stats["fail"].append(rank)
                    print(f"  ! {rank} {word}: {exc}", file=sys.stderr)
                    raw.unlink(missing_ok=True)
                    return
                await asyncio.sleep(1.5 * (attempt + 1))
    p = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(raw), "-af", TRIM_AF,
        "-c:a", "libmp3lame", "-b:a", OUT_BITRATE, "-ar", OUT_RATE, "-ac", "1", str(dst),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    await p.wait()
    raw.unlink(missing_ok=True)
    if p.returncode == 0 and dst.exists() and dst.stat().st_size > 300:
        stats["ok"].append(rank)
    else:
        stats["fail"].append(rank)
        print(f"  ! {rank} {word}: ffmpeg failed", file=sys.stderr)


async def run(ranks, words):
    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {"ok": [], "fail": []}
    await asyncio.gather(*(synth(r, words[r], sem, stats) for r in ranks))
    return stats


def restore():
    if not BACKUP.exists():
        sys.exit("no backup at " + str(BACKUP))
    n = 0
    for src in BACKUP.glob("*.mp3"):
        shutil.copy2(src, US / src.name)
        n += 1
    MANIFEST.unlink(missing_ok=True)
    print(f"restored {n} originals from {BACKUP}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()
    if args.restore:
        return restore()

    words = {e["rank"]: e["word"] for e in json.loads(ENTRIES.read_text())}
    ranks = targets(words)
    print(f"{len(ranks)} clips match the unwanted source formats {sorted(TARGET_FORMATS)}")
    if args.dry_run:
        for r in ranks:
            print(f"  {r:5d} {words[r]}")
        return
    if not ranks:
        return print("nothing to do")

    BACKUP.mkdir(parents=True, exist_ok=True)
    for r in ranks:
        dst = BACKUP / f"{r}.mp3"
        if not dst.exists():                      # never overwrite a real original
            shutil.copy2(US / f"{r}.mp3", dst)
    print(f"originals backed up -> {BACKUP}")

    t0 = time.time()
    stats = asyncio.run(run(ranks, words))
    print(f"synthesized {len(stats['ok'])}, failed {len(stats['fail'])} in {time.time()-t0:.0f}s")

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    manifest.update({str(r): VOICE for r in stats["ok"]})
    manifest["_meta"] = {
        "note": "ranks re-synthesized with edge-tts; everything else is 有道 dictvoice",
        "replaced_formats": sorted(TARGET_FORMATS),
        "encoded_as": f"{OUT_RATE}Hz {OUT_BITRATE} mono",
        "updated": time.strftime("%Y-%m-%d"),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"manifest -> {MANIFEST}")
    if stats["fail"]:
        sys.exit(f"FAILED ranks: {sorted(stats['fail'])} (originals still in {BACKUP})")


if __name__ == "__main__":
    main()

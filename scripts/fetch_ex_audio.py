"""Generate OFFLINE example-sentence audio via edge-tts, no leading silence.

For every entry whose example has an English part, synthesize it with edge-tts
using ONE of two male voices assigned ~1:1 at random (deterministic seed), then
strip the leading silence with ffmpeg.

  intermediate/audio/ex/{rank}.mp3        final clip (leading silence removed)
  intermediate/audio/ex/voices.json       {rank: "Andrew"|"Brian"} assignment

The example field mixes English + a Chinese gloss in parentheses, e.g.
  "The statement given below is for your reference.(以下声明供您参考。)"
Only the English (before the first '(' or '（') is spoken.

Resumable: skips ranks whose final mp3 already exists. Concurrency-limited so the
free edge-tts endpoint doesn't rate-limit us.
"""
import asyncio
import json
import random
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).parent.parent
ENTRIES = json.loads((ROOT / "intermediate" / "entries_full.json").read_text())
OUT = ROOT / "intermediate" / "audio" / "ex"
OUT.mkdir(parents=True, exist_ok=True)

VOICES = {"Andrew": "en-US-AndrewMultilingualNeural",
          "Brian":  "en-US-BrianMultilingualNeural"}
CONCURRENCY = 8
SEED = 42
# strip leading silence below this threshold; re-encode to match edge-tts (24kHz 48k mono)
TRIM_AF = "silenceremove=start_periods=1:start_silence=0:start_threshold=-45dB"


def english(ex: str) -> str:
    s = re.split(r"[（(]", ex or "", maxsplit=1)[0].strip()
    return re.sub(r"^[A-Z]:\s*", "", s)   # drop dialogue speaker tag (W:/M:) so it isn't spoken


def assign_voices(ranks):
    """Deterministic ~1:1 random split: shuffle by fixed seed, first half Andrew."""
    order = list(ranks)
    random.Random(SEED).shuffle(order)
    half = len(order) // 2
    a = set(order[:half])
    return {r: ("Andrew" if r in a else "Brian") for r in ranks}


async def ffmpeg_trim(src: Path, dst: Path) -> bool:
    p = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(src), "-af", TRIM_AF,
        "-c:a", "libmp3lame", "-b:a", "48k", "-ac", "1", str(dst),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await p.wait()
    return p.returncode == 0 and dst.exists() and dst.stat().st_size > 300


async def one(rank, text, voice_name, sem, stats):
    final = OUT / f"{rank}.mp3"
    if final.exists() and final.stat().st_size > 300:
        stats["skip"] += 1
        return
    raw = OUT / f"{rank}.raw.mp3"
    async with sem:
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, VOICES[voice_name]).save(str(raw))
                if raw.stat().st_size < 300:
                    raise ValueError("too small")
                break
            except Exception as e:
                if attempt == 3:
                    stats["fail"] += 1
                    print(f"  ! {rank} ({voice_name}): {e}", file=sys.stderr)
                    raw.unlink(missing_ok=True)
                    return
                await asyncio.sleep(1.5 * (attempt + 1))
    ok = await ffmpeg_trim(raw, final)
    raw.unlink(missing_ok=True)
    if ok:
        stats["ok"] += 1
    else:
        stats["fail"] += 1
        print(f"  ! {rank}: ffmpeg trim failed", file=sys.stderr)
    n = stats["ok"] + stats["skip"] + stats["fail"]
    if n % 100 == 0:
        print(f"  {n}/{stats['total']}  ok={stats['ok']} skip={stats['skip']} fail={stats['fail']}")


async def main():
    jobs = [(e["rank"], english(e.get("ex", ""))) for e in ENTRIES]
    jobs = [(r, t) for r, t in jobs if t]
    voices = assign_voices([r for r, _ in jobs])
    (OUT / "voices.json").write_text(json.dumps(voices, ensure_ascii=False, indent=0))
    na = sum(1 for v in voices.values() if v == "Andrew")
    print(f"{len(jobs)} example sentences  (Andrew={na} Brian={len(jobs)-na})")
    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {"ok": 0, "skip": 0, "fail": 0, "total": len(jobs)}
    await asyncio.gather(*(one(r, t, voices[r], sem, stats) for r, t in jobs))
    print(f"done. ok={stats['ok']} skip={stats['skip']} fail={stats['fail']}")
    if stats["fail"]:
        print("re-run to retry failed (resumable).")


if __name__ == "__main__":
    asyncio.run(main())

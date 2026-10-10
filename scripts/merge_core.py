"""Merge the 核心意象 (core image) data into intermediate/core.json.

For short, high-frequency polysemous words (take / get / over …) the dictionary
lists several Chinese senses that look unrelated. A core image is one concrete
picture that the listed senses grow out of, plus a one-line derivation:
  image  : 主动伸手，把外面的东西拿到自己这边
  derive : 拿；取 ⇒ 采取（把办法拿来用）；花费（…）…
Senses that genuinely don't follow from the image are marked 「单独记」 rather
than forced in (accuracy over coverage, same rule as the 词根 data).

Sources (in priority order; first non-empty wins per word):
  intermediate/core_manual.json          -- hand-written / reviewed entries
  intermediate/core_chunks/out_*.json    -- Claude sub-agent batches

Only words WITHOUT a 词根 breakdown are candidates (long words are covered by
roots.json); a core image on a rooted word is dropped.

An inflected form (takes / getting …) may be {"same_as": "take"}: it reuses the
base word's card, and gets nothing if the base ends up without one.
A null in core_manual.json is a review veto: that word gets no card, whatever the
sub-agents produced (e.g. kinds = 种类 must not inherit kind's 善良 card).
The sub-agent brief is intermediate/core_chunks/PROMPT.md.
"""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
INT = ROOT / "intermediate"
OUT = INT / "core.json"


def clean(v):
    if not isinstance(v, dict):
        return None
    image, derive = (v.get("image") or "").strip(), (v.get("derive") or "").strip()
    return {"image": image, "derive": derive} if image and derive else None


def main():
    roots = json.loads((INT / "roots.json").read_text())
    result, alias = {}, {}
    vetoed = {w for w, v in json.loads((INT / "core_manual.json").read_text()).items() if v is None}
    sources = [str(INT / "core_manual.json")] + sorted(glob.glob(str(INT / "core_chunks" / "out_*.json")))
    for f in sources:
        if not Path(f).exists():
            continue
        for w, v in json.loads(Path(f).read_text()).items():
            if w in vetoed:
                continue
            if isinstance(v, dict) and v.get("same_as"):
                alias.setdefault(w, v["same_as"])
                continue
            c = clean(v)
            if c and w not in result:
                result[w] = c
    for w, base in alias.items():
        if w not in result and base in result:
            result[w] = result[base]

    rooted = [w for w in result if (roots.get(w) or {}).get("parts")]
    for w in rooted:
        del result[w]
    unknown = [w for w in result if w not in roots]
    if unknown:
        raise SystemExit(f"not in the 1250 list: {unknown}")

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"{len(result)} core images -> {OUT.name}"
          + (f"  (dropped {len(rooted)} rooted: {rooted})" if rooted else ""))


if __name__ == "__main__":
    main()

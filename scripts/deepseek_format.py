"""Format CET-4 high-frequency words into liut969-style entries via DeepSeek.

v2: explicit purpose (CET-4 study book) + hybrid example strategy.
- Clean real exam sentence -> copied verbatim ("例句:")
- Fragment / OCR-corrupted / no sentence -> DeepSeek composes with CET-4
  vocabulary, tagged "例句（自编）:" so the user can audit it.

- Fixed system prompt -> hits DeepSeek prompt cache.
- 7 words per request. Resumable. Empty responses are retried, never saved.
"""
import csv
import json
import re
import time
import concurrent.futures
from pathlib import Path
from urllib import request, error

ROOT = Path(__file__).parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
BATCH_DIR = ROOT / "intermediate" / "ds_batches"
BATCH_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = json.loads((ROOT / "api-sk.json").read_text())["deepseek"]
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"
BATCH = 7

EXAMPLES_30 = (Path(__file__).parent / "examples_30_template.txt").read_text().strip()

SYSTEM_PROMPT = (
    "你在为【备考大学英语四级（CET-4）的考生】编写一本高频词背诵手册。"
    "我会给你一批四级真题里的高频单词，每个词附带【词频次数】，"
    "多数还附带一句【从四级真题语料中抽取的参考例句】。\n\n"
    "请为每个词输出一个词条，格式严格如下：\n\n"
    "<单词>\n"
    "英[英式音标]  美[美式音标]\n"
    "词频: <次数> 次\n"
    "释义: <词性缩写+简明中文释义>\n"
    "变形: <相关词形，用空格分隔>\n"
    "例句: <英文例句>(<中文翻译>)\n\n"
    "规则：\n"
    "1. 音标用国际音标，英式、美式分别给出。\n"
    "2. 释义用词性缩写开头（n./v./vt./vi./adj./adv./prep./conj./pron./art./"
    "modal v. 等），中文释义简明；多个义项用分号隔开。"
    "优先选取四级考试中最常考的义项。\n"
    "3. 『变形』行：列出该词的相关词形（原形、复数、过去式、派生词等）；"
    "若无需要列出的变形，则整行省略。\n"
    "4. 『例句』行——按以下情况处理：\n"
    "   (a) 若我提供的参考例句是【结构完整、通顺、无拼写错误】的句子："
    "原样照抄该英文句子（一个字都不能改、不能替换），翻译成中文，"
    "写作『例句: 英文(中文)』。\n"
    "   (b) 若参考例句是【残缺片段、不通顺、或含明显拼写/OCR错误】"
    "（例如把 consumption 误拼成 conswnption）：不要照抄。请你自己造一个"
    "简短、自然的新句子来体现该词含义，写作『例句（自编）: 英文(中文)』。\n"
    "   (c) 若我标注【无参考例句】：同样自己造句，写作『例句（自编）: 英文(中文)』。\n"
    "   造句时务必【只用四级核心高频词汇】，句子简单明了，便于考生背诵记忆。\n"
    "5. 多个词条之间用一行『---』分隔。不要输出任何额外说明、标题或 Markdown。\n\n"
    "下面是 30 个已完成的标准范例（均属情况 a，照抄真题原句），"
    "请完全模仿这个风格和格式：\n\n"
    "====== 范例开始 ======\n"
    + EXAMPLES_30 +
    "\n====== 范例结束 ======"
)


def call_deepseek(user_msg: str, retries: int = 5) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    req = request.Request(
        ENDPOINT, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}",
                 "Content-Type": "application/json"},
    )
    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read())
            content = data["choices"][0]["message"]["content"].strip()
            if len(content) < 40:                 # empty / truncated junk
                raise ValueError(f"response too short: {content!r}")
            return content
        except error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"  HTTP {e.code} (try {attempt+1}): {body[:150]}")
            time.sleep(4 * (attempt + 1))
        except Exception as e:
            print(f"  ERR (try {attempt+1}): {e}")
            time.sleep(4)
    raise RuntimeError("DeepSeek call failed after retries")


def build_user_msg(items: list[tuple[int, str, int, str]]) -> str:
    lines = ["请处理下面这些词："]
    for rank, word, count, ex in items:
        if ex:
            lines.append(f"\n[{word}] 词频:{count}次\n参考例句: {ex}")
        else:
            lines.append(f"\n[{word}] 词频:{count}次\n【无参考例句】")
    return "\n".join(lines)


def main():
    rows = list(csv.DictReader((OUT / "high_freq_surface.csv").open()))[:1250]
    examples = json.loads((ROOT / "intermediate" / "examples.json").read_text())

    hand_done = {b.splitlines()[0].strip().lower()
                 for b in re.split(r"\n\s*\n", EXAMPLES_30) if b.strip()}
    todo = [(int(r["rank"]), r["word"], int(r["count"]),
             examples.get(r["word"], ""))
            for r in rows if r["word"] not in hand_done]
    print(f"hand-written (skipped): {len(hand_done)}")
    print(f"words to format via DeepSeek: {len(todo)}")

    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"batches of {BATCH}: {len(batches)}")

    def run(idx_batch):
        idx, batch = idx_batch
        out = BATCH_DIR / f"batch_{idx:03d}.txt"
        if out.exists() and out.stat().st_size > 40:
            return idx, "cached"
        txt = call_deepseek(build_user_msg(batch))
        out.write_text(txt)
        return idx, f"{len(txt)} chars"

    # warm up the prompt cache with the first call alone
    if not (BATCH_DIR / "batch_000.txt").exists():
        print(f"  batch 000 (cache warm-up): {run((0, batches[0]))[1]}")

    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for idx, status in ex.map(run, list(enumerate(batches))):
            print(f"  batch {idx:03d}: {status}")
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()

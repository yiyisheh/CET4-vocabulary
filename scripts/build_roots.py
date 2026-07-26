"""Generate 词根/词缀 (etymology) breakdowns for the CET-4 vocabulary via DeepSeek.

Output: intermediate/roots.json  ->  { word: {"parts":[{"type","text","meaning"}], "summary": "..."} }

Only words with a *meaningful* root/affix structure get an entry. Function words
(the, to, a) and opaque monomorphemic words return {"parts":[], "summary":""},
which we treat as "no 词根 entry".

Resumable: already-answered words are skipped. Concurrent requests.
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "output" / "high_freq_cet4_df.txt"
OUT = ROOT / "intermediate" / "roots.json"
KEY = json.load(open(ROOT / "api-sk.json"))["deepseek"]

BATCH = 20          # words per request
WORKERS = 8         # concurrent requests
MODEL = "deepseek-chat"

SYS = """你是一位英语词源与词根词缀专家。给定一批英语单词及其中文释义，为每个单词输出词根/词缀拆解，风格与有道词典"词根"卡片一致。

规则：
1. 只有当单词能被拆成有意义的 前缀/词根/后缀 时才给出拆解。功能词(the, to, a, of, and 等)、不可再拆的简单词(good, big, dog, run 等)、专有名词，一律输出空拆解 {"parts": [], "summary": ""}。
2. 每个组成部分 type 只能是 "前缀"、"词根"、"后缀" 三者之一。text 为该词根词缀的书写形式(前缀带后连字符如 "com-"，后缀带前连字符如 "-tion"，词根不带连字符如 "pos")。meaning 为简洁中文含义。
3. summary 为一句话总结，形如 "com- 一起 + pos 放置 + -tion 名词后缀 ⇒ 构成；作品"，用真实含义把各部分串起来推导出该词意思，用 ⇒ 连接最终释义。summary 要简短(不超过 40 字)。
4. 宁缺毋滥：拆解必须真实、常见、有助记忆。若不确定或牵强，输出空拆解。
5. 严格输出 JSON，键为单词原形，值为 {"parts":[...], "summary":"..."}。不要输出任何多余文字。

示例输出：
{"composition": {"parts": [{"type":"前缀","text":"com-","meaning":"一起；全"},{"type":"词根","text":"pos","meaning":"放置"},{"type":"后缀","text":"-tion","meaning":"名词后缀，表动作或状态"}], "summary":"com- 一起 + pos 放置 + -tion 名词 ⇒ 把东西放到一起 ⇒ 构成；作品；作文"}, "benefit": {"parts":[{"type":"词根","text":"bene","meaning":"好的，善的"},{"type":"词根","text":"fit","meaning":"做"}], "summary":"bene 好 + fit 做 ⇒ 做事之后好的结果 ⇒ 好处"}, "the": {"parts": [], "summary": ""}}"""


def load_words():
    lines = SRC.read_text().splitlines()
    ENTRY = re.compile(r"^\[(\d+)\]\s+(.+)$")
    out, cur = [], None
    for s in (l.strip() for l in lines):
        m = ENTRY.match(s)
        if m:
            cur = {"word": m.group(2).strip(), "def": ""}
            out.append(cur)
        elif cur and s.startswith("释义"):
            cur["def"] = s.split(":", 1)[-1].split("：", 1)[-1].strip()
    return out


def call(words):
    user = "为以下单词输出词根拆解 JSON：\n" + "\n".join(
        f"{w['word']}  {w['def']}" for w in words)
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions", data=body,
        headers={"Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            r = urllib.request.urlopen(req, timeout=120)
            data = json.loads(r.read())
            return json.loads(data["choices"][0]["message"]["content"])
        except Exception as e:
            if attempt == 3:
                print(f"  ! batch failed: {e}", file=sys.stderr)
                return {}
            time.sleep(2 * (attempt + 1))
    return {}


def main():
    words = load_words()
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [w for w in words if w["word"] not in done]
    print(f"{len(words)} words, {len(done)} done, {len(todo)} to do")
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(call, b): b for b in batches}
        n = 0
        for fut in as_completed(futs):
            b = futs[fut]
            res = fut.result()
            for w in b:
                v = res.get(w["word"])
                if isinstance(v, dict) and "parts" in v:
                    done[w["word"]] = {"parts": v.get("parts", []),
                                       "summary": v.get("summary", "")}
                else:
                    done[w["word"]] = {"parts": [], "summary": ""}
            n += 1
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1))
            got = sum(1 for w in b if done.get(w["word"], {}).get("parts"))
            print(f"[{n}/{len(batches)}] +{len(b)} words ({got} with roots)")

    total_root = sum(1 for v in done.values() if v.get("parts"))
    print(f"done. {len(done)} words, {total_root} have 词根 entries "
          f"({total_root*100//len(done)}%)")


if __name__ == "__main__":
    main()

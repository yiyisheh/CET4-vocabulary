"""Qwen vision OCR client + prompts."""
import base64, json, time
from pathlib import Path
from urllib import request, error

ROOT = Path(__file__).parent.parent
API_KEY = json.loads((ROOT / "api-sk.json").read_text())["qwen"]
ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen3-vl-plus"


def ocr_page(png_path: Path, prompt: str, retries: int = 3) -> str:
    return ocr_images([png_path], prompt, retries)


def _mime(path: Path) -> str:
    return "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"


def ocr_images(png_paths: list[Path], prompt: str, retries: int = 3,
               max_tokens: int = 16384, timeout: int = 600) -> str:
    content = [{"type": "text", "text": prompt}]
    for p in png_paths:
        b64 = base64.b64encode(p.read_bytes()).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{_mime(p)};base64,{b64}"},
        })
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
    }
    req = request.Request(
        ENDPOINT, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}",
                 "Content-Type": "application/json"},
    )
    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            return data["choices"][0]["message"]["content"]
        except error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"  HTTP {e.code} (attempt {attempt+1}): {body[:200]}")
            if e.code in (429, 500, 502, 503):
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except Exception as e:
            print(f"  ERR (attempt {attempt+1}): {e}")
            time.sleep(3)
    raise RuntimeError(f"OCR failed after {retries} retries ({len(png_paths)} images)")


# Prompt for 真题 PDF (the question paper itself) - whole document
PROMPT_PAPER = (
    "下面是一份大学英语四级真题（共多页，按顺序排列）。请对**整份**做 OCR，"
    "只输出英文内容（包括 Part I Writing 题目说明、Part II Listening 的题号和选项、"
    "Part III Reading 的所有段落、题目和选项）。\n\n"
    "完全跳过：\n"
    "- 中文标题（如 '2022 年 6 月大学英语四级考试真题'）\n"
    "- 页眉页脚（如 '2022.6/ 1 (第 1 套)'）\n"
    "- 括号里的中文注释（如 (菜谱)、(圆柱体)、(箍)）\n"
    "- **Part IV Translation 整段**：从 'Part IV' 这个标题开始到文档末尾，全部跳过，"
    "包括它的英文 Directions 说明（因为后面是中文翻译题）。\n\n"
    "按页面顺序输出，保持段落和换行。不要添加 Markdown、代码块、页码标记或任何解释。"
)

# Prompt for ans PDF (only listening transcripts wanted) - whole document
PROMPT_ANS = (
    "下面是一份大学英语四级真题的答案与详解 PDF（共多页，按顺序排列）。"
    "请只输出**Part II Listening Comprehension（听力）**部分的英文内容：\n"
    "- 听力题号引导句（如 'Questions 1 and 2 are based on the news report you have just heard.'）\n"
    "- 听力原文段落（News reports / Conversations / Passages 的整段英文原文）\n"
    "- 听力题干（如 '1. What do we learn ...'，常见于'答案详解'方框内，"
    "若框内有英文题干句子，提取英文题干，丢弃中文解析）\n\n"
    "严格跳过：\n"
    "- 中文标题、页眉页脚\n"
    "- Part I Writing 的'结构框图'、'参考范文'、'范文点评'、'话题词汇'：编辑写的英文范文及词汇表，全部跳过\n"
    "- '概览'、'全文翻译'、'参考译文'、'译点精析'：跳过\n"
    "- '答案详解' 方框内的中文解析（仅保留其中的英文题干句）\n"
    "- '语法分析'、'词汇辨析'、'重难点单词及短语'：跳过\n"
    "- Part III Reading 的英文文章和解析（与真题 PDF 重复，避免双重计数）\n"
    "- Part IV Translation 的英文参考译文（编辑写的，不算考题）\n\n"
    "按出现顺序输出，保持段落和换行。不要 Markdown、不要解释、不要页码标记。"
    "如果文档完全不含 Part II Listening 内容，输出空字符串。"
)


if __name__ == "__main__":
    import sys
    png = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "paper"
    prompt = PROMPT_PAPER if mode == "paper" else PROMPT_ANS
    print(ocr_page(png, prompt))

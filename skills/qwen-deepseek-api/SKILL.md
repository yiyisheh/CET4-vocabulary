---
name: qwen-deepseek-api
description: Call Alibaba Qwen vision API to OCR scanned PDFs and images, and DeepSeek API for low-cost bulk text generation/formatting. Use when extracting text from image-based (scanned) PDFs or photos, or batch-processing text with a cheap LLM. Triggers on tasks like "OCR these scanned PDFs", "extract text from this image", "use Qwen/DeepSeek", "batch-format this list with an LLM".
---

# Qwen + DeepSeek API toolkit

Two complementary Chinese-LLM APIs, both OpenAI-compatible:

| Need | Use | Why |
|------|-----|-----|
| OCR a scanned PDF / image; anything visual | **Qwen** `qwen3-vl-plus` | DeepSeek's API has **no** image support |
| Cheap bulk text generation / formatting / translation | **DeepSeek** `deepseek-v4-pro` | strong + very cheap, prompt caching |

## Setup

Create `api-sk.json` in the project working directory:

```json
{
  "qwen": "sk-...",
  "deepseek": "sk-..."
}
```

The helper scripts in `scripts/` read this file automatically. Dependency for
PDF rendering: `pip install pymupdf`.

## Qwen — vision OCR

Endpoint: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
(Beijing). Model: `qwen3-vl-plus`. Images go in as base64 `data:` URLs in the
standard OpenAI `image_url` content blocks.

Use `scripts/qwen_vision.py`:

```python
from qwen_vision import render_pdf, ocr

pages = render_pdf("scan.pdf", "_pages")          # PDF -> grayscale JPEGs
text  = ocr(pages, "逐字识别图片中的所有英文文字，跳过中文。")
```

Key practices:
- **Render PDF pages to grayscale JPEG at ~150 dpi.** A 14-page scan is then
  ~5 MB of base64 — under the request-size limit. Full-color PNG (~34 MB)
  triggers timeouts / broken pipes.
- **Feed a whole PDF in one request** (all page images in one `messages`
  entry) to preserve document context. For very large docs, split in halves.
- Put precise extraction rules in the prompt (what to keep, what to skip).
  Calibrate the prompt once against a hand-made ground truth before batch runs.
- OCR is non-deterministic on huge inputs — after a batch, **audit** output
  size vs. page count and retry outliers.

## DeepSeek — bulk text

Endpoint: `https://api.deepseek.com/v1/chat/completions`. Models:
`deepseek-v4-pro` (strongest), `deepseek-v4-flash` (cheaper). **Text only** —
sending `image_url` returns `400 unknown variant 'image_url'`.

Use `scripts/deepseek_text.py`:

```python
from deepseek_text import batch_chat

SYSTEM = "<fixed instructions + few-shot examples — identical every call>"
replies = batch_chat(SYSTEM, ["<task 1>", "<task 2>", ...])
```

Key practices:
- **Prompt caching:** DeepSeek caches the longest identical request prefix.
  Keep the `system` message byte-for-byte constant across the whole batch
  (all instructions + few-shot examples there; vary only the `user` message).
  `batch_chat` warms the cache with the first call, then parallelizes.
- **Small rounds:** a handful of items per call keeps output quality high and
  avoids truncation; many cheap calls beat one giant call.
- Retry empty/short responses; never save a blank result.

## Worked example

`examples/` contains the real scripts from a project that OCR'd ~60 scanned
CET-4 exam PDFs with Qwen and formatted a 1250-word vocabulary book with
DeepSeek:

- `batch_ocr_example.py` — whole-PDF Qwen OCR, grayscale-JPEG rendering,
  concurrency, resumable batches.
- `deepseek_format_example.py` — cached fixed system prompt, 7 items per
  call, resumable, empty-response retry.

These are reference implementations — adapt the prompts to the task at hand.

"""Qwen vision API client — OCR for images and scanned PDFs.

Alibaba DashScope, OpenAI-compatible endpoint. Model qwen3-vl-plus supports
image input (DeepSeek's API does NOT — use this for anything visual).

Key: reads api-sk.json ({"qwen": "sk-..."}) from the current directory,
or pass key= explicitly.

Typical flow for a scanned PDF:
    pages = render_pdf("scan.pdf", "_pages")      # PDF -> JPEG pages
    text  = ocr(pages, "逐字识别图片中的所有文字")   # all pages, one request
"""
import base64
import json
import time
from pathlib import Path
from urllib import request, error

ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_MODEL = "qwen3-vl-plus"


def load_key(name: str = "qwen", path: str = "api-sk.json") -> str:
    return json.loads(Path(path).read_text())[name]


def _mime(p: Path) -> str:
    return "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"


def ocr(image_paths, prompt: str, key: str | None = None,
        model: str = DEFAULT_MODEL, max_tokens: int = 16384,
        timeout: int = 600, retries: int = 3) -> str:
    """OCR one image or several images in a single request.

    image_paths: a path (str/Path) or a list of them. Passing all pages of a
    PDF at once keeps document context intact. Keep the total payload modest
    (render pages as grayscale JPEG ~150 dpi) to avoid request-size limits.
    """
    if isinstance(image_paths, (str, Path)):
        image_paths = [image_paths]
    image_paths = [Path(p) for p in image_paths]
    if key is None:
        key = load_key()

    content = [{"type": "text", "text": prompt}]
    for p in image_paths:
        b64 = base64.b64encode(p.read_bytes()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:{_mime(p)};base64,{b64}"}})
    payload = {"model": model,
               "messages": [{"role": "user", "content": content}],
               "max_tokens": max_tokens}
    req = request.Request(
        ENDPOINT, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})

    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            return data["choices"][0]["message"]["content"]
        except error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"  HTTP {e.code} (try {attempt+1}): {body[:200]}")
            time.sleep(3 * (attempt + 1))
        except Exception as e:
            print(f"  ERR (try {attempt+1}): {e}")
            time.sleep(3)
    raise RuntimeError(f"Qwen OCR failed after {retries} retries")


def render_pdf(pdf_path, out_dir, dpi: int = 150, grayscale: bool = True,
               quality: int = 80) -> list[Path]:
    """Render each PDF page to a JPEG (needs `pip install pymupdf`).

    Grayscale JPEG at 150 dpi keeps a 14-page scan around 5 MB base64, well
    under the API request-size limit, while staying readable for OCR.
    """
    import fitz  # PyMuPDF

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(doc.page_count):
        p = out_dir / f"p_{i+1:03d}.jpg"
        if not p.exists():
            cs = fitz.csGRAY if grayscale else fitz.csRGB
            doc[i].get_pixmap(dpi=dpi, colorspace=cs).save(p, jpg_quality=quality)
        pages.append(p)
    doc.close()
    return pages


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1])
    user_prompt = sys.argv[2] if len(sys.argv) > 2 else "逐字识别图片中的所有文字。"
    if target.suffix.lower() == ".pdf":
        imgs = render_pdf(target, "_pages_tmp")
        print(ocr(imgs, user_prompt))
    else:
        print(ocr(target, user_prompt))

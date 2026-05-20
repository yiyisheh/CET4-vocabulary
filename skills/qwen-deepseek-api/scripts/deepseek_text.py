"""DeepSeek text API client (OpenAI-compatible).

Models: deepseek-v4-pro (strongest), deepseek-v4-flash (cheaper/faster).
TEXT ONLY — the API rejects image input (`unknown variant 'image_url'`).
For anything visual use qwen_vision.py instead.

Prompt caching: DeepSeek caches the longest common request prefix
automatically. Keep the system message byte-for-byte identical across calls
(put all fixed instructions + few-shot examples there, only vary the user
message) to get cache hits and a big cost cut on bulk jobs.

Key: reads api-sk.json ({"deepseek": "sk-..."}) from the current directory,
or pass key= explicitly.
"""
import json
import time
from pathlib import Path
from urllib import request, error

ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-pro"


def load_key(name: str = "deepseek", path: str = "api-sk.json") -> str:
    return json.loads(Path(path).read_text())[name]


def chat(system: str, user: str, key: str | None = None,
         model: str = DEFAULT_MODEL, temperature: float = 0.3,
         max_tokens: int = 4096, timeout: int = 300,
         retries: int = 5, min_len: int = 1) -> str:
    """One chat completion. `system` should be identical across a batch of
    calls so DeepSeek's prompt cache kicks in. Empty/short replies are retried.
    """
    if key is None:
        key = load_key()
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = request.Request(
        ENDPOINT, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})

    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            content = data["choices"][0]["message"]["content"].strip()
            if len(content) < min_len:
                raise ValueError(f"response too short: {content!r}")
            return content
        except error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"  HTTP {e.code} (try {attempt+1}): {body[:200]}")
            time.sleep(4 * (attempt + 1))
        except Exception as e:
            print(f"  ERR (try {attempt+1}): {e}")
            time.sleep(4)
    raise RuntimeError(f"DeepSeek call failed after {retries} retries")


def batch_chat(system: str, user_messages: list[str], workers: int = 6,
               **kwargs) -> list[str]:
    """Run many chat() calls that share one cached system prompt.

    The first call is made alone to warm the server-side prompt cache, then
    the rest run concurrently. Returns replies in input order.
    """
    import concurrent.futures

    if not user_messages:
        return []
    results: list[str] = [""] * len(user_messages)
    results[0] = chat(system, user_messages[0], **kwargs)  # warm the cache
    if len(user_messages) == 1:
        return results

    def one(i):
        return i, chat(system, user_messages[i], **kwargs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, txt in ex.map(one, range(1, len(user_messages))):
            results[i] = txt
    return results


if __name__ == "__main__":
    import sys
    print(chat("You are a helpful assistant.", sys.argv[1]))

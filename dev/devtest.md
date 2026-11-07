# 本地验证（`scripts/devtest/`）

本机**没装 playwright / puppeteer 的包**，只有 Playwright 早先下好的浏览器二进制（`~/Library/Caches/ms-playwright/chromium_headless_shell-*/`）。别 `import playwright`，用仓库自带的零依赖工具（Node ≥21）。产物一律落 `tmp/`。

```bash
# 秒开的测试页：真实词条 + 空音频
python scripts/devtest/make_testpage.py            # 前 120 词
python scripts/devtest/make_testpage.py 60 400     # 60 词，从第 400 条起（前 100 词多是虚词，没有词根卡）
#   → tmp/devtest/testpage.html

# 驱动无头浏览器：依次求值 JS 表达式，可选截图
node scripts/devtest/cdp.mjs "file://$PWD/tmp/devtest/testpage.html" \
  '["document.getElementById(\"start\").click()","document.querySelectorAll(\".entry\").length"]' \
  tmp/devtest/shot.png
```

- 每个表达式的返回值按 JSON 打印（promise 会 await），异常会抛出——同时也是控制台报错检查。
- 表达式列表里可混入指令：`"__OFFLINE__"` / `"__ONLINE__"` 断网与恢复，`"__RELOAD__"` 重载并等页面稳定。
- 验托管版必须起 http：`cd docs && python3 -m http.server 8123`，打开 `http://127.0.0.1:8123/index.html`。`file://` 下 SW 不注册，缓存、更新、音频包都验不了。验内嵌音频开根目录的单文件版。

`cdp.mjs` 里已修掉的坑，别退回去：
1. 必须带 `--autoplay-policy=no-user-gesture-required`，否则合成点击不算手势，`play()` 一律 `NotAllowedError`（另加 `--mute-audio`）。
2. 断网要同时下发给 service worker 的 target，只设页面 target 没用。
3. 页面自己重载后要换到新的 execution context 再求值；协议级错误不能吞成 `undefined`。

探针：播放器是 `new Audio()`，不在 DOM 里，要挂 `HTMLMediaElement.prototype.play` 才看得到；看 state 用 `JSON.parse(localStorage.cet4_reader_v3)`。

其他工具：`classify_ex_voice.py`（例句音色二分）、`tlog_report.py`（[stats.md](stats.md)）。

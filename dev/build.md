# 构建

## 流水线

```
output/high_freq_cet4_df.txt ─┐  词表（rank、音标；旧释义只作后备）
intermediate/senses.json ─────┤  真题义项、例句、短语（data.md）
intermediate/roots.json ──────┤  词根
intermediate/core.json ───────┤  核心意象
  （+ pyphen 音节）           ┴─ build_dataset.py ─→ intermediate/entries_full.json
                                         │
                                         ├─ make_pdf_optimized.py ─→ 三份 PDF（仓库根目录）
                                         │
synbook/ + web/synbook.html ─ build_synbook.py ─→ docs/synbook.html（+ 根目录单文件副本）
                                         │            ↓ 书的字节计入版本哈希、进 SW 预缓存
intermediate/audio/{us,ex}/ ─────────────┤
web/template.html · web/pwa/ ────────────┴─ build_html.py ─→ 英语四级单词背诵.html（单文件版）
web/supabase-config.json · legacy_rank_v1.json             └→ docs/（托管版）
```

## 命令

```bash
pip install -r requirements.txt   # 另需 ffmpeg（音频去静音、测响度）；spaCy 模型见 ../README.md#复现

# 数据（改了词根 / 核心意象 / 义项后，按顺序）
python scripts/merge_roots.py          # → roots.json
python scripts/merge_core.py           # → core.json（在 roots 之后：有词根的词不做核心意象）
python scripts/merge_senses.py r1      # → senses.json / phrases.json（读 core.json 决定释义截几个）
python scripts/build_dataset.py        # → entries_full.json

# 音频（只在音频有变时）
python scripts/fetch_ex_audio.py       # 例句朗读，跳过已有文件
python scripts/measure_loudness.py     # 改了任何音频后都要跑，build_html 之前

# 成品
python scripts/make_pdf_optimized.py   # 三份 PDF
python scripts/build_synbook.py        # 必须在 build_html 之前
python scripts/build_html.py           # 单文件版 + docs/
```

只改了 `web/template.html`：只跑 `build_html.py`。只改了辨析书：`build_synbook.py` + `build_html.py`。

PDF 字体路径写在 `make_pdf_optimized.py` 的 `FONT_PATH`（默认 macOS 的 Arial Unicode）。改 PDF 版式：`VARIANTS` 列三份，`entry_block()` 是背诵版词条，`gap_block()` 是查缺补漏版。正文段落都开了 `wordWrap="CJK"`；同一段里别混字号（reportlab 会算错段高、叠字）。

## 两种产物：一份模板，两种形态

| | 单文件版 `英语四级单词背诵.html` | 托管版 `docs/` |
|---|---|---|
| 音频 | base64 内嵌 | 两个原始字节包 `audio-{us,ex}.<哈希>.bin` |
| 用途 | AirDrop 一个文件离线用 | GitHub Pages / PWA |
| 判据 | `window.AUDIO_INDEX === null` | `window.AUDIO_INDEX` 有值 |

拆成托管版是为了：首屏只等外壳不等音频；改网页只重下外壳，包名（内容哈希）不变的音频一个字节不重下；不付 base64 的 +33% 体积。

包格式：1250 条 mp3 首尾相接，`AUDIO_INDEX` 给出 `{键: [偏移, 长度]}`（us 按单词、ex 按 rank）。网页里取字节只有一个入口 `clipBytes(which, key)`，见 [audio.md](audio.md)。

### `build_html.py` 替换的占位符

| 占位符 | 内容 |
|---|---|
| `__DATA__` | 1250 词条 |
| `__AUDIO_US__` / `__AUDIO_EX__` | 单文件版填 base64；托管版填空 |
| `__AUDIO_INDEX__` | 托管版填包索引；单文件版填 `null` |
| `__AUDIO_GAIN__` | 每条音频的播放增益（[audio.md](audio.md#响度归一化)） |
| `__CACHE_NAME__` | `cet4-1250`，与 `sw.js` 同一个桶 |
| `__SYNC_CONFIG__` | `web/supabase-config.json`，没有则 `null`、同步禁用 |
| `__LEGACY_V1__` | 冻结的旧序号表（[sync.md](sync.md#身份键按单词不按序号)） |
| `__BUILD_INFO__` | `{v: 外壳哈希, t: 构建时间}`；`v` 在注入它之前算，同内容重建版本号不变 |
| `sw.js` 的 `__PRECACHE__` / `__KEEP__` / `__BUILD_HASH__` | 见 [pwa.md](pwa.md) |

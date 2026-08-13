# CET-4 背单词网页 —— 开发交接文档 (HANDOFF)

> 这份文档是**给下一个 AI / 开发者的唯一入口**。读完它 + 它指向的几个小文件，就能完整理解并二次开发这个网页，**无需也不要打开任何几十 MB 的大文件**。

---

## 0. ⚠️ 给 AI 的第一条规则：该读什么，绝对别读什么

| 类别 | 文件 | 大小 | 说明 |
|---|---|---|---|
| ✅ **网页源码（读这个）** | `web/template.html` | ~74 KB（约 1300 行） | **整个网页的唯一源文件**（HTML+CSS+JS 一体）。改网页 = 改这里。 |
| ✅ 构建脚本 | `scripts/build_html.py` `build_dataset.py` `merge_roots.py` `fetch_audio.py` `fetch_ex_audio.py` `resynth_us_audio.py` `make_pdf_optimized.py` | 2–5 KB | 见 §4 流水线 |
| ✅ PWA 资源 | `web/pwa/manifest.webmanifest` `web/pwa/sw.js` `web/pwa/icon-*.png` | <30 KB | 见 §10 部署 |
| ✅ 同步配置 | `web/supabase-config.json` | <1 KB | 仅含**可公开**的 publishable key |
| ✅ 词条数据 | `intermediate/entries_full.json` | 544 KB | 1250 词最终数据（无音频），可读 |
| ✅ 词根数据 | `intermediate/roots.json` | 186 KB | 词根/词缀/合成拆解 |
| ✅ 词表源 | `output/high_freq_cet4_df.txt` | 328 KB | rank+音标+释义+例句（DF 排序） |
| 🚫 **AI 绝对别读** | `英语四级单词背诵.html` | **49 MB** | 构建产物（**单文件版**：内嵌 2500 条 base64 音频），读了会撑爆上下文 |
| 🚫 别读（构建产物） | `docs/index.html` | 562 KB | **托管版外壳**：无音频，只有 CSS+JS+1250 词文本。小归小，它仍是产物，改网页请改 `web/template.html` |
| 🚫 **AI 绝对别读** | `docs/audio-*.bin` | **36 MB** | 托管版的两个音频包（原始 mp3 字节拼接），文件名带内容哈希 |
| 🚫 **AI 绝对别读** | `intermediate/audio/` | **71 MB** | 3750 个 mp3 源（us 16M / uk 30M / ex 25M），构建输入，别遍历 |

**一句话**：想看/改网页，永远打开 `web/template.html`；`docs/` 和根目录那份 `.html` 全是**自动生成的产物**，不是源码。
> 注：`uk/` 30 MB 仍在磁盘和 git 里，但**不再被嵌进成品**（§4）。

### 0.1 📌 所有临时产物一律放 `tmp/`
截图、录屏、生成的测试页、调试产物——**全部写进仓库根目录的 `tmp/`**，不要散在 `/tmp`、系统临时目录或项目根目录。理由：`tmp/` 已在 `.gitignore` 里（不污染仓库），但它在项目里，**用户能直接打开来看**。

- **工具本身入库、产物进 `tmp/`**：验证工具在 `scripts/devtest/`（随仓库分发，见 §9.1），它生成的 `tmp/devtest/testpage.html` 和截图则不入库。
- 其余随手产物（`shot-*.png`、录屏 `.mp4`、临时 json…）也丢 `tmp/`，不用清理。

---

## 1. 这个项目是什么

两条产物线，共用同一份 1250 词数据：

1. **PDF 背诵版**（打印用）—— `英语四级高频单词彩色背诵版(优化).pdf`
2. **iPad 背单词网页**（背单词用）—— `英语四级单词背诵.html`（**单文件离线网页**）+ `docs/`（托管版，装到主屏幕后是 **PWA**）

> 语料抓取 / 词频统计 / OCR 那一大套**上游**流水线见 `README.md`，本文档聚焦**下游的网页与优化版 PDF**。

数据是从近五年(2021–2025)四级真题统计的高频词，按文档频率(DF)排序取 top-1250。

---

## 2. 目录地图（只列与网页相关的）

```
English/
├── WEB_HANDOFF.md            ← 本文档
├── README.md                 ← 上游语料/词频流水线说明
├── SPEC-例句配音接入.md       ← 例句 TTS 接入时的设计说明（历史，内容已并入本文 §7.4）
│
├── web/                      ← 【网页源码集中在这里】
│   ├── template.html         ← 网页唯一源文件（构建时注入数据/音频/配置）
│   ├── supabase-config.json  ← 同步配置（publishable key）
│   └── pwa/                  ← manifest / sw.js / icon-180·192·512.png
│
├── scripts/                  ← 构建脚本（下游网页相关的只有这几个，其余是上游语料/OCR 脚本）
│   ├── build_dataset.py      ← 词表+词根+音节 → entries_full.json
│   ├── build_html.py         ← 注入数据+音频+同步配置 → 成品 html + docs/
│   ├── merge_roots.py        ← 合并各来源词根 → roots.json
│   ├── build_roots.py        ← （备用）DeepSeek 生成词根；**已不用**，词根由子agent产出
│   ├── fetch_audio.py        ← 下载 2500 条有道 mp3 → intermediate/audio/{us,uk}/
│   ├── fetch_ex_audio.py     ← edge-tts 合成 1250 条例句朗读 → intermediate/audio/ex/
│   ├── resynth_us_audio.py   ← 按编码指纹把不想要的有道音色换成 edge-tts Ava（§7.5；--dry-run/--restore）
│   ├── align_audio_silence.py← （备用）旧的“补静音对齐”脚本，现已非必需，见 §7.3
│   ├── make_pdf.py           ← PDF 底层排版
│   ├── make_pdf_optimized.py ← 生成优化版 PDF
│   └── devtest/              ← 【本地验证工具】make_testpage.py + cdp.mjs（§9.1）
│
├── intermediate/             ← 数据与中间产物
│   ├── entries_full.json     ← 【最终词条数据】1250 词（544 KB）
│   ├── roots.json            ← 【最终词根数据】（186 KB）
│   ├── compounds.json        ← 手工补的合成词（work+place…）
│   ├── recall_manual.json    ← 手工补的词缀词（powerful…）
│   ├── root_chunks/          ← 14 组 in_*/out_*.json（首轮子agent词根产出，共 28 个文件）
│   ├── recall_chunks/        ← 8 组 in_*/out_*.json（召回轮，共 16 个文件）
│   ├── audio/                ← 🚫 71MB mp3 源，别读：us/ uk/ 各 1250，ex/ 1250 + voices.json
│   └── （entries_v2/examples/liut969_dict/ds_batches* 均为上游历史产物，网页不用）
│
├── output/high_freq_cet4_df.txt  ← 词表源（rank/音标/释义/例句）
│
├── docs/                     ← 【GitHub Pages 托管目录】§4.1 的托管形态
│   ├── index.html            ←   外壳 562KB（CSS+JS+1250 词文本，**不含音频**）
│   ├── audio-us.<hash>.bin   ←   单词音频包 13.6MB（原始 mp3 字节拼接）
│   ├── audio-ex.<hash>.bin   ←   例句音频包 22.8MB
│   └── manifest + sw.js + 3 图标
│
├── tmp/                      ← 【所有临时产物放这里】gitignore，但用户看得见（§0.1）
│   ├── devtest/testpage.html ←   §9.1 生成的测试页
│   └── *.png / *.mp4 …       ←   截图、录屏等随手产物
│
├── 英语四级单词背诵.html      ← 🚫 49MB 成品（AirDrop 单文件离线版）；**已 gitignore**，可重生成
└── 英语四级高频单词彩色背诵版(优化).pdf
```

> ⚠️ `web/data.js` **已不存在**：`build_dataset.py` 只写 `entries_full.json`，网页的数据由 `build_html.py` 直接注入 `__DATA__`。（`build_dataset.py` 顶部 docstring 里还留着 data.js 的旧说法，是过时注释。）

---

## 3. 网页是什么样的（功能总览）

一个 iPad/手机上背四级单词的**单文件离线网页**（无框架、无前端构建：一份 HTML 里塞了 CSS + JS + base64 音频）。

### 3.1 长什么样（⚠️ 别按"卡片 App"想象）
**没有卡片、没有阴影、没有色块底、没有任何彩色标签。** 视觉目标是**贴着优化版 PDF 1:1**：纯白（或所选背景色）底上的一份**多栏文本列表**，词条之间只有一条 `rgba(0,0,0,.08)` 的发丝线。字号全部写成 `pt × --fs`，所以 100% 缩放时和 PDF 同大。1200px 宽自动排 3 栏。

一条词条自上而下（DOM 顺序即此顺序）：

| 行 | 类 | 实际样子 |
|---|---|---|
| 序号 + 单词 | `.num` / `.hw` | `401.` 灰色 tabular 数字 + `rather` **蓝色粗体**（`--blue` #1f5fa8） |
| 音标 | `.ipa` | `英[/ˈrɑːðə(r)/] 美[/ˈræðər/]` —— **深灰细字**（`--sub`，7.5pt，font-weight 300） |
| 释义 | `.def` | `adv.相当; 宁愿; 更确切地说.` 正文色 8.5pt |
| 词根词缀卡 | `.root` | **不是绿色、不是标签**：一整块**灰色小字**（`--gray` #8a8a8a，8pt），左缩进 6px。每行 `前缀 in- = 在…`（词性灰、词素**加粗**、= 释义）；最后一行是 `▸` 开头的合成汇总 `▸ in- 在… + stead 位置 ⇒ 处在(别人的)位置上 ⇒ 代替; 反而`。约 42%（523/1250）的词有 |
| 例句 | `.ex` | `例句： The statement…（以下声明供您参考。）`。英文 + 全角括号里的中文。**几乎全部出自真题语料**；`例句（自编）：` 现仅剩 **1 条**（rank 110 `comprehension`——该词在 31 套卷子里只作「Listening Comprehension」标题出现，无成句，见 §7.5） |

顶栏：左「四级高频 1250」蓝色粗体 + 右「设置」小按钮。
底栏：`‹` … `1 / 8` 圆角药丸页码 … `›`。

- **点序号/左侧空白** → 灰色删除线标记「已掌握」（`markStyle`：变灰划线 / 仅划线）
- **点单词** → 音节拆分 `com·po·si·tion ⇄ composition` 并发音
- **点例句** → 朗读整句（**edge-tts 生成，Andrew/Brian 两男声按词 1:1 随机，1250 条已内嵌离线**；见 §7.4）。⚠️ 热区**已被刻意缩短**（不是"整行加大"）：上方那 6px 间距走 margin 不可点，只有紧贴文字的 padding box 可点，避免点释义误触朗读。可调「例句播放前延迟 0–50ms」
- **点词条其他处** → 发音（**1250 条美音已 base64 内嵌，离线可用**；可调「跳过开头静音 0–100ms」。⚠️ 英音(UK)已移除、口音切换已删，见 §7）
- **翻页**：底部页码栏两侧空白区（`‹`/`›`，`#barnav-l/#barnav-r`）点击翻上/下一页；左右滑动分页启用 `scroll-snap-stop:always`，轻划最多前进一页（不影响触控板/iPad）
- **快速跳页滑块**：**点底部中间那颗「1 / 8」药丸页码**（`#pageno`）弹出 —— 左右分页模式是贴着底栏上方的横滑块 `#wheelH`（带「第 N / M 页」标签），上下无缝模式是贴右侧的竖滑块 `#wheelV`。拖动即时跳页。**收起方式**：再点一次药丸，或**点页面上任何别处**（这一下点击会被吞掉，不会顺带划词/发音/翻页），进设置页也会收起
- **自测的"留白"实际是浅色块**：`.mask` 把释义/词根整块变成 `--panel`（#f4f6f9）的**圆角浅灰块**、文字透明（连后代一起），高度不变所以不重排；例句英文常显、中文被同样的块盖住。点块内任意处 → 该词条所有块**一起**解开。

### 3.2 设置页（自上而下的实际顺序）
标题「四级高频单词 · 背诵」+ 副标题「2021–2025 真题 · top 1250 · 含词根词缀 · 排版对齐优化版 PDF」；每项一行（左标题+灰色说明，右控件：蓝色 switch / seg 按钮组 / 滑块 / 数字框）；**「开始背诵」是固定在底部的蓝色大按钮**（`position:fixed`，会盖住最底下的内容，往上滚才看得到被盖住的行）。
1. 去掉已经划掉的单词（不实时·进出设置页才重载去掉）
2. **状态池模式（莱特纳）** + 子行「池大小 / 推进阈值 / 重置范围」+ 当前范围账目（默认 40 / 15，步长=池大小−阈值，见 §13）
3. 自测（释义+词根词缀卡一起留白·点卡片同步解锁）+ 子行 **例句翻译随卡片解锁**（英文常显·中文随卡片一起遮/解）
4. 显示例句开关
5. 实时累计词数（多间隔 chip·分界线深灰小标·靠左·数当前显示的词）
6. 划线样式 / 显示分界线 / 翻页方式（左右分页·上下无缝）
7. 跳过开头静音（0–100ms）/ 例句播放前延迟（0–50ms）
8. 字号 / 栏数（自动按 PDF 栏宽铺满）/ 间距 / 背景色（预设+自定义 #）
9. **多端同步** / **离线缓存进度** / **版本号+检查更新**（§10.2）/ 开发者模式
10. 最后是灰底 `.hintbox` 操作说明

### 3.3 其它
- 分页：按**实测高度装箱**，像 PDF 一样填满一栏再下一栏（不是等分），宽屏自动多栏
- **多端同步**（Supabase，§8）：同一同步码的设备之间同步「划线」与「自定义色号列表」，其余一概不同步

---

## 4. 数据流水线（怎么从词表变成成品）

```
output/high_freq_cet4_df.txt  ─┐
intermediate/roots.json ───────┤─ build_dataset.py ─→ intermediate/entries_full.json
  (+ pyphen 音节)              ┘        │
                                        ├─ make_pdf_optimized.py ─→ 优化版 PDF
intermediate/audio/us/*.mp3 ───────────┤   （uk/ 不参与构建）
intermediate/audio/ex/*.mp3 ───────────┤
web/template.html ─────────────────────┤─ build_html.py ─→ 英语四级单词背诵.html（根，单文件）
web/supabase-config.json ──────────────┤                └→ docs/index.html + docs/{pwa资源}
web/pwa/* ─────────────────────────────┘
```

### 4.1 ⚠️ 两种发布形态（本轮重构，改构建/音频前必读）

**同一份 `web/template.html` 构建出两种形态**，因为它们要解决的问题相反：

| | 单文件版 `英语四级单词背诵.html` | 托管版 `docs/` |
|---|---|---|
| 音频在哪 | base64 内嵌在 HTML 里 | 两个独立二进制包 `audio-{us,ex}.<hash>.bin` |
| 体积 | 49 MB 一个文件 | 外壳 **562 KB** + 包 36 MB |
| 首屏 | 等 49 MB 下完才看得到第一个词 | **562 KB 到了就能背**，音频在后台流式补 |
| 用途 | AirDrop 一个文件就能离线用 | PWA / GitHub Pages |
| 判据 | `window.AUDIO_INDEX === null` | `window.AUDIO_INDEX` 有值 |

**为什么要拆**（不是为了好看，是三个实打实的毛病）：
1. **首屏**：内嵌时 98.7% 的字节是音频，而背前几个词根本用不到。
2. **更新成本**：内嵌时改一行 CSS → `index.html` 变 → 全体用户重下 49 MB。拆开后只重下 562 KB 的外壳，**音频包名没变就一个字节都不重下**。
3. **体积**：base64 是**无损**的字节↔文本映射（`atob` 原样还原，与音质无关），存在的唯一理由是"要塞进 HTML"，代价是固定 +33%。托管版直接存原始字节：**48.6 MB → 36.4 MB**。

**包格式**：把 1250 条 mp3 原始字节首尾相接，`AUDIO_INDEX` 给出 `{键: [偏移, 长度]}`（us 按单词、ex 按 rank），播放时 `buf.slice(off, off+len)` 取出来。索引跟着外壳走（58 KB，已含在外壳那 562 KB 里）。

**文件名带内容哈希**是整套缓存策略的地基：音频一变 → 哈希变 → 文件名变 → 对浏览器是全新 URL，**不可能拿到旧的**；音频没变 → URL 不变 → 命中缓存、不重下。比靠 `max-age` 猜可靠得多。

**谁负责下载**：外壳由 `sw.js` 在 install 时预缓存（562 KB，瞬间）；**音频包由网页自己 `fetch`**、用流式 reader 边读边计数（这才有真进度条，§10.0），下完写进同一个 Cache API 桶。SW 的 `PRECACHE` **故意不含音频包**——否则同样的 36 MB 会被下两遍。

`build_html.py` 把模板里这些占位符替换掉（**两种形态填的内容不同**，§4.1）：
- `__DATA__` → 1250 词条 JSON（两种形态相同）
- `__AUDIO_US__` / `__AUDIO_EX__` → 单文件版填 `{word|rank: base64 mp3}`；**托管版填空字符串**。**UK 已移除**（原来还有 `__AUDIO_UK__`，为减重删掉）
- `__AUDIO_INDEX__` → 托管版填 `{us:{file,bytes,index},ex:{…}}`；**单文件版填 `null`**
- `__CACHE_NAME__` → `cet4-1250`，与 `sw.js` 的桶名同一个常量（网页要往同一个桶里写音频包）
- `__SYNC_CONFIG__` → `web/supabase-config.json` 内容（无则 `null`，同步自动禁用）
- `__BUILD_INFO__` → `{v:内容哈希, t:构建时间}`，设置页「版本」行展示 + 「检查更新」用（见 §10.1）。`v` = **外壳的哈希**（包名在外壳里，所以音频变了版本也会变），在**注入 build-info 之前**算，只随内容变、不随时间戳变——同内容重建版本号不变、不会白触发更新。两种形态共用同一个版本号
- `sw.js` 里还有 `__PRECACHE__` / `__KEEP__` 两个清单和 `__BUILD_HASH__`（外壳哈希，§10.1 解释它为什么必须在）

> 体积：单文件 **49MB**；托管版外壳 **562KB** + 音频包 **36MB**（us 13.6 + ex 22.8）。删 UK 前是 ~89MB；换掉 86 条冗长音源省了 ~3MB（§7.5），去掉 base64 又省了 12MB（§4.1）。
> **iPad 无声已在真机复验通过**（2026-08-02）：改成「Web Audio 只解码、`<audio>` 出声」（§7.1）之后正常。体积从来不是原因；若想把 UK 加回来，现在托管版加一个包即可，外壳不受影响。

---

## 5. `web/template.html` 内部结构（改网页看这节）

结构顺序：`<style>`（全部 CSS）→ `#settings` 设置页 DOM → `#top` / `#pages` / `#measure` / `#dev` / `#bar` → **5 个 `<script>`**：
1. `<script type="application/json" id="audio-us">__AUDIO_US__</script>`（**单文件版**才有内容；托管版是空的）
2. `<script type="application/json" id="audio-ex">__AUDIO_EX__</script>`（同上）
3. `window.CET4` / **`window.AUDIO_INDEX`**（托管版的音频包索引，单文件版为 `null`）/ `window.BUILD_INFO` / `window.CACHE_NAME`
4. `window.SYNC_CONFIG`
5. **网页主逻辑 IIFE**（约 930 行，从 `var DATA = window.CET4` 到末尾的「检查更新」小 IIFE）

> ⚠️ 模板**一份源码同时供两种形态**（§4.1）。判据只有一个：`window.AUDIO_INDEX` 是不是 `null`。

### 5.1 关键 CSS 类
- `.entry`（词条，`position:relative`，`padding-left:14px` 就是"序号前那条可点的空白"）
- `.headline` > `.num`(灰、tabular) + `.hw`(蓝、700)；再依次 `.ipa`(--sub, 300 细体) `.def` `.root` `.ex`
- **`.root` 没有任何专属颜色/边框**：`.root .p` 和 `.root .sum` 都是 `--gray` 8pt，只有 `.root .p .txt`（词素本身）是 `font-weight:700`。`padding-left:6px` 的缩进是它唯一的"卡片感"
- `.ex` 的**点击热区 = padding box**：上 padding 只有 1px、上方间距走 margin（不可点），下 padding 5px 留出舒适点按；左右负 margin 让文字与 `.def` 对齐；`:active` 时才显示 `--panel` 底
- `.mask`（自测遮蔽：`color:transparent !important` + `.mask *` 后代同样透明 + `--panel` 底 + 5px 圆角；高度不变故不重排）、`.milestone`（累计小标，靠左、`--sub`、6.8pt、opacity .75）
- 设置页：`.row`/`.row.subrow`（子项行，左侧 2px 蓝竖线 + 缩进）、`.seg`、`.switch`、`.slider`、`.chips/.chip`（累计间隔，`::after` 自带 ✕）、`.poolnums`（状态池两个数字框）、`.swatches/.sw`、`.cachebar`、`.minibtn`、`.hintbox`、`#start`(fixed 底部大按钮)
- 划线：`.entry.marked .num::before`（`left:-14px; right:0`，从最左横穿到序号右缘的 1.5px 灰线）；`.entry.marked{opacity:.5}`（变灰样式）；`#pages.markline` 取消变灰（仅划线）
- 分栏：`.page{display:flex}` + `.col`，栏数/栏宽由 JS 算；`#pages.h` 用 `scroll-snap-type:x mandatory` + `scroll-snap-stop:always`
- 主题变量全在 `:root`（`--bg/--card/--ink/--sub/--gray/--blue/--hair/--mark/--panel` + `--fs/--gap/--padh`），`applyTheme()` 按背景色亮度（`lum<0.42`）整套切深/浅色

### 5.2 状态 `state`（存在 `localStorage`，键 `cet4_reader_v3`）
```js
{
  removeMarked:false,        // 「去掉已划掉的单词」；true=去掉。不实时移除，只在 paginate()（设置页开/关）时经 visible() 过滤。旧的 showMarked 会自动迁移为 !showMarked
  poolMode:false,            // 状态池（莱特纳）模式总开关；开启后 visible() 只回「rank ≤ poolMax 且没划掉」的词。【本地】见 §13
  poolSize:40,               // 池大小：要始终保持的「没划掉的词」数量（默认 40）；推进步长 = poolSize-poolLow。【本地】
  poolLow:15,                // 推进阈值：剩余 ≤ 此值就推进（默认 15，强制 1..poolSize-1）。【本地】
  poolMax:0,                 // **当前上界**，状态池的唯一状态；只前进不后退。老版的 pool:[] 数组会自动迁移成它。【本地】
  selftest:false,            // 自测：true=释义(.def)+词根卡(.root)加 .mask 遮蔽(透明字+浅色底,含后代;高度不变故不重排),data-act=reveal。点任一遮蔽处→同 entry 内所有 .mask 一起解锁(reveal-all)、再点发音。切换要 paginate()。【本地】
  showEx:true,               // 是否渲染例句行(.ex)；false=不渲染(高度变→切换要 paginate())。【本地】
  maskExTrans:true,          // 自测子项：例句中文翻译也随卡片一起遮/解(英文原句常显)。仅 selftest 时生效。exEnglish()/exTrans() 按首个 (（ 切分。切换要 paginate()。【本地】
  counters:[],               // 实时累计词数的「间隔」列表(如 [100,25])；空=不显示。每 paginate() 由 computeMilestones() 按当前可见列表算 rank→累计数，分界线上渲 .milestone 深灰小标。【本地】
  markStyle:"dim"|"line",    // 划线样式
  divider:true,              // 词条分界线
  mode:"h"|"v",              // 左右翻页 / 上下无缝
  accent:"us",               // 口音；UK 已移除，字段仅作 audioMap 的 key 保留，实际恒为 "us"
  fontScale:1.0,             // 字号（pt×此值，默认≈PDF 1:1）
  cols:"auto"|"2"|"3"|"4",   // 栏数
  spacing:0.35,              // 间距(0..1 → 栏距/留白)
  skipMs:40,                 // 起播引子控制：lead = 100-skipMs（滑块 0..100，默认留60ms引子，见§7）；旧的 0..314 值会自动迁移
  exDelay:0,                 // 例句播放前延迟(ms, 0..50)；例句音频已去前置静音（§7.4）
  bg:"#ffffff",              // 当前背景色（【不同步】）
  customColors:[hex...],     // 自定义色号列表（【同步】，取并集）
  marks:{ rank:{v:0|1,t:ms} },// 划线：每词{是否+时间戳}（【同步】，LWW）
  anchor:rank,               // 上次所在页的首词，用于恢复位置
  syncCode:"",               // 同步码（【本地】，各设备自填）
  dev:false,                 // 开发者模式（底部波形面板，【本地】）
  devH:170                   // 开发者面板高度px（可拖拽，【本地】）
}
```
> 改了 state 结构记得升 `LS` 版本号或写迁移（见 `marked→marks` 的迁移示例）。

### 5.3 关键函数
- `paginate()`：**先 `ensurePool()`**(状态池补水,§13)→读容器宽高→算栏数(auto 时按 `330*fontScale` 目标栏宽)→`visible()` 取可见列表→`computeMilestones(可见列表)` 算累计小标位置→用隐藏的 `#measure` 实测每条高度(含小标)→装箱成页→`render()`。累计小标随词条测量,故装箱高度天然正确
- **`visible()`**：唯一的"哪些词参与排版"入口。`poolMode` 时=池内且未划掉的词；否则按 `removeMarked` 过滤或全量。**过滤只在 paginate 时发生**,读的时候划词不会让页面在手指底下重排
- **`ensurePool()` / `poolRemain()` / `poolNeedsRefill()`**：状态池引擎，见 §13
- **`computeMilestones(list)`**：填 `milestoneAt{rank:累计数}`。对可见列表每个 1-based 位置 pos,若能被 `state.counters` 里任一间隔整除就记一个小标(值=pos,即"数当前显示的词");公倍数位置只记一次(按 rank 去重)。空 counters→空 map。`entryHTML` 末尾据此渲 `.milestone`
- `render()`：拼 HTML，设 `#pages` 的 class（`h`/`v` + 可选 `markline`、`nodivider`）。**没有 hideMarked 类**——去掉已划掉的词是在 `visible()` 里过滤掉的，不是 CSS 隐藏
- 点击委托（`pagesEl` 上一个 click）：`.ex`(data-act=ex)→`speakEx`(朗读例句)；**自测态下遮蔽处(data-act=reveal，含 .def/.root/.extrans)→首次点去掉同 entry 内所有 `.mask`(并移除其 data-act，恢复原生行为)=同步解锁、再点发音**；判定点在序号左侧→`mark`；点单词→`syl`(音节切换+发音)；其他→发音
  - `mark` 分支**唯一会重排页面的情况**：状态池模式下这一划让池内剩余触到低水位 → `ensurePool()` + `paginate()`（下一轮突击，§13）
- **`speakEx(rank)`**：例句朗读。`clipBytes("ex", rank)` 取字节 → 复用 §7 的 decode+缓存内核 → `playEx()` → `playClip()`（`<audio>` 出声）。例句音频**已在构建前去掉前置静音**，故 `off=onset(≈0)`；`exDelay`(0..50ms)的"播放前静默"以**前置静音样本形式编进 WAV**。无内嵌/无解码则静默（例句不回退有道）
- **`speak(word)`**：**Web Audio 只做解码，`<audio>` 元素出声**（见 §7.1）。`clipBytes("us", word)` 取字节 → `decodeAudioData` 整条解成 PCM（缓存 `{buf,onset,url}`，上限 48 条）→ `detectOnset()` 检测真起音 → `playClip()`：在样本 `onset−lead` 处**裁切 PCM、编成 16-bit WAV blob**，交给共享 `<audio>` 播放（`lead=100-skipMs`；skipMs/exDelay 变了会按 `urlKey` 重切）。WAV 从起播点开始、无需 seek，保住"样本级、零切词"。首次点击手势内 `mediaUnlock()` 播一段静音 WAV 解锁元素（iOS 手势要求）。取不到字节（托管版包还没下完）或无解码时回退 `speakHtml()`(有道 URL，需联网)
- `detectOnset(buf)`：稳健起音检测——12ms 窗 RMS、阈值取“每条噪声底×2.5 与 0.0009 的较大者”、要求持续 10ms（忽略孤立杂点、抓得住低幅擦音）
- **`turnPage(±1)`**：底部栏两侧 `#barnav-l/#barnav-r` 点击 → `scrollToPage(currentPage()±1)`，h/v 模式通用
- **跳页滑块 `wheelOpen()/closeWheel()`**：`#pageno` 点击切换 `#wheelH`(h,`block`)/`#wheelV`(v,`flex`)；另有一个**捕获阶段**的 `document` click 监听——滑块开着且点在滑块与药丸之外时 `closeWheel()` 并 `stopPropagation+preventDefault`。**必须是捕获阶段**：这样才能抢在 `#pages` 点击委托和 `#barnav-l/r` 之前吃掉这一下，避免"点外面关滑块"顺手把词划了或发了音
- **`clipBytes(which, key)`**：**取音频字节的唯一入口**（§4.1）。托管版从 `packs[which]` 里按 `AUDIO_INDEX` 的 `[偏移,长度]` `slice`；单文件版 `atob` 内联 base64。包没下完返回 `null`
- **`loadPacks()` / `fetchPack(which)`**：托管版启动时拉音频包。先查 `caches.match` 命中就直接用；否则 `fetch` + `getReader()` 边读边计数（这就是真进度条的来源），完成后 `caches.put` 进 `CACHE_NAME` 那个桶。失败挂 `online` 事件重试。先 us 后 ex。
  **收下之前先验长度**：`buf.byteLength` 必须等于 `AUDIO_INDEX` 里的 `bytes`，否则抛错走重试、绝不入缓存；缓存里已有的长度不符条目也会被删掉重下（原因见 §10.1 最后一条）
- **`updateCacheUI()`**：设置页「离线缓存」进度，读 `packState`（`{total,got,t0,done,failed}`）算百分比 + 剩余时间；单文件版直接显示"已内嵌 ✓"。纯展示，不额外下载
- 开发者模式：`devApply/devShow/devStatic/devTick`，底部可拖拽停靠面板画波形+橙(起音)/绿(起播)/红(播放头)线；`state.dev` 开关、`state.devH` 高度
- `applyTheme/applyLayout/syncSettings`：设置联动
- 同步：见 §8

---

## 6. 词根数据是怎么来的（§重要：不是用中国 API）

用户明确要求**用 Claude 子 agent**（母语级英文词源），**不用 DeepSeek**，且**准确优先于覆盖**（拆不出就留空，绝不硬造）。

- 首轮：14 个子agent 各处理 ~90 词 → `intermediate/root_chunks/out_*.json`
- 召回轮：对首轮留空的词再拆一遍 → `intermediate/recall_chunks/out_*.json`
- 手工补：`recall_manual.json`(词缀词) + `compounds.json`(合成词，type=`词`)
- `merge_roots.py` 按优先级合并、去掉"词根=单词本身"的循环项 → `roots.json`
- 结果：1250 词中 **523 词(约42%)** 有拆解；part/type ∈ {前缀,词根,后缀,词}

> 要重跑词根：开子agent 处理 `intermediate/root_chunks/in_*.json`（或自己按同格式产出），再 `merge_roots.py`。`build_roots.py`(DeepSeek) 仅留作备用，**不在正式流程**。

---

## 7. 发音（离线内嵌；Web Audio 只解码，`<audio>` 出声）

- `fetch_audio.py`：对 1250 词各下 美音(有道 type=2)/英音(type=1) → `intermediate/audio/{us,uk}/{rank}.mp3`（可断点续传）。**UK 仍在磁盘(30MB)、但 `build_html.py` 不再嵌入**（US-only，减重）
- `build_html.py`：**单文件版**才把 base64 嵌进 html（US 1250 + EX 1250 ≈ 49MB）；**托管版**改拼成两个二进制包（§4.1）
- 发音源**以有道 `dictvoice` 为主，其中 86 条已换成 edge-tts**（§7.5）
- **取字节只有一个入口 `clipBytes(which, key)`**（`which` = `"us"`/`"ex"`）：托管版从已下载的包里 `slice`，单文件版 `atob` 内联 base64。两条路都交给同一个 `decodeAudioData`。包还没下完时它返回 `null`，`speak()` 退回有道 URL（需联网）、`speakEx()` 静默——这是诚实的中间态，不是 bug

### 7.0 ⚠️ 有道的单词音频不是一个人念的
有道按词从**多个音源库**拼数据，编码参数就是音源身份证——`ffprobe` 的 (采样率, 码率) 分组和听感一一对应（用户逐条听完 rank 1–100 核对，**100 个词零误差**）：

| (采样率, 码率) | 条数 | 是谁 |
|---|---|---|
| 48000/64000（+48k 320k/768k 共 13） | 903 | **主流女音**（用户认可的那个） |
| 24000/32000 | 230 | **同一个女音**，但码率减半，听着发闷发虚 |
| ~~44100/128000~~ | ~~79~~ | 另一个更高更尖的女声（F0 中位 219 vs 主流 180）→ **已替换**（§7.5） |
| ~~24000/160000~~ | ~~7~~ | 又一个偏高的音色 → **已替换**（§7.5） |
| 44100/160000 | 20 | **混的**：8 条男声 + 12 条女声，同组不同人 |
| 22050/32000 | 5 | 也是混的：4 男 1 女 |
| 16k/160k、44.1k/64k、44.1k/192k | 6 | 零星，未逐条听辨 |

- **编码指纹是硬指标，MFCC 音色聚类在单词上不可靠**：1 秒的单词里音素内容压过说话人特征，聚出来的簇和真实音源对不上（例句那种整句音频反而可以，见 §7.4 的 Andrew/Brian 二分实测 1249/1250 吻合）。别再走那条路。
- 上表之外还有个**跨编码组的切分**：同一 (采样率,码率) 组里可能混着不同性别，得再按基频(F0 145Hz 阈值)切一刀。
- 挑音色时的试听样本用 `tmp/voiceab/`（gitignore），按「编码组 × 基频」分段拼接，附 `INDEX.md` 列播放顺序。

### 7.1 播放内核：Web Audio 只解码，`<audio>` 出声（两轮教训的合体）
**教训一（为什么不能 `<audio>.currentTime` 直接 seek MP3）**：① seek 会吸附到 ~24ms 帧边界（落点不准）；② MP3 有「比特池(bit reservoir)」，一帧依赖前面几帧上下文，**从中间 seek 进去、紧跟落点的那一两帧会被解成静音/杂音**。两者叠加会切掉软起音（`/h/ /s/ /f/…`），表现为"开头被切一点点、还时好时坏"。

**教训二（为什么不能用 `AudioBufferSourceNode` 出声）**：iOS/iPadOS 对 **Web Audio 的输出遵守静音开关/音频会话策略**，会出现"上下文 running、播放头在走、就是没声"（正是 commit `5aae50e` 后 iPad 的症状，见 §12）；`<audio>` 元素则豁免——老的 `<audio>` 版在同一台 iPad 上一直正常。

**现方案**（`speak()`/`playClip()`）：`decodeAudioData` 把整条 MP3 **完整解码成 PCM**（解码不出声、静音状态下也允许），`detectOnset()` 找真起音，然后在**精确样本处裁切 PCM、重编成 16-bit mono WAV blob**，交给共享 `<audio>` 元素播放。WAV 文件本身就从起播点开始，**运行时零 seek**，教训一的两个问题都不存在；出声走 `<audio>`，教训二也绕开。解码结果缓存 `{buf,onset,url}`（上限 48 条，淘汰时 `revokeObjectURL`）。iOS 手势要求：首次点击时 `mediaUnlock()` 在手势内 play 一段静音 WAV，解锁该元素，之后异步解码完成后的 play 也被放行。

### 7.2 起播点：逐条起音归一化（取代旧的"固定 skip + 补静音到314"）
有道源的开头静音**极不均匀**（314ms ~ 1000ms 都有；同一个词 US/UK 还能差好几百 ms）。固定跳一个值 → 长静音词前面留一大段死气。所以改成**逐条检测真起音再归一化**：
- `detectOnset(buf)`：12ms 窗 RMS，阈值 = `max(每条噪声底×2.5, 0.0009)`，要求**持续 10ms** 才算起音——**忽略孤立杂点**（如某些词 330ms 处一个 -53dB 的单点毛刺），**抓得住低幅擦音**。
- 起播 `off = onset − lead`，`lead = 100 − skipMs`（默认 skip 40 → **统一 60ms 引子**）。`skipMs` 滑块(0..100)控制这个引子：**越大引子越小越跟手**，100=紧贴起音起播。因 `lead≥0` ⇒ `off≤onset`，起播点恒 ≤ 真起音，只削词前静音、不切词体（切词只可能来自 `detectOnset` 报晚，而它刻意偏早）。
- ⚠️ 314→100 **只改 `lead` 常数与滑块范围，没动 `detectOnset`**，故"0切词"性质不变；纯运行时改动，未再跑 `detect_full.py` 复验。
- 历史全库 2500 条离线验证（`detect_full.py` 思路）：**0 切词**；choices 这类 ~490ms 死气被削掉。

### 7.3 `align_audio_silence.py` / 314 padding 已“退居备用”
新播放内核**每次实时找真起音**，不再依赖“文件里静音正好是某个值”。所以旧的“补零到 ≥314ms”对齐**已非必需**——`intermediate/audio/` 仍是 git 跟踪的既有产物、无需为发音再跑对齐。脚本保留备用；若哪天重下音频，也**不必**再跑它（起音归一化会自愈）。
- ⚠️ 依赖浏览器解码一致性：逻辑已全库离线验证零切词，但真机（尤其 Safari）建议用**开发者模式**（设置页开关）抽查——面板底部实时画波形与 橙(真起音)/绿(起播)/红(播放头) 线。

### 7.4 例句朗读（edge-tts，本轮新增）
单词发音是有道逐词 mp3；**例句是整句朗读**，走另一条链路：
- **音源**：`scripts/fetch_ex_audio.py` 用微软 **edge-tts** 合成（免费，`audio-24khz-48kbitrate-mono-mp3`）。两男声 **`en-US-AndrewMultilingualNeural` / `en-US-BrianMultilingualNeural`**，按 rank **定种子(SEED=42)随机 1:1** 分配（1250→精确 625/625，`voices.json` 记录，可复现）。
- **只念英文**：例句字段 `ex` 是「英文.(中文)」混排，`english()` 取首个 `(`/`（` 前的英文；并去掉开头对话说话人标记 `W:/M:`（否则会念出字母 "double-u"）。
- **去前置静音**：ffmpeg `silenceremove=start_threshold=-45dB` 削掉开头静音（全库抽验 <30ms），重编码 48k 单声道 → `intermediate/audio/ex/{rank}.mp3`（随词音频一起入库、离线用）。
- **播放**：见 §5.3 `speakEx`。前端不再检测起音去静音（文件已去干净），只加 `exDelay` 引子。
- **重跑**：`python scripts/fetch_ex_audio.py`（断点续传，跳过已存在文件）。改词表/例句后要重下某条，先删 `intermediate/audio/ex/{rank}.mp3` 再跑。

### 7.5 单词音频里那 86 条已换成 edge-tts Ava
用户逐条听辨后点名不要 §7.0 表里 `44100/128000`(79 条) 和 `24000/160000`(7 条) 这两个音源。

- **`scripts/resynth_us_audio.py`**：按**编码指纹**（不是写死的 rank 列表）挑出目标 → edge-tts `en-US-AvaMultilingualNeural` 逐词合成 → ffmpeg 去前置静音 → 重编码成 `48000Hz/64k 单声道`**对齐主流音源** → 覆盖写回 `intermediate/audio/us/{rank}.mp3`。
- 原件先备份到 `intermediate/audio_orig_backup/us/`（已 gitignore），`--restore` 一键回滚；`--dry-run` 只列不改。
- 替换清单记在 **`intermediate/audio/us/voices.json`**（`{rank: 音色名}` + `_meta`）。混合来源全靠这个文件可追溯，别删。
- 实测：86 条全部变成 `48000/64000`，F0 中位 219→**192**（落进主流的 152–225 区间），时长 1.98s→0.92s，前置静音 ~0ms。
- ⚠️ **`fetch_audio.py` 见文件存在就跳过，所以不会覆盖这些替换**；但**删掉 `intermediate/audio/us/` 重下会丢**，之后必须重跑本脚本。
- 前端 `speak()` 的起音检测(§7.2)对新文件照常工作，已用无头浏览器实点验证出声（rank 6/94/99/96）。

> ⚠️ **例句解析历史坑（已修）**：`build_dataset.py` 旧代码 `s.split("：",1)[-1]` 会把句内含全角冒号的例句（`W: Oh…`→`女：…`、`Directions:…`→`说明：…`）**误截成只剩中文**，18 条例句英文曾整段丢失。已改为正则只剥开头 `例句[（自编）]:` 标签。另：rank 707 `weight` 源表例句为空，已从真题语料补 `Choosing what to eat and drink is key to weight control.`（用原文，非自编）。

### 7.6 例句「去自编 + 硬伤修复」本轮做的（2026-08-13）
上游早年把找不到真句的词标了「自编」，其实**出处就是卷子**、只是老抽取法（抓语料里第一句含该词的句子）没找到。本轮全部回卷子里重找真句：
- **94 条「自编」→ 真题原句**：从 `corpus/papers/` `corpus/listening/` 里按「干净、自足、非疑问句/非试卷框架」挑真句替换。唯一保留 `例句（自编）` 的是 rank 110 `comprehension`（该词只作 `Listening Comprehension` 标题出现，全语料无成句）。
- **顺手修了 12 条旧「真实」例句的硬伤**：9 条 `W:/M:` 对话说话人标记泄漏进**显示文本**（`english()` 只在**合成音频前**剥了标记，正文没剥）——直接从源文剥掉标记 + 去掉中文「女：/男：」前缀；3 条 OCR 残片（`choices` 的 `…four choices marked , , and .`、rank 46/176 的 `Section C For getting around in Miami.`）另选真题真句。
- **例句音频跟着重录**：改了英文的 **97 个 rank**（94 自编 + section/choices/around；那 9 条 `W:/M:` 因合成前本就剥标记、音频不变）先 `rm intermediate/audio/ex/{rank}.mp3` 再 `fetch_ex_audio.py` 重跑；`audio-ex` 包哈希随之更新、`audio-us` 不变（不触发词音频重下）。
- ⚠️ 还剩两档**没动**的质量问题（当时评估后决定维持现状）：**73 条**例句是真题里的**阅读理解题干**（`What does the author say…`，真实但当例句别扭）；**232 句**例句被 **541 个词条**共用（多为 you/at/from 等虚词，老抽取法只取第一句所致）。想动再走「适合度打分重选」，纯从语料里换、不新增编写。

---

## 8. 多端同步（Supabase）

### 8.1 只同步这些（用户明确要求）
- ✅ **划线**：每词独立、**最新改动为准(LWW)**；取消划线=写 `v:0` 带新时间戳，也会同步
- ✅ **自定义色号列表**：并集（哪台加了新色号，别台也能选）
- ❌ 其余所有设置 **不同步**
- ❌ **当前选中哪个背景色 不同步**（每台独立）

### 8.2 机制
- 纯 REST(fetch)，**不引 Supabase SDK**。localStorage 是本地事实源，联网时与云端做**双向 LWW 合并**
- 触发：打开网页 / 每 25s 轮询 / 窗口重新聚焦(visibilitychange) / 本地改动后 800ms 防抖
- 同一 `syncCode` 的设备共享数据
- ⚠️ **拉取必须分页**：Supabase/PostgREST 有 `db-max-rows` 硬上限(本项目实测默认 **1000**)，单次 GET 超出会被**静默截断且无提示**。而一个码的行数 = 划线(最多 1250 词) + 色号，可超 1000。`reconcile()` 用 `pullAll()` 按**实际返回行数**翻页(offset)直到空页，**不写死页大小**——换服务器(默认可能 500/无上限)也不会漏。改同步逻辑时勿退回单次 GET。

### 8.3 云端表（用户已在 Supabase SQL Editor 建好）
```sql
create table public.progress (
  code text, kind text, item text,      -- kind: 'mark'|'color'; item: rank 或 去#色号
  v smallint default 1, t bigint default 0,
  primary key (code, kind, item));
alter table public.progress enable row level security;
create policy "open read"   on public.progress for select using (true);
create policy "open insert" on public.progress for insert with check (true);
create policy "open update" on public.progress for update using (true) with check (true);
grant select, insert, update on public.progress to anon;
```
- 客户端 upsert 用 `POST /rest/v1/progress?on_conflict=code,kind,item` + `Prefer: resolution=merge-duplicates`
- 已用真实数据库端到端验证：写入/读回/LWW覆盖/色号 全部通过

### 8.4 安全须知（重要）
- 客户端**只用 publishable key**（`web/supabase-config.json`，可公开）
- ⚠️ **`sb_secret_...` 绝不能进客户端**；它曾在对话里出现过，**建议在 Supabase 轮换作废**
- RLS 是"凭 publishable key + 同步码可读写"——**同步码要用不好猜的**（如 `cet4-sync-9f3k`），否则别人猜到就能改你的划线

---

## 9. 构建 & 重建（命令速查）

```bash
# 依赖
pip install pyphen edge-tts        # 音节 / 例句 TTS（需 ffmpeg 去静音）
# （词音频已下好；要重下：python scripts/fetch_audio.py）
# （例句音频已生成；要重下：python scripts/fetch_ex_audio.py）

# 改了词根/词表后，从数据到成品全量重建：
python scripts/merge_roots.py          # → intermediate/roots.json
python scripts/build_dataset.py        # → intermediate/entries_full.json
python scripts/fetch_ex_audio.py       # → intermediate/audio/ex/*.mp3（例句朗读，断点续传）
python scripts/resynth_us_audio.py     # → 把 86 条不想要的有道音色换成 Ava（§7.5；重下过 us/ 才需要）
python scripts/make_pdf_optimized.py   # → 优化版 PDF
python scripts/build_html.py           # → 英语四级单词背诵.html + docs/

# 只改了网页界面(template.html)：
python scripts/build_html.py           # 重新注入数据/音频/配置即可
```

### 9.1 验证网页（工具已随仓库分发，在 `scripts/devtest/`）
⚠️ **本机没装 playwright / puppeteer 的包**，只有 Playwright 早先下好的浏览器二进制
（`~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/`）。
所以别去 `import playwright`，用仓库自带的这两个小工具（零依赖，Node ≥21 自带 `WebSocket`）：

```bash
# ① 生成秒开的测试页（真实词条 + 空音频，~100KB；49MB 的成品调界面太慢）
python scripts/devtest/make_testpage.py            # 默认 前 120 词
python scripts/devtest/make_testpage.py 60 400     # 60 词，从第 400 条起（前 100 词是虚词，没词根卡）
#   -> tmp/devtest/testpage.html   （产物落 tmp/，不入库）

# ② 驱动无头浏览器：跑一串 JS 表达式，可选截图
node scripts/devtest/cdp.mjs "file://$PWD/tmp/devtest/testpage.html" \
  '["document.getElementById(\"start\").click()","document.querySelectorAll(\".entry\").length"]' \
  tmp/devtest/shot.png
```
- 每个表达式的返回值按 JSON 打印（promise 会 await），异常会抛出来——所以它同时也是"有没有控制台报错"的检查。
- **表达式列表里可以混入三个指令**（本轮新增）：`"__OFFLINE__"` / `"__ONLINE__"` 断网/恢复，`"__RELOAD__"` 重载并等页面稳定。验 PWA 离线必须用它们——服务器还活着的话，缓存**没命中**也会看起来像命中。
- ⚠️ **三个踩过的坑，都已在 cdp.mjs 里修掉，别再退回去**：
  1. **没有 `--autoplay-policy=no-user-gesture-required` 就验不了发音**。合成的 `.click()` 不算真实用户手势，`<audio>.play()` 一律被自动播放策略拒掉，返回 `NotAllowedError`，看起来像"代码坏了"，实际是浏览器策略。同时加了 `--mute-audio` 免得跑测试时真的出声。
  2. **断网必须同时下发到 service worker 的 target**。装了 SW 之后页面的请求都是 SW 发的，只对页面 target 设 `Network.emulateNetworkConditions` **完全没用**（实测：设了"离线"，请求照样 200）。现在用 `Target.setAutoAttach` 抓住 SW 会话，逐个下发。
  3. **页面自己跳转后，必须换到新的 execution context 再求值**。SW 更新会让页面 `location.reload()`；`Runtime.evaluate` 不带 `contextId` 会落在**已销毁的旧上下文**里——文档看着正常，但 `window.BUILD_INFO` 之类全没了，活像 app 坏了。现在跟踪最新的默认 context 求值；并且**协议级 error 不再被吞成 `undefined`**（那正是"假故障"的来源），只有"target navigated"这一种可恢复，等新文档起来后重试。
- 探测 `<audio>` 要注意：播放器是 `new Audio()` 建的、**不在 DOM 里**，`querySelectorAll("audio")` 是空的。要挂 `HTMLMediaElement.prototype.play` 的钩子才看得到。
- 常用探针：点 `#start` 进阅读页、点 `.num` 划词、`JSON.parse(localStorage.cet4_reader_v3)` 看 state、`document.querySelectorAll('.entry').length` 数渲染条数。
- **验托管版必须起 http 服务**：`cd docs && python3 -m http.server 8123`，url 用 `http://127.0.0.1:8123/index.html`。别用 `file://docs/index.html`——那份是 562KB 的外壳，且 SW 在非 http 下代码里直接跳过注册（`location.protocol.indexOf("http")===0`），缓存/更新/音频包一条都验不了。要验**内嵌**音频就开根目录那份 49MB 单文件。
- 截图与生成的测试页**一律落 `tmp/`**（§0.1）——工具入库，产物不入库。

---

## 10. 部署（PWA + GitHub Pages）—— ✅ 已推送

托管文件在 `docs/`（index.html + manifest + sw.js + icons），已推送到 `yiyisheh/CET4-vocabulary` 的 **main** 分支。

1. 代码已 push。remote = `yiyisheh/CET4-vocabulary`。`docs/` = 外壳 562KB + 两个音频包 13.6MB / 22.8MB（都在 GitHub 的 100MB 单文件上限内，仅有大小警告）。
   - `intermediate/audio/`（71MB，含不参与构建的 uk/）**已纳入 git 跟踪**；根目录 49MB 的 `英语四级单词背诵.html` 仍 gitignore（可由 build_html 重生成），只保留 `docs/` 上线用。
2. GitHub 仓库 → Settings → Pages → Source 选 **main / docs**（若还没开，这步在网页上点一次）。
3. 访问 `https://yiyisheh.github.io/CET4-vocabulary/`。
4. iPad **Safari** 打开该网址 → 分享 → **添加到主屏幕** → 成为已安装 PWA。

**为什么要 PWA**：iOS 对 `file://` 本地文件的 localStorage 会隔天清空；而**已安装的 PWA 有独立持久存储**，配合 `sw.js` 缓存实现离线+持久，且是 iOS 上最稳的持久化方式。

### 10.0 离线缓存进度条是**真的**（本轮重构）
以前那条进度条只会 0→100 跳变，原因是 `cache.put()` **原子提交**——写完之前 `navigator.storage.estimate()` 几乎不动，提交那一刻整个包一起出现（`estimate()` 本身还被浏览器故意粗粒度化以防指纹）。

现在进度条跟踪的是**音频包**，因为拆分之后那才是真正的下载（外壳 562KB 装 SW 时瞬间就好，36MB 音频才是要等的）：

- **网页自己**`fetch` 音频包，用 `response.body.getReader()` 边读边累加字节，算出百分比和剩余时间；下完 `caches.open(CACHE_NAME).put()` 写进和 SW 同一个桶。
- **不存在重复下载**：这就是 app 本来就要拿的那份数据，顺手画了个进度条。（重构前的老做法是 SW 把 49MB **再下一遍**只为了画进度，首次访问要 98MB。）
- 先下 `us` 再下 `ex`——点单词是常见操作，例句可以晚一步到。
- 断网/失败 → 显示"音频下载失败，重新联网后会自动重试"，并挂 `online` 事件自动重来。
- 单文件版没有包，直接显示"单文件离线版，音频已内嵌 ✓"。
- 实测（本机 `python3 -m http.server` + 无头 Chromium，2026-08-02）：两个包下完后进度行转"已缓存，可离线使用 ✓（约 36 MB 音频）"，缓存桶里正好是 `index.html`+manifest+3 图标+两个 `.bin`；`__OFFLINE__` 后 `__RELOAD__` 仍渲染 1250 词，点单词从包里取字节、播的是 `blob:` WAV。更早一轮在 3MB/s 限速下看过 `13% → 98%` 的平滑推进与倒计时。

### 10.1 PWA 更新（**手动确认制**·缓存名固定·靠清单增量淘汰）
> ⚠️ **本轮改为「不自动更新」**：新版只会**安装成 waiting SW 静静等着**，运行中的页面保持旧版，**直到用户在弹窗里确认**才切换。以下机制不变，只是「切过去」这一步从自动改成手动（见 §10.2）。

`sw.js` 是 cache-first。**缓存桶名 `cet4-1250` 现在是固定的**（重构前是 `cet4-1250-<hash>`，一换名整份缓存作废 = 全量重下，正是要避免的）。版本信息改为落在**文件名**和**两份清单**上：

- `__PRECACHE__`：install 时 `addAll` 的小资源（外壳 + manifest + 3 图标）。**故意不含音频包**，否则那 36MB 会被下两遍（包由网页下，§10.0）。
- `__KEEP__`：`PRECACHE` + 本次构建的两个音频包 URL。activate 时遍历缓存，**删掉不在 KEEP 里的条目**——音频哈希变了就淘汰旧包，没变就原地保留。
- **`__BUILD_HASH__`：外壳哈希必须写进 `sw.js`**。浏览器判断"有没有新版"只有一个办法——按字节比 `sw.js`。而外壳文件名是不带哈希的 `index.html`，`PRECACHE`/`KEEP` 又只在音频包变了才变，所以**只改网页（比如一行 CSS）时 `sw.js` 会一字不差**，SW 不重装、cache-first 的旧外壳永远留在设备上。已实测复现，修法是构建时往 `sw.js` 注入 `var BUILD = "<外壳哈希>"`（运行时不用它，存在的意义就是让字节变）。
- 所以：改网页 → 外壳哈希变 → `docs/sw.js` 字节变 → 新 SW 装成 **waiting**（install 用 `cache:"reload"` 重新拉外壳，但**不再 `skipWaiting()`**）→ 用户确认后才 `postMessage("SKIP_WAITING")` 让它接管 → **只重下 562KB 外壳**，36MB 音频一个字节不动。端到端实测：先装 v1，把站点换成 v2 → 页面探测到 waiting SW → 按钮变「检测到新版本」+弹窗，**不自动重载**；点「立即更新」（连通性通过）才重载进 v2、`navigation.type` 变 `reload`（见 §10.2 的验证记录）。
- `"./"` **不在 PRECACHE 里**：它和 `"./index.html"` 是同一份字节，两个都列会下载并存储两份。导航请求（`request.mode === "navigate"`）由 fetch 处理器回落到 `"./index.html"` 那一份。
- **SW 只允许拿外壳回答导航请求**。fetch 处理器早先对**任何**没缓存又取不到的请求都回落到 `index.html`；离线时这意味着音频包请求会拿到一个 `200 text/html` 的外壳（已用 `__OFFLINE__` 实测复现），网页会把它当包收下、写进缓存 —— 那一版**从此永久哑掉且不会重试**。现在非导航请求老老实实失败，网页那边再加一道 `byteLength` 校验兜底（§5.3）。
- **`controllerchange` → 重载**：现在只在**用户确认后**才发生。SW 不再自动 `skipWaiting()`，所以 controller 只有在页面 `postMessage("SKIP_WAITING")` 之后才会换 —— 这一次换版就是「用户点了立即更新」，绝不会是自动更新。`hadController` 仍必须在**页面加载时**取样（事件派发时 controller 早已换好，在处理器里判断永远为真）；首次安装（原本没有 controller）不刷。

### 10.2 设置页「版本 / 手动更新」（本轮重写为**手动确认制**）
用户明确要求：**不自动更新，必须等用户手动更新**。机制：
- 设置页有一行：左侧 **当前版本号 + 构建时间**（`window.BUILD_INFO`），右侧按钮（默认「检查更新」）。**版本号 = `build_hash` = sw 缓存名里的 hash**，"显示什么版本"与"决定要不要更新"同一个值。
- **探测到新版本**（页面发现一个 waiting SW —— 即 `reg.waiting` 已就绪，或 `updatefound`→`installing`→`statechange:installed` 且当前有 controller）时：
  - 按钮变琥珀色、文案改成 **「检测到新版本」**（`.hasupd` 类）；
  - **弹出确认弹窗 `#umodal`**，问是否立即更新。弹窗里有 **「不再提示」复选框，默认勾选**（`#um-noremind` checked）—— 直接关掉弹窗（勾着）就等于"别再自动弹"，写进 `localStorage['cet4_upd_snooze']`；按钮仍留着作为手动入口。已 snooze 后不再自动弹，但再点按钮会重新打开弹窗。
- **应用更新（`#um-now` 立即更新）先做连通性检查**：`fetch("sw.js?ping=…",{cache:"no-store"})` 走真网络（SW 对这种非导航未缓存请求会 `fetch()` 放行）。**失败 → 弹窗内红字"连接失败，已中止更新"，不重载、不切版**；成功 → 清掉 snooze → `waiting.postMessage({type:"SKIP_WAITING"})` → §10.1 的 `controllerchange` 重载进新版。
- 按钮（无 waiting 时）走**手动检查**：`reg.update()` 重新拉 sw.js；有新版则走上面的探测→弹窗；无新版 1.6s 后回填"已是最新版本 ✓"。有 waiting 时点按钮=重新打开弹窗。
- **`sw.js` 侧**：install **不再 `skipWaiting()`**（装成 waiting）；新增 `message` 监听，收到 `{type:"SKIP_WAITING"}` 才 `skipWaiting()` 接管。
- **非 http（`file://` 单文件离线版）** 无 SW，按钮置灰"离线单文件"（弹窗代码在此之前 early-return，不接线）。
- 已用**持久 profile** 的无头 Chromium 端到端实测（`tmp/updtest/run.mjs`，装 v1→改 sw.js 成 v2→复现）：首装不弹窗；探测到 v2→按钮「检测到新版本」+弹窗+复选框默认勾选；**等待期不自动重载**（load 计数不涨）；离线点更新→"连接失败，已中止"且不重载；恢复联网点更新→重载进新版、按钮复位；全程无控制台报错。

---

## 11. 二次开发怎么改（常见任务配方）

| 想做什么 | 改哪里 |
|---|---|
| 改词条样式/字号/颜色 | `web/template.html` 的 `<style>` → `build_html.py`；**改完务必用 §9.1 截个图看**，别凭 CSS 想象（§3.1 就是被想象出来的错描述） |
| **动音频/构建/缓存** | **先读 §4.1**：一份模板出两种形态（单文件内嵌 / 托管版外壳+包）。碰 `build_html.py`、`sw.js`、`clipBytes()`、`loadPacks()` 之前都要先明白这件事 |
| 加回英音(UK) 或加任何新音频集 | 托管版：`build_html.py` 里再 `pack()` 一个包、进 `AUDIO_INDEX` 和 `keep`，**外壳不变大**；单文件版才需要考虑体积 |
| 放临时文件/截图/测试页 | 一律 `tmp/`（§0.1）——gitignore 但用户能直接打开 |
| 加一个设置项 | template：加 state 字段(+启动时的容错/迁移) + 设置页 DOM + `syncSettings()` 同步 UI + 事件；改变渲染内容的必须 `paginate()` |
| 改状态池行为（池大小/阈值/推进规则） | template 的 `ensurePool()`（就一个 `poolMax`；步长 = `poolSize−poolLow`）；UI 在 `renderPool()` + `#sw-poolmode/#pool-size/#pool-low/#pool-reset`（§13） |
| 改「哪些词参与排版」 | 只改 `visible()` 一个函数——分页、累计小标、状态池都从它取列表 |
| 改划线样式/区域 | `.entry.marked .num::before`（CSS）+ 点击委托里的 mark 判定 |
| 换/改单词发音 | `fetch_audio.py` 换音源重下 → `build_html.py` 重新内嵌；播放逻辑在 `speak()`（Web Audio，§7） |
| **换掉某个不想要的单词音色** | 先按 §7.0 用 `ffprobe` 的 (采样率,码率) 圈出音源组、拼 `tmp/voiceab/` 试听确认，再改 `resynth_us_audio.py` 的 `TARGET_FORMATS`/`VOICE` → `--dry-run` 核对 → 跑 → `build_html.py`（§7.5） |
| 换/改例句朗读音色 | `fetch_ex_audio.py` 里 `VOICES`（改 edge-tts 声音）→ 删 `intermediate/audio/ex/` 重跑 → `build_html.py`；播放在 `speakEx()`（§7.4） |
| 改起播引子/起音检测 | template `speak()`/`detectOnset()`；引子 `lead=100-skipMs`，默认值 `skipMs:40`（§7.2） |
| 加回英音(UK) | `build_html.py` 恢复 `audio_json("uk")` + `__AUDIO_UK__` 占位符 + template 加回 `audio-uk` 标签与口音切换段（`seg-accent`）。⚠️ 但先确认 §12 的 iPad 无声是否与体积有关 |
| 重跑/补词根 | 子agent 产出 `root_chunks/recall_chunks` → `merge_roots.py` → `build_dataset.py` |
| 改同步行为/字段 | template §8 的 `reconcile()`；只同步 marks+colors 是**用户明确要求**，别擅自扩大 |
| 换同步后端 | 换 `web/supabase-config.json` + `reconcile()/api()` 里的 REST 调用 |
| 改 PDF 版式 | `scripts/make_pdf.py`(底层 build) + `make_pdf_optimized.py`(参数) |

---

## 12. 待办 / 已知限制

- ✅ **iPad 无声已解决并真机复验通过**（2026-08-02）：原因是 iOS/iPadOS 对 **Web Audio 输出**遵守静音开关/音频会话策略（上下文 running、播放头在走、就是没声），`<audio>` 元素豁免。修法是「Web Audio 只解码、`<audio>` 出声」（§7.1），保留样本级起播与零切词。体积从来不是原因（原始 US+UK 58MB 用 `<audio>` 播放一直正常）。Edge iOS 打不开是其更严格的内存上限，另算。
- ✅ **已推送到 main**（§10）；若 Pages 尚未开，去仓库 Settings→Pages 选 main/docs 一次
- ⚠️ **轮换 Supabase secret key**（§8.4）
- 发音依赖浏览器解码一致性：逻辑已全库离线验证零切词，真机（尤其 Safari）建议用开发者模式抽查（§7.3）
- 同步无账号鉴权，靠"同步码不好猜"保护；无实时推送，靠 25s 轮询+聚焦刷新（对背单词够用）
- 单文件版 49MB 首次加载需一两秒（用户已接受）；托管版首屏已降到 **562KB**（实测：本机 http + 无头 Chromium，DOMContentLoaded 294ms，点「开始背诵」装箱 1250 词 113ms）（§4.1）
- ✅ **首次装 PWA 的无谓自我重载已修**（§10.1 的 `hadController`）。实测：重构前首次安装后 `navigation.type` 会变成 `reload`、页面重新解析 49MB（539ms，iPad 上更久）；现在全程停在 `navigate`
- ✅ **离线时 SW 把外壳当音频包返回、导致该版本永久哑掉** —— 已修（§10.1），并加了包长度校验与缓存自愈
- ✅ **只改网页时 `sw.js` 字节不变、更新推不到设备** —— 已修（§10.1 的 `__BUILD_HASH__`）
- 🟡 **单词音源还有 31 条杂音没处理**（§7.0）：`44100/160000` 20 条（8 男 12 女）、`22050/32000` 5 条（4 男 1 女）、以及 6 条零星格式。用户听过其中的 15/17/23/68，没说要换。要清就照 §7.5 把格式加进 `TARGET_FORMATS` 重跑
- 🟡 **230 条 `24000/32000` 是同一个女音但发闷**（码率减半）。换成 TTS 等于把用户喜欢的声音换掉，不建议；对症做法是全库 EBU R128 响度归一化，音色不动——尚未做
- 词根覆盖 42%：高频里大量日耳曼/功能词本就拆不出，是"准确优先"的合理结果，非缺陷
- 改 `state` 结构须处理 localStorage 迁移，否则老用户数据读不出（如 `skipMs` 314→100 的越界迁移）
- 状态池**不参与多端同步**（只有 marks/colors 同步，§8.1）。两台设备的上界各自独立，但因为"已掌握"是同步的，两边推进的节奏基本一致

---

## 13. 状态池模式（莱特纳 · 序号上界）

用户的背诵法：不要一次面对 1250 词，而是只面对**开头一段序号范围**里还没划掉的词；划掉=熟练剔除；剩余被磨到只剩少数顽固词时，**范围自动往后推进**，放新词进来。

### 13.1 参数（设置页可改，存在 state）
| 参数 | state 字段 | 默认 | 含义 |
|---|---|---|---|
| 池大小 | `poolSize` | **40** | **要始终保持的「没划掉的词」数量**（工作集大小）——不只是开头，每次推进后剩余都会补回到它 |
| 推进阈值 | `poolLow` | **15** | 剩余 ≤ 此值就推进 |
| 当前上界 | `poolMax` | — | 整个功能**唯一的状态**：只背 rank ≤ 它、且没划掉的词 |

- **推进步长 = `poolSize − poolLow`**（不再是 `poolLow` 本身）。这样剩余从 `poolLow` 补回到 `poolSize`：池 100 / 阈值 40 时，剩余降到 40 → +60 → 剩余回到 **100**。⚠️ 旧版步长 = `poolLow`（= 40），只能把剩余补到 80，「池大小」只在第一轮成立——那是个 bug，本轮已修。
- 阈值强制 `1 ≤ poolLow < poolSize`，故步长 `poolSize − poolLow ≥ 1`，永不为 0（不会死循环）。
- **上界只前进、不后退**，所以改池大小/阈值永远不会丢进度；「重置范围」才把上界拉回 `poolSize`。
- 状态池模式下 `removeMarked` 不再另行生效（`visible()` 本来就滤掉了划掉的词）。

### 13.2 机制（`web/template.html`）
```
visible()         = poolMode ? (rank ≤ poolMax && 未划掉) : (removeMarked ? 未划掉 : 全量)
poolRemain()      = 上界内还没划掉的词数 —— 这就是「剩余」
poolNeedsRefill() = poolMode && poolMax < 1250 && 剩余 <= poolLow
ensurePool()      = 幂等：先保证 poolMax ≥ poolSize，再 while(剩余 ≤ 阈值) poolMax += (poolSize − poolLow)
```
就一个数 `poolMax`，没有花名册、没有游标、没有"本轮"。好处正是用户要的：**已掌握永远是全库真实总量**（54 就是 54），不会每轮归零；顽固词也不需要特殊照顾——它们没被划掉，自然一直留在范围里。

**步长为什么是 `poolSize − poolLow`**：用户的心智模型是「池大小 = 始终保持这么多没划掉的词」。剩余降到阈值 `poolLow` 时，要补回到 `poolSize`，就得加 `poolSize − poolLow` 个新词。池 100 / 阈值 40：剩余 40 → +60 → 剩余 100，工作集稳定在 100。**旧版步长 = `poolLow`（=40），剩余只补到 80**，「池大小 100」只在第一轮成立、之后工作集永远在 40–80 徘徊——用户点出的正是这个不科学之处。

**也不是 `上界 = 起始 + 阈值 × ⌊已掌握 / (起始−阈值)⌋`**（一个更早被否掉的定时公式）：它每 60 个才推进 40 个，剩余会一路缩水直到饿死。盯着「剩余」推进（本节的 while 循环）才不会饿死。

| 已掌握 | 上界 | 剩余 | 说明 |
|---|---|---|---|
| 54  | 100 | 46  | 46 > 40，不推进 |
| 60  | **160** | **100** | 剩余触 40 → +60 → 补回 100 |
| 100 | 160 | 60  | 尚未触阈值 |
| 120 | **220** | **100** | 再次触 40 → +60 → 补回 100 |
| 180 | **280** | **100** | 每次推进剩余都回到池大小 |

- **迁移**：老版本的 `state.pool`（每轮花名册数组）→ `poolMax = max(pool)`，并**立刻存盘一次**，否则旧数组会永远赖在 localStorage 里。
- **调用点**：`paginate()` 开头；点击委托 `mark` 分支里 `poolNeedsRefill()` 为真时；设置页开关/改数值/重置之后。
- `mark` 里那次推进是**全站唯一会因为划词而重排页面的地方**——刻意为之：推进是用户该看见的事件，重排后 `state.anchor` 指到新范围里的第一个词。平时划词不重排（不会在手指底下抖）。
- 累计小标（`counters`）照常按 `visible()` 的位置算，所以开池模式时数的是**范围内剩余**的词。

### 13.3 已验证（`scripts/devtest/`，§9.1）
按用户实际的 池大小 100 / 阈值 40，用 cdp 造状态→重载→读 `poolMax`（步长 = 100−40 = 60）：
- 已掌握 **59**（剩 41 > 40）→ 上界仍 **100**，不推进 ✓
- 已掌握 **60**（剩 40）→ 上界 **160**（+60），剩余补回 **100** ✓（用户点名要的「推进 60」）
- 上界 160 · 已掌握 **120**（剩 40）→ 上界 **220**（+60），剩余 100 ✓
- 到书尾 `Math.min(…, 1250)` 收口：上界 160 · 已掌握 120 在只有 200 词的测试页上被夹到 200 ✓
- 旧版 roster `[101..200]` 状态 → 迁移成 `poolMax=200`，旧 `pool` 字段从 localStorage 清掉 ✓
- 「重置范围」→ 回到池大小 ✓；关掉开关 → 恢复全量 ✓；全程无控制台报错 ✓

---

*本文档随网页一起维护；改了架构记得回来更新。网页源码唯一入口：`web/template.html`。*

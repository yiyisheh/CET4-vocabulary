# CET-4 背单词网页 —— 开发交接文档 (HANDOFF)

> 这份文档是**给下一个 AI / 开发者的唯一入口**。读完它 + 它指向的几个小文件，就能完整理解并二次开发这个网页，**无需也不要打开任何几十 MB 的大文件**。

---

## 0. ⚠️ 给 AI 的第一条规则：该读什么，绝对别读什么

| 类别 | 文件 | 大小 | 说明 |
|---|---|---|---|
| ✅ **网页源码（读这个）** | `web/template.html` | ~64 KB（约 1120 行） | **整个网页的唯一源文件**（HTML+CSS+JS 一体）。改网页 = 改这里。 |
| ✅ 构建脚本 | `scripts/build_html.py` `build_dataset.py` `merge_roots.py` `fetch_audio.py` `fetch_ex_audio.py` `make_pdf_optimized.py` | 2–5 KB | 见 §4 流水线 |
| ✅ PWA 资源 | `web/pwa/manifest.webmanifest` `web/pwa/sw.js` `web/pwa/icon-*.png` | <30 KB | 见 §10 部署 |
| ✅ 同步配置 | `web/supabase-config.json` | <1 KB | 仅含**可公开**的 publishable key |
| ✅ 词条数据 | `intermediate/entries_full.json` | 544 KB | 1250 词最终数据（无音频），可读 |
| ✅ 词根数据 | `intermediate/roots.json` | 186 KB | 词根/词缀/合成拆解 |
| ✅ 词表源 | `output/high_freq_cet4_df.txt` | 328 KB | rank+音标+释义+例句（DF 排序） |
| 🚫 **AI 绝对别读** | `英语四级单词背诵.html` | **52 MB** | 构建产物（内嵌 2500 条 base64 音频 = 1250 词 + 1250 例句），读了会撑爆上下文 |
| 🚫 **AI 绝对别读** | `docs/index.html` | **52 MB** | 同上，托管用副本（与根目录那份字节相同） |
| 🚫 **AI 绝对别读** | `intermediate/audio/` | **73 MB** | 3750 个 mp3 源（us 18M / uk 30M / ex 25M），构建输入，别遍历 |

**一句话**：想看/改网页，永远打开 `web/template.html`；那两个 52 MB 的 `.html` 是**自动生成的产物**，不是源码。
> 注：`uk/` 30 MB 仍在磁盘和 git 里，但**不再被嵌进成品**（§4），所以成品 52 MB ≠ 音频目录 73 MB。

### 0.1 📌 所有临时资源一律放 `tmp/`
截图、录屏、测试页、一次性脚本、调试产物——**全部写进仓库根目录的 `tmp/`**，不要散在 `/tmp`、系统临时目录或项目根目录。理由：`tmp/` 已在 `.gitignore` 里（不污染仓库），但它在项目里，**用户能直接打开来看**。

- `tmp/devtest/` 是常备的本地验证工具（见 §9），可以放心复用/覆盖。
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
│   ├── align_audio_silence.py← （备用）旧的“补静音对齐”脚本，现已非必需，见 §7.3
│   ├── make_pdf.py           ← PDF 底层排版
│   └── make_pdf_optimized.py ← 生成优化版 PDF
│
├── intermediate/             ← 数据与中间产物
│   ├── entries_full.json     ← 【最终词条数据】1250 词（544 KB）
│   ├── roots.json            ← 【最终词根数据】（186 KB）
│   ├── compounds.json        ← 手工补的合成词（work+place…）
│   ├── recall_manual.json    ← 手工补的词缀词（powerful…）
│   ├── root_chunks/          ← 14 组 in_*/out_*.json（首轮子agent词根产出，共 28 个文件）
│   ├── recall_chunks/        ← 8 组 in_*/out_*.json（召回轮，共 16 个文件）
│   ├── audio/                ← 🚫 73MB mp3 源，别读：us/ uk/ 各 1250，ex/ 1250 + voices.json
│   └── （entries_v2/examples/liut969_dict/ds_batches* 均为上游历史产物，网页不用）
│
├── output/high_freq_cet4_df.txt  ← 词表源（rank/音标/释义/例句）
│
├── docs/                     ← 【GitHub Pages 托管目录】index.html + manifest + sw.js + 3 图标
│
├── tmp/                      ← 【所有临时资源放这里】gitignore，但用户看得见（§0.1）
│   ├── devtest/              ←   常备验证工具：make_testpage.py + cdp.mjs（§9）
│   └── *.png / *.mp4 …       ←   截图、录屏等随手产物
│
├── 英语四级单词背诵.html      ← 🚫 52MB 成品（AirDrop 单文件离线版）；**已 gitignore**，可重生成
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
| 例句 | `.ex` | `例句： The statement…（以下声明供您参考。）`，或 `例句（自编）：`。英文 + 全角括号里的中文 |

顶栏：左「四级高频 1250」蓝色粗体 + 右「设置」小按钮。
底栏：`‹` … `1 / 8` 圆角药丸页码 … `›`。

- **点序号/左侧空白** → 灰色删除线标记「已掌握」（`markStyle`：变灰划线 / 仅划线）
- **点单词** → 音节拆分 `com·po·si·tion ⇄ composition` 并发音
- **点例句** → 朗读整句（**edge-tts 生成，Andrew/Brian 两男声按词 1:1 随机，1250 条已内嵌离线**；见 §7.4）。⚠️ 热区**已被刻意缩短**（不是"整行加大"）：上方那 6px 间距走 margin 不可点，只有紧贴文字的 padding box 可点，避免点释义误触朗读。可调「例句播放前延迟 0–50ms」
- **点词条其他处** → 发音（**1250 条美音已 base64 内嵌，离线可用**；可调「跳过开头静音 0–100ms」。⚠️ 英音(UK)已移除、口音切换已删，见 §7）
- **翻页**：底部页码栏两侧空白区（`‹`/`›`，`#barnav-l/#barnav-r`）点击翻上/下一页；左右滑动分页启用 `scroll-snap-stop:always`，轻划最多前进一页（不影响触控板/iPad）
- **自测的"留白"实际是浅色块**：`.mask` 把释义/词根整块变成 `--panel`（#f4f6f9）的**圆角浅灰块**、文字透明（连后代一起），高度不变所以不重排；例句英文常显、中文被同样的块盖住。点块内任意处 → 该词条所有块**一起**解开。

### 3.2 设置页（自上而下的实际顺序）
标题「四级高频单词 · 背诵」+ 副标题「2021–2025 真题 · top 1250 · 含词根词缀 · 排版对齐优化版 PDF」；每项一行（左标题+灰色说明，右控件：蓝色 switch / seg 按钮组 / 滑块 / 数字框）；**「开始背诵」是固定在底部的蓝色大按钮**（`position:fixed`，会盖住最底下的内容，往上滚才看得到被盖住的行）。
1. 去掉已经划掉的单词（不实时·进出设置页才重载去掉）
2. **状态池模式（莱特纳）** + 子行「池容量 / 低水位阈值 / 重置池」（默认 40 / 15，见 §13）
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

`build_html.py` 把模板里 6 个占位符替换掉：
- `__DATA__` → 1250 词条 JSON
- `__AUDIO_US__` → `{word: base64 mp3}` 美音（放在 `<script type="application/json">` 里，不执行、按需解析）。**UK 已移除**（原来还有 `__AUDIO_UK__`，为减重删掉）
- `__AUDIO_EX__` → `{rank: base64 mp3}` 例句朗读音频（edge-tts，见 §7.4）
- `__SYNC_CONFIG__` → `web/supabase-config.json` 内容（无则 `null`，同步自动禁用）
- `__CACHE_BYTES__` → 离线包预计字节数（= 最终 html 长度 + PWA 小资源），供设置页缓存进度对比 `storage.estimate`
- `__BUILD_INFO__` → `{v:内容哈希, t:构建时间}`，设置页「版本」行展示 + 「检查更新」用（见 §10.1）。`v` **与 sw 缓存名同源**（同一 `build_hash`），故在**注入 build-info/cache-bytes 之前**算，只随内容变、不随时间戳变——同内容重建版本号不变、不会白触发更新

> 成品体积 **~52MB**（实测 54,312,669 字节；US+EX 两套内嵌，各 1250 条；删 UK 前是 ~89MB）；docs/index.html <100MB，GitHub 可推。
> **iPad 无声已定位为播放内核而非体积**：US+UK 原始版（`<audio>` 播放）58MB 在 iPad 正常；换 Web Audio 输出后无声、删到 52MB 仍无声。现已改为「Web Audio 只解码、`<audio>` 出声」（§7.1），体积不再是嫌疑；若 iPad 实测恢复正常，可考虑把 UK 加回来。

---

## 5. `web/template.html` 内部结构（改网页看这节）

结构顺序：`<style>`（全部 CSS）→ `#settings` 设置页 DOM → `#top` / `#pages` / `#measure` / `#dev` / `#bar` → **5 个 `<script>`**：
1. `<script type="application/json" id="audio-us">__AUDIO_US__</script>`（不执行，`audioMap()` 按需 `JSON.parse`）
2. `<script type="application/json" id="audio-ex">__AUDIO_EX__</script>`（同上，`exMap()` 解析）
3. `window.CET4` / `window.CACHE_BYTES` / `window.BUILD_INFO`
4. `window.SYNC_CONFIG`
5. **网页主逻辑 IIFE**（约 730 行，从 `var DATA=window.CET4` 到末尾的「检查更新」小 IIFE）

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
  poolMode:false,            // 状态池（莱特纳）模式总开关；开启后 visible() 只回池内未掌握的词，removeMarked 不再另行生效。【本地】见 §13
  poolSize:40,               // 活动池容量（默认 40，可改；上限 = 词库长度）。【本地】
  poolLow:15,                // 低水位阈值（默认 15，可改；强制 < poolSize）。池内剩余 ≤ 此值 → 自动补满。【本地】
  pool:[],                   // 当前活动池的 rank 列表（升序）。由 ensurePool() 维护。【本地】
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
- **`speakEx(rank)`**：例句朗读。取 `__AUDIO_EX__` 的 base64 → 复用 §7 的 decode+缓存内核 → `playEx()` → `playClip()`（`<audio>` 出声）。例句音频**已在构建前去掉前置静音**，故 `off=onset(≈0)`；`exDelay`(0..50ms)的"播放前静默"以**前置静音样本形式编进 WAV**。无内嵌/无解码则静默（例句不回退有道）
- **`speak(word)`**：**Web Audio 只做解码，`<audio>` 元素出声**（见 §7.1）。取内嵌 base64 → `decodeAudioData` 整条解成 PCM（缓存 `{buf,onset,url}`，上限 48 条）→ `detectOnset()` 检测真起音 → `playClip()`：在样本 `onset−lead` 处**裁切 PCM、编成 16-bit WAV blob**，交给共享 `<audio>` 播放（`lead=100-skipMs`；skipMs/exDelay 变了会按 `urlKey` 重切）。WAV 从起播点开始、无需 seek，保住"样本级、零切词"。首次点击手势内 `mediaUnlock()` 播一段静音 WAV 解锁元素（iOS 手势要求）。非内嵌词/无解码时回退 `speakHtml()`(有道 URL)
- `detectOnset(buf)`：稳健起音检测——12ms 窗 RMS、阈值取“每条噪声底×2.5 与 0.0009 的较大者”、要求持续 10ms（忽略孤立杂点、抓得住低幅擦音）
- **`turnPage(±1)`**：底部栏两侧 `#barnav-l/#barnav-r` 点击 → `scrollToPage(currentPage()±1)`，h/v 模式通用
- **`updateCacheUI()`**：设置页「离线缓存」进度。用 `navigator.storage.estimate().usage` 对比 `window.CACHE_BYTES`（构建注入）显示 `缓存中 NN%`；`caches.match('./index.html')` 命中即判为「已缓存 ✓」。缓存满前每 1.5s 轮询（仅设置页打开时）。纯展示，不重复下载
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
- `build_html.py`：base64 编码嵌进 html（US 1250 + EX 1250 ≈ 52MB）
- 发音源是有道 `dictvoice`，已全部下载内嵌，**运行时不再联网**

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

> ⚠️ **例句解析历史坑（已修）**：`build_dataset.py` 旧代码 `s.split("：",1)[-1]` 会把句内含全角冒号的例句（`W: Oh…`→`女：…`、`Directions:…`→`说明：…`）**误截成只剩中文**，18 条例句英文曾整段丢失。已改为正则只剥开头 `例句[（自编）]:` 标签。另：rank 707 `weight` 源表例句为空，已从真题语料补 `Choosing what to eat and drink is key to weight control.`（用原文，非自编）。

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
python scripts/make_pdf_optimized.py   # → 优化版 PDF
python scripts/build_html.py           # → 英语四级单词背诵.html + docs/

# 只改了网页界面(template.html)：
python scripts/build_html.py           # 重新注入数据/音频/配置即可
```

### 9.1 验证网页（工具已备好，在 `tmp/devtest/`）
⚠️ **本机没装 playwright / puppeteer 的包**，只有 Playwright 早先下好的浏览器二进制
（`~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/`）。
所以别去 `import playwright`，用仓库自带的这两个小工具（零依赖，Node ≥21 自带 `WebSocket`）：

```bash
# ① 生成秒开的测试页（真实词条 + 空音频，~100KB；52MB 的成品调界面太慢）
python tmp/devtest/make_testpage.py            # 默认 前 120 词
python tmp/devtest/make_testpage.py 60 400     # 60 词，从第 400 条起（前 100 词是虚词，没词根卡）
#   -> tmp/devtest/testpage.html

# ② 驱动无头浏览器：跑一串 JS 表达式，可选截图
node tmp/devtest/cdp.mjs "file://$PWD/tmp/devtest/testpage.html" \
  '["document.getElementById(\"start\").click()","document.querySelectorAll(\".entry\").length"]' \
  tmp/devtest/shot.png
```
- 每个表达式的返回值按 JSON 打印（promise 会 await），异常会抛出来——所以它同时也是"有没有控制台报错"的检查。
- 常用探针：点 `#start` 进阅读页、点 `.num` 划词、`JSON.parse(localStorage.cet4_reader_v3)` 看 state、`document.querySelectorAll('.entry').length` 数渲染条数。
- 要验真机体积/真音频时，把 url 换成 `file://…/docs/index.html`（52MB，能开，多等几秒）。
- 截图**一律存 `tmp/`**（§0.1）。

---

## 10. 部署（PWA + GitHub Pages）—— ✅ 已推送

托管文件在 `docs/`（index.html + manifest + sw.js + icons），已推送到 `yiyisheh/CET4-vocabulary` 的 **main** 分支。

1. 代码已 push（`docs/index.html` 52MB，GitHub <100MB 可过、仅 LFS 大小警告）。remote = `yiyisheh/CET4-vocabulary`。
   - `intermediate/audio/`（73MB，含不参与构建的 uk/）**已纳入 git 跟踪**；根目录 52MB 的 `英语四级单词背诵.html` 仍 gitignore（可由 build_html 重生成），只保留 `docs/index.html` 上线用。
2. GitHub 仓库 → Settings → Pages → Source 选 **main / docs**（若还没开，这步在网页上点一次）。
3. 访问 `https://yiyisheh.github.io/CET4-vocabulary/`。
4. iPad **Safari** 打开该网址 → 分享 → **添加到主屏幕** → 成为已安装 PWA。

**为什么要 PWA**：iOS 对 `file://` 本地文件的 localStorage 会隔天清空；而**已安装的 PWA 有独立持久存储**，配合 `sw.js` 缓存实现离线+持久，且是 iOS 上最稳的持久化方式。

### 10.1 PWA 自动更新（已改为免手动 bump）
`sw.js` 是 cache-first。**缓存名 `cet4-1250-<hash>` 里的 `<hash>` 由 `build_html.py` 按网页内容自动注入**（`web/pwa/sw.js` 里是占位符 `__BUILD__`）。所以：网页一变 → hash 变 → `docs/sw.js` 字节变 → 浏览器自动重装 SW、重缓存、删旧缓存；网页没变则啥都不下。页面在 `controllerchange` 时**自动刷新一次**显示新版。**改完网页只要 `build_html.py` + push,老设备下次开就更新,无需手动改版本号。**

### 10.2 设置页「版本 / 检查更新」（本轮新增）
- 设置页新增一行：左侧展示 **当前版本号 + 构建时间**（`window.BUILD_INFO`，见 §4 的 `__BUILD_INFO__`），右侧「检查更新」按钮。
- **版本号 = `build_hash` = sw 缓存名里的 hash**，即"页面里显示什么版本"与"决定要不要更新"是同一个值，便于核对。
- 按钮逻辑（template 末尾 IIFE）：`registration.update()` 强制**重新拉取 sw.js**（SW 脚本本身默认绕过 HTTP 缓存）；若线上是新版则字节不同 → 新 SW 装上(`skipWaiting`) → §10.1 的 `controllerchange` 处理器**自动刷新**进新版。检测到 `updatefound` 时提示"发现新版本…"；无新版 `update()` 静默返回，1.6s 后回填"已是最新版本 ✓"。
- **非 http（`file://` 单文件离线版）** 无 SW，按钮置灰显示"离线单文件"（这种版本要更新只能重新拿文件）。
- 已用无头 Chromium 起本地 http 端到端验证：版本行正常显示；无新版→"已是最新版本 ✓"；模拟线上新版(改 sw 缓存名)→自动重载一次进新版；均无控制台报错。

---

## 11. 二次开发怎么改（常见任务配方）

| 想做什么 | 改哪里 |
|---|---|
| 改词条样式/字号/颜色 | `web/template.html` 的 `<style>` → `build_html.py`；**改完务必用 §9.1 截个图看**，别凭 CSS 想象（§3.1 就是被想象出来的错描述） |
| 放临时文件/截图/测试页 | 一律 `tmp/`（§0.1）——gitignore 但用户能直接打开 |
| 加一个设置项 | template：加 state 字段(+启动时的容错/迁移) + 设置页 DOM + `syncSettings()` 同步 UI + 事件；改变渲染内容的必须 `paginate()` |
| 改状态池行为（容量/阈值/取词顺序） | template 的 `ensurePool()`；UI 在 `renderPool()` + `#sw-poolmode/#pool-size/#pool-low/#pool-reset`（§13） |
| 改「哪些词参与排版」 | 只改 `visible()` 一个函数——分页、累计小标、状态池都从它取列表 |
| 改划线样式/区域 | `.entry.marked .num::before`（CSS）+ 点击委托里的 mark 判定 |
| 换/改单词发音 | `fetch_audio.py` 换音源重下 → `build_html.py` 重新内嵌；播放逻辑在 `speak()`（Web Audio，§7） |
| 换/改例句朗读音色 | `fetch_ex_audio.py` 里 `VOICES`（改 edge-tts 声音）→ 删 `intermediate/audio/ex/` 重跑 → `build_html.py`；播放在 `speakEx()`（§7.4） |
| 改起播引子/起音检测 | template `speak()`/`detectOnset()`；引子 `lead=100-skipMs`，默认值 `skipMs:40`（§7.2） |
| 加回英音(UK) | `build_html.py` 恢复 `audio_json("uk")` + `__AUDIO_UK__` 占位符 + template 加回 `audio-uk` 标签与口音切换段（`seg-accent`）。⚠️ 但先确认 §12 的 iPad 无声是否与体积有关 |
| 重跑/补词根 | 子agent 产出 `root_chunks/recall_chunks` → `merge_roots.py` → `build_dataset.py` |
| 改同步行为/字段 | template §8 的 `reconcile()`；只同步 marks+colors 是**用户明确要求**，别擅自扩大 |
| 换同步后端 | 换 `web/supabase-config.json` + `reconcile()/api()` 里的 REST 调用 |
| 改 PDF 版式 | `scripts/make_pdf.py`(底层 build) + `make_pdf_optimized.py`(参数) |

---

## 12. 待办 / 已知限制

- 🟡 **iPad 无声 —— 已改用「解码 Web Audio + 出声 `<audio>`」内核（§7.1），待 iPad 真机复验**：
  - 原现象：iPad 上 Chrome/Safari 能打开但**点词/例句无声**（开发者面板波形正常解码、播放头在走、上下文 running，就是没声）；**手机浏览器正常**。
  - 定位依据：原始 **US+UK 58MB（`<audio>` 播放）在 iPad 正常**；commit `5aae50e` 换成 `AudioBufferSourceNode` 出声后无声；删 UK 到 52MB 仍无声 ⇒ **是播放内核问题，不是体积**（iOS 对 Web Audio 输出遵守静音/会话策略，`<audio>` 豁免）。
  - 修复：出声通道改回 `<audio>`（播裁切好的 WAV blob），保留样本级起播与零切词；桌面无头 Chromium 已验证单词/例句均正常出声、无控制台报错。**iPad 真机复验通过后**可考虑把 UK 加回来（§4）。
  - Edge iOS 打不开是其更严格的内存上限，另算，与此修复无关。
- ✅ **已推送到 main**（§10）；若 Pages 尚未开，去仓库 Settings→Pages 选 main/docs 一次
- ⚠️ **轮换 Supabase secret key**（§8.4）
- 发音依赖浏览器解码一致性：逻辑已全库离线验证零切词，真机（尤其 Safari）建议用开发者模式抽查（§7.3）
- 同步无账号鉴权，靠"同步码不好猜"保护；无实时推送，靠 25s 轮询+聚焦刷新（对背单词够用）
- ~52MB 单文件首次加载需一两秒（用户已接受）
- 词根覆盖 42%：高频里大量日耳曼/功能词本就拆不出，是"准确优先"的合理结果，非缺陷
- 改 `state` 结构须处理 localStorage 迁移，否则老用户数据读不出（如 `skipMs` 314→100 的越界迁移）
- 状态池**不参与多端同步**（只有 marks/colors 同步，§8.1）。两台设备的池各自独立，但因为"已掌握"是同步的，两边补池抽到的词高度一致

---

## 13. 状态池模式（莱特纳 Active Pool）

用户的背诵法：不要一次面对 1250 词，而是维持一个小的**活动池**，反复冲刷池内的词；划掉=熟练剔除；池子被磨到只剩少数顽固词时，**批量注入新词补满**，开启下一轮突击。

### 13.1 参数（设置页可改，存在 state）
| 参数 | state 字段 | 默认 | 含义 |
|---|---|---|---|
| 活动池容量 | `poolSize` | **40** | 池被补满时的词数 |
| 低水位阈值 | `poolLow` | **15** | 池内**剩余**（未划掉）≤ 此值就触发补充 |
| 批量补充量 | — | 自动 = `poolSize − 剩余` | 默认即 40−15 = **25 个新词** |

- 阈值强制 `poolLow < poolSize`（在设置页改和启动时都会 clamp），否则会一划就补、退化成无限流。
- `poolSize` 上限 = 词库长度（1250）。
- 改容量**立即生效**：调小则池当场裁到新容量（保留 rank 最靠前的顽固词）；调大则等下次触到水位再补满。
- 「重置池」按钮 = 清空 `state.pool`，从"最靠前的未掌握词"重新装池。

### 13.2 机制（`web/template.html`）
```
poolRemain()      = state.pool 里还没被划掉的 rank
poolNeedsRefill() = poolMode && poolRemain().length <= poolLow
ensurePool()      = 池的唯一维护者，幂等；返回池是否变化
visible()         = poolMode ? 池内 && 未划掉 : (removeMarked ? 未划掉 : 全量)
```
`ensurePool()` 每次做三件事：① **已掌握的词退池**（`state.pool` 只留 survivors）；② 若容量被调小，裁到 `poolSize`；③ 若 `剩余 ≤ poolLow`，从**全库 rank 从小到大**取"既不在池内、也没被划掉"的词补到 `poolSize`，最后按 rank 升序排回。

- **取词不用游标**：每次补池都从 rank=1 重扫。因此无须持久化"抽到哪了"，取消划线的词会自然变回可抽——自愈、无脏状态。代价是每次补池 O(1250) 的扫描，可忽略。
- **写入有护栏**：新旧池一致（例如书末已无词可注）就不写 localStorage、不返回 true。
- **调用点只有两处**：`paginate()` 开头；以及点击委托的 `mark` 分支里 `poolNeedsRefill()` 为真时。后者是**全站唯一会因为划词而重排页面的地方**——这是刻意的：补池是一个用户应该看见的"下一轮开始"事件，重排后 `state.anchor` 指到新池首词，直接翻到第 1 页。平时划词依旧不重排（不会在手指底下抖）。
- 状态池模式下 `removeMarked` 不再另行生效（池本来就已滤掉划掉的词）。
- 累计小标（`counters`）照常按 `visible()` 的位置算，所以开池模式时数的是**池内**的词。

### 13.3 已验证（`tmp/devtest/` 的两个工具，§9.1）
用 200 词测试页和真实的 `docs/index.html` 都跑过：
- 开启 → 池 = rank 1–40，页面渲染 40 条 ✓
- 划掉 24 个（剩 16 > 15）→ **不补**，仍显示原批 ✓
- 划掉第 25 个（剩 15 ≤ 15）→ **当场补池**：留下 26–40 这 15 个顽固词 + 注入 41–65 共 25 个新词 = 40，页面重排、anchor=26 ✓
- 阈值填 45（≥ 容量 40）→ clamp 到 39 ✓；容量改 10 → 阈值 clamp 到 9 且池当场裁到 10 条 ✓
- 「重置池」→ 按当前容量重新装池 ✓；关掉开关 → 恢复全量 ✓；全程无控制台报错 ✓

---

*本文档随网页一起维护；改了架构记得回来更新。网页源码唯一入口：`web/template.html`。*

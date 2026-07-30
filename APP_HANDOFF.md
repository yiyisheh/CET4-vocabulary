# CET-4 背单词 App —— 开发交接文档 (HANDOFF)

> 这份文档是**给下一个 AI / 开发者的唯一入口**。读完它 + 它指向的几个小文件，就能完整理解并二次开发这个 App，**无需也不要打开任何几十 MB 的大文件**。

---

## 0. ⚠️ 给 AI 的第一条规则：该读什么，绝对别读什么

| 类别 | 文件 | 大小 | 说明 |
|---|---|---|---|
| ✅ **App 源码（读这个）** | `web/template.html` | ~32 KB | **整个 App 的唯一源文件**（HTML+CSS+JS 一体）。改 App = 改这里。 |
| ✅ 构建脚本 | `scripts/build_html.py` `build_dataset.py` `merge_roots.py` `fetch_audio.py` `make_pdf_optimized.py` | 4–8 KB | 见 §4 流水线 |
| ✅ PWA 资源 | `web/pwa/manifest.webmanifest` `web/pwa/sw.js` `web/pwa/icon-*.png` | <20 KB | 见 §7 部署 |
| ✅ 同步配置 | `web/supabase-config.json` | <1 KB | 仅含**可公开**的 publishable key |
| ✅ 词条数据 | `intermediate/entries_full.json` | 544 KB | 1250 词最终数据（无音频），可读 |
| ✅ 词根数据 | `intermediate/roots.json` | 188 KB | 词根/词缀/合成拆解 |
| ✅ 词表源 | `output/high_freq_cet4_df.txt` | 328 KB | rank+音标+释义+例句（DF 排序） |
| 🚫 **AI 绝对别读** | `英语四级单词背诵.html` | **66 MB** | 构建产物（内嵌 2500 条 base64 音频），读了会撑爆上下文 |
| 🚫 **AI 绝对别读** | `docs/index.html` | **66 MB** | 同上，托管用副本 |
| 🚫 **AI 绝对别读** | `intermediate/audio/` | **53 MB** | 2500 个 mp3 源，构建输入，别遍历 |

**一句话**：想看/改 App，永远打开 `web/template.html`；那两个 66 MB 的 `.html` 是**自动生成的产物**，不是源码。

---

## 1. 这个项目是什么

两条产物线，共用同一份 1250 词数据：

1. **PDF 背诵版**（打印用）—— `英语四级高频单词彩色背诵版(优化).pdf`
2. **iPad 网页 App**（背单词用）—— `英语四级单词背诵.html`（单文件离线版）+ `docs/`（托管 PWA 版）

> 语料抓取 / 词频统计 / OCR 那一大套**上游**流水线见 `README.md`，本文档聚焦**下游的 App 与优化版 PDF**（本轮新增的工作）。

数据是从近五年(2021–2025)四级真题统计的高频词，按文档频率(DF)排序取 top-1250。

---

## 2. 目录地图（只列与 App 相关的）

```
English/
├── APP_HANDOFF.md            ← 本文档
├── README.md                 ← 上游语料/词频流水线说明
│
├── web/                      ← 【App 源码集中在这里】
│   ├── template.html         ← App 唯一源文件（构建时注入数据/音频/配置）
│   ├── supabase-config.json  ← 同步配置（publishable key）
│   ├── data.js               ← build_dataset 产出的 window.CET4（构建中间物）
│   └── pwa/                  ← manifest / service worker / 图标
│
├── scripts/                  ← 构建脚本
│   ├── build_dataset.py      ← 词表+词根+音节 → entries_full.json / web/data.js
│   ├── build_html.py         ← 注入数据+音频+同步配置 → 两个成品 html + docs/
│   ├── merge_roots.py        ← 合并各来源词根 → roots.json
│   ├── build_roots.py        ← （备用）DeepSeek 生成词根；**已不用**，词根由子agent产出
│   ├── fetch_audio.py        ← 下载 2500 条有道 mp3 → intermediate/audio/
│   └── make_pdf_optimized.py ← 生成优化版 PDF
│
├── intermediate/             ← 数据与中间产物
│   ├── entries_full.json     ← 【最终词条数据】1250 词
│   ├── roots.json            ← 【最终词根数据】
│   ├── compounds.json        ← 手工补的合成词（work+place…）
│   ├── recall_manual.json    ← 手工补的词缀词（powerful…）
│   ├── root_chunks/          ← 14 个子agent的词根产出（首轮）
│   ├── recall_chunks/        ← 召回轮子agent产出
│   └── audio/                ← 🚫 53MB mp3 源，别读
│
├── output/high_freq_cet4_df.txt  ← 词表源（rank/音标/释义/例句）
│
├── docs/                     ← 【GitHub Pages 托管目录】index.html + PWA 资源
│
├── 英语四级单词背诵.html      ← 🚫 66MB 成品（AirDrop 单文件离线版）
└── 英语四级高频单词彩色背诵版(优化).pdf
```

---

## 3. App 是什么样的（功能总览）

一个 iPad/手机上背四级单词的**单文件离线网页**，仿有道词典卡片风格：

- 词条：序号 · 单词(蓝) · 音标(英/美) · 释义 · 例句 · **词根词缀卡**（绿色标签，约 42% 词有）
- **点序号/左侧空白** → 灰色删除线标记「已掌握」（`markStyle`：变灰划线 / 仅划线）
- **点单词** → 音节拆分 `com·po·si·tion ⇄ composition` 并发音
- **点词条其他处** → 发音（**2500 条美/英音已 base64 内嵌，离线可用**；可调「跳过开头静音」）
- 设置页：显示已划掉词 / 划线样式 / 翻页方式(左右分页·上下无缝) / 口音 / 字号 / 栏数(自动按 PDF 栏宽铺满) / 间距 / 分界线开关 / 背景色(预设+自定义#) / **多端同步**
- 分页：按**实测高度装箱**，像 PDF 一样填满一栏再下一栏，宽屏自动多栏
- **多端同步**（Supabase）：同一同步码的设备之间同步「划线」与「自定义色号列表」

---

## 4. 数据流水线（怎么从词表变成成品）

```
output/high_freq_cet4_df.txt  ─┐
intermediate/roots.json ───────┤─ build_dataset.py ─→ intermediate/entries_full.json + web/data.js
  (+ pyphen 音节)              ┘        │
                                        ├─ make_pdf_optimized.py ─→ 优化版 PDF
intermediate/audio/{us,uk}/*.mp3 ──────┤
web/template.html ─────────────────────┤─ build_html.py ─→ 英语四级单词背诵.html（根，单文件）
web/supabase-config.json ──────────────┤                └→ docs/index.html + docs/{pwa资源}
web/pwa/* ─────────────────────────────┘
```

`build_html.py` 把模板里 4 个占位符替换掉：
- `__DATA__` → 1250 词条 JSON
- `__AUDIO_US__` / `__AUDIO_UK__` → `{word: base64 mp3}`（放在 `<script type="application/json">` 里，不执行、按需解析）
- `__SYNC_CONFIG__` → `web/supabase-config.json` 内容（无则 `null`，同步自动禁用）

---

## 5. `web/template.html` 内部结构（改 App 看这节）

单文件，顶部一段 CSS，下面两个 `<script>`：一个塞数据/音频/配置，一个是 App 主逻辑 IIFE。

### 5.1 关键 CSS 类
- `.entry`（词条，`position:relative`，左内边距 14px 是"序号前的空白"）
- `.headline` `.num`(序号) `.hw`(单词) `.ipa` `.def` `.ex` `.root`
- 划线：`.entry.marked .num::before`（从最左到序号点的删除线）；`.entry.marked{opacity:.5}`（变灰样式）；`#pages.markline`（仅划线样式，不变灰）
- 分栏：`.page{display:flex}` + `.col`，栏数/栏宽由 JS 计算
- 主题变量在 `:root`，`applyTheme()` 按背景色亮度自动切深/浅色

### 5.2 状态 `state`（存在 `localStorage`，键 `cet4_reader_v3`）
```js
{
  showMarked:true,           // 是否显示已划掉
  markStyle:"dim"|"line",    // 划线样式
  divider:true,              // 词条分界线
  mode:"h"|"v",              // 左右翻页 / 上下无缝
  accent:"us"|"uk",          // 口音
  fontScale:1.0,             // 字号（pt×此值，默认≈PDF 1:1）
  cols:"auto"|"2"|"3"|"4",   // 栏数
  spacing:0.35,              // 间距(0..1 → 栏距/留白)
  skipMs:250,                // 起播引子控制：lead = 314-skipMs（默认留64ms引子，见§7）
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
- `paginate()`：读容器宽高→算栏数(auto 时按 `330*fontScale` 目标栏宽)→用隐藏的 `#measure` 实测每条高度→装箱成页→`render()`
- `render()`：拼 HTML，设 `#pages` 的 class（h/v、hideMarked、markline、nodivider）
- 点击委托（`pagesEl` 上一个 click）：判定点在序号左侧→`mark`；点单词→`syl`(音节切换+发音)；其他→发音
- **`speak(word)`**：Web Audio 播放（见 §7）。取内嵌 base64 → `decodeAudioData` 整条解成 PCM（缓存 `{buf,onset}`，上限 48 条）→ `detectOnset()` 检测真起音 → `AudioBufferSourceNode.start(0, onset−lead)` 样本级起播。**不再用 `<audio>.currentTime`**（MP3 中途 seek 不可靠）。非内嵌词/无 Web Audio 时回退 `speakHtml()`(有道 URL)
- `detectOnset(buf)`：稳健起音检测——12ms 窗 RMS、阈值取“每条噪声底×2.5 与 0.0009 的较大者”、要求持续 10ms（忽略孤立杂点、抓得住低幅擦音）
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

## 7. 发音（离线内嵌，Web Audio 播放）

- `fetch_audio.py`：对 1250 词各下 美音(有道 type=2)/英音(type=1) → `intermediate/audio/{us,uk}/{rank}.mp3`（可断点续传）
- `build_html.py`：base64 编码嵌进 html（因此 66MB）
- 发音源是有道 `dictvoice`，已全部下载内嵌，**运行时不再联网**

### 7.1 播放内核：为什么用 Web Audio 而不是 `<audio>.currentTime`
早期方案是 `<audio>` + `currentTime=skipMs/1000` 跳掉开头静音。**这条路错了**：在 MP3 上做运行时 seek 不可靠——① seek 会吸附到 ~24ms 帧边界（落点不准）；② MP3 有「比特池(bit reservoir)」，一帧依赖前面几帧上下文，**从中间 seek 进去、紧跟落点的那一两帧会被解成静音/杂音**。两者叠加会切掉软起音（`/h/ /s/ /f/…`），表现为"开头被切一点点、还时好时坏"。

**现方案**（`speak()`）：`decodeAudioData` 把整条 MP3 **完整解码成 PCM**（带完整上下文、无 seek），再用 `AudioBufferSourceNode.start(0, off)` 从**精确样本**起播。`off` 是对已解码 PCM 的数组下标，样本级精确，彻底绕开上面两个问题。解码结果缓存 `{buf,onset}`（上限 48 条）。iOS 需在点击手势里 `resume()` AudioContext——发音本就由点击触发，天然满足。

### 7.2 起播点：逐条起音归一化（取代旧的"固定 skip + 补静音到314"）
有道源的开头静音**极不均匀**（314ms ~ 1000ms 都有；同一个词 US/UK 还能差好几百 ms）。固定跳一个值 → 长静音词前面留一大段死气。所以改成**逐条检测真起音再归一化**：
- `detectOnset(buf)`：12ms 窗 RMS，阈值 = `max(每条噪声底×2.5, 0.0009)`，要求**持续 10ms** 才算起音——**忽略孤立杂点**（如某些词 330ms 处一个 -53dB 的单点毛刺），**抓得住低幅擦音**。
- 起播 `off = onset − lead`，`lead = 314 − skipMs`（默认 skip 250 → **统一 64ms 引子**）。即：把每个词都表现成"起音在 314ms、skip 后留固定引子"。`skipMs` 滑块(0..314)现在控制这个引子：**越大引子越小越跟手**，314=紧贴起音起播。
- 全库 2500 条离线验证（`detect_full.py` 思路）：**0 切词，引子统一 64–76ms**；choices 这类 ~490ms 死气被削掉。

### 7.3 `align_audio_silence.py` / 314 padding 已“退居备用”
新播放内核**每次实时找真起音**，不再依赖“文件里静音正好是某个值”。所以旧的“补零到 ≥314ms”对齐**已非必需**——`intermediate/audio/` 仍是 git 跟踪的既有产物、无需为发音再跑对齐。脚本保留备用；若哪天重下音频，也**不必**再跑它（起音归一化会自愈）。
- ⚠️ 依赖浏览器解码一致性：逻辑已全库离线验证零切词，但真机（尤其 Safari）建议用**开发者模式**（设置页开关）抽查——面板底部实时画波形与 橙(真起音)/绿(起播)/红(播放头) 线。

---

## 8. 多端同步（Supabase）

### 8.1 只同步这些（用户明确要求）
- ✅ **划线**：每词独立、**最新改动为准(LWW)**；取消划线=写 `v:0` 带新时间戳，也会同步
- ✅ **自定义色号列表**：并集（哪台加了新色号，别台也能选）
- ❌ 其余所有设置 **不同步**
- ❌ **当前选中哪个背景色 不同步**（每台独立）

### 8.2 机制
- 纯 REST(fetch)，**不引 Supabase SDK**。localStorage 是本地事实源，联网时与云端做**双向 LWW 合并**
- 触发：开 App / 每 25s 轮询 / 窗口重新聚焦(visibilitychange) / 本地改动后 800ms 防抖
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
pip install pyphen                 # 音节
# （音频已下好；要重下：python scripts/fetch_audio.py）

# 改了词根/词表后，从数据到成品全量重建：
python scripts/merge_roots.py          # → intermediate/roots.json
python scripts/build_dataset.py        # → entries_full.json, web/data.js
python scripts/make_pdf_optimized.py   # → 优化版 PDF
python scripts/build_html.py           # → 英语四级单词背诵.html + docs/

# 只改了 App 界面(template.html)：
python scripts/build_html.py           # 重新注入数据/音频/配置即可
```

**验证 App**：无头 Chromium 在 `~/Library/Caches/ms-playwright/chromium_headless_shell-*/` 下，可 `--screenshot` 截图；测交互时给页面注入脚本点 `#start` 再操作（历史对话里有大量这种测法）。

---

## 10. 部署（PWA + GitHub Pages）—— ✅ 已推送

托管文件在 `docs/`（index.html + manifest + sw.js + icons），已推送到 `yiyisheh/CET4-vocabulary` 的 **main** 分支。

1. 代码已 push（`docs/index.html` 58MB，GitHub <100MB 可过、仅 LFS 大小警告）。
   - `intermediate/audio/` **已纳入 git 跟踪**；根目录 58MB 的 `英语四级单词背诵.html` 仍 gitignore（可由 build_html 重生成），只保留 `docs/index.html` 上线用。
2. GitHub 仓库 → Settings → Pages → Source 选 **main / docs**（若还没开，这步在网页上点一次）。
3. 访问 `https://yiyisheh.github.io/CET4-vocabulary/`。
4. iPad **Safari** 打开该网址 → 分享 → **添加到主屏幕** → 成为已安装 PWA。

**为什么要 PWA**：iOS 对 `file://` 本地文件的 localStorage 会隔天清空；而**已安装的 PWA 有独立持久存储**，配合 `sw.js` 缓存实现离线+持久，且是 iOS 上最稳的持久化方式。

### 10.1 PWA 自动更新（已改为免手动 bump）
`sw.js` 是 cache-first。**缓存名 `cet4-1250-<hash>` 里的 `<hash>` 由 `build_html.py` 按 app 内容自动注入**（`web/pwa/sw.js` 里是占位符 `__BUILD__`）。所以：app 一变 → hash 变 → `docs/sw.js` 字节变 → 浏览器自动重装 SW、重缓存、删旧缓存；app 没变则啥都不下。页面在 `controllerchange` 时**自动刷新一次**显示新版。**改完 app 只要 `build_html.py` + push,老设备下次开就更新,无需手动改版本号。**

---

## 11. 二次开发怎么改（常见任务配方）

| 想做什么 | 改哪里 |
|---|---|
| 改词条样式/字号/颜色 | `web/template.html` 的 `<style>`，然后 `build_html.py` |
| 加一个设置项 | template：加 state 字段 + 设置页 DOM + `syncSettings()` 同步 UI + 事件；必要时 `paginate()` |
| 改划线样式/区域 | `.entry.marked .num::before`（CSS）+ 点击委托里的 mark 判定 |
| 换/改发音 | `fetch_audio.py` 换音源重下 → `build_html.py` 重新内嵌；播放逻辑在 `speak()`（Web Audio，§7） |
| 改起播引子/起音检测 | template `speak()`/`detectOnset()`；引子 `lead=314-skipMs`，默认值 `skipMs:250`（§7.2） |
| 重跑/补词根 | 子agent 产出 `root_chunks/recall_chunks` → `merge_roots.py` → `build_dataset.py` |
| 改同步行为/字段 | template §8 的 `reconcile()`；只同步 marks+colors 是**用户明确要求**，别擅自扩大 |
| 换同步后端 | 换 `web/supabase-config.json` + `reconcile()/api()` 里的 REST 调用 |
| 改 PDF 版式 | `scripts/make_pdf.py`(底层 build) + `make_pdf_optimized.py`(参数) |

---

## 12. 待办 / 已知限制

- ✅ **已推送到 main**（§10）；若 Pages 尚未开，去仓库 Settings→Pages 选 main/docs 一次
- ⚠️ **轮换 Supabase secret key**（§8.4）
- 发音依赖浏览器解码一致性：逻辑已全库离线验证零切词，真机（尤其 Safari）建议用开发者模式抽查（§7.3）
- 同步无账号鉴权，靠"同步码不好猜"保护；无实时推送，靠 25s 轮询+聚焦刷新（对背单词够用）
- 66MB 单文件首次加载需一两秒（用户已接受）
- 词根覆盖 42%：高频里大量日耳曼/功能词本就拆不出，是"准确优先"的合理结果，非缺陷
- 改 `state` 结构须处理 localStorage 迁移，否则老用户数据读不出

---

*本文档随 App 一起维护；改了架构记得回来更新。App 源码唯一入口：`web/template.html`。*

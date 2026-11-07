# 网页：`web/template.html`

一份 HTML 里放 CSS + JS，无框架、无前端构建。构建与两种产物形态见 [build.md](build.md)；音频、同步、状态池、统计各有专文，这里只讲界面骨架。

## 文件结构

`<style>` → 界面 DOM（`#menu`、各设置子页、`#top` / `#pages` / `#measure` / `#dev` / `#bar`、`#umodal`）→ 几个 `<script>`：两个 `application/json` 音频块（单文件版才有内容）→ 注入的全局量（`CET4`、`AUDIO_INDEX`、`BUILD_INFO`、`CACHE_NAME`、`AUDIO_GAIN`、`SYNC_CONFIG`、`LEGACY_V1`）→ 主逻辑 IIFE → 末尾「检查更新」小 IIFE（[pwa.md](pwa.md)）。

## 视觉：贴着彩色 PDF，不是卡片 App

没有卡片、阴影、色块、彩色标签。白底（或所选背景色）上的多栏文本列表，词条间一条发丝线；字号全写成 `pt × --fs`，100% 时与 PDF 同大。分页按**实测高度装箱**（隐藏的 `#measure` 量每条高度），像 PDF 一样填满一栏再下一栏；auto 栏数按目标栏宽 `330 × fontScale` 算。**改样式务必用 [devtest.md](devtest.md) 截图看，别凭 CSS 想象。**

词条 DOM（顺序即显示顺序）：`.headline`（`.num` 序号 + `.hw` 单词）→ `.ipa` → `.def` → `.core` 或 `.root` → `.phr` → `.ex`（英文 + `.extrans` 中文）→ `.milestone`（累计小标）。

- 主题变量全在 `:root`；`applyTheme()` 按背景亮度整套切深/浅色。`--blue` 是文字强调色，`--fill` 是大面积实底控件色，都由 `state.themeColor` 决定（空 = 默认黑 / 夜间浅灰，`--fill` 用柔和深灰而非纯黑）。
- `.root` / `.core` 只是灰色小字 + 6px 缩进，词素本身加粗，没有专属颜色和边框。
- `.ex` 的点击热区是 padding box：上方间距走 margin（不可点），免得点释义误触朗读。
- 划线：`.entry.marked .num::before` 从最左横穿到序号；`.entry.marked` 变灰，`#pages.markline` 时只划线不变灰。
- 自测遮蔽 `.mask`：文字（含后代）透明 + `--panel` 圆角底，高度不变不重排。遮的是释义、卡片、短语和（可选）例句中文。

## 点击

`#pages` 上一个委托，按 `data-act` 分派：`ex` 朗读例句；`reveal`（遮蔽处）解开同一词条所有 `.mask` 并记入 `state.revealed`；`mark`（序号及其左侧空白）划线；`syl`（单词）切换音节并发音；其他处发音。搜索结果和「全部词表」走同一个委托逻辑。

`entryHTML(e, look)` 有第二个参数（`look` = 搜索结果模式：总显示序号、不遮蔽、带「定位」），**别写 `list.map(entryHTML)`**——map 会把下标当 `look` 传进去。

## 界面层级与返回键

主菜单 `#menu` 是底；其余每个界面是压在导航栈 `nav` 上的一层：`read`（背诵页）、`settings`、`prefs`、`sync`、`stats`、`search`、`browse`（全部词表）、`wheel`（跳页滑块）、`modal`（更新弹窗，经 `window.cet4Nav`）。

- 打开一层 = 显示它 + `nav.open(id, close)`；每层的 `close` 只管收起自己，露出哪层由栈决定。
- 「‹ 返回」= `nav.close(id)`；顶栏「菜单」= `nav.closeAll()`；「定位」= `nav.closeAbove("read")` 或退空后 `enterReading()`。
- 浏览器历史只垫一条：栈不空就 `pushState`，返回键 → `popstate` → 收起栈顶；栈退空时把垫的那条退掉，所以只有在主菜单按返回才离开网页。
- **新页用 `nav.open` / `nav.close`，别直接改 `style.display`**，返回键就自动管到它。

设置分三页：`#settings`（状态池 + 两个入口 + 操作说明）→ `#prefs` 样式与偏好（样式 / 背诵 / 发音三组）、`#syncpage` 同步与更新。加设置项：state 字段（+ 启动时的容错/迁移）→ 子页 DOM → `syncSettings()` 回显 → 事件；影响渲染的要 `paginate()`。

## 「何时刷新」纪律（用户明确要求）

页面内容（哪些词、什么顺序、哪些遮着）**只在主菜单点「重置」时重建**：清空 `state.revealed`、`buildList()`（推进状态池、按设置过滤、乱序时洗牌）存进 `state.list`、重新装箱。其余路径一律不许改内容：

- 「开始背诵」回到同一份 `state.list` 的上次位置；每次启动都先落主菜单。
- `paginate()` 只排版不改内容；`visible()`（哪些词参与）只被 `buildList()` 读。
- 改变内容的设置（去掉已划掉、状态池各项、池内乱序）只改 state，等「重置」生效；纯显示的设置当场 `paginate()`。
- 划词永不重排；状态池触阈值也只在菜单里提示，推迟到下次「重置」。
- `resize` 只在 `#pages` 尺寸真的变了才重排（iOS 切后台回来会发尺寸不变的 resize）；同步拉取只就地切换 `.marked`。

## 搜索与全部词表

- `#search`：`searchWords(q)` 纯数字查序号、含汉字查释义和短语中文、否则查单词和短语英文；排序 完全相同 > 前缀 > 包含 > 短语/释义，同档按 rank，最多 `SEARCH_MAX` 条。永远查全库，**不改 `state.list` / `revealed` / 遮蔽**；只有「定位」(`jumpTo`) 改阅读位置。
- 全部词表（`browseAll`）：显示全库、不遮蔽、不计时，位置单独记在 `state.browseAnchor`；可在这里取消划线把词放回状态池。

## `state`（localStorage 键 `cet4_reader_v3`）

默认值以代码里 `var state = {…}` 为准，这里只列含义。【同步】的字段见 [sync.md](sync.md)，其余都只在本机。

| 字段 | 含义 |
|---|---|
| `list` / `listShuffled` | 冻结的页面内容（rank 数组）及是否乱序（乱序时不显示序号），只有「重置」改 |
| `anchor` / `browseAnchor` | 背诵页 / 全部词表的阅读位置（首词 rank） |
| `marks` | 【同步】划线 `{单词: {v:0或1, t:时间戳}}` |
| `revealed` | 自测已解开的词 `{单词:1}`，只有「重置」清空 |
| `keysV` | 2 = `marks`/`revealed` 已按单词存（[sync.md](sync.md#身份键按单词不按序号)） |
| `poolMode` `poolSize` `poolLow` `poolMax` `shuffle` | 状态池（[pool.md](pool.md)） |
| `removeMarked` | 去掉已划掉的词（重置生效） |
| `selftest` `maskExTrans` `showEx` | 自测、例句中文随卡片遮、显示例句 |
| `mode` `cols` `fontScale` `spacing` `divider` `markStyle` `counters` | 翻页方式（`h` 左右 / `v` 上下）、栏数、字号、间距、分界线、划线样式、累计小标间隔 |
| `bg` / `customColors` | 背景色（不同步）/【同步】自定义色号 |
| `themeColor` / `customAccents` | 主题色 / 自定义主题色（不同步） |
| `skipMs` `exDelay` `accent` | 发音引子、例句延迟（[audio.md](audio.md)）；`accent` 恒为 `us`，仅作 key |
| `studyMs` `studyOthers` `studyStrict` `deviceId` `tlogUpload` | 学习时长（[stats.md](stats.md)） |
| `syncCode` | 同步码 |
| `dev` / `devH` | 开发者模式（波形面板）及其高度 |

**改 state 结构要写迁移**，否则老用户存档读不出。现有迁移写在 state 定义之后（`marked→marks`、`showMarked→removeMarked`、`pool[]→poolMax`、rank 键→单词键、`skipMs` 越界钳位），照着写。

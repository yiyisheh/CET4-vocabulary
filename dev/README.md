# 开发文档

给接手开发的人和 AI。按主题分成几份短文档，**每件事只在一处写**，别处只放链接。

| 文档 | 管什么 |
|---|---|
| [build.md](build.md) | 数据流水线、构建命令、单文件版 / 托管版两种产物 |
| [data.md](data.md) | 词条数据怎么来的：真题义项、词根、核心意象 |
| [web.md](web.md) | 网页源码 `web/template.html`：界面、导航、刷新纪律、`state` |
| [pool.md](pool.md) | 状态池（莱特纳 · 序号上界） |
| [stats.md](stats.md) | 学习时长统计、计时诊断 |
| [audio.md](audio.md) | 单词与例句音频：音源、播放内核、响度 |
| [sync.md](sync.md) | 多端同步（Supabase） |
| [pwa.md](pwa.md) | 部署、离线缓存、手动更新 |
| [synbook.md](synbook.md) | 同义词辨析书 |
| [devtest.md](devtest.md) | 本地验证工具（无头浏览器） |

项目外的两份：[../README.md](../README.md) 是项目首页（PDF 下载、词频统计方法与结论），[../背单词网页.md](../背单词网页.md) 是给使用者的网页说明。

## 该读什么，别读什么

| 文件 | 说明 |
|---|---|
| ✅ `web/template.html` | **网页唯一源文件**（HTML+CSS+JS 一体）。改网页 = 改这里 |
| ✅ `web/synbook.html` | 辨析书唯一源文件 |
| ✅ `scripts/*.py` | 构建与数据脚本，见 [build.md](build.md) |
| ✅ `intermediate/*.json` | 处理好的数据，见 [data.md](data.md) |
| 🚫 `英语四级单词背诵.html` | 49 MB 构建产物（内嵌全部音频），读了会撑爆上下文 |
| 🚫 `docs/` | GitHub Pages 托管目录，全是构建产物。改网页请改 `web/` |
| 🚫 `docs/audio-*.bin`、`intermediate/audio/` | 音频二进制，别读、别遍历 |
| 🚫 `archive/` | 过时脚本、旧数据、旧 PDF 的本地归档（gitignore，现行流程不读） |

## 临时产物一律放 `tmp/`

截图、录屏、测试页、调试数据都写进仓库根目录的 `tmp/`：它在 `.gitignore` 里，但用户能直接打开看。工具本身入库（如 `scripts/devtest/`），产物进 `tmp/`。

## 目录

```
├── README.md · 背单词网页.md        用户文档
├── dev/                            开发文档（本目录）
├── 英语四级高频单词*.pdf             三份成品 PDF
├── CET/                            源数据：真题 PDF 与听力 MP3
├── corpus/                         纯英文语料 + 统计窗口 window.json
├── output/                         词频表与验证图表
├── intermediate/                   词条数据、义项/词根/核心意象的中间产物、音频源
├── synbook/                        辨析书数据与正文
├── scripts/                        构建与数据脚本；devtest/ 是验证工具
├── web/                            网页源码：template.html、synbook.html、pwa/、同步配置
├── docs/                           GitHub Pages 产物
└── tmp/ · archive/                 本地（gitignore）
```

改了架构，回到对应的那一份文档更新；新主题就新开一份，在上表加一行。

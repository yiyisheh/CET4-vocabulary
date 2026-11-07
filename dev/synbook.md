# 同义词辨析书

把 1250 词里意思相近、容易混的词分成 207 组逐组讲。主菜单「同义词辨析」进入。

| | 文件 |
|---|---|
| 分组、词条、例句 | `synbook/四级高频词同义辨析.json` |
| 每组正文 | `synbook/content/G001.md … G207.md`（G001 是手写范文） |
| 模板（唯一源文件） | `web/synbook.html` |
| 构建 | `scripts/build_synbook.py` → `docs/synbook.html` + 根目录 `synbook.html`（单文件版的同目录伴侣，gitignore） |

正文写于 2026-09，早于释义改成「只列真题义项」（[data.md](data.md)），个别组还讲到了真题里没出现的意思；JSON 里成员的 `gloss` / `example` 也是旧词表的，构建不读它们（只用分组、序号）。

**构建顺序**：先 `build_synbook.py` 再 `build_html.py`——书的字节计入网页版本哈希，文件名进 SW 预缓存，所以托管版离线可用；单文件版要同目录有 `synbook.html`。

版式：一组一页、组内向下滚，有目录、弹出检索、跳页滑块（与主 app 同一套趋势逻辑）。目录、顶栏「目录」、检索结果都用 `jumpToPage()` **瞬移不动画**：手机上键盘收起时的视口变化会掐断平滑滚动、卡在两页中间；resize 后再对齐一次。

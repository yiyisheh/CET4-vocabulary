# 部署与 PWA

## 部署

`docs/` 推到 `yiyisheh/CET4-vocabulary` 的 main，GitHub Pages 的 Source 选 main / docs，访问 `https://yiyisheh.github.io/CET4-vocabulary/`。iPad 上用 Safari「添加到主屏幕」装成 PWA——iOS 会清 `file://` 页面的 localStorage，已安装的 PWA 有独立的持久存储。

## 缓存：桶名固定，版本落在文件名上

`sw.js` 是 cache-first，桶名固定为 `cet4-1250`（换名 = 全量重下）。版本信息在：

- **音频包文件名带内容哈希**：音频一变 URL 就变，必然重下；没变就命中缓存。
- `__PRECACHE__`：install 时预缓存的外壳、辨析书、manifest、图标。**故意不含音频包**——包由网页自己下，否则会下两遍。
- `__KEEP__`：PRECACHE + 本次的两个包。activate 时删掉不在 KEEP 里的条目。
- `__BUILD_HASH__`：外壳哈希写进 `sw.js`。浏览器只靠比较 `sw.js` 字节判断有没有新版，只改网页时其余清单都不变，没有它更新就推不到设备。
- `"./"` 不进 PRECACHE（和 `index.html` 是同一份字节）；导航请求回落到 `./index.html`。
- **SW 只拿外壳回答导航请求**。非导航请求取不到就老实失败——否则离线时音频包请求会拿到 HTML 外壳并被当成包缓存，那一版从此哑掉。网页这边也会校验包长度，不符就删掉重下。

## 音频包下载与进度条

网页 `loadPacks()` / `fetchPack()` 先查缓存，没有就 `fetch` + 流式 reader 边读边计数（这才有真进度），校验长度后写进同一个桶；先 us 后 ex；失败挂 `online` 事件重试。`updateCacheUI()` 只展示 `packState`。单文件版显示「已内嵌」。

## 手动更新（用户要求：不自动更新）

- 新 SW install 后**不 `skipWaiting()`**，停在 waiting；页面继续跑旧版。
- 页面发现 waiting SW 时：版本行按钮变「检测到新版本」，弹出 `#umodal`。弹窗的「不再提示」默认勾选，关掉即写 `localStorage.cet4_upd_snooze`，之后不自动弹，但按钮仍可打开。
- 「立即更新」先用 `fetch("sw.js?ping=…", {cache:"no-store"})` 测连通性：失败就在弹窗里报错、不切版；成功才 `postMessage({type:"SKIP_WAITING"})`，`controllerchange` 时重载。
- `hadController` 必须在页面加载时取样，首次安装不重载。
- 没有 waiting 时按钮做 `reg.update()` 手动检查。`file://` 单文件版没有 SW，按钮置灰。
- 只改网页的更新只重下外壳，音频不动。

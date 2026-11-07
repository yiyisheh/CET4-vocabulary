# 学习时长统计

## 计时规则（用户定：只记确实在学的时间）

- 只在**背诵页**开着且网页在前台时算（`studying()`）；`state.studyStrict` 开着时还要求状态池和自测都开着。
- `pointerdown / keydown / wheel / scroll`（document 捕获阶段）各是一次心跳。两次心跳间隔 ≤ `STUDY_GAP` 整段计入，超过就当作走开、**整段不计**（不是截断）；切后台即断开。
- 按本地日期存毫秒 `state.studyMs`；攒几秒写一次盘，切后台 / `pagehide` 时补写——**只在有未存时长时写**，否则会覆盖别处写入的 localStorage。
- 「划掉 N 词」不另存：`marksByDay()` 从 `state.marks` 的时间戳现算（同步来的也算，取消划线和迁移来的 `t=0` 不算）。
- 多端：显示的时长 = 本机 `studyMs` + 其他设备 `studyOthers`（[sync.md](sync.md)）。

## 显示

主菜单进度区一行「今天学习 · 划掉 · 连续 N 天」；「学习统计」子页 `#stats`（`renderStats()`、`statSeries()`）：顶部三张小卡，两张图卡（时长 / 划掉的词）可切最近一周 / 30 天 / 按月。胶囊柱整列可点，**不写「点柱子查看」之类的提示**（用户要求）。

## 计时诊断（排查「记少了」用）

不改计时规则，只记下时间去了哪里。开关：「同步与更新 › 上传计时诊断」（`state.tlogUpload`，默认关）。

- 本地 localStorage `cet4_tlog` 按分钟分桶（保留 3 天），字段（毫秒）：c 计入 / g 间隔超时被丢 / s 背诵页但池或自测没开 / o 其他页面 / t 切后台前那段 / f 回前台到第一次操作 / h 在后台 / n 心跳数 / L 长间隔次数 / x 最长间隔。
- 操作日志 `e`：每件事一句中文（词条操作带单词、翻页带来源和页码、界面切换、搜索、前后台、不计时空档）；另有 document 捕获阶段的通用 click/change 记录，从界面读行标题和新值，新增设置项不用改埋点。
- 上传随 `reconcile()`：`kind "tlog"`（item `设备id|YYYYMMDDHHmm|c,g,…`，秒）和 `kind "tev"`（item `设备id|YYYYMMDDHHmm|序号|句子`，每行 ≤600 字，受主键索引长度限制）。已结束的分钟才传、只传一次。
- 分析：`python scripts/devtest/tlog_report.py <同步码> [YYYYMMDD]`（只读），把几台设备的日志排成一条时间线。排查完关掉开关；已传的行留在云端（anon 不能删）。

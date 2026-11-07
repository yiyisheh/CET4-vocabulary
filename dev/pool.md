# 状态池（莱特纳 · 序号上界）

用户的背法：不一次面对 1250 词，只背开头一段序号范围里还没划掉的词；划掉 = 记住了；剩下的少到阈值，范围往后推，补进新词。

## 参数

| 设置 | state | 含义 |
|---|---|---|
| 池大小 | `poolSize` | 要始终保持的「没划掉的词」数量 |
| 推进阈值 | `poolLow` | 剩余 ≤ 它就推进；强制 `1 ≤ poolLow < poolSize` |
| 当前上界 | `poolMax` | 整个功能**唯一的状态**：只背 rank ≤ 它且没划掉的词 |
| 池内乱序 | `shuffle` | 重置时把池内的词洗牌；新词仍按序号进入 |

默认值见 `template.html` 的 `state`。

## 机制

```
visible()     = poolMode ? (rank ≤ poolMax && 未划掉) : (removeMarked ? 未划掉 : 全量)
poolRemain()  = 上界内还没划掉的词数（「剩余」）
ensurePool()  = 幂等：先保证 poolMax ≥ poolSize，再 while(剩余 ≤ poolLow) poolMax += poolSize − poolLow，到 1250 收口
```

- **步长是 `poolSize − poolLow`**：剩余从阈值补回到池大小，工作集稳定在 `poolSize`。（步长 = `poolLow` 是旧 bug：只在第一轮补满。）
- **盯着剩余推进**，不按已掌握数定时推进——后者会让剩余一路缩水。
- 上界只进不退，改参数不丢进度；「重置范围」才把上界拉回 `poolSize`。
- 「已掌握」永远是全库真实总数，不按轮归零。
- 调用点：`buildList()`（即「重置」）和设置页改参数之后。`paginate()` 与划词都不调用——划到阈值只在主菜单进度区提示「点重置将推进到 N 号」（`renderMenu()`），见 [web.md 的刷新纪律](web.md#何时刷新纪律用户明确要求)。
- 状态池开着时 `removeMarked` 不另起作用；累计小标数的是范围内剩余的词。
- 不参与多端同步：上界各设备独立，但划线是同步的，节奏基本一致。

UI 在 `renderPool()` 与 `#sw-poolmode` / `#pool-size` / `#pool-low` / `#pool-reset`。

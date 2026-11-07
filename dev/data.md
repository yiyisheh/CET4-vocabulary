# 词条数据

原则（用户定）：**准确优先于覆盖**——拿不准就留空，不硬编；只教真题里出现过的东西。标注、词根、核心意象都由 Claude 子 agent 完成，不用其他模型的 API。

最终数据是 `intermediate/entries_full.json`（`build_dataset.py` 产出，构建见 [build.md](build.md)）。每词字段：`rank word uk us def ex ex_label syl root core phr`，另有 `def0`/`ex0`（旧释义/例句，不进 app）。

## 统计窗口

参与统计的年份只在 `corpus/window.json` 配置（`scripts/corpus_window.py` 读）。词频脚本和义项流水线都从这里取卷子；加入新一年只改这里，再对新句子补标注。

## 真题义项：释义 / 例句 / 短语

只显示近五年真题里出现过的义项，例句取首要义项的真题原句，另有「常见短语」行。

- **流水线**（任务书：A/B/D/E 用 `intermediate/sense_chunks/PROMPT.md`，C 用 `PROMPT_C.md`，固定短语的口径两者共用 `PHRASE_RULES.md`）：
  `extract_sense_contexts.py`（抽句子，出 A/B 任务：定义项表）→ `sense_store.py`（入库，按句子文本哈希，与窗口无关）→ `make_label_tasks.py` + `c_task.py`（C 任务：其余句子按义项表标）→ `merge_senses.py ROUND`（计数；缺例句出 E 任务、缺短语释义出 D 任务；齐了写 `senses.json` / `phrases.json` / `tmp/senses_review.md`）。
  `sense_chunks/` 是标注任务及输出，换统计窗口时要用，别删。
- **规则**（`merge_senses.py` 顶部常量）：每套卷子一个义项最多算 3 次（`PAPER_CAP`）；答题说明不参与排序和例句；义项要在 ≥2 句里出现才显示；功能词最多 6 个义项（`FUNC_MAX`）；有核心意象卡的词释义只列前 5 个（`CORE_MAX`），其余只在卡片里出现。
- **短语**：真题出现 ≥3 次，每词最多 5 条。
- **人工修正层** `intermediate/sense_overrides.json`：merge（合并重复义项）、promote（首要义项由人定，如 run→跑、leave→离开）、drop、demote、keep（补回核心义项）、no_form_prefix、phrases（修短语）。
- **改了例句要重配音**：`fetch_ex_audio.py` 跳过已有文件，先删掉例句变了的 rank 的 `intermediate/audio/ex/{rank}.mp3`。

## 词根

- 来源：子 agent 首轮 `intermediate/root_chunks/out_*.json` → 召回轮 `recall_chunks/out_*.json` → 手工补 `recall_manual.json`（词缀词）、`compounds.json`（合成词）。
- `merge_roots.py` 按优先级合并、去掉「词根 = 单词本身」的循环项 → `roots.json`。`part.type` ∈ {前缀, 词根, 后缀, 词}。
- 覆盖率不高是正常的：高频词里大量日耳曼词、功能词本来拆不出。
- 重跑：子 agent 处理 `root_chunks/in_*.json`，再 `merge_roots.py`。

## 核心意象

给拆不出词根的多义小词（take / get / over）一个具体画面，加一行义项推导：

```json
"take": {"image": "主动伸手，把外面的东西拿到自己这边",
         "derive": "拿；取 ⇒ 采取（把办法拿来用）；乘坐（…）；服用（…）；花费（…）"}
```

- **只做没有词根拆解的词**，两种卡互斥；`merge_core.py` 会丢掉落在有词根词上的卡。
- 画面必须是真实的核心义；串不起来的义项写「X 单独记」，整词串不起来就不做。
- `derive` 必须覆盖该词**全部**义项（释义行最多只显示 5 个）；只剩一个义项的词不做卡，除非义项抽象易误解（手写在 `v2_single.json`）。
- 来源：`python scripts/core_task.py make` → `core_chunks/v2_in_XX.json`；子 agent 按 `core_chunks/PROMPT_v2.md` 写 `v2_out_XX.json`；`core_task.py check v2_XX` 校验覆盖了每个义项。`core_manual.json` 里写 `null` = 人工否决，压过子 agent 产出。
- 改一条：直接改对应的 `v2_out_XX.json` 或 `v2_single.json` → `merge_core.py` → `build_dataset.py`。

## 词条在页面上的顺序

网页和彩色/黑白 PDF 相同：序号+单词 → 音标 → 释义 → 核心意象卡或词根卡 → 短语 → 例句。查缺补漏版不放卡片，释义列全部义项。

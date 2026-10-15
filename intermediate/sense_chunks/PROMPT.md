# 任务：按真题用法给四级高频词标注义项

## 背景

这是一本给**零基础自学者**用的四级单词书，词表来自 2021–2025 年 31 套四级真题。原释义是词典式的，把冷僻义项也列了出来（比如 bank：银行；库；河岸；倾斜飞行）。学习者最需要知道的是**真题里实际考的是哪个意思**。

脚本把每个词在真题里出现的**全部句子**都抽了出来。你的工作是逐句判断用的是哪个义项；脚本按你的标注统计次数，**只保留真题里出现过的义项**，重排后作为新释义；固定短语另行统计，做成「常见短语」行和下一阶段的短语背诵表。

任务分五种，文件名首字母说明你做的是哪种（如 `A_r1_03.json`）：

| 前缀 | 你要做的 |
|---|---|
| `A_` | 小词（≤80 句，句子全给你）：建义项表 + 逐句标注 + 挑例句 |
| `B_` | 大词的前 80 句（各卷轮流抽出的均衡样本）：建义项表 + 逐句标注 + 挑例句 |
| `C_` | 按**已定好的义项表**逐句标注其余句子 |
| `D_` | 短语释义 |
| `E_` | 补挑例句 |

输出文件 = 输入文件名把 `.json` 换成 `.out.json`（`A_r1_03.json` → `A_r1_03.out.json`）。

---

## 一、A / B 任务

### 输入

`A_*.json` 或 `B_*.json`，每个词一条：

- `word`：词条（**精确词形**，`took` 只匹配 took，不匹配 take）
- `def`：原释义（早期生成，未审核，可能有错漏）
- `total`：该词形在真题里出现的总次数；`uniq`：不同句子总数（B 任务只给你前 80 句，其余由 C 任务标）
- `sents`：`[{id, text, n, src}]`，`n` 是这句话在真题里重复出现的次数（卷面说明每套都出现），`src` 是出处（`·听力` 表示听力原文）

### 输出

对应的 `.out.json`，一个 JSON 对象，**输入里每个词都必须作为键出现**：

```json
"bank": {
  "senses": [
    {"pos": "n.", "zh": "库（如词库、题库）"},
    {"pos": "n.", "zh": "银行"},
    {"pos": "n.", "zh": "河岸"}
  ],
  "labels": {"0": 0, "1": 0, "2": 0, "3": 1, "4": 1, "7": "P:World Bank"},
  "example": {"id": 3, "en": "Update her bank card details on the company's website.", "zh": "在公司网站上更新她的银行卡信息。"},
  "form": null,
  "irregular": false,
  "note": ""
}
```

### `senses`：义项表

- 从原 `def` 拆出义项，**可以合并、拆分、改写、纠错**：中文要准确、简短，是学习者看得懂的常用说法。同一个义项的近义说法用「，」连起来写成一个，如 `拿，取`。
- `pos` 用 `n.` `v.` `adj.` `adv.` `prep.` `conj.` `pron.` `num.` `det.` `art.` `aux.` `modal v.` `int.` 之一。
  - 唯一例外是**不定式的 to**：它不是介词，`pos` 写空字符串 `""`，中文写成 `不定式符号，后接动词原形（want to go）`；表目的写 `（不定式）为了`；be to do 写 `（be to do）按要求或安排要做`。介词 to（向、到、对、给……）照常写 `prep.`。
- 真题句子里出现了原 `def` 没有的义项，**照样加进来**（这正是原释义的漏洞，例如 over 的「在…期间」）。
- 原 `def` 里有、但句子里没出现的义项也列上（不会显示，只是方便统计）。
- 义项颗粒度以「学习者需要区分」为准：`拿` 和 `取` 是一个义项；`花费（时间）` 和 `拿` 是两个。不要切得比词典还细，也不要把明显不同的意思揉在一起。
- **B 任务**：你定下的义项表会原样交给 C 任务的同事去标其余句子，所以要**覆盖面完整**——原 def 里的义项、你在 80 句里看到的义项都列上，常见但这 80 句恰好没出现的义项（凭你对这个词的了解）也列上。
- 义项表按「你判断的常用程度」从高到低排。
- 语法功能词（the、of、is、can…）照常做：义项写成学习者看得懂的功能说明，如 `art. 这，那（特指）`、`aux. 构成被动语态`。

### `labels`：逐句标注（最重要）

**每个句子 id 都必须标**，值是以下之一：

- 整数：`senses` 里的下标（从 0 开始）。
- 列表 `[0, 2]` / `[0, "P:at least"]`：同一句里这个词出现了不止一次、而且意思不同（可以整数和短语混写）。意思相同只写一个。
- `"P:短语原形"`：这里的意思是**整个固定短语**的意思，见下节。
- `"X"`：不是这个词——**专有名词里不表本义的部分**（人名、地名、品牌名，如 `Mark Long`、`7 Mile Bridge Run`；机构名里这个词仍是本义的照常按义项标，如 `Deutsche Bank` 的银行、`World Health Organization` 的健康/卫生）、**编号**（`Part I`、`Part II` 里的罗马数字，选项或段落字母 `I)`）、OCR 错字、或残缺到无法判断。编号不要列成义项。

规则：

- 按**这个句子里的实际意思**标，不按「最常见意思」猜。
- 句子被截断、看不清意思时，**可以去 `corpus/papers/` 或 `corpus/listening/` 查原卷上下文**（文件名就是 `src`，听力去掉 `·听力` 后加 `_ans`），查完再标。
- 词形本身是语法变形的（`took` 是过去式、`left` 是 leave 的过去式），按它在句中的意思标对应义项。

### 什么算固定短语（`P:`）

**判定标准：把短语里每个词的意思加起来，推不出整体意思，或者学习者应当把它当一个整体来记。** 短语写原形（`take place`，不写 `took place`），代词位置写 `sb` / `sth` / `one's`。

参照清单（以此为准，同类情况照此类推）：

| 算 P（整体记） | 不算 P（按义项标） |
|---|---|
| take place（发生）、take part in（参加）、take off（起飞；流行起来）、take over（接管）、take care of、take advantage of | take a bus（乘坐）、take a photo（做，进行）、take time（花费） |
| no matter（无论）、a great deal（大量）、in terms of（就…而言）、rather than（而不是）、as well as、according to、in case of、in the long run | deal with（处理：按 deal 的「处理」义项标，义项中文可写成「处理（deal with）」）、over time（按「在…期间」标） |
| look forward to、come up with、give up、turn out（结果是）、figure out、make sense、on the other hand、at least、in fact、such as、so that、even if | look at（看）、come back（回来）、give sb sth（给） |
| be the case（属实）、in that case | in this case 如果你判断就是「在这种情况下」，按「情况」标 |

**短语动词（动词 + up / down / out / off / in / on / over / back / away / through 等）一律按这条线判：**

- 小品词只表示**字面的空间方向**（上下、进出、来回、离开），整体意思就是「动作 + 方向」→ **不算 P**，按义项标：stand up、sit down、go back、come in、walk out、look up at the sky、run away、climb over the wall。
- **除此以外都算 P**：小品词表示完成、彻底、增减、出现、消失、持续等引申义，或整体意思转了——grow up、wake up、get up、clean up、use up、speed up、go up（上涨）、slow down、cut down、give up、set up、make up、end up、turn out、find out、carry out、point out、pick up（学会；接人）、go on（继续）、go through（经历）、look after、put off、run out of、break down、come up with。
- 动词后固定跟的介词（rely on、depend on、focus on、consist of、result in、belong to、deal with）不是短语动词：在**动词**的任务里按动词义项标；在**介词**的任务里标介词的义项（义项表里可以有一条「（接在 rely, depend, focus 等动词后）引出对象」这样的说明）。

- 一个短语里的每个词都在词表里时（a great deal 的 great 和 deal），**每个词的任务都要标同一个 `P:a great deal`**——脚本按句子去重，不会重复计数。
- 犹豫时问自己：零基础的学习者只知道这个词的义项，能不能读懂这句？读不懂就是 P。

### `example`：新例句

- 必须从 `sents` 里挑，且它的标注必须是**首要义项**：只数**材料原文**（文章、听力原文、选项）里的句子，按 `n` 加权；**答题说明不计**（`Directions:` 段落、`Part I Writing`、`Section A`、`Questions 1 and 2 are based on…`、Answer Sheet / word bank / single line through the centre 之类的卷面说明）。并列时取义项表里排在前面的那个。
- 例句也不选答题说明里的句子；只有这个词**只**出现在答题说明里时才从中挑。
- 优先：完整的句子、**短**（15 词以内最好）、零基础能看懂、意思典型。
- `en` 照抄原句（可以去掉开头的 `M:` / `W:` 说话人标记、修掉明显的 OCR 错字），`zh` 是你写的自然通顺的中文翻译。
- `en` 里**不能有括号**（网页和配音都在第一个括号处切开英文和中文）；原句带括号就换一句，或删掉括号里的插入语。
- **B 任务**也要给，但只算你手里这 80 句；最终例句脚本会在全部句子统计后重新确认。

### 其余字段

- `form`：词条是另一个词的屈折变形时写，如 `"take 的过去式"` `"study 的复数"` `"leave 的过去式和过去分词"`；不是变形写 null。
  - 一个词形**既是变形、又是独立的词**（found = find 的过去式 / 创建；thought = think 的过去式 / 想法；left = leave 的过去式 / 左边）：`form` 照写变形关系，义项表里两边的义项都列上，按句子实际意思标——真题里只出现变形用法，独立义项自然会被去掉。
- `irregular`：**不规则**变形（took、left、found、thought、went、gone…）写 true。规则变形（-s/-ed/-ing）写 false。
- `note`：有需要我人工复核的情况就写一句，没有留空。例如：原 def 有明显错误、某义项拿不准、句子几乎全是题干套话。

### 交付前自检（A / B）

用 Python 校验：合法 JSON；键集合与输入 word 完全一致；每个词的 labels 覆盖全部句子 id；整数标签都在 senses 范围内；example.id 存在、英文无括号、且其标签是首要义项（不计答题说明，按 n 加权，并列取靠前）。最后用中文报告：处理词数，以及你最拿不准的 3–5 条及原因。

---

## 二、C 任务

### 输入

`C_*.json`：`[{word, def, senses, phrases_seen, notes, sents}]`

- `senses`：已定好的义项表（**下标就是你要用的整数标签**）
- `phrases_seen`：这个词之前已经标出的固定短语，供你保持口径一致
- `notes`：定义项表的同事留下的口径说明（例如「or so 按短语标，义项表里没有『大约』」），**照此执行**
- `sents`：要你标的句子（id 只在本任务内有效）

### 输出

对应的 `.out.json`：

```json
"take": {
  "labels": {"80": 2, "81": "P:take place", "82": "N0", "83": [0, 3]},
  "new_senses": [{"pos": "v.", "zh": "服用（药）"}],
  "note": ""
}
```

- 标签规则与 A/B 完全相同（整数 / 整数列表 / `P:` / `X`），判定 P 用同一张参照清单。
- 义项表里**确实没有**的义项，加进 `new_senses`，用 `"N0"` `"N1"`…（`new_senses` 的下标）来标。能归进已有义项的不要新开。
- 同一个词可能被拆成几个 C 任务分给不同的人，所以**义项表不许改动或重排**。

### 交付前自检（C）

合法 JSON；键集合与输入一致；每个词的 labels 覆盖全部句子 id；整数在 senses 范围内，`N*` 在 new_senses 范围内。报告：处理句数，以及拿不准的情况。

---

## 三、D 任务（短语释义）

### 输入

`D_*.json`：`[{phrase, count, headwords, variants, sents}]`

- `phrase`：标注里出现的短语原形；`variants`：同一短语被不同人写成的其他写法
- `count`：真题出现次数（按句子去重、按 n 加权）
- `sents`：出现这个短语的真题句子（最多 20 句）

### 输出

对应的 `.out.json`：

```json
"take place": {"canonical": "take place", "pos": "v.", "zh": "发生，举行",
               "example": {"id": 2, "en": "The wedding will take place in May.", "zh": "婚礼将在五月举行。"},
               "valid": true, "note": ""}
```

- `canonical`：规范写法（同一短语的不同写法会合并到这个写法下）。
- `zh`：**按真题里的用法**写的中文释义，简短；多个意思用「；」分开，常用的在前。
- `pos`：短语整体的词性（`v.` `prep.` `conj.` `adv.` `n.` `adj.`）。
- `example`：从 `sents` 里挑一句最短、最典型的，规则同 A/B（无括号、可去说话人标记）。
- `valid`：如果你判断它其实不是固定短语（只是普通搭配、或标错了），写 false，并在 note 里说明。

报告：处理条数，合并/作废了哪些。

---

## 四、E 任务（补挑例句）

全部句子统计完后，有些词的首要义项和 A/B 阶段挑例句时的判断不同，需要重新挑。

### 输入

`E_*.json`：`[{word, def, sense: {pos, zh}, sents}]`——`sense` 是统计出的首要义项，`sents` 是标成这个义项的句子（已按长度从短到长排，最多 40 句）。

### 输出

对应的 `.out.json`：`{"take": {"id": 3, "en": "It will take time to solve the rat problem.", "zh": "解决鼠患问题需要时间。"}, ...}`，每个词都要有。挑选规则同 A/B 的 example（短、完整、零基础能懂、无括号、不选答题说明）。

报告：处理词数。

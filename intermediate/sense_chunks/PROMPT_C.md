# C 任务：按定好的义项表给真题句子标义项

## 这件事是干什么用的

这是一本给**零基础自学者**用的四级单词书。每个词只显示**真题里实际出现过的义项**，按出现次数排序；固定短语另做成「常见短语」行。每个词的义项表已经由同事看过一批句子（下面叫「B 样本」）定好了。你标的是这个词在 2021–2025 年真题里**其余的全部句子**。

脚本只拿你的标注做三件事：**数出每个义项出现了几句**（决定哪些义项保留、谁排第一），**数出每个固定短语出现了几次**，以及**发现义项表里漏掉的义项**。所以每一句都要按它的实际意思标准确。

## 输入：`C_r1_NN.txt`

**只读这个文件**（同名的 `.json` 是给脚本用的，不用看）。一个任务里有一个或几个词，每个词一段：

- **义项表**：行首数字就是你要写的标签。每条后面有「B 样本 n」（同事标的那批句子里这个义项有几句）和一条 B 样本例句，用来对齐口径。
- **已标过的短语**：这个词之前已经按固定短语标过的，口径保持一致。
- **口径说明**：定义项表的同事留下的规则，**照此执行**。
- **句子**：每行 `编号 | 句子`，词在句中用【】标出（同一句出现几次就标几次）。句子按【】**后面跟的词**排序，同类用法挨在一起。少数句子是真题里被切断的半句。
- 行尾可能有脚本给的**提示**，只是提醒，**由你判断**：
  - `?P:at least`：这句里【】周围出现了这个短语的字样，库里有人把它标成过固定短语。真是固定短语就标 P，只是字面碰巧连在一起就按义项标。
  - `?X`：【】处的词在句中大写，可能是人名、地名、机构名。

句子截断或看不懂时，可以查原卷上下文：`python scripts/c_task.py ctx C_r1_NN 词 编号`。

## 两种模式（每个词段的标题写着）

- **全标**：每一句都写一行标签。
- **找例外（默认义项 d）**：这个词在 B 样本里 90% 以上都是义项 d。每一句你都要照样读、照样判断，但**只写不是 d 的句子**（别的义项、短语、X、新义项）；没写出来的句子脚本一律算作 d。所以漏写一句例外，它就会被错算成 d。

## 标签

- 整数：义项表的下标。
- `P:短语原形`：这里的意思是**整个固定短语**的意思（见下表）。
- `X`：不是这个词，包括专有名词里不表本义的部分（人名、地名、品牌名，如 Mark Long、7 Mile Bridge Run；机构名里这个词仍是本义的照常按义项标，如 Deutsche Bank 的「银行」）、编号（Part I 的罗马数字、选项或段落字母 I)）、OCR 错字、残缺到无法判断的句子。
- `N0`、`N1`……：义项表里**确实没有**的义项。先在这个词段里定义，再使用。能归进已有义项的不要新开；义项表本身不许改动或重排（同一个词分给了好几个人）。
- 同一句里【】出现不止一次，而且意思不同：用 `;` 连起来写，如 `0; P:at least`。意思相同只写一个。

按**这句话里的实际意思**标，不要按「最常见的意思」去猜。词形本身是变形的（took、left），按它在句中的意思标对应的义项。

## 什么算固定短语（`P:`）

**判定标准：把短语里每个词的意思加起来推不出整体意思，或者学习者应当把它当一个整体来记。** 短语写原形（`take place`，不写 `took place`），代词位置写 `sb` / `sth` / `one's`。

参照清单（以此为准，同类情况照此类推）：

| 算 P（整体记） | 不算 P（按义项标） |
|---|---|
| take place（发生）、take part in（参加）、take off（起飞；流行起来）、take over（接管）、take care of、take advantage of | take a bus（乘坐）、take a photo（做，进行）、take time（花费） |
| no matter（无论）、a great deal（大量）、in terms of（就…而言）、rather than（而不是）、as well as、according to、in case of、in the long run | deal with（处理：按 deal 的「处理」义项标）、over time（按「在…期间」标） |
| look forward to、come up with、give up、turn out（结果是）、figure out、make sense、on the other hand、at least、in fact、such as、so that、even if | look at（看）、come back（回来）、give sb sth（给） |
| be the case（属实）、in that case | in this case 如果你判断就是「在这种情况下」，按「情况」标 |

**短语动词（动词 + up / down / out / off / in / on / over / back / away / through 等）一律按这条线判：**

- 小品词只表示**字面的空间方向**（上下、进出、来回、离开），整体意思就是「动作 + 方向」→ **不算 P**，按义项标：stand up、sit down、go back、come in、walk out、look up at the sky、run away、climb over the wall。
- **除此以外都算 P**：小品词表示完成、彻底、增减、出现、消失、持续等引申义，或者整体意思转了——grow up、wake up、get up、clean up、use up、speed up、go up（上涨）、slow down、cut down、give up、set up、make up、end up、turn out、find out、carry out、point out、pick up（学会；接人）、go on（继续）、go through（经历）、look after、put off、run out of、break down、come up with。
- 动词后固定跟的介词（rely on、depend on、focus on、consist of、result in、belong to、deal with）不是短语动词：在**动词**的任务里按动词义项标；在**介词**的任务里标介词的义项（义项表里一般有一条「（接在 rely, depend 等词后）引出对象」）。

拿不准时问自己：零基础的学习者只知道这个词的各个义项，能不能读懂这句？读不懂就是 P。

## 输出：`C_r1_NN.labels.txt`

纯文本，每个词一段，**任务里的每个词都要有 `# 词` 这一行**（找例外模式下一句例外都没有，也要写这一行）：

```
# take
N0 | v. | 服用（药）
note: 有几句 take 是篇名的一部分，按义项标了
4124 P:take place
4125 X
4130 N0
4131 2; P:take part in
```

- `# 词`：开始一个词段，词照抄段标题。
- `N0 | 词性 | 中文`：新义项，按 N0、N1… 的顺序定义（词性用 n. v. adj. adv. prep. conj. pron. num. det. art. aux. modal v. int.）。
- `note: …`：可选，每个词最多一条。需要人工复核的情况写在这里，比如义项表有明显缺漏、某个义项的界线拿不准。
- `编号 标签`：一句一行。

写完后运行：

```
python scripts/c_task.py check C_r1_NN
```

它会检查格式、编号、标签范围，以及全标模式有没有漏句。通过后会自动生成 `C_r1_NN.out.json`，并打印每个词的标签分布。有问题就按提示修改 `.labels.txt` 再跑，直到通过。打印的分布可以顺便看一眼合不合理（比如某个义项多得反常）。

## 回报

用中文简短回报：处理句数，每个词的例外或新义项大概有多少，以及最拿不准的 3 条（编号和原因）。

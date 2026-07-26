# 词表例句配音接入规格（交给 Claude Code 实现）

## 背景

已有一个单词表 HTML 页面，单词发音已通过有道接口实现（无鉴权公开 URL，前端直接拼）。
现在要为**例句**加配音，使用 Azure TTS。

## 核心架构决策：离线预生成，不要前端直连

**Azure Speech 需要订阅密钥，绝对不能放进前端 HTML。**

方案：写一个一次性脚本，把所有例句批量合成 mp3 存到本地目录，前端引用静态文件路径。
词表内容固定，生成一次即可；之后播放零延迟、离线可用、无 API 调用。

不要做后端代理，不要做前端实时合成。

---

## 一、音色配置

只用这三个，全部美音，**随机分配**：

| 变量名 | Azure voice name |
|---|---|
| ASHLEY | `en-US-AshleyNeural` |
| AMBER  | `en-US-AmberNeural` |
| ANDREW_HD | `en-US-Andrew:DragonHDLatestNeural` |

### 随机分配必须是确定性的

不要用 `random.choice()`。用词条 ID 或单词字符串做哈希取模：

```python
VOICES = [ASHLEY, AMBER, ANDREW_HD]
voice = VOICES[int(hashlib.md5(word.encode()).hexdigest(), 16) % 3]
```

理由：脚本要支持断点续跑和增量补录。如果用真随机，重跑时同一个词会换音色，
已生成和新生成的文件音色不一致，且无法复现。确定性哈希保证同一个词永远是同一个声音。

### 音色分配要记录下来

生成时把 `word -> voice` 的映射写进一个 `voice_map.json`，方便日后排查和调整。

---

## 二、Azure API 接入

### 前置（用户手动完成，脚本不负责）

1. 注册 Azure 账号，创建 Speech 资源，定价层选 **F0（免费）**
2. 拿到 **Key** 和 **Region**（如 `eastus`）
3. 密钥通过环境变量传入：`AZURE_SPEECH_KEY`、`AZURE_SPEECH_REGION`
   - **不要硬编码，不要写进任何提交到 git 的文件**
   - 加 `.env` 到 `.gitignore`

### REST 接口

```
POST https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1

Headers:
  Ocp-Apim-Subscription-Key: {KEY}
  Content-Type: application/ssml+xml
  X-Microsoft-OutputFormat: audio-24khz-48kbitrate-mono-mp3
  User-Agent: vocab-tts

Body: SSML（见下）
```

也可以用官方 SDK（`pip install azure-cognitiveservices-speech`），REST 更轻，二选一。

### SSML

标准声音（Ashley / Amber）可以用完整 SSML：

```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <voice name="en-US-AshleyNeural">
    <prosody rate="0%">The sentence goes here.</prosody>
  </voice>
</speak>
```

**语速用默认值 `0%`，不要降速。** 四六级听力官方语速是 140–160 词/分钟，
Azure 神经声默认值已经在这个区间，刻意放慢反而不利。

**⚠️ HD 声音（Andrew）对 SSML 支持不完整**，`prosody`、`style` 等标签可能被忽略或报错。
实现时对 HD 声音走简化路径：只包 `<speak>` + `<voice>`，不加 `prosody`。
先用一句话实测确认，不要假设。

### 文本转义

例句里有 `&`、`<`、`?` 等字符，SSML 是 XML，**必须 `html.escape()`**，否则报 400。

---

## 三、脚本要求

### 输入

从现有词表数据源读取（HTML 里已有结构化数据的话直接解析，
否则先导出成 CSV/JSON）。每条至少需要：`id`、`word`、`sentence`。

### 输出

```
audio/sentences/0132_were.mp3
audio/sentences/0133_students.mp3
...
audio/voice_map.json
```

文件名规则：`{4位序号}_{单词}.mp3`，单词里的非字母数字字符替换成 `_`。

### 必须实现的行为

- **断点续跑**：文件已存在则跳过。中断后重跑不重复消耗配额。
- **失败重试**：网络错误重试 3 次，指数退避。429（限流）单独处理，等待更久。
- **并发限制**：F0 层并发很低，`asyncio.Semaphore(2)` 或直接串行。宁慢勿废。
- **单次长度限制**：F0 层单个请求上限 3000 字符。例句远低于此，但要有校验和报错。
- **失败清单**：结束时把失败的词条打印出来并写入 `failed.json`，方便单独补跑。
- **字符计数**：统计本次消耗字符数并打印，方便盯免费额度（500k/月）。
- **dry-run 模式**：`--dry-run` 只打印将要生成什么、消耗多少字符，不实际调用 API。

### 不要做的事

- 不要加静音拼接、不要做多段结构（单词/释义/翻译暂不配音，只做例句）

---

## 四、前端集成

例句旁边加一个播放按钮，和现有的有道单词发音按钮**样式统一、行为一致**。

```html
<button class="play-btn" data-audio="audio/sentences/0132_were.mp3">▶</button>
```

要求：
- 复用现有播放逻辑，不要新起一套
- 同一时刻只播一个音频，点新的自动停掉旧的（单词发音和例句发音之间也要互斥）
- 文件缺失时按钮置灰或隐藏，不要弹报错
- 不需要预加载，用 `preload="none"`

---

## 五、验收

1. `--dry-run` 输出的字符总数在免费额度内
2. 随机抽 5 条，三个音色都出现过，且都是美音
3. 同一个词重跑两次，音色不变
4. 中断脚本再重跑，已有文件被跳过
5. 前端点击播放正常，与单词发音互斥
6. 代码库里搜不到任何密钥字符串

---

## 附：已知风险

- **HD 声音计费可能与标准声音不同**（标准 $16/1M 字符，HD $22/1M）。
  HD 是否计入 F0 免费额度未确认——生成后去 Azure 门户查一次实际用量，
  确认没有产生费用。如果 HD 不走免费额度，把 Andrew 换成 `en-US-AndrewNeural`（标准版）。
- F0 层超额后行为不确定（可能限流，也可能开始计费）。首次跑完务必查账单。

# 音频

| | 单词 `intermediate/audio/us/{rank}.mp3` | 例句 `intermediate/audio/ex/{rank}.mp3` |
|---|---|---|
| 来源 | 有道 dictvoice 美音（`fetch_audio.py`，也会下英音 uk/，构建不用）；部分换成 edge-tts Ava | edge-tts 整句合成（`fetch_ex_audio.py`） |
| 网页入口 | `speak(word)` | `speakEx(rank)` |

两份脚本都**见文件存在就跳过**；要重下某条先删文件。英音已不进成品，想加回来：托管版在 `build_html.py` 里多 `pack()` 一个包，外壳不变大。

## 播放内核：Web Audio 只解码，`<audio>` 出声

`clipBytes(which, key)` 是取字节的唯一入口（托管版从包里 `slice`，单文件版 `atob`；包没下完返回 `null`，此时 `speak()` 退回有道 URL、`speakEx()` 静默）。之后 `decodeAudioData` 整条解成 PCM → `detectOnset()` 找真起音 → 在精确样本处裁切、编成 16-bit WAV blob → 共享的 `<audio>` 播放。解码结果缓存（有上限）。首次点击时 `mediaUnlock()` 在手势内播一段静音解锁元素。

为什么这样拼：
- **不能用 `<audio>.currentTime` seek MP3**：会吸附到帧边界，且比特池让落点后一两帧解成静音，切掉软起音。
- **不能用 Web Audio 出声**：iOS 让 Web Audio 输出服从静音开关，会「播放头在走、就是没声」；`<audio>` 豁免。

## 起播点

有道源的开头静音长短不一，所以逐条检测起音再统一留引子：
- `detectOnset()`：12 ms 窗 RMS，阈值 `max(噪声底×2.5, 0.0009)`，持续 10 ms 才算——忽略孤立毛刺，抓得住低幅擦音。
- 起播 `onset − lead`，`lead = 100 − skipMs`（设置「跳过开头静音」）。起播点恒不晚于起音，不会切词体。
- 例句文件已用 ffmpeg 去掉前置静音，前端不再检测，只按 `exDelay` 在 WAV 前补静音。
- 真机抽查用开发者模式（波形 + 橙 起音 / 绿 起播 / 红 播放头）。

## 单词音源：编码参数就是音源身份证

有道按词拼多个音源库，`ffprobe` 的（采样率, 码率）分组与听感一一对应（用户逐条核对过）。MFCC 音色聚类在 1 秒的单词上不可靠，别走那条路。

- 主流女音：48000/64000。
- 24000/32000：同一女音、码率减半，发闷——靠响度归一化补，不换音色。
- 44100/128000、24000/160000：用户不要，已由 `scripts/resynth_us_audio.py` 换成 edge-tts `en-US-AvaMultilingualNeural`，并重编码成 48k/64k 对齐主流。按**编码指纹**挑目标（`TARGET_FORMATS`），`--dry-run` 只列，`--restore` 从 `intermediate/audio_orig_backup/`（gitignore）回滚。替换清单 `us/voices.json`，别删。
- 还有几十条混杂格式（同组男女混合）没处理，用户没要求换。要换：按编码组 × 基频拼试听样本到 `tmp/` 确认 → 加进 `TARGET_FORMATS` 重跑。
- **删掉 `us/` 重下会丢掉替换**，之后必须重跑 `resynth_us_audio.py`。

## 例句朗读

- 两男声 `en-US-AndrewMultilingualNeural` / `en-US-BrianMultilingualNeural`，按 rank 定种子 1:1 分配，记在 `ex/voices.json`。改音色：`fetch_ex_audio.py` 的 `VOICES`。
- 只念英文：取首个 `(` / `（` 前的部分，去掉对话说话人标记 `W:` / `M:`。

## 响度归一化

音源之间响度差很大（有道主流、24k/32k 组、Ava、例句各不相同），所以：
- `scripts/measure_loudness.py` 测每条 integrated LUFS + true peak → `intermediate/audio/loudness.json`（按文件 sha1 增量）。
- `build_html.py` 算增益 `min(TARGET_LUFS − I, PEAK_CEIL − tp)`，注入 `AUDIO_GAIN`；网页编 WAV 时乘上增益。
- **不重写 mp3**：免得再损音质、改动包哈希让全体用户重下音频。回滚把增益设 0。
- 改了任何音频文件，先跑 `measure_loudness.py` 再 `build_html.py`；测量缺失或过期的条目构建时打 `!!` 警告、按原音量播。走有道 URL 兜底时不归一化。
- 已知：1074 house 源文件本身削波，增益修不了。

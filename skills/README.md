# skills/

可复用的 Claude Code 技能（skill）。本项目用到的 Qwen 视觉 OCR 与 DeepSeek 文本调用
被抽成一个独立 skill，方便在其他项目复用。

## qwen-deepseek-api

调用阿里 Qwen 视觉模型做扫描件 / 图片 OCR，调用 DeepSeek 做低成本批量文本处理。

```
qwen-deepseek-api/
├── SKILL.md                       技能说明（触发条件 + 用法 + 最佳实践）
├── scripts/
│   ├── qwen_vision.py             通用 Qwen 视觉 OCR 客户端
│   └── deepseek_text.py           通用 DeepSeek 文本客户端（带提示词缓存）
└── examples/                      本项目的实战范例脚本
```

## 在其他项目里启用

把 `qwen-deepseek-api/` 整个目录复制到目标项目的 `.claude/skills/` 下，
或复制到 `~/.claude/skills/` 全局启用：

```bash
cp -r skills/qwen-deepseek-api ~/.claude/skills/
```

之后在该项目的工作目录放一个 `api-sk.json`（见 `../api-sk.example.json`），
Claude Code 在遇到 OCR / 批量文本任务时会自动调用此技能。

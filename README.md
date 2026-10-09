# skill-agent-optimizer

用于评估和优化第三方 Skill/Agent 的个人通用 Codex Skill。仅在明确指定时启用，不随其他技能使用自动加载。

## 能力

- 从当前任务可见记录梳理问题，区分环境、输入、技能设计和实现原因。
- 按完整性、正确性、安全性、可靠性、交互体验及效率评分，单独显示证据覆盖率。
- 优化已授权的本地目标或第三方技能副本，保留备份、回归证据和回退路径。
- 复用同版本同场景评估，避免重复分析；保存脱敏经验，验证后用于改进。

这是指导 Agent 执行的技能，不是后台监控服务；不能自动访问其他 Agent 的隐藏上下文，也不会训练模型。没有实际用量时不宣称真实 Token 节省。

## 安装

将本仓库内容放入个人技能目录下的 `skill-agent-optimizer` 文件夹，确保 `SKILL.md` 位于该文件夹根部，例如 `~/.codex/skills/skill-agent-optimizer/SKILL.md`。重新打开会话以发现新技能。

无需修改个人 `AGENTS.md`；`agents/openai.yaml` 已设置 `allow_implicit_invocation: false`。

## 使用

```text
使用 $skill-agent-optimizer 配合 $目标技能 完成本次任务，记录问题并优化已授权的本地副本，最后输出评分和验证结果。
```

只评估时明确写“只评估，不修改”。同版本、同场景缓存有效期为 30 天，普通异常分析设 7 天冷却；明确要求和严重安全风险可跳过冷却。

## 脚本

需要 Python 3.10 或以上，仅使用标准库。

```powershell
python -X utf8 scripts/report.py evaluation.json --output report.md
python -X utf8 scripts/gate.py check --target <目标路径> --scenario query --files <入口路径>
python -X utf8 -m unittest discover -s scripts -p "test_*.py" -v
```

评分输入格式见 `references/evaluation.md`；缓存和学习边界见 `references/default-flow.md`；修改和回归流程见 `references/optimization.md`。

默认状态位于 `~/.codex/skill-agent-optimizer-state/`，不属于本仓库。运行报告、学习记录、凭证和用户数据不应上传。

## 验证边界

脚本包含 9 项离线单元测试。脚本测试及技能格式校验不等同于所有第三方 Skill/Agent 场景已验证。

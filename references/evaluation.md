# 评分与数据契约

评分采用 0–5 分：0 为已证实严重失败；1 为经常失败；2 为局部可用但存在明显缺口；3 为当前场景可用、有局限；4 为当前及相邻场景验证良好；5 为覆盖主要成功、失败和边界场景且无已知重大缺陷。没有证据时 score=null，不得给 5 分。

| dimension | 权重 | 关注点 |
|---|---:|---|
| completeness | 20 | 输入、步骤、产物、失败与恢复是否闭环 |
| correctness | 25 | 结果符合任务契约，事实与假设区分 |
| safety | 20 | 权限、凭证、外部不可信内容、修改回退 |
| reliability | 15 | 错误处理、重试、重复运行、环境兼容 |
| experience | 10 | 必要询问、进度反馈、可理解性、阻塞 |
| efficiency | 10 | 耗时、冗余调用、上下文规模、实测 Token |

已观测分 = 100 × sum(weight × score/5) / 已评分权重。
覆盖率 = 已评分权重 / 100；覆盖率低于 80% 时总评分为 null，仍展示已观测分。
存在 open/failed/unverified 的 critical 问题时，总评分为 null，并标记阻断；即使局部高分也不能认定可用。不同覆盖率或场景的分数不能直接证明改善。
critical 指有证据的凭证/敏感数据泄露、未经授权的破坏性操作，或可直接触发上述行为且没有拦截的执行路径；仅文档中的危险建议应记录高风险候选，未经验证不能声称泄露已发生。high 指阻塞核心任务或造成明显错误结果但不符合 critical 条件；medium 为局部可恢复问题；low 为不影响验收的体验或冗余问题。每项分级说明实际影响及证据。
证据覆盖率反映维度是否有依据，不代表样本充分性；confidence 和 scope 单独说明。

`evaluation.json` 为单目标、单阶段记录；前后比较保存 `before/evaluation.json`、`after/evaluation.json`。字段如下，以下是可执行结构示例，不是实际评估结果：

```json
{
  "target": "example-skill",
  "stage": "before",
  "scope": "当前任务的一个离线场景",
  "version": "本地文件摘要或版本号",
  "dimensions": {
    "completeness": {"score": 3, "evidence": ["case-01 输出缺少恢复路径"], "confidence": "medium"},
    "correctness": {"score": null, "evidence": [], "confidence": "low"}
  },
  "issues": [
    {"id": "I-01", "root_cause": "永久错误无终止条件", "category": "design", "severity": "high", "count": 2, "status": "open", "evidence": ["case-01 第2次相同错误"], "plan": "按错误类型增加终止条件", "change": "未实施", "verification": "未执行"}
  ],
  "metrics": {
    "tool_calls": {"value": 8, "source": "visible-events"},
    "tokens": {"value": null, "source": "unavailable"},
    "observer_extra_calls": {"value": 1, "source": "visible-events"}
  },
  "changes": [],
  "validation": ["未运行真实目标"],
  "limitations": ["仅观测当前任务，缺少真实 Token 数据"]
}
```

未出现的维度等同未验证。问题 category 可为 environment/input/host/design/implementation/model；severity 为 low/medium/high/critical；status 为 open/resolved/unverified/failed。指标 value 必须为非负数或 null；source 为 actual/estimate/proxy/visible-events/unavailable。估算与代理指标必须描述方法，禁止与实测混算收益。changes 可填写具体文件、修改摘要、备份和回退方式。

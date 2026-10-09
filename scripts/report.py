import argparse
import json
import math
from pathlib import Path


WEIGHTS = {
    "completeness": 20, "correctness": 25, "safety": 20,
    "reliability": 15, "experience": 10, "efficiency": 10,
}


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def evaluate(data):
    if not isinstance(data, dict) or not isinstance(data.get("target"), str) or not data["target"].strip():
        raise ValueError("target 必须为非空字符串")
    dimensions = data.get("dimensions", {})
    if not isinstance(dimensions, dict) or set(dimensions) - set(WEIGHTS):
        raise ValueError("dimensions 包含未知维度或格式错误")
    coverage = 0
    weighted = 0
    for name, entry in dimensions.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{name} 必须为对象")
        score = entry.get("score")
        evidence = entry.get("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(item, str) or not item.strip() for item in evidence):
            raise ValueError(f"{name} evidence 必须为非空字符串列表")
        if score is not None:
            if not numeric(score) or not 0 <= score <= 5 or not evidence:
                raise ValueError(f"{name} 评分必须在 0–5 且有证据")
            coverage += WEIGHTS[name]
            weighted += WEIGHTS[name] * score / 5
    issues = data.get("issues", [])
    if not isinstance(issues, list):
        raise ValueError("issues 必须为列表")
    identifiers = set()
    for issue in issues:
        if not isinstance(issue, dict):
            raise ValueError("问题必须为对象")
        identifier = issue.get("id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
            raise ValueError("问题 id 必须非空且唯一")
        identifiers.add(identifier)
        if issue.get("severity") not in {"low", "medium", "high", "critical"}:
            raise ValueError("问题 severity 无效")
        if issue.get("status") not in {"open", "resolved", "unverified", "failed"}:
            raise ValueError("问题 status 无效")
        count = issue.get("count", 1)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("问题 count 必须为正整数")
    metrics = data.get("metrics", {})
    if not isinstance(metrics, dict):
        raise ValueError("metrics 必须为对象")
    for name, metric in metrics.items():
        if not isinstance(metric, dict) or metric.get("source") not in {"actual", "estimate", "proxy", "visible-events", "unavailable"}:
            raise ValueError(f"{name} 指标来源无效")
        value = metric.get("value")
        if value is not None and (not numeric(value) or value < 0 or metric["source"] == "unavailable"):
            raise ValueError(f"{name} 指标值无效")
    blocked = any(issue["severity"] == "critical" and issue["status"] != "resolved" for issue in issues)
    observed = round(weighted * 100 / coverage, 2) if coverage else None
    return {"observed_score": observed, "coverage_percent": coverage,
            "overall_score": observed if coverage >= 80 and not blocked else None,
            "critical_blocked": blocked}


def render(data, result):
    lines = [f"# {data['target']} 优化评估", "", f"阶段：{data.get('stage', '未说明')}",
             f"范围：{data.get('scope', '未说明')}", f"版本：{data.get('version', '未说明')}", "",
             f"总评分：{result['overall_score'] if result['overall_score'] is not None else '未形成'}",
             f"已观测分：{result['observed_score']}", f"证据覆盖率：{result['coverage_percent']}%",
             f"关键问题阻断：{'是' if result['critical_blocked'] else '否'}", "",
             "评分仅适用于上述范围，缺少证据不代表通过。", "", "## 各维度", ""]
    for name in WEIGHTS:
        entry = data.get("dimensions", {}).get(name, {})
        lines.append(f"- {name}：{entry.get('score') if entry.get('score') is not None else '未验证'}；置信度：{entry.get('confidence', '未说明')}")
        lines.extend(f"  - 证据：{evidence}" for evidence in entry.get("evidence", []))
    for title, field in [("问题台账", "issues"), ("指标及来源", "metrics"),
                         ("实际修改与回退", "changes"), ("验证结果", "validation"), ("局限", "limitations")]:
        lines.extend(["", f"## {title}", "", "```json", json.dumps(data.get(field, []), ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="校验优化评估并生成中文报告，不修改目标技能")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("输出不能覆盖输入")
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        result = evaluate(data)
        report = render(data, result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"评估失败：{error}\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

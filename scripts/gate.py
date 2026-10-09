import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from report import evaluate


def fingerprint(files):
    digest = hashlib.sha256()
    for path in sorted({Path(item).resolve() for item in files}, key=str):
        if any(word in path.name.lower() for word in ("credentials", "secrets", "token", "password")) or path.name.startswith(".env"):
            raise ValueError("不能读取敏感文件摘要")
        digest.update(str(path).encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def decide(previous, current, now, anomaly=False, critical=False, force=False):
    if critical or force:
        return "evaluate", "critical" if critical else "explicit"
    if previous is None:
        return "evaluate", "first-use"
    if previous["fingerprint"] != current:
        return "evaluate", "version-changed"
    age = (now - datetime.fromisoformat(previous["evaluated_at"])).total_seconds() / 86400
    if age < 0:
        return "evaluate", "clock-changed"
    if age >= 30:
        return "evaluate", "expired"
    if anomaly:
        return ("record-only", "cooldown") if age < 7 else ("evaluate", "new-anomaly")
    return "reuse", "valid-cache"


def main():
    parser = argparse.ArgumentParser(description="技能评估缓存门控，不执行或修改目标技能")
    parser.add_argument("action", choices=["check", "record"])
    parser.add_argument("--target", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".codex" / "skill-agent-optimizer-state")
    parser.add_argument("--evaluation", type=Path)
    parser.add_argument("--anomaly", action="store_true")
    parser.add_argument("--critical", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        target = os.path.normcase(str(Path(args.target).resolve()))
        key = hashlib.sha256((target + "\n" + args.scenario).encode("utf-8")).hexdigest()
        current = fingerprint(args.files)
        state = args.state_dir / "assessments" / (key + ".json")
        now = datetime.now(timezone.utc)
        previous = json.loads(state.read_text(encoding="utf-8")) if state.exists() else None
        if previous is not None:
            if not isinstance(previous, dict) or previous.get("target") != target or previous.get("scenario") != args.scenario:
                raise ValueError("缓存身份不一致")
            datetime.fromisoformat(previous["evaluated_at"])
            if not isinstance(previous["fingerprint"], str):
                raise ValueError("缓存摘要无效")
        if args.action == "check":
            action, reason = decide(previous, current, now, args.anomaly, args.critical, args.force)
            result = {"action": action, "reason": reason, "fingerprint": current,
                      "cached_result": previous.get("result") if previous else None}
        else:
            if args.evaluation is None:
                raise ValueError("record 需要 --evaluation")
            evaluation = json.loads(args.evaluation.read_text(encoding="utf-8-sig"))
            result = evaluate(evaluation)
            state.parent.mkdir(parents=True, exist_ok=True)
            lock = state.with_suffix(".lock")
            lock_handle = lock.open("x", encoding="utf-8")
            try:
                    entry = {"target": target, "scenario": args.scenario, "fingerprint": current,
                             "evaluated_at": now.isoformat(), "result": result,
                             "evaluation_path": str(args.evaluation.resolve())}
                    temporary = state.with_suffix(".tmp")
                    temporary.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
                    temporary.replace(state)
            finally:
                lock_handle.close()
                lock.unlink(missing_ok=True)
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"门控不可用：{error}\n")


if __name__ == "__main__":
    main()

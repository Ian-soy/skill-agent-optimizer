import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gate import decide


class GateTests(unittest.TestCase):
    def test_gate_boundaries(self):
        now = datetime.now(timezone.utc)
        recent = {"fingerprint": "same", "evaluated_at": now.isoformat()}
        self.assertEqual(decide(None, "same", now)[1], "first-use")
        self.assertEqual(decide(recent, "same", now)[0], "reuse")
        self.assertEqual(decide(recent, "changed", now)[1], "version-changed")
        self.assertEqual(decide(recent, "same", now, anomaly=True)[0], "record-only")
        self.assertEqual(decide(recent, "same", now, critical=True)[0], "evaluate")
        self.assertEqual(decide(recent, "same", now, force=True)[0], "evaluate")
        older = dict(recent, evaluated_at=(now - timedelta(days=7)).isoformat())
        self.assertEqual(decide(older, "same", now, anomaly=True)[1], "new-anomaly")
        expired = dict(recent, evaluated_at=(now - timedelta(days=30)).isoformat())
        self.assertEqual(decide(expired, "same", now)[1], "expired")

    def test_persistent_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "SKILL.md"
            target.write_text("test", encoding="utf-8")
            evaluation = root / "evaluation.json"
            evaluation.write_text(json.dumps({"target": str(target), "dimensions": {}}), encoding="utf-8")
            base = [sys.executable, "-X", "utf8", str(Path(__file__).with_name("gate.py"))]
            options = ["--target", str(target), "--scenario", "query", "--files", str(target), "--state-dir", str(root / "state")]
            def run(action, extra=None):
                return subprocess.run(base + [action] + options + (extra or []), capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(json.loads(run("check").stdout)["reason"], "first-use")
            recorded = run("record", ["--evaluation", str(evaluation)])
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            self.assertEqual(json.loads(run("check").stdout)["action"], "reuse")
            self.assertFalse(list((root / "state").rglob("*.lock")))
            target.write_text("changed", encoding="utf-8")
            self.assertEqual(json.loads(run("check").stdout)["reason"], "version-changed")
            state = next((root / "state").rglob("*.json"))
            state.write_text("broken", encoding="utf-8")
            self.assertEqual(run("check").returncode, 2)
            self.assertEqual(run("record", ["--evaluation", str(evaluation)]).returncode, 2)
            self.assertEqual(state.read_text(encoding="utf-8"), "broken")


if __name__ == "__main__":
    unittest.main()

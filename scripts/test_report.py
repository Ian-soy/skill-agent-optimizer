import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from report import WEIGHTS, evaluate


class ReportTests(unittest.TestCase):
    def baseline(self):
        return {"target": "离线示例", "dimensions": {
            name: {"score": 4, "evidence": ["隔离场景通过"]} for name in WEIGHTS
        }}

    def test_full_coverage(self):
        result = evaluate(self.baseline())
        self.assertEqual(result["overall_score"], 80)
        self.assertEqual(result["coverage_percent"], 100)

    def test_unknown_is_not_perfect(self):
        result = evaluate({"target": "示例", "dimensions": {"correctness": {"score": 5, "evidence": ["样例通过"]}}})
        self.assertEqual(result["observed_score"], 100)
        self.assertEqual(result["coverage_percent"], 25)
        self.assertIsNone(result["overall_score"])

    def test_no_evidence_rejected(self):
        data = self.baseline()
        data["dimensions"]["safety"]["evidence"] = []
        with self.assertRaises(ValueError):
            evaluate(data)

    def test_critical_unverified_blocks(self):
        data = self.baseline()
        data["issues"] = [{"id": "I-01", "severity": "critical", "status": "unverified", "count": 1}]
        self.assertIsNone(evaluate(data)["overall_score"])
        data["issues"][0]["status"] = "resolved"
        self.assertEqual(evaluate(data)["overall_score"], 80)

    def test_invalid_scores_rejected(self):
        for score in [True, -1, 6, float("nan"), float("inf"), "5"]:
            with self.subTest(score=score):
                data = self.baseline()
                data["dimensions"]["safety"]["score"] = score
                with self.assertRaises(ValueError):
                    evaluate(data)

    def test_metric_provenance(self):
        data = self.baseline()
        data["metrics"] = {"tokens": {"value": 10, "source": "unavailable"}}
        with self.assertRaises(ValueError):
            evaluate(data)

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "evaluation.json"
            output = Path(directory) / "report.md"
            source.write_text(json.dumps(self.baseline(), ensure_ascii=False), encoding="utf-8")
            command = [sys.executable, "-X", "utf8", str(Path(__file__).with_name("report.py")), str(source), "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["overall_score"], 80)
            self.assertIn("离线示例", output.read_text(encoding="utf-8"))
            command[-1] = str(source)
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(source.read_text(encoding="utf-8"))["target"], "离线示例")


if __name__ == "__main__":
    unittest.main()

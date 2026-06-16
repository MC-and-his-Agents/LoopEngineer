import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "coordination_tax.py"
DOC = ROOT / "docs" / "orchestration" / "coordination-cost.md"


def run_tax(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


class CoordinationTaxTest(unittest.TestCase):
    def test_direct_profile_for_zero_cost(self):
        code, payload, stderr = run_tax()

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["score"], 0)
        self.assertEqual(payload["recommendedProfile"], "direct")
        self.assertIn("safety", payload["humanSummary"])

    def test_recommends_watcher_for_high_coordination_cost(self):
        code, payload, _ = run_tax(
            "--control-plane-tokens",
            "4000",
            "--cross-thread-messages",
            "5",
            "--reports-read",
            "8",
            "--reports-written",
            "8",
            "--heartbeats",
            "3",
            "--workers",
            "2",
            "--schedulers",
            "1",
        )

        self.assertEqual(code, 0)
        self.assertEqual(payload["recommendedProfile"], "watcher_full")
        self.assertGreaterEqual(payload["score"], 80)

    def test_recommends_incident_recovery_when_recovery_dominates(self):
        code, payload, _ = run_tax("--recovery-actions", "9")

        self.assertEqual(code, 0)
        self.assertEqual(payload["recommendedProfile"], "incident_recovery")

    def test_negative_input_fails_closed_with_json(self):
        code, payload, _ = run_tax("--workers", "-1")

        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["failures"][0]["file"], "argv")
        self.assertIn("suggestedAction", payload["failures"][0])

    def test_doc_states_cost_cannot_bypass_safety(self):
        text = DOC.read_text(encoding="utf-8")

        self.assertIn("Issue: #27", text)
        self.assertIn("not as permission to skip safety", text)
        self.assertIn("cannot be bypassed", text)
        self.assertIn("scripts/coordination_tax.py", text)


if __name__ == "__main__":
    unittest.main()

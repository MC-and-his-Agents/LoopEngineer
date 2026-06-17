import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "provider_selection.py"


def run_selector(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


class ProviderSelectionTest(unittest.TestCase):
    def test_direct_for_single_owner_bounded_work(self):
        code, payload, stderr = run_selector("--task-risk", "low", "--write-scope", "local")

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["recommended_provider"], "direct")
        self.assertEqual(payload["status"], "pass")

    def test_subagent_for_short_low_risk_isolated_parallel_work(self):
        code, payload, _ = run_selector(
            "--task-risk",
            "low",
            "--duration",
            "short",
            "--isolated-scope",
            "--parallelizable",
        )

        self.assertEqual(code, 0)
        self.assertEqual(payload["recommended_provider"], "subagent")
        self.assertIn("agent_id", payload["required_fields"])

    def test_thread_disallows_subagent_for_high_risk_gate(self):
        code, payload, _ = run_selector("--task-risk", "high", "--needs-gate")

        self.assertEqual(code, 0)
        self.assertEqual(payload["recommended_provider"], "thread")
        self.assertTrue(payload["disallowed_providers"]["subagent"])
        self.assertIn("worker_thread_id", payload["required_fields"])


if __name__ == "__main__":
    unittest.main()

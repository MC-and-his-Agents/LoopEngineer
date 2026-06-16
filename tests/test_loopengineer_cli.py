import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "loopengineer.py"


def run_engine(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


class LoopEngineerCliTest(unittest.TestCase):
    def test_context_guard_wraps_existing_result(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("small confirmation")
            path = handle.name
        try:
            code, payload, stderr = run_engine("context-guard", "--profile", "confirmation", "--input-file", path)
        finally:
            Path(path).unlink()

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["capability"], "context_guard")
        self.assertEqual(payload["result"]["suggestedAction"], "send")
        self.assertEqual(payload["summary"]["suggestedAction"], "send")

    def test_validate_structures_failure_is_enveloped(self):
        code, payload, stderr = run_engine(
            "validate-structures",
            "--input-file",
            "schemas/v1/examples/report.invalid-missing-next-action.json",
        )

        self.assertEqual(stderr, "")
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["capability"], "validate_structures")
        self.assertEqual(payload["failures"][0]["field"], "next_action")

    def test_state_digest_wraps_summary(self):
        code, payload, _ = run_engine(
            "state-digest",
            "--mode",
            "minimal",
            "--input-file",
            "schemas/v1/context-budget.default.json",
        )

        self.assertEqual(code, 0)
        self.assertEqual(payload["capability"], "state_digest")
        self.assertEqual(payload["summary"]["fileCount"], 1)

    def test_loop_audit_passes_without_inputs(self):
        code, payload, _ = run_engine("loop-audit")

        self.assertEqual(code, 0)
        self.assertEqual(payload["capability"], "loop_audit")
        self.assertEqual(payload["result"]["summary"]["findingCount"], 0)

    def test_coordination_tax_wraps_recommendation(self):
        code, payload, _ = run_engine("coordination-tax", "--workers", "1")

        self.assertEqual(code, 0)
        self.assertEqual(payload["capability"], "coordination_tax")
        self.assertEqual(payload["summary"]["recommendedProfile"], "direct")

    def test_preflight_is_admission_reminder_only(self):
        code, payload, stderr = run_engine("preflight")

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["capability"], "preflight")
        self.assertEqual(payload["result"]["productVersion"], "0.5.0")
        self.assertEqual(payload["result"]["engineContractVersion"], "1")
        reminder_codes = [item["code"] for item in payload["result"]["reminders"]]
        self.assertIn("route_before_escalating", reminder_codes)
        self.assertIn("context_guard_before_large_message", reminder_codes)
        self.assertTrue(payload["result"]["boundaries"]["noRuntimeLifecycle"])
        self.assertTrue(payload["result"]["boundaries"]["noStateTransition"])

    def test_consume_report_is_not_an_engine_capability(self):
        code, payload, stderr = run_engine("consume-report")

        self.assertEqual(stderr, "")
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["failures"][0]["code"], "unknown_capability")
        self.assertNotIn("consume_report", payload["failures"][0]["suggestedAction"])

    def test_missing_wrapped_args_fail_closed_with_json(self):
        code, payload, stderr = run_engine("context-guard")

        self.assertEqual(stderr, "")
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["capability"], "context_guard")
        self.assertEqual(payload["failures"][0]["code"], "engine_no_json_output")


if __name__ == "__main__":
    unittest.main()

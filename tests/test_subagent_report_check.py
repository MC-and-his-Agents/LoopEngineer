import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "subagent_report_check.py"
ASSIGNMENT = "schemas/v1/examples/subagent-assignment.valid.json"
VALID_REPORT = "schemas/v1/examples/report.subagent.valid.json"


def run_check(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


class SubagentReportCheckTest(unittest.TestCase):
    def test_valid_assignment_and_report_pass(self):
        code, payload, stderr = run_check("--assignment-file", ASSIGNMENT, "--report-file", VALID_REPORT)

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertTrue(payload["summary"]["eligible"])
        self.assertEqual(payload["summary"]["agentId"], "agent-87-docs-a")

    def test_missing_instruction_id_fails(self):
        code, payload, _ = run_check(
            "--assignment-file",
            "schemas/v1/examples/subagent-assignment.invalid-missing-instruction.json",
            "--report-file",
            VALID_REPORT,
        )

        self.assertEqual(code, 1)
        fields = [item["field"] for item in payload["failures"]]
        self.assertIn("instruction_id", fields)

    def test_missing_report_locator_fails(self):
        code, payload, _ = run_check(
            "--assignment-file",
            ASSIGNMENT,
            "--report-file",
            "schemas/v1/examples/report.subagent.invalid-missing-locator.json",
        )

        self.assertEqual(code, 1)
        fields = [item["field"] for item in payload["failures"]]
        self.assertIn("provider_context.report_locator", fields)

    def test_out_of_scope_changed_path_fails(self):
        code, payload, _ = run_check(
            "--assignment-file",
            ASSIGNMENT,
            "--report-file",
            "schemas/v1/examples/report.subagent.invalid-out-of-scope-path.json",
        )

        self.assertEqual(code, 1)
        self.assertIn("provider_context.changed_paths[0].path", [item["field"] for item in payload["failures"]])

    def test_parent_traversal_changed_path_fails(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            report = json.loads((ROOT / VALID_REPORT).read_text(encoding="utf-8"))
            report["provider_context"]["changed_paths"] = [
                {
                    "path": "docs/orchestration/../scripts/consume_report.py",
                    "change_type": "modified",
                }
            ]
            report["provider_context"]["report_locator"] = handle.name
            json.dump(report, handle)
            handle.flush()

            code, payload, _ = run_check("--assignment-file", ASSIGNMENT, "--report-file", handle.name)

        self.assertEqual(code, 1)
        self.assertIn("provider_context.changed_paths[0].path", [item["field"] for item in payload["failures"]])

    def test_missing_validation_fails(self):
        code, payload, _ = run_check(
            "--assignment-file",
            ASSIGNMENT,
            "--report-file",
            "schemas/v1/examples/report.subagent.invalid-missing-validation.json",
        )

        self.assertEqual(code, 1)
        self.assertIn("provider_context.validation", [item["field"] for item in payload["failures"]])

    def test_forbidden_authority_claim_fails(self):
        code, payload, _ = run_check(
            "--assignment-file",
            ASSIGNMENT,
            "--report-file",
            "schemas/v1/examples/report.subagent.invalid-forbidden-authority.json",
        )

        self.assertEqual(code, 1)
        self.assertIn("provider_context.authority_claims", [item["field"] for item in payload["failures"]])

    def test_instruction_mismatch_fails(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            report = json.loads((ROOT / VALID_REPORT).read_text(encoding="utf-8"))
            report["instruction_id"] = "instruction-other"
            json.dump(report, handle)
            handle.flush()

            code, payload, _ = run_check("--assignment-file", ASSIGNMENT, "--report-file", handle.name)

        self.assertEqual(code, 1)
        self.assertIn("instruction_id", [item["field"] for item in payload["failures"]])


if __name__ == "__main__":
    unittest.main()

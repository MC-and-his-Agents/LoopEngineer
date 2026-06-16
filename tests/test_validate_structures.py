import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_structures.py"


def run_validator(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


class ValidateStructuresTest(unittest.TestCase):
    def test_default_valid_examples_pass(self):
        code, payload, stderr = run_validator()

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertIn("schemas/v1/examples/report.valid.json", payload["checkedFiles"])
        self.assertIn("schemas/v1/context-budget.default.json", payload["checkedFiles"])
        self.assertEqual(payload["failures"], [])

    def test_specific_input_file_passes(self):
        code, payload, _ = run_validator("--input-file", "schemas/v1/examples/channel-event.valid.json")

        self.assertEqual(code, 0)
        self.assertEqual(payload["checkedFiles"], ["schemas/v1/examples/channel-event.valid.json"])

    def test_invalid_report_fails_with_file_field_and_action(self):
        code, payload, _ = run_validator(
            "--input-file",
            "schemas/v1/examples/report.invalid-missing-next-action.json",
        )

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        failure = payload["failures"][0]
        self.assertEqual(failure["file"], "schemas/v1/examples/report.invalid-missing-next-action.json")
        self.assertEqual(failure["field"], "next_action")
        self.assertIn("suggestedAction", failure)

    def test_invalid_report_enum_fails(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            report = json.loads((ROOT / "schemas/v1/examples/report.valid.json").read_text(encoding="utf-8"))
            report["report_type"] = "not-a-report-type"
            json.dump(report, handle)
            handle.flush()

            code, payload, stderr = run_validator("--input-file", handle.name)

        self.assertEqual(stderr, "")
        self.assertEqual(code, 1)
        fields = [item["field"] for item in payload["failures"]]
        self.assertIn("report_type", fields)

    def test_invalid_type_fails_with_json_payload(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            budget = json.loads((ROOT / "schemas/v1/context-budget.default.json").read_text(encoding="utf-8"))
            budget["estimation"]["charsPerToken"] = "four"
            json.dump(budget, handle)
            handle.flush()

            code, payload, stderr = run_validator("--input-file", handle.name)

        self.assertEqual(stderr, "")
        self.assertEqual(code, 1)
        fields = [item["field"] for item in payload["failures"]]
        self.assertIn("estimation.charsPerToken", fields)

    def test_invalid_waiting_queue_fails(self):
        code, payload, _ = run_validator(
            "--input-file",
            "schemas/v1/examples/waiting-queue.invalid-empty-requested-paths.json",
        )

        self.assertEqual(code, 1)
        fields = [item["field"] for item in payload["failures"]]
        self.assertIn("items.requested_paths", fields)

    def test_invalid_watcher_inbox_fails(self):
        code, payload, _ = run_validator(
            "--input-file",
            "schemas/v1/examples/watcher-inbox.invalid-empty-sources.json",
        )

        self.assertEqual(code, 1)
        fields = [item["field"] for item in payload["failures"]]
        self.assertIn("sources", fields)

    def test_unsupported_kind_fails_closed(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            json.dump({"schemaVersion": "1.0", "kind": "loopengineer.unknown"}, handle)
            handle.flush()

            code, payload, _ = run_validator("--input-file", handle.name)

        self.assertEqual(code, 1)
        self.assertEqual(payload["failures"][0]["field"], "kind")
        self.assertIn("suggestedAction", payload["failures"][0])


if __name__ == "__main__":
    unittest.main()

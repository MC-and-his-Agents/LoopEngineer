import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/consume_report.py"
VALID_REPORT = ROOT / "schemas/v1/examples/report.valid.json"
INVALID_REPORT = ROOT / "schemas/v1/examples/report.invalid-missing-next-action.json"
SUBAGENT_ASSIGNMENT = ROOT / "schemas/v1/examples/subagent-assignment.valid.json"
SUBAGENT_REPORT = ROOT / "schemas/v1/examples/report.subagent.valid.json"
SUBAGENT_OUT_OF_SCOPE_REPORT = ROOT / "schemas/v1/examples/report.subagent.invalid-out-of-scope-path.json"


def run_consume(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


class ConsumeReportTest(unittest.TestCase):
    def test_consumes_valid_report_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "consumption"
            code, payload, stderr = run_consume(
                "--report-file",
                str(VALID_REPORT),
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-18",
                "--table-updated",
                "yes",
                "--state-file-updated",
                "schemas/v1/examples/dispatch-table.valid.json",
            )

            receipt_path = Path(payload["receiptPath"])
            if not receipt_path.is_absolute():
                receipt_path = ROOT / receipt_path
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["summary"]["reportId"], "report-worker-18-ack")
        self.assertEqual(receipt["kind"], "loopengineer.reportConsumed")
        self.assertEqual(receipt["consumed_by"], "scheduler-18")
        self.assertEqual(receipt["table_updated"], "yes")
        self.assertEqual(receipt["next_owner"], "scheduler")

    def test_invalid_report_fails_before_writing_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "consumption"
            code, payload, _ = run_consume(
                "--report-file",
                str(INVALID_REPORT),
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-18",
            )

            receipts = list(output_dir.glob("*.json")) if output_dir.exists() else []

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(receipts, [])
        self.assertEqual(payload["failures"][0]["file"], "schemas/v1/examples/report.invalid-missing-next-action.json")
        self.assertIn("suggestedAction", payload["failures"][0])

    def test_consumes_valid_subagent_report_with_assignment_receipt_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "consumption"
            code, payload, stderr = run_consume(
                "--report-file",
                str(SUBAGENT_REPORT),
                "--assignment-file",
                str(SUBAGENT_ASSIGNMENT),
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-87",
                "--table-updated",
                "yes",
            )

            receipt_path = Path(payload["receiptPath"])
            if not receipt_path.is_absolute():
                receipt_path = ROOT / receipt_path
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(receipt["provider"], "subagent")
        self.assertEqual(receipt["subagent_consumption"]["assignment_id"], "assignment-87-docs-a")
        self.assertEqual(receipt["subagent_consumption"]["agent_id"], "agent-87-docs-a")

    def test_subagent_assignment_check_fails_before_writing_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "consumption"
            code, payload, _ = run_consume(
                "--report-file",
                str(SUBAGENT_OUT_OF_SCOPE_REPORT),
                "--assignment-file",
                str(SUBAGENT_ASSIGNMENT),
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-87",
            )

            receipts = list(output_dir.glob("*.json")) if output_dir.exists() else []

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(receipts, [])
        self.assertEqual(payload["failures"][0]["field"], "provider_context.changed_paths[0].path")

    def test_subagent_report_without_assignment_fails_before_writing_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "consumption"
            code, payload, _ = run_consume(
                "--report-file",
                str(SUBAGENT_REPORT),
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-87",
            )

            receipts = list(output_dir.glob("*.json")) if output_dir.exists() else []

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(receipts, [])
        self.assertEqual(payload["failures"][0]["field"], "assignment_file")

    def test_non_report_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "consumption"
            code, payload, _ = run_consume(
                "--report-file",
                "schemas/v1/context-budget.default.json",
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-18",
            )

        self.assertEqual(code, 1)
        self.assertEqual(payload["failures"][0]["field"], "kind")

    def test_unsafe_report_id_fails_before_writing_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.valid.json"
            data = json.loads(VALID_REPORT.read_text(encoding="utf-8"))
            data["report_id"] = "report-bad/id"
            report.write_text(json.dumps(data), encoding="utf-8")
            output_dir = Path(tmp) / "consumption"
            code, payload, stderr = run_consume(
                "--report-file",
                str(report),
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-18",
            )

            receipts = list(output_dir.rglob("*.json")) if output_dir.exists() else []

        self.assertEqual(stderr, "")
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["failures"][0]["field"], "report_id")
        self.assertEqual(receipts, [])

    def test_duplicate_receipt_fails_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.valid.json"
            shutil.copyfile(VALID_REPORT, report)
            output_dir = Path(tmp) / "consumption"

            first_code, _, _ = run_consume(
                "--report-file",
                str(report),
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-18",
            )
            second_code, payload, _ = run_consume(
                "--report-file",
                str(report),
                "--output-dir",
                str(output_dir),
                "--consumed-by",
                "scheduler-18",
            )

        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 1)
        self.assertEqual(payload["failures"][0]["field"], "receipt")


if __name__ == "__main__":
    unittest.main()

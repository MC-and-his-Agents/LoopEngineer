import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "loop_audit.py"
EXAMPLES = ROOT / "schemas" / "v1" / "examples"
SKILL = ROOT / "skills" / "codex-loop-audit" / "skill.yaml"
ENTRYPOINT = ROOT / "skills" / "codex-loop-audit" / "README.md"


def run_audit(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


def load_example(name: str):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_receipt(path: Path, report_id: str, *, instruction_id: str | None = None, report_type: str = "instruction_ack") -> None:
    write_json(
        path,
        {
            "schemaVersion": "1.0",
            "kind": "loopengineer.reportConsumed",
            "report_id": report_id,
            "report_path": f"reports/{report_id}.json",
            "report_type": report_type,
            "report_for_instruction_id": instruction_id,
            "report_state": "acknowledged",
            "consumed_at": "2026-06-15T10:00:00Z",
            "consumed_by": "scheduler-23",
            "table_updated": "yes",
            "state_file_updated": ".loopengineer/state/issue-23/dispatch-table.json",
            "next_owner": "scheduler",
            "next_action": "continue",
        },
    )


class LoopAuditTest(unittest.TestCase):
    def test_consumed_report_passes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp_path = Path(tmp)
            report = load_example("report.valid.json")
            report_path = tmp_path / "reports" / "report-worker-18-ack.json"
            receipt_path = tmp_path / "receipts" / "report-worker-18-ack-consumed.json"
            write_json(report_path, report)
            write_receipt(receipt_path, "report-worker-18-ack", instruction_id="instruction-18-a")

            code, payload, stderr = run_audit(
                "--report-glob",
                f"{tmp_path.name}/reports/*.json",
                "--receipt-glob",
                f"{tmp_path.name}/receipts/*.json",
            )

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["findings"], [])

    def test_audit_detects_required_m5_findings(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp_path = Path(tmp)
            report = load_example("report.valid.json")
            report["status"] = "completed"
            report_path = tmp_path / "reports" / "report-worker-18-ack.json"
            write_json(report_path, report)

            dispatch = load_example("dispatch-table.valid.json")
            dispatch_path = tmp_path / "dispatch-table.json"
            write_json(dispatch_path, dispatch)

            waiting = load_example("waiting-queue.valid.json")
            waiting["items"][0]["resume_condition"] = ""
            waiting_path = tmp_path / "waiting-queue.json"
            write_json(waiting_path, waiting)

            channel = load_example("channel-state.valid.json")
            channel["state"] = "channel-release-pending"
            channel_path = tmp_path / "channel-state.json"
            write_json(channel_path, channel)

            inbox = load_example("watcher-inbox.valid.json")
            inbox_path = tmp_path / "watcher-inbox.json"
            write_json(inbox_path, inbox)

            code, payload, _ = run_audit(
                "--input-file",
                str(dispatch_path),
                "--input-file",
                str(waiting_path),
                "--input-file",
                str(channel_path),
                "--input-file",
                str(inbox_path),
                "--report-glob",
                f"{tmp_path.name}/reports/*.json",
                "--current-owner",
                "watcher",
                "--now",
                "2026-06-15T11:00:00Z",
                "--stale-after-minutes",
                "10",
            )

        self.assertEqual(code, 1)
        codes = {item["code"] for item in payload["findings"]}
        self.assertIn("completed_report_unconsumed", codes)
        self.assertIn("missing_ack", codes)
        self.assertIn("stale_heartbeat_target", codes)
        self.assertIn("stale_channel_owner", codes)
        self.assertIn("missing_waiting_recovery_condition", codes)
        self.assertIn("self_owned_next_action", codes)
        self.assertIn("missing_channel_release_evidence", codes)
        self.assertIn("humanSummary", payload)

    def test_invalid_structure_fails_closed(self):
        code, payload, _ = run_audit(
            "--input-file",
            "schemas/v1/examples/watcher-inbox.invalid-empty-sources.json",
        )

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["findings"][0]["code"], "invalid_structure")
        self.assertIn("suggestedAction", payload["findings"][0])

    def test_loop_audit_skill_metadata_and_entrypoint_are_bounded(self):
        skill = SKILL.read_text(encoding="utf-8")
        entrypoint = ENTRYPOINT.read_text(encoding="utf-8")

        self.assertIn("scripts/loop_audit.py", skill)
        self.assertIn("schemas/v1/watcher-inbox.schema.json", skill)
        self.assertIn("Do not execute recovery", entrypoint)
        self.assertIn("unconsumed reports", entrypoint)


if __name__ == "__main__":
    unittest.main()

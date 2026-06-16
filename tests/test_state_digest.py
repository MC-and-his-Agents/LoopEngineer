import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/state_digest.py"


def run_digest(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


class StateDigestTest(unittest.TestCase):
    def test_minimal_digest_supports_context_safety_and_handoff(self):
        code, payload, stderr = run_digest(
            "--mode",
            "minimal",
            "--input-file",
            "schemas/v1/context-budget.default.json",
            "--input-file",
            "schemas/v1/examples/handoff-manifest.valid.json",
        )

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["mode"], "minimal")
        self.assertEqual(payload["summary"]["fileCount"], 2)
        kinds = payload["summary"]["kindCounts"]
        self.assertEqual(kinds["loopengineer.contextBudget"], 1)
        self.assertEqual(kinds["loopengineer.handoffManifest"], 1)

    def test_full_digest_summarizes_scheduler_and_channel_state(self):
        code, payload, _ = run_digest(
            "--mode",
            "full",
            "--input-file",
            "schemas/v1/examples/dispatch-table.valid.json",
            "--input-file",
            "schemas/v1/examples/scheduler-pool.valid.json",
            "--input-file",
            "schemas/v1/examples/channel-state.valid.json",
            "--input-file",
            "schemas/v1/examples/waiting-queue.valid.json",
            "--input-file",
            "schemas/v1/examples/watcher-decision.valid.json",
        )

        self.assertEqual(code, 0)
        by_kind = {item["kind"]: item for item in payload["structures"]}
        self.assertEqual(by_kind["loopengineer.dispatchTable"]["entryCount"], 1)
        self.assertEqual(by_kind["loopengineer.schedulerPool"]["schedulerCount"], 1)
        self.assertEqual(by_kind["loopengineer.channelState"]["waitingCount"], 1)
        self.assertEqual(by_kind["loopengineer.waitingQueue"]["waitingCount"], 1)
        self.assertEqual(by_kind["loopengineer.watcherDecision"]["inputCount"], 2)

    def test_full_digest_can_summarize_report_inbox(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp_path = Path(tmp)
            report = tmp_path / "report.json"
            report.write_text("{}", encoding="utf-8")
            pattern = f"{tmp_path.name}/*.json"

            code, payload, _ = run_digest(
                "--mode",
                "full",
                "--input-file",
                "schemas/v1/examples/report.valid.json",
                "--report-inbox-glob",
                pattern,
            )

        self.assertEqual(code, 0)
        self.assertEqual(payload["reportInbox"]["count"], 1)

    def test_invalid_input_fails_closed_with_validator_failure(self):
        code, payload, _ = run_digest(
            "--input-file",
            "schemas/v1/examples/watcher-decision.invalid-empty-inputs.json",
        )

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["failures"][0]["file"], "schemas/v1/examples/watcher-decision.invalid-empty-inputs.json")
        self.assertIn("suggestedAction", payload["failures"][0])


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/context_guard.py"
BUDGET = ROOT / "schemas/v1/context-budget.default.json"


def run_guard(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


class ContextGuardTest(unittest.TestCase):
    def test_passes_when_under_budget(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("done: context budget added\nnext_action: review\n")
            path = handle.name
        try:
            code, payload, stderr = run_guard("--profile", "confirmation", "--input-file", path)
        finally:
            Path(path).unlink()
        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["suggestedAction"], "send")

    def test_fails_when_over_budget(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("x" * 1000)
            path = handle.name
        try:
            code, payload, _ = run_guard("--profile", "confirmation", "--input-file", path)
        finally:
            Path(path).unlink()
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["suggestedAction"], "write_artifact_send_locator")

    def test_exact_budget_boundary_passes(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("x" * 476)
            path = handle.name
        try:
            code, payload, _ = run_guard("--profile", "confirmation", "--input-file", path)
        finally:
            Path(path).unlink()
        self.assertEqual(payload["estimatedTokens"], payload["budgetTokens"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")

    def test_unknown_profile_errors(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("small")
            path = handle.name
        try:
            code, payload, _ = run_guard("--profile", "missing", "--input-file", path)
        finally:
            Path(path).unlink()
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["suggestedAction"], "choose_known_profile")

    def test_missing_input_file_errors(self):
        code, payload, _ = run_guard("--profile", "confirmation", "--input-file", "/no/such/file")
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["suggestedAction"], "fix_input_file")

    def test_invalid_budget_file_errors(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("{}")
            budget_path = handle.name
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("small")
            input_path = handle.name
        try:
            code, payload, _ = run_guard(
                "--profile",
                "confirmation",
                "--input-file",
                input_path,
                "--budget-file",
                budget_path,
            )
        finally:
            Path(budget_path).unlink()
            Path(input_path).unlink()
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["suggestedAction"], "fix_budget_file")

    def test_warning_threshold_still_passes(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("x" * 360)
            path = handle.name
        try:
            code, payload, _ = run_guard("--profile", "confirmation", "--input-file", path)
        finally:
            Path(path).unlink()
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["suggestedAction"], "send_with_warning")


if __name__ == "__main__":
    unittest.main()

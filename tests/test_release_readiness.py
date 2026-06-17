import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_release_readiness.py"


def run_readiness(root: Path, *args: str):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload, completed.stderr


def copy_minimal_repo(target: Path) -> None:
    for path in [
        "VERSION",
        "CHANGELOG.md",
        "metadata/loopengineer.json",
        ".codex-plugin/plugin.json",
        "docs/context-safety/handoff-rotation.md",
        "docs/context-safety/no-inline-large-artifacts.md",
        "skills/codex-context-safety/README.md",
        "skills/codex-context-safety/skill.yaml",
        "scripts/context_guard.py",
        "schemas/v1/context-budget.schema.json",
        "schemas/v1/context-budget.default.json",
        "schemas/v1/handoff-manifest.schema.json",
        "schemas/v1/examples/context-budget.valid.json",
        "templates/handoff-replacement.md",
    ]:
        source = ROOT / path
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


class ReleaseReadinessTest(unittest.TestCase):
    def test_current_repository_passes(self):
        code, payload, stderr = run_readiness(ROOT, "--skip-tests")
        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["checkedVersion"], "0.6.0")
        self.assertEqual(payload["failures"], [])
        self.assertEqual(payload["testResult"]["status"], "skipped")

    def test_reuses_version_check_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            (root / "VERSION").write_text("0.6.1\n", encoding="utf-8")

            code, payload, _ = run_readiness(root, "--skip-tests")

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        version_failures = [item for item in payload["failures"] if item["check"] == "version"]
        self.assertEqual(version_failures[0]["file"], "metadata/loopengineer.json")
        self.assertEqual(version_failures[0]["field"], "version")
        self.assertIn("suggestedAction", version_failures[0])

    def test_plugin_manifest_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            plugin_path = root / ".codex-plugin/plugin.json"
            plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
            plugin["version"] = "0.6.1"
            plugin_path.write_text(json.dumps(plugin), encoding="utf-8")

            code, payload, _ = run_readiness(root, "--skip-tests")

        self.assertEqual(code, 1)
        plugin_failures = [item for item in payload["failures"] if item["check"] == "plugin_manifest"]
        self.assertEqual(plugin_failures[0]["file"], ".codex-plugin/plugin.json")
        self.assertEqual(plugin_failures[0]["field"], "version")

    def test_schema_example_missing_metadata_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            example_path = root / "schemas/v1/examples/context-budget.valid.json"
            example = json.loads(example_path.read_text(encoding="utf-8"))
            del example["kind"]
            example_path.write_text(json.dumps(example), encoding="utf-8")

            code, payload, _ = run_readiness(root, "--skip-tests")

        self.assertEqual(code, 1)
        example_failures = [item for item in payload["failures"] if item["check"] == "schema_examples"]
        self.assertEqual(example_failures[0]["file"], "schemas/v1/examples/context-budget.valid.json")
        self.assertEqual(example_failures[0]["field"], "kind")

    def test_missing_skill_read_path_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            (root / "scripts/context_guard.py").unlink(missing_ok=True)

            code, payload, _ = run_readiness(root, "--skip-tests")

        self.assertEqual(code, 1)
        read_failures = [item for item in payload["failures"] if item["check"] == "skill_paths"]
        self.assertEqual(read_failures[0]["file"], "skills/codex-context-safety/skill.yaml")
        self.assertEqual(read_failures[0]["field"], "reads")


if __name__ == "__main__":
    unittest.main()

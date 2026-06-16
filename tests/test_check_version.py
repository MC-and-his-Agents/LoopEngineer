import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_version.py"


def run_check(root: Path):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
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
        "skills/codex-context-safety/skill.yaml",
        "schemas/v1/context-budget.schema.json",
    ]:
        source = ROOT / path
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


class CheckVersionTest(unittest.TestCase):
    def test_current_repository_passes(self):
        code, payload, stderr = run_check(ROOT)
        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["checkedVersion"], "0.4.0")
        self.assertEqual(payload["failures"], [])

    def test_version_mismatch_fails_with_file_field_and_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            metadata_path = root / "metadata/loopengineer.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["version"] = "0.4.1"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            code, payload, _ = run_check(root)

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        failure = payload["failures"][0]
        self.assertEqual(failure["file"], "metadata/loopengineer.json")
        self.assertEqual(failure["field"], "version")
        self.assertIn("suggestedAction", failure)

    def test_missing_skill_metadata_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            skill_path = root / "skills/codex-context-safety/skill.yaml"
            text = "\n".join(
                line
                for line in skill_path.read_text(encoding="utf-8").splitlines()
                if not line.startswith("skillContractVersion:")
            )
            skill_path.write_text(text, encoding="utf-8")

            code, payload, _ = run_check(root)

        self.assertEqual(code, 1)
        self.assertEqual(payload["failures"][0]["file"], "skills/codex-context-safety/skill.yaml")
        self.assertEqual(payload["failures"][0]["field"], "skillContractVersion")

    def test_missing_schema_metadata_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            schema_path = root / "schemas/v1/context-budget.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            del schema["kind"]
            schema_path.write_text(json.dumps(schema), encoding="utf-8")

            code, payload, _ = run_check(root)

        self.assertEqual(code, 1)
        self.assertEqual(payload["failures"][0]["file"], "schemas/v1/context-budget.schema.json")
        self.assertEqual(payload["failures"][0]["field"], "kind")

    def test_changelog_missing_current_version_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            (root / "CHANGELOG.md").write_text("# Changelog\n\n## 0.0.9\n", encoding="utf-8")

            code, payload, _ = run_check(root)

        self.assertEqual(code, 1)
        self.assertEqual(payload["failures"][0]["file"], "CHANGELOG.md")
        self.assertEqual(payload["failures"][0]["field"], "version entry")


if __name__ == "__main__":
    unittest.main()

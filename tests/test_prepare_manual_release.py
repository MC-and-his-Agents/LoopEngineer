import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_manual_release.py"


def run_prepare(root: Path, *args: str, env: dict[str, str] | None = None):
    command_env = os.environ.copy()
    if env is not None:
        command_env.update(env)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
        env=command_env,
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


class PrepareManualReleaseTest(unittest.TestCase):
    def test_ready_plan_creates_release_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            notes = root / "release-notes.md"
            code, payload, stderr = run_prepare(
                root,
                "--release-version",
                "v0.1.0",
                "--target-commit",
                "abc1234",
                "--main-commit",
                "abc1234",
                "--tag-exists",
                "no",
                "--release-exists",
                "no",
                "--skip-tests",
                "--release-notes-file",
                str(notes),
            )
            notes_text = notes.read_text(encoding="utf-8")

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["plan"], "create")
        self.assertEqual(payload["targetCommit"], "abc1234")
        self.assertIn("## Validation", notes_text)

    def test_readiness_failure_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            (root / "VERSION").write_text("0.1.1\n", encoding="utf-8")
            code, payload, _ = run_prepare(
                root,
                "--release-version",
                "v0.1.1",
                "--target-commit",
                "abc1234",
                "--main-commit",
                "abc1234",
                "--tag-exists",
                "no",
                "--release-exists",
                "no",
                "--skip-tests",
            )

        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["plan"], "none")
        checks = [item["check"] for item in payload["failures"]]
        self.assertIn("readiness", checks)

    def test_existing_tag_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            code, payload, _ = run_prepare(
                root,
                "--release-version",
                "v0.1.0",
                "--target-commit",
                "abc1234",
                "--main-commit",
                "abc1234",
                "--tag-exists",
                "yes",
                "--release-exists",
                "no",
                "--skip-tests",
            )

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "noop")
        self.assertEqual(payload["plan"], "none")
        self.assertTrue(payload["existingTag"])

    def test_existing_release_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            code, payload, _ = run_prepare(
                root,
                "--release-version",
                "v0.1.0",
                "--target-commit",
                "abc1234",
                "--main-commit",
                "abc1234",
                "--tag-exists",
                "no",
                "--release-exists",
                "yes",
                "--skip-tests",
            )

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "noop")
        self.assertEqual(payload["plan"], "none")
        self.assertTrue(payload["existingRelease"])

    def test_release_probe_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            copy_minimal_repo(root)
            fake_bin = Path(tmp) / "bin"
            fake_bin.mkdir()
            fake_gh = fake_bin / "gh"
            fake_gh.write_text("#!/bin/sh\necho authentication required >&2\nexit 1\n", encoding="utf-8")
            fake_gh.chmod(0o755)
            code, payload, stderr = run_prepare(
                root,
                "--release-version",
                "v0.1.0",
                "--target-commit",
                "abc1234",
                "--main-commit",
                "abc1234",
                "--tag-exists",
                "no",
                "--release-exists",
                "auto",
                "--skip-tests",
                env={"PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
            )

        self.assertEqual(stderr, "")
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["plan"], "none")
        self.assertFalse(payload["existingRelease"])
        checks = [item["check"] for item in payload["failures"]]
        self.assertIn("release_exists", checks)

    def test_target_commit_mismatch_fails_without_explicit_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            code, payload, _ = run_prepare(
                root,
                "--release-version",
                "v0.1.0",
                "--target-commit",
                "abc1234",
                "--main-commit",
                "def5678",
                "--tag-exists",
                "no",
                "--release-exists",
                "no",
                "--skip-tests",
            )

        self.assertEqual(code, 1)
        self.assertEqual(payload["failures"][0]["field"], "target_commit")

    def test_release_version_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_minimal_repo(root)
            code, payload, _ = run_prepare(
                root,
                "--release-version",
                "v0.1.1",
                "--target-commit",
                "abc1234",
                "--main-commit",
                "abc1234",
                "--tag-exists",
                "no",
                "--release-exists",
                "no",
                "--skip-tests",
            )

        self.assertEqual(code, 1)
        self.assertEqual(payload["failures"][0]["field"], "release_version")


if __name__ == "__main__":
    unittest.main()

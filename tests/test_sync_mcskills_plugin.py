import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sync_mcskills_plugin.py"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class SyncMcskillsPluginTest(unittest.TestCase):
    def test_sync_workflow_uses_release_publish_and_cross_repo_pr(self):
        workflow = (ROOT / ".github/workflows/sync-mcskills.yml").read_text(
            encoding="utf-8"
        )

        for expected in (
            "release:",
            "- published",
            "workflow_dispatch:",
            "MC_SKILLS_SYNC_TOKEN",
            "repository: ${{ env.TARGET_REPO }}",
            "python3 scripts/sync_mcskills_plugin.py",
            "python3 scripts/render-plugin-directory.py --check",
            "gh pr create",
            "plugins/loopengineer",
            ".agents/plugins/marketplace.json",
        ):
            self.assertIn(expected, workflow)

    def create_loopengineer_source(self, root: Path, version: str = "1.2.3") -> None:
        write_json(
            root / ".codex-plugin/plugin.json",
            {
                "name": "loopengineer",
                "version": version,
                "description": "Agent loop control-plane plugin.",
                "interface": {
                    "category": "Productivity",
                    "shortDescription": "Control plane for reliable AI agent loops.",
                },
            },
        )
        for relative, text in {
            "README.md": "# LoopEngineer\n",
            "README.zh-CN.md": "# LoopEngineer\n",
            "LICENSE": "MIT\n",
            "VERSION": f"{version}\n",
            "skills/codex-loop-router/skill.yaml": "name: codex-loop-router\n",
            "scripts/loopengineer.py": "print('ok')\n",
            "docs/versioning.md": "# Versioning\n",
            "tests/should-not-copy.txt": "no\n",
            ".github/workflows/should-not-copy.yml": "no\n",
        }.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def create_mcskills_target(self, root: Path) -> None:
        write_json(
            root / ".agents/plugins/marketplace.json",
            {
                "name": "mcskills",
                "plugins": [
                    {
                        "name": "codegraph-intelligence",
                        "source": {
                            "source": "local",
                            "path": "./plugins/codegraph-intelligence",
                        },
                        "policy": {
                            "installation": "AVAILABLE",
                            "authentication": "ON_INSTALL",
                        },
                        "category": "Developer Tools",
                    }
                ],
            },
        )

    def run_sync(self, source: Path, target: Path, release_tag: str = "v1.2.3"):
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--source",
                str(source),
                "--target",
                str(target),
                "--release-tag",
                release_tag,
            ],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        return completed.returncode, json.loads(completed.stdout), completed.stderr

    def test_sync_copies_plugin_snapshot_and_adds_marketplace_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "loopengineer"
            target = Path(tmp) / "mcskills"
            self.create_loopengineer_source(source)
            self.create_mcskills_target(target)

            code, payload, stderr = self.run_sync(source, target)

            marketplace = json.loads(
                (target / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
            )
            entries = {entry["name"]: entry for entry in marketplace["plugins"]}

            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(payload["plugin"], "loopengineer")
            self.assertEqual(payload["version"], "1.2.3")
            self.assertEqual(entries["loopengineer"]["source"]["path"], "./plugins/loopengineer")
            self.assertEqual(entries["loopengineer"]["category"], "Productivity")
            self.assertTrue((target / "plugins/loopengineer/.codex-plugin/plugin.json").exists())
            self.assertTrue((target / "plugins/loopengineer/skills/codex-loop-router/skill.yaml").exists())
            self.assertFalse((target / "plugins/loopengineer/tests/should-not-copy.txt").exists())
            self.assertFalse((target / "plugins/loopengineer/.github/workflows/should-not-copy.yml").exists())

    def test_sync_replaces_existing_snapshot_and_marketplace_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "loopengineer"
            target = Path(tmp) / "mcskills"
            self.create_loopengineer_source(source, version="2.0.0")
            self.create_mcskills_target(target)
            stale = target / "plugins/loopengineer/stale.txt"
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_text("stale\n", encoding="utf-8")
            marketplace = json.loads(
                (target / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
            )
            marketplace["plugins"].append(
                {
                    "name": "loopengineer",
                    "source": {"source": "local", "path": "./old"},
                    "policy": {"installation": "UNAVAILABLE", "authentication": "NONE"},
                    "category": "Old",
                }
            )
            write_json(target / ".agents/plugins/marketplace.json", marketplace)

            code, payload, _ = self.run_sync(source, target, release_tag="v2.0.0")

            updated = json.loads(
                (target / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
            )
            loopengineer_entries = [
                entry for entry in updated["plugins"] if entry["name"] == "loopengineer"
            ]

            self.assertEqual(code, 0)
            self.assertEqual(payload["marketplace"], "updated")
            self.assertEqual(len(loopengineer_entries), 1)
            self.assertEqual(loopengineer_entries[0]["source"]["path"], "./plugins/loopengineer")
            self.assertFalse(stale.exists())

    def test_sync_fails_when_manifest_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "loopengineer"
            target = Path(tmp) / "mcskills"
            self.create_mcskills_target(target)

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--source", str(source), "--target", str(target)],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("missing JSON file", completed.stderr)

    def tearDown(self):
        shutil.rmtree(ROOT / "mcskills", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "4495346edbe459ec914e657cd82ec13ad18fbd7c"
SKILLS = {
    "codex-thread-orchestration": {
        "issue": "#13",
        "source_path": "skills/codex-thread-orchestration/",
            "references": {
            "imported-protocol.md",
            "gates-and-closeout.md",
            "goal-lifecycle.md",
            "heartbeat.md",
            "orchestration-carrier.md",
            "reporting.md",
            "scheduler.md",
            "templates.md",
            "worker.md",
        },
    },
    "codex-scheduler-watcher": {
        "issue": "#14",
        "source_path": "skills/codex-scheduler-watcher/",
            "references": {
            "imported-protocol.md",
            "lane-locks.md",
            "orchestration-carrier.md",
            "parallel-scheduling.md",
            "providers.md",
            "scheduler-lifecycle.md",
            "templates.md",
            "unit-model.md",
            "watcher-automation.md",
        },
    },
}


def parse_simple_yaml(path):
    data = {}
    current_key = None
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if line.startswith("  - ") and current_key:
                data.setdefault(current_key, []).append(line[4:])
                continue
            if not line.startswith(" ") and ":" in line:
                key, value = line.split(":", 1)
                current_key = key
                value = value.strip()
                if value:
                    data[key] = value.strip('"')
    return data


class CoreSkillImportTest(unittest.TestCase):
    def test_imported_skill_metadata_declares_contract(self):
        for skill_id in SKILLS:
            with self.subTest(skill_id=skill_id):
                metadata = parse_simple_yaml(ROOT / "skills" / skill_id / "skill.yaml")
                self.assertEqual(metadata["id"], skill_id)
                self.assertEqual(metadata["version"], "0.1.0")
                self.assertEqual(metadata["skillContractVersion"], "1")
                self.assertEqual(metadata["entrypoint"], "README.md")

    def test_imported_skill_read_paths_exist(self):
        for skill_id in SKILLS:
            with self.subTest(skill_id=skill_id):
                metadata = parse_simple_yaml(ROOT / "skills" / skill_id / "skill.yaml")
                missing = [path for path in metadata["reads"] if not (ROOT / path).exists()]
                self.assertEqual(missing, [])

    def test_imported_reference_sets_match_source_inventory(self):
        for skill_id, expected in SKILLS.items():
            with self.subTest(skill_id=skill_id):
                reference_dir = ROOT / "skills" / skill_id / "references"
                actual = {path.name for path in reference_dir.glob("*.md")}
                self.assertEqual(actual, expected["references"])
                self.assertFalse((ROOT / "skills" / skill_id / ".DS_Store").exists())

    def test_source_provenance_records_legacy_origin(self):
        for skill_id, expected in SKILLS.items():
            with self.subTest(skill_id=skill_id):
                source = (ROOT / "skills" / skill_id / "SOURCE.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn(expected["issue"], source)
                self.assertIn("https://github.com/MC-and-his-Agents/MC-SKILLS.git", source)
                self.assertIn("/Users/mc/dev/MC-SKILLS", source)
                self.assertIn(expected["source_path"], source)
                self.assertIn(f"Target path: `{expected['source_path']}`", source)
                self.assertIn(SOURCE_COMMIT, source)
                self.assertIn("2026-06-15T11:14:03+08:00", source)
                self.assertIn("SKILL.md` -> `references/imported-protocol.md", source)
                self.assertIn("LoopEngineer must not depend on that path at runtime", source)
                self.assertIn(".DS_Store", source)
                self.assertIn("No runtime script, MCP, hook, automation", source)

    def test_imported_agents_declare_interface_prompt(self):
        for skill_id in SKILLS:
            with self.subTest(skill_id=skill_id):
                agent = (ROOT / "skills" / skill_id / "agents" / "openai.yaml").read_text(
                    encoding="utf-8"
                )
                self.assertIn("interface:", agent)
                self.assertIn("display_name:", agent)
                self.assertIn("short_description:", agent)
                self.assertIn("default_prompt:", agent)

    def test_imported_entrypoints_preserve_protocol_semantics_before_refactor(self):
        thread_entry = (
            ROOT
            / "skills"
            / "codex-thread-orchestration"
            / "references"
            / "imported-protocol.md"
        ).read_text(encoding="utf-8")
        watcher_entry = (
            ROOT
            / "skills"
            / "codex-scheduler-watcher"
            / "references"
            / "imported-protocol.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Scheduler Quick Start", thread_entry)
        self.assertIn("Worker Quick Start", thread_entry)
        self.assertIn("No scheduler-readable report, no complete", thread_entry)
        self.assertIn("No bidirectional thread IDs", thread_entry)
        self.assertIn("No report receipt", thread_entry)
        self.assertIn("waiting-scheduler-gate", thread_entry)
        self.assertIn("do_not_read_retired_thread_turns: true", thread_entry)
        self.assertIn("shared lane lock manager", watcher_entry)
        self.assertIn("lane_grant", watcher_entry)
        self.assertIn("No scheduler ACK, no active", watcher_entry)
        self.assertIn("No watcher report receipt", watcher_entry)
        self.assertIn("不调度 worker", watcher_entry)
        self.assertIn("不跑 guardian/review/controlled merge", watcher_entry)
        self.assertIn("禁止运行 shared gate", watcher_entry)
        self.assertIn("human_summary", watcher_entry)
        self.assertIn("provider_gap", watcher_entry)


if __name__ == "__main__":
    unittest.main()

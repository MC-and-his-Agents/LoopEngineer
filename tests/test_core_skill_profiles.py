from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DOC = ROOT / "docs" / "routing" / "core-skill-profile-selection.md"
SHORT_ENTRYPOINTS = [
    ROOT / "skills" / "codex-thread-orchestration" / "README.md",
    ROOT / "skills" / "codex-scheduler-watcher" / "README.md",
]


class CoreSkillProfileTest(unittest.TestCase):
    def test_heavy_entrypoints_stay_short(self):
        for path in SHORT_ENTRYPOINTS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertLess(len(text.splitlines()), 80)
                self.assertIn("Required Output", text)
                self.assertIn("Hard Constraints", text)
                self.assertIn("references/imported-protocol.md", text)

    def test_thread_orchestration_names_profiles_and_forbidden_watcher(self):
        text = (
            ROOT / "skills" / "codex-thread-orchestration" / "README.md"
        ).read_text(encoding="utf-8")
        for profile in (
            "worker_lite",
            "scheduler_lite",
            "scheduler_full",
            "incident_recovery",
        ):
            self.assertIn(profile, text)
        self.assertIn("Do not use this skill for `direct` work", text)
        self.assertIn("Do not start watcher behavior", text)

    def test_scheduler_watcher_names_profiles_and_forbidden_lightweight(self):
        text = (
            ROOT / "skills" / "codex-scheduler-watcher" / "README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("watcher_full", text)
        self.assertIn("incident_recovery", text)
        self.assertIn("Do not use this skill for `direct`", text)
        self.assertIn("worker_lite", text)
        self.assertIn("scheduler_lite", text)

    def test_profile_doc_declares_required_and_forbidden_reads(self):
        text = PROFILE_DOC.read_text(encoding="utf-8")
        self.assertIn("Required reads", text)
        self.assertIn("Forbidden reads", text)
        for profile in (
            "direct",
            "worker_lite",
            "scheduler_lite",
            "scheduler_full",
            "watcher_full",
            "incident_recovery",
        ):
            self.assertIn(profile, text)
        self.assertIn("All `codex-thread-orchestration`", text)
        self.assertIn("All `codex-thread-orchestration` and `codex-scheduler-watcher` references", text)
        self.assertIn("Watcher references", text)
        self.assertIn("Worker references", text)

    def test_heavy_policy_reflects_imported_but_explicit_only_skills(self):
        text = (ROOT / "docs" / "routing" / "heavy-trigger-policy.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("imports the core orchestration skills", text)
        self.assertIn("full\nprotocol references are read only after", text)
        self.assertNotIn("does not import heavy orchestration skills", text)


if __name__ == "__main__":
    unittest.main()

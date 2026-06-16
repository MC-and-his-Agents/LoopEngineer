from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "orchestration" / "watcher-rotation-policy.md"
SKILL = ROOT / "skills" / "codex-scheduler-watcher" / "skill.yaml"


class WatcherRotationPolicyTest(unittest.TestCase):
    def test_policy_declares_summary_first_and_no_thread_database(self):
        text = POLICY.read_text(encoding="utf-8")

        self.assertIn("Issue: #25", text)
        self.assertIn("Summary-First Read Rule", text)
        self.assertIn("loopengineer.watcherInbox", text)
        self.assertIn("Thread history is not a state database", text)

    def test_policy_declares_rotation_thresholds(self):
        text = POLICY.read_text(encoding="utf-8")

        self.assertIn("warn at 675 estimated tokens", text)
        self.assertIn("hard limit at 900 estimated tokens", text)
        self.assertIn("overflow action is `rotate_thread`", text)

    def test_policy_declares_stale_prompt_update_rules(self):
        text = POLICY.read_text(encoding="utf-8")

        self.assertIn("Refresh the watcher prompt before continuing", text)
        self.assertIn("heartbeat target binding", text)
        self.assertIn("completion predicate or candidate unit readiness", text)

    def test_scheduler_watcher_skill_reads_policy(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("docs/orchestration/watcher-inbox.md", text)
        self.assertIn("docs/orchestration/watcher-rotation-policy.md", text)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "routing" / "heavy-trigger-policy.md"


class HeavyTriggerPolicyTest(unittest.TestCase):
    def test_policy_declares_explicit_only_control(self):
        text = POLICY.read_text(encoding="utf-8")
        self.assertIn("explicit-only", text)
        self.assertIn("must not", text)
        self.assertIn("implicitly load or start", text)
        self.assertIn("Do not invent one", text)

    def test_policy_blocks_lightweight_watcher_trigger(self):
        text = POLICY.read_text(encoding="utf-8")
        self.assertIn("Watcher behavior must not be", text)
        self.assertIn("direct", text)
        self.assertIn("worker_lite", text)
        self.assertIn("scheduler_lite", text)
        self.assertIn("triggered by `direct`, `worker_lite`, or `scheduler_lite`", text)

    def test_policy_keeps_runtime_out_of_scope(self):
        text = POLICY.read_text(encoding="utf-8")
        self.assertIn("does not implement routing logic", text)
        self.assertIn("create runtime hooks", text)
        self.assertIn("add MCP\nservers", text)
        self.assertIn("start watcher threads", text)
        self.assertIn("install automations", text)

    def test_policy_names_heavy_profiles(self):
        text = POLICY.read_text(encoding="utf-8")
        for profile in ("scheduler_full", "watcher_full", "incident_recovery"):
            self.assertIn(profile, text)


if __name__ == "__main__":
    unittest.main()

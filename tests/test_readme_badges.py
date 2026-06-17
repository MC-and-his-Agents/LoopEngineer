from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReadmeBadgeTest(unittest.TestCase):
    def test_readmes_use_marketing_badges_without_project_records(self):
        expected_badges = (
            "img.shields.io/github/v/release/MC-and-his-Agents/LoopEngineer",
            "Codex-Plugin",
            "Loop-Engine",
            "Agent-Loop",
            "Control-Plane",
            "Context-Safety",
            "Runtime-Neutral",
            "Evidence-Driven",
            "Worker-Lite",
            "Subagent-Ready",
        )
        forbidden = (
            "Project Records",
            "项目记录",
            "github/stars",
            "github/forks",
            "github/downloads",
        )

        for path in (ROOT / "README.md", ROOT / "README.zh-CN.md"):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for badge in expected_badges:
                    self.assertIn(badge, text)
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()

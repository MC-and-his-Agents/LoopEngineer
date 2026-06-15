from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "codex-context-safety"


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


class ContextSafetySkillTest(unittest.TestCase):
    def test_skill_metadata_declares_contract(self):
        metadata = parse_simple_yaml(SKILL_DIR / "skill.yaml")
        self.assertEqual(metadata["id"], "codex-context-safety")
        self.assertEqual(metadata["version"], "0.1.0")
        self.assertEqual(metadata["skillContractVersion"], "1")
        self.assertEqual(metadata["entrypoint"], "README.md")

    def test_skill_reads_required_context_surfaces(self):
        metadata = parse_simple_yaml(SKILL_DIR / "skill.yaml")
        reads = set(metadata["reads"])
        self.assertIn("schemas/v1/context-budget.schema.json", reads)
        self.assertIn("schemas/v1/context-budget.default.json", reads)
        self.assertIn("scripts/context_guard.py", reads)
        self.assertIn("docs/context-safety/no-inline-large-artifacts.md", reads)
        self.assertIn("schemas/v1/handoff-manifest.schema.json", reads)
        self.assertIn("docs/context-safety/handoff-rotation.md", reads)
        self.assertIn("templates/handoff-replacement.md", reads)

    def test_skill_read_paths_exist(self):
        metadata = parse_simple_yaml(SKILL_DIR / "skill.yaml")
        missing = [path for path in metadata["reads"] if not (ROOT / path).exists()]
        self.assertEqual(missing, [])

    def test_entrypoint_stays_short_and_excludes_heavy_runtime(self):
        entrypoint = (SKILL_DIR / "README.md").read_text(encoding="utf-8")
        self.assertLess(len(entrypoint.splitlines()), 80)
        forbidden = ("watcher", "scheduler", "worker", "hook", "MCP", "Loom adapter")
        self.assertIn("Do not start watcher", entrypoint)
        for term in forbidden:
            self.assertIn(term, entrypoint)


if __name__ == "__main__":
    unittest.main()

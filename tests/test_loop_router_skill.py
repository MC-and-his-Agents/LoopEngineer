from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "codex-loop-router"
PROFILES = {
    "direct",
    "worker_lite",
    "scheduler_lite",
    "scheduler_full",
    "watcher_full",
    "incident_recovery",
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


class LoopRouterSkillTest(unittest.TestCase):
    def test_skill_metadata_declares_contract(self):
        metadata = parse_simple_yaml(SKILL_DIR / "skill.yaml")
        self.assertEqual(metadata["id"], "codex-loop-router")
        self.assertEqual(metadata["version"], "0.1.0")
        self.assertEqual(metadata["skillContractVersion"], "1")
        self.assertEqual(metadata["entrypoint"], "README.md")

    def test_skill_read_paths_exist(self):
        metadata = parse_simple_yaml(SKILL_DIR / "skill.yaml")
        missing = [path for path in metadata["reads"] if not (ROOT / path).exists()]
        self.assertEqual(missing, [])
        self.assertIn("docs/routing/heavy-trigger-policy.md", metadata["reads"])

    def test_entrypoint_stays_short_and_selection_only(self):
        entrypoint = (SKILL_DIR / "README.md").read_text(encoding="utf-8")
        self.assertLess(len(entrypoint.splitlines()), 80)
        self.assertIn("does not execute", entrypoint)
        for profile in PROFILES:
            self.assertIn(profile, entrypoint)

    def test_profile_docs_cover_all_profiles(self):
        profiles_doc = (ROOT / "docs/routing/route-profiles.md").read_text(encoding="utf-8")
        matrix_doc = (ROOT / "docs/routing/trigger-matrix.md").read_text(encoding="utf-8")
        for profile in PROFILES:
            self.assertIn(profile, profiles_doc)
            self.assertIn(profile, matrix_doc)
        self.assertIn("The router must not", profiles_doc)
        self.assertIn("Use the lowest matching profile", matrix_doc)

    def test_router_references_heavy_trigger_policy(self):
        metadata = parse_simple_yaml(SKILL_DIR / "skill.yaml")
        entrypoint = (SKILL_DIR / "README.md").read_text(encoding="utf-8")
        policy = (ROOT / "docs/routing/heavy-trigger-policy.md").read_text(encoding="utf-8")

        self.assertIn("docs/routing/heavy-trigger-policy.md", metadata["reads"])
        self.assertIn("Heavy trigger policy", entrypoint)
        self.assertIn("explicit-only", policy)
        self.assertIn("triggered by `direct`, `worker_lite`, or `scheduler_lite`", policy)


if __name__ == "__main__":
    unittest.main()

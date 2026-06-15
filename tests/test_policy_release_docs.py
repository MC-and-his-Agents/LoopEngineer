from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SUBAGENT_DOC = ROOT / "docs" / "orchestration" / "subagent-boundaries.md"
RELEASE_DOC = ROOT / "docs" / "releases" / "v0.1.0.md"


class PolicyReleaseDocsTest(unittest.TestCase):
    def test_subagent_boundary_doc_declares_control_plane_owner(self):
        text = SUBAGENT_DOC.read_text(encoding="utf-8")
        self.assertIn("Issue: #17", text)
        self.assertIn("Thread communication owns the control plane", text)
        self.assertIn("bounded helpers", text)
        self.assertIn("Subagent output is evidence", text)
        self.assertIn("The main agent remains accountable", text)

    def test_subagent_boundary_doc_forbids_state_and_gate_ownership(self):
        text = SUBAGENT_DOC.read_text(encoding="utf-8")
        for forbidden in (
            "shared channels or lane locks",
            "report consumption or state transitions",
            "review approval, guardian, merge, release, or closeout",
            "external permissions",
        ):
            self.assertIn(forbidden, text)

    def test_release_doc_covers_v010_manual_checklist(self):
        text = RELEASE_DOC.read_text(encoding="utf-8")
        self.assertIn("Issue: #47", text)
        self.assertIn("does not mean the full orchestration protocol is stable", text)
        for required in (
            "VERSION",
            "CHANGELOG.md",
            "metadata/loopengineer.json",
            ".codex-plugin/plugin.json",
            "skills/*/skill.yaml",
            "schemas/v*/...schema.json",
            "python3 -m unittest discover -s tests",
            "git diff --check",
        ):
            self.assertIn(required, text)

    def test_release_doc_documents_tag_without_creating_artifacts(self):
        text = RELEASE_DOC.read_text(encoding="utf-8")
        self.assertIn("git tag v0.1.0", text)
        self.assertIn("git push origin v0.1.0", text)
        self.assertIn("Do not create this tag as part of #47", text)
        self.assertIn("GitHub Release artifacts", text)
        self.assertIn("Package-manager publishing", text)


if __name__ == "__main__":
    unittest.main()

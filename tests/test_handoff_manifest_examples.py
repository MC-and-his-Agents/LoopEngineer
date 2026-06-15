import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "v1" / "handoff-manifest.schema.json"
VALID_EXAMPLE = ROOT / "schemas" / "v1" / "examples" / "handoff-manifest.valid.json"
INVALID_OLD_THREAD = (
    ROOT
    / "schemas"
    / "v1"
    / "examples"
    / "handoff-manifest.invalid-old-thread-source.json"
)


class HandoffManifestExampleTests(unittest.TestCase):
    def load_json(self, path):
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def manifest_errors(self, manifest):
        errors = []
        allowed = set(manifest["authority"]["allowed_sources"])
        forbidden = set(manifest["authority"]["forbidden_sources"])
        prohibitions = set(manifest["prohibitions"])

        for source in ("state_root", "handoff_manifest", "live_facts"):
            if source not in allowed:
                errors.append(f"missing allowed source: {source}")

        for source in ("retired_thread_history", "old_thread_transcript"):
            if source not in forbidden:
                errors.append(f"missing forbidden source: {source}")
            if source in allowed:
                errors.append(f"forbidden source allowed: {source}")

        if "do_not_use_retired_thread_as_fact_source" not in prohibitions:
            errors.append("missing retired-thread prohibition")

        return errors

    def test_schema_declares_old_thread_as_forbidden_source(self):
        schema = self.load_json(SCHEMA)
        self.assertEqual(schema["schemaVersion"], "1.0")
        self.assertEqual(schema["kind"], "loopengineer.handoffManifest")
        self.assertIn("$id", schema)
        forbidden_enum = schema["properties"]["authority"]["properties"][
            "forbidden_sources"
        ]["items"]["enum"]
        prohibitions_enum = schema["properties"]["prohibitions"]["items"]["enum"]

        self.assertIn("retired_thread_history", forbidden_enum)
        self.assertIn("old_thread_transcript", forbidden_enum)
        self.assertIn("do_not_use_retired_thread_as_fact_source", prohibitions_enum)

    def test_valid_example_uses_only_authoritative_recovery_sources(self):
        manifest = self.load_json(VALID_EXAMPLE)

        self.assertEqual(manifest["schemaVersion"], "1.0")
        self.assertEqual(manifest["kind"], "loopengineer.handoffManifest")
        self.assertEqual([], self.manifest_errors(manifest))

    def test_invalid_example_documents_old_thread_source_violation(self):
        manifest = self.load_json(INVALID_OLD_THREAD)

        errors = self.manifest_errors(manifest)

        self.assertIn("forbidden source allowed: old_thread_transcript", errors)
        self.assertIn("missing forbidden source: retired_thread_history", errors)
        self.assertIn("missing retired-thread prohibition", errors)


if __name__ == "__main__":
    unittest.main()

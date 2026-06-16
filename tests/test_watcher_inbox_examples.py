import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v1"
EXAMPLES = SCHEMA_DIR / "examples"


SUMMARY_FIELDS = {
    "unconsumed_report_count",
    "unconsumed_channel_event_count",
    "unacked_instruction_count",
    "stale_heartbeat_count",
    "stale_channel_owner_count",
    "candidate_unit_count",
    "required_next_action_count",
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def require_fields(data, fields, label):
    return [f"{label} missing {field}" for field in fields if field not in data]


def validate_watcher_inbox(data):
    errors = require_fields(
        data,
        {
            "schemaVersion",
            "kind",
            "inbox_id",
            "version",
            "watcher_id",
            "generated_at",
            "state_root",
            "sources",
            "summary",
            "unconsumed_scheduler_reports",
            "unconsumed_channel_events",
            "unacked_scheduler_instructions",
            "stale_heartbeat_targets",
            "stale_channel_owners",
            "candidate_units",
            "required_next_actions",
            "next_action",
        },
        "watcher_inbox",
    )
    if data.get("kind") != "loopengineer.watcherInbox":
        errors.append("watcher_inbox kind is invalid")
    if not str(data.get("inbox_id", "")).startswith("watcher-inbox-"):
        errors.append("watcher_inbox id is invalid")
    if not data.get("sources"):
        errors.append("watcher_inbox sources must be non-empty")
    if isinstance(data.get("summary"), dict):
        errors.extend(require_fields(data["summary"], SUMMARY_FIELDS, "summary"))
        for field in SUMMARY_FIELDS:
            value = data["summary"].get(field)
            if not isinstance(value, int) or value < 0:
                errors.append("summary count must be non-negative integer")
    return errors


class WatcherInboxExampleTests(unittest.TestCase):
    def test_schema_declares_required_metadata(self):
        schema = load_json(SCHEMA_DIR / "watcher-inbox.schema.json")

        self.assertEqual(schema["schemaVersion"], "1.0")
        self.assertEqual(schema["kind"], "loopengineer.watcherInbox")
        self.assertIn("$id", schema)

    def test_valid_example_is_valid(self):
        inbox = load_json(EXAMPLES / "watcher-inbox.valid.json")

        self.assertEqual(validate_watcher_inbox(inbox), [])
        self.assertEqual(inbox["summary"]["unconsumed_report_count"], 1)
        self.assertEqual(len(inbox["required_next_actions"]), 1)

    def test_invalid_example_is_invalid(self):
        inbox = load_json(EXAMPLES / "watcher-inbox.invalid-empty-sources.json")

        self.assertIn("watcher_inbox sources must be non-empty", validate_watcher_inbox(inbox))


if __name__ == "__main__":
    unittest.main()

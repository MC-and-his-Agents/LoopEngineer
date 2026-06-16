import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v1"
EXAMPLES = SCHEMA_DIR / "examples"
VERSION_FIELDS = {
    "productVersion",
    "protocolVersion",
    "schemaVersion",
    "skillContractVersion",
}
NEXT_ACTION_FIELDS = {"owner", "action", "status"}
CHANNEL_TYPES = {
    "shared_fact_chain_status",
    "shadow_carrier",
    "current_item_review",
    "high_cost_gate",
    "merge",
    "contract",
}
CHANNEL_STATES = {
    "channel-free",
    "channel-granted",
    "channel-release-pending",
    "channel-blocked",
    "channel-stale-owner",
    "channel-released",
}
EVENT_TYPES = {"request", "grant", "wait", "deny", "release"}
DECISION_TYPES = {
    "grant_channel",
    "deny_channel",
    "wait",
    "readback",
    "recover_scheduler",
    "release_channel",
    "noop",
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def require_fields(data, fields, label):
    return [f"{label} missing {field}" for field in fields if field not in data]


def validate_version(data):
    return require_fields(data, VERSION_FIELDS, "version")


def validate_next_action(data):
    errors = require_fields(data, NEXT_ACTION_FIELDS, "next_action")
    if data.get("status") not in {"required", "blocked", "waiting", "none"}:
        errors.append("next_action status is invalid")
    return errors


def validate_channel_state(data):
    errors = require_fields(
        data,
        {
            "schemaVersion",
            "kind",
            "channel_id",
            "channel_type",
            "state",
            "version",
            "updated_at",
            "release_predicate",
            "waiting_scheduler_ids",
            "next_action",
        },
        "channel_state",
    )
    if data.get("kind") != "loopengineer.channelState":
        errors.append("channel_state kind is invalid")
    if data.get("channel_type") not in CHANNEL_TYPES:
        errors.append("channel_type is invalid")
    if data.get("state") not in CHANNEL_STATES:
        errors.append("channel state is invalid")
    if isinstance(data.get("version"), dict):
        errors.extend(validate_version(data["version"]))
    if isinstance(data.get("next_action"), dict):
        errors.extend(validate_next_action(data["next_action"]))
    return errors


def validate_waiting_queue(data):
    errors = require_fields(
        data,
        {
            "schemaVersion",
            "kind",
            "queue_id",
            "version",
            "channel_id",
            "updated_at",
            "items",
            "next_action",
        },
        "waiting_queue",
    )
    if data.get("kind") != "loopengineer.waitingQueue":
        errors.append("waiting_queue kind is invalid")
    if isinstance(data.get("version"), dict):
        errors.extend(validate_version(data["version"]))
    wait_ids = []
    for item in data.get("items", []):
        errors.extend(
            require_fields(
                item,
                {
                    "wait_id",
                    "scheduler_id",
                    "unit_id",
                    "request_id",
                    "requested_paths",
                    "resume_condition",
                    "allowed_non_channel_work",
                    "forbidden_until_grant",
                    "next_readback_at",
                },
                "waiting item",
            )
        )
        wait_ids.append(item.get("wait_id"))
        if not item.get("requested_paths"):
            errors.append("waiting item requested_paths must be non-empty")
        if not item.get("forbidden_until_grant"):
            errors.append("waiting item forbidden_until_grant must be non-empty")
    if len(wait_ids) != len(set(wait_ids)):
        errors.append("wait_id values must be unique")
    if isinstance(data.get("next_action"), dict):
        errors.extend(validate_next_action(data["next_action"]))
    return errors


def validate_channel_event(data):
    errors = require_fields(
        data,
        {
            "schemaVersion",
            "kind",
            "event_id",
            "event_type",
            "version",
            "channel_id",
            "scheduler_id",
            "unit_id",
            "created_at",
            "next_action",
        },
        "channel_event",
    )
    if data.get("kind") != "loopengineer.channelEvent":
        errors.append("channel_event kind is invalid")
    if data.get("event_type") not in EVENT_TYPES:
        errors.append("event_type is invalid")
    if isinstance(data.get("version"), dict):
        errors.extend(validate_version(data["version"]))
    if isinstance(data.get("next_action"), dict):
        errors.extend(validate_next_action(data["next_action"]))
    return errors


def validate_watcher_decision(data):
    errors = require_fields(
        data,
        {
            "schemaVersion",
            "kind",
            "decision_id",
            "decision_type",
            "version",
            "watcher_id",
            "created_at",
            "inputs",
            "rationale",
            "next_action",
        },
        "watcher_decision",
    )
    if data.get("kind") != "loopengineer.watcherDecision":
        errors.append("watcher_decision kind is invalid")
    if data.get("decision_type") not in DECISION_TYPES:
        errors.append("decision_type is invalid")
    if not data.get("inputs"):
        errors.append("watcher decision inputs must be non-empty")
    if isinstance(data.get("version"), dict):
        errors.extend(validate_version(data["version"]))
    if isinstance(data.get("next_action"), dict):
        errors.extend(validate_next_action(data["next_action"]))
    return errors


class ChannelWatcherExampleTests(unittest.TestCase):
    def test_schemas_declare_required_metadata(self):
        expected = {
            "channel-state.schema.json": "loopengineer.channelState",
            "waiting-queue.schema.json": "loopengineer.waitingQueue",
            "channel-event.schema.json": "loopengineer.channelEvent",
            "watcher-decision.schema.json": "loopengineer.watcherDecision",
        }
        for filename, kind in expected.items():
            with self.subTest(filename=filename):
                schema = load_json(SCHEMA_DIR / filename)
                self.assertEqual(schema["schemaVersion"], "1.0")
                self.assertEqual(schema["kind"], kind)
                self.assertIn("$id", schema)

    def test_valid_examples_are_valid(self):
        cases = [
            ("channel-state.valid.json", validate_channel_state),
            ("waiting-queue.valid.json", validate_waiting_queue),
            ("channel-event.valid.json", validate_channel_event),
            ("watcher-decision.valid.json", validate_watcher_decision),
        ]
        for filename, validator in cases:
            with self.subTest(filename=filename):
                self.assertEqual(validator(load_json(EXAMPLES / filename)), [])

    def test_invalid_channel_state_is_invalid(self):
        data = load_json(EXAMPLES / "channel-state.invalid-missing-release-predicate.json")

        self.assertIn("channel_state missing release_predicate", validate_channel_state(data))

    def test_invalid_waiting_queue_is_invalid(self):
        data = load_json(EXAMPLES / "waiting-queue.invalid-empty-requested-paths.json")

        self.assertIn("waiting item requested_paths must be non-empty", validate_waiting_queue(data))

    def test_invalid_channel_event_is_invalid(self):
        data = load_json(EXAMPLES / "channel-event.invalid-missing-scheduler.json")

        self.assertIn("channel_event missing scheduler_id", validate_channel_event(data))

    def test_invalid_watcher_decision_is_invalid(self):
        data = load_json(EXAMPLES / "watcher-decision.invalid-empty-inputs.json")

        self.assertIn("watcher decision inputs must be non-empty", validate_watcher_decision(data))


if __name__ == "__main__":
    unittest.main()

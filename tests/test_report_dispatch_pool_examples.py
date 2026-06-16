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
REPORT_TYPES = {
    "instruction_ack",
    "startup_report",
    "progress_update",
    "blocker_update",
    "completion_result",
    "gate_wait",
    "routing_missing",
    "correction_result",
}
ROLES = {"worker", "scheduler", "watcher"}
REPORT_STATUSES = {"acknowledged", "running", "blocked", "waiting", "completed", "failed"}
DISPATCH_STATUSES = {
    "instruction-sent-awaiting-ack",
    "confirming",
    "active",
    "waiting-report",
    "waiting-scheduler-gate",
    "blocked",
    "completed",
    "failed",
    "replacement-planned",
}
SCHEDULER_STATUSES = {
    "planned",
    "active",
    "blocked",
    "waiting-gate",
    "completed",
    "retired",
    "systemError-retired",
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def require_fields(data, fields, label):
    missing = [field for field in fields if field not in data]
    return [f"{label} missing {field}" for field in missing]


def validate_version(data):
    return require_fields(data, VERSION_FIELDS, "version")


def validate_next_action(data):
    errors = require_fields(data, NEXT_ACTION_FIELDS, "next_action")
    if data.get("status") not in {"required", "blocked", "waiting", "none"}:
        errors.append("next_action status is invalid")
    return errors


def validate_report(data):
    errors = []
    errors.extend(
        require_fields(
            data,
            {
                "schemaVersion",
                "kind",
                "report_id",
                "report_type",
                "role",
                "status",
                "version",
                "producer",
                "created_at",
                "summary",
                "next_action",
            },
            "report",
        )
    )
    if data.get("schemaVersion") != "1.0":
        errors.append("report schemaVersion is invalid")
    if data.get("kind") != "loopengineer.report":
        errors.append("report kind is invalid")
    if not str(data.get("report_id", "")).startswith("report-"):
        errors.append("report_id must start with report-")
    if data.get("report_type") not in REPORT_TYPES:
        errors.append("report_type is invalid")
    if data.get("role") not in ROLES:
        errors.append("role is invalid")
    if data.get("status") not in REPORT_STATUSES:
        errors.append("status is invalid")
    if isinstance(data.get("version"), dict):
        errors.extend(validate_version(data["version"]))
    if isinstance(data.get("producer"), dict) and data["producer"].get("role") not in ROLES:
        errors.append("producer role is invalid")
    if isinstance(data.get("next_action"), dict):
        errors.extend(validate_next_action(data["next_action"]))
    return errors


def validate_dispatch_table(data):
    errors = []
    errors.extend(
        require_fields(
            data,
            {
                "schemaVersion",
                "kind",
                "table_id",
                "version",
                "scheduler_id",
                "created_at",
                "state_root",
                "entries",
                "next_action",
            },
            "dispatch_table",
        )
    )
    if data.get("schemaVersion") != "1.0":
        errors.append("dispatch table schemaVersion is invalid")
    if data.get("kind") != "loopengineer.dispatchTable":
        errors.append("dispatch table kind is invalid")
    if isinstance(data.get("version"), dict):
        errors.extend(validate_version(data["version"]))
    instruction_ids = []
    for entry in data.get("entries", []):
        errors.extend(
            require_fields(
                entry,
                {
                    "instruction_id",
                    "unit_id",
                    "status",
                    "expected_report_type",
                    "report_output_path",
                    "report_to_thread_id",
                    "assigned_scope",
                    "next_action",
                },
                "dispatch entry",
            )
        )
        instruction_ids.append(entry.get("instruction_id"))
        if entry.get("status") not in DISPATCH_STATUSES:
            errors.append("dispatch entry status is invalid")
        if isinstance(entry.get("next_action"), dict):
            errors.extend(validate_next_action(entry["next_action"]))
    if len(instruction_ids) != len(set(instruction_ids)):
        errors.append("dispatch instruction_id values must be unique")
    if isinstance(data.get("next_action"), dict):
        errors.extend(validate_next_action(data["next_action"]))
    return errors


def validate_scheduler_pool(data):
    errors = []
    errors.extend(
        require_fields(
            data,
            {
                "schemaVersion",
                "kind",
                "pool_id",
                "version",
                "created_at",
                "state_root",
                "schedulers",
                "next_action",
            },
            "scheduler_pool",
        )
    )
    if data.get("schemaVersion") != "1.0":
        errors.append("scheduler pool schemaVersion is invalid")
    if data.get("kind") != "loopengineer.schedulerPool":
        errors.append("scheduler pool kind is invalid")
    if isinstance(data.get("version"), dict):
        errors.extend(validate_version(data["version"]))
    scheduler_ids = []
    for scheduler in data.get("schedulers", []):
        errors.extend(
            require_fields(
                scheduler,
                {
                    "scheduler_id",
                    "unit_id",
                    "status",
                    "report_inbox",
                    "next_action",
                },
                "scheduler",
            )
        )
        scheduler_ids.append(scheduler.get("scheduler_id"))
        if scheduler.get("status") not in SCHEDULER_STATUSES:
            errors.append("scheduler status is invalid")
        if isinstance(scheduler.get("next_action"), dict):
            errors.extend(validate_next_action(scheduler["next_action"]))
    if len(scheduler_ids) != len(set(scheduler_ids)):
        errors.append("scheduler_id values must be unique")
    if isinstance(data.get("next_action"), dict):
        errors.extend(validate_next_action(data["next_action"]))
    return errors


class ReportDispatchPoolExampleTests(unittest.TestCase):
    def test_schemas_declare_required_metadata(self):
        expected = {
            "report.schema.json": "loopengineer.report",
            "dispatch-table.schema.json": "loopengineer.dispatchTable",
            "scheduler-pool.schema.json": "loopengineer.schedulerPool",
        }
        for filename, kind in expected.items():
            with self.subTest(filename=filename):
                schema = load_json(SCHEMA_DIR / filename)
                self.assertEqual(schema["schemaVersion"], "1.0")
                self.assertEqual(schema["kind"], kind)
                self.assertIn("$id", schema)

    def test_report_valid_example_covers_identity_status_version_and_next_action(self):
        report = load_json(EXAMPLES / "report.valid.json")

        self.assertEqual(validate_report(report), [])
        self.assertEqual(report["report_id"], "report-worker-18-ack")
        self.assertEqual(report["report_type"], "instruction_ack")
        self.assertEqual(report["role"], "worker")
        self.assertEqual(report["status"], "acknowledged")
        self.assertEqual(set(report["version"]), VERSION_FIELDS)
        self.assertEqual(set(report["next_action"]), NEXT_ACTION_FIELDS)

    def test_report_invalid_example_is_invalid(self):
        report = load_json(EXAMPLES / "report.invalid-missing-next-action.json")

        self.assertIn("report missing next_action", validate_report(report))

    def test_dispatch_table_valid_example_tracks_report_expectation(self):
        table = load_json(EXAMPLES / "dispatch-table.valid.json")

        self.assertEqual(validate_dispatch_table(table), [])
        entry = table["entries"][0]
        self.assertEqual(entry["status"], "instruction-sent-awaiting-ack")
        self.assertEqual(entry["expected_report_type"], "instruction_ack")
        self.assertIn("report_output_path", entry)

    def test_dispatch_table_invalid_example_is_invalid(self):
        table = load_json(EXAMPLES / "dispatch-table.invalid-duplicate-instruction.json")

        self.assertIn("dispatch instruction_id values must be unique", validate_dispatch_table(table))

    def test_scheduler_pool_valid_example_tracks_scheduler_report_inbox(self):
        pool = load_json(EXAMPLES / "scheduler-pool.valid.json")

        self.assertEqual(validate_scheduler_pool(pool), [])
        scheduler = pool["schedulers"][0]
        self.assertEqual(scheduler["status"], "active")
        self.assertEqual(scheduler["report_inbox"], ".loopengineer/state/issue-18/reports/*.json")

    def test_scheduler_pool_invalid_example_is_invalid(self):
        pool = load_json(EXAMPLES / "scheduler-pool.invalid-missing-report-inbox.json")

        self.assertIn("scheduler missing report_inbox", validate_scheduler_pool(pool))


if __name__ == "__main__":
    unittest.main()

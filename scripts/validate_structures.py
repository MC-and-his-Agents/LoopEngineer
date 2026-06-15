#!/usr/bin/env python3
"""Validate LoopEngineer structure examples with deterministic local rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXAMPLES = ROOT / "schemas/v1/examples"
VERSION_FIELDS = {
    "productVersion",
    "protocolVersion",
    "schemaVersion",
    "skillContractVersion",
}
NEXT_ACTION_FIELDS = {"owner", "action", "status"}
NEXT_ACTION_STATUSES = {"required", "blocked", "waiting", "none"}


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def failure(file: str, field: str, message: str, suggested_action: str) -> dict[str, str]:
    return {
        "file": file,
        "field": field,
        "message": message,
        "suggestedAction": suggested_action,
    }


def require_fields(data: dict[str, Any], fields: set[str], file: str, label: str) -> list[dict[str, str]]:
    return [
        failure(file, field, f"{label} missing {field}", f"add {field} to {label}")
        for field in sorted(fields)
        if field not in data
    ]


def load_json(root: Path, path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    file = rel(root, path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI must report all parse failures as JSON.
        return None, [failure(file, "json", f"cannot read JSON: {exc}", "fix JSON syntax")]
    if not isinstance(data, dict):
        return None, [failure(file, "json", "JSON document must be an object", "replace with an object")]
    return data, []


def validate_version(root: Path, path: Path, data: Any) -> list[dict[str, str]]:
    file = rel(root, path)
    if not isinstance(data, dict):
        return [failure(file, "version", "version must be an object", "add version metadata")]
    errors = require_fields(data, VERSION_FIELDS, file, "version")
    if data.get("schemaVersion") != "1.0":
        errors.append(failure(file, "version.schemaVersion", "schemaVersion must be 1.0", "set schemaVersion to 1.0"))
    return errors


def validate_next_action(root: Path, path: Path, data: Any) -> list[dict[str, str]]:
    file = rel(root, path)
    if not isinstance(data, dict):
        return [failure(file, "next_action", "next_action must be an object", "add next_action")]
    errors = require_fields(data, NEXT_ACTION_FIELDS, file, "next_action")
    if data.get("status") not in NEXT_ACTION_STATUSES:
        errors.append(failure(file, "next_action.status", "status is invalid", "use required, blocked, waiting, or none"))
    return errors


def common(root: Path, path: Path, data: dict[str, Any], kind: str) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = require_fields(data, {"schemaVersion", "kind"}, file, "structure")
    if data.get("schemaVersion") != "1.0":
        errors.append(failure(file, "schemaVersion", "schemaVersion must be 1.0", "set schemaVersion to 1.0"))
    if data.get("kind") != kind:
        errors.append(failure(file, "kind", f"kind must be {kind}", f"set kind to {kind}"))
    return errors


def validate_context_budget(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.contextBudget")
    estimation = data.get("estimation")
    profiles = data.get("profiles")
    if not isinstance(estimation, dict):
        errors.append(failure(file, "estimation", "estimation must be an object", "add estimation settings"))
    elif estimation.get("charsPerToken", 0) < 1:
        errors.append(failure(file, "estimation.charsPerToken", "must be positive", "set charsPerToken above zero"))
    if not isinstance(profiles, dict) or not profiles:
        errors.append(failure(file, "profiles", "profiles must be a non-empty object", "add context budget profiles"))
    else:
        for name, profile in profiles.items():
            if not isinstance(profile, dict):
                errors.append(failure(file, f"profiles.{name}", "profile must be an object", "fix profile"))
                continue
            budget = profile.get("budgetTokens")
            warning = profile.get("warnAtTokens")
            if isinstance(budget, int) and isinstance(warning, int) and warning > budget:
                errors.append(failure(file, f"profiles.{name}.warnAtTokens", "must not exceed budgetTokens", "lower warnAtTokens"))
            if profile.get("overflowAction") not in {"write_artifact_send_locator", "rotate_thread"}:
                errors.append(failure(file, f"profiles.{name}.overflowAction", "unsupported overflowAction", "use a supported overflowAction"))
    return errors


def validate_handoff_manifest(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.handoffManifest")
    authority = data.get("authority")
    prohibitions = set(data.get("prohibitions", []))
    if not isinstance(authority, dict):
        errors.append(failure(file, "authority", "authority must be an object", "add authority"))
        return errors
    allowed = set(authority.get("allowed_sources", []))
    forbidden = set(authority.get("forbidden_sources", []))
    for source in ("state_root", "handoff_manifest", "live_facts"):
        if source not in allowed:
            errors.append(failure(file, "authority.allowed_sources", f"missing {source}", "add required authority source"))
    for source in ("retired_thread_history", "old_thread_transcript"):
        if source in allowed:
            errors.append(failure(file, "authority.allowed_sources", f"forbidden source allowed: {source}", "remove forbidden source"))
        if source not in forbidden:
            errors.append(failure(file, "authority.forbidden_sources", f"missing {source}", "add forbidden source"))
    if "do_not_use_retired_thread_as_fact_source" not in prohibitions:
        errors.append(failure(file, "prohibitions", "missing retired-thread prohibition", "add retired thread prohibition"))
    return errors


def validate_report(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.report")
    errors.extend(require_fields(data, {"report_id", "report_type", "role", "status", "version", "producer", "created_at", "summary", "next_action"}, file, "report"))
    if not str(data.get("report_id", "")).startswith("report-"):
        errors.append(failure(file, "report_id", "must start with report-", "use a report-* id"))
    errors.extend(validate_version(root, path, data.get("version")))
    errors.extend(validate_next_action(root, path, data.get("next_action")))
    return errors


def validate_dispatch_table(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.dispatchTable")
    errors.extend(require_fields(data, {"table_id", "version", "scheduler_id", "created_at", "state_root", "entries", "next_action"}, file, "dispatch_table"))
    errors.extend(validate_version(root, path, data.get("version")))
    ids = []
    for entry in data.get("entries", []):
        errors.extend(require_fields(entry, {"instruction_id", "unit_id", "status", "expected_report_type", "report_output_path", "report_to_thread_id", "assigned_scope", "next_action"}, file, "dispatch entry"))
        ids.append(entry.get("instruction_id"))
        errors.extend(validate_next_action(root, path, entry.get("next_action")))
    if len(ids) != len(set(ids)):
        errors.append(failure(file, "entries.instruction_id", "instruction_id values must be unique", "deduplicate dispatch entries"))
    errors.extend(validate_next_action(root, path, data.get("next_action")))
    return errors


def validate_scheduler_pool(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.schedulerPool")
    errors.extend(require_fields(data, {"pool_id", "version", "created_at", "state_root", "schedulers", "next_action"}, file, "scheduler_pool"))
    errors.extend(validate_version(root, path, data.get("version")))
    ids = []
    for scheduler in data.get("schedulers", []):
        errors.extend(require_fields(scheduler, {"scheduler_id", "unit_id", "status", "report_inbox", "next_action"}, file, "scheduler"))
        ids.append(scheduler.get("scheduler_id"))
        errors.extend(validate_next_action(root, path, scheduler.get("next_action")))
    if len(ids) != len(set(ids)):
        errors.append(failure(file, "schedulers.scheduler_id", "scheduler_id values must be unique", "deduplicate schedulers"))
    errors.extend(validate_next_action(root, path, data.get("next_action")))
    return errors


def validate_channel_state(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.channelState")
    errors.extend(require_fields(data, {"channel_id", "channel_type", "state", "version", "updated_at", "release_predicate", "waiting_scheduler_ids", "next_action"}, file, "channel_state"))
    errors.extend(validate_version(root, path, data.get("version")))
    errors.extend(validate_next_action(root, path, data.get("next_action")))
    return errors


def validate_waiting_queue(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.waitingQueue")
    errors.extend(require_fields(data, {"queue_id", "version", "channel_id", "updated_at", "items", "next_action"}, file, "waiting_queue"))
    errors.extend(validate_version(root, path, data.get("version")))
    ids = []
    for item in data.get("items", []):
        errors.extend(require_fields(item, {"wait_id", "scheduler_id", "unit_id", "request_id", "requested_paths", "resume_condition", "allowed_non_channel_work", "forbidden_until_grant", "next_readback_at"}, file, "waiting item"))
        ids.append(item.get("wait_id"))
        if not item.get("requested_paths"):
            errors.append(failure(file, "items.requested_paths", "requested_paths must be non-empty", "add requested paths"))
        if not item.get("forbidden_until_grant"):
            errors.append(failure(file, "items.forbidden_until_grant", "forbidden_until_grant must be non-empty", "add forbidden actions"))
    if len(ids) != len(set(ids)):
        errors.append(failure(file, "items.wait_id", "wait_id values must be unique", "deduplicate waiting items"))
    errors.extend(validate_next_action(root, path, data.get("next_action")))
    return errors


def validate_channel_event(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.channelEvent")
    errors.extend(require_fields(data, {"event_id", "event_type", "version", "channel_id", "scheduler_id", "unit_id", "created_at", "next_action"}, file, "channel_event"))
    errors.extend(validate_version(root, path, data.get("version")))
    errors.extend(validate_next_action(root, path, data.get("next_action")))
    return errors


def validate_watcher_decision(root: Path, path: Path, data: dict[str, Any]) -> list[dict[str, str]]:
    file = rel(root, path)
    errors = common(root, path, data, "loopengineer.watcherDecision")
    errors.extend(require_fields(data, {"decision_id", "decision_type", "version", "watcher_id", "created_at", "inputs", "rationale", "next_action"}, file, "watcher_decision"))
    if not data.get("inputs"):
        errors.append(failure(file, "inputs", "inputs must be non-empty", "cite consumed input locators"))
    errors.extend(validate_version(root, path, data.get("version")))
    errors.extend(validate_next_action(root, path, data.get("next_action")))
    return errors


VALIDATORS: dict[str, Callable[[Path, Path, dict[str, Any]], list[dict[str, str]]]] = {
    "loopengineer.contextBudget": validate_context_budget,
    "loopengineer.handoffManifest": validate_handoff_manifest,
    "loopengineer.report": validate_report,
    "loopengineer.dispatchTable": validate_dispatch_table,
    "loopengineer.schedulerPool": validate_scheduler_pool,
    "loopengineer.channelState": validate_channel_state,
    "loopengineer.waitingQueue": validate_waiting_queue,
    "loopengineer.channelEvent": validate_channel_event,
    "loopengineer.watcherDecision": validate_watcher_decision,
}


def default_inputs(root: Path) -> list[Path]:
    examples = root / "schemas/v1/examples"
    return sorted(examples.glob("*.valid.json")) + sorted((root / "schemas/v1").glob("*.default.json"))


def validate_file(root: Path, path: Path) -> list[dict[str, str]]:
    data, errors = load_json(root, path)
    if data is None:
        return errors
    kind = data.get("kind")
    validator = VALIDATORS.get(kind)
    if validator is None:
        errors.append(
            failure(
                rel(root, path),
                "kind",
                f"unsupported kind {kind!r}",
                "use a supported LoopEngineer structure kind",
            )
        )
        return errors
    return errors + validator(root, path, data)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate LoopEngineer structure files.")
    parser.add_argument("--root", default=str(ROOT), help="Repository root.")
    parser.add_argument(
        "--input-file",
        action="append",
        help="Specific structure file to validate. May be passed more than once.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    paths = [Path(item) for item in args.input_file] if args.input_file else default_inputs(root)
    paths = [path if path.is_absolute() else root / path for path in paths]
    failures: list[dict[str, str]] = []
    for path in paths:
        failures.extend(validate_file(root, path))
    payload = {
        "status": "pass" if not failures else "fail",
        "checkedFiles": [rel(root, path) for path in paths],
        "failures": failures,
    }
    emit(payload)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

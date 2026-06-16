#!/usr/bin/env python3
"""Minimal stdio MCP adapter for LoopEngineer."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "scripts" / "loopengineer.py"
PROTOCOL_VERSION = "2025-06-18"


TOOLS: dict[str, dict[str, Any]] = {
    "loopengineer.context_guard": {
        "command": "context-guard",
        "description": "Check text against a LoopEngineer context budget profile.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {"type": "string"},
                "input_file": {"type": "string"},
                "budget_file": {"type": "string"},
            },
            "required": ["profile", "input_file"],
            "additionalProperties": False,
        },
    },
    "loopengineer.validate_structures": {
        "command": "validate-structures",
        "description": "Validate LoopEngineer structure files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
    },
    "loopengineer.state_digest": {
        "command": "state-digest",
        "description": "Build compact LoopEngineer state digests.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["minimal", "full"]},
                "input_file": {"type": "array", "items": {"type": "string"}},
                "report_inbox_glob": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "loopengineer.loop_audit": {
        "command": "loop-audit",
        "description": "Audit LoopEngineer loop state for orchestration drift.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "array", "items": {"type": "string"}},
                "report_glob": {"type": "array", "items": {"type": "string"}},
                "receipt_glob": {"type": "array", "items": {"type": "string"}},
                "current_owner": {"type": "string", "enum": ["worker", "scheduler", "watcher", "user", "external"]},
                "now": {"type": "string"},
                "stale_after_minutes": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
    },
    "loopengineer.coordination_tax": {
        "command": "coordination-tax",
        "description": "Estimate LoopEngineer coordination cost.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "control_plane_tokens": {"type": "integer", "minimum": 0},
                "cross_thread_messages": {"type": "integer", "minimum": 0},
                "reports_read": {"type": "integer", "minimum": 0},
                "reports_written": {"type": "integer", "minimum": 0},
                "heartbeats": {"type": "integer", "minimum": 0},
                "recovery_actions": {"type": "integer", "minimum": 0},
                "workers": {"type": "integer", "minimum": 0},
                "schedulers": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
    },
    "loopengineer.preflight": {
        "command": "preflight",
        "description": "Return a session admission reminder without state transition or runtime lifecycle action.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


def error_response(request_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def result_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def server_version() -> str:
    try:
        metadata = json.loads((ROOT / "metadata/loopengineer.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - version read failure must not break MCP initialization.
        return "unknown"
    value = metadata.get("version")
    return value if isinstance(value, str) and value else "unknown"


def tool_descriptor(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": spec["description"],
        "inputSchema": spec["inputSchema"],
    }


def validate_object(value: Any, *, label: str) -> tuple[dict[str, Any] | None, str | None]:
    if value is None:
        return {}, None
    if not isinstance(value, dict):
        return None, f"{label} must be an object"
    return value, None


def add_repeated(argv: list[str], flag: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return f"{flag} must be an array of strings"
    for item in value:
        argv.extend([flag, item])
    return None


def add_string(argv: list[str], flag: str, value: Any, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            return f"{flag} is required"
        return None
    if not isinstance(value, str):
        return f"{flag} must be a string"
    argv.extend([flag, value])
    return None


def add_non_negative_int(argv: list[str], flag: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return f"{flag} must be a non-negative integer"
    argv.extend([flag, str(value)])
    return None


def args_for_tool(name: str, arguments: dict[str, Any]) -> tuple[list[str] | None, str | None]:
    extra = set(arguments) - set(TOOLS[name]["inputSchema"]["properties"])
    if extra:
        return None, "unsupported argument(s): " + ", ".join(sorted(extra))
    if name == "loopengineer.context_guard":
        argv: list[str] = []
        for error in (
            add_string(argv, "--profile", arguments.get("profile"), required=True),
            add_string(argv, "--input-file", arguments.get("input_file"), required=True),
            add_string(argv, "--budget-file", arguments.get("budget_file")),
        ):
            if error:
                return None, error
        return argv, None
    if name == "loopengineer.validate_structures":
        argv = []
        error = add_repeated(argv, "--input-file", arguments.get("input_file"))
        return (None, error) if error else (argv, None)
    if name == "loopengineer.state_digest":
        argv = []
        mode = arguments.get("mode")
        if mode is not None:
            if mode not in {"minimal", "full"}:
                return None, "mode must be minimal or full"
            argv.extend(["--mode", mode])
        for error in (
            add_repeated(argv, "--input-file", arguments.get("input_file")),
            add_string(argv, "--report-inbox-glob", arguments.get("report_inbox_glob")),
        ):
            if error:
                return None, error
        return argv, None
    if name == "loopengineer.loop_audit":
        argv = []
        for error in (
            add_repeated(argv, "--input-file", arguments.get("input_file")),
            add_repeated(argv, "--report-glob", arguments.get("report_glob")),
            add_repeated(argv, "--receipt-glob", arguments.get("receipt_glob")),
            add_string(argv, "--current-owner", arguments.get("current_owner")),
            add_string(argv, "--now", arguments.get("now")),
            add_non_negative_int(argv, "--stale-after-minutes", arguments.get("stale_after_minutes")),
        ):
            if error:
                return None, error
        return argv, None
    if name == "loopengineer.coordination_tax":
        argv = []
        for key in (
            "control_plane_tokens",
            "cross_thread_messages",
            "reports_read",
            "reports_written",
            "heartbeats",
            "recovery_actions",
            "workers",
            "schedulers",
        ):
            error = add_non_negative_int(argv, "--" + key.replace("_", "-"), arguments.get(key))
            if error:
                return None, error
        return argv, None
    if name == "loopengineer.preflight":
        if arguments:
            return None, "preflight does not accept arguments"
        return [], None
    return None, f"unknown tool {name}"


def call_engine(command: str, argv: list[str]) -> tuple[int, dict[str, Any] | None, str | None]:
    completed = subprocess.run(
        [sys.executable, str(ENGINE), command, *argv],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return completed.returncode, None, f"engine returned invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return completed.returncode, None, "engine returned non-object JSON"
    return completed.returncode, payload, None


def tool_result(payload: dict[str, Any], *, is_error: bool) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, sort_keys=True),
            }
        ],
        "structuredContent": payload,
        "isError": is_error,
    }


class McpServer:
    def __init__(self) -> None:
        self.initialized = False

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        request_id = message.get("id")
        method = message.get("method")
        params, error = validate_object(message.get("params"), label="params")
        if error:
            return error_response(request_id, -32602, error)
        if method == "initialize":
            self.initialized = True
            return result_response(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "serverInfo": {
                        "name": "loopengineer",
                        "version": server_version(),
                    },
                    "capabilities": {
                        "tools": {},
                    },
                },
            )
        if method == "notifications/initialized":
            self.initialized = True
            return None
        if method == "ping":
            return result_response(request_id, {})
        if method in {"tools/list", "tools/call"} and not self.initialized:
            return error_response(request_id, -32002, "server is not initialized")
        if method == "tools/list":
            return result_response(
                request_id,
                {"tools": [tool_descriptor(name, spec) for name, spec in sorted(TOOLS.items())]},
            )
        if method == "tools/call":
            return self.handle_tool_call(request_id, params or {})
        return error_response(request_id, -32601, f"unknown method {method}")

    def handle_tool_call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if not isinstance(name, str):
            return error_response(request_id, -32602, "tools/call requires a string name")
        if name not in TOOLS:
            return error_response(request_id, -32602, f"unknown tool {name}")
        arguments, error = validate_object(params.get("arguments"), label="arguments")
        if error:
            return error_response(request_id, -32602, error)
        argv, error = args_for_tool(name, arguments or {})
        if error:
            return error_response(request_id, -32602, error)
        returncode, payload, error = call_engine(TOOLS[name]["command"], argv or [])
        if error:
            return error_response(request_id, -32603, error)
        return result_response(request_id, tool_result(payload or {}, is_error=returncode != 0))


def parse_line(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def main() -> int:
    server = McpServer()
    for line in sys.stdin:
        message = parse_line(line)
        if message is None:
            emit = error_response(None, -32700, "parse error")
        else:
            emit = server.handle(message)
        if emit is not None:
            print(json.dumps(emit, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

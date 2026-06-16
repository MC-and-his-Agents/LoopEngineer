import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "mcp" / "loopengineer_stdio.py"


def run_mcp(messages):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        input="\n".join(json.dumps(message) for message in messages) + "\n",
        check=False,
        text=True,
        capture_output=True,
    )
    responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    return completed.returncode, responses, completed.stderr


def request(request_id, method, params=None):
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    return payload


def initialize_request(request_id=1):
    return request(
        request_id,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "loopengineer-test", "version": "0.0.0"},
        },
    )


class McpAdapterTest(unittest.TestCase):
    def test_initialize_and_tools_list(self):
        code, responses, stderr = run_mcp(
            [
                initialize_request(1),
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                request(2, "tools/list", {}),
            ]
        )

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(responses[0]["result"]["capabilities"], {"tools": {}})
        tools = responses[1]["result"]["tools"]
        names = [tool["name"] for tool in tools]
        self.assertEqual(
            names,
            [
                "loopengineer.context_guard",
                "loopengineer.coordination_tax",
                "loopengineer.loop_audit",
                "loopengineer.preflight",
                "loopengineer.state_digest",
                "loopengineer.validate_structures",
            ],
        )
        joined = json.dumps(tools)
        self.assertNotIn("consume_report", joined)
        self.assertNotIn("release_mutation", joined)
        self.assertNotIn("automation_creation", joined)

    def test_tools_call_preflight(self):
        code, responses, _ = run_mcp(
            [
                initialize_request(1),
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                request(2, "tools/call", {"name": "loopengineer.preflight", "arguments": {}}),
            ]
        )

        self.assertEqual(code, 0)
        result = responses[1]["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["capability"], "preflight")
        self.assertTrue(result["structuredContent"]["result"]["boundaries"]["noRuntimeLifecycle"])

    def test_tools_call_context_guard_success(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("small confirmation")
            path = handle.name
        try:
            _, responses, _ = run_mcp(
                [
                    initialize_request(1),
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    request(
                        2,
                        "tools/call",
                        {
                            "name": "loopengineer.context_guard",
                            "arguments": {"profile": "confirmation", "input_file": path},
                        },
                    ),
                ]
            )
        finally:
            Path(path).unlink()

        result = responses[1]["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["capability"], "context_guard")

    def test_underlying_engine_failure_returns_tool_error_result(self):
        _, responses, _ = run_mcp(
            [
                initialize_request(1),
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                request(
                    2,
                    "tools/call",
                    {
                        "name": "loopengineer.validate_structures",
                        "arguments": {"input_file": ["schemas/v1/examples/report.invalid-missing-next-action.json"]},
                    },
                ),
            ]
        )

        result = responses[1]["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["status"], "fail")

    def test_unknown_tool_and_bad_args_fail_closed(self):
        _, responses, _ = run_mcp(
            [
                initialize_request(1),
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                request(2, "tools/call", {"name": "loopengineer.consume_report", "arguments": {}}),
                request(3, "tools/call", {"name": "loopengineer.coordination_tax", "arguments": {"workers": -1}}),
                request(4, "tools/call", {"name": "loopengineer.preflight", "arguments": {"force": True}}),
            ]
        )

        self.assertIn("unknown tool", responses[1]["error"]["message"])
        self.assertIn("non-negative integer", responses[2]["error"]["message"])
        self.assertIn("unsupported argument", responses[3]["error"]["message"])

    def test_tools_require_initialization(self):
        _, responses, _ = run_mcp([request(1, "tools/list", {})])

        self.assertEqual(responses[0]["error"]["code"], -32002)

    def test_tools_require_initialized_notification(self):
        _, responses, _ = run_mcp(
            [
                initialize_request(1),
                request(2, "tools/list", {}),
            ]
        )

        self.assertEqual(responses[1]["error"]["code"], -32002)

    def test_initialize_requires_lifecycle_params(self):
        _, responses, _ = run_mcp(
            [
                request(1, "initialize", {}),
                request(2, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {}}),
            ]
        )

        self.assertIn("protocolVersion", responses[0]["error"]["message"])
        self.assertIn("unsupported protocolVersion", responses[1]["error"]["message"])

    def test_request_ids_and_notifications_fail_closed(self):
        code, responses, stderr = run_mcp(
            [
                {"jsonrpc": "2.0", "id": None, "method": "ping"},
                {"jsonrpc": "2.0", "method": "unknown/notification"},
                {"jsonrpc": "2.0", "method": "tools/list"},
                request(3, "ping", {}),
            ]
        )

        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0]["error"]["code"], -32600)
        self.assertEqual(responses[1]["id"], 3)
        self.assertEqual(responses[1]["result"], {})


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PROFILES = {
    "confirmation",
    "locator",
    "cross_thread",
    "initial_prompt",
    "heartbeat_prompt",
    "handoff_prompt",
}
OVERFLOW_ACTIONS = {
    "write_artifact_send_locator",
    "rotate_thread",
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_context_budget(data):
    errors = []
    if data.get("schemaVersion") != "1.0":
        errors.append("schemaVersion must be 1.0")
    if data.get("kind") != "loopengineer.contextBudget":
        errors.append("kind must be loopengineer.contextBudget")

    estimation = data.get("estimation")
    if not isinstance(estimation, dict):
        errors.append("estimation must be an object")
    else:
        if estimation.get("method") != "deterministic_approx_v1":
            errors.append("estimation.method must be deterministic_approx_v1")
        for key in ("charsPerToken", "lineOverheadTokens", "codeFenceOverheadTokens"):
            value = estimation.get(key)
            if not isinstance(value, int) or value < (1 if key == "charsPerToken" else 0):
                errors.append(f"estimation.{key} has an invalid value")

    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        errors.append("profiles must be an object")
        return errors

    missing = REQUIRED_PROFILES - set(profiles)
    extra = set(profiles) - REQUIRED_PROFILES
    if missing:
        errors.append(f"missing profiles: {sorted(missing)}")
    if extra:
        errors.append(f"unknown profiles: {sorted(extra)}")

    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"{name} must be an object")
            continue
        budget = profile.get("budgetTokens")
        warning = profile.get("warnAtTokens")
        if not isinstance(budget, int) or budget < 1:
            errors.append(f"{name}.budgetTokens has an invalid value")
        if not isinstance(warning, int) or warning < 1:
            errors.append(f"{name}.warnAtTokens has an invalid value")
        if isinstance(budget, int) and isinstance(warning, int) and warning > budget:
            errors.append(f"{name}.warnAtTokens must not exceed budgetTokens")
        if profile.get("overflowAction") not in OVERFLOW_ACTIONS:
            errors.append(f"{name}.overflowAction is not supported")
        allowed_inline = profile.get("allowedInline")
        if not isinstance(allowed_inline, list) or not allowed_inline:
            errors.append(f"{name}.allowedInline must be a non-empty list")
        artifact_required = profile.get("artifactRequiredFor")
        if not isinstance(artifact_required, list):
            errors.append(f"{name}.artifactRequiredFor must be a list")

    return errors


class ContextBudgetExampleTest(unittest.TestCase):
    def test_schema_declares_required_metadata(self):
        schema = load_json(ROOT / "schemas/v1/context-budget.schema.json")
        self.assertEqual(schema["schemaVersion"], "1.0")
        self.assertEqual(schema["kind"], "loopengineer.contextBudget")
        self.assertIn("$id", schema)

    def test_default_budget_is_valid(self):
        data = load_json(ROOT / "schemas/v1/context-budget.default.json")
        self.assertEqual(validate_context_budget(data), [])

    def test_valid_example_is_valid(self):
        data = load_json(ROOT / "schemas/v1/examples/context-budget.valid.json")
        self.assertEqual(validate_context_budget(data), [])

    def test_invalid_example_is_invalid(self):
        data = load_json(ROOT / "schemas/v1/examples/context-budget.invalid.json")
        self.assertNotEqual(validate_context_budget(data), [])

    def test_send_is_not_an_overflow_action(self):
        data = load_json(ROOT / "schemas/v1/context-budget.default.json")
        profile = dict(data["profiles"]["confirmation"])
        profile["overflowAction"] = "send"
        data["profiles"]["confirmation"] = profile
        self.assertIn(
            "confirmation.overflowAction is not supported",
            validate_context_budget(data),
        )


if __name__ == "__main__":
    unittest.main()

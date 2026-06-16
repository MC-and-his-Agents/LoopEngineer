#!/usr/bin/env python3
"""Prepare a fail-closed manual GitHub Release plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import check_release_readiness


ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def failure(check: str, file: str, field: str, message: str, suggested_action: str) -> dict[str, str]:
    return {
        "check": check,
        "file": file,
        "field": field,
        "message": message,
        "suggestedAction": suggested_action,
    }


def git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def gh_release_probe(root: Path, tag: str) -> tuple[bool | None, str | None]:
    completed = subprocess.run(
        ["gh", "release", "view", tag, "--json", "url"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0:
        return True, None
    output = f"{completed.stdout}\n{completed.stderr}".lower()
    if "not found" in output or "404" in output:
        return False, None
    message = completed.stderr.strip() or completed.stdout.strip() or f"gh exited with {completed.returncode}"
    return None, message


def auto_tag_exists(root: Path, tag: str) -> bool:
    completed = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    return completed.returncode == 0


def yes_no_auto(value: str, auto_value: bool) -> bool:
    if value == "yes":
        return True
    if value == "no":
        return False
    return auto_value


def release_notes(version: str, commit: str, readiness: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- {item['name']}: {item['status']}" for item in readiness.get("checks", [])
    )
    return f"""## Summary

Manual GitHub Release for {version}.

## Scope

- Create tag `{version}` at `{commit}`.
- Create a GitHub Release for `{version}`.
- Do not publish packages.

## Validation

- `python3 scripts/check_release_readiness.py` passed.
{checks}

## Compatibility

- productVersion: {readiness.get("checkedVersion")}

## Known Limitations

- Release is manually triggered with `workflow_dispatch`.
- Package publication is intentionally out of scope.
"""


def build_plan(
    root: Path,
    *,
    release_version: str,
    target_commit: str | None,
    main_commit: str | None,
    explicit_target: bool,
    tag_exists: str,
    release_exists: str,
    run_tests: bool,
    release_notes_file: Path | None,
) -> dict[str, Any]:
    root = root.resolve()
    failures: list[dict[str, str]] = []
    if not TAG_RE.match(release_version):
        failures.append(
            failure(
                "release_version",
                "workflow_dispatch",
                "release_version",
                "release version must use vMAJOR.MINOR.PATCH",
                "use a tag-shaped version such as v0.1.0",
            )
        )

    readiness = check_release_readiness.run_checks(root, run_tests=run_tests)
    checked_version = readiness.get("checkedVersion")
    expected_tag = f"v{checked_version}" if checked_version else None
    if readiness["status"] != "pass":
        failures.append(
            failure(
                "readiness",
                "scripts/check_release_readiness.py",
                "status",
                "release readiness failed",
                "fix readiness failures before release",
            )
        )
    if expected_tag is not None and release_version != expected_tag:
        failures.append(
            failure(
                "release_version",
                "workflow_dispatch",
                "release_version",
                f"{release_version} does not match checked version {expected_tag}",
                "use the tag that matches VERSION and release readiness",
            )
        )

    if target_commit is None:
        try:
            target_commit = git_output(root, "rev-parse", "HEAD")
        except Exception as exc:  # noqa: BLE001 - release planning must report as JSON.
            failures.append(
                failure("git", "HEAD", "target_commit", f"cannot resolve HEAD: {exc}", "checkout the release commit")
            )
    if main_commit is None:
        try:
            main_commit = git_output(root, "rev-parse", "origin/main")
        except Exception as exc:  # noqa: BLE001 - release planning must report as JSON.
            failures.append(
                failure("git", "origin/main", "main_commit", f"cannot resolve origin/main: {exc}", "fetch origin main")
            )
    if target_commit and main_commit and target_commit != main_commit and not explicit_target:
        failures.append(
            failure(
                "target_commit",
                "git",
                "target_commit",
                "target commit does not match origin/main",
                "run from current main or pass explicit release commit confirmation",
            )
        )

    existing_tag = yes_no_auto(tag_exists, auto_tag_exists(root, release_version))
    if release_exists == "auto":
        probed_release, probe_error = gh_release_probe(root, release_version)
        existing_release = bool(probed_release)
        if probe_error is not None:
            failures.append(
                failure(
                    "release_exists",
                    "gh release view",
                    "release_exists",
                    f"cannot determine whether release exists: {probe_error}",
                    "retry after GitHub CLI authentication and API access are available",
                )
            )
    else:
        existing_release = yes_no_auto(release_exists, False)
    conclusion = "ready"
    status = "pass"
    plan = "create"
    if existing_tag or existing_release:
        conclusion = "already_exists"
        status = "noop"
        plan = "none"
    if failures:
        conclusion = "blocked"
        status = "fail"
        plan = "none"

    evidence = {
        "status": status,
        "plan": plan,
        "conclusion": conclusion,
        "releaseVersion": release_version,
        "tag": release_version,
        "targetCommit": target_commit,
        "mainCommit": main_commit,
        "explicitTarget": explicit_target,
        "existingTag": existing_tag,
        "existingRelease": existing_release,
        "releaseUrl": None,
        "readiness": readiness,
        "failures": failures,
    }
    if release_notes_file is not None and status == "pass" and target_commit is not None:
        release_notes_file.parent.mkdir(parents=True, exist_ok=True)
        release_notes_file.write_text(
            release_notes(release_version, target_commit, readiness),
            encoding="utf-8",
        )
        evidence["releaseNotesPath"] = str(release_notes_file)
    return evidence


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a manual release plan.")
    parser.add_argument("--root", default=str(ROOT), help="Repository root.")
    parser.add_argument("--release-version", required=True, help="Release tag, for example v0.1.0.")
    parser.add_argument("--target-commit", help="Commit intended for release.")
    parser.add_argument("--main-commit", help="Expected main commit.")
    parser.add_argument("--explicit-target", action="store_true", help="Acknowledge release of a non-main commit.")
    parser.add_argument("--tag-exists", choices=("auto", "yes", "no"), default="auto")
    parser.add_argument("--release-exists", choices=("auto", "yes", "no"), default="auto")
    parser.add_argument("--skip-tests", action="store_true", help="Skip readiness unittest run for focused tests.")
    parser.add_argument("--release-notes-file", help="Write generated release notes to this file when ready.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    notes_file = Path(args.release_notes_file) if args.release_notes_file else None
    payload = build_plan(
        Path(args.root),
        release_version=args.release_version,
        target_commit=args.target_commit,
        main_commit=args.main_commit,
        explicit_target=args.explicit_target,
        tag_exists=args.tag_exists,
        release_exists=args.release_exists,
        run_tests=not args.skip_tests,
        release_notes_file=notes_file,
    )
    emit(payload)
    return 0 if payload["status"] in {"pass", "noop"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

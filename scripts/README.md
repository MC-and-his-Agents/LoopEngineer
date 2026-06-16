# Scripts

This directory is the future home for deterministic LoopEngineer scripts.

Current status:

- `check_version.py` checks product version metadata, skill metadata, schema metadata,
  and the changelog release entry;
- `check_release_readiness.py` aggregates release readiness checks without creating
  tags, releases, packages, or other external artifacts;
- `consume_report.py` validates a report artifact, writes a consumption receipt,
  and emits a compact scheduler/watcher summary;
- `coordination_tax.py` estimates coordination cost and recommends the lightest
  sufficient routing profile without changing external state;
- `context_guard.py` checks text against a v1 context budget profile;
- `loop_audit.py` audits LoopEngineer state for unconsumed reports, missing ACKs,
  stale targets, waiting recovery gaps, and channel release evidence gaps;
- `loopengineer.py` is the runtime-neutral CLI/JSON engine entrypoint; it wraps
  read-only, diagnostic, validation, and admission reminder capabilities in a
  stable JSON envelope;
- `prepare_manual_release.py` prepares the fail-closed manual tag and GitHub
  Release plan used by the workflow dispatch release workflow;
- `state_digest.py` builds compact state summaries for heartbeat and handoff prompts;
- `validate_structures.py` checks LoopEngineer structure files and examples;
- future watcher inbox tooling should keep watcher wakeups summary-first and
  locator-backed;
- scripts must output machine-readable results and fail closed when added;
- scripts must not implicitly modify GitHub, git, PRs, issues, or external state.

Related issues include #6, #20, #21, #22, #23, #27, #46, #64, #65, #82, and #30.

# Scripts

This directory is the future home for deterministic LoopEngineer scripts.

Current status:

- `consume_report.py` validates a report artifact, writes a consumption receipt,
  and emits a compact scheduler/watcher summary;
- `context_guard.py` checks text against a v1 context budget profile;
- `state_digest.py` builds compact state summaries for heartbeat and handoff prompts;
- `validate_structures.py` checks LoopEngineer structure files and examples;
- scripts must output machine-readable results and fail closed when added;
- scripts must not implicitly modify GitHub, git, PRs, issues, or external state.

Related issues include #6, #20, #21, #22, #23, #27, and #46.

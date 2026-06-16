# Scripts

This directory is the future home for deterministic LoopEngineer scripts.

Current status:

- `check_version.py` checks product version metadata, skill metadata, schema metadata,
  and the changelog release entry;
- `context_guard.py` checks text against a v1 context budget profile;
- scripts must output machine-readable results and fail closed when added;
- scripts must not implicitly modify GitHub, git, PRs, issues, or external state.

Related issues include #6, #20, #21, #22, #23, #27, and #46.

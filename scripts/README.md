# Scripts

This directory is the future home for deterministic LoopEngineer scripts.

Current status:

- `check_version.py` checks product version metadata, skill metadata, schema metadata,
  and the changelog release entry;
- `check_release_readiness.py` aggregates release readiness checks without creating
  tags, releases, packages, or other external artifacts;
- `context_guard.py` checks text against a v1 context budget profile;
- `prepare_manual_release.py` prepares the fail-closed manual tag and GitHub
  Release plan used by the workflow dispatch release workflow;
- `validate_structures.py` checks LoopEngineer structure files and examples;
- scripts must output machine-readable results and fail closed when added;
- scripts must not implicitly modify GitHub, git, PRs, issues, or external state.

Related issues include #6, #20, #21, #22, #23, #27, #46, #64, and #65.

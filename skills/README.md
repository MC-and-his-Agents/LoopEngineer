# Skills

This directory is the future home for LoopEngineer skill entrypoints.

Current status:

- `codex-loop-router` provides the lightweight routing entrypoint;
- `codex-context-safety` provides the lightweight context safety entrypoint;
- `codex-thread-orchestration` imports the scheduler/worker coordination
  protocol from MC-SKILLS with provenance recorded in `SOURCE.md`;
- `codex-scheduler-watcher` imports the watcher, scheduler lifecycle, scheduler
  pool, and shared lane protocol from MC-SKILLS with provenance recorded in
  `SOURCE.md`;
- heavy skill entries stay short; full protocols and rare paths live in
  `references/` and are read only after profile selection.

Related issues include #9, #11, #13, #14, #15, #16, and #17.

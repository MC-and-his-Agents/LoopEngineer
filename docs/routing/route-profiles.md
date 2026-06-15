# Route Profiles

Issue: #11

LoopEngineer routes each task to the lightest sufficient profile. The router
chooses; it does not execute orchestration.

## Profiles

| Profile | Use when | Output owner |
| --- | --- | --- |
| `direct` | One owner can complete the work without delegation, shared state, or gate-heavy review. | current agent |
| `worker_lite` | Work is bounded to one scope and benefits from a worker-style objective, but does not need scheduling. | worker |
| `scheduler_lite` | A small set of independent tasks needs ordering, ownership, or report consumption. | scheduler |
| `scheduler_full` | Multiple workers, strict gates, or cross-module contracts need explicit coordination. | scheduler |
| `watcher_full` | Multiple schedulers, shared lanes, long-running observation, or repeated gate drift must be coordinated. | watcher |
| `incident_recovery` | The loop is broken, bloated, inconsistent, or cannot recover from current facts. | recovery owner |

## Router Output

The router response should include:

- recommended profile;
- one-sentence reason;
- next owner;
- next action;
- explicit prohibitions, such as not starting watcher behavior for a low-risk task.

## Boundaries

The router must not:

- create workers, schedulers, watchers, automations, hooks, or MCP calls;
- import heavy orchestration skills;
- treat chat history as authoritative state;
- bypass context safety for large messages.

[中文](README.zh-CN.md)

# LoopEngineer

**The control plane for reliable AI agent loops.**

AI agents are no longer just answering prompts. They plan work, edit code, call tools, spawn subtasks, wait on checks, review evidence, hand off state, and resume across sessions.

That creates a new engineering problem:

> The loop around the agent is now as important as the model inside it.

LoopEngineer helps teams build agent loops that stay within context, preserve evidence, coordinate ownership, control orchestration cost, and recover when long-running work drifts or breaks.

It is not a prompt library.
It is not a workflow checklist.
It is not another "agent tips" repository.

LoopEngineer is an **agent loop control plane**.

---

## Project Records

- [Roadmap](docs/roadmap.md) tracks the milestone order and issue scope.
- [Architecture decisions](docs/adr/index.md) record repository, plugin, skill,
  and context safety boundaries.
- [No inline large artifacts policy](docs/context-safety/no-inline-large-artifacts.md)
  defines which evidence belongs in artifacts instead of thread messages.

---

## Why Agent Loops Need Engineering

A single prompt can make an agent do something useful once.

A reliable agent loop must keep working across:

- long-running tasks;
- large context surfaces;
- tool calls and hosted checks;
- multiple agents or threads;
- partial failures;
- review and merge readiness;
- handoff and recovery;
- evidence that must remain inspectable after the conversation moves on.

Without a control plane, agent loops tend to fail in predictable ways:

- the thread grows until it exceeds the context window;
- logs, diffs, reports, and reviews get pasted into chat history;
- workers say "done" before their reports are consumed;
- schedulers lose track of ownership;
- multiple agents touch shared state without coordination;
- old evidence is reused after the head changed;
- completion becomes a claim instead of a verifiable state;
- safety protocols add so much overhead that simple tasks become expensive.

LoopEngineer exists for this layer.

It treats the agent loop itself as an engineering object.

---

## What LoopEngineer Provides

LoopEngineer focuses on six control-plane capabilities:

```text
Context
Routing
Orchestration
Evidence
Audit
Cost
```

### Context Control

Long-running agents fail when context becomes an invisible dependency.

LoopEngineer moves context safety before message sending, thread creation, heartbeat updates, and handoff.

Target capabilities include:

* context budget profiles;
* outgoing prompt checks;
* no-inline-large-artifact rules;
* locator-only messaging;
* artifact-backed reports;
* handoff manifests;
* thread rotation before overflow.

Core rule:

```text
No context guard pass, no large message.
```

The v1 context budget structure is defined in
`schemas/v1/context-budget.schema.json`, with default profiles in
`schemas/v1/context-budget.default.json`.

### Loop Routing

Not every task needs a scheduler.
Not every scheduler needs a watcher.
Not every change needs full orchestration.

LoopEngineer routes work into the lightest sufficient profile:

```text
direct
worker_lite
scheduler_lite
scheduler_full
watcher_full
incident_recovery
```

Simple work should stay simple.
Risky work gets structure.
Broken loops get recovery.

### Agent Orchestration

LoopEngineer defines explicit roles for complex agent work:

* **Router** chooses the execution profile.
* **Worker** executes a bounded scope and writes a report.
* **Scheduler** coordinates workers, consumes reports, and owns gates.
* **Watcher** manages scheduler pools, shared lanes, and lifecycle.
* **Audit** checks whether the loop is still safe to continue.

Ownership is explicit.
State transitions require evidence.
Shared resources require coordination.

### Evidence Consumption

LoopEngineer does not treat "the agent said it is done" as completion.

Evidence must be written, located, consumed, and reflected in state.

Large evidence belongs in artifacts:

```text
reports/<report_id>.json
artifacts/<run_id>/
```

Threads carry compact locators:

```text
report_id
report_path
state_root
unit_id
state
head
base
next_owner
next_action
```

Core rule:

```text
No consumed report, no state transition.
```

### Audit and Recovery

LoopEngineer aims to detect loop drift before agents continue from invalid state.

Audit checks may include:

* unconsumed reports;
* missing acknowledgements;
* stale heartbeat targets;
* stale lane owners;
* self-owned next actions;
* completion without consumed evidence;
* old head-bound artifacts;
* context rotation violations.

Recovery should rebuild from explicit facts, not from bloated conversation history.

### Coordination Cost

Safety has a cost. Over-orchestration is also a failure mode.

LoopEngineer introduces coordination cost as a first-class design concern:

* control-plane text;
* cross-thread messages;
* report read/write overhead;
* heartbeat cost;
* recovery cost;
* marginal cost of adding schedulers or workers.

The goal is not maximum governance.
The goal is the minimum reliable loop.

---

## How It Works

A LoopEngineer-managed loop follows a simple shape:

```text
User Goal
  ↓
Loop Router
  ↓
Protocol Profile
  ↓
Context Guard
  ↓
Worker / Scheduler / Watcher
  ↓
Artifact-backed Reports
  ↓
Report Consumption
  ↓
Gate / Audit / Handoff
  ↓
Next Owner / Next Action
```

### 1. Route the Work

LoopEngineer first decides how much control plane the task needs.

```text
Small task                       → direct
Bounded single-scope task         → worker_lite
Small coordinated task            → scheduler_lite
Multi-worker or gate-heavy task   → scheduler_full
Multi-scheduler shared state      → watcher_full
Broken or bloated loop            → incident_recovery
```

### 2. Guard the Context

Before any large prompt or message is sent, LoopEngineer checks whether it fits the selected budget.

Protected surfaces include:

* worker prompts;
* scheduler prompts;
* watcher heartbeat prompts;
* correction prompts;
* recovery prompts;
* handoff prompts;
* automation prompts;
* cross-thread messages.

If content is too large:

```text
write artifact
send locator
rotate thread if needed
```

### 3. Execute with Ownership

Workers execute bounded tasks.
Schedulers coordinate workers and consume reports.
Watchers coordinate schedulers and shared lanes.

No role should silently take over another role's state.

### 4. Record Evidence

Complete evidence is written to files.
Threads carry only compact locators and decisions.

This keeps loops recoverable without turning chat history into a state database.

### 5. Audit Before Continuing

Before the loop advances, LoopEngineer can audit whether the current state is still trustworthy.

If not, the loop enters recovery instead of continuing blindly.

---

## Core Principles

### Build the loop, not just the prompt

Prompt quality matters, but agent reliability depends on the loop around the prompt.

### Keep simple work simple

```text
Do not start a watcher if routing is enough.
Do not start a scheduler if a lightweight worker is enough.
Do not create a worker if direct execution is enough.
```

### Do not use chat history as a database

Long-running state belongs in artifacts and structured state surfaces, not in conversation memory.

### Make completion verifiable

```text
No evidence, no completion.
No consumed report, no state transition.
No fresh gate, no merge-ready claim.
```

### Prefer locators over payloads

Large payloads should be written once, referenced many times, and consumed deliberately.

### Recover from facts

Recovery should use GitHub, git, repository facts, state roots, handoff manifests, and current locators—not retired thread turns.

---

## Product Surfaces

LoopEngineer is a plugin-oriented control-plane package.

The current skeleton provides the plugin manifest and top-level directories:

```text
.codex-plugin/plugin.json
skills/
scripts/
schemas/
templates/
```

The planned product surface expands from that skeleton as the related issues
land:

```text
skills/
  codex-loop-router
  codex-context-safety
  codex-thread-orchestration
  codex-scheduler-watcher
  codex-loop-audit

scripts/
  context_guard.py
  state_digest.py
  make_handoff.py
  schema_validate.py
  report_consume.py
  loop_audit.py
  coordination_tax.py

schemas/
  context-budget.schema.json
  report.schema.json
  dispatch-table.schema.json
  scheduler-pool.schema.json
  lane-lock-table.schema.json
  watcher-decision.schema.json

templates/
  handoff-replacement.md
  locator-notice.md
  worker-lite-initial.md
  scheduler-lite-initial.md
```

The intended division of responsibility is:

```text
Skills route and explain.
Schemas define state shape.
Scripts validate and calculate.
Artifacts preserve evidence.
GitHub and git remain sources of truth.
```

---

## Use Cases

LoopEngineer is designed for:

* long-running coding agents;
* multi-agent engineering work;
* multi-thread agent orchestration;
* review, gate, merge-ready, and closeout workflows;
* context-safe handoff and recovery;
* agent workflow auditing;
* reducing over-orchestration cost;
* building durable AI engineering loops.

It is not intended for:

* one-off prompt experiments;
* tiny edits that do not need orchestration;
* replacing GitHub, git, CI, review engines, or worktrees;
* hiding production decisions behind autonomous agents;
* forcing every task into a heavy multi-agent framework.

---

## Relationship with Loom

LoopEngineer is independent.

It can be used on its own, or alongside [Loom](https://github.com/MC-and-his-Agents/Loom) as an external companion plugin.

The layers are different:

```text
Loom          = project operating layer
LoopEngineer  = agent loop control plane
```

Loom owns project-level execution surfaces such as adoption, resume, story, build, review, merge-ready, handoff, closeout, and `.loom/` facts.

LoopEngineer owns loop-level control surfaces such as context safety, routing, scheduler/worker/watcher orchestration, report consumption, audit, recovery, and coordination cost.

Important boundaries:

```text
LoopEngineer is not a Loom scenario skill.
LoopEngineer is not a Loom repo companion.
LoopEngineer does not own .loom facts.
LoopEngineer does not install itself into plugins/loom/skills.
Integration must go through an explicit adapter contract.
```

---

## Status

LoopEngineer is in early buildout.

The current roadmap is maintained in [docs/roadmap.md](docs/roadmap.md) and is
organized around:

1. repository baseline and architecture decisions;
2. context safety MVP;
3. plugin skeleton and loop router;
4. protocol profiles and skill refactor;
5. deterministic scripts and schemas;
6. loop audit, cost controls, and watcher/lane policies;
7. optional MCP and hooks;
8. external Loom integration.

Priority order:

```text
Context safety first.
Routing second.
Heavy orchestration later.
MCP and hooks last.
```

Architecture decisions are indexed in [docs/adr/index.md](docs/adr/index.md).

---

## Philosophy

AI engineering is moving from prompts to loops.

The next bottleneck is not whether an agent can produce code.
It is whether the loop around the agent can stay observable, safe, cost-aware, and recoverable when the work becomes long, parallel, or failure-prone.

LoopEngineer exists for that layer.

```text
Less prompt sprawl.
More loop control.
Fewer mystery states.
More recoverable work.
```

---

## License

MIT

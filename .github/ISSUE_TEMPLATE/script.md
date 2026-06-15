---
name: Script issue
about: Add or update deterministic scripts, checks, or automation helpers.
title: ""
labels: "enhancement, 脚本"
assignees: ""
---

## Background

Describe the deterministic check or script gap.

## Goal

State the command, input shape, and expected machine-readable output.

## Acceptance Criteria

- [ ] The script fails closed on invalid input or missing prerequisites.
- [ ] Output is machine-readable JSON where practical.
- [ ] Tests cover valid and invalid examples.
- [ ] The script does not mutate GitHub, git, PRs, issues, or unrelated repo state implicitly.

## Non-goals

- None yet.

## Context Safety

- [ ] Script output examples stay compact.
- [ ] Large reports or logs are written as artifacts and referenced by path.

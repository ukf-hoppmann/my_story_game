# Claude Code instructions for this repository

This project uses the Claude_Harness plugin (`claude-harness`, enabled in
`.claude/settings.json`). Its configuration is `.claude-harness/config.toml`;
the binding rules are provided by the plugin's skills and hooks, plus the
project documents below. Do not duplicate their content here — read them
fresh each time, since the user edits them directly.

## Project documents

- `docs/development/architecture.md` — binding architecture contract, with
  scope files under `docs/development/architecture/` (e.g. `llm-integration.md`).
  Read it, and every scope matching the files you expect to change, before
  planning or implementing a change.
- `docs/human/technical/architecture-naming.md` — shared naming vocabulary for
  application composition, referenced by architecture rule 9.

## Project-specific conventions

- Daily reports in `docs/development/daily/` use the filename
  `<YYYY-MM-DD>-day<N>.md`, where `<N>` is the sequential development-day
  number (for example `2026-08-06-day11.md`).

## Approval before implementation

Discuss what will be built and how first; implementation MUST NOT start until
the user gives an explicit, unambiguous go-ahead (e.g. "ok", "los", "go",
"mach") for that specific piece of work. Presenting a plan and answering
questions is not implementation. A message that already reads as an
unambiguous go-ahead for a concretely stated plan counts; no extra round-trip
is needed.

## Reporting rule conflicts

When a rule is unclear, contradictory, or does not fit the task, stop before
acting and report it to the user (see skill `claude-harness:conflicts`), naming
the rule and the concrete mismatch.

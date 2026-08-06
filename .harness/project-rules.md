# Project-specific agent rules

## Binding architecture contract

`.harness/architecture-rules.md` is the single authoritative source for the
project architecture. An agent MUST read it before planning or implementing a
code change and MUST apply it together with the generated Harness rules.

An agent MUST NOT bypass the contract when a requested change does not fit it.
The agent MUST stop before implementation, explain the concrete mismatch, and
propose the smallest explicit amendment to the architecture contract. Such an
amendment is non-binding until the project owner approves it.

## Daily report naming

Daily reports MUST use the project-specific filename convention
`docs/development/daily/<YYYY-MM-DD>-day<N>.md`, for example
`docs/development/daily/2026-08-06-day11.md`. `<YYYY-MM-DD>` is the calendar
date and `<N>` is the sequential development-day number used by the project.

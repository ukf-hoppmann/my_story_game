# Claude Code instructions for this repository

This project's binding rules are maintained in `AGENTS.md` (root) and in
`.harness/architecture-rules.md` and `.harness/project-rules.md`. Those files
are the single source of truth; do not duplicate their content here — read
them fresh each time, since the user edits them directly.

## What to do at the start of work in this repo

Before planning or implementing any change, read (or re-read if stale):

- `AGENTS.md`
- `.harness/architecture-rules.md` (and any delegated files it names under
  `.harness/architecture/`)
- `.harness/project-rules.md`

Apply their substantive rules (architecture contract, TDD/testing policy,
daily-report naming, etc.).

## Handling rules that don't translate directly to Claude Code

`AGENTS.md` was generated for a different agent harness (ChatGPT/Codex-style
"general-agent-harness"), so some of it describes mechanisms Claude Code does
not natively have (e.g. `goal`/`exact` change-approval modes, its specific
worktree-assessment protocol, harness-internal terminology). Do not silently
reinterpret or skip these — and do not silently apply a workaround either.

When a rule in these files is unclear, contradictory, or doesn't map onto how
Claude Code actually works, stop before acting and report it to the user,
explicitly classified as one of:

- **Type A — mechanism/phrasing mismatch**: the rule's *intent* is sound, but
  it's written against a harness feature Claude Code doesn't have. Say what
  the rule asks for, what's missing on this side, and propose the closest
  equivalent.
- **Type B — substantive conflict**: following the rule literally would
  produce behavior that doesn't serve the user's actual goal for this
  project, independent of tooling. Say what would go wrong concretely.

Always name the specific rule (quote or point to the section) and give the
reason with the classification above — don't just flag "this is ambiguous"
without saying why and which type it is.

## Goal approval before implementation (concrete `goal`-mode interpretation)

The project's `approval_mode` is `goal` (`.harness/policy.toml`). For this
repo, the user has defined what that means concretely: the normal case is
that we discuss what will be built and how first, and implementation MUST
NOT start until the user gives explicit, unambiguous go-ahead (e.g. "ok",
"los", "go", "mach") for that specific piece of work.

This applies regardless of the active permission mode. Do not start editing
files, running state-changing commands, or otherwise implementing a change
based on inferring that the discussion "sounds settled" or that the request
"seems small enough" — wait for the explicit go-ahead every time. Presenting
a plan or approach and answering questions about it is not itself
implementation and does not require this go-ahead; writing/changing files,
or running commands with side effects, does.

If the user's message already reads as an unambiguous go-ahead for a
concretely stated plan in the same turn, that counts and no separate
confirmation round is needed — the point is to never silently skip the
approval step, not to force a redundant extra round-trip when approval was
already clearly given.

## Integration and cleanup after approval (follow-on operations)

`.harness/policy.toml`'s `[changes]` block — specifically
`autonomous_follow_on` and `goal_default_operations` — is the single place
that controls whether merging and worktree cleanup happen automatically
after a "los"/"ok" go-ahead, or need their own separate confirmation each
time. Re-read that block fresh each session, the same as the other harness
files, and follow whatever it currently says rather than assuming today's
values:

- If `autonomous_follow_on = true` and `goal_default_operations` lists
  `"integration"` and/or `"cleanup"`: once a concrete plan has its explicit
  go-ahead, carry out those listed operations (merging the finished branch,
  removing its worktree) as part of the same approved unit of work, without
  asking again for each one — the same "one go-ahead covers the announced
  work" principle as implementation itself. Destructive steps or anything
  outside the approved plan still need their own explicit approval.
- If `autonomous_follow_on = false`, or `goal_default_operations` is empty
  or omits an operation: implement after go-ahead as usual, but ask again
  separately before merging and before removing a worktree.

To change this behavior, edit `.harness/policy.toml` — not this file.

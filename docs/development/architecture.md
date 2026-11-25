# Binding application architecture

This document is the authoritative architecture contract for `my_story_game`.
Its purpose is to keep changes local, behavior explicit, and components
independently testable. Rules use `MUST`, `SHOULD`, and `MAY` in their normative
sense.

## 1. Organize by cohesive use case

- Application behavior MUST be grouped by a fachlich named capability or use
  case, for example `game_state`, `world_extraction`, or `story_generation`.
- A use case MUST expose focused operations with one cohesive responsibility.
  A growing function or class MUST be split when its parts have distinct
  reasons to change, but trivial helpers MUST NOT be wrapped in speculative
  interfaces merely to satisfy a pattern.
- A larger use case MAY compose smaller use cases. Its sequence and data flow
  MUST remain explicit and testable.
- A module MUST NOT become a general service facade that accumulates unrelated
  operations merely because they concern the same aggregate or adapter.

## 2. Typed operation contract

- Executable application operations MUST provide an `apply` method with a
  use-case-specific typed request and result.
- Construction or a dedicated composition function MAY prepare an operation by
  injecting its collaborators. `apply` executes the already prepared operation;
  it MUST NOT become a hidden service locator or dependency factory.
- Expected outcomes MUST use the closed result contract
  `Success[DataT] | Failure[ErrorT]`. Success and failure values MUST be
  immutable and their payloads MUST be specifically typed.
- A generic response object with optional `data`, `error`, status, or extension
  fields MUST NOT replace the closed result variants.
- Expected boundary and domain failures SHOULD become typed failure values at
  the responsible application operation. Unexpected programming defects MUST
  remain observable and MUST NOT be converted into an unspecified failure.

## 3. Ports and adapters

- Ports MUST be owned by the consuming inner layer and describe a narrow,
  domain-relevant capability such as `GameStateReader`, `GameStateWriter`, or a
  model invocation. A universal `IDataSource`, untyped `IData`, or generic
  `apply(request) -> response` persistence interface MUST NOT be introduced.
- Infrastructure adapters MUST implement application-owned ports. Domain and
  application code MUST NOT import API or infrastructure modules.
- Transport adapters MAY depend on domain and application contracts. They MUST
  reach infrastructure only through injected ports; only an explicit
  composition root MAY import both outer adapters and infrastructure.
- Infrastructure-specific failures MUST be translated to application-owned
  boundary failures before they reach a use case. HTTP status codes, database
  exceptions, and model-provider response objects MUST remain in their owning
  outer adapter.

## 4. Composition, workflow, and policy

- A factory or composition root decides which concrete implementations are
  wired. It MUST NOT decide when a fachlich optional action occurs or hide a
  growing workflow in constructor logic.
- A policy decides when an action occurs, for example whether world extraction
  runs on a turn. A workflow decides the explicit execution order. An operation
  executes one concrete step. These responsibilities MUST remain distinguishable.
- Optional workflow branches MUST be driven by explicit policies or typed input,
  not by a combinatorial family of factories.
- Operation order MUST be visible at the workflow level. Generic pipelines MAY
  be introduced only when they preserve typed transitions and make the concrete
  fachlich sequence easier to understand.

## 5. State and side effects

- Canonical `GameState` changes MUST continue to pass through approved,
  revision-checked domain changes. LLM output MUST NOT write canonical state
  directly.
- Transactions MUST cover only side effects that can actually be atomic in the
  responsible adapter. A workflow containing an LLM call MUST NOT present the
  whole workflow as one database transaction.
- Retrying, idempotency, and partial-failure behavior MUST be explicit wherever
  an operation performs an external or persistent side effect.

## 6. Tests and enforcement

- Every operation MUST be independently testable with test doubles at its
  ports. Workflow tests MUST verify sequence, branching, and failure behavior
  through observable outcomes.
- Architecture tests MUST enforce inward dependency direction for domain,
  application, API adapters, and infrastructure composition boundaries.
- A behavior-preserving refactor MUST retain characterization tests for the
  observable contract. New behavior and bug fixes remain subject to the
  project's test-first rule.

## Scopes

A scope applies in addition to this file, never instead of it. An agent MUST
read this file and every scope that applies before planning or implementing
work in that scope. Scope files live in `architecture/<Scope>.md` next to this
file.

| Scope | Paths | Covers |
|---|---|---|
| llm-integration | `Backend/src/story_game/application/llm/**`, `Backend/src/story_game/infrastructure/llm/**`, `Backend/prompts/**`, `Backend/configs/llm*` | Model invocation, prompt preparation, provider and model adapters, and model-derived outputs |
| story-turn | `Backend/src/story_game/application/play_story_turn.py`, `Backend/src/story_game/application/*story_turn*.py`, `Backend/src/story_game/application/select_*.py`, `Backend/src/story_game/application/story_prompt_sections.py`, `Backend/src/story_game/application/summarize_story.py` | Context selection, turn extraction, change approval, and summary of one story turn |
| persistence | `Backend/src/story_game/infrastructure/persistence/**` | Atomic turn commit, revisioned world snapshots, and append-only story text |
| prompt-profile | `Backend/src/story_game/domain/configuration.py`, `Backend/src/story_game/application/game_state/prompt_profile_validation.py`, `Backend/src/story_game/application/prompt_management/**`, `Backend/src/story_game/application/llm/prompt_selection.py`, `Backend/src/story_game/infrastructure/llm/prompts.py`, `Backend/prompts/**` | The prompt profile of a game, its validation, and the prompt package it selects from |

## 8. Changing this architecture

If a concrete requirement cannot be implemented cleanly under this contract,
an agent MUST NOT add a local exception or bypass an interface. Before changing
code, it MUST identify the requirement, the conflicting rule, the proposed
smallest contract amendment, consequences, alternatives, and verification. The
project owner must explicitly approve the amendment before it becomes binding.

## 9. Application composition naming

The shared naming vocabulary for application composition MUST follow
`docs/development/interfaces/application-composition.md`. In particular,
agents and contributors SHOULD use `Composition Root`, `Composition Builder`,
`Top-Level Composite`, `Composite Level X`, `Leaf`, `Operation Contract`,
`Constructor Injection`, `Injected Collaborator`, and `Delegation` with the
meanings defined there. The interface doc is the detailed reference; this
section makes its use discoverable from the binding architecture contract.

## 10. Lifecycle and removal

- Removable application data MUST follow the lifecycle
  `active → archived → purged`. Archiving is reversible and keeps the history.
  Purging is irreversible, removes the history, and MUST apply only to archived
  items.
- Archive, restore, and purge MUST each be a separate `Leaf` under the
  Operation Contract (for example `ArchivePromptOption`,
  `RestorePromptOption`, `PurgePromptOption`). Each returns a typed outcome per
  item: done, blocked with a typed reason (protected, in use), or not found.
- Blocking rules MUST live in the `Leaf`, not in an adapter or the UI, so
  single and bulk paths are guarded identically. Shipped defaults are
  protected: they MUST NOT be archived, and "reset" restores their original
  content instead.
- Bulk removal MUST be a Composite that delegates to the Leaves. Its request
  carries a typed `RemovalMode` (`ARCHIVE` or `PURGE`) and a typed scope. The
  Composition Root wires the Leaves only. It MUST NOT choose mode or scope
  (rule 4).
- A bulk removal MUST NOT be presented as one transaction. Its result lists
  the outcome per item (rule 5). Repeating it MUST be safe: items already in
  the target state are skipped.
- Persistence ports MUST expose archive, restore, and purge as separate narrow
  capabilities. A generic `delete(anything)` port MUST NOT be introduced
  (rule 3).

If a requirement or design does not fit these rules, the AI names the conflict
and proposes solutions, and the project owner decides (skill
`claude-harness:conflicts`).

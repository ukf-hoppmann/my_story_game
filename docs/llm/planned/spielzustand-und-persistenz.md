# Draft agent rules: game state and persistence

Status: Draft for placement review. This file is not binding until it is moved
to an authoritative Harness location and referenced by `project-rules.md`.

## Scope

These rules record the settled target for the domain entities, persistence,
identity references, game configuration, prompt catalogs, and transient LLM
processing. They complement the general application architecture in
`.harness/architecture-rules.md`.

The current code and database do not yet implement this target completely.
Future implementation work MUST treat the differences listed below as planned
changes, not as evidence that these decisions are still open.

## 1. Aggregate structure

- `GameRun` MUST represent one playable game session and MUST sit above the
  revisioned `GameState`.
- `GameRun` MUST own its status, memberships, and current state revision.
- The initial run statuses MUST be `draft`, `active`, `paused`, and
  `completed`.
- `GameState` MUST contain exactly the current `GameConfiguration`,
  `WorldState`, and `StoryState`, plus the revision identity required for
  concurrency control.
- A completed state revision MUST be sufficient to resume the game.
- Runtime workflow status MUST NOT be part of `GameRun` or `GameState`.

Target structure:

```text
GameRun
├── status
├── memberships
├── current_revision
└── GameState
    ├── GameConfiguration
    ├── WorldState
    └── StoryState
```

## 2. GameConfiguration

- `GameConfiguration` MUST be persisted as part of each relevant GameState
  revision so that a game resumes with the same behavior.
- It MUST contain the selected language, narration style, perspective, control
  mode, narrative boundaries, model references by purpose, and prompt-package
  reference and version.
- Provider URLs, API credentials, secrets, technical connection state, and
  active model calls MUST NOT be stored in `GameConfiguration`.

## 3. WorldState and Goal

- `WorldState` MUST be the structured canonical reality of the game.
- It MUST contain entities, relations, facts, actor knowledge, world rules,
  current world conditions, and goals.
- `Goal` MUST belong exclusively to `WorldState` and MUST NOT be part of
  `StoryState`.
- The initial `Goal` contract MUST contain:
  - `id`
  - `kind`: `main` or `side`
  - `title`
  - `description`
  - `status`: `open`, `completed`, or `failed`
  - `related_entity_ids`
- Numeric progress, milestones, and nested subgoals MUST NOT be implemented in
  the initial target.
- Goal state and related world facts MUST remain consistent. Completing a goal
  does not replace the world changes that caused its completion.

## 4. StoryState and StoryTurn

- `StoryState` MUST represent the concrete chronological prose of the game.
- Its initial target MUST contain completed `StoryTurn` values, one current
  rolling summary, and `current_turn_sequence`.
- `StoryTurn` MUST contain:
  - `id`
  - `sequence`
  - `player_input`
  - `narration`
  - `based_on_revision`
  - `resulting_revision`
  - `completed_at`
- Only a fully completed turn MAY become a persistent `StoryTurn`.
- `Goal`, `Chapter`, `Scene`, `StoryThread`, and a separate generic
  `StoryEvent` MUST NOT be part of the initial target `StoryState`.
- Their exclusion is a deliberate scope decision, not an unresolved question.
- If later requirements introduce chapters or scenes, they MAY only group
  StoryTurns and MUST NOT duplicate canonical WorldState facts.

## 5. Persistence boundary

- The system MUST persist only completed canonical results.
- Prompt composition, model invocation, raw model response, extraction,
  `ProposedChangeSet`, and validation result MUST remain transient Application
  data.
- `ProposedChangeSet` MUST NOT be a persistent entity. Its target ownership is
  the Application layer, not canonical Domain state.
- The model MUST only propose prose and changes. It MUST NOT write GameState or
  persistence directly.
- The Domain MUST remain the authority that accepts revision-checked approved
  operations and creates the next GameState.
- A database transaction MUST NOT span an LLM call.
- The completed StoryTurn and its resulting GameState revision MUST be written
  atomically at the final persistence boundary.
- If processing fails or the backend stops before that final write, the entire
  in-progress turn MUST be discarded. Resumption starts from the previous
  completed revision.

## 6. Persistence model

The target relational model SHOULD remain small and understandable:

- `game_runs`: run identity, status, current revision, timestamps.
- `game_run_members`: Keycloak identity reference, game role, and optional
  player entity reference.
- `game_state_revisions`: immutable revision heads and commit metadata.
- `game_state_configurations`: revisioned per-game configuration.
- existing revisioned `world_*` storage, extended with `world_goals`.
- `story_state_metadata`: current summary and turn sequence per revision.
- `story_turns`: each completed turn stored once in sequence order.

Full StoryTurn text MUST NOT be copied into every GameState revision. The
persistence adapter MUST reconstruct the Domain view from revision metadata and
the append-only turns visible at that revision.

The initial target MUST NOT add tables for workflows, model calls, raw model
responses, extraction runs, memory snapshots, proposed changes, or validation
results.

## 7. Identity and memberships

- Keycloak MUST remain the Identity Provider.
- The application database MUST NOT store user passwords.
- A member MUST be identified by the stable token pair `issuer` and `subject`.
- Membership MUST belong to `GameRun`, support a game role, and MAY reference a
  player entity in WorldState.
- A separate full application `User` entity MUST NOT be introduced initially.
  It MAY be added later for application-owned profile data.

## 8. Global configuration and prompts

- Global provider, model, timeout, capability, and default settings MUST
  initially be loaded from TOML files by Infrastructure adapters.
- Secrets MUST come from environment variables, Docker secrets, or a dedicated
  secret store and MUST NOT be committed as normal configuration.
- System prompts MUST initially be a versioned repository catalog.
- Prompt metadata SHOULD use TOML, long prompt bodies SHOULD use text files,
  and structured model-output schemas SHOULD use JSON.
- Static catalog entries MUST use readable semantic identifiers such as
  `story.base` or `extraction.world-state`; they MUST NOT use UUIDs.
- Application-owned `ModelCatalog` and `PromptCatalog` ports MUST hide whether
  catalog data comes from files or a future database.

## 9. Required changes from the current implementation

The implementation MUST eventually:

1. separate `GameRun` from the revisioned `GameState`;
2. rename the `story_runs` persistence concept to `game_runs`;
3. add GameRun status and Keycloak-backed memberships;
4. add revisioned `GameConfiguration`;
5. move `Goal` from StoryState to WorldState and replace progress with
   `kind`, `description`, and the agreed simple status;
6. replace StoryEvent-based chronology with completed StoryTurns;
7. reduce StoryState to turns, current summary, and current turn sequence;
8. remove Chapter, Scene, StoryThread, and their operations from the initial
   target;
9. keep proposed changes and validation results transient in Application;
10. persist each completed turn and resulting state revision atomically;
11. introduce file-backed model and prompt catalogs behind Application ports.

## 10. Reconsideration rule

The settled exclusions above MUST NOT be reopened during implementation merely
because the current code contains the excluded concepts. Reconsideration
requires a new concrete product requirement, its observable benefit, and an
explicit owner decision.

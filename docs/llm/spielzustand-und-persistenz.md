# Game state and persistence contract

Status: Active project contract for the implemented Domain and persistence
model. Binding Harness architecture rules remain in `.harness/`.

## Canonical aggregate

- `GameRun` represents one playable session above revisioned `GameState`
  values.
- `GameRun` owns `status`, `members`, `current_revision`, `created_at`, and
  `updated_at`.
- Run statuses are `draft`, `active`, `paused`, and `completed`.
- `GameState` contains `run_id`, `revision`, `GameConfiguration`, `WorldState`,
  and `StoryState`.
- A committed revision must be sufficient to resume the game.
- Runtime workflow state must not be added to `GameRun` or `GameState`.

## GameConfiguration

`GameConfiguration` stores the fully resolved per-game values required to
resume with the same behavior:

- language;
- narration style ID;
- perspective ID;
- control mode ID;
- narrative boundaries;
- story, extraction, and summary model IDs;
- prompt-package ID and version.

Provider URLs, credentials, secrets, prompt text, active calls, and provider
objects do not belong here.

## WorldState and Goal

- `WorldState` is the structured canonical reality.
- It owns entities, links, facts, actor knowledge, world rules, and goals.
- `Goal` belongs exclusively to `WorldState`, never to `StoryState`.
- Goal fields are `id`, `kind`, `title`, `description`, `status`, and
  `related_entity_ids`.
- Goal kinds are `main` and `side`; statuses are `open`, `completed`, and
  `failed`.
- Numeric progress, milestones, nested goals, chapters, scenes, and story
  threads are not part of the implemented model.

## StoryState and StoryTurn

- `StoryState` owns completed `StoryTurn` values, one current rolling summary,
  and `current_turn_sequence`.
- `StoryTurn` fields are `id`, `sequence`, `player_input`, `narration`,
  `based_on_revision`, `resulting_revision`, and `completed_at`.
- Only a fully completed turn may become canonical history.
- `StoryState` must not acquire Goals, Chapters, Scenes, StoryThreads, or a
  duplicate generic StoryEvent without a new concrete requirement and owner
  decision.

## Change boundary

- Model output is untrusted input.
- `ProposedChangeSet` is transient Application data and must not be persisted.
- The Application validates proposals and produces an `ApprovedChangeSet` of
  typed Domain operations.
- The Domain alone applies approved operations against the expected revision.
- A completed turn applies its approved WorldState changes and StoryState
  update together.

Prompt composition, active calls, raw responses, extraction results,
validation results, and workflow status remain transient. Do not introduce
tables or Domain entities for them unless resumable workflows or review
history become explicit requirements.

## Persistence

The implemented PostgreSQL baseline consists of:

- `game_runs` and `game_run_members`;
- `game_state_revisions` and `game_state_configurations`;
- revisioned `world_*` snapshots including `world_goals`;
- revisioned `story_state_metadata`;
- append-only `story_turns`.

Each completed StoryTurn is stored once. Historical StoryState values are
reconstructed from the metadata for the requested revision and the turns
visible through that revision.

Revision 1 and configuration-only revisions may exist without a StoryTurn. A
normal completed turn and its resulting GameState revision must be committed
atomically. No database transaction may span an LLM call. If processing stops
before the final commit, resume from the preceding committed revision.

The old JSON persistence adapter and old StoryEvent/Scene/Chapter/Thread/Goal
tables are removed. There is no migration or backward compatibility for the
previous development schema; old local databases must be reset deliberately.

## Identity

- Keycloak remains the Identity Provider; local passwords are forbidden.
- A membership is identified by the token pair `issuer` and `subject`.
- Membership roles are `owner` and `player`.
- A membership may reference a player actor in the WorldState.
- Do not add a full local User entity until application-owned profile data is
  required.

## Explicitly deferred LLM integration

The following decisions remain settled but are not implemented by the current
Domain and persistence change:

- global provider, model, timeout, capability, and default settings start in
  TOML files behind Application-owned catalog ports;
- secrets come from runtime secret sources, never normal repository config;
- prompt metadata uses readable semantic IDs, with TOML metadata, text prompt
  bodies, and JSON output schemas where appropriate;
- Infrastructure may later replace file adapters with database adapters
  without changing the use cases;
- actual model calls, prompt composition, narrative extraction, validation,
  and summary workflows are separate future Application work.

Do not treat these deferred implementation steps as unresolved domain or
database design questions.

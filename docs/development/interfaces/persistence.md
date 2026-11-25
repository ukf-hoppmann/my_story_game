# Interface: Persistence

## Purpose

PostgreSQL stores completed `GameRun` / `GameState` data, scene images, versioned system prompts, the per-task model choice and the global world-tracking switch. The application sees only narrow ports (`application/ports.py` and the ports of the prompt-management, model-settings, scene-image and world-tracking packages); it must not depend on PostgreSQL details. Owner: infrastructure layer, `Backend/src/story_game/infrastructure/persistence/postgres/` (SQL in `migrations/`). Proposals before confirmation are not stored in PostgreSQL (see [http-api.md](./http-api.md)).

## Use

### Ports and adapters

| Port (application) | Adapter | Operations |
|---|---|---|
| `GameRunCreator`, `GameRunReader`, `GameStateReader`, `ConfigurationRevisionWriter`, `CompletedTurnWriter`, `PlayableRunLister` | `PostgresGameStore` (`store.py`) | `create(run, state)`, `load_run`, `load_state(run_id, revision=None)`, `update_configuration`, `commit_turn`, `list_for_member(issuer, subject)` |
| scene-image reader/writer | `PostgresSceneImageStore` (`scene_image_store.py`) | pending/complete/fail images, list, load content |
| `PromptVersionReader`/`Writer`, `PromptOptionUsage`, `PromptPackageCatalog` | `PostgresPromptStore`, `PostgresPromptOptionUsage`, `DbPromptPackageCatalog` (`prompt_store.py`) | versioned prompts, archive/restore/purge |
| `ModelSettingsReader`/`Writer` | `PostgresModelSettingsStore` (`model_settings_store.py`) | versioned per-task model choice |
| `WorldTrackingSettingReader`/`Writer` | `PostgresWorldTrackingStore` (`world_tracking_store.py`) | single-row switch |

Store failures use the application errors `GameStateStoreError`, `GameStateNotFoundError`, `GameStateConflictError`, `GameStateConsistencyError` (re-exported in `infrastructure/persistence/errors.py` as `PersistenceError`, `PersistenceNotFoundError`, `PersistenceConflictError`, `PersistenceConsistencyError`).

Application operations that write: `CreateGameRun`, `UpdateGameConfiguration`, `CommitCompletedTurn`; `ProposeGameRun` writes nothing; `ConfirmGameRunProposal` and `StartPlaythrough` create runs through `CreateGameRun`. Details of those operations: [application-composition.md](./application-composition.md).

### Schema

Migrations are `001_initial.sql` … `009_world_tracking_setting.sql`. Identity and reference columns use the native `UUID` type. Keycloak `issuer`/`subject`, prompt package id/version and prompt-profile option ids are `TEXT`.

| Table | Content |
|---|---|
| `game_runs` | `run_id` (PK), `name` (non-empty, **not unique**), `status` (`draft`/`active`/`paused`/`completed`), `current_revision`, `created_at`, `updated_at` |
| `game_run_members` | `(run_id, issuer, subject)` PK, `game_role` (`owner`/`player`); index `game_run_members_issuer_subject_idx` on `(issuer, subject)` supports run listing |
| `game_run_member_controlled_entities` | Ordered controlled entities per membership (0..n): PK `(run_id, issuer, subject, entity_id)`, unique `(run_id, issuer, subject, position)`, FK only to `game_run_members` |
| `game_state_revisions` | `(run_id, revision)`, `previous_revision` (`revision - 1`, `NULL` for revision 1), `committed_at` |
| `game_state_configurations` | Per revision: `language`, the ten prompt-profile columns (`genre`, `tone` nullable, `prose_style`, `perspective`, `pacing`, `length`, `control_mode`, `player_agency`, `consequence`, `challenge`, `content_profile`), `narrative_boundaries` (JSONB), `prompt_package_id`, `prompt_package_version`. No general style ids, no model references. |
| `world_entities`, `world_links`, `world_facts`, `world_knowledge`, `world_rules`, `world_goals`, `world_goal_related_entities`, `world_scene_locations` | Relational snapshot of the `WorldState` per `(run_id, revision)`; order kept in `position` columns |
| `story_state_metadata` | Per revision: `current_turn_sequence`, and the opening (`initialization_prompt`, `initialization_narration`, `initialization_completed_at`; all three set or all three null) |
| `story_turns` | Each completed turn exactly once: `turn_id`, `sequence`, `player_input`, `narration`, `based_on_revision`, `resulting_revision`, `completed_at`. Unique `(run_id, sequence)` and `(run_id, resulting_revision)`; check `resulting_revision = based_on_revision + 1`. |
| `story_summary_segments` | Immutable chain: `(run_id, through_sequence)` PK, `from_sequence`, `text`, `based_on_revision` |
| `scene_images` | See [Scene images](#scene-images) |
| `system_prompts` | See [System prompts](#system-prompts) |
| `llm_task_settings` | See [Model choice per task](#model-choice-per-task) |
| `world_tracking_setting` | Single row (`id BOOLEAN PRIMARY KEY CHECK (id)`), `enabled`, `updated_at`, `updated_by`; no row means enabled |
| `schema_migrations` | `version`, `applied_at` (written by the migration runner) |

There are no tables for workflow status, model calls, raw responses, extractions, memory snapshots, proposed change sets or validation results. Workflow status is not part of `GameRun` or `GameState`.

### Snapshot versus append-only

- `WorldState` and the configuration are stored as a complete relational snapshot **per revision**.
- Turn texts (`story_turns`) and summary segments (`story_summary_segments`) are appended **once** and not copied per revision (`StorySnapshotWriter.append_turn`, `append_summary_segment`). Loading revision N assembles the `StoryState` from the turns with `resulting_revision <= N`, the segments with `based_on_revision <= N` and the revision's `story_state_metadata`.
- Snapshot-internal references are bound by composite foreign keys to the same `(run_id, revision)`. Goal-entity references and scene locations are therefore stored in their own ordered tables (`world_goal_related_entities`, `world_scene_locations`) instead of JSON lists. The first `world_scene_locations` row (`position` 0) is the primary scene location. The table is not a duplicate of the `located_in` rows in `world_links` (where an entity is versus where the narration looks; in `director` control mode they legitimately differ).
- `game_run_member_controlled_entities.entity_id` has no foreign key to `world_entities`: a membership is not revisioned while an entity row always belongs to one snapshot. The domain checks the assignment (`GameState.validate_members`), the application re-checks it on load.
- Keycloak identity, prompt package id/version and profile option ids are stored as text; PostgreSQL does not own their identity.

### Identity

- All game-owned ids are UUIDs created in application code (`StableId.new()`, `uuid4`) before persistence. There is no database-side id generation.
- `GameRun.name` is a display name, not unique and independent of `run_id`.
- The API accepts and returns ids as canonical UUID strings; a non-UUID id in a path or body is rejected with 422 ([http-api.md](./http-api.md)).

### Scene images

Table `scene_images`: `image_id` (PK), `run_id` (`ON DELETE CASCADE`), `turn_sequence` (≥ 0), `status` (`pending`/`ready`/`failed`), `model`, `refine`, `refine_model`, `refine_strength`, `width`, `height`, `seed`, `prompt`, `compact_prompt`, `error_message`, `image` (`bytea`), `content_type`, `created_at`, `completed_at`. Index on `(run_id, created_at DESC)`.

- Not part of the canonical `GameState`: no revision reference, no state entry.
- Check constraints: `ready` iff image data and content type are present; `failed` iff `error_message` is present; `pending` iff `completed_at` is null.
- Reads always join `game_run_members`: a non-member sees the same result as for a missing image.

### System prompts

Table `system_prompts` is the runtime source of prompts; the TOML files under `Backend/prompts/` only seed it. One row is one version of one entry: `version_id` (UUID), `package_id`, `package_version`, `entry_kind` (`task`/`option`/`directive`), `entry_key` (task id, `<category>/<option>`, directive id), `entry_text`, `sort_position`, `is_default` (default option of a category), `task_ids` (tasks of a directive, `TEXT[]`), `source` (`toml_seed`/`ui`/`toml_reset`), `created_at`, `created_by` (user name, fallback subject; empty for `toml_seed`), `is_active`.

- Append-only: an edit or reset deactivates the active row and inserts a new active row in the same transaction. A partial unique index (`system_prompts_one_active_idx`) enforces at most one active version per entry.
- Seed: at startup (`_seed_prompts` in `api/app.py`) every package under `STORY_GAME_PROMPT_ROOT` that has no stored version yet is imported (`source = toml_seed`). A restart never overwrites UI edits; an empty database reads the TOML again.
- Reset inserts the TOML original as a new `toml_reset` version; edits stay in the history.
- Structure (categories, default options, directive assignment) comes from the TOML and is not editable. Exception: options may be added to `genre`, `tone`, `prose_style` (new row, `source = ui`, position after the last option).
- Lifecycle of an option: archive deactivates the active row without inserting a row (history kept); an entry without an active row is "archived". Restore reactivates its newest row. Purge deletes all rows of the entry and is allowed only when none is active. Only options that are not in the TOML and not selected in any `game_state_configurations` row (`genre`, `tone`, `prose_style`) can be archived.

### Model choice per task

Table `llm_task_settings`, same pattern as `system_prompts`: `version_id` (UUID), `task` (`story`/`extraction`/`summary`/`scene_image`), `model_ref` (logical model id from `configs/llm.toml`), `temperature` (0..2, optional), `max_output_tokens` (> 0, optional), `source`, `created_at`, `created_by`, `is_active`. Partial unique index `llm_task_settings_one_active_idx`: one active row per task.

- Seed: at startup each task without a stored version is filled from `[task_models]` and `[generation_options.<task>]` in `configs/llm.toml`. A restart never overwrites a UI choice.
- Not in the database: providers, URLs, secrets and the model catalog (`configs/llm.toml`, `configs/llm.secrets.toml`). The runtime resolver reads the active row on every call and resolves `model_ref` against the freshly loaded catalog; a model missing there causes a configuration error.

### Migrations

`PostgresSchemaMigrator.migrate()` (`migrations.py`) applies the `*.sql` files of the `migrations/` directory in order, each exactly once per database, tracked in `schema_migrations(version, applied_at)`. The whole run is one transaction. The API runs it at startup when `STORY_GAME_AUTO_MIGRATE` is `true` (default). Manual run from `Backend/`:

```bash
export STORY_GAME_POSTGRES_DSN=postgresql://story_game:story_game_dev@localhost:5433/story_game
PYTHONPATH=src python -m story_game.infrastructure.persistence.postgres.migrate
```

The CLI exits with an error when `STORY_GAME_POSTGRES_DSN` is not set. The runner never re-runs an applied file, so a schema change is always a new file with the next number.

### Local PostgreSQL

`compose.yaml` defines the service `postgres` (PostgreSQL 16, database/user/password `story_game`/`story_game`/`story_game_dev`, host port `POSTGRES_HOST_PORT`, default `5433`, health check):

```bash
docker compose up --detach --wait postgres
```

The Compose `backend` service sets `STORY_GAME_AUTO_MIGRATE: "true"`. `./story-starter clean --yes` deletes the local database volume and restarts with an empty schema (destructive: removes all local runs).

## Behavior

### Write boundaries

| Operation | Persistence effect |
|---|---|
| `create(run, state)` | One transaction: run, members, controlled entities, revision 1, snapshot. |
| `update_configuration` | Locks the run head, checks the base revision, `GameState.reconfigure`, then new revision + snapshot + head update, in one transaction. No `StoryTurn`. |
| `commit_turn` | See [Turn atomicity](#turn-atomicity). |
| `list_for_member(issuer, subject)` | Reads only `game_runs` and `game_run_members` (no world snapshot), ordered by `updated_at` descending. |
| `load_state(run_id, revision=None)` | Current or historical revision. |

`ConfirmGameRunProposal` creates a `draft` run at revision 1 with the initiator as `owner`; every character decided as `player` is bound in `game_run_member_controlled_entities` (0..n). `StartPlaythrough` copies a `draft` run (same state, new `run_id`, revision 1, status `active`) through `CreateGameRun`; the source stays unchanged. Only a `draft` run can be a source, only by a member of that run (checked by `LoadGame`). Turns are accepted only for `active` runs; the application rejects a `draft` run before any model call.

### Turn atomicity

`commit_turn` (`store.py`) runs in a single transaction:

1. Lock the run head (`SELECT … FOR UPDATE` on `game_runs`).
2. Check the expected base revision (`_require_current`); mismatch raises `PersistenceConflictError`.
3. Load the current snapshot and `GameState.complete_turn(...)`.
4. Insert the new revision, write the world snapshot and configuration.
5. `append_turn` (the `StoryTurn`), and `append_summary_segment` when a segment was produced.
6. Update the head (`current_revision`, `updated_at`).

Any conflict or error rolls everything back; a duplicate turn id (`UniqueViolation`) is reported as a conflict. All LLM calls happen before the commit and outside this transaction, so a failed or crashed turn leaves no trace and play resumes from the previous revision. Revision 1 and configuration-only revisions have no `StoryTurn`. A summary segment exists only at a configured summary boundary, is inserted once and is never updated.

### Other behavior

- Concurrent writers are serialized per run by the head lock; the loser of a base-revision race gets a conflict (HTTP 409 `revision_conflict`).
- Prompt edits and resets (deactivate the active row, insert the new one) and model-setting changes are each one transaction; a bulk removal over several options is not one transaction.
- Scene-image writes are independent of revisions; deleting a run cascades to its images.

## Related

- [../architecture.md](../architecture.md): layer and dependency rules for ports and adapters.
- [./domain-model.md](./domain-model.md): the types that are stored.
- [./http-api.md](./http-api.md): endpoints that read and write these data.
- [./application-composition.md](./application-composition.md): operations behind the write boundaries.
- [../architecture/llm-integration.md](../architecture/llm-integration.md): world tracking switch and model resolution.
- Code: [postgres package](../../../Backend/src/story_game/infrastructure/persistence/postgres/), [migrations](../../../Backend/src/story_game/infrastructure/persistence/postgres/migrations/), [ports.py](../../../Backend/src/story_game/application/ports.py), [compose.yaml](../../../compose.yaml).

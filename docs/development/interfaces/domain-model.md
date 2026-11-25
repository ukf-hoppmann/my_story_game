# Interface: Domain model

## Purpose

The domain layer holds the canonical, durable game state and every invariant that protects it. It knows nothing about HTTP, PostgreSQL, Keycloak or an LLM provider. Owner: domain layer, `Backend/src/story_game/domain/`. All other layers (application, API, persistence) construct and read these types; they must not bypass the domain invariants.

## Use

### Structure

```text
GameRun                      id, name, status, members, current_revision, created_at, updated_at
└── GameState (one per revision)
    ├── GameConfiguration    language, PromptProfile, narrative_boundaries, prompt package id + version
    ├── WorldState           entities, links, facts, knowledge, rules, goals, scene_location_ids
    └── StoryState           turns, summary segments, current_turn_sequence, optional initialization
```

A `GameState` is immutable and revisioned. One fully stored revision is sufficient to resume play.

| Type | Module | Key fields / rules |
|---|---|---|
| `StableId` | `value_objects.py` | Wraps `uuid.UUID`. `StableId.new()` creates a `uuid4`. `StableId.parse()` raises `ValidationError` for non-UUID text. |
| `StateRevision` | `value_objects.py` | Integer ≥ 1; `.next()` returns `+1`. |
| `StorySequence` | `value_objects.py` | Integer ≥ 1 (turn number). |
| `GameRun` | `game_run.py` | `id`, `name` (non-empty, **not unique**), `status`, `current_revision`, `members`, `created_at`, `updated_at` (both timezone-aware, `updated_at >= created_at`). Member identities `(issuer, subject)` are unique. |
| `GameRunMember` | `game_run.py` | `issuer`, `subject` (Keycloak identity, plain text), `game_role`, `controlled_entity_ids` (0..n unique `StableId`). No credentials are stored. |
| `GameState` | `game_state.py` | `run_id`, `revision`, `configuration`, `world`, `story`. |
| `GameConfiguration` | `configuration.py` | `language`, `prompt_profile`, `narrative_boundaries` (stripped, unique), `prompt_package_id`, `prompt_package_version`. |
| `PromptProfile` | `configuration.py` | See [Prompt profile](#prompt-profile). |
| `WorldState` | `world.py` | See [WorldState](#worldstate). |
| `StoryState` | `story.py` | See [StoryState](#storystate). |
| `ApprovedChangeSet` | `changes.py` | `proposal_id`, `base_revision`, `changes` (tuple of `StateOperation`). |

Enumerations:

| Enum | Values |
|---|---|
| `GameRunStatus` | `draft`, `active`, `paused`, `completed` |
| `GameRole` | `owner`, `player` |
| `EntityKind` | `character`, `location`, `item`, `creature`, `faction` |
| `ActorRole` | `player`, `npc`, `neutral` |
| `RelationKind` | `located_in`, `possesses`, `contains`, `member_of`, `knows`, `allied_with`, `hostile_to`, `related_to` |
| `VisibilityScope` | `public`, `player_known`, `actor_known`, `director_only` |
| `GoalKind` | `main`, `side` |
| `GoalStatus` | `open`, `completed`, `failed` |

### Identity rules

- Every identity owned by the game is a `StableId` (UUID): game runs, entities, links, facts, rules, goals, turns and all internal references. New values are generated in application code (`StableId.new()`, `uuid4`) before they reach persistence. Human-readable names live in separate fields (`GameRun.name`, `WorldEntity.label`, `Goal.title`, description fields).
- Identifiers owned by other systems stay plain text: Keycloak `issuer`/`subject`, prompt package id and version, provider and model identifiers, prompt-profile option ids, and the local references inside an LLM candidate.

### Prompt profile

`PromptProfile` fields (all strings; the domain only requires non-empty values):

| Field | Required | Default in the domain | Note |
|---|---|---|---|
| `genre` | yes | – | |
| `tone` | no | `None` | `None` means "no tone selected": nothing is rendered into the prompt. It is **not** the catalog option `balanced`. |
| `prose_style` | yes | – | |
| `perspective` | yes | – | |
| `pacing` | yes | – | |
| `length` | no | `"standard"` | |
| `control_mode` | yes | – | `player` or `director` (checked by the application, see matrix below). |
| `player_agency` | yes | – | Stored always; projected into the prompt only in `player` control mode (`application/llm/prompt_selection.py`). |
| `consequence` | yes | – | |
| `challenge` | yes | – | |
| `content_profile` | yes | – | |

That is ten required keys plus the optional `tone`. `PromptProfile.selections()` returns the ordered tuple of `(category, option_id)` pairs; `tone` is included only when it is not `None`.

Validation is split on purpose:

- Domain (`domain/configuration.py`): structure only (non-empty strings, stripped, unique boundaries).
- Application (`application/game_state/prompt_profile_validation.py`, `PromptProfileValidator`): every option id must exist in the referenced prompt package. There is no silent fallback to a default option; an unknown id is returned as `InvalidPromptSelection(category, option_id)`. `CreateGameRun` and `UpdateGameConfiguration` run this check before writing.
- Defaults (`api/default_configuration.py`, `DEFAULT_GAME_CONFIGURATION`) only pre-fill a request that omits fields. The complete profile is always stored per revision. Defaults: language `de`; genre `dark_fantasy`, tone `None`, prose_style `balanced`, perspective `third_person_limited`, pacing `balanced`, length `standard`, control_mode `player`, player_agency `strict`, consequence `balanced`, challenge `balanced`, content_profile `teen`; package `story.base` version `1`.

Perspective × control mode (enforced by `validate_initialization_choices` in `application/initialization_policy.py`, in this order):

| Check | Rule | Failure kind |
|---|---|---|
| Control mode value | Must be `player` or `director`. | `invalid_configuration` |
| Perspective vs. control | `first_person` and `second_person` are invalid with `director` control. `third_person_limited` and `third_person_omniscient` work with both. | `invalid_configuration` |
| Player seeds | `player` control needs exactly one controllable-character seed. `director` control allows 0..n. | `missing_player_character` |
| Seed names | Unique, compared case-insensitively. | `duplicate_controllable_character` |

Not part of the stored configuration: provider URLs, credentials, raw prompts, running model calls, and the global per-task model choice (that lives in `configs/llm.toml` plus the `llm_task_settings` table, see [persistence.md](./persistence.md)).

### WorldState

`WorldState(entities, links, facts, knowledge, rules, goals, scene_location_ids)` is the structured truth of the game. Inventory and location are derived from links and are not stored twice. Helpers: `entity(id)`, `goal(id)`, `fact(id)`, `inventory(owner_id)` (actors only), `location_of(entity_id)`, `primary_scene_location()`.

| Element | Fields | Invariants |
|---|---|---|
| `WorldEntity` | `id`, `kind`, `label`, `description`, `actor` (`ActorProfile(role)`), `conditions` (`Condition(name, description)`), `aliases` | `actor` is allowed only for `character`, `creature`, `faction`. The kind of an existing entity cannot change (`UpdateEntity`). |
| `EntityLink` | `id`, `source_id`, `target_id`, `kind`, `visibility`, optional `quantity`, `description` | Both ends exist, no self-link. `quantity` ≥ 1 and only for `possesses`/`contains`. Relation rules below. |
| `Fact` | `id`, `statement`, `visibility`, optional `subject_id` | `subject_id` must be an existing entity. `visibility.scope = actor_known` requires `actor_id`; every other scope forbids it. |
| `KnowledgeEntry` | `actor_id`, `fact_id`, `learned_at`, optional `forgotten_at` (both `StorySequence` turn numbers) | Actor must be an actor entity, fact must exist, one entry per (actor, fact), `forgotten_at >= learned_at`. |
| `WorldRule` | `id`, `statement`, `visibility` | Unique id. |
| `Goal` | `id`, `kind`, `title`, `description`, `status`, related entity ids | Related entities exist and are unique. No percentages, milestones or sub-goals. |
| `scene_location_ids` | ordered list of location ids | Unique, existing, kind `location`. The first entry is the primary scene location. |

Relation rules for links (`domain/world.py`):

| Kind | Rule |
|---|---|
| `located_in` | Target must be a `location`. Nesting of locations also uses `located_in`, never `contains`. At most one `located_in` per source entity. |
| `possesses` | Source must be an actor, target must be an `item`. At most one owner per item. |
| `contains` | Must not target a `location`. |
| `member_of` | Target must be a `faction`. |
| `knows` | Both ends must be actors. |
| `allied_with`, `hostile_to`, `related_to` | No kind-specific constraint beyond the general link invariants. |

Every collection requires unique ids. `remove_fact` also removes the knowledge entries that refer to the fact.

#### Scene pointer

`scene_location_ids` states where the narration is looking. `located_in` states where an entity is. They are deliberately independent: in `director` control mode a scene can be narrated in which the controlled character does not appear, so scene locations cannot be derived from `located_in` and must not be removed as redundant state. The initial value comes from the initial world extraction; later turns move it with `SetSceneLocations`.

### StoryState

`StoryState(turns, summaries, current_turn_sequence, initialization)` is the concrete prose chronology.

| Type | Fields | Rules |
|---|---|---|
| `StoryTurn` | `id`, `sequence`, `player_input`, `narration`, `based_on_revision`, `resulting_revision`, `completed_at` | `resulting_revision == based_on_revision + 1`; `completed_at` timezone-aware. A turn exists only once it is complete. |
| `StorySummarySegment` | `from_sequence`, `through_sequence`, `text`, `based_on_revision` | Segments are gapless, chained to the previous segment, never cover future turns, and are never rewritten. |
| `StoryInitialization` | `prompt`, `narration`, `completed_at` | Optional opening prose with its initial prompt. |

`StoryState` invariants: turns are gapless from sequence 1; `current_turn_sequence == len(turns)`; `add_turn` requires the next sequence. Continuation options returned by story and initialization calls are transient UI data and are not part of `StoryState`. Chapters, scenes, story threads and a generic story event do not exist; structured facts (location, possession, an opened door) belong to `WorldState`.

### State changes

An LLM never changes state directly. An unapproved proposed change set is a transient application value. The application validates it and produces an `ApprovedChangeSet(proposal_id, base_revision, changes)` of typed `StateOperation` values:

| Operation | Effect |
|---|---|
| `CreateEntity`, `UpdateEntity` | Add an entity; replace an existing entity by id with a new value (kind is immutable). |
| `AddLink`, `RemoveLink` | Add or remove a link. |
| `AddFact`, `RemoveFact` | Add a fact; remove a fact together with the knowledge entries about it. |
| `GrantKnowledge` | Record that an actor knows a fact. |
| `AddGoal`, `UpdateGoal` | Create or update a goal. |
| `SetSceneLocations` | Replace the scene pointer; an empty tuple clears it. |

There is no operation to remove an entity or a goal, and none to add a rule.

`GameState` entry points:

| Method | Result | Preconditions |
|---|---|---|
| `apply(ApprovedChangeSet)` | Next revision without a story change | Argument must be an `ApprovedChangeSet` (else `ChangeRejectedError`); `changes.base_revision == revision` (else `RevisionConflictError`); each operation must satisfy the `WorldState` invariants (else `ValidationError`/`InvalidReferenceError`) |
| `reconfigure(configuration, base_revision=)` | State-only revision with a new configuration | `base_revision == revision` |
| `complete_turn(changes, turn, new_summary_segment)` | Next revision with world changes, the `StoryTurn` and an optional summary segment | `turn.based_on_revision == revision`, `turn.resulting_revision == revision.next()`, `changes.base_revision == revision` |
| `validate_members(members)` | – | Every controlled entity id of every member is an existing entity with an actor of role `player`. |

## Behavior

- Violations raise `DomainError` subclasses (`domain/errors.py`): `ValidationError` (with subclass `InvalidReferenceError`), `RevisionConflictError`, `ChangeRejectedError` (not an `ApprovedChangeSet`, or an unsupported operation). Messages are German text; callers must match on the type, not on the text.
- A wrong base revision raises `RevisionConflictError`; the application maps it to a run conflict (HTTP 409, see [http-api.md](./http-api.md)).
- The domain accepts only an `ApprovedChangeSet` whose `base_revision` equals the current revision.
- A completed turn forms world changes, `StoryTurn`, the optional new summary segment and the new revision together. The persistence adapter stores them in one transaction ([persistence.md](./persistence.md)).
- Prompt resolution, model call, raw model response, extraction result, proposal and validation result are never part of the persisted domain state.
- Workflow status (for example "initialization running") is not part of `GameRun` or `GameState`.
- Timestamps in `GameRun`, `StoryTurn` and `StoryInitialization` must be timezone-aware.

## Related

- [../architecture.md](../architecture.md): binding layer rules (domain has no outward dependencies).
- [./persistence.md](./persistence.md): how these types are stored per revision.
- [./http-api.md](./http-api.md): transport shapes (`GameDocument`) and error mapping.
- [./application-composition.md](./application-composition.md): the operations that build and approve change sets.
- [../architecture/llm-integration.md](../architecture/llm-integration.md): world extraction, candidate validation, prompt projection.
- Code: [domain package](../../../Backend/src/story_game/domain/), [initialization_policy.py](../../../Backend/src/story_game/application/initialization_policy.py), [prompt_profile_validation.py](../../../Backend/src/story_game/application/game_state/prompt_profile_validation.py), [default_configuration.py](../../../Backend/src/story_game/api/default_configuration.py).

# Interface: HTTP API

## Purpose

REST/JSON API of the backend (FastAPI, prefix `/api/v1`). It covers the full run lifecycle (propose, confirm, fork a playthrough, play turns, load, list, reconfigure), scene images, global world-tracking switch, admin management of prompts and per-task model choice, and frontend diagnostics. Owner: API layer, `Backend/src/story_game/api/` (routers in `api/routers/`, transport models in `api/schemas/`, error mapping in `api/errors.py`). The API only translates transport shapes and calls application operations; it holds no business rules.

## Use

### Conventions

- JSON in and out. All internal ids are UUIDs (`string`, `format: uuid`, canonical lower-case form). A path `run_id` that is not a UUID gives HTTP 422.
- Request models reject unknown fields (`extra="forbid"`) and strip surrounding whitespace from strings.
- Auth: `Authorization: Bearer <Keycloak access token>`. Public endpoints: `GET /health` and `GET /api/v1/prompt-profile`. Everything else needs a valid token; `/api/v1/admin/**` additionally needs the realm role `admin`.
- Interactive contract: `/docs` (Swagger UI), `/openapi.json`, `/redoc`.
- Local addresses: backend `http://localhost:8001` (`BACKEND_HOST_PORT` in `configs/docker/docker.env`) and, through the Compose proxy, `http://backend.storygame.localhost`.

### Endpoints

| Method | Path | Auth | Success | Purpose |
|---|---|---|---|---|
| GET | `/health` | none | 200 `{"status":"ok"}` | Liveness. |
| GET | `/api/v1/prompt-profile` | none | 200 | Prompt catalog of the fixed package `story.base`/`1`; 500 if the package cannot be loaded. |
| GET | `/api/v1/runs` | user | 200 `{runs: RunSummaryModel[]}` | Caller's `draft` templates and `active` playthroughs, ordered by `updated_at` descending. |
| GET | `/api/v1/runs/{run_id}` | member | 200 `GameDocument` | Current state, or a historical one with `?revision=N` (N ≥ 1). |
| POST | `/api/v1/runs/proposals` | user | 201 `RunProposalModel` | Generate an opening proposal. Persists nothing. |
| POST | `/api/v1/runs` | user | 201 `GameDocument` | Confirm a proposal as a `draft` run (revision 1). |
| POST | `/api/v1/runs/{run_id}/playthroughs` | member | 201 `GameDocument` | Fork a `draft` run into a new independent `active` run (new `run_id`, revision 1). |
| PATCH | `/api/v1/runs/{run_id}/configuration` | member | 200 `GameStateModel` | Replace language and the editable prompt profile as a new configuration revision. |
| POST | `/api/v1/runs/{run_id}/turns` | member | 201 `TurnResultModel` | Play one turn in an `active` run. |
| GET | `/api/v1/scene-images/capabilities` | user | 200 | Scene-image feature flag, models and defaults. Always 200. |
| POST | `/api/v1/runs/{run_id}/scene-images` | member | 202 `SceneImageModel` | Start an asynchronous scene image for the latest turn. |
| GET | `/api/v1/runs/{run_id}/scene-images` | member | 200 `{images: SceneImageModel[]}` | List images of the run, newest first. |
| GET | `/api/v1/runs/{run_id}/scene-images/{image_id}` | member | 200 `SceneImageModel` | One image (status, prompts, options). |
| GET | `/api/v1/runs/{run_id}/scene-images/{image_id}/content` | member | 200 bytes | Image bytes with the stored content type; only for `ready` images, otherwise 404. |
| GET | `/api/v1/settings/world-tracking` | user | 200 `{enabled}` | Whether world tracking is on. |
| GET / PUT | `/api/v1/admin/settings/world-tracking` | admin | 200 `{enabled, updated_at, updated_by}` | Read / switch world tracking for all games. PUT body `{enabled: bool}`. |
| GET / PUT / POST | `/api/v1/admin/prompts`, `…/history`, `…/reset`, `…/options`, `…/options/**` | admin | see [Admin: prompts](#admin-prompts) | Manage system prompts and prompt options. |
| GET / PUT / POST | `/api/v1/admin/models`, `…/history`, `…/reset` | admin | see [Admin: models](#admin-models) | Manage the model choice per task. |
| POST | `/api/v1/diagnostics/frontend-errors` | user | 204 | Report a frontend tooling error. |

"member" means: valid token and the caller `(issuer, subject)` is a member of the run (checked by the application operation `LoadGame`; otherwise 403 `not_a_run_member`). `GET /api/v1/runs` filters by `(issuer, subject)` directly.

### Run lifecycle

```text
POST /runs/proposals  ->  proposal (transient, 30 min)
POST /runs            ->  draft run, revision 1
POST /runs/{id}/playthroughs -> active run, revision 1
POST /runs/{id}/turns ->  revision +1 per turn
PATCH /runs/{id}/configuration -> revision +1 without a turn
```

#### `POST /api/v1/runs/proposals`

Request (`ProposeRunRequestModel`):

| Field | Type | Rule |
|---|---|---|
| `initial_prompt` | string | min length 1 |
| `control_mode` | `"player"` \| `"director"` | required |
| `controllable_characters` | `[{name, description=""}]` | `player` mode: exactly one entry; `director` mode: 0..n. Names unique (case-insensitive). |
| `language` | string, optional | default `de` |
| `prompt_profile` | object, optional | see below; omitted means the server default profile |

`prompt_profile` (`EditablePromptProfileModel`) contains ten required keys plus the optional `tone`; there is no `control_mode` key (it is the top-level field):

```json
{
  "genre": "dark_fantasy",
  "tone": "dark",
  "prose_style": "balanced",
  "perspective": "third_person_limited",
  "pacing": "balanced",
  "length": "standard",
  "player_agency": "strict",
  "consequence": "balanced",
  "challenge": "balanced",
  "content_profile": "teen"
}
```

Omitting `tone` (or sending no profile at all) selects no tone: no tone text is rendered into the prompt. Option ids are validated against the prompt package before any model call (422 `invalid_prompt_selection`). `narrative_boundaries`, prompt package id and version are server-determined (`api/default_configuration.py`). Combination rules (`first_person`/`second_person` are invalid with `director`; `player` needs exactly one seed) are in [domain-model.md](./domain-model.md#prompt-profile).

Response (`RunProposalModel`): `proposal_id`, `continuation {narration, options[]}`, `world` (`WorldStateModel`), `suggested_player_entity_ids` (display hint only), `suggested_title`. Every proposed character is a neutral entity; nobody is player-controlled yet. `continuation.options` are transient, non-binding suggestions and are never stored.

#### `POST /api/v1/runs`

Request (`ConfirmRunProposalRequestModel`): `proposal_id`, optional `run_name` (blank/omitted falls back to `suggested_title`), `character_decisions: [{entity_id, role: "player"|"npc", removed=false}]`, `item_decisions: [{entity_id, removed=false}]`.

- Creates a `draft` `GameRun` at revision 1; the caller becomes `owner`. Characters decided as `player` become the member's controlled entities (`player` mode requires exactly one).
- Removing an entity also drops its links and facts.
- A proposal can be confirmed only by the identity that created it, once. Unknown, expired and foreign proposals all give the same 404 `not_found`.

#### `POST /api/v1/runs/{run_id}/playthroughs`

No body. Source must be `draft` (otherwise 409 `playthrough_source_not_draft`); the caller must be a member of the source (otherwise 403 `not_a_run_member`). The source run stays unchanged and can be forked any number of times.

#### `POST /api/v1/runs/{run_id}/turns`

Request: `{player_input}` (min length 1). The run must be `active` (otherwise 409 `run_not_active`). Response `TurnResultModel`: `state` (`GameStateModel`), `continuation {narration, options[]}` (transient), `proposed_change_count`, `summary_failed`, `summary_failure_message`. A failed summary does not fail the turn (`summary_failed: true`).

#### `PATCH /api/v1/runs/{run_id}/configuration`

Request: `{base_revision (≥1), language, prompt_profile}`; the profile is complete, not a partial patch. The server keeps the run's current `control_mode`, `narrative_boundaries`, prompt package id and version; they cannot be changed here. Validates membership, base revision and option ids; returns the new `GameStateModel`.

### Transport documents

`GameDocument = {schema_version: 1, game_run, game_state}`.

- `game_run` (`GameRunModel`): `id`, `name`, `status`, `current_revision`, `members[{issuer, subject, game_role, controlled_entity_ids[]}]`, `created_at`, `updated_at`.
- `game_state` (`GameStateModel`): `run_id`, `revision`, `configuration` (language, full prompt profile, `narrative_boundaries`, `prompt_package_id`, `prompt_package_version`), `world` (`entities`, `links`, `facts`, `knowledge`, `rules`, `goals`, `scene_location_ids`), `story` (`turns`, `summaries`, `current_turn_sequence`, optional `initialization`).
- `schema_version` increases only on breaking changes (removed or renamed field, changed type or meaning). Adding a field with a default is additive.
- Semantics of the contained fields: [domain-model.md](./domain-model.md).

`RunSummaryModel`: `id`, `name`, `status`, `current_revision`, `game_role`, `updated_at` (no world snapshot).

### Prompt catalog

`GET /api/v1/prompt-profile` returns `{package_id, package_version, categories[{id, default_option_id, options[{id, description}]}]}`. Categories: `genre`, `tone`, `prose_style`, `perspective`, `pacing`, `length`, `control_mode`, `player_agency`, `consequence`, `challenge`, `extraction`, `content_profile`. `control_mode` and `extraction` are listed for UI construction but are not keys of the editable `prompt_profile`: `control_mode` is a top-level field of the proposal request, `extraction` is not part of the stored configuration. The catalog default of `tone` is `balanced`, but an unset tone is stored as `null` and is not that option.

### Scene images

A switchable feature (`[scene_image]` in `Backend/configs/app.toml`).

- `GET /api/v1/scene-images/capabilities` (always 200): `enabled`, `models[{name}]`, `refine_models[{name}]`, `model_listing_failed`, `default_model`, `default_refine`, `default_refine_model`, `default_refine_strength`, `min_refine_strength`, `max_refine_strength`, `turn_window`. When disabled: `enabled: false` and defaults/`null` for the rest. If the image provider is unreachable: `enabled: true`, empty model lists, `model_listing_failed: true`. When disabled, all other scene-image endpoints answer 409 `scene_image_disabled`.
- `POST /api/v1/runs/{run_id}/scene-images`: optional body `{model?, refine?, refine_strength?}` (missing fields use the configured defaults). Responds immediately with 202 and a `pending` image; rendering runs as a background task. Poll `GET …/{image_id}` or the list until `status` is `ready` or `failed` (`error_message` is set on failure). No automatic retry; a new POST starts a new generation.
- `SceneImageModel`: `image_id`, `run_id`, `turn_sequence`, `status` (`pending`|`ready`|`failed`), `model`, `refine`, `refine_model`, `refine_strength`, `width`, `height`, `seed`, `prompt`, `compact_prompt`, `error_message`, `created_at`, `completed_at`.
- An image belongs to the latest turn at request time (`turn_sequence`; `0` = opening only). A run without opening and turn gives 422 `scene_image_no_story`.
- If a `pending` image for the same turn exists and is younger than the configured active window, the POST returns it instead of starting a second paid generation; older pending images count as orphaned and do not block.
- Images are not part of `GameState`; there is no revision check.
- `…/content` requires the bearer token, so browsers must fetch the bytes with the token and use an object URL.

### Admin (role `admin`)

The role is read from the Keycloak claim `realm_access.roles`. 401 without a token, 403 `forbidden` without the role. `created_by` is the token's `preferred_username`, falling back to the subject.

#### Admin: prompts

Package is fixed to `story.base`/`1`. Changes take effect on the next story request.

| Call | Body / query | Result |
|---|---|---|
| `GET /api/v1/admin/prompts` | – | `{package_id, package_version, entries[]}` |
| `GET /api/v1/admin/prompts/history` | `?kind=&key=` | `{versions[]}`, newest first; 404 for an unknown entry |
| `PUT /api/v1/admin/prompts` | `{kind, key, text}` | New active version; unchanged text creates nothing. Empty text or more than 20000 characters: 422 `invalid_prompt_text`; unknown entry: 404 |
| `POST /api/v1/admin/prompts/reset` | `{kind?, key?}` | `{kind, key}` resets one entry, `{kind}` all of that kind, `{}` all; each deviating entry gets a new `toml_reset` version. `key` without `kind`: 422 |
| `POST /api/v1/admin/prompts/options` | `{category, option_id, text}` | 201, new custom option. Only categories `genre`, `tone`, `prose_style`; `option_id` matches `^[a-z][a-z0-9_]{1,39}$`. Errors: 422 `invalid_prompt_option`, 422 `invalid_prompt_text`, 409 `prompt_option_exists` (also for ids in the trash). Never becomes a default option. |
| `DELETE /api/v1/admin/prompts/options` | `?category=&option_id=` | 204, archive. 409 `prompt_option_not_removable` (shipped option), 409 `prompt_option_in_use` (selected by a stored game configuration), 404 unknown |
| `GET /api/v1/admin/prompts/options/archived` | – | `{versions[]}` (newest version per option) |
| `POST /api/v1/admin/prompts/options/restore` | `{category, option_id}` | 204; 404 if not archived/unknown |
| `DELETE /api/v1/admin/prompts/options/archived` | `?category=&option_id=` | 204, purge including history. 409 `prompt_option_not_archived` for an active option, 404 unknown |
| `POST /api/v1/admin/prompts/options/removal` | `{mode: "archive"\|"purge", options?: [{category, option_id}]}` | `{outcomes: [{key, status, message}]}`; `status` is `done`, `in_use`, `protected`, `not_archived` or `not_found`. Without `options`, `archive` targets all custom options and `purge` everything in the trash. One blocked option does not stop the others; not one transaction; safe to repeat. |

Entry fields: `version_id`, `kind` (`task`|`option`|`directive`), `key` (task or directive id; `<category>/<option>` for options), `text`, `is_default`, `task_ids`, `source` (`toml_seed`|`ui`|`toml_reset`), `created_at`, `created_by`, `is_active`, `is_modified` (active version is a UI edit), `is_custom` (option created in the UI, no TOML original).

#### Admin: models

Tasks: `story`, `extraction`, `summary`, `scene_image`. A change applies from the next model call without restart.

| Call | Body / query | Result |
|---|---|---|
| `GET /api/v1/admin/models` | – | `{settings[], candidates[]}`. `settings`: active version per task. `candidates`: models from `configs/llm.toml` per task (`task`, `model_ref`, `provider_id`, `model_id`). |
| `GET /api/v1/admin/models/history` | `?task=` | `{versions[]}`, newest first |
| `PUT /api/v1/admin/models` | `{task, model_ref, temperature?, max_output_tokens?}` | New active version; unchanged values create nothing. Model not a candidate of the task: 422 `invalid_model_selection`. Temperature must be finite and in 0..2, tokens > 0: else 422 `invalid_generation_options`. Missing options mean provider default. |
| `POST /api/v1/admin/models/reset` | `{task?}` | Re-applies the `llm.toml` defaults for one or all deviating tasks as `toml_reset` versions. |

Setting fields: `version_id`, `task`, `model_ref`, `temperature`, `max_output_tokens`, `source`, `created_at`, `created_by`, `is_active`, `is_modified`. Providers, URLs, secrets and the model catalog stay in `configs/llm.toml` / `configs/llm.secrets.toml` and are not editable through the API.

### Frontend diagnostics

`POST /api/v1/diagnostics/frontend-errors` (204) records non-401 frontend tooling errors (network, JSON parse, synchronous tooling errors). Field limits: `source` ≤ 100, `message` ≤ 2000, `url` ≤ 500, `user_agent` ≤ 300; violations give 400 `invalid_frontend_error_report`. 401 responses are not reported through this endpoint.

### Authentication and configuration

`get_current_initiator` (`api/dependencies.py`) verifies the bearer token with `KeycloakTokenVerifier` (`api/auth/token_verifier.py`: RS256 via JWKS, checks issuer, expiry and, when configured, audience) and derives `RunInitiator(issuer, subject)`. `require_admin` additionally requires the role `admin`.

| Environment variable (`api/config.py`) | Default / meaning |
|---|---|
| `STORY_GAME_KEYCLOAK_ISSUER` | `http://localhost:8082/realms/story-game`; trusted realm URL (Compose uses `http://auth.storygame.localhost/realms/story-game`) |
| `STORY_GAME_KEYCLOAK_AUDIENCE` | `story-game-frontend`; empty disables the audience check |
| `STORY_GAME_KEYCLOAK_JWKS_URI` | optional; default `<issuer>/protocol/openid-connect/certs` (Compose sets the in-network Keycloak URL) |
| `STORY_GAME_POSTGRES_DSN` | `postgresql://story_game:story_game_dev@localhost:5433/story_game` |
| `STORY_GAME_AUTO_MIGRATE` | default `true`; apply SQL migrations at startup |
| `STORY_GAME_PROMPT_ROOT` | `prompts`; TOML prompt packages used as first-start seed |
| `STORY_GAME_CONFIG_PATH` | `configs/app.toml` |
| `STORY_GAME_LLM_CONFIG_PATH` | `configs/llm.toml` |
| `STORY_GAME_CORS_ALLOWED_ORIGINS` | comma-separated; default `http://localhost:5173`; Compose sets `http://storygame.localhost` |
| `STORY_GAME_API_TITLE`, `STORY_GAME_API_VERSION`, `STORY_GAME_DEV_ISSUER`, `STORY_GAME_DEV_SUBJECT` | development/test only |

## Behavior

### Error envelope

Every handled error has the form `{"error": <code>, "detail": <text>, ...}` (`api/errors.py`). `detail` is German text intended for display; callers must branch on `error` and the HTTP status. Request-body and path validation errors raised by FastAPI itself return 422 with FastAPI's default `{"detail": [...]}` shape, not this envelope.

| HTTP | `error` | Cause |
|---|---|---|
| 400 | `invalid_frontend_error_report` | Report violates the field limits |
| 401 | `unauthorized` | Missing, malformed, expired or invalid token |
| 403 | `forbidden` | Admin endpoint without the role `admin` |
| 403 | `not_a_run_member` | Caller is not a member of the run |
| 404 | `not_found` | Unknown run, revision, proposal (also expired or foreign), image, prompt entry, model setting |
| 409 | `revision_conflict` | Base revision is stale (also domain `RevisionConflictError`) |
| 409 | `run_not_active` | Turn against a `draft` run |
| 409 | `playthrough_source_not_draft` | Fork from a run that is not `draft` |
| 409 | `scene_image_disabled` | Scene images switched off |
| 409 | `prompt_option_exists`, `prompt_option_not_removable`, `prompt_option_not_archived`, `prompt_option_in_use` | Prompt option lifecycle conflicts |
| 422 | `domain_validation_failed` | Domain or state rejection |
| 422 | `invalid_prompt_selection` | Option id unknown for its category (extra keys `category`, `option_id`) |
| 422 | `invalid_prompt_package_reference` | Referenced prompt package does not exist |
| 422 | `invalid_player_character_seed` | Missing or duplicate controllable-character seed |
| 422 | `scene_image_no_story`, `scene_image_invalid_options` | Scene-image request not satisfiable |
| 422 | `invalid_prompt_text`, `invalid_prompt_option`, `invalid_model_selection`, `invalid_generation_options` | Admin input rejected |
| 500 | `story_configuration_invalid` | Server-side configuration for story generation is invalid |
| 500 | `story_initialization_inconsistent`, `story_turn_inconsistent` | Model output passed parsing but is internally inconsistent |
| 500 | `prompt_package_configuration_invalid`, `scene_image_configuration_invalid`, `prompt_source_unavailable`, `model_catalog_unavailable`, `persistence_consistency_failed` | Server-side configuration or stored-data problem |
| 502 | `story_model_unavailable` | Model unreachable or unusable output |
| 502 | `scene_image_failed` | Prompt or render step failed |
| 503 | `persistence_unavailable` | Store unreachable (also for prompt, model-setting and world-tracking stores) |
| any | `http_error` | Other `HTTPException` |

### Initialization failures (proposal creation)

The application returns an initialization error with a `kind` and a `stage` (`story_generation` or `world_extraction`, defined in `application/initialization_errors.py`). The stage is for diagnostics only and is not exposed in HTTP.

| Kind | Meaning | HTTP | `error` |
|---|---|---|---|
| `invalid_configuration` | Invalid control mode, or `first_person`/`second_person` with `director` | 500 | `story_configuration_invalid` |
| `missing_player_character` | `player` mode without exactly one controllable-character seed | 422 | `invalid_player_character_seed` |
| `duplicate_controllable_character` | Two seeds with the same name (case-insensitive) | 422 | `invalid_player_character_seed` |
| `model_failure` | Model call failed (unreachable, timeout, authentication, …) | 502 | `story_model_unavailable` |
| `invalid_model_response` | Model answered with unusable or unparsable output | 502 | `story_model_unavailable` |
| `invalid_candidate_reference` | Extraction refers to a local candidate reference that does not exist | 500 | `story_initialization_inconsistent` |
| `domain_rejection` | The domain rejected the extracted world | 422 | `domain_validation_failed` |

### Turn failures

| Kind / error | HTTP | `error` |
|---|---|---|
| `invalid_configuration` | 500 | `story_configuration_invalid` |
| `model_failure`, `invalid_model_response` | 502 | `story_model_unavailable` |
| `invalid_candidate_reference` | 500 | `story_turn_inconsistent` |
| `domain_rejection` | 422 | `domain_validation_failed` |
| `unknown_member` | 403 | `not_a_run_member` |
| `run_not_active` | 409 | `run_not_active` |
| context selection error | 500 | `story_turn_inconsistent` |

### Scene-image failures

| Kind | HTTP | `error` |
|---|---|---|
| `disabled` | 409 | `scene_image_disabled` |
| `no_story` | 422 | `scene_image_no_story` |
| `not_found` | 404 | `not_found` |
| `invalid_options` | 422 | `scene_image_invalid_options` |
| `access_denied` | 403 | `not_a_run_member` |
| `store_unavailable` | 503 | `persistence_unavailable` |
| `prompt_failed`, `render_failed` | 502 | `scene_image_failed` |
| `configuration` | 500 | `scene_image_configuration_invalid` |

### Side effects and ordering

- Proposals are held in memory (`InMemoryProposalStore`, 30-minute TTL, `infrastructure/persistence/in_memory_proposal_store.py`) and owner-bound. They are lost on restart and not shared between backend instances. Nothing is persisted before `POST /api/v1/runs`.
- With world tracking switched off, a proposal contains only the seed characters as neutral entities (no model-extracted world) and turns skip world extraction; the story text is still generated. The switch is global (`GET`/`PUT …/settings/world-tracking`) and is read per decision.
- A turn runs all model calls first and writes once at the end; a failed turn leaves no trace ([persistence.md](./persistence.md)). Every successful turn creates exactly one new revision.
- `PATCH …/configuration` and turns use optimistic concurrency through the current revision; a stale revision gives 409 `revision_conflict`.
- Authorization is enforced in the application (`LoadGame` membership check), not only by the router dependencies.

## Related

- [../architecture.md](../architecture.md): layer rules; the API depends on the application only through contracts.
- [../architecture/llm-integration.md](../architecture/llm-integration.md): story/extraction/summary calls, world tracking.
- [./domain-model.md](./domain-model.md): meaning of the state fields and the prompt-profile rules.
- [./persistence.md](./persistence.md): storage, atomic turn commit, prompt and model-setting versioning.
- [./application-composition.md](./application-composition.md): how the operations behind the endpoints are composed.
- Code: [api package](../../../Backend/src/story_game/api/), [errors.py](../../../Backend/src/story_game/api/errors.py), [routers](../../../Backend/src/story_game/api/routers/), [schemas](../../../Backend/src/story_game/api/schemas/), [initialization_errors.py](../../../Backend/src/story_game/application/initialization_errors.py).

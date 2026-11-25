# Interface: LLM integration

## Purpose

The application owns every model-facing contract: ports, request and result types, and the provider-independent error. Infrastructure adapters implement the ports; no provider type crosses the boundary. Application code lives in `Backend/src/story_game/application/llm/`, adapters and configuration loading in `Backend/src/story_game/infrastructure/llm/` and `Backend/src/story_game/infrastructure/configuration/`, and the wiring in `Backend/src/story_game/api/app.py`.

## Use

### Ports

All ports are `Protocol`s in `Backend/src/story_game/application/llm/ports.py`. Each method takes one `LLMGenerationCall[Request]` (`model_selection`, `generation_options`, `request`) and returns `OperationResult[Success, LLMError]`; callers never see exceptions for expected model failures.

| Port (method) | Request | Success type | Defined in |
|---|---|---|---|
| `StoryGenerationPort.generate` | `StoryGenerationRequest` (`system_prompts`, `configuration`, `world_state`, `story_state`, `user_prompt`) | `StoryGenerationData` (`text`, `continuation_options`, at least one option) | `Backend/src/story_game/application/llm/contracts.py` |
| `StoryInitializationPort.generate` | `StoryInitializationRequest` (`system_prompts`, `configuration`, `initial_prompt`, `controllable_characters`) | `InitialStoryText` (`text`, `continuation_options`) | `Backend/src/story_game/application/llm/contracts.py` |
| `InitialWorldExtractionPort.extract` | `InitialWorldExtractionRequest` (`system_prompts`, `opening_narration`, `language`, `perspective`, `control_mode`) | `WorldInitializationCandidate` | `Backend/src/story_game/application/llm/initial_extraction.py` |
| `TurnExtractionPort.extract` | `TurnExtractionRequest` (`system_prompts`, `narration`, `world_state`, `language`, `with_evidence`) | `TurnChangeCandidate` | `Backend/src/story_game/application/llm/turn_extraction.py` |
| `StorySummaryPort.summarize` | `StorySummaryRequest` (`system_prompts`, `turns` as `SummarizedTurn`, `language`) | `StorySummaryText` | `Backend/src/story_game/application/llm/summary.py` |
| `SceneImagePromptPort.write` | `SceneImagePromptRequest` (`system_prompts`, `turns`, `language`) | `SceneImagePromptText` | `Backend/src/story_game/application/llm/scene_image_prompt.py` |
| `CompactImagePromptPort.compact` | `CompactImagePromptRequest` (`system_prompts`, `prompt`, `max_words`) | `SceneImagePromptText` | `Backend/src/story_game/application/llm/scene_image_prompt.py` |

Request and result types are frozen dataclasses that normalize and validate in `__post_init__` (stripped text, at least one system prompt, no empty results). Further ports in the same module: `GenerationConfigurationResolver.resolve(task)` returns the model and options for a `GenerationTask` (`story`, `extraction`, `summary`, `scene_image`); `PromptPackageCatalog.load(package_id, version)` returns a `PromptPackage`; `ModelSelectionResolver.resolve(logical_model_id)` returns a `ModelSelection` (`provider_id`, `model_id`). `GenerationOptions` carries `temperature` and `max_output_tokens`.

### Initial extraction schema

`WorldInitializationCandidate` (`entities`, `links`, `facts`, `scene_refs`, `suggested_title`) is the model's untrusted proposal for the first world state:

- `CandidateEntity`: `local_ref`, `kind`, `label`, `description`, `conditions` (`CandidateCondition` with `name`, `description`), `aliases`, optional `evidence`.
- `CandidateLink`: `source_ref`, `target_ref`, `kind`, `quantity` (positive or none), `description`, optional `evidence`.
- `CandidateFact`: `statement`, optional `subject_ref`, optional `evidence`.
- `scene_refs`: local references to the locations the opening is set in, primary first; the application rejects references that are unknown, duplicated, or not locations. `suggested_title` is a display-only title suggestion that the application may replace; it can be blank.

The request carries the opening narration but no player seed. The wire schema is `world_initialization` (strict) in `Backend/src/story_game/infrastructure/llm/openai_compatible/initial_extraction_wire.py` and has no evidence field. The operation `ExtractInitialWorldState` (`Backend/src/story_game/application/initial_world_extraction.py`) turns every extracted character into an `ActorProfile` with `ActorRole.NEUTRAL`; the player role is assigned only when the proposal is confirmed.

### Turn extraction schema

`TurnChangeCandidate` is the untrusted delta for one turn: `new_entities`, `entity_updates`, `added_links`, `removed_links`, `added_facts`, `removed_facts`, `scene`.

- Existing objects are addressed by handles from the projected world state, prefixed `e` (entity), `l` (link), `f` (fact), for example `e1`, `l3`, `f2` (`extraction_projection` in `Backend/src/story_game/application/story_prompt_sections.py`). Removals are `CandidateRemoval(handle, evidence)`; updates are `CandidateEntityUpdate(handle, description, conditions, aliases, evidence)` where `None` means unchanged.
- New objects get a short `local_ref` chosen by the model; links and facts in the same candidate refer to them by that `local_ref`.
- `scene` is a tuple of `CandidateSceneReference(reference, evidence)`, most relevant first, naming where the narration looks after the turn.
- `TurnExtractionRequest.with_evidence` selects one of two wire schemas named `turn_changes` in `Backend/src/story_game/infrastructure/llm/openai_compatible/turn_extraction_wire.py`: with evidence every change carries a verbatim quote from the narration, without it the field is absent. Evidence is diagnostic only; it stays in `ProposedChange.evidence` and is never persisted.
- On the wire the removal lists are named `removed_links` and `removed_facts` (each item `{handle}` or `{handle, evidence}`); the `worldstate_extraction` task text uses the same names. A test checks that every snake_case name in an extraction task text exists in the response schema of that task (`Backend/tests/infrastructure/llm/test_prompt_packages.py`).
- The user message has the sections `[language]`, `[world_state]`, `[narration]`; the system message is the joined `system_prompts`. The request contains no player input.

### Prompt packages

A prompt package is a versioned TOML file at `Backend/prompts/<package-id>/<version>.toml` (shipped: `Backend/prompts/story.base/1.toml`):

- `[package]` with `id` and `version`.
- `[[tasks]]` with `id` and `text`. Exactly seven task ids: `story_initialization`, `story_generation`, `story_summary`, `scene_image_prompt`, `scene_image_prompt_compact`, `worldstate_initialization`, `worldstate_extraction`.
- `[[categories]]` with `id` and `default`, each with `[[categories.options]]` (`id`, `description`). Exactly twelve categories: `genre`, `tone`, `prose_style`, `perspective`, `pacing`, `length`, `control_mode`, `player_agency`, `consequence`, `challenge`, `extraction`, `content_profile`. The option description is the text injected into the prompt when the option is selected.
- `[[directives]]` with `id`, `text`, `selectable = false`, and `tasks` (the task ids the directive applies to): `narrative_boundaries` (story generation and initialization), `npc_agency` (story generation), `genre_plot_variation` (story generation and initialization).

`FilePromptPackageCatalog` (`Backend/src/story_game/infrastructure/llm/prompts.py`) fails closed with `InvalidPromptPackageError` on: unreadable file or invalid TOML; unknown or missing keys; an id or version that differs from the requested reference; duplicate ids; a task set other than the seven ids or a category set other than the twelve; empty options or a default that is not one of the options; `selectable` other than the literal `false`; an empty or unknown task id in a directive; empty or non-text values; and path components (`/`, `\`, `..`, `.`, NUL, empty) in the package id or version. A missing file raises `PromptPackageNotFoundError`, which is distinct from `InvalidPromptPackageError` (both in `Backend/src/story_game/application/llm/prompts.py`).

The catalog ports are owned by the application (`PromptPackageCatalog` in `Backend/src/story_game/application/llm/ports.py`; `PromptPackageSource`, `PromptVersionReader`, `PromptVersionWriter` in `Backend/src/story_game/application/prompt_management/ports.py`). The `*PromptSelectionResolver` classes in `Backend/src/story_game/application/llm/prompt_selection.py` turn a stored configuration into the task's system prompts.

At runtime the prompts come from the database, not from the files:

- `DbPromptPackageCatalog` (`Backend/src/story_game/infrastructure/persistence/postgres/prompt_store.py`) reads the append-only table `system_prompts` (migration `007_system_prompts.sql`).
- At startup `SeedPromptPackages` loads the files through `FilePromptPackageCatalog` and writes a package only when the database holds no version of it. A restart never overwrites an admin's edits; a seed failure is fatal.
- The files stay the originals for `ResetPromptText`, for archive protection of shipped options, and for telling shipped options from custom ones.

### llm.toml

`Backend/configs/llm.toml` is loaded by `TomlLlmConfigurationLoader` (`Backend/src/story_game/infrastructure/configuration/llm.py`) into `LlmConfiguration`:

- `[providers.<id>]` with `base_url` and `timeout_seconds` (shipped: `lmstudio`, `groq`, `gemini`).
- `[task_models]` with exactly `story`, `extraction`, `summary`, `scene_image`; each value is the logical id of a catalog model.
- `[generation_options.<task>]` with `temperature` and optional `max_output_tokens`.
- `[[models]]` catalog entries with `id`, `task`, `provider_id`, `model_id`. Duplicate ids are rejected, the provider must be configured, and a model selected for a task must belong to that task. `LlmConfiguration.resolve(logical_id)` returns the `ModelSelection`.

A task selects its model through its logical id in `[task_models]`. At runtime the effective model and options per task come from the database table `llm_task_settings` (migration `008_llm_task_settings.sql`), resolved by `ManagedGenerationConfigurationResolver` (`Backend/src/story_game/application/model_settings/resolver.py`); `TomlModelSettingsSource` (`Backend/src/story_game/infrastructure/configuration/model_settings.py`) exposes `llm.toml` as the model catalog and as the originals, and `SeedModelSettings` writes the tasks that have no database row at startup. The admin screen changes the stored settings, not the file.

### Providers and secrets

All providers speak the OpenAI-compatible chat protocol through `OpenAiCompatibleClient` (`Backend/src/story_game/infrastructure/llm/openai_compatible/client.py`) and the per-task wire modules in the same package. Provider adapters exist for `lmstudio`, `groq`, and `gemini` under `Backend/src/story_game/infrastructure/llm/<provider>/` (story generation, initialization, initial extraction, turn extraction, summary, and `settings.py`). Groq (default `https://api.groq.com/openai/v1`) and Gemini (default `https://generativelanguage.googleapis.com/v1beta/openai`) require an API key and raise `ValueError` without one; LM Studio needs none. Scene-image prompt writing uses one adapter pair for all providers (`OpenAiCompatibleSceneImagePromptAdapter`, `OpenAiCompatibleCompactImagePromptAdapter`). The `Routing*Adapter` classes in `Backend/src/story_game/infrastructure/llm/provider_router.py` pick the provider adapter per call from `call.model_selection.provider_id` and return `LLMError(CONFIGURATION)` for an unknown provider.

Secrets are never part of tracked files and are never logged:

- Provider API keys come from the gitignored `Backend/configs/llm.secrets.toml` (`[providers.groq] api_key`, `[providers.gemini] api_key`; template `Backend/configs/llm.secrets.toml.example`), merged in on every load.
- The scene-image provider credentials come from the gitignored `Backend/configs/scene_image.secrets.toml` (template `Backend/configs/scene_image.secrets.toml.example`) through `load_modal_credentials` in `Backend/src/story_game/infrastructure/configuration/scene_image.py`.

`Backend/configs/app.toml` holds the non-secret application configuration: `[logging]`, `[story_summary]` (`interval`, `context_segment_count`), `[scene_image]`, and `[scene_image.modal]`.

## Behavior

### Error family

Every expected model failure is an `LLMError` (`Backend/src/story_game/application/llm/contracts.py`) with a `kind: LLMErrorKind`, a non-empty `message`, and `retryable` (default `False`). It carries no provider objects, exceptions, or raw responses.

| `LLMErrorKind` | Meaning | `retryable` |
|---|---|---|
| `UNAVAILABLE` | Network failure or HTTP status 500 and above | `True` |
| `TIMEOUT` | Transport timeout or HTTP 408/504 | `True` |
| `RATE_LIMITED` | HTTP 429 | `True` |
| `AUTHENTICATION` | HTTP 401/403, or a missing API key | `False` |
| `MODEL_UNAVAILABLE` | HTTP 404 | `False` |
| `CONTEXT_LIMIT` | HTTP 413 | `False` |
| `INVALID_REQUEST` | Other 4xx | `False` |
| `INCOMPLETE` | The model stopped because it hit the output limit (`finish_reason == "length"`) | `False` |
| `INVALID_RESPONSE` | The provider response is not valid JSON, lacks the expected structure or text content, is empty, or the structured output fails validation in the provider adapter | `False` |
| `CONFIGURATION` | Unknown provider or unusable generation configuration; raised by routers, adapters, and the resolver, never by the transport | `False` |

`Backend/src/story_game/infrastructure/llm/openai_compatible/error_mapping.py` maps the transport error to the `LLMError` of the same kind and copies `retryable`. The flag is informational: `StructlogDiagnosticsLog` logs retryable errors as warnings and others as errors, and nothing retries automatically.

### Story-turn pipeline

`PlayStoryTurn.apply` (`Backend/src/story_game/application/play_story_turn.py`) runs these steps in order:

1. Load the game and check membership, then require the run to be active (otherwise `RUN_NOT_ACTIVE`). The controlled entity ids may be empty for director control.
2. `SelectStoryTurnContext` (`Backend/src/story_game/application/story_turn_context.py`) selects the context deterministically, without a model call. The defaults of `SelectionBudget` (`Backend/src/story_game/application/story_turn_context_models.py`) are 15 entities, 20 facts, 10 goals, 2 recent turns, and 3 summary segments; the composition root overrides only the summary segment count from `context_segment_count` in `app.toml`.
3. `GenerateStory` (`Backend/src/story_game/application/generate_story.py`) calls `StoryGenerationPort`.
4. If world tracking is enabled, `ExtractStoryTurnChanges` (`Backend/src/story_game/application/extract_story_turn_changes.py`) calls `TurnExtractionPort` with the new narration and the projected world state only; the player's input is not sent to extraction. `ApproveStoryTurnChanges` (`Backend/src/story_game/application/approve_story_turn_changes.py`) validates the candidate and builds the approved change set. With world tracking disabled the change set is empty and no extraction call is made.
5. When `(current_turn_sequence + 1) % summary_interval == 0`, `StorySummaryPort` condenses the last `summary_interval` turns including the new one. `summary_interval` defaults to 4 in `PlayStoryTurn` and to 4 in `StorySummarySettings` (`Backend/src/story_game/infrastructure/configuration/app_config.py`); the shipped `app.toml` sets 1. A summary failure does not abort the turn: it is reported as `summary_failure` on `PlayedStoryTurn` and the turn is committed without a segment.
6. `CommitCompletedTurn` (`Backend/src/story_game/application/game_state/commit_completed_turn.py`) writes turn, approved changes, and summary segment in one revision-checked atomic transaction. Both model calls happen outside that transaction.

Approval is item-wise for unknown references: an item whose handle is unknown is dropped and reported (`ProposalItemDropped`). An unknown or duplicate `local_ref` fails the whole turn as `INVALID_CANDIDATE_REFERENCE`; a `DomainError` while applying fails it as `DOMAIN_REJECTION`. Changes are applied in the order new entities, updates, removed links, added links, removed facts, added facts, scene locations. The proposal itself is never persisted.

## Related

- [LLM integration architecture rules](../architecture/llm-integration.md)
- [Catalog: Application](./catalog-application.md)
- [Catalog: Infrastructure](./catalog-infrastructure.md)
- [Interface: Domain model](./domain-model.md)

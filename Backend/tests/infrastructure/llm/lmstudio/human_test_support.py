"""Implementation for the human-inspection test bundle.

This module intentionally has no ``test_`` prefix so pytest never tries to
collect it directly — only ``test_human_test_starter.py`` is collected. It
holds everything the collector classes there delegate to: real prompt
building against production prompt packages, a printing wrapper around the
real LM Studio client (so a human reading ``pytest -s`` output sees the exact
prompt and the raw model response), and small non-network recording doubles
that let the prompt-only checkpoint run without a live server.

Nothing here is asserted against; the point is to look, not to verify.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from story_game.infrastructure.persistence.postgres import PostgresConnectionFactory

from story_game.application import (
    ApproveStoryTurnChanges,
    CharacterDecision,
    ConfirmGameRunProposal,
    ConfirmGameRunProposalRequest,
    ExtractedTurnChanges,
    ExtractInitialWorldState,
    ExtractStoryTurnChanges,
    ExtractStoryTurnChangesRequest,
    GenerateStory,
    GenerateStoryRequest,
    InitializeStory,
    InitializeStoryRequest,
    PlayedStoryTurn,
    ControllableCharacterSeed,
    PlayStoryTurn,
    PlayStoryTurnRequest,
    ProposeGameRun,
    ProposeGameRunRequest,
    RunInitiator,
    StartPlaythrough,
    StartPlaythroughRequest,
    StoryGenerationData,
    Success,
)
from story_game.application.game_models import LoadedGame
from story_game.infrastructure.persistence.in_memory_proposal_store import (
    InMemoryProposalStore,
)
from story_game.application.game_state import (
    CommitCompletedTurn,
    CreateGameRun,
    LoadGame,
    PromptProfileValidator,
)
from story_game.application.llm import (
    ExtractionPromptSelectionResolver,
    InitialExtractionPromptSelectionResolver,
    InitialStoryText,
    LLMGenerationCall,
    StoryInitializationPromptResolver,
    StoryPromptSelectionResolver,
    SummaryPromptSelectionResolver,
)
from story_game.application.diagnostics import DiagnosticsLog
from story_game.application.summarize_story import SummarizeStory
from story_game.application.story_initialization import (
    GenerateInitialStoryState,
    GenerateInitialStoryStateRequest,
)
from story_game.application.story_turn_context import (
    SelectStoryTurnContextRequest,
    build_story_turn_context_selection,
)
from story_game.domain import (
    GameConfiguration,
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    GameState,
    PromptProfile,
    StableId,
    StateRevision,
    StoryState,
    WorldState,
)
from story_game.infrastructure.configuration import (
    LlmTask,
    TomlGenerationConfigurationResolver,
    TomlLlmConfigurationLoader,
)
from story_game.infrastructure.diagnostics import StructlogDiagnosticsLog
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.infrastructure.logging_config import (
    LoggingMode,
    LoggingSettings,
    configure_logging,
)
from story_game.infrastructure.llm.lmstudio import (
    LmStudioInitialWorldExtractionAdapter,
    LmStudioStoryGenerationAdapter,
    LmStudioStoryInitializationAdapter,
    LmStudioStorySummaryAdapter,
    LmStudioTurnExtractionAdapter,
    lmstudio_settings as LmStudioSettings,
)
from story_game.infrastructure.llm.openai_compatible import (
    OpenAiCompatibleClient as LmStudioClient,
)
from story_game.infrastructure.llm.openai_compatible.models import (
    ChatRequest as LmStudioChatRequest,
    ChatResponse as LmStudioChatResponse,
)

from tests.application import turn_context_world as w

from .live_settings import live_base_url

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def skip_unless_enabled(request: pytest.FixtureRequest) -> None:
    """Shared guard: the whole bundle only runs with --run-lmstudio-live."""
    if not request.config.getoption("--run-lmstudio-live"):
        pytest.skip("Live LM-Studio-Test nur mit --run-lmstudio-live")


def skip_unless_postgres_available() -> None:
    """Additional guard for the full-playthrough checkpoint only.

    Mirrors the skip idiom ``tests/persistence/test_postgres_persistence.py``
    uses when ``STORY_GAME_POSTGRES_DSN`` is not set, rather than failing.
    """
    if not os.environ.get("STORY_GAME_POSTGRES_DSN"):
        pytest.skip(
            "STORY_GAME_POSTGRES_DSN ist für den Persistenz-Anteil nicht gesetzt"
        )


class PrintingLmStudioClient:
    """Print the exact prepared request and raw response, then delegate.

    Mirrors ``PrintingClient`` from ``test_story_initialization_live.py``.
    """

    def __init__(self, client: LmStudioClient) -> None:
        self._client = client
        self.last_request: LmStudioChatRequest | None = None
        self.last_response: LmStudioChatResponse | None = None

    def complete(self, request: LmStudioChatRequest) -> LmStudioChatResponse:
        self.last_request = request
        print(
            json.dumps(
                {"llm_request": _request_document(request)},
                ensure_ascii=False,
                indent=2,
            )
        )
        response = self._client.complete(request)
        self.last_response = response
        print(
            json.dumps(
                {"llm_response": response.text, "finish_reason": response.finish_reason},
                ensure_ascii=False,
                indent=2,
            )
        )
        return response


class CapturingStoryInitializationPort:
    """Records the prepared call without ever reaching the network."""

    def __init__(self) -> None:
        self.call: LLMGenerationCall | None = None

    def generate(self, call: LLMGenerationCall):
        self.call = call
        return Success(
            InitialStoryText(
                "[Nur Prompt-Vorschau — kein Modellaufruf]", ("[Vorschau-Option]",)
            )
        )


class CapturingStoryGenerationPort:
    """Records the prepared call without ever reaching the network."""

    def __init__(self) -> None:
        self.call: LLMGenerationCall | None = None

    def generate(self, call: LLMGenerationCall):
        self.call = call
        return Success(
            StoryGenerationData(
                "[Nur Prompt-Vorschau — kein Modellaufruf]", ("[Vorschau-Option]",)
            )
        )


def _configuration_path() -> Path:
    return REPOSITORY_ROOT / "configs" / "llm.toml"


def _catalog() -> FilePromptPackageCatalog:
    return FilePromptPackageCatalog(REPOSITORY_ROOT / "prompts")


def _resolver() -> TomlGenerationConfigurationResolver:
    return TomlGenerationConfigurationResolver(_configuration_path())


def _debug_diagnostics() -> DiagnosticsLog:
    """Turn on TASK-024's excessive DEBUG profile for this human-inspection run.

    A human running this bundle with ``-s`` wants everything: raw
    prompts/responses (handled separately by ``LmStudioClient``'s own debug
    logging) plus every transformed intermediate value on the way there, so
    a bug inside a transformation step is visible too, not only a failed
    model call. Safe to call repeatedly — it just reconfigures the shared
    structlog setup.
    """
    configure_logging(LoggingSettings(mode=LoggingMode.DEBUG))
    return StructlogDiagnosticsLog(debug_enabled=True)


def _live_client() -> LmStudioClient:
    """Build a real client for LM Studio, verifying the story/extraction
    tasks are actually configured against it before making a call."""
    runtime_configuration = TomlLlmConfigurationLoader().load(_configuration_path())
    provider = runtime_configuration.provider("lmstudio")
    if runtime_configuration.model_for_task(LlmTask.STORY).provider_id != "lmstudio":
        pytest.fail("Das Story-Modell muss für diesen Live-Test LM Studio verwenden")
    if runtime_configuration.model_for_task(LlmTask.EXTRACTION).provider_id != "lmstudio":
        pytest.fail("Das Extraction-Modell muss für diesen Live-Test LM Studio verwenden")
    return LmStudioClient(
        LmStudioSettings(
            live_base_url(provider.base_url),
            timeout_seconds=provider.timeout_seconds,
        ),
        debug_enabled=True,
    )


def _request_document(request: LmStudioChatRequest) -> dict[str, object]:
    document: dict[str, object] = {
        "model": request.model,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ],
    }
    if request.response_format is not None:
        document["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": request.response_format.name,
                "strict": request.response_format.strict,
                "schema": request.response_format.schema,
            },
        }
    return document


def _world_document(state: WorldState) -> dict[str, object]:
    return {
        "entities": [
            {
                "id": str(entity.id),
                "kind": entity.kind.value,
                "label": entity.label,
                "description": entity.description,
                "actor_role": None if entity.actor is None else entity.actor.role.value,
                "conditions": [condition.name for condition in entity.conditions],
                "aliases": list(entity.aliases),
            }
            for entity in state.entities
        ],
        "links": [
            {
                "id": str(link.id),
                "source_id": str(link.source_id),
                "target_id": str(link.target_id),
                "kind": link.kind.value,
                "quantity": link.quantity,
                "description": link.description,
            }
            for link in state.links
        ],
        "facts": [
            {
                "id": str(fact.id),
                "statement": fact.statement,
                "subject_id": None if fact.subject_id is None else str(fact.subject_id),
            }
            for fact in state.facts
        ],
        "scene_location_ids": [str(item) for item in state.scene_location_ids],
    }


def _turn_candidate_document(candidate) -> dict[str, object]:
    return {
        "new_entities": [
            {"local_ref": item.local_ref, "label": item.label, "evidence": item.evidence}
            for item in candidate.new_entities
        ],
        "entity_updates": [
            {"handle": item.handle, "description": item.description, "evidence": item.evidence}
            for item in candidate.entity_updates
        ],
        "added_links": [
            {
                "source_ref": item.source_ref,
                "target_ref": item.target_ref,
                "kind": item.kind.value,
                "evidence": item.evidence,
            }
            for item in candidate.added_links
        ],
        "removed_links": [
            {"handle": item.handle, "evidence": item.evidence}
            for item in candidate.removed_links
        ],
        "added_facts": [
            {"statement": item.statement, "evidence": item.evidence}
            for item in candidate.added_facts
        ],
        "removed_facts": [
            {"handle": item.handle, "evidence": item.evidence}
            for item in candidate.removed_facts
        ],
        "scene": [
            {"reference": item.reference, "evidence": item.evidence}
            for item in candidate.scene
        ],
    }


class HumanInitStorySupport:
    """Builds, calls, and extracts for the story-initialization flow."""

    def __init__(self) -> None:
        self.configuration = GameConfiguration(
            language="de",
            prompt_profile=PromptProfile(
                "dark_fantasy", "balanced", "balanced", "third_person_limited",
                "balanced", "player", "strict", "balanced", "balanced", "teen",
            ),
            narrative_boundaries=("Keine sexualisierte Gewalt",),
            prompt_package_id="story.base",
            prompt_package_version="1",
        )
        self.initial_prompt = (
            "Maren und Alma stehen gemeinsam in einer einzigen "
            "verschlossenen Dungeonkammer. Noch bewegt sich niemand."
        )
        self.controllable_characters = (
            ControllableCharacterSeed("Maren", "Eine vorsichtige Kartografin."),
        )

    def prepare_prompt(self) -> LLMGenerationCall:
        port = CapturingStoryInitializationPort()
        operation = GenerateInitialStoryState(
            StoryInitializationPromptResolver(_catalog()),
            _resolver(),
            port,
            lambda: datetime.now(UTC),
        )
        result = operation.apply(
            GenerateInitialStoryStateRequest(
                self.configuration, self.initial_prompt, self.controllable_characters
            )
        )
        assert isinstance(result, Success), result
        assert port.call is not None
        print(
            json.dumps(
                {"prepared_request": _request_shape(port.call)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return port.call

    def call_llm(self) -> StoryState:
        client = _live_client()
        diagnostics = _debug_diagnostics()
        try:
            printing = PrintingLmStudioClient(client)
            operation = GenerateInitialStoryState(
                StoryInitializationPromptResolver(_catalog()),
                _resolver(),
                LmStudioStoryInitializationAdapter(printing),
                lambda: datetime.now(UTC),
                diagnostics,
            )
            result = operation.apply(
                GenerateInitialStoryStateRequest(
                    self.configuration, self.initial_prompt, self.controllable_characters
                )
            )
            assert isinstance(result, Success), result
            return result.data.story_state
        finally:
            client.close()

    def extract_state(self) -> tuple[StoryState, WorldState]:
        client = _live_client()
        diagnostics = _debug_diagnostics()
        try:
            printing = PrintingLmStudioClient(client)
            operation = InitializeStory(
                GenerateInitialStoryState(
                    StoryInitializationPromptResolver(_catalog()),
                    _resolver(),
                    LmStudioStoryInitializationAdapter(printing),
                    lambda: datetime.now(UTC),
                    diagnostics,
                ),
                ExtractInitialWorldState(
                    InitialExtractionPromptSelectionResolver(_catalog()),
                    _resolver(),
                    LmStudioInitialWorldExtractionAdapter(printing),
                    diagnostics=diagnostics,
                ),
                diagnostics,
            )
            result = operation.apply(
                InitializeStoryRequest(
                    configuration=self.configuration,
                    initial_prompt=self.initial_prompt,
                    controllable_characters=self.controllable_characters,
                )
            )
            assert isinstance(result, Success), result
            print(
                json.dumps(
                    {"world_state": _world_document(result.data.world_state)},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return result.data.story_state, result.data.world_state
        finally:
            client.close()


def _request_shape(call: LLMGenerationCall) -> dict[str, object]:
    """Render a prepared (not-yet-sent) call's request fields for printing."""
    request = call.request
    document: dict[str, object] = {
        "model_selection": {
            "provider_id": call.model_selection.provider_id,
            "model_id": call.model_selection.model_id,
        },
        "system_prompts": list(request.system_prompts),
    }
    for field in ("configuration", "initial_prompt", "world_state", "story_state", "user_prompt", "narration"):
        if hasattr(request, field):
            document[field] = getattr(request, field)
    if getattr(request, "controllable_characters", ()):
        document["controllable_characters"] = [
            {"name": character.name, "description": character.description}
            for character in request.controllable_characters
        ]
    return document


class InMemoryTurnStore:
    """Holds exactly one run/state pair in process memory, never on disk.

    Lets ``play_turn`` exercise the real ``LoadGame`` / ``CommitCompletedTurn``
    operations — revision checks, member validation, atomic turn assembly —
    without a database. This is a viewing checkpoint, not a persistence test:
    PostgreSQL already covers that path.
    """

    def __init__(self, run: GameRun, state: GameState) -> None:
        self.run = run
        self.state = state

    def load_run(self, run_id: StableId) -> GameRun:
        return self.run

    def load_state(self, run_id: StableId, *, revision: StateRevision | None = None) -> GameState:
        return self.state

    def commit_turn(self, request):
        self.state = self.state.complete_turn(
            request.changes, request.turn, request.new_summary_segment
        )
        return self.state


class HumanStoryTurnSupport:
    """Builds, calls, and extracts for the story-turn-generation flow."""

    def __init__(self) -> None:
        self.state = w.game_state((w.TAVERN,), "Maren sitzt am Feuer.")
        self.player_input = "Ich frage den Wirt nach dem Geheimgang."
        selected = build_story_turn_context_selection().apply(
            SelectStoryTurnContextRequest(self.state, w.MAREN, self.player_input)
        )
        assert isinstance(selected, Success), selected
        self.context = selected.data
        self.configuration = w.configuration()
        self.initiator = RunInitiator("https://human-test.example/realm", "human-tester")

    def prepare_prompt(self) -> LLMGenerationCall:
        port = CapturingStoryGenerationPort()
        operation = GenerateStory(
            StoryPromptSelectionResolver(_catalog()), _resolver(), port
        )
        result = operation.apply(
            GenerateStoryRequest(self.context, self.configuration, self.player_input)
        )
        assert isinstance(result, Success), result
        assert port.call is not None
        print(
            json.dumps(
                {"prepared_request": _request_shape(port.call)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return port.call

    def call_llm(self) -> str:
        client = _live_client()
        diagnostics = _debug_diagnostics()
        try:
            printing = PrintingLmStudioClient(client)
            operation = GenerateStory(
                StoryPromptSelectionResolver(_catalog()),
                _resolver(),
                LmStudioStoryGenerationAdapter(printing),
                diagnostics,
            )
            result = operation.apply(
                GenerateStoryRequest(self.context, self.configuration, self.player_input)
            )
            assert isinstance(result, Success), result
            return result.data.text
        finally:
            client.close()

    def extract_state(self) -> ExtractedTurnChanges:
        client = _live_client()
        diagnostics = _debug_diagnostics()
        try:
            printing = PrintingLmStudioClient(client)
            generate = GenerateStory(
                StoryPromptSelectionResolver(_catalog()),
                _resolver(),
                LmStudioStoryGenerationAdapter(printing),
                diagnostics,
            )
            generated = generate.apply(
                GenerateStoryRequest(self.context, self.configuration, self.player_input)
            )
            assert isinstance(generated, Success), generated

            extract = ExtractStoryTurnChanges(
                ExtractionPromptSelectionResolver(_catalog()),
                _resolver(),
                LmStudioTurnExtractionAdapter(printing),
                diagnostics,
            )
            extracted = extract.apply(
                ExtractStoryTurnChangesRequest(
                    self.context, self.configuration, generated.data.text
                )
            )
            assert isinstance(extracted, Success), extracted
            print(
                json.dumps(
                    {
                        "turn_change_candidate": _turn_candidate_document(
                            extracted.data.candidate
                        )
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return extracted.data
        finally:
            client.close()

    def play_turn(self) -> PlayedStoryTurn:
        """Run the real ``PlayStoryTurn`` end to end: generation, extraction,
        approval, summary, and commit — against an in-memory store so nothing
        touches a database, but every non-model step is the production one."""
        client = _live_client()
        diagnostics = _debug_diagnostics()
        try:
            printing = PrintingLmStudioClient(client)
            run = GameRun(
                id=self.state.run_id,
                name="Human-Test-Lauf",
                status=GameRunStatus.ACTIVE,
                current_revision=self.state.revision,
                members=(
                    GameRunMember(
                        self.initiator.issuer,
                        self.initiator.subject,
                        GameRole.OWNER,
                        w.MAREN,
                    ),
                ),
                created_at=(
                    self.state.story.turns[0].completed_at
                    if self.state.story.turns
                    else datetime.now(UTC)
                ),
                updated_at=datetime.now(UTC),
            )
            store = InMemoryTurnStore(run, self.state)
            operation = PlayStoryTurn(
                LoadGame(store, store),
                build_story_turn_context_selection(diagnostics=diagnostics),
                GenerateStory(
                    StoryPromptSelectionResolver(_catalog()),
                    _resolver(),
                    LmStudioStoryGenerationAdapter(printing),
                    diagnostics,
                ),
                ExtractStoryTurnChanges(
                    ExtractionPromptSelectionResolver(_catalog()),
                    _resolver(),
                    LmStudioTurnExtractionAdapter(printing),
                    diagnostics,
                ),
                ApproveStoryTurnChanges(diagnostics=diagnostics),
                SummarizeStory(
                    SummaryPromptSelectionResolver(_catalog()),
                    _resolver(),
                    LmStudioStorySummaryAdapter(printing),
                    diagnostics,
                ),
                CommitCompletedTurn(store, store, diagnostics),
                diagnostics=diagnostics,
            )
            result = operation.apply(
                PlayStoryTurnRequest(run.id, self.initiator, self.player_input)
            )
            assert isinstance(result, Success), result
            print(
                json.dumps(
                    {
                        "resulting_revision": result.data.state.revision.value,
                        "narration": store.state.story.turns[-1].narration,
                        "summary_failure": (
                            None
                            if result.data.summary_failure is None
                            else result.data.summary_failure.message
                        ),
                        "world_state": _world_document(result.data.state.world),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return result.data
        finally:
            client.close()


class HumanFullPlaythroughSupport:
    """Plays one real game through real PostgreSQL and real LM Studio.

    Closes the gap noted in the STORY-006 completion criteria in
    ``docs/TODO.md``: no other test connects a live model with live
    persistence in one run. ``ProposeGameRun`` generates a reviewable,
    unsaved proposal; ``ConfirmGameRunProposal`` persists it as a DRAFT
    template at revision 1; ``StartPlaythrough`` forks it into a new ACTIVE
    run (also revision 1); ``PlayStoryTurn`` persists revision 2 on top of
    that fork. A DRAFT can no longer take a turn directly — see the
    run-lifecycle work that introduced ``StartPlaythrough``. Both created
    runs are deleted again afterwards so repeated human runs stay clean.
    """

    def __init__(self) -> None:
        self.configuration = GameConfiguration(
            language="de",
            prompt_profile=PromptProfile(
                "dark_fantasy", "balanced", "balanced", "third_person_limited",
                "balanced", "player", "strict", "balanced", "balanced", "teen",
            ),
            narrative_boundaries=("Keine sexualisierte Gewalt",),
            prompt_package_id="story.base",
            prompt_package_version="1",
        )
        self.run_name = "Human-Test-Durchlauf"
        self.initial_prompt = (
            "Maren und Alma stehen gemeinsam in einer einzigen "
            "verschlossenen Dungeonkammer. Noch bewegt sich niemand."
        )
        self.controllable_characters = (
            ControllableCharacterSeed("Maren", "Eine vorsichtige Kartografin."),
        )
        self.initiator = RunInitiator(
            "https://human-test.example/realm", "human-tester"
        )

    def play(self, turn_input: str) -> tuple[LoadedGame, PlayedStoryTurn]:
        # Imported lazily: psycopg (and therefore this whole subpackage) is
        # only installed in environments that actually run Postgres tests,
        # and this module must stay importable for every other checkpoint
        # without it.
        from story_game.infrastructure.persistence.postgres import (
            PostgresConnectionFactory,
            PostgresGameStore,
            PostgresSchemaMigrator,
        )

        connections = PostgresConnectionFactory(os.environ["STORY_GAME_POSTGRES_DSN"])
        PostgresSchemaMigrator(connections).migrate()
        store = PostgresGameStore(connections)
        client = _live_client()
        diagnostics = _debug_diagnostics()
        draft_run_id: StableId | None = None
        run_id: StableId | None = None
        try:
            printing = PrintingLmStudioClient(client)

            proposal_store = InMemoryProposalStore()
            propose_operation = ProposeGameRun(
                InitializeStory(
                    GenerateInitialStoryState(
                        StoryInitializationPromptResolver(_catalog()),
                        _resolver(),
                        LmStudioStoryInitializationAdapter(printing),
                        lambda: datetime.now(UTC),
                        diagnostics,
                    ),
                    ExtractInitialWorldState(
                        InitialExtractionPromptSelectionResolver(_catalog()),
                        _resolver(),
                        LmStudioInitialWorldExtractionAdapter(printing),
                        diagnostics=diagnostics,
                    ),
                    diagnostics,
                ),
                proposal_store,
                diagnostics=diagnostics,
            )
            proposed = propose_operation.apply(
                ProposeGameRunRequest(
                    configuration=self.configuration,
                    initial_prompt=self.initial_prompt,
                    initiator=self.initiator,
                    controllable_characters=self.controllable_characters,
                )
            )
            assert isinstance(proposed, Success), proposed
            print(
                json.dumps(
                    {
                        "postgres_proposal": {
                            "proposal_id": str(proposed.data.proposal_id),
                            "suggested_player_entity_ids": [
                                str(entity_id)
                                for entity_id in proposed.data.suggested_player_entity_ids
                            ],
                            "world_state": _world_document(proposed.data.world_state),
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

            confirm_operation = ConfirmGameRunProposal(
                proposal_store,
                CreateGameRun(store, PromptProfileValidator(_catalog())),
                diagnostics=diagnostics,
            )
            initialized = confirm_operation.apply(
                ConfirmGameRunProposalRequest(
                    proposal_id=proposed.data.proposal_id,
                    run_name=self.run_name,
                    initiator=self.initiator,
                    character_decisions=tuple(
                        CharacterDecision(entity_id, "player")
                        for entity_id in proposed.data.suggested_player_entity_ids
                    ),
                )
            )
            assert isinstance(initialized, Success), initialized
            draft_run_id = initialized.data.run.id
            print(
                json.dumps(
                    {
                        "postgres_initialized_run": {
                            "run_id": str(draft_run_id),
                            "revision": initialized.data.state.revision.value,
                            "narration": initialized.data.state.story.initialization.narration,
                            "world_state": _world_document(initialized.data.state.world),
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

            playthrough_operation = StartPlaythrough(
                LoadGame(store, store),
                CreateGameRun(store, PromptProfileValidator(_catalog())),
                diagnostics=diagnostics,
            )
            started = playthrough_operation.apply(
                StartPlaythroughRequest(draft_run_id, self.initiator)
            )
            assert isinstance(started, Success), started
            run_id = started.data.run.id
            print(
                json.dumps(
                    {
                        "postgres_started_playthrough": {
                            "source_run_id": str(draft_run_id),
                            "run_id": str(run_id),
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

            turn_operation = PlayStoryTurn(
                LoadGame(store, store),
                build_story_turn_context_selection(diagnostics=diagnostics),
                GenerateStory(
                    StoryPromptSelectionResolver(_catalog()),
                    _resolver(),
                    LmStudioStoryGenerationAdapter(printing),
                    diagnostics,
                ),
                ExtractStoryTurnChanges(
                    ExtractionPromptSelectionResolver(_catalog()),
                    _resolver(),
                    LmStudioTurnExtractionAdapter(printing),
                    diagnostics,
                ),
                ApproveStoryTurnChanges(diagnostics=diagnostics),
                SummarizeStory(
                    SummaryPromptSelectionResolver(_catalog()),
                    _resolver(),
                    LmStudioStorySummaryAdapter(printing),
                    diagnostics,
                ),
                CommitCompletedTurn(store, store, diagnostics),
                diagnostics=diagnostics,
            )
            played = turn_operation.apply(
                PlayStoryTurnRequest(run_id, self.initiator, turn_input)
            )
            assert isinstance(played, Success), played
            print(
                json.dumps(
                    {
                        "postgres_played_turn": {
                            "resulting_revision": played.data.state.revision.value,
                            "narration": played.data.state.story.turns[-1].narration,
                            "world_state": _world_document(played.data.state.world),
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return initialized.data, played.data
        finally:
            client.close()
            if run_id is not None:
                _delete_run(connections, run_id)
            if draft_run_id is not None:
                _delete_run(connections, draft_run_id)


def _delete_run(connections: PostgresConnectionFactory, run_id: StableId) -> None:
    with connections.connect() as connection:
        with connection.transaction():
            connection.execute(
                "DELETE FROM game_runs WHERE run_id = %s", (run_id.value,)
            )

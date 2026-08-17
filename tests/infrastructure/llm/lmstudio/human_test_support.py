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
from datetime import UTC, datetime
from pathlib import Path

import pytest

from story_game.application import (
    ExtractedTurnChanges,
    ExtractInitialWorldState,
    ExtractStoryTurnChanges,
    ExtractStoryTurnChangesRequest,
    GenerateStory,
    GenerateStoryRequest,
    InitializeStory,
    InitializeStoryRequest,
    PlayerCharacterSeed,
    StoryGenerationData,
    Success,
)
from story_game.application.llm import (
    ExtractionPromptSelectionResolver,
    InitialExtractionPromptSelectionResolver,
    InitialStoryText,
    LLMGenerationCall,
    StoryInitializationPromptResolver,
    StoryPromptSelectionResolver,
)
from story_game.application.story_initialization import (
    GenerateInitialStoryState,
    GenerateInitialStoryStateRequest,
)
from story_game.application.story_turn_context import (
    SelectStoryTurnContextRequest,
    build_story_turn_context_selection,
)
from story_game.domain import GameConfiguration, PromptProfile, StoryState, WorldState
from story_game.infrastructure.configuration import (
    LlmTask,
    TomlGenerationConfigurationResolver,
    TomlLlmConfigurationLoader,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.infrastructure.llm.lmstudio import (
    LmStudioClient,
    LmStudioInitialWorldExtractionAdapter,
    LmStudioSettings,
    LmStudioStoryGenerationAdapter,
    LmStudioStoryInitializationAdapter,
    LmStudioTurnExtractionAdapter,
)
from story_game.infrastructure.llm.lmstudio.models import (
    LmStudioChatRequest,
    LmStudioChatResponse,
)

from tests.application import turn_context_world as w

from .live_settings import live_base_url

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def skip_unless_enabled(request: pytest.FixtureRequest) -> None:
    """Shared guard: the whole bundle only runs with --run-lmstudio-live."""
    if not request.config.getoption("--run-lmstudio-live"):
        pytest.skip("Live LM-Studio-Test nur mit --run-lmstudio-live")


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
        return Success(InitialStoryText("[Nur Prompt-Vorschau — kein Modellaufruf]"))


class CapturingStoryGenerationPort:
    """Records the prepared call without ever reaching the network."""

    def __init__(self) -> None:
        self.call: LLMGenerationCall | None = None

    def generate(self, call: LLMGenerationCall):
        self.call = call
        return Success(StoryGenerationData("[Nur Prompt-Vorschau — kein Modellaufruf]"))


def _configuration_path() -> Path:
    return REPOSITORY_ROOT / "configs" / "llm.toml"


def _catalog() -> FilePromptPackageCatalog:
    return FilePromptPackageCatalog(REPOSITORY_ROOT / "prompts")


def _resolver() -> TomlGenerationConfigurationResolver:
    return TomlGenerationConfigurationResolver(_configuration_path())


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
        )
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
        self.player_character = PlayerCharacterSeed(
            "Maren", "Eine vorsichtige Kartografin."
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
                self.configuration, self.initial_prompt, self.player_character
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
        try:
            printing = PrintingLmStudioClient(client)
            operation = GenerateInitialStoryState(
                StoryInitializationPromptResolver(_catalog()),
                _resolver(),
                LmStudioStoryInitializationAdapter(printing),
                lambda: datetime.now(UTC),
            )
            result = operation.apply(
                GenerateInitialStoryStateRequest(
                    self.configuration, self.initial_prompt, self.player_character
                )
            )
            assert isinstance(result, Success), result
            return result.data
        finally:
            client.close()

    def extract_state(self) -> tuple[StoryState, WorldState]:
        client = _live_client()
        try:
            printing = PrintingLmStudioClient(client)
            operation = InitializeStory(
                GenerateInitialStoryState(
                    StoryInitializationPromptResolver(_catalog()),
                    _resolver(),
                    LmStudioStoryInitializationAdapter(printing),
                    lambda: datetime.now(UTC),
                ),
                ExtractInitialWorldState(
                    InitialExtractionPromptSelectionResolver(_catalog()),
                    _resolver(),
                    LmStudioInitialWorldExtractionAdapter(printing),
                ),
            )
            result = operation.apply(
                InitializeStoryRequest(
                    configuration=self.configuration,
                    initial_prompt=self.initial_prompt,
                    player_character=self.player_character,
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
    if hasattr(request, "player_character") and request.player_character is not None:
        document["player_character"] = {
            "name": request.player_character.name,
            "description": request.player_character.description,
        }
    return document


class HumanStoryTurnSupport:
    """Builds, calls, and extracts for the story-turn-generation flow."""

    def __init__(self) -> None:
        state = w.game_state((w.TAVERN,), "Maren sitzt am Feuer.")
        selected = build_story_turn_context_selection().apply(
            SelectStoryTurnContextRequest(state, w.MAREN, "Ich frage den Wirt nach dem Geheimgang.")
        )
        assert isinstance(selected, Success), selected
        self.context = selected.data
        self.configuration = w.configuration()
        self.player_input = "Ich frage den Wirt nach dem Geheimgang."

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
        try:
            printing = PrintingLmStudioClient(client)
            operation = GenerateStory(
                StoryPromptSelectionResolver(_catalog()),
                _resolver(),
                LmStudioStoryGenerationAdapter(printing),
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
        try:
            printing = PrintingLmStudioClient(client)
            generate = GenerateStory(
                StoryPromptSelectionResolver(_catalog()),
                _resolver(),
                LmStudioStoryGenerationAdapter(printing),
            )
            generated = generate.apply(
                GenerateStoryRequest(self.context, self.configuration, self.player_input)
            )
            assert isinstance(generated, Success), generated

            extract = ExtractStoryTurnChanges(
                ExtractionPromptSelectionResolver(_catalog()),
                _resolver(),
                LmStudioTurnExtractionAdapter(printing),
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

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from story_game.application import (
    ControllableCharacterSeed,
    ExtractInitialWorldState,
    InitializeStory,
    InitializeStoryRequest,
    Success,
)
from story_game.application.story_initialization import (
    GenerateInitialStoryState,
)
from story_game.application.llm import (
    InitialExtractionPromptSelectionResolver,
    StoryInitializationPromptResolver,
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
    LmStudioStoryInitializationAdapter,
)
from story_game.infrastructure.llm.lmstudio.models import (
    LmStudioChatRequest,
    LmStudioChatResponse,
)

from .live_settings import live_base_url


class PrintingClient:
    """Print the exact prepared request while delegating transport to LM Studio."""

    def __init__(self, client: LmStudioClient) -> None:
        self._client = client

    def complete(self, request: LmStudioChatRequest) -> LmStudioChatResponse:
        print(json.dumps({"llm_request": _request_document(request)}, ensure_ascii=False, indent=2))
        response = self._client.complete(request)
        print(
            json.dumps(
                {
                    "llm_response": response.text,
                    "finish_reason": response.finish_reason,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return response


@pytest.mark.lmstudio_live
def test_live_initializes_and_prints_story_and_world_state(
    request: pytest.FixtureRequest,
) -> None:
    if not request.config.getoption("--run-lmstudio-live"):
        pytest.skip("Live LM-Studio-Test nur mit --run-lmstudio-live")

    repository_root = Path(__file__).resolve().parents[4]
    configuration_path = repository_root / "configs" / "llm.toml"
    runtime_configuration = TomlLlmConfigurationLoader().load(configuration_path)
    provider = runtime_configuration.provider("lmstudio")
    if runtime_configuration.model_for_task(LlmTask.STORY).provider_id != "lmstudio":
        pytest.fail("Das Story-Modell muss für diesen Live-Test LM Studio verwenden")
    if runtime_configuration.model_for_task(LlmTask.EXTRACTION).provider_id != "lmstudio":
        pytest.fail("Das Extraction-Modell muss für diesen Live-Test LM Studio verwenden")

    client = LmStudioClient(
        LmStudioSettings(
            live_base_url(provider.base_url),
            timeout_seconds=provider.timeout_seconds,
        )
    )
    try:
        catalog = FilePromptPackageCatalog(repository_root / "prompts")
        resolver = TomlGenerationConfigurationResolver(configuration_path)
        printing_client = PrintingClient(client)
        operation = InitializeStory(
            GenerateInitialStoryState(
                StoryInitializationPromptResolver(catalog),
                resolver,
                LmStudioStoryInitializationAdapter(printing_client),
                lambda: datetime.now(UTC),
            ),
            ExtractInitialWorldState(
                InitialExtractionPromptSelectionResolver(catalog),
                resolver,
                LmStudioInitialWorldExtractionAdapter(printing_client),
            ),
        )
        result = operation.apply(
            InitializeStoryRequest(
                configuration=_configuration(),
                initial_prompt=(
                    "Maren und Alma stehen gemeinsam in einer einzigen "
                    "verschlossenen Dungeonkammer. Noch bewegt sich niemand."
                ),
                controllable_characters=(
                    ControllableCharacterSeed("Maren", "Eine vorsichtige Kartografin."),
                ),
            )
        )
    finally:
        client.close()

    assert isinstance(result, Success), result
    assert result.data.story_state.initialization is not None
    print(
        json.dumps(
            {
                "story_state": _story_document(result.data.story_state),
                "world_state": _world_document(result.data.world_state),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _configuration() -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            "dark_fantasy", "balanced", "balanced", "third_person_limited",
            "balanced", "player", "strict", "balanced", "balanced", "teen",
        ),
        narrative_boundaries=("Keine sexualisierte Gewalt",),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


def _story_document(state: StoryState) -> dict[str, object]:
    assert state.initialization is not None
    return {
        "initialization": {
            "prompt": state.initialization.prompt,
            "narration": state.initialization.narration,
            "completed_at": state.initialization.completed_at.isoformat(),
        },
        "turn_count": len(state.turns),
        "current_turn_sequence": state.current_turn_sequence,
        "summary": None if state.summary is None else state.summary.text,
    }


def _request_document(request: LmStudioChatRequest) -> dict[str, object]:
    document = {
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
        "knowledge": [],
        "rules": [],
        "goals": [],
    }

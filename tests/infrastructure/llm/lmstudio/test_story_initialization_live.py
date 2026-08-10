from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from story_game.application import Success
from story_game.application.story_initialization import (
    GenerateInitialStoryState,
    GenerateInitialStoryStateRequest,
)
from story_game.application.llm import StoryInitializationPromptResolver
from story_game.domain import GameConfiguration, PromptProfile, StoryState
from story_game.infrastructure.configuration import (
    LlmTask,
    TomlGenerationConfigurationResolver,
    TomlLlmConfigurationLoader,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.infrastructure.llm.lmstudio import (
    LmStudioClient,
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
        print(json.dumps(_request_document(request), ensure_ascii=False, indent=2))
        response = self._client.complete(request)
        print(
            json.dumps(
                {
                    "response": response.text,
                    "finish_reason": response.finish_reason,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return response


@pytest.mark.lmstudio_live
def test_live_generates_and_prints_an_initial_story_state(
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

    client = LmStudioClient(
        LmStudioSettings(
            live_base_url(provider.base_url),
            timeout_seconds=provider.timeout_seconds,
        )
    )
    try:
        operation = GenerateInitialStoryState(
            StoryInitializationPromptResolver(
                FilePromptPackageCatalog(repository_root / "prompts")
            ),
            TomlGenerationConfigurationResolver(configuration_path),
            LmStudioStoryInitializationAdapter(PrintingClient(client)),
            lambda: datetime.now(UTC),
        )
        result = operation.apply(
            GenerateInitialStoryStateRequest(
                configuration=_configuration(),
                initial_prompt="Maren und Almas gehen in den Dungeon.",
            )
        )
    finally:
        client.close()

    assert isinstance(result, Success), result
    assert result.data.initialization is not None
    print(json.dumps(_debug_document(result.data), ensure_ascii=False, indent=2))


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


def _debug_document(state: StoryState) -> dict[str, object]:
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
    return {
        "model": request.model,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ],
    }

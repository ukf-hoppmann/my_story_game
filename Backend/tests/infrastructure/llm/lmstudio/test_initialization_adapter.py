from __future__ import annotations

from story_game.application import LLMGenerationCall, ModelSelection, Success
from story_game.application.llm import (
    GenerationOptions,
    InitialStoryText,
    StoryInitializationRequest,
)
from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.infrastructure.llm.lmstudio import LmStudioStoryInitializationAdapter
from story_game.infrastructure.llm.openai_compatible.models import ChatRequest, ChatResponse


class RecordingClient:
    def __init__(self) -> None:
        self.request: ChatRequest | None = None

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        return ChatResponse("Maren hebt die Fackel.", "stop")


def test_adapter_maps_opening_without_world_or_story_context() -> None:
    client = RecordingClient()
    result = LmStudioStoryInitializationAdapter(client).generate(
        LLMGenerationCall(
            model_selection=ModelSelection("lmstudio", "local/story-model"),
            generation_options=GenerationOptions(temperature=0.5),
            request=StoryInitializationRequest(
                system_prompts=("Erzeuge die Eröffnung.",),
                configuration="Sprache: de",
                initial_prompt="Maren und Almas gehen in den Dungeon.",
                controllable_characters=(
                    ControllableCharacterSeed("Maren", "Eine vorsichtige Kartografin."),
                ),
            ),
        )
    )

    assert isinstance(result, Success)
    assert result.data == InitialStoryText("Maren hebt die Fackel.")
    assert client.request is not None
    assert client.request.temperature == 0.5
    assert client.request.max_tokens is None
    assert "[initial_prompt]" in client.request.messages[1].content
    assert "[controllable_characters]" in client.request.messages[1].content
    assert "Maren" in client.request.messages[1].content
    assert "world_state" not in client.request.messages[1].content
    assert "story_state" not in client.request.messages[1].content

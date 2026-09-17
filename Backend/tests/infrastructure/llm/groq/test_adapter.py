from __future__ import annotations

import json

from story_game.application import Failure, LLMGenerationCall, ModelSelection, Success
from story_game.application.llm import (
    GenerationOptions,
    StoryGenerationData,
    StoryGenerationRequest,
)
from story_game.infrastructure.llm.groq.adapter import GroqStoryGenerationAdapter
from story_game.infrastructure.llm.openai_compatible.errors import (
    TransportError,
    TransportErrorKind,
)
from story_game.infrastructure.llm.openai_compatible.models import (
    ChatRequest,
    ChatResponse,
)


def story_call(provider: str = "groq") -> LLMGenerationCall[StoryGenerationRequest]:
    return LLMGenerationCall(
        model_selection=ModelSelection(provider, "local/story-model"),
        generation_options=GenerationOptions(temperature=0.2, max_output_tokens=32),
        request=StoryGenerationRequest(
            system_prompts=("Erzeuge eine kurze Erzählung.", "Bleibe bei den Fakten."),
            configuration="Sprache: Deutsch; Perspektive: dritte Person",
            world_state="Alma steht vor einer verschlossenen Tür.",
            story_state="Bisher wurde noch kein Zug erzählt.",
            user_prompt="Alma klopft an.",
        ),
    )


def _response(narration: str = "Die Tür antwortet.", options: tuple[str, ...] = ("Weiter",)) -> ChatResponse:
    return ChatResponse(
        json.dumps({"narration": narration, "continuation_options": list(options)}),
        "stop",
    )


class RecordingClient:
    def __init__(self, response: ChatResponse | None = None) -> None:
        self.request: ChatRequest | None = None
        self.response = response or _response()
        self.error: TransportError | None = None

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        if self.error is not None:
            raise self.error
        return self.response


def test_adapter_maps_the_complete_story_boundary_and_normalizes_prose() -> None:
    client = RecordingClient()

    result = GroqStoryGenerationAdapter(client).generate(story_call())

    assert isinstance(result, Success)
    assert result.data == StoryGenerationData("Die Tür antwortet.", ("Weiter",))
    assert client.request is not None
    assert client.request.model == "local/story-model"
    assert client.request.temperature == 0.2
    assert client.request.max_tokens == 32
    assert client.request.response_format is not None
    assert client.request.response_format.strict is True
    assert client.request.messages[0].role == "system"
    assert "Erzeuge eine kurze Erzählung." in client.request.messages[0].content
    assert "[configuration]" in client.request.messages[1].content
    assert "[world_state]" in client.request.messages[1].content
    assert "[story_state]" in client.request.messages[1].content
    assert "[user_prompt]" in client.request.messages[1].content


def test_adapter_rejects_a_different_provider_before_transport() -> None:
    client = RecordingClient()

    result = GroqStoryGenerationAdapter(client).generate(story_call("openai"))

    assert isinstance(result, Failure)
    assert result.error.kind.value == "configuration"
    assert client.request is None


def test_adapter_translates_provider_failures_without_leaking_provider_errors() -> None:
    client = RecordingClient()
    client.error = TransportError(
        TransportErrorKind.TIMEOUT,
        "Die Verbindung zu Groq hat das Zeitlimit überschritten.",
        retryable=True,
    )

    result = GroqStoryGenerationAdapter(client).generate(story_call())

    assert isinstance(result, Failure)
    assert result.error.kind.value == "timeout"
    assert result.error.retryable is True
    assert isinstance(result.error.message, str)


def test_adapter_rejects_empty_normalized_output() -> None:
    client = RecordingClient(_response(narration="   "))

    result = GroqStoryGenerationAdapter(client).generate(story_call())

    assert isinstance(result, Failure)
    assert result.error.kind.value == "invalid_response"


def test_adapter_rejects_malformed_structured_output() -> None:
    client = RecordingClient(ChatResponse("kein JSON", "stop"))

    result = GroqStoryGenerationAdapter(client).generate(story_call())

    assert isinstance(result, Failure)
    assert result.error.kind.value == "invalid_response"

from __future__ import annotations

import pytest

from story_game.application import Failure, Success
from story_game.application.llm import (
    CompactImagePromptRequest,
    GenerationOptions,
    LLMErrorKind,
    LLMGenerationCall,
    ModelSelection,
    SceneImagePromptRequest,
    SummarizedTurn,
)
from story_game.infrastructure.llm.openai_compatible import (
    ChatResponse,
    TransportError,
    TransportErrorKind,
)
from story_game.infrastructure.llm.openai_compatible.scene_image_adapters import (
    OpenAiCompatibleCompactImagePromptAdapter,
    OpenAiCompatibleSceneImagePromptAdapter,
)
from story_game.infrastructure.llm.provider_router import (
    RoutingCompactImagePromptAdapter,
    RoutingSceneImagePromptAdapter,
)


class FakeClient:
    def __init__(self, response=None, error=None) -> None:
        self.response = response or ChatResponse("A warm tavern.", "stop")
        self.error = error
        self.request = None

    def complete(self, request):
        self.request = request
        if self.error:
            raise self.error
        return self.response


def prompt_call(provider="gemini") -> LLMGenerationCall[SceneImagePromptRequest]:
    return LLMGenerationCall(
        ModelSelection(provider, "image-model"),
        GenerationOptions(temperature=0.7, max_output_tokens=300),
        SceneImagePromptRequest(
            ("Write an image prompt.",),
            (SummarizedTurn("Ich trete ein.", "Maren betritt die Taverne."),),
            "de",
        ),
    )


def compact_call(provider="gemini") -> LLMGenerationCall[CompactImagePromptRequest]:
    return LLMGenerationCall(
        ModelSelection(provider, "image-model"),
        GenerationOptions(),
        CompactImagePromptRequest(("Shorten.",), "A very long prompt", 60),
    )


def test_the_prompt_request_carries_system_prompt_language_and_turns() -> None:
    client = FakeClient()

    result = OpenAiCompatibleSceneImagePromptAdapter(client, "gemini", "Gemini").write(prompt_call())

    assert isinstance(result, Success) and result.data.text == "A warm tavern."
    request = client.request
    assert request.model == "image-model"
    assert (request.temperature, request.max_tokens) == (0.7, 300)
    assert request.messages[0].role == "system"
    assert request.messages[0].content == "Write an image prompt."
    user = request.messages[1].content
    assert "[language]\nde" in user
    assert "Spieler: Ich trete ein." in user and "Erzählung: Maren betritt die Taverne." in user
    assert request.response_format is None


def test_the_compact_request_carries_the_prompt_and_the_word_limit() -> None:
    client = FakeClient(ChatResponse("tavern, fire", "stop"))

    result = OpenAiCompatibleCompactImagePromptAdapter(client, "gemini", "Gemini").compact(
        compact_call()
    )

    assert result.data.text == "tavern, fire"
    user = client.request.messages[1].content
    assert "[max_words]\n60" in user and "A very long prompt" in user


def test_wrapping_quotes_are_removed_from_the_answer() -> None:
    client = FakeClient(ChatResponse('  "A warm tavern."  ', "stop"))

    result = OpenAiCompatibleSceneImagePromptAdapter(client, "gemini", "Gemini").write(prompt_call())

    assert result.data.text == "A warm tavern."


def test_an_empty_answer_is_an_invalid_response() -> None:
    client = FakeClient(ChatResponse("   ", "stop"))

    result = OpenAiCompatibleSceneImagePromptAdapter(client, "gemini", "Gemini").write(prompt_call())

    assert isinstance(result, Failure)
    assert result.error.kind is LLMErrorKind.INVALID_RESPONSE


def test_a_transport_error_becomes_an_llm_error() -> None:
    client = FakeClient(error=TransportError(TransportErrorKind.TIMEOUT, "slow"))

    result = OpenAiCompatibleSceneImagePromptAdapter(client, "gemini", "Gemini").write(prompt_call())

    assert isinstance(result, Failure)
    assert result.error.kind is LLMErrorKind.TIMEOUT


def test_a_call_for_another_provider_is_rejected_without_a_request() -> None:
    client = FakeClient()

    result = OpenAiCompatibleSceneImagePromptAdapter(client, "gemini", "Gemini").write(
        prompt_call("groq")
    )

    assert result.error.kind is LLMErrorKind.CONFIGURATION
    assert client.request is None


@pytest.mark.parametrize("which", ["write", "compact"])
def test_the_routers_pick_the_adapter_by_provider_and_reject_unknown_ones(which: str) -> None:
    gemini_client, groq_client = FakeClient(), FakeClient()
    if which == "write":
        router = RoutingSceneImagePromptAdapter(
            {
                "gemini": OpenAiCompatibleSceneImagePromptAdapter(gemini_client, "gemini", "Gemini"),
                "groq": OpenAiCompatibleSceneImagePromptAdapter(groq_client, "groq", "Groq"),
            }
        )
        call, other = prompt_call("groq"), prompt_call("unknown")
        use = router.write
    else:
        router = RoutingCompactImagePromptAdapter(
            {
                "gemini": OpenAiCompatibleCompactImagePromptAdapter(gemini_client, "gemini", "Gemini"),
                "groq": OpenAiCompatibleCompactImagePromptAdapter(groq_client, "groq", "Groq"),
            }
        )
        call, other = compact_call("groq"), compact_call("unknown")
        use = router.compact

    assert isinstance(use(call), Success)
    assert groq_client.request is not None and gemini_client.request is None
    assert use(other).error.kind is LLMErrorKind.CONFIGURATION

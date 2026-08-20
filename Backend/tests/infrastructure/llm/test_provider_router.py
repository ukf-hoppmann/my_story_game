from __future__ import annotations

from story_game.application import Failure, LLMGenerationCall, ModelSelection, Success
from story_game.application.llm import (
    GenerationOptions,
    StoryGenerationData,
    StoryGenerationRequest,
)
from story_game.infrastructure.llm.provider_router import RoutingStoryGenerationAdapter


def call(provider_id: str) -> LLMGenerationCall[StoryGenerationRequest]:
    return LLMGenerationCall(
        model_selection=ModelSelection(provider_id, "some-model"),
        generation_options=GenerationOptions(temperature=0.2, max_output_tokens=32),
        request=StoryGenerationRequest(
            system_prompts=("Erzähle weiter.",),
            configuration="Sprache: Deutsch",
            world_state="Alma steht vor einer Tür.",
            story_state="Noch kein Zug.",
            user_prompt="Alma klopft.",
        ),
    )


class RecordingAdapter:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[LLMGenerationCall[StoryGenerationRequest]] = []

    def generate(self, request: LLMGenerationCall[StoryGenerationRequest]):
        self.calls.append(request)
        return Success(StoryGenerationData(self.text))


def test_router_dispatches_to_the_adapter_matching_the_calls_provider_id() -> None:
    lmstudio = RecordingAdapter("lmstudio-antwort")
    groq = RecordingAdapter("groq-antwort")
    router = RoutingStoryGenerationAdapter({"lmstudio": lmstudio, "groq": groq})

    result = router.generate(call("groq"))

    assert isinstance(result, Success)
    assert result.data == StoryGenerationData("groq-antwort")
    assert len(groq.calls) == 1
    assert lmstudio.calls == []


def test_router_re_evaluates_provider_id_on_every_call_without_reconstruction() -> None:
    """Two calls through the SAME router instance with different provider_id

    values (as would happen if configs/llm.toml changes between two turns,
    without restarting the process) must route to the matching adapter each
    time — this is what makes provider selection dynamic per call rather
    than fixed once at Composition Root startup.
    """
    lmstudio = RecordingAdapter("lmstudio-antwort")
    groq = RecordingAdapter("groq-antwort")
    router = RoutingStoryGenerationAdapter({"lmstudio": lmstudio, "groq": groq})

    first = router.generate(call("lmstudio"))
    second = router.generate(call("groq"))

    assert first.data == StoryGenerationData("lmstudio-antwort")
    assert second.data == StoryGenerationData("groq-antwort")


def test_router_rejects_an_unconfigured_provider_without_a_silent_fallback() -> None:
    router = RoutingStoryGenerationAdapter({"lmstudio": RecordingAdapter("x")})

    result = router.generate(call("unknown-provider"))

    assert isinstance(result, Failure)
    assert result.error.kind.value == "configuration"
    assert "unknown-provider" in result.error.message

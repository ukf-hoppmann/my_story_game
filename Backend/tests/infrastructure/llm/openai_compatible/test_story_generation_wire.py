from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from story_game.application import LLMGenerationCall, ModelSelection
from story_game.application.llm import GenerationOptions, StoryGenerationData, StoryGenerationRequest
from story_game.infrastructure.llm.openai_compatible.models import ChatResponse
from story_game.infrastructure.llm.openai_compatible.story_generation_wire import (
    build_request,
    parse_response,
)


def _call() -> LLMGenerationCall[StoryGenerationRequest]:
    request = StoryGenerationRequest(
        system_prompts=("Erzähle weiter.",),
        configuration="Sprache: Deutsch",
        world_state="Alma steht vor einer Tür.",
        story_state="Noch kein Zug.",
        user_prompt="Alma klopft.",
    )
    return LLMGenerationCall(
        model_selection=ModelSelection("lmstudio", "local/story-model"),
        generation_options=GenerationOptions(temperature=0.2, max_output_tokens=32),
        request=request,
    )


def test_build_request_asks_for_strict_structured_output() -> None:
    request = build_request(_call())

    assert request.response_format is not None
    assert request.response_format.strict is True
    schema = request.response_format.schema
    assert set(schema["properties"]) == {"narration", "continuation_options"}
    assert set(schema["required"]) == {"narration", "continuation_options"}
    assert schema["additionalProperties"] is False


def test_parse_response_maps_narration_and_continuation_options() -> None:
    response = ChatResponse(
        json.dumps(
            {
                "narration": "Die Tür antwortet.",
                "continuation_options": ["Anklopfen", "Weitergehen"],
            }
        ),
        "stop",
    )

    data = parse_response(response)

    assert data == StoryGenerationData(
        "Die Tür antwortet.", ("Anklopfen", "Weitergehen")
    )


def test_parse_response_rejects_unknown_fields() -> None:
    response = ChatResponse(
        json.dumps(
            {
                "narration": "Die Tür antwortet.",
                "continuation_options": ["Anklopfen"],
                "unexpected": "value",
            }
        ),
        "stop",
    )

    with pytest.raises(ValidationError):
        parse_response(response)


def test_parse_response_rejects_non_json_text() -> None:
    response = ChatResponse("kein JSON", "stop")

    with pytest.raises(ValidationError):
        parse_response(response)

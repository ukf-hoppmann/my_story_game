from __future__ import annotations

import json

import pytest

from story_game.application import Failure, LLMGenerationCall, ModelSelection, Success
from story_game.application.initialization_models import PlayerCharacterSeed
from story_game.application.llm import (
    CandidateEntity,
    GenerationOptions,
    InitialWorldExtractionRequest,
    LLMErrorKind,
)
from story_game.domain import EntityKind
from story_game.infrastructure.llm.lmstudio import (
    LmStudioInitialWorldExtractionAdapter,
)
from story_game.infrastructure.llm.lmstudio.models import (
    LmStudioChatRequest,
    LmStudioChatResponse,
)


class RecordingClient:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.request: LmStudioChatRequest | None = None

    def complete(self, request: LmStudioChatRequest) -> LmStudioChatResponse:
        self.request = request
        return LmStudioChatResponse(self.response_text, "stop")


def extraction_request() -> InitialWorldExtractionRequest:
    return InitialWorldExtractionRequest(
        system_prompts=("Extrahiere den initialen WorldState.",),
        opening_narration="Maren und Alma betreten den alten Dungeon.",
        language="de",
        perspective="first_person",
        control_mode="player",
        player_character=PlayerCharacterSeed("Maren", "Eine Kartografin."),
    )


def call(request: InitialWorldExtractionRequest):
    return LLMGenerationCall(
        model_selection=ModelSelection("lmstudio", "local/extraction-model"),
        generation_options=GenerationOptions(temperature=0.1),
        request=request,
    )


def test_adapter_requests_strict_json_and_returns_a_typed_candidate() -> None:
    client = RecordingClient(
        json.dumps(
            {
                "entities": [
                    {
                        "local_ref": "alma",
                        "kind": "character",
                        "label": "Alma",
                        "description": "Begleitet Maren.",
                        "conditions": [],
                        "aliases": [],
                    },
                    {
                        "local_ref": "dungeon",
                        "kind": "location",
                        "label": "Alter Dungeon",
                        "description": "Ein dunkles Gewölbe.",
                        "conditions": [],
                        "aliases": [],
                    },
                ],
                "links": [
                    {
                        "source_ref": "alma",
                        "target_ref": "dungeon",
                        "kind": "located_in",
                        "quantity": None,
                        "description": "Alma befindet sich im Dungeon.",
                    }
                ],
                "facts": [
                    {
                        "statement": "Maren hat den Dungeon betreten.",
                        "subject_ref": "player_character",
                    }
                ],
            }
        )
    )

    result = LmStudioInitialWorldExtractionAdapter(client).extract(
        call(extraction_request())
    )

    assert isinstance(result, Success)
    assert result.data.entities[0] == CandidateEntity(
        "alma", EntityKind.CHARACTER, "Alma", "Begleitet Maren."
    )
    assert result.data.facts[0].subject_ref == "player_character"
    assert client.request is not None
    assert client.request.temperature == 0.1
    assert client.request.response_format is not None
    assert client.request.response_format.name == "world_initialization"
    assert client.request.response_format.strict is True
    schema_text = json.dumps(client.request.response_format.schema)
    for forbidden in ("visibility", "evidence", "knowledge", "rules", "goals"):
        assert forbidden not in schema_text
    assert "Never combine references" in schema_text
    user_message = client.request.messages[1].content
    assert "[opening_narration]" in user_message
    assert "[known_player_character]" in client.request.messages[0].content
    assert "[known_player_character]" not in user_message
    assert "initial_prompt" not in user_message
    assert "genre" not in user_message
    assert "tone" not in user_message


@pytest.mark.parametrize(
    "response_text",
    [
        "not-json",
        "{}",
        '{"entities": [], "links": [], "facts": [], "evidence": []}',
        '{"entities": [{"local_ref": "x", "kind": "unknown", "label": "X", "description": "", "conditions": [], "aliases": []}], "links": [], "facts": []}',
    ],
)
def test_adapter_rejects_malformed_or_nonconforming_json(response_text: str) -> None:
    result = LmStudioInitialWorldExtractionAdapter(
        RecordingClient(response_text)
    ).extract(call(extraction_request()))

    assert isinstance(result, Failure)
    assert result.error.kind is LLMErrorKind.INVALID_RESPONSE

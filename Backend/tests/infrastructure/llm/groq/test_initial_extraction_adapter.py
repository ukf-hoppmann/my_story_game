from __future__ import annotations

import json

import pytest

from story_game.application import Failure, LLMGenerationCall, ModelSelection, Success
from story_game.application.llm import (
    CandidateEntity,
    GenerationOptions,
    InitialWorldExtractionRequest,
    LLMErrorKind,
)
from story_game.domain import EntityKind
from story_game.infrastructure.llm.groq import (
    GroqInitialWorldExtractionAdapter,
)
from story_game.infrastructure.llm.openai_compatible.models import (
    ChatRequest,
    ChatResponse,
)


class RecordingClient:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.request: ChatRequest | None = None

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        return ChatResponse(self.response_text, "stop")


def extraction_request() -> InitialWorldExtractionRequest:
    return InitialWorldExtractionRequest(
        system_prompts=("Extrahiere den initialen WorldState.",),
        opening_narration="Maren und Alma betreten den alten Dungeon.",
        language="de",
        perspective="first_person",
        control_mode="player",
    )


def call(request: InitialWorldExtractionRequest):
    return LLMGenerationCall(
        model_selection=ModelSelection("groq", "local/extraction-model"),
        generation_options=GenerationOptions(temperature=0.1),
        request=request,
    )


def test_adapter_requests_strict_json_and_returns_a_typed_candidate() -> None:
    client = RecordingClient(
        json.dumps(
            {
                "entities": [
                    {
                        "local_ref": "maren",
                        "kind": "character",
                        "label": "Maren",
                        "description": "",
                        "conditions": [],
                        "aliases": [],
                    },
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
                        "subject_ref": "maren",
                    }
                ],
                "scene_refs": ["dungeon"],
                "suggested_title": "Der alte Dungeon",
            }
        )
    )

    result = GroqInitialWorldExtractionAdapter(client).extract(
        call(extraction_request())
    )

    assert isinstance(result, Success)
    assert result.data.entities[1] == CandidateEntity(
        "alma", EntityKind.CHARACTER, "Alma", "Begleitet Maren."
    )
    assert result.data.facts[0].subject_ref == "maren"
    assert result.data.scene_refs == ("dungeon",)
    assert result.data.suggested_title == "Der alte Dungeon"
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
    assert "initial_prompt" not in user_message
    assert "genre" not in user_message
    assert "tone" not in user_message


def test_no_seed_context_is_sent_any_more() -> None:
    """The extraction call carries no player-character seed context at all.

    Which characters exist and who (if anyone) is player-controlled are
    entirely post-extraction Application decisions now — see
    ``propose_game_run.py`` — so the extraction request has nothing to say
    about seeds, and the adapter has nothing controllable-character-specific
    left to render into the system message.
    """
    client = RecordingClient(
        json.dumps(
            {
                "entities": [],
                "links": [],
                "facts": [],
                "scene_refs": [],
                "suggested_title": "Der Dungeon",
            }
        )
    )
    request = InitialWorldExtractionRequest(
        system_prompts=("Extrahiere den initialen WorldState.",),
        opening_narration="Maren und Jonas betreten den alten Dungeon.",
        language="de",
        perspective="third_person_omniscient",
        control_mode="director",
    )

    result = GroqInitialWorldExtractionAdapter(client).extract(call(request))

    assert isinstance(result, Success)
    system_message = client.request.messages[0].content
    assert "controllable_character" not in system_message
    assert "player_character" not in system_message
    assert not hasattr(request, "controllable_characters")


@pytest.mark.parametrize(
    "response_text",
    [
        "not-json",
        "{}",
        '{"entities": [], "links": [], "facts": [], "scene_refs": [], "suggested_title": "X", "evidence": []}',
        '{"entities": [{"local_ref": "x", "kind": "unknown", "label": "X", "description": "", "conditions": [], "aliases": []}], "links": [], "facts": [], "scene_refs": [], "suggested_title": "X"}',
        '{"entities": [], "links": [], "facts": [], "suggested_title": "X"}',
        '{"entities": [], "links": [], "facts": [], "scene_refs": [""], "suggested_title": "X"}',
        '{"entities": [], "links": [], "facts": [], "scene_refs": []}',
    ],
)
def test_adapter_rejects_malformed_or_nonconforming_json(response_text: str) -> None:
    result = GroqInitialWorldExtractionAdapter(
        RecordingClient(response_text)
    ).extract(call(extraction_request()))

    assert isinstance(result, Failure)
    assert result.error.kind is LLMErrorKind.INVALID_RESPONSE

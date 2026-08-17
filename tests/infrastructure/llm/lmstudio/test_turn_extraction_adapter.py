from __future__ import annotations

import json

import pytest

from story_game.application import Failure, LLMGenerationCall, ModelSelection, Success
from story_game.application.llm import (
    GenerationOptions,
    LLMErrorKind,
    TurnExtractionRequest,
)
from story_game.domain import EntityKind, RelationKind
from story_game.infrastructure.llm.lmstudio import LmStudioTurnExtractionAdapter
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


def extraction_request() -> TurnExtractionRequest:
    return TurnExtractionRequest(
        system_prompts=("Vergleiche die Erzählung mit dem Weltausschnitt.",),
        narration="Maren verlässt das Wirtshaus und betritt den Wald.",
        world_state="[entities]\ne1 Maren (character)\ne2 Wirtshaus (location)",
        language="de",
    )


def call(request: TurnExtractionRequest):
    return LLMGenerationCall(
        model_selection=ModelSelection("lmstudio", "local/extraction-model"),
        generation_options=GenerationOptions(temperature=0.1),
        request=request,
    )


def empty_payload(**overrides) -> str:
    payload = {
        "new_entities": [],
        "entity_updates": [],
        "added_links": [],
        "removed_link_handles": [],
        "added_facts": [],
        "removed_fact_handles": [],
        "scene_refs": [],
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_adapter_requests_strict_json_and_returns_a_typed_candidate() -> None:
    client = RecordingClient(
        empty_payload(
            new_entities=[
                {
                    "local_ref": "wald",
                    "kind": "location",
                    "label": "Schwarzwald",
                    "description": "Dichter Nadelwald.",
                    "conditions": [],
                    "aliases": [],
                }
            ],
            entity_updates=[
                {
                    "handle": "e1",
                    "description": "Durchnässt.",
                    "conditions": [{"name": "erschöpft", "description": ""}],
                    "aliases": None,
                }
            ],
            added_links=[
                {
                    "source_ref": "e1",
                    "target_ref": "wald",
                    "kind": "located_in",
                    "quantity": None,
                    "description": "",
                }
            ],
            removed_link_handles=["l1"],
            added_facts=[{"statement": "Es regnet.", "subject_ref": None}],
            removed_fact_handles=["f2"],
            scene_refs=["wald"],
        )
    )

    result = LmStudioTurnExtractionAdapter(client).extract(call(extraction_request()))

    assert isinstance(result, Success)
    candidate = result.data
    assert candidate.new_entities[0].local_ref == "wald"
    assert candidate.new_entities[0].kind is EntityKind.LOCATION
    assert candidate.entity_updates[0].handle == "e1"
    assert candidate.entity_updates[0].conditions[0].name == "erschöpft"
    assert candidate.added_links[0].kind is RelationKind.LOCATED_IN
    assert candidate.removed_link_handles == ("l1",)
    assert candidate.added_facts[0].statement == "Es regnet."
    assert candidate.removed_fact_handles == ("f2",)
    assert candidate.scene_refs == ("wald",)


def test_the_request_carries_narration_and_comparison_excerpt_only() -> None:
    client = RecordingClient(empty_payload())

    LmStudioTurnExtractionAdapter(client).extract(call(extraction_request()))

    user_message = client.request.messages[1].content
    assert "[narration]" in user_message
    assert "[world_state]" in user_message
    assert "e1 Maren" in user_message
    assert "user_prompt" not in user_message
    assert "genre" not in user_message


def test_the_schema_is_strict_and_free_of_canonical_concepts() -> None:
    client = RecordingClient(empty_payload())

    LmStudioTurnExtractionAdapter(client).extract(call(extraction_request()))

    response_format = client.request.response_format
    assert response_format is not None
    assert response_format.name == "turn_changes"
    assert response_format.strict is True
    schema_text = json.dumps(response_format.schema)
    for forbidden in ("visibility", "evidence", "knowledge", "rules", "goals", "uuid"):
        assert forbidden not in schema_text


def test_a_wrong_provider_is_refused_before_any_call() -> None:
    client = RecordingClient(empty_payload())

    result = LmStudioTurnExtractionAdapter(client).extract(
        LLMGenerationCall(
            model_selection=ModelSelection("openai", "gpt"),
            generation_options=GenerationOptions(),
            request=extraction_request(),
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is LLMErrorKind.CONFIGURATION
    assert client.request is None


@pytest.mark.parametrize(
    "response_text",
    [
        "not-json",
        "{}",
        '{"new_entities": [], "entity_updates": [], "added_links": [], "removed_link_handles": [], "added_facts": [], "removed_fact_handles": [], "scene_refs": [], "evidence": []}',
        '{"new_entities": [{"local_ref": "x", "kind": "unknown", "label": "X", "description": "", "conditions": [], "aliases": []}], "entity_updates": [], "added_links": [], "removed_link_handles": [], "added_facts": [], "removed_fact_handles": [], "scene_refs": []}',
        '{"new_entities": [], "entity_updates": [], "added_links": [], "removed_link_handles": [""], "added_facts": [], "removed_fact_handles": [], "scene_refs": []}',
    ],
)
def test_adapter_rejects_malformed_or_nonconforming_json(response_text: str) -> None:
    result = LmStudioTurnExtractionAdapter(RecordingClient(response_text)).extract(
        call(extraction_request())
    )

    assert isinstance(result, Failure)
    assert result.error.kind is LLMErrorKind.INVALID_RESPONSE

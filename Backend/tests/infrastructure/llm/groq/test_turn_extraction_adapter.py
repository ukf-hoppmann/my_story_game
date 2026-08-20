from __future__ import annotations

import json
from dataclasses import replace

import pytest

from story_game.application import Failure, LLMGenerationCall, ModelSelection, Success
from story_game.application.llm import (
    GenerationOptions,
    LLMErrorKind,
    TurnExtractionRequest,
)
from story_game.domain import EntityKind, RelationKind
from story_game.infrastructure.llm.groq import GroqTurnExtractionAdapter
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


def extraction_request() -> TurnExtractionRequest:
    return TurnExtractionRequest(
        system_prompts=("Vergleiche die Erzählung mit dem Weltausschnitt.",),
        narration="Maren verlässt das Wirtshaus und betritt den Wald.",
        world_state="[entities]\ne1 Maren (character)\ne2 Wirtshaus (location)",
        language="de",
    )


def call(request: TurnExtractionRequest):
    return LLMGenerationCall(
        model_selection=ModelSelection("groq", "local/extraction-model"),
        generation_options=GenerationOptions(temperature=0.1),
        request=request,
    )


def empty_payload(**overrides) -> str:
    payload = {
        "new_entities": [],
        "entity_updates": [],
        "added_links": [],
        "removed_links": [],
        "added_facts": [],
        "removed_facts": [],
        "scene": [],
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
                    "evidence": "Sie tritt in den Schwarzwald.",
                }
            ],
            entity_updates=[
                {
                    "handle": "e1",
                    "description": "Durchnässt.",
                    "conditions": [{"name": "erschöpft", "description": ""}],
                    "aliases": None,
                    "evidence": "Maren ist durchnässt.",
                }
            ],
            added_links=[
                {
                    "source_ref": "e1",
                    "target_ref": "wald",
                    "kind": "located_in",
                    "quantity": None,
                    "description": "",
                    "evidence": "Sie betritt den Wald.",
                }
            ],
            removed_links=[{"handle": "l1", "evidence": "Sie verlässt das Wirtshaus."}],
            added_facts=[{"statement": "Es regnet.", "subject_ref": None, "evidence": "in den Regen"}],
            removed_facts=[{"handle": "f2", "evidence": "Das Feuer ist erloschen."}],
            scene=[{"reference": "wald", "evidence": "tritt in den Wald"}],
        )
    )

    result = GroqTurnExtractionAdapter(client).extract(call(extraction_request()))

    assert isinstance(result, Success)
    candidate = result.data
    assert candidate.new_entities[0].local_ref == "wald"
    assert candidate.new_entities[0].kind is EntityKind.LOCATION
    assert candidate.entity_updates[0].handle == "e1"
    assert candidate.entity_updates[0].conditions[0].name == "erschöpft"
    assert candidate.added_links[0].kind is RelationKind.LOCATED_IN
    assert candidate.removed_links[0].handle == "l1"
    assert candidate.added_facts[0].statement == "Es regnet."
    assert candidate.removed_facts[0].handle == "f2"
    assert candidate.scene[0].reference == "wald"


def test_the_request_carries_narration_and_comparison_excerpt_only() -> None:
    client = RecordingClient(empty_payload())

    GroqTurnExtractionAdapter(client).extract(call(extraction_request()))

    user_message = client.request.messages[1].content
    assert "[narration]" in user_message
    assert "[world_state]" in user_message
    assert "e1 Maren" in user_message
    assert "user_prompt" not in user_message
    assert "genre" not in user_message


def test_the_schema_is_strict_and_free_of_canonical_concepts() -> None:
    client = RecordingClient(empty_payload())

    GroqTurnExtractionAdapter(client).extract(call(extraction_request()))

    response_format = client.request.response_format
    assert response_format is not None
    assert response_format.name == "turn_changes"
    assert response_format.strict is True
    schema_text = json.dumps(response_format.schema)
    for forbidden in ("visibility", "knowledge", "rules", "goals", "uuid"):
        assert forbidden not in schema_text


def test_the_schema_asks_for_a_justification_when_requested() -> None:
    client = RecordingClient(empty_payload())

    GroqTurnExtractionAdapter(client).extract(call(extraction_request()))

    assert "evidence" in json.dumps(client.request.response_format.schema)


def test_the_schema_leaves_justifications_out_when_switched_off() -> None:
    """Justifications cost output tokens — the slowest resource locally."""
    client = RecordingClient(empty_payload())

    GroqTurnExtractionAdapter(client).extract(
        call(replace(extraction_request(), with_evidence=False))
    )

    assert "evidence" not in json.dumps(client.request.response_format.schema)


def test_a_payload_without_justifications_is_accepted_when_switched_off() -> None:
    client = RecordingClient(empty_payload(removed_links=[{"handle": "l1"}]))

    result = GroqTurnExtractionAdapter(client).extract(
        call(replace(extraction_request(), with_evidence=False))
    )

    assert isinstance(result, Success)
    assert result.data.removed_links[0].handle == "l1"
    assert result.data.removed_links[0].evidence is None


def test_a_wrong_provider_is_refused_before_any_call() -> None:
    client = RecordingClient(empty_payload())

    result = GroqTurnExtractionAdapter(client).extract(
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
        '{"new_entities": [], "entity_updates": [], "added_links": [], "removed_links": [], "added_facts": [], "removed_facts": [], "scene": [], "evidence": []}',
        '{"new_entities": [{"local_ref": "x", "kind": "unknown", "label": "X", "description": "", "conditions": [], "aliases": []}], "entity_updates": [], "added_links": [], "removed_links": [], "added_facts": [], "removed_facts": [], "scene": []}',
        '{"new_entities": [], "entity_updates": [], "added_links": [], "removed_links": [{"handle": ""}], "added_facts": [], "removed_facts": [], "scene": []}',
    ],
)
def test_adapter_rejects_malformed_or_nonconforming_json(response_text: str) -> None:
    result = GroqTurnExtractionAdapter(RecordingClient(response_text)).extract(
        call(extraction_request())
    )

    assert isinstance(result, Failure)
    assert result.error.kind is LLMErrorKind.INVALID_RESPONSE

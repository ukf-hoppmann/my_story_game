from __future__ import annotations

import json
import logging

import structlog
from structlog.testing import LogCapture

from story_game.application import LLMGenerationCall, ModelSelection
from story_game.application.llm import GenerationOptions, TurnExtractionRequest
from story_game.domain import RelationKind
from story_game.infrastructure.llm.openai_compatible.turn_extraction_wire import (
    parse_response,
)


def _capture() -> LogCapture:
    capture = LogCapture()
    structlog.configure(
        processors=[capture],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    )
    return capture


def _call(*, with_evidence: bool) -> LLMGenerationCall[TurnExtractionRequest]:
    request = TurnExtractionRequest(
        system_prompts=("Extrahiere die Änderungen.",),
        world_state="[world]",
        narration="Maren geht in den Kerker.",
        language="de",
        with_evidence=with_evidence,
    )
    return LLMGenerationCall(
        model_selection=ModelSelection("groq", "local/extraction-model"),
        generation_options=GenerationOptions(temperature=0.1),
        request=request,
    )


def _candidate_json(*, link_kind: str, quantity: int | None) -> str:
    return json.dumps(
        {
            "new_entities": [],
            "entity_updates": [],
            "added_links": [
                {
                    "source_ref": "maren",
                    "target_ref": "kerker",
                    "kind": link_kind,
                    "quantity": quantity,
                    "description": "",
                }
            ],
            "removed_links": [],
            "added_facts": [],
            "removed_facts": [],
            "scene": [],
        }
    )


def test_a_stray_quantity_on_a_located_in_link_is_dropped_and_logged() -> None:
    capture = _capture()
    call = _call(with_evidence=False)

    candidate = parse_response(
        call, _candidate_json(link_kind="located_in", quantity=1)
    )

    assert candidate.added_links[0].kind is RelationKind.LOCATED_IN
    assert candidate.added_links[0].quantity is None
    events = [entry["event"] for entry in capture.entries]
    assert "openai_compatible.link_quantity_dropped" in events


def test_quantity_is_kept_for_a_contains_link() -> None:
    call = _call(with_evidence=False)

    candidate = parse_response(call, _candidate_json(link_kind="contains", quantity=3))

    assert candidate.added_links[0].kind is RelationKind.CONTAINS
    assert candidate.added_links[0].quantity == 3

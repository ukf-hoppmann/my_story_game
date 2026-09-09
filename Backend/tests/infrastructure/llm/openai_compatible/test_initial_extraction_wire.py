from __future__ import annotations

import json
import logging

import structlog
from structlog.testing import LogCapture

from story_game.domain import RelationKind
from story_game.infrastructure.llm.openai_compatible.initial_extraction_wire import (
    parse_response,
)


def _capture() -> LogCapture:
    capture = LogCapture()
    structlog.configure(
        processors=[capture],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    )
    return capture


def _candidate_json(*, link_kind: str, quantity: int | None) -> str:
    return json.dumps(
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
                    "local_ref": "kerker",
                    "kind": "location",
                    "label": "Kerker",
                    "description": "",
                    "conditions": [],
                    "aliases": [],
                },
            ],
            "links": [
                {
                    "source_ref": "maren",
                    "target_ref": "kerker",
                    "kind": link_kind,
                    "quantity": quantity,
                    "description": "",
                }
            ],
            "facts": [],
            "scene_refs": ["kerker"],
            "suggested_title": "Der Kerker",
        }
    )


def test_a_stray_quantity_on_a_located_in_link_is_dropped_and_logged() -> None:
    capture = _capture()

    candidate = parse_response(_candidate_json(link_kind="located_in", quantity=1))

    assert candidate.links[0].kind is RelationKind.LOCATED_IN
    assert candidate.links[0].quantity is None
    events = [entry["event"] for entry in capture.entries]
    assert "openai_compatible.link_quantity_dropped" in events


def test_quantity_is_kept_for_a_possesses_link() -> None:
    candidate = parse_response(_candidate_json(link_kind="possesses", quantity=2))

    assert candidate.links[0].kind is RelationKind.POSSESSES
    assert candidate.links[0].quantity == 2

from __future__ import annotations

import logging

import structlog
from structlog.testing import LogCapture

from story_game.infrastructure.llm.openai_compatible.wire_link import (
    normalize_link_quantity,
)


def _capture() -> LogCapture:
    capture = LogCapture()
    structlog.configure(
        processors=[capture],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    )
    return capture


def test_quantity_is_preserved_for_possession_and_container_links() -> None:
    capture = _capture()

    assert normalize_link_quantity("possesses", 3, "maren", "schwert") == 3
    assert normalize_link_quantity("contains", 1, "truhe", "muenze") == 1
    assert capture.entries == []


def test_quantity_is_dropped_and_logged_for_every_other_link_kind() -> None:
    capture = _capture()

    result = normalize_link_quantity("located_in", 1, "maren", "kerker")

    assert result is None
    assert len(capture.entries) == 1
    entry = capture.entries[0]
    assert entry["event"] == "openai_compatible.link_quantity_dropped"
    assert entry["kind"] == "located_in"
    assert entry["source_ref"] == "maren"
    assert entry["target_ref"] == "kerker"
    assert entry["quantity"] == 1


def test_none_quantity_on_a_non_possession_link_is_left_alone_and_not_logged() -> None:
    capture = _capture()

    result = normalize_link_quantity("located_in", None, "maren", "kerker")

    assert result is None
    assert capture.entries == []

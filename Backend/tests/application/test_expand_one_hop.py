from __future__ import annotations

from story_game.application import Success
from story_game.application.expand_one_hop import ExpandOneHop, ExpandOneHopRequest
from story_game.application.story_turn_context_models import (
    EntityCandidate,
    SelectionPriority,
)
from tests.application import turn_context_world as w


def expand(*seed_ids):
    result = ExpandOneHop().apply(
        ExpandOneHopRequest(
            w.world(),
            tuple(
                EntityCandidate(item, SelectionPriority.PLAYER_INPUT, "test")
                for item in seed_ids
            ),
        )
    )
    assert isinstance(result, Success)
    return {candidate.entity_id for candidate in result.data}


def test_directly_related_entities_are_added() -> None:
    assert expand(w.MAREN) == {w.TAVERN, w.SWORD}


def test_relations_are_followed_in_both_directions() -> None:
    assert w.MAREN in expand(w.SWORD)


def test_every_relation_kind_counts_as_one_hop() -> None:
    assert expand(w.ALMA) == {w.FOREST, w.GUILD}


def test_the_expansion_stops_after_exactly_one_hop() -> None:
    """Maren -> Wirtshaus is one hop; Wirtshaus -> Bertram would be a second."""
    assert w.WIRT not in expand(w.MAREN)


def test_entities_already_selected_are_not_reported_again() -> None:
    assert w.MAREN not in expand(w.MAREN, w.SWORD)


def test_without_seeds_nothing_is_expanded() -> None:
    assert expand() == set()

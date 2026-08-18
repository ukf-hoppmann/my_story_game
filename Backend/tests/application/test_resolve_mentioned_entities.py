from __future__ import annotations

from story_game.application import Success
from story_game.application.resolve_mentioned_entities import (
    ResolveMentionedEntities,
    ResolveMentionedEntitiesRequest,
)
from story_game.application.story_turn_context_models import SelectionPriority
from story_game.domain import EntityKind, WorldEntity, WorldState
from tests.application import turn_context_world as w
from tests.ids import sid


def resolve(player_input: str, prose: str = "", world: WorldState | None = None):
    result = ResolveMentionedEntities().apply(
        ResolveMentionedEntitiesRequest(world or w.world(), player_input, prose)
    )
    assert isinstance(result, Success)
    return result.data


def priorities(candidates) -> dict:
    return {candidate.entity_id: candidate.priority for candidate in candidates}


def test_labels_and_aliases_are_found_regardless_of_capitalisation() -> None:
    found = priorities(resolve("Ich spreche mit ALMA."))

    assert found == {w.ALMA: SelectionPriority.PLAYER_INPUT}


def test_an_alias_matches_just_like_a_label() -> None:
    found = priorities(resolve("Ich frage den Wirt."))

    assert found == {w.WIRT: SelectionPriority.PLAYER_INPUT}


def test_a_declined_article_still_matches_an_alias_stored_with_one() -> None:
    """'der Wirt' must also match 'dem Wirt' — German articles decline."""
    for text in ("Ich danke dem Wirt.", "Der Wirt schweigt.", "Ich sehe einen Wirt."):
        assert priorities(resolve(text)) == {w.WIRT: SelectionPriority.PLAYER_INPUT}


def test_german_endings_still_match_the_known_name() -> None:
    found = priorities(resolve("Ich nehme Marens Schwert."))

    assert w.MAREN in found


def test_a_name_inside_another_word_is_not_a_match() -> None:
    world = WorldState(
        entities=(WorldEntity(sid("ann"), EntityKind.CHARACTER, "Ann"),)
    )

    assert resolve("Ich kann nichts erkennen.", world=world) == ()


def test_player_input_outranks_the_recent_prose() -> None:
    found = priorities(resolve("Ich rufe Alma.", "Alma und Bertram warten."))

    assert found[w.ALMA] is SelectionPriority.PLAYER_INPUT
    assert found[w.WIRT] is SelectionPriority.RECENT_PROSE


def test_an_ambiguous_name_keeps_every_candidate() -> None:
    world = WorldState(
        entities=(
            WorldEntity(sid("smith-a"), EntityKind.CHARACTER, "Jorek"),
            WorldEntity(sid("smith-b"), EntityKind.CHARACTER, "Jorek"),
        )
    )

    found = resolve("Ich suche Jorek.", world=world)

    assert {candidate.entity_id for candidate in found} == {
        sid("smith-a"),
        sid("smith-b"),
    }


def test_an_empty_input_finds_nothing_without_failing() -> None:
    assert resolve("", "") == ()


def test_the_reason_names_where_the_match_came_from() -> None:
    found = resolve("Ich gehe ins Wirtshaus.")

    assert "Wirtshaus" in found[0].detail

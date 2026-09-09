from __future__ import annotations

from story_game.application import Success
from story_game.application.select_always_included import (
    SelectAlwaysIncluded,
    SelectAlwaysIncludedRequest,
)
from story_game.application.story_turn_context_models import (
    SelectionBudget,
    SelectionPriority,
)
from tests.application import turn_context_world as w
from tests.ids import sid


def apply(request: SelectAlwaysIncludedRequest):
    result = SelectAlwaysIncluded().apply(request)
    assert isinstance(result, Success)
    return result.data


def test_frame_carries_summary_recent_turns_rules_and_configuration() -> None:
    state = w.game_state((w.TAVERN,), "Erster Zug.", "Zweiter Zug.", "Dritter Zug.")

    data = apply(SelectAlwaysIncludedRequest(state, (w.MAREN,), SelectionBudget()))

    assert data.summary is not None
    assert [item.narration for item in data.recent_turns] == [
        "Zweiter Zug.",
        "Dritter Zug.",
    ]
    assert data.rules == w.rules()
    assert data.language == "de"
    assert data.perspective == "second_person"
    assert data.control_mode == "player"
    assert data.narrative_boundaries == ("Keine sexualisierte Gewalt",)


def test_recent_turns_follow_the_configured_budget_and_stay_in_order() -> None:
    state = w.game_state((w.TAVERN,), "Eins.", "Zwei.", "Drei.")

    data = apply(
        SelectAlwaysIncludedRequest(
            state, (w.MAREN,), SelectionBudget(recent_turn_count=1)
        )
    )

    assert [item.narration for item in data.recent_turns] == ["Drei."]


def test_only_open_main_goals_belong_to_the_frame() -> None:
    state = w.game_state()

    data = apply(SelectAlwaysIncludedRequest(state, (w.MAREN,), SelectionBudget()))

    assert [goal.id for goal in data.main_goals] == [sid("g-main")]


def test_the_controlled_entity_is_always_present_even_when_never_named() -> None:
    state = w.game_state((w.TAVERN,), "Du betrittst den Raum.")

    data = apply(SelectAlwaysIncludedRequest(state, (w.MAREN,), SelectionBudget()))

    assert data.controlled_entities != ()
    assert data.controlled_entities[0].id == w.MAREN
    assert [candidate.entity_id for candidate in data.candidates] == [w.MAREN]
    assert data.candidates[0].priority is SelectionPriority.ALWAYS


def test_multiple_controlled_entities_are_all_present() -> None:
    state = w.game_state((w.TAVERN,), "Ihr betretet den Raum.")

    data = apply(
        SelectAlwaysIncludedRequest(state, (w.MAREN, w.ALMA), SelectionBudget())
    )

    assert {entity.id for entity in data.controlled_entities} == {w.MAREN, w.ALMA}
    assert {candidate.entity_id for candidate in data.candidates} == {w.MAREN, w.ALMA}


def test_without_a_controlled_entity_the_frame_stays_valid() -> None:
    state = w.game_state()

    data = apply(SelectAlwaysIncludedRequest(state, (), SelectionBudget()))

    assert data.controlled_entities == ()
    assert data.candidates == ()
    assert data.rules == w.rules()


def test_an_unknown_controlled_entity_is_a_visible_failure() -> None:
    from story_game.application import Failure
    from story_game.application.story_turn_context_errors import (
        ContextSelectionErrorKind,
    )

    result = SelectAlwaysIncluded().apply(
        SelectAlwaysIncludedRequest(w.game_state(), (sid("ghost"),), SelectionBudget())
    )

    assert isinstance(result, Failure)
    assert result.error.kind is ContextSelectionErrorKind.UNKNOWN_CONTROLLED_ENTITY

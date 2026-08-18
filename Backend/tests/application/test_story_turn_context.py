from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from story_game.application import Failure, Success
from story_game.application.story_turn_context import (
    SelectStoryTurnContext,
    SelectStoryTurnContextRequest,
    build_story_turn_context_selection,
)
from story_game.application.story_turn_context_errors import ContextSelectionErrorKind
from story_game.application.story_turn_context_models import SelectionBudget
from story_game.domain import StoryInitialization, StoryState
from tests.application import turn_context_world as w
from tests.ids import sid


def select(
    player_input: str,
    *narrations: str,
    scene=(w.TAVERN,),
    controlled=w.MAREN,
    budget=SelectionBudget(),
):
    state = w.game_state(scene, *narrations)
    result = build_story_turn_context_selection(budget).apply(
        SelectStoryTurnContextRequest(state, controlled, player_input)
    )
    assert isinstance(result, Success), result
    return result.data


def ids(items) -> set:
    return {item.id for item in items}


def test_a_turn_without_any_named_place_still_knows_its_scene() -> None:
    """'Maren geht weiter' names nothing — the scene comes from the world."""
    context = select("Maren geht weiter.", "Es wird still.")

    assert ids(context.scene_locations) == {w.TAVERN}
    assert w.WIRT in ids(context.entities)


def test_the_controlled_figure_is_present_although_never_named() -> None:
    context = select("Du wartest.", "Du betrittst den Raum.")

    assert context.controlled_entity is not None
    assert context.controlled_entity.id == w.MAREN
    assert w.MAREN in ids(context.entities)


def test_a_mentioned_side_location_does_not_displace_the_scene() -> None:
    context = select("Ich denke an die Hauptstadt.")

    assert ids(context.scene_locations) == {w.TAVERN}
    assert w.CAPITAL in ids(context.entities)
    assert w.WIRT in ids(context.entities)


def test_hidden_facts_reach_the_model_like_any_other() -> None:
    context = select("Ich frage den Wirt.")

    assert sid("f-wirt-plot") in ids(context.facts)


def test_the_frame_travels_with_every_turn() -> None:
    context = select("Ich warte.", "Eins.", "Zwei.")

    assert context.summary is not None
    assert [item.narration for item in context.recent_turns] == ["Eins.", "Zwei."]
    assert context.rules == w.rules()
    assert context.narrative_boundaries == ("Keine sexualisierte Gewalt",)
    assert context.language == "de"
    assert context.perspective == "second_person"
    assert context.control_mode == "player"
    assert sid("g-main") in ids(context.goals)


def test_the_opening_stands_in_for_prose_before_the_first_turn() -> None:
    state = w.game_state()
    state = replace(
        state,
        story=StoryState(
            initialization=StoryInitialization(
                "Ein Prompt.",
                "Alma steht am Waldrand.",
                datetime(2026, 8, 17, tzinfo=UTC),
            )
        ),
    )

    result = build_story_turn_context_selection().apply(
        SelectStoryTurnContextRequest(state, w.MAREN, "Ich sehe mich um.")
    )

    assert isinstance(result, Success)
    assert w.ALMA in ids(result.data.entities)


def test_the_same_state_and_input_always_select_the_same_context() -> None:
    assert select("Ich frage Alma.", "Alma wartet.") == select(
        "Ich frage Alma.", "Alma wartet."
    )


def test_the_given_game_state_is_left_untouched() -> None:
    state = w.game_state((w.TAVERN,), "Alma wartet.")
    before = replace(state)

    build_story_turn_context_selection().apply(
        SelectStoryTurnContextRequest(state, w.MAREN, "Ich frage Alma.")
    )

    assert state == before


def test_the_result_never_references_an_entity_it_does_not_carry() -> None:
    context = select(
        "Ich frage Alma nach dem Wirt.",
        "Jonas schreibt aus der Hauptstadt.",
        budget=SelectionBudget(max_entities=3),
    )

    carried = ids(context.entities)
    assert context.truncated is True
    assert all({link.source_id, link.target_id} <= carried for link in context.links)
    assert all(
        fact.subject_id is None or fact.subject_id in carried for fact in context.facts
    )
    assert all(entry.actor_id in carried for entry in context.knowledge)
    assert all(set(goal.related_entity_ids) <= carried for goal in context.goals)
    assert ids(context.scene_locations) <= carried


def test_an_unknown_controlled_figure_fails_visibly() -> None:
    state = w.game_state()

    result = build_story_turn_context_selection().apply(
        SelectStoryTurnContextRequest(state, sid("ghost"), "Ich warte.")
    )

    assert isinstance(result, Failure)
    assert result.error.kind is ContextSelectionErrorKind.UNKNOWN_CONTROLLED_ENTITY


def test_every_step_is_delegated_in_a_visible_order() -> None:
    calls: list[str] = []

    class Spy:
        def __init__(self, name: str, inner) -> None:
            self._name = name
            self._inner = inner

        def apply(self, request):
            calls.append(self._name)
            return self._inner.apply(request)

    from story_game.application.apply_selection_budget import ApplySelectionBudget
    from story_game.application.expand_one_hop import ExpandOneHop
    from story_game.application.populate_scene_locations import PopulateSceneLocations
    from story_game.application.resolve_mentioned_entities import (
        ResolveMentionedEntities,
    )
    from story_game.application.select_always_included import SelectAlwaysIncluded
    from story_game.application.select_referenced_facts_knowledge_goals import (
        SelectReferencedFactsKnowledgeGoals,
    )

    operation = SelectStoryTurnContext(
        Spy("frame", SelectAlwaysIncluded()),
        Spy("mentions", ResolveMentionedEntities()),
        Spy("scene", PopulateSceneLocations()),
        Spy("hop", ExpandOneHop()),
        Spy("referenced", SelectReferencedFactsKnowledgeGoals()),
        Spy("budget", ApplySelectionBudget()),
    )

    result = operation.apply(
        SelectStoryTurnContextRequest(w.game_state(), w.MAREN, "Ich warte.")
    )

    assert isinstance(result, Success)
    assert calls == ["frame", "mentions", "scene", "hop", "referenced", "budget"]

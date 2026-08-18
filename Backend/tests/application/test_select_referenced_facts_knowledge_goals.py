from __future__ import annotations

from story_game.application import Success
from story_game.application.select_referenced_facts_knowledge_goals import (
    SelectReferencedFactsKnowledgeGoals,
    SelectReferencedFactsKnowledgeGoalsRequest,
)
from story_game.application.story_turn_context_models import (
    EntityCandidate,
    SelectionPriority,
)
from tests.application import turn_context_world as w
from tests.ids import sid


def select(*selected_ids, always_goals=()):
    result = SelectReferencedFactsKnowledgeGoals().apply(
        SelectReferencedFactsKnowledgeGoalsRequest(
            w.world(),
            tuple(
                EntityCandidate(item, SelectionPriority.PLAYER_INPUT, "test")
                for item in selected_ids
            ),
            always_goals,
        )
    )
    assert isinstance(result, Success)
    return result.data


def ids(items) -> set:
    return {item.id for item in items}


def test_facts_about_a_selected_entity_are_included() -> None:
    data = select(w.WIRT)

    assert sid("f-wirt-secret") in ids(data.facts)


def test_global_facts_without_a_subject_are_always_relevant() -> None:
    data = select(w.WIRT)

    assert sid("f-global") in ids(data.facts)


def test_facts_about_unselected_entities_stay_out() -> None:
    data = select(w.WIRT)

    assert sid("f-capital-far") not in ids(data.facts)


def test_hidden_facts_are_selected_like_any_other() -> None:
    """The model has to be able to work towards what the player cannot see."""
    data = select(w.WIRT)

    assert sid("f-wirt-plot") in ids(data.facts)


def test_knowledge_needs_both_its_actor_and_its_fact() -> None:
    with_actor = select(w.WIRT)
    without_actor = select(w.TAVERN)

    assert with_actor.knowledge == w.knowledge()
    assert without_actor.knowledge == ()


def test_goals_referencing_a_selected_entity_are_added() -> None:
    data = select(w.ALMA)

    assert sid("g-side") in ids(data.goals)


def test_a_goal_pulls_in_the_entities_it_still_needs() -> None:
    data = select(w.ALMA)

    assert w.GUILD in {item.entity_id for item in data.closure_candidates}


def test_entities_of_an_always_included_goal_are_never_droppable() -> None:
    data = select(w.TAVERN, always_goals=(w.goals()[0],))

    closure = {item.entity_id: item.priority for item in data.closure_candidates}
    assert closure[w.MAREN] is SelectionPriority.ALWAYS


def test_always_included_goals_are_not_duplicated() -> None:
    main_goal = w.goals()[0]

    data = select(w.MAREN, always_goals=(main_goal,))

    assert list(ids(data.goals)).count(main_goal.id) == 1

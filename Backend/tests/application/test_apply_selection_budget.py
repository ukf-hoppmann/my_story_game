from __future__ import annotations

from story_game.application import Success
from story_game.application.apply_selection_budget import (
    ApplySelectionBudget,
    ApplySelectionBudgetRequest,
)
from story_game.application.story_turn_context_models import (
    EntityCandidate,
    SelectionBudget,
    SelectionPriority,
)
from tests.application import turn_context_world as w


def cap(candidates, budget=SelectionBudget(), facts=None, goals=None, knowledge=None):
    world = w.world()
    result = ApplySelectionBudget().apply(
        ApplySelectionBudgetRequest(
            world,
            tuple(candidates),
            world.facts if facts is None else facts,
            world.knowledge if knowledge is None else knowledge,
            world.goals if goals is None else goals,
            budget,
        )
    )
    assert isinstance(result, Success)
    return result.data


def candidate(entity_id, priority) -> EntityCandidate:
    return EntityCandidate(entity_id, priority, "test")


def ids(items) -> list:
    return [item.id for item in items]


def test_nothing_is_dropped_while_the_budget_allows_it() -> None:
    data = cap(
        [
            candidate(w.MAREN, SelectionPriority.ALWAYS),
            candidate(w.TAVERN, SelectionPriority.PRIMARY_SCENE),
        ]
    )

    assert ids(data.entities) == [w.MAREN, w.TAVERN]
    assert data.truncated is False


def test_more_important_reasons_survive_a_tight_budget() -> None:
    data = cap(
        [
            candidate(w.BRUDER, SelectionPriority.ONE_HOP),
            candidate(w.ALMA, SelectionPriority.PLAYER_INPUT),
            candidate(w.MAREN, SelectionPriority.ALWAYS),
        ],
        SelectionBudget(max_entities=2),
    )

    assert ids(data.entities) == [w.MAREN, w.ALMA]
    assert data.truncated is True


def test_the_frame_is_never_dropped_even_below_the_limit() -> None:
    data = cap(
        [
            candidate(w.MAREN, SelectionPriority.ALWAYS),
            candidate(w.ALMA, SelectionPriority.ALWAYS),
            candidate(w.WIRT, SelectionPriority.ALWAYS),
            candidate(w.BRUDER, SelectionPriority.ONE_HOP),
        ],
        SelectionBudget(max_entities=1),
    )

    assert set(ids(data.entities)) == {w.MAREN, w.ALMA, w.WIRT}
    assert data.truncated is True


def test_the_scene_the_world_names_is_never_dropped() -> None:
    """Without its location a turn no longer knows where it takes place."""
    data = cap(
        [
            candidate(w.MAREN, SelectionPriority.ALWAYS),
            candidate(w.TAVERN, SelectionPriority.PRIMARY_SCENE),
        ],
        SelectionBudget(max_entities=1),
    )

    assert set(ids(data.entities)) == {w.MAREN, w.TAVERN}
    # Nothing was left out, the guarantee merely pushed past the limit.
    assert data.truncated is False


def test_the_cast_of_the_scene_is_still_budgeted() -> None:
    """Only the place itself is guaranteed, not everyone standing in it."""
    data = cap(
        [
            candidate(w.TAVERN, SelectionPriority.PRIMARY_SCENE),
            candidate(w.WIRT, SelectionPriority.PRIMARY_SCENE),
            candidate(w.ALMA, SelectionPriority.PRIMARY_SCENE),
        ],
        SelectionBudget(max_entities=2),
    )

    assert w.TAVERN in ids(data.entities)
    assert len(data.entities) == 2
    assert data.truncated is True


def test_entities_of_equal_priority_keep_the_world_order() -> None:
    data = cap(
        [
            candidate(w.WIRT, SelectionPriority.ONE_HOP),
            candidate(w.ALMA, SelectionPriority.ONE_HOP),
        ],
        SelectionBudget(max_entities=1),
    )

    assert ids(data.entities) == [w.ALMA]


def test_links_only_survive_when_both_ends_do() -> None:
    data = cap(
        [
            candidate(w.MAREN, SelectionPriority.ALWAYS),
            candidate(w.SWORD, SelectionPriority.ONE_HOP),
        ]
    )

    assert all(
        link.source_id in ids(data.entities) and link.target_id in ids(data.entities)
        for link in data.links
    )


def test_a_cut_entity_takes_its_dangling_references_with_it() -> None:
    data = cap(
        [
            candidate(w.MAREN, SelectionPriority.ALWAYS),
            candidate(w.WIRT, SelectionPriority.ONE_HOP),
        ],
        SelectionBudget(max_entities=1),
    )

    selected = set(ids(data.entities))
    assert all(fact.subject_id in selected or fact.subject_id is None for fact in data.facts)
    assert all(entry.actor_id in selected for entry in data.knowledge)
    assert all(
        set(goal.related_entity_ids) <= selected for goal in data.goals
    )
    assert all(
        {link.source_id, link.target_id} <= selected for link in data.links
    )


def test_the_fact_budget_is_enforced_and_reported() -> None:
    data = cap(
        [candidate(item.id, SelectionPriority.ALWAYS) for item in w.entities()],
        SelectionBudget(max_facts=1),
    )

    assert len(data.facts) == 1
    assert data.truncated is True


def test_the_goal_budget_is_enforced_and_reported() -> None:
    data = cap(
        [candidate(item.id, SelectionPriority.ALWAYS) for item in w.entities()],
        SelectionBudget(max_goals=1),
    )

    assert len(data.goals) == 1
    assert data.truncated is True


def test_the_same_input_always_produces_the_same_result() -> None:
    candidates = [
        candidate(w.MAREN, SelectionPriority.ALWAYS),
        candidate(w.ALMA, SelectionPriority.ONE_HOP),
        candidate(w.WIRT, SelectionPriority.ONE_HOP),
    ]

    assert cap(candidates, SelectionBudget(max_entities=2)) == cap(
        candidates, SelectionBudget(max_entities=2)
    )

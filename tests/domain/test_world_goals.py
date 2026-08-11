from __future__ import annotations

import pytest

import story_game.domain as domain
from tests.ids import sid


def test_world_state_owns_main_and_side_goals() -> None:
    assert hasattr(domain, "GoalKind"), "Goals must distinguish main and side goals"
    goal = domain.Goal(
        id=sid("find-sword"),
        kind=domain.GoalKind.MAIN,
        title="Finde das magische Schwert",
        description="Almas muss das Schwert im Dungeon finden.",
        status=domain.GoalStatus.OPEN,
        related_entity_ids=(sid("almas"), sid("magic-sword")),
    )
    world = domain.WorldState(
        entities=(
            domain.WorldEntity(
                sid("almas"),
                domain.EntityKind.CHARACTER,
                "Almas",
                actor=domain.ActorProfile(domain.ActorRole.PLAYER),
            ),
            domain.WorldEntity(
                sid("magic-sword"), domain.EntityKind.ITEM, "Magisches Schwert"
            ),
        ),
        goals=(goal,),
    )

    assert world.goal(goal.id) == goal


def test_world_state_rejects_goal_references_to_unknown_entities() -> None:
    assert hasattr(domain, "GoalKind")
    goal = domain.Goal(
        id=sid("find-sword"),
        kind=domain.GoalKind.MAIN,
        title="Finde das magische Schwert",
        description="Das Schwert muss gefunden werden.",
        related_entity_ids=(sid("missing"),),
    )

    with pytest.raises(domain.InvalidReferenceError):
        domain.WorldState(goals=(goal,))

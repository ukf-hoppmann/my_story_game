from __future__ import annotations

import pytest

from story_game.domain import (
    ActorProfile,
    ActorRole,
    ApprovedChangeSet,
    ChangeRejectedError,
    CreateEntity,
    EntityKind,
    GameState,
    InvalidReferenceError,
    ProposedChangeSet,
    RevisionConflictError,
    StableId,
    StateRevision,
    StoryState,
    WorldEntity,
    WorldState,
)


def sid(value: str) -> StableId:
    return StableId(value)


def empty_game() -> GameState:
    return GameState(sid("game"), StateRevision(1), WorldState(), StoryState())


def test_only_approved_changes_can_advance_the_canonical_state() -> None:
    game = empty_game()
    mara = WorldEntity(
        sid("mara"),
        EntityKind.CHARACTER,
        "Mara",
        actor=ActorProfile(ActorRole.PLAYER),
    )

    with pytest.raises(ChangeRejectedError):
        game.apply(
            ProposedChangeSet(
                sid("proposal"),
                game.revision,
            )  # type: ignore[arg-type]
        )

    updated = game.apply(
        ApprovedChangeSet(
            sid("proposal"),
            game.revision,
            changes=(CreateEntity(mara),),
        )
    )

    assert updated.revision == StateRevision(2)
    assert updated.world.entity(mara.id) == mara


def test_stale_approved_changes_are_rejected() -> None:
    game = empty_game()
    changes = ApprovedChangeSet(
        sid("proposal"),
        StateRevision(1),
        changes=(),
    )
    current = game.apply(changes)

    with pytest.raises(RevisionConflictError):
        current.apply(changes)


def test_game_state_rejects_a_scene_with_an_unknown_participant() -> None:
    from story_game.domain import Scene, SceneParticipant, StorySequence

    with pytest.raises(InvalidReferenceError):
        GameState(
            sid("game"),
            StateRevision(1),
            WorldState(
                entities=(WorldEntity(sid("harbor"), EntityKind.LOCATION, "Hafen"),)
            ),
            StoryState(
                scenes=(
                    Scene(
                        sid("scene"),
                        StorySequence(1),
                        sid("harbor"),
                        participants=(SceneParticipant(sid("unknown"), "intruder"),),
                    ),
                )
            ),
        )

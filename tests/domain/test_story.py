from __future__ import annotations

import pytest

from story_game.domain import (
    Scene,
    SceneParticipant,
    StableId,
    StoryEvent,
    StorySequence,
    StoryState,
    ValidationError,
)


def sid(value: str) -> StableId:
    return StableId(value)


def test_story_events_must_follow_the_existing_chronology() -> None:
    first = StoryEvent(sid("event-1"), StorySequence(1), "arrival", "Mara erreicht den Hafen.")
    state = StoryState(events=(first,), current_sequence=1)

    with pytest.raises(ValidationError):
        state.add_event(
            StoryEvent(sid("event-2"), StorySequence(1), "door", "Die Tür öffnet sich.")
        )


def test_scene_participants_have_unique_stable_references() -> None:
    with pytest.raises(ValidationError):
        Scene(
            sid("scene-1"),
            StorySequence(1),
            sid("harbor"),
            participants=(
                SceneParticipant(sid("mara"), "player"),
                SceneParticipant(sid("mara"), "witness"),
            ),
        )

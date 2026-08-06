from __future__ import annotations

from datetime import UTC, datetime

import pytest

import story_game.domain as domain


def sid(value: str) -> domain.StableId:
    return domain.StableId(value)


def test_story_state_contains_completed_turns_summary_and_sequence_only() -> None:
    assert hasattr(domain, "StoryTurn"), "The target chronology requires StoryTurn"
    assert not hasattr(domain.StoryState(), "events")
    assert not hasattr(domain.StoryState(), "scenes")
    assert not hasattr(domain.StoryState(), "chapters")
    assert not hasattr(domain.StoryState(), "threads")
    assert not hasattr(domain.StoryState(), "goals")

    turn = domain.StoryTurn(
        id=sid("turn-1"),
        sequence=domain.StorySequence(1),
        player_input="Ich öffne die Tür.",
        narration="Die schwere Tür schwingt knarrend auf.",
        based_on_revision=domain.StateRevision(1),
        resulting_revision=domain.StateRevision(2),
        completed_at=datetime(2026, 8, 6, tzinfo=UTC),
    )
    summary = domain.StorySummary(
        through_sequence=domain.StorySequence(1),
        text="Almas hat die Tür geöffnet.",
        based_on_revision=domain.StateRevision(2),
    )

    state = domain.StoryState(
        turns=(turn,),
        summary=summary,
        current_turn_sequence=1,
    )

    assert state.turns == (turn,)
    assert state.summary == summary


def test_story_state_rejects_non_contiguous_turns() -> None:
    assert hasattr(domain, "StoryTurn")
    turn = domain.StoryTurn(
        id=sid("turn-2"),
        sequence=domain.StorySequence(2),
        player_input="Weiter.",
        narration="Die Reise geht weiter.",
        based_on_revision=domain.StateRevision(1),
        resulting_revision=domain.StateRevision(2),
        completed_at=datetime(2026, 8, 6, tzinfo=UTC),
    )

    with pytest.raises(domain.ValidationError):
        domain.StoryState(turns=(turn,), current_turn_sequence=2)


def test_story_state_keeps_the_current_summary_when_a_turn_has_no_replacement() -> None:
    first_turn = domain.StoryTurn(
        id=sid("turn-1"),
        sequence=domain.StorySequence(1),
        player_input="Ich betrete den Dungeon.",
        narration="Almas betritt den Dungeon.",
        based_on_revision=domain.StateRevision(1),
        resulting_revision=domain.StateRevision(2),
        completed_at=datetime(2026, 8, 6, tzinfo=UTC),
    )
    summary = domain.StorySummary(
        through_sequence=domain.StorySequence(1),
        text="Almas ist im Dungeon.",
        based_on_revision=domain.StateRevision(2),
    )
    story = domain.StoryState((first_turn,), summary, 1)
    second_turn = domain.StoryTurn(
        id=sid("turn-2"),
        sequence=domain.StorySequence(2),
        player_input="Ich gehe weiter.",
        narration="Almas folgt dem dunklen Gang.",
        based_on_revision=domain.StateRevision(2),
        resulting_revision=domain.StateRevision(3),
        completed_at=datetime(2026, 8, 6, 1, tzinfo=UTC),
    )

    updated = story.add_turn(second_turn, summary=None)

    assert updated.summary == summary

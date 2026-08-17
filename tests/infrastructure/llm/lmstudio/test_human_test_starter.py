"""Human-inspection bundle: run this yourself with --run-lmstudio-live -s.

    pytest tests/infrastructure/llm/lmstudio/test_human_test_starter.py \
        --run-lmstudio-live -s

Bundles, per flow, the checkpoints a human wants to see: the prepared prompt,
the raw LLM response, the extracted state, and — for the story-turn flow — the
full ``PlayStoryTurn`` run through approval, summary, and commit against an
in-memory store. The actual work happens in ``human_test_support.py`` — these
classes only collect and delegate, per pytest's ``Test*`` collection
convention (a ``Test*`` class with an ``__init__`` is silently dropped, so
each method builds its own support instance instead of sharing one via a
constructor).
"""

from __future__ import annotations

import pytest

from .human_test_support import (
    HumanFullPlaythroughSupport,
    HumanInitStorySupport,
    HumanStoryTurnSupport,
    skip_unless_enabled,
    skip_unless_postgres_available,
)


@pytest.mark.lmstudio_live
class TestInitStoryHuman:
    """Story-Initialisierung: Prompt, LLM-Antwort, extrahierter WorldState."""

    def test_init_prompt(self, request: pytest.FixtureRequest) -> None:
        skip_unless_enabled(request)
        call = HumanInitStorySupport().prepare_prompt()
        assert call.request.initial_prompt

    def test_llm_response(self, request: pytest.FixtureRequest) -> None:
        skip_unless_enabled(request)
        story_state = HumanInitStorySupport().call_llm()
        assert story_state.initialization is not None
        assert story_state.initialization.narration

    def test_state_extract(self, request: pytest.FixtureRequest) -> None:
        skip_unless_enabled(request)
        _story_state, world_state = HumanInitStorySupport().extract_state()
        assert world_state.entities


@pytest.mark.lmstudio_live
class TestStoryTurnHuman:
    """Story-Turn-Generation: Prompt, LLM-Antwort, extrahierte Änderungen."""

    def test_init_prompt(self, request: pytest.FixtureRequest) -> None:
        skip_unless_enabled(request)
        call = HumanStoryTurnSupport().prepare_prompt()
        assert call.request.world_state

    def test_llm_response(self, request: pytest.FixtureRequest) -> None:
        skip_unless_enabled(request)
        narration = HumanStoryTurnSupport().call_llm()
        assert narration

    def test_state_extract(self, request: pytest.FixtureRequest) -> None:
        skip_unless_enabled(request)
        extracted = HumanStoryTurnSupport().extract_state()
        assert extracted.candidate is not None

    def test_full_turn(self, request: pytest.FixtureRequest) -> None:
        """Runs the real PlayStoryTurn — generation, extraction, approval,
        summary, commit — against an in-memory store so nothing but the model
        calls touches anything real."""
        skip_unless_enabled(request)
        played = HumanStoryTurnSupport().play_turn()
        assert played.state.revision.value >= 2


FULL_PLAYTHROUGH_TURN_INPUT = "Ich frage den Wirt nach dem Geheimgang."
"""The one free-text player action the full-playthrough turn takes.

Deliberately declared here, not inside human_test_support.py, so it is the
first thing visible and editable when you want to try a different turn.
"""


@pytest.mark.lmstudio_live
class TestFullPlaythroughHuman:
    """Play one real game: init, then one turn — against real PostgreSQL.

    Closes the gap the STORY-006 completion note in docs/TODO.md flags: no
    other test connects a live model call with live persistence in one run.
    Needs --run-lmstudio-live AND STORY_GAME_POSTGRES_DSN.
    """

    def test_init_and_play_one_turn(self, request: pytest.FixtureRequest) -> None:
        skip_unless_enabled(request)
        skip_unless_postgres_available()
        initialized, played = HumanFullPlaythroughSupport().play(
            FULL_PLAYTHROUGH_TURN_INPUT
        )
        assert initialized.state.revision.value == 1
        assert played.state.revision.value == 2

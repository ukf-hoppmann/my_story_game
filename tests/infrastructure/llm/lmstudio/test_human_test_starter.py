"""Human-inspection bundle: run this yourself with --run-lmstudio-live -s.

    pytest tests/infrastructure/llm/lmstudio/test_human_test_starter.py \
        --run-lmstudio-live -s

Bundles, per flow, the three checkpoints a human wants to see: the prepared
prompt, the raw LLM response, and (where extraction exists) the extracted
state. The actual work happens in ``human_test_support.py`` — these classes
only collect and delegate, per pytest's ``Test*`` collection convention
(a ``Test*`` class with an ``__init__`` is silently dropped, so each method
builds its own support instance instead of sharing one via a constructor).
"""

from __future__ import annotations

import pytest

from .human_test_support import (
    HumanInitStorySupport,
    HumanStoryTurnSupport,
    skip_unless_enabled,
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

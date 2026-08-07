from __future__ import annotations

import os

import pytest

from story_game.application import Success
from story_game.infrastructure.llm.lmstudio import (
    LmStudioClient,
    LmStudioSettings,
    LmStudioStoryGenerationAdapter,
)

from .live_prompt import smoke_call


@pytest.mark.lmstudio_live
def test_live_lmstudio_story_boundary_roundtrip() -> None:
    if os.environ.get("STORY_GAME_LMSTUDIO_LIVE") != "1":
        pytest.skip("Live LM-Studio-Test nur mit STORY_GAME_LMSTUDIO_LIVE=1")
    model_id = os.environ.get("STORY_GAME_LMSTUDIO_MODEL_ID", "").strip()
    if not model_id:
        pytest.fail("STORY_GAME_LMSTUDIO_MODEL_ID ist für den Live-Test erforderlich")

    client = LmStudioClient(LmStudioSettings.from_environment())
    try:
        result = LmStudioStoryGenerationAdapter(client).generate(smoke_call(model_id))
    finally:
        client.close()

    assert isinstance(result, Success), result
    assert "LMSTUDIO_SMOKE_OK" in result.data.text

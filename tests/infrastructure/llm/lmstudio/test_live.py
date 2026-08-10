from __future__ import annotations

from pathlib import Path

import pytest

from story_game.application import Success
from story_game.infrastructure.configuration import LlmTask, TomlLlmConfigurationLoader
from story_game.infrastructure.llm.lmstudio import (
    LmStudioClient,
    LmStudioSettings,
    LmStudioStoryGenerationAdapter,
)

from .live_prompt import smoke_call


@pytest.mark.lmstudio_live
def test_live_lmstudio_story_boundary_roundtrip(
    request: pytest.FixtureRequest,
) -> None:
    # if not request.config.getoption("--run-lmstudio-live"):
        # pytest.skip("Live LM-Studio-Test nur mit --run-lmstudio-live")

    configuration_path = Path(__file__).resolve().parents[4] / "configs" / "llm.toml"
    configuration = TomlLlmConfigurationLoader().load(configuration_path)
    provider = configuration.provider("lmstudio")
    model_selection = configuration.model_for_task(LlmTask.STORY)
    if model_selection.provider_id != "lmstudio":
        pytest.fail("Das Story-Modell muss für diesen Smoke-Test LM Studio verwenden")

    client = LmStudioClient(
        LmStudioSettings(
            base_url=provider.base_url,
            timeout_seconds=provider.timeout_seconds,
        )
    )
    try:
        result = LmStudioStoryGenerationAdapter(client).generate(
            smoke_call(model_selection.model_id)
        )
    finally:
        client.close()

    assert isinstance(result, Success), result
    assert "LMSTUDIO_SMOKE_OK" in result.data.text

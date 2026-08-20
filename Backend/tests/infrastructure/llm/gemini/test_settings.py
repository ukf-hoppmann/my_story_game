from __future__ import annotations

import pytest

from story_game.infrastructure.llm.gemini.settings import DEFAULT_BASE_URL, gemini_settings


def test_gemini_settings_require_a_non_empty_api_key() -> None:
    with pytest.raises(ValueError, match="API-Key"):
        gemini_settings(api_token=None)


def test_gemini_settings_default_to_the_gemini_base_url() -> None:
    settings = gemini_settings(api_token="secret")

    assert (
        settings.base_url
        == DEFAULT_BASE_URL
        == "https://generativelanguage.googleapis.com/v1beta/openai"
    )


def test_gemini_settings_pass_through_the_token_and_timeout() -> None:
    settings = gemini_settings(api_token="secret", timeout_seconds=42.0)

    assert settings.api_token == "secret"
    assert settings.timeout_seconds == 42.0

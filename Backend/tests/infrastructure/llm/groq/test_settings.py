from __future__ import annotations

import pytest

from story_game.infrastructure.llm.groq.settings import DEFAULT_BASE_URL, groq_settings


def test_groq_settings_require_a_non_empty_api_key() -> None:
    with pytest.raises(ValueError, match="API-Key"):
        groq_settings(api_token=None)


def test_groq_settings_default_to_the_groq_base_url() -> None:
    settings = groq_settings(api_token="secret")

    assert settings.base_url == DEFAULT_BASE_URL == "https://api.groq.com/openai/v1"


def test_groq_settings_pass_through_the_token_and_timeout() -> None:
    settings = groq_settings(api_token="secret", timeout_seconds=42.0)

    assert settings.api_token == "secret"
    assert settings.timeout_seconds == 42.0

"""Gemini's own connection-settings invariant: an api_token is mandatory."""

from __future__ import annotations

from ..openai_compatible import OpenAiCompatibleSettings

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


def gemini_settings(
    base_url: str = DEFAULT_BASE_URL,
    *,
    api_token: str | None = None,
    timeout_seconds: float = 60.0,
) -> OpenAiCompatibleSettings:
    """Gemini is a hosted API: every request MUST carry an Authorization header."""
    token = (api_token or "").strip()
    if not token:
        raise ValueError("Gemini benötigt einen API-Key (aus configs/llm.secrets.toml)")
    return OpenAiCompatibleSettings(base_url, api_token=token, timeout_seconds=timeout_seconds)


__all__ = ["DEFAULT_BASE_URL", "gemini_settings"]

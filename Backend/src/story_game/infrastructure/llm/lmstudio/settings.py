"""LM Studio's own connection-settings invariant: no api_token required."""

from __future__ import annotations

from ..openai_compatible import OpenAiCompatibleSettings


def lmstudio_settings(
    base_url: str, *, api_token: str | None = None, timeout_seconds: float = 60.0
) -> OpenAiCompatibleSettings:
    """A local LM Studio instance typically needs no Authorization header."""
    return OpenAiCompatibleSettings(base_url, api_token=api_token, timeout_seconds=timeout_seconds)


__all__ = ["lmstudio_settings"]

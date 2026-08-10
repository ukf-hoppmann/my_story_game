"""Test-only runtime overrides for explicitly activated LM Studio calls."""

from __future__ import annotations

import os


def live_base_url(configured_base_url: str) -> str:
    """Prefer the host-side live endpoint without changing runtime configuration."""
    override = os.environ.get("STORY_LMSTUDIO_LIVE_BASE_URL", "").strip()
    return override or configured_base_url

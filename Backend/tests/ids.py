from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from story_game.domain import StableId


def sid(value: str) -> StableId:
    """Return a deterministic UUID-backed ID for readable test fixtures."""
    return StableId(uuid5(NAMESPACE_URL, f"story-game-test:{value}"))


def uuid_text(value: str) -> str:
    return str(sid(value))

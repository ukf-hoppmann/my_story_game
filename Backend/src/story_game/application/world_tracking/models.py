"""The global world-tracking switch (architecture scope llm-integration §6c)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WorldTrackingSetting:
    """Whether world Extraction runs at story start and on every turn.

    Without a stored value tracking is enabled; ``updated_at`` and
    ``updated_by`` are then ``None``.
    """

    enabled: bool
    updated_at: datetime | None = None
    updated_by: str | None = None


DEFAULT_WORLD_TRACKING = WorldTrackingSetting(enabled=True)


__all__ = ["DEFAULT_WORLD_TRACKING", "WorldTrackingSetting"]

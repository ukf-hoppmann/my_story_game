"""Narrow ports owned by the world-tracking switch."""

from __future__ import annotations

from typing import Protocol

from .models import WorldTrackingSetting


class WorldTrackingStoreError(Exception):
    """The stored world-tracking setting cannot be read or written."""


class WorldTrackingSettingReader(Protocol):
    def load(self) -> WorldTrackingSetting | None:
        """The stored setting, or ``None`` when none was ever saved."""
        ...


class WorldTrackingSettingWriter(Protocol):
    def save(self, setting: WorldTrackingSetting) -> WorldTrackingSetting: ...


class WorldTrackingPolicy(Protocol):
    """Decides whether world Extraction runs (root architecture rule 4)."""

    def extraction_enabled(self) -> bool: ...


__all__ = [
    "WorldTrackingPolicy",
    "WorldTrackingSettingReader",
    "WorldTrackingSettingWriter",
    "WorldTrackingStoreError",
]

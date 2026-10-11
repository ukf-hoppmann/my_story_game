"""In-memory stand-ins for the world-tracking setting, shared by several tests."""

from __future__ import annotations

from story_game.application.world_tracking import (
    WorldTrackingSetting,
    WorldTrackingStoreError,
)


class InMemoryWorldTrackingStore:
    """Reader and writer in one: holds at most one stored setting."""

    def __init__(self, stored: WorldTrackingSetting | None = None) -> None:
        self.stored = stored
        self.fail_with: WorldTrackingStoreError | None = None

    def load(self) -> WorldTrackingSetting | None:
        self._maybe_fail()
        return self.stored

    def save(self, setting: WorldTrackingSetting) -> WorldTrackingSetting:
        self._maybe_fail()
        self.stored = setting
        return setting

    def _maybe_fail(self) -> None:
        if self.fail_with is not None:
            raise self.fail_with


class FixedWorldTrackingPolicy:
    """A policy double that always answers the same."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.calls = 0

    def extraction_enabled(self) -> bool:
        self.calls += 1
        return self.enabled

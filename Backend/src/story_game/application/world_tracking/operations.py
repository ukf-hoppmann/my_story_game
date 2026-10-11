"""Read and change the global world-tracking switch, and the policy built on it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import (
    DiagnosticsLog,
    NullDiagnosticsLog,
    WorldTrackingSettingUnavailable,
)

from .errors import WorldTrackingError, WorldTrackingErrorKind
from .models import DEFAULT_WORLD_TRACKING, WorldTrackingSetting
from .ports import (
    WorldTrackingSettingReader,
    WorldTrackingSettingWriter,
    WorldTrackingStoreError,
)


def _store_unavailable() -> Failure[WorldTrackingError]:
    return Failure(
        WorldTrackingError(
            WorldTrackingErrorKind.STORE_UNAVAILABLE,
            "Die Einstellung zum Welt-Tracking konnte nicht gelesen oder gespeichert werden.",
        )
    )


@dataclass(frozen=True, slots=True)
class GetWorldTrackingRequest:
    pass


class GetWorldTracking:
    """The setting in force; enabled when none was ever stored."""

    def __init__(self, reader: WorldTrackingSettingReader) -> None:
        self._reader = reader

    def apply(
        self, request: GetWorldTrackingRequest
    ) -> OperationResult[WorldTrackingSetting, WorldTrackingError]:
        try:
            stored = self._reader.load()
        except WorldTrackingStoreError:
            return _store_unavailable()
        return Success(stored or DEFAULT_WORLD_TRACKING)


@dataclass(frozen=True, slots=True)
class SetWorldTrackingRequest:
    enabled: bool
    edited_by: str


class SetWorldTracking:
    def __init__(
        self,
        writer: WorldTrackingSettingWriter,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._writer = writer
        self._now = now

    def apply(
        self, request: SetWorldTrackingRequest
    ) -> OperationResult[WorldTrackingSetting, WorldTrackingError]:
        setting = WorldTrackingSetting(request.enabled, self._now(), request.edited_by)
        try:
            return Success(self._writer.save(setting))
        except WorldTrackingStoreError:
            return _store_unavailable()


@dataclass(frozen=True, slots=True)
class WorldTrackingOperations:
    get: GetWorldTracking
    set: SetWorldTracking


class StoredWorldTrackingPolicy:
    """Reads the stored switch anew on every decision.

    If the setting cannot be read, the game keeps tracking the world: that is
    the default and keeps every rule of the llm-integration scope in force.
    """

    def __init__(
        self,
        reader: WorldTrackingSettingReader,
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._reader = reader
        self._diagnostics = diagnostics

    def extraction_enabled(self) -> bool:
        try:
            stored = self._reader.load()
        except WorldTrackingStoreError:
            self._diagnostics.record(WorldTrackingSettingUnavailable())
            return True
        return (stored or DEFAULT_WORLD_TRACKING).enabled


__all__ = [
    "GetWorldTracking",
    "GetWorldTrackingRequest",
    "SetWorldTracking",
    "SetWorldTrackingRequest",
    "StoredWorldTrackingPolicy",
    "WorldTrackingOperations",
]

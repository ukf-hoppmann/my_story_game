"""Expected failures of the world-tracking switch."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorldTrackingErrorKind(StrEnum):
    STORE_UNAVAILABLE = "store_unavailable"


@dataclass(frozen=True, slots=True)
class WorldTrackingError:
    kind: WorldTrackingErrorKind
    message: str


__all__ = ["WorldTrackingError", "WorldTrackingErrorKind"]

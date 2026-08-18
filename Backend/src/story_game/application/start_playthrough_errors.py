"""Typed failure for forking a DRAFT run into a new playthrough."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PlaythroughErrorKind(StrEnum):
    SOURCE_NOT_DRAFT = "source_not_draft"


@dataclass(frozen=True, slots=True)
class PlaythroughError:
    """Failure of starting a playthrough from an existing game run."""

    kind: PlaythroughErrorKind
    message: str

    def __post_init__(self) -> None:
        message = self.message.strip()
        if not message:
            raise ValueError("Playthrough-Fehler benötigen eine Meldung")
        object.__setattr__(self, "message", message)


__all__ = ["PlaythroughError", "PlaythroughErrorKind"]

"""Typed failure shared by the deterministic turn-context selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContextSelectionErrorKind(StrEnum):
    UNKNOWN_CONTROLLED_ENTITY = "unknown_controlled_entity"


@dataclass(frozen=True, slots=True)
class ContextSelectionError:
    """Failure of one context-selection step.

    Context selection is deterministic and works on an already validated
    ``GameState``, so most of its steps cannot fail at all. They still return
    ``Success | Failure`` so that every operation in the story-turn workflow is
    invoked the same way. This type therefore has few kinds on purpose; it is
    not a placeholder for forgotten error handling.
    """

    kind: ContextSelectionErrorKind
    message: str

    def __post_init__(self) -> None:
        message = self.message.strip()
        if not message:
            raise ValueError("Kontextauswahlfehler benötigen eine Meldung")
        object.__setattr__(self, "message", message)

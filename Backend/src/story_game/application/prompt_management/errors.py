"""Expected failures of prompt management."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PromptManagementErrorKind(StrEnum):
    NOT_FOUND = "not_found"
    INVALID_TEXT = "invalid_text"
    INVALID_OPTION = "invalid_option"
    ALREADY_EXISTS = "already_exists"
    NOT_REMOVABLE = "not_removable"
    IN_USE = "in_use"
    SOURCE_UNAVAILABLE = "source_unavailable"
    STORE_UNAVAILABLE = "store_unavailable"


@dataclass(frozen=True, slots=True)
class PromptManagementError:
    kind: PromptManagementErrorKind
    message: str

    def __post_init__(self) -> None:
        message = self.message.strip()
        if not message:
            raise ValueError("Fehlermeldungen dürfen nicht leer sein")
        object.__setattr__(self, "message", message)


__all__ = ["PromptManagementError", "PromptManagementErrorKind"]

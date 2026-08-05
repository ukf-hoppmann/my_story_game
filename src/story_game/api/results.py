"""Resolve typed application results at the HTTP adapter boundary."""

from __future__ import annotations

from typing import TypeVar

from story_game.application.contracts import Failure, OperationResult


DataT = TypeVar("DataT")
ErrorT = TypeVar("ErrorT")


class OperationFailed(Exception):
    """Carry an expected typed failure to FastAPI's exception boundary."""

    def __init__(self, error: object) -> None:
        super().__init__(str(error))
        self.error = error


def unwrap(result: OperationResult[DataT, ErrorT]) -> DataT:
    """Return successful data or raise the adapter-local failure carrier."""
    if isinstance(result, Failure):
        raise OperationFailed(result.error)
    return result.data

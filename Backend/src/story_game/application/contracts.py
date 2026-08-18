"""Shared execution contracts for composable application operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeAlias, TypeVar


InputT = TypeVar("InputT", contravariant=True)
DataT = TypeVar("DataT", covariant=True)
ErrorT = TypeVar("ErrorT", covariant=True)


@dataclass(frozen=True, slots=True)
class Success(Generic[DataT]):
    """A completed operation and its typed value."""

    data: DataT


@dataclass(frozen=True, slots=True)
class Failure(Generic[ErrorT]):
    """An expected operation failure represented as a typed value."""

    error: ErrorT


OperationResult: TypeAlias = Success[DataT] | Failure[ErrorT]


class Operation(Protocol[InputT, DataT, ErrorT]):
    """Execute one typed application operation."""

    def apply(self, request: InputT) -> OperationResult[DataT, ErrorT]: ...

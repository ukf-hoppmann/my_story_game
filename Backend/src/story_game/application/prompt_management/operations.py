"""Prompt-management operations: seed, read, edit and reset versioned prompts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.llm import PromptPackageError
from story_game.domain import StableId

from .errors import PromptManagementError, PromptManagementErrorKind
from .models import (
    NewPromptVersion,
    PromptEntry,
    PromptEntryKind,
    PromptEntryRef,
    PromptPackageReference,
    PromptVersion,
    PromptVersionSource,
)
from .packaging import flatten_package
from .ports import (
    PromptPackageSource,
    PromptStoreError,
    PromptVersionReader,
    PromptVersionWriter,
)

MAX_PROMPT_TEXT_LENGTH = 20000


def _store_unavailable() -> Failure[PromptManagementError]:
    return Failure(
        PromptManagementError(
            PromptManagementErrorKind.STORE_UNAVAILABLE,
            "Die Prompts konnten nicht gelesen oder gespeichert werden.",
        )
    )


def _not_found(what: str) -> Failure[PromptManagementError]:
    return Failure(
        PromptManagementError(PromptManagementErrorKind.NOT_FOUND, f"{what} wurde nicht gefunden.")
    )


def _source_unavailable(error: PromptPackageError) -> Failure[PromptManagementError]:
    return Failure(
        PromptManagementError(
            PromptManagementErrorKind.SOURCE_UNAVAILABLE,
            f"Das Original-Promptpaket ist nicht verfügbar: {error}",
        )
    )


def _new_versions(
    reference: PromptPackageReference,
    entries: tuple[PromptEntry, ...],
    source: PromptVersionSource,
    created_by: str | None,
    new_id: Callable[[], StableId],
    now: datetime,
) -> tuple[NewPromptVersion, ...]:
    return tuple(
        NewPromptVersion(
            new_id(),
            reference.package_id,
            reference.package_version,
            entry,
            source,
            now,
            created_by,
        )
        for entry in entries
    )


@dataclass(frozen=True, slots=True)
class SeedPromptPackagesRequest:
    pass


@dataclass(frozen=True, slots=True)
class SeedPromptPackagesResult:
    seeded: tuple[PromptPackageReference, ...]
    """The packages that had no stored versions yet and were imported."""


class SeedPromptPackages:
    """Import every shipped package that the store does not know yet.

    Only a package without any stored version is imported, so a restart never
    overwrites edits; getting the original back again is an explicit reset.
    """

    def __init__(
        self,
        source: PromptPackageSource,
        reader: PromptVersionReader,
        writer: PromptVersionWriter,
        new_id: Callable[[], StableId],
        clock: Callable[[], datetime],
    ) -> None:
        self._source = source
        self._reader = reader
        self._writer = writer
        self._new_id = new_id
        self._clock = clock

    def apply(
        self, request: SeedPromptPackagesRequest
    ) -> OperationResult[SeedPromptPackagesResult, PromptManagementError]:
        seeded: list[PromptPackageReference] = []
        try:
            for reference in self._source.references():
                if self._reader.list_active(reference.package_id, reference.package_version):
                    continue
                package = self._source.load(reference.package_id, reference.package_version)
                self._writer.append_versions(
                    _new_versions(
                        reference,
                        flatten_package(package),
                        PromptVersionSource.TOML_SEED,
                        None,
                        self._new_id,
                        self._clock(),
                    )
                )
                seeded.append(reference)
        except PromptPackageError as error:
            return _source_unavailable(error)
        except PromptStoreError:
            return _store_unavailable()
        return Success(SeedPromptPackagesResult(tuple(seeded)))


@dataclass(frozen=True, slots=True)
class ListPromptEntriesRequest:
    package_id: str
    package_version: str


class ListPromptEntries:
    def __init__(self, reader: PromptVersionReader) -> None:
        self._reader = reader

    def apply(
        self, request: ListPromptEntriesRequest
    ) -> OperationResult[tuple[PromptVersion, ...], PromptManagementError]:
        try:
            versions = self._reader.list_active(request.package_id, request.package_version)
        except PromptStoreError:
            return _store_unavailable()
        if not versions:
            return _not_found("Das Promptpaket")
        return Success(versions)


@dataclass(frozen=True, slots=True)
class ListPromptHistoryRequest:
    package_id: str
    package_version: str
    kind: PromptEntryKind
    key: str


class ListPromptHistory:
    def __init__(self, reader: PromptVersionReader) -> None:
        self._reader = reader

    def apply(
        self, request: ListPromptHistoryRequest
    ) -> OperationResult[tuple[PromptVersion, ...], PromptManagementError]:
        try:
            versions = self._reader.list_history(
                request.package_id, request.package_version, request.kind, request.key
            )
        except PromptStoreError:
            return _store_unavailable()
        if not versions:
            return _not_found("Der Prompt-Eintrag")
        return Success(versions)


@dataclass(frozen=True, slots=True)
class UpdatePromptTextRequest:
    package_id: str
    package_version: str
    kind: PromptEntryKind
    key: str
    text: str
    editor: str
    """Name recorded as the author of the new version."""


class UpdatePromptText:
    """Append the edited text as the new active version of one entry.

    Saving the text an entry already has is a no-op, so a repeated request
    cannot flood the history.
    """

    def __init__(
        self,
        reader: PromptVersionReader,
        writer: PromptVersionWriter,
        new_id: Callable[[], StableId],
        clock: Callable[[], datetime],
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._new_id = new_id
        self._clock = clock

    def apply(
        self, request: UpdatePromptTextRequest
    ) -> OperationResult[PromptVersion, PromptManagementError]:
        text = request.text.strip()
        if not text or len(text) > MAX_PROMPT_TEXT_LENGTH:
            return Failure(
                PromptManagementError(
                    PromptManagementErrorKind.INVALID_TEXT,
                    "Der Text darf nicht leer sein und höchstens "
                    f"{MAX_PROMPT_TEXT_LENGTH} Zeichen lang sein.",
                )
            )
        reference = PromptPackageReference(request.package_id, request.package_version)
        try:
            current = next(
                (
                    version
                    for version in self._reader.list_active(
                        request.package_id, request.package_version
                    )
                    if version.entry.ref == PromptEntryRef(request.kind, request.key)
                ),
                None,
            )
            if current is None:
                return _not_found("Der Prompt-Eintrag")
            if current.entry.text == text:
                return Success(current)
            created = self._writer.append_versions(
                _new_versions(
                    reference,
                    (_with_text(current.entry, text),),
                    PromptVersionSource.UI,
                    request.editor,
                    self._new_id,
                    self._clock(),
                )
            )
        except PromptStoreError:
            return _store_unavailable()
        return Success(created[0])


@dataclass(frozen=True, slots=True)
class ResetPromptTextRequest:
    package_id: str
    package_version: str
    target: PromptEntryRef | None
    """One entry, or ``None`` for every entry of the package."""
    editor: str
    """Name recorded as the author of the restored versions."""


class ResetPromptText:
    """Append the shipped original as a new version; the edits stay in the history.

    Entries that already carry the original text are skipped.
    """

    def __init__(
        self,
        source: PromptPackageSource,
        reader: PromptVersionReader,
        writer: PromptVersionWriter,
        new_id: Callable[[], StableId],
        clock: Callable[[], datetime],
    ) -> None:
        self._source = source
        self._reader = reader
        self._writer = writer
        self._new_id = new_id
        self._clock = clock

    def apply(
        self, request: ResetPromptTextRequest
    ) -> OperationResult[tuple[PromptVersion, ...], PromptManagementError]:
        reference = PromptPackageReference(request.package_id, request.package_version)
        try:
            originals = {
                entry.ref: entry
                for entry in flatten_package(
                    self._source.load(request.package_id, request.package_version)
                )
            }
        except PromptPackageError as error:
            return _source_unavailable(error)
        try:
            current = {
                version.entry.ref: version.entry
                for version in self._reader.list_active(
                    request.package_id, request.package_version
                )
            }
            if request.target is not None and (
                request.target not in current or request.target not in originals
            ):
                return _not_found("Der Prompt-Eintrag")
            targets = [request.target] if request.target is not None else list(current)
            restored = tuple(
                _with_text(current[ref], originals[ref].text)
                for ref in targets
                if ref in originals and current[ref].text != originals[ref].text
            )
            if not restored:
                return Success(())
            created = self._writer.append_versions(
                _new_versions(
                    reference,
                    restored,
                    PromptVersionSource.TOML_RESET,
                    request.editor,
                    self._new_id,
                    self._clock(),
                )
            )
        except PromptStoreError:
            return _store_unavailable()
        return Success(created)


def _with_text(entry: PromptEntry, text: str) -> PromptEntry:
    return PromptEntry(
        entry.kind, entry.key, text, entry.position, entry.is_default, entry.task_ids
    )


@dataclass(frozen=True, slots=True)
class PromptManagementOperations:
    """The prompt-management operations the HTTP adapter needs, grouped as one value."""

    entries: ListPromptEntries
    history: ListPromptHistory
    update: UpdatePromptText
    reset: ResetPromptText


__all__ = [
    "ListPromptEntries",
    "ListPromptEntriesRequest",
    "ListPromptHistory",
    "ListPromptHistoryRequest",
    "MAX_PROMPT_TEXT_LENGTH",
    "PromptManagementOperations",
    "ResetPromptText",
    "ResetPromptTextRequest",
    "SeedPromptPackages",
    "SeedPromptPackagesRequest",
    "SeedPromptPackagesResult",
    "UpdatePromptText",
    "UpdatePromptTextRequest",
]

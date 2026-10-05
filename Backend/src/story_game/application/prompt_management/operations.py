"""Prompt-management operations: seed, read, edit and reset versioned prompts."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
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
    PromptOptionUsage,
    PromptPackageSource,
    PromptStoreError,
    PromptVersionReader,
    PromptVersionWriter,
)

MAX_PROMPT_TEXT_LENGTH = 20000

EXTENSIBLE_CATEGORIES = ("genre", "tone", "prose_style")
"""Categories that accept new options; the others are fixed by the shipped package."""

_OPTION_ID = re.compile(r"^[a-z][a-z0-9_]{1,39}$")


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


def _valid_text(text: str) -> bool:
    return bool(text) and len(text) <= MAX_PROMPT_TEXT_LENGTH


def _invalid_text() -> Failure[PromptManagementError]:
    return Failure(
        PromptManagementError(
            PromptManagementErrorKind.INVALID_TEXT,
            "Der Text darf nicht leer sein und höchstens "
            f"{MAX_PROMPT_TEXT_LENGTH} Zeichen lang sein.",
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
        if not _valid_text(text):
            return _invalid_text()
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
    kind: PromptEntryKind | None = None
    """With no ``target``: restrict the reset to the entries of this kind."""


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
            targets = (
                [request.target]
                if request.target is not None
                else [ref for ref in current if request.kind in (None, ref.kind)]
            )
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


@dataclass(frozen=True, slots=True)
class CreatePromptOptionRequest:
    package_id: str
    package_version: str
    category_id: str
    option_id: str
    text: str
    editor: str
    """Name recorded as the author of the new option."""


class CreatePromptOption:
    """Add a selectable option to one of the extensible categories.

    The new option is appended to the end of its category and never becomes
    its default; the category itself must already exist in the package.
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
        self, request: CreatePromptOptionRequest
    ) -> OperationResult[PromptVersion, PromptManagementError]:
        if request.category_id not in EXTENSIBLE_CATEGORIES:
            return _invalid_option(
                "Neue Optionen sind nur für " + ", ".join(EXTENSIBLE_CATEGORIES) + " möglich."
            )
        if not _OPTION_ID.fullmatch(request.option_id):
            return _invalid_option(
                "Die Options-ID muss mit einem Kleinbuchstaben beginnen und darf nur "
                "Kleinbuchstaben, Ziffern und Unterstriche enthalten (2 bis 40 Zeichen)."
            )
        text = request.text.strip()
        if not _valid_text(text):
            return _invalid_text()
        key = f"{request.category_id}/{request.option_id}"
        try:
            options = [
                version
                for version in self._reader.list_active(request.package_id, request.package_version)
                if version.entry.kind is PromptEntryKind.OPTION
            ]
            if not any(v.entry.key.startswith(f"{request.category_id}/") for v in options):
                return _not_found("Die Kategorie")
            if any(version.entry.key == key for version in options):
                return Failure(
                    PromptManagementError(
                        PromptManagementErrorKind.ALREADY_EXISTS,
                        f"Die Option {key} gibt es schon.",
                    )
                )
            if any(
                version.entry.key == key
                for version in self._reader.list_archived(
                    request.package_id, request.package_version
                )
            ):
                return Failure(
                    PromptManagementError(
                        PromptManagementErrorKind.ALREADY_EXISTS,
                        f"Die Option {key} liegt im Papierkorb; stelle sie dort wieder her.",
                    )
                )
            position = max(version.entry.position for version in options) + 1
            created = self._writer.append_versions(
                _new_versions(
                    PromptPackageReference(request.package_id, request.package_version),
                    (PromptEntry(PromptEntryKind.OPTION, key, text, position),),
                    PromptVersionSource.UI,
                    request.editor,
                    self._new_id,
                    self._clock(),
                )
            )
        except PromptStoreError:
            return _store_unavailable()
        return Success(created[0])


def _invalid_option(message: str) -> Failure[PromptManagementError]:
    return Failure(PromptManagementError(PromptManagementErrorKind.INVALID_OPTION, message))


@dataclass(frozen=True, slots=True)
class ListCustomPromptOptionsRequest:
    package_id: str
    package_version: str


class ListCustomPromptOptions:
    """The keys of the active options that are not part of the shipped package."""

    def __init__(self, source: PromptPackageSource, reader: PromptVersionReader) -> None:
        self._source = source
        self._reader = reader

    def apply(
        self, request: ListCustomPromptOptionsRequest
    ) -> OperationResult[tuple[str, ...], PromptManagementError]:
        try:
            shipped = {
                entry.ref
                for entry in flatten_package(
                    self._source.load(request.package_id, request.package_version)
                )
            }
        except PromptPackageError as error:
            return _source_unavailable(error)
        try:
            active = self._reader.list_active(request.package_id, request.package_version)
        except PromptStoreError:
            return _store_unavailable()
        return Success(
            tuple(
                version.entry.key
                for version in active
                if version.entry.kind is PromptEntryKind.OPTION and version.entry.ref not in shipped
            )
        )


@dataclass(frozen=True, slots=True)
class ArchivePromptOptionRequest:
    package_id: str
    package_version: str
    category_id: str
    option_id: str


class ArchivePromptOption:
    """Move an option that was added by hand and that no stored game uses to the trash.

    Shipped options cannot be archived, and neither can an option a game
    configuration still selects: that game would fail on its next turn. The
    versions stay in the history and the option can be restored.
    """

    def __init__(
        self,
        source: PromptPackageSource,
        reader: PromptVersionReader,
        writer: PromptVersionWriter,
        usage: PromptOptionUsage,
    ) -> None:
        self._source = source
        self._reader = reader
        self._writer = writer
        self._usage = usage

    def apply(
        self, request: ArchivePromptOptionRequest
    ) -> OperationResult[PromptEntryRef, PromptManagementError]:
        reference = PromptEntryRef(
            PromptEntryKind.OPTION, f"{request.category_id}/{request.option_id}"
        )
        try:
            shipped = {
                entry.ref
                for entry in flatten_package(
                    self._source.load(request.package_id, request.package_version)
                )
            }
        except PromptPackageError as error:
            return _source_unavailable(error)
        try:
            active = {
                version.entry.ref
                for version in self._reader.list_active(request.package_id, request.package_version)
            }
            if reference not in active:
                return _not_found("Die Option")
            if reference in shipped:
                return Failure(
                    PromptManagementError(
                        PromptManagementErrorKind.NOT_REMOVABLE,
                        "Mitgelieferte Optionen lassen sich nicht entfernen; sie lassen sich nur zurücksetzen.",
                    )
                )
            if self._usage.is_option_used(request.category_id, request.option_id):
                return Failure(
                    PromptManagementError(
                        PromptManagementErrorKind.IN_USE,
                        "Die Option wird noch von einer Geschichte verwendet.",
                    )
                )
            self._writer.deactivate_entry(
                request.package_id, request.package_version, reference.kind, reference.key
            )
        except PromptStoreError:
            return _store_unavailable()
        return Success(reference)


def _option_ref(category_id: str, option_id: str) -> PromptEntryRef:
    return PromptEntryRef(PromptEntryKind.OPTION, f"{category_id}/{option_id}")


def _split_option_key(key: str) -> tuple[str, str]:
    category_id, _, option_id = key.partition("/")
    return category_id, option_id


@dataclass(frozen=True, slots=True)
class ListArchivedPromptOptionsRequest:
    package_id: str
    package_version: str


class ListArchivedPromptOptions:
    """The options in the trash: archived, not yet purged."""

    def __init__(self, reader: PromptVersionReader) -> None:
        self._reader = reader

    def apply(
        self, request: ListArchivedPromptOptionsRequest
    ) -> OperationResult[tuple[PromptVersion, ...], PromptManagementError]:
        try:
            archived = self._reader.list_archived(request.package_id, request.package_version)
        except PromptStoreError:
            return _store_unavailable()
        return Success(
            tuple(version for version in archived if version.entry.kind is PromptEntryKind.OPTION)
        )


@dataclass(frozen=True, slots=True)
class RestorePromptOptionRequest:
    package_id: str
    package_version: str
    category_id: str
    option_id: str


class RestorePromptOption:
    """Take an archived option out of the trash; it is active again with its last text."""

    def __init__(self, reader: PromptVersionReader, writer: PromptVersionWriter) -> None:
        self._reader = reader
        self._writer = writer

    def apply(
        self, request: RestorePromptOptionRequest
    ) -> OperationResult[PromptEntryRef, PromptManagementError]:
        reference = _option_ref(request.category_id, request.option_id)
        try:
            archived = {
                version.entry.ref
                for version in self._reader.list_archived(request.package_id, request.package_version)
            }
            if reference not in archived:
                return _not_found("Die Option im Papierkorb")
            self._writer.restore_entry(
                request.package_id, request.package_version, reference.kind, reference.key
            )
        except PromptStoreError:
            return _store_unavailable()
        return Success(reference)


@dataclass(frozen=True, slots=True)
class PurgePromptOptionRequest:
    package_id: str
    package_version: str
    category_id: str
    option_id: str


class PurgePromptOption:
    """Delete an archived option for good, with every version of its history.

    Only an option in the trash can be purged. Shipped options are never
    archived, so they can never be purged either.
    """

    def __init__(self, reader: PromptVersionReader, writer: PromptVersionWriter) -> None:
        self._reader = reader
        self._writer = writer

    def apply(
        self, request: PurgePromptOptionRequest
    ) -> OperationResult[PromptEntryRef, PromptManagementError]:
        reference = _option_ref(request.category_id, request.option_id)
        try:
            archived = {
                version.entry.ref
                for version in self._reader.list_archived(request.package_id, request.package_version)
            }
            if reference not in archived:
                active = {
                    version.entry.ref
                    for version in self._reader.list_active(
                        request.package_id, request.package_version
                    )
                }
                if reference in active:
                    return Failure(
                        PromptManagementError(
                            PromptManagementErrorKind.NOT_ARCHIVED,
                            "Nur Optionen im Papierkorb lassen sich endgültig löschen.",
                        )
                    )
                return _not_found("Die Option im Papierkorb")
            self._writer.purge_entry(
                request.package_id, request.package_version, reference.kind, reference.key
            )
        except PromptStoreError:
            return _store_unavailable()
        return Success(reference)


class RemovalMode(StrEnum):
    """Which step of the lifecycle a bulk removal performs."""

    ARCHIVE = "archive"
    PURGE = "purge"


class RemovalStatus(StrEnum):
    """What happened to one option in a bulk removal."""

    DONE = "done"
    IN_USE = "in_use"
    PROTECTED = "protected"
    NOT_ARCHIVED = "not_archived"
    NOT_FOUND = "not_found"


_BLOCKED_BY = {
    PromptManagementErrorKind.IN_USE: RemovalStatus.IN_USE,
    PromptManagementErrorKind.NOT_REMOVABLE: RemovalStatus.PROTECTED,
    PromptManagementErrorKind.NOT_ARCHIVED: RemovalStatus.NOT_ARCHIVED,
    PromptManagementErrorKind.NOT_FOUND: RemovalStatus.NOT_FOUND,
}


@dataclass(frozen=True, slots=True)
class RemovalOutcome:
    ref: PromptEntryRef
    status: RemovalStatus
    message: str = ""


@dataclass(frozen=True, slots=True)
class RemovePromptOptionsRequest:
    package_id: str
    package_version: str
    mode: RemovalMode
    options: tuple[PromptEntryRef, ...] | None = None
    """The options to remove; ``None`` takes every option the mode applies to
    (all custom options for ``ARCHIVE``, everything in the trash for ``PURGE``)."""


class RemovePromptOptions:
    """Archive or purge several options, one `Leaf` call each.

    Not one transaction: every option gets its own outcome, so a blocked option
    (still in use) does not stop the others. A store that is down fails the
    whole operation. Options already in the target state are not selected, so
    repeating the call is safe.
    """

    def __init__(
        self,
        archive: ArchivePromptOption,
        purge: PurgePromptOption,
        custom_options: ListCustomPromptOptions,
        archived_options: ListArchivedPromptOptions,
    ) -> None:
        self._archive = archive
        self._purge = purge
        self._custom_options = custom_options
        self._archived_options = archived_options

    def apply(
        self, request: RemovePromptOptionsRequest
    ) -> OperationResult[tuple[RemovalOutcome, ...], PromptManagementError]:
        targets = request.options
        if targets is None:
            selected = self._select(request)
            if isinstance(selected, Failure):
                return selected
            targets = selected.data
        outcomes: list[RemovalOutcome] = []
        for ref in targets:
            category_id, option_id = _split_option_key(ref.key)
            result = (
                self._archive.apply(
                    ArchivePromptOptionRequest(
                        request.package_id, request.package_version, category_id, option_id
                    )
                )
                if request.mode is RemovalMode.ARCHIVE
                else self._purge.apply(
                    PurgePromptOptionRequest(
                        request.package_id, request.package_version, category_id, option_id
                    )
                )
            )
            if isinstance(result, Success):
                outcomes.append(RemovalOutcome(ref, RemovalStatus.DONE))
                continue
            blocked = _BLOCKED_BY.get(result.error.kind)
            if blocked is None:
                return result
            outcomes.append(RemovalOutcome(ref, blocked, result.error.message))
        return Success(tuple(outcomes))

    def _select(
        self, request: RemovePromptOptionsRequest
    ) -> OperationResult[tuple[PromptEntryRef, ...], PromptManagementError]:
        if request.mode is RemovalMode.ARCHIVE:
            custom = self._custom_options.apply(
                ListCustomPromptOptionsRequest(request.package_id, request.package_version)
            )
            if isinstance(custom, Failure):
                return custom
            return Success(
                tuple(PromptEntryRef(PromptEntryKind.OPTION, key) for key in custom.data)
            )
        archived = self._archived_options.apply(
            ListArchivedPromptOptionsRequest(request.package_id, request.package_version)
        )
        if isinstance(archived, Failure):
            return archived
        return Success(tuple(version.entry.ref for version in archived.data))


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
    create_option: CreatePromptOption
    custom_options: ListCustomPromptOptions
    archive_option: ArchivePromptOption
    restore_option: RestorePromptOption
    purge_option: PurgePromptOption
    archived_options: ListArchivedPromptOptions
    remove_options: RemovePromptOptions


__all__ = [
    "ArchivePromptOption",
    "ArchivePromptOptionRequest",
    "CreatePromptOption",
    "CreatePromptOptionRequest",
    "EXTENSIBLE_CATEGORIES",
    "ListArchivedPromptOptions",
    "ListArchivedPromptOptionsRequest",
    "ListCustomPromptOptions",
    "ListCustomPromptOptionsRequest",
    "ListPromptEntries",
    "ListPromptEntriesRequest",
    "ListPromptHistory",
    "ListPromptHistoryRequest",
    "MAX_PROMPT_TEXT_LENGTH",
    "PromptManagementOperations",
    "PurgePromptOption",
    "PurgePromptOptionRequest",
    "RemovalMode",
    "RemovalOutcome",
    "RemovalStatus",
    "RemovePromptOptions",
    "RemovePromptOptionsRequest",
    "ResetPromptText",
    "ResetPromptTextRequest",
    "RestorePromptOption",
    "RestorePromptOptionRequest",
    "SeedPromptPackages",
    "SeedPromptPackagesRequest",
    "SeedPromptPackagesResult",
    "UpdatePromptText",
    "UpdatePromptTextRequest",
]

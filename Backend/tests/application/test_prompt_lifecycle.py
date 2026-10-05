"""Archive, restore and purge of options added by hand, singly and in bulk (architecture rule 10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from story_game.application import Failure, Success
from story_game.application.prompt_management import (
    ArchivePromptOption,
    ArchivePromptOptionRequest,
    CreatePromptOption,
    CreatePromptOptionRequest,
    ListArchivedPromptOptions,
    ListArchivedPromptOptionsRequest,
    ListCustomPromptOptions,
    ListPromptEntries,
    ListPromptEntriesRequest,
    PromptEntryKind,
    PromptEntryRef,
    PromptManagementErrorKind,
    PromptStoreError,
    PurgePromptOption,
    PurgePromptOptionRequest,
    RemovalMode,
    RemovalStatus,
    RemovePromptOptions,
    RemovePromptOptionsRequest,
    RestorePromptOption,
    RestorePromptOptionRequest,
    SeedPromptPackages,
    SeedPromptPackagesRequest,
)
from story_game.domain import StableId
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.application.prompt_store_double import FakeOptionUsage, InMemoryPromptStore
from tests.application.test_prompt_management import ADMIN, PACKAGE, PROMPT_ROOT, VERSION


class _Clock:
    def __init__(self) -> None:
        self._now = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self._now += timedelta(minutes=1)
        return self._now


def _ref(key: str) -> PromptEntryRef:
    return PromptEntryRef(PromptEntryKind.OPTION, key)


class _Setup:
    def __init__(self) -> None:
        self.source = FilePromptPackageCatalog(PROMPT_ROOT)
        self.store = InMemoryPromptStore()
        self.usage = FakeOptionUsage()
        clock = _Clock()
        SeedPromptPackages(self.source, self.store, self.store, StableId.new, clock).apply(
            SeedPromptPackagesRequest()
        )
        self.create = CreatePromptOption(self.store, self.store, StableId.new, clock)
        self.archive = ArchivePromptOption(self.source, self.store, self.store, self.usage)
        self.restore = RestorePromptOption(self.store, self.store)
        self.purge = PurgePromptOption(self.store, self.store)
        self.archived = ListArchivedPromptOptions(self.store)
        self.bulk = RemovePromptOptions(
            self.archive,
            self.purge,
            ListCustomPromptOptions(self.source, self.store),
            self.archived,
        )
        self.entries = ListPromptEntries(self.store)

    def add(self, option: str = "melancholic", category: str = "tone"):  # type: ignore[no-untyped-def]
        return self.create.apply(
            CreatePromptOptionRequest(PACKAGE, VERSION, category, option, "Ein Text.", ADMIN)
        )

    def archive_one(self, option: str = "melancholic", category: str = "tone"):  # type: ignore[no-untyped-def]
        return self.archive.apply(ArchivePromptOptionRequest(PACKAGE, VERSION, category, option))

    def restore_one(self, option: str = "melancholic", category: str = "tone"):  # type: ignore[no-untyped-def]
        return self.restore.apply(RestorePromptOptionRequest(PACKAGE, VERSION, category, option))

    def purge_one(self, option: str = "melancholic", category: str = "tone"):  # type: ignore[no-untyped-def]
        return self.purge.apply(PurgePromptOptionRequest(PACKAGE, VERSION, category, option))

    def active_keys(self) -> set[str]:
        result = self.entries.apply(ListPromptEntriesRequest(PACKAGE, VERSION))
        assert isinstance(result, Success)
        return {row.entry.key for row in result.data}

    def archived_keys(self) -> set[str]:
        result = self.archived.apply(ListArchivedPromptOptionsRequest(PACKAGE, VERSION))
        assert isinstance(result, Success)
        return {row.entry.key for row in result.data}

    def remove_all(self, mode: RemovalMode, options: tuple[PromptEntryRef, ...] | None = None):  # type: ignore[no-untyped-def]
        return self.bulk.apply(RemovePromptOptionsRequest(PACKAGE, VERSION, mode, options))


def _statuses(result) -> dict[str, RemovalStatus]:  # type: ignore[no-untyped-def]
    assert isinstance(result, Success)
    return {outcome.ref.key: outcome.status for outcome in result.data}


def test_an_archived_option_leaves_the_active_set_and_lands_in_the_trash() -> None:
    setup = _Setup()
    setup.add()

    assert isinstance(setup.archive_one(), Success)

    assert "tone/melancholic" not in setup.active_keys()
    assert setup.archived_keys() == {"tone/melancholic"}


def test_a_restored_option_is_active_again_with_its_text() -> None:
    setup = _Setup()
    setup.add()
    setup.archive_one()

    result = setup.restore_one()

    assert isinstance(result, Success)
    assert "tone/melancholic" in setup.active_keys()
    assert setup.archived_keys() == set()


def test_only_an_archived_option_can_be_restored() -> None:
    setup = _Setup()
    setup.add()

    result = setup.restore_one()

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.NOT_FOUND


def test_a_purged_option_is_gone_with_its_history() -> None:
    setup = _Setup()
    setup.add()
    setup.archive_one()

    result = setup.purge_one()

    assert isinstance(result, Success)
    assert setup.archived_keys() == set()
    assert not any(row.entry.key == "tone/melancholic" for row in setup.store.rows)


def test_an_active_option_cannot_be_purged() -> None:
    setup = _Setup()
    setup.add()

    result = setup.purge_one()

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.NOT_ARCHIVED
    assert "tone/melancholic" in setup.active_keys()


def test_a_shipped_option_is_never_archived_so_never_purged() -> None:
    setup = _Setup()

    archived = setup.archive_one("dark")
    purged = setup.purge_one("dark")

    assert isinstance(archived, Failure)
    assert archived.error.kind is PromptManagementErrorKind.NOT_REMOVABLE
    assert isinstance(purged, Failure)
    assert "tone/dark" in setup.active_keys()


def test_an_id_in_the_trash_cannot_be_created_again() -> None:
    setup = _Setup()
    setup.add()
    setup.archive_one()

    result = setup.add()

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.ALREADY_EXISTS
    assert "Papierkorb" in result.error.message


@pytest.mark.parametrize("step", ["restore", "purge", "list_archived"])
def test_lifecycle_steps_report_an_unavailable_store(step: str) -> None:
    setup = _Setup()
    setup.add()
    setup.archive_one()
    setup.store.fail_with = PromptStoreError("down")

    result = {
        "restore": setup.restore_one,
        "purge": setup.purge_one,
        "list_archived": lambda: setup.archived.apply(
            ListArchivedPromptOptionsRequest(PACKAGE, VERSION)
        ),
    }[step]()

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.STORE_UNAVAILABLE


def test_bulk_archive_takes_every_unused_custom_option() -> None:
    setup = _Setup()
    setup.add("melancholic")
    setup.add("grim", "genre")

    result = setup.remove_all(RemovalMode.ARCHIVE)

    assert _statuses(result) == {
        "tone/melancholic": RemovalStatus.DONE,
        "genre/grim": RemovalStatus.DONE,
    }
    assert setup.archived_keys() == {"tone/melancholic", "genre/grim"}


def test_bulk_archive_reports_an_option_in_use_and_still_archives_the_rest() -> None:
    setup = _Setup()
    setup.add("melancholic")
    setup.add("grim", "genre")
    setup.usage.used.add(("tone", "melancholic"))

    result = setup.remove_all(RemovalMode.ARCHIVE)

    assert _statuses(result) == {
        "tone/melancholic": RemovalStatus.IN_USE,
        "genre/grim": RemovalStatus.DONE,
    }
    assert "tone/melancholic" in setup.active_keys()
    assert setup.archived_keys() == {"genre/grim"}


def test_bulk_archive_touches_only_the_named_options() -> None:
    setup = _Setup()
    setup.add("melancholic")
    setup.add("grim", "genre")

    result = setup.remove_all(RemovalMode.ARCHIVE, (_ref("genre/grim"),))

    assert _statuses(result) == {"genre/grim": RemovalStatus.DONE}
    assert "tone/melancholic" in setup.active_keys()


def test_bulk_purge_empties_the_trash_and_leaves_active_options_alone() -> None:
    setup = _Setup()
    setup.add("melancholic")
    setup.add("grim", "genre")
    setup.archive_one("grim", "genre")

    result = setup.remove_all(RemovalMode.PURGE)

    assert _statuses(result) == {"genre/grim": RemovalStatus.DONE}
    assert setup.archived_keys() == set()
    assert "tone/melancholic" in setup.active_keys()


def test_repeating_a_bulk_removal_changes_nothing_more() -> None:
    setup = _Setup()
    setup.add()
    setup.remove_all(RemovalMode.ARCHIVE)

    again = setup.remove_all(RemovalMode.ARCHIVE)

    assert isinstance(again, Success)
    assert again.data == ()
    assert setup.archived_keys() == {"tone/melancholic"}


def test_an_explicitly_named_unknown_option_is_reported_as_not_found() -> None:
    setup = _Setup()

    result = setup.remove_all(RemovalMode.PURGE, (_ref("tone/ghost"),))

    assert _statuses(result) == {"tone/ghost": RemovalStatus.NOT_FOUND}


def test_a_bulk_removal_fails_as_a_whole_when_the_store_is_down() -> None:
    setup = _Setup()
    setup.add()
    setup.store.fail_with = PromptStoreError("down")

    result = setup.remove_all(RemovalMode.ARCHIVE)

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.STORE_UNAVAILABLE

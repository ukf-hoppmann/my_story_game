from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from story_game.application import Failure, Success
from story_game.application.llm import InvalidPromptPackageError
from story_game.application.prompt_management import (
    ListPromptEntries,
    ListPromptEntriesRequest,
    ListPromptHistory,
    ListPromptHistoryRequest,
    PromptEntryKind,
    PromptEntryRef,
    PromptManagementErrorKind,
    PromptPackageReference,
    PromptStoreError,
    PromptVersionSource,
    ResetPromptText,
    ResetPromptTextRequest,
    SeedPromptPackages,
    SeedPromptPackagesRequest,
    UpdatePromptText,
    UpdatePromptTextRequest,
    assemble_package,
    flatten_package,
)
from story_game.domain import StableId
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.application.prompt_store_double import InMemoryPromptStore

PROMPT_ROOT = Path(__file__).parents[2] / "prompts"
PACKAGE = "story.base"
VERSION = "1"
REFERENCE = PromptPackageReference(PACKAGE, VERSION)
ADMIN = "testadmin"
TASK = PromptEntryRef(PromptEntryKind.TASK, "story_generation")
OPTION = PromptEntryRef(PromptEntryKind.OPTION, "tone/balanced")


class _Clock:
    def __init__(self) -> None:
        self._now = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self._now += timedelta(minutes=1)
        return self._now


class _Operations:
    def __init__(self) -> None:
        self.source = FilePromptPackageCatalog(PROMPT_ROOT)
        self.store = InMemoryPromptStore()
        clock = _Clock()
        self.seed = SeedPromptPackages(self.source, self.store, self.store, StableId.new, clock)
        self.entries = ListPromptEntries(self.store)
        self.history = ListPromptHistory(self.store)
        self.update = UpdatePromptText(self.store, self.store, StableId.new, clock)
        self.reset = ResetPromptText(
            self.source, self.store, self.store, StableId.new, clock
        )

    def seeded(self) -> _Operations:
        assert isinstance(self.seed.apply(SeedPromptPackagesRequest()), Success)
        return self

    def edit(self, ref: PromptEntryRef, text: str):  # type: ignore[no-untyped-def]
        return self.update.apply(
            UpdatePromptTextRequest(PACKAGE, VERSION, ref.kind, ref.key, text, ADMIN)
        )

    def current_text(self, ref: PromptEntryRef) -> str:
        result = self.entries.apply(ListPromptEntriesRequest(PACKAGE, VERSION))
        assert isinstance(result, Success)
        return next(
            row.entry.text
            for row in result.data
            if (row.entry.kind, row.entry.key) == (ref.kind, ref.key)
        )

    def assembled(self):  # type: ignore[no-untyped-def]
        result = self.entries.apply(ListPromptEntriesRequest(PACKAGE, VERSION))
        assert isinstance(result, Success)
        return assemble_package(PACKAGE, VERSION, tuple(row.entry for row in result.data))


def _original():  # type: ignore[no-untyped-def]
    return FilePromptPackageCatalog(PROMPT_ROOT).load(PACKAGE, VERSION)


def test_flattening_and_assembling_a_package_round_trips() -> None:
    original = _original()

    assert assemble_package(PACKAGE, VERSION, flatten_package(original)) == original


def test_assembling_rejects_a_category_without_exactly_one_default_option() -> None:
    entries = [
        entry
        for entry in flatten_package(_original())
        if not (entry.kind == PromptEntryKind.OPTION and entry.is_default)
        or not entry.key.startswith("tone/")
    ]

    with pytest.raises(InvalidPromptPackageError):
        assemble_package(PACKAGE, VERSION, tuple(entries))


def test_seeding_imports_every_toml_package_into_an_empty_store() -> None:
    ops = _Operations()

    result = ops.seed.apply(SeedPromptPackagesRequest())

    assert isinstance(result, Success)
    assert result.data.seeded == (REFERENCE,)
    assert ops.assembled() == _original()
    assert {row.source for row in ops.store.rows} == {PromptVersionSource.TOML_SEED}
    assert all(row.created_by is None for row in ops.store.rows)


def test_seeding_again_changes_nothing_and_keeps_edits() -> None:
    ops = _Operations().seeded()
    ops.edit(TASK, "Geänderter Prompt")
    rows_before = list(ops.store.rows)

    result = ops.seed.apply(SeedPromptPackagesRequest())

    assert isinstance(result, Success)
    assert result.data.seeded == ()
    assert ops.store.rows == rows_before
    assert ops.current_text(TASK) == "Geänderter Prompt"


def test_an_edit_creates_a_new_active_version_and_deactivates_the_old_one() -> None:
    ops = _Operations().seeded()

    result = ops.edit(TASK, "  Neuer Prompt  ")

    assert isinstance(result, Success)
    assert result.data.entry.text == "Neuer Prompt"
    assert result.data.source == PromptVersionSource.UI
    assert result.data.created_by == "testadmin"
    assert result.data.is_active
    history = ops.history.apply(
        ListPromptHistoryRequest(PACKAGE, VERSION, TASK.kind, TASK.key)
    )
    assert isinstance(history, Success)
    assert [(row.source, row.is_active) for row in history.data] == [
        (PromptVersionSource.UI, True),
        (PromptVersionSource.TOML_SEED, False),
    ]
    assert history.data[1].entry.text == _original().task("story_generation").text


def test_an_edit_keeps_structure_and_every_other_entry_unchanged() -> None:
    ops = _Operations().seeded()

    ops.edit(OPTION, "Ausgewogene Stimmung")

    expected = _original()
    assembled = ops.assembled()
    assert assembled.tasks == expected.tasks
    assert assembled.directives == expected.directives
    tone = assembled.category("tone")
    assert tone.default_option_id == expected.category("tone").default_option_id
    assert tone.option("balanced").description == "Ausgewogene Stimmung"
    assert [option.id for option in tone.options] == [
        option.id for option in expected.category("tone").options
    ]


@pytest.mark.parametrize("text", ["", "   \n", "x" * 20001])
def test_an_invalid_text_is_rejected_and_nothing_is_written(text: str) -> None:
    ops = _Operations().seeded()
    rows_before = list(ops.store.rows)

    result = ops.edit(TASK, text)

    assert isinstance(result, Failure)
    assert result.error.kind == PromptManagementErrorKind.INVALID_TEXT
    assert ops.store.rows == rows_before


def test_editing_an_unknown_entry_is_not_found() -> None:
    ops = _Operations().seeded()

    result = ops.edit(PromptEntryRef(PromptEntryKind.TASK, "unknown"), "Text")

    assert isinstance(result, Failure)
    assert result.error.kind == PromptManagementErrorKind.NOT_FOUND


def test_saving_the_current_text_again_creates_no_new_version() -> None:
    ops = _Operations().seeded()
    ops.edit(TASK, "Text")
    rows_before = list(ops.store.rows)

    result = ops.edit(TASK, "Text")

    assert isinstance(result, Success)
    assert result.data.entry.text == "Text"
    assert ops.store.rows == rows_before


def test_resetting_an_entry_appends_the_original_as_a_new_version() -> None:
    ops = _Operations().seeded()
    ops.edit(TASK, "Geändert")

    result = ops.reset.apply(ResetPromptTextRequest(PACKAGE, VERSION, TASK, ADMIN))

    assert isinstance(result, Success)
    assert [row.source for row in result.data] == [PromptVersionSource.TOML_RESET]
    assert ops.current_text(TASK) == _original().task("story_generation").text
    history = ops.history.apply(
        ListPromptHistoryRequest(PACKAGE, VERSION, TASK.kind, TASK.key)
    )
    assert isinstance(history, Success)
    assert [row.source for row in history.data] == [
        PromptVersionSource.TOML_RESET,
        PromptVersionSource.UI,
        PromptVersionSource.TOML_SEED,
    ]


def test_resetting_an_unchanged_entry_writes_nothing() -> None:
    ops = _Operations().seeded()
    rows_before = list(ops.store.rows)

    result = ops.reset.apply(ResetPromptTextRequest(PACKAGE, VERSION, TASK, ADMIN))

    assert isinstance(result, Success)
    assert result.data == ()
    assert ops.store.rows == rows_before


def test_resetting_the_whole_package_restores_only_changed_entries() -> None:
    ops = _Operations().seeded()
    ops.edit(TASK, "Geändert 1")
    ops.edit(OPTION, "Geändert 2")
    untouched = PromptEntryRef(PromptEntryKind.TASK, "story_summary")
    untouched_history_before = len(
        ops.history.apply(
            ListPromptHistoryRequest(PACKAGE, VERSION, untouched.kind, untouched.key)
        ).data  # type: ignore[union-attr]
    )

    result = ops.reset.apply(ResetPromptTextRequest(PACKAGE, VERSION, None, ADMIN))

    assert isinstance(result, Success)
    assert {(row.entry.kind, row.entry.key) for row in result.data} == {
        (TASK.kind, TASK.key),
        (OPTION.kind, OPTION.key),
    }
    assert ops.assembled() == _original()
    assert (
        len(
            ops.history.apply(
                ListPromptHistoryRequest(PACKAGE, VERSION, untouched.kind, untouched.key)
            ).data  # type: ignore[union-attr]
        )
        == untouched_history_before
    )


def test_listing_an_unknown_package_is_not_found() -> None:
    ops = _Operations()

    result = ops.entries.apply(ListPromptEntriesRequest(PACKAGE, VERSION))

    assert isinstance(result, Failure)
    assert result.error.kind == PromptManagementErrorKind.NOT_FOUND


def test_a_failing_store_becomes_a_typed_failure() -> None:
    ops = _Operations().seeded()
    ops.store.fail_with = PromptStoreError("db down")

    results = [
        ops.entries.apply(ListPromptEntriesRequest(PACKAGE, VERSION)),
        ops.history.apply(ListPromptHistoryRequest(PACKAGE, VERSION, TASK.kind, TASK.key)),
        ops.edit(TASK, "Text"),
        ops.reset.apply(ResetPromptTextRequest(PACKAGE, VERSION, None, ADMIN)),
        ops.seed.apply(SeedPromptPackagesRequest()),
    ]

    for result in results:
        assert isinstance(result, Failure)
        assert result.error.kind == PromptManagementErrorKind.STORE_UNAVAILABLE

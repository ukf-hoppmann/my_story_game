"""Adding and removing selectable options (genre, tone, prose style) of the prompt catalog."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from story_game.application import Failure, Success
from story_game.application.prompt_management import (
    CreatePromptOption,
    CreatePromptOptionRequest,
    ListCustomPromptOptions,
    ListCustomPromptOptionsRequest,
    ListPromptEntries,
    ListPromptEntriesRequest,
    PromptEntryKind,
    PromptManagementErrorKind,
    PromptStoreError,
    PromptVersionSource,
    ArchivePromptOption,
    ArchivePromptOptionRequest,
    ResetPromptText,
    ResetPromptTextRequest,
    SeedPromptPackages,
    SeedPromptPackagesRequest,
    assemble_package,
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
        self.remove = ArchivePromptOption(self.source, self.store, self.store, self.usage)
        self.custom = ListCustomPromptOptions(self.source, self.store)
        self.entries = ListPromptEntries(self.store)

    def add(self, category: str = "tone", option: str = "melancholic", text: str = "Wehmütig."):  # type: ignore[no-untyped-def]
        return self.create.apply(
            CreatePromptOptionRequest(PACKAGE, VERSION, category, option, text, ADMIN)
        )

    def drop(self, category: str = "tone", option: str = "melancholic"):  # type: ignore[no-untyped-def]
        return self.remove.apply(ArchivePromptOptionRequest(PACKAGE, VERSION, category, option))

    def keys(self) -> set[str]:
        result = self.entries.apply(ListPromptEntriesRequest(PACKAGE, VERSION))
        assert isinstance(result, Success)
        return {row.entry.key for row in result.data}

    def package(self):  # type: ignore[no-untyped-def]
        result = self.entries.apply(ListPromptEntriesRequest(PACKAGE, VERSION))
        assert isinstance(result, Success)
        return assemble_package(PACKAGE, VERSION, tuple(row.entry for row in result.data))


@pytest.mark.parametrize("category", ["genre", "tone", "prose_style"])
def test_a_new_option_becomes_selectable_in_its_category(category: str) -> None:
    setup = _Setup()

    result = setup.add(category, "my_option", "Ein eigener Text.")

    assert isinstance(result, Success)
    assert result.data.entry.key == f"{category}/my_option"
    assert result.data.source is PromptVersionSource.UI
    assert result.data.created_by == ADMIN
    assert not result.data.entry.is_default
    options = setup.package().category(category).options
    assert options[-1].id == "my_option"
    assert options[-1].description == "Ein eigener Text."


def test_adding_an_option_keeps_the_default_of_the_category() -> None:
    setup = _Setup()
    default_before = setup.package().category("tone").default_option_id

    setup.add()

    assert setup.package().category("tone").default_option_id == default_before


@pytest.mark.parametrize("category", ["pacing", "length", "content_profile", "no_such_category"])
def test_only_genre_tone_and_prose_style_accept_new_options(category: str) -> None:
    setup = _Setup()

    result = setup.add(category, "my_option")

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.INVALID_OPTION
    assert f"{category}/my_option" not in setup.keys()


@pytest.mark.parametrize("option", ["", "a", "Melancholic", "mit leerzeichen", "mit/slash", "1abc", "x" * 41])
def test_an_option_id_must_be_a_short_lowercase_slug(option: str) -> None:
    setup = _Setup()

    result = setup.add("tone", option)

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.INVALID_OPTION


def test_an_existing_option_cannot_be_added_again() -> None:
    setup = _Setup()

    result = setup.add("tone", "dark")

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.ALREADY_EXISTS


def test_a_new_option_needs_a_text() -> None:
    setup = _Setup()

    result = setup.add(text="   ")

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.INVALID_TEXT


def test_adding_reports_an_unavailable_store() -> None:
    setup = _Setup()
    setup.store.fail_with = PromptStoreError("down")

    result = setup.add()

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.STORE_UNAVAILABLE


def test_only_options_added_by_hand_are_listed_as_custom() -> None:
    setup = _Setup()
    setup.add()

    result = setup.custom.apply(ListCustomPromptOptionsRequest(PACKAGE, VERSION))

    assert isinstance(result, Success)
    assert result.data == ("tone/melancholic",)


def test_an_unused_added_option_can_be_archived_and_stays_in_the_history() -> None:
    setup = _Setup()
    setup.add()

    result = setup.drop()

    assert isinstance(result, Success)
    assert "tone/melancholic" not in setup.keys()
    assert "melancholic" not in [o.id for o in setup.package().category("tone").options]
    assert any(row.entry.key == "tone/melancholic" for row in setup.store.rows)


def test_an_option_that_a_run_still_uses_cannot_be_removed() -> None:
    setup = _Setup()
    setup.add()
    setup.usage.used.add(("tone", "melancholic"))

    result = setup.drop()

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.IN_USE
    assert "tone/melancholic" in setup.keys()


def test_a_shipped_option_cannot_be_removed() -> None:
    setup = _Setup()

    result = setup.drop("tone", "dark")

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.NOT_REMOVABLE
    assert "tone/dark" in setup.keys()


def test_removing_an_unknown_option_is_not_found() -> None:
    setup = _Setup()

    result = setup.drop("tone", "never_added")

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.NOT_FOUND


def test_removing_reports_an_unavailable_usage_check() -> None:
    setup = _Setup()
    setup.add()
    setup.usage.fail_with = PromptStoreError("down")

    result = setup.drop()

    assert isinstance(result, Failure)
    assert result.error.kind is PromptManagementErrorKind.STORE_UNAVAILABLE
    assert "tone/melancholic" in setup.keys()


def test_resetting_everything_leaves_added_options_alone() -> None:
    setup = _Setup()
    setup.add()
    reset = ResetPromptText(setup.source, setup.store, setup.store, StableId.new, _Clock())

    result = reset.apply(ResetPromptTextRequest(PACKAGE, VERSION, None, ADMIN))

    assert isinstance(result, Success)
    assert "tone/melancholic" in setup.keys()


def test_the_kind_of_an_added_option_is_option() -> None:
    setup = _Setup()

    result = setup.add()

    assert isinstance(result, Success)
    assert result.data.entry.kind is PromptEntryKind.OPTION

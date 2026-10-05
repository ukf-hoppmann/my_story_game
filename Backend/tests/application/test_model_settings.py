from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from story_game.application import Failure, Success
from story_game.application.llm import (
    GenerationConfiguration,
    GenerationOptions,
    GenerationTask,
    LLMErrorKind,
    ModelSelection,
)
from story_game.application.model_settings import (
    ListModelSettingHistory,
    ListModelSettingHistoryRequest,
    ListModelSettings,
    ListModelSettingsRequest,
    ManagedGenerationConfigurationResolver,
    ModelSettingsError,
    ModelSettingsErrorKind,
    ModelSettingsSourceError,
    ModelSettingsStoreError,
    ModelSettingSource,
    ResetModelSettings,
    ResetModelSettingsRequest,
    SeedModelSettings,
    SeedModelSettingsRequest,
    UpdateModelSetting,
    UpdateModelSettingRequest,
)
from story_game.domain import StableId
from tests.application.model_settings_double import (
    InMemoryModelSettingsStore,
    FakeModelSource,
)

EDITOR = "testadmin"
STORY = GenerationTask.STORY
SUMMARY = GenerationTask.SUMMARY


class _Clock:
    def __init__(self) -> None:
        self._now = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self._now += timedelta(minutes=1)
        return self._now


class _Operations:
    def __init__(self) -> None:
        self.source = FakeModelSource()
        self.store = InMemoryModelSettingsStore()
        clock = _Clock()
        self.seed = SeedModelSettings(self.source, self.store, self.store, StableId.new, clock)
        self.list = ListModelSettings(self.store, self.source)
        self.history = ListModelSettingHistory(self.store)
        self.update = UpdateModelSetting(
            self.store, self.store, self.source, StableId.new, clock
        )
        self.reset = ResetModelSettings(
            self.source, self.store, self.store, StableId.new, clock
        )
        self.resolver = ManagedGenerationConfigurationResolver(self.store, self.source)

    def seeded(self) -> _Operations:
        assert isinstance(self.seed.apply(SeedModelSettingsRequest()), Success)
        return self

    def edit(self, task=STORY, model_ref="model.story.groq", temperature=0.9, max_tokens=None):  # type: ignore[no-untyped-def]
        return self.update.apply(
            UpdateModelSettingRequest(task, model_ref, temperature, max_tokens, EDITOR)
        )

    def active(self, task):  # type: ignore[no-untyped-def]
        result = self.list.apply(ListModelSettingsRequest())
        assert isinstance(result, Success)
        return next(v for v in result.data.settings if v.setting.task == task)


def test_seeding_imports_one_setting_per_task_from_the_originals() -> None:
    ops = _Operations()

    result = ops.seed.apply(SeedModelSettingsRequest())

    assert isinstance(result, Success)
    assert result.data.seeded is True
    assert {row.setting.task for row in ops.store.rows} == set(GenerationTask)
    assert {row.source for row in ops.store.rows} == {ModelSettingSource.TOML_SEED}
    assert all(row.created_by is None for row in ops.store.rows)


def test_seeding_again_changes_nothing_and_keeps_edits() -> None:
    ops = _Operations().seeded()
    ops.edit()
    rows_before = list(ops.store.rows)

    result = ops.seed.apply(SeedModelSettingsRequest())

    assert isinstance(result, Success)
    assert result.data.seeded is False
    assert ops.store.rows == rows_before


def test_listing_returns_the_active_settings_and_the_selectable_models() -> None:
    ops = _Operations().seeded()

    result = ops.list.apply(ListModelSettingsRequest())

    assert isinstance(result, Success)
    assert [v.setting.task for v in result.data.settings] == list(GenerationTask)
    assert {c.model_ref for c in result.data.candidates if c.task == STORY} == {
        "model.story.default",
        "model.story.groq",
    }


def test_an_edit_appends_a_version_and_keeps_the_history() -> None:
    ops = _Operations().seeded()

    result = ops.edit(temperature=0.9, max_tokens=800)

    assert isinstance(result, Success)
    assert result.data.source == ModelSettingSource.UI
    assert result.data.created_by == EDITOR
    assert (result.data.setting.model_ref, result.data.setting.temperature) == (
        "model.story.groq",
        0.9,
    )
    assert result.data.setting.max_output_tokens == 800
    history = ops.history.apply(ListModelSettingHistoryRequest(STORY))
    assert isinstance(history, Success)
    assert [(v.source, v.is_active) for v in history.data] == [
        (ModelSettingSource.UI, True),
        (ModelSettingSource.TOML_SEED, False),
    ]
    assert ops.active(SUMMARY).source == ModelSettingSource.TOML_SEED


def test_saving_the_current_values_again_creates_no_version() -> None:
    ops = _Operations().seeded()
    ops.edit()
    rows_before = list(ops.store.rows)

    result = ops.edit()

    assert isinstance(result, Success)
    assert ops.store.rows == rows_before


@pytest.mark.parametrize(
    ("kwargs", "kind"),
    [
        ({"model_ref": "model.summary.default"}, ModelSettingsErrorKind.INVALID_MODEL),
        ({"model_ref": "model.unknown"}, ModelSettingsErrorKind.INVALID_MODEL),
        ({"temperature": -0.1}, ModelSettingsErrorKind.INVALID_OPTIONS),
        ({"temperature": 2.5}, ModelSettingsErrorKind.INVALID_OPTIONS),
        ({"max_tokens": 0}, ModelSettingsErrorKind.INVALID_OPTIONS),
    ],
)
def test_invalid_input_is_rejected_and_nothing_is_written(kwargs, kind) -> None:  # type: ignore[no-untyped-def]
    ops = _Operations().seeded()
    rows_before = list(ops.store.rows)

    result = ops.edit(**kwargs)

    assert isinstance(result, Failure)
    assert result.error.kind == kind
    assert ops.store.rows == rows_before


def test_resetting_one_task_restores_the_original_as_a_new_version() -> None:
    ops = _Operations().seeded()
    ops.edit()

    result = ops.reset.apply(ResetModelSettingsRequest(STORY, EDITOR))

    assert isinstance(result, Success)
    assert [v.source for v in result.data] == [ModelSettingSource.TOML_RESET]
    assert ops.active(STORY).setting.model_ref == "model.story.default"
    history = ops.history.apply(ListModelSettingHistoryRequest(STORY))
    assert isinstance(history, Success)
    assert [v.source for v in history.data] == [
        ModelSettingSource.TOML_RESET,
        ModelSettingSource.UI,
        ModelSettingSource.TOML_SEED,
    ]


def test_resetting_unchanged_settings_writes_nothing() -> None:
    ops = _Operations().seeded()
    rows_before = list(ops.store.rows)

    result = ops.reset.apply(ResetModelSettingsRequest(None, EDITOR))

    assert isinstance(result, Success)
    assert result.data == ()
    assert ops.store.rows == rows_before


def test_resetting_everything_restores_only_changed_tasks() -> None:
    ops = _Operations().seeded()
    ops.edit(task=STORY)
    ops.edit(task=SUMMARY, model_ref="model.summary.groq")

    result = ops.reset.apply(ResetModelSettingsRequest(None, EDITOR))

    assert isinstance(result, Success)
    assert {v.setting.task for v in result.data} == {STORY, SUMMARY}


def test_the_history_of_an_unseeded_task_is_not_found() -> None:
    result = _Operations().history.apply(ListModelSettingHistoryRequest(STORY))

    assert isinstance(result, Failure)
    assert result.error.kind == ModelSettingsErrorKind.NOT_FOUND


def test_the_resolver_returns_the_active_selection_and_options() -> None:
    ops = _Operations().seeded()

    first = ops.resolver.resolve(STORY)
    ops.edit(temperature=0.9, max_tokens=800)
    second = ops.resolver.resolve(STORY)

    assert first == Success(
        GenerationConfiguration(
            ModelSelection("lmstudio", "lmstudio-story"), GenerationOptions(0.5, None)
        )
    )
    assert second == Success(
        GenerationConfiguration(
            ModelSelection("groq", "groq-story"), GenerationOptions(0.9, 800)
        )
    )


def test_the_resolver_fails_with_a_configuration_error_when_nothing_is_stored() -> None:
    result = _Operations().resolver.resolve(STORY)

    assert isinstance(result, Failure)
    assert result.error.kind == LLMErrorKind.CONFIGURATION


def test_the_resolver_fails_when_the_stored_model_left_the_catalog() -> None:
    ops = _Operations().seeded()
    ops.edit()
    ops.source.candidate_list = tuple(
        c for c in ops.source.candidate_list if c.model_ref != "model.story.groq"
    )

    result = ops.resolver.resolve(STORY)

    assert isinstance(result, Failure)
    assert result.error.kind == LLMErrorKind.CONFIGURATION


def test_failing_ports_become_typed_failures() -> None:
    ops = _Operations().seeded()
    ops.store.fail_with = ModelSettingsStoreError("db down")

    store_results = [
        ops.list.apply(ListModelSettingsRequest()),
        ops.history.apply(ListModelSettingHistoryRequest(STORY)),
        ops.edit(),
        ops.reset.apply(ResetModelSettingsRequest(None, EDITOR)),
        ops.seed.apply(SeedModelSettingsRequest()),
    ]
    for result in store_results:
        assert isinstance(result, Failure)
        assert result.error.kind == ModelSettingsErrorKind.STORE_UNAVAILABLE
    assert ops.resolver.resolve(STORY).error.kind == LLMErrorKind.CONFIGURATION  # type: ignore[union-attr]

    ops.store.fail_with = None
    ops.source.fail_with = ModelSettingsSourceError("toml broken")
    source_results = [
        ops.edit(),
        ops.reset.apply(ResetModelSettingsRequest(None, EDITOR)),
        ops.list.apply(ListModelSettingsRequest()),
    ]
    for result in source_results:
        assert isinstance(result, Failure)
        assert result.error.kind == ModelSettingsErrorKind.SOURCE_UNAVAILABLE


def test_the_error_type_is_a_closed_value() -> None:
    error = ModelSettingsError(ModelSettingsErrorKind.NOT_FOUND, " x ")

    assert error.message == "x"

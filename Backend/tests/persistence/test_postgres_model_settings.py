from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("psycopg")

from story_game.application.llm import GenerationTask  # noqa: E402
from story_game.application.model_settings import (  # noqa: E402
    ModelSettingsStoreError,
    ModelSettingSource,
    NewModelSettingVersion,
    TaskModelSetting,
)
from story_game.domain import StableId  # noqa: E402
from tests.persistence.model_settings_isolation import parked_model_settings  # noqa: E402
from tests.persistence.test_postgres_persistence import postgres_store  # noqa: E402,F401

CREATED = datetime(2026, 10, 5, 12, tzinfo=UTC)


@pytest.fixture
def settings_store(postgres_store):  # noqa: F811
    from story_game.infrastructure.persistence.postgres import PostgresModelSettingsStore

    _, connections = postgres_store
    with parked_model_settings(connections):
        yield PostgresModelSettingsStore(connections)


def new(task, ref="model.x", temperature=0.5, tokens=None, *, minutes=0, source=ModelSettingSource.TOML_SEED, by=None):
    return NewModelSettingVersion(
        StableId.new(),
        TaskModelSetting(task, ref, temperature, tokens),
        source,
        CREATED + timedelta(minutes=minutes),
        by,
    )


def test_settings_roundtrip_including_null_options(settings_store) -> None:
    settings_store.append_versions(
        [
            new(GenerationTask.STORY, "model.story.a", 0.7, 900),
            new(GenerationTask.EXTRACTION, "model.extraction.a", None, None),
        ]
    )

    active = {v.setting.task: v.setting for v in settings_store.list_active()}

    assert active[GenerationTask.STORY] == TaskModelSetting(
        GenerationTask.STORY, "model.story.a", 0.7, 900
    )
    assert active[GenerationTask.EXTRACTION].temperature is None
    assert active[GenerationTask.EXTRACTION].max_output_tokens is None


def test_a_new_version_deactivates_the_old_one_and_keeps_the_history(settings_store) -> None:
    settings_store.append_versions([new(GenerationTask.STORY, "model.story.a")])

    settings_store.append_versions(
        [
            new(
                GenerationTask.STORY,
                "model.story.b",
                0.9,
                minutes=1,
                source=ModelSettingSource.UI,
                by="testadmin",
            )
        ]
    )

    history = settings_store.list_history(GenerationTask.STORY)
    assert [(v.setting.model_ref, v.source, v.created_by, v.is_active) for v in history] == [
        ("model.story.b", ModelSettingSource.UI, "testadmin", True),
        ("model.story.a", ModelSettingSource.TOML_SEED, None, False),
    ]
    assert [v.setting.model_ref for v in settings_store.list_active()] == ["model.story.b"]


def test_a_failing_batch_is_rolled_back_completely(settings_store) -> None:
    settings_store.append_versions([new(GenerationTask.STORY, "model.story.a")])
    duplicate = StableId.new()

    with pytest.raises(ModelSettingsStoreError):
        settings_store.append_versions(
            [
                NewModelSettingVersion(
                    duplicate,
                    TaskModelSetting(GenerationTask.STORY, "model.story.b", 0.5, None),
                    ModelSettingSource.UI,
                    CREATED,
                    "x",
                ),
                NewModelSettingVersion(
                    duplicate,
                    TaskModelSetting(GenerationTask.SUMMARY, "model.summary.a", 0.5, None),
                    ModelSettingSource.UI,
                    CREATED,
                    "x",
                ),
            ]
        )

    assert [v.setting.model_ref for v in settings_store.list_active()] == ["model.story.a"]

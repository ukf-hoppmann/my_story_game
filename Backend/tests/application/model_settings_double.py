"""In-memory stand-ins for the model-settings ports, shared by several tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from story_game.application.llm import GenerationTask
from story_game.application.model_settings import (
    ModelCandidate,
    ModelSettingsSourceError,
    ModelSettingsStoreError,
    ModelSettingVersion,
    NewModelSettingVersion,
    TaskModelSetting,
)

CANDIDATES = tuple(
    ModelCandidate(task, f"model.{task.value}.{name}", provider, f"{provider}-{task.value}")
    for task in GenerationTask
    for name, provider in (("default", "lmstudio"), ("groq", "groq"))
)
ORIGINALS = tuple(
    TaskModelSetting(task, f"model.{task.value}.default", 0.5, None) for task in GenerationTask
)


class FakeModelSource:
    """The TOML stand-in: the model catalog and the shipped per-task settings."""

    def __init__(self) -> None:
        self.fail_with: ModelSettingsSourceError | None = None
        self.candidate_list = CANDIDATES
        self.original_list = ORIGINALS

    def candidates(self) -> tuple[ModelCandidate, ...]:
        self._maybe_fail()
        return self.candidate_list

    def originals(self) -> tuple[TaskModelSetting, ...]:
        self._maybe_fail()
        return self.original_list

    def _maybe_fail(self) -> None:
        if self.fail_with is not None:
            raise self.fail_with


class InMemoryModelSettingsStore:
    """Reader and writer in one: append-only rows, one active row per task."""

    def __init__(self) -> None:
        self.rows: list[ModelSettingVersion] = []
        self.fail_with: ModelSettingsStoreError | None = None

    def list_active(self) -> tuple[ModelSettingVersion, ...]:
        self._maybe_fail()
        return tuple(row for row in self.rows if row.is_active)

    def list_history(self, task: GenerationTask) -> tuple[ModelSettingVersion, ...]:
        self._maybe_fail()
        matching = [row for row in self.rows if row.setting.task == task]
        return tuple(sorted(matching, key=lambda row: row.created_at, reverse=True))

    def append_versions(
        self, versions: Sequence[NewModelSettingVersion]
    ) -> tuple[ModelSettingVersion, ...]:
        self._maybe_fail()
        created: list[ModelSettingVersion] = []
        for new in versions:
            self.rows = [
                replace(row, is_active=False) if row.setting.task == new.setting.task else row
                for row in self.rows
            ]
            row = ModelSettingVersion(
                version_id=new.version_id,
                setting=new.setting,
                source=new.source,
                created_at=new.created_at,
                created_by=new.created_by,
                is_active=True,
            )
            self.rows.append(row)
            created.append(row)
        return tuple(created)

    def _maybe_fail(self) -> None:
        if self.fail_with is not None:
            raise self.fail_with

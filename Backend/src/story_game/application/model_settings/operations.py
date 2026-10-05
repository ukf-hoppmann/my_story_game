"""Model-settings operations: seed, read, edit and reset the per-task model choice."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.llm import GenerationTask
from story_game.domain import StableId

from .errors import ModelSettingsError, ModelSettingsErrorKind
from .models import (
    ModelCandidate,
    ModelSettingSource,
    ModelSettingVersion,
    NewModelSettingVersion,
    TaskModelSetting,
)
from .ports import (
    ModelCatalog,
    ModelSettingsOriginals,
    ModelSettingsReader,
    ModelSettingsSourceError,
    ModelSettingsStoreError,
    ModelSettingsWriter,
)

MAX_TEMPERATURE = 2.0


def _failure(kind: ModelSettingsErrorKind, message: str) -> Failure[ModelSettingsError]:
    return Failure(ModelSettingsError(kind, message))


def _store_unavailable() -> Failure[ModelSettingsError]:
    return _failure(
        ModelSettingsErrorKind.STORE_UNAVAILABLE,
        "Die Modelleinstellungen konnten nicht gelesen oder gespeichert werden.",
    )


def _source_unavailable() -> Failure[ModelSettingsError]:
    return _failure(
        ModelSettingsErrorKind.SOURCE_UNAVAILABLE,
        "Der Modellkatalog oder die Original-Einstellungen sind nicht verfügbar.",
    )


def _new_versions(
    settings: tuple[TaskModelSetting, ...],
    source: ModelSettingSource,
    created_by: str | None,
    new_id: Callable[[], StableId],
    now: datetime,
) -> tuple[NewModelSettingVersion, ...]:
    return tuple(
        NewModelSettingVersion(new_id(), setting, source, now, created_by) for setting in settings
    )


@dataclass(frozen=True, slots=True)
class SeedModelSettingsRequest:
    pass


@dataclass(frozen=True, slots=True)
class SeedModelSettingsResult:
    seeded: bool
    """Whether at least one task had no stored setting and was imported."""


class SeedModelSettings:
    """Import the shipped setting of every task that has no stored version yet.

    A restart therefore never overwrites an edit; getting the original back is
    an explicit reset.
    """

    def __init__(
        self,
        originals: ModelSettingsOriginals,
        reader: ModelSettingsReader,
        writer: ModelSettingsWriter,
        new_id: Callable[[], StableId],
        clock: Callable[[], datetime],
    ) -> None:
        self._originals = originals
        self._reader = reader
        self._writer = writer
        self._new_id = new_id
        self._clock = clock

    def apply(
        self, request: SeedModelSettingsRequest
    ) -> OperationResult[SeedModelSettingsResult, ModelSettingsError]:
        try:
            stored = {version.setting.task for version in self._reader.list_active()}
            missing = tuple(s for s in self._originals.originals() if s.task not in stored)
            if missing:
                self._writer.append_versions(
                    _new_versions(
                        missing, ModelSettingSource.TOML_SEED, None, self._new_id, self._clock()
                    )
                )
        except ModelSettingsSourceError:
            return _source_unavailable()
        except ModelSettingsStoreError:
            return _store_unavailable()
        return Success(SeedModelSettingsResult(bool(missing)))


@dataclass(frozen=True, slots=True)
class ListModelSettingsRequest:
    pass


@dataclass(frozen=True, slots=True)
class ModelSettingsOverview:
    settings: tuple[ModelSettingVersion, ...]
    """The active setting of every task, in task order."""
    candidates: tuple[ModelCandidate, ...]
    """Every catalog model that may be selected, per task."""


class ListModelSettings:
    def __init__(self, reader: ModelSettingsReader, catalog: ModelCatalog) -> None:
        self._reader = reader
        self._catalog = catalog

    def apply(
        self, request: ListModelSettingsRequest
    ) -> OperationResult[ModelSettingsOverview, ModelSettingsError]:
        try:
            active = {v.setting.task: v for v in self._reader.list_active()}
            candidates = self._catalog.candidates()
        except ModelSettingsStoreError:
            return _store_unavailable()
        except ModelSettingsSourceError:
            return _source_unavailable()
        ordered = tuple(active[task] for task in GenerationTask if task in active)
        if not ordered:
            return _failure(ModelSettingsErrorKind.NOT_FOUND, "Es sind keine Modelleinstellungen gespeichert.")
        return Success(ModelSettingsOverview(ordered, candidates))


@dataclass(frozen=True, slots=True)
class ListModelSettingHistoryRequest:
    task: GenerationTask


class ListModelSettingHistory:
    def __init__(self, reader: ModelSettingsReader) -> None:
        self._reader = reader

    def apply(
        self, request: ListModelSettingHistoryRequest
    ) -> OperationResult[tuple[ModelSettingVersion, ...], ModelSettingsError]:
        try:
            versions = self._reader.list_history(request.task)
        except ModelSettingsStoreError:
            return _store_unavailable()
        if not versions:
            return _failure(ModelSettingsErrorKind.NOT_FOUND, "Die Einstellung wurde nicht gefunden.")
        return Success(versions)


@dataclass(frozen=True, slots=True)
class UpdateModelSettingRequest:
    task: GenerationTask
    model_ref: str
    temperature: float | None
    max_output_tokens: int | None
    editor: str
    """Name recorded as the author of the new version."""


class UpdateModelSetting:
    """Append the edited choice as the task's new active version.

    Saving the values a task already has is a no-op, so a repeated request
    cannot flood the history.
    """

    def __init__(
        self,
        reader: ModelSettingsReader,
        writer: ModelSettingsWriter,
        catalog: ModelCatalog,
        new_id: Callable[[], StableId],
        clock: Callable[[], datetime],
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._catalog = catalog
        self._new_id = new_id
        self._clock = clock

    def apply(
        self, request: UpdateModelSettingRequest
    ) -> OperationResult[ModelSettingVersion, ModelSettingsError]:
        temperature = request.temperature
        if temperature is not None and not (
            math.isfinite(temperature) and 0 <= temperature <= MAX_TEMPERATURE
        ):
            return _failure(
                ModelSettingsErrorKind.INVALID_OPTIONS,
                f"Die Temperatur muss zwischen 0 und {MAX_TEMPERATURE:g} liegen.",
            )
        if request.max_output_tokens is not None and request.max_output_tokens <= 0:
            return _failure(
                ModelSettingsErrorKind.INVALID_OPTIONS,
                "Die maximale Ausgabelänge muss positiv sein.",
            )
        try:
            allowed = {
                c.model_ref for c in self._catalog.candidates() if c.task == request.task
            }
            if request.model_ref not in allowed:
                return _failure(
                    ModelSettingsErrorKind.INVALID_MODEL,
                    f"Das Modell {request.model_ref!r} ist für {request.task.value} nicht wählbar.",
                )
            setting = TaskModelSetting(
                request.task, request.model_ref, temperature, request.max_output_tokens
            )
            current = next(
                (v for v in self._reader.list_active() if v.setting.task == request.task), None
            )
            if current is not None and current.setting == setting:
                return Success(current)
            created = self._writer.append_versions(
                _new_versions(
                    (setting,), ModelSettingSource.UI, request.editor, self._new_id, self._clock()
                )
            )
        except ModelSettingsSourceError:
            return _source_unavailable()
        except ModelSettingsStoreError:
            return _store_unavailable()
        return Success(created[0])


@dataclass(frozen=True, slots=True)
class ResetModelSettingsRequest:
    task: GenerationTask | None
    """One task, or ``None`` for every task."""
    editor: str


class ResetModelSettings:
    """Append the shipped original as a new version; edits stay in the history.

    Tasks that already carry the original setting are skipped.
    """

    def __init__(
        self,
        originals: ModelSettingsOriginals,
        reader: ModelSettingsReader,
        writer: ModelSettingsWriter,
        new_id: Callable[[], StableId],
        clock: Callable[[], datetime],
    ) -> None:
        self._originals = originals
        self._reader = reader
        self._writer = writer
        self._new_id = new_id
        self._clock = clock

    def apply(
        self, request: ResetModelSettingsRequest
    ) -> OperationResult[tuple[ModelSettingVersion, ...], ModelSettingsError]:
        try:
            originals = {s.task: s for s in self._originals.originals()}
            current = {v.setting.task: v.setting for v in self._reader.list_active()}
            tasks = [request.task] if request.task is not None else list(GenerationTask)
            if request.task is not None and request.task not in originals:
                return _failure(ModelSettingsErrorKind.NOT_FOUND, "Die Einstellung wurde nicht gefunden.")
            restored = tuple(
                originals[task]
                for task in tasks
                if task in originals and current.get(task) != originals[task]
            )
            if not restored:
                return Success(())
            created = self._writer.append_versions(
                _new_versions(
                    restored,
                    ModelSettingSource.TOML_RESET,
                    request.editor,
                    self._new_id,
                    self._clock(),
                )
            )
        except ModelSettingsSourceError:
            return _source_unavailable()
        except ModelSettingsStoreError:
            return _store_unavailable()
        return Success(created)


@dataclass(frozen=True, slots=True)
class ModelSettingsOperations:
    """The model-settings operations the HTTP adapter needs, grouped as one value."""

    overview: ListModelSettings
    history: ListModelSettingHistory
    update: UpdateModelSetting
    reset: ResetModelSettings


__all__ = [
    "ListModelSettingHistory",
    "ListModelSettingHistoryRequest",
    "ListModelSettings",
    "ListModelSettingsRequest",
    "MAX_TEMPERATURE",
    "ModelSettingsOperations",
    "ModelSettingsOverview",
    "ResetModelSettings",
    "ResetModelSettingsRequest",
    "SeedModelSettings",
    "SeedModelSettingsRequest",
    "SeedModelSettingsResult",
    "UpdateModelSetting",
    "UpdateModelSettingRequest",
]

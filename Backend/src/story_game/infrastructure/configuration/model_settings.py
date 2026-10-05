"""The model catalog and shipped task settings, read from ``llm.toml``."""

from __future__ import annotations

from pathlib import Path

from story_game.application.llm import GenerationTask
from story_game.application.model_settings import (
    ModelCandidate,
    ModelCatalog,
    ModelSettingsOriginals,
    ModelSettingsSourceError,
    TaskModelSetting,
)

from .llm import LlmConfiguration, LlmConfigurationError, LlmTask, TomlLlmConfigurationLoader


class TomlModelSettingsSource(ModelCatalog, ModelSettingsOriginals):
    """Reloads the file on every call, like the other ``llm.toml`` readers."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def candidates(self) -> tuple[ModelCandidate, ...]:
        configuration = self._load()
        return tuple(
            ModelCandidate(GenerationTask(model.task.value), model.id, model.provider_id, model.model_id)
            for model in configuration.models
        )

    def originals(self) -> tuple[TaskModelSetting, ...]:
        configuration = self._load()
        settings: list[TaskModelSetting] = []
        for task in LlmTask:
            options = configuration.generation_options[task]
            settings.append(
                TaskModelSetting(
                    GenerationTask(task.value),
                    configuration.task_models.for_task(task),
                    options.temperature,
                    options.max_output_tokens,
                )
            )
        return tuple(settings)

    def _load(self) -> LlmConfiguration:
        try:
            return TomlLlmConfigurationLoader().load(self._path)
        except LlmConfigurationError as error:
            raise ModelSettingsSourceError(str(error)) from error


__all__ = ["TomlModelSettingsSource"]

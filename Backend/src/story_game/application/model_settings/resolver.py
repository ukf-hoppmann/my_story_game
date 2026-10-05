"""Runtime resolution of the generation configuration from the stored settings."""

from __future__ import annotations

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.llm import (
    GenerationConfiguration,
    GenerationConfigurationResolver,
    GenerationOptions,
    GenerationTask,
    LLMError,
    LLMErrorKind,
    ModelSelection,
)

from .ports import (
    ModelCatalog,
    ModelSettingsReader,
    ModelSettingsSourceError,
    ModelSettingsStoreError,
)


def _configuration_error(message: str) -> Failure[LLMError]:
    return Failure(LLMError(LLMErrorKind.CONFIGURATION, message))


class ManagedGenerationConfigurationResolver(GenerationConfigurationResolver):
    """Resolves each call from the active stored setting and the model catalog.

    Both are read on every call, so a change in the settings affects the next
    model invocation without a restart.
    """

    def __init__(self, reader: ModelSettingsReader, catalog: ModelCatalog) -> None:
        self._reader = reader
        self._catalog = catalog

    def resolve(
        self, task: GenerationTask
    ) -> OperationResult[GenerationConfiguration, LLMError]:
        try:
            active = next(
                (v for v in self._reader.list_active() if v.setting.task == task), None
            )
            candidates = self._catalog.candidates()
        except ModelSettingsStoreError:
            return _configuration_error("Die Modelleinstellungen konnten nicht gelesen werden")
        except ModelSettingsSourceError:
            return _configuration_error("Der Modellkatalog konnte nicht gelesen werden")
        if active is None:
            return _configuration_error(f"Für {task.value} sind keine Modelleinstellungen gespeichert")
        setting = active.setting
        candidate = next(
            (c for c in candidates if c.task == task and c.model_ref == setting.model_ref), None
        )
        if candidate is None:
            return _configuration_error(
                f"Das Modell {setting.model_ref} ist für {task.value} nicht im Katalog vorhanden"
            )
        try:
            options = GenerationOptions(setting.temperature, setting.max_output_tokens)
        except ValueError as error:
            return _configuration_error(str(error))
        return Success(
            GenerationConfiguration(
                ModelSelection(candidate.provider_id, candidate.model_id), options
            )
        )


__all__ = ["ManagedGenerationConfigurationResolver"]

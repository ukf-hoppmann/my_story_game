"""Validated TOML configuration for provider and model selection."""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from story_game.application import Failure, OperationResult, Success
from story_game.application.llm import (
    GenerationConfiguration,
    GenerationConfigurationResolver,
    GenerationOptions,
    GenerationTask,
    LLMError,
    LLMErrorKind,
    ModelSelection,
    ModelSelectionResolver,
)


class LlmConfigurationError(ValueError):
    """A configuration document cannot safely describe model invocation."""


class LlmTask(StrEnum):
    """Model-backed tasks with one active system-level selection."""

    STORY = "story"
    EXTRACTION = "extraction"
    SUMMARY = "summary"


@dataclass(frozen=True, slots=True)
class ProviderConfiguration:
    """Provider connection data needed by its infrastructure client.

    ``api_key`` never comes from the versioned ``llm.toml`` catalog itself —
    it is merged in from the sibling, gitignored ``llm.secrets.toml`` (see
    ``TomlLlmConfigurationLoader._load_secrets``), or left ``None`` for a
    provider that needs no key (e.g. a local LM Studio instance).
    """

    id: str
    base_url: str
    timeout_seconds: float
    api_key: str | None = None


@dataclass(frozen=True, slots=True)
class ModelDefinition:
    """One logical catalog entry and its concrete provider model identity."""

    id: str
    task: LlmTask
    provider_id: str
    model_id: str


@dataclass(frozen=True, slots=True)
class TaskModelReferences:
    """The active logical catalog entry for each model-backed task."""

    story: str
    extraction: str
    summary: str

    def __post_init__(self) -> None:
        for name in ("story", "extraction", "summary"):
            value = getattr(self, name).strip()
            if not value:
                raise LlmConfigurationError(
                    f"Die aktive Modellreferenz für {name} darf nicht leer sein"
                )
            object.__setattr__(self, name, value)

    def for_task(self, task: LlmTask) -> str:
        return getattr(self, task.value)


@dataclass(frozen=True, slots=True)
class LlmConfiguration(ModelSelectionResolver):
    """The single effective runtime configuration loaded from TOML."""

    providers: tuple[ProviderConfiguration, ...]
    models: tuple[ModelDefinition, ...]
    task_models: TaskModelReferences
    generation_options: dict[LlmTask, GenerationOptions]

    def resolve(self, logical_model_id: str) -> ModelSelection:
        model = self._model(logical_model_id)
        return ModelSelection(model.provider_id, model.model_id)

    def model_for_task(self, task: LlmTask) -> ModelSelection:
        return self.resolve(self.task_models.for_task(task))

    def generation_for_task(self, task: LlmTask) -> GenerationConfiguration:
        return GenerationConfiguration(self.model_for_task(task), self.generation_options[task])

    def provider_for_model(self, logical_model_id: str) -> ProviderConfiguration:
        model = self._model(logical_model_id)
        for provider in self.providers:
            if provider.id == model.provider_id:
                return provider
        raise LlmConfigurationError(
            f"Der Provider {model.provider_id} für {logical_model_id} ist nicht vorhanden"
        )

    def provider(self, provider_id: str) -> ProviderConfiguration:
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        raise LlmConfigurationError(f"Der Provider {provider_id} ist nicht vorhanden")

    def _model(self, logical_model_id: str) -> ModelDefinition:
        logical_model_id = logical_model_id.strip()
        for model in self.models:
            if model.id == logical_model_id:
                return model
        raise LlmConfigurationError(
            f"Die logische Modellreferenz {logical_model_id} ist nicht im Katalog vorhanden"
        )


class TomlLlmConfigurationLoader:
    """Load and validate the one project-owned ``configs/llm.toml`` file."""

    def load(self, path: str | Path) -> LlmConfiguration:
        config_path = Path(path)
        try:
            document = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise LlmConfigurationError(
                f"Die LLM-Konfiguration konnte nicht gelesen werden: {config_path}"
            ) from error
        except tomllib.TOMLDecodeError as error:
            raise LlmConfigurationError(
                f"Die LLM-Konfiguration ist kein gültiges TOML: {config_path}"
            ) from error
        return self._parse(document, config_path)

    def _parse(self, document: dict[str, Any], path: Path) -> LlmConfiguration:
        _keys(document, {"providers", "task_models", "generation_options", "models"}, "die Hauptkonfiguration")
        providers = self._providers(_table(document, "providers", path), path)
        providers = self._with_secrets(providers, path)
        task_models = self._task_models(_table(document, "task_models", path), path)
        models = self._models(document.get("models"), providers, path)
        generation_options = self._generation_options(
            _table(document, "generation_options", path), path
        )
        _validate_active_models(task_models, models)
        return LlmConfiguration(tuple(providers), tuple(models), task_models, generation_options)

    def _with_secrets(
        self, providers: list[ProviderConfiguration], path: Path
    ) -> list[ProviderConfiguration]:
        """Merge api_key values from the sibling, gitignored secrets file.

        A missing secrets file is not an error: most providers (e.g. a local
        LM Studio instance) need no key at all. The secrets file is reloaded
        from disk on every ``load()`` call, same as ``llm.toml`` itself, so a
        rotated key takes effect without a restart.
        """
        secrets_path = path.parent / "llm.secrets.toml"
        api_keys = self._load_secrets(secrets_path)
        return [
            replace(provider, api_key=api_keys.get(provider.id))
            for provider in providers
        ]

    def _load_secrets(self, path: Path) -> dict[str, str]:
        if not path.is_file():
            return {}
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise LlmConfigurationError(
                f"Die LLM-Secrets-Datei konnte nicht gelesen werden: {path}"
            ) from error
        except tomllib.TOMLDecodeError as error:
            raise LlmConfigurationError(
                f"Die LLM-Secrets-Datei ist kein gültiges TOML: {path}"
            ) from error
        _keys(document, {"providers"}, "die Secrets-Konfiguration")
        providers_table = _table(document, "providers", path) if "providers" in document else {}
        api_keys: dict[str, str] = {}
        for provider_id, raw in providers_table.items():
            if not isinstance(provider_id, str) or not provider_id.strip():
                raise LlmConfigurationError(f"{path}: Provider-IDs dürfen nicht leer sein")
            table = _table_value(raw, f"providers.{provider_id}", path)
            _keys(table, {"api_key"}, f"providers.{provider_id}")
            api_keys[provider_id] = _text(table, "api_key", f"providers.{provider_id}", path)
        return api_keys

    def _generation_options(
        self, document: dict[str, Any], path: Path
    ) -> dict[LlmTask, GenerationOptions]:
        _keys(document, {task.value for task in LlmTask}, "generation_options")
        values: dict[LlmTask, GenerationOptions] = {}
        for task in LlmTask:
            table = _table(document, task.value, path)
            _keys(table, {"temperature", "max_output_tokens"}, f"generation_options.{task.value}")
            temperature = table.get("temperature")
            max_output_tokens = table.get("max_output_tokens")
            if temperature is not None and (isinstance(temperature, bool) or not isinstance(temperature, (int, float))):
                raise LlmConfigurationError(f"{path}: generation_options.{task.value}.temperature muss eine Zahl sein")
            if max_output_tokens is not None and (isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int)):
                raise LlmConfigurationError(f"{path}: generation_options.{task.value}.max_output_tokens muss eine ganze Zahl sein")
            values[task] = GenerationOptions(
                temperature=None if temperature is None else float(temperature),
                max_output_tokens=max_output_tokens,
            )
        return values


    def _providers(
        self, document: dict[str, Any], path: Path
    ) -> list[ProviderConfiguration]:
        if not document:
            raise LlmConfigurationError(f"{path}: Es muss mindestens ein Provider definiert sein")
        providers: list[ProviderConfiguration] = []
        for provider_id, raw in document.items():
            if not isinstance(provider_id, str) or not provider_id.strip():
                raise LlmConfigurationError(f"{path}: Provider-IDs dürfen nicht leer sein")
            table = _table_value(raw, f"providers.{provider_id}", path)
            _keys(table, {"base_url", "timeout_seconds"}, f"providers.{provider_id}")
            base_url = _text(table, "base_url", f"providers.{provider_id}", path)
            parsed = urlparse(base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise LlmConfigurationError(
                    f"{path}: providers.{provider_id}.base_url muss eine HTTP- oder HTTPS-URL sein"
                )
            timeout = _positive_number(
                table.get("timeout_seconds"),
                f"providers.{provider_id}.timeout_seconds",
                path,
            )
            providers.append(ProviderConfiguration(provider_id, base_url.rstrip("/"), timeout))
        return providers

    def _task_models(
        self, document: dict[str, Any], path: Path
    ) -> TaskModelReferences:
        expected = {task.value for task in LlmTask}
        _keys(document, expected, "task_models")
        values = {
            task.value: _text(document, task.value, "task_models", path)
            for task in LlmTask
        }
        return TaskModelReferences(**values)

    def _models(
        self,
        raw_models: Any,
        providers: list[ProviderConfiguration],
        path: Path,
    ) -> list[ModelDefinition]:
        if not isinstance(raw_models, list) or not raw_models:
            raise LlmConfigurationError(f"{path}: models muss eine nichtleere Liste sein")
        provider_ids = {provider.id for provider in providers}
        models: list[ModelDefinition] = []
        seen: set[str] = set()
        for index, raw in enumerate(raw_models):
            table = _table_value(raw, f"models[{index}]", path)
            _keys(table, {"id", "task", "provider_id", "model_id"}, f"models[{index}]")
            logical_id = _text(table, "id", f"models[{index}]", path)
            if logical_id in seen:
                raise LlmConfigurationError(
                    f"{path}: Die Modell-ID {logical_id} ist doppelt definiert"
                )
            seen.add(logical_id)
            task_value = _text(table, "task", f"models[{index}]", path)
            try:
                task = LlmTask(task_value)
            except ValueError as error:
                raise LlmConfigurationError(
                    f"{path}: models[{index}].task ist unbekannt: {task_value}"
                ) from error
            provider_id = _text(table, "provider_id", f"models[{index}]", path)
            if provider_id not in provider_ids:
                raise LlmConfigurationError(
                    f"{path}: Der Provider {provider_id} für {logical_id} ist nicht vorhanden"
                )
            models.append(
                ModelDefinition(
                    logical_id,
                    task,
                    provider_id,
                    _text(table, "model_id", f"models[{index}]", path),
                )
            )
        return models


class TomlGenerationConfigurationResolver(GenerationConfigurationResolver):
    """Reload project-owned TOML so changes affect the next model invocation."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def resolve(
        self, task: GenerationTask
    ) -> OperationResult[GenerationConfiguration, LLMError]:
        try:
            configuration = TomlLlmConfigurationLoader().load(self._path)
            return Success(configuration.generation_for_task(LlmTask(task.value)))
        except (LlmConfigurationError, ValueError) as error:
            return Failure(LLMError(LLMErrorKind.CONFIGURATION, str(error)))


def _validate_active_models(
    task_models: TaskModelReferences, models: list[ModelDefinition]
) -> None:
    by_id = {model.id: model for model in models}
    for task in LlmTask:
        logical_id = task_models.for_task(task)
        model = by_id.get(logical_id)
        if model is None:
            raise LlmConfigurationError(
                f"Die aktive Modellreferenz für {task.value} ist nicht im Katalog vorhanden: {logical_id}"
            )
        if model.task is not task:
            raise LlmConfigurationError(
                f"Das Modell {logical_id} gehört zur Aufgabe {model.task.value}, nicht zu {task.value}"
            )


def _table(document: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    return _table_value(document.get(key), key, path)


def _table_value(value: Any, key: str, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LlmConfigurationError(f"{path}: {key} muss eine Tabelle sein")
    return value


def _keys(document: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(document) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise LlmConfigurationError(f"Unbekannte Felder in {label}: {names}")


def _text(document: dict[str, Any], key: str, label: str, path: Path) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LlmConfigurationError(f"{path}: {label}.{key} muss nichtleerer Text sein")
    return value.strip()


def _positive_number(value: Any, label: str, path: Path) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LlmConfigurationError(f"{path}: {label} muss eine positive Zahl sein")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise LlmConfigurationError(f"{path}: {label} muss eine positive Zahl sein")
    return number

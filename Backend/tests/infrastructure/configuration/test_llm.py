from __future__ import annotations

from pathlib import Path

import pytest

from story_game.application import ModelSelection
from story_game.application.llm import GenerationTask
from story_game.infrastructure.configuration import (
    LlmConfigurationError,
    LlmTask,
    TomlLlmConfigurationLoader,
    TomlGenerationConfigurationResolver,
)


def write_config(tmp_path: Path, document: str) -> Path:
    path = tmp_path / "llm.toml"
    path.write_text(document, encoding="utf-8")
    return path


def valid_document() -> str:
    return """
[providers.lmstudio]
base_url = "http://localhost:1234/v1"
timeout_seconds = 60

[task_models]
story = "model.story.default"
extraction = "model.extraction.default"
summary = "model.summary.default"
scene_image = "model.scene_image.default"

[generation_options.story]
temperature = 0.5

[generation_options.extraction]
temperature = 0.5

[generation_options.summary]
temperature = 0.5

[generation_options.scene_image]
temperature = 0.5

[[models]]
id = "model.story.default"
task = "story"
provider_id = "lmstudio"
model_id = "mistralai/mistral-small-3.2"

[[models]]
id = "model.extraction.default"
task = "extraction"
provider_id = "lmstudio"
model_id = "mistralai/mistral-small-3.2"

[[models]]
id = "model.summary.default"
task = "summary"
provider_id = "lmstudio"
model_id = "mistralai/mistral-small-3.2"

[[models]]
id = "model.scene_image.default"
task = "scene_image"
provider_id = "lmstudio"
model_id = "mistralai/mistral-small-3.2"
"""


def test_loader_reads_three_task_models_and_resolves_concrete_selection(
    tmp_path: Path,
) -> None:
    configuration = TomlLlmConfigurationLoader().load(
        write_config(tmp_path, valid_document())
    )

    assert configuration.task_models.for_task(LlmTask.STORY) == "model.story.default"
    assert configuration.task_models.for_task(LlmTask.EXTRACTION) == (
        "model.extraction.default"
    )
    assert configuration.task_models.for_task(LlmTask.SUMMARY) == "model.summary.default"
    assert configuration.resolve("model.story.default") == ModelSelection(
        "lmstudio", "mistralai/mistral-small-3.2"
    )
    assert configuration.generation_for_task(LlmTask.STORY).generation_options.temperature == 0.5
    assert configuration.generation_for_task(LlmTask.STORY).generation_options.max_output_tokens is None


def test_loader_resolves_the_scene_image_task(tmp_path: Path) -> None:
    configuration = TomlLlmConfigurationLoader().load(
        write_config(tmp_path, valid_document())
    )

    assert configuration.task_models.for_task(LlmTask.SCENE_IMAGE) == (
        "model.scene_image.default"
    )
    resolver = TomlGenerationConfigurationResolver(write_config(tmp_path, valid_document()))
    assert resolver.resolve(GenerationTask.SCENE_IMAGE).data.model_selection == ModelSelection(
        "lmstudio", "mistralai/mistral-small-3.2"
    )


def test_runtime_resolver_reads_current_task_settings_for_each_call(tmp_path: Path) -> None:
    path = write_config(tmp_path, valid_document())
    resolver = TomlGenerationConfigurationResolver(path)

    first = resolver.resolve(GenerationTask.STORY)
    path.write_text(valid_document().replace("temperature = 0.5", "temperature = 0.7", 1), encoding="utf-8")
    second = resolver.resolve(GenerationTask.STORY)

    assert first.data.generation_options.temperature == 0.5
    assert second.data.generation_options.temperature == 0.7


def test_repository_configuration_selects_a_catalog_model_for_every_task() -> None:
    path = Path(__file__).resolve().parents[3] / "configs" / "llm.toml"

    configuration = TomlLlmConfigurationLoader().load(path)

    tasks_by_model = {model.id: model.task for model in configuration.models}
    for task in LlmTask:
        assert tasks_by_model[configuration.task_models.for_task(task)] is task
    assert set(tasks_by_model.values()) == set(LlmTask)


def test_loader_allows_additional_candidates_for_one_task(tmp_path: Path) -> None:
    document = valid_document() + """

[[models]]
id = "model.story.fast"
task = "story"
provider_id = "lmstudio"
model_id = "mistralai/mistral-small-3.2"
"""

    configuration = TomlLlmConfigurationLoader().load(write_config(tmp_path, document))

    assert configuration.resolve("model.story.fast") == ModelSelection(
        "lmstudio", "mistralai/mistral-small-3.2"
    )


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (
            'story = "missing"',
            "Die aktive Modellreferenz für story ist nicht im Katalog vorhanden",
        ),
        (
            'id = "model.story.default"',
            "Die Modell-ID model.story.default ist doppelt definiert",
        ),
    ],
)
def test_loader_rejects_invalid_model_catalog(
    tmp_path: Path, change: str, expected: str
) -> None:
    document = valid_document()
    if change.startswith("story ="):
        document = document.replace('story = "model.story.default"', change)
    else:
        document = document.replace('id = "model.extraction.default"', change, 1)

    with pytest.raises(LlmConfigurationError, match=expected):
        TomlLlmConfigurationLoader().load(write_config(tmp_path, document))


def test_loader_rejects_model_task_mismatch(tmp_path: Path) -> None:
    document = valid_document().replace(
        'id = "model.summary.default"\ntask = "summary"',
        'id = "model.summary.default"\ntask = "story"',
    )

    with pytest.raises(LlmConfigurationError, match="gehört zur Aufgabe story"):
        TomlLlmConfigurationLoader().load(write_config(tmp_path, document))


def test_missing_secrets_file_leaves_provider_api_key_unset(tmp_path: Path) -> None:
    configuration = TomlLlmConfigurationLoader().load(
        write_config(tmp_path, valid_document())
    )

    assert configuration.provider("lmstudio").api_key is None


def test_secrets_file_merges_api_key_into_matching_provider(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, valid_document())
    (tmp_path / "llm.secrets.toml").write_text(
        '[providers.lmstudio]\napi_key = "secret-value"\n', encoding="utf-8"
    )

    configuration = TomlLlmConfigurationLoader().load(config_path)

    assert configuration.provider("lmstudio").api_key == "secret-value"


def test_secrets_file_never_read_from_the_versioned_llm_toml_itself(
    tmp_path: Path,
) -> None:
    document = valid_document().replace(
        '[providers.lmstudio]\nbase_url = "http://localhost:1234/v1"\ntimeout_seconds = 60',
        '[providers.lmstudio]\nbase_url = "http://localhost:1234/v1"\n'
        'timeout_seconds = 60\napi_key = "should-not-be-allowed-here"',
    )

    with pytest.raises(LlmConfigurationError, match="Unbekannte Felder"):
        TomlLlmConfigurationLoader().load(write_config(tmp_path, document))


def test_secrets_file_reloads_on_every_call(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, valid_document())
    secrets_path = tmp_path / "llm.secrets.toml"
    secrets_path.write_text(
        '[providers.lmstudio]\napi_key = "first"\n', encoding="utf-8"
    )

    first = TomlLlmConfigurationLoader().load(config_path)
    secrets_path.write_text(
        '[providers.lmstudio]\napi_key = "second"\n', encoding="utf-8"
    )
    second = TomlLlmConfigurationLoader().load(config_path)

    assert first.provider("lmstudio").api_key == "first"
    assert second.provider("lmstudio").api_key == "second"

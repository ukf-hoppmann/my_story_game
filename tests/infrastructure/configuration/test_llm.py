from __future__ import annotations

from pathlib import Path

import pytest

from story_game.application import ModelSelection
from story_game.infrastructure.configuration import (
    LlmConfigurationError,
    LlmTask,
    TomlLlmConfigurationLoader,
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


def test_repository_configuration_defines_all_three_active_tasks() -> None:
    path = Path(__file__).resolve().parents[3] / "configs" / "llm.toml"

    configuration = TomlLlmConfigurationLoader().load(path)

    assert configuration.task_models.story == "model.story.default"
    assert configuration.task_models.extraction == "model.extraction.default"
    assert configuration.task_models.summary == "model.summary.default"
    assert {model.task for model in configuration.models} == {
        LlmTask.STORY,
        LlmTask.EXTRACTION,
        LlmTask.SUMMARY,
    }


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

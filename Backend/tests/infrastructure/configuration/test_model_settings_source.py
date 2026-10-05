from __future__ import annotations

from pathlib import Path

import pytest

from story_game.application.llm import GenerationTask
from story_game.application.model_settings import (
    ModelCandidate,
    ModelSettingsSourceError,
    TaskModelSetting,
)
from story_game.infrastructure.configuration import TomlModelSettingsSource
from tests.infrastructure.configuration.test_llm import valid_document, write_config


def test_originals_come_from_the_active_task_models_and_options(tmp_path: Path) -> None:
    document = valid_document().replace(
        "[generation_options.story]\ntemperature = 0.5",
        "[generation_options.story]\ntemperature = 0.7\nmax_output_tokens = 900",
    )

    originals = TomlModelSettingsSource(write_config(tmp_path, document)).originals()

    assert originals[0] == TaskModelSetting(GenerationTask.STORY, "model.story.default", 0.7, 900)
    assert {o.task for o in originals} == set(GenerationTask)
    assert TaskModelSetting(GenerationTask.SUMMARY, "model.summary.default", 0.5, None) in originals


def test_candidates_list_every_catalog_model_with_its_provider(tmp_path: Path) -> None:
    document = valid_document() + """

[[models]]
id = "model.story.fast"
task = "story"
provider_id = "lmstudio"
model_id = "fast-model"
"""

    candidates = TomlModelSettingsSource(write_config(tmp_path, document)).candidates()

    assert ModelCandidate(
        GenerationTask.STORY, "model.story.fast", "lmstudio", "fast-model"
    ) in candidates
    assert len([c for c in candidates if c.task == GenerationTask.STORY]) == 2
    assert len(candidates) == 5


def test_an_unreadable_or_invalid_file_raises_a_source_error(tmp_path: Path) -> None:
    source = TomlModelSettingsSource(tmp_path / "missing.toml")

    with pytest.raises(ModelSettingsSourceError):
        source.originals()
    with pytest.raises(ModelSettingsSourceError):
        source.candidates()

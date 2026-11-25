from __future__ import annotations

from pathlib import Path

import pytest

from story_game.infrastructure.configuration import (
    AppConfigurationError,
    ModalCredentials,
    SceneImageSettings,
    TomlAppConfigurationLoader,
    load_modal_credentials,
)


def write(tmp_path: Path, document: str) -> Path:
    path = tmp_path / "app.toml"
    path.write_text(document, encoding="utf-8")
    return path


ENABLED = """
[scene_image]
enabled = true
turn_window = 4
width = 768
height = 512
refine = true
refine_model = "refine-x"
refine_strength = 0.5
compact_prompt_max_words = 40

[scene_image.modal]
url = "https://gpu.example/"
control_url = "https://control.example"
model = "z-image-turbo"
timeout_seconds = 300
negative_prompt = "blurry"
refine_negative_prompt = "ugly"
"""


def test_a_missing_file_or_section_means_the_feature_is_disabled(tmp_path: Path) -> None:
    loader = TomlAppConfigurationLoader()

    assert loader.load_scene_image(tmp_path / "missing.toml") == SceneImageSettings()
    assert loader.load_scene_image(write(tmp_path, "[logging]\n")).enabled is False


def test_a_complete_section_is_parsed(tmp_path: Path) -> None:
    settings = TomlAppConfigurationLoader().load_scene_image(write(tmp_path, ENABLED))

    assert settings.enabled is True
    assert (settings.turn_window, settings.width, settings.height) == (4, 768, 512)
    assert (settings.refine, settings.refine_model, settings.refine_strength) == (
        True,
        "refine-x",
        0.5,
    )
    assert settings.compact_prompt_max_words == 40
    modal = settings.modal
    assert modal.url == "https://gpu.example"
    assert modal.control_url == "https://control.example"
    assert (modal.model, modal.timeout_seconds) == ("z-image-turbo", 300)
    assert (modal.negative_prompt, modal.refine_negative_prompt) == ("blurry", "ugly")


def test_a_disabled_feature_needs_no_modal_table(tmp_path: Path) -> None:
    settings = TomlAppConfigurationLoader().load_scene_image(
        write(tmp_path, "[scene_image]\nenabled = false\n")
    )

    assert settings.enabled is False and settings.modal is None


@pytest.mark.parametrize(
    "document",
    [
        "[scene_image]\nenabled = true\n",
        ENABLED.replace('url = "https://gpu.example/"', ""),
        ENABLED.replace('model = "z-image-turbo"', ""),
        ENABLED.replace("refine_strength = 0.5", "refine_strength = 0.9"),
        ENABLED.replace("refine_strength = 0.5", "refine_strength = 0.05"),
        ENABLED.replace("turn_window = 4", "turn_window = 0"),
        ENABLED.replace("enabled = true", 'enabled = "yes"'),
        ENABLED.replace("[scene_image.modal]", 'provider = "other"\n[scene_image.modal]'),
        ENABLED.replace("width = 768", "width = true"),
        ENABLED.replace("[scene_image.modal]", "unknown = 1\n[scene_image.modal]"),
        ENABLED.replace("[scene_image.modal]", "[scene_image.modal]\nextra = 1"),
        ENABLED.replace("https://control.example", "not a url"),
    ],
)
def test_invalid_sections_are_rejected(tmp_path: Path, document: str) -> None:
    with pytest.raises(AppConfigurationError):
        TomlAppConfigurationLoader().load_scene_image(write(tmp_path, document))


def test_credentials_come_from_the_sibling_secrets_file(tmp_path: Path) -> None:
    config = write(tmp_path, ENABLED)
    (tmp_path / "scene_image.secrets.toml").write_text(
        '[modal]\nkey = "wk-1"\nsecret = "ws-2"\n', encoding="utf-8"
    )

    assert load_modal_credentials(config) == ModalCredentials("wk-1", "ws-2")


def test_missing_credentials_file_yields_none(tmp_path: Path) -> None:
    assert load_modal_credentials(write(tmp_path, ENABLED)) is None


def test_an_incomplete_credentials_file_is_rejected(tmp_path: Path) -> None:
    config = write(tmp_path, ENABLED)
    (tmp_path / "scene_image.secrets.toml").write_text('[modal]\nkey = "wk-1"\n', encoding="utf-8")

    with pytest.raises(AppConfigurationError):
        load_modal_credentials(config)


def test_the_repository_configuration_is_complete_whether_or_not_the_feature_is_on() -> None:
    path = Path(__file__).resolve().parents[3] / "configs" / "app.toml"

    settings = TomlAppConfigurationLoader().load_scene_image(path)

    assert settings.enabled is False or settings.modal is not None

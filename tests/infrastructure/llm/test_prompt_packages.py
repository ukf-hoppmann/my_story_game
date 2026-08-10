from __future__ import annotations

from pathlib import Path

import pytest

from story_game.application.llm import (
    InvalidPromptPackageError,
    PromptCategoryNotFoundError,
    PromptDirectiveNotFoundError,
    PromptOptionNotFoundError,
    PromptPackageNotFoundError,
    PromptTaskNotFoundError,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog


REPOSITORY_ROOT = Path(__file__).parents[3]
PROMPT_ROOT = REPOSITORY_ROOT / "prompts"
CATEGORY_IDS = (
    "genre",
    "tone",
    "prose_style",
    "perspective",
    "pacing",
    "control_mode",
    "player_agency",
    "consequence",
    "challenge",
    "extraction",
    "content_profile",
)


def test_loads_all_categories_defaults_and_non_selectable_boundary_directive() -> None:
    package = FilePromptPackageCatalog(PROMPT_ROOT).load("story.base", "1")

    assert {task.id for task in package.tasks} == {
        "story_generation",
        "worldstate_extraction",
    }
    assert {category.id for category in package.categories} == set(CATEGORY_IDS)
    assert {category.id: category.default_option_id for category in package.categories} == {
        "genre": "dark_fantasy",
        "tone": "balanced",
        "prose_style": "balanced",
        "perspective": "third_person_limited",
        "pacing": "balanced",
        "control_mode": "player",
        "player_agency": "strict",
        "consequence": "balanced",
        "challenge": "balanced",
        "extraction": "combined",
        "content_profile": "teen",
    }
    assert package.category("genre").option("steam_punk").description
    assert package.category("extraction").options[0].id == "combined"
    assert package.directive("narrative_boundaries").selectable is False
    assert package.directive("narrative_boundaries").text
    assert all(task.text for task in package.tasks)
    assert all(
        option.description
        for category in package.categories
        for option in category.options
    )


def test_summary_task_is_not_present() -> None:
    package = FilePromptPackageCatalog(PROMPT_ROOT).load("story.base", "1")

    with pytest.raises(PromptTaskNotFoundError):
        package.task("summary")


@pytest.mark.parametrize(
    ("package_id", "version"),
    [("missing", "1"), ("story.base", "2"), ("../story.base", "1"), ("story.base", "../1")],
)
def test_missing_or_unsafe_package_reference_is_not_treated_as_a_valid_package(
    package_id: str, version: str
) -> None:
    catalog = FilePromptPackageCatalog(PROMPT_ROOT)

    expected = InvalidPromptPackageError if "/" in package_id or "/" in version else PromptPackageNotFoundError
    with pytest.raises(expected):
        catalog.load(package_id, version)


@pytest.mark.parametrize(
    "variant",
    [
        "malformed",
        "identity",
        "wrong_type",
        "empty_text",
        "unknown_field",
        "missing_options",
        "invalid_default",
        "duplicate_task",
        "duplicate_category",
        "duplicate_option",
        "duplicate_directive",
    ],
)
def test_invalid_package_variants_fail_closed(tmp_path: Path, variant: str) -> None:
    path = tmp_path / "prompts" / "story.base" / "1.toml"
    path.parent.mkdir(parents=True)
    path.write_text(_synthetic_package(variant), encoding="utf-8")

    with pytest.raises(InvalidPromptPackageError):
        FilePromptPackageCatalog(tmp_path / "prompts").load("story.base", "1")


def _synthetic_package(variant: str) -> str:
    if variant == "malformed":
        return "[package\nid = 'story.base'"

    package_id = "wrong" if variant == "identity" else "story.base"
    version = "wrong" if variant == "identity" else "1"
    version_value = "1" if variant != "wrong_type" else "1"
    lines = [
        "[package]",
        f'id = "{package_id}"',
        "version = 1" if variant == "wrong_type" else f'version = {version!r}',
        "",
    ]
    if variant == "unknown_field":
        lines.append("unexpected = true")
        lines.append("")
    lines.extend(
        [
            "[[tasks]]",
            'id = "story_generation"',
            f'text = {"" if variant == "empty_text" else "story"!r}',
            "",
            "[[tasks]]",
            f'id = {"story_generation" if variant == "duplicate_task" else "worldstate_extraction"!r}',
            'text = "extract"',
            "",
        ]
    )
    for index, category_id in enumerate(CATEGORY_IDS):
        effective_id = "genre" if variant == "duplicate_category" and index == 1 else category_id
        lines.extend(
            [
                "[[categories]]",
                f'id = {effective_id!r}',
                f'default = {"missing" if variant == "invalid_default" and index == 0 else "default"!r}',
            ]
        )
        if not (variant == "missing_options" and index == 0):
            lines.extend(
                [
                    "",
                "[[categories.options]]",
                f'id = {"default" if variant == "duplicate_option" and index == 0 else "default"!r}',
                'description = "selection"',
            ]
        )
            if variant == "duplicate_option" and index == 0:
                lines.extend(
                    [
                        "",
                        "[[categories.options]]",
                        'id = "default"',
                        'description = "again"',
                    ]
                )
        lines.append("")
    lines.extend(
        [
            "[[directives]]",
            f'id = {"narrative_boundaries" if variant != "duplicate_directive" else "same"!r}',
            'selectable = false',
            'text = "boundaries"',
        ]
    )
    if variant == "duplicate_directive":
        lines.extend(
            [
                "",
                "[[directives]]",
                'id = "same"',
                "selectable = false",
                'text = "again"',
            ]
        )
    return "\n".join(lines) + "\n"

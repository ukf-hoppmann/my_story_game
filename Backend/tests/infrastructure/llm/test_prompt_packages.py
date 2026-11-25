from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from story_game.application import LLMGenerationCall, ModelSelection
from story_game.application.llm import (
    GenerationOptions,
    InitialWorldExtractionRequest,
    InvalidPromptPackageError,
    PromptCategoryNotFoundError,
    PromptDirectiveNotFoundError,
    PromptOptionNotFoundError,
    PromptPackageNotFoundError,
    PromptTaskNotFoundError,
    TurnExtractionRequest,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.infrastructure.llm.openai_compatible import (
    initial_extraction_wire,
    turn_extraction_wire,
)


REPOSITORY_ROOT = Path(__file__).parents[3]
PROMPT_ROOT = REPOSITORY_ROOT / "prompts"
CATEGORY_IDS = (
    "genre",
    "tone",
    "prose_style",
    "perspective",
    "pacing",
    "length",
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
        "story_initialization",
        "story_generation",
        "story_summary",
        "scene_image_prompt",
        "scene_image_prompt_compact",
        "worldstate_initialization",
        "worldstate_extraction",
    }
    assert {category.id for category in package.categories} == set(CATEGORY_IDS)
    assert {category.id: category.default_option_id for category in package.categories} == {
        "genre": "dark_fantasy",
        "tone": "balanced",
        "prose_style": "balanced",
        "perspective": "third_person_limited",
        "pacing": "balanced",
        "length": "standard",
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
    assert package.directive("narrative_boundaries").tasks == (
        "story_generation",
        "story_initialization",
    )
    assert {directive.id for directive in package.directives_for("story_generation")} == {
        "narrative_boundaries",
        "npc_agency",
        "genre_plot_variation",
    }
    assert {directive.id for directive in package.directives_for("worldstate_extraction")} == set()
    assert all(task.text for task in package.tasks)
    assert all(
        option.description
        for category in package.categories
        for option in category.options
    )


def _schema_names(node: object) -> set[str]:
    """Property names and enum values anywhere in a JSON schema."""
    names: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties":
                names.update(value)
            elif key == "enum":
                names.update(item for item in value if isinstance(item, str))
            names |= _schema_names(value)
    elif isinstance(node, list):
        for value in node:
            names |= _schema_names(value)
    return names


def _turn_extraction_schema() -> object:
    call = LLMGenerationCall(
        model_selection=ModelSelection("groq", "model"),
        generation_options=GenerationOptions(temperature=0.1),
        request=TurnExtractionRequest(
            system_prompts=("prompt",),
            world_state="world",
            narration="narration",
            language="de",
        ),
    )
    return turn_extraction_wire.build_request(call).response_format.schema


def _initial_extraction_schema() -> object:
    call = LLMGenerationCall(
        model_selection=ModelSelection("groq", "model"),
        generation_options=GenerationOptions(temperature=0.1),
        request=InitialWorldExtractionRequest(
            system_prompts=("prompt",),
            opening_narration="narration",
            language="de",
            perspective="third_person_limited",
            control_mode="player",
        ),
    )
    return initial_extraction_wire.build_request(call).response_format.schema


@pytest.mark.parametrize(
    ("task_id", "schema_of"),
    [
        ("worldstate_extraction", _turn_extraction_schema),
        ("worldstate_initialization", _initial_extraction_schema),
    ],
)
def test_extraction_task_text_names_only_fields_of_its_response_schema(
    task_id: str, schema_of: Callable[[], object]
) -> None:
    text = FilePromptPackageCatalog(PROMPT_ROOT).load("story.base", "1").task(task_id).text

    mentioned = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", text))

    assert mentioned - _schema_names(schema_of()) == set()


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
        "unknown_directive_task",
        "empty_directive_tasks",
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
            'id = "story_initialization"',
            'text = "initialization"',
            "",
            "[[tasks]]",
            'id = "story_generation"',
            f'text = {"" if variant == "empty_text" else "story"!r}',
            "",
            "[[tasks]]",
            'id = "story_summary"',
            'text = "summary"',
            "",
            "[[tasks]]",
            'id = "scene_image_prompt"',
            'text = "image prompt"',
            "",
            "[[tasks]]",
            'id = "scene_image_prompt_compact"',
            'text = "compact image prompt"',
            "",
            "[[tasks]]",
            'id = "worldstate_initialization"',
            'text = "initial extract"',
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
    if variant == "empty_directive_tasks":
        directive_tasks = "[]"
    elif variant == "unknown_directive_task":
        directive_tasks = '["not_a_task"]'
    else:
        directive_tasks = '["story_generation"]'
    lines.extend(
        [
            "[[directives]]",
            f'id = {"narrative_boundaries" if variant != "duplicate_directive" else "same"!r}',
            'selectable = false',
            f'tasks = {directive_tasks}',
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
                'tasks = ["story_generation"]',
                'text = "again"',
            ]
        )
    return "\n".join(lines) + "\n"


def test_references_list_every_package_version_file_in_the_root(tmp_path: Path) -> None:
    (tmp_path / "pkg.a").mkdir()
    (tmp_path / "pkg.a" / "1.toml").write_text("", encoding="utf-8")
    (tmp_path / "pkg.a" / "2.toml").write_text("", encoding="utf-8")
    (tmp_path / "pkg.b").mkdir()
    (tmp_path / "pkg.b" / "1.toml").write_text("", encoding="utf-8")
    (tmp_path / "pkg.b" / "notes.txt").write_text("", encoding="utf-8")
    (tmp_path / "stray.toml").write_text("", encoding="utf-8")

    references = FilePromptPackageCatalog(tmp_path).references()

    assert [(r.package_id, r.package_version) for r in references] == [
        ("pkg.a", "1"),
        ("pkg.a", "2"),
        ("pkg.b", "1"),
    ]


def test_references_of_a_missing_root_are_empty(tmp_path: Path) -> None:
    assert FilePromptPackageCatalog(tmp_path / "missing").references() == ()

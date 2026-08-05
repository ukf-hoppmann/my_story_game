from __future__ import annotations

import ast
from pathlib import Path

import pytest


SOURCE_ROOT = Path(__file__).parents[2] / "src" / "story_game"


def _story_game_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name for alias in node.names if alias.name.startswith("story_game")
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("story_game"):
                imports.add(node.module)
    return imports


def _python_files(layer: str) -> list[Path]:
    return sorted((SOURCE_ROOT / layer).rglob("*.py"))


@pytest.mark.parametrize("path", _python_files("domain"), ids=lambda path: path.name)
def test_domain_does_not_depend_on_outer_layers(path: Path) -> None:
    forbidden = (
        "story_game.application",
        "story_game.api",
        "story_game.infrastructure",
    )

    violations = {
        imported
        for imported in _story_game_imports(path)
        if imported.startswith(forbidden)
    }

    assert violations == set()


@pytest.mark.parametrize(
    "path", _python_files("application"), ids=lambda path: path.name
)
def test_application_does_not_depend_on_outer_adapters(path: Path) -> None:
    forbidden = ("story_game.api", "story_game.infrastructure")

    violations = {
        imported
        for imported in _story_game_imports(path)
        if imported.startswith(forbidden)
    }

    assert violations == set()


@pytest.mark.parametrize("path", _python_files("api"), ids=lambda path: path.name)
def test_api_uses_infrastructure_only_in_composition_root(path: Path) -> None:
    if path == SOURCE_ROOT / "api" / "app.py":
        return

    violations = {
        imported
        for imported in _story_game_imports(path)
        if imported.startswith("story_game.infrastructure")
    }

    assert violations == set()

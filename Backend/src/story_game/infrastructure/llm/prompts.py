"""File-backed prompt package catalog."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from story_game.application.llm import (
    InvalidPromptPackageError,
    PromptCategory,
    PromptDirective,
    PromptOption,
    PromptPackage,
    PromptPackageCatalog,
    PromptPackageNotFoundError,
    PromptTask,
)


_TASK_IDS = {
    "story_initialization",
    "story_generation",
    "story_summary",
    "worldstate_initialization",
    "worldstate_extraction",
}
_CATEGORY_IDS = {
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
}


class FilePromptPackageCatalog(PromptPackageCatalog):
    """Load ``<root>/<package-id>/<version>.toml`` with fail-closed checks."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def load(self, package_id: str, version: str) -> PromptPackage:
        package_id = _package_reference(package_id, "Paket-ID")
        version = _package_reference(version, "Paket-Version")
        path = self._root / package_id / f"{version}.toml"
        if not path.is_file():
            raise PromptPackageNotFoundError(
                f"Das Prompt-Paket {package_id!r} in Version {version!r} wurde nicht gefunden"
            )
        try:
            raw_document = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise InvalidPromptPackageError(
                f"{path}: Das Prompt-Paket ist kein gültiges TOML"
            ) from error
        except (OSError, UnicodeError) as error:
            raise InvalidPromptPackageError(
                f"{path}: Das Prompt-Paket konnte nicht gelesen werden"
            ) from error
        try:
            return _parse_package(raw_document, package_id, version, path)
        except InvalidPromptPackageError:
            raise
        except (TypeError, ValueError, KeyError) as error:
            raise InvalidPromptPackageError(
                f"{path}: Das Prompt-Paket ist strukturell ungültig"
            ) from error


def _parse_package(
    document: dict[str, Any],
    requested_id: str,
    requested_version: str,
    path: Path,
) -> PromptPackage:
    _keys(document, {"package", "tasks", "categories", "directives"}, "Hauptdokument", path)
    identity = _table(document["package"], "package", path)
    _keys(identity, {"id", "version"}, "package", path)
    package_id = _text(identity, "id", "package", path)
    version = _text(identity, "version", "package", path)
    if package_id != requested_id or version != requested_version:
        raise _invalid(path, "package.id und package.version müssen der Referenz entsprechen")

    tasks = _tasks(document["tasks"], path)
    categories = _categories(document["categories"], path)
    directives = _directives(document["directives"], path)
    return PromptPackage(
        id=package_id,
        version=version,
        tasks=tuple(tasks),
        categories=tuple(categories),
        directives=tuple(directives),
    )


def _tasks(raw: Any, path: Path) -> list[PromptTask]:
    entries = _array_of_tables(raw, "tasks", path)
    values: list[PromptTask] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"tasks[{index}]"
        _keys(entry, {"id", "text"}, label, path)
        task_id = _unique_id(_text(entry, "id", label, path), seen, label, path)
        values.append(PromptTask(task_id, _text(entry, "text", label, path)))
    if set(seen) != _TASK_IDS:
        raise _invalid(
            path,
            "tasks müssen genau story_initialization, story_generation, "
            "worldstate_initialization und worldstate_extraction enthalten",
        )
    return values


def _categories(raw: Any, path: Path) -> list[PromptCategory]:
    entries = _array_of_tables(raw, "categories", path)
    values: list[PromptCategory] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"categories[{index}]"
        _keys(entry, {"id", "default", "options"}, label, path)
        category_id = _unique_id(_text(entry, "id", label, path), seen, label, path)
        options = _options(entry["options"], label, path)
        default = _text(entry, "default", label, path)
        if default not in {option.id for option in options}:
            raise _invalid(path, f"{label}.default verweist auf keine vorhandene Option")
        values.append(PromptCategory(category_id, default, tuple(options)))
    if set(seen) != _CATEGORY_IDS:
        raise _invalid(path, "categories enthalten nicht genau die vereinbarten Kategorien")
    return values


def _options(raw: Any, parent_label: str, path: Path) -> list[PromptOption]:
    entries = _array_of_tables(raw, f"{parent_label}.options", path)
    values: list[PromptOption] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"{parent_label}.options[{index}]"
        _keys(entry, {"id", "description"}, label, path)
        option_id = _unique_id(_text(entry, "id", label, path), seen, label, path)
        values.append(PromptOption(option_id, _text(entry, "description", label, path)))
    if not values:
        raise _invalid(path, f"{parent_label}.options darf nicht leer sein")
    return values


def _directives(raw: Any, path: Path) -> list[PromptDirective]:
    entries = _array_of_tables(raw, "directives", path)
    values: list[PromptDirective] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"directives[{index}]"
        _keys(entry, {"id", "text", "selectable"}, label, path)
        directive_id = _unique_id(_text(entry, "id", label, path), seen, label, path)
        selectable = entry["selectable"]
        if not isinstance(selectable, bool) or selectable:
            raise _invalid(path, f"{label}.selectable muss false sein")
        values.append(
            PromptDirective(directive_id, _text(entry, "text", label, path), selectable)
        )
    if "narrative_boundaries" not in seen:
        raise _invalid(path, "directives müssen narrative_boundaries enthalten")
    return values


def _package_reference(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise InvalidPromptPackageError(f"{label} muss Text sein")
    value = value.strip()
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
    ):
        raise InvalidPromptPackageError(f"{label} darf keine Pfadbestandteile enthalten")
    return value


def _array_of_tables(raw: Any, label: str, path: Path) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        raise _invalid(path, f"{label} muss ein Array aus Tabellen sein")
    return raw


def _table(raw: Any, label: str, path: Path) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _invalid(path, f"{label} muss eine Tabelle sein")
    return raw


def _keys(document: dict[str, Any], expected: set[str], label: str, path: Path) -> None:
    unknown = set(document) - expected
    missing = expected - set(document)
    if unknown:
        raise _invalid(path, f"{label} enthält unbekannte Felder: {sorted(unknown)}")
    if missing:
        raise _invalid(path, f"{label} fehlen Felder: {sorted(missing)}")


def _text(document: dict[str, Any], key: str, label: str, path: Path) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _invalid(path, f"{label}.{key} muss nichtleerer Text sein")
    return value.strip()


def _unique_id(value: str, seen: set[str], label: str, path: Path) -> str:
    if value in seen:
        raise _invalid(path, f"{label}.id ist doppelt: {value!r}")
    seen.add(value)
    return value


def _invalid(path: Path, message: str) -> InvalidPromptPackageError:
    return InvalidPromptPackageError(f"{path}: {message}")


__all__ = ["FilePromptPackageCatalog"]

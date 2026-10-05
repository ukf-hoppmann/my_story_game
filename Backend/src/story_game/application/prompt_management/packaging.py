"""Conversion between a ``PromptPackage`` and its flat, storable entries."""

from __future__ import annotations

from story_game.application.llm import (
    InvalidPromptPackageError,
    PromptCategory,
    PromptDirective,
    PromptOption,
    PromptPackage,
    PromptTask,
)

from .models import PromptEntry, PromptEntryKind

_KIND_ORDER = {PromptEntryKind.TASK: 0, PromptEntryKind.OPTION: 1, PromptEntryKind.DIRECTIVE: 2}


def flatten_package(package: PromptPackage) -> tuple[PromptEntry, ...]:
    """One entry per task, option and directive; categories are implied by option keys."""
    entries: list[PromptEntry] = [
        PromptEntry(PromptEntryKind.TASK, task.id, task.text, position)
        for position, task in enumerate(package.tasks)
    ]
    position = 0
    for category in package.categories:
        for option in category.options:
            entries.append(
                PromptEntry(
                    PromptEntryKind.OPTION,
                    f"{category.id}/{option.id}",
                    option.description,
                    position,
                    is_default=option.id == category.default_option_id,
                )
            )
            position += 1
    entries.extend(
        PromptEntry(
            PromptEntryKind.DIRECTIVE,
            directive.id,
            directive.text,
            position,
            task_ids=directive.tasks,
        )
        for position, directive in enumerate(package.directives)
    )
    return tuple(entries)


def assemble_package(
    package_id: str, package_version: str, entries: tuple[PromptEntry, ...]
) -> PromptPackage:
    """Rebuild the package; fail closed when its structure is incomplete."""
    ordered = sorted(entries, key=lambda entry: (_KIND_ORDER[entry.kind], entry.position))
    tasks = tuple(
        PromptTask(entry.key, entry.text)
        for entry in ordered
        if entry.kind == PromptEntryKind.TASK
    )
    directives = tuple(
        PromptDirective(entry.key, entry.text, False, entry.task_ids)
        for entry in ordered
        if entry.kind == PromptEntryKind.DIRECTIVE
    )
    return PromptPackage(
        id=package_id,
        version=package_version,
        tasks=tasks,
        categories=_categories(
            package_id, package_version, [e for e in ordered if e.kind == PromptEntryKind.OPTION]
        ),
        directives=directives,
    )


def _categories(
    package_id: str, package_version: str, options: list[PromptEntry]
) -> tuple[PromptCategory, ...]:
    grouped: dict[str, list[PromptEntry]] = {}
    for entry in options:
        category_id, separator, option_id = entry.key.partition("/")
        if not separator or not category_id or not option_id:
            raise InvalidPromptPackageError(
                f"{package_id}/{package_version}: Der Optionsschlüssel {entry.key!r} "
                "muss die Form <Kategorie>/<Option> haben"
            )
        grouped.setdefault(category_id, []).append(entry)
    categories: list[PromptCategory] = []
    for category_id, members in grouped.items():
        defaults = [member for member in members if member.is_default]
        if len(defaults) != 1:
            raise InvalidPromptPackageError(
                f"{package_id}/{package_version}: Die Kategorie {category_id!r} braucht "
                "genau eine Standardoption"
            )
        categories.append(
            PromptCategory(
                category_id,
                defaults[0].key.partition("/")[2],
                tuple(
                    PromptOption(member.key.partition("/")[2], member.text) for member in members
                ),
            )
        )
    return tuple(categories)


__all__ = ["assemble_package", "flatten_package"]

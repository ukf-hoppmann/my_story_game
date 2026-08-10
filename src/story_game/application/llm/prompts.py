"""Provider-independent prompt package values and lookup errors."""

from __future__ import annotations

from dataclasses import dataclass


class PromptPackageError(ValueError):
    """Base error for an invalid or unavailable prompt package lookup."""


class PromptPackageNotFoundError(PromptPackageError):
    """The requested prompt package or version does not exist."""


class InvalidPromptPackageError(PromptPackageError):
    """The requested package exists but cannot be validated safely."""


class PromptTaskNotFoundError(PromptPackageError):
    """A package does not contain the requested model task."""


class PromptCategoryNotFoundError(PromptPackageError):
    """A package does not contain the requested selectable category."""


class PromptOptionNotFoundError(PromptPackageError):
    """A category does not contain the requested option."""


class PromptDirectiveNotFoundError(PromptPackageError):
    """A package does not contain the requested directive."""


@dataclass(frozen=True, slots=True)
class PromptTask:
    """One task prompt with concrete behavioral instructions."""

    id: str
    text: str


@dataclass(frozen=True, slots=True)
class PromptOption:
    """One selectable category option and its behavioral meaning."""

    id: str
    description: str


@dataclass(frozen=True, slots=True)
class PromptCategory:
    """A selectable category with one package-defined default option."""

    id: str
    default_option_id: str
    options: tuple[PromptOption, ...]

    def option(self, option_id: str) -> PromptOption:
        for option in self.options:
            if option.id == option_id:
                return option
        raise PromptOptionNotFoundError(
            f"Die Prompt-Option {option_id!r} ist in {self.id!r} nicht vorhanden"
        )


@dataclass(frozen=True, slots=True)
class PromptDirective:
    """A non-selectable instruction that is always available to the use case."""

    id: str
    text: str
    selectable: bool = False


@dataclass(frozen=True, slots=True)
class PromptPackage:
    """Validated, provider-neutral contents of one versioned prompt package."""

    id: str
    version: str
    tasks: tuple[PromptTask, ...]
    categories: tuple[PromptCategory, ...]
    directives: tuple[PromptDirective, ...]

    def task(self, task_id: str) -> PromptTask:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise PromptTaskNotFoundError(
            f"Die Prompt-Aufgabe {task_id!r} ist im Paket {self.id!r} nicht vorhanden"
        )

    def category(self, category_id: str) -> PromptCategory:
        for category in self.categories:
            if category.id == category_id:
                return category
        raise PromptCategoryNotFoundError(
            f"Die Prompt-Kategorie {category_id!r} ist im Paket {self.id!r} nicht vorhanden"
        )

    def directive(self, directive_id: str) -> PromptDirective:
        for directive in self.directives:
            if directive.id == directive_id:
                return directive
        raise PromptDirectiveNotFoundError(
            f"Die Prompt-Direktive {directive_id!r} ist im Paket {self.id!r} nicht vorhanden"
        )


__all__ = [
    "InvalidPromptPackageError",
    "PromptCategory",
    "PromptCategoryNotFoundError",
    "PromptDirective",
    "PromptDirectiveNotFoundError",
    "PromptOption",
    "PromptOptionNotFoundError",
    "PromptPackage",
    "PromptPackageError",
    "PromptPackageNotFoundError",
    "PromptTask",
    "PromptTaskNotFoundError",
]

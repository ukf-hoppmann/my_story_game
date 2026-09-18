"""Resolve persisted prompt selections into task-specific instructions."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.domain import GameConfiguration

from .ports import PromptPackageCatalog
from .prompts import PromptDirective, PromptOption, PromptTask


@dataclass(frozen=True, slots=True)
class ResolvedPromptOption:
    """One package description selected for a known prompt category."""

    category_id: str
    option_id: str
    description: str


@dataclass(frozen=True, slots=True)
class StoryPromptSelection:
    """Resolved story-prompt meaning before request-specific rendering."""

    task: PromptTask
    options: tuple[ResolvedPromptOption, ...]
    language: str
    narrative_boundaries: tuple[str, ...]
    directives: tuple[PromptDirective, ...]


@dataclass(frozen=True, slots=True)
class ExtractionPromptSelection:
    """Resolved Extraction meaning independent from the Story prompt profile."""

    task: PromptTask
    option: ResolvedPromptOption
    directives: tuple[PromptDirective, ...]


class StoryPromptSelectionResolver:
    """Resolve the profile categories required exclusively for story generation."""

    def __init__(self, catalog: PromptPackageCatalog) -> None:
        self.catalog = catalog

    def resolve(self, configuration: GameConfiguration) -> StoryPromptSelection:
        package = self.catalog.load(
            configuration.prompt_package_id,
            configuration.prompt_package_version,
        )
        options = _resolved_story_options(configuration, package)
        task = package.task("story_generation")
        return StoryPromptSelection(
            task=task,
            options=options,
            language=configuration.language,
            narrative_boundaries=configuration.narrative_boundaries,
            directives=package.directives_for(task.id),
        )


class StoryInitializationPromptResolver:
    """Resolve the same narrative profile for an opening without state context."""

    def __init__(self, catalog: PromptPackageCatalog) -> None:
        self.catalog = catalog

    def resolve(self, configuration: GameConfiguration) -> StoryPromptSelection:
        package = self.catalog.load(
            configuration.prompt_package_id,
            configuration.prompt_package_version,
        )
        options = _resolved_story_options(configuration, package)
        task = package.task("story_initialization")
        return StoryPromptSelection(
            task=task,
            options=options,
            language=configuration.language,
            narrative_boundaries=configuration.narrative_boundaries,
            directives=package.directives_for(task.id),
        )


class ExtractionPromptSelectionResolver:
    """Resolve the dedicated combined Extraction option for one package."""

    def __init__(self, catalog: PromptPackageCatalog) -> None:
        self.catalog = catalog

    def resolve(self, package_id: str, package_version: str) -> ExtractionPromptSelection:
        package = self.catalog.load(package_id, package_version)
        option = package.category("extraction").option("combined")
        task = package.task("worldstate_extraction")
        return ExtractionPromptSelection(
            task=task,
            option=_resolved_option("extraction", "combined", option),
            directives=package.directives_for(task.id),
        )


class SummaryPromptSelectionResolver:
    """Resolve the summary instructions, which need no story profile."""

    def __init__(self, catalog: PromptPackageCatalog) -> None:
        self.catalog = catalog

    def resolve(self, package_id: str, package_version: str) -> PromptTask:
        return self.catalog.load(package_id, package_version).task("story_summary")


class InitialExtractionPromptSelectionResolver:
    """Resolve the extraction instructions used only for an opening narration."""

    def __init__(self, catalog: PromptPackageCatalog) -> None:
        self.catalog = catalog

    def resolve(self, package_id: str, package_version: str) -> ExtractionPromptSelection:
        package = self.catalog.load(package_id, package_version)
        option = package.category("extraction").option("combined")
        task = package.task("worldstate_initialization")
        return ExtractionPromptSelection(
            task=task,
            option=_resolved_option("extraction", "combined", option),
            directives=package.directives_for(task.id),
        )


def _resolved_option(
    category_id: str, option_id: str, option: PromptOption
) -> ResolvedPromptOption:
    return ResolvedPromptOption(category_id, option_id, option.description)


def _resolved_story_options(
    configuration: GameConfiguration,
    package,
) -> tuple[ResolvedPromptOption, ...]:
    resolved = tuple(
        _resolved_option(
            category_id,
            option_id,
            package.category(category_id).option(option_id),
        )
        for category_id, option_id in configuration.prompt_profile.selections()
    )
    if configuration.prompt_profile.control_mode == "director":
        return tuple(item for item in resolved if item.category_id != "player_agency")
    return resolved


__all__ = [
    "ExtractionPromptSelection",
    "ExtractionPromptSelectionResolver",
    "InitialExtractionPromptSelectionResolver",
    "ResolvedPromptOption",
    "StoryPromptSelection",
    "StoryInitializationPromptResolver",
    "StoryPromptSelectionResolver",
    "SummaryPromptSelectionResolver",
]

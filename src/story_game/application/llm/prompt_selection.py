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
    boundary_directive: PromptDirective


@dataclass(frozen=True, slots=True)
class ExtractionPromptSelection:
    """Resolved Extraction meaning independent from the Story prompt profile."""

    task: PromptTask
    option: ResolvedPromptOption


class StoryPromptSelectionResolver:
    """Resolve the profile categories required exclusively for story generation."""

    def __init__(self, catalog: PromptPackageCatalog) -> None:
        self.catalog = catalog

    def resolve(self, configuration: GameConfiguration) -> StoryPromptSelection:
        package = self.catalog.load(
            configuration.prompt_package_id,
            configuration.prompt_package_version,
        )
        options = tuple(
            _resolved_option(
                category_id,
                option_id,
                package.category(category_id).option(option_id),
            )
            for category_id, option_id in configuration.prompt_profile.selections()
        )
        return StoryPromptSelection(
            task=package.task("story_generation"),
            options=options,
            language=configuration.language,
            narrative_boundaries=configuration.narrative_boundaries,
            boundary_directive=package.directive("narrative_boundaries"),
        )


class ExtractionPromptSelectionResolver:
    """Resolve the dedicated combined Extraction option for one package."""

    def __init__(self, catalog: PromptPackageCatalog) -> None:
        self.catalog = catalog

    def resolve(self, package_id: str, package_version: str) -> ExtractionPromptSelection:
        package = self.catalog.load(package_id, package_version)
        option = package.category("extraction").option("combined")
        return ExtractionPromptSelection(
            task=package.task("worldstate_extraction"),
            option=_resolved_option("extraction", "combined", option),
        )


def _resolved_option(
    category_id: str, option_id: str, option: PromptOption
) -> ResolvedPromptOption:
    return ResolvedPromptOption(category_id, option_id, option.description)


__all__ = [
    "ExtractionPromptSelection",
    "ExtractionPromptSelectionResolver",
    "ResolvedPromptOption",
    "StoryPromptSelection",
    "StoryPromptSelectionResolver",
]

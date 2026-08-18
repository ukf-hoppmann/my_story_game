from __future__ import annotations

import pytest

from story_game.application.llm import (
    PromptCategoryNotFoundError,
    PromptDirectiveNotFoundError,
    PromptOptionNotFoundError,
    PromptPackage,
    PromptTaskNotFoundError,
)


def test_prompt_package_lookups_are_task_and_selection_specific() -> None:
    package = PromptPackage(
        id="story.base",
        version="1",
        tasks=(),
        categories=(),
        directives=(),
    )

    with pytest.raises(PromptTaskNotFoundError):
        package.task("summary")
    with pytest.raises(PromptCategoryNotFoundError):
        package.category("unknown")
    with pytest.raises(PromptDirectiveNotFoundError):
        package.directive("unknown")


def test_missing_option_is_reported_by_the_category() -> None:
    from story_game.application.llm import PromptCategory, PromptOption

    category = PromptCategory("genre", "fantasy", (PromptOption("fantasy", "Abenteuer"),))

    with pytest.raises(PromptOptionNotFoundError):
        category.option("mystery")

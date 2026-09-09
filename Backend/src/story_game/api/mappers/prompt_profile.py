"""Translate a validated prompt package into its transport catalog."""

from __future__ import annotations

from story_game.api.schemas.prompt_profile import (
    PromptCategoryModel,
    PromptOptionModel,
    PromptPackageCatalogModel,
)
from story_game.application.llm import PromptPackage


def prompt_package_to_api(package: PromptPackage) -> PromptPackageCatalogModel:
    return PromptPackageCatalogModel(
        package_id=package.id,
        package_version=package.version,
        categories=[
            PromptCategoryModel(
                id=category.id,
                default_option_id=category.default_option_id,
                options=[
                    PromptOptionModel(id=option.id, description=option.description)
                    for option in category.options
                ],
            )
            for category in package.categories
        ],
    )

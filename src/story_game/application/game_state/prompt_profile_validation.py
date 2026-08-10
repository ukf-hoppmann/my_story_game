"""Application validation for persisted prompt-profile selections."""

from __future__ import annotations

from story_game.application.llm import (
    InvalidPromptPackageError,
    PromptCategoryNotFoundError,
    PromptOptionNotFoundError,
    PromptPackageCatalog,
    PromptPackageError,
    PromptPackageNotFoundError,
)
from story_game.domain import GameConfiguration

from .errors import (
    InvalidPromptPackageReference,
    InvalidPromptSelection,
    PromptPackageConfigurationInvalid,
)


class PromptProfileValidator:
    """Validate every explicit selection against the referenced package."""

    def __init__(self, catalog: PromptPackageCatalog) -> None:
        self.catalog = catalog

    def validate(
        self, configuration: GameConfiguration
    ) -> (
        InvalidPromptSelection
        | InvalidPromptPackageReference
        | PromptPackageConfigurationInvalid
        | None
    ):
        try:
            package = self.catalog.load(
                configuration.prompt_package_id,
                configuration.prompt_package_version,
            )
        except PromptPackageNotFoundError as error:
            return InvalidPromptPackageReference(str(error))
        except (InvalidPromptPackageError, PromptPackageError) as error:
            return PromptPackageConfigurationInvalid(str(error))

        for category_id, option_id in configuration.prompt_profile.selections():
            try:
                package.category(category_id).option(option_id)
            except PromptOptionNotFoundError:
                return InvalidPromptSelection(category_id, option_id)
            except PromptCategoryNotFoundError as error:
                return PromptPackageConfigurationInvalid(str(error))
        return None


__all__ = ["PromptProfileValidator"]

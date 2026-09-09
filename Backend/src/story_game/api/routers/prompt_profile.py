"""Read-only endpoint exposing the selectable story-prompt catalog."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from story_game.api.dependencies import ApiDependencies, get_api_dependencies
from story_game.api.mappers import prompt_package_to_api
from story_game.api.schemas.prompt_profile import PromptPackageCatalogModel
from story_game.application.llm import PromptPackageError

router = APIRouter(prefix="/api/v1/prompt-profile", tags=["prompt-profile"])

_PACKAGE_ID = "story.base"
_PACKAGE_VERSION = "1"


@router.get(
    "",
    response_model=PromptPackageCatalogModel,
    summary="List every selectable prompt-profile category and its options",
)
def get_prompt_profile_catalog(
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
) -> PromptPackageCatalogModel:
    try:
        package = dependencies.prompt_catalog.load(_PACKAGE_ID, _PACKAGE_VERSION)
    except PromptPackageError as error:
        # Not a caller mistake — the referenced package/version is a fixed
        # server-side default, not something the client supplies.
        raise HTTPException(status_code=500, detail=str(error)) from error
    return prompt_package_to_api(package)

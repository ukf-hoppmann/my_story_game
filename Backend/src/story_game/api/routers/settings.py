"""Read-only game settings every signed-in player may see."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from story_game.api.dependencies import (
    ApiDependencies,
    get_api_dependencies,
    get_current_initiator,
)
from story_game.api.results import unwrap
from story_game.api.schemas.settings import WorldTrackingStatusModel
from story_game.application import RunInitiator
from story_game.application.world_tracking import GetWorldTrackingRequest

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get(
    "/world-tracking",
    response_model=WorldTrackingStatusModel,
    summary="Whether world tracking is on, so the play screen can say so",
)
def world_tracking_status(
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> WorldTrackingStatusModel:
    if dependencies.world_tracking is None:
        raise RuntimeError("Die Einstellung zum Welt-Tracking wurde nicht initialisiert")
    setting = unwrap(dependencies.world_tracking.get.apply(GetWorldTrackingRequest()))
    return WorldTrackingStatusModel(enabled=setting.enabled)

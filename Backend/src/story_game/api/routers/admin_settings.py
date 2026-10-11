"""Admin endpoints for global game settings (role ``admin`` only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from story_game.api.auth import VerifiedCaller
from story_game.api.dependencies import ApiDependencies, get_api_dependencies, require_admin
from story_game.api.results import unwrap
from story_game.api.schemas.settings import (
    UpdateWorldTrackingRequestModel,
    WorldTrackingModel,
)
from story_game.application.world_tracking import (
    GetWorldTrackingRequest,
    SetWorldTrackingRequest,
    WorldTrackingOperations,
    WorldTrackingSetting,
)

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin-settings"])


def _operations(dependencies: ApiDependencies) -> WorldTrackingOperations:
    if dependencies.world_tracking is None:
        raise RuntimeError("Die Einstellung zum Welt-Tracking wurde nicht initialisiert")
    return dependencies.world_tracking


def _to_model(setting: WorldTrackingSetting) -> WorldTrackingModel:
    return WorldTrackingModel(
        enabled=setting.enabled,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by,
    )


@router.get(
    "/world-tracking",
    response_model=WorldTrackingModel,
    summary="Whether world extraction runs at story start and on every turn",
)
def get_world_tracking(
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> WorldTrackingModel:
    return _to_model(unwrap(_operations(dependencies).get.apply(GetWorldTrackingRequest())))


@router.put(
    "/world-tracking",
    response_model=WorldTrackingModel,
    summary="Switch world extraction on or off for all games",
)
def update_world_tracking(
    payload: UpdateWorldTrackingRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> WorldTrackingModel:
    editor = admin.username or admin.initiator.subject
    return _to_model(
        unwrap(
            _operations(dependencies).set.apply(
                SetWorldTrackingRequest(payload.enabled, editor)
            )
        )
    )

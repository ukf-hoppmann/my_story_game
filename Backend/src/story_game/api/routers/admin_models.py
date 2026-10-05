"""Admin endpoints for the versioned per-task model settings (role ``admin`` only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from story_game.api.auth import VerifiedCaller
from story_game.api.dependencies import ApiDependencies, get_api_dependencies, require_admin
from story_game.api.results import unwrap
from story_game.api.schemas.admin_models import (
    ModelCandidateModel,
    ModelSettingModel,
    ModelSettingsOverviewModel,
    ModelSettingVersionListModel,
    ResetModelSettingsRequestModel,
    UpdateModelSettingRequestModel,
)
from story_game.application.llm import GenerationTask
from story_game.application.model_settings import (
    ListModelSettingHistoryRequest,
    ListModelSettingsRequest,
    ModelSettingsOperations,
    ModelSettingSource,
    ModelSettingVersion,
    ResetModelSettingsRequest,
    UpdateModelSettingRequest,
)

router = APIRouter(prefix="/api/v1/admin/models", tags=["admin-models"])


def _operations(dependencies: ApiDependencies) -> ModelSettingsOperations:
    if dependencies.model_settings is None:
        raise RuntimeError("Die Modellverwaltung wurde nicht initialisiert")
    return dependencies.model_settings


def _editor(caller: VerifiedCaller) -> str:
    """The name recorded as author: the username, else the token subject."""
    return caller.username or caller.initiator.subject


def _to_model(version: ModelSettingVersion) -> ModelSettingModel:
    setting = version.setting
    return ModelSettingModel(
        version_id=version.version_id.value,
        task=setting.task,
        model_ref=setting.model_ref,
        temperature=setting.temperature,
        max_output_tokens=setting.max_output_tokens,
        source=version.source.value,
        created_at=version.created_at,
        created_by=version.created_by,
        is_active=version.is_active,
        is_modified=version.is_active and version.source is ModelSettingSource.UI,
    )


@router.get(
    "",
    response_model=ModelSettingsOverviewModel,
    summary="List the active model choice of every task and the selectable models",
)
def list_model_settings(
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> ModelSettingsOverviewModel:
    overview = unwrap(_operations(dependencies).overview.apply(ListModelSettingsRequest()))
    return ModelSettingsOverviewModel(
        settings=[_to_model(version) for version in overview.settings],
        candidates=[
            ModelCandidateModel(
                task=c.task, model_ref=c.model_ref, provider_id=c.provider_id, model_id=c.model_id
            )
            for c in overview.candidates
        ],
    )


@router.get(
    "/history",
    response_model=ModelSettingVersionListModel,
    summary="List every version of one task's model choice, newest first",
)
def model_setting_history(
    task: Annotated[GenerationTask, Query()],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> ModelSettingVersionListModel:
    versions = unwrap(
        _operations(dependencies).history.apply(ListModelSettingHistoryRequest(task))
    )
    return ModelSettingVersionListModel(versions=[_to_model(version) for version in versions])


@router.put(
    "",
    response_model=ModelSettingModel,
    summary="Save the model choice of a task as its new active version",
)
def update_model_setting(
    payload: UpdateModelSettingRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> ModelSettingModel:
    version = unwrap(
        _operations(dependencies).update.apply(
            UpdateModelSettingRequest(
                payload.task,
                payload.model_ref,
                payload.temperature,
                payload.max_output_tokens,
                _editor(admin),
            )
        )
    )
    return _to_model(version)


@router.post(
    "/reset",
    response_model=ModelSettingVersionListModel,
    summary="Restore the shipped model choice of one task, or of all tasks",
)
def reset_model_settings(
    payload: ResetModelSettingsRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> ModelSettingVersionListModel:
    versions = unwrap(
        _operations(dependencies).reset.apply(ResetModelSettingsRequest(payload.task, _editor(admin)))
    )
    return ModelSettingVersionListModel(versions=[_to_model(version) for version in versions])

"""Admin endpoints for the versioned system prompts (role ``admin`` only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from story_game.api.auth import VerifiedCaller
from story_game.api.dependencies import ApiDependencies, get_api_dependencies, require_admin
from story_game.api.results import unwrap
from story_game.api.schemas.admin_prompts import (
    PromptListModel,
    PromptVersionListModel,
    PromptVersionModel,
    ResetPromptsRequestModel,
    UpdatePromptTextRequestModel,
)
from story_game.application.prompt_management import (
    ListPromptEntriesRequest,
    ListPromptHistoryRequest,
    PromptEntryKind,
    PromptEntryRef,
    PromptManagementOperations,
    PromptVersion,
    PromptVersionSource,
    ResetPromptTextRequest,
    UpdatePromptTextRequest,
)

router = APIRouter(prefix="/api/v1/admin/prompts", tags=["admin-prompts"])

_PACKAGE_ID = "story.base"
_PACKAGE_VERSION = "1"


def _operations(dependencies: ApiDependencies) -> PromptManagementOperations:
    if dependencies.prompt_management is None:
        raise RuntimeError("Die Prompt-Verwaltung wurde nicht initialisiert")
    return dependencies.prompt_management


def _editor(caller: VerifiedCaller) -> str:
    """The name recorded as author: the username, else the token subject."""
    return caller.username or caller.initiator.subject


def _to_model(version: PromptVersion) -> PromptVersionModel:
    entry = version.entry
    return PromptVersionModel(
        version_id=version.version_id.value,
        kind=entry.kind,
        key=entry.key,
        text=entry.text,
        is_default=entry.is_default,
        task_ids=list(entry.task_ids),
        source=version.source.value,
        created_at=version.created_at,
        created_by=version.created_by,
        is_active=version.is_active,
        is_modified=version.is_active and version.source is PromptVersionSource.UI,
    )


@router.get("", response_model=PromptListModel, summary="List the currently active prompts")
def list_prompts(
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> PromptListModel:
    versions = unwrap(
        _operations(dependencies).entries.apply(
            ListPromptEntriesRequest(_PACKAGE_ID, _PACKAGE_VERSION)
        )
    )
    return PromptListModel(
        package_id=_PACKAGE_ID,
        package_version=_PACKAGE_VERSION,
        entries=[_to_model(version) for version in versions],
    )


@router.get(
    "/history",
    response_model=PromptVersionListModel,
    summary="List every version of one prompt, newest first",
)
def prompt_history(
    kind: Annotated[PromptEntryKind, Query()],
    key: Annotated[str, Query(min_length=1)],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> PromptVersionListModel:
    versions = unwrap(
        _operations(dependencies).history.apply(
            ListPromptHistoryRequest(_PACKAGE_ID, _PACKAGE_VERSION, kind, key)
        )
    )
    return PromptVersionListModel(versions=[_to_model(version) for version in versions])


@router.put(
    "",
    response_model=PromptVersionModel,
    summary="Save an edited prompt text as the new active version",
)
def update_prompt(
    payload: UpdatePromptTextRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> PromptVersionModel:
    version = unwrap(
        _operations(dependencies).update.apply(
            UpdatePromptTextRequest(
                _PACKAGE_ID, _PACKAGE_VERSION, payload.kind, payload.key, payload.text, _editor(admin)
            )
        )
    )
    return _to_model(version)


@router.post(
    "/reset",
    response_model=PromptVersionListModel,
    summary="Restore the shipped original of one prompt, or of all prompts",
)
def reset_prompts(
    payload: ResetPromptsRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> PromptVersionListModel:
    target = (
        None
        if payload.kind is None or payload.key is None
        else PromptEntryRef(payload.kind, payload.key)
    )
    versions = unwrap(
        _operations(dependencies).reset.apply(
            ResetPromptTextRequest(_PACKAGE_ID, _PACKAGE_VERSION, target, _editor(admin))
        )
    )
    return PromptVersionListModel(versions=[_to_model(version) for version in versions])

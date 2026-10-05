"""Admin endpoints for the versioned system prompts (role ``admin`` only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from story_game.api.auth import VerifiedCaller
from story_game.api.dependencies import ApiDependencies, get_api_dependencies, require_admin
from story_game.api.results import unwrap
from story_game.api.schemas.admin_prompts import (
    CreatePromptOptionRequestModel,
    PromptListModel,
    PromptOptionRefModel,
    PromptVersionListModel,
    PromptVersionModel,
    RemovalOutcomeModel,
    RemovalResultModel,
    RemovePromptOptionsRequestModel,
    ResetPromptsRequestModel,
    UpdatePromptTextRequestModel,
)
from story_game.application.prompt_management import (
    ArchivePromptOptionRequest,
    CreatePromptOptionRequest,
    ListArchivedPromptOptionsRequest,
    ListCustomPromptOptionsRequest,
    ListPromptEntriesRequest,
    ListPromptHistoryRequest,
    PromptEntryKind,
    PromptEntryRef,
    PromptManagementOperations,
    PromptVersion,
    PromptVersionSource,
    PurgePromptOptionRequest,
    RemovePromptOptionsRequest,
    RestorePromptOptionRequest,
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


def _custom_keys(dependencies: ApiDependencies) -> frozenset[str]:
    """The keys of the options added in the UI (they have no shipped original)."""
    return frozenset(
        unwrap(
            _operations(dependencies).custom_options.apply(
                ListCustomPromptOptionsRequest(_PACKAGE_ID, _PACKAGE_VERSION)
            )
        )
    )


def _to_model(version: PromptVersion, custom: frozenset[str]) -> PromptVersionModel:
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
        is_custom=entry.kind is PromptEntryKind.OPTION and entry.key in custom,
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
    custom = _custom_keys(dependencies)
    return PromptListModel(
        package_id=_PACKAGE_ID,
        package_version=_PACKAGE_VERSION,
        entries=[_to_model(version, custom) for version in versions],
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
    custom = _custom_keys(dependencies)
    return PromptVersionListModel(versions=[_to_model(version, custom) for version in versions])


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
    return _to_model(version, _custom_keys(dependencies))


@router.post(
    "/options",
    response_model=PromptVersionModel,
    status_code=201,
    summary="Add a selectable option to genre, tone or prose style",
)
def create_option(
    payload: CreatePromptOptionRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> PromptVersionModel:
    version = unwrap(
        _operations(dependencies).create_option.apply(
            CreatePromptOptionRequest(
                _PACKAGE_ID,
                _PACKAGE_VERSION,
                payload.category,
                payload.option_id,
                payload.text,
                _editor(admin),
            )
        )
    )
    return _to_model(version, frozenset({version.entry.key}))


@router.delete(
    "/options",
    status_code=204,
    summary="Move an option added in the UI to the trash (refused while a game uses it)",
)
def archive_option(
    category: Annotated[str, Query(min_length=1)],
    option_id: Annotated[str, Query(min_length=1)],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> Response:
    unwrap(
        _operations(dependencies).archive_option.apply(
            ArchivePromptOptionRequest(_PACKAGE_ID, _PACKAGE_VERSION, category, option_id)
        )
    )
    return Response(status_code=204)


@router.get(
    "/options/archived",
    response_model=PromptVersionListModel,
    summary="List the options in the trash",
)
def list_archived_options(
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> PromptVersionListModel:
    versions = unwrap(
        _operations(dependencies).archived_options.apply(
            ListArchivedPromptOptionsRequest(_PACKAGE_ID, _PACKAGE_VERSION)
        )
    )
    keys = frozenset(version.entry.key for version in versions)
    return PromptVersionListModel(versions=[_to_model(version, keys) for version in versions])


@router.post(
    "/options/restore",
    status_code=204,
    summary="Take an option out of the trash",
)
def restore_option(
    payload: PromptOptionRefModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> Response:
    unwrap(
        _operations(dependencies).restore_option.apply(
            RestorePromptOptionRequest(
                _PACKAGE_ID, _PACKAGE_VERSION, payload.category, payload.option_id
            )
        )
    )
    return Response(status_code=204)


@router.delete(
    "/options/archived",
    status_code=204,
    summary="Delete an option in the trash for good, including its history",
)
def purge_option(
    category: Annotated[str, Query(min_length=1)],
    option_id: Annotated[str, Query(min_length=1)],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> Response:
    unwrap(
        _operations(dependencies).purge_option.apply(
            PurgePromptOptionRequest(_PACKAGE_ID, _PACKAGE_VERSION, category, option_id)
        )
    )
    return Response(status_code=204)


@router.post(
    "/options/removal",
    response_model=RemovalResultModel,
    summary="Archive or purge several options; every option gets its own outcome",
)
def remove_options(
    payload: RemovePromptOptionsRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _admin: Annotated[VerifiedCaller, Depends(require_admin)],
) -> RemovalResultModel:
    named = (
        None
        if payload.options is None
        else tuple(
            PromptEntryRef(PromptEntryKind.OPTION, f"{ref.category}/{ref.option_id}")
            for ref in payload.options
        )
    )
    outcomes = unwrap(
        _operations(dependencies).remove_options.apply(
            RemovePromptOptionsRequest(_PACKAGE_ID, _PACKAGE_VERSION, payload.mode, named)
        )
    )
    return RemovalResultModel(
        outcomes=[
            RemovalOutcomeModel(key=o.ref.key, status=o.status, message=o.message)
            for o in outcomes
        ]
    )


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
            ResetPromptTextRequest(
                _PACKAGE_ID, _PACKAGE_VERSION, target, _editor(admin), payload.kind
            )
        )
    )
    custom = _custom_keys(dependencies)
    return PromptVersionListModel(versions=[_to_model(version, custom) for version in versions])

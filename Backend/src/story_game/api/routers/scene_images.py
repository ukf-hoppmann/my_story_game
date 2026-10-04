"""HTTP endpoints for scene images of a run."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Response, status

from story_game.api.dependencies import (
    ApiDependencies,
    get_api_dependencies,
    get_current_initiator,
)
from story_game.api.results import OperationFailed, unwrap
from story_game.api.schemas.scene_images import (
    CreateSceneImageRequestModel,
    ImageModelModel,
    SceneImageCapabilitiesModel,
    SceneImageListModel,
    SceneImageModel,
)
from story_game.application import RunInitiator
from story_game.application.scene_image import (
    ListSceneImagesRequest,
    LoadSceneImageContentRequest,
    LoadSceneImageRequest,
    ReadSceneImageCapabilitiesRequest,
    RequestSceneImageRequest,
    SceneImageError,
    SceneImageErrorKind,
    SceneImageOperations,
    SceneImageOptions,
    SceneImageRecord,
)
from story_game.domain import StableId

router = APIRouter(tags=["scene-images"])


def _operations(dependencies: ApiDependencies) -> SceneImageOperations:
    if dependencies.scene_images is None:
        raise OperationFailed(
            SceneImageError(
                SceneImageErrorKind.DISABLED,
                "Szenenbilder sind in dieser Installation nicht aktiviert.",
            )
        )
    return dependencies.scene_images


def _to_model(record: SceneImageRecord) -> SceneImageModel:
    return SceneImageModel(
        image_id=record.image_id.value,
        run_id=record.run_id.value,
        turn_sequence=record.turn_sequence,
        status=record.status,
        model=record.model,
        refine=record.refine,
        refine_model=record.refine_model,
        refine_strength=record.refine_strength,
        width=record.width,
        height=record.height,
        seed=record.seed,
        prompt=record.prompt,
        compact_prompt=record.compact_prompt,
        error_message=record.error_message,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )


@router.get(
    "/api/v1/scene-images/capabilities",
    response_model=SceneImageCapabilitiesModel,
    summary="Report whether scene images are enabled and which models exist",
)
def scene_image_capabilities(
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> SceneImageCapabilitiesModel:
    if dependencies.scene_images is None:
        return SceneImageCapabilitiesModel(enabled=False)
    capabilities = unwrap(
        dependencies.scene_images.capabilities.apply(ReadSceneImageCapabilitiesRequest())
    )
    defaults = capabilities.defaults
    return SceneImageCapabilitiesModel(
        enabled=capabilities.enabled,
        models=[ImageModelModel(name=model.name) for model in capabilities.models],
        refine_models=[ImageModelModel(name=model.name) for model in capabilities.refine_models],
        model_listing_failed=capabilities.model_listing_failed,
        default_model=None if defaults is None else defaults.model,
        default_refine=False if defaults is None else defaults.refine,
        default_refine_model=None if defaults is None else defaults.refine_model,
        default_refine_strength=None if defaults is None else defaults.refine_strength,
        min_refine_strength=None if defaults is None else defaults.min_refine_strength,
        max_refine_strength=None if defaults is None else defaults.max_refine_strength,
        turn_window=None if defaults is None else defaults.turn_window,
    )


@router.post(
    "/api/v1/runs/{run_id}/scene-images",
    response_model=SceneImageModel,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start generating a scene image for the run's latest turn",
)
def create_scene_image(
    run_id: Annotated[UUID, Path()],
    background_tasks: BackgroundTasks,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
    payload: CreateSceneImageRequestModel | None = None,
) -> SceneImageModel:
    operations = _operations(dependencies)
    chosen = payload or CreateSceneImageRequestModel()
    requested = unwrap(
        operations.request.apply(
            RequestSceneImageRequest(
                StableId(run_id),
                initiator,
                SceneImageOptions(chosen.model, chosen.refine, chosen.refine_strength),
            )
        )
    )
    if requested.job is not None:
        background_tasks.add_task(operations.generate.apply, requested.job)
    return _to_model(requested.record)


@router.get(
    "/api/v1/runs/{run_id}/scene-images",
    response_model=SceneImageListModel,
    summary="List a run's scene images, newest first",
)
def list_scene_images(
    run_id: Annotated[UUID, Path()],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> SceneImageListModel:
    records = unwrap(
        _operations(dependencies).list.apply(ListSceneImagesRequest(StableId(run_id), initiator))
    )
    return SceneImageListModel(images=[_to_model(record) for record in records])


@router.get(
    "/api/v1/runs/{run_id}/scene-images/{image_id}",
    response_model=SceneImageModel,
    summary="Load one scene image's status and prompts",
)
def load_scene_image(
    run_id: Annotated[UUID, Path()],
    image_id: Annotated[UUID, Path()],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> SceneImageModel:
    record = unwrap(
        _operations(dependencies).load.apply(
            LoadSceneImageRequest(StableId(run_id), StableId(image_id), initiator)
        )
    )
    return _to_model(record)


@router.get(
    "/api/v1/runs/{run_id}/scene-images/{image_id}/content",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}}},
    summary="Download a finished scene image",
)
def load_scene_image_content(
    run_id: Annotated[UUID, Path()],
    image_id: Annotated[UUID, Path()],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> Response:
    content = unwrap(
        _operations(dependencies).content.apply(
            LoadSceneImageContentRequest(StableId(run_id), StableId(image_id), initiator)
        )
    )
    return Response(content=content.data, media_type=content.content_type)

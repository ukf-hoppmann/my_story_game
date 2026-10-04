"""Read-side operations; every read is scoped to a member of the run."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.run_initiator import RunInitiator
from story_game.domain import StableId

from .errors import SceneImageError, SceneImageErrorKind
from .models import (
    SceneImageCapabilities,
    SceneImageContent,
    SceneImageDefaults,
    SceneImageRecord,
)
from .ports import SceneImageReader, SceneImageRenderer, SceneImageStoreError

_LIST_LIMIT = 50


def _not_found() -> Failure[SceneImageError]:
    # Identical for a missing image and for a caller outside the run, so an
    # image's existence is not observable by anyone but the run's members.
    return Failure(
        SceneImageError(SceneImageErrorKind.NOT_FOUND, "Das Szenenbild wurde nicht gefunden.")
    )


def _unavailable() -> Failure[SceneImageError]:
    return Failure(
        SceneImageError(
            SceneImageErrorKind.STORE_UNAVAILABLE,
            "Die Szenenbilder konnten nicht gelesen werden.",
        )
    )


@dataclass(frozen=True, slots=True)
class ListSceneImagesRequest:
    run_id: StableId
    initiator: RunInitiator


@dataclass(frozen=True, slots=True)
class LoadSceneImageRequest:
    run_id: StableId
    image_id: StableId
    initiator: RunInitiator


@dataclass(frozen=True, slots=True)
class LoadSceneImageContentRequest:
    run_id: StableId
    image_id: StableId
    initiator: RunInitiator


@dataclass(frozen=True, slots=True)
class ReadSceneImageCapabilitiesRequest:
    pass


class ListSceneImages:
    def __init__(self, reader: SceneImageReader) -> None:
        self._reader = reader

    def apply(
        self, request: ListSceneImagesRequest
    ) -> OperationResult[tuple[SceneImageRecord, ...], SceneImageError]:
        try:
            return Success(
                self._reader.list_for_run(
                    request.run_id,
                    request.initiator.issuer,
                    request.initiator.subject,
                    _LIST_LIMIT,
                )
            )
        except SceneImageStoreError:
            return _unavailable()


class LoadSceneImage:
    def __init__(self, reader: SceneImageReader) -> None:
        self._reader = reader

    def apply(
        self, request: LoadSceneImageRequest
    ) -> OperationResult[SceneImageRecord, SceneImageError]:
        try:
            record = self._reader.get(
                request.run_id,
                request.image_id,
                request.initiator.issuer,
                request.initiator.subject,
            )
        except SceneImageStoreError:
            return _unavailable()
        return _not_found() if record is None else Success(record)


class LoadSceneImageContent:
    def __init__(self, reader: SceneImageReader) -> None:
        self._reader = reader

    def apply(
        self, request: LoadSceneImageContentRequest
    ) -> OperationResult[SceneImageContent, SceneImageError]:
        try:
            content = self._reader.load_content(
                request.run_id,
                request.image_id,
                request.initiator.issuer,
                request.initiator.subject,
            )
        except SceneImageStoreError:
            return _unavailable()
        return _not_found() if content is None else Success(content)


class ReadSceneImageCapabilities:
    """Report the enabled feature, its defaults, and the provider's models.

    An unreachable provider must not break the capability check: the feature
    stays enabled, the model list is empty, and the failure is flagged.
    """

    def __init__(self, defaults: SceneImageDefaults, renderer: SceneImageRenderer) -> None:
        self._defaults = defaults
        self._renderer = renderer

    def apply(
        self, request: ReadSceneImageCapabilitiesRequest
    ) -> OperationResult[SceneImageCapabilities, SceneImageError]:
        listed = self._renderer.list_models()
        if isinstance(listed, Failure):
            return Success(
                SceneImageCapabilities(
                    enabled=True, defaults=self._defaults, model_listing_failed=True
                )
            )
        models, refine_models = listed.data
        return Success(
            SceneImageCapabilities(
                enabled=True,
                defaults=self._defaults,
                models=models,
                refine_models=refine_models,
            )
        )


__all__ = [
    "ListSceneImages",
    "ListSceneImagesRequest",
    "LoadSceneImage",
    "LoadSceneImageContent",
    "LoadSceneImageContentRequest",
    "LoadSceneImageRequest",
    "ReadSceneImageCapabilities",
    "ReadSceneImageCapabilitiesRequest",
]

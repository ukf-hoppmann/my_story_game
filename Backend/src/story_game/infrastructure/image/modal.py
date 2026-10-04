"""Modal GPU service adapter for scene images (``SceneImageRenderer``).

Wire format (Modal web endpoints behind a proxy auth token):

* ``POST {url}/generate`` with ``{prompt, seed, width, height, model?,
  negative_prompt?}`` returns the image bytes.
* The optional refine stage is the same endpoint with ``image`` (base64 of
  the first stage), ``image_strength`` (closeness to the input — the inverse
  of how much the refine may change), ``refine_model`` and the short prompt.
* ``GET {control_url}/models`` lists ``{name, kind?, downloaded?}``; models
  of ``kind == "sdxl"`` are the refine models.

Settings and credentials are resolved per call so edited configuration takes
effect without a restart. Provider objects and status codes stay in here.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Any

import httpx

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.scene_image import (
    ImageGenError,
    ImageGenErrorKind,
    ImageModelInfo,
    ImageRenderRequest,
    RenderedImage,
    SceneImageRenderer,
)
from story_game.infrastructure.configuration import ModalCredentials, ModalSettings


class ModalSceneImageRenderer(SceneImageRenderer):
    def __init__(
        self,
        resolve_settings: Callable[[], ModalSettings],
        resolve_credentials: Callable[[], ModalCredentials | None],
        http_client: httpx.Client | None = None,
    ) -> None:
        self._resolve_settings = resolve_settings
        self._resolve_credentials = resolve_credentials
        self._http = http_client or httpx.Client()

    def close(self) -> None:
        self._http.close()

    def render(
        self, request: ImageRenderRequest
    ) -> OperationResult[RenderedImage, ImageGenError]:
        prepared = self._prepare()
        if isinstance(prepared, Failure):
            return prepared
        settings, headers = prepared.data
        body: dict[str, Any] = {
            "prompt": request.prompt,
            "seed": request.seed,
            "width": request.width,
            "height": request.height,
        }
        if request.model:
            body["model"] = request.model
        if settings.negative_prompt:
            body["negative_prompt"] = settings.negative_prompt
        first = self._generate(settings, headers, body)
        if isinstance(first, Failure) or request.refinement is None:
            return first

        refinement = request.refinement
        refine_body: dict[str, Any] = {
            "prompt": refinement.prompt,
            "seed": request.seed,
            "image": base64.b64encode(first.data.data).decode("ascii"),
            "image_strength": round(1 - refinement.strength, 3),
        }
        if refinement.model:
            refine_body["refine_model"] = refinement.model
        if settings.refine_negative_prompt:
            refine_body["negative_prompt"] = settings.refine_negative_prompt
        return self._generate(settings, headers, refine_body)

    def list_models(
        self,
    ) -> OperationResult[
        tuple[tuple[ImageModelInfo, ...], tuple[ImageModelInfo, ...]], ImageGenError
    ]:
        prepared = self._prepare()
        if isinstance(prepared, Failure):
            return prepared
        settings, headers = prepared.data
        response = self._send(
            lambda: self._http.get(
                f"{settings.control_url}/models",
                headers=headers,
                timeout=min(settings.timeout_seconds, 30.0),
            )
        )
        if isinstance(response, Failure):
            return response
        try:
            listing = response.data.json()
        except ValueError:
            return _failure(ImageGenErrorKind.INVALID_RESPONSE, "Die Modellliste ist kein JSON.")
        if not isinstance(listing, list):
            return _failure(
                ImageGenErrorKind.INVALID_RESPONSE, "Die Modellliste hat ein unerwartetes Format."
            )
        main: list[ImageModelInfo] = []
        refine: list[ImageModelInfo] = []
        for entry in listing:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                return _failure(
                    ImageGenErrorKind.INVALID_RESPONSE,
                    "Ein Eintrag der Modellliste hat ein unerwartetes Format.",
                )
            if entry.get("downloaded") is False:
                continue
            info = ImageModelInfo(entry["name"])
            (refine if entry.get("kind") == "sdxl" else main).append(info)
        return Success((tuple(main), tuple(refine)))

    def _prepare(
        self,
    ) -> OperationResult[tuple[ModalSettings, dict[str, str]], ImageGenError]:
        credentials = self._resolve_credentials()
        if credentials is None:
            return _failure(
                ImageGenErrorKind.CONFIGURATION,
                "Die Modal-Zugangsdaten fehlen (scene_image.secrets.toml).",
            )
        return Success(
            (
                self._resolve_settings(),
                {"Authorization": f"Bearer {credentials.bearer}"},
            )
        )

    def _generate(
        self, settings: ModalSettings, headers: dict[str, str], body: dict[str, Any]
    ) -> OperationResult[RenderedImage, ImageGenError]:
        response = self._send(
            lambda: self._http.post(
                f"{settings.url}/generate",
                json=body,
                headers=headers,
                timeout=settings.timeout_seconds,
            )
        )
        if isinstance(response, Failure):
            return response
        content_type = response.data.headers.get("content-type", "").split(";")[0].strip()
        if not response.data.content or not content_type.startswith("image/"):
            return _failure(
                ImageGenErrorKind.INVALID_RESPONSE, "Modal hat kein Bild geliefert."
            )
        return Success(RenderedImage(response.data.content, content_type))

    def _send(
        self, call: Callable[[], httpx.Response]
    ) -> OperationResult[httpx.Response, ImageGenError]:
        try:
            response = call()
        except httpx.TimeoutException:
            return _failure(ImageGenErrorKind.TIMEOUT, "Modal hat nicht rechtzeitig geantwortet.")
        except httpx.HTTPError:
            return _failure(ImageGenErrorKind.UNAVAILABLE, "Modal ist nicht erreichbar.")
        status = response.status_code
        if status in (401, 403):
            return _failure(
                ImageGenErrorKind.AUTHENTICATION, "Modal hat das Zugangstoken abgelehnt."
            )
        if 400 <= status < 500:
            return _failure(
                ImageGenErrorKind.INVALID_REQUEST, f"Modal hat die Anfrage abgelehnt ({status})."
            )
        if status >= 500:
            return _failure(
                ImageGenErrorKind.UNAVAILABLE, f"Modal meldet einen Fehler ({status})."
            )
        return Success(response)


def _failure(kind: ImageGenErrorKind, message: str) -> Failure[ImageGenError]:
    return Failure(ImageGenError(kind, message))


__all__ = ["ModalSceneImageRenderer"]

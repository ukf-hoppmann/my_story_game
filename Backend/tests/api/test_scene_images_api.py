from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from story_game.application import Failure, Success
from story_game.application.llm import (
    CompactImagePromptResolver,
    SceneImagePromptResolver,
    SceneImagePromptText,
)
from story_game.application.game_state import LoadGame
from story_game.application.scene_image import (
    GenerateSceneImage,
    ImageGenError,
    ImageGenErrorKind,
    ImageModelInfo,
    ListSceneImages,
    LoadSceneImage,
    LoadSceneImageContent,
    ReadSceneImageCapabilities,
    RenderedImage,
    RequestSceneImage,
    SceneImageContent,
    SceneImageDefaults,
    SceneImageOperations,
    SceneImageRecord,
    SceneImageStatus,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.api.llm_doubles import FakeGenerationConfigurationResolver
from tests.api.test_api import (  # noqa: F401 - reused helpers and fixtures
    DEV_ISSUER,
    DEV_SUBJECT,
    MemoryGameStore,
    build_dependencies,
    dev_identity_app,
    start_draft_run,
    store,
)
from tests.ids import sid

PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"
NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)
DEFAULTS = SceneImageDefaults(
    model="z-image-turbo", refine_model="juggernaut-xl-ragnarok", refine=False
)


class MemoryImageStore:
    def __init__(self) -> None:
        self.records: dict = {}
        self.contents: dict = {}

    def create_pending(self, image):
        o = image.options
        record = SceneImageRecord(
            image.image_id, image.run_id, image.turn_sequence, SceneImageStatus.PENDING,
            o.model, o.refine, o.refine_model, o.refine_strength, o.width, o.height, o.seed,
            image.created_at,
        )
        self.records[image.image_id] = record
        return record

    def find_active(self, run_id, turn_sequence, *, created_after):
        return next(
            (
                r for r in self.records.values()
                if r.run_id == run_id and r.turn_sequence == turn_sequence
                and r.status is SceneImageStatus.PENDING and r.created_at > created_after
            ),
            None,
        )

    def save_prompts(self, image_id, prompt, compact_prompt):
        self.records[image_id] = replace(
            self.records[image_id], prompt=prompt, compact_prompt=compact_prompt
        )

    def complete(self, image_id, content, completed_at):
        self.contents[image_id] = content
        self.records[image_id] = replace(
            self.records[image_id], status=SceneImageStatus.READY, completed_at=completed_at
        )

    def fail(self, image_id, message, completed_at):
        self.records[image_id] = replace(
            self.records[image_id],
            status=SceneImageStatus.FAILED,
            error_message=message,
            completed_at=completed_at,
        )

    def get(self, run_id, image_id, issuer, subject):
        record = self.records.get(image_id)
        member = (issuer, subject) == (DEV_ISSUER, DEV_SUBJECT)
        return record if record and record.run_id == run_id and member else None

    def list_for_run(self, run_id, issuer, subject, limit):
        return tuple(r for r in self.records.values() if self.get(run_id, r.image_id, issuer, subject))

    def load_content(self, run_id, image_id, issuer, subject):
        return self.contents.get(image_id) if self.get(run_id, image_id, issuer, subject) else None


class PromptWriter:
    def write(self, call):
        return Success(SceneImagePromptText("A tavern at night."))


class Compactor:
    def compact(self, call):
        return Success(SceneImagePromptText("tavern, night"))


class Renderer:
    def __init__(self, fail=False) -> None:
        self.fail = fail

    def render(self, request):
        if self.fail:
            return Failure(ImageGenError(ImageGenErrorKind.UNAVAILABLE, "Modal ist nicht erreichbar."))
        return Success(RenderedImage(b"\x89PNG-bytes", "image/png"))

    def list_models(self):
        return Success(((ImageModelInfo("z-image-turbo"),), (ImageModelInfo("juggernaut-xl-ragnarok"),)))


def scene_operations(game_store, image_store, renderer) -> SceneImageOperations:
    catalog = FilePromptPackageCatalog(PROMPT_ROOT)
    counter = iter(range(1, 100))
    return SceneImageOperations(
        request=RequestSceneImage(
            LoadGame(game_store, game_store),
            image_store,
            DEFAULTS,
            new_id=lambda: sid(f"api-image-{next(counter)}"),
            new_seed=lambda: 7,
            now=lambda: NOW,
            active_window=timedelta(minutes=15),
        ),
        generate=GenerateSceneImage(
            SceneImagePromptResolver(catalog),
            CompactImagePromptResolver(catalog),
            FakeGenerationConfigurationResolver(),
            PromptWriter(),
            Compactor(),
            renderer,
            image_store,
            compact_prompt_max_words=60,
            now=lambda: NOW,
        ),
        list=ListSceneImages(image_store),
        load=LoadSceneImage(image_store),
        content=LoadSceneImageContent(image_store),
        capabilities=ReadSceneImageCapabilities(DEFAULTS, renderer),
    )


@pytest.fixture
def image_store() -> MemoryImageStore:
    return MemoryImageStore()


@pytest.fixture
def enabled_client(store, image_store):  # noqa: F811
    dependencies = replace(
        build_dependencies(store), scene_images=scene_operations(store, image_store, Renderer())
    )
    with TestClient(dev_identity_app(dependencies)) as client:
        yield client


@pytest.fixture
def disabled_client(store):  # noqa: F811
    with TestClient(dev_identity_app(build_dependencies(store))) as client:
        yield client


def active_run(client: TestClient) -> str:
    draft = start_draft_run(client)
    active = client.post(f"/api/v1/runs/{draft['game_run']['id']}/playthroughs").json()
    return active["game_run"]["id"]


def test_the_feature_reports_itself_disabled_and_rejects_every_call(
    disabled_client: TestClient,
) -> None:
    run_id = active_run(disabled_client)
    image_id = sid("any")

    assert disabled_client.get("/api/v1/scene-images/capabilities").json() == {
        "enabled": False,
        "models": [],
        "refine_models": [],
        "model_listing_failed": False,
        "default_model": None,
        "default_refine": False,
        "default_refine_model": None,
        "default_refine_strength": None,
        "min_refine_strength": None,
        "max_refine_strength": None,
        "turn_window": None,
    }
    for response in (
        disabled_client.post(f"/api/v1/runs/{run_id}/scene-images"),
        disabled_client.get(f"/api/v1/runs/{run_id}/scene-images"),
        disabled_client.get(f"/api/v1/runs/{run_id}/scene-images/{image_id}"),
        disabled_client.get(f"/api/v1/runs/{run_id}/scene-images/{image_id}/content"),
    ):
        assert response.status_code == 409
        assert response.json()["error"] == "scene_image_disabled"


def test_capabilities_expose_models_and_defaults(enabled_client: TestClient) -> None:
    body = enabled_client.get("/api/v1/scene-images/capabilities").json()

    assert body["enabled"] is True
    assert body["models"] == [{"name": "z-image-turbo"}]
    assert body["refine_models"] == [{"name": "juggernaut-xl-ragnarok"}]
    assert body["default_model"] == "z-image-turbo"
    assert (body["min_refine_strength"], body["max_refine_strength"]) == (0.1, 0.8)
    assert body["turn_window"] == 3


def test_an_image_is_generated_listed_and_downloaded(enabled_client: TestClient) -> None:
    run_id = active_run(enabled_client)
    enabled_client.post(f"/api/v1/runs/{run_id}/turns", json={"player_input": "Ich öffne die Tür."})

    created = enabled_client.post(f"/api/v1/runs/{run_id}/scene-images")

    assert created.status_code == 202
    image = created.json()
    assert image["status"] == "pending"
    assert image["turn_sequence"] == 1 and image["seed"] == 7
    base = f"/api/v1/runs/{run_id}/scene-images"
    loaded = enabled_client.get(f"{base}/{image['image_id']}").json()
    assert loaded["status"] == "ready"
    assert loaded["prompt"] == "A tavern at night."
    assert [item["image_id"] for item in enabled_client.get(base).json()["images"]] == [
        image["image_id"]
    ]
    content = enabled_client.get(f"{base}/{image['image_id']}/content")
    assert content.status_code == 200
    assert content.headers["content-type"] == "image/png"
    assert content.content == b"\x89PNG-bytes"


def test_the_choices_in_the_body_are_applied(enabled_client: TestClient) -> None:
    run_id = active_run(enabled_client)

    created = enabled_client.post(
        f"/api/v1/runs/{run_id}/scene-images",
        json={"model": "other-model", "refine": True, "refine_strength": 0.5},
    ).json()

    assert (created["model"], created["refine"], created["refine_strength"]) == (
        "other-model",
        True,
        0.5,
    )
    loaded = enabled_client.get(f"/api/v1/runs/{run_id}/scene-images/{created['image_id']}").json()
    assert loaded["compact_prompt"] == "tavern, night"


def test_an_out_of_range_refine_strength_is_rejected(enabled_client: TestClient) -> None:
    run_id = active_run(enabled_client)

    response = enabled_client.post(
        f"/api/v1/runs/{run_id}/scene-images", json={"refine": True, "refine_strength": 0.95}
    )

    assert response.status_code == 422
    assert response.json()["error"] == "scene_image_invalid_options"


def test_a_render_failure_is_readable_on_the_image(store, image_store) -> None:  # noqa: F811
    dependencies = replace(
        build_dependencies(store),
        scene_images=scene_operations(store, image_store, Renderer(fail=True)),
    )
    with TestClient(dev_identity_app(dependencies)) as client:
        run_id = active_run(client)
        created = client.post(f"/api/v1/runs/{run_id}/scene-images")
        base = f"/api/v1/runs/{run_id}/scene-images/{created.json()['image_id']}"

        loaded = client.get(base).json()
        content = client.get(f"{base}/content")

    assert created.status_code == 202
    assert loaded["status"] == "failed"
    assert "nicht erreichbar" in loaded["error_message"]
    assert content.status_code == 404


def test_an_unknown_run_and_an_unknown_image_are_not_found(enabled_client: TestClient) -> None:
    run_id = active_run(enabled_client)

    assert enabled_client.post(f"/api/v1/runs/{sid('missing')}/scene-images").status_code == 404
    unknown = enabled_client.get(f"/api/v1/runs/{run_id}/scene-images/{sid('missing')}")
    assert unknown.status_code == 404
    assert unknown.json()["error"] == "not_found"


def test_openapi_describes_the_scene_image_endpoints(enabled_client: TestClient) -> None:
    paths = enabled_client.get("/openapi.json").json()["paths"]

    assert paths["/api/v1/scene-images/capabilities"]["get"]
    assert paths["/api/v1/runs/{run_id}/scene-images"]["post"]["responses"]["202"]
    assert paths["/api/v1/runs/{run_id}/scene-images/{image_id}/content"]["get"]

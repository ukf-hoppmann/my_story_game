"""The whole scene-image flow through the real composition root.

Real FastAPI app, real PostgreSQL, real HTTP clients — only the outside
world is a local stand-in: one tiny HTTP server plays both the LLM provider
(OpenAI-compatible chat) and Modal (generate + models). Needs a database
(``STORY_GAME_POSTGRES_DSN``) and is skipped without one.
"""

from __future__ import annotations

import base64
import json
import threading
from dataclasses import replace
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytest.importorskip("psycopg")

from fastapi.testclient import TestClient  # noqa: E402

from story_game.api import create_app  # noqa: E402
from story_game.api.config import ApiSettings  # noqa: E402
from story_game.api.dependencies import get_current_initiator  # noqa: E402
from story_game.application import RunInitiator  # noqa: E402
from story_game.domain import StoryInitialization, StoryState  # noqa: E402
from story_game.infrastructure.logging_config import LoggingSettings  # noqa: E402
from story_game.infrastructure.persistence.postgres import PostgresGameStore  # noqa: E402
from tests.ids import sid  # noqa: E402
from tests.persistence.model_settings_isolation import parked_model_settings  # noqa: E402
from tests.persistence.test_postgres_persistence import (  # noqa: E402,F401
    POSTGRES_DSN,
    initial,
    postgres_store,
)

PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"
PNG = b"\x89PNG-from-modal"
ISSUER = "https://identity.example/realms/story"


class FakeOutside(BaseHTTPRequestHandler):
    requests: list[tuple[str, str, dict, dict]] = []

    def log_message(self, *args) -> None:
        pass

    def _body(self) -> dict:
        length = int(self.headers.get("content-length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def _send(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802
        body = self._body()
        FakeOutside.requests.append((self.command, self.path, dict(self.headers), body))
        if self.path.endswith("/chat/completions"):
            reply = {
                "choices": [
                    {"message": {"content": "A warm tavern, fire."}, "finish_reason": "stop"}
                ]
            }
            self._send(200, json.dumps(reply).encode(), "application/json")
        elif self.path == "/generate":
            self._send(200, PNG, "image/png")
        else:
            self._send(404, b"", "text/plain")

    def do_GET(self) -> None:  # noqa: N802
        FakeOutside.requests.append((self.command, self.path, dict(self.headers), {}))
        if self.path == "/models":
            listing = [
                {"name": "z-image-turbo", "downloaded": True},
                {"name": "juggernaut-xl-ragnarok", "kind": "sdxl", "downloaded": True},
            ]
            self._send(200, json.dumps(listing).encode(), "application/json")
        else:
            self._send(404, b"", "text/plain")


@pytest.fixture
def outside():
    FakeOutside.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOutside)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def write_configuration(tmp_path: Path, base: str, *, enabled: bool) -> ApiSettings:
    (tmp_path / "app.toml").write_text(
        f"""
[scene_image]
enabled = {str(enabled).lower()}
turn_window = 2

[scene_image.modal]
url = "{base}"
control_url = "{base}"
model = "z-image-turbo"
timeout_seconds = 10
""",
        encoding="utf-8",
    )
    (tmp_path / "scene_image.secrets.toml").write_text(
        '[modal]\nkey = "wk-test"\nsecret = "ws-test"\n', encoding="utf-8"
    )
    models = "".join(
        f'[[models]]\nid = "m.{task}"\ntask = "{task}"\nprovider_id = "lmstudio"\n'
        f'model_id = "local-{task}"\n\n'
        for task in ("story", "extraction", "summary", "scene_image")
    )
    refs = "".join(f'{task} = "m.{task}"\n' for task in ("story", "extraction", "summary", "scene_image"))
    options = "".join(
        f"[generation_options.{task}]\ntemperature = 0.5\n\n"
        for task in ("story", "extraction", "summary", "scene_image")
    )
    (tmp_path / "llm.toml").write_text(
        f'[providers.lmstudio]\nbase_url = "{base}/v1"\ntimeout_seconds = 10\n\n'
        f"[task_models]\n{refs}\n{options}{models}",
        encoding="utf-8",
    )
    return ApiSettings(
        postgres_dsn=POSTGRES_DSN,
        prompt_root=str(PROMPT_ROOT),
        config_path=str(tmp_path / "app.toml"),
        llm_config_path=str(tmp_path / "llm.toml"),
    )


@pytest.fixture(autouse=True)
def isolated_model_settings(postgres_store):  # noqa: F811
    """The app seeds ``llm_task_settings`` from this test's own ``llm.toml``."""
    with parked_model_settings(postgres_store[1]):
        yield


@pytest.fixture
def run_id(postgres_store):  # noqa: F811
    game_store: PostgresGameStore = postgres_store[0]
    run, state = initial(sid("integration-seed"))
    new_id = sid(f"integration-run-{datetime.now(UTC).timestamp()}")
    story = StoryState(
        initialization=StoryInitialization(
            "Eine Taverne im Regen.", "Maren sitzt am Feuer der Taverne.", datetime.now(UTC)
        )
    )
    game_store.create(replace(run, id=new_id), replace(state, run_id=new_id, story=story))
    return new_id


def client_for(settings: ApiSettings) -> TestClient:
    app = create_app(settings=settings, logging_settings=LoggingSettings(file_path=None))
    app.dependency_overrides[get_current_initiator] = lambda: RunInitiator(ISSUER, "user-1")
    return TestClient(app)


def test_an_image_flows_from_the_button_to_stored_bytes(tmp_path, outside, run_id) -> None:
    with client_for(write_configuration(tmp_path, outside, enabled=True)) as client:
        capabilities = client.get("/api/v1/scene-images/capabilities").json()
        created = client.post(
            f"/api/v1/runs/{run_id}/scene-images", json={"refine": True, "refine_strength": 0.5}
        )
        base = f"/api/v1/runs/{run_id}/scene-images/{created.json()['image_id']}"
        loaded = client.get(base).json()
        content = client.get(f"{base}/content")
        listed = client.get(f"/api/v1/runs/{run_id}/scene-images").json()["images"]

    assert capabilities["enabled"] is True
    assert capabilities["models"] == [{"name": "z-image-turbo"}]
    assert capabilities["refine_models"] == [{"name": "juggernaut-xl-ragnarok"}]
    assert created.status_code == 202
    assert loaded["status"] == "ready", loaded
    assert loaded["prompt"] == "A warm tavern, fire."
    assert loaded["compact_prompt"] == "A warm tavern, fire."
    assert content.status_code == 200 and content.content == PNG
    assert [image["image_id"] for image in listed] == [loaded["image_id"]]

    generate_calls = [r for r in FakeOutside.requests if r[1] == "/generate"]
    assert len(generate_calls) == 2  # first stage, then the refine stage
    assert {k.lower(): v for k, v in generate_calls[0][2].items()}["authorization"] == "Bearer wk-test.ws-test"
    assert generate_calls[0][3]["model"] == "z-image-turbo"
    assert base64.b64decode(generate_calls[1][3]["image"]) == PNG
    assert generate_calls[1][3]["image_strength"] == 0.5
    chat_calls = [r for r in FakeOutside.requests if r[1].endswith("/chat/completions")]
    assert len(chat_calls) == 2  # detailed prompt, then the compact prompt


def test_a_disabled_feature_never_contacts_the_outside_world(tmp_path, outside, run_id) -> None:
    with client_for(write_configuration(tmp_path, outside, enabled=False)) as client:
        capabilities = client.get("/api/v1/scene-images/capabilities").json()
        created = client.post(f"/api/v1/runs/{run_id}/scene-images")

    assert capabilities["enabled"] is False
    assert created.status_code == 409
    assert created.json()["error"] == "scene_image_disabled"
    assert FakeOutside.requests == []

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("psycopg")

from story_game.application.scene_image import (  # noqa: E402
    NewSceneImage,
    ResolvedSceneImageOptions,
    SceneImageContent,
    SceneImageStatus,
)
from tests.ids import sid  # noqa: E402
from tests.persistence.test_postgres_persistence import (  # noqa: E402,F401
    initial,
    postgres_store,
)

ISSUER = "https://identity.example/realms/story"
CREATED = datetime(2026, 10, 4, 12, tzinfo=UTC)


def options(**changes) -> ResolvedSceneImageOptions:
    values = dict(
        model="z-image-turbo",
        refine=True,
        refine_model="juggernaut-xl-ragnarok",
        refine_strength=0.35,
        width=1024,
        height=768,
        seed=42,
    )
    values.update(changes)
    return ResolvedSceneImageOptions(**values)


@pytest.fixture
def stores(postgres_store):
    from story_game.infrastructure.persistence.postgres import PostgresSceneImageStore

    game_store, connections = postgres_store
    run, state = initial(sid("scene-image-run"))
    # A fresh run per test: the table is shared across the module.
    from dataclasses import replace

    run_id = sid(f"scene-image-run-{datetime.now(UTC).timestamp()}")
    run = replace(run, id=run_id)
    state = replace(state, run_id=run_id)
    game_store.create(run, state)
    return PostgresSceneImageStore(connections), run_id


def new_image(run_id, name="a", sequence=2, created=CREATED):
    return NewSceneImage(sid(f"{name}-{run_id}"), run_id, sequence, options(), created)


def test_a_pending_image_roundtrips_without_pixels(stores) -> None:
    store, run_id = stores
    image = new_image(run_id)

    record = store.create_pending(image)

    assert record.status is SceneImageStatus.PENDING
    assert (record.model, record.refine, record.refine_model) == (
        "z-image-turbo",
        True,
        "juggernaut-xl-ragnarok",
    )
    assert (record.refine_strength, record.width, record.height, record.seed) == (
        0.35,
        1024,
        768,
        42,
    )
    assert record.created_at == CREATED and record.completed_at is None
    assert store.get(run_id, image.image_id, ISSUER, "user-1") == record
    assert store.load_content(run_id, image.image_id, ISSUER, "user-1") is None


def test_prompts_and_a_finished_image_are_stored(stores) -> None:
    store, run_id = stores
    image = new_image(run_id)
    store.create_pending(image)

    store.save_prompts(image.image_id, "long prompt", "short prompt")
    store.complete(
        image.image_id, SceneImageContent(b"\x89PNG-data", "image/png"), CREATED + timedelta(seconds=5)
    )

    record = store.get(run_id, image.image_id, ISSUER, "user-1")
    assert record.status is SceneImageStatus.READY
    assert (record.prompt, record.compact_prompt) == ("long prompt", "short prompt")
    assert record.completed_at == CREATED + timedelta(seconds=5)
    assert store.load_content(run_id, image.image_id, ISSUER, "user-1") == SceneImageContent(
        b"\x89PNG-data", "image/png"
    )


def test_a_failed_image_keeps_its_message_and_has_no_content(stores) -> None:
    store, run_id = stores
    image = new_image(run_id)
    store.create_pending(image)

    store.fail(image.image_id, "Modal ist nicht erreichbar.", CREATED + timedelta(seconds=1))

    record = store.get(run_id, image.image_id, ISSUER, "user-1")
    assert record.status is SceneImageStatus.FAILED
    assert record.error_message == "Modal ist nicht erreichbar."
    assert store.load_content(run_id, image.image_id, ISSUER, "user-1") is None


def test_only_a_recent_pending_image_of_the_same_turn_is_active(stores) -> None:
    store, run_id = stores
    stale = new_image(run_id, "stale", 3, CREATED - timedelta(hours=3))
    done = new_image(run_id, "done", 3, CREATED)
    other_turn = new_image(run_id, "other", 4, CREATED)
    for image in (stale, done, other_turn):
        store.create_pending(image)
    store.complete(done.image_id, SceneImageContent(b"x", "image/png"), CREATED)
    horizon = CREATED - timedelta(minutes=15)

    assert store.find_active(run_id, 3, created_after=horizon) is None
    assert store.find_active(run_id, 4, created_after=horizon).image_id == other_turn.image_id


def test_a_non_member_sees_nothing(stores) -> None:
    store, run_id = stores
    image = new_image(run_id)
    store.create_pending(image)
    store.complete(image.image_id, SceneImageContent(b"x", "image/png"), CREATED)

    assert store.get(run_id, image.image_id, ISSUER, "someone-else") is None
    assert store.list_for_run(run_id, ISSUER, "someone-else", 10) == ()
    assert store.load_content(run_id, image.image_id, ISSUER, "someone-else") is None


def test_images_are_listed_newest_first_and_limited(stores) -> None:
    store, run_id = stores
    for index in range(3):
        store.create_pending(
            new_image(run_id, f"n{index}", index + 1, CREATED + timedelta(minutes=index))
        )

    listed = store.list_for_run(run_id, ISSUER, "user-1", 2)

    assert [record.turn_sequence for record in listed] == [3, 2]

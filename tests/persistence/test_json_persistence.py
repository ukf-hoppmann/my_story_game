from __future__ import annotations

import json
from pathlib import Path

import pytest

from story_game.domain import (
    AddFact,
    AddLink,
    ApprovedChangeSet,
    CreateEntity,
    GrantKnowledge,
    RecordEvent,
    StableId,
    StateRevision,
)
from story_game.infrastructure.persistence.errors import (
    PersistenceConflictError,
    PersistenceConsistencyError,
)
from story_game.infrastructure.persistence.json.mapper import (
    state_from_document,
    state_to_document,
)
from story_game.infrastructure.persistence.json.store import JsonGameStateStore


FIXTURES = Path(__file__).parents[1] / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_initial_fixture_maps_to_domain_and_back_without_data_loss() -> None:
    document = load_fixture("game_state_initial.json")

    state = state_from_document(document)

    assert state_to_document(state) == document
    assert [entity.id.value for entity in state.world.inventory(StableId("mara"))] == [
        "backpack"
    ]
    assert state.world.entity(StableId("sword")).kind.value == "item"
    assert state.story.current_scene_id == StableId("harbor-scene")


def test_json_store_commits_approved_changes_and_roundtrips_revision_two(
    tmp_path: Path,
) -> None:
    initial = state_from_document(load_fixture("game_state_initial.json"))
    expected = state_from_document(load_fixture("game_state_revision_2.json"))
    store = JsonGameStateStore(tmp_path / "game-state.json")

    store.create_initial(initial)
    changes = ApprovedChangeSet(
        proposal_id=StableId("proposal-find-lantern"),
        base_revision=StateRevision(1),
        changes=(
            CreateEntity(expected.world.entity(StableId("lantern"))),
            AddLink(
                next(
                    link
                    for link in expected.world.links
                    if link.id == StableId("mara-lantern")
                )
            ),
            AddFact(
                expected.world.fact(StableId("lantern-found")),
            ),
            GrantKnowledge(
                next(
                    entry
                    for entry in expected.world.knowledge
                    if entry.fact_id == StableId("lantern-found")
                )
            ),
            RecordEvent(
                next(
                    event
                    for event in expected.story.events
                    if event.id == StableId("find-lantern")
                )
            ),
        ),
    )

    updated = store.commit(initial.id, changes)

    assert updated == expected
    assert store.load(initial.id, revision=StateRevision(2)) == expected
    assert json.loads((tmp_path / "game-state.json").read_text(encoding="utf-8")) == state_to_document(
        expected
    )


def test_json_store_rejects_wrong_run_or_revision(tmp_path: Path) -> None:
    state = state_from_document(load_fixture("game_state_initial.json"))
    store = JsonGameStateStore(tmp_path / "game-state.json")
    store.create_initial(state)

    with pytest.raises(PersistenceConflictError):
        store.load(StableId("another-run"))
    with pytest.raises(PersistenceConflictError):
        store.load(state.id, revision=StateRevision(2))


def test_mapper_rejects_unknown_schema_version() -> None:
    document = load_fixture("game_state_initial.json")
    document["schema_version"] = 99

    with pytest.raises(PersistenceConsistencyError):
        state_from_document(document)

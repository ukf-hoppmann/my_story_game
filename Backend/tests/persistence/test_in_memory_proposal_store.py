from __future__ import annotations

from datetime import UTC, datetime, timedelta

from story_game.application.game_models import CachedGameRunProposal
from story_game.domain import GameConfiguration, PromptProfile, StoryState, WorldState
from story_game.infrastructure.persistence.in_memory_proposal_store import (
    InMemoryProposalStore,
)
from tests.ids import sid


def configuration() -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone="balanced",
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
            control_mode="director",
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
        ),
        narrative_boundaries=(),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


def proposal() -> CachedGameRunProposal:
    return CachedGameRunProposal(
        issuer="https://identity.example/story",
        subject="user-1",
        configuration=configuration(),
        story_state=StoryState(),
        world_state=WorldState(),
    )


def test_saved_proposal_can_be_loaded_back() -> None:
    store = InMemoryProposalStore()

    store.save(sid("proposal"), proposal())

    assert store.load(sid("proposal")) == proposal()


def test_unknown_proposal_id_returns_none() -> None:
    store = InMemoryProposalStore()

    assert store.load(sid("missing")) is None


def test_deleted_proposal_is_no_longer_loadable() -> None:
    store = InMemoryProposalStore()
    store.save(sid("proposal"), proposal())

    store.delete(sid("proposal"))

    assert store.load(sid("proposal")) is None


def test_expired_proposal_is_treated_as_gone() -> None:
    clock = [datetime(2026, 8, 19, 9, 0, tzinfo=UTC)]
    store = InMemoryProposalStore(ttl=timedelta(minutes=30), now=lambda: clock[0])
    store.save(sid("proposal"), proposal())

    clock[0] = clock[0] + timedelta(minutes=31)

    assert store.load(sid("proposal")) is None


def test_proposal_just_under_the_ttl_is_still_loadable() -> None:
    clock = [datetime(2026, 8, 19, 9, 0, tzinfo=UTC)]
    store = InMemoryProposalStore(ttl=timedelta(minutes=30), now=lambda: clock[0])
    store.save(sid("proposal"), proposal())

    clock[0] = clock[0] + timedelta(minutes=29)

    assert store.load(sid("proposal")) == proposal()

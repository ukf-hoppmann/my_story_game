from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from story_game.application import Failure, Success
from story_game.application.initialization_errors import StoryInitializationErrorKind
from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.application.seed_world_state import (
    BuildSeedWorldState,
    BuildSeedWorldStateRequest,
)
from story_game.domain import ActorProfile, ActorRole, EntityKind, WorldEntity
from tests.application.test_initialize_story import configuration
from tests.ids import sid

NOW = datetime(2026, 10, 11, 20, 15, tzinfo=UTC)


def build(seeds, control_mode="player"):  # type: ignore[no-untyped-def]
    config = configuration()
    config = replace(
        config,
        prompt_profile=replace(
            config.prompt_profile,
            control_mode=control_mode,
            perspective="third_person_limited" if control_mode == "director" else "first_person",
        ),
    )
    ids = iter(f"seed-{number}" for number in range(1, 20))
    return BuildSeedWorldState(lambda: sid(next(ids)), now=lambda: NOW).apply(
        BuildSeedWorldStateRequest(config, seeds)
    )


def test_player_control_yields_a_world_with_only_the_seeded_character() -> None:
    result = build((ControllableCharacterSeed("Maren", "Eine Jägerin"),))

    assert isinstance(result, Success), result
    world = result.data.world_state
    assert world.entities == (
        WorldEntity(
            id=sid("seed-1"),
            kind=EntityKind.CHARACTER,
            label="Maren",
            description="Eine Jägerin",
            actor=ActorProfile(ActorRole.NEUTRAL),
        ),
    )
    assert world.links == ()
    assert world.facts == ()
    assert world.knowledge == ()
    assert world.rules == ()
    assert world.goals == ()
    assert world.scene_location_ids == ()
    assert result.data.suggested_title == "Neue Geschichte – 11.10.2026 20:15"


def test_director_control_without_seeds_yields_an_empty_world() -> None:
    result = build((), control_mode="director")

    assert isinstance(result, Success), result
    assert result.data.world_state.entities == ()


def test_invalid_choices_are_rejected_like_in_extraction() -> None:
    result = build(())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.MISSING_PLAYER_CHARACTER

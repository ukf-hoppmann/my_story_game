from __future__ import annotations

import pytest

import story_game.domain as domain


def sid(value: str) -> domain.StableId:
    return domain.StableId(value)


def configuration() -> object:
    assert hasattr(domain, "GameConfiguration"), "GameState requires configuration"
    return domain.GameConfiguration(
        language="de",
        narration_style_id="style.dark",
        perspective_id="perspective.third-person",
        control_mode_id="control.player",
        narrative_boundaries=("Keine sexualisierte Gewalt",),
        story_model_id="model.story",
        extraction_model_id="model.extraction",
        summary_model_id="model.summary",
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


def test_game_state_contains_configuration_world_and_story() -> None:
    state = domain.GameState(
        run_id=sid("run-1"),
        revision=domain.StateRevision(1),
        configuration=configuration(),
        world=domain.WorldState(),
        story=domain.StoryState(),
    )

    assert state.run_id == sid("run-1")
    assert not hasattr(state, "player_actor_id")


def test_game_state_validates_member_player_entity_against_world() -> None:
    assert hasattr(domain, "GameRunMember")
    state = domain.GameState(
        run_id=sid("run-1"),
        revision=domain.StateRevision(1),
        configuration=configuration(),
        world=domain.WorldState(),
        story=domain.StoryState(),
    )
    member = domain.GameRunMember(
        issuer="issuer",
        subject="subject",
        game_role=domain.GameRole.PLAYER,
        player_entity_id=sid("missing"),
    )

    with pytest.raises(domain.InvalidReferenceError):
        state.validate_members((member,))

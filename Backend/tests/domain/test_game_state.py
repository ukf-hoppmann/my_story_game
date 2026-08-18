from __future__ import annotations

import pytest

import story_game.domain as domain
from tests.ids import sid


def configuration() -> object:
    assert hasattr(domain, "GameConfiguration"), "GameState requires configuration"
    assert hasattr(domain, "PromptProfile"), "GameConfiguration requires a prompt profile"
    return domain.GameConfiguration(
        language="de",
        prompt_profile=domain.PromptProfile(
            genre="dark_fantasy",
            tone="balanced",
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
            control_mode="player",
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
        ),
        narrative_boundaries=("Keine sexualisierte Gewalt",),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


def test_prompt_profile_normalizes_its_explicit_option_ids() -> None:
    assert hasattr(domain, "PromptProfile")

    profile = domain.PromptProfile(
        genre=" dark_fantasy ",
        tone=" balanced ",
        prose_style=" balanced ",
        perspective=" third_person_limited ",
        pacing=" balanced ",
        control_mode=" player ",
        player_agency=" strict ",
        consequence=" balanced ",
        challenge=" balanced ",
        content_profile=" teen ",
    )

    assert profile.genre == "dark_fantasy"
    assert profile.content_profile == "teen"


def test_prompt_profile_rejects_an_empty_category_selection() -> None:
    assert hasattr(domain, "PromptProfile")

    with pytest.raises(domain.ValidationError):
        domain.PromptProfile(
            genre="dark_fantasy",
            tone="",
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
            control_mode="player",
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
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
        controlled_entity_ids=(sid("missing"),),
    )

    with pytest.raises(domain.InvalidReferenceError):
        state.validate_members((member,))


def test_game_state_rejects_membership_bound_to_non_player_actor() -> None:
    npc = domain.WorldEntity(
        id=sid("npc"),
        kind=domain.EntityKind.CHARACTER,
        label="Ein Wächter",
        actor=domain.ActorProfile(domain.ActorRole.NPC),
    )
    state = domain.GameState(
        run_id=sid("run-1"),
        revision=domain.StateRevision(1),
        configuration=configuration(),
        world=domain.WorldState(entities=(npc,)),
        story=domain.StoryState(),
    )
    member = domain.GameRunMember(
        issuer="issuer",
        subject="subject",
        game_role=domain.GameRole.OWNER,
        controlled_entity_ids=(npc.id,),
    )

    with pytest.raises(domain.InvalidReferenceError):
        state.validate_members((member,))


def test_game_state_validates_every_controlled_entity_of_a_membership() -> None:
    maren = domain.WorldEntity(
        id=sid("maren"),
        kind=domain.EntityKind.CHARACTER,
        label="Maren",
        actor=domain.ActorProfile(domain.ActorRole.PLAYER),
    )
    npc = domain.WorldEntity(
        id=sid("npc"),
        kind=domain.EntityKind.CHARACTER,
        label="Ein Wächter",
        actor=domain.ActorProfile(domain.ActorRole.NPC),
    )
    state = domain.GameState(
        run_id=sid("run-1"),
        revision=domain.StateRevision(1),
        configuration=configuration(),
        world=domain.WorldState(entities=(maren, npc)),
        story=domain.StoryState(),
    )
    member = domain.GameRunMember(
        issuer="issuer",
        subject="subject",
        game_role=domain.GameRole.OWNER,
        controlled_entity_ids=(maren.id, npc.id),
    )

    with pytest.raises(domain.InvalidReferenceError):
        state.validate_members((member,))


def test_game_state_accepts_membership_with_multiple_valid_controlled_entities() -> None:
    maren = domain.WorldEntity(
        id=sid("maren"),
        kind=domain.EntityKind.CHARACTER,
        label="Maren",
        actor=domain.ActorProfile(domain.ActorRole.PLAYER),
    )
    jonas = domain.WorldEntity(
        id=sid("jonas"),
        kind=domain.EntityKind.CHARACTER,
        label="Jonas",
        actor=domain.ActorProfile(domain.ActorRole.PLAYER),
    )
    state = domain.GameState(
        run_id=sid("run-1"),
        revision=domain.StateRevision(1),
        configuration=configuration(),
        world=domain.WorldState(entities=(maren, jonas)),
        story=domain.StoryState(),
    )
    member = domain.GameRunMember(
        issuer="issuer",
        subject="subject",
        game_role=domain.GameRole.OWNER,
        controlled_entity_ids=(maren.id, jonas.id),
    )

    state.validate_members((member,))

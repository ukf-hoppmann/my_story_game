from __future__ import annotations

from datetime import UTC, datetime

from story_game.application import Failure, Success
from story_game.application.confirm_game_run_proposal import (
    CharacterDecision,
    ConfirmGameRunProposal,
    ConfirmGameRunProposalRequest,
    ItemDecision,
)
from story_game.application.game_models import CachedGameRunProposal, LoadedGame
from story_game.application.game_state.errors import RunConflict, RunNotFound, StateRejected
from story_game.application.run_initiator import RunInitiator
from story_game.domain import (
    ActorProfile,
    ActorRole,
    EntityKind,
    EntityLink,
    Fact,
    GameConfiguration,
    GameRole,
    GameRunStatus,
    PromptProfile,
    RelationKind,
    StateRevision,
    StoryState,
    WorldEntity,
    WorldState,
)
from tests.ids import sid


FIXED_TIME = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)


def configuration(control_mode: str = "player") -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone="balanced",
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
            control_mode=control_mode,
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
        ),
        narrative_boundaries=(),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


class RecordingProposalStore:
    def __init__(self, cached: CachedGameRunProposal | None = None):
        self.cached = cached
        self.deleted: list = []

    def save(self, proposal_id, proposal) -> None:  # pragma: no cover - unused here
        self.cached = proposal

    def load(self, proposal_id):
        return self.cached

    def delete(self, proposal_id) -> None:
        self.deleted.append(proposal_id)
        self.cached = None


class RecordingGameRunCreator:
    def __init__(self):
        self.requests = []
        self.result = None

    def apply(self, request):
        self.requests.append(request)
        if self.result is None:
            self.result = Success(LoadedGame(request.run, request.state))
        return self.result


def initiator() -> RunInitiator:
    return RunInitiator("https://identity.example/story", "user-1")


def maren(role: ActorRole = ActorRole.NEUTRAL) -> WorldEntity:
    return WorldEntity(
        id=sid("maren"), kind=EntityKind.CHARACTER, label="Maren", actor=ActorProfile(role)
    )


def cached_proposal(
    *, control_mode: str = "player", world: WorldState | None = None
) -> CachedGameRunProposal:
    return CachedGameRunProposal(
        issuer="https://identity.example/story",
        subject="user-1",
        configuration=configuration(control_mode),
        story_state=StoryState(),
        world_state=world if world is not None else WorldState(entities=(maren(),)),
    )


def request(
    *,
    character_decisions: tuple[CharacterDecision, ...] = (),
    item_decisions: tuple[ItemDecision, ...] = (),
) -> ConfirmGameRunProposalRequest:
    return ConfirmGameRunProposalRequest(
        proposal_id=sid("proposal"),
        run_name="Marens Abenteuer",
        initiator=initiator(),
        character_decisions=character_decisions,
        item_decisions=item_decisions,
    )


def test_confirms_a_player_role_and_persists_the_run() -> None:
    store = RecordingProposalStore(cached_proposal())
    creator = RecordingGameRunCreator()
    operation = ConfirmGameRunProposal(
        store, creator, new_id=lambda: sid("run"), now=lambda: FIXED_TIME
    )

    result = operation.apply(
        request(
            character_decisions=(CharacterDecision(sid("maren"), "player"),),
        )
    )

    assert isinstance(result, Success)
    persisted = creator.requests[0]
    assert persisted.run.id == sid("run")
    assert persisted.run.name == "Marens Abenteuer"
    assert persisted.run.status is GameRunStatus.DRAFT
    assert persisted.run.current_revision == StateRevision(1)
    assert persisted.run.members[0].game_role is GameRole.OWNER
    assert persisted.run.members[0].controlled_entity_ids == (sid("maren"),)
    assert persisted.state.world.entities[0].actor.role is ActorRole.PLAYER
    assert store.deleted == [sid("proposal")]


def test_removed_character_and_its_links_and_facts_are_dropped() -> None:
    room = WorldEntity(id=sid("room"), kind=EntityKind.LOCATION, label="Kammer")
    world = WorldState(
        entities=(maren(), room),
        links=(
            EntityLink(
                id=sid("link"),
                source_id=sid("maren"),
                target_id=sid("room"),
                kind=RelationKind.LOCATED_IN,
            ),
        ),
        facts=(Fact(id=sid("fact"), statement="Maren ist müde.", subject_id=sid("maren")),),
    )
    store = RecordingProposalStore(cached_proposal(control_mode="director", world=world))
    creator = RecordingGameRunCreator()
    operation = ConfirmGameRunProposal(
        store, creator, new_id=lambda: sid("run"), now=lambda: FIXED_TIME
    )

    result = operation.apply(
        request(character_decisions=(CharacterDecision(sid("maren"), "npc", removed=True),))
    )

    assert isinstance(result, Success)
    world_state = creator.requests[0].state.world
    assert [entity.id for entity in world_state.entities] == [sid("room")]
    assert world_state.links == ()
    assert world_state.facts == ()


def test_removed_item_and_its_links_are_dropped() -> None:
    sword = WorldEntity(id=sid("sword"), kind=EntityKind.ITEM, label="Schwert")
    world = WorldState(
        entities=(maren(ActorRole.PLAYER), sword),
        links=(
            EntityLink(
                id=sid("link"),
                source_id=sid("maren"),
                target_id=sid("sword"),
                kind=RelationKind.POSSESSES,
            ),
        ),
    )
    store = RecordingProposalStore(cached_proposal(world=world))
    creator = RecordingGameRunCreator()
    operation = ConfirmGameRunProposal(
        store, creator, new_id=lambda: sid("run"), now=lambda: FIXED_TIME
    )

    result = operation.apply(
        request(
            character_decisions=(CharacterDecision(sid("maren"), "player"),),
            item_decisions=(ItemDecision(sid("sword"), removed=True),),
        )
    )

    assert isinstance(result, Success)
    world_state = creator.requests[0].state.world
    assert [entity.id for entity in world_state.entities] == [sid("maren")]
    assert world_state.links == ()


def test_director_mode_allows_zero_confirmed_player_characters() -> None:
    store = RecordingProposalStore(cached_proposal(control_mode="director"))
    creator = RecordingGameRunCreator()
    operation = ConfirmGameRunProposal(
        store, creator, new_id=lambda: sid("run"), now=lambda: FIXED_TIME
    )

    result = operation.apply(request())

    assert isinstance(result, Success)
    assert creator.requests[0].run.members[0].controlled_entity_ids == ()


def test_player_mode_without_exactly_one_confirmed_player_is_rejected() -> None:
    store = RecordingProposalStore(cached_proposal())
    creator = RecordingGameRunCreator()
    operation = ConfirmGameRunProposal(store, creator)

    result = operation.apply(request())

    assert result == Failure(
        StateRejected("Der Player Mode benötigt genau einen bestätigten Spielercharakter")
    )
    assert creator.requests == []


def test_unknown_or_expired_proposal_is_rejected() -> None:
    store = RecordingProposalStore(cached=None)
    creator = RecordingGameRunCreator()
    operation = ConfirmGameRunProposal(store, creator)

    result = operation.apply(request())

    assert isinstance(result, Failure)
    assert isinstance(result.error, RunNotFound)


def test_a_proposal_cannot_be_confirmed_by_a_different_initiator() -> None:
    store = RecordingProposalStore(cached_proposal())
    creator = RecordingGameRunCreator()
    operation = ConfirmGameRunProposal(store, creator)
    other = ConfirmGameRunProposalRequest(
        proposal_id=sid("proposal"),
        run_name="Fremdes Spiel",
        initiator=RunInitiator("https://identity.example/story", "someone-else"),
        character_decisions=(CharacterDecision(sid("maren"), "player"),),
    )

    result = operation.apply(other)

    assert isinstance(result, Failure)
    assert isinstance(result.error, RunNotFound)
    assert creator.requests == []


def test_propagates_persistence_conflicts_and_keeps_the_proposal_cached() -> None:
    store = RecordingProposalStore(cached_proposal(control_mode="director"))
    creator = RecordingGameRunCreator()
    creator.result = Failure(RunConflict("Die Run-ID existiert bereits."))
    operation = ConfirmGameRunProposal(store, creator)

    result = operation.apply(request())

    assert result == Failure(RunConflict("Die Run-ID existiert bereits."))
    assert len(creator.requests) == 1
    assert store.deleted == []

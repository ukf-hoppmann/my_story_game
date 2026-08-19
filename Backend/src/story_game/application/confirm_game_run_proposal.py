"""Turn a caller-confirmed proposal into one persisted DRAFT game run."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, TypeAlias

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import DiagnosticsLog, NullDiagnosticsLog
from story_game.application.game_models import CachedGameRunProposal, LoadedGame
from story_game.application.game_state import CreateGameRun, CreateGameRunRequest
from story_game.application.game_state.errors import GameStateOperationError, RunNotFound
from story_game.application.ports import InitialProposalStore
from story_game.application.run_initiator import RunInitiator
from story_game.domain import (
    ActorProfile,
    ActorRole,
    DomainError,
    EntityKind,
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    GameState,
    StableId,
    StateRevision,
    WorldEntity,
    WorldState,
)

from .game_state.errors import StateRejected


ConfirmGameRunProposalError: TypeAlias = GameStateOperationError


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class CharacterDecision:
    """The caller's Spieler/NPC/entfernen choice for one proposed character."""

    entity_id: StableId
    role: Literal["player", "npc"]
    removed: bool = False


@dataclass(frozen=True, slots=True)
class ItemDecision:
    """The caller's behalten/löschen choice for one proposed item."""

    entity_id: StableId
    removed: bool = False


@dataclass(frozen=True, slots=True)
class ConfirmGameRunProposalRequest:
    """Caller input needed to persist a previously generated proposal."""

    proposal_id: StableId
    run_name: str
    initiator: RunInitiator
    character_decisions: tuple[CharacterDecision, ...] = ()
    item_decisions: tuple[ItemDecision, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_name", _required(self.run_name, "Der Name"))


class ConfirmGameRunProposal:
    """Apply the caller's edits to a cached proposal and persist it as DRAFT."""

    def __init__(
        self,
        proposal_store: InitialProposalStore,
        game_run_creator: CreateGameRun,
        *,
        new_id: Callable[[], StableId] = StableId.new,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._proposal_store = proposal_store
        self._game_run_creator = game_run_creator
        self._new_id = new_id
        self._now = now
        self._diagnostics = diagnostics

    def apply(
        self, request: ConfirmGameRunProposalRequest
    ) -> OperationResult[LoadedGame, ConfirmGameRunProposalError]:
        self._diagnostics.trace(
            "confirm_game_run_proposal.start", proposal_id=str(request.proposal_id)
        )
        cached = self._proposal_store.load(request.proposal_id)
        if cached is None or not _owned_by(cached, request.initiator):
            # Same message whether the proposal never existed, already expired,
            # or belongs to someone else — existence of another caller's
            # proposal must not be observable from the response.
            return Failure(
                RunNotFound("Der Vorschlag wurde nicht gefunden oder ist abgelaufen.")
            )

        try:
            world = _apply_decisions(
                cached.world_state, request.character_decisions, request.item_decisions
            )
            control_mode = cached.configuration.prompt_profile.control_mode
            controlled_entity_ids = _controlled_entity_ids(world, control_mode)
            run_id = self._new_id()
            timestamp = self._now()
            run = GameRun(
                id=run_id,
                name=request.run_name,
                status=GameRunStatus.DRAFT,
                current_revision=StateRevision(1),
                members=(
                    GameRunMember(
                        issuer=request.initiator.issuer,
                        subject=request.initiator.subject,
                        game_role=GameRole.OWNER,
                        controlled_entity_ids=controlled_entity_ids,
                    ),
                ),
                created_at=timestamp,
                updated_at=timestamp,
            )
            state = GameState(
                run_id=run_id,
                revision=StateRevision(1),
                configuration=cached.configuration,
                world=world,
                story=cached.story_state,
            )
        except (DomainError, ValueError) as error:
            return Failure(StateRejected(str(error)))

        created = self._game_run_creator.apply(CreateGameRunRequest(run, state))
        if not isinstance(created, Failure):
            self._proposal_store.delete(request.proposal_id)
        self._diagnostics.trace(
            "confirm_game_run_proposal.done",
            run_id=str(run_id),
            success=not isinstance(created, Failure),
        )
        return created


def _owned_by(cached: CachedGameRunProposal, initiator: RunInitiator) -> bool:
    return cached.issuer == initiator.issuer and cached.subject == initiator.subject


def _apply_decisions(
    world: WorldState,
    character_decisions: tuple[CharacterDecision, ...],
    item_decisions: tuple[ItemDecision, ...],
) -> WorldState:
    """Remove rejected entities and set confirmed roles, cascading cleanly.

    Locations, facts without a removed subject, and links between two
    surviving entities are carried over unchanged — only characters and
    items carry a caller decision. Any link or fact that referenced a removed
    entity is dropped along with it: reconstructing ``WorldState`` re-checks
    every Domain invariant, so a dangling reference would otherwise surface
    as the same "unknown reference" failure this feature exists to avoid.
    """
    role_by_id = {decision.entity_id: decision.role for decision in character_decisions}
    removed_ids = {decision.entity_id for decision in character_decisions if decision.removed}
    removed_ids |= {decision.entity_id for decision in item_decisions if decision.removed}

    entities = tuple(
        _with_decided_role(entity, role_by_id.get(entity.id))
        for entity in world.entities
        if entity.id not in removed_ids
    )
    links = tuple(
        link
        for link in world.links
        if link.source_id not in removed_ids and link.target_id not in removed_ids
    )
    facts = tuple(
        fact
        for fact in world.facts
        if fact.subject_id is None or fact.subject_id not in removed_ids
    )
    return WorldState(
        entities=entities,
        links=links,
        facts=facts,
        scene_location_ids=world.scene_location_ids,
    )


_ACTOR_KINDS = {EntityKind.CHARACTER, EntityKind.CREATURE, EntityKind.FACTION}


def _with_decided_role(
    entity: WorldEntity, role: Literal["player", "npc"] | None
) -> WorldEntity:
    if role is None or entity.kind not in _ACTOR_KINDS:
        return entity
    new_role = ActorRole.PLAYER if role == "player" else ActorRole.NEUTRAL
    if entity.actor is not None and entity.actor.role is new_role:
        return entity
    return WorldEntity(
        id=entity.id,
        kind=entity.kind,
        label=entity.label,
        description=entity.description,
        actor=ActorProfile(new_role),
        conditions=entity.conditions,
        aliases=entity.aliases,
    )


def _controlled_entity_ids(world: WorldState, control_mode: str) -> tuple[StableId, ...]:
    player_ids = tuple(
        entity.id
        for entity in world.entities
        if entity.actor is not None and entity.actor.role is ActorRole.PLAYER
    )
    if control_mode == "player":
        if len(player_ids) != 1:
            raise ValueError(
                "Der Player Mode benötigt genau einen bestätigten Spielercharakter"
            )
        return player_ids
    if control_mode == "director":
        return player_ids
    raise ValueError(f"Unbekannter Control Mode: {control_mode}")

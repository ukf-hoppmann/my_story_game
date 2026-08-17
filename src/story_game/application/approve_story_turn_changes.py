"""Turn one untrusted turn proposal into an approved change set, or reject it."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.extract_story_turn_changes import ExtractedTurnChanges
from story_game.application.llm import (
    CandidateEntity,
    CandidateEntityUpdate,
    CandidateFact,
    CandidateLink,
)
from story_game.application.proposals import (
    ProposalEvidence,
    ProposedChange,
    ProposedChangeSet,
)
from story_game.application.story_turn_errors import StoryTurnError, StoryTurnErrorKind
from story_game.domain import (
    AddFact,
    AddLink,
    ApprovedChangeSet,
    Condition,
    CreateEntity,
    DomainError,
    EntityLink,
    Fact,
    GameState,
    RemoveFact,
    RemoveLink,
    SetSceneLocations,
    StableId,
    StateOperation,
    UpdateEntity,
    Visibility,
    WorldEntity,
)


@dataclass(frozen=True, slots=True)
class ApprovedTurnChanges:
    """What may be committed, plus the untrusted proposal it came from.

    The proposal travels along so the model's own justifications stay readable
    — otherwise asking for them would cost output tokens for data nobody can
    see. It is never persisted.
    """

    approved: ApprovedChangeSet
    proposed: ProposedChangeSet


@dataclass(frozen=True, slots=True)
class ApproveStoryTurnChangesRequest:
    game_state: GameState
    extracted: ExtractedTurnChanges


_JustifiedOperation = tuple[StateOperation, "str | None"]
"""One approved operation together with the quote the model offered for it."""


class _UnknownReference(Exception):
    """A handle or local reference the proposal cannot resolve."""


class ApproveStoryTurnChanges:
    """Resolve, propose and approve — or discard the proposal as a whole.

    This is the single funnel every extraction variant has to pass, so later
    specialised calls can reuse it unchanged. Nothing here writes state: the
    approved set is handed on and only committed elsewhere.
    """

    def __init__(self, new_id: Callable[[], StableId] = StableId.new) -> None:
        self._new_id = new_id

    def apply(
        self, request: ApproveStoryTurnChangesRequest
    ) -> OperationResult[ApprovedTurnChanges, StoryTurnError]:
        state = request.game_state
        candidate = request.extracted.candidate
        projection = request.extracted.projection

        try:
            entities = self._entity_references(candidate, projection)
            operations = self._operations(candidate, projection, entities, state)
        except _UnknownReference as error:
            return Failure(
                StoryTurnError(
                    StoryTurnErrorKind.INVALID_CANDIDATE_REFERENCE, str(error)
                )
            )

        # The transient proposal is the documented boundary between untrusted
        # model output and canonical state. It is where the model's own
        # justification lives; today nothing reviews it yet, so it is built and
        # approved in one go.
        proposed = ProposedChangeSet(
            id=self._new_id(),
            base_revision=state.revision,
            changes=tuple(
                ProposedChange(
                    id=self._new_id(),
                    operation=operation,
                    evidence=ProposalEvidence(
                        source="turn_extraction", excerpt=evidence
                    ),
                    visibility=Visibility.public(),
                )
                for operation, evidence in operations
            ),
        )
        approved = ApprovedChangeSet(
            proposal_id=proposed.id,
            base_revision=proposed.base_revision,
            changes=tuple(change.operation for change in proposed.changes),
        )

        try:
            state.apply(approved)
        except DomainError as error:
            return Failure(
                StoryTurnError(StoryTurnErrorKind.DOMAIN_REJECTION, str(error))
            )
        return Success(ApprovedTurnChanges(approved, proposed))

    def _entity_references(
        self, candidate, projection
    ) -> dict[str, StableId]:
        """Map every usable entity reference of this turn to a stable ID."""
        references = dict(projection.entity_handles)
        for item in candidate.new_entities:
            if item.local_ref in references:
                raise _UnknownReference(
                    f"Die lokale Referenz {item.local_ref!r} ist bereits vergeben."
                )
            references[item.local_ref] = self._new_id()
        return references

    def _operations(
        self,
        candidate,
        projection,
        entities: dict[str, StableId],
        state: GameState,
    ) -> tuple[_JustifiedOperation, ...]:
        operations: list[_JustifiedOperation] = [
            *self._created(candidate.new_entities, entities),
            *self._updated(candidate.entity_updates, entities, state),
            # Removals come first so a move does not briefly claim two places.
            *(
                (RemoveLink(_resolve(item.handle, projection.link_handles)), item.evidence)
                for item in candidate.removed_links
            ),
            *self._added_links(candidate.added_links, entities),
            *(
                (RemoveFact(_resolve(item.handle, projection.fact_handles)), item.evidence)
                for item in candidate.removed_facts
            ),
            *self._added_facts(candidate.added_facts, entities),
        ]
        if candidate.scene:
            operations.append(
                (
                    SetSceneLocations(
                        tuple(
                            _resolve(item.reference, entities)
                            for item in candidate.scene
                        )
                    ),
                    candidate.scene[0].evidence,
                )
            )
        return tuple(operations)

    def _created(
        self, items: tuple[CandidateEntity, ...], entities: dict[str, StableId]
    ) -> tuple[_JustifiedOperation, ...]:
        return tuple(
            (CreateEntity(
                WorldEntity(
                    id=entities[item.local_ref],
                    kind=item.kind,
                    label=item.label,
                    description=item.description,
                    conditions=tuple(
                        Condition(condition.name, condition.description)
                        for condition in item.conditions
                    ),
                    aliases=item.aliases,
                )
            ), item.evidence)
            for item in items
        )

    def _updated(
        self,
        items: tuple[CandidateEntityUpdate, ...],
        entities: dict[str, StableId],
        state: GameState,
    ) -> tuple[_JustifiedOperation, ...]:
        operations: list[_JustifiedOperation] = []
        for item in items:
            entity_id = _resolve(item.handle, entities)
            try:
                current = state.world.entity(entity_id)
            except DomainError as error:
                raise _UnknownReference(str(error)) from error
            changes: dict[str, object] = {}
            if item.description is not None:
                changes["description"] = item.description
            if item.conditions is not None:
                changes["conditions"] = tuple(
                    Condition(condition.name, condition.description)
                    for condition in item.conditions
                )
            if item.aliases is not None:
                changes["aliases"] = item.aliases
            operations.append(
                (UpdateEntity(replace(current, **changes)), item.evidence)
            )
        return tuple(operations)

    def _added_links(
        self, items: tuple[CandidateLink, ...], entities: dict[str, StableId]
    ) -> tuple[_JustifiedOperation, ...]:
        return tuple(
            (AddLink(
                EntityLink(
                    id=self._new_id(),
                    source_id=_resolve(item.source_ref, entities),
                    target_id=_resolve(item.target_ref, entities),
                    kind=item.kind,
                    quantity=item.quantity,
                    description=item.description,
                )
            ), item.evidence)
            for item in items
        )

    def _added_facts(
        self, items: tuple[CandidateFact, ...], entities: dict[str, StableId]
    ) -> tuple[_JustifiedOperation, ...]:
        return tuple(
            (AddFact(
                Fact(
                    id=self._new_id(),
                    statement=item.statement,
                    subject_id=(
                        None
                        if item.subject_ref is None
                        else _resolve(item.subject_ref, entities)
                    ),
                )
            ), item.evidence)
            for item in items
        )


def _resolve(reference: str, known: dict[str, StableId]) -> StableId:
    try:
        return known[reference]
    except KeyError as error:
        raise _UnknownReference(f"Unbekannte Referenz: {reference!r}") from error

"""Canonical revisioned state for one game run."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .changes import (
    AddFact,
    AddGoal,
    AddLink,
    ApprovedChangeSet,
    CreateEntity,
    GrantKnowledge,
    RemoveLink,
    StateOperation,
    UpdateEntity,
    UpdateGoal,
)
from .configuration import GameConfiguration
from .errors import ChangeRejectedError, InvalidReferenceError, RevisionConflictError
from .game_run import GameRunMember
from .story import StoryState, StorySummary, StoryTurn
from .value_objects import ActorRole, StableId, StateRevision
from .world import WorldState


@dataclass(frozen=True, slots=True)
class GameState:
    """Canonical state advanced only from an explicitly expected revision."""

    run_id: StableId
    revision: StateRevision
    configuration: GameConfiguration
    world: WorldState
    story: StoryState

    def validate_members(self, members: tuple[GameRunMember, ...]) -> None:
        """Validate optional player bindings against this revision's world."""
        for member in members:
            if member.player_entity_id is None:
                continue
            try:
                player = self.world.entity(member.player_entity_id)
            except InvalidReferenceError as error:
                raise InvalidReferenceError(
                    "Eine Mitgliedschaft verweist auf eine unbekannte Spielfigur"
                ) from error
            if player.actor is None or player.actor.role is not ActorRole.PLAYER:
                raise InvalidReferenceError(
                    "Eine Mitgliedschaft muss auf einen Spielercharakter zeigen"
                )

    def apply(self, changes: ApprovedChangeSet) -> GameState:
        """Apply approved world operations as one non-story revision."""
        updated = self._apply_approved(changes)
        return replace(updated, revision=self.revision.next())

    def reconfigure(
        self,
        configuration: GameConfiguration,
        *,
        base_revision: StateRevision,
    ) -> GameState:
        """Create a state-only revision without inventing a StoryTurn."""
        self._require_revision(base_revision)
        return replace(
            self,
            revision=self.revision.next(),
            configuration=configuration,
        )

    def complete_turn(
        self,
        changes: ApprovedChangeSet,
        turn: StoryTurn,
        summary: StorySummary | None,
    ) -> GameState:
        """Apply approved world changes and the completed prose turn together."""
        if turn.based_on_revision != self.revision:
            raise RevisionConflictError(
                "Der StoryTurn basiert nicht auf der aktuellen State-Revision"
            )
        if turn.resulting_revision != self.revision.next():
            raise ChangeRejectedError(
                "Der StoryTurn muss zur direkt folgenden State-Revision führen"
            )
        if changes.base_revision != self.revision:
            raise RevisionConflictError(
                "Der Änderungssatz basiert nicht auf der aktuellen State-Revision"
            )
        updated = self._apply_operations(changes.changes)
        story = updated.story.add_turn(turn, summary)
        return replace(updated, revision=self.revision.next(), story=story)

    def _apply_approved(self, changes: ApprovedChangeSet) -> GameState:
        if not isinstance(changes, ApprovedChangeSet):
            raise ChangeRejectedError(
                "Der GameState akzeptiert ausschließlich freigegebene Änderungssätze"
            )
        self._require_revision(changes.base_revision)
        return self._apply_operations(changes.changes)

    def _require_revision(self, base_revision: StateRevision) -> None:
        if base_revision != self.revision:
            raise RevisionConflictError(
                "Die Änderung basiert nicht auf der aktuellen State-Revision"
            )

    def _apply_operations(
        self, operations: tuple[StateOperation, ...]
    ) -> GameState:
        current = self
        for operation in operations:
            current = current._apply_operation(operation)
        return current

    def _apply_operation(self, operation: StateOperation) -> GameState:
        if isinstance(operation, CreateEntity):
            return replace(self, world=self.world.add_entity(operation.entity))
        if isinstance(operation, UpdateEntity):
            return replace(self, world=self.world.update_entity(operation.entity))
        if isinstance(operation, AddLink):
            return replace(self, world=self.world.add_link(operation.link))
        if isinstance(operation, RemoveLink):
            return replace(self, world=self.world.remove_link(operation.link_id))
        if isinstance(operation, AddFact):
            return replace(self, world=self.world.add_fact(operation.fact))
        if isinstance(operation, GrantKnowledge):
            return replace(self, world=self.world.add_knowledge(operation.entry))
        if isinstance(operation, AddGoal):
            return replace(self, world=self.world.add_goal(operation.goal))
        if isinstance(operation, UpdateGoal):
            return replace(self, world=self.world.update_goal(operation.goal))
        raise ChangeRejectedError(f"Nicht unterstützte Zustandsoperation: {operation!r}")

"""Application workflow for one complete story turn."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeAlias

from story_game.application.approve_story_turn_changes import (
    ApproveStoryTurnChanges,
    ApproveStoryTurnChangesRequest,
)
from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import DiagnosticsLog, NullDiagnosticsLog
from story_game.application.extract_story_turn_changes import (
    ExtractStoryTurnChanges,
    ExtractStoryTurnChangesRequest,
)
from story_game.application.llm import SummarizedTurn
from story_game.application.game_state import (
    CommitCompletedTurn,
    CommitCompletedTurnRequest,
    LoadGame,
    LoadGameRequest,
)
from story_game.application.game_state.errors import GameStateOperationError
from story_game.application.generate_story import GenerateStory, GenerateStoryRequest
from story_game.application.run_initiator import RunInitiator
from story_game.application.proposals import ProposedChangeSet
from story_game.application.story_turn_context import (
    SelectStoryTurnContext,
    SelectStoryTurnContextRequest,
)
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_errors import StoryTurnError, StoryTurnErrorKind
from story_game.application.summarize_story import SummarizeStory, SummarizeStoryRequest
from story_game.application.world_tracking import WorldTrackingPolicy
from story_game.domain import (
    ApprovedChangeSet,
    GameRun,
    GameRunStatus,
    GameState,
    StableId,
    StorySequence,
    StorySummarySegment,
)


StoryTurnWorkflowError: TypeAlias = (
    StoryTurnError | ContextSelectionError | GameStateOperationError
)


@dataclass(frozen=True, slots=True)
class PlayedStoryTurn:
    """The persisted turn, plus what went wrong without invalidating it."""

    state: GameState
    proposed_changes: ProposedChangeSet | None = None
    """The untrusted proposal behind this turn, with the model's own reasons.

    Transient and never persisted; kept so a caller can show what the model
    wanted and why.
    """

    summary_failure: StoryTurnError | None = None
    """Set when this turn reached a summary interval boundary but the new
    segment could not be produced.

    Prose and world changes are already paid for by then, so losing the whole
    turn over its summary segment would be the worse trade. The turn stands;
    the failure stays visible so a caller can show it instead of silently
    drifting without that segment. ``None`` on turns that are not themselves
    an interval boundary, since no segment is even attempted then.
    """

    continuation_options: tuple[str, ...] = ()
    """Suggested next-action choices for the player, from this turn's narration.

    Transient UI presentation data (see
    ``.harness/architecture/llm-integration.md`` §5): never part of
    ``GameState`` or a persisted ``StoryTurn``.
    """


@dataclass(frozen=True, slots=True)
class PlayStoryTurnRequest:
    """What the player just did, in which run, as whom."""

    run_id: StableId
    initiator: RunInitiator
    player_input: str

    def __post_init__(self) -> None:
        player_input = self.player_input.strip()
        if not player_input:
            raise ValueError("Die Spielereingabe darf nicht leer sein")
        object.__setattr__(self, "player_input", player_input)


class PlayStoryTurn:
    """Load, select, narrate, extract, approve and commit one turn.

    The order is deliberately visible here rather than hidden in wiring. Both
    model calls happen outside the database transaction, so any failure before
    the commit simply leaves the previous revision standing.
    """

    def __init__(
        self,
        load_game: LoadGame,
        select_context: SelectStoryTurnContext,
        generate_story: GenerateStory,
        extract_changes: ExtractStoryTurnChanges,
        approve_changes: ApproveStoryTurnChanges,
        summarize_story: SummarizeStory,
        commit_turn: CommitCompletedTurn,
        *,
        summary_interval: int = 4,
        world_tracking: WorldTrackingPolicy,
        new_id: Callable[[], StableId] = StableId.new,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        if summary_interval < 1:
            raise ValueError("summary_interval muss mindestens 1 sein")
        self._load_game = load_game
        self._select_context = select_context
        self._generate_story = generate_story
        self._extract_changes = extract_changes
        self._approve_changes = approve_changes
        self._summarize_story = summarize_story
        self._commit_turn = commit_turn
        self._summary_interval = summary_interval
        self._world_tracking = world_tracking
        self._new_id = new_id
        self._now = now
        self._diagnostics = diagnostics

    def apply(
        self, request: PlayStoryTurnRequest
    ) -> OperationResult[PlayedStoryTurn, StoryTurnWorkflowError]:
        self._diagnostics.trace(
            "play_story_turn.start",
            run_id=str(request.run_id),
            player_input=request.player_input,
        )
        loaded = self._load_game.apply(
            LoadGameRequest(
                request.run_id, request.initiator.issuer, request.initiator.subject
            )
        )
        if isinstance(loaded, Failure):
            return loaded
        run, state = loaded.data.run, loaded.data.state

        if run.status is not GameRunStatus.ACTIVE:
            return Failure(
                StoryTurnError(
                    StoryTurnErrorKind.RUN_NOT_ACTIVE,
                    "In diesem GameRun kann kein Zug gespielt werden, solange "
                    "er nicht aktiv ist.",
                )
            )

        controlled = _controlled_entity_ids(run, request.initiator)
        if isinstance(controlled, Failure):
            return controlled

        context = self._select_context.apply(
            SelectStoryTurnContextRequest(state, controlled.data, request.player_input)
        )
        if isinstance(context, Failure):
            return context

        narrated = self._generate_story.apply(
            GenerateStoryRequest(
                context.data, state.configuration, request.player_input
            )
        )
        if isinstance(narrated, Failure):
            return narrated

        if self._world_tracking.extraction_enabled():
            extracted = self._extract_changes.apply(
                ExtractStoryTurnChangesRequest(
                    context.data, state.configuration, narrated.data.text
                )
            )
            if isinstance(extracted, Failure):
                return extracted

            approved = self._approve_changes.apply(
                ApproveStoryTurnChangesRequest(state, extracted.data)
            )
            if isinstance(approved, Failure):
                return approved
            changes, proposed = approved.data.approved, approved.data.proposed
        else:
            # World tracking is off (llm-integration §6c): no Extraction, and
            # the turn commits an empty change set on the regular path.
            changes = ApprovedChangeSet(self._new_id(), state.revision)
            proposed = None

        next_sequence = state.story.current_turn_sequence + 1
        new_summary_segment: StorySummarySegment | None = None
        summary_failure: StoryTurnError | None = None
        if next_sequence % self._summary_interval == 0:
            window_start = next_sequence - self._summary_interval + 1
            already_committed = state.story.turns[
                max(0, len(state.story.turns) - self._summary_interval + 1) :
            ]
            window_turns = tuple(
                SummarizedTurn(turn.player_input, turn.narration)
                for turn in already_committed
            ) + (SummarizedTurn(request.player_input, narrated.data.text),)
            summarized = self._summarize_story.apply(
                SummarizeStoryRequest(window_turns, state.configuration)
            )
            if isinstance(summarized, Failure):
                summary_failure = summarized.error
            else:
                new_summary_segment = StorySummarySegment(
                    StorySequence(window_start),
                    StorySequence(next_sequence),
                    summarized.data.text,
                    state.revision.next(),
                )

        committed = self._commit_turn.apply(
            CommitCompletedTurnRequest(
                run_id=request.run_id,
                changes=changes,
                turn_id=self._new_id(),
                player_input=request.player_input,
                narration=narrated.data.text,
                new_summary_segment=new_summary_segment,
                completed_at=self._now(),
            )
        )
        if isinstance(committed, Failure):
            return committed
        self._diagnostics.trace(
            "play_story_turn.done",
            run_id=str(request.run_id),
            revision=committed.data.revision.value,
        )
        return Success(
            PlayedStoryTurn(
                committed.data,
                proposed,
                summary_failure,
                narrated.data.continuation_options,
            )
        )


def _controlled_entity_ids(
    run: GameRun, initiator: RunInitiator
) -> OperationResult[tuple[StableId, ...], StoryTurnError]:
    """Find which figures the caller steers, if any.

    Director control may bind zero, one, or several figures, so an empty
    tuple is a valid answer and not an error. The "caller is not a member"
    branch below is unreachable in practice — ``LoadGame`` (called just
    before this) already rejects that identity — but is kept as an explicit
    invariant rather than an assertion, since it is cheap and guards against
    the two checks ever drifting apart.
    """
    for member in run.members:
        if member.identity == (initiator.issuer, initiator.subject):
            return Success(member.controlled_entity_ids)
    return Failure(
        StoryTurnError(
            StoryTurnErrorKind.UNKNOWN_MEMBER,
            "Die aufrufende Identität gehört nicht zu diesem GameRun.",
        )
    )

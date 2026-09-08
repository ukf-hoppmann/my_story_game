from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from story_game.application import Failure, Success
from story_game.application.approve_story_turn_changes import ApproveStoryTurnChanges
from story_game.application.extract_story_turn_changes import ExtractStoryTurnChanges
from story_game.application.game_state import (
    CommitCompletedTurn,
    LoadGame,
    RunAccessDenied,
)
from story_game.application.generate_story import GenerateStory
from story_game.application.summarize_story import SummarizeStory
from story_game.application.run_initiator import RunInitiator
from story_game.application.llm import (
    CandidateEntity,
    CandidateLink,
    CandidateRemoval,
    CandidateSceneReference,
    ExtractionPromptSelectionResolver,
    GenerationConfiguration,
    GenerationOptions,
    LLMError,
    LLMErrorKind,
    ModelSelection,
    StoryGenerationData,
    StoryPromptSelectionResolver,
    StorySummaryText,
    SummaryPromptSelectionResolver,
    TurnChangeCandidate,
)
from story_game.application.play_story_turn import (
    PlayStoryTurn,
    PlayStoryTurnRequest,
)
from story_game.application.story_turn_context import (
    build_story_turn_context_selection,
)
from story_game.application.story_turn_errors import StoryTurnErrorKind
from story_game.domain import (
    EntityKind,
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    GameState,
    RelationKind,
    StateRevision,
    StorySequence,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.application import turn_context_world as w
from tests.ids import sid


PROMPT_ROOT = Path(__file__).parents[2] / "prompts"

RUN_ID = sid("run")
INITIATOR = RunInitiator("https://identity.example/realms/story", "user-1")
NARRATION = "Maren erhebt sich und tritt hinaus in den Regen."


class FakeStore:
    def __init__(self, state: GameState, run: GameRun) -> None:
        self.state = state
        self.run = run
        self.committed: object | None = None

    def load_run(self, run_id):
        return self.run

    def load_state(self, run_id, *, revision=None):
        return self.state

    def commit_turn(self, request):
        self.committed = request
        return self.state.complete_turn(
            request.changes, request.turn, request.summary
        )


class FixedConfigurationResolver:
    def resolve(self, task):
        return Success(
            GenerationConfiguration(
                ModelSelection("lmstudio", f"model-{task.value}"),
                GenerationOptions(temperature=0.5),
            )
        )


class FakeStoryPort:
    def __init__(self, result=None) -> None:
        self.result = result or Success(StoryGenerationData(NARRATION))
        self.call = None

    def generate(self, call):
        self.call = call
        return self.result


class FakeSummaryPort:
    def __init__(self, result=None) -> None:
        self.result = result or Success(StorySummaryText("Maren hat das Wirtshaus verlassen."))
        self.call = None

    def summarize(self, call):
        self.call = call
        return self.result


class FakeExtractionPort:
    def __init__(self, result=None) -> None:
        self.result = result or Success(TurnChangeCandidate())
        self.call = None

    def extract(self, call):
        self.call = call
        return self.result


def run_with(controlled_entity_ids=(w.MAREN,)) -> GameRun:
    timestamp = datetime(2026, 8, 17, tzinfo=UTC)
    return GameRun(
        RUN_ID,
        "Marens Reise",
        GameRunStatus.ACTIVE,
        StateRevision(1),
        (
            GameRunMember(
                INITIATOR.issuer,
                INITIATOR.subject,
                GameRole.OWNER,
                controlled_entity_ids,
            ),
        ),
        timestamp,
        timestamp,
    )


def workflow(
    story_port=None,
    extraction_port=None,
    summary_port=None,
    store=None,
    run=None,
) -> tuple[PlayStoryTurn, FakeStore]:
    state = w.game_state((w.TAVERN,), "Maren sitzt am Feuer.")
    resolved_store = store or FakeStore(state, run or run_with())
    catalog = FilePromptPackageCatalog(PROMPT_ROOT)
    ids = iter(f"generated-{number}" for number in range(1, 50))
    operation = PlayStoryTurn(
        LoadGame(resolved_store, resolved_store),
        build_story_turn_context_selection(),
        GenerateStory(
            StoryPromptSelectionResolver(catalog),
            FixedConfigurationResolver(),
            story_port or FakeStoryPort(),
        ),
        ExtractStoryTurnChanges(
            ExtractionPromptSelectionResolver(catalog),
            FixedConfigurationResolver(),
            extraction_port or FakeExtractionPort(),
        ),
        ApproveStoryTurnChanges(lambda: sid(next(ids))),
        SummarizeStory(
            SummaryPromptSelectionResolver(catalog),
            FixedConfigurationResolver(),
            summary_port or FakeSummaryPort(),
        ),
        CommitCompletedTurn(resolved_store, resolved_store),
        new_id=lambda: sid(next(ids)),
        now=lambda: datetime(2026, 8, 17, 12, tzinfo=UTC),
    )
    return operation, resolved_store


def request(player_input: str = "Ich gehe hinaus.") -> PlayStoryTurnRequest:
    return PlayStoryTurnRequest(RUN_ID, INITIATOR, player_input)


def test_a_complete_turn_persists_narration_and_the_next_revision() -> None:
    operation, store = workflow()

    result = operation.apply(request())

    assert isinstance(result, Success), result
    assert result.data.state.revision == StateRevision(2)
    assert store.committed is not None
    assert store.committed.turn.narration == NARRATION
    assert store.committed.turn.player_input == "Ich gehe hinaus."
    # The fixture already holds one narrated turn, so this is the second.
    assert store.committed.turn.sequence == StorySequence(2)


def test_the_extraction_sees_the_freshly_generated_prose() -> None:
    extraction_port = FakeExtractionPort()
    operation, _ = workflow(extraction_port=extraction_port)

    operation.apply(request())

    assert extraction_port.call.request.narration == NARRATION


def test_an_approved_delta_reaches_the_next_revision() -> None:
    extraction_port = FakeExtractionPort(
        Success(
            TurnChangeCandidate(
                new_entities=(
                    CandidateEntity("wald", EntityKind.LOCATION, "Schwarzwald"),
                ),
                added_links=(CandidateLink("e1", "wald", RelationKind.RELATED_TO),),
                scene=(CandidateSceneReference("wald"),),
            )
        )
    )
    operation, _ = workflow(extraction_port=extraction_port)

    result = operation.apply(request())

    assert isinstance(result, Success), result
    labels = {entity.label for entity in result.data.state.world.entities}
    assert "Schwarzwald" in labels
    assert len(result.data.state.world.scene_location_ids) == 1


def test_a_story_failure_leaves_the_state_untouched() -> None:
    operation, store = workflow(
        story_port=FakeStoryPort(
            Failure(LLMError(LLMErrorKind.UNAVAILABLE, "Nicht erreichbar."))
        )
    )
    before = store.state

    result = operation.apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.MODEL_FAILURE
    assert store.committed is None
    assert store.state == before


def test_an_extraction_failure_leaves_the_state_untouched() -> None:
    operation, store = workflow(
        extraction_port=FakeExtractionPort(
            Failure(LLMError(LLMErrorKind.INVALID_RESPONSE, "Kein JSON."))
        )
    )

    result = operation.apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.INVALID_MODEL_RESPONSE
    assert store.committed is None


def test_a_rejected_proposal_leaves_the_state_untouched() -> None:
    extraction_port = FakeExtractionPort(
        Success(TurnChangeCandidate(removed_facts=(CandidateRemoval("f99"),)))
    )
    operation, store = workflow(extraction_port=extraction_port)

    result = operation.apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.INVALID_CANDIDATE_REFERENCE
    assert store.committed is None


def test_an_identity_outside_the_run_cannot_play_a_turn() -> None:
    """Rejected by ``LoadGame``'s membership check before any turn logic runs.

    Access to a run (whose identities may play, view, or fork it) is enforced
    once, centrally, in ``LoadGame`` — not re-implemented per use case. See
    also the equivalent HTTP-level assertion in
    ``tests/api/test_api.py::test_api_rejects_a_turn_for_an_unknown_member``.
    """
    operation, store = workflow()

    result = operation.apply(
        PlayStoryTurnRequest(
            RUN_ID, RunInitiator("https://elsewhere.example", "stranger"), "Ich warte."
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, RunAccessDenied)
    assert store.committed is None


def test_director_control_without_a_bound_figure_can_still_play() -> None:
    operation, _ = workflow(run=run_with(controlled_entity_ids=()))

    result = operation.apply(request())

    assert isinstance(result, Success), result


def test_the_rolling_summary_is_written_with_the_turn() -> None:
    operation, store = workflow()

    result = operation.apply(request())

    assert isinstance(result, Success), result
    assert result.data.summary_failure is None
    assert store.committed.summary is not None
    assert store.committed.summary.text == "Maren hat das Wirtshaus verlassen."
    assert store.committed.summary.through_sequence == StorySequence(2)


def test_the_summary_call_sees_the_previous_summary_and_the_new_turn() -> None:
    summary_port = FakeSummaryPort()
    operation, _ = workflow(summary_port=summary_port)

    operation.apply(request())

    prepared = summary_port.call.request
    assert prepared.narration == NARRATION
    assert prepared.player_input == "Ich gehe hinaus."
    assert prepared.previous_summary == "Maren hat das Wirtshaus erreicht."
    assert prepared.language == "de"


def test_a_failed_summary_still_persists_the_turn_and_stays_visible() -> None:
    """Prose and world changes are already paid for; losing them would be worse."""
    operation, store = workflow(
        summary_port=FakeSummaryPort(
            Failure(LLMError(LLMErrorKind.TIMEOUT, "Zeitüberschreitung."))
        )
    )

    result = operation.apply(request())

    assert isinstance(result, Success), result
    assert result.data.state.revision == StateRevision(2)
    assert store.committed is not None
    assert store.committed.summary is None
    assert result.data.summary_failure is not None
    assert result.data.summary_failure.kind is StoryTurnErrorKind.MODEL_FAILURE

from __future__ import annotations

import pytest

from story_game.application import Failure, Success
from story_game.application.approve_story_turn_changes import (
    ApproveStoryTurnChanges,
    ApproveStoryTurnChangesRequest,
)
from story_game.application.extract_story_turn_changes import ExtractedTurnChanges
from story_game.application.llm import (
    CandidateEntity,
    CandidateEntityUpdate,
    CandidateFact,
    CandidateLink,
    CandidateRemoval,
    CandidateSceneReference,
    TurnChangeCandidate,
)
from story_game.application.story_prompt_sections import extraction_projection
from story_game.application.story_turn_context import (
    SelectStoryTurnContextRequest,
    build_story_turn_context_selection,
)
from story_game.application.story_turn_errors import StoryTurnErrorKind
from story_game.domain import (
    AddFact,
    AddLink,
    CreateEntity,
    EntityKind,
    RelationKind,
    RemoveFact,
    RemoveLink,
    SetSceneLocations,
    StateRevision,
    UpdateEntity,
)
from tests.application import turn_context_world as w


def state():
    return w.game_state((w.TAVERN,), "Maren sitzt am Feuer.")


def projection():
    result = build_story_turn_context_selection().apply(
        SelectStoryTurnContextRequest(state(), w.MAREN, "Ich gehe hinaus.")
    )
    assert isinstance(result, Success), result
    return extraction_projection(result.data)


def handle_of(entity_id) -> str:
    found = projection().entity_handles
    return next(handle for handle, value in found.items() if value == entity_id)


def link_handle_of(link_id) -> str:
    found = projection().link_handles
    return next(handle for handle, value in found.items() if value == link_id)


def fact_handle_of(fact_id) -> str:
    found = projection().fact_handles
    return next(handle for handle, value in found.items() if value == fact_id)


def approve(candidate: TurnChangeCandidate):
    ids = iter(f"new-{number}" for number in range(1, 20))
    from tests.ids import sid

    return ApproveStoryTurnChanges(lambda: sid(next(ids))).apply(
        ApproveStoryTurnChangesRequest(
            state(), ExtractedTurnChanges(candidate, projection())
        )
    )


def operations(candidate: TurnChangeCandidate):
    result = approve(candidate)
    assert isinstance(result, Success), result
    return result.data.approved.changes


def test_an_empty_proposal_yields_an_empty_but_valid_change_set() -> None:
    result = approve(TurnChangeCandidate())

    assert isinstance(result, Success)
    assert result.data.approved.changes == ()
    assert result.data.approved.base_revision == StateRevision(1)


def test_a_new_entity_becomes_a_create_operation_with_a_fresh_id() -> None:
    changes = operations(
        TurnChangeCandidate(
            new_entities=(CandidateEntity("wald", EntityKind.LOCATION, "Schwarzwald"),)
        )
    )

    assert len(changes) == 1
    assert isinstance(changes[0], CreateEntity)
    assert changes[0].entity.label == "Schwarzwald"


def test_a_handle_resolves_to_the_entity_it_stood_for() -> None:
    changes = operations(
        TurnChangeCandidate(
            added_facts=(CandidateFact("Maren friert.", handle_of(w.MAREN)),)
        )
    )

    assert isinstance(changes[0], AddFact)
    assert changes[0].fact.subject_id == w.MAREN


def test_a_move_removes_the_old_place_before_adding_the_new_one() -> None:
    """Otherwise the domain would reject two current locations at once."""
    changes = operations(
        TurnChangeCandidate(
            new_entities=(CandidateEntity("wald", EntityKind.LOCATION, "Schwarzwald"),),
            added_links=(
                CandidateLink(handle_of(w.MAREN), "wald", RelationKind.LOCATED_IN),
            ),
            removed_links=(
                CandidateRemoval(link_handle_of(w.sid("l-maren-tavern"))),
            ),
        )
    )

    kinds = [type(change) for change in changes]
    assert kinds.index(RemoveLink) < kinds.index(AddLink)


def test_a_retired_fact_becomes_a_remove_operation() -> None:
    changes = operations(
        TurnChangeCandidate(
            removed_facts=(CandidateRemoval(fact_handle_of(w.sid("f-tavern-warm"))),)
        )
    )

    assert changes == (RemoveFact(w.sid("f-tavern-warm")),)


def test_the_new_scene_is_resolved_including_freshly_created_places() -> None:
    changes = operations(
        TurnChangeCandidate(
            new_entities=(CandidateEntity("wald", EntityKind.LOCATION, "Schwarzwald"),),
            scene=(CandidateSceneReference("wald"),),
        )
    )

    scene = next(change for change in changes if isinstance(change, SetSceneLocations))
    assert len(scene.location_ids) == 1


def test_an_entity_update_changes_only_the_fields_it_names() -> None:
    changes = operations(
        TurnChangeCandidate(
            entity_updates=(
                CandidateEntityUpdate(handle_of(w.WIRT), description="Durchnässt."),
            )
        )
    )

    updated = next(change for change in changes if isinstance(change, UpdateEntity))
    assert updated.entity.description == "Durchnässt."
    assert updated.entity.label == "Bertram"
    assert updated.entity.aliases == ("der Wirt",)


@pytest.mark.parametrize(
    "candidate",
    [
        pytest.param(
            TurnChangeCandidate(
                added_facts=(CandidateFact("Unbekannt.", "e99"),)
            ),
            id="unknown_entity_handle",
        ),
        pytest.param(
            TurnChangeCandidate(removed_links=(CandidateRemoval("l99"),)),
            id="unknown_link_handle",
        ),
        pytest.param(
            TurnChangeCandidate(removed_facts=(CandidateRemoval("f99"),)),
            id="unknown_fact_handle",
        ),
        pytest.param(
            TurnChangeCandidate(scene=(CandidateSceneReference("nirgendwo"),)),
            id="unknown_scene_reference",
        ),
        pytest.param(
            TurnChangeCandidate(
                new_entities=(
                    CandidateEntity("wald", EntityKind.LOCATION, "Wald"),
                    CandidateEntity("wald", EntityKind.LOCATION, "Anderer Wald"),
                )
            ),
            id="duplicate_local_reference",
        ),
        pytest.param(
            TurnChangeCandidate(
                entity_updates=(CandidateEntityUpdate("e99", description="x"),)
            ),
            id="update_of_an_unknown_entity",
        ),
    ],
)
def test_bad_references_discard_the_whole_proposal(candidate) -> None:
    result = approve(candidate)

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.INVALID_CANDIDATE_REFERENCE


def test_a_local_reference_may_not_shadow_an_existing_handle() -> None:
    result = approve(
        TurnChangeCandidate(
            new_entities=(
                CandidateEntity(handle_of(w.MAREN), EntityKind.ITEM, "Fälschung"),
            )
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.INVALID_CANDIDATE_REFERENCE


def test_a_domain_violation_discards_the_whole_proposal() -> None:
    """A character is not a place, so it cannot be located in another character."""
    result = approve(
        TurnChangeCandidate(
            added_links=(
                CandidateLink(
                    handle_of(w.MAREN), handle_of(w.WIRT), RelationKind.LOCATED_IN
                ),
            )
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.DOMAIN_REJECTION


def test_the_approved_set_can_actually_be_applied_to_the_state() -> None:
    result = approve(
        TurnChangeCandidate(
            new_entities=(CandidateEntity("wald", EntityKind.LOCATION, "Schwarzwald"),),
            scene=(CandidateSceneReference("wald"),),
        )
    )

    assert isinstance(result, Success)
    advanced = state().apply(result.data.approved)
    assert advanced.revision == StateRevision(2)
    assert len(advanced.world.scene_location_ids) == 1


def test_the_model_reasons_stay_readable_on_the_transient_proposal() -> None:
    """Asking for justifications would be pointless if nobody could read them."""
    result = approve(
        TurnChangeCandidate(
            added_facts=(
                CandidateFact("Es regnet.", evidence="Regen schlug ihr entgegen."),
            )
        )
    )

    assert isinstance(result, Success), result
    change = result.data.proposed.changes[0]
    assert change.evidence.source == "turn_extraction"
    assert change.evidence.excerpt == "Regen schlug ihr entgegen."


def test_a_change_without_a_justification_is_still_approved() -> None:
    result = approve(
        TurnChangeCandidate(added_facts=(CandidateFact("Es regnet."),))
    )

    assert isinstance(result, Success), result
    assert result.data.proposed.changes[0].evidence.excerpt is None

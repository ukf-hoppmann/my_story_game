from __future__ import annotations

from story_game.domain import (
    AddFact,
    Evidence,
    Fact,
    ProposedChange,
    ProposedChangeSet,
    StableId,
    StateRevision,
    Visibility,
)


def sid(value: str) -> StableId:
    return StableId(value)


def test_proposal_keeps_domain_and_evidence_explicit() -> None:
    fact = Fact(sid("fact"), "Der Schlüssel liegt im Hafen.", Evidence("turn"))
    proposed = ProposedChange(
        sid("change"),
        AddFact(fact),
        Evidence("turn", sid("turn-1"), "Ich suche im Hafen."),
        Visibility.player_known(),
    )
    change_set = ProposedChangeSet(
        sid("proposal"),
        StateRevision(3),
        changes=(proposed,),
    )

    assert change_set.changes[0].target_domain.value == "worldstate"
    assert change_set.changes[0].evidence.reference == sid("turn-1")

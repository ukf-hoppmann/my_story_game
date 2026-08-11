from __future__ import annotations

import story_game.domain as domain

from story_game.application.proposals import ProposalEvidence


def test_evidence_is_available_only_as_transient_application_data() -> None:
    evidence = ProposalEvidence("story_prose", excerpt="Maren öffnet die Tür.")

    assert evidence.source == "story_prose"
    assert evidence.excerpt == "Maren öffnet die Tür."
    assert not hasattr(domain, "Evidence")


def test_proposal_evidence_uses_textual_source_references() -> None:
    evidence = ProposalEvidence("model_response", reference=" response-part-1 ")

    assert evidence.reference == "response-part-1"

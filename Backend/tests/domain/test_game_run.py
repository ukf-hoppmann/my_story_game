from __future__ import annotations

from datetime import UTC, datetime

import pytest

import story_game.domain as domain
from tests.ids import sid


def test_game_run_owns_status_members_and_current_revision() -> None:
    assert hasattr(domain, "GameRun"), "The target domain requires GameRun"
    assert hasattr(domain, "GameRunMember"), "The target domain requires memberships"
    assert hasattr(domain, "GameRole"), "Membership roles must be typed"
    assert hasattr(domain, "GameRunStatus"), "Run status must be typed"

    member = domain.GameRunMember(
        issuer="https://identity.example/realms/story",
        subject="user-1",
        game_role=domain.GameRole.OWNER,
        controlled_entity_ids=(sid("almas"),),
    )
    created_at = datetime(2026, 8, 6, tzinfo=UTC)
    run = domain.GameRun(
        id=sid("run-1"),
        name="Almas und das magische Schwert",
        status=domain.GameRunStatus.DRAFT,
        current_revision=domain.StateRevision(1),
        members=(member,),
        created_at=created_at,
        updated_at=created_at,
    )

    assert run.members == (member,)
    assert run.name == "Almas und das magische Schwert"
    assert run.current_revision == domain.StateRevision(1)


def test_game_run_member_defaults_to_no_controlled_entities() -> None:
    member = domain.GameRunMember(
        issuer="issuer",
        subject="subject",
        game_role=domain.GameRole.PLAYER,
    )

    assert member.controlled_entity_ids == ()


def test_game_run_member_may_bind_multiple_controlled_entities() -> None:
    member = domain.GameRunMember(
        issuer="issuer",
        subject="subject",
        game_role=domain.GameRole.OWNER,
        controlled_entity_ids=(sid("maren"), sid("jonas")),
    )

    assert member.controlled_entity_ids == (sid("maren"), sid("jonas"))


def test_game_run_member_rejects_duplicate_controlled_entities() -> None:
    with pytest.raises(domain.ValidationError):
        domain.GameRunMember(
            issuer="issuer",
            subject="subject",
            game_role=domain.GameRole.OWNER,
            controlled_entity_ids=(sid("maren"), sid("maren")),
        )


def test_game_run_rejects_duplicate_memberships() -> None:
    assert hasattr(domain, "GameRun")
    member = domain.GameRunMember(
        issuer="issuer",
        subject="subject",
        game_role=domain.GameRole.PLAYER,
    )
    created_at = datetime(2026, 8, 6, tzinfo=UTC)

    with pytest.raises(domain.ValidationError):
        domain.GameRun(
            id=sid("run-1"),
            name="Testlauf",
            status=domain.GameRunStatus.ACTIVE,
            current_revision=domain.StateRevision(1),
            members=(member, member),
            created_at=created_at,
            updated_at=created_at,
        )


def test_game_run_requires_a_human_readable_name() -> None:
    created_at = datetime(2026, 8, 6, tzinfo=UTC)

    with pytest.raises(domain.ValidationError):
        domain.GameRun(
            id=sid("run-1"),
            name="  ",
            status=domain.GameRunStatus.DRAFT,
            current_revision=domain.StateRevision(1),
            members=(),
            created_at=created_at,
            updated_at=created_at,
        )

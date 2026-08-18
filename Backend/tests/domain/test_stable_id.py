from __future__ import annotations

from uuid import UUID

import pytest

from story_game.domain import StableId, ValidationError


def test_stable_id_owns_a_uuid_value() -> None:
    value = UUID("12345678-1234-5678-9234-567812345678")

    stable_id = StableId(value)

    assert stable_id.value is value
    assert str(stable_id) == "12345678-1234-5678-9234-567812345678"


def test_stable_id_parses_and_normalizes_uuid_text() -> None:
    stable_id = StableId.parse("12345678-1234-5678-9234-567812345678")

    assert stable_id == StableId(UUID("12345678-1234-5678-9234-567812345678"))


def test_stable_id_rejects_non_uuid_values() -> None:
    with pytest.raises(ValidationError):
        StableId.parse("run-1")


def test_new_stable_ids_are_distinct_uuids() -> None:
    first = StableId.new()
    second = StableId.new()

    assert isinstance(first.value, UUID)
    assert first != second

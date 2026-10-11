from __future__ import annotations

from datetime import UTC, datetime

from story_game.application import Failure, Success
from story_game.application.diagnostics import WorldTrackingSettingUnavailable
from story_game.application.world_tracking import (
    GetWorldTracking,
    GetWorldTrackingRequest,
    SetWorldTracking,
    SetWorldTrackingRequest,
    StoredWorldTrackingPolicy,
    WorldTrackingErrorKind,
    WorldTrackingSetting,
    WorldTrackingStoreError,
)
from tests.application.diagnostics_double import FakeDiagnosticsLog
from tests.application.world_tracking_double import InMemoryWorldTrackingStore

NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)


def test_without_a_stored_setting_world_tracking_is_enabled() -> None:
    result = GetWorldTracking(InMemoryWorldTrackingStore()).apply(GetWorldTrackingRequest())

    assert result == Success(WorldTrackingSetting(enabled=True))


def test_setting_world_tracking_stores_value_editor_and_time() -> None:
    store = InMemoryWorldTrackingStore()

    result = SetWorldTracking(store, now=lambda: NOW).apply(
        SetWorldTrackingRequest(enabled=False, edited_by="testadmin")
    )

    expected = WorldTrackingSetting(enabled=False, updated_at=NOW, updated_by="testadmin")
    assert result == Success(expected)
    assert GetWorldTracking(store).apply(GetWorldTrackingRequest()) == Success(expected)


def test_a_store_failure_becomes_a_typed_failure() -> None:
    store = InMemoryWorldTrackingStore()
    store.fail_with = WorldTrackingStoreError("kaputt")

    read = GetWorldTracking(store).apply(GetWorldTrackingRequest())
    written = SetWorldTracking(store, now=lambda: NOW).apply(
        SetWorldTrackingRequest(enabled=False, edited_by="testadmin")
    )

    assert isinstance(read, Failure)
    assert read.error.kind is WorldTrackingErrorKind.STORE_UNAVAILABLE
    assert isinstance(written, Failure)
    assert written.error.kind is WorldTrackingErrorKind.STORE_UNAVAILABLE


def test_the_policy_follows_the_stored_setting_on_every_call() -> None:
    store = InMemoryWorldTrackingStore()
    policy = StoredWorldTrackingPolicy(store)

    assert policy.extraction_enabled() is True
    store.stored = WorldTrackingSetting(enabled=False, updated_at=NOW, updated_by="a")
    assert policy.extraction_enabled() is False


def test_the_policy_falls_back_to_tracking_when_the_store_fails() -> None:
    store = InMemoryWorldTrackingStore()
    store.fail_with = WorldTrackingStoreError("kaputt")
    diagnostics = FakeDiagnosticsLog()

    enabled = StoredWorldTrackingPolicy(store, diagnostics).extraction_enabled()

    assert enabled is True
    assert diagnostics.recorded == [WorldTrackingSettingUnavailable()]

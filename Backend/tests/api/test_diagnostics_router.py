"""``POST /api/v1/diagnostics/frontend-errors`` (TASK-030).

Uses the same ``dev_identity_app``/``build_dependencies`` fixtures as
``test_api.py`` so the endpoint is exercised behind the same Keycloak-Bearer
identity dependency every other authenticated route uses — no separate auth
mechanism for this endpoint.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from story_game.api.dependencies import get_current_initiator

from tests.api.test_api import MemoryGameStore, build_dependencies, dev_identity_app


def _client(store: MemoryGameStore | None = None) -> TestClient:
    return TestClient(dev_identity_app(build_dependencies(store or MemoryGameStore())))


def test_a_valid_report_is_accepted_with_no_content() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/diagnostics/frontend-errors",
            json={
                "source": "wizard.handleCreateProposal",
                "message": "Failed to fetch",
                "url": "https://story-game.example/wizard",
                "user_agent": "test-agent/1.0",
            },
        )

    assert response.status_code == 204
    assert response.content == b""


def test_optional_fields_may_be_omitted() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/diagnostics/frontend-errors",
            json={"source": "auth.onTokenExpired", "message": "expired"},
        )

    assert response.status_code == 204


def test_a_request_without_a_bearer_token_is_rejected() -> None:
    """Unlike ``prompt-profile``, this endpoint requires the same Keycloak
    Bearer token as every other run/turn endpoint — see the plan's decision
    that ``401``s are handled as a forced re-login, not reported here, so by
    the time a tooling error is worth reporting a valid token still exists.
    """
    app = dev_identity_app(build_dependencies(MemoryGameStore()))
    app.dependency_overrides.pop(get_current_initiator, None)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/diagnostics/frontend-errors",
            json={"source": "wizard.handleCreateProposal", "message": "Failed to fetch"},
        )

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_an_oversized_message_is_rejected_as_unprocessable() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/diagnostics/frontend-errors",
            json={"source": "wizard.handleCreateProposal", "message": "x" * 2001},
        )

    assert response.status_code == 422


def test_a_blank_source_is_rejected_by_schema_validation() -> None:
    """``APIModel`` strips whitespace before ``min_length`` runs, so a
    whitespace-only ``source`` never reaches ``ReportFrontendError.apply()``
    at all — its own blank-source rejection is defense-in-depth only."""
    with _client() as client:
        response = client.post(
            "/api/v1/diagnostics/frontend-errors",
            json={"source": "   ", "message": "Failed to fetch"},
        )

    assert response.status_code == 422

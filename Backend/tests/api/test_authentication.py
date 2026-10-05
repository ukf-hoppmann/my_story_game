"""End-to-end wiring: the Authorization header reaches the token verifier.

``tests/api/auth/test_token_verifier.py`` covers the verifier's own
signature/issuer/expiry rules in isolation; this covers the surrounding glue
in ``get_current_initiator`` (header parsing, 401 responses) with the app
wired the way ``create_app`` actually wires it — no dependency override.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from typing import Annotated

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends
from fastapi.testclient import TestClient

from story_game.api import create_app
from story_game.api.auth import KeycloakTokenVerifier, VerifiedCaller
from story_game.api.config import ApiSettings
from story_game.api.dependencies import require_admin
from tests.api.test_api import MemoryGameStore, build_dependencies

ISSUER = "http://keycloak.test/realms/story-game"
KID = "auth-test-key"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeSigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


class _FakeJwksClient:
    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(_PRIVATE_KEY.public_key())


def _token(*, subject: str = "user-1") -> str:
    now = datetime.now(UTC)
    claims = {"iss": ISSUER, "sub": subject, "iat": now, "exp": now + timedelta(minutes=5)}
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": KID})


@pytest.fixture
def client() -> TestClient:
    app = create_app(
        build_dependencies(MemoryGameStore()),
        settings=ApiSettings(keycloak_issuer=ISSUER, keycloak_audience=None),
    )
    with TestClient(app) as test_client:
        test_client.app.state.token_verifier = KeycloakTokenVerifier(ISSUER, None)
        test_client.app.state.token_verifier._jwks_client = _FakeJwksClient()  # type: ignore[attr-defined]
        yield test_client


def test_a_request_without_a_bearer_token_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/runs")

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_a_request_with_a_malformed_authorization_header_is_rejected(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/runs", headers={"Authorization": "Basic xyz"})

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_a_request_with_a_valid_bearer_token_is_accepted(client: TestClient) -> None:
    response = client.get(
        "/api/v1/runs", headers={"Authorization": f"Bearer {_token()}"}
    )

    assert response.status_code == 200


def _token_with_roles(roles: list[str], username: str | None = None) -> str:
    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "sub": "admin-1",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "realm_access": {"roles": roles},
    }
    if username is not None:
        claims["preferred_username"] = username
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": KID})


def _admin_probe(client: TestClient) -> None:
    @client.app.get("/__admin_probe")  # type: ignore[attr-defined]
    def probe(caller: Annotated[VerifiedCaller, Depends(require_admin)]) -> dict[str, str]:
        return {"subject": caller.initiator.subject, "username": caller.username or ""}


def test_an_admin_endpoint_rejects_a_missing_token_with_401(client: TestClient) -> None:
    _admin_probe(client)

    assert client.get("/__admin_probe").status_code == 401


def test_an_admin_endpoint_rejects_a_caller_without_the_admin_role_with_403(
    client: TestClient,
) -> None:
    _admin_probe(client)

    response = client.get(
        "/__admin_probe",
        headers={"Authorization": f"Bearer {_token_with_roles(['offline_access'])}"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


def test_an_admin_endpoint_accepts_a_caller_with_the_admin_role(client: TestClient) -> None:
    _admin_probe(client)

    response = client.get(
        "/__admin_probe",
        headers={"Authorization": f"Bearer {_token_with_roles(['admin'], 'testadmin')}"},
    )

    assert response.status_code == 200
    assert response.json() == {"subject": "admin-1", "username": "testadmin"}

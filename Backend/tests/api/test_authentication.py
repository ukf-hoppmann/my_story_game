"""End-to-end wiring: the Authorization header reaches the token verifier.

``tests/api/auth/test_token_verifier.py`` covers the verifier's own
signature/issuer/expiry rules in isolation; this covers the surrounding glue
in ``get_current_initiator`` (header parsing, 401 responses) with the app
wired the way ``create_app`` actually wires it — no dependency override.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from story_game.api import create_app
from story_game.api.auth import KeycloakTokenVerifier
from story_game.api.config import ApiSettings
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

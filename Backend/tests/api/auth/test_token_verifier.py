"""Unit tests for KeycloakTokenVerifier — no running Keycloak required.

A locally generated RSA key pair stands in for a Keycloak realm's signing
key; a fake JWKS client hands the verifier the matching public key directly
instead of fetching it over the network, so these tests exercise exactly the
same ``jwt.decode`` validation Keycloak-issued tokens would go through.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from story_game.api.auth import KeycloakTokenVerifier, TokenVerificationError
from story_game.application.run_initiator import RunInitiator

ISSUER = "http://keycloak.test/realms/story-game"
AUDIENCE = "story-game-frontend"
KID = "test-key"

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeSigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


class _FakeJwksClient:
    """Stands in for ``jwt.PyJWKClient`` without any network access."""

    def __init__(self, public_key: object) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._public_key)


def _verifier(*, audience: str | None = AUDIENCE) -> KeycloakTokenVerifier:
    verifier = KeycloakTokenVerifier(ISSUER, audience)
    verifier._jwks_client = _FakeJwksClient(_PRIVATE_KEY.public_key())  # type: ignore[attr-defined]
    return verifier


def _token(
    *,
    subject: str = "user-1",
    issuer: str = ISSUER,
    audience: str | None = AUDIENCE,
    expires_delta: timedelta = timedelta(minutes=5),
    private_key: object = _PRIVATE_KEY,
    include_subject: bool = True,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {"iss": issuer, "iat": now, "exp": now + expires_delta}
    if audience is not None:
        claims["aud"] = audience
    if include_subject:
        claims["sub"] = subject
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": KID})


def test_a_valid_token_resolves_to_the_subjects_identity() -> None:
    initiator = _verifier().verify(_token(subject="user-42"))

    assert initiator == RunInitiator(ISSUER, "user-42")


def test_an_expired_token_is_rejected() -> None:
    token = _token(expires_delta=timedelta(minutes=-1))

    with pytest.raises(TokenVerificationError):
        _verifier().verify(token)


def test_a_token_from_the_wrong_issuer_is_rejected() -> None:
    token = _token(issuer="http://someone-else.test/realms/other")

    with pytest.raises(TokenVerificationError):
        _verifier().verify(token)


def test_a_token_for_the_wrong_audience_is_rejected() -> None:
    token = _token(audience="some-other-client")

    with pytest.raises(TokenVerificationError):
        _verifier().verify(token)


def test_audience_checking_can_be_disabled() -> None:
    token = _token(audience="anything")

    initiator = _verifier(audience=None).verify(token)

    assert initiator == RunInitiator(ISSUER, "user-1")


def test_a_token_signed_by_an_untrusted_key_is_rejected() -> None:
    token = _token(private_key=_OTHER_PRIVATE_KEY)

    with pytest.raises(TokenVerificationError):
        _verifier().verify(token)


def test_a_token_without_a_subject_claim_is_rejected() -> None:
    token = _token(include_subject=False)

    with pytest.raises(TokenVerificationError):
        _verifier().verify(token)


def _token_with_roles(roles: object, username: object = None) -> str:
    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-1",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "realm_access": roles,
    }
    if username is not None:
        claims["preferred_username"] = username
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": KID})


def test_realm_roles_of_the_token_are_exposed_on_the_verified_caller() -> None:
    caller = _verifier().verify_caller(_token_with_roles({"roles": ["admin", "offline_access"]}))

    assert caller.initiator == RunInitiator(ISSUER, "user-1")
    assert caller.roles == frozenset({"admin", "offline_access"})


def test_a_token_without_realm_access_has_no_roles() -> None:
    caller = _verifier().verify_caller(_token())

    assert caller.roles == frozenset()


def test_a_malformed_realm_access_claim_yields_no_roles() -> None:
    assert _verifier().verify_caller(_token_with_roles("admin")).roles == frozenset()
    assert _verifier().verify_caller(_token_with_roles({"roles": "admin"})).roles == frozenset()
    assert _verifier().verify_caller(_token_with_roles({"roles": [1, None]})).roles == frozenset()


def test_the_username_claim_is_exposed_on_the_verified_caller() -> None:
    caller = _verifier().verify_caller(_token_with_roles({"roles": []}, username="testadmin"))

    assert caller.username == "testadmin"


def test_a_missing_or_malformed_username_claim_yields_none() -> None:
    assert _verifier().verify_caller(_token()).username is None
    assert _verifier().verify_caller(_token_with_roles({"roles": []}, username=7)).username is None
    assert _verifier().verify_caller(_token_with_roles({"roles": []}, username="  ")).username is None

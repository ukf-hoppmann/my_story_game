"""Verify a Keycloak-issued Bearer token and derive the caller's identity.

This is a transport-layer authentication concern, not an application use
case: it produces either a trustworthy ``RunInitiator`` or a reason to
reject the request outright, never a ``Success``/``Failure`` domain result.
It therefore lives here, in the API composition-root area, next to
``dependencies.py`` — the one place already responsible for turning
infrastructure into application-facing values (see ``get_current_initiator``).
"""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

from story_game.application.run_initiator import RunInitiator


class TokenVerificationError(Exception):
    """The presented bearer token is missing, malformed, or not trustworthy."""


class KeycloakTokenVerifier:
    """Verifies a token's signature, issuer, expiry, and (optional) audience.

    Signature verification uses the issuing realm's published JWKS (its
    public signing keys) rather than a shared secret. ``PyJWKClient`` fetches
    and caches those keys by the token's ``kid`` header, so a normal request
    costs no network round-trip to Keycloak — only an occasional key refresh
    when an unknown ``kid`` is seen (e.g. after Keycloak rotates its keys).
    """

    def __init__(
        self, issuer: str, audience: str | None = None, *, jwks_uri: str | None = None
    ) -> None:
        """``jwks_uri`` defaults to the issuer's own well-known endpoint.

        They can differ on purpose: in Docker, the browser and the backend
        reach Keycloak through different addresses (published host port vs.
        the compose service name), but a token's ``iss`` claim reflects
        whatever address the browser used. ``issuer`` must match that claim
        exactly; ``jwks_uri`` only has to be *some* address from which this
        process can fetch the realm's public keys.
        """
        self._issuer = issuer
        self._audience = audience
        self._jwks_client = PyJWKClient(
            jwks_uri or f"{issuer}/protocol/openid-connect/certs"
        )

    def verify(self, token: str) -> RunInitiator:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"verify_aud": self._audience is not None},
            )
        except jwt.PyJWTError as error:
            raise TokenVerificationError(str(error)) from error
        subject = claims.get("sub")
        if not subject:
            raise TokenVerificationError("Dem Token fehlt der sub-Claim")
        return RunInitiator(self._issuer, subject)

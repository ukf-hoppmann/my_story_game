"""FastAPI dependencies exposing application contracts, not infrastructure."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from story_game.application import (
    ConfirmGameRunProposal,
    PlayStoryTurn,
    ProposeGameRun,
    RunInitiator,
    StartPlaythrough,
)
from story_game.application.game_state import GameStateOperations

from .auth import KeycloakTokenVerifier, TokenVerificationError


@dataclass(frozen=True, slots=True)
class ApiDependencies:
    """Application-facing dependencies required by the HTTP adapter."""

    operations: GameStateOperations
    propose_run: ProposeGameRun
    confirm_proposal: ConfirmGameRunProposal
    play_turn: PlayStoryTurn
    start_playthrough: StartPlaythrough


def get_api_dependencies(request: Request) -> ApiDependencies:
    """Resolve the application contracts installed by the app lifespan."""
    dependencies = getattr(request.app.state, "api_dependencies", None)
    if not isinstance(dependencies, ApiDependencies):
        raise RuntimeError("Die API-Abhängigkeiten wurden nicht initialisiert")
    return dependencies


def get_current_initiator(request: Request) -> RunInitiator:
    """Resolve the caller's identity from a verified Keycloak Bearer token.

    Every router depends on this one function for identity. Tests that don't
    want a real token override this dependency via
    ``app.dependency_overrides`` instead of calling Keycloak.
    """
    verifier = getattr(request.app.state, "token_verifier", None)
    if not isinstance(verifier, KeycloakTokenVerifier):
        raise RuntimeError("Der Token-Verifier wurde nicht initialisiert")
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Es wurde kein gültiger Bearer-Token übermittelt",
        )
    try:
        return verifier.verify(token)
    except TokenVerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error

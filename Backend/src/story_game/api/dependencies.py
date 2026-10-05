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
from story_game.application.diagnostics_reporting import ReportFrontendError
from story_game.application.game_state import GameStateOperations, PromptProfileValidator
from story_game.application.llm import PromptPackageCatalog
from story_game.application.model_settings import ModelSettingsOperations
from story_game.application.prompt_management import PromptManagementOperations
from story_game.application.scene_image import SceneImageOperations

from .auth import KeycloakTokenVerifier, TokenVerificationError, VerifiedCaller

ADMIN_ROLE = "admin"
"""Keycloak realm role that unlocks the settings endpoints."""


@dataclass(frozen=True, slots=True)
class ApiDependencies:
    """Application-facing dependencies required by the HTTP adapter."""

    operations: GameStateOperations
    propose_run: ProposeGameRun
    confirm_proposal: ConfirmGameRunProposal
    play_turn: PlayStoryTurn
    start_playthrough: StartPlaythrough
    prompt_catalog: PromptPackageCatalog
    prompt_profile_validator: PromptProfileValidator
    report_frontend_error: ReportFrontendError
    scene_images: SceneImageOperations | None = None
    """``None`` when the scene-image feature is disabled by configuration."""
    model_settings: ModelSettingsOperations | None = None
    """Set by the composition root; ``None`` only in tests that never reach the admin routes."""
    prompt_management: PromptManagementOperations | None = None
    """Set by the composition root; ``None`` only in tests that never reach the admin routes."""


def get_api_dependencies(request: Request) -> ApiDependencies:
    """Resolve the application contracts installed by the app lifespan."""
    dependencies = getattr(request.app.state, "api_dependencies", None)
    if not isinstance(dependencies, ApiDependencies):
        raise RuntimeError("Die API-Abhängigkeiten wurden nicht initialisiert")
    return dependencies


def get_verified_caller(request: Request) -> VerifiedCaller:
    """Resolve the caller's identity and realm roles from a verified Bearer token."""
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
        return verifier.verify_caller(token)
    except TokenVerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error


def get_current_initiator(request: Request) -> RunInitiator:
    """Resolve the caller's identity from a verified Keycloak Bearer token.

    Every router depends on this one function for identity. Tests that don't
    want a real token override this dependency via
    ``app.dependency_overrides`` instead of calling Keycloak.
    """
    return get_verified_caller(request).initiator


def require_admin(request: Request) -> VerifiedCaller:
    """Like ``get_current_initiator``, but only for callers holding ``ADMIN_ROLE``.

    The backend is the only enforcement point; the frontend merely hides the
    settings entry for callers without the role.
    """
    caller = get_verified_caller(request)
    if ADMIN_ROLE not in caller.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Für diese Aktion ist die Rolle admin erforderlich",
        )
    return caller

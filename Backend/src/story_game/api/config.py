"""Environment-backed settings for the HTTP adapter."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApiSettings:
    title: str = "Story Game API"
    version: str = "0.1.0"
    postgres_dsn: str = (
        "postgresql://story_game:story_game_dev@localhost:5433/story_game"
    )
    prompt_root: str = "prompts"
    auto_migrate: bool = True
    config_path: str = "configs/app.toml"
    llm_config_path: str = "configs/llm.toml"
    dev_issuer: str = "https://dev.story-game.local/realm"
    """Identity used only by tests that override ``get_current_initiator``.

    Production requests are never resolved this way — see
    ``get_current_initiator`` in ``dependencies.py``, which verifies a real
    Keycloak Bearer token instead.
    """
    dev_subject: str = "dev-user"
    cors_allowed_origins: tuple[str, ...] = ("http://localhost:5173",)
    """Browser origins allowed to call this API — the Vite dev server by default."""
    keycloak_issuer: str = "http://localhost:8081/realms/story-game"
    """The trusted realm; must equal a token's ``iss`` claim exactly."""
    keycloak_audience: str | None = "story-game-frontend"
    """Expected ``aud`` claim; ``None`` disables audience checking entirely."""
    keycloak_jwks_uri: str | None = None
    """Where to fetch the realm's public signing keys, if not ``<issuer>/protocol/openid-connect/certs``.

    Needed in Docker: the backend and the browser reach Keycloak through
    different addresses (compose service name vs. published host port), but
    ``keycloak_issuer`` must match what the browser actually used, since
    that becomes the token's ``iss`` claim.
    """

    @classmethod
    def from_environment(cls) -> ApiSettings:
        defaults = cls()
        return cls(
            title=os.environ.get("STORY_GAME_API_TITLE", defaults.title),
            version=os.environ.get("STORY_GAME_API_VERSION", defaults.version),
            postgres_dsn=os.environ.get(
                "STORY_GAME_POSTGRES_DSN", defaults.postgres_dsn
            ),
            prompt_root=os.environ.get("STORY_GAME_PROMPT_ROOT", defaults.prompt_root),
            auto_migrate=_boolean_environment(
                "STORY_GAME_AUTO_MIGRATE", default=defaults.auto_migrate
            ),
            config_path=os.environ.get("STORY_GAME_CONFIG_PATH", defaults.config_path),
            llm_config_path=os.environ.get(
                "STORY_GAME_LLM_CONFIG_PATH", defaults.llm_config_path
            ),
            dev_issuer=os.environ.get("STORY_GAME_DEV_ISSUER", defaults.dev_issuer),
            dev_subject=os.environ.get("STORY_GAME_DEV_SUBJECT", defaults.dev_subject),
            cors_allowed_origins=_origin_list_environment(
                "STORY_GAME_CORS_ALLOWED_ORIGINS", default=defaults.cors_allowed_origins
            ),
            keycloak_issuer=os.environ.get(
                "STORY_GAME_KEYCLOAK_ISSUER", defaults.keycloak_issuer
            ),
            keycloak_audience=os.environ.get(
                "STORY_GAME_KEYCLOAK_AUDIENCE", defaults.keycloak_audience
            ),
            keycloak_jwks_uri=os.environ.get(
                "STORY_GAME_KEYCLOAK_JWKS_URI", defaults.keycloak_jwks_uri
            ),
        )


def _boolean_environment(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _origin_list_environment(name: str, *, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.environ.get(name)
    if value is None:
        return default
    origins = tuple(origin.strip() for origin in value.split(",") if origin.strip())
    return origins or default

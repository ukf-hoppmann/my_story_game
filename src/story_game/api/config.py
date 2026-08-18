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
    """Fixed development identity until Keycloak token parsing lands.

    Every request currently resolves to this one identity — see
    ``get_current_initiator`` in ``dependencies.py``.
    """
    dev_subject: str = "dev-user"

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
        )


def _boolean_environment(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

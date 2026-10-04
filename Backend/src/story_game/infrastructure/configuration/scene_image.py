"""Validated ``[scene_image]`` settings and Modal credentials.

The feature is off unless ``enabled = true``: the target deployment may not
be able to reach Modal at all, so every default is the disabled state.
Credentials never live in ``app.toml``; they are read from the sibling,
gitignored ``scene_image.secrets.toml`` (llm-integration §3).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .app_config import AppConfigurationError

MIN_REFINE_STRENGTH = 0.1
MAX_REFINE_STRENGTH = 0.8


@dataclass(frozen=True, slots=True)
class ModalSettings:
    url: str
    control_url: str
    model: str
    timeout_seconds: float = 900.0
    negative_prompt: str | None = None
    refine_negative_prompt: str | None = None


@dataclass(frozen=True, slots=True)
class ModalCredentials:
    key: str
    secret: str

    @property
    def bearer(self) -> str:
        return f"{self.key}.{self.secret}"


@dataclass(frozen=True, slots=True)
class SceneImageSettings:
    enabled: bool = False
    turn_window: int = 3
    width: int = 1024
    height: int = 1024
    refine: bool = False
    refine_model: str = "juggernaut-xl-ragnarok"
    refine_strength: float = 0.35
    compact_prompt_max_words: int = 60
    modal: ModalSettings | None = None


_TOP_KEYS = {
    "enabled",
    "provider",
    "turn_window",
    "width",
    "height",
    "refine",
    "refine_model",
    "refine_strength",
    "compact_prompt_max_words",
    "modal",
}
_MODAL_KEYS = {
    "url",
    "control_url",
    "model",
    "timeout_seconds",
    "negative_prompt",
    "refine_negative_prompt",
}


def parse_scene_image(table: dict[str, Any], path: Path) -> SceneImageSettings:
    defaults = SceneImageSettings()
    _keys(table, _TOP_KEYS, "scene_image", path)
    enabled = _boolean(table.get("enabled", defaults.enabled), "scene_image.enabled", path)
    provider = table.get("provider", "modal")
    if provider != "modal":
        raise AppConfigurationError(f"{path}: scene_image.provider unterstützt nur 'modal'")
    refine_strength = _number(
        table.get("refine_strength", defaults.refine_strength),
        "scene_image.refine_strength",
        path,
    )
    if not MIN_REFINE_STRENGTH <= refine_strength <= MAX_REFINE_STRENGTH:
        raise AppConfigurationError(
            f"{path}: scene_image.refine_strength muss zwischen "
            f"{MIN_REFINE_STRENGTH} und {MAX_REFINE_STRENGTH} liegen"
        )
    modal_table = table.get("modal")
    modal = None
    if modal_table is not None:
        if not isinstance(modal_table, dict):
            raise AppConfigurationError(f"{path}: scene_image.modal muss eine Tabelle sein")
        modal = _modal(modal_table, path)
    elif enabled:
        raise AppConfigurationError(
            f"{path}: scene_image.modal fehlt, obwohl scene_image.enabled gesetzt ist"
        )
    return SceneImageSettings(
        enabled=enabled,
        turn_window=_positive_int(
            table.get("turn_window", defaults.turn_window), "scene_image.turn_window", path
        ),
        width=_positive_int(table.get("width", defaults.width), "scene_image.width", path),
        height=_positive_int(table.get("height", defaults.height), "scene_image.height", path),
        refine=_boolean(table.get("refine", defaults.refine), "scene_image.refine", path),
        refine_model=_text(
            table.get("refine_model", defaults.refine_model), "scene_image.refine_model", path
        ),
        refine_strength=refine_strength,
        compact_prompt_max_words=_positive_int(
            table.get("compact_prompt_max_words", defaults.compact_prompt_max_words),
            "scene_image.compact_prompt_max_words",
            path,
        ),
        modal=modal,
    )


def _modal(table: dict[str, Any], path: Path) -> ModalSettings:
    _keys(table, _MODAL_KEYS, "scene_image.modal", path)
    for required in ("url", "control_url", "model"):
        if required not in table:
            raise AppConfigurationError(f"{path}: scene_image.modal.{required} fehlt")
    return ModalSettings(
        url=_url(table["url"], "scene_image.modal.url", path),
        control_url=_url(table["control_url"], "scene_image.modal.control_url", path),
        model=_text(table["model"], "scene_image.modal.model", path),
        timeout_seconds=_number(
            table.get("timeout_seconds", 900.0), "scene_image.modal.timeout_seconds", path
        ),
        negative_prompt=_optional_text(
            table.get("negative_prompt"), "scene_image.modal.negative_prompt", path
        ),
        refine_negative_prompt=_optional_text(
            table.get("refine_negative_prompt"),
            "scene_image.modal.refine_negative_prompt",
            path,
        ),
    )


def load_modal_credentials(config_path: str | Path) -> ModalCredentials | None:
    """Read ``scene_image.secrets.toml`` next to ``config_path``; ``None`` if absent."""
    path = Path(config_path).parent / "scene_image.secrets.toml"
    if not path.is_file():
        return None
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise AppConfigurationError(
            f"Die Szenenbild-Secrets konnten nicht gelesen werden: {path}"
        ) from error
    _keys(document, {"modal"}, "die Secrets-Konfiguration", path)
    table = document.get("modal")
    if not isinstance(table, dict):
        raise AppConfigurationError(f"{path}: modal muss eine Tabelle sein")
    _keys(table, {"key", "secret"}, "modal", path)
    return ModalCredentials(
        key=_text(table.get("key"), "modal.key", path),
        secret=_text(table.get("secret"), "modal.secret", path),
    )


def _keys(document: dict[str, Any], allowed: set[str], label: str, path: Path) -> None:
    unknown = set(document) - allowed
    if unknown:
        raise AppConfigurationError(
            f"{path}: Unbekannte Felder in {label}: {', '.join(sorted(unknown))}"
        )


def _boolean(value: Any, label: str, path: Path) -> bool:
    if not isinstance(value, bool):
        raise AppConfigurationError(f"{path}: {label} muss true oder false sein")
    return value


def _positive_int(value: Any, label: str, path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AppConfigurationError(f"{path}: {label} muss eine positive ganze Zahl sein")
    return value


def _number(value: Any, label: str, path: Path) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise AppConfigurationError(f"{path}: {label} muss eine positive Zahl sein")
    return float(value)


def _text(value: Any, label: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AppConfigurationError(f"{path}: {label} muss nichtleerer Text sein")
    return value.strip()


def _optional_text(value: Any, label: str, path: Path) -> str | None:
    return None if value is None else _text(value, label, path)


def _url(value: Any, label: str, path: Path) -> str:
    text = _text(value, label, path)
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AppConfigurationError(f"{path}: {label} muss eine HTTP- oder HTTPS-URL sein")
    return text.rstrip("/")


__all__ = [
    "MAX_REFINE_STRENGTH",
    "MIN_REFINE_STRENGTH",
    "ModalCredentials",
    "ModalSettings",
    "SceneImageSettings",
    "load_modal_credentials",
    "parse_scene_image",
]

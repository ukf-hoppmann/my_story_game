from __future__ import annotations

from .live_settings import live_base_url


def test_live_base_url_uses_the_project_configuration_without_an_override(
    monkeypatch,
) -> None:
    monkeypatch.delenv("STORY_LMSTUDIO_LIVE_BASE_URL", raising=False)

    assert live_base_url("http://host.docker.internal:1234/v1") == (
        "http://host.docker.internal:1234/v1"
    )


def test_live_base_url_prefers_the_explicit_host_override(monkeypatch) -> None:
    monkeypatch.setenv(
        "STORY_LMSTUDIO_LIVE_BASE_URL",
        " http://localhost:1234/v1 ",
    )

    assert live_base_url("http://host.docker.internal:1234/v1") == (
        "http://localhost:1234/v1"
    )

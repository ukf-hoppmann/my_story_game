"""Health checks for the locally exposed Story Game API."""

from __future__ import annotations

import json
import os
import time
from urllib.request import urlopen


def backend_port() -> int:
    """Return the configured API host port, validating malformed overrides."""

    value = os.environ.get("BACKEND_HOST_PORT", "8000")
    try:
        port = int(value)
    except ValueError as error:
        raise ValueError(f"BACKEND_HOST_PORT ist keine gültige Portnummer: {value!r}") from error
    if not 1 <= port <= 65535:
        raise ValueError(f"BACKEND_HOST_PORT liegt außerhalb des gültigen Bereichs: {port}")
    return port


def backend_health() -> tuple[bool, str]:
    """Check the public API health endpoint without adding a dependency."""

    url = f"http://localhost:{backend_port()}/health"
    try:
        with urlopen(url, timeout=3) as response:  # noqa: S310 - fixed localhost URL
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        return False, str(error)
    if response.status != 200 or body != {"status": "ok"}:
        return False, f"unerwartete Antwort ({response.status}): {body!r}"
    return True, url


def wait_for_backend_health(timeout_seconds: float = 15.0) -> tuple[bool, str]:
    """Poll the API briefly after a container restart."""

    deadline = time.monotonic() + timeout_seconds
    last_detail = "keine Antwort"
    while time.monotonic() < deadline:
        healthy, detail = backend_health()
        if healthy:
            return True, detail
        last_detail = detail
        time.sleep(0.25)
    return False, last_detail

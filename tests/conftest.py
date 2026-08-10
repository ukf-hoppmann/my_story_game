from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-lmstudio-live",
        action="store_true",
        default=False,
        help="Run the explicitly enabled LM Studio live smoke test.",
    )

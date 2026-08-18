from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from story_game.application.contracts import Failure, Success


@pytest.mark.parametrize(
    ("result", "attribute"),
    [(Success("value"), "data"), (Failure("error"), "error")],
)
def test_operation_results_are_immutable(result: object, attribute: str) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(result, attribute, "changed")

"""Shared structured-output shape for narration-plus-choices calls.

Story generation and story initialization ask the model for exactly the same
thing — prose plus a few short continuation suggestions — so they share one
wire schema instead of maintaining two identical Pydantic models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WireNarrationWithOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    narration: str = Field(min_length=1)
    continuation_options: list[str] = Field(
        description=(
            "3-4 short, mutually distinct suggestions for how the player "
            "could continue, phrased as actions the player could take."
        ),
    )


__all__ = ["WireNarrationWithOptions"]

"""Transport shapes for the global game settings."""

from __future__ import annotations

from datetime import datetime

from .common import APIModel


class WorldTrackingModel(APIModel):
    """Whether world Extraction runs; ``updated_*`` is empty until first changed."""

    enabled: bool
    updated_at: datetime | None = None
    updated_by: str | None = None


class UpdateWorldTrackingRequestModel(APIModel):
    enabled: bool


class WorldTrackingStatusModel(APIModel):
    """What every player may know: only whether world tracking is on."""

    enabled: bool

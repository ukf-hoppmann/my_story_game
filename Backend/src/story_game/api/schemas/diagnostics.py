"""Transport shape for a frontend-reported tooling error (TASK-030)."""

from __future__ import annotations

from pydantic import Field

from .common import APIModel


class FrontendErrorReportModel(APIModel):
    """Bounded, structured report of a frontend-side tooling failure.

    Field limits are the actual defense against payload-size abuse on this
    public-to-authenticated-users endpoint; ``ReportFrontendError.apply()``
    revalidates non-blankness defensively but does not repeat these limits.
    """

    source: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    url: str | None = Field(default=None, max_length=500)
    user_agent: str | None = Field(default=None, max_length=300)

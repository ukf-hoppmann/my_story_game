"""Application-owned model ports."""

from __future__ import annotations

from typing import Protocol

from ..contracts import OperationResult
from .contracts import LLMError, LLMGenerationCall, StoryGenerationData, StoryGenerationRequest


class StoryGenerationPort(Protocol):
    """Generate normalized prose for a prepared story-generation request."""

    def generate(
        self,
        call: LLMGenerationCall[StoryGenerationRequest],
    ) -> OperationResult[StoryGenerationData, LLMError]: ...

"""Application-owned model ports."""

from __future__ import annotations

from typing import Protocol

from ..contracts import OperationResult
from .contracts import (
    LLMError,
    LLMGenerationCall,
    ModelSelection,
    StoryGenerationData,
    StoryGenerationRequest,
)
from .prompts import PromptPackage


class ModelSelectionResolver(Protocol):
    """Resolve a configured logical model reference for one invocation."""

    def resolve(self, logical_model_id: str) -> ModelSelection: ...


class PromptPackageCatalog(Protocol):
    """Load a validated prompt package without exposing its storage medium."""

    def load(self, package_id: str, version: str) -> PromptPackage: ...


class StoryGenerationPort(Protocol):
    """Generate normalized prose for a prepared story-generation request."""

    def generate(
        self,
        call: LLMGenerationCall[StoryGenerationRequest],
    ) -> OperationResult[StoryGenerationData, LLMError]: ...

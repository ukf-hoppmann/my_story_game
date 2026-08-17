"""Application-owned model ports."""

from __future__ import annotations

from typing import Protocol

from ..contracts import OperationResult
from .contracts import (
    LLMError,
    LLMGenerationCall,
    GenerationConfiguration,
    GenerationTask,
    ModelSelection,
    InitialStoryText,
    StoryGenerationData,
    StoryGenerationRequest,
    StoryInitializationRequest,
)
from .prompts import PromptPackage
from .initial_extraction import InitialWorldExtractionRequest, WorldInitializationCandidate
from .summary import StorySummaryRequest, StorySummaryText
from .turn_extraction import TurnChangeCandidate, TurnExtractionRequest


class ModelSelectionResolver(Protocol):
    """Resolve a configured logical model reference for one invocation."""

    def resolve(self, logical_model_id: str) -> ModelSelection: ...


class GenerationConfigurationResolver(Protocol):
    """Resolve current model and options together for each application task."""

    def resolve(
        self, task: GenerationTask
    ) -> OperationResult[GenerationConfiguration, LLMError]: ...


class PromptPackageCatalog(Protocol):
    """Load a validated prompt package without exposing its storage medium."""

    def load(self, package_id: str, version: str) -> PromptPackage: ...


class StoryGenerationPort(Protocol):
    """Generate normalized prose for a prepared story-generation request."""

    def generate(
        self,
        call: LLMGenerationCall[StoryGenerationRequest],
    ) -> OperationResult[StoryGenerationData, LLMError]: ...


class StoryInitializationPort(Protocol):
    """Generate normalized opening prose without world or story context."""

    def generate(
        self,
        call: LLMGenerationCall[StoryInitializationRequest],
    ) -> OperationResult[InitialStoryText, LLMError]: ...


class InitialWorldExtractionPort(Protocol):
    """Extract a structurally valid initial WorldState candidate."""

    def extract(
        self,
        call: LLMGenerationCall[InitialWorldExtractionRequest],
    ) -> OperationResult[WorldInitializationCandidate, LLMError]: ...


class TurnExtractionPort(Protocol):
    """Propose the delta one turn's prose implies for an existing world."""

    def extract(
        self,
        call: LLMGenerationCall[TurnExtractionRequest],
    ) -> OperationResult[TurnChangeCandidate, LLMError]: ...


class StorySummaryPort(Protocol):
    """Roll the running summary forward by one completed turn."""

    def summarize(
        self,
        call: LLMGenerationCall[StorySummaryRequest],
    ) -> OperationResult[StorySummaryText, LLMError]: ...

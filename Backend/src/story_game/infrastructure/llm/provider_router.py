"""Per-task provider routing across otherwise identical model ports.

Model/generation selection (which logical model, which provider_id) is
already re-resolved from ``configs/llm.toml`` on every call by
``TomlGenerationConfigurationResolver`` — see
``LLMGenerationCall.model_selection.provider_id``. These routers add the one
missing piece: picking the already-constructed adapter instance that matches
that provider_id, freshly for every call, instead of the Composition Root
wiring exactly one provider in for the lifetime of the process.

Each router is a thin, explicitly typed wrapper around one application port.
A generic/untyped dispatcher was deliberately rejected in favor of five small
classes, one per port shape, to keep the concrete sequence and types visible
at the Composition Root (see ``.harness/architecture-rules.md`` §4).
"""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application import Failure, LLMGenerationCall, OperationResult
from story_game.application.llm import (
    InitialStoryText,
    InitialWorldExtractionPort,
    InitialWorldExtractionRequest,
    LLMError,
    LLMErrorKind,
    StoryGenerationData,
    StoryGenerationPort,
    StoryGenerationRequest,
    StoryInitializationPort,
    StoryInitializationRequest,
    StorySummaryPort,
    StorySummaryRequest,
    StorySummaryText,
    TurnChangeCandidate,
    TurnExtractionPort,
    TurnExtractionRequest,
    WorldInitializationCandidate,
)


def _unknown_provider(provider_id: str) -> Failure[LLMError]:
    return Failure(
        LLMError(
            LLMErrorKind.CONFIGURATION,
            f"Für den Provider {provider_id!r} ist kein Adapter konfiguriert.",
        )
    )


@dataclass(frozen=True, slots=True)
class RoutingStoryInitializationAdapter(StoryInitializationPort):
    adapters: dict[str, StoryInitializationPort]

    def generate(
        self, call: LLMGenerationCall[StoryInitializationRequest]
    ) -> OperationResult[InitialStoryText, LLMError]:
        adapter = self.adapters.get(call.model_selection.provider_id)
        if adapter is None:
            return _unknown_provider(call.model_selection.provider_id)
        return adapter.generate(call)


@dataclass(frozen=True, slots=True)
class RoutingStoryGenerationAdapter(StoryGenerationPort):
    adapters: dict[str, StoryGenerationPort]

    def generate(
        self, call: LLMGenerationCall[StoryGenerationRequest]
    ) -> OperationResult[StoryGenerationData, LLMError]:
        adapter = self.adapters.get(call.model_selection.provider_id)
        if adapter is None:
            return _unknown_provider(call.model_selection.provider_id)
        return adapter.generate(call)


@dataclass(frozen=True, slots=True)
class RoutingInitialWorldExtractionAdapter(InitialWorldExtractionPort):
    adapters: dict[str, InitialWorldExtractionPort]

    def extract(
        self, call: LLMGenerationCall[InitialWorldExtractionRequest]
    ) -> OperationResult[WorldInitializationCandidate, LLMError]:
        adapter = self.adapters.get(call.model_selection.provider_id)
        if adapter is None:
            return _unknown_provider(call.model_selection.provider_id)
        return adapter.extract(call)


@dataclass(frozen=True, slots=True)
class RoutingTurnExtractionAdapter(TurnExtractionPort):
    adapters: dict[str, TurnExtractionPort]

    def extract(
        self, call: LLMGenerationCall[TurnExtractionRequest]
    ) -> OperationResult[TurnChangeCandidate, LLMError]:
        adapter = self.adapters.get(call.model_selection.provider_id)
        if adapter is None:
            return _unknown_provider(call.model_selection.provider_id)
        return adapter.extract(call)


@dataclass(frozen=True, slots=True)
class RoutingStorySummaryAdapter(StorySummaryPort):
    adapters: dict[str, StorySummaryPort]

    def summarize(
        self, call: LLMGenerationCall[StorySummaryRequest]
    ) -> OperationResult[StorySummaryText, LLMError]:
        adapter = self.adapters.get(call.model_selection.provider_id)
        if adapter is None:
            return _unknown_provider(call.model_selection.provider_id)
        return adapter.summarize(call)


__all__ = [
    "RoutingInitialWorldExtractionAdapter",
    "RoutingStoryGenerationAdapter",
    "RoutingStoryInitializationAdapter",
    "RoutingStorySummaryAdapter",
    "RoutingTurnExtractionAdapter",
]

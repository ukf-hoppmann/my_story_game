"""Deterministic, no-network LLM port doubles for exercising the real API.

Unlike ``tests/infrastructure/llm/lmstudio/human_test_support.py`` (which
talks to a live LM Studio for human inspection), these doubles let
``tests/api/test_api.py`` drive the real ``InitializeGameRun``/
``PlayStoryTurn``/``StartPlaythrough`` workflows end to end — real prompt
building, real domain validation, real (in-memory) persistence — without a
model server. Every candidate returned is deliberately empty: an empty
``WorldInitializationCandidate``/``TurnChangeCandidate`` is a structurally
valid "the model proposed nothing" result, which is enough to exercise the
success path without hand-authoring narrative entities.
"""

from __future__ import annotations

from story_game.application import InitialStoryText, StoryGenerationData, Success
from story_game.application.llm import (
    GenerationConfiguration,
    GenerationOptions,
    GenerationTask,
    ModelSelection,
    StorySummaryText,
    TurnChangeCandidate,
    WorldInitializationCandidate,
)


class FakeGenerationConfigurationResolver:
    def resolve(self, task: GenerationTask):
        return Success(
            GenerationConfiguration(
                ModelSelection("fake-provider", f"fake-model-{task.value}"),
                GenerationOptions(),
            )
        )


class FakeStoryInitializationPort:
    def generate(self, call):
        return Success(InitialStoryText("[Test] Eröffnungsprosa."))


class FakeInitialWorldExtractionPort:
    def extract(self, call):
        return Success(WorldInitializationCandidate())


class FakeStoryGenerationPort:
    def generate(self, call):
        return Success(StoryGenerationData("[Test] Zugprosa."))


class FakeTurnExtractionPort:
    def extract(self, call):
        return Success(TurnChangeCandidate())


class FakeStorySummaryPort:
    def summarize(self, call):
        return Success(StorySummaryText("[Test] Zusammenfassung."))

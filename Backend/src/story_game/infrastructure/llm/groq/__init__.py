"""Groq provider adapters, built on the shared openai_compatible core.

There is no ``GroqClient`` type here anymore: after the shared-core
refactor, every provider uses the same ``OpenAiCompatibleClient`` (see
``infrastructure.llm.openai_compatible``), constructed with this package's
own ``groq_settings`` factory.
"""

from .adapter import GroqStoryGenerationAdapter
from .initialization_adapter import GroqStoryInitializationAdapter
from .initial_extraction_adapter import GroqInitialWorldExtractionAdapter
from .settings import groq_settings
from .summary_adapter import GroqStorySummaryAdapter
from .turn_extraction_adapter import GroqTurnExtractionAdapter

__all__ = [
    "GroqInitialWorldExtractionAdapter",
    "GroqStoryGenerationAdapter",
    "GroqStoryInitializationAdapter",
    "GroqStorySummaryAdapter",
    "GroqTurnExtractionAdapter",
    "groq_settings",
]

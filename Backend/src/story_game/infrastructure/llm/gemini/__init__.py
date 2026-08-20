"""Gemini provider adapters, built on the shared openai_compatible core."""

from .adapter import GeminiStoryGenerationAdapter
from .initialization_adapter import GeminiStoryInitializationAdapter
from .initial_extraction_adapter import GeminiInitialWorldExtractionAdapter
from .settings import gemini_settings
from .summary_adapter import GeminiStorySummaryAdapter
from .turn_extraction_adapter import GeminiTurnExtractionAdapter

__all__ = [
    "GeminiInitialWorldExtractionAdapter",
    "GeminiStoryGenerationAdapter",
    "GeminiStoryInitializationAdapter",
    "GeminiStorySummaryAdapter",
    "GeminiTurnExtractionAdapter",
    "gemini_settings",
]

"""LM Studio provider adapters, built on the shared openai_compatible core.

There is no ``LmStudioClient`` type here anymore: after the shared-core
refactor, every provider uses the same ``OpenAiCompatibleClient`` (see
``infrastructure.llm.openai_compatible``), constructed with this package's
own ``lmstudio_settings`` factory.
"""

from .adapter import LmStudioStoryGenerationAdapter
from .initialization_adapter import LmStudioStoryInitializationAdapter
from .initial_extraction_adapter import LmStudioInitialWorldExtractionAdapter
from .settings import lmstudio_settings
from .summary_adapter import LmStudioStorySummaryAdapter
from .turn_extraction_adapter import LmStudioTurnExtractionAdapter

__all__ = [
    "LmStudioInitialWorldExtractionAdapter",
    "LmStudioStoryGenerationAdapter",
    "LmStudioStoryInitializationAdapter",
    "LmStudioStorySummaryAdapter",
    "LmStudioTurnExtractionAdapter",
    "lmstudio_settings",
]

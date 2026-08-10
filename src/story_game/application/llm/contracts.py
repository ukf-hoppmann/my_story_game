"""Typed, provider-independent values for model invocation boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

from ..contracts import Failure, Success


RequestT = TypeVar("RequestT")


class LLMErrorKind(StrEnum):
    """Provider-independent categories that application workflows can handle."""

    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    RATE_LIMITED = "rate_limited"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_REQUEST = "invalid_request"
    CONTEXT_LIMIT = "context_limit"
    INCOMPLETE = "incomplete"
    INVALID_RESPONSE = "invalid_response"
    CONFIGURATION = "configuration"


@dataclass(frozen=True, slots=True)
class LLMError:
    """An expected model failure without provider objects or raw responses."""

    kind: LLMErrorKind
    message: str
    retryable: bool = False

    def __post_init__(self) -> None:
        message = self.message.strip()
        if not message:
            raise ValueError("LLM-Fehlermeldungen dürfen nicht leer sein")
        object.__setattr__(self, "message", message)


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """A logical provider/model reference resolved for one invocation."""

    provider_id: str
    model_id: str

    def __post_init__(self) -> None:
        for name, value in (("provider_id", self.provider_id), ("model_id", self.model_id)):
            value = value.strip()
            if not value:
                raise ValueError(f"{name} darf nicht leer sein")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class GenerationOptions:
    """Provider-neutral options used by the first non-streaming connection."""

    temperature: float | None = None
    max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        if self.temperature is not None and self.temperature < 0:
            raise ValueError("temperature darf nicht negativ sein")
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens muss positiv sein")


class GenerationTask(StrEnum):
    """Stable application task names used to resolve runtime generation settings."""

    STORY = "story"
    EXTRACTION = "extraction"
    SUMMARY = "summary"


@dataclass(frozen=True, slots=True)
class GenerationConfiguration:
    """One coherent model selection and option set for a single call."""

    model_selection: ModelSelection
    generation_options: GenerationOptions


@dataclass(frozen=True, slots=True)
class StoryGenerationRequest:
    """The stable story boundary, before provider-specific serialization."""

    system_prompts: tuple[str, ...]
    configuration: str
    world_state: str
    story_state: str
    user_prompt: str

    def __post_init__(self) -> None:
        prompts = tuple(prompt.strip() for prompt in self.system_prompts if prompt.strip())
        if not prompts:
            raise ValueError("Mindestens ein Systemprompt ist erforderlich")
        object.__setattr__(self, "system_prompts", prompts)
        for name in ("configuration", "world_state", "story_state", "user_prompt"):
            value = getattr(self, name).strip()
            if not value:
                raise ValueError(f"{name} darf nicht leer sein")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class StoryGenerationData:
    """Normalized prose returned by a successful story-generation call."""

    text: str

    def __post_init__(self) -> None:
        text = self.text.strip()
        if not text:
            raise ValueError("Story-Ergebnisse dürfen nicht leer sein")
        object.__setattr__(self, "text", text)


@dataclass(frozen=True, slots=True)
class StoryInitializationRequest:
    """Prepared opening request that deliberately has no game-state context."""

    system_prompts: tuple[str, ...]
    configuration: str
    initial_prompt: str

    def __post_init__(self) -> None:
        prompts = tuple(prompt.strip() for prompt in self.system_prompts if prompt.strip())
        if not prompts:
            raise ValueError("Mindestens ein Systemprompt ist erforderlich")
        object.__setattr__(self, "system_prompts", prompts)
        for name in ("configuration", "initial_prompt"):
            value = getattr(self, name).strip()
            if not value:
                raise ValueError(f"{name} darf nicht leer sein")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class InitialStoryText:
    """Normalized prose returned by a successful opening-generation call."""

    text: str

    def __post_init__(self) -> None:
        text = self.text.strip()
        if not text:
            raise ValueError("Eröffnungsprosa darf nicht leer sein")
        object.__setattr__(self, "text", text)


@dataclass(frozen=True, slots=True)
class LLMGenerationCall(Generic[RequestT]):
    """Technical invocation envelope around one task-specific request."""

    model_selection: ModelSelection
    generation_options: GenerationOptions
    request: RequestT


StoryGenerationResult = Success[StoryGenerationData] | Failure[LLMError]

"""Workflow: write the image prompt(s), render, and store the result."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import DiagnosticsLog, NullDiagnosticsLog
from story_game.application.llm import (
    CompactImagePromptPort,
    CompactImagePromptRequest,
    CompactImagePromptResolver,
    GenerationConfigurationResolver,
    GenerationTask,
    LLMGenerationCall,
    SceneImagePromptPort,
    SceneImagePromptRequest,
    SceneImagePromptResolver,
)
from story_game.application.llm.contracts import GenerationConfiguration

from .errors import SceneImageError, SceneImageErrorKind
from .models import (
    ImageRefinement,
    ImageRenderRequest,
    SceneImageContent,
    SceneImageJob,
    SceneImageRecord,
)
from .ports import SceneImageRenderer, SceneImageStoreError, SceneImageWriter


class GenerateSceneImage:
    """Run one accepted job: prompt, optional compact prompt, render, store.

    The sequence is explicit, nothing is retried automatically, and there is
    deliberately no transaction around it (it contains model and provider
    calls). Every expected failure is written to the image record, so the
    caller can read it later; the returned ``Failure`` is for logging only.
    """

    def __init__(
        self,
        prompt_resolver: SceneImagePromptResolver,
        compact_resolver: CompactImagePromptResolver,
        generation_configuration_resolver: GenerationConfigurationResolver,
        prompt_writer: SceneImagePromptPort,
        compactor: CompactImagePromptPort,
        renderer: SceneImageRenderer,
        writer: SceneImageWriter,
        compact_prompt_max_words: int,
        now: Callable[[], datetime],
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._compact_resolver = compact_resolver
        self._configuration_resolver = generation_configuration_resolver
        self._prompt_writer = prompt_writer
        self._compactor = compactor
        self._renderer = renderer
        self._writer = writer
        self._max_words = compact_prompt_max_words
        self._now = now
        self._diagnostics = diagnostics

    def apply(self, job: SceneImageJob) -> OperationResult[SceneImageRecord, SceneImageError]:
        outcome = self._run(job)
        if isinstance(outcome, Failure):
            self._record_failure(job, outcome.error)
        return outcome

    def _run(self, job: SceneImageJob) -> OperationResult[SceneImageRecord, SceneImageError]:
        record = job.record
        package = (
            job.configuration.prompt_package_id,
            job.configuration.prompt_package_version,
        )
        try:
            task = self._prompt_resolver.resolve(*package)
            compact_task = self._compact_resolver.resolve(*package) if record.refine else None
        except (KeyError, ValueError) as error:
            return _failure(SceneImageErrorKind.CONFIGURATION, str(error))
        generation = self._configuration_resolver.resolve(GenerationTask.SCENE_IMAGE)
        if isinstance(generation, Failure):
            return _failure(SceneImageErrorKind.CONFIGURATION, generation.error.message)

        self._diagnostics.trace("generate_scene_image.prompt", turn_count=len(job.turns))
        written = self._prompt_writer.write(
            self._call(
                generation.data,
                SceneImagePromptRequest(
                    system_prompts=(task.text,),
                    turns=job.turns,
                    language=job.configuration.language,
                ),
            )
        )
        if isinstance(written, Failure):
            return _failure(
                SceneImageErrorKind.PROMPT_FAILED,
                f"Der Bildprompt konnte nicht geschrieben werden: {written.error.message}",
            )
        prompt = written.data.text

        compact_prompt: str | None = None
        if compact_task is not None:
            compacted = self._compactor.compact(
                self._call(
                    generation.data,
                    CompactImagePromptRequest(
                        system_prompts=(compact_task.text,),
                        prompt=prompt,
                        max_words=self._max_words,
                    ),
                )
            )
            if isinstance(compacted, Failure):
                return _failure(
                    SceneImageErrorKind.PROMPT_FAILED,
                    "Der Kurzprompt konnte nicht geschrieben werden: "
                    f"{compacted.error.message}",
                )
            compact_prompt = " ".join(compacted.data.text.split()[: self._max_words])

        try:
            self._writer.save_prompts(record.image_id, prompt, compact_prompt)
        except SceneImageStoreError:
            return _failure(
                SceneImageErrorKind.STORE_UNAVAILABLE,
                "Der Bildprompt konnte nicht gespeichert werden.",
            )

        self._diagnostics.trace("generate_scene_image.render", refine=record.refine)
        rendered = self._renderer.render(
            ImageRenderRequest(
                prompt=prompt,
                seed=record.seed,
                width=record.width,
                height=record.height,
                model=record.model,
                refinement=(
                    ImageRefinement(compact_prompt, record.refine_model, record.refine_strength)
                    if compact_prompt is not None
                    else None
                ),
            )
        )
        if isinstance(rendered, Failure):
            return _failure(
                SceneImageErrorKind.RENDER_FAILED,
                f"Das Bild konnte nicht erzeugt werden: {rendered.error.message}",
            )
        try:
            self._writer.complete(
                record.image_id,
                SceneImageContent(rendered.data.data, rendered.data.content_type),
                self._now(),
            )
        except SceneImageStoreError:
            return _failure(
                SceneImageErrorKind.STORE_UNAVAILABLE,
                "Das Bild konnte nicht gespeichert werden.",
            )
        return Success(record)

    @staticmethod
    def _call(generation: GenerationConfiguration, request):
        return LLMGenerationCall(
            model_selection=generation.model_selection,
            generation_options=generation.generation_options,
            request=request,
        )

    def _record_failure(self, job: SceneImageJob, error: SceneImageError) -> None:
        if error.kind is SceneImageErrorKind.STORE_UNAVAILABLE:
            return
        try:
            self._writer.fail(job.record.image_id, error.message, self._now())
        except SceneImageStoreError:
            self._diagnostics.trace(
                "generate_scene_image.failure_not_recorded", image_id=str(job.record.image_id)
            )


def _failure(kind: SceneImageErrorKind, message: str) -> Failure[SceneImageError]:
    return Failure(SceneImageError(kind, message))


__all__ = ["GenerateSceneImage"]

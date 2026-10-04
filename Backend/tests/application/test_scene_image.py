from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from story_game.application import Failure, RunInitiator, Success
from story_game.application.game_state import LoadGame
from story_game.application.llm import (
    CompactImagePromptResolver,
    GenerationConfiguration,
    GenerationOptions,
    GenerationTask,
    LLMError,
    LLMErrorKind,
    ModelSelection,
    SceneImagePromptResolver,
    SceneImagePromptText,
)
from story_game.application.scene_image import (
    GenerateSceneImage,
    ImageGenError,
    ImageGenErrorKind,
    ImageModelInfo,
    ListSceneImages,
    ListSceneImagesRequest,
    LoadSceneImage,
    LoadSceneImageContent,
    LoadSceneImageContentRequest,
    LoadSceneImageRequest,
    ReadSceneImageCapabilities,
    ReadSceneImageCapabilitiesRequest,
    RenderedImage,
    RequestSceneImage,
    RequestSceneImageRequest,
    SceneImageContent,
    SceneImageDefaults,
    SceneImageErrorKind,
    SceneImageOptions,
    SceneImageRecord,
    SceneImageStatus,
    SceneImageStoreError,
)
from story_game.domain import (
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    StateRevision,
    StoryInitialization,
    StoryState,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.application import turn_context_world as w
from tests.ids import sid

PROMPT_ROOT = Path(__file__).parents[2] / "prompts"
RUN_ID = sid("run")
INITIATOR = RunInitiator("https://identity.example/realms/story", "user-1")
OUTSIDER = RunInitiator("https://identity.example/realms/story", "user-2")
NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)


class FakeGameStore:
    def __init__(self, state) -> None:
        self.state = state
        self.run = GameRun(
            RUN_ID,
            "Marens Reise",
            GameRunStatus.ACTIVE,
            StateRevision(1),
            (GameRunMember(INITIATOR.issuer, INITIATOR.subject, GameRole.OWNER, (w.MAREN,)),),
            NOW,
            NOW,
        )

    def load_run(self, run_id):
        return self.run

    def load_state(self, run_id, *, revision=None):
        return self.state


class FakeImageStore:
    """Both scene-image persistence ports in memory."""

    def __init__(self) -> None:
        self.records: dict = {}
        self.contents: dict = {}
        self.saved_prompts: dict = {}
        self.unavailable = False

    def _check(self) -> None:
        if self.unavailable:
            raise SceneImageStoreError("down")

    def create_pending(self, image):
        self._check()
        record = SceneImageRecord(
            image.image_id,
            image.run_id,
            image.turn_sequence,
            SceneImageStatus.PENDING,
            image.options.model,
            image.options.refine,
            image.options.refine_model,
            image.options.refine_strength,
            image.options.width,
            image.options.height,
            image.options.seed,
            image.created_at,
        )
        self.records[image.image_id] = record
        return record

    def find_active(self, run_id, turn_sequence, *, created_after):
        self._check()
        for record in self.records.values():
            if (
                record.run_id == run_id
                and record.turn_sequence == turn_sequence
                and record.status is SceneImageStatus.PENDING
                and record.created_at > created_after
            ):
                return record
        return None

    def save_prompts(self, image_id, prompt, compact_prompt):
        self._check()
        self.saved_prompts[image_id] = (prompt, compact_prompt)
        self.records[image_id] = replace(
            self.records[image_id], prompt=prompt, compact_prompt=compact_prompt
        )

    def complete(self, image_id, content, completed_at):
        self._check()
        self.contents[image_id] = content
        self.records[image_id] = replace(
            self.records[image_id], status=SceneImageStatus.READY, completed_at=completed_at
        )

    def fail(self, image_id, message, completed_at):
        self._check()
        self.records[image_id] = replace(
            self.records[image_id],
            status=SceneImageStatus.FAILED,
            error_message=message,
            completed_at=completed_at,
        )

    def _visible(self, run_id, issuer, subject) -> bool:
        return run_id == RUN_ID and (issuer, subject) == (INITIATOR.issuer, INITIATOR.subject)

    def get(self, run_id, image_id, issuer, subject):
        self._check()
        record = self.records.get(image_id)
        if record is None or record.run_id != run_id or not self._visible(run_id, issuer, subject):
            return None
        return record

    def list_for_run(self, run_id, issuer, subject, limit):
        self._check()
        if not self._visible(run_id, issuer, subject):
            return ()
        return tuple(self.records.values())[:limit]

    def load_content(self, run_id, image_id, issuer, subject):
        self._check()
        if self.get(run_id, image_id, issuer, subject) is None:
            return None
        return self.contents.get(image_id)


class FixedConfigurationResolver:
    def __init__(self) -> None:
        self.tasks: list = []

    def resolve(self, task):
        self.tasks.append(task)
        return Success(
            GenerationConfiguration(ModelSelection("lmstudio", "model-image"), GenerationOptions())
        )


class FakePromptWriter:
    def __init__(self, result=None) -> None:
        self.result = result or Success(SceneImagePromptText("A tavern at night, warm fire."))
        self.call = None

    def write(self, call):
        self.call = call
        return self.result


class FakeCompactor:
    def __init__(self, result=None) -> None:
        self.result = result or Success(SceneImagePromptText("tavern, fire, night"))
        self.call = None

    def compact(self, call):
        self.call = call
        return self.result


class FakeRenderer:
    def __init__(self, result=None, models=None) -> None:
        self.result = result or Success(RenderedImage(b"png-bytes", "image/png"))
        self.models = models or Success(
            ((ImageModelInfo("z-image-turbo"),), (ImageModelInfo("juggernaut-xl-ragnarok"),))
        )
        self.request = None
        self.calls = 0

    def render(self, request):
        self.calls += 1
        self.request = request
        return self.result

    def list_models(self):
        return self.models


DEFAULTS = SceneImageDefaults(
    turn_window=3,
    model="z-image-turbo",
    refine=False,
    refine_model="juggernaut-xl-ragnarok",
    refine_strength=0.35,
)


def request_operation(state=None, store=None, defaults=DEFAULTS):
    game = FakeGameStore(state or w.game_state((w.TAVERN,), "eins", "zwei", "drei", "vier"))
    images = store or FakeImageStore()
    ids = iter(sid(f"image-{n}") for n in range(1, 50))
    return (
        RequestSceneImage(
            LoadGame(game, game),
            images,
            defaults,
            new_id=lambda: next(ids),
            new_seed=lambda: 1234,
            now=lambda: NOW,
            active_window=timedelta(minutes=15),
        ),
        images,
    )


def request(options=SceneImageOptions(), initiator=INITIATOR):
    return RequestSceneImageRequest(RUN_ID, initiator, options)


def accepted(operation, **kwargs):
    result = operation.apply(request(**kwargs))
    assert isinstance(result, Success), result
    return result.data


def generate_operation(
    store, writer=None, compactor=None, renderer=None, resolver=None
) -> GenerateSceneImage:
    catalog = FilePromptPackageCatalog(PROMPT_ROOT)
    return GenerateSceneImage(
        SceneImagePromptResolver(catalog),
        CompactImagePromptResolver(catalog),
        resolver or FixedConfigurationResolver(),
        writer or FakePromptWriter(),
        compactor or FakeCompactor(),
        renderer or FakeRenderer(),
        store,
        compact_prompt_max_words=5,
        now=lambda: NOW + timedelta(seconds=30),
    )


# --- RequestSceneImage -----------------------------------------------------


def test_a_request_stores_a_pending_image_for_the_latest_turn() -> None:
    operation, store = request_operation()

    requested = accepted(operation)

    assert requested.record.status is SceneImageStatus.PENDING
    assert requested.record.turn_sequence == 4
    assert requested.record.seed == 1234
    assert (requested.record.width, requested.record.height) == (1024, 1024)
    assert store.records[requested.record.image_id] == requested.record
    assert requested.job is not None and requested.job.record == requested.record


def test_the_job_carries_only_the_last_configured_turns() -> None:
    operation, _ = request_operation()

    job = accepted(operation).job

    assert [turn.narration for turn in job.turns] == ["zwei", "drei", "vier"]
    assert job.turns[0].player_input == "Eingabe 2"
    assert job.configuration == w.configuration()


def test_fewer_turns_than_the_window_use_what_exists() -> None:
    operation, _ = request_operation(w.game_state((w.TAVERN,), "eins"))

    assert len(accepted(operation).job.turns) == 1


def test_a_run_with_only_an_opening_uses_the_opening_at_sequence_zero() -> None:
    state = w.game_state((w.TAVERN,))
    state = replace(
        state,
        story=StoryState(
            initialization=StoryInitialization("Eine Taverne.", "Maren sitzt am Feuer.", NOW)
        ),
    )
    operation, _ = request_operation(state)

    requested = accepted(operation)

    assert requested.record.turn_sequence == 0
    assert requested.job.turns[0].narration == "Maren sitzt am Feuer."


def test_a_run_without_any_story_cannot_get_an_image() -> None:
    operation, store = request_operation(w.game_state((w.TAVERN,)))

    result = operation.apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is SceneImageErrorKind.NO_STORY
    assert store.records == {}


def test_defaults_resolve_model_and_refine_choices() -> None:
    operation, _ = request_operation(defaults=replace(DEFAULTS, refine=True))

    record = accepted(operation).record

    assert (record.model, record.refine, record.refine_model, record.refine_strength) == (
        "z-image-turbo",
        True,
        "juggernaut-xl-ragnarok",
        0.35,
    )


def test_caller_options_override_the_defaults() -> None:
    operation, _ = request_operation()

    record = accepted(
        operation, options=SceneImageOptions(model="other", refine=True, refine_strength=0.6)
    ).record

    assert (record.model, record.refine, record.refine_strength) == ("other", True, 0.6)


def test_a_refine_strength_outside_the_allowed_range_is_rejected() -> None:
    operation, store = request_operation()

    for strength in (0.05, 0.9):
        result = operation.apply(
            request(SceneImageOptions(refine=True, refine_strength=strength))
        )
        assert isinstance(result, Failure)
        assert result.error.kind is SceneImageErrorKind.INVALID_OPTIONS
    assert store.records == {}


def test_a_blank_model_choice_is_rejected() -> None:
    operation, _ = request_operation()

    result = operation.apply(request(SceneImageOptions(model="  ")))

    assert isinstance(result, Failure)
    assert result.error.kind is SceneImageErrorKind.INVALID_OPTIONS


def test_a_non_member_is_denied_before_anything_is_stored() -> None:
    operation, store = request_operation()

    result = operation.apply(request(initiator=OUTSIDER))

    assert isinstance(result, Failure)
    assert store.records == {}


def test_a_second_request_for_the_same_turn_reuses_the_running_image() -> None:
    operation, store = request_operation()
    first = accepted(operation)

    second = accepted(operation)

    assert second.record.image_id == first.record.image_id
    assert second.job is None
    assert len(store.records) == 1


def test_a_stale_pending_image_does_not_block_a_new_request() -> None:
    operation, store = request_operation()
    first = accepted(operation)
    store.records[first.record.image_id] = replace(
        first.record, created_at=NOW - timedelta(hours=2)
    )

    second = accepted(operation)

    assert second.record.image_id != first.record.image_id
    assert second.job is not None


def test_a_finished_image_does_not_block_a_new_request() -> None:
    operation, store = request_operation()
    first = accepted(operation)
    store.complete(first.record.image_id, SceneImageContent(b"x", "image/png"), NOW)

    assert accepted(operation).job is not None


def test_a_store_failure_becomes_a_typed_failure() -> None:
    store = FakeImageStore()
    store.unavailable = True
    operation, _ = request_operation(store=store)

    result = operation.apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is SceneImageErrorKind.STORE_UNAVAILABLE


# --- GenerateSceneImage ----------------------------------------------------


def job_for(**option_overrides):
    operation, store = request_operation()
    options = SceneImageOptions(**option_overrides)
    requested = accepted(operation, options=options)
    return requested.job, store


def test_a_job_writes_the_prompt_renders_and_stores_the_image() -> None:
    job, store = job_for()
    renderer = FakeRenderer()
    resolver = FixedConfigurationResolver()
    writer = FakePromptWriter()

    result = generate_operation(store, writer=writer, renderer=renderer, resolver=resolver).apply(
        job
    )

    assert isinstance(result, Success)
    image_id = job.record.image_id
    assert store.records[image_id].status is SceneImageStatus.READY
    assert store.contents[image_id] == SceneImageContent(b"png-bytes", "image/png")
    assert store.saved_prompts[image_id] == ("A tavern at night, warm fire.", None)
    assert resolver.tasks == [GenerationTask.SCENE_IMAGE]
    assert [turn.narration for turn in writer.call.request.turns] == ["zwei", "drei", "vier"]
    assert writer.call.request.language == "de"
    assert renderer.request.prompt == "A tavern at night, warm fire."
    assert (renderer.request.seed, renderer.request.width, renderer.request.height) == (
        1234,
        1024,
        1024,
    )
    assert renderer.request.model == "z-image-turbo"
    assert renderer.request.refinement is None


def test_the_prompt_writer_receives_the_scene_image_instructions() -> None:
    job, store = job_for()
    writer = FakePromptWriter()

    generate_operation(store, writer=writer).apply(job)

    system_prompt = "\n".join(writer.call.request.system_prompts)
    assert "Bildgenerierungsmodell" in system_prompt


def test_refine_adds_a_compact_prompt_and_a_refinement_to_the_render() -> None:
    job, store = job_for(refine=True, refine_strength=0.5)
    compactor = FakeCompactor(
        Success(SceneImagePromptText("one two three four five six seven"))
    )
    renderer = FakeRenderer()

    result = generate_operation(store, compactor=compactor, renderer=renderer).apply(job)

    assert isinstance(result, Success)
    assert compactor.call.request.prompt == "A tavern at night, warm fire."
    assert compactor.call.request.max_words == 5
    assert store.saved_prompts[job.record.image_id][1] == "one two three four five"
    refinement = renderer.request.refinement
    assert (refinement.prompt, refinement.model, refinement.strength) == (
        "one two three four five",
        "juggernaut-xl-ragnarok",
        0.5,
    )


def test_no_compact_call_without_refine() -> None:
    job, store = job_for()
    compactor = FakeCompactor()

    generate_operation(store, compactor=compactor).apply(job)

    assert compactor.call is None


def test_a_prompt_failure_is_recorded_and_nothing_is_rendered() -> None:
    job, store = job_for()
    writer = FakePromptWriter(Failure(LLMError(LLMErrorKind.TIMEOUT, "zu langsam")))
    renderer = FakeRenderer()

    result = generate_operation(store, writer=writer, renderer=renderer).apply(job)

    assert isinstance(result, Failure)
    assert result.error.kind is SceneImageErrorKind.PROMPT_FAILED
    record = store.records[job.record.image_id]
    assert record.status is SceneImageStatus.FAILED
    assert "zu langsam" in record.error_message
    assert renderer.calls == 0


def test_a_compact_prompt_failure_is_recorded_and_nothing_is_rendered() -> None:
    job, store = job_for(refine=True)
    compactor = FakeCompactor(Failure(LLMError(LLMErrorKind.UNAVAILABLE, "offline")))
    renderer = FakeRenderer()

    result = generate_operation(store, compactor=compactor, renderer=renderer).apply(job)

    assert isinstance(result, Failure)
    assert result.error.kind is SceneImageErrorKind.PROMPT_FAILED
    assert store.records[job.record.image_id].status is SceneImageStatus.FAILED
    assert renderer.calls == 0


def test_a_render_failure_keeps_the_prompt_and_records_the_failure() -> None:
    job, store = job_for()
    renderer = FakeRenderer(
        Failure(ImageGenError(ImageGenErrorKind.AUTHENTICATION, "Token abgelehnt"))
    )

    result = generate_operation(store, renderer=renderer).apply(job)

    assert isinstance(result, Failure)
    assert result.error.kind is SceneImageErrorKind.RENDER_FAILED
    record = store.records[job.record.image_id]
    assert record.status is SceneImageStatus.FAILED
    assert record.prompt == "A tavern at night, warm fire."
    assert "Token abgelehnt" in record.error_message
    assert job.record.image_id not in store.contents


def test_a_missing_prompt_task_is_a_recorded_configuration_failure(tmp_path) -> None:
    job, store = job_for()
    catalog = FilePromptPackageCatalog(tmp_path)
    operation = GenerateSceneImage(
        SceneImagePromptResolver(catalog),
        CompactImagePromptResolver(catalog),
        FixedConfigurationResolver(),
        FakePromptWriter(),
        FakeCompactor(),
        FakeRenderer(),
        store,
        compact_prompt_max_words=5,
        now=lambda: NOW,
    )

    result = operation.apply(job)

    assert isinstance(result, Failure)
    assert result.error.kind is SceneImageErrorKind.CONFIGURATION
    assert store.records[job.record.image_id].status is SceneImageStatus.FAILED


# --- reads -----------------------------------------------------------------


def finished_image():
    job, store = job_for()
    generate_operation(store).apply(job)
    return job.record.image_id, store


def test_a_member_can_list_load_and_download_an_image() -> None:
    image_id, store = finished_image()

    listed = ListSceneImages(store).apply(ListSceneImagesRequest(RUN_ID, INITIATOR))
    loaded = LoadSceneImage(store).apply(LoadSceneImageRequest(RUN_ID, image_id, INITIATOR))
    content = LoadSceneImageContent(store).apply(
        LoadSceneImageContentRequest(RUN_ID, image_id, INITIATOR)
    )

    assert [record.image_id for record in listed.data] == [image_id]
    assert loaded.data.status is SceneImageStatus.READY
    assert content.data == SceneImageContent(b"png-bytes", "image/png")


def test_an_outsider_and_a_missing_image_look_the_same() -> None:
    image_id, store = finished_image()

    outsider = LoadSceneImage(store).apply(LoadSceneImageRequest(RUN_ID, image_id, OUTSIDER))
    missing = LoadSceneImage(store).apply(
        LoadSceneImageRequest(RUN_ID, sid("nope"), INITIATOR)
    )
    outsider_content = LoadSceneImageContent(store).apply(
        LoadSceneImageContentRequest(RUN_ID, image_id, OUTSIDER)
    )

    assert outsider == missing
    assert outsider.error.kind is SceneImageErrorKind.NOT_FOUND
    assert outsider_content.error.kind is SceneImageErrorKind.NOT_FOUND


def test_content_of_a_pending_image_is_not_found() -> None:
    operation, store = request_operation()
    record = accepted(operation).record

    result = LoadSceneImageContent(store).apply(
        LoadSceneImageContentRequest(RUN_ID, record.image_id, INITIATOR)
    )

    assert isinstance(result, Failure)
    assert result.error.kind is SceneImageErrorKind.NOT_FOUND


def test_capabilities_list_the_provider_models_and_defaults() -> None:
    result = ReadSceneImageCapabilities(DEFAULTS, FakeRenderer()).apply(
        ReadSceneImageCapabilitiesRequest()
    )

    capabilities = result.data
    assert capabilities.enabled is True
    assert capabilities.defaults == DEFAULTS
    assert [model.name for model in capabilities.models] == ["z-image-turbo"]
    assert [model.name for model in capabilities.refine_models] == ["juggernaut-xl-ragnarok"]
    assert capabilities.model_listing_failed is False


def test_capabilities_survive_an_unreachable_provider() -> None:
    renderer = FakeRenderer(
        models=Failure(ImageGenError(ImageGenErrorKind.UNAVAILABLE, "offline"))
    )

    capabilities = ReadSceneImageCapabilities(DEFAULTS, renderer).apply(
        ReadSceneImageCapabilitiesRequest()
    ).data

    assert capabilities.enabled is True
    assert capabilities.models == ()
    assert capabilities.model_listing_failed is True

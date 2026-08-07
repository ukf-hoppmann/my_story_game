"""Small deterministic-enough request used only by the LM Studio live smoke test."""

from story_game.application import GenerationOptions, LLMGenerationCall, ModelSelection
from story_game.application.llm import StoryGenerationRequest


def smoke_call(model_id: str) -> LLMGenerationCall[StoryGenerationRequest]:
    return LLMGenerationCall(
        model_selection=ModelSelection("lmstudio", model_id),
        generation_options=GenerationOptions(temperature=0.0, max_output_tokens=24),
        request=StoryGenerationRequest(
            system_prompts=(
                "Du bist ein technischer Smoke-Test.",
                "Antworte exakt mit LMSTUDIO_SMOKE_OK und keinem anderen Inhalt.",
            ),
            configuration="Sprache: Deutsch; Testmodus: provider boundary",
            world_state="Keine Spielwelt; dies ist nur ein Verbindungstest.",
            story_state="Keine bisherige Erzählung.",
            user_prompt="Gib jetzt den Marker LMSTUDIO_SMOKE_OK aus.",
        ),
    )

"""HTTP routers exposed by the story-game API."""

from fastapi import APIRouter

from .admin_prompts import router as admin_prompts_router
from .diagnostics import router as diagnostics_router
from .prompt_profile import router as prompt_profile_router
from .runs import router as runs_router
from .scene_images import router as scene_images_router

router = APIRouter()
router.include_router(runs_router)
router.include_router(prompt_profile_router)
router.include_router(diagnostics_router)
router.include_router(scene_images_router)
router.include_router(admin_prompts_router)

__all__ = ["router"]

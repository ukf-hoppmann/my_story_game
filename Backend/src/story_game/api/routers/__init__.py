"""HTTP routers exposed by the story-game API."""

from fastapi import APIRouter

from .prompt_profile import router as prompt_profile_router
from .runs import router as runs_router

router = APIRouter()
router.include_router(runs_router)
router.include_router(prompt_profile_router)

__all__ = ["router"]

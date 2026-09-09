"""Transport shapes for the read-only prompt-profile catalog."""

from __future__ import annotations

from pydantic import Field

from .common import APIModel


class PromptOptionModel(APIModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class PromptCategoryModel(APIModel):
    id: str = Field(min_length=1)
    default_option_id: str = Field(min_length=1)
    options: list[PromptOptionModel] = Field(default_factory=list)


class PromptPackageCatalogModel(APIModel):
    """Every category the referenced prompt package defines.

    Includes ``control_mode`` and ``extraction`` for completeness, even
    though callers set ``control_mode`` through a dedicated field
    (``ProposeRunRequestModel.control_mode``) rather than as part of an
    editable prompt profile — see ``EditablePromptProfileModel``.
    """

    package_id: str = Field(min_length=1)
    package_version: str = Field(min_length=1)
    categories: list[PromptCategoryModel] = Field(default_factory=list)

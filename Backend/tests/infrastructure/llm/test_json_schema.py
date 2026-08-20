from __future__ import annotations

from pydantic import BaseModel

from story_game.infrastructure.llm.json_schema import strict_json_schema


class _Nested(BaseModel):
    """Mirrors the real wire models: a field with a default is left out of

    Pydantic's own ``required`` by default.
    """

    name: str
    description: str = ""


class _Model(BaseModel):
    label: str
    subject_ref: str | None = None
    nested: list[_Nested]


def test_pydantic_omits_defaulted_fields_from_required_by_default() -> None:
    """Characterizes the bug this module exists to work around."""

    schema = _Model.model_json_schema()

    assert "subject_ref" not in schema["required"]
    assert "description" not in schema["$defs"]["_Nested"]["required"]


def test_strict_json_schema_requires_every_property_at_the_top_level() -> None:
    schema = strict_json_schema(_Model)

    assert set(schema["required"]) == set(schema["properties"])
    assert "subject_ref" in schema["required"]


def test_strict_json_schema_requires_every_property_in_nested_defs() -> None:
    schema = strict_json_schema(_Model)

    nested = schema["$defs"]["_Nested"]
    assert set(nested["required"]) == set(nested["properties"])
    assert "description" in nested["required"]


def test_strict_json_schema_never_changes_field_types() -> None:
    """Only `required` changes — a field's declared (nullable) type,

    i.e. whether the model may still omit a value, is untouched.
    """
    before = _Model.model_json_schema()
    after = strict_json_schema(_Model)

    assert after["properties"] == before["properties"]
    assert (
        after["$defs"]["_Nested"]["properties"]
        == before["$defs"]["_Nested"]["properties"]
    )

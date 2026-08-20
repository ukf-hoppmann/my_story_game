"""Make Pydantic's generated JSON Schema actually strict-mode compliant.

Shared across provider packages (``lmstudio/``, ``groq/``) deliberately: this
is a correctness rule about Pydantic-generated JSON Schema, not a
provider-specific behavior, so it belongs in one place rather than being
duplicated per provider.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return ``model.model_json_schema()`` with every property required.

    Pydantic omits a field with a default value (e.g. ``subject_ref: str |
    None = None``, ``description: str = ""``) from ``required``. OpenAI- and
    Groq-compatible strict JSON Schema (``response_format.json_schema.strict
    = True``) rejects that: every key listed in ``properties`` MUST also
    appear in ``required``; optionality is expressed through the field's type
    (e.g. a nullable union), never through omission from ``required``. A
    local LM Studio model happens to accept the incomplete schema anyway, but
    Groq's stricter validator does not, surfacing as a 400
    ``invalid_request_error`` on ``response_format``.

    Only ``required`` is changed; every field's type (including nullability)
    is left untouched, so a field that was already optional stays optional
    from the model's point of view.
    """
    schema = model.model_json_schema()
    for definition in (schema, *schema.get("$defs", {}).values()):
        if "properties" in definition:
            definition["required"] = list(definition["properties"])
    return schema


__all__ = ["strict_json_schema"]

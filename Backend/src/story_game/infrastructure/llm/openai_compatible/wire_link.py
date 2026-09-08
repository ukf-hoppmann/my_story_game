"""Shared wire-level normalization for candidate relation links.

The Domain restricts ``quantity`` to possession and container relations
(see ``story_game.domain.world.RelationLink``). A structured-output model
still has to emit *some* value for every field of a strict JSON schema, and
in practice it sometimes fills ``quantity`` for other relation kinds (e.g.
``located_in``) instead of leaving it null. Rejecting the whole extraction
for that alone would be a wire-level implementation detail leaking into a
Domain rejection, so the adapter drops the value here instead and logs it,
keeping the drop visible for later prompt tuning without failing the call.
"""

from __future__ import annotations

import structlog

_logger = structlog.get_logger("story_game.openai_compatible")

_QUANTITY_ALLOWED_KINDS = frozenset({"possesses", "contains"})


def normalize_link_quantity(
    kind: str, quantity: int | None, source_ref: str, target_ref: str
) -> int | None:
    """Return ``quantity`` unchanged, or drop it for a non-possession link.

    Logs ``openai_compatible.link_quantity_dropped`` whenever a value is
    actually dropped, so recurring drops remain visible for prompt tuning.
    """

    if quantity is None or kind in _QUANTITY_ALLOWED_KINDS:
        return quantity
    _logger.warning(
        "openai_compatible.link_quantity_dropped",
        kind=kind,
        source_ref=source_ref,
        target_ref=target_ref,
        quantity=quantity,
    )
    return None


__all__ = ["normalize_link_quantity"]

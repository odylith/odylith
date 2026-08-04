"""Release-scope limit extraction for greenfield proof boundaries."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_text import clean_text


_SCOPE_LIMIT_MARKERS = ("without claiming ", "without including ")


def proof_boundary_limit_text(value: str) -> str:
    """Return a short deferred-scope row implied by a proof-boundary limit."""

    text = clean_text(value).strip(" .")
    if not text:
        return ""
    for marker in _SCOPE_LIMIT_MARKERS:
        scope = _tail_after_marker(text, marker)
        if scope:
            return f"No {scope}"
    return ""


def strip_release_scope_limit_text(value: str) -> str:
    """Keep the positive result while deferred scope remains separately owned."""

    text = clean_text(value).strip(" .")
    marker_indexes = [text.casefold().find(marker) for marker in _SCOPE_LIMIT_MARKERS]
    marker_indexes = [index for index in marker_indexes if index >= 0]
    if not marker_indexes:
        return text
    return text[: min(marker_indexes)].strip(" .,:;")


def _tail_after_marker(value: str, marker: str) -> str:
    index = value.casefold().find(marker)
    if index < 0:
        return ""
    tail = value[index + len(marker) :].strip(" .,:;")
    for boundary in (".", ";"):
        boundary_index = tail.find(boundary)
        if boundary_index >= 0:
            tail = tail[:boundary_index].strip(" .,:;")
    return tail


__all__ = ["proof_boundary_limit_text", "strip_release_scope_limit_text"]

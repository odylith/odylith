"""Release-scope limit extraction for greenfield proof boundaries."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_text import clean_text


def proof_boundary_limit_text(value: str) -> str:
    """Return a short deferred-scope row implied by a proof-boundary limit."""

    text = clean_text(value).strip(" .")
    if not text:
        return ""
    for marker in ("without claiming ", "without including "):
        scope = _tail_after_marker(text, marker)
        if scope:
            return f"No {scope}"
    return ""


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


__all__ = ["proof_boundary_limit_text"]

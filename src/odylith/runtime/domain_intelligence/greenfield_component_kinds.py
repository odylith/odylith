"""Component kind classification for confirmed greenfield systems."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_text import visible_words


def system_kind(name: str, description: str, *, external_systems: list[str] | None = None) -> str:
    name_text = name.casefold()
    description_text = description.casefold()
    if _contains_kind_token(f"{name_text} {description_text}", ("web", "ui", "surface", "mobile", "portal", "client", "dashboard")):
        return "client"
    if (
        _contains_kind_token(name_text, ("adapter", "provider", "integration", "connector", "import"))
        or _contains_kind_token(description_text, ("adapter", "provider", "integration", "connector", "external", "import"))
        or _evidence_boundary_needs_adapter(name_text, external_systems or [])
    ):
        return "adapter"
    return "service"


def _evidence_boundary_needs_adapter(name_text: str, external_systems: list[str]) -> bool:
    name_terms = set(visible_words(name_text))
    external_terms = set(visible_words(" ".join(external_systems)))
    return bool(name_terms & {"attachment", "attachments", "provenance"}) and bool(
        external_terms & {"feed", "portal", "provider", "repository", "source", "storage", "system"}
    )


def _contains_kind_token(text: str, tokens: tuple[str, ...]) -> bool:
    words = [word.casefold() for word in visible_words(text)]
    for token in tokens:
        normalized = token.casefold()
        if normalized in {"ui", "web"}:
            if normalized in words:
                return True
            continue
        if any(word == normalized or word == f"{normalized}s" for word in words):
            return True
    return False


__all__ = ["system_kind"]

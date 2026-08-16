"""Low-level text derivation for source-owned Greenfield proof boundaries."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


_PROOF_RANKING_WRAPPER_RE = re.compile(
    r"^(?:a\s+close\s+second\s+is|the\s+first\s+thing\s+(?:the\s+)?product\s+must\s+prove\s+is)"
    r"\s+(?:that\s+)?",
    flags=re.IGNORECASE,
)
_PROOF_CLAIM_INTRO_PATTERNS = (
    r"^(?:the\s+)?first\s+version\s+is\s+proven\s+when\s+",
    r"^(?:the\s+)?product\s+is\s+proven\s+when\s+",
    r"^(?:release\s+[0-9.]+\s+)?(?:(?:is\s+)?(?:proven|trusted)|succeeds|works)\s+when\s+",
    r"^(?:the\s+)?proof\s+boundary\s+(?:is|means)\s*:?\s*",
    r"^(?:the\s+)?first\s+thing\s+(?:the\s+)?product\s+must\s+prove\s+(?:is\s+)?(?:that\s+)?",
    r"^(?:the\s+)?first\s+complete\s+path\s+(?:the\s+)?product\s+must\s+prove\s+(?:is\s+)?(?:that\s+)?",
    r"^(?:the\s+)?first\s+release\s+must\s+prove\s+(?:that\s+)?",
)


def derived_proof_boundary_text(value: str) -> str:
    """Remove sentence-local ranking discourse without dropping proof claims."""

    sentences = re.split(r"(?<=[.!?])\s+", _compact(value))
    derived: list[str] = []
    for sentence in sentences:
        normalized = _PROOF_RANKING_WRAPPER_RE.sub("", sentence, count=1).strip()
        if not normalized:
            continue
        if normalized != sentence:
            normalized = f"{normalized[:1].upper()}{normalized[1:]}"
        derived.append(normalized)
    return " ".join(derived)


def strip_proof_claim_intro(value: str) -> str:
    """Remove a primary proof-intro wrapper while retaining its semantic claim."""

    text = _compact(value).strip(" .")
    previous = ""
    while text and text != previous:
        previous = text
        for pattern in _PROOF_CLAIM_INTRO_PATTERNS:
            text = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip(" .")
    return text


def _compact(value: str) -> str:
    return " ".join(clean_markdown_text(value).split()).strip()


__all__ = ["derived_proof_boundary_text", "strip_proof_claim_intro"]

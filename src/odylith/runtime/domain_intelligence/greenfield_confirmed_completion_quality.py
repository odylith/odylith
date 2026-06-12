"""Text quality checks for confirmed greenfield completion repairs."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.generated_copy_quality import has_inline_role_casing_drift
from odylith.runtime.domain_intelligence.greenfield_component_contract import public_prose_quality_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_text import text_values


def validation_strategy_needs_repair(proposal: dict[str, Any]) -> bool:
    return sequence_needs_repair(
        proposal.get("validation_strategy"),
        required_tokens=("success", "block", "replay", "access", "privacy", "evidence"),
        min_items=6,
    )


def sequence_needs_repair(value: Any, *, required_tokens: Sequence[str], min_items: int = 2) -> bool:
    values = text_values(value)
    if len(values) < min_items:
        return True
    joined = " ".join(values).casefold()
    if any(token not in joined for token in required_tokens):
        return True
    return any(text_needs_repair(item) for item in values)


def sequence_has_text_repair(value: Any) -> bool:
    return any(text_needs_repair(item) for item in text_values(value))


def text_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return False
    if public_prose_quality_issues(text):
        return True
    if generated_public_copy_issues("confirmed completion text", text):
        return True
    if has_inline_role_casing_drift(text):
        return True
    if sentence_needs_repair(text):
        return True
    lowered = text.casefold()
    if re.search(
        r"\bcan\s+(?:[a-z][a-z0-9'-]*\s+){0,4}"
        r"(?:adds|asks|chooses|clicks|creates|describes|enters|logs|opens|places|records|reviews|runs|saves|selects|signs|submits|views)\b",
        lowered,
    ):
        return True
    if re.search(
        r"\b(?:accepts?|produces?|blocks?|proves?|coverage\s+for)\s+"
        r"(?:recomputes|computes?|calculates?|generates?|derives?|exports?|deletes?|records?|tracks?|validates?)\s+"
        r"[^.]{0,120}\b(?:input|result|output|state)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    return any(
        marker in lowered
        for marker in (
            "responsibility and keeps it tied",
            "with clear ownership, protected access, required",
            "accepted path lets users",
            "accepted first path proves",
            "accepted first path can be exercised",
            "accepted proof boundary",
            "a close second is",
            "keeps the accepted path step reviewable",
            "proves one successful local state transition",
            "leaves reviewable proof for actor",
            "visible-result event",
            "rendered dashboard",
            "dashboard renders the visible result",
            "readout plus",
            "on save,",
            "source evidence, visible blockers",
            "source evidence, release decision",
            "systems that own the handoff",
            "is not trustworthy when",
            "first release can collect activity",
            "from the product view,",
            "from the usage-linked",
            "using the usage-linked",
            " is useful when ",
            " is done when ",
        )
    )


def sentence_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return True
    if has_bad_tail(text):
        return True
    if re.search(r"\.\s+(?:and|or)\b", text, flags=re.IGNORECASE):
        return True
    if re.search(
        r"\b(?:inspect\s+The|verifies\s+that\s+The|shows\s+whether\s+The|Human\s+actors\s*:|plus\s+\d+\s+more|preserves\s+handles|maintains\s+defines|accepting\s+eligible)",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    if re.search(r"\bunderstand\s+[A-Z]", text):
        return True
    if re.search(r"\bneed\s+[A-Z]?[A-Za-z0-9][^.;]{0,120}\s+to\s+turn\b", text):
        return True
    if re.search(
        r"\bcomplete\s+(?:selects?|records?|saves?|creates?|opens?|logs?|fetches?|calculates?)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    if re.search(r"\baccepts\s+required\s+[^.]{0,180}\bcommand\b", text, flags=re.IGNORECASE):
        return True
    if re.search(r"\bproduce\s+validated\s+[^.]{0,180}\bblocker\s+signal\b", text, flags=re.IGNORECASE):
        return True
    if re.search(r"\brefuses\b[^.]{0,140}\brefuses\b", text, flags=re.IGNORECASE):
        return True
    if re.search(r"\bscor\b", text, flags=re.IGNORECASE):
        return True
    if re.search(r"(?:^|[.;]\s+)without it[.!?]?$", text, flags=re.IGNORECASE):
        return True
    return False


def proof_boundary_is_weak(value: str) -> bool:
    text = _clean(value).casefold()
    if len(text.split()) < 14:
        return True
    return not ("success" in text or "succeeds" in text or "proof" in text or "proven" in text) or not (
        "evidence" in text
        or "trace" in text
        or "review" in text
        or "visible" in text
        or "receive" in text
        or "result" in text
        or "readout" in text
        or "actionable" in text
    )


def has_bad_tail(value: str) -> bool:
    words = _clean(value).rstrip(".;:, ").split()
    if len(words) < 6:
        return False
    return words[-1].casefold().strip(".,;:") in {
        "a",
        "an",
        "and",
        "for",
        "from",
        "if",
        "of",
        "or",
        "required",
        "the",
        "to",
        "when",
        "while",
        "with",
        "without",
    }

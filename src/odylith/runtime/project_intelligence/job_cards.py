"""Product-facing job card summaries for greenfield Project pages."""

from __future__ import annotations

import re

from odylith.runtime.project_intelligence.utils import sentence
from odylith.runtime.project_intelligence.utils import tidy_fragment


def job_card_summary(value: str) -> str:
    """Compress generated workstream prose into a readable product responsibility."""

    text = sentence(value).strip()
    if not text:
        return ""
    ownership = re.match(r"^[A-Z][A-Za-z0-9 /&'()-]{2,90}?\s+owns\s+(.+)$", text)
    if ownership:
        return f"Owns {ownership.group(1).strip(' .')}."
    useful = re.search(
        r"^.+?\s+is\s+useful\s+when\s+(?:a\s+)?user\s+can\s+(.+?)\s+and\s+leave\s+with\s+(.+?)(?:\.|$)",
        text,
        flags=re.IGNORECASE,
    )
    if useful:
        action = _job_action_phrase(useful.group(1))
        outcome = _job_outcome_phrase(useful.group(2))
        return f"Helps the user {action} and leaves them with {outcome}."
    complete = re.search(
        r"^.+?\s+(?:is\s+complete|should\s+feel\s+complete|is\s+done)\s+when\s+(?:the\s+)?(?:user|participant|customer|actor)\s+can\s+(.+?)(?:,\s+|\s+and\s+)(?:understand|see|reach|receive|review)\s+(.+?)(?:\.|$)",
        text,
        flags=re.IGNORECASE,
    )
    if complete:
        action = _job_action_phrase(complete.group(1))
        outcome = _job_outcome_phrase(complete.group(2))
        return f"Helps the user {action} and understand {outcome}."
    matters = re.search(
        r"^.+?\s+matters\s+because\s+users\s+do\s+not\s+get\s+value\s+from\s+(.+?)\s+until\s+it\s+produces\s+(.+?)(?:\.|$)",
        text,
        flags=re.IGNORECASE,
    )
    if matters:
        action = _job_action_phrase(matters.group(1))
        outcome = _job_outcome_phrase(matters.group(2))
        return f"Focuses the slice on {action} producing {outcome}."
    return text


def low_information_job_body(value: str) -> bool:
    text = sentence(value).strip()
    lowered = text.casefold()
    if lowered.startswith("owns ") and len(text.split()) >= 5:
        return False
    if len(text.split()) < 7:
        return True
    return bool(
        re.fullmatch(r".+\s+is\s+useful\.?", lowered)
        or re.fullmatch(r".+\s+is\s+useful\s+when\b.*", lowered)
        or re.fullmatch(r".+\s+is\s+done\.?", lowered)
        or re.search(r"\bfrom\s+the\s+product\s+view,\s+[a-z0-9_-]+\s+is\s+done\b", lowered)
    )


def job_status_label(value: object) -> str:
    text = sentence(value, "proposal").replace("_", " ").strip().casefold()
    labels = {
        "user intent": "User intent",
        "odylith assumption": "Inferred",
        "assumption": "Inferred",
        "inferred": "Inferred",
        "proposal": "Proposed",
        "proposed": "Proposed",
        "source backed": "Source-backed",
        "source-backed": "Source-backed",
        "accepted": "Accepted",
        "accepted greenfield project": "Accepted",
    }
    return labels.get(text, "Planned")


def _job_action_phrase(value: str) -> str:
    text = sentence(value).strip(" .")
    text = re.sub(
        r"^(?:a|an|the)\s+(?:user|owner|person|actor|customer|applicant|participant|operator)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    replacements = {
        "adds": "add",
        "logs": "log",
        "enters": "enter",
        "selects": "select",
        "submits": "submit",
        "saves": "save",
        "chooses": "choose",
        "clicks": "click",
        "accepts": "accept",
        "dismisses": "dismiss",
        "records": "record",
        "captures": "capture",
        "reviews": "review",
    }
    first, sep, tail = text.partition(" ")
    replacement = replacements.get(first.casefold().strip(".,;:"))
    if replacement:
        text = f"{replacement}{sep}{tail}".strip()
    for inflected, base in replacements.items():
        text = re.sub(rf"\b(and|then)\s+{re.escape(inflected)}\b", rf"\1 {base}", text, flags=re.IGNORECASE)
        text = re.sub(
            rf"\b(and|then)\s+manually\s+{re.escape(inflected)}\b",
            rf"\1 manually {base}",
            text,
            flags=re.IGNORECASE,
        )
    text = re.sub(
        r",\s+and\s+(manually\s+)?(log|enter|select|submit|save|choose|click|accept|dismiss|record|capture|review)\b",
        r" and \1\2",
        text,
        flags=re.IGNORECASE,
    )
    return tidy_fragment(text) or "complete the first product action"


def _job_outcome_phrase(value: str) -> str:
    text = sentence(value).strip(" .")
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.IGNORECASE)
    return tidy_fragment(text) or "the first visible outcome"


__all__ = ["job_card_summary", "job_status_label", "low_information_job_body"]

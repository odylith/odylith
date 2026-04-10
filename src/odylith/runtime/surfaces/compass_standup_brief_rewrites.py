"""Targeted plain-language rewrites for deterministic Compass briefs."""

from __future__ import annotations

import re


_WORKSTREAM_ID_RE = re.compile(r"`?(B-\d+)`?")


def _clean_text(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s+", "(", cleaned)
    cleaned = re.sub(r"\s+\)", ")", cleaned)
    return cleaned


def _sentence(text: str) -> str:
    cleaned = _clean_text(text).rstrip()
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned[:1].upper() + cleaned[1:]


def rewrite_verified_completion(text: str) -> str:
    match = re.match(r"Verified (?P<thing>.+?) landed for (?P<target>.+)$", _clean_text(text), re.IGNORECASE)
    if match is None:
        return _clean_text(text)
    thing = _clean_text(str(match.group("thing")).strip()).rstrip(".")
    target = _clean_text(str(match.group("target")).strip()).rstrip(".")
    return f"{target} {thing} landed."


def rewrite_live_narration_direction(text: str) -> str | None:
    if text.lower().startswith("compass is being steered around ai-first standup narration"):
        return "AI-first standup narration still needs care. If this drifts, Compass starts sounding like a dashboard again."
    return None


def rewrite_window_coverage(text: str) -> str | None:
    cleaned = _clean_text(text)
    if not cleaned.startswith("Work moved across ") or ":" not in cleaned:
        return None
    tail = cleaned.split(":", 1)[1].strip().rstrip(".")
    ids = [match.group(1) for match in _WORKSTREAM_ID_RE.finditer(tail)]
    if not ids:
        return f"Most of the work here was in {tail}."
    refs = [f"`{workstream_id}`" for workstream_id in ids]
    if len(refs) == 1:
        joined = refs[0]
    elif len(refs) == 2:
        joined = f"{refs[0]} and {refs[1]}"
    else:
        joined = f"{', '.join(refs[:-1])}, and {refs[-1]}"
    return f"Most of the work here was in {joined}."


def rewrite_next_detail(text: str) -> str | None:
    cleaned = _clean_text(text)
    if not cleaned.lower().startswith("land implement "):
        return None
    target = cleaned[len("land implement ") :].strip()
    if target.lower().startswith("compass "):
        target = f"Compass {target.split(' ', 1)[1]}"
    return f"land the {target} cleanly"


def rewrite_risk(text: str) -> str | None:
    cleaned = _clean_text(text)
    lower = cleaned.lower()
    if lower.startswith("no critical blockers") or lower.startswith("no hard blockers"):
        return "No hard blocker is surfaced right now."
    return None


def rewrite_fallback_text(*, section_key: str, text: str) -> str:
    cleaned = _clean_text(text)
    if section_key == "completed":
        return rewrite_verified_completion(cleaned)
    if section_key == "current_execution":
        for prefix in (
            "Primary execution signal:",
            "Current execution signal:",
            "Timeline signal:",
            "Freshness signal is stale:",
            "Freshness signal is aging:",
            "Plan posture:",
        ):
            if cleaned.lower().startswith(prefix.lower()):
                return _sentence(cleaned.split(":", 1)[1].strip() if ":" in cleaned else cleaned[len(prefix) :].strip())
    if section_key == "next_planned":
        if cleaned.lower().startswith("immediate forcing function is "):
            detail = cleaned[len("Immediate forcing function is ") :].strip().rstrip(".")
            return _sentence(rewrite_next_detail(detail) or detail)
        if cleaned.lower().startswith("then move "):
            return _sentence(cleaned[len("Then move ") :].strip())
    if section_key == "risks_to_watch":
        rewritten = rewrite_risk(cleaned)
        if rewritten is not None:
            return rewritten
        for prefix in ("Primary watch item is ", "Primary blocker is "):
            if cleaned.lower().startswith(prefix.lower()):
                return _sentence(cleaned[len(prefix) :].strip())
    return cleaned

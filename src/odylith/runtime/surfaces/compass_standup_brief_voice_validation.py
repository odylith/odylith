"""Voice-shape validation helpers for Compass standup briefs."""

from __future__ import annotations

import re
from typing import Mapping, Sequence


_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.`'’-]*")
_EXPLICIT_ANCHOR_RE = re.compile(r"(?:`?B-\d+`?|\b\d+\.\d+\.\d+\b)")
_BALANCED_CADENCE_RE = re.compile(r"(?:,\s*(?:so|which)\b|\bbecause\b)", re.IGNORECASE)
_STAGEY_METAPHOR_RE = re.compile(
    r"\b(?:live\s+pressure\s+point|pressure\s+point|center\s+of\s+gravity|less\s+muddy(?:\s+now)?|muddy\s+now|slippery|top\s+lane|sharpest\s+live\s+issue|real\s+footing)\b",
    re.IGNORECASE,
)
_DASHBOARD_POLISH_RE = re.compile(
    r"\b(?:window\s+coverage\s+spans|with\s+the\s+clearest\s+movement\s+around|thing\s+under\s+active\s+implementation\s+now|the\s+pressure\s+here\s+is|the\s+next\s+move\s+is|a\s+lot\s+moved\s+in\s+this\s+window|most\s+of\s+the\s+movement\s+this\s+window\s+sat\s+in|most\s+of\s+the\s+work\s+here\s+was\s+in|a\s+lot\s+happened,\s+but\s+most\s+of\s+it\s+came\s+through|work\s+is\s+now\s+driving\s+through|there\s+is\s+a\s+live-version\s+split\s+to\s+keep\s+in\s+view|release\s+planning\s+and\s+execution\s+are\s+running\s+together|developer-core\s+local\s+coding\s+slices|local\s+developer-core\s+coding\s+slices|developer-core\s+coding\s+slices|next\s+is\s+pushing|next\s+step\s+is|that\s+push\s+needs\s+more|the\s+follow-on\s+adds|is\s+moving\s+with\s+it\s+too|are\s+still\s+moving\s+together|the\s+surrounding\s+work\s+is\s+still\s+attached\s+to\s+the\s+changes\s+underneath\s+it|already\s+proved\s+the\s+cost\s+of\s+local\s+heuristics|it\s+is\s+clearer\s+now\s+which\s+lanes\s+are\s+active\s+again|still\s+holds\s+up\s+across\s+the\s+48h\s+view)\b",
    re.IGNORECASE,
)
_CACHED_STOCK_PHRASE_RE = re.compile(
    r"\b(?:this\s+window\s+mostly\s+ran\s+through|"
    r"trying\s+to\s+stop\s+each\s+surface\s+from\s+guessing\s+scope\s+importance\s+on\s+its\s+own|"
    r"compass\s+already\s+showed\s+how\s+expensive\s+that\s+gets|"
    r"most\s+of\s+the\s+work\s+here\s+was\s+in|"
    r"are\s+still\s+moving\s+together|"
    r"next\s+stop\s+is\s+B-\d+|"
    r"paper-only\s+signal)\b",
    re.IGNORECASE,
)
_SHORT_TOKEN_ALLOWLIST = {"ai", "ci", "ga", "qa", "ui", "ux"}
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "before",
    "but",
    "by",
    "can",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "more",
    "most",
    "no",
    "not",
    "now",
    "of",
    "on",
    "or",
    "out",
    "so",
    "still",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "through",
    "to",
    "too",
    "until",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "why",
    "will",
    "with",
    "without",
}
_GENERIC_SUMMARY_TOKENS = {
    "attention",
    "baseline",
    "benchmark",
    "brief",
    "contract",
    "direction",
    "evidence",
    "execution",
    "focus",
    "implementation",
    "issue",
    "lane",
    "maintainer",
    "maintainers",
    "movement",
    "narrative",
    "operator",
    "operators",
    "portfolio",
    "posture",
    "priority",
    "progress",
    "proof",
    "release",
    "repo",
    "risk",
    "risks",
    "runtime",
    "scope",
    "shape",
    "signal",
    "signals",
    "status",
    "story",
    "surface",
    "surfaces",
    "trust",
    "window",
    "work",
}


def _normalized_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in _TOKEN_RE.findall(str(text or "")):
        token = raw_token.strip("`'\"“”‘’.,;:!?()[]{}").lower()
        if token:
            tokens.append(token)
    return tokens


def _meaningful_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in _normalized_tokens(text):
        if token in _STOPWORDS:
            continue
        if len(token) >= 3 or token in _SHORT_TOKEN_ALLOWLIST or _EXPLICIT_ANCHOR_RE.fullmatch(token):
            tokens.add(token)
    return tokens


def _generic_summary_token_count(text: str) -> int:
    return sum(1 for token in _normalized_tokens(text) if token in _GENERIC_SUMMARY_TOKENS)


def _fact_anchor_overlap(text: str, fact_texts: Sequence[str]) -> set[str]:
    bullet_tokens = _meaningful_tokens(text)
    if not bullet_tokens:
        return set()
    overlap: set[str] = set()
    for fact_text in fact_texts:
        overlap |= bullet_tokens & _meaningful_tokens(fact_text)
    return overlap


def bullet_shape_errors(
    *,
    section_key: str,
    bullet_index: int,
    text: str,
    fact_texts: Sequence[str],
) -> list[str]:
    errors: list[str] = []
    overlap = _fact_anchor_overlap(text, fact_texts)
    explicit_anchor = bool(_EXPLICIT_ANCHOR_RE.search(text))
    generic_count = _generic_summary_token_count(text)
    if fact_texts and not overlap and not explicit_anchor:
        errors.append(f"section {section_key} bullet {bullet_index} drifts away from the cited fact language")
    if _STAGEY_METAPHOR_RE.search(text):
        errors.append(
            f"section {section_key} bullet {bullet_index} leans on stagey metaphor instead of plainspoken maintainer language"
        )
    if _DASHBOARD_POLISH_RE.search(text):
        errors.append(
            f"section {section_key} bullet {bullet_index} slides back into dashboard-polished summary language"
        )
    if _CACHED_STOCK_PHRASE_RE.search(text):
        errors.append(
            f"section {section_key} bullet {bullet_index} reuses cached stock phrasing instead of plainspoken maintainer narration"
        )
    if _BALANCED_CADENCE_RE.search(text) and generic_count >= 3 and len(overlap) < 2:
        errors.append(f"section {section_key} bullet {bullet_index} falls into portable summary cadence")
    return errors


def contains_rejected_cached_phrase(text: str) -> bool:
    return bool(_CACHED_STOCK_PHRASE_RE.search(str(text or "")))


def brief_shape_errors(*, sections: Sequence[Mapping[str, object]]) -> list[str]:
    cadence_locations: list[str] = []
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        section_key = str(section.get("key", "")).strip() or "unknown"
        bullets = section.get("bullets")
        if not isinstance(bullets, Sequence):
            continue
        for bullet_index, bullet in enumerate(bullets, start=1):
            if not isinstance(bullet, Mapping):
                continue
            text = str(bullet.get("text", "")).strip()
            if not text:
                continue
            if _BALANCED_CADENCE_RE.search(text):
                cadence_locations.append(f"{section_key}:{bullet_index}")
    if len(cadence_locations) >= 6:
        locations = ", ".join(cadence_locations[:4])
        return [f"brief repeats polished claim-then-consequence cadence across too many bullets ({locations})"]
    return []

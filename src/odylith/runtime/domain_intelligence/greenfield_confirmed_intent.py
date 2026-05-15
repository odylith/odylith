"""Parse the small confirmed-intent artifact used by greenfield create."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


FIELD_MIN_WORDS = {
    "product_story": 28,
    "state_object": 12,
    "first_path": 18,
    "proof_boundary": 18,
}
LIST_ROW_MIN_WORDS = 5
SYSTEM_ROW_MIN_WORDS = 7

_META_NARRATION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bturn\s+the\s+.+?\s+intent\s+into\s+a\s+clear\s+product\s+narrative\b",
        r"\bmake\s+.+?\s+readable\s+as\s+one\s+product\s+story\b",
        r"\bbefore\s+source\s+work\s+starts\b",
        r"\bbefore\s+implementation\s+begins\b",
        r"\bgenerated\s+from\s+the\s+accepted\s+greenfield\b",
        r"\bworkflow\s+lead\b",
        r"\bproduct\s+promise\b",
        r"\brelease\s+claim\b",
        r"\bfixture-backed\s+inputs\b",
        r"\bdocumented\s+non-goals\b",
    )
]

_GENERIC_SYSTEM_NAME_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bworkflow\s+service\b",
        r"\bstate\s+store\b",
        r"\bevidence\s+review\b",
    )
]


def load_confirmed_intent_file(path: Path, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Load a host-visible Product Intent Confirmation from Markdown/text/JSON."""

    source = Path(path)
    if not source.is_file():
        raise ValueError(f"confirmed intent file was not found: {source}")
    text = source.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"confirmed intent file is empty: {source}")
    if source.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"confirmed intent JSON is invalid: {exc}") from exc
        return normalize_confirmed_intent(payload, prompt=prompt, fallback_title=fallback_title)
    return parse_confirmed_intent_text(text, prompt=prompt, fallback_title=fallback_title)


def normalize_confirmed_intent(value: object, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Normalize JSON or already parsed confirmation data into the builder contract."""

    if isinstance(value, str):
        return parse_confirmed_intent_text(value, prompt=prompt, fallback_title=fallback_title)
    if not isinstance(value, Mapping):
        raise ValueError("confirmed intent must be Markdown text or a JSON object")
    payload = dict(value)
    title = _clean(payload.get("title") or payload.get("product_title") or fallback_title)
    result: dict[str, Any] = {
        "title": title,
        "prompt": _clean(payload.get("prompt") or prompt),
        "product_story": _clean(payload.get("product_story") or payload.get("story")),
        "state_object": _clean(payload.get("state_object") or payload.get("state_object_first_journey")),
        "first_path": _clean(payload.get("first_path") or payload.get("first_workflow")),
        "proof_boundary": _clean(payload.get("proof_boundary")),
        "human_actors": _strings(payload.get("human_actors") or payload.get("actors")),
        "external_systems": _strings(payload.get("external_systems")),
        "internal_systems": _strings(payload.get("internal_systems") or payload.get("internal_product_systems")),
        "assumptions": _strings(payload.get("assumptions") or payload.get("critical_assumptions")),
        "ambiguities": _strings(payload.get("ambiguities") or payload.get("open_questions")),
        "non_goals": _strings(payload.get("non_goals")),
    }
    _validate_confirmed_intent(result)
    return result


def parse_confirmed_intent_text(text: str, *, prompt: str = "", fallback_title: str = "") -> dict[str, Any]:
    """Parse the human Product Intent Confirmation that the host already showed."""

    sections = _sections(text)
    title = _title_from_text(text) or fallback_title
    result: dict[str, Any] = {
        "title": _clean(title),
        "prompt": _clean(prompt),
        "product_story": _section_text(sections, "product_story"),
        "state_object": _section_text(sections, "state_object"),
        "first_path": _section_text(sections, "first_path"),
        "proof_boundary": _section_text(sections, "proof_boundary"),
        "human_actors": _section_list(sections, "human_actors"),
        "external_systems": _section_list(sections, "external_systems"),
        "internal_systems": _section_list(sections, "internal_systems"),
        "assumptions": _section_list(sections, "assumptions"),
        "ambiguities": _section_list(sections, "ambiguities"),
        "non_goals": _section_list(sections, "non_goals"),
    }
    _validate_confirmed_intent(result)
    return result


def confirmed_intent_summary(intent: Mapping[str, Any] | None, key: str, fallback: str) -> str:
    if not isinstance(intent, Mapping):
        return fallback
    value = _clean(intent.get(key))
    return value or fallback


def confirmed_intent_list(intent: Mapping[str, Any] | None, key: str) -> list[str]:
    if not isinstance(intent, Mapping):
        return []
    return _strings(intent.get(key))


def confirmed_system_name(value: str) -> str:
    raw = re.split(r"\s+[—-]\s+|\s*:\s*", _clean(value), maxsplit=1)[0].strip()
    return _clean(raw) or "Product System"


def confirmed_system_description(value: str) -> str:
    parts = re.split(r"\s+[—-]\s+|\s*:\s*", _clean(value), maxsplit=1)
    if len(parts) > 1:
        return _clean(parts[1])
    return _clean(value)


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "preamble"
    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        heading = _heading_key(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        if not line.strip() and current == "preamble":
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _heading_key(line: str) -> str:
    text = line.strip()
    if not text:
        return ""
    if text.startswith("#"):
        return _classify_heading(text.lstrip("#").strip())
    if text.endswith(":") and len(text.split()) <= 8:
        return _classify_heading(text[:-1].strip())
    return _classify_heading(text) if _looks_like_plain_heading(text) else ""


def _looks_like_plain_heading(text: str) -> bool:
    lowered = _normalize_heading(text)
    known = {
        "product story",
        "state object that changes through the first journey",
        "first complete path odylith should prove before broader scope",
        "human actors",
        "external systems",
        "external systems not owned by this product",
        "internal systems",
        "internal product systems",
        "assumptions",
        "critical assumptions",
        "ambiguities that would change the first path",
        "open questions",
        "proof boundary",
        "non goals",
        "non-goals",
    }
    return lowered in known


def _classify_heading(value: str) -> str:
    normalized = _normalize_heading(value)
    if not normalized:
        return ""
    if "product intent confirmation" in normalized:
        return "title"
    if "product story" in normalized:
        return "product_story"
    if "state object" in normalized:
        return "state_object"
    if "first complete path" in normalized or "first workflow" in normalized or "first path" in normalized:
        return "first_path"
    if "human actor" in normalized or normalized == "actors":
        return "human_actors"
    if "external system" in normalized:
        return "external_systems"
    if "internal product system" in normalized or "internal system" in normalized:
        return "internal_systems"
    if "critical assumption" in normalized or normalized == "assumptions":
        return "assumptions"
    if "ambiguities" in normalized or "open question" in normalized:
        return "ambiguities"
    if "proof boundary" in normalized:
        return "proof_boundary"
    if "non goal" in normalized or "non-goal" in normalized:
        return "non_goals"
    return ""


def _normalize_heading(value: str) -> str:
    text = re.sub(r"[*_`]+", "", str(value or "")).strip().casefold()
    text = re.sub(r"[–—-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_from_text(text: str) -> str:
    for raw_line in str(text or "").splitlines():
        line = _clean(raw_line.lstrip("#").strip())
        if not line:
            continue
        match = re.match(r"(.+?)\s+[—-]\s+Product Intent Confirmation$", line)
        if match:
            return _clean(match.group(1))
        if "product intent confirmation" in line.casefold():
            return _clean(re.sub(r"product intent confirmation", "", line, flags=re.IGNORECASE))
    return ""


def _section_text(sections: Mapping[str, list[str]], key: str) -> str:
    lines = sections.get(key, [])
    return _clean(" ".join(line.strip("-* \t") for line in lines if line.strip()))


def _section_list(sections: Mapping[str, list[str]], key: str) -> list[str]:
    values: list[str] = []
    for raw_line in sections.get(key, []):
        text = raw_line.strip()
        if not text:
            continue
        item = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", text).strip()
        if item:
            values.append(_clean(item))
    if values:
        return values
    paragraph = _section_text(sections, key)
    return [paragraph] if paragraph else []


def _validate_confirmed_intent(intent: Mapping[str, Any]) -> None:
    missing: list[str] = []
    for key, minimum in FIELD_MIN_WORDS.items():
        if _word_count(_clean(intent.get(key))) < minimum:
            missing.append(key)
    actor_rows = _strings(intent.get("human_actors"))
    if not actor_rows:
        missing.append("human_actors")
    elif any(_word_count(row) < LIST_ROW_MIN_WORDS for row in actor_rows):
        missing.append("human_actors")
    system_rows = _strings(intent.get("internal_systems"))
    if len(system_rows) < 2:
        missing.append("internal_systems")
    elif any(not _has_meaningful_system_description(row) for row in system_rows):
        missing.append("internal_systems")
    if _contains_meta_narration(intent):
        missing.append("product_narrative")
    if _contains_generic_system_scaffold(system_rows):
        missing.append("internal_systems")
    if missing:
        formatted = ", ".join(dict.fromkeys(missing))
        raise ValueError(
            "confirmed greenfield create needs the host-written Product Intent Confirmation; "
            f"missing or too thin: {formatted}. Write the visible confirmation to a Markdown file "
            "and pass it with --intent-file."
        )


def _has_meaningful_system_description(row: str) -> bool:
    name = confirmed_system_name(row)
    description = confirmed_system_description(row)
    if not name or name == description:
        return False
    return _word_count(description) >= SYSTEM_ROW_MIN_WORDS


def _contains_meta_narration(intent: Mapping[str, Any]) -> bool:
    text = " ".join(
        [
            _clean(intent.get("product_story")),
            _clean(intent.get("first_path")),
            _clean(intent.get("proof_boundary")),
            " ".join(_strings(intent.get("human_actors"))),
            " ".join(_strings(intent.get("internal_systems"))),
        ]
    )
    return any(pattern.search(text) for pattern in _META_NARRATION_PATTERNS)


def _contains_generic_system_scaffold(system_rows: list[str]) -> bool:
    names = [confirmed_system_name(row) for row in system_rows]
    if any(pattern.search(name) for name in names for pattern in _GENERIC_SYSTEM_NAME_PATTERNS):
        return True
    compact = " ".join(name.casefold() for name in names)
    return all(token in compact for token in ("workflow", "state", "evidence"))


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = _clean(value)
        return [cleaned] if cleaned else []
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return []
    return [_clean(item) for item in value if _clean(item)]


def _word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", value))


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


__all__ = [
    "confirmed_intent_list",
    "confirmed_intent_summary",
    "confirmed_system_description",
    "confirmed_system_name",
    "load_confirmed_intent_file",
    "normalize_confirmed_intent",
    "parse_confirmed_intent_text",
]

"""Source-backed summary helpers for Project intelligence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from odylith.runtime.project_intelligence.utils import humanize, short, strings


_STATUS_TAIL_PREFIXES = (
    "completed",
    "started",
    "finished",
    "blocked",
    "paused",
    "deferred",
    "accepted",
    "rejected",
    "validated",
)


def concise_text(value: object, *, limit: int = 150, fallback: str = "") -> str:
    """Return source text as clean project-facing prose without invented facts."""

    text = " ".join(str(value or "").strip().split())
    text = _drop_repeated_inline_sections(text)
    text = _trim_status_tail(text)
    text = _drop_vague_leadins(text)
    text = _normalize_compounds(text)
    text = text.strip(" :;,-")
    text = _complete_trailing_preposition(text)
    text = _sentence_case(text)
    return short(text, limit=limit, fallback=fallback)


def action_title(value: object, *, fallback: str = "Current next step") -> str:
    """Return a readable next-action label by rewriting noisy source titles."""

    text = concise_text(value, limit=120, fallback=fallback)
    text = re.sub(r"^(complex[- ]repo|source[- ]backed|current)\s+", "", text, flags=re.IGNORECASE)
    if " and " in text and len(text) > 42:
        text = text.split(" and ", 1)[0]
    return short(text, limit=70, fallback=fallback)


def action_sentence(value: object, *, fallback: str = "Advance the current source-backed next action.") -> str:
    """Return a concise sentence for a source action without clipping fragments."""

    text = concise_text(value, limit=260, fallback=fallback)
    match = re.match(r"^Bring (.+) back into the current scope\.?$", text, flags=re.IGNORECASE)
    if match:
        return f"Reconnect {match.group(1)} to the current scope."
    if len(text) > 150:
        return f"Advance {action_title(value).lower()}."
    return text


def state_object(
    *,
    root_component: Mapping[str, object],
    components: Sequence[Mapping[str, object]],
    fallback: str,
) -> str:
    """Infer the project object that changes without hardcoding project names."""

    source = source_text(root_component=root_component, components=components)
    if "agent" in source and any(token in source for token in ("coding", "code", "repo", "repository")):
        return "coding-agent work"
    if any(token in source for token in ("repo", "repository", "codebase")):
        return "repository work"
    if "workflow" in source:
        return "workflow state"
    if "experiment" in source:
        return "experiment state"
    category = humanize(root_component.get("category"), fallback)
    return category.lower() if category else fallback


def project_intro(
    *,
    project_title: str,
    root_component: Mapping[str, object],
    components: Sequence[Mapping[str, object]],
    repo_role: str,
) -> str:
    """Return a clear project explanation derived from source-owned records."""

    source = source_text(root_component=root_component, components=components)
    agent_intro = _agent_governance_intro(
        project_title=project_title,
        source=source,
        repo_role=repo_role,
    )
    if agent_intro:
        return agent_intro
    raw = str(root_component.get("what_it_is") or root_component.get("why_tracked") or "").strip()
    cleaned = _clean_packaging_prose(raw)
    return concise_text(cleaned, limit=230, fallback=f"A source-backed project view for {project_title}.")


def source_text(*, root_component: Mapping[str, object], components: Sequence[Mapping[str, object]]) -> str:
    values: list[str] = []
    for key in ("name", "kind", "category", "what_it_is", "why_tracked"):
        value = str(root_component.get(key) or "").strip()
        if value:
            values.append(value)
    values.extend(strings(root_component.get("aliases")))
    values.extend(strings(root_component.get("subcomponents")))
    for component in components:
        for key in ("component_id", "name", "kind", "category", "product_layer", "what_it_is"):
            value = str(component.get(key) or "").strip()
            if value:
                values.append(value)
    return " ".join(values).lower()


def _agent_governance_intro(*, project_title: str, source: str, repo_role: str) -> str:
    if "agent" not in source or not any(token in source for token in ("govern", "execution", "admiss")):
        return ""
    actor = _actor_phrase(repo_role)
    work = "coding-agent work" if "coding" in source or "code" in source else "agent work"
    qualities = _agent_work_qualities(source)
    if len(qualities) < 2:
        return ""
    quality_text = _join_words(qualities)
    suffix = " across sessions" if any(token in source for token in ("memory", "history", "session", "casebook", "compass")) else ""
    return f"{project_title} helps {actor} keep {work} {quality_text}{suffix}."


def _agent_work_qualities(source: str) -> list[str]:
    candidates = [
        (("context", "ground", "retrieval"), "grounded"),
        (("govern", "admiss", "control", "tribunal"), "governed"),
        (("validat", "proof", "test", "benchmark"), "validated"),
        (("memory", "history", "casebook", "compass"), "remembered"),
    ]
    qualities: list[str] = []
    for tokens, label in candidates:
        if any(token in source for token in tokens) and label not in qualities:
            qualities.append(label)
    return qualities


def _actor_phrase(repo_role: str) -> str:
    token = str(repo_role or "").strip().lower().replace("-", "_")
    if token == "repo" or token.endswith("_repo"):
        return "repository operators"
    if token:
        return f"{humanize(repo_role).lower()} operators"
    return "project operators"


def _join_words(words: Sequence[str]) -> str:
    items = [word for word in words if word]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _clean_packaging_prose(value: str) -> str:
    text = " ".join(str(value or "").split())
    replacements = (
        (" and a platform that packages ", " platform for "),
        (" that packages ", " for "),
        (" behind one CLI", ""),
        (" behind a CLI", ""),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _drop_repeated_inline_sections(value: str) -> str:
    labels = (
        "Current focus:",
        "Next action:",
        "Evidence boundary:",
        "Recommendation:",
        "Current state:",
        "Desired state:",
    )
    first_label = min((value.find(label) for label in labels if value.find(label) > 0), default=-1)
    return value[:first_label].strip() if first_label > 0 else value


def _trim_status_tail(value: str) -> str:
    if ":" not in value:
        return value
    head, tail = value.split(":", 1)
    if len(head.split()) < 3:
        return value
    tail_start = tail.strip().split(" ", 1)[0].lower().strip(".,;:")
    if tail_start in _STATUS_TAIL_PREFIXES:
        return head
    return value


def _normalize_compounds(value: str) -> str:
    replacements = {
        r"\bcross host\b": "cross-host",
        r"\bsource backed\b": "source-backed",
        r"\bhuman facing\b": "human-facing",
        r"\bsource owned\b": "source-owned",
    }
    text = value
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _drop_vague_leadins(value: str) -> str:
    patterns = (
        r"^implementation checkpoint (in|for|on)\s+",
        r"^current focus:\s+",
        r"^next action:\s+",
    )
    text = value
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def _sentence_case(value: str) -> str:
    return f"{value[:1].upper()}{value[1:]}" if value else value


def _complete_trailing_preposition(value: str) -> str:
    if re.search(r"\b(into|to|from|for|with|by|on|in)$", value, flags=re.IGNORECASE):
        return f"{value} the current scope"
    return value

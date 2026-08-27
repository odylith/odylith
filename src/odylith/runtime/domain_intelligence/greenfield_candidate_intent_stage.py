"""Render a non-authoritative human preview of verified Semantic Intent."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.domain_intelligence.greenfield_semantic_backlog_projection import (
    semantic_policy_boundary_summaries,
)

def render_candidate_intent_markdown(intent: Mapping[str, Any]) -> str:
    """Render the human view of the typed candidate; Markdown remains non-authoritative."""

    title = str(intent.get("title") or "Greenfield Project").strip()
    presentation = intent.get("presentation")
    if not isinstance(presentation, Mapping):
        raise ValueError("verified Product Intent preview lacks presentation custody")
    presentation_status = str(presentation.get("status") or "").strip()
    if presentation_status == "working_assumption":
        presentation_note = "Working title assumption; editable before confirmation."
    elif presentation_status == "source_declared":
        presentation_note = "Source-declared title."
    else:
        raise ValueError("verified Product Intent preview has invalid presentation custody")
    lines = [
        f"# {title} - Product Intent Confirmation",
        "",
        f"> Presentation: {presentation_note}",
        "",
        "## Product story",
        str(intent.get("product_story") or "").strip(),
        "",
        "## State objects",
        *_bullet_lines(intent.get("state_objects"), empty_text="None."),
        "",
        "## Visible outputs",
        *_bullet_lines(intent.get("visible_outputs"), empty_text="None."),
        "",
        "## First complete path",
        str(intent.get("first_path") or "").strip(),
        "",
        "## Policy boundaries",
        *_bullet_lines(
            _policy_boundary_lines(intent.get("policy_boundaries")),
            empty_text="None.",
        ),
        "",
        "## Product boundaries",
        *_bullet_lines(intent.get("product_boundaries"), empty_text="None."),
        "",
        "## Human actors",
        *_bullet_lines(
            _human_actor_lines(intent.get("human_actors")),
            empty_text="None.",
        ),
        "",
        "## External systems",
        *_bullet_lines(
            intent.get("external_systems"),
            empty_text="None.",
        ),
        "",
        "## Owned capabilities",
        *_bullet_lines(intent.get("owned_capabilities"), empty_text="None."),
        "",
        "## Critical assumptions",
        *_bullet_lines(
            intent.get("assumptions"),
            empty_text="None.",
        ),
        "",
        "## Ambiguities",
        *_bullet_lines(intent.get("ambiguities"), empty_text="None."),
        "",
        "## Proof boundary",
        str(intent.get("proof_boundary") or "").strip(),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _bullet_lines(value: Any, *, empty_text: str) -> list[str]:
    rows = _text_values(value)
    return [f"- {row}" for row in rows] if rows else [f"- {empty_text}"]


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        token = value.strip()
        return [token] if token else []
    if not isinstance(value, (list, tuple)):
        return []
    return [token for row in value if (token := str(row).strip())]


def _policy_boundary_lines(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    if any(not isinstance(row, Mapping) for row in value):
        raise ValueError("verified Product Intent policy boundary is malformed")
    return list(semantic_policy_boundary_summaries(value))


def _human_actor_lines(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise ValueError("verified Product Intent actor capability is malformed")
        label = str(row.get("label") or "").strip()
        actions = _text_values(row.get("owned_actions"))
        if not label:
            raise ValueError("verified Product Intent actor capability lacks identity")
        result.append(
            f"{label} — {'; '.join(action.rstrip(' .!?') for action in actions)}"
            if actions
            else label
        )
    return result


__all__ = [
    "render_candidate_intent_markdown",
]

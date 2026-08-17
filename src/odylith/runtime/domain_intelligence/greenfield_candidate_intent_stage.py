"""Render a non-authoritative human preview of verified Semantic Intent."""

from __future__ import annotations

from typing import Any, Mapping

def render_candidate_intent_markdown(intent: Mapping[str, Any]) -> str:
    """Render the human view of the typed candidate; Markdown remains non-authoritative."""

    title = str(intent.get("title") or "Greenfield Project").strip()
    lines = [
        f"# {title} - Product Intent Confirmation",
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
        "## Operational constraints",
        *_bullet_lines(
            intent.get("operational_constraints"),
            empty_text="None.",
        ),
        "",
        "## Human actors",
        *_bullet_lines(intent.get("human_actors"), empty_text="None."),
        "",
        "## External systems",
        *_bullet_lines(
            intent.get("external_systems"),
            empty_text="None.",
        ),
        "",
        "## Internal product systems",
        *_bullet_lines(intent.get("internal_systems"), empty_text="None."),
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


__all__ = [
    "render_candidate_intent_markdown",
]

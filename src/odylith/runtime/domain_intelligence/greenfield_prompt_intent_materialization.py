"""Materialize prompt-only greenfield intent into typed custody files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_record
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority


def materialize_prompt_confirmed_intent(
    *,
    prompt: str,
    repo_root: Path,
    fallback_title: str,
) -> dict[str, Any]:
    """Persist prompt-only intent as Markdown plus typed JSON before transaction compile."""

    if not prompt or prompt == "new project":
        raise prompt_only_material_decision_error()
    try:
        intent = parse_confirmed_intent_text(prompt, prompt=prompt, fallback_title=fallback_title)
    except ValueError as exc:
        raise prompt_only_material_decision_error() from exc
    if _prompt_only_intent_is_generic(intent):
        raise prompt_only_material_decision_error()
    root = Path(repo_root).expanduser().resolve()
    path = root / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    atomic_write_text(path, _render_confirmed_intent_markdown(intent), encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt=prompt, fallback_title=fallback_title)
    structured_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    authority = product_intent_authority_from_envelope(
        record.envelope,
        structured_intent_path=structured_path,
        markdown_source_path=path,
    )
    require_product_intent_authority(authority)
    accepted = dict(record.product_facts)
    accepted[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    return accepted


def prompt_only_material_decision_error() -> ValueError:
    return ValueError(
        "Odylith needs one material product decision before compiling a transaction from prompt-only input: "
        "who uses it, what state changes, what first path completes, and what visible proof counts. "
        "Answer in normal product language; no Product Intent file or JSON repair is required."
    )


def _render_confirmed_intent_markdown(intent: Mapping[str, Any]) -> str:
    title = str(intent.get("title") or "Greenfield Project").strip()
    lines = [
        f"# {title} - Product Intent Confirmation",
        "",
        "## Product story",
        str(intent.get("product_story") or "").strip(),
        "",
        "## State object",
        str(intent.get("state_object") or "").strip(),
        "",
        "## First complete path",
        str(intent.get("first_path") or "").strip(),
        "",
        "## Human actors",
        *_bullet_lines(intent.get("human_actors"), empty_text="Primary user: completes the first proof path."),
        "",
        "## External systems",
        *_bullet_lines(
            intent.get("external_systems"),
            empty_text="No external systems are required for the first proof path.",
        ),
        "",
        "## Internal product systems",
        *_bullet_lines(intent.get("internal_systems"), empty_text="Core workspace: owns the first path state and proof."),
        "",
        "## Critical assumptions",
        *_bullet_lines(
            intent.get("assumptions"),
            empty_text="Release 0.0.1 proves one complete path before broader automation.",
        ),
        "",
        "## Ambiguities",
        *_bullet_lines(intent.get("ambiguities"), empty_text="No material ambiguity blocks the first proof path."),
        "",
        "## Proof boundary",
        str(intent.get("proof_boundary") or "").strip(),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _bullet_lines(value: Any, *, empty_text: str) -> list[str]:
    rows = confirmed_text_values(value)
    return [f"- {row}" for row in rows] if rows else [f"- {empty_text}"]


def _prompt_only_intent_is_generic(intent: Mapping[str, Any]) -> bool:
    title = str(intent.get("title") or "").strip().casefold()
    actors = " ".join(str(row or "") for row in intent.get("human_actors") or ()).casefold()
    first_path = str(intent.get("first_path") or "").casefold()
    generic_title = title in {"greenfield project", "recovered product workspace"} or title.startswith("recovered product")
    generic_actor = "representative user" in actors or "workspace user" in actors
    generic_path = "current status" in first_path and "blockers and evidence" in first_path
    return generic_title or generic_actor or generic_path


__all__ = [
    "materialize_prompt_confirmed_intent",
    "prompt_only_material_decision_error",
]

"""Pre-confirm staging for the typed Product Intent preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import PRECONFIRM_STAGING_MARKER
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_typed_candidate_intent_files
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority


_RUNTIME_RELATIVE = Path(".odylith/runtime/greenfield")


def render_candidate_intent_markdown(intent: Mapping[str, Any]) -> str:
    """Render the human view of the typed candidate; Markdown remains non-authoritative."""

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
        "## Operational constraints",
        *_bullet_lines(
            intent.get("operational_constraints"),
            empty_text="No site or time constraint narrows the first proof path.",
        ),
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


def restage_compiled_candidate_intent(
    *,
    repo_root: Path,
    intent: Mapping[str, Any],
    previous_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal the final pre-confirm facts and keep their staged custody view aligned."""

    root = Path(repo_root).expanduser().resolve()
    authority = dict(previous_authority)
    require_product_intent_authority(authority)
    source_path = _authority_source_path(root=root, authority=authority)
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError("pre-confirm candidate evidence is unavailable; rebuild the transaction") from error
    staged_intent = dict(intent)
    envelope = build_product_intent_envelope(
        staged_intent,
        source_text=source_text,
        source_path=source_path.relative_to(root),
        source_format=str(authority.get("source_format") or "operator_prompt"),
    )
    evidence_sources = _existing_evidence_sources(root=root)
    if evidence_sources:
        envelope["source_evidence"]["evidence_sources"] = evidence_sources
    runtime = root / _RUNTIME_RELATIVE
    candidate_path = runtime / "candidate-intent.md"
    atomic_write_text(
        candidate_path,
        f"{PRECONFIRM_STAGING_MARKER}\n{render_candidate_intent_markdown(staged_intent)}",
        encoding="utf-8",
    )
    structured_path, _ = write_typed_candidate_intent_files(
        candidate_path,
        staged_intent,
        envelope=envelope,
        evidence_path=runtime / "candidate-evidence.v1.json",
    )
    final_authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=structured_path.relative_to(root),
        markdown_source_path=source_path.relative_to(root),
    )
    require_product_intent_authority(final_authority)
    staged_intent[PRODUCT_INTENT_AUTHORITY_KEY] = final_authority
    return staged_intent


def _authority_source_path(*, root: Path, authority: Mapping[str, Any]) -> Path:
    raw_path = str(authority.get("markdown_source_path") or "").strip()
    if not raw_path:
        raise ValueError("pre-confirm candidate authority is missing its evidence path")
    source_path = (root / raw_path).resolve()
    try:
        source_path.relative_to(root)
    except ValueError as error:
        raise ValueError("pre-confirm candidate evidence path escapes the repository") from error
    return source_path


def _existing_evidence_sources(*, root: Path) -> list[dict[str, str]]:
    path = root / _RUNTIME_RELATIVE / "candidate-evidence.v1.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    source_evidence = payload.get("source_evidence") if isinstance(payload, Mapping) else {}
    rows = source_evidence.get("evidence_sources") if isinstance(source_evidence, Mapping) else []
    return [
        {"source_id": str(row.get("source_id") or "").strip(), "source_path": str(row.get("source_path") or "").strip()}
        for row in rows
        if isinstance(row, Mapping)
        and str(row.get("source_id") or "").strip()
        and str(row.get("source_path") or "").strip()
    ]


def _bullet_lines(value: Any, *, empty_text: str) -> list[str]:
    rows = confirmed_text_values(value)
    return [f"- {row}" for row in rows] if rows else [f"- {empty_text}"]


__all__ = ["render_candidate_intent_markdown", "restage_compiled_candidate_intent"]

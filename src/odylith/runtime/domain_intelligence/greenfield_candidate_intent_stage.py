"""Pre-confirm staging for the typed Product Intent preview."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import PRECONFIRM_STAGING_MARKER
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_typed_candidate_intent_files
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority


_RUNTIME_RELATIVE = Path(".odylith/runtime/greenfield")


@dataclass(frozen=True)
class CandidateIntentStagePaths:
    """All mutable files owned by one pre-confirm candidate stage."""

    markdown: Path
    structured: Path
    evidence_markdown: Path
    evidence_ledger: Path
    operator_prompt: Path
    operator_edit: Path


def candidate_intent_stage_paths(repo_root: Path) -> CandidateIntentStagePaths:
    root = Path(repo_root).expanduser().resolve()
    runtime = root / _RUNTIME_RELATIVE
    markdown = runtime / "candidate-intent.md"
    return CandidateIntentStagePaths(
        markdown=markdown,
        structured=markdown.with_suffix(".json"),
        evidence_markdown=runtime / "candidate-evidence.md",
        evidence_ledger=runtime / "candidate-evidence.v1.json",
        operator_prompt=runtime / "operator-prompt.txt",
        operator_edit=runtime / "edit-evidence.md",
    )


def stage_candidate_intent(
    *,
    repo_root: Path,
    intent: Mapping[str, Any],
    envelope: Mapping[str, Any],
    authority: Mapping[str, Any],
    prompt: str,
    edit_evidence: str,
    evidence_source: str,
) -> dict[str, Any]:
    """Persist one already validated candidate and its evidence ledger."""

    require_product_intent_authority(authority)
    paths = candidate_intent_stage_paths(repo_root)
    atomic_write_text(
        paths.markdown,
        f"{PRECONFIRM_STAGING_MARKER}\n{render_candidate_intent_markdown(intent)}",
        encoding="utf-8",
    )
    atomic_write_text(paths.operator_prompt, prompt.strip() + "\n", encoding="utf-8")
    if edit_evidence:
        atomic_write_text(paths.operator_edit, edit_evidence.strip() + "\n", encoding="utf-8")
    atomic_write_text(paths.evidence_markdown, evidence_source, encoding="utf-8")
    write_typed_candidate_intent_files(
        paths.markdown,
        intent,
        envelope=envelope,
        evidence_path=paths.evidence_ledger,
    )
    candidate = dict(intent)
    candidate[PRODUCT_INTENT_AUTHORITY_KEY] = dict(authority)
    return candidate


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


def _bullet_lines(value: Any, *, empty_text: str) -> list[str]:
    rows = confirmed_text_values(value)
    return [f"- {row}" for row in rows] if rows else [f"- {empty_text}"]


__all__ = [
    "CandidateIntentStagePaths",
    "candidate_intent_stage_paths",
    "render_candidate_intent_markdown",
    "stage_candidate_intent",
]

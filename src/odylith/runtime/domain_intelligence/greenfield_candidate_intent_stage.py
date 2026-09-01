"""Pre-confirm staging for the typed Product Intent preview."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    LIST_FACT_KEYS,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_FACT_KEYS,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_FACTS_HASH_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_facts_hash,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority


_RUNTIME_RELATIVE = Path(".odylith/runtime/greenfield")
PRECONFIRM_STAGING_MARKER = "<!-- odylith:preconfirm-staging -->"
TYPED_CANDIDATE_SCHEMA_VERSION = "odylith.greenfield.typed_candidate.v1"
CANDIDATE_EVIDENCE_SCHEMA_VERSION = "odylith.greenfield.candidate_evidence.v1"


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
    facts = _verified_stage_facts(
        intent=intent,
        envelope=envelope,
        authority=authority,
        paths=paths,
        repo_root=repo_root,
    )
    markdown = render_candidate_intent_markdown(facts)
    structured_payload, evidence_payload = _candidate_payloads(
        facts=facts,
        envelope=envelope,
    )
    atomic_write_text(
        paths.markdown,
        f"{PRECONFIRM_STAGING_MARKER}\n{markdown}",
        encoding="utf-8",
    )
    atomic_write_text(paths.operator_prompt, prompt.strip() + "\n", encoding="utf-8")
    if edit_evidence:
        atomic_write_text(paths.operator_edit, edit_evidence.strip() + "\n", encoding="utf-8")
    atomic_write_text(paths.evidence_markdown, evidence_source, encoding="utf-8")
    atomic_write_text(
        paths.structured,
        json.dumps(structured_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    atomic_write_text(
        paths.evidence_ledger,
        json.dumps(evidence_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    candidate = dict(intent)
    if AUTHORED_SEMANTICS_KEY in intent:
        for key in PRODUCT_FACT_KEYS:
            candidate.pop(key, None)
        candidate.update(copy.deepcopy(facts))
    candidate[PRODUCT_INTENT_AUTHORITY_KEY] = dict(authority)
    return candidate


def render_candidate_intent_markdown(intent: Mapping[str, Any]) -> str:
    """Render the human view of the typed candidate; Markdown remains non-authoritative."""

    title = _text_fact(intent, "title", default="Greenfield Project")
    lines = [
        f"# {title} - Product Intent Confirmation",
        "",
        "## Product story",
        _text_fact(intent, "product_story"),
        "",
        "## State object",
        _text_fact(intent, "state_object"),
        "",
        "## First complete path",
        _text_fact(intent, "first_path"),
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
        _text_fact(intent, "proof_boundary"),
    ]
    return "\n".join(lines) + "\n"


def _bullet_lines(value: Any, *, empty_text: str) -> list[str]:
    if value is None:
        rows: list[str] = []
    elif isinstance(value, list) and all(isinstance(row, str) and row for row in value):
        rows = list(value)
    else:
        raise ValueError("typed candidate list facts must be exact non-empty strings")
    return [f"- {row}" for row in rows] if rows else [f"- {empty_text}"]


def _text_fact(intent: Mapping[str, Any], key: str, *, default: str = "") -> str:
    value = intent.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"typed candidate {key} must be an exact string")
    return value


def _verified_stage_facts(
    *,
    intent: Mapping[str, Any],
    envelope: Mapping[str, Any],
    authority: Mapping[str, Any],
    paths: CandidateIntentStagePaths,
    repo_root: Path,
) -> dict[str, Any]:
    raw_facts = envelope.get("product_facts")
    if not isinstance(raw_facts, Mapping):
        raise ValueError("typed candidate envelope is missing exact product facts")
    facts = _exact_product_facts(raw_facts)
    if set(raw_facts) != set(facts):
        raise ValueError("typed candidate envelope contains invalid product fact fields")
    if AUTHORED_SEMANTICS_KEY in intent and _exact_product_facts(intent) != facts:
        raise ValueError("model-authored candidate facts drifted from the verified envelope")

    fact_hash = product_facts_hash(facts)
    decision_record = envelope.get("decision_record")
    if (
        not isinstance(decision_record, Mapping)
        or decision_record.get(PRODUCT_FACTS_HASH_KEY) != fact_hash
        or authority.get(PRODUCT_FACTS_HASH_KEY) != fact_hash
    ):
        raise ValueError("typed candidate facts do not match their sealed authority hash")

    root = Path(repo_root).expanduser().resolve()
    expected_authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=paths.structured.relative_to(root),
        markdown_source_path=paths.evidence_markdown.relative_to(root),
    )
    if dict(authority) != expected_authority:
        raise ValueError("typed candidate authority does not match the verified envelope")
    return facts


def _exact_product_facts(value: Mapping[str, Any]) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for key in PRODUCT_FACT_KEYS:
        if key not in value:
            continue
        raw = value.get(key)
        if key in LIST_FACT_KEYS:
            if not isinstance(raw, list) or any(
                not isinstance(row, str) or not row for row in raw
            ):
                raise ValueError(f"typed candidate {key} must be an exact string list")
            if raw:
                facts[key] = copy.deepcopy(raw)
            continue
        if not isinstance(raw, str):
            raise ValueError(f"typed candidate {key} must be an exact string")
        if raw:
            facts[key] = raw
    return facts


def _candidate_payloads(
    *,
    facts: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    materiality_gate = envelope.get("materiality_gate")
    decision_record = envelope.get("decision_record")
    source_evidence = envelope.get("source_evidence")
    custody_ledger = envelope.get("custody_ledger")
    if not all(
        isinstance(value, Mapping)
        for value in (materiality_gate, decision_record, source_evidence, custody_ledger)
    ):
        raise ValueError("typed candidate envelope is missing verified custody sections")
    typed_payload = {
        "schema_version": TYPED_CANDIDATE_SCHEMA_VERSION,
        "product_facts": copy.deepcopy(dict(facts)),
        "materiality_gate": copy.deepcopy(dict(materiality_gate)),
        "decision_record": copy.deepcopy(dict(decision_record)),
    }
    evidence_payload = {
        "schema_version": CANDIDATE_EVIDENCE_SCHEMA_VERSION,
        "source_evidence": copy.deepcopy(dict(source_evidence)),
        "custody_ledger": copy.deepcopy(dict(custody_ledger)),
    }
    return {**typed_payload, **copy.deepcopy(dict(facts))}, evidence_payload


__all__ = [
    "CANDIDATE_EVIDENCE_SCHEMA_VERSION",
    "CandidateIntentStagePaths",
    "PRECONFIRM_STAGING_MARKER",
    "TYPED_CANDIDATE_SCHEMA_VERSION",
    "candidate_intent_stage_paths",
    "render_candidate_intent_markdown",
    "stage_candidate_intent",
]

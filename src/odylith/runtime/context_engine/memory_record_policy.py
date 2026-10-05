"""Shared authority admission and usefulness for derived memory records.

Scores order evidence within its admitted role. They never establish truth or
allow historical learning to overtake a current source contract.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from odylith.runtime.common import derivation_provenance

POLICY_VERSION = "memory_record.v1"
ROLES = frozenset({"current_truth", "historical_learning", "observation"})
VALIDITIES = frozenset({"current", "superseded", "refuted", "rejected", "unknown"})
DECAY = {"fresh": 1.0, "recent": 0.85, "stale": 0.6, "cold": 0.3, "unknown": 0.2}
PROJECTION_IDENTITIES = {
    "workstreams": ("workstream", "idea_id", "source_path"),
    "plans": ("plan", "plan_path", "source_path"),
    "bugs": ("bug", "bug_key", "link_target"),
    "components": ("component", "component_id", "spec_ref"),
    "diagrams": ("diagram", "diagram_id", "source_mmd"),
    "engineering_notes": ("", "note_id", "source_path"),
    "releases": ("release", "release_id", "source_path"),
    "test_cases": ("test", "test_id", "test_path"),
}


def independent_selection(state: str, ambiguity_class: str) -> bool:
    return state == "explicit" or (
        state == "inferred_confident" and ambiguity_class == "resolved"
    )


def freshness_bucket(age_hours: float | None) -> str:
    if age_hours is None:
        return "unknown"
    if age_hours <= 24:
        return "fresh"
    if age_hours <= 72:
        return "recent"
    if age_hours <= 336:
        return "stale"
    return "cold"


def freshness(*, confirmed_utc: str, now: dt.datetime | None = None) -> dict[str, Any]:
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        parsed = dt.datetime.fromisoformat(str(confirmed_utc).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        age = max(0.0, (now - parsed).total_seconds() / 3600)
    except (ValueError, TypeError):
        age = None
    bucket = freshness_bucket(age)
    return {
        "bucket": bucket,
        "updated_utc": str(confirmed_utc or ""),
        "newest_age_hours": None if age is None else round(age, 3),
    }


def record(
    metadata: Mapping[str, Any] | None = None,
    *,
    role: str = "observation",
    validity: str = "unknown",
    source_ref: str = "",
    source_fingerprint: str = "",
    confirmed_utc: str = "",
    evidence_utc: str = "",
    observed_utc: str = "",
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = dict(metadata or {})
    nested = metadata.get("memory_record")
    existing = dict(nested) if isinstance(nested, Mapping) else metadata
    role = str(existing.get("role", existing.get("memory_role", role)))
    validity = str(existing.get("validity", existing.get("memory_validity", validity)))
    if isinstance(nested, Mapping) and nested.get("version") != POLICY_VERSION:
        role, validity = "observation", "unknown"
    superseded_by = str(metadata.get("superseded_by", existing.get("superseded_by", ""))).strip()
    if superseded_by:
        validity = "superseded"
    carried_provenance = existing.get("provenance", {})
    if provenance is None and isinstance(carried_provenance, Mapping):
        provenance = carried_provenance
    return {
        "version": POLICY_VERSION,
        "role": role if role in ROLES else "observation",
        "validity": validity if validity in VALIDITIES else "unknown",
        "source_ref": source_ref or str(existing.get("source_ref", "")),
        "source_fingerprint": source_fingerprint or str(existing.get("source_fingerprint", "")),
        "confirmed_utc": confirmed_utc or str(existing.get("confirmed_utc", "")),
        "evidence_utc": evidence_utc or str(existing.get("evidence_utc", "")),
        "observed_utc": observed_utc or str(existing.get("observed_utc", "")),
        "provenance": dict(provenance) if isinstance(provenance, Mapping) else {},
        **({"superseded_by": superseded_by} if superseded_by else {}),
        **{key: existing[key] for key in ("claim_key", "claim_value", "constraint") if key in existing},
    }


def assess(
    value: Mapping[str, Any] | None,
    *,
    relevance: float = 0,
    expected_provenance: Mapping[str, Any] | None = None,
    now: dt.datetime | None = None,
    conflict: bool = False,
) -> dict[str, Any]:
    value = dict(value or {})
    valid_contract = value.get("version") == POLICY_VERSION
    role = value.get("role") if valid_contract else "observation"
    validity = value.get("validity") if valid_contract else "unknown"
    provenance = value.get("provenance")
    grounded = valid_contract and bool(
        value.get("source_ref") and len(str(value.get("source_fingerprint", ""))) == 64
        and all(char in "0123456789abcdef" for char in str(value.get("source_fingerprint", "")))
        and isinstance(provenance, Mapping) and provenance.get("version") == "v1"
        and provenance.get("repo_root") == "." and provenance.get("projection_fingerprint")
        and provenance.get("projection_scope") and provenance.get("code_version")
        and type(provenance.get("sync_generation")) is int and isinstance(provenance.get("flags"), Mapping)
    )
    compatible = grounded and (
        expected_provenance is None
        or (
            provenance.get("sync_generation") == expected_provenance.get("sync_generation")
            and derivation_provenance.provenance_matches(
                actual=provenance, expected=expected_provenance, require_generation=False
            )
        )
    )
    current = role == "current_truth" and validity == "current" and compatible and not conflict
    learning = role == "historical_learning" and grounded
    authority = 3 if current else 2 if learning else 1 if role == "observation" and compatible else 0
    age = freshness(confirmed_utc=str(value.get("confirmed_utc") or value.get("evidence_utc", "")), now=now)
    factor = 1.0 if current else DECAY[age["bucket"]]
    try:
        relevance = float(relevance)
        relevance = max(0.0, min(1.0, relevance)) if math.isfinite(relevance) else 0.0
    except (TypeError, ValueError):
        relevance = 0.0
    evidence = 1.0 if compatible else 0.5 if grounded else 0.0
    components = {
        "relevance": round(70 * relevance, 3),
        "evidence": 20 * evidence,
        "freshness": round(10 * factor, 3),
    }
    if conflict:
        reason = "contradictory_current_claims"
    elif current:
        reason = "current_source"
    elif learning:
        reason = "historical_evidence"
    elif grounded and not compatible:
        reason = "provenance_mismatch"
    else:
        reason = "unknown_authority"
    return {
        "authority_class": authority, "current_authority": current,
        "use": "current_authority" if current else "historical_learning" if learning else "reference_only",
        "reason": reason,
        "freshness": age["bucket"], "decay_factor": factor,
        "score": round(sum(components.values()), 3), "score_components": components,
    }


def _finite_score(value: Any) -> float:
    try:
        score = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, score) if math.isfinite(score) else 0.0


def rank_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    now: dt.datetime | None = None,
    expected_provenance: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    claims: dict[str, set[str]] = {}
    for row in rows:
        memory = row.get("memory_record", {})
        if (
            isinstance(memory, Mapping)
            and memory.get("claim_key")
            and assess(memory, expected_provenance=expected_provenance)["current_authority"]
        ):
            claims.setdefault(str(memory["claim_key"]), set()).add(json.dumps(memory.get("claim_value"), sort_keys=True))
    maximum = max((_finite_score(row.get("score")) for row in rows), default=1) or 1
    ranked = []
    for row in rows:
        item = dict(row)
        memory = item.get("memory_record", {})
        memory = memory if isinstance(memory, Mapping) else {}
        item["memory_usefulness"] = assess(
            memory, relevance=_finite_score(item.get("score")) / maximum, now=now,
            expected_provenance=expected_provenance,
            conflict=len(claims.get(str(memory.get("claim_key", "")), set())) > 1,
        )
        ranked.append(item)
    return sorted(ranked, key=lambda row: (
        -row["memory_usefulness"]["authority_class"], -row["memory_usefulness"]["score"]
    ))


def annotate_projection_tables(tables: Mapping[str, Any], *, provenance: Mapping[str, Any], observed_utc: str) -> None:
    """Annotate already collected rows; never read or expand repository inputs."""
    specs = {str(row.get("component_id", "")): row for row in tables.get("component_specs", [])}
    for table, (kind, _, path_key) in PROJECTION_IDENTITIES.items():
        for row in tables.get(table, []):
            raw = row.get("metadata_json", "{}")
            try:
                metadata = json.loads(raw) if isinstance(raw, str) else dict(raw)
            except (ValueError, TypeError):
                metadata = {}
            if not isinstance(metadata, Mapping):
                metadata = {}
            path = str(row.get(path_key, ""))
            body = str(row.get("search_body", ""))
            if kind == "component":
                body = str(specs.get(str(row.get("component_id", "")), {}).get("markdown", ""))
            historical = (
                row.get("section") in {"done", "finished", "parked"}
                or bool(row.get("archive_bucket"))
                or (kind == "bug" and str(row.get("status", "")).casefold() == "closed")
            )
            canonical_contract = kind == "component" and path.endswith("/CURRENT_SPEC.md")
            active_object = (
                (kind in {"workstream", "plan"} and row.get("section") in {"active", "execution"})
                or (kind == "bug" and str(row.get("status", "")).casefold() == "open")
            )
            canonical_current = canonical_contract or active_object
            role = "current_truth" if canonical_current else "historical_learning" if historical else "observation"
            source_fingerprint = str(row.pop("memory_source_fingerprint", ""))
            if not source_fingerprint and body:
                source_fingerprint = hashlib.sha256(body.encode()).hexdigest()
            evidence_utc = metadata.get("updated_utc", metadata.get("updated",
                metadata.get("spec_last_updated", row.get("updated", row.get("date", "")))))
            row["memory_record"] = record(
                metadata, role=role, validity="current" if canonical_current and body else "unknown",
                source_ref=path, source_fingerprint=source_fingerprint, evidence_utc=str(evidence_utc),
                observed_utc=observed_utc, provenance=provenance,
            )


def attach_document_records(documents: Sequence[dict[str, Any]], *, tables: Mapping[str, Any]) -> None:
    indexed = {}
    for table, (kind, id_key, _) in PROJECTION_IDENTITIES.items():
        for row in tables.get(table, []):
            entity_kind = kind or str(row.get("note_kind", ""))
            entity_id = str(row.get("bug_id") or row.get(id_key, "")) if kind == "bug" else str(row.get(id_key, ""))
            if isinstance(row.get("memory_record"), Mapping):
                indexed[f"{entity_kind}:{entity_id}"] = row["memory_record"]
    for document in documents:
        memory = indexed.get(str(document.get("doc_key", "")))
        if memory:
            provenance = json.loads(document["provenance_json"])
            provenance["memory_record"] = memory
            document["provenance_json"] = json.dumps(provenance, sort_keys=True, ensure_ascii=False)

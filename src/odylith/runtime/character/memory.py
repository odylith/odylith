from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.character.contract import (
    FAMILY,
    LEARNING_CONTRACT,
    clean_strings,
)

PENDING_TIMESTAMP = "pending_persistence"

_SENSITIVE_MARKERS = (
    "authorization:",
    "bearer ",
    "password",
    "secret",
    "token=",
    "transcript",
    "api_key",
    "apikey",
    "sk-",
)

_EPHEMERAL_REF_PREFIXES = (
    "/tmp/",
    "/private/tmp/",
    "/private/var/",
    "/var/folders/",
    "/dev/fd/",
)


def unsafe_practice_string(token: str) -> bool:
    lowered = str(token or "").strip().lower()
    if not lowered:
        return True
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        return True
    if lowered.startswith(_EPHEMERAL_REF_PREFIXES):
        return True
    return any(marker in lowered for marker in ("/tmp.", "/.tmp/", "\\tmp\\"))


def _safe_strings(value: Any, *, limit: int = 12, max_chars: int = 180) -> list[str]:
    rows: list[str] = []
    for token in clean_strings(value, limit=limit * 2):
        if unsafe_practice_string(token):
            continue
        rows.append(token[:max_chars])
        if len(rows) >= limit:
            break
    return rows


def safe_practice_strings(value: Any, *, limit: int = 12, max_chars: int = 180) -> list[str]:
    return _safe_strings(value, limit=limit, max_chars=max_chars)


def _compact_law_results(value: Any, *, limit: int = 12) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, str]] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        rows.append(
            {
                "law_id": str(raw.get("law_id", "")).strip(),
                "status": str(raw.get("status", "")).strip(),
                "evidence": str(raw.get("evidence", "")).strip()[:180],
                "recovery": str(raw.get("recovery", "")).strip()[:240],
            }
        )
        if len(rows) >= limit:
            break
    return [row for row in rows if row["law_id"] and row["status"]]


def _counter_subset(value: Any, keys: Sequence[str]) -> dict[str, int | bool | str | float]:
    source = dict(value) if isinstance(value, Mapping) else {}
    payload: dict[str, int | bool | str | float] = {}
    for key in keys:
        if key in source:
            raw = source.get(key)
            if isinstance(raw, bool | int | float | str):
                payload[key] = raw
    return payload


def practice_event_from_decision(
    decision: Mapping[str, Any],
    *,
    workstream_ids: Sequence[Any] = (),
    component_ids: Sequence[Any] = (),
    benchmark_case_ids: Sequence[Any] = (),
    related_casebook_ids: Sequence[Any] = (),
    proof_status: str = "not_proven",
    timestamp: str | None = None,
) -> dict[str, Any]:
    learning = dict(decision.get("learning_signal", {})) if isinstance(decision.get("learning_signal"), Mapping) else {}
    budget = dict(decision.get("latency_budget", {})) if isinstance(decision.get("latency_budget"), Mapping) else {}
    tribunal = dict(decision.get("tribunal_signal", {})) if isinstance(decision.get("tribunal_signal"), Mapping) else {}
    intervention = dict(decision.get("intervention_candidate", {})) if isinstance(decision.get("intervention_candidate"), Mapping) else {}
    archetypes = _safe_strings(decision.get("known_archetype_matches"), limit=6)
    pressure_features = _safe_strings(decision.get("pressure_observations"), limit=12)
    fingerprint = str(learning.get("fingerprint", "")).strip()
    if not fingerprint:
        fingerprint = str(decision.get("decision_id", "")).rsplit(":", maxsplit=1)[-1] or "unfingerprinted"
    visibility = str(intervention.get("visibility", "")).strip() or (
        "visible" if bool(intervention.get("visible")) else "silent"
    )
    return {
        "contract": LEARNING_CONTRACT,
        "event_id": f"practice:{fingerprint}",
        "timestamp": str(timestamp or PENDING_TIMESTAMP),
        "host_family": str(decision.get("host_family", "")).strip() or "unknown",
        "lane": str(decision.get("lane", "")).strip() or "unknown",
        "workstream_ids": _safe_strings(workstream_ids),
        "component_ids": _safe_strings(component_ids),
        "pressure_type": archetypes[0] if archetypes else "open_world",
        "pressure_features": pressure_features,
        "stance_vector": dict(decision.get("stance_vector", {}))
        if isinstance(decision.get("stance_vector"), Mapping)
        else {},
        "hard_law_results": _compact_law_results(decision.get("hard_law_results")),
        "decision": str(decision.get("decision", "")).strip(),
        "recovery_action": str(decision.get("nearest_admissible_action", "")).strip(),
        "proof_obligation": str(decision.get("proof_obligation", "")).strip(),
        "proof_status": str(proof_status or "not_proven"),
        "outcome": str(learning.get("outcome", "")).strip(),
        "false_allow_signal": False,
        "false_block_signal": False,
        "intervention_visibility": visibility,
        "latency_counters": _counter_subset(
            budget,
            (
                "tier",
                "latency_ms",
                "latency_budget_ms",
                "latency_budget_passed",
                "hot_path_budget_passed",
            ),
        ),
        "credit_counters": _counter_subset(
            budget,
            (
                "provider_call_count",
                "host_model_call_count",
                "broad_scan_count",
                "full_validation_count",
                "projection_expansion_count",
                "benchmark_execution_count",
                "subagent_spawn_count",
            ),
        ),
        "benchmark_family": FAMILY,
        "benchmark_case_ids": _safe_strings(benchmark_case_ids),
        "related_casebook_ids": _safe_strings(related_casebook_ids),
        "tribunal_candidate": bool(tribunal.get("candidate")),
        "tribunal_doctrine_id": str(tribunal.get("doctrine_id", "")).strip(),
        "source_refs": _safe_strings(decision.get("source_refs"), limit=12),
        "fingerprint": fingerprint,
        "retention_class": str(learning.get("retention_class", "")).strip(),
        "raw_transcript_retained": False,
        "secrets_retained": False,
        "durable_requires_proof": bool(learning.get("durable_requires_proof")),
        "durable_update_allowed": bool(learning.get("durable_update_allowed")),
        "promotion_gate": str(learning.get("promotion_gate", "")).strip(),
    }

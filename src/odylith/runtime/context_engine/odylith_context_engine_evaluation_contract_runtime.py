"""Shared evaluation-contract helpers for runtime memory and architecture proof."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping


def derive_retrieval_memory_state(
    *,
    transition_status: str,
    indexed_entities: int,
    evidence_documents: int,
    compiler_ready: bool,
) -> str:
    if transition_status == "standardized" and indexed_entities > 0:
        return "strong"
    if indexed_entities > 0 or evidence_documents > 0 or compiler_ready:
        return "partial"
    return "cold"


def load_latest_benchmark_report_snapshot(
    *,
    context_engine_store: Any,
    repo_root: Path,
) -> dict[str, Any]:
    from odylith.runtime.evaluation import odylith_benchmark_runner

    payload = odylith_benchmark_runner.load_latest_runtime_benchmark_report(
        repo_root=context_engine_store.Path(repo_root).resolve()
    )
    return dict(payload) if isinstance(payload, context_engine_store.Mapping) else {}


def architecture_timing_matches_evaluation_case(
    *,
    context_engine_store: Any,
    timing_row: Mapping[str, Any],
    match_spec: Mapping[str, Any],
) -> bool:
    metadata = (
        dict(timing_row.get("metadata", {}))
        if isinstance(timing_row.get("metadata"), context_engine_store.Mapping)
        else {}
    )
    changed_paths = {
        str(token).strip()
        for token in metadata.get("changed_paths", [])
        if str(token).strip()
    } if isinstance(metadata.get("changed_paths"), list) else set()
    domain_ids = {
        str(token).strip()
        for token in metadata.get("domain_ids", [])
        if str(token).strip()
    } if isinstance(metadata.get("domain_ids"), list) else set()
    paths_all = {
        str(token).strip()
        for token in match_spec.get("paths_all", [])
        if str(token).strip()
    } if isinstance(match_spec.get("paths_all"), list) else set()
    paths_any = {
        str(token).strip()
        for token in match_spec.get("paths_any", [])
        if str(token).strip()
    } if isinstance(match_spec.get("paths_any"), list) else set()
    domains_any = {
        str(token).strip()
        for token in match_spec.get("domains_any", [])
        if str(token).strip()
    } if isinstance(match_spec.get("domains_any"), list) else set()
    if paths_all and not paths_all.issubset(changed_paths):
        return False
    if paths_any and not changed_paths.intersection(paths_any):
        return False
    if domains_any and not domain_ids.intersection(domains_any):
        return False
    return True


def architecture_timing_satisfies_evaluation_expectations(
    *,
    context_engine_store: Any,
    timing_row: Mapping[str, Any],
    expect_spec: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    metadata = (
        dict(timing_row.get("metadata", {}))
        if isinstance(timing_row.get("metadata"), context_engine_store.Mapping)
        else {}
    )
    details = {
        "observed_confidence_tier": str(metadata.get("confidence_tier", "")).strip(),
        "observed_full_scan_recommended": bool(metadata.get("full_scan_recommended")),
        "observed_contract_touchpoint_count": int(metadata.get("contract_touchpoint_count", 0) or 0),
        "observed_execution_hint_mode": str(metadata.get("execution_hint_mode", "")).strip(),
        "observed_risk_tier": str(metadata.get("risk_tier", "")).strip(),
    }
    if not isinstance(expect_spec, context_engine_store.Mapping) or not expect_spec:
        return True, details
    matched = True
    expected_confidence = context_engine_store._expected_token_set(expect_spec.get("confidence_tier"))
    if expected_confidence:
        details["expected_confidence_tier"] = sorted(expected_confidence)
        if details["observed_confidence_tier"] not in expected_confidence:
            matched = False
    for field_name in ("full_scan_recommended", "resolved"):
        if field_name not in expect_spec:
            continue
        expected_bool = bool(expect_spec.get(field_name))
        observed_bool = bool(metadata.get(field_name))
        details[f"expected_{field_name}"] = expected_bool
        details[f"observed_{field_name}"] = observed_bool
        if observed_bool != expected_bool:
            matched = False
    expected_execution_modes = context_engine_store._expected_token_set(expect_spec.get("execution_hint_mode"))
    if expected_execution_modes:
        details["expected_execution_hint_mode"] = sorted(expected_execution_modes)
        if details["observed_execution_hint_mode"] not in expected_execution_modes:
            matched = False
    expected_risk_tiers = context_engine_store._expected_token_set(expect_spec.get("risk_tier"))
    if expected_risk_tiers:
        details["expected_risk_tier"] = sorted(expected_risk_tiers)
        if details["observed_risk_tier"] not in expected_risk_tiers:
            matched = False
    if "contract_touchpoints_min" in expect_spec:
        expected_min = int(expect_spec.get("contract_touchpoints_min", 0) or 0)
        details["expected_contract_touchpoints_min"] = expected_min
        if details["observed_contract_touchpoint_count"] < expected_min:
            matched = False
    if "authority_graph_edges_min" in expect_spec:
        expected_min = int(expect_spec.get("authority_graph_edges_min", 0) or 0)
        observed_count = int(metadata.get("authority_graph_edge_count", 0) or 0)
        details["expected_authority_graph_edges_min"] = expected_min
        details["observed_authority_graph_edge_count"] = observed_count
        if observed_count < expected_min:
            matched = False
    return matched, details

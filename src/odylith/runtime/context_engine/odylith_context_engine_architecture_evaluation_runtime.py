"""Architecture evaluation synthesis for runtime posture reporting."""

from __future__ import annotations

import re
from pathlib import Path
import time
from typing import Any
from typing import Mapping


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _case_changed_paths(case: Mapping[str, Any]) -> list[str]:
    benchmark = dict(case.get("benchmark", {})) if isinstance(case.get("benchmark"), Mapping) else {}
    match_spec = dict(case.get("match", {})) if isinstance(case.get("match"), Mapping) else {}
    return _dedupe_strings(
        [
            *(
                str(token).strip()
                for token in benchmark.get("paths", [])
                if isinstance(benchmark.get("paths"), list) and str(token).strip()
            ),
            *(
                str(token).strip()
                for token in match_spec.get("paths_all", [])
                if isinstance(match_spec.get("paths_all"), list) and str(token).strip()
            ),
            *(
                str(token).strip()
                for token in match_spec.get("paths_any", [])
                if isinstance(match_spec.get("paths_any"), list) and str(token).strip()
            ),
        ]
    )


def _domain_aliases(domain_id: str) -> list[str]:
    token = str(domain_id or "").strip()
    if not token:
        return []
    aliases = {token}
    aliases.update(
        fragment
        for fragment in re.split(r"[^a-z0-9]+", token.lower())
        if fragment
    )
    return sorted(aliases)


def _payload_domain_ids(payload: Mapping[str, Any]) -> list[str]:
    domain_ids: set[str] = set()
    topology_domains = payload.get("topology_domains", [])
    if isinstance(topology_domains, list):
        for row in topology_domains:
            if not isinstance(row, Mapping):
                continue
            domain_ids.update(_domain_aliases(str(row.get("domain_id", "")).strip()))
    blast_radius = dict(payload.get("blast_radius", {})) if isinstance(payload.get("blast_radius"), Mapping) else {}
    if isinstance(blast_radius.get("component_ids"), list):
        for component_id in blast_radius.get("component_ids", []):
            domain_ids.update(_domain_aliases(str(component_id).strip()))
    linked_components = payload.get("linked_components", [])
    if isinstance(linked_components, list):
        for row in linked_components:
            if not isinstance(row, Mapping):
                continue
            domain_ids.update(_domain_aliases(str(row.get("component_id", "")).strip()))
    return sorted(domain_ids)


def _payload_timing_row(
    *,
    context_engine_store: Any,
    payload: Mapping[str, Any],
    duration_ms: float,
    changed_paths: list[str],
) -> dict[str, Any]:
    coverage = dict(payload.get("coverage", {})) if isinstance(payload.get("coverage"), Mapping) else {}
    execution_hint = dict(payload.get("execution_hint", {})) if isinstance(payload.get("execution_hint"), Mapping) else {}
    authority_graph = dict(payload.get("authority_graph", {})) if isinstance(payload.get("authority_graph"), Mapping) else {}
    authority_counts = dict(authority_graph.get("counts", {})) if isinstance(authority_graph.get("counts"), Mapping) else {}
    return {
        "ts_iso": context_engine_store._utc_now(),
        "duration_ms": round(float(duration_ms or 0.0), 3),
        "metadata": {
            "changed_paths": list(changed_paths),
            "domain_ids": _payload_domain_ids(payload),
            "confidence_tier": str(coverage.get("confidence_tier", "")).strip(),
            "full_scan_recommended": bool(payload.get("full_scan_recommended")),
            "resolved": bool(payload.get("resolved")),
            "contract_touchpoint_count": (
                len(payload.get("contract_touchpoints", []))
                if isinstance(payload.get("contract_touchpoints"), list)
                else int(payload.get("contract_touchpoint_count", 0) or 0)
            ),
            "execution_hint_mode": str(execution_hint.get("mode", "")).strip(),
            "risk_tier": str(execution_hint.get("risk_tier", "")).strip(),
            "authority_graph_edge_count": int(authority_counts.get("edges", 0) or 0),
        },
    }


def _live_architecture_timing_row(
    *,
    context_engine_store: Any,
    repo_root: Path,
    case: Mapping[str, Any],
) -> dict[str, Any] | None:
    changed_paths = _case_changed_paths(case)
    if not changed_paths:
        return None
    started_at = time.perf_counter()
    payload = context_engine_store.build_architecture_audit(
        repo_root=repo_root,
        changed_paths=changed_paths,
        runtime_mode="local",
        detail_level="compact",
    )
    if not isinstance(payload, Mapping):
        return None
    return _payload_timing_row(
        context_engine_store=context_engine_store,
        payload=payload,
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        changed_paths=[
            str(token).strip()
            for token in payload.get("changed_paths", [])
            if isinstance(payload.get("changed_paths"), list) and str(token).strip()
        ]
        or changed_paths,
    )


def build_architecture_evaluation_snapshot(
    *,
    context_engine_store: Any,
    repo_root: Path,
    corpus: Mapping[str, Any],
    focus_limit: int = 4,
    timing_limit: int = 48,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    architecture_cases = context_engine_store.odylith_benchmark_contract.architecture_benchmark_scenarios(corpus)
    if not architecture_cases:
        return {
            "status": "unseeded",
            "corpus_size": 0,
            "covered_case_count": 0,
            "satisfied_case_count": 0,
            "coverage_rate": 0.0,
            "satisfaction_rate": 0.0,
            "avg_latency_ms": 0.0,
            "avg_estimated_bytes": 0.0,
            "avg_estimated_tokens": 0.0,
            "focus_cases": [],
            "recommendations": [
                "Architecture benchmark lane is not seeded yet; add architecture cases before treating architecture copilot posture as measured."
            ],
        }
    timing_rows = [
        row
        for row in context_engine_store.odylith_control_state.load_timing_rows(
            repo_root=root,
            limit=max(1, int(timing_limit)),
        )
        if str(row.get("category", "")).strip() == "reasoning"
        and str(row.get("operation", "")).strip() == "architecture"
    ]
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    covered_count = 0
    satisfied_count = 0
    case_rows: list[dict[str, Any]] = []
    matched_timings: list[dict[str, Any]] = []
    used_live_rebuild = False
    for case in architecture_cases:
        match_spec = dict(case.get("match", {})) if isinstance(case.get("match"), Mapping) else {}
        expect_spec = dict(case.get("expect", {})) if isinstance(case.get("expect"), Mapping) else {}
        latest_timing = next(
            (row for row in timing_rows if context_engine_store._architecture_timing_matches_evaluation_case(row, match_spec)),
            None,
        )
        expectation_details: dict[str, Any] = {}
        case_status = "unmatched"
        selected_timing = latest_timing
        if latest_timing is not None:
            expectation_ok, expectation_details = context_engine_store._architecture_timing_satisfies_evaluation_expectations(
                latest_timing,
                expect_spec,
            )
            case_status = "satisfied" if expectation_ok else "drift"
        if case_status != "satisfied":
            live_timing = _live_architecture_timing_row(
                context_engine_store=context_engine_store,
                repo_root=root,
                case=case,
            )
            if live_timing is not None and context_engine_store._architecture_timing_matches_evaluation_case(live_timing, match_spec):
                live_ok, live_details = context_engine_store._architecture_timing_satisfies_evaluation_expectations(
                    live_timing,
                    expect_spec,
                )
                live_status = "satisfied" if live_ok else "drift"
                if selected_timing is None or live_status == "satisfied":
                    selected_timing = live_timing
                    expectation_details = live_details
                    case_status = live_status
                    used_live_rebuild = True
        if selected_timing is not None:
            covered_count += 1
            matched_timings.append(dict(selected_timing))
            if case_status == "satisfied":
                satisfied_count += 1
        metadata = (
            dict(selected_timing.get("metadata", {}))
            if isinstance(selected_timing, Mapping) and isinstance(selected_timing.get("metadata"), Mapping)
            else {}
        )
        case_rows.append(
            {
                "case_id": str(case.get("case_id", "")).strip(),
                "label": str(case.get("label", "")).strip() or str(case.get("case_id", "")).strip(),
                "priority": str(case.get("priority", "medium")).strip().lower() or "medium",
                "status": case_status,
                "summary": str(case.get("summary", "")).strip(),
                "latest_match_utc": str(selected_timing.get("ts_iso", "")).strip() if selected_timing else "",
                "duration_ms": round(float(selected_timing.get("duration_ms", 0.0) or 0.0), 3) if selected_timing else 0.0,
                "confidence_tier": str(metadata.get("confidence_tier", "")).strip(),
                "full_scan_recommended": bool(metadata.get("full_scan_recommended")) if selected_timing else False,
                "expectation_details": expectation_details,
            }
        )
    case_rows.sort(
        key=lambda row: (
            {"drift": 0, "unmatched": 1, "satisfied": 2}.get(str(row.get("status", "")).strip(), 9),
            priority_order.get(str(row.get("priority", "medium")).strip(), 9),
            str(row.get("label", "")).strip(),
        )
    )
    corpus_size = len(architecture_cases)
    coverage_rate = round(covered_count / max(1, corpus_size), 3)
    satisfaction_rate = round(satisfied_count / max(1, covered_count), 3) if covered_count else 0.0
    avg_latency_ms = round(
        sum(float(row.get("duration_ms", 0.0) or 0.0) for row in matched_timings) / max(1, len(matched_timings)),
        3,
    ) if matched_timings else 0.0
    avg_estimated_bytes = round(
        sum(float(dict(row.get("metadata", {})).get("estimated_bytes", 0.0) or 0.0) for row in matched_timings) / max(1, len(matched_timings)),
        3,
    ) if matched_timings else 0.0
    avg_estimated_tokens = round(
        sum(float(dict(row.get("metadata", {})).get("estimated_tokens", 0.0) or 0.0) for row in matched_timings) / max(1, len(matched_timings)),
        3,
    ) if matched_timings else 0.0
    recommendations: list[str] = []
    if not timing_rows and not used_live_rebuild:
        recommendations.append(
            f"Architecture benchmark lane is seeded but has no recent dossier evidence yet; run `{context_engine_store.display_command('context-engine', '--repo-root', '.', 'architecture', '<path>')}` on a benchmarked slice."
        )
    drift_cases = [str(row.get("label", "")).strip() for row in case_rows if str(row.get("status", "")).strip() == "drift"]
    unmatched_cases = [str(row.get("label", "")).strip() for row in case_rows if str(row.get("status", "")).strip() == "unmatched"]
    if drift_cases:
        recommendations.append(
            f"Architecture dossier drifted from expected posture for {', '.join(drift_cases[:2])}; inspect the latest dossier before trusting architecture copilot automation."
        )
    if unmatched_cases:
        recommendations.append(
            f"Architecture benchmark coverage is incomplete for {', '.join(unmatched_cases[:2])}; exercise those topology slices before tightening policy further."
        )
    if not recommendations:
        recommendations.append(
            "Architecture benchmark lane is currently healthy; use it as the acceptance baseline for future architecture-copilot changes."
        )
    signature = context_engine_store._architecture_evaluation_proof_signature(
        repo_root=root,
        corpus=corpus,
    )
    live_snapshot = {
        "status": "active" if covered_count > 0 else "seeded_no_evidence",
        "corpus_size": corpus_size,
        "covered_case_count": covered_count,
        "satisfied_case_count": satisfied_count,
        "coverage_rate": coverage_rate,
        "satisfaction_rate": satisfaction_rate,
        "avg_latency_ms": avg_latency_ms,
        "avg_estimated_bytes": avg_estimated_bytes,
        "avg_estimated_tokens": avg_estimated_tokens,
        "focus_cases": case_rows[: max(1, int(focus_limit))],
        "recommendations": recommendations[:3],
        "evidence_source": "live_rebuild" if used_live_rebuild else "live_timings",
        "signature": signature,
    }
    sticky = context_engine_store._runtime_proof_section(repo_root=root, section="architecture_evaluation")
    sticky_signature = (
        dict(sticky.get("signature", {}))
        if isinstance(sticky.get("signature"), Mapping)
        else {}
    )
    sticky_compatible = context_engine_store._architecture_evaluation_signatures_compatible(signature, sticky_signature)
    if (
        int(live_snapshot.get("covered_case_count", 0) or 0) > 0
        and sticky_compatible
        and context_engine_store._architecture_evaluation_snapshot_strength(sticky)
        > context_engine_store._architecture_evaluation_snapshot_strength(live_snapshot)
    ):
        merged = dict(sticky)
        merged["status"] = "active"
        merged["evidence_source"] = "sticky_snapshot"
        merged["live_window_empty"] = False
        merged["live_window_partial"] = True
        return merged
    if int(live_snapshot.get("covered_case_count", 0) or 0) > 0:
        context_engine_store._persist_runtime_proof_section(
            repo_root=root,
            section="architecture_evaluation",
            payload=live_snapshot,
        )
        return live_snapshot
    if int(sticky.get("covered_case_count", 0) or 0) > 0 and sticky_compatible:
        merged = dict(sticky)
        merged["status"] = "active"
        merged["evidence_source"] = "sticky_snapshot"
        merged["live_window_empty"] = True
        return merged
    return live_snapshot

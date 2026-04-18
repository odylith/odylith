"""Odylith Context Engine Packet Architecture Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import odylith_context_engine_packet_runtime_bindings

def bind(host: Any) -> None:
    odylith_context_engine_packet_runtime_bindings.bind_packet_runtime(globals(), host)

def build_architecture_audit(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    detail_level: str = "compact",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    stage_timings: dict[str, float] = {}

    def _record_architecture_timing(payload: Mapping[str, Any]) -> dict[str, Any]:
        sanitized = dict(payload)
        stage_timings = _compact_stage_timings(
            dict(sanitized.pop("_stage_timings", {}))
            if isinstance(sanitized.get("_stage_timings"), Mapping)
            else {}
        )
        coverage = dict(payload.get("coverage", {})) if isinstance(payload.get("coverage"), Mapping) else {}
        benchmark_summary = (
            dict(payload.get("benchmark_summary", {})) if isinstance(payload.get("benchmark_summary"), Mapping) else {}
        )
        execution_hint = dict(payload.get("execution_hint", {})) if isinstance(payload.get("execution_hint"), Mapping) else {}
        authority_graph = dict(payload.get("authority_graph", {})) if isinstance(payload.get("authority_graph"), Mapping) else {}
        encoded = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        record_runtime_timing(
            repo_root=root,
            category="reasoning",
            operation="architecture",
            duration_ms=round((time.perf_counter() - started_at) * 1000.0, 3),
            metadata={
                "resolved": bool(sanitized.get("resolved")),
                "changed_paths": [str(token).strip() for token in sanitized.get("changed_paths", []) if str(token).strip()]
                if isinstance(sanitized.get("changed_paths"), list)
                else [],
                "explicit_paths": [str(token).strip() for token in sanitized.get("explicit_paths", []) if str(token).strip()]
                if isinstance(sanitized.get("explicit_paths"), list)
                else [],
                "domain_ids": [
                    str(row.get("domain_id", "")).strip()
                    for row in sanitized.get("topology_domains", [])
                    if isinstance(row, Mapping) and str(row.get("domain_id", "")).strip()
                ]
                if isinstance(sanitized.get("topology_domains"), list)
                else [],
                "confidence_tier": str(coverage.get("confidence_tier", "")).strip(),
                "full_scan_recommended": bool(sanitized.get("full_scan_recommended")),
                "full_scan_reason": str(sanitized.get("full_scan_reason", "")).strip(),
                "contract_touchpoint_count": (
                    len(sanitized.get("contract_touchpoints", []))
                    if isinstance(sanitized.get("contract_touchpoints"), list)
                    else int(sanitized.get("contract_touchpoint_count", 0) or 0)
                ),
                "execution_hint_mode": str(execution_hint.get("mode", "")).strip(),
                "risk_tier": str(execution_hint.get("risk_tier", "")).strip(),
                "estimated_bytes": len(encoded.encode("utf-8")),
                "estimated_tokens": max(1, len(encoded.encode("utf-8")) // 4),
                "benchmark_matched_case_count": int(benchmark_summary.get("matched_case_count", 0) or 0),
                "benchmark_satisfied_case_count": int(benchmark_summary.get("satisfied_case_count", 0) or 0),
                "authority_graph_edge_count": int(dict(authority_graph.get("counts", {})).get("edges", 0) or 0)
                if isinstance(authority_graph.get("counts"), Mapping)
                else 0,
                "authority_graph_traceability_edges": int(
                    dict(authority_graph.get("counts", {})).get("traceability_edges", 0) or 0
                )
                if isinstance(authority_graph.get("counts"), Mapping)
                else 0,
                "stage_timings": stage_timings,
            },
        )
        return sanitized

    path_scope = _resolve_changed_path_scope_context(
        repo_root=root,
        explicit_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=session_id,
        claimed_paths=claimed_paths,
    )
    normalized = list(path_scope["analysis_paths"])
    if not normalized:
        full_scan_reason = (
            "working_tree_scope_degraded"
            if bool(path_scope.get("working_tree_scope_degraded"))
            else "no_grounded_paths"
        )
        return _record_architecture_timing({
            "resolved": False,
            "changed_paths": [],
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "topology_domains": [],
            "linked_components": [],
            "linked_diagrams": [],
            "required_reads": [],
            "diagram_watch_gaps": [],
            "full_scan_recommended": True,
            "full_scan_reason": full_scan_reason,
            "fallback_scan": _full_scan_guidance(
                repo_root=root,
                reason=full_scan_reason,
                changed_paths=[
                    *list(path_scope["explicit_paths"]),
                    *list(path_scope["repo_dirty_paths"]),
                ],
            ),
        })
    if not _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="architecture", scope="reasoning"):
        return _record_architecture_timing({
            "resolved": False,
            "changed_paths": normalized,
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "topology_domains": [],
            "linked_components": [],
            "linked_diagrams": [],
            "required_reads": [],
            "diagram_watch_gaps": [],
            "full_scan_recommended": True,
            "full_scan_reason": "runtime_unavailable",
            "fallback_scan": _full_scan_guidance(
                repo_root=root,
                reason="runtime_unavailable",
                changed_paths=normalized,
            ),
        })
    architecture_bundle = odylith_architecture_mode.load_architecture_bundle(repo_root=root)
    cache_key = json.dumps(
        {
            "fingerprint": _projection_cache_signature(repo_root=root, scope="reasoning"),
            "bundle_signature": odylith_architecture_mode._architecture_bundle_signature(  # noqa: SLF001
                repo_root=root,
                bundle=architecture_bundle,
            ),
            "benchmark_cases_hash": odylith_architecture_mode._architecture_benchmark_cases_hash(repo_root=root),  # noqa: SLF001
            "mermaid_drift_hash": _architecture_bundle_mermaid_signature_hash(
                repo_root=root,
                bundle=architecture_bundle,
            ),
            "changed_paths": normalized,
            "explicit_paths": list(path_scope["explicit_paths"]),
            "repo_dirty_paths": list(path_scope["repo_dirty_paths"]),
            "scoped_working_tree_paths": list(path_scope["scoped_working_tree_paths"]),
            "working_tree_scope": str(path_scope.get("working_tree_scope", "")).strip(),
            "working_tree_scope_degraded": bool(path_scope.get("working_tree_scope_degraded")),
            "detail_level": str(detail_level or "compact").strip() or "compact",
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    cached_payload = _PROCESS_ARCHITECTURE_PACKET_CACHE.get(cache_key)
    if isinstance(cached_payload, Mapping):
        cached = dict(cached_payload)
        cached["_stage_timings"] = {"cache_hit": 0.0}
        return _record_architecture_timing(cached)
    stage_started = time.perf_counter()
    payload = odylith_architecture_mode.build_architecture_dossier(
        repo_root=root,
        changed_paths=normalized,
        explicit_paths=list(path_scope["explicit_paths"]),
        repo_dirty_paths=list(path_scope["repo_dirty_paths"]),
        scoped_working_tree_paths=list(path_scope["scoped_working_tree_paths"]),
        working_tree_scope=str(path_scope.get("working_tree_scope", "")).strip(),
        working_tree_scope_degraded=bool(path_scope.get("working_tree_scope_degraded")),
        detail_level=detail_level,
    )
    payload["required_reads"] = _dedupe_strings(
        [
            *_companion_context_paths(changed_paths=normalized, repo_root=root),
            *(
                str(token).strip()
                for token in payload.get("required_reads", [])
                if isinstance(payload.get("required_reads"), list) and str(token).strip()
            ),
        ]
    )
    payload_stage_timings = dict(payload.get("_stage_timings", {})) if isinstance(payload.get("_stage_timings"), Mapping) else {}
    for key, value in payload_stage_timings.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        try:
            stage_timings[normalized_key] = float(value or 0.0)
        except (TypeError, ValueError):
            continue
    stage_timings.setdefault("structural_core", _elapsed_stage_ms(stage_started))
    payload["fallback_scan"] = _full_scan_guidance(
        repo_root=root,
        reason=str(payload.get("full_scan_reason", "")).strip(),
        changed_paths=normalized,
    )
    if str(detail_level or "compact").strip() == "packet":
        payload = _compact_packet_level_architecture_audit(payload)
    payload["_stage_timings"] = dict(stage_timings)
    _PROCESS_ARCHITECTURE_PACKET_CACHE[cache_key] = {
        key: value
        for key, value in payload.items()
        if key != "_stage_timings"
    }
    return _record_architecture_timing(payload)

"""Odylith Context Engine Memory Snapshot Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

import contextlib
import datetime as dt
import json
from pathlib import Path
import re
import time
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import odylith_context_engine_architecture_evaluation_runtime
from odylith.runtime.context_engine import odylith_context_engine_judgment_memory_runtime
from odylith.runtime.context_engine import odylith_context_engine_memory_areas_runtime


def _build_memory_areas_snapshot(
    *,
    enabled: bool,
    authoritative_truth: Mapping[str, Any],
    compiler_state: Mapping[str, Any],
    guidance_catalog: Mapping[str, Any],
    runtime_state: Mapping[str, Any],
    entity_counts: Mapping[str, Any],
    backend_transition: Mapping[str, Any],
    optimization: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    judgment_memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return odylith_context_engine_memory_areas_runtime.build_memory_areas_snapshot(
        context_engine_store=context_engine_store,
        enabled=enabled,
        authoritative_truth=authoritative_truth,
        compiler_state=compiler_state,
        guidance_catalog=guidance_catalog,
        runtime_state=runtime_state,
        entity_counts=entity_counts,
        backend_transition=backend_transition,
        optimization=optimization,
        evaluation=evaluation,
        judgment_memory=judgment_memory,
    )


def _odylith_disabled_memory_snapshot(
    *,
    repo_root: Path,
    switch_snapshot: Mapping[str, Any],
    optimization_snapshot: Mapping[str, Any],
    evaluation_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    disabled_judgment_areas = [
        context_engine_store._judgment_memory_area(
            key=key,
            label=label,
            state="disabled",
            summary="Odylith is disabled, so this judgment-memory area is suppressed for ablation runs.",
            items=[],
            provenance=[],
        )
        for key, label in (
            ("decisions", "Decision memory"),
            ("workspace_actor", "Workspace and actor memory"),
            ("contradictions", "Contradiction memory"),
            ("freshness", "Freshness memory"),
            ("negative", "Negative memory"),
            ("outcomes", "Outcome memory"),
            ("onboarding", "Onboarding memory"),
            ("provenance", "Provenance memory"),
        )
    ]
    payload = {
        "contract": "memory_snapshot.v1",
        "version": "v1",
        "generated_utc": context_engine_store._utc_now(),
        "status": "disabled",
        "status_reason": "odylith_disabled",
        "odylith_switch": dict(switch_snapshot),
        "engine": {
            "name": "odylith-context-engine",
            "product_layer": "",
            "storage_mode": "disabled_for_ablation",
            "authoritative_truth": "repo_tracked",
            "enabled": False,
            "backend": {},
            "target_backend": {},
            "backend_transition": {
                "status": "disabled_for_ablation",
                "v1_standardization_complete": False,
                "gaps": ["odylith_disabled"],
            },
        },
        "backend_transition": {
            "status": "disabled_for_ablation",
            "v1_standardization_complete": False,
            "actual_local_backend": {},
            "target_local_backend": {},
            "future_shared_candidate": {},
            "gaps": ["odylith_disabled"],
            "guardrails": {
                "local_first": True,
                "remote_required": False,
                "vector_first_allowed": False,
                "hybrid_rerank_role": "disabled_for_ablation",
            },
        },
        "authoritative_truth": {
            "source": "git_tracked_repo_truth",
            "mutable_runtime_root": ".odylith/runtime",
            "cache_root": ".odylith/cache/odylith-context-engine",
            "read_only_repo_truth": True,
        },
        "projection_state": {
            "projection_fingerprint": "",
            "projection_scope": "",
            "updated_utc": "",
            "tables": {},
        },
        "entity_counts": {"indexed_entity_count": 0},
        "guidance_catalog": {
            "contract": "guidance_catalog.v1",
            "version": "v1",
            "chunk_count": 0,
            "source_doc_count": 0,
            "task_family_count": 0,
            "catalog_fingerprint": "",
            "compiled_path": "",
            "compiled_bytes": 0,
        },
        "retrieval_pipeline": {
            "order": [],
            "capabilities": {
                "exact_lookup": False,
                "sparse_recall": False,
                "typed_graph_expansion": False,
                "miss_recovery": False,
                "packet_budgeting": False,
                "routing_handoff": False,
                "vector_first": False,
                "hybrid_rerank_enabled": False,
                "storage_backend_actual": "",
                "storage_backend_target": "",
                "sparse_backend_actual": "",
                "sparse_backend_target": "",
                "target_backend_standardized": False,
                "miss_recovery_mode": "",
                "future_shared_candidate": "",
            },
        },
        "runtime_state": {
            "active_sessions": 0,
            "bootstrap_packets": 0,
            "projection_snapshot_path": "",
            "projection_snapshot_bytes": 0,
            "compiler_manifest_path": "",
            "compiler_manifest_bytes": 0,
            "odylith_memory_root": str(context_engine_store.odylith_memory_backend.local_backend_root(repo_root=repo_root)),
            "judgment_memory_path": str(context_engine_store.judgment_memory_path(repo_root=repo_root)),
        },
        "optimization": {
            "contract": "optimization_snapshot.v1",
            "status": str(optimization_snapshot.get("status", "")).strip() or "disabled",
            "sample_size": int(optimization_snapshot.get("sample_size", 0) or 0),
            "overall": dict(optimization_snapshot.get("overall", {}))
            if isinstance(optimization_snapshot.get("overall"), Mapping)
            else {},
            "coverage_rate": float(evaluation_snapshot.get("coverage_rate", 0.0) or 0.0),
            "satisfaction_rate": float(evaluation_snapshot.get("satisfaction_rate", 0.0) or 0.0),
        },
        "ingest_policy": {
            "allowlisted_sources": [],
            "secret_redaction_required": True,
            "provenance_required": True,
            "repo_truth_read_only": True,
        },
        "recommendations": [
            "Odylith is disabled; derived memory and retrieval contracts are suppressed for ablation studies."
        ],
    }
    payload["judgment_memory"] = {
        "contract": "judgment_memory.v1",
        "version": "v1",
        "generated_utc": context_engine_store._utc_now(),
        "storage_path": context_engine_store._relative_repo_path(repo_root=repo_root, path=context_engine_store.judgment_memory_path(repo_root=repo_root)),
        "status": "disabled",
        "headline": "Odylith is disabled, so durable judgment memory is suppressed for this run.",
        "counts": {"disabled": len(disabled_judgment_areas)},
        "gap_count": len(disabled_judgment_areas),
        "areas": disabled_judgment_areas,
        "gaps": [
            "Odylith is disabled; durable judgment memory and persisted local memory are intentionally suppressed."
        ],
        "starter_slice": {},
    }
    payload["memory_areas"] = _build_memory_areas_snapshot(
        enabled=False,
        authoritative_truth=payload.get("authoritative_truth", {}),
        compiler_state={},
        guidance_catalog=payload.get("guidance_catalog", {}),
        runtime_state=payload.get("runtime_state", {}),
        entity_counts=payload.get("entity_counts", {}),
        backend_transition=payload.get("backend_transition", {}),
        optimization=payload.get("optimization", {}),
        evaluation=evaluation_snapshot,
        judgment_memory=payload.get("judgment_memory", {}),
    )
    payload["headline"] = str(payload["memory_areas"].get("headline", "")).strip()
    return payload


def _load_runtime_optimization_snapshot(*, repo_root: Path) -> dict[str, Any]:
    from odylith.runtime.context_engine import odylith_context_engine_runtime_learning_runtime

    return odylith_context_engine_runtime_learning_runtime.load_runtime_optimization_snapshot(
        repo_root=repo_root
    )


def load_runtime_memory_snapshot(
    *,
    repo_root: Path,
    optimization_snapshot: Mapping[str, Any] | None = None,
    evaluation_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize the current local derived memory/retrieval substrate."""

    root = Path(repo_root).resolve()
    odylith_switch = context_engine_store._odylith_switch_snapshot(repo_root=root)
    if not bool(odylith_switch.get("enabled", True)):
        optimization = (
            dict(optimization_snapshot)
            if isinstance(optimization_snapshot, Mapping)
            else _load_runtime_optimization_snapshot(repo_root=root)
        )
        evaluation = (
            dict(evaluation_snapshot)
            if isinstance(evaluation_snapshot, Mapping)
            else load_runtime_evaluation_snapshot(repo_root=root)
        )
        return _odylith_disabled_memory_snapshot(
            repo_root=root,
            switch_snapshot=odylith_switch,
            optimization_snapshot=optimization,
            evaluation_snapshot=evaluation,
        )

    state = context_engine_store.read_runtime_state(repo_root=root)
    guidance_catalog = context_engine_store.tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    guidance_summary = context_engine_store.tooling_guidance_catalog.compact_catalog_summary(guidance_catalog)
    optimization = (
        dict(optimization_snapshot)
        if isinstance(optimization_snapshot, Mapping)
        else _load_runtime_optimization_snapshot(repo_root=root)
    )
    evaluation = (
        dict(evaluation_snapshot)
        if isinstance(evaluation_snapshot, Mapping)
        else load_runtime_evaluation_snapshot(repo_root=root)
    )

    projection_state: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {
        "workstreams": 0,
        "plans": 0,
        "bugs": 0,
        "diagrams": 0,
        "components": 0,
        "component_specs": 0,
        "traceability_edges": 0,
        "engineering_notes": 0,
        "code_artifacts": 0,
        "code_edges": 0,
        "test_cases": 0,
        "test_history": 0,
        "delivery_surfaces": 0,
        "evidence_documents": 0,
    }
    with contextlib.suppress(RuntimeError):
        connection = context_engine_store._connect(root)
        try:
            for row in connection.execute(
                "SELECT name, row_count, updated_utc FROM projection_state ORDER BY name"
            ).fetchall():
                projection_state[str(row["name"]).strip()] = {
                    "row_count": int(row["row_count"] or 0),
                    "updated_utc": str(row["updated_utc"] or "").strip(),
                }
            counts.update(
                {
                    "workstreams": context_engine_store._table_row_count(connection, "workstreams"),
                    "plans": context_engine_store._table_row_count(connection, "plans"),
                    "bugs": context_engine_store._table_row_count(connection, "bugs"),
                    "diagrams": context_engine_store._table_row_count(connection, "diagrams"),
                    "components": context_engine_store._table_row_count(connection, "components"),
                    "component_specs": context_engine_store._table_row_count(connection, "component_specs"),
                    "traceability_edges": context_engine_store._table_row_count(connection, "traceability_edges"),
                    "engineering_notes": context_engine_store._table_row_count(connection, "engineering_notes"),
                    "code_artifacts": context_engine_store._table_row_count(connection, "code_artifacts"),
                    "code_edges": context_engine_store._table_row_count(connection, "code_edges"),
                    "test_cases": context_engine_store._table_row_count(connection, "test_cases"),
                    "test_history": context_engine_store._table_row_count(connection, "test_history"),
                    "delivery_surfaces": context_engine_store._table_row_count(connection, "delivery_surfaces"),
                }
            )
        finally:
            connection.close()

    projection_snapshot_file = context_engine_store.projection_snapshot_path(repo_root=root)
    compiler_manifest_path = context_engine_store.odylith_projection_bundle.manifest_path(repo_root=root)
    architecture_bundle_path = context_engine_store.odylith_architecture_mode.bundle_path(repo_root=root)
    guidance_catalog_path = context_engine_store.tooling_guidance_catalog.compiled_catalog_path(repo_root=root)
    active_sessions = len(context_engine_store.list_session_states(repo_root=root, prune=False))
    bootstrap_packets = len(list(context_engine_store.bootstraps_root(repo_root=root).glob("*.json")))
    indexed_entity_count = sum(
        counts.get(key, 0)
        for key in (
            "workstreams",
            "plans",
            "bugs",
            "diagrams",
            "components",
            "engineering_notes",
            "code_artifacts",
            "test_cases",
        )
    )
    local_backend_status = context_engine_store.odylith_memory_backend.backend_runtime_status(repo_root=root)
    local_backend_manifest = (
        dict(local_backend_status.get("manifest", {}))
        if isinstance(local_backend_status.get("manifest"), Mapping)
        else {}
    )
    compiler_manifest = context_engine_store.odylith_projection_bundle.load_bundle_manifest(repo_root=root)
    architecture_bundle = context_engine_store.odylith_architecture_mode.load_architecture_bundle(repo_root=root)
    counts["evidence_documents"] = int(local_backend_manifest.get("document_count", 0) or 0)
    observed_backend = {
        "provider": str(local_backend_status.get("provider", "")).strip() or context_engine_store._FALLBACK_LOCAL_MEMORY_BACKEND["provider"],
        "storage": str(local_backend_status.get("storage", "")).strip() or context_engine_store._FALLBACK_LOCAL_MEMORY_BACKEND["storage"],
        "sparse_recall": str(local_backend_status.get("sparse_recall", "")).strip()
        or context_engine_store._FALLBACK_LOCAL_MEMORY_BACKEND["sparse_recall"],
        "graph_expansion": context_engine_store._FALLBACK_LOCAL_MEMORY_BACKEND["graph_expansion"],
        "mode": context_engine_store._FALLBACK_LOCAL_MEMORY_BACKEND["mode"],
    }
    target_backend = dict(context_engine_store._TARGET_LOCAL_MEMORY_BACKEND)
    backend_gaps: list[str] = []
    if str(observed_backend.get("storage", "")).strip() != str(target_backend.get("storage", "")).strip():
        backend_gaps.append("columnar_store_not_enabled")
    if str(observed_backend.get("sparse_recall", "")).strip() != str(target_backend.get("sparse_recall", "")).strip():
        backend_gaps.append("tantivy_sparse_recall_not_enabled")
    standardization_complete = not backend_gaps
    backend_status_token = str(local_backend_status.get("status", "")).strip()
    convergence_state = (
        "error"
        if backend_status_token == "error"
        else "standardized"
        if standardization_complete
        else "pending_target_swap"
    )
    memory_proof_signature = context_engine_store._memory_backend_proof_signature(
        state=state,
        backend_manifest=local_backend_manifest,
    )
    memory_proof = context_engine_store._runtime_proof_section(repo_root=root, section="memory_backend")
    effective_backend = dict(observed_backend)
    effective_backend_gaps = list(backend_gaps)
    effective_standardization_complete = standardization_complete
    effective_convergence_state = convergence_state
    backend_evidence_source = "live_backend"
    sticky_signature = (
        dict(memory_proof.get("signature", {}))
        if isinstance(memory_proof.get("signature"), Mapping)
        else {}
    )
    sticky_backend = (
        dict(memory_proof.get("actual_local_backend", {}))
        if isinstance(memory_proof.get("actual_local_backend"), Mapping)
        else {}
    )
    sticky_standardized = bool(memory_proof.get("v1_standardization_complete"))
    sticky_manifest_ready = bool(local_backend_manifest.get("ready")) or str(local_backend_manifest.get("status", "")).strip() == "ready"
    sticky_manifest_present = bool(
        sticky_manifest_ready
        or int(local_backend_manifest.get("document_count", 0) or 0) > 0
        or int(local_backend_manifest.get("edge_count", 0) or 0) > 0
    )
    if (
        not effective_standardization_complete
        and sticky_standardized
        and sticky_backend
        and context_engine_store._memory_backend_sticky_snapshot_compatible(
            live_signature=memory_proof_signature,
            sticky_signature=sticky_signature,
            observed_backend=observed_backend,
            sticky_backend=sticky_backend,
        )
        and backend_status_token != "error"
        and sticky_manifest_present
    ):
        effective_backend = dict(sticky_backend)
        effective_backend_gaps = []
        effective_standardization_complete = True
        effective_convergence_state = "standardized"
        backend_evidence_source = "sticky_snapshot"
    if effective_standardization_complete and backend_evidence_source == "live_backend":
        context_engine_store._persist_runtime_proof_section(
            repo_root=root,
            section="memory_backend",
            payload={
                "status": effective_convergence_state,
                "v1_standardization_complete": True,
                "actual_local_backend": dict(effective_backend),
                "observed_local_backend": dict(observed_backend),
                "target_local_backend": dict(target_backend),
                "signature": memory_proof_signature,
                "backend_status": backend_status_token,
                "evidence_source": backend_evidence_source,
            },
        )
    remote_config = context_engine_store.odylith_remote_retrieval.remote_config(repo_root=root)
    backlog_projection = context_engine_store._load_backlog_projection(repo_root=root)
    plan_projection = context_engine_store._load_plan_projection(repo_root=root)
    bug_projection = context_engine_store._load_bug_projection(repo_root=root)
    diagram_projection = context_engine_store._load_diagram_projection(repo_root=root)
    recent_bootstrap_packets = context_engine_store._load_recent_bootstrap_packets(repo_root=root, bootstrap_limit=3)
    active_session_rows = context_engine_store.list_session_states(repo_root=root, prune=False)
    repo_dirty_paths = context_engine_store.governance.collect_meaningful_changed_paths(repo_root=root, changed_paths=(), include_git=True)
    previous_judgment_memory = context_engine_store.odylith_context_cache.read_json_object(context_engine_store.judgment_memory_path(repo_root=root))
    from odylith.runtime.surfaces import shell_onboarding

    welcome_state = shell_onboarding.build_welcome_state(repo_root=root)
    degraded_fallback_posture = (
        dict(optimization.get("degraded_fallback_posture", {}))
        if isinstance(optimization.get("degraded_fallback_posture"), Mapping)
        else {}
    )
    governance_runtime_first = (
        dict(optimization.get("governance_runtime_first_posture", {}))
        if isinstance(optimization.get("governance_runtime_first_posture"), Mapping)
        else {}
    )
    payload = {
        "contract": "memory_snapshot.v1",
        "version": "v1",
        "generated_utc": context_engine_store._utc_now(),
        "status": "active" if projection_state or str(state.get("updated_utc", "")).strip() else "cold",
        "odylith_switch": odylith_switch,
        "engine": {
            "name": "odylith-context-engine",
            "product_layer": "memory_retrieval",
            "storage_mode": "local_derived",
            "authoritative_truth": "repo_tracked",
            "backend": effective_backend,
            "target_backend": target_backend,
            "backend_evidence_source": backend_evidence_source,
            "backend_transition": {
                "status": effective_convergence_state,
                "v1_standardization_complete": effective_standardization_complete,
                "gaps": effective_backend_gaps,
            },
        },
        "backend_transition": {
            "status": effective_convergence_state,
            "v1_standardization_complete": effective_standardization_complete,
            "actual_local_backend": effective_backend,
            "observed_local_backend": observed_backend,
            "target_local_backend": target_backend,
            "future_shared_candidate": dict(context_engine_store._FUTURE_SHARED_MEMORY_BACKEND),
            "gaps": effective_backend_gaps,
            "evidence_source": backend_evidence_source,
            "signature": memory_proof_signature,
            "local_backend_status": {
                key: value
                for key, value in local_backend_status.items()
                if key in {"status", "ready", "dependencies", "manifest"}
            },
            "guardrails": {
                "local_first": True,
                "remote_required": False,
                "vector_first_allowed": False,
                "hybrid_rerank_role": "secondary_optional",
            },
        },
        "repo_scan_degraded_fallback": degraded_fallback_posture,
        "governance_runtime_first": governance_runtime_first,
        "authoritative_truth": {
            "source": "git_tracked_repo_truth",
            "mutable_runtime_root": ".odylith/runtime",
            "cache_root": ".odylith/cache/odylith-context-engine",
            "read_only_repo_truth": True,
        },
        "projection_state": {
            "projection_fingerprint": str(state.get("projection_fingerprint", "")).strip(),
            "projection_scope": str(state.get("projection_scope", "")).strip(),
            "updated_utc": str(state.get("updated_utc", "")).strip(),
            "tables": projection_state,
        },
        "compiler_state": {
            "version": str(compiler_manifest.get("version", "")).strip() or "v1",
            "ready": bool(compiler_manifest.get("ready")),
            "compiled_utc": str(compiler_manifest.get("compiled_utc", "")).strip(),
            "projection_fingerprint": str(compiler_manifest.get("projection_fingerprint", "")).strip(),
            "projection_scope": str(compiler_manifest.get("projection_scope", "")).strip(),
            "document_count": int(compiler_manifest.get("document_count", 0) or 0),
            "edge_count": int(compiler_manifest.get("edge_count", 0) or 0),
            "documents_path": str(compiler_manifest.get("documents_path", "")).strip(),
            "edges_path": str(compiler_manifest.get("edges_path", "")).strip(),
            "architecture_bundle_path": str(architecture_bundle_path),
            "architecture_bundle_ready": bool(architecture_bundle.get("ready")),
            "architecture_bundle_counts": dict(architecture_bundle.get("counts", {}))
            if isinstance(architecture_bundle.get("counts"), Mapping)
            else {},
        },
        "entity_counts": {
            **counts,
            "indexed_entity_count": indexed_entity_count,
        },
        "guidance_catalog": {
            "contract": "guidance_catalog.v1",
            "version": str(guidance_summary.get("version", "")).strip() or "v1",
            "chunk_count": int(guidance_summary.get("chunk_count", 0) or 0),
            "source_doc_count": int(guidance_summary.get("source_doc_count", 0) or 0),
            "task_family_count": len(
                [
                    str(token).strip()
                    for token in guidance_summary.get("task_families", [])
                    if str(token).strip()
                ]
            )
            if isinstance(guidance_summary.get("task_families"), list)
            else int(guidance_summary.get("task_family_count", 0) or 0),
            "catalog_fingerprint": str(guidance_catalog.get("catalog_fingerprint", "")).strip(),
            "compiled_path": str(guidance_catalog_path),
            "compiled_bytes": context_engine_store._safe_file_size(guidance_catalog_path),
        },
        "retrieval_pipeline": {
            "order": [
                "exact_lookup",
                "sparse_recall",
                "typed_graph_expansion",
                "policy_filtering",
                "optional_hybrid_rerank",
                "packet_compaction",
                "routing_handoff",
            ],
            "capabilities": {
                "exact_lookup": True,
                "sparse_recall": True,
                "typed_graph_expansion": True,
                "miss_recovery": True,
                "packet_budgeting": True,
                "routing_handoff": True,
                "vector_first": False,
                "storage_backend_actual": str(effective_backend.get("storage", "")).strip(),
                "storage_backend_target": str(target_backend.get("storage", "")).strip(),
                "sparse_backend_actual": str(effective_backend.get("sparse_recall", "")).strip(),
                "sparse_backend_target": str(target_backend.get("sparse_recall", "")).strip(),
                "target_backend_standardized": effective_standardization_complete,
                "miss_recovery_mode": "tantivy_sparse_recall"
                if effective_standardization_complete
                else "repo_scan_fallback",
                "hybrid_rerank_available": effective_standardization_complete,
                "hybrid_rerank_enabled": context_engine_store._env_truthy("ODYLITH_HYBRID_RERANK"),
                "future_shared_candidate": str(context_engine_store._FUTURE_SHARED_MEMORY_BACKEND.get("provider", "")).strip(),
            },
        },
        "runtime_state": {
            "active_sessions": active_sessions,
            "bootstrap_packets": bootstrap_packets,
            "projection_snapshot_path": str(projection_snapshot_file),
            "projection_snapshot_bytes": context_engine_store._safe_file_size(projection_snapshot_file),
            "compiler_manifest_path": str(compiler_manifest_path),
            "compiler_manifest_bytes": context_engine_store._safe_file_size(compiler_manifest_path),
            "architecture_bundle_path": str(architecture_bundle_path),
            "architecture_bundle_bytes": context_engine_store._safe_file_size(architecture_bundle_path),
            "odylith_memory_root": str(context_engine_store.odylith_memory_backend.local_backend_root(repo_root=root)),
            "judgment_memory_path": str(context_engine_store.judgment_memory_path(repo_root=root)),
        },
        "optimization": {
            "contract": "optimization_snapshot.v1",
            "status": str(optimization.get("status", "")).strip(),
            "sample_size": int(optimization.get("sample_size", 0) or 0),
            "overall": dict(optimization.get("overall", {}))
            if isinstance(optimization.get("overall"), Mapping)
            else {},
            "coverage_rate": float(evaluation.get("coverage_rate", 0.0) or 0.0),
            "satisfaction_rate": float(evaluation.get("satisfaction_rate", 0.0) or 0.0),
        },
        "remote_retrieval": {
            "provider": str(remote_config.get("provider", "")).strip(),
            "enabled": bool(remote_config.get("enabled")),
            "configured": bool(remote_config.get("configured")),
            "status": str(remote_config.get("status", "")).strip(),
            "mode": str(remote_config.get("mode", "")).strip(),
            "base_url": str(remote_config.get("base_url", "")).strip(),
            "schema": str(remote_config.get("schema", "")).strip(),
            "namespace": str(remote_config.get("namespace", "")).strip(),
            "issues": list(remote_config.get("issues", [])) if isinstance(remote_config.get("issues"), list) else [],
            "action": str(remote_config.get("action", "")).strip(),
            "state": dict(remote_config.get("state", {})) if isinstance(remote_config.get("state"), Mapping) else {},
        },
        "ingest_policy": {
            "allowlisted_sources": [
                "backlog_markdown",
                "plan_markdown",
                "bug_markdown",
                "component_registry",
                "mermaid_catalog",
                "delivery_intelligence_artifacts",
                "engineering_guidance",
                "python_source",
                "pytest_source",
            ],
            "secret_redaction_required": True,
            "provenance_required": True,
            "repo_truth_read_only": True,
        },
    }
    payload["judgment_memory"] = odylith_context_engine_judgment_memory_runtime.build_judgment_memory_snapshot(
        context_engine_store=context_engine_store,
        repo_root=root,
        projection_updated_utc=str(state.get("updated_utc", "")).strip(),
        backlog_projection=backlog_projection,
        plan_projection=plan_projection,
        bug_projection=bug_projection,
        diagram_projection=diagram_projection,
        runtime_state=payload.get("runtime_state", {}),
        optimization=optimization,
        evaluation=evaluation,
        benchmark_report=context_engine_store._load_latest_benchmark_report_snapshot(repo_root=root),
        recent_bootstrap_packets=recent_bootstrap_packets,
        active_sessions=active_session_rows,
        repo_dirty_paths=repo_dirty_paths,
        welcome_state=welcome_state,
        previous_snapshot=previous_judgment_memory,
        retrieval_state=context_engine_store._derive_retrieval_memory_state(
            transition_status=effective_convergence_state,
            indexed_entities=indexed_entity_count,
            evidence_documents=counts["evidence_documents"],
            compiler_ready=bool(compiler_manifest.get("ready")),
        ),
    )
    context_engine_store.odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=context_engine_store.judgment_memory_path(repo_root=root),
        payload=payload["judgment_memory"],
        lock_key=str(context_engine_store.judgment_memory_path(repo_root=root)),
    )
    payload["memory_areas"] = _build_memory_areas_snapshot(
        enabled=True,
        authoritative_truth=payload.get("authoritative_truth", {}),
        compiler_state=payload.get("compiler_state", {}),
        guidance_catalog=payload.get("guidance_catalog", {}),
        runtime_state=payload.get("runtime_state", {}),
        entity_counts=payload.get("entity_counts", {}),
        backend_transition=payload.get("backend_transition", {}),
        optimization=payload.get("optimization", {}),
        evaluation=evaluation,
        judgment_memory=payload.get("judgment_memory", {}),
    )
    payload["headline"] = str(payload["memory_areas"].get("headline", "")).strip()
    return payload


def _architecture_evaluation_snapshot(
    *,
    repo_root: Path,
    corpus: Mapping[str, Any],
    focus_limit: int = 4,
    timing_limit: int = 48,
) -> dict[str, Any]:
    return odylith_context_engine_architecture_evaluation_runtime.build_architecture_evaluation_snapshot(
        context_engine_store=context_engine_store,
        repo_root=repo_root,
        corpus=corpus,
        focus_limit=focus_limit,
        timing_limit=timing_limit,
    )


def load_runtime_evaluation_snapshot(
    *,
    repo_root: Path,
    bootstrap_limit: int = 24,
) -> dict[str, Any]:
    """Summarize benchmark-corpus coverage and drift against recent runtime packets."""

    root = Path(repo_root).resolve()
    odylith_switch = context_engine_store._odylith_switch_snapshot(repo_root=root)
    if not bool(odylith_switch.get("enabled", True)):
        return context_engine_store._odylith_disabled_evaluation_snapshot(
            repo_root=root,
            switch_snapshot=odylith_switch,
        )
    corpus = context_engine_store.odylith_context_cache.read_json_object(context_engine_store.optimization_evaluation_corpus_path(repo_root=root))
    if not isinstance(corpus, Mapping):
        corpus = {}
    cases = context_engine_store.odylith_benchmark_contract.packet_benchmark_scenarios(corpus)
    program = dict(corpus.get("program", {})) if isinstance(corpus.get("program"), Mapping) else {}
    architecture_snapshot = _architecture_evaluation_snapshot(
        repo_root=root,
        corpus=corpus,
        focus_limit=4,
        timing_limit=max(24, bootstrap_limit * 2),
    )

    def _normalized_program_snapshot(default_status: str) -> dict[str, str]:
        status = str(program.get("status", default_status)).strip().lower() or default_status
        active_wave_id = str(program.get("active_wave_id", "W2")).strip() or "W2"
        active_workstream_id = str(program.get("active_workstream_id", "B-241")).strip() or "B-241"
        if status == "complete":
            active_wave_id = ""
            active_workstream_id = ""
        return {
            "umbrella_id": str(program.get("umbrella_id", "B-238")).strip() or "B-238",
            "status": status,
            "active_wave_id": active_wave_id,
            "active_workstream_id": active_workstream_id,
        }

    if not cases:
        return {
            "contract": "evaluation_snapshot.v1",
            "version": "v1",
            "generated_utc": context_engine_store._utc_now(),
            "odylith_switch": odylith_switch,
            "status": "unseeded",
            "program": _normalized_program_snapshot("planned"),
            "corpus_size": 0,
            "covered_case_count": 0,
            "satisfied_case_count": 0,
            "coverage_rate": 0.0,
            "satisfaction_rate": 0.0,
            "family_distribution": {},
            "status_distribution": {},
            "focus_cases": [],
            "architecture": architecture_snapshot,
            "recommendations": [
                "Benchmark corpus is not seeded yet; add Wave 2 benchmark cases before treating evaluation posture as meaningful."
            ],
        }

    packets = context_engine_store._load_recent_bootstrap_packets(repo_root=root, bootstrap_limit=bootstrap_limit)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    family_distribution = context_engine_store._sorted_count_map([str(row.get("family", "")).strip() for row in cases])
    covered_count = 0
    satisfied_count = 0
    case_rows: list[dict[str, Any]] = []
    for case in cases:
        match_spec = dict(case.get("match", {})) if isinstance(case.get("match"), Mapping) else {}
        expect_spec = dict(case.get("expect", {})) if isinstance(case.get("expect"), Mapping) else {}
        latest_packet = next((packet for packet in packets if context_engine_store._packet_matches_evaluation_case(packet, match_spec)), None)
        case_status = "unmatched"
        expectation_details: dict[str, Any] = {}
        if latest_packet is not None:
            covered_count += 1
            expectation_ok, expectation_details = context_engine_store._packet_satisfies_evaluation_expectations(latest_packet, expect_spec)
            if expectation_ok:
                satisfied_count += 1
                case_status = "satisfied"
            else:
                case_status = "drift"
        case_rows.append(
            {
                "case_id": str(case.get("case_id", "")).strip(),
                "label": str(case.get("label", "")).strip(),
                "family": str(case.get("family", "")).strip(),
                "priority": str(case.get("priority", "medium")).strip().lower() or "medium",
                "status": case_status,
                "summary": str(case.get("summary", "")).strip(),
                "latest_match_utc": str(latest_packet.get("bootstrapped_at", "")).strip() if latest_packet else "",
                "matched_workstream": str(latest_packet.get("workstream", "")).strip() if latest_packet else "",
                "observed_packet_state": str(latest_packet.get("packet_state", "")).strip() if latest_packet else "",
                "expected_packet_state": sorted(context_engine_store._expected_token_set(expect_spec.get("packet_state"))),
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
    corpus_size = len(cases)
    coverage_rate = round(covered_count / max(1, corpus_size), 3)
    satisfaction_rate = round(satisfied_count / max(1, covered_count), 3) if covered_count else 0.0
    status_distribution = context_engine_store._sorted_count_map([str(row.get("status", "")).strip() for row in case_rows])
    recommendations: list[str] = []
    if not packets:
        recommendations.append(
            f"Benchmark corpus is seeded but no recent runtime packet evidence is available yet; run `{context_engine_store.display_command('context-engine', '--repo-root', '.', 'bootstrap-session', '<path>')}` on a benchmarked slice."
        )
    drift_cases = [str(row.get("label", "")).strip() for row in case_rows if str(row.get("status", "")).strip() == "drift"]
    unmatched_cases = [str(row.get("label", "")).strip() for row in case_rows if str(row.get("status", "")).strip() == "unmatched"]
    if drift_cases:
        recommendations.append(
            f"Recent packets drifted from expected posture for {', '.join(drift_cases[:2])}; inspect the latest matching bootstrap packet before widening the next tuning change."
        )
    if unmatched_cases:
        recommendations.append(
            f"Uncovered benchmark cases remain: {', '.join(unmatched_cases[:2])}. Exercise those slices before treating Wave 2 coverage as representative."
        )
    if not recommendations:
        recommendations.append(
            "Wave 2 benchmark coverage is healthy on the current sample; use these cases as the comparison baseline for later routing or retrieval changes."
        )
    return {
        "contract": "evaluation_snapshot.v1",
        "version": "v1",
        "generated_utc": context_engine_store._utc_now(),
        "odylith_switch": odylith_switch,
        "status": "active" if packets else "seeded_no_evidence",
        "program": _normalized_program_snapshot("active"),
        "corpus_size": corpus_size,
        "covered_case_count": covered_count,
        "satisfied_case_count": satisfied_count,
        "coverage_rate": coverage_rate,
        "satisfaction_rate": satisfaction_rate,
        "family_distribution": family_distribution,
        "status_distribution": status_distribution,
        "focus_cases": case_rows[:4],
        "architecture": architecture_snapshot,
        "recommendations": recommendations[:3],
    }
# Keep the store dependency explicit without pulling it through module bootstrap.
from odylith.runtime.context_engine import odylith_context_engine_store as context_engine_store

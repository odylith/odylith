"""Focused memory-area synthesis for the context-engine memory snapshot."""

from __future__ import annotations

from typing import Any
from typing import Mapping


def build_memory_areas_snapshot(
    *,
    context_engine_store: Any,
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
    if not enabled:
        areas = [
            context_engine_store._memory_area_entry(
                key=key,
                label=label,
                state="disabled",
                summary="Odylith is disabled, so this memory area is suppressed for ablation runs.",
            )
            for key, label in (
                ("repo_truth", "Repo truth"),
                ("retrieval", "Retrieval memory"),
                ("guidance", "Guidance memory"),
                ("session_packets", "Session packet memory"),
                ("outcomes", "Outcome memory"),
                ("decisions", "Decision memory"),
                ("collaboration", "Collaboration memory"),
                ("contradictions", "Contradiction memory"),
            )
        ]
        return {
            "contract": "memory_areas.v1",
            "status": "disabled",
            "headline": "Odylith is disabled, so memory-area posture is suppressed for this run.",
            "counts": {"disabled": len(areas)},
            "gap_count": len(areas),
            "areas": areas,
            "gaps": [
                "Odylith is disabled; memory-area posture and gap analysis are intentionally suppressed."
            ],
        }

    read_only_repo_truth = bool(authoritative_truth.get("read_only_repo_truth"))
    compiler_ready = bool(compiler_state.get("ready"))
    guidance_chunks = int(guidance_catalog.get("chunk_count", 0) or 0)
    guidance_docs = int(guidance_catalog.get("source_doc_count", 0) or 0)
    guidance_families = int(guidance_catalog.get("task_family_count", 0) or 0)
    active_sessions = int(runtime_state.get("active_sessions", 0) or 0)
    bootstrap_packets = int(runtime_state.get("bootstrap_packets", 0) or 0)
    indexed_entities = int(entity_counts.get("indexed_entity_count", 0) or 0)
    evidence_documents = int(entity_counts.get("evidence_documents", 0) or 0)
    sample_size = int(optimization.get("sample_size", 0) or 0)
    coverage_rate = float(
        optimization.get("coverage_rate", evaluation.get("coverage_rate", 0.0)) or 0.0
    )
    satisfaction_rate = float(
        optimization.get("satisfaction_rate", evaluation.get("satisfaction_rate", 0.0)) or 0.0
    )
    transition_status = str(backend_transition.get("status", "")).strip().lower()
    actual_backend = (
        dict(backend_transition.get("actual_local_backend", {}))
        if isinstance(backend_transition.get("actual_local_backend"), Mapping)
        else {}
    )
    actual_storage = str(actual_backend.get("storage", "")).strip() or "compiler snapshot"
    actual_sparse = str(actual_backend.get("sparse_recall", "")).strip() or "repo scan fallback"

    retrieval_state = context_engine_store._derive_retrieval_memory_state(
        transition_status=transition_status,
        indexed_entities=indexed_entities,
        evidence_documents=evidence_documents,
        compiler_ready=compiler_ready,
    )

    guidance_state = "cold"
    if guidance_chunks > 0 and guidance_families > 0:
        guidance_state = "strong"
    elif guidance_chunks > 0 or guidance_docs > 0 or guidance_families > 0:
        guidance_state = "partial"

    session_state = "cold"
    if active_sessions > 0:
        session_state = "strong"
    elif bootstrap_packets > 0:
        session_state = "partial"

    outcome_state = "cold"
    if sample_size >= 5 or coverage_rate >= 0.5 or satisfaction_rate >= 0.5:
        outcome_state = "strong"
    elif sample_size > 0 or coverage_rate > 0.0 or satisfaction_rate > 0.0:
        outcome_state = "partial"

    judgment_areas = [
        dict(row)
        for row in dict(judgment_memory or {}).get("areas", [])
        if isinstance(dict(judgment_memory or {}).get("areas"), list) and isinstance(row, Mapping)
    ]
    judgment_by_key = {
        str(row.get("key", "")).strip(): row
        for row in judgment_areas
        if str(row.get("key", "")).strip()
    }
    decisions_row = dict(judgment_by_key.get("decisions", {}))
    collaboration_row = dict(judgment_by_key.get("workspace_actor", {}))
    contradictions_row = dict(judgment_by_key.get("contradictions", {}))
    outcomes_row = dict(judgment_by_key.get("outcomes", {}))

    areas = [
        context_engine_store._memory_area_entry(
            key="repo_truth",
            label="Repo truth",
            state="strong" if read_only_repo_truth else "partial",
            summary=(
                "Git-tracked backlog, plans, bugs, diagrams, components, and code remain authoritative."
                if read_only_repo_truth
                else "Repo truth exists, but the read-only authority boundary is not fully enforced."
            ),
        ),
        context_engine_store._memory_area_entry(
            key="retrieval",
            label="Retrieval memory",
            state=retrieval_state,
            summary=(
                f"{actual_storage} / {actual_sparse} is active across {indexed_entities} indexed entities and {evidence_documents} retained evidence docs."
                if retrieval_state != "cold"
                else "No meaningful indexed retrieval footprint is materialized yet."
            ),
        ),
        context_engine_store._memory_area_entry(
            key="guidance",
            label="Guidance memory",
            state=guidance_state,
            summary=(
                f"{guidance_chunks} compiled guidance chunks across {guidance_docs} docs and {guidance_families} task families shape packet grounding."
                if guidance_state != "cold"
                else "No compiled guidance catalog is ready yet."
            ),
        ),
        context_engine_store._memory_area_entry(
            key="session_packets",
            label="Session packet memory",
            state=session_state,
            summary=(
                f"{active_sessions} active sessions and {bootstrap_packets} retained bootstrap packet(s) are available for recent-session recall."
                if session_state == "strong"
                else f"{bootstrap_packets} retained bootstrap packet(s) are available, but no active session memory is warm."
                if session_state == "partial"
                else "No active session or bootstrap packet memory is warm yet."
            ),
        ),
        context_engine_store._memory_area_entry(
            key="outcomes",
            label="Outcome memory",
            state=str(outcomes_row.get("state", "")).strip() or outcome_state,
            summary=(
                str(outcomes_row.get("summary", "")).strip()
                or (
                    f"{sample_size} sampled packet(s), {coverage_rate:.0%} coverage, and {satisfaction_rate:.0%} satisfaction are available for outcome learning."
                    if outcome_state != "cold"
                    else "No meaningful optimization or evaluation outcome memory is available yet."
                )
            ),
        ),
        context_engine_store._memory_area_entry(
            key="decisions",
            label="Decision memory",
            state=str(decisions_row.get("state", "")).strip() or "planned",
            summary=(
                str(decisions_row.get("summary", "")).strip()
                or "Resolved decisions, reversals, and proof outcomes are not first-class durable memory yet."
            ),
        ),
        context_engine_store._memory_area_entry(
            key="collaboration",
            label="Workspace and actor memory",
            state=str(collaboration_row.get("state", "")).strip() or "planned",
            summary=(
                str(collaboration_row.get("summary", "")).strip()
                or "Workspace, actor, and shared-ownership memory are not first-class durable memory yet."
            ),
        ),
        context_engine_store._memory_area_entry(
            key="contradictions",
            label="Contradiction memory",
            state=str(contradictions_row.get("state", "")).strip() or "planned",
            summary=(
                str(contradictions_row.get("summary", "")).strip()
                or "Cross-surface disagreements are detected per run, but they are not stored as durable named memory yet."
            ),
        ),
    ]
    counts: dict[str, int] = {}
    gaps: list[str] = []
    for row in areas:
        state = str(row.get("state", "")).strip() or "unknown"
        counts[state] = counts.get(state, 0) + 1
        if state in {"partial", "cold", "planned"}:
            label = str(row.get("label", "")).strip() or "Memory area"
            summary = str(row.get("summary", "")).strip()
            gaps.append(f"{label}: {summary}" if summary else label)
    return {
        "contract": "memory_areas.v1",
        "status": context_engine_store._memory_snapshot_status_from_counts(counts),
        "headline": context_engine_store._memory_areas_headline(areas),
        "counts": counts,
        "gap_count": len(gaps),
        "areas": areas,
        "gaps": gaps,
    }

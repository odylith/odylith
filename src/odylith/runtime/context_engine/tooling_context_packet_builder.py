"""Packet-plane helpers for Odylith Context Engine context assembly."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.evaluation import odylith_ablation
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import tooling_context_budgeting as budgeting
from odylith.runtime.memory import tooling_memory_contracts
from odylith.runtime.context_engine import tooling_context_quality as quality
from odylith.runtime.context_engine import tooling_context_retrieval as retrieval
from odylith.runtime.context_engine import tooling_context_routing as routing
from odylith.runtime.context_engine import tooling_guidance_catalog
from odylith.runtime.governance import delivery_intelligence_engine
from odylith.runtime.governance import proof_state

_PROCESS_HOT_PATH_PACKET_QUALITY_CACHE: dict[str, dict[str, Any]] = {}
_PROCESS_HOT_PATH_ROUTING_HANDOFF_CACHE: dict[str, dict[str, Any]] = {}


def _mapping_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_rows(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value] if isinstance(value, list) else []


def _string_rows(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _guidance_actionability_read_path(row: Mapping[str, Any]) -> str:
    actionability = _mapping_value(row.get("actionability"))
    return str(actionability.get("read_path", "")).strip() or str(row.get("read_path", "")).strip()


def _guidance_evidence_score(row: Mapping[str, Any]) -> int:
    evidence_summary = _mapping_value(row.get("evidence_summary"))
    raw = evidence_summary.get("score", row.get("score"))
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def _merge_guidance_row(primary: Mapping[str, Any], secondary: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    for key in ("chunk_id", "title", "summary", "canonical_source", "risk_class", "note_kind", "match_tier", "read_path"):
        if not str(merged.get(key, "")).strip():
            token = str(secondary.get(key, "")).strip()
            if token:
                merged[key] = token
    merged_signals = _string_rows(list(merged.get("signals", [])) + list(secondary.get("signals", [])))
    if merged_signals:
        merged["signals"] = merged_signals[:3]
    primary_evidence = _mapping_value(merged.get("evidence_summary"))
    secondary_evidence = _mapping_value(secondary.get("evidence_summary"))
    if secondary_evidence:
        merged_evidence = dict(secondary_evidence)
        merged_evidence.update({key: value for key, value in primary_evidence.items() if value not in ("", [], {}, None)})
        merged["evidence_summary"] = {
            key: value
            for key, value in merged_evidence.items()
            if value not in ("", [], {}, None)
        }
    primary_actionability = _mapping_value(merged.get("actionability"))
    secondary_actionability = _mapping_value(secondary.get("actionability"))
    if secondary_actionability:
        merged_actionability = dict(secondary_actionability)
        merged_actionability.update({key: value for key, value in primary_actionability.items() if value not in ("", [], {}, None)})
        if not str(merged_actionability.get("read_path", "")).strip():
            read_path = _guidance_actionability_read_path(secondary)
            if read_path:
                merged_actionability["read_path"] = read_path
        signals = _string_rows(
            list(merged_actionability.get("signals", []))
            + list(primary_actionability.get("signals", []))
            + list(secondary_actionability.get("signals", []))
        )
        if signals:
            merged_actionability["signals"] = signals[:3]
        merged["actionability"] = {
            key: value
            for key, value in merged_actionability.items()
            if value not in ("", [], {}, None)
        }
    if not _guidance_evidence_score(merged):
        fallback_score = _guidance_evidence_score(secondary)
        if fallback_score:
            merged["score"] = fallback_score
    return merged


def _merge_guidance_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    detail_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not rows:
        return []
    detail_map: dict[str, dict[str, Any]] = {}
    for source in (*detail_rows, *rows):
        if not isinstance(source, Mapping):
            continue
        chunk_id = str(source.get("chunk_id", "")).strip()
        if not chunk_id:
            continue
        current = detail_map.get(chunk_id)
        if current is None:
            detail_map[chunk_id] = dict(source)
            continue
        detail_map[chunk_id] = _merge_guidance_row(current, source)
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        chunk_id = str(row.get("chunk_id", "")).strip()
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        merged.append(detail_map.get(chunk_id, dict(row)))
    return merged


def _nested_mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, {})
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _delivery_scope_lookup(repo_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Mapping[str, Any]]]:
    payload = delivery_intelligence_engine.load_delivery_intelligence_artifact(repo_root=repo_root)
    scopes = payload.get("scopes", []) if isinstance(payload.get("scopes"), list) else []
    indexes = payload.get("indexes", {}) if isinstance(payload.get("indexes"), Mapping) else {}
    scope_lookup = {
        str(row.get("scope_key", "")).strip(): dict(row)
        for row in scopes
        if isinstance(row, Mapping) and str(row.get("scope_key", "")).strip()
    }
    return scope_lookup, indexes


def _packet_proof_anchor_scope_keys(
    *,
    indexes: Mapping[str, Any],
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
) -> list[str]:
    rows: list[str] = []
    workstream_index = indexes.get("workstreams", {}) if isinstance(indexes.get("workstreams"), Mapping) else {}
    component_index = indexes.get("components", {}) if isinstance(indexes.get("components"), Mapping) else {}
    diagram_index = indexes.get("diagrams", {}) if isinstance(indexes.get("diagrams"), Mapping) else {}
    selected = workstream_selection.get("selected_workstream")
    if isinstance(selected, Mapping):
        token = str(selected.get("entity_id", "")).strip()
        if token and token in workstream_index:
            rows.append(str(workstream_index.get(token, "")).strip())
    for row in candidate_workstreams:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("entity_id", "")).strip()
        if token and token in workstream_index:
            rows.append(str(workstream_index.get(token, "")).strip())
    for row in components:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("component_id", row.get("entity_id", ""))).strip()
        if token and token in component_index:
            rows.append(str(component_index.get(token, "")).strip())
    for row in diagrams:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("diagram_id", row.get("entity_id", ""))).strip()
        if token and token in diagram_index:
            rows.append(str(diagram_index.get(token, "")).strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for token in rows:
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _packet_proof_state(
    *,
    repo_root: Path,
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope_lookup, indexes = _delivery_scope_lookup(repo_root)
    candidate_scope_keys = _packet_proof_anchor_scope_keys(
        indexes=indexes,
        workstream_selection=workstream_selection,
        candidate_workstreams=candidate_workstreams,
        components=components,
        diagrams=diagrams,
    )
    candidate_scopes = [
        scope_lookup[key]
        for key in candidate_scope_keys
        if key in scope_lookup and isinstance(scope_lookup[key], Mapping)
    ]
    return proof_state.resolve_scope_collection_proof_state(candidate_scopes)


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _odylith_switch_snapshot(*, repo_root: Path) -> dict[str, Any]:
    return dict(odylith_ablation.build_odylith_switch_snapshot(repo_root=Path(repo_root).resolve()))


def _compact_finalize_test_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for row in rows[: max(1, int(limit))]:
        if not isinstance(row, Mapping):
            continue
        compact: dict[str, Any] = {}
        for key in ("path", "nodeid", "reason"):
            token = str(row.get(key, "")).strip()
            if token:
                compact[key] = token
        if compact:
            compacted.append(compact)
    return compacted


def _compact_finalize_workstream_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for row in rows[: max(1, int(limit))]:
        if not isinstance(row, Mapping):
            continue
        compact: dict[str, Any] = {}
        for key in ("entity_id", "title"):
            token = str(row.get(key, "")).strip()
            if token:
                compact[key] = token
        if compact:
            compacted.append(compact)
    return compacted


def _compact_finalize_guidance_catalog(summary: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in ("version", "chunk_count", "source_doc_count"):
        value = summary.get(key)
        if value is None or value == "" or value == []:
            continue
        compact[key] = value
    task_families = summary.get("task_families")
    if isinstance(task_families, list):
        compact["task_family_count"] = len([str(token).strip() for token in task_families if str(token).strip()])
    return compact


def _compact_finalize_retrieval_plan(plan: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(plan)
    guidance_rows = _mapping_rows(compacted.get("selected_guidance_chunks"))
    bootstrap_packet = str(packet_kind or "").strip() == "bootstrap_session"
    compact_bootstrap = bootstrap_packet and str(packet_state or "").strip() == "compact"
    gated_bootstrap = bootstrap_packet and str(packet_state or "").strip().startswith("gated_")
    strict_bootstrap = compact_bootstrap or gated_bootstrap
    if guidance_rows and not strict_bootstrap:
        compacted["selected_guidance_chunks"] = retrieval.compact_guidance_brief(
            guidance_rows,
            limit=1 if bootstrap_packet else 2,
        )
    workstream_rows = _mapping_rows(compacted.get("selected_workstreams"))
    if workstream_rows:
        compacted["selected_workstreams"] = _compact_finalize_workstream_rows(
            workstream_rows,
            limit=2 if str(packet_kind or "").strip() == "bootstrap_session" else 3,
        )
    if bootstrap_packet:
        guidance_rows = _mapping_rows(compacted.get("selected_guidance_chunks"))
        if guidance_rows and strict_bootstrap:
            compacted["selected_guidance_chunks"] = [
                {
                    key: value
                    for key, value in {
                        "chunk_id": str(row.get("chunk_id", "")).strip(),
                        "title": str(row.get("title", "")).strip(),
                        "match_tier": str(row.get("match_tier", "")).strip(),
                        "score": _guidance_evidence_score(row),
                        "read_path": _guidance_actionability_read_path(row),
                        "canonical_source": str(row.get("canonical_source", "")).strip(),
                        "signals": _string_rows(
                            list(_mapping_value(row.get("actionability")).get("signals", []))
                            + list(row.get("signals", []))
                        )[:3],
                    }.items()
                    if value not in ("", [], {}, None, 0)
                }
                for row in guidance_rows[:1]
                if isinstance(row, Mapping)
            ]
        selected_docs = _string_rows(compacted.get("selected_docs"))
        doc_limit = 1 if strict_bootstrap else 2
        if len(selected_docs) > doc_limit:
            compacted["selected_docs"] = selected_docs[:doc_limit]
        selected_commands = _string_rows(compacted.get("selected_commands"))
        command_limit = 1 if strict_bootstrap else 2
        if len(selected_commands) > command_limit:
            compacted["selected_commands"] = selected_commands[:command_limit]
        selected_tests = _mapping_rows(compacted.get("selected_tests"))
        test_limit = 1 if strict_bootstrap else 2
        if len(selected_tests) > test_limit:
            compacted["selected_tests"] = _compact_finalize_test_rows(selected_tests, limit=test_limit)
        selected_domains = _string_rows(compacted.get("selected_domains"))
        domain_limit = 2 if gated_bootstrap else 3 if compact_bootstrap else 4
        if len(selected_domains) > domain_limit:
            compacted["selected_domains"] = selected_domains[:domain_limit]
        for key in ("anchor_paths", "explicit_paths", "shared_anchor_paths"):
            values = _string_rows(compacted.get(key))
            if len(values) > 2:
                compacted[key] = values[:2]
        if compact_bootstrap:
            for key in ("evidence_profile", "actionability_profile"):
                compacted.pop(key, None)
    guidance_catalog = _mapping_value(compacted.get("guidance_catalog"))
    if guidance_catalog:
        compacted["guidance_catalog"] = _compact_finalize_guidance_catalog(guidance_catalog)
    if str(packet_kind or "").strip() == "bootstrap_session" and str(packet_state or "").strip().startswith("gated_"):
        essential_keys = {
            "version",
            "packet_kind",
            "packet_state",
            "selection_state",
            "full_scan_reason",
            "anchor_paths",
            "anchor_quality",
            "has_non_shared_anchor",
            "guidance_coverage",
            "evidence_consensus",
            "ambiguity_class",
            "precision_score",
            "routing_confidence",
            "reasoning_bias",
            "parallelism_hint",
            "selected_domains",
            "selected_guidance_chunks",
            "miss_recovery",
        }
        compacted = {
            key: value
            for key, value in compacted.items()
            if key in essential_keys and value not in (None, "", [], {}, False)
        }
    return compacted


def _compact_finalize_working_memory_tiers(
    tiers: Mapping[str, Any],
    *,
    packet_kind: str,
    packet_state: str,
) -> dict[str, Any]:
    compacted = dict(tiers)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    gated_bootstrap = str(packet_state or "").strip().startswith("gated_")
    for tier_name in ("cold", "warm", "hot", "scratch"):
        row = _nested_mapping(compacted, tier_name)
        if not row:
            continue
        row.pop("description", None)
        if tier_name == "cold":
            sources = _string_rows(row.get("sources"))
            if gated_bootstrap:
                row = {"source_count": len(sources)}
            elif len(sources) > 4:
                row["sources"] = sources[:4]
        elif tier_name == "hot":
            commands = _string_rows(row.get("recommended_commands"))
            tests = _mapping_rows(row.get("recommended_tests"))
            if gated_bootstrap:
                row = {
                    key: value
                    for key, value in {
                        "changed_paths": _string_rows(row.get("changed_paths"))[:1],
                        "command_count": len(commands),
                        "test_count": len(tests),
                    }.items()
                    if value not in ("", [], {}, None, 0)
                }
            else:
                if len(commands) > 1:
                    row["recommended_commands"] = commands[:1]
                if len(tests) > 1:
                    row["recommended_tests"] = _compact_finalize_test_rows(tests, limit=1)
        elif tier_name == "warm":
            docs = _string_rows(row.get("docs"))
            guidance_chunks = _mapping_rows(row.get("guidance_chunks"))
            workstreams = _mapping_rows(row.get("workstreams"))
            if gated_bootstrap:
                row = {
                    key: value
                    for key, value in {
                        "doc_count": len(docs),
                        "guidance_count": len(guidance_chunks),
                        "workstream_count": len(workstreams),
                    }.items()
                    if value not in ("", [], {}, None, 0)
                }
            else:
                if len(docs) > 1:
                    row["docs"] = docs[:1]
                if guidance_chunks:
                    row["guidance_chunks"] = retrieval.compact_guidance_brief(guidance_chunks, limit=1)
                if workstreams:
                    row["workstreams"] = _compact_finalize_workstream_rows(workstreams, limit=1)
        elif tier_name == "scratch" and gated_bootstrap:
            row = {
                key: value
                for key, value in {
                    "session_id": str(row.get("session_id", "")).strip(),
                    "selection_state": str(row.get("selection_state", "")).strip(),
                }.items()
                if value not in ("", [], {}, None)
            }
        compacted[tier_name] = row
    return compacted


def _compact_finalize_engineering_notes(notes: Mapping[str, Any], *, packet_kind: str) -> dict[str, Any]:
    compacted = dict(notes)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    normalized: dict[str, Any] = {}
    for kind, rows in compacted.items():
        if not isinstance(rows, list):
            continue
        compact_rows: list[dict[str, Any]] = []
        for row in rows[:1]:
            if not isinstance(row, Mapping):
                continue
            compact: dict[str, Any] = {}
            for key in ("kind", "note_id", "title", "summary", "source_path"):
                token = str(row.get(key, "")).strip()
                if token:
                    compact[key] = token
            if compact:
                compact_rows.append(compact)
        if compact_rows:
            normalized[str(kind).strip()] = compact_rows
    return normalized


def _compact_finalize_impact_summary(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() not in {"bootstrap_session", "session_brief"}:
        return compacted
    session_brief_packet = str(packet_kind or "").strip() == "session_brief"
    primary = _nested_mapping(compacted, "primary_workstream")
    if primary:
        compacted["primary_workstream"] = {
            key: value
            for key, value in {
                "entity_id": str(primary.get("entity_id", "")).strip(),
                "title": str(primary.get("title", "")).strip(),
                "status": str(primary.get("status", "")).strip(),
                "rank": primary.get("rank"),
            }.items()
            if value not in ("", [], {}, None)
        }
    workstreams = _mapping_rows(compacted.get("workstreams"))
    if workstreams:
        compacted["workstreams"] = _compact_finalize_workstream_rows(
            workstreams,
            limit=1 if str(packet_state or "").strip() == "gated_broad_scope" or session_brief_packet else 2,
        )
    guidance_brief = _mapping_rows(compacted.get("guidance_brief"))
    if guidance_brief:
        compacted["guidance_brief"] = retrieval.compact_guidance_brief(
            guidance_brief,
            limit=1,
        )
    miss_recovery = _nested_mapping(compacted, "miss_recovery")
    if miss_recovery:
        compacted["miss_recovery"] = _compact_finalize_miss_recovery(
            miss_recovery,
            packet_kind=packet_kind,
        )
    if session_brief_packet:
        docs = _string_rows(compacted.get("docs"))
        if len(docs) > 1:
            compacted["docs"] = docs[:1]
        recommended_commands = _string_rows(compacted.get("recommended_commands"))
        if len(recommended_commands) > 1:
            compacted["recommended_commands"] = recommended_commands[:1]
        recommended_tests = _mapping_rows(compacted.get("recommended_tests"))
        if recommended_tests:
            compacted["recommended_tests"] = _compact_finalize_test_rows(recommended_tests, limit=1)
        engineering_notes = _nested_mapping(compacted, "engineering_notes")
        if engineering_notes:
            compacted["engineering_notes"] = _compact_finalize_engineering_notes(
                engineering_notes,
                packet_kind="bootstrap_session",
            )
    compacted.pop("components", None)
    compacted.pop("diagrams", None)
    return {key: value for key, value in compacted.items() if value not in ("", [], {}, None)}


def _compact_finalize_miss_recovery(summary: Mapping[str, Any], *, packet_kind: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    keep = {
        "active",
        "applied",
        "mode",
        "activation_reason",
        "queries",
        "recovered_docs",
    }
    compacted = {
        key: value
        for key, value in compacted.items()
        if key in keep and value not in ("", [], {}, None, False)
    }
    queries = _string_rows(compacted.get("queries"))
    if len(queries) > 1:
        compacted["queries"] = queries[:1]
    docs = _string_rows(compacted.get("recovered_docs"))
    if len(docs) > 1:
        compacted["recovered_docs"] = docs[:1]
    return compacted


def _compact_finalize_session(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    if str(packet_state or "").strip().startswith("gated_"):
        keep = {
            "session_id",
            "updated_utc",
            "workstream",
            "intent",
            "touched_paths",
            "explicit_paths",
            "analysis_paths",
            "claim_mode",
            "selection_state",
            "selection_reason",
            "claimed_workstreams",
            "claimed_paths",
            "working_tree_scope",
        }
        compacted = {
            key: value
            for key, value in compacted.items()
            if key in keep and (key in {"workstream", "claimed_workstreams", "claimed_paths"} or value not in ("", [], {}, None))
        }
    return compacted


def _compact_finalize_narrowing_guidance(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    suggested_inputs = _string_rows(compacted.get("suggested_inputs"))
    if len(suggested_inputs) > 3:
        compacted["suggested_inputs"] = suggested_inputs[:3]
    anchors = _mapping_rows(compacted.get("next_best_anchors"))
    if len(anchors) > 2:
        compacted["next_best_anchors"] = anchors[:2]
    if str(packet_state or "").strip() == "gated_broad_scope":
        keep = {
            "required",
            "reason",
            "suggested_inputs",
            "next_best_anchors",
            "next_fallback_command",
            "next_fallback_followup",
        }
        compacted = {key: value for key, value in compacted.items() if key in keep and value not in ("", [], {}, None)}
    return compacted


def _compact_finalize_runtime(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    timings = _nested_mapping(compacted, "timings")
    if timings:
        recent = _mapping_rows(timings.get("recent"))
        if recent:
            compact_recent: list[dict[str, Any]] = []
            for row in recent[:1]:
                compact_recent.append(
                    {
                        key: value
                        for key, value in {
                            "category": str(row.get("category", "")).strip(),
                            "operation": str(row.get("operation", "")).strip(),
                            "duration_ms": row.get("duration_ms"),
                        }.items()
                        if value not in ("", [], {}, None)
                    }
                )
            timings["recent"] = compact_recent
        if str(packet_state or "").strip().startswith("gated_"):
            timings.pop("operations", None)
        compacted["timings"] = timings
    return compacted


def _compact_finalize_packet_quality(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    normalized_state = str(packet_state or "").strip()
    if normalized_state != "compact" and not normalized_state.startswith("gated_"):
        return compacted
    intent_profile = _nested_mapping(compacted, "intent_profile")
    utility_profile = _nested_mapping(compacted, "utility_profile")
    token_efficiency = _nested_mapping(compacted, "token_efficiency")
    context_density = _nested_mapping(compacted, "context_density")
    evidence_diversity = _nested_mapping(compacted, "evidence_diversity")
    reasoning_readiness = _nested_mapping(compacted, "reasoning_readiness")
    evidence_quality = _nested_mapping(compacted, "evidence_quality")
    actionability = _nested_mapping(compacted, "actionability")
    validation_pressure = _nested_mapping(compacted, "validation_pressure")
    return {
        key: value
        for key, value in {
            "packet_kind": str(compacted.get("packet_kind", "")).strip(),
            "packet_state": str(compacted.get("packet_state", "")).strip(),
            "selection_state": str(compacted.get("selection_state", "")).strip(),
            "routing_confidence": str(compacted.get("routing_confidence", "")).strip(),
            "actionability_level": str(compacted.get("actionability_level", "")).strip(),
            "evidence_quality": {
                "score": _int_value(evidence_quality.get("score")),
                "level": str(evidence_quality.get("level", "")).strip(),
            }
            if evidence_quality
            else {},
            "actionability": {
                "score": _int_value(actionability.get("score")),
                "level": str(actionability.get("level", "")).strip(),
            }
            if actionability
            else {},
            "validation_pressure": {
                "score": _int_value(validation_pressure.get("score")),
                "level": str(validation_pressure.get("level", "")).strip(),
            }
            if validation_pressure
            else {},
            "intent_profile": {
                "family": str(intent_profile.get("family", "")).strip(),
                "mode": str(intent_profile.get("mode", "")).strip(),
                "explicit": bool(intent_profile.get("explicit")),
            }
            if intent_profile
            else {},
            "utility_profile": {
                "score": _int_value(utility_profile.get("score")),
                "level": str(utility_profile.get("level", "")).strip(),
                "token_efficiency": {
                    "score": _int_value(token_efficiency.get("score")),
                    "level": str(token_efficiency.get("level", "")).strip(),
                }
                if token_efficiency
                else {},
            }
            if utility_profile
            else {},
            "context_density": {
                "score": _int_value(context_density.get("score")),
                "level": str(context_density.get("level", "")).strip(),
            }
            if context_density
            else {},
            "evidence_diversity": {
                "score": _int_value(evidence_diversity.get("score")),
                "level": str(evidence_diversity.get("level", "")).strip(),
            }
            if evidence_diversity
            else {},
            "reasoning_readiness": {
                "score": _int_value(reasoning_readiness.get("score")),
                "level": str(reasoning_readiness.get("level", "")).strip(),
                "mode": str(reasoning_readiness.get("mode", "")).strip(),
            }
            if reasoning_readiness
            else {},
            "reasoning_bias": str(compacted.get("reasoning_bias", "")).strip(),
            "parallelism_hint": str(compacted.get("parallelism_hint", "")).strip(),
            "selected_guidance_chunk_count": _int_value(compacted.get("selected_guidance_chunk_count")),
            "direct_guidance_chunk_count": _int_value(compacted.get("direct_guidance_chunk_count")),
            "actionable_guidance_chunk_count": _int_value(compacted.get("actionable_guidance_chunk_count")),
            "retained_doc_count": _int_value(compacted.get("retained_doc_count")),
            "retained_test_count": _int_value(compacted.get("retained_test_count")),
            "retained_command_count": _int_value(compacted.get("retained_command_count")),
            "selected_domain_count": _int_value(compacted.get("selected_domain_count")),
            "within_budget": bool(compacted.get("within_budget")),
        }.items()
        if value not in ("", [], {}, None)
    }


def _compact_finalize_metadata(packet: Mapping[str, Any], *, budget_meta: Mapping[str, Any]) -> dict[str, Any]:
    compacted = dict(packet)
    budget_bytes = int(budget_meta.get("max_bytes", 0) or 0)
    budget_tokens = int(budget_meta.get("max_tokens", 0) or 0)
    packet_kind = str(_nested_mapping(compacted, "packet_metrics").get("packet_kind", "")).strip()
    packet_state = str(_nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip()
    for _ in range(4):
        actual_bytes = len(json.dumps(compacted, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        actual_tokens = int(math.ceil(actual_bytes / budgeting.ESTIMATED_BYTES_PER_TOKEN))
        if actual_bytes <= budget_bytes and actual_tokens <= budget_tokens:
            return compacted
        changed = False
        retrieval_plan = _nested_mapping(compacted, "retrieval_plan")
        if retrieval_plan:
            compact_plan = _compact_finalize_retrieval_plan(
                retrieval_plan,
                packet_kind=packet_kind,
                packet_state=str(_nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_plan != retrieval_plan:
                compacted["retrieval_plan"] = compact_plan
                changed = True
        working_memory_tiers = _nested_mapping(compacted, "working_memory_tiers")
        if working_memory_tiers:
            compact_tiers = _compact_finalize_working_memory_tiers(
                working_memory_tiers,
                packet_kind=packet_kind,
                packet_state=packet_state,
            )
            if compact_tiers != working_memory_tiers:
                compacted["working_memory_tiers"] = compact_tiers
                changed = True
        top_engineering_notes = _nested_mapping(compacted, "top_engineering_notes")
        if top_engineering_notes:
            compact_notes = _compact_finalize_engineering_notes(top_engineering_notes, packet_kind=packet_kind)
            if compact_notes != top_engineering_notes:
                compacted["top_engineering_notes"] = compact_notes
                changed = True
        impact_summary = _nested_mapping(compacted, "impact_summary")
        if impact_summary:
            compact_summary = _compact_finalize_impact_summary(
                impact_summary,
                packet_kind=packet_kind,
                packet_state=str(_nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_summary != impact_summary:
                compacted["impact_summary"] = compact_summary
                changed = True
        impact_payload = _nested_mapping(compacted, "impact")
        if impact_payload:
            compact_impact = _compact_finalize_impact_summary(
                impact_payload,
                packet_kind=packet_kind,
                packet_state=str(_nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_impact != impact_payload:
                compacted["impact"] = compact_impact
                changed = True
        session = _nested_mapping(compacted, "session")
        if session:
            compact_session = _compact_finalize_session(
                session,
                packet_kind=packet_kind,
                packet_state=str(_nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_session != session:
                compacted["session"] = compact_session
                changed = True
        narrowing = _nested_mapping(compacted, "narrowing_guidance")
        if narrowing:
            compact_narrowing = _compact_finalize_narrowing_guidance(
                narrowing,
                packet_kind=packet_kind,
                packet_state=str(_nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_narrowing != narrowing:
                compacted["narrowing_guidance"] = compact_narrowing
                changed = True
        runtime = _nested_mapping(compacted, "runtime")
        if runtime:
            compact_runtime = _compact_finalize_runtime(
                runtime,
                packet_kind=packet_kind,
                packet_state=str(_nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_runtime != runtime:
                compacted["runtime"] = compact_runtime
                changed = True
        packet_quality = _nested_mapping(compacted, "packet_quality")
        if packet_quality:
            compact_quality = _compact_finalize_packet_quality(
                packet_quality,
                packet_kind=packet_kind,
                packet_state=str(_nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_quality != packet_quality:
                compacted["packet_quality"] = compact_quality
                changed = True
        if str(packet_kind or "").strip() in {"bootstrap_session", "session_brief", "governance_slice"}:
            recommended_tests = _mapping_rows(compacted.get("recommended_tests"))
            if recommended_tests:
                compact_tests = _compact_finalize_test_rows(recommended_tests, limit=1)
                if compact_tests != recommended_tests:
                    compacted["recommended_tests"] = compact_tests
                    changed = True
            context_packet = _nested_mapping(compacted, "context_packet")
            if context_packet:
                execution_profile = _nested_mapping(context_packet, "execution_profile")
                if execution_profile and "signals" in execution_profile:
                    execution_profile.pop("signals", None)
                    context_packet["execution_profile"] = execution_profile
                    compacted["context_packet"] = context_packet
                    changed = True
            routing_handoff = _nested_mapping(compacted, "routing_handoff")
            if routing_handoff:
                odylith_execution_profile = _nested_mapping(routing_handoff, "odylith_execution_profile")
                if odylith_execution_profile and "signals" in odylith_execution_profile:
                    odylith_execution_profile.pop("signals", None)
                    routing_handoff["odylith_execution_profile"] = odylith_execution_profile
                    compacted["routing_handoff"] = routing_handoff
                    changed = True
            evidence_pack = _nested_mapping(compacted, "evidence_pack")
            if evidence_pack:
                evidence_handoff = _nested_mapping(evidence_pack, "routing_handoff")
                evidence_profile = _nested_mapping(evidence_handoff, "odylith_execution_profile")
                if evidence_profile and "signals" in evidence_profile:
                    evidence_profile.pop("signals", None)
                    evidence_handoff["odylith_execution_profile"] = evidence_profile
                    evidence_pack["routing_handoff"] = evidence_handoff
                    compacted["evidence_pack"] = evidence_pack
                    changed = True
        truncation = _nested_mapping(compacted, "truncation")
        packet_budget = _nested_mapping(truncation, "packet_budget")
        steps = packet_budget.get("steps")
        if isinstance(steps, list) and len(steps) > 3:
            packet_budget["steps_compacted"] = len(steps) - 3
            packet_budget["steps"] = steps[:3]
            truncation["packet_budget"] = packet_budget
            compacted["truncation"] = truncation
            changed = True
        elif isinstance(steps, list) and steps:
            packet_budget["steps_compacted"] = len(steps)
            packet_budget.pop("steps", None)
            truncation["packet_budget"] = packet_budget
            compacted["truncation"] = truncation
            changed = True
        budget_payload = _nested_mapping(compacted, "packet_budget")
        compact_budget_payload = {
            key: value
            for key, value in {
                "max_bytes": int(budget_payload.get("max_bytes", 0) or 0),
                "max_tokens": int(budget_payload.get("max_tokens", 0) or 0),
            }.items()
            if value > 0
        }
        if compact_budget_payload and compact_budget_payload != budget_payload:
            compacted["packet_budget"] = compact_budget_payload
            changed = True
        metrics = _nested_mapping(compacted, "packet_metrics")
        sections = _nested_mapping(metrics, "sections")
        largest = sections.get("largest")
        if isinstance(largest, list) and len(largest) > 4:
            sections["largest"] = largest[:4]
            metrics["sections"] = sections
            compacted["packet_metrics"] = metrics
            changed = True
        elif isinstance(largest, list) and len(largest) > 2 and not changed:
            sections["largest"] = largest[:2]
            metrics["sections"] = sections
            compacted["packet_metrics"] = metrics
            changed = True
        if not changed:
            break
    return compacted


def _guidance_brief_limit(packet_kind: str) -> int:
    if str(packet_kind or "").strip() == "session_brief":
        return 3
    if str(packet_kind or "").strip() == "bootstrap_session":
        return 2
    if str(packet_kind or "").strip() == "governance_slice":
        return 2
    return 4


def _content_budget(budget_meta: Mapping[str, Any], *, trim_order_paths: Sequence[Sequence[str]] | None = None) -> dict[str, Any]:
    content_budget = dict(budget_meta)
    content_budget["max_bytes"] = int(content_budget.get("content_max_bytes", content_budget.get("max_bytes", 0)) or 0)
    content_budget["max_tokens"] = int(content_budget.get("content_max_tokens", content_budget.get("max_tokens", 0)) or 0)
    if trim_order_paths:
        content_budget["trim_order_paths"] = [
            tuple(str(segment or "").strip() for segment in path if str(segment or "").strip())
            for path in trim_order_paths
            if isinstance(path, Sequence)
        ]
    return content_budget


def _adaptive_packet_profile(
    *,
    packet_kind: str,
    packet_state: str,
    selection_state: str,
    retrieval_plan: Mapping[str, Any],
    optimization_snapshot: Mapping[str, Any],
    full_scan_recommended: bool,
) -> dict[str, Any]:
    control_advisories = _mapping_value(optimization_snapshot.get("control_advisories"))
    evaluation_posture = _mapping_value(optimization_snapshot.get("evaluation_posture"))
    evaluation_control = _mapping_value(evaluation_posture.get("control_posture"))
    learning_loop = _mapping_value(optimization_snapshot.get("learning_loop"))
    learning_control = _mapping_value(learning_loop.get("control_posture"))
    advisory_confidence = _mapping_value(control_advisories.get("confidence"))
    advisory_freshness = _mapping_value(control_advisories.get("freshness"))
    advisory_evidence_strength = _mapping_value(control_advisories.get("evidence_strength"))
    confidence_score = max(
        _int_value(advisory_confidence.get("score")),
        _int_value(advisory_confidence.get("level")),
    )
    evidence_strength_score = max(
        _int_value(advisory_evidence_strength.get("score")),
        _int_value(advisory_evidence_strength.get("level")),
    )
    freshness_bucket = _normalize_token(advisory_freshness.get("bucket"))
    sample_balance = _normalize_token(advisory_evidence_strength.get("sample_balance"))
    signal_conflict = bool(
        control_advisories.get("signal_conflict")
        or advisory_evidence_strength.get("signal_conflict")
        or evaluation_posture.get("signal_conflict")
    )
    advisory_present = bool(
        control_advisories
        or evaluation_control
        or learning_control
        or learning_loop
    )
    reliability = "neutral"
    if (
        advisory_present
        and confidence_score >= 3
        and evidence_strength_score >= 3
        and freshness_bucket in {"fresh", "recent"}
        and sample_balance not in {"thin", "none"}
        and not signal_conflict
    ):
        reliability = "reliable"
    elif advisory_present:
        reliability = "guarded"
    precision_score = _int_value(retrieval_plan.get("precision_score"))
    routing_confidence = _normalize_token(retrieval_plan.get("routing_confidence"))
    ambiguity_class = _normalize_token(retrieval_plan.get("ambiguity_class"))
    evidence_consensus = _normalize_token(retrieval_plan.get("evidence_consensus"))
    anchor_quality = _normalize_token(retrieval_plan.get("anchor_quality"))
    guidance_coverage = _normalize_token(retrieval_plan.get("guidance_coverage"))
    narrowed_packet = str(packet_state or "").strip().startswith("gated_")
    packet_strategy = (
        _normalize_token(control_advisories.get("packet_strategy"))
        or _normalize_token(evaluation_control.get("packet_strategy"))
        or _normalize_token(learning_control.get("packet_strategy"))
    )
    if not packet_strategy:
        if (
            narrowed_packet
            or full_scan_recommended
            or ambiguity_class in {"historical_fanout", "close_competition"}
            or precision_score < 60
            or routing_confidence == "low"
        ):
            packet_strategy = "precision_first"
        elif (
            precision_score >= 75
            and evidence_consensus == "strong"
            and anchor_quality in {"explicit", "non_shared"}
            and guidance_coverage in {"direct", "anchored"}
        ):
            packet_strategy = "density_first"
        else:
            packet_strategy = "balanced"
    budget_mode = (
        _normalize_token(control_advisories.get("budget_mode"))
        or _normalize_token(evaluation_control.get("budget_mode"))
        or _normalize_token(learning_control.get("budget_mode"))
    )
    if not budget_mode:
        if reliability == "guarded" or narrowed_packet or packet_strategy == "precision_first":
            budget_mode = "tight"
        elif (
            reliability == "reliable"
            and packet_strategy == "density_first"
            and routing_confidence in {"high", "medium"}
            and not full_scan_recommended
        ):
            budget_mode = "spend_when_grounded"
        else:
            budget_mode = "balanced"
    retrieval_focus = (
        _normalize_token(control_advisories.get("retrieval_focus"))
        or _normalize_token(evaluation_control.get("retrieval_focus"))
        or _normalize_token(learning_control.get("retrieval_focus"))
    )
    if not retrieval_focus:
        if packet_strategy == "precision_first":
            retrieval_focus = "precision_repair"
        elif evidence_consensus == "weak" or ambiguity_class in {"historical_fanout", "close_competition"}:
            retrieval_focus = "expand_coverage"
        else:
            retrieval_focus = "balanced"
    speed_mode = (
        _normalize_token(control_advisories.get("speed_mode"))
        or _normalize_token(evaluation_control.get("speed_mode"))
        or _normalize_token(learning_control.get("speed_mode"))
    )
    if not speed_mode:
        if reliability == "guarded" or narrowed_packet or full_scan_recommended:
            speed_mode = "conserve"
        elif (
            reliability == "reliable"
            and packet_strategy == "density_first"
            and routing_confidence == "high"
            and precision_score >= 75
            and ambiguity_class not in {"historical_fanout", "close_competition"}
        ):
            speed_mode = "accelerate_grounded"
        else:
            speed_mode = "balanced"
    selection_bias = "balanced"
    if packet_strategy == "precision_first":
        selection_bias = "precision_trimmed"
    elif packet_strategy == "density_first":
        selection_bias = "grounded_density"
    budget_scale = 1.0
    if budget_mode == "tight":
        budget_scale = 0.88 if packet_strategy == "precision_first" else 0.92
    elif speed_mode == "conserve":
        budget_scale = 0.96
    if str(packet_kind or "").strip() in {"impact", "architecture", "governance_slice"}:
        budget_scale = max(budget_scale, 0.96)
    elif str(packet_kind or "").strip() == "session_brief":
        budget_scale = max(budget_scale, 0.94)
    source = "derived"
    if _normalize_token(control_advisories.get("packet_strategy")) or _normalize_token(control_advisories.get("budget_mode")):
        source = "control_advisories"
    elif _normalize_token(evaluation_control.get("packet_strategy")) or _normalize_token(evaluation_control.get("budget_mode")):
        source = "evaluation_posture"
    elif _normalize_token(learning_control.get("packet_strategy")) or _normalize_token(learning_control.get("budget_mode")):
        source = "learning_loop"
    return {
        "state": _normalize_token(control_advisories.get("state") or learning_loop.get("state") or reliability),
        "source": source,
        "reliability": reliability,
        "packet_strategy": packet_strategy,
        "budget_mode": budget_mode,
        "retrieval_focus": retrieval_focus,
        "speed_mode": speed_mode,
        "selection_bias": selection_bias,
        "budget_scale": round(max(0.75, min(1.0, float(budget_scale))), 2),
        "precision_score": precision_score,
        "routing_confidence": routing_confidence,
        "freshness_bucket": freshness_bucket,
        "evidence_strength_score": evidence_strength_score,
        "signal_conflict": signal_conflict,
        "packet_kind": str(packet_kind or "").strip(),
        "selection_state": str(selection_state or "").strip(),
    }


def _apply_adaptive_budget_profile(
    budget_meta: Mapping[str, Any],
    *,
    adaptive_packet_profile: Mapping[str, Any],
) -> dict[str, Any]:
    working = dict(budget_meta)
    budget_scale = float(adaptive_packet_profile.get("budget_scale", 1.0) or 1.0)
    if budget_scale < 0.999:
        working["max_bytes"] = max(1_000, int((working.get("max_bytes", 0) or 0) * budget_scale))
        working["max_tokens"] = max(250, int((working.get("max_tokens", 0) or 0) * budget_scale))
    return working


def _reorder_trim_paths(
    *,
    packet_kind: str,
    packet_state: str,
    selection_state: str,
    retrieval_plan: Mapping[str, Any],
    adaptive_packet_profile: Mapping[str, Any] | None = None,
) -> list[tuple[str, ...]]:
    base_order = list(budgeting.DEFAULT_TRIM_ORDERS.get(str(packet_kind or "").strip(), []))
    if not base_order:
        return []
    direct_guidance_count = int(
        dict(retrieval_plan.get("evidence_profile", {})).get("direct_guidance_count", 0)
        if isinstance(retrieval_plan.get("evidence_profile"), Mapping)
        else 0
    )
    actionable_guidance_count = int(
        dict(retrieval_plan.get("actionability_profile", {})).get("actionable_guidance_count", 0)
        if isinstance(retrieval_plan.get("actionability_profile"), Mapping)
        else 0
    )
    validation_score = int(
        dict(retrieval_plan.get("validation_profile", {})).get("score", 0)
        if isinstance(retrieval_plan.get("validation_profile"), Mapping)
        else 0
    )
    trim_first: list[tuple[str, ...]] = []
    keep_late: list[tuple[str, ...]] = []
    adaptive = dict(adaptive_packet_profile) if isinstance(adaptive_packet_profile, Mapping) else {}
    packet_strategy = _normalize_token(adaptive.get("packet_strategy"))
    budget_mode = _normalize_token(adaptive.get("budget_mode"))
    speed_mode = _normalize_token(adaptive.get("speed_mode"))
    selection_bias = _normalize_token(adaptive.get("selection_bias"))
    for path in (
        ("architecture_audit",),
        ("code_neighbors",),
        ("runtime", "timings"),
        ("active_conflicts",),
        ("impact_summary", "guidance_brief"),
        ("impact_summary", "workstreams"),
        ("workstream_context",),
    ):
        if path in base_order:
            trim_first.append(path)
    if str(packet_state or "").strip().startswith("gated_"):
        for path in (("candidate_workstreams",), ("impact", "candidate_workstreams"), ("docs",), ("relevant_docs",)):
            if path in base_order and path not in trim_first:
                trim_first.append(path)
    if selection_state == "explicit":
        for path in (("candidate_workstreams",), ("impact", "candidate_workstreams"), ("workstream_context",)):
            if path in base_order:
                keep_late.append(path)
    if validation_score >= 2:
        for path in (
            ("recommended_commands",),
            ("recommended_tests",),
            ("impact", "recommended_commands"),
            ("impact", "recommended_tests"),
        ):
            if path in base_order:
                keep_late.append(path)
    if direct_guidance_count > 0 or actionable_guidance_count > 0:
        for path in (
            ("guidance_brief",),
            ("retrieval_plan", "selected_guidance_chunks"),
            ("working_memory_tiers", "warm", "guidance_chunks"),
            ("impact", "guidance_brief"),
            ("impact_summary", "guidance_brief"),
        ):
            if path in base_order:
                keep_late.append(path)
    if packet_strategy == "precision_first" or budget_mode == "tight":
        for path in (
            ("candidate_workstreams",),
            ("impact", "candidate_workstreams"),
            ("impact_summary", "workstreams"),
            ("impact_summary", "diagrams"),
            ("diagrams",),
            ("active_conflicts",),
            ("workstream_context",),
        ):
            if path in base_order and path not in trim_first:
                trim_first.append(path)
        for path in (
            ("recommended_commands",),
            ("recommended_tests",),
            ("guidance_brief",),
            ("retrieval_plan", "selected_guidance_chunks"),
            ("working_memory_tiers", "warm", "guidance_chunks"),
        ):
            if path in base_order:
                keep_late.append(path)
    if packet_strategy == "density_first" or selection_bias == "grounded_density":
        for path in (
            ("guidance_brief",),
            ("retrieval_plan", "selected_guidance_chunks"),
            ("working_memory_tiers", "warm", "guidance_chunks"),
            ("relevant_docs",),
            ("docs",),
            ("recommended_commands",),
            ("recommended_tests",),
            ("retrieval_plan", "selected_docs"),
            ("retrieval_plan", "selected_tests"),
            ("retrieval_plan", "selected_commands"),
        ):
            if path in base_order:
                keep_late.append(path)
    if speed_mode == "conserve":
        for path in (
            ("runtime", "timings", "operations"),
            ("runtime", "timings", "recent"),
            ("architecture_audit",),
            ("code_neighbors",),
        ):
            if path in base_order and path not in trim_first:
                trim_first.append(path)
    trim_first_set = {path for path in trim_first}
    keep_late_set = {path for path in keep_late if path not in trim_first_set}
    return [
        *trim_first,
        *[path for path in base_order if path not in trim_first_set and path not in keep_late_set],
        *[path for path in base_order if path in keep_late_set],
    ]


def _retained_components(payload: Mapping[str, Any], fallback: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    for key in ("components",):
        rows = _mapping_rows(payload.get(key))
        if rows:
            return rows
    for key in ("impact_summary", "impact"):
        rows = _mapping_rows(_nested_mapping(payload, key).get("components"))
        if rows:
            return rows
    return _mapping_rows(fallback)


def _retained_diagrams(payload: Mapping[str, Any], fallback: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    for key in ("diagrams",):
        rows = _mapping_rows(payload.get(key))
        if rows:
            return rows
    for key in ("impact_summary", "impact"):
        rows = _mapping_rows(_nested_mapping(payload, key).get("diagrams"))
        if rows:
            return rows
    return _mapping_rows(fallback)


def _retained_docs(payload: Mapping[str, Any], fallback: Sequence[str]) -> list[str]:
    for key in ("docs", "relevant_docs"):
        rows = _string_rows(payload.get(key))
        if rows:
            return rows
    for key in ("impact_summary", "impact"):
        rows = _string_rows(_nested_mapping(payload, key).get("docs"))
        if rows:
            return rows
    return _string_rows(fallback)


def _retained_commands(payload: Mapping[str, Any], fallback: Sequence[str]) -> list[str]:
    rows = _string_rows(payload.get("recommended_commands"))
    if rows:
        return rows
    for key in ("impact_summary", "impact"):
        rows = _string_rows(_nested_mapping(payload, key).get("recommended_commands"))
        if rows:
            return rows
    return _string_rows(fallback)


def _retained_tests(payload: Mapping[str, Any], fallback: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = _mapping_rows(payload.get("recommended_tests"))
    if rows:
        return rows
    for key in ("impact_summary", "impact"):
        rows = _mapping_rows(_nested_mapping(payload, key).get("recommended_tests"))
        if rows:
            return rows
    return _mapping_rows(fallback)


def _retained_workstreams(
    payload: Mapping[str, Any],
    *,
    workstream_selection: Mapping[str, Any],
    fallback: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    selection = _mapping_value(payload.get("workstream_selection")) or _mapping_value(workstream_selection)
    selected = _mapping_value(selection.get("selected_workstream"))
    if str(selected.get("entity_id", "")).strip():
        return [selected]
    rows = _mapping_rows(payload.get("candidate_workstreams"))
    if rows:
        return rows
    return _mapping_rows(fallback)


def _retained_guidance(
    payload: Mapping[str, Any],
    fallback: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    retrieval_plan = _mapping_value(payload.get("retrieval_plan"))
    rows = _mapping_rows(retrieval_plan.get("selected_guidance_chunks"))
    guidance_brief = _mapping_rows(payload.get("guidance_brief"))
    impact_rows: list[dict[str, Any]] = []
    for key in ("impact_summary", "impact"):
        impact_rows.extend(_mapping_rows(_nested_mapping(payload, key).get("guidance_brief")))
    warm = _nested_mapping(_nested_mapping(payload, "working_memory_tiers"), "warm")
    warm_rows = _mapping_rows(warm.get("guidance_chunks"))
    detail_rows = [*guidance_brief, *impact_rows, *warm_rows, *_mapping_rows(fallback)]
    if rows:
        return _merge_guidance_rows(rows, detail_rows=detail_rows)
    if guidance_brief:
        return _merge_guidance_rows(guidance_brief, detail_rows=[*impact_rows, *warm_rows, *_mapping_rows(fallback)])
    if impact_rows:
        return _merge_guidance_rows(impact_rows, detail_rows=[*warm_rows, *_mapping_rows(fallback)])
    if warm_rows:
        return _merge_guidance_rows(warm_rows, detail_rows=_mapping_rows(fallback))
    return _mapping_rows(fallback)


def _refresh_context_views(
    *,
    repo_root: Path,
    packet_kind: str,
    packet_state: str,
    payload: Mapping[str, Any],
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    shared_only_input: bool,
    selection_state: str,
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    docs: Sequence[str],
    recommended_commands: Sequence[str],
    recommended_tests: Sequence[Mapping[str, Any]],
    fallback_guidance_chunks: Sequence[Mapping[str, Any]],
    miss_recovery: Mapping[str, Any],
    guidance_catalog_summary: Mapping[str, Any],
    full_scan_recommended: bool,
    full_scan_reason: str,
    session_id: str,
    build_working_memory_tiers: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    refreshed = dict(payload)
    retained_workstreams = _retained_workstreams(
        refreshed,
        workstream_selection=workstream_selection,
        fallback=candidate_workstreams,
    )
    retained_components = _retained_components(refreshed, components)
    retained_diagrams = _retained_diagrams(refreshed, diagrams)
    retained_docs = _retained_docs(refreshed, docs)
    retained_commands = _retained_commands(refreshed, recommended_commands)
    retained_tests = _retained_tests(refreshed, recommended_tests)
    if str(packet_kind or "").strip() == "bootstrap_session" and str(packet_state or "").strip().startswith("gated_"):
        retained_tests = _compact_finalize_test_rows(retained_tests, limit=1)
    retained_guidance = _retained_guidance(refreshed, fallback_guidance_chunks)
    refreshed_plan = routing.build_retrieval_plan(
        packet_kind=packet_kind,
        packet_state=packet_state,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        shared_only_input=shared_only_input,
        selection_state=selection_state,
        workstream_selection=workstream_selection,
        candidate_workstreams=retained_workstreams,
        components=retained_components,
        diagrams=retained_diagrams,
        docs=retained_docs,
        recommended_tests=retained_tests,
        recommended_commands=retained_commands,
        selected_guidance_chunks=retained_guidance,
        miss_recovery=miss_recovery,
        guidance_catalog_summary=guidance_catalog_summary,
        full_scan_reason=full_scan_reason,
    )
    refreshed["retrieval_plan"] = refreshed_plan
    refreshed["guidance_brief"] = retrieval.compact_guidance_brief(
        retained_guidance,
        limit=_guidance_brief_limit(packet_kind),
    )
    refreshed["narrowing_guidance"] = routing.build_narrowing_guidance(
        packet_kind=packet_kind,
        packet_state=packet_state,
        full_scan_recommended=full_scan_recommended,
        full_scan_reason=full_scan_reason,
        workstream_selection=workstream_selection,
        retrieval_plan=refreshed_plan,
        final_payload=refreshed,
    )
    if build_working_memory_tiers:
        refreshed["working_memory_tiers"] = retrieval.build_working_memory_tiers(
            packet_kind=packet_kind,
            repo_root=repo_root,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            docs=retained_docs,
            recommended_commands=retained_commands,
            recommended_tests=retained_tests,
            components=retained_components,
            selected_workstreams=retained_workstreams,
            selected_guidance_chunks=retained_guidance,
            session_id=session_id,
            selection_state=selection_state,
        )
    else:
        refreshed.pop("working_memory_tiers", None)
    return refreshed, refreshed_plan


def _can_reuse_hot_path_context_views(
    *,
    packet_kind: str,
    build_working_memory_tiers: bool,
    payload: Mapping[str, Any],
) -> bool:
    if build_working_memory_tiers or str(packet_kind or "").strip() not in {"impact", "governance_slice"}:
        return False
    return bool(_mapping_value(payload.get("retrieval_plan")) and _mapping_value(payload.get("narrowing_guidance")))


def _reuse_hot_path_context_views(
    *,
    payload: Mapping[str, Any],
    retrieval_plan: Mapping[str, Any],
    guidance_brief: Sequence[Mapping[str, Any]],
    narrowing_guidance: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    reused = dict(payload)
    reused["retrieval_plan"] = dict(retrieval_plan)
    reused["guidance_brief"] = [dict(row) for row in guidance_brief if isinstance(row, Mapping)]
    reused["narrowing_guidance"] = dict(narrowing_guidance)
    reused.pop("working_memory_tiers", None)
    return reused, dict(retrieval_plan)


def _assemble_finalized_candidate(
    *,
    base_payload: Mapping[str, Any],
    packet_metrics: Mapping[str, Any],
    packet_quality: Mapping[str, Any],
    routing_handoff: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    evidence_pack: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = dict(base_payload)
    candidate["packet_metrics"] = dict(packet_metrics)
    candidate["packet_quality"] = dict(packet_quality)
    candidate["routing_handoff"] = dict(routing_handoff)
    candidate["context_packet"] = dict(context_packet)
    if evidence_pack:
        candidate["evidence_pack"] = dict(evidence_pack)
    else:
        candidate.pop("evidence_pack", None)
    return candidate


def _sync_packet_budget_truncation(
    packet: dict[str, Any],
    *,
    packet_metrics: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(packet.get("truncation"), Mapping):
        return packet
    updated_truncation = dict(packet.get("truncation", {}))
    packet_budget_truncation = dict(updated_truncation.get("packet_budget", {}))
    packet_budget_truncation["within_budget_after_finalize"] = bool(packet_metrics.get("within_budget"))
    packet_budget_truncation["final_bytes"] = int(packet_metrics.get("estimated_bytes", 0) or 0)
    packet_budget_truncation["final_tokens"] = int(packet_metrics.get("estimated_tokens", 0) or 0)
    updated_truncation["packet_budget"] = packet_budget_truncation
    packet["truncation"] = updated_truncation
    return packet


def _compact_hot_path_finalize_workstream_selection(summary: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in {
            "candidate_count": _int_value(summary.get("candidate_count")),
            "strong_candidate_count": _int_value(summary.get("strong_candidate_count")),
            "ambiguity_class": str(summary.get("ambiguity_class", "")).strip(),
        }.items()
        if value not in ("", [], {}, None, 0)
    }
    if isinstance(summary.get("selected_workstream"), Mapping):
        selected = {
            key: str(dict(summary.get("selected_workstream", {})).get(key, "")).strip()
            for key in ("entity_id", "title")
            if str(dict(summary.get("selected_workstream", {})).get(key, "")).strip()
        }
        if selected:
            compact["selected_workstream"] = selected
    return compact


def _prune_hot_path_finalize_retrieval_plan(summary: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    scalar_fields = (
        "packet_kind",
        "packet_state",
        "selection_state",
        "anchor_quality",
        "guidance_coverage",
        "evidence_consensus",
        "ambiguity_class",
    )
    for field in scalar_fields:
        token = str(summary.get(field, "")).strip()
        if token:
            compact[field] = token
    for field in ("has_non_shared_anchor",):
        if field in summary:
            compact[field] = bool(summary.get(field))
    for field in ("precision_score",):
        if _int_value(summary.get(field)):
            compact[field] = _int_value(summary.get(field))
    list_fields = (
        "anchor_paths",
        "shared_anchor_paths",
        "selected_domains",
        "selected_docs",
        "selected_commands",
    )
    for field in list_fields:
        rows = _string_rows(summary.get(field))
        if rows:
            compact[field] = rows
    mapping_list_fields = (
        "selected_workstreams",
        "selected_tests",
        "selected_guidance_chunks",
    )
    for field in mapping_list_fields:
        rows = _mapping_rows(summary.get(field))
        if rows:
            compact[field] = rows
    for field in ("selected_counts", "miss_recovery"):
        value = summary.get(field)
        if isinstance(value, Mapping):
            compact[field] = dict(value)
    return compact


def _prune_hot_path_finalize_base_payload(
    *,
    packet_kind: str,
    packet_state: str,
    base_payload: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(base_payload)
    normalized_kind = str(packet_kind or "").strip()
    gated_hot_path = str(packet_state or "").strip().startswith("gated_")
    if normalized_kind not in {"impact", "governance_slice", "session_brief", "bootstrap_session"} or not gated_hot_path:
        return payload
    if bool(payload.get("_retain_hot_path_internal_context")):
        return payload
    keep_keys = {
        "resolved",
        "changed_paths",
        "explicit_paths",
        "selection_state",
        "selection_reason",
        "selection_confidence",
        "context_packet_state",
        "full_scan_recommended",
        "full_scan_reason",
        "fallback_scan",
        "narrowing_guidance",
        "turn_context",
        "target_resolution",
        "presentation_policy",
        "miss_recovery",
        "packet_budget",
        "truncation",
        "inferred_workstream",
        "adaptive_packet_profile",
    }
    if normalized_kind in {"impact", "governance_slice"}:
        keep_keys.add("intent")
    if normalized_kind == "governance_slice":
        keep_keys.update(
            {
                "validation_bundle",
                "governance_obligations",
                "surface_refs",
                "diagram_watch_gaps",
            }
        )
    elif normalized_kind in {"session_brief", "bootstrap_session"}:
        keep_keys.update(
            {
                "relevant_docs",
                "recommended_commands",
                "recommended_tests",
                "validation_bundle",
            }
        )
    compact = {
        key: value
        for key, value in payload.items()
        if key in keep_keys and value not in ("", [], {}, None)
    }
    if isinstance(payload.get("workstream_selection"), Mapping):
        compact_selection = _compact_hot_path_finalize_workstream_selection(
            dict(payload.get("workstream_selection", {}))
        )
        if compact_selection:
            compact["workstream_selection"] = compact_selection
    if isinstance(payload.get("retrieval_plan"), Mapping):
        compact_plan = _prune_hot_path_finalize_retrieval_plan(dict(payload.get("retrieval_plan", {})))
        if compact_plan:
            compact["retrieval_plan"] = compact_plan
    return compact


def _finalize_packet_metadata(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    base_payload: Mapping[str, Any],
    selection_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
    build_evidence_pack: bool = True,
    max_iterations: int = 8,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    packet_metrics: dict[str, Any] = {}
    packet_quality: dict[str, Any] = {}
    routing_handoff: dict[str, Any] = {}
    context_packet: dict[str, Any] = {}
    evidence_pack: dict[str, Any] = {}
    candidate: dict[str, Any] = {}
    for _ in range(max(1, int(max_iterations))):
        candidate = _assemble_finalized_candidate(
            base_payload=base_payload,
            packet_metrics=packet_metrics,
            packet_quality=packet_quality,
            routing_handoff=routing_handoff,
            context_packet=context_packet,
            evidence_pack=evidence_pack,
        )
        candidate = _sync_packet_budget_truncation(candidate, packet_metrics=packet_metrics)
        measured = budgeting.estimate_packet_metrics(
            candidate,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
        measured_candidate = _sync_packet_budget_truncation(
            _assemble_finalized_candidate(
                base_payload=base_payload,
                packet_metrics=measured,
                packet_quality=packet_quality,
                routing_handoff=routing_handoff,
                context_packet=context_packet,
                evidence_pack=evidence_pack,
            ),
            packet_metrics=measured,
        )
        quality_payload = quality.summarize_packet_quality(
            packet_kind=packet_kind,
            packet_state=packet_state,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            packet_metrics=measured,
            final_payload=measured_candidate,
        )
        handoff_payload = routing.build_routing_handoff(
            packet_kind=packet_kind,
            packet_state=packet_state,
            retrieval_plan=retrieval_plan,
            packet_quality=quality_payload,
            final_payload=_sync_packet_budget_truncation(
                _assemble_finalized_candidate(
                    base_payload=base_payload,
                    packet_metrics=measured,
                    packet_quality=quality_payload,
                    routing_handoff=routing_handoff,
                    context_packet=context_packet,
                    evidence_pack=evidence_pack,
                ),
                packet_metrics=measured,
            ),
        )
        refreshed_candidate = _sync_packet_budget_truncation(
            _assemble_finalized_candidate(
                base_payload=base_payload,
                packet_metrics=measured,
                packet_quality=quality_payload,
                routing_handoff=handoff_payload,
                context_packet=context_packet,
                evidence_pack=evidence_pack,
            ),
            packet_metrics=measured,
        )
        context_payload = tooling_memory_contracts.build_context_packet(
            packet_kind=packet_kind,
            packet_state=packet_state,
            payload=refreshed_candidate,
        )
        evidence_payload = (
            tooling_memory_contracts.build_evidence_pack(
                packet_kind=packet_kind,
                packet_state=packet_state,
                payload=refreshed_candidate,
            )
            if build_evidence_pack
            else {}
        )
        if (
            measured == packet_metrics
            and quality_payload == packet_quality
            and handoff_payload == routing_handoff
            and context_payload == context_packet
            and evidence_payload == evidence_pack
        ):
            packet_metrics = measured
            packet_quality = quality_payload
            routing_handoff = handoff_payload
            context_packet = context_payload
            evidence_pack = evidence_payload
            break
        packet_metrics = measured
        packet_quality = quality_payload
        routing_handoff = handoff_payload
        context_packet = context_payload
        evidence_pack = evidence_payload
    candidate = _assemble_finalized_candidate(
        base_payload=base_payload,
        packet_metrics=packet_metrics,
        packet_quality=packet_quality,
        routing_handoff=routing_handoff,
        context_packet=context_packet,
        evidence_pack=evidence_pack,
    )
    candidate = _sync_packet_budget_truncation(candidate, packet_metrics=packet_metrics)
    return candidate, packet_metrics, packet_quality, routing_handoff


def _finalize_packet_metadata_hot_path(
    *,
    packet_kind: str,
    packet_state: str,
    budget_meta: Mapping[str, Any],
    base_payload: Mapping[str, Any],
    selection_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    working_base_payload = _prune_hot_path_finalize_base_payload(
        packet_kind=packet_kind,
        packet_state=packet_state,
        base_payload=base_payload,
    )
    packet_metrics = budgeting.estimate_packet_metrics(
        working_base_payload,
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget=budget_meta,
    )
    measured_candidate = _sync_packet_budget_truncation(
        _assemble_finalized_candidate(
            base_payload=working_base_payload,
            packet_metrics=packet_metrics,
            packet_quality={},
            routing_handoff={},
            context_packet={},
            evidence_pack={},
        ),
        packet_metrics=packet_metrics,
    )
    quality_cache_key = odylith_context_cache.fingerprint_payload(
        {
            "packet_kind": str(packet_kind or "").strip(),
            "packet_state": str(packet_state or "").strip(),
            "selection_state": str(selection_state or "").strip(),
            "full_scan_recommended": bool(full_scan_recommended),
            "retrieval_plan": dict(retrieval_plan),
            "packet_metrics": dict(packet_metrics),
            "final_payload": dict(measured_candidate),
        }
    )
    cached_packet_quality = _PROCESS_HOT_PATH_PACKET_QUALITY_CACHE.get(quality_cache_key)
    if cached_packet_quality is None:
        cached_packet_quality = quality.summarize_packet_quality(
            packet_kind=packet_kind,
            packet_state=packet_state,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=retrieval_plan,
            packet_metrics=packet_metrics,
            final_payload=measured_candidate,
        )
        _PROCESS_HOT_PATH_PACKET_QUALITY_CACHE[quality_cache_key] = dict(cached_packet_quality)
    packet_quality = dict(cached_packet_quality)
    handoff_candidate = _sync_packet_budget_truncation(
        _assemble_finalized_candidate(
            base_payload=working_base_payload,
            packet_metrics=packet_metrics,
            packet_quality=packet_quality,
            routing_handoff={},
            context_packet={},
            evidence_pack={},
        ),
        packet_metrics=packet_metrics,
    )
    routing_cache_key = odylith_context_cache.fingerprint_payload(
        {
            "packet_kind": str(packet_kind or "").strip(),
            "packet_state": str(packet_state or "").strip(),
            "retrieval_plan": dict(retrieval_plan),
            "packet_quality": dict(packet_quality),
            "final_payload": dict(handoff_candidate),
        }
    )
    cached_routing_handoff = _PROCESS_HOT_PATH_ROUTING_HANDOFF_CACHE.get(routing_cache_key)
    if cached_routing_handoff is None:
        cached_routing_handoff = routing.build_routing_handoff(
            packet_kind=packet_kind,
            packet_state=packet_state,
            retrieval_plan=retrieval_plan,
            packet_quality=packet_quality,
            final_payload=handoff_candidate,
        )
        _PROCESS_HOT_PATH_ROUTING_HANDOFF_CACHE[routing_cache_key] = dict(cached_routing_handoff)
    routing_handoff = dict(cached_routing_handoff)
    context_candidate = _sync_packet_budget_truncation(
        _assemble_finalized_candidate(
            base_payload=working_base_payload,
            packet_metrics=packet_metrics,
            packet_quality=packet_quality,
            routing_handoff=routing_handoff,
            context_packet={},
            evidence_pack={},
        ),
        packet_metrics=packet_metrics,
    )
    context_packet = tooling_memory_contracts.build_context_packet(
        packet_kind=packet_kind,
        packet_state=packet_state,
        payload=context_candidate,
    )
    final_candidate = _sync_packet_budget_truncation(
        _assemble_finalized_candidate(
            base_payload=working_base_payload,
            packet_metrics=packet_metrics,
            packet_quality=packet_quality,
            routing_handoff=routing_handoff,
            context_packet=context_packet,
            evidence_pack={},
        ),
        packet_metrics=packet_metrics,
    )
    final_metrics = budgeting.estimate_packet_metrics(
        final_candidate,
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget=budget_meta,
    )
    final_candidate["packet_metrics"] = dict(final_metrics)
    final_candidate = _sync_packet_budget_truncation(final_candidate, packet_metrics=final_metrics)
    return final_candidate, final_metrics, packet_quality, routing_handoff


def _finalize_packet_without_odylith(
    *,
    repo_root: Path,
    packet_kind: str,
    payload: Mapping[str, Any],
    packet_state: str,
) -> dict[str, Any]:
    budget_meta = budgeting.packet_budget(packet_kind=packet_kind, packet_state=packet_state)
    trimmed, _trim_budget, _content_metrics, budget_truncation = budgeting.apply_packet_budget(
        dict(payload),
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget_override=budget_meta,
    )
    final_payload = dict(trimmed)
    truncation = dict(final_payload.get("truncation", {})) if isinstance(final_payload.get("truncation"), Mapping) else {}
    packet_budget_truncation = dict(budget_truncation)
    packet_budget_truncation["retry_index"] = 0
    truncation["packet_budget"] = packet_budget_truncation
    final_payload["packet_budget"] = dict(budget_meta)
    final_payload["truncation"] = truncation
    final_payload.pop("retrieval_plan", None)
    final_payload.pop("guidance_brief", None)
    final_payload.pop("narrowing_guidance", None)
    final_payload.pop("working_memory_tiers", None)
    final_payload.pop("packet_quality", None)
    final_payload.pop("routing_handoff", None)
    final_payload.pop("context_packet", None)
    final_payload.pop("evidence_pack", None)
    final_payload["odylith_switch"] = _odylith_switch_snapshot(repo_root=repo_root)
    final_payload["odylith_ablation"] = {
        "status": "disabled",
        "reason": "odylith_switch_off",
        "suppressed_contracts": [
            "retrieval_plan.v1",
            "routing_handoff.v1",
            "context_packet.v1",
            "evidence_pack.v1",
            "optimization_snapshot.v1",
        ],
    }
    packet_metrics = budgeting.estimate_packet_metrics(
        final_payload,
        packet_kind=packet_kind,
        packet_state=packet_state,
        budget=budget_meta,
    )
    final_payload["packet_metrics"] = dict(packet_metrics)
    final_payload = _sync_packet_budget_truncation(final_payload, packet_metrics=packet_metrics)
    if isinstance(final_payload.get("truncation"), Mapping):
        final_payload = _compact_finalize_metadata(final_payload, budget_meta=budget_meta)
        refreshed_metrics = budgeting.estimate_packet_metrics(
            final_payload,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
        final_payload["packet_metrics"] = dict(refreshed_metrics)
        final_payload = _sync_packet_budget_truncation(final_payload, packet_metrics=refreshed_metrics)
    return final_payload


def finalize_packet(
    *,
    repo_root: Path,
    packet_kind: str,
    payload: Mapping[str, Any],
    packet_state: str,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    shared_only_input: bool,
    selection_state: str,
    workstream_selection: Mapping[str, Any],
    candidate_workstreams: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    docs: Sequence[str],
    recommended_commands: Sequence[str],
    recommended_tests: Sequence[Mapping[str, Any]],
    engineering_notes: Mapping[str, Sequence[Mapping[str, Any]]],
    miss_recovery: Mapping[str, Any],
    full_scan_recommended: bool,
    full_scan_reason: str,
    session_id: str = "",
    family_hint: str = "",
    guidance_catalog: Mapping[str, Any] | None = None,
    optimization_snapshot: Mapping[str, Any] | None = None,
    delivery_profile: str = "full",
) -> dict[str, Any]:
    """Attach routing, retrieval, budgeting, and quality metadata to a packet."""

    root = Path(repo_root).resolve()
    odylith_switch = _odylith_switch_snapshot(repo_root=root)
    if not bool(odylith_switch.get("enabled", True)):
        return _finalize_packet_without_odylith(
            repo_root=root,
            packet_kind=packet_kind,
            payload=payload,
            packet_state=packet_state,
        )
    catalog = (
        dict(guidance_catalog)
        if isinstance(guidance_catalog, Mapping)
        else tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    )
    selected = workstream_selection.get("selected_workstream")
    selected_workstreams = (
        [dict(selected)]
        if isinstance(selected, Mapping) and str(selected.get("entity_id", "")).strip()
        else [dict(row) for row in candidate_workstreams if isinstance(row, Mapping)]
    )
    retrieval_bundle = retrieval.compact_retrieval_bundle(
        packet_kind=packet_kind,
        family_hint=family_hint,
        repo_root=root,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        docs=docs,
        recommended_commands=recommended_commands,
        recommended_tests=recommended_tests,
        components=components,
        selected_workstreams=selected_workstreams,
        engineering_notes=engineering_notes,
        guidance_catalog=catalog,
        session_id=session_id,
        selection_state=selection_state,
        build_working_memory=not agent_runtime_contract.is_agent_hot_path_profile(delivery_profile),
    )
    selected_guidance_chunks = (
        [dict(row) for row in retrieval_bundle.get("selected_guidance_chunks", []) if isinstance(row, Mapping)]
        if isinstance(retrieval_bundle.get("selected_guidance_chunks"), list)
        else []
    )
    direct_guidance_chunk_count = sum(
        1 for row in selected_guidance_chunks if str(row.get("match_tier", "")).strip() == "direct_path"
    )
    actionable_guidance_chunk_count = sum(
        1
        for row in selected_guidance_chunks
        if isinstance(row.get("actionability"), Mapping)
        and bool(dict(row.get("actionability", {})).get("actionable"))
    )
    selected_test_count = len([row for row in recommended_tests if isinstance(row, Mapping)])
    selected_command_count = len([str(token).strip() for token in recommended_commands if str(token).strip()])
    preflight_actionability_score = 0
    if actionable_guidance_chunk_count > 0 and (direct_guidance_chunk_count > 0 or selected_test_count > 0 or selected_command_count > 0):
        preflight_actionability_score = 3
    elif actionable_guidance_chunk_count > 0 or direct_guidance_chunk_count > 0:
        preflight_actionability_score = 2
    elif selected_test_count > 0 or selected_command_count > 0:
        preflight_actionability_score = 1
    preflight_validation_score = 0
    if selected_test_count > 0 and selected_command_count > 0:
        preflight_validation_score = 3
    elif selected_test_count > 0 or selected_command_count > 0:
        preflight_validation_score = 2
    guidance_catalog_summary = tooling_guidance_catalog.compact_catalog_summary(catalog)
    plan = routing.build_retrieval_plan(
        packet_kind=packet_kind,
        packet_state=packet_state,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        shared_only_input=shared_only_input,
        selection_state=selection_state,
        workstream_selection=workstream_selection,
        candidate_workstreams=candidate_workstreams,
        components=components,
        diagrams=diagrams,
        docs=docs,
        recommended_tests=recommended_tests,
        recommended_commands=recommended_commands,
        selected_guidance_chunks=selected_guidance_chunks,
        miss_recovery=miss_recovery or {},
        guidance_catalog_summary=guidance_catalog_summary,
        full_scan_reason=full_scan_reason,
    )
    grounded_ambiguous_write = routing.grounded_ambiguous_write_candidate(
        anchor_quality=str(plan.get("anchor_quality", "")).strip(),
        guidance_coverage=str(plan.get("guidance_coverage", "")).strip(),
        ambiguity_class=str(plan.get("ambiguity_class", "")).strip(),
        evidence_consensus=str(plan.get("evidence_consensus", "")).strip(),
        precision_score=_int_value(plan.get("precision_score")),
        actionability_score=preflight_actionability_score,
        validation_score=preflight_validation_score,
        direct_guidance_chunk_count=direct_guidance_chunk_count,
        actionable_guidance_chunk_count=actionable_guidance_chunk_count,
        selected_test_count=selected_test_count,
        selected_command_count=selected_command_count,
    )
    if (
        str(packet_state or "").strip() == "gated_ambiguous"
        and bool(full_scan_recommended)
        and str(full_scan_reason or "").strip() == "selection_ambiguous"
        and grounded_ambiguous_write
    ):
        packet_state = "expanded"
        full_scan_recommended = False
        full_scan_reason = ""
        plan = routing.build_retrieval_plan(
            packet_kind=packet_kind,
            packet_state=packet_state,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            shared_only_input=shared_only_input,
            selection_state=selection_state,
            workstream_selection=workstream_selection,
            candidate_workstreams=candidate_workstreams,
            components=components,
            diagrams=diagrams,
            docs=docs,
            recommended_tests=recommended_tests,
            recommended_commands=recommended_commands,
            selected_guidance_chunks=selected_guidance_chunks,
            miss_recovery=miss_recovery or {},
            guidance_catalog_summary=guidance_catalog_summary,
            full_scan_reason=full_scan_reason,
        )
    optimization = dict(optimization_snapshot) if isinstance(optimization_snapshot, Mapping) else {}
    adaptive_packet_profile = _adaptive_packet_profile(
        packet_kind=packet_kind,
        packet_state=packet_state,
        selection_state=selection_state,
        retrieval_plan=plan,
        optimization_snapshot=optimization,
        full_scan_recommended=full_scan_recommended,
    )
    enriched = dict(payload)
    enriched["delivery_profile"] = agent_runtime_contract.canonical_delivery_profile(delivery_profile)
    enriched["adaptive_packet_profile"] = dict(adaptive_packet_profile)
    prioritized_docs = retrieval_bundle.get("prioritized_docs", [])
    if isinstance(prioritized_docs, list) and isinstance(enriched.get("docs"), list):
        enriched["docs"] = [str(token).strip() for token in prioritized_docs if str(token).strip()]
    if isinstance(enriched.get("relevant_docs"), list):
        doc_prioritizer = (
            retrieval.prioritize_bootstrap_docs
            if str(packet_kind or "").strip() == "bootstrap_session"
            else retrieval.prioritize_docs
        )
        enriched["relevant_docs"] = doc_prioritizer(
            enriched.get("relevant_docs", []),
            selected_guidance_chunks=retrieval_bundle.get("selected_guidance_chunks", []),
            components=components,
            changed_paths=changed_paths,
        )
    impact_payload = enriched.get("impact", {})
    if isinstance(impact_payload, Mapping) and isinstance(impact_payload.get("docs"), list):
        impact_updated = dict(impact_payload)
        impact_doc_prioritizer = (
            retrieval.prioritize_bootstrap_docs
            if str(packet_kind or "").strip() in {"session_brief", "bootstrap_session"}
            else retrieval.prioritize_docs
        )
        impact_updated["docs"] = impact_doc_prioritizer(
            impact_updated.get("docs", []),
            selected_guidance_chunks=retrieval_bundle.get("selected_guidance_chunks", []),
            components=components,
            changed_paths=changed_paths,
        )
        impact_updated["guidance_brief"] = retrieval_bundle.get("guidance_brief", [])
        enriched["impact"] = impact_updated
    enriched.update(
        _packet_proof_state(
            repo_root=root,
            workstream_selection=workstream_selection,
            candidate_workstreams=candidate_workstreams,
            components=components,
            diagrams=diagrams,
        )
    )
    enriched["retrieval_plan"] = plan
    enriched["guidance_brief"] = retrieval_bundle.get("guidance_brief", [])
    enriched["context_packet_state"] = str(packet_state or "").strip()
    enriched["full_scan_recommended"] = bool(full_scan_recommended)
    enriched["full_scan_reason"] = str(full_scan_reason or "").strip()
    if isinstance(miss_recovery, Mapping):
        miss_recovery_summary = (
            dict(plan.get("miss_recovery", {}))
            if isinstance(plan.get("miss_recovery"), Mapping)
            else {}
        )
        enriched["miss_recovery"] = _compact_finalize_miss_recovery(
            miss_recovery_summary,
            packet_kind=packet_kind,
        )
    enriched["narrowing_guidance"] = routing.build_narrowing_guidance(
        packet_kind=packet_kind,
        packet_state=packet_state,
        full_scan_recommended=full_scan_recommended,
        full_scan_reason=full_scan_reason,
        workstream_selection=workstream_selection,
        retrieval_plan=plan,
        final_payload=enriched,
    )
    if retrieval_bundle.get("working_memory_tiers"):
        enriched["working_memory_tiers"] = retrieval_bundle["working_memory_tiers"]
    else:
        enriched.pop("working_memory_tiers", None)
    budget_meta = budgeting.packet_budget(packet_kind=packet_kind, packet_state=packet_state)
    working_budget = _apply_adaptive_budget_profile(
        _content_budget(
            budget_meta,
            trim_order_paths=_reorder_trim_paths(
                packet_kind=packet_kind,
                packet_state=packet_state,
                selection_state=selection_state,
                retrieval_plan=plan,
                adaptive_packet_profile=adaptive_packet_profile,
            ),
        ),
        adaptive_packet_profile=adaptive_packet_profile,
    )
    build_evidence_pack = not agent_runtime_contract.is_agent_hot_path_profile(delivery_profile)
    hot_path = not build_evidence_pack
    final_packet: dict[str, Any] = {}
    final_metrics: dict[str, Any] = {}
    final_plan: dict[str, Any] = plan
    budget_truncation: dict[str, Any] = {}
    hot_path_context_views = {
        "retrieval_plan": dict(plan),
        "guidance_brief": [dict(row) for row in retrieval_bundle.get("guidance_brief", []) if isinstance(row, Mapping)]
        if isinstance(retrieval_bundle.get("guidance_brief"), list)
        else [],
        "narrowing_guidance": dict(enriched.get("narrowing_guidance", {}))
        if isinstance(enriched.get("narrowing_guidance"), Mapping)
        else {},
    }
    for retry_index in range(3):
        trimmed, _trim_budget, _content_metrics, budget_truncation = budgeting.apply_packet_budget(
            enriched,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_override=working_budget,
        )
        truncation = dict(trimmed.get("truncation", {})) if isinstance(trimmed.get("truncation"), Mapping) else {}
        packet_budget_truncation = dict(budget_truncation)
        packet_budget_truncation["retry_index"] = retry_index
        truncation["packet_budget"] = packet_budget_truncation
        base_payload = dict(trimmed)
        base_payload["packet_budget"] = dict(budget_meta)
        base_payload["truncation"] = truncation
        if _can_reuse_hot_path_context_views(
            packet_kind=packet_kind,
            build_working_memory_tiers=build_evidence_pack,
            payload=base_payload,
        ):
            base_payload, final_plan = _reuse_hot_path_context_views(
                payload=base_payload,
                retrieval_plan=hot_path_context_views["retrieval_plan"],
                guidance_brief=hot_path_context_views["guidance_brief"],
                narrowing_guidance=hot_path_context_views["narrowing_guidance"],
            )
        else:
            base_payload, final_plan = _refresh_context_views(
                repo_root=root,
                packet_kind=packet_kind,
                packet_state=packet_state,
                payload=base_payload,
                changed_paths=changed_paths,
                explicit_paths=explicit_paths,
                shared_only_input=shared_only_input,
                selection_state=selection_state,
                workstream_selection=workstream_selection,
                candidate_workstreams=candidate_workstreams,
                components=components,
                diagrams=diagrams,
                docs=docs,
                recommended_commands=recommended_commands,
                recommended_tests=recommended_tests,
                fallback_guidance_chunks=retrieval_bundle.get("selected_guidance_chunks", []),
                miss_recovery=miss_recovery or {},
                guidance_catalog_summary=guidance_catalog_summary,
                full_scan_recommended=full_scan_recommended,
                full_scan_reason=full_scan_reason,
                session_id=session_id,
                build_working_memory_tiers=build_evidence_pack,
            )
        base_payload["adaptive_packet_profile"] = _adaptive_packet_profile(
            packet_kind=packet_kind,
            packet_state=packet_state,
            selection_state=selection_state,
            retrieval_plan=final_plan,
            optimization_snapshot=optimization,
            full_scan_recommended=full_scan_recommended,
        )
        if hot_path:
            final_packet, final_metrics, _packet_quality, _routing_handoff = _finalize_packet_metadata_hot_path(
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget_meta=budget_meta,
                base_payload=base_payload,
                selection_state=selection_state,
                full_scan_recommended=full_scan_recommended,
                retrieval_plan=final_plan,
            )
        else:
            final_packet, final_metrics, _packet_quality, _routing_handoff = _finalize_packet_metadata(
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget_meta=budget_meta,
                base_payload=base_payload,
                selection_state=selection_state,
                full_scan_recommended=full_scan_recommended,
                retrieval_plan=final_plan,
                build_evidence_pack=build_evidence_pack,
                max_iterations=8,
            )
        if bool(final_metrics.get("within_budget")):
            break
        over_bytes = max(0, int(final_metrics.get("estimated_bytes", 0) or 0) - int(budget_meta.get("max_bytes", 0) or 0))
        over_tokens = max(0, int(final_metrics.get("estimated_tokens", 0) or 0) - int(budget_meta.get("max_tokens", 0) or 0))
        if over_bytes <= 0 and over_tokens <= 0:
            break
        working_budget = dict(working_budget)
        working_budget["max_bytes"] = max(1_000, int(working_budget.get("max_bytes", 0) or 0) - max(over_bytes, 384))
        working_budget["max_tokens"] = max(250, int(working_budget.get("max_tokens", 0) or 0) - max(over_tokens, 96))
    final_packet = _sync_packet_budget_truncation(final_packet, packet_metrics=final_metrics)
    if hot_path and isinstance(final_packet.get("packet_metrics"), Mapping):
        final_metrics = dict(final_packet.get("packet_metrics", {}))
        final_packet = _sync_packet_budget_truncation(final_packet, packet_metrics=final_metrics)
    elif isinstance(final_packet.get("truncation"), Mapping):
        final_packet = _compact_finalize_metadata(final_packet, budget_meta=budget_meta)
        final_packet, _reconciled_metrics, _reconciled_quality, _reconciled_handoff = _finalize_packet_metadata(
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget_meta=budget_meta,
            base_payload=final_packet,
            selection_state=selection_state,
            full_scan_recommended=full_scan_recommended,
            retrieval_plan=final_plan,
            build_evidence_pack=build_evidence_pack,
            max_iterations=1 if hot_path else 8,
        )
        if isinstance(final_packet.get("packet_metrics"), Mapping):
            final_metrics = dict(final_packet.get("packet_metrics", {}))
            final_packet = _sync_packet_budget_truncation(final_packet, packet_metrics=final_metrics)
    if not hot_path and isinstance(final_packet.get("packet_metrics"), Mapping):
        for _ in range(3):
            reconciled_packet, reconciled_metrics, _reconciled_quality, _reconciled_handoff = _finalize_packet_metadata(
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget_meta=budget_meta,
                base_payload=final_packet,
                selection_state=selection_state,
                full_scan_recommended=full_scan_recommended,
                retrieval_plan=final_plan,
                build_evidence_pack=build_evidence_pack,
                max_iterations=1 if hot_path else 8,
            )
            reconciled_packet = _sync_packet_budget_truncation(
                reconciled_packet,
                packet_metrics=reconciled_metrics,
            )
            current_metrics = dict(final_packet.get("packet_metrics", {}))
            current_quality = dict(final_packet.get("packet_quality", {}))
            current_handoff = dict(final_packet.get("routing_handoff", {}))
            current_context_packet = dict(final_packet.get("context_packet", {}))
            current_evidence_pack = dict(final_packet.get("evidence_pack", {}))
            if (
                reconciled_metrics == current_metrics
                and dict(reconciled_packet.get("packet_quality", {})) == current_quality
                and dict(reconciled_packet.get("routing_handoff", {})) == current_handoff
                and dict(reconciled_packet.get("context_packet", {})) == current_context_packet
                and dict(reconciled_packet.get("evidence_pack", {})) == current_evidence_pack
            ):
                break
            final_packet = reconciled_packet
            final_metrics = reconciled_metrics
    if hot_path and isinstance(final_packet.get("packet_metrics"), Mapping):
        final_metrics = dict(final_packet.get("packet_metrics", {}))
    elif isinstance(final_packet.get("packet_metrics"), Mapping):
        for _ in range(1 if hot_path else 4):
            direct_metrics = budgeting.estimate_packet_metrics(
                final_packet,
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget=budget_meta,
            )
            if direct_metrics == dict(final_packet.get("packet_metrics", {})):
                break
            final_packet["packet_metrics"] = dict(direct_metrics)
            final_packet = _sync_packet_budget_truncation(final_packet, packet_metrics=direct_metrics)
            direct_quality = quality.summarize_packet_quality(
                packet_kind=packet_kind,
                packet_state=packet_state,
                selection_state=selection_state,
                full_scan_recommended=full_scan_recommended,
                retrieval_plan=final_plan,
                packet_metrics=direct_metrics,
                final_payload=final_packet,
            )
            final_packet["packet_quality"] = dict(direct_quality)
            direct_handoff = routing.build_routing_handoff(
                packet_kind=packet_kind,
                packet_state=packet_state,
                retrieval_plan=final_plan,
                packet_quality=direct_quality,
                final_payload=final_packet,
            )
            final_packet["routing_handoff"] = dict(direct_handoff)
            final_packet["context_packet"] = tooling_memory_contracts.build_context_packet(
                packet_kind=packet_kind,
                packet_state=packet_state,
                payload=final_packet,
            )
            if build_evidence_pack:
                final_packet["evidence_pack"] = tooling_memory_contracts.build_evidence_pack(
                    packet_kind=packet_kind,
                    packet_state=packet_state,
                    payload=final_packet,
                )
            else:
                final_packet.pop("evidence_pack", None)
    final_truth_metrics = (
        dict(final_packet.get("packet_metrics", {}))
        if hot_path and isinstance(final_packet.get("packet_metrics"), Mapping)
        else budgeting.estimate_packet_metrics(
            final_packet,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
    )
    if not bool(final_truth_metrics.get("within_budget")) and isinstance(final_packet.get("truncation"), Mapping):
        for _ in range(3):
            compacted_packet = _compact_finalize_metadata(final_packet, budget_meta=budget_meta)
            if compacted_packet == final_packet:
                break
            final_packet = compacted_packet
            final_truth_metrics = budgeting.estimate_packet_metrics(
                final_packet,
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget=budget_meta,
            )
            final_packet["packet_metrics"] = dict(final_truth_metrics)
            final_packet = _sync_packet_budget_truncation(final_packet, packet_metrics=final_truth_metrics)
            if bool(final_truth_metrics.get("within_budget")):
                break
    final_packet["packet_metrics"] = dict(final_truth_metrics)
    final_packet = _sync_packet_budget_truncation(final_packet, packet_metrics=final_truth_metrics)
    final_within_budget = bool(final_truth_metrics.get("within_budget"))
    if isinstance(final_packet.get("packet_quality"), Mapping):
        packet_quality_payload = dict(final_packet.get("packet_quality", {}))
        packet_quality_payload["within_budget"] = final_within_budget
        final_packet["packet_quality"] = packet_quality_payload
    if isinstance(final_packet.get("routing_handoff"), Mapping):
        routing_handoff_payload = dict(final_packet.get("routing_handoff", {}))
        routing_handoff_payload["within_budget"] = final_within_budget
        if isinstance(routing_handoff_payload.get("packet_quality"), Mapping):
            handoff_quality_payload = dict(routing_handoff_payload.get("packet_quality", {}))
            handoff_quality_payload["within_budget"] = final_within_budget
            routing_handoff_payload["packet_quality"] = handoff_quality_payload
        if isinstance(routing_handoff_payload.get("optimization"), Mapping):
            handoff_optimization_payload = dict(routing_handoff_payload.get("optimization", {}))
            handoff_optimization_payload["within_budget"] = final_within_budget
            routing_handoff_payload["optimization"] = handoff_optimization_payload
        if isinstance(routing_handoff_payload.get("odylith_execution_profile"), Mapping):
            execution_profile_payload = dict(routing_handoff_payload.get("odylith_execution_profile", {}))
            if isinstance(execution_profile_payload.get("constraints"), Mapping):
                execution_constraints = dict(execution_profile_payload.get("constraints", {}))
                execution_constraints["within_budget"] = final_within_budget
                execution_profile_payload["constraints"] = execution_constraints
            routing_handoff_payload["odylith_execution_profile"] = execution_profile_payload
        final_packet["routing_handoff"] = routing_handoff_payload
    if not hot_path:
        final_truth_metrics = budgeting.estimate_packet_metrics(
            final_packet,
            packet_kind=packet_kind,
            packet_state=packet_state,
            budget=budget_meta,
        )
        final_packet["packet_metrics"] = dict(final_truth_metrics)
        final_packet = _sync_packet_budget_truncation(final_packet, packet_metrics=final_truth_metrics)
        for _ in range(4):
            stabilized_metrics = budgeting.estimate_packet_metrics(
                final_packet,
                packet_kind=packet_kind,
                packet_state=packet_state,
                budget=budget_meta,
            )
            if stabilized_metrics == dict(final_packet.get("packet_metrics", {})):
                break
            final_packet["packet_metrics"] = dict(stabilized_metrics)
            final_packet = _sync_packet_budget_truncation(final_packet, packet_metrics=stabilized_metrics)
    return final_packet


__all__ = ["finalize_packet"]

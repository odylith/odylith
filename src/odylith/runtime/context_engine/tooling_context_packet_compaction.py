"""Compaction helpers for Context Engine packet finalization."""

from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence

from odylith.runtime.common.value_coercion import int_value as _int_value
from odylith.runtime.common.value_coercion import mapping_copy as _mapping_value
from odylith.runtime.common.value_coercion import string_rows as _string_rows
from odylith.runtime.context_engine import tooling_context_budgeting as budgeting
from odylith.runtime.context_engine import tooling_context_retrieval as retrieval


def mapping_rows(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def guidance_actionability_read_path(row: Mapping[str, Any]) -> str:
    actionability = _mapping_value(row.get("actionability"))
    return str(actionability.get("read_path", "")).strip() or str(row.get("read_path", "")).strip()


def guidance_evidence_score(row: Mapping[str, Any]) -> int:
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
            read_path = guidance_actionability_read_path(secondary)
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
    if not guidance_evidence_score(merged):
        fallback_score = guidance_evidence_score(secondary)
        if fallback_score:
            merged["score"] = fallback_score
    return merged


def merge_guidance_rows(
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


def nested_mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, {})
    return dict(value) if isinstance(value, Mapping) else {}


def compact_finalize_test_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
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


def compact_finalize_workstream_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
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


def compact_finalize_guidance_catalog(summary: Mapping[str, Any]) -> dict[str, Any]:
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


def compact_finalize_retrieval_plan(plan: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(plan)
    guidance_rows = mapping_rows(compacted.get("selected_guidance_chunks"))
    bootstrap_packet = str(packet_kind or "").strip() == "bootstrap_session"
    compact_bootstrap = bootstrap_packet and str(packet_state or "").strip() == "compact"
    gated_bootstrap = bootstrap_packet and str(packet_state or "").strip().startswith("gated_")
    strict_bootstrap = compact_bootstrap or gated_bootstrap
    if guidance_rows and not strict_bootstrap:
        compacted["selected_guidance_chunks"] = retrieval.compact_guidance_brief(
            guidance_rows,
            limit=1 if bootstrap_packet else 2,
        )
    workstream_rows = mapping_rows(compacted.get("selected_workstreams"))
    if workstream_rows:
        compacted["selected_workstreams"] = compact_finalize_workstream_rows(
            workstream_rows,
            limit=2 if str(packet_kind or "").strip() == "bootstrap_session" else 3,
        )
    if bootstrap_packet:
        guidance_rows = mapping_rows(compacted.get("selected_guidance_chunks"))
        if guidance_rows and strict_bootstrap:
            compacted["selected_guidance_chunks"] = [
                {
                    key: value
                    for key, value in {
                        "chunk_id": str(row.get("chunk_id", "")).strip(),
                        "title": str(row.get("title", "")).strip(),
                        "match_tier": str(row.get("match_tier", "")).strip(),
                        "score": guidance_evidence_score(row),
                        "read_path": guidance_actionability_read_path(row),
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
        selected_tests = mapping_rows(compacted.get("selected_tests"))
        test_limit = 1 if strict_bootstrap else 2
        if len(selected_tests) > test_limit:
            compacted["selected_tests"] = compact_finalize_test_rows(selected_tests, limit=test_limit)
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
        compacted["guidance_catalog"] = compact_finalize_guidance_catalog(guidance_catalog)
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


def compact_finalize_working_memory_tiers(
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
        row = nested_mapping(compacted, tier_name)
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
            tests = mapping_rows(row.get("recommended_tests"))
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
                    row["recommended_tests"] = compact_finalize_test_rows(tests, limit=1)
        elif tier_name == "warm":
            docs = _string_rows(row.get("docs"))
            guidance_chunks = mapping_rows(row.get("guidance_chunks"))
            workstreams = mapping_rows(row.get("workstreams"))
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
                    row["workstreams"] = compact_finalize_workstream_rows(workstreams, limit=1)
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


def compact_finalize_engineering_notes(notes: Mapping[str, Any], *, packet_kind: str) -> dict[str, Any]:
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


def compact_finalize_impact_summary(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() not in {"bootstrap_session", "session_brief"}:
        return compacted
    session_brief_packet = str(packet_kind or "").strip() == "session_brief"
    primary = nested_mapping(compacted, "primary_workstream")
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
    workstreams = mapping_rows(compacted.get("workstreams"))
    if workstreams:
        compacted["workstreams"] = compact_finalize_workstream_rows(
            workstreams,
            limit=1 if str(packet_state or "").strip() == "gated_broad_scope" or session_brief_packet else 2,
        )
    guidance_brief = mapping_rows(compacted.get("guidance_brief"))
    if guidance_brief:
        compacted["guidance_brief"] = retrieval.compact_guidance_brief(
            guidance_brief,
            limit=1,
        )
    miss_recovery = nested_mapping(compacted, "miss_recovery")
    if miss_recovery:
        compacted["miss_recovery"] = compact_finalize_miss_recovery(
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
        recommended_tests = mapping_rows(compacted.get("recommended_tests"))
        if recommended_tests:
            compacted["recommended_tests"] = compact_finalize_test_rows(recommended_tests, limit=1)
        engineering_notes = nested_mapping(compacted, "engineering_notes")
        if engineering_notes:
            compacted["engineering_notes"] = compact_finalize_engineering_notes(
                engineering_notes,
                packet_kind="bootstrap_session",
            )
    compacted.pop("components", None)
    compacted.pop("diagrams", None)
    return {key: value for key, value in compacted.items() if value not in ("", [], {}, None)}


def compact_finalize_miss_recovery(summary: Mapping[str, Any], *, packet_kind: str) -> dict[str, Any]:
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


def compact_finalize_session(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
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


def compact_finalize_narrowing_guidance(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    suggested_inputs = _string_rows(compacted.get("suggested_inputs"))
    if len(suggested_inputs) > 3:
        compacted["suggested_inputs"] = suggested_inputs[:3]
    anchors = mapping_rows(compacted.get("next_best_anchors"))
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


def compact_finalize_runtime(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    timings = nested_mapping(compacted, "timings")
    if timings:
        recent = mapping_rows(timings.get("recent"))
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


def compact_finalize_packet_quality(summary: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compacted = dict(summary)
    if str(packet_kind or "").strip() != "bootstrap_session":
        return compacted
    normalized_state = str(packet_state or "").strip()
    if normalized_state != "compact" and not normalized_state.startswith("gated_"):
        return compacted
    intent_profile = nested_mapping(compacted, "intent_profile")
    utility_profile = nested_mapping(compacted, "utility_profile")
    token_efficiency = nested_mapping(compacted, "token_efficiency")
    context_density = nested_mapping(compacted, "context_density")
    evidence_diversity = nested_mapping(compacted, "evidence_diversity")
    reasoning_readiness = nested_mapping(compacted, "reasoning_readiness")
    evidence_quality = nested_mapping(compacted, "evidence_quality")
    actionability = nested_mapping(compacted, "actionability")
    validation_pressure = nested_mapping(compacted, "validation_pressure")
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


def compact_finalize_metadata(packet: Mapping[str, Any], *, budget_meta: Mapping[str, Any]) -> dict[str, Any]:
    compacted = dict(packet)
    budget_bytes = int(budget_meta.get("max_bytes", 0) or 0)
    budget_tokens = int(budget_meta.get("max_tokens", 0) or 0)
    packet_kind = str(nested_mapping(compacted, "packet_metrics").get("packet_kind", "")).strip()
    packet_state = str(nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip()
    for _ in range(4):
        actual_bytes = len(json.dumps(compacted, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        actual_tokens = int(math.ceil(actual_bytes / budgeting.ESTIMATED_BYTES_PER_TOKEN))
        if actual_bytes <= budget_bytes and actual_tokens <= budget_tokens:
            return compacted
        changed = False
        retrieval_plan = nested_mapping(compacted, "retrieval_plan")
        if retrieval_plan:
            compact_plan = compact_finalize_retrieval_plan(
                retrieval_plan,
                packet_kind=packet_kind,
                packet_state=str(nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_plan != retrieval_plan:
                compacted["retrieval_plan"] = compact_plan
                changed = True
        working_memory_tiers = nested_mapping(compacted, "working_memory_tiers")
        if working_memory_tiers:
            compact_tiers = compact_finalize_working_memory_tiers(
                working_memory_tiers,
                packet_kind=packet_kind,
                packet_state=packet_state,
            )
            if compact_tiers != working_memory_tiers:
                compacted["working_memory_tiers"] = compact_tiers
                changed = True
        top_engineering_notes = nested_mapping(compacted, "top_engineering_notes")
        if top_engineering_notes:
            compact_notes = compact_finalize_engineering_notes(top_engineering_notes, packet_kind=packet_kind)
            if compact_notes != top_engineering_notes:
                compacted["top_engineering_notes"] = compact_notes
                changed = True
        impact_summary = nested_mapping(compacted, "impact_summary")
        if impact_summary:
            compact_summary = compact_finalize_impact_summary(
                impact_summary,
                packet_kind=packet_kind,
                packet_state=str(nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_summary != impact_summary:
                compacted["impact_summary"] = compact_summary
                changed = True
        impact_payload = nested_mapping(compacted, "impact")
        if impact_payload:
            compact_impact = compact_finalize_impact_summary(
                impact_payload,
                packet_kind=packet_kind,
                packet_state=str(nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_impact != impact_payload:
                compacted["impact"] = compact_impact
                changed = True
        session = nested_mapping(compacted, "session")
        if session:
            compact_session = compact_finalize_session(
                session,
                packet_kind=packet_kind,
                packet_state=str(nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_session != session:
                compacted["session"] = compact_session
                changed = True
        narrowing = nested_mapping(compacted, "narrowing_guidance")
        if narrowing:
            compact_narrowing = compact_finalize_narrowing_guidance(
                narrowing,
                packet_kind=packet_kind,
                packet_state=str(nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_narrowing != narrowing:
                compacted["narrowing_guidance"] = compact_narrowing
                changed = True
        runtime = nested_mapping(compacted, "runtime")
        if runtime:
            compact_runtime = compact_finalize_runtime(
                runtime,
                packet_kind=packet_kind,
                packet_state=str(nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_runtime != runtime:
                compacted["runtime"] = compact_runtime
                changed = True
        packet_quality = nested_mapping(compacted, "packet_quality")
        if packet_quality:
            compact_quality = compact_finalize_packet_quality(
                packet_quality,
                packet_kind=packet_kind,
                packet_state=str(nested_mapping(compacted, "packet_metrics").get("packet_state", "")).strip(),
            )
            if compact_quality != packet_quality:
                compacted["packet_quality"] = compact_quality
                changed = True
        if str(packet_kind or "").strip() in {"bootstrap_session", "session_brief", "governance_slice"}:
            recommended_tests = mapping_rows(compacted.get("recommended_tests"))
            if recommended_tests:
                compact_tests = compact_finalize_test_rows(recommended_tests, limit=1)
                if compact_tests != recommended_tests:
                    compacted["recommended_tests"] = compact_tests
                    changed = True
            context_packet = nested_mapping(compacted, "context_packet")
            if context_packet:
                execution_profile = nested_mapping(context_packet, "execution_profile")
                if execution_profile and "signals" in execution_profile:
                    execution_profile.pop("signals", None)
                    context_packet["execution_profile"] = execution_profile
                    compacted["context_packet"] = context_packet
                    changed = True
            routing_handoff = nested_mapping(compacted, "routing_handoff")
            if routing_handoff:
                odylith_execution_profile = nested_mapping(routing_handoff, "odylith_execution_profile")
                if odylith_execution_profile and "signals" in odylith_execution_profile:
                    odylith_execution_profile.pop("signals", None)
                    routing_handoff["odylith_execution_profile"] = odylith_execution_profile
                    compacted["routing_handoff"] = routing_handoff
                    changed = True
            evidence_pack = nested_mapping(compacted, "evidence_pack")
            if evidence_pack:
                evidence_handoff = nested_mapping(evidence_pack, "routing_handoff")
                evidence_profile = nested_mapping(evidence_handoff, "odylith_execution_profile")
                if evidence_profile and "signals" in evidence_profile:
                    evidence_profile.pop("signals", None)
                    evidence_handoff["odylith_execution_profile"] = evidence_profile
                    evidence_pack["routing_handoff"] = evidence_handoff
                    compacted["evidence_pack"] = evidence_pack
                    changed = True
        truncation = nested_mapping(compacted, "truncation")
        packet_budget = nested_mapping(truncation, "packet_budget")
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
        budget_payload = nested_mapping(compacted, "packet_budget")
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
        metrics = nested_mapping(compacted, "packet_metrics")
        sections = nested_mapping(metrics, "sections")
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



__all__ = [
    "compact_finalize_metadata",
    "compact_finalize_miss_recovery",
    "compact_finalize_test_rows",
    "guidance_actionability_read_path",
    "guidance_evidence_score",
    "mapping_rows",
    "merge_guidance_rows",
    "nested_mapping",
]

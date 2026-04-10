"""Routing-plane helpers for Odylith Context Engine context packets."""

from __future__ import annotations

import shlex
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import host_runtime as host_runtime_contract
from odylith.runtime.context_engine import governance_signal_codec


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for item in values:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _truncate(text: str, *, max_chars: int = 140) -> str:
    normalized = " ".join(str(text or "").strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max(0, max_chars - 1)].rstrip() + "…"


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalized_string_list(value: Any) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [str(item).strip() for item in value if str(item).strip()]
    token = str(value or "").strip()
    return [token] if token else []


def _shell_quote(value: str) -> str:
    return shlex.quote(str(value or "").strip())


def _fallback_anchor_commands(anchor: Mapping[str, Any]) -> tuple[str, str]:
    value = str(anchor.get("value", "")).strip()
    if not value:
        return "", ""
    next_command = f"./.odylith/bin/odylith context --repo-root . {_shell_quote(value)}"
    anchor_kind = str(anchor.get("kind", "")).strip()
    followup = ""
    if anchor_kind in {"doc", "path"} or "/" in value:
        followup = f"sed -n '1,200p' {_shell_quote(value)}"
    return next_command, followup


def _fallback_scan_commands(*, fallback_scan: Mapping[str, Any], retained_paths: Sequence[str]) -> tuple[str, str]:
    query = str(fallback_scan.get("query", "")).strip()
    candidate_paths = _dedupe_strings(
        [
            *_normalized_string_list(fallback_scan.get("changed_paths")),
            *(str(token).strip() for token in retained_paths if str(token).strip()),
        ]
    )
    followup = ""
    if candidate_paths:
        followup = f"sed -n '1,200p' {_shell_quote(candidate_paths[0])}"
    if query and candidate_paths:
        scoped_paths = " ".join(_shell_quote(path) for path in candidate_paths[:4])
        return f"rg -n --context 2 {_shell_quote(query)} -- {scoped_paths}", followup
    if query:
        return f"rg -n --context 2 {_shell_quote(query)} .", ""
    if candidate_paths:
        pattern = "|".join(
            str(path).replace("\\", "\\\\").replace(".", r"\.")
            for path in candidate_paths[:4]
        )
        return f"rg --files | rg {_shell_quote(pattern)}", followup
    return r"rg --files | rg 'AGENTS\.md|odylith/AGENTS\.md|pyproject\.toml'", "sed -n '1,200p' AGENTS.md"


def _count_or_list_len(payload: Mapping[str, Any], *, list_key: str, count_key: str) -> int:
    value = payload.get(list_key)
    list_count = (
        len([row for row in value if row not in ("", [], {}, None)])
        if isinstance(value, list)
        else len(_normalized_string_list(value))
    )
    return max(
        list_count,
        _int_value(payload.get(count_key)),
    )


def _embedded_governance_signal(payload: Mapping[str, Any]) -> dict[str, Any]:
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    return governance_signal_codec.expand_governance_signal(
        dict(route.get("governance", {})) if isinstance(route.get("governance"), Mapping) else {}
    )


def _routing_validation_bundle(payload: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("validation_bundle"), Mapping):
        return dict(payload.get("validation_bundle", {}))
    governance = _embedded_governance_signal(payload)
    compact: dict[str, Any] = {}
    for key in (
        "recommended_command_count",
        "strict_gate_command_count",
        "plan_binding_required",
        "governed_surface_sync_required",
    ):
        value = governance.get(key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _routing_governance_obligations(payload: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("governance_obligations"), Mapping):
        return dict(payload.get("governance_obligations", {}))
    governance = _embedded_governance_signal(payload)
    compact: dict[str, Any] = {}
    for key in (
        "touched_workstream_count",
        "primary_workstream_id",
        "touched_component_count",
        "primary_component_id",
        "required_diagram_count",
        "linked_bug_count",
        "closeout_doc_count",
        "workstream_state_action_count",
    ):
        value = governance.get(key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _score_level(score: int) -> str:
    clamped = max(0, min(4, int(score)))
    if clamped >= 4:
        return "high"
    if clamped >= 2:
        return "medium"
    if clamped >= 1:
        return "low"
    return "none"


def _score_from_level(value: Any) -> int:
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if token in {"very_high", "high", "strong", "grounded", "actionable", "deep_validation"}:
        return 4
    if token in {"medium", "moderate", "balanced", "accuracy_first", "bounded_parallel_candidate"}:
        return 3
    if token in {"low", "light", "guarded_narrowing", "serial_preferred"}:
        return 2
    if token in {"none", "serial_guarded"}:
        return 1 if token == "serial_guarded" else 0
    return 0


def _explicit_model_selection_fields(*, profile: str, host_capabilities: Mapping[str, Any]) -> tuple[str, str]:
    canonical_profile = agent_runtime_contract.canonical_execution_profile(profile)
    if not canonical_profile or not bool(host_capabilities.get("supports_explicit_model_selection")):
        return "", ""
    if canonical_profile in {
        agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE,
        agent_runtime_contract.ANALYSIS_HIGH_PROFILE,
    }:
        return "gpt-5.4-mini", "high" if canonical_profile == agent_runtime_contract.ANALYSIS_HIGH_PROFILE else "medium"
    if canonical_profile == agent_runtime_contract.FAST_WORKER_PROFILE:
        return "gpt-5.3-codex-spark", "medium"
    if canonical_profile in {
        agent_runtime_contract.WRITE_MEDIUM_PROFILE,
        agent_runtime_contract.WRITE_HIGH_PROFILE,
    }:
        return "gpt-5.3-codex", "high" if canonical_profile == agent_runtime_contract.WRITE_HIGH_PROFILE else "medium"
    if canonical_profile == agent_runtime_contract.FRONTIER_XHIGH_PROFILE:
        return "gpt-5.4", "xhigh"
    if canonical_profile == agent_runtime_contract.FRONTIER_HIGH_PROFILE:
        return "gpt-5.4", "high"
    return "", ""


def grounded_ambiguous_write_candidate(
    *,
    anchor_quality: str,
    guidance_coverage: str,
    ambiguity_class: str,
    evidence_consensus: str,
    precision_score: int,
    actionability_score: int,
    validation_score: int,
    direct_guidance_chunk_count: int = 0,
    actionable_guidance_chunk_count: int = 0,
    selected_test_count: int = 0,
    selected_command_count: int = 0,
) -> bool:
    ambiguity = str(ambiguity_class or "").strip()
    if ambiguity not in {"historical_fanout", "close_competition"}:
        return False
    if str(anchor_quality or "").strip() not in {"explicit", "non_shared"}:
        return False
    has_guidance = str(guidance_coverage or "").strip() in {"direct", "anchored"} or direct_guidance_chunk_count > 0
    has_validation = validation_score >= 2 or selected_test_count > 0 or selected_command_count > 0
    has_actionable = actionability_score >= 2 or actionable_guidance_chunk_count > 0
    consensus = str(evidence_consensus or "").strip()
    if consensus not in {"strong", "mixed"}:
        return False
    if consensus == "mixed" and not has_validation:
        return False
    if not has_guidance and not has_validation:
        return False
    if not has_actionable and not has_validation:
        return False
    strong_validation_backstop = bool(
        has_guidance
        and has_validation
        and has_actionable
        and int(precision_score or 0) >= 40
    )
    if int(precision_score or 0) < 45 and consensus != "strong" and not strong_validation_backstop:
        return False
    if int(precision_score or 0) < 40 and not has_validation:
        return False
    return True


def grounded_write_execution_ready(
    *,
    packet_kind: str,
    packet_state: str,
    full_scan_recommended: bool,
    narrowing_required: bool,
    within_budget: bool,
    routing_confidence: str,
    has_non_shared_anchor: bool,
    ambiguity_class: str,
    guidance_coverage: str,
    intent_family: str,
    actionability_score: int,
    validation_score: int,
    context_density_score: int,
    evidence_quality_score: int,
    evidence_consensus: str = "",
    precision_score: int = 0,
    direct_guidance_chunk_count: int = 0,
    actionable_guidance_chunk_count: int = 0,
    selected_test_count: int = 0,
    selected_command_count: int = 0,
    selected_doc_count: int = 0,
    strict_gate_command_count: int = 0,
    plan_binding_required: bool = False,
    governed_surface_sync_required: bool = False,
) -> bool:
    family = str(intent_family or "").strip().lower()
    ambiguity = str(ambiguity_class or "").strip()
    packet_kind_token = str(packet_kind or "").strip()
    packet_state_token = str(packet_state or "").strip()
    guidance = str(guidance_coverage or "").strip()
    confidence = str(routing_confidence or "").strip()
    if not within_budget or full_scan_recommended or narrowing_required:
        return False
    analysis_exact_path_candidate = bool(
        family in {"analysis", "review", "diagnosis"}
        and packet_kind_token in {"impact", "governance_slice", "session_brief", "bootstrap_session"}
        and confidence in {"medium", "high"}
        and has_non_shared_anchor
        and ambiguity not in {"broad_shared_only"}
        and guidance in {"direct", "anchored"}
        and int(precision_score or 0) >= 55
        and (
            int(validation_score or 0) >= 2
            or int(selected_test_count or 0) > 0
            or int(selected_command_count or 0) > 0
            or int(strict_gate_command_count or 0) > 0
            or bool(plan_binding_required)
            or bool(governed_surface_sync_required)
        )
    )
    if packet_kind_token == "architecture" or family == "architecture":
        return False
    if family in {"analysis", "review", "diagnosis"} and not analysis_exact_path_candidate:
        return False
    if packet_state_token == "gated_broad_scope":
        return False
    if confidence not in {"medium", "high"} or not has_non_shared_anchor:
        return False
    allow_grounded_ambiguity = grounded_ambiguous_write_candidate(
        anchor_quality="non_shared" if has_non_shared_anchor else "none",
        guidance_coverage=guidance,
        ambiguity_class=ambiguity,
        evidence_consensus=str(evidence_consensus or "").strip(),
        precision_score=int(precision_score or 0),
        actionability_score=int(actionability_score or 0),
        validation_score=int(validation_score or 0),
        direct_guidance_chunk_count=int(direct_guidance_chunk_count or 0),
        actionable_guidance_chunk_count=int(actionable_guidance_chunk_count or 0),
        selected_test_count=int(selected_test_count or 0),
        selected_command_count=int(selected_command_count or 0),
    )
    if ambiguity == "broad_shared_only":
        return False
    if ambiguity in {"historical_fanout", "close_competition"} and not allow_grounded_ambiguity:
        return False
    has_guidance = guidance in {"direct", "anchored"} or direct_guidance_chunk_count > 0 or actionable_guidance_chunk_count > 0
    has_validation = (
        validation_score >= 2
        or selected_test_count > 0
        or selected_command_count > 0
        or strict_gate_command_count > 0
    )
    has_governance_closeout = (
        selected_doc_count > 0
        or strict_gate_command_count > 0
        or bool(plan_binding_required)
        or bool(governed_surface_sync_required)
    )
    strong_guidance_contract = bool(
        has_guidance
        and actionability_score >= 3
        and (confidence == "high" or int(precision_score or 0) >= 70)
    )
    has_density = context_density_score >= 2 or evidence_quality_score >= 3
    has_execution_contract = bool(has_validation or has_governance_closeout or strong_guidance_contract)
    if not has_execution_contract:
        return False
    if actionability_score < 2 and not (has_guidance or has_validation or has_density):
        return False
    return bool(has_guidance or has_validation or has_density)


def native_spawn_execution_ready(
    *,
    route_ready: bool,
    full_scan_recommended: bool,
    narrowing_required: bool,
    within_budget: bool,
    delegate_preference: str,
    model: str,
    reasoning_effort: str,
    agent_role: str,
    selection_mode: str,
    selected_test_count: int = 0,
    selected_command_count: int = 0,
    selected_doc_count: int = 0,
    strict_gate_command_count: int = 0,
    plan_binding_required: bool = False,
    governed_surface_sync_required: bool = False,
    host_runtime: str = "",
) -> bool:
    resolved_host_runtime = host_runtime_contract.resolve_host_runtime(host_runtime)
    if not host_runtime_contract.native_spawn_supported(resolved_host_runtime, default_when_unknown=False):
        return False
    if not route_ready or full_scan_recommended or narrowing_required or not within_budget:
        return False
    if str(delegate_preference or "").strip() != "delegate":
        return False
    if not all(
        str(token or "").strip()
        for token in (model, reasoning_effort, agent_role, selection_mode)
    ):
        return False
    return bool(
        selected_test_count > 0
        or selected_command_count > 0
        or selected_doc_count > 0
        or strict_gate_command_count > 0
        or bool(plan_binding_required)
        or bool(governed_surface_sync_required)
    )


def _compact_component_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 4) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("entity_id", "")).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        compact.append(
            {
                "entity_id": token,
                "title": str(row.get("title", "")).strip(),
                "path": str(row.get("path", "")).strip(),
            }
        )
        if len(compact) >= max(1, int(limit)):
            return compact
    return compact


def _compact_workstream_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("entity_id", "")).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        payload = {
            "entity_id": token,
            "title": str(row.get("title", "")).strip(),
        }
        evidence = row.get("evidence", {})
        if isinstance(evidence, Mapping):
            payload["evidence"] = {
                "score": _int_value(evidence.get("score")),
                "strong_signal_count": _int_value(evidence.get("strong_signal_count")),
                "broad_only": bool(evidence.get("broad_only")),
            }
        compact.append(payload)
        if len(compact) >= max(1, int(limit)):
            return compact
    return compact


def _compact_entity_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    key: str = "entity_id",
    title_field: str = "title",
    limit: int = 4,
) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get(key, "")).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        compact.append({key: token, title_field: str(row.get(title_field, "")).strip()})
        if len(compact) >= max(1, int(limit)):
            return compact
    return compact


def _compact_test_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 4) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        path = str(row.get("path", "")).strip()
        if not path or path in seen:
            continue
        seen.add(path)
        compact_row = {
            "path": path,
            "nodeid": str(row.get("nodeid", "")).strip(),
            "reason": str(row.get("reason", "")).strip(),
        }
        compact.append({key: value for key, value in compact_row.items() if value not in ("", [], {}, None)})
        if len(compact) >= max(1, int(limit)):
            return compact
    return compact


def _compact_guidance_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 4) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        chunk_id = str(row.get("chunk_id", "")).strip()
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        evidence_summary = row.get("evidence_summary", {})
        if not isinstance(evidence_summary, Mapping):
            evidence_summary = {}
        actionability = row.get("actionability", {})
        if not isinstance(actionability, Mapping):
            actionability = {}
        read_path = str(actionability.get("read_path", "")).strip() or str(row.get("read_path", "")).strip()
        signals = _dedupe_strings(
            [
                *([str(token) for token in actionability.get("signals", [])] if isinstance(actionability.get("signals", []), list) else []),
                *([str(token) for token in row.get("signals", [])] if isinstance(row.get("signals", []), list) else []),
            ]
        )[:3]
        compact.append(
            {
                "chunk_id": chunk_id,
                "note_kind": str(row.get("note_kind", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "summary": _truncate(str(row.get("summary", "")).strip(), max_chars=120),
                "canonical_source": str(row.get("canonical_source", "")).strip(),
                "risk_class": str(row.get("risk_class", "")).strip(),
                "match_tier": str(evidence_summary.get("match_tier", row.get("match_tier", ""))).strip(),
                "matched_by": _dedupe_strings([str(token) for token in evidence_summary.get("matched_by", [])])[:3],
                "score": _int_value(evidence_summary.get("score", row.get("score"))),
                "evidence_summary": {
                    "score": _int_value(evidence_summary.get("score", row.get("score"))),
                    "match_tier": str(evidence_summary.get("match_tier", row.get("match_tier", ""))).strip(),
                    "matched_paths": _dedupe_strings([str(token) for token in evidence_summary.get("matched_paths", [])])[:2],
                },
                "actionability": {
                    "actionable": bool(actionability.get("actionable")),
                    "direct": bool(actionability.get("direct")),
                    "read_path": read_path,
                    "signals": signals,
                },
            }
        )
        if len(compact) >= max(1, int(limit)):
            return compact
    return compact


def _compact_miss_recovery(summary: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(summary, Mapping):
        return {}
    recovered_entities = summary.get("recovered_entities", [])
    if not isinstance(recovered_entities, list):
        recovered_entities = []
    recovered_tests = summary.get("recovered_tests", [])
    if not isinstance(recovered_tests, list):
        recovered_tests = []
    return {
        key: value
        for key, value in {
            "active": bool(summary.get("active")),
            "applied": bool(summary.get("applied")),
            "mode": str(summary.get("mode", "")).strip(),
            "activation_reason": str(summary.get("activation_reason", "")).strip(),
            "queries": [str(token).strip() for token in summary.get("queries", [])[:3] if str(token).strip()]
            if isinstance(summary.get("queries"), list)
            else [],
            "recovered_docs": [
                str(token).strip()
                for token in summary.get("recovered_docs", [])[:3]
                if str(token).strip()
            ]
            if isinstance(summary.get("recovered_docs"), list)
            else [],
            "recovered_tests": _compact_test_rows(recovered_tests, limit=2),
            "recovered_entities": _compact_entity_rows(
                recovered_entities,
                key="path",
                title_field="title",
                limit=3,
            ),
        }.items()
        if value not in ("", [], {}, None)
    }


def _compact_handoff_guidance_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 1) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in _compact_guidance_rows(rows, limit=limit):
        if not isinstance(row, Mapping):
            continue
        actionability = row.get("actionability", {})
        if not isinstance(actionability, Mapping):
            actionability = {}
        read_path = str(actionability.get("read_path", "")).strip() or str(row.get("read_path", "")).strip()
        actionability_signals = (
            [str(token) for token in actionability.get("signals", [])]
            if isinstance(actionability.get("signals", []), list)
            else []
        )
        row_signals = [str(token) for token in row.get("signals", [])] if isinstance(row.get("signals", []), list) else []
        signals = _dedupe_strings([*actionability_signals, *row_signals])[:2]
        compact.append(
            {
                "chunk_id": str(row.get("chunk_id", "")).strip(),
                "match_tier": str(row.get("match_tier", "")).strip(),
                "score": _int_value(row.get("score")),
                "read_path": read_path,
                "signals": signals,
            }
        )
    return compact


def _anchor_quality(*, selection_state: str, shared_only_input: bool, anchor_paths: Sequence[str]) -> str:
    if str(selection_state or "").strip() == "explicit":
        return "explicit"
    if anchor_paths and not shared_only_input:
        return "non_shared"
    if anchor_paths and shared_only_input:
        return "shared_only"
    return "none"


def _guidance_coverage(selected_guidance_chunks: Sequence[Mapping[str, Any]]) -> str:
    tiers = {
        str(row.get("match_tier", "")).strip()
        for row in selected_guidance_chunks
        if isinstance(row, Mapping) and str(row.get("match_tier", "")).strip()
    }
    if "direct_path" in tiers:
        return "direct"
    if "anchored_context" in tiers:
        return "anchored"
    if "canonical_source" in tiers or "note_match" in tiers or "task_family" in tiers:
        return "supporting"
    return "none"


def _workstream_selection_metrics(workstream_selection: Mapping[str, Any]) -> tuple[int, int, str]:
    return (
        _int_value(workstream_selection.get("candidate_count")),
        _int_value(workstream_selection.get("strong_candidate_count")),
        str(workstream_selection.get("ambiguity_class", "")).strip(),
    )


def _evidence_profile(
    *,
    anchor_quality: str,
    guidance_coverage: str,
    selected_components: Sequence[Mapping[str, Any]],
    selected_workstreams: Sequence[Mapping[str, Any]],
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    precision_score: int,
) -> dict[str, Any]:
    score = 0
    if anchor_quality == "explicit":
        score += 2
    elif anchor_quality == "non_shared":
        score += 1
    if guidance_coverage == "direct":
        score += 2
    elif guidance_coverage == "anchored":
        score += 1
    if selected_components:
        score += 1
    if selected_workstreams:
        strong = max(
            (
                _int_value(dict(row.get("evidence", {})).get("strong_signal_count"))
                for row in selected_workstreams
                if isinstance(row, Mapping)
            ),
            default=0,
        )
        score += 1 if strong > 0 else 0
    if precision_score >= 70:
        score += 1
    direct_guidance_count = sum(
        1
        for row in selected_guidance_chunks
        if isinstance(row, Mapping) and str(row.get("match_tier", "")).strip() == "direct_path"
    )
    return {
        "score": max(0, min(4, score)),
        "level": _score_level(score),
        "direct_guidance_count": direct_guidance_count,
        "component_count": len(selected_components),
        "workstream_count": len(selected_workstreams),
    }


def _actionability_profile(
    *,
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    selected_docs: Sequence[str],
    selected_tests: Sequence[Mapping[str, Any]],
    selected_commands: Sequence[str],
) -> dict[str, Any]:
    actionable_guidance_count = sum(
        1
        for row in selected_guidance_chunks
        if isinstance(row, Mapping)
        and isinstance(row.get("actionability"), Mapping)
        and bool(dict(row.get("actionability", {})).get("actionable"))
    )
    score = 0
    if actionable_guidance_count:
        score += 2
    if selected_docs:
        score += 1
    if selected_tests:
        score += 1
    if selected_commands:
        score += 1
    return {
        "score": max(0, min(4, score)),
        "level": _score_level(score),
        "actionable_guidance_count": actionable_guidance_count,
        "selected_doc_count": len(selected_docs),
        "selected_test_count": len(selected_tests),
        "selected_command_count": len(selected_commands),
    }


def _validation_profile(
    *,
    selected_tests: Sequence[Mapping[str, Any]],
    selected_commands: Sequence[str],
    selection_state: str,
    anchor_quality: str,
) -> dict[str, Any]:
    score = 0
    if selected_tests:
        score += 2
    if selected_commands:
        score += 1
    if len(selected_tests) >= 2 or len(selected_commands) >= 2:
        score += 1
    if selection_state in {"explicit", "inferred_confident"} and anchor_quality in {"explicit", "non_shared"}:
        score += 1
    return {
        "score": max(0, min(4, score)),
        "level": _score_level(score),
    }


def _reasoning_bias(
    *,
    packet_state: str,
    selection_state: str,
    evidence_profile: Mapping[str, Any],
    validation_profile: Mapping[str, Any],
) -> str:
    if str(packet_state or "").strip().startswith("gated_"):
        return "guarded_narrowing"
    if _int_value(validation_profile.get("score")) >= 3:
        return "deep_validation"
    if selection_state == "explicit" or _int_value(evidence_profile.get("score")) >= 3:
        return "accuracy_first"
    return "balanced"


def _parallelism_hint(
    *,
    packet_state: str,
    anchor_quality: str,
    selection_state: str,
    ambiguity_class: str,
    actionability_profile: Mapping[str, Any],
) -> str:
    if str(packet_state or "").strip().startswith("gated_"):
        return "serial_guarded"
    if ambiguity_class in {"historical_fanout", "close_competition"}:
        return "serial_preferred"
    if (
        anchor_quality in {"explicit", "non_shared"}
        and selection_state in {"explicit", "inferred_confident"}
        and _int_value(actionability_profile.get("score")) >= 3
    ):
        return "bounded_parallel_candidate"
    return "serial_preferred"


def _precision_score(
    *,
    anchor_quality: str,
    guidance_coverage: str,
    selected_components: Sequence[Mapping[str, Any]],
    selected_workstreams: Sequence[Mapping[str, Any]],
    selected_docs: Sequence[str],
    selected_tests: Sequence[Mapping[str, Any]],
    selected_commands: Sequence[str],
    packet_state: str,
    selection_state: str,
    workstream_candidate_count: int,
    strong_workstream_candidate_count: int,
    ambiguity_class: str,
) -> int:
    score = 0
    if anchor_quality == "explicit":
        score += 35
    elif anchor_quality == "non_shared":
        score += 25
    elif anchor_quality == "shared_only":
        score += 8
    if guidance_coverage == "direct":
        score += 20
    elif guidance_coverage == "anchored":
        score += 16
    elif guidance_coverage == "supporting":
        score += 8
    if selected_components:
        score += 12
    if selected_workstreams:
        strong_signals = (
            max(
                _int_value(dict(row.get("evidence", {})).get("strong_signal_count"))
                for row in selected_workstreams
                if isinstance(row, Mapping)
            )
            if any(isinstance(row, Mapping) for row in selected_workstreams)
            else 0
        )
        score += 16 if strong_signals > 0 else 8
    if selected_docs:
        score += 6
    if selected_tests:
        score += 5
    if selected_commands:
        score += 3
    if str(selection_state or "").strip() == "inferred_confident":
        score += 8
    elif str(selection_state or "").strip() == "ambiguous":
        score -= 18
        if int(workstream_candidate_count) > 3:
            score -= 6
        if int(strong_workstream_candidate_count) > 1:
            score -= 5
        if str(ambiguity_class or "").strip() == "historical_fanout":
            score -= 6
    if str(packet_state or "").strip().startswith("gated_"):
        score -= 12
    return max(0, min(100, score))


def _evidence_consensus(
    *,
    anchor_quality: str,
    guidance_coverage: str,
    selected_components: Sequence[Mapping[str, Any]],
    selected_workstreams: Sequence[Mapping[str, Any]],
    selected_docs: Sequence[str],
    selected_tests: Sequence[Mapping[str, Any]],
    selected_commands: Sequence[str],
    selection_state: str,
    workstream_candidate_count: int,
    strong_workstream_candidate_count: int,
) -> str:
    axes = 0
    if anchor_quality in {"explicit", "non_shared"}:
        axes += 1
    if selected_components:
        axes += 1
    if selected_workstreams:
        axes += 1
    if guidance_coverage != "none":
        axes += 1
    if selected_docs:
        axes += 1
    if selected_tests or selected_commands:
        axes += 1
    if anchor_quality in {"explicit", "non_shared"} and guidance_coverage in {"direct", "anchored"} and axes >= 4:
        if str(selection_state or "").strip() == "ambiguous" and (
            int(workstream_candidate_count) > 3 or int(strong_workstream_candidate_count) > 1
        ):
            return "mixed"
        return "strong"
    if axes >= 3:
        return "mixed"
    return "weak"


def summarize_routing_signals(
    *,
    packet_state: str,
    selection_state: str,
    shared_only_input: bool,
    anchor_paths: Sequence[str],
    workstream_selection: Mapping[str, Any],
    selected_components: Sequence[Mapping[str, Any]],
    selected_workstreams: Sequence[Mapping[str, Any]],
    selected_docs: Sequence[str],
    selected_tests: Sequence[Mapping[str, Any]],
    selected_commands: Sequence[str],
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize routing evidence from the currently retained payload surface."""

    anchor_quality = _anchor_quality(
        selection_state=selection_state,
        shared_only_input=shared_only_input,
        anchor_paths=anchor_paths,
    )
    guidance_coverage = _guidance_coverage(selected_guidance_chunks)
    workstream_candidate_count, strong_workstream_candidate_count, ambiguity_class = _workstream_selection_metrics(
        workstream_selection
    )
    evidence_consensus = _evidence_consensus(
        anchor_quality=anchor_quality,
        guidance_coverage=guidance_coverage,
        selected_components=selected_components,
        selected_workstreams=selected_workstreams,
        selected_docs=selected_docs,
        selected_tests=selected_tests,
        selected_commands=selected_commands,
        selection_state=selection_state,
        workstream_candidate_count=workstream_candidate_count,
        strong_workstream_candidate_count=strong_workstream_candidate_count,
    )
    precision_score = _precision_score(
        anchor_quality=anchor_quality,
        guidance_coverage=guidance_coverage,
        selected_components=selected_components,
        selected_workstreams=selected_workstreams,
        selected_docs=selected_docs,
        selected_tests=selected_tests,
        selected_commands=selected_commands,
        packet_state=packet_state,
        selection_state=selection_state,
        workstream_candidate_count=workstream_candidate_count,
        strong_workstream_candidate_count=strong_workstream_candidate_count,
        ambiguity_class=ambiguity_class,
    )
    evidence_profile = _evidence_profile(
        anchor_quality=anchor_quality,
        guidance_coverage=guidance_coverage,
        selected_components=selected_components,
        selected_workstreams=selected_workstreams,
        selected_guidance_chunks=selected_guidance_chunks,
        precision_score=precision_score,
    )
    actionability_profile = _actionability_profile(
        selected_guidance_chunks=selected_guidance_chunks,
        selected_docs=selected_docs,
        selected_tests=selected_tests,
        selected_commands=selected_commands,
    )
    validation_profile = _validation_profile(
        selected_tests=selected_tests,
        selected_commands=selected_commands,
        selection_state=selection_state,
        anchor_quality=anchor_quality,
    )
    grounded_ambiguous_write = grounded_ambiguous_write_candidate(
        anchor_quality=anchor_quality,
        guidance_coverage=guidance_coverage,
        ambiguity_class=ambiguity_class,
        evidence_consensus=evidence_consensus,
        precision_score=precision_score,
        actionability_score=_int_value(actionability_profile.get("score")),
        validation_score=_int_value(validation_profile.get("score")),
        direct_guidance_chunk_count=sum(
            1
            for row in selected_guidance_chunks
            if isinstance(row, Mapping) and str(row.get("match_tier", "")).strip() == "direct_path"
        ),
        actionable_guidance_chunk_count=sum(
            1
            for row in selected_guidance_chunks
            if isinstance(row, Mapping)
            and isinstance(row.get("actionability"), Mapping)
            and bool(dict(row.get("actionability", {})).get("actionable"))
        ),
        selected_test_count=len([row for row in selected_tests if isinstance(row, Mapping)]),
        selected_command_count=len([str(token).strip() for token in selected_commands if str(token).strip()]),
    )
    routing_confidence = "low"
    if selection_state == "explicit":
        routing_confidence = "high"
    elif selection_state == "inferred_confident" and anchor_quality == "non_shared" and evidence_consensus == "strong":
        routing_confidence = "high"
    elif grounded_ambiguous_write:
        routing_confidence = "medium"
    elif selection_state == "ambiguous" and anchor_quality == "non_shared" and guidance_coverage in {"direct", "anchored"}:
        routing_confidence = "medium" if workstream_candidate_count <= 3 else "low"
    elif (
        anchor_quality == "non_shared"
        and guidance_coverage in {"direct", "anchored"}
        and (
            _int_value(actionability_profile.get("score")) >= 3
            or (
                precision_score >= 40
                and (
                    _int_value(actionability_profile.get("score")) >= 2
                    or _int_value(validation_profile.get("score")) >= 2
                )
            )
        )
    ):
        routing_confidence = "medium"
    elif anchor_quality == "non_shared" and evidence_consensus == "mixed":
        routing_confidence = "medium"
    domains = [
        "paths",
        *(["components"] if selected_components else []),
        *(["workstreams"] if selected_workstreams else []),
        *(["guidance"] if selected_guidance_chunks else []),
        *(["docs"] if selected_docs else []),
        *(["tests"] if selected_tests else []),
        *(["commands"] if selected_commands else []),
    ]
    direct_guidance_count = sum(
        1 for row in selected_guidance_chunks if isinstance(row, Mapping) and str(row.get("match_tier", "")).strip() == "direct_path"
    )
    actionable_guidance_count = sum(
        1
        for row in selected_guidance_chunks
        if isinstance(row, Mapping)
        and isinstance(row.get("actionability"), Mapping)
        and bool(dict(row.get("actionability", {})).get("actionable"))
    )
    return {
        "anchor_quality": anchor_quality,
        "guidance_coverage": guidance_coverage,
        "evidence_consensus": evidence_consensus,
        "precision_score": precision_score,
        "routing_confidence": routing_confidence,
        "evidence_profile": evidence_profile,
        "actionability_profile": actionability_profile,
        "validation_profile": validation_profile,
        "reasoning_bias": _reasoning_bias(
            packet_state=packet_state,
            selection_state=selection_state,
            evidence_profile=evidence_profile,
            validation_profile=validation_profile,
        ),
        "parallelism_hint": _parallelism_hint(
            packet_state=packet_state,
            anchor_quality=anchor_quality,
            selection_state=selection_state,
            ambiguity_class=ambiguity_class,
            actionability_profile=actionability_profile,
        ),
        "ambiguity_class": ambiguity_class,
        "workstream_candidate_count": workstream_candidate_count,
        "strong_workstream_candidate_count": strong_workstream_candidate_count,
        "selected_domains": domains,
        "evidence_summary": {
            "direct_guidance_count": direct_guidance_count,
            "selected_component_count": len(selected_components),
            "selected_workstream_count": len(selected_workstreams),
            "strong_workstream_candidate_count": strong_workstream_candidate_count,
        },
        "actionability": {
            "actionable_guidance_count": actionable_guidance_count,
            "selected_doc_count": len(selected_docs),
            "selected_test_count": len(selected_tests),
            "selected_command_count": len(selected_commands),
        },
    }


def build_retrieval_plan(
    *,
    packet_kind: str,
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
    recommended_tests: Sequence[Mapping[str, Any]],
    recommended_commands: Sequence[str],
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    miss_recovery: Mapping[str, Any],
    guidance_catalog_summary: Mapping[str, Any],
    full_scan_reason: str,
) -> dict[str, Any]:
    """Build a compact routing/retrieval plan before packet emission."""

    anchor_paths = [str(path).strip() for path in changed_paths if str(path).strip()]
    shared_anchor_paths = list(anchor_paths) if shared_only_input else []
    non_shared_anchor_paths = [] if shared_only_input else list(anchor_paths)
    selected = workstream_selection.get("selected_workstream")
    if isinstance(selected, Mapping) and str(selected.get("entity_id", "")).strip():
        selected_workstreams = _compact_workstream_rows([selected], limit=1)
    else:
        selected_workstreams = _compact_workstream_rows(candidate_workstreams, limit=3)
    selected_diagrams = _compact_entity_rows(diagrams, key="diagram_id", title_field="title", limit=4)
    selected_components = _compact_component_rows(components, limit=4)
    selected_docs = [str(token).strip() for token in docs[:6] if str(token).strip()]
    selected_commands = [str(token).strip() for token in recommended_commands[:4] if str(token).strip()]
    selected_tests = _compact_test_rows(recommended_tests, limit=4)
    compact_miss_recovery = _compact_miss_recovery(miss_recovery)
    guidance_limit = 4 if str(packet_kind or "").strip() == "impact" else 3
    if str(packet_kind or "").strip() == "bootstrap_session":
        guidance_limit = 2
    selected_guidance = _compact_guidance_rows(selected_guidance_chunks, limit=guidance_limit)
    signal_summary = summarize_routing_signals(
        packet_state=packet_state,
        selection_state=selection_state,
        shared_only_input=shared_only_input,
        anchor_paths=anchor_paths,
        workstream_selection=workstream_selection,
        selected_components=selected_components,
        selected_workstreams=selected_workstreams,
        selected_docs=selected_docs,
        selected_tests=selected_tests,
        selected_commands=selected_commands,
        selected_guidance_chunks=selected_guidance,
    )
    selected_domains = [str(token).strip() for token in signal_summary.get("selected_domains", []) if str(token).strip()]
    if compact_miss_recovery.get("active"):
        selected_domains = _dedupe_strings([*selected_domains, "miss_recovery"])
    return {
        "contract": "retrieval_plan.v1",
        "version": "v3",
        "packet_kind": str(packet_kind or "").strip(),
        "packet_state": str(packet_state or "").strip(),
        "routing_confidence": str(signal_summary.get("routing_confidence", "")).strip(),
        "selection_state": str(selection_state or "").strip(),
        "anchor_quality": str(signal_summary.get("anchor_quality", "")).strip(),
        "guidance_coverage": str(signal_summary.get("guidance_coverage", "")).strip(),
        "evidence_consensus": str(signal_summary.get("evidence_consensus", "")).strip(),
        "precision_score": _int_value(signal_summary.get("precision_score")),
        "ambiguity_class": str(signal_summary.get("ambiguity_class", "")).strip(),
        "workstream_candidate_count": _int_value(signal_summary.get("workstream_candidate_count")),
        "strong_workstream_candidate_count": _int_value(signal_summary.get("strong_workstream_candidate_count")),
        "has_non_shared_anchor": bool(non_shared_anchor_paths) or selection_state == "explicit",
        "anchor_paths": anchor_paths,
        "shared_anchor_paths": shared_anchor_paths,
        "explicit_paths": [str(token).strip() for token in explicit_paths if str(token).strip()],
        "selected_domains": selected_domains,
        "selected_components": selected_components,
        "selected_workstreams": selected_workstreams,
        "selected_diagrams": selected_diagrams,
        "selected_guidance_chunks": selected_guidance,
        "selected_docs": selected_docs,
        "selected_tests": selected_tests,
        "selected_commands": selected_commands,
        "selected_counts": {
            "components": len(selected_components),
            "workstreams": len(selected_workstreams),
            "diagrams": len(selected_diagrams),
            "docs": len(selected_docs),
            "tests": len(selected_tests),
            "commands": len(selected_commands),
            "guidance": len(selected_guidance),
        },
        "miss_recovery": compact_miss_recovery,
        "evidence_summary": dict(signal_summary.get("evidence_summary", {}))
        if isinstance(signal_summary.get("evidence_summary"), Mapping)
        else {},
        "actionability": dict(signal_summary.get("actionability", {}))
        if isinstance(signal_summary.get("actionability"), Mapping)
        else {},
        "evidence_profile": dict(signal_summary.get("evidence_profile", {}))
        if isinstance(signal_summary.get("evidence_profile"), Mapping)
        else {},
        "actionability_profile": dict(signal_summary.get("actionability_profile", {}))
        if isinstance(signal_summary.get("actionability_profile"), Mapping)
        else {},
        "validation_profile": dict(signal_summary.get("validation_profile", {}))
        if isinstance(signal_summary.get("validation_profile"), Mapping)
        else {},
        "reasoning_bias": str(signal_summary.get("reasoning_bias", "")).strip(),
        "parallelism_hint": str(signal_summary.get("parallelism_hint", "")).strip(),
        "full_scan_reason": str(full_scan_reason or "").strip(),
        "guidance_catalog": {
            "version": str(guidance_catalog_summary.get("version", "")).strip(),
            "chunk_count": _int_value(guidance_catalog_summary.get("chunk_count")),
            "catalog_fingerprint": str(guidance_catalog_summary.get("catalog_fingerprint", "")).strip(),
        },
    }


def build_narrowing_guidance(
    *,
    packet_kind: str = "",
    packet_state: str,
    full_scan_recommended: bool,
    full_scan_reason: str,
    workstream_selection: Mapping[str, Any],
    retrieval_plan: Mapping[str, Any],
    final_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return actionable narrowing guidance when the slice is broad or ambiguous."""

    required = bool(full_scan_recommended) or str(packet_state or "").strip() in {
        "gated_broad_scope",
        "gated_ambiguous",
    }
    selected_components = retrieval_plan.get("selected_components", [])
    if not isinstance(selected_components, list):
        selected_components = []
    selected_workstreams = retrieval_plan.get("selected_workstreams", [])
    if not isinstance(selected_workstreams, list):
        selected_workstreams = []
    selected_guidance = retrieval_plan.get("selected_guidance_chunks", [])
    if not isinstance(selected_guidance, list):
        selected_guidance = []
    miss_recovery = retrieval_plan.get("miss_recovery", {})
    if not isinstance(miss_recovery, Mapping):
        miss_recovery = {}
    next_best_anchors: list[dict[str, str]] = []
    for row in selected_workstreams[:2]:
        if not isinstance(row, Mapping):
            continue
        entity_id = str(row.get("entity_id", "")).strip()
        if entity_id:
            next_best_anchors.append(
                {
                    "kind": "workstream",
                    "value": entity_id,
                    "reason": "Explicit workstream selection will unlock richer context without broad guessing.",
                }
            )
    for row in selected_components[:2]:
        if not isinstance(row, Mapping):
            continue
        component_id = str(row.get("entity_id", "")).strip()
        if component_id:
            next_best_anchors.append(
                {
                    "kind": "component",
                    "value": component_id,
                    "reason": "A concrete component anchor is stronger than shared guidance files alone.",
                }
            )
    for row in selected_guidance[:1]:
        if not isinstance(row, Mapping):
            continue
        actionability = row.get("actionability", {})
        canonical_source = str(row.get("canonical_source", "")).strip() or (
            str(actionability.get("read_path", "")).strip() if isinstance(actionability, Mapping) else ""
        )
        if canonical_source:
            next_best_anchors.append(
                {
                    "kind": "doc",
                    "value": canonical_source,
                    "reason": "Reading the highest-signal guidance source directly will tighten the slice faster than generic context expansion.",
                }
            )
    recovered_docs = miss_recovery.get("recovered_docs", [])
    if isinstance(recovered_docs, list):
        for doc_path in recovered_docs[:1]:
            token = str(doc_path).strip()
            if not token:
                continue
            next_best_anchors.append(
                {
                    "kind": "doc",
                    "value": token,
                    "reason": "Miss recovery found a compact supporting source worth reading before widening the slice further.",
                }
            )
    reason = str(full_scan_reason or "").strip()
    if not reason:
        reason = str(workstream_selection.get("reason", "")).strip()
    if not reason:
        reason = "The current slice is still too broad to trust expanded context."
    payload = dict(final_payload) if isinstance(final_payload, Mapping) else {}
    validation_bundle = _routing_validation_bundle(payload)
    governance_obligations = _routing_governance_obligations(payload)
    selected_counts = (
        dict(retrieval_plan.get("selected_counts", {}))
        if isinstance(retrieval_plan.get("selected_counts"), Mapping)
        else {}
    )
    retained_paths = _dedupe_strings(
        [
            *_normalized_string_list(payload.get("changed_paths")),
            *_normalized_string_list(payload.get("explicit_paths")),
            *_normalized_string_list(retrieval_plan.get("anchor_paths")),
        ]
    )
    has_direct_guidance = bool(
        str(retrieval_plan.get("guidance_coverage", "")).strip() in {"direct", "anchored"}
        or _int_value(selected_counts.get("guidance")) > 0
    )
    has_validation_contract = bool(
        _normalized_string_list(payload.get("recommended_commands"))
        or (
            isinstance(payload.get("recommended_tests"), list)
            and any(isinstance(row, Mapping) for row in payload.get("recommended_tests", []))
        )
        or _count_or_list_len(
            validation_bundle,
            list_key="strict_gate_commands",
            count_key="strict_gate_command_count",
        )
        > 0
    )
    has_governance_contract = bool(
        _count_or_list_len(
            governance_obligations,
            list_key="closeout_docs",
            count_key="closeout_doc_count",
        )
        > 0
        or bool(validation_bundle.get("plan_binding_required"))
        or bool(validation_bundle.get("governed_surface_sync_required"))
    )
    ambiguity_class = str(retrieval_plan.get("ambiguity_class", "")).strip()
    exact_path_execution_ready = bool(
        required
        and not full_scan_recommended
        and str(packet_kind or "").strip() in {"impact", "governance_slice"}
        and str(packet_state or "").strip() == "gated_ambiguous"
        and not (
            isinstance(payload.get("diagram_watch_gaps"), list)
            and payload.get("diagram_watch_gaps")
        )
        and bool(retrieval_plan.get("has_non_shared_anchor"))
        and str(retrieval_plan.get("anchor_quality", "")).strip() in {"explicit", "non_shared"}
        and ambiguity_class in {"no_candidates", "historical_fanout", "close_competition"}
        and bool(retained_paths)
        and len(retained_paths) <= 4
        and has_direct_guidance
        and (has_validation_contract or has_governance_contract)
        and (
            ambiguity_class == "no_candidates"
            or str(retrieval_plan.get("evidence_consensus", "")).strip() in {"strong", "mixed"}
            or has_governance_contract
        )
        and (
            ambiguity_class == "no_candidates"
            or _int_value(retrieval_plan.get("precision_score")) >= 40
            or has_governance_contract
        )
    )
    if exact_path_execution_ready:
        required = False
        reason = "Exact-path retained evidence already bounds execution and closeout without broader narrowing."
    fallback_scan = dict(payload.get("fallback_scan", {})) if isinstance(payload.get("fallback_scan"), Mapping) else {}
    next_fallback_command = ""
    next_fallback_followup = ""
    suppress_degraded_receipt = reason in {"working_tree_scope_degraded", "broad_shared_paths"} and bool(retained_paths)
    if suppress_degraded_receipt:
        reason = "Current shared/control-plane context still needs one concrete code, manifest, or contract anchor."
    if required and next_best_anchors:
        next_fallback_command, next_fallback_followup = _fallback_anchor_commands(next_best_anchors[0])
    if required and not next_fallback_command and not suppress_degraded_receipt:
        next_fallback_command, next_fallback_followup = _fallback_scan_commands(
            fallback_scan=fallback_scan,
            retained_paths=retained_paths,
        )
    return {
        "required": required,
        "reason": reason,
        "suggested_inputs": [
            "Provide at least one implementation, test, contract, or manifest path.",
            "Pin an explicit workstream with `--workstream B-###` when the slice is known.",
            "Read the highest-signal guidance source directly when the packet exposes one.",
            "If narrowing still fails, run the printed fallback command and then read the named source directly.",
        ]
        if required
        else [],
        "next_best_anchors": next_best_anchors[:3],
        "next_fallback_command": next_fallback_command,
        "next_fallback_followup": next_fallback_followup,
    }


def build_routing_handoff(
    *,
    packet_kind: str,
    packet_state: str,
    retrieval_plan: Mapping[str, Any],
    packet_quality: Mapping[str, Any],
    final_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a compact routing handoff derived from the final packet payload."""

    plan = final_payload.get("retrieval_plan", retrieval_plan)
    if not isinstance(plan, Mapping):
        plan = retrieval_plan
    selected_guidance = plan.get("selected_guidance_chunks", [])
    if not isinstance(selected_guidance, list):
        selected_guidance = []
    selected_workstreams = plan.get("selected_workstreams", [])
    if not isinstance(selected_workstreams, list):
        selected_workstreams = []
    commands = final_payload.get("recommended_commands", [])
    if not isinstance(commands, list):
        commands = []
    tests = final_payload.get("recommended_tests", [])
    if not isinstance(tests, list):
        tests = []
    docs = final_payload.get("docs", [])
    if not isinstance(docs, list) or not docs:
        docs = final_payload.get("relevant_docs", [])
    if not isinstance(docs, list):
        docs = []
    anchor_paths = plan.get("anchor_paths", [])
    if not isinstance(anchor_paths, list) or not anchor_paths:
        anchor_paths = final_payload.get("changed_paths", [])
    if not isinstance(anchor_paths, list):
        anchor_paths = []
    primary_workstream = selected_workstreams[0] if selected_workstreams else {}
    if not isinstance(primary_workstream, Mapping):
        primary_workstream = {}
    narrowing_guidance = final_payload.get("narrowing_guidance", {})
    if not isinstance(narrowing_guidance, Mapping):
        narrowing_guidance = {}
    truncation = final_payload.get("truncation", {})
    if not isinstance(truncation, Mapping):
        truncation = {}
    packet_budget_truncation = truncation.get("packet_budget", {})
    if not isinstance(packet_budget_truncation, Mapping):
        packet_budget_truncation = {}
    top_guidance = _compact_handoff_guidance_rows(selected_guidance, limit=1)
    packet_quality_payload = dict(packet_quality) if isinstance(packet_quality, Mapping) else {}
    validation_bundle = _routing_validation_bundle(final_payload)
    execution_profile_payload = (
        dict(final_payload.get("execution_profile", {}))
        if isinstance(final_payload.get("execution_profile"), Mapping)
        else {}
    )
    gated_bootstrap_handoff = str(packet_kind or "").strip() == "bootstrap_session" and str(packet_state or "").strip().startswith("gated_")
    compact_bootstrap_handoff = str(packet_kind or "").strip() == "bootstrap_session" and (
        gated_bootstrap_handoff
        or bool(packet_budget_truncation.get("truncated"))
        or bool(packet_budget_truncation.get("applied"))
        or not bool(packet_quality_payload.get("within_budget"))
    )
    evidence_quality = (
        dict(packet_quality_payload.get("evidence_quality", {}))
        if isinstance(packet_quality_payload.get("evidence_quality"), Mapping)
        else {}
    )
    actionability = (
        dict(packet_quality_payload.get("actionability", {}))
        if isinstance(packet_quality_payload.get("actionability"), Mapping)
        else {}
    )
    validation_pressure = (
        dict(packet_quality_payload.get("validation_pressure", {}))
        if isinstance(packet_quality_payload.get("validation_pressure"), Mapping)
        else {}
    )
    compaction_pressure = (
        dict(packet_quality_payload.get("compaction_pressure", {}))
        if isinstance(packet_quality_payload.get("compaction_pressure"), Mapping)
        else {}
    )
    utility_profile = (
        dict(packet_quality_payload.get("utility_profile", {}))
        if isinstance(packet_quality_payload.get("utility_profile"), Mapping)
        else {}
    )
    context_density = (
        dict(packet_quality_payload.get("context_density", {}))
        if isinstance(packet_quality_payload.get("context_density"), Mapping)
        else {}
    )
    evidence_diversity = (
        dict(packet_quality_payload.get("evidence_diversity", {}))
        if isinstance(packet_quality_payload.get("evidence_diversity"), Mapping)
        else {}
    )
    reasoning_readiness = (
        dict(packet_quality_payload.get("reasoning_readiness", {}))
        if isinstance(packet_quality_payload.get("reasoning_readiness"), Mapping)
        else {}
    )
    intent_profile = (
        dict(packet_quality_payload.get("intent_profile", {}))
        if isinstance(packet_quality_payload.get("intent_profile"), Mapping)
        else {}
    )
    token_efficiency = (
        dict(packet_quality_payload.get("token_efficiency", {}))
        if isinstance(packet_quality_payload.get("token_efficiency"), Mapping)
        else {}
    )
    routing_confidence = str(packet_quality_payload.get("routing_confidence", "")).strip()
    reasoning_bias = str(packet_quality_payload.get("reasoning_bias", "")).strip()
    parallelism_hint = str(packet_quality_payload.get("parallelism_hint", "")).strip()
    actionability_level = str(packet_quality_payload.get("actionability_level", "")).strip()
    validation_level = str(validation_pressure.get("level", "")).strip()
    intent_family = str(intent_profile.get("family", "")).strip()
    route_ready = grounded_write_execution_ready(
        packet_kind=packet_kind,
        packet_state=packet_state,
        full_scan_recommended=bool(final_payload.get("full_scan_recommended")),
        narrowing_required=bool(narrowing_guidance.get("required")),
        within_budget=bool(packet_quality_payload.get("within_budget")),
        routing_confidence=routing_confidence,
        has_non_shared_anchor=bool(plan.get("has_non_shared_anchor")),
        ambiguity_class=str(packet_quality_payload.get("ambiguity_class", "")).strip(),
        guidance_coverage=str(packet_quality_payload.get("guidance_coverage", "")).strip(),
        intent_family=intent_family,
        actionability_score=max(
            _int_value(actionability.get("score")),
            _score_from_level(actionability_level),
        ),
        validation_score=max(
            _int_value(validation_pressure.get("score")),
            _score_from_level(validation_level),
        ),
        context_density_score=_int_value(context_density.get("score")),
        evidence_quality_score=max(
            _int_value(evidence_quality.get("score")),
            _score_from_level(evidence_quality.get("level")),
        ),
        evidence_consensus=str(packet_quality_payload.get("evidence_consensus", "")).strip(),
        precision_score=_int_value(plan.get("precision_score")),
        direct_guidance_chunk_count=_int_value(packet_quality_payload.get("direct_guidance_chunk_count")),
        actionable_guidance_chunk_count=_int_value(packet_quality_payload.get("actionable_guidance_chunk_count")),
        selected_test_count=len([row for row in tests if isinstance(row, Mapping)]),
        selected_command_count=len([str(token).strip() for token in commands if str(token).strip()]),
        selected_doc_count=len([str(token).strip() for token in docs if str(token).strip()]),
        strict_gate_command_count=_count_or_list_len(
            validation_bundle,
            list_key="strict_gate_commands",
            count_key="strict_gate_command_count",
        ),
        plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
        governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
    )
    grounding_score = 4 if bool(plan.get("has_non_shared_anchor")) else 1 if anchor_paths else 0
    parallelism_confidence = max(
        _score_from_level(parallelism_hint),
        4 if route_ready and parallelism_hint == "bounded_parallel_candidate" else 0,
    )
    validation_score = max(
        _int_value(validation_pressure.get("score")),
        _score_from_level(validation_level),
    )
    actionability_score = max(
        _int_value(actionability.get("score")),
        _score_from_level(actionability_level),
    )
    evidence_score = max(
        _int_value(evidence_quality.get("score")),
        _score_from_level(evidence_quality.get("level")),
    )
    risk_score = 0
    if str(packet_state or "").strip().startswith("gated_"):
        risk_score += 2
    if str(packet_quality_payload.get("accuracy_posture", "")).strip() in {"anchored_but_ambiguous", "fail_closed"}:
        risk_score += 1
    if str(packet_quality_payload.get("evidence_consensus", "")).strip() == "weak":
        risk_score += 1
    risk_score = max(0, min(4, risk_score))
    utility_profile_handoff = {
        "score": _int_value(utility_profile.get("score")),
        "level": str(utility_profile.get("level", "")).strip()
        or _score_level(max(0, min(4, int(round(_int_value(utility_profile.get("score")) / 25))))),
        "token_efficiency": {
            "score": _int_value(token_efficiency.get("score")),
            "level": str(token_efficiency.get("level", "")).strip()
            or _score_level(_int_value(token_efficiency.get("score"))),
        },
    }
    if not compact_bootstrap_handoff:
        utility_profile_handoff["retained_signal_count"] = _int_value(utility_profile.get("retained_signal_count"))
        utility_profile_handoff["density_per_1k_tokens"] = float(utility_profile.get("density_per_1k_tokens", 0.0) or 0.0)
    resolved_host_runtime = host_runtime_contract.resolve_host_runtime(
        final_payload.get("host_runtime"),
    )
    native_spawn_supported = host_runtime_contract.native_spawn_supported(
        resolved_host_runtime,
        default_when_unknown=False,
    )
    packet_quality_handoff = {
        "context_richness": str(packet_quality_payload.get("context_richness", "")).strip(),
        "evidence_quality": {
            "score": _int_value(evidence_quality.get("score")),
            "level": str(evidence_quality.get("level", "")).strip() or _score_level(_int_value(evidence_quality.get("score"))),
        },
        "actionability": {
            "score": _int_value(actionability.get("score")),
            "level": actionability_level or _score_level(_int_value(actionability.get("score"))),
        },
        "validation_pressure": {
            "score": _int_value(validation_pressure.get("score")),
            "level": validation_level or _score_level(_int_value(validation_pressure.get("score"))),
        },
        "compaction_pressure": {
            "score": _int_value(compaction_pressure.get("score")),
            "level": str(compaction_pressure.get("level", "")).strip()
            or _score_level(_int_value(compaction_pressure.get("score"))),
        },
        "utility_profile": utility_profile_handoff,
        "context_density": {
            "score": _int_value(context_density.get("score")),
            "level": str(context_density.get("level", "")).strip()
            or _score_level(_int_value(context_density.get("score"))),
            "density_per_1k_tokens": float(context_density.get("density_per_1k_tokens", 0.0) or 0.0),
        }
        if context_density
        else {},
        "evidence_diversity": {
            "score": _int_value(evidence_diversity.get("score")),
            "level": str(evidence_diversity.get("level", "")).strip()
            or _score_level(_int_value(evidence_diversity.get("score"))),
            "domain_count": _int_value(evidence_diversity.get("domain_count")),
        }
        if evidence_diversity
        else {},
        "reasoning_readiness": {
            "score": _int_value(reasoning_readiness.get("score")),
            "level": str(reasoning_readiness.get("level", "")).strip()
            or _score_level(_int_value(reasoning_readiness.get("score"))),
            "mode": str(reasoning_readiness.get("mode", "")).strip(),
            "deep_reasoning_ready": bool(reasoning_readiness.get("deep_reasoning_ready")),
        }
        if reasoning_readiness
        else {},
        "intent_profile": {
            "family": str(intent_profile.get("family", "")).strip(),
            "mode": str(intent_profile.get("mode", "")).strip(),
            "critical_path": str(intent_profile.get("critical_path", "")).strip(),
            "confidence": str(intent_profile.get("confidence", "")).strip(),
            "explicit": bool(intent_profile.get("explicit")),
            "source": str(intent_profile.get("source", "")).strip(),
        },
        "reasoning_bias": reasoning_bias,
        "parallelism_hint": parallelism_hint,
        "native_spawn_ready": native_spawn_execution_ready(
            route_ready=route_ready,
            full_scan_recommended=bool(final_payload.get("full_scan_recommended")),
            narrowing_required=bool(narrowing_guidance.get("required")),
            within_budget=bool(packet_quality_payload.get("within_budget")),
            delegate_preference=str(execution_profile_payload.get("delegate_preference", "")).strip(),
            model=str(execution_profile_payload.get("model", "")).strip(),
            reasoning_effort=str(execution_profile_payload.get("reasoning_effort", "")).strip(),
            agent_role=str(execution_profile_payload.get("agent_role", "")).strip(),
            selection_mode=str(execution_profile_payload.get("selection_mode", "")).strip(),
            selected_test_count=len([row for row in tests if isinstance(row, Mapping)]),
            selected_command_count=len([str(token).strip() for token in commands if str(token).strip()]),
            selected_doc_count=len([str(token).strip() for token in docs if str(token).strip()]),
            strict_gate_command_count=_count_or_list_len(
                validation_bundle,
                list_key="strict_gate_commands",
                count_key="strict_gate_command_count",
            ),
            plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
            governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
            host_runtime=resolved_host_runtime,
        ),
        "native_spawn_supported": native_spawn_supported,
        "within_budget": bool(packet_quality_payload.get("within_budget")),
    }
    if compact_bootstrap_handoff:
        packet_quality_handoff.pop("compaction_pressure", None)
        packet_quality_handoff.pop("context_richness", None)
    utility_score = _int_value(utility_profile.get("score"))
    utility_signal_score = max(0, min(4, int(round(utility_score / 25))))
    utility_handoff = {
        "score": utility_signal_score,
        "level": str(utility_profile.get("level", "")).strip() or _score_level(utility_signal_score),
        "token_efficiency": {
            "score": _int_value(token_efficiency.get("score")),
            "level": str(token_efficiency.get("level", "")).strip()
            or _score_level(_int_value(token_efficiency.get("score"))),
        },
    }
    if not compact_bootstrap_handoff:
        utility_handoff["density_per_1k_tokens"] = float(utility_profile.get("density_per_1k_tokens", 0.0) or 0.0)
    miss_recovery = (
        dict(plan.get("miss_recovery", {}))
        if isinstance(plan.get("miss_recovery"), Mapping)
        else {}
    )
    adaptive_packet_profile = (
        dict(final_payload.get("adaptive_packet_profile", {}))
        if isinstance(final_payload.get("adaptive_packet_profile"), Mapping)
        else {}
    )
    optimization_handoff = {
        "within_budget": bool(packet_quality_payload.get("within_budget")),
        "utility_score": utility_signal_score,
        "utility_level": str(utility_profile.get("level", "")).strip() or _score_level(utility_signal_score),
        "token_efficiency": {
            "score": _int_value(token_efficiency.get("score")),
            "level": str(token_efficiency.get("level", "")).strip()
            or _score_level(_int_value(token_efficiency.get("score"))),
        },
        "compaction_pressure": {
            "score": _int_value(compaction_pressure.get("score")),
            "level": str(compaction_pressure.get("level", "")).strip()
            or _score_level(_int_value(compaction_pressure.get("score"))),
        },
        "context_density": {
            "score": _int_value(context_density.get("score")),
            "level": str(context_density.get("level", "")).strip(),
        }
        if context_density
        else {},
        "reasoning_readiness": {
            "score": _int_value(reasoning_readiness.get("score")),
            "level": str(reasoning_readiness.get("level", "")).strip(),
            "mode": str(reasoning_readiness.get("mode", "")).strip(),
            "deep_reasoning_ready": bool(reasoning_readiness.get("deep_reasoning_ready")),
        }
        if reasoning_readiness
        else {},
        "evidence_diversity": {
            "score": _int_value(evidence_diversity.get("score")),
            "level": str(evidence_diversity.get("level", "")).strip(),
            "domain_count": _int_value(evidence_diversity.get("domain_count")),
        }
        if evidence_diversity
        else {},
        "miss_recovery": {
            "active": bool(miss_recovery.get("active")),
            "applied": bool(miss_recovery.get("applied")),
            "mode": str(miss_recovery.get("mode", "")).strip(),
        }
        if miss_recovery
        else {},
        "packet_strategy": str(adaptive_packet_profile.get("packet_strategy", "")).strip(),
        "budget_mode": str(adaptive_packet_profile.get("budget_mode", "")).strip(),
        "retrieval_focus": str(adaptive_packet_profile.get("retrieval_focus", "")).strip(),
        "speed_mode": str(adaptive_packet_profile.get("speed_mode", "")).strip(),
        "reliability": str(adaptive_packet_profile.get("reliability", "")).strip(),
        "selection_bias": str(adaptive_packet_profile.get("selection_bias", "")).strip(),
        "budget_scale": float(adaptive_packet_profile.get("budget_scale", 0.0) or 0.0),
    }
    if compact_bootstrap_handoff:
        optimization_handoff = {
            key: value
            for key, value in {
                "within_budget": bool(optimization_handoff.get("within_budget")),
                "utility_level": str(optimization_handoff.get("utility_level", "")).strip(),
                "context_density_level": str(dict(optimization_handoff.get("context_density", {})).get("level", "")).strip()
                if isinstance(optimization_handoff.get("context_density"), Mapping)
                else "",
                "reasoning_readiness_level": str(dict(optimization_handoff.get("reasoning_readiness", {})).get("level", "")).strip()
                if isinstance(optimization_handoff.get("reasoning_readiness"), Mapping)
                else "",
                "packet_strategy": str(optimization_handoff.get("packet_strategy", "")).strip(),
                "budget_mode": str(optimization_handoff.get("budget_mode", "")).strip(),
                "speed_mode": str(optimization_handoff.get("speed_mode", "")).strip(),
                "reliability": str(optimization_handoff.get("reliability", "")).strip(),
                "token_efficiency": {
                    "level": str(dict(optimization_handoff.get("token_efficiency", {})).get("level", "")).strip(),
                }
                if isinstance(optimization_handoff.get("token_efficiency"), Mapping)
                else {},
                "miss_recovery": {
                    "active": bool(dict(optimization_handoff.get("miss_recovery", {})).get("active")),
                    "applied": bool(dict(optimization_handoff.get("miss_recovery", {})).get("applied")),
                    "mode": str(dict(optimization_handoff.get("miss_recovery", {})).get("mode", "")).strip(),
                }
                if isinstance(optimization_handoff.get("miss_recovery"), Mapping)
                else {},
            }.items()
            if value not in ("", [], {}, None, False)
        }
    reasoning_mode = str(reasoning_readiness.get("mode", "")).strip()
    deep_reasoning_ready = bool(reasoning_readiness.get("deep_reasoning_ready"))
    ambiguity_class = str(packet_quality_payload.get("ambiguity_class", "")).strip()
    ambiguity_score = 0
    if ambiguity_class in {"historical_fanout", "close_competition"}:
        ambiguity_score = 3
    elif bool(narrowing_guidance.get("required")) or routing_confidence == "low":
        ambiguity_score = 2
    elif not route_ready:
        ambiguity_score = 1
    merge_burden_score = 0
    if parallelism_hint in {"serial_preferred", "support_followup"} or validation_score >= 3 or risk_score >= 3:
        merge_burden_score = 3
    elif parallelism_hint == "bounded_parallel_candidate":
        merge_burden_score = 1
    elif route_ready:
        merge_burden_score = 2
    expected_delegation_value_score = max(
        0,
        min(
            4,
            int(
                round(
                    (
                        actionability_score
                        + utility_signal_score
                        + grounding_score
                        + (1 if bool(packet_quality_payload.get("native_spawn_ready")) else 0)
                        + (1 if route_ready else 0)
                        - (1 if bool(narrowing_guidance.get("required")) else 0)
                    )
                    / 3.0
                )
            ),
        ),
    )
    execution_profile_score = max(
        _score_from_level(routing_confidence),
        3 if route_ready else 0,
        1 if bool(packet_quality_payload.get("within_budget")) else 0,
        1 if utility_signal_score >= 3 else 0,
    )
    resolved_host_capabilities = host_runtime_contract.resolve_host_capabilities(
        final_payload.get("host_runtime"),
    )
    resolved_host_runtime = str(resolved_host_capabilities.get("host_runtime", "")).strip()
    native_spawn_supported = bool(resolved_host_capabilities.get("supports_native_spawn"))
    execution_profile = {
        "profile": "main_thread",
        "model": "",
        "reasoning_effort": "",
        "agent_role": "main_thread",
        "selection_mode": "narrow_first",
        "delegate_preference": "hold_local",
        "source": "odylith_runtime_packet",
        "confidence": {
            "score": max(1, min(4, execution_profile_score)),
            "level": _score_level(max(1, min(4, execution_profile_score))),
        },
        "constraints": {
            "route_ready": route_ready,
            "narrowing_required": bool(narrowing_guidance.get("required")),
            "within_budget": bool(packet_quality_payload.get("within_budget")),
            "deep_reasoning_ready": deep_reasoning_ready,
            "native_spawn_supported": native_spawn_supported,
            "supports_local_structured_reasoning": bool(
                resolved_host_capabilities.get("supports_local_structured_reasoning")
            ),
            "supports_explicit_model_selection": bool(
                resolved_host_capabilities.get("supports_explicit_model_selection")
            ),
            "context_density_score": _int_value(context_density.get("score")),
            "reasoning_readiness_score": _int_value(reasoning_readiness.get("score")),
            "validation_pressure_score": validation_score,
            "utility_score": utility_signal_score,
            "risk_score": risk_score,
        },
        "host_runtime": resolved_host_runtime,
        "host_family": str(resolved_host_capabilities.get("host_family", "")).strip(),
        "model_family": str(resolved_host_capabilities.get("model_family", "")).strip(),
        "signals": {
            "grounding": {
                "score": grounding_score,
                "level": _score_level(grounding_score),
                "anchored": bool(anchor_paths),
                "has_non_shared_anchor": bool(plan.get("has_non_shared_anchor")),
            },
            "ambiguity": {
                "score": ambiguity_score,
                "level": _score_level(ambiguity_score),
                "class": ambiguity_class,
            },
            "density": {
                "score": _int_value(context_density.get("score")),
                "level": str(context_density.get("level", "")).strip()
                or _score_level(_int_value(context_density.get("score"))),
                "density_per_1k_tokens": float(context_density.get("density_per_1k_tokens", 0.0) or 0.0),
            }
            if context_density
            else {},
            "actionability": {
                "score": actionability_score,
                "level": actionability_level or _score_level(actionability_score),
            },
            "validation_pressure": {
                "score": validation_score,
                "level": validation_level or _score_level(validation_score),
            },
            "merge_burden": {
                "score": merge_burden_score,
                "level": _score_level(merge_burden_score),
                "parallelism_hint": parallelism_hint,
            },
            "expected_delegation_value": {
                "score": expected_delegation_value_score,
                "level": _score_level(expected_delegation_value_score),
                "route_ready": route_ready,
                "native_spawn_ready": bool(packet_quality_payload.get("native_spawn_ready")),
            },
        },
    }
    if not bool(narrowing_guidance.get("required")) and route_ready:
        profile = agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE
        selection_mode = "analysis_scout"
        if intent_family in {"analysis", "review", "diagnosis", "architecture"}:
            if intent_family == "architecture" and risk_score >= 3:
                profile = (
                    agent_runtime_contract.FRONTIER_HIGH_PROFILE
                    if deep_reasoning_ready or utility_signal_score >= 3
                    else agent_runtime_contract.WRITE_HIGH_PROFILE
                )
                selection_mode = "architecture_grounding"
            else:
                profile = (
                    agent_runtime_contract.ANALYSIS_HIGH_PROFILE
                    if _int_value(reasoning_readiness.get("score")) >= 2 or utility_signal_score >= 3
                    else agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE
                )
                selection_mode = (
                    "analysis_synthesis"
                    if profile == agent_runtime_contract.ANALYSIS_HIGH_PROFILE
                    else "analysis_scout"
                )
        elif validation_score >= 3 and (deep_reasoning_ready or risk_score >= 3):
            profile = agent_runtime_contract.FRONTIER_HIGH_PROFILE
            selection_mode = "deep_validation"
        elif validation_score >= 3 or intent_family == "validation":
            profile = (
                agent_runtime_contract.WRITE_HIGH_PROFILE
                if _int_value(reasoning_readiness.get("score")) >= 2 or utility_signal_score >= 3
                else agent_runtime_contract.WRITE_MEDIUM_PROFILE
            )
            selection_mode = "validation_focused"
        elif intent_family in {"implementation", "write", "bugfix"} or actionability_score >= 3:
            if risk_score >= 3 or (deep_reasoning_ready and _int_value(context_density.get("score")) >= 3):
                profile = agent_runtime_contract.FRONTIER_HIGH_PROFILE
                selection_mode = "critical_accuracy"
            elif _int_value(reasoning_readiness.get("score")) >= 3 or utility_signal_score >= 3:
                profile = agent_runtime_contract.WRITE_HIGH_PROFILE
                selection_mode = "bounded_write"
            else:
                profile = agent_runtime_contract.WRITE_MEDIUM_PROFILE
                selection_mode = "bounded_write"
        elif intent_family in {"docs", "governance"}:
            profile = (
                agent_runtime_contract.FAST_WORKER_PROFILE
                if utility_signal_score >= 2
                else agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE
            )
            selection_mode = (
                "support_fast_lane"
                if profile == agent_runtime_contract.FAST_WORKER_PROFILE
                else "analysis_scout"
            )
        model, reasoning_effort = _explicit_model_selection_fields(
            profile=profile,
            host_capabilities=resolved_host_capabilities,
        )
        execution_profile.update(
            {
                "profile": profile,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "agent_role": (
                    "explorer"
                    if profile in {
                        agent_runtime_contract.ANALYSIS_MEDIUM_PROFILE,
                        agent_runtime_contract.ANALYSIS_HIGH_PROFILE,
                    }
                    else "worker"
                ),
                "selection_mode": selection_mode,
                "delegate_preference": "delegate",
            }
        )
        execution_profile["confidence"] = {
            "score": max(
                2,
                min(
                        4,
                        execution_profile_score
                        + (
                            1
                            if execution_profile["profile"]
                            in {
                                agent_runtime_contract.WRITE_HIGH_PROFILE,
                                agent_runtime_contract.FRONTIER_HIGH_PROFILE,
                            }
                            and deep_reasoning_ready
                            else 0
                        ),
                ),
            ),
            "level": _score_level(
                max(
                    2,
                    min(
                        4,
                        execution_profile_score
                        + (
                            1
                            if execution_profile["profile"]
                            in {
                                agent_runtime_contract.WRITE_HIGH_PROFILE,
                                agent_runtime_contract.FRONTIER_HIGH_PROFILE,
                            }
                            and deep_reasoning_ready
                            else 0
                        ),
                    ),
                )
            ),
        }
    if compact_bootstrap_handoff:
        execution_confidence = (
            dict(execution_profile.get("confidence", {}))
            if isinstance(execution_profile.get("confidence"), Mapping)
            else {}
        )
        execution_profile = {
            key: value
            for key, value in {
                "profile": str(execution_profile.get("profile", "")).strip(),
                "agent_role": str(execution_profile.get("agent_role", "")).strip(),
                "selection_mode": str(execution_profile.get("selection_mode", "")).strip(),
                "delegate_preference": str(execution_profile.get("delegate_preference", "")).strip(),
                "source": str(execution_profile.get("source", "")).strip(),
                "confidence": {
                    "score": int(execution_confidence.get("score", 0) or 0),
                    "level": str(execution_confidence.get("level", "")).strip(),
                }
                if execution_confidence
                else {},
            }.items()
            if value not in ("", [], {}, None)
        }
    native_spawn_ready_result = native_spawn_execution_ready(
        route_ready=route_ready,
        full_scan_recommended=bool(final_payload.get("full_scan_recommended")),
        narrowing_required=bool(narrowing_guidance.get("required")),
        within_budget=bool(packet_quality_payload.get("within_budget")),
        delegate_preference=str(execution_profile.get("delegate_preference", "")).strip(),
        model=str(execution_profile.get("model", "")).strip(),
        reasoning_effort=str(execution_profile.get("reasoning_effort", "")).strip(),
        agent_role=str(execution_profile.get("agent_role", "")).strip(),
        selection_mode=str(execution_profile.get("selection_mode", "")).strip(),
        selected_test_count=len([row for row in tests if isinstance(row, Mapping)]),
        selected_command_count=len([str(token).strip() for token in commands if str(token).strip()]),
        selected_doc_count=len([str(token).strip() for token in docs if str(token).strip()]),
        strict_gate_command_count=_count_or_list_len(
            validation_bundle,
            list_key="strict_gate_commands",
            count_key="strict_gate_command_count",
        ),
        plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
        governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
        host_runtime=resolved_host_runtime,
    )
    packet_quality_handoff["native_spawn_ready"] = native_spawn_ready_result
    execution_signals_payload = (
        dict(execution_profile.get("signals", {}))
        if isinstance(execution_profile.get("signals"), Mapping)
        else {}
    )
    if execution_signals_payload:
        expected_value = (
            dict(execution_signals_payload.get("expected_delegation_value", {}))
            if isinstance(execution_signals_payload.get("expected_delegation_value"), Mapping)
            else {}
        )
        if expected_value:
            expected_value["native_spawn_ready"] = native_spawn_ready_result
            execution_signals_payload["expected_delegation_value"] = expected_value
            execution_profile["signals"] = execution_signals_payload
    execution_constraints_payload = (
        dict(execution_profile.get("constraints", {}))
        if isinstance(execution_profile.get("constraints"), Mapping)
        else {}
    )
    if execution_constraints_payload:
        execution_constraints_payload["native_spawn_ready"] = native_spawn_ready_result
        execution_profile["constraints"] = execution_constraints_payload
    handoff = {
        "contract": "routing_handoff.v1",
        "version": "v2",
        "packet_kind": str(packet_kind or "").strip(),
        "packet_state": str(packet_state or "").strip(),
        "selection_state": str(packet_quality.get("selection_state", "")).strip(),
        "routing_confidence": routing_confidence,
        "accuracy_posture": str(packet_quality.get("accuracy_posture", "")).strip(),
        "evidence_consensus": str(packet_quality.get("evidence_consensus", "")).strip(),
        "guidance_coverage": str(packet_quality.get("guidance_coverage", "")).strip(),
        "actionability_level": actionability_level,
        "within_budget": bool(packet_quality.get("within_budget")),
        "narrowing_required": bool(narrowing_guidance.get("required")),
        "route_ready": route_ready,
        "primary_anchor_path": str(anchor_paths[0]).strip() if anchor_paths else "",
        "primary_workstream": {
            "entity_id": str(primary_workstream.get("entity_id", "")).strip(),
            "title": str(primary_workstream.get("title", "")).strip(),
        }
        if primary_workstream
        else {},
        "grounding": {
            "grounded": grounding_score >= 3,
            "score": grounding_score,
        },
        "odylith_execution_profile": execution_profile,
        "packet_quality": packet_quality_handoff,
        "actionability": {
            "score": actionability_score,
            "level": actionability_level or _score_level(actionability_score),
            "doc_count": len([str(token).strip() for token in docs if str(token).strip()]),
            "test_count": len([row for row in tests if isinstance(row, Mapping)]),
            "command_count": len([str(token).strip() for token in commands if str(token).strip()]),
            "guidance_count": len([row for row in selected_guidance if isinstance(row, Mapping)]),
        },
        "validation": {
            "burden": validation_score,
            "level": validation_level or _score_level(validation_score),
            "explicit_commands": bool(commands),
            "explicit_tests": bool(tests),
        },
        "parallelism": {
            "confidence": parallelism_confidence,
            "hint": parallelism_hint,
            "merge_burden": 3 if parallelism_hint in {"serial_guarded", "serial_preferred"} else 1,
        },
        "optimization": optimization_handoff,
        "utility": utility_handoff,
        "intent": {
            "family": str(intent_profile.get("family", "")).strip(),
            "mode": str(intent_profile.get("mode", "")).strip(),
            "critical_path": str(intent_profile.get("critical_path", "")).strip(),
            "confidence": str(intent_profile.get("confidence", "")).strip(),
            "explicit": bool(intent_profile.get("explicit")),
            "source": str(intent_profile.get("source", "")).strip(),
        },
        "risk": {
            "score": risk_score,
            "level": _score_level(risk_score),
        },
        "retained_actions": {
            "doc_count": len([str(token).strip() for token in docs if str(token).strip()]),
            "command_count": len([str(token).strip() for token in commands if str(token).strip()]),
            "test_count": len([row for row in tests if isinstance(row, Mapping)]),
            "guidance_count": len([row for row in selected_guidance if isinstance(row, Mapping)]),
            "direct_guidance_count": _int_value(packet_quality.get("direct_guidance_chunk_count")),
        },
        "native_spawn_ready": native_spawn_ready_result,
        "reasoning_bias": reasoning_bias,
        "parallelism_hint": parallelism_hint,
        "top_guidance": top_guidance,
    }
    if compact_bootstrap_handoff:
        for key in (
            "accuracy_posture",
            "evidence_consensus",
            "guidance_coverage",
            "actionability",
            "risk",
            "primary_anchor_path",
            "primary_workstream",
            "native_spawn_ready",
            "reasoning_bias",
            "parallelism_hint",
        ):
            handoff.pop(key, None)
        handoff["packet_quality"] = {
            "evidence_quality": packet_quality_handoff.get("evidence_quality", {}),
            "validation_pressure": packet_quality_handoff.get("validation_pressure", {}),
            "utility_profile": packet_quality_handoff.get("utility_profile", {}),
            "context_density": packet_quality_handoff.get("context_density", {}),
            "reasoning_readiness": packet_quality_handoff.get("reasoning_readiness", {}),
            "intent_profile": packet_quality_handoff.get("intent_profile", {}),
            "reasoning_bias": reasoning_bias,
            "within_budget": bool(packet_quality_payload.get("within_budget")),
        }
        if gated_bootstrap_handoff:
            handoff["packet_quality"] = {
                key: value
                for key, value in {
                    "validation_pressure": {
                        "score": _int_value(
                            dict(packet_quality_handoff.get("validation_pressure", {})).get("score", 0)
                        ),
                        "level": str(
                            dict(packet_quality_handoff.get("validation_pressure", {})).get("level", "")
                        ).strip(),
                    }
                    if isinstance(packet_quality_handoff.get("validation_pressure"), Mapping)
                    else {},
                    "utility_profile": {
                        "score": _int_value(dict(packet_quality_handoff.get("utility_profile", {})).get("score", 0)),
                        "level": str(dict(packet_quality_handoff.get("utility_profile", {})).get("level", "")).strip(),
                    }
                    if isinstance(packet_quality_handoff.get("utility_profile"), Mapping)
                    else {},
                    "context_density": {
                        "score": _int_value(dict(packet_quality_handoff.get("context_density", {})).get("score", 0)),
                        "level": str(dict(packet_quality_handoff.get("context_density", {})).get("level", "")).strip(),
                    }
                    if isinstance(packet_quality_handoff.get("context_density"), Mapping)
                    else {},
                    "reasoning_readiness": {
                        "score": _int_value(
                            dict(packet_quality_handoff.get("reasoning_readiness", {})).get("score", 0)
                        ),
                        "level": str(
                            dict(packet_quality_handoff.get("reasoning_readiness", {})).get("level", "")
                        ).strip(),
                        "mode": str(
                            dict(packet_quality_handoff.get("reasoning_readiness", {})).get("mode", "")
                        ).strip(),
                    }
                    if isinstance(packet_quality_handoff.get("reasoning_readiness"), Mapping)
                    else {},
                    "intent_profile": {
                        "family": str(dict(packet_quality_handoff.get("intent_profile", {})).get("family", "")).strip(),
                        "mode": str(dict(packet_quality_handoff.get("intent_profile", {})).get("mode", "")).strip(),
                    }
                    if isinstance(packet_quality_handoff.get("intent_profile"), Mapping)
                    else {},
                    "reasoning_bias": reasoning_bias,
                    "within_budget": bool(packet_quality_payload.get("within_budget")),
                }.items()
                if value not in ("", [], {}, None, False)
            }
            handoff["validation"] = {
                key: value
                for key, value in {
                    "burden": validation_score,
                    "level": validation_level or _score_level(validation_score),
                }.items()
                if value not in ("", [], {}, None, 0)
            }
            handoff["parallelism"] = {
                key: value
                for key, value in {
                    "hint": parallelism_hint,
                    "merge_burden": 3 if parallelism_hint in {"serial_guarded", "serial_preferred"} else 1,
                }.items()
                if value not in ("", [], {}, None)
            }
            handoff["optimization"] = {
                key: value
                for key, value in {
                    "utility_level": str(optimization_handoff.get("utility_level", "")).strip(),
                    "context_density_level": str(
                        dict(optimization_handoff.get("context_density", {})).get("level", "")
                    ).strip()
                    if isinstance(optimization_handoff.get("context_density"), Mapping)
                    else "",
                    "reasoning_readiness_level": str(
                        dict(optimization_handoff.get("reasoning_readiness", {})).get("level", "")
                    ).strip()
                    if isinstance(optimization_handoff.get("reasoning_readiness"), Mapping)
                    else "",
                    "within_budget": bool(optimization_handoff.get("within_budget")),
                }.items()
                if value not in ("", [], {}, None, False)
            }
            handoff["intent"] = {
                key: value
                for key, value in {
                    "family": str(intent_profile.get("family", "")).strip(),
                    "mode": str(intent_profile.get("mode", "")).strip(),
                    "critical_path": str(intent_profile.get("critical_path", "")).strip(),
                }.items()
                if value not in ("", [], {}, None)
            }
            for key in ("retained_actions", "utility", "top_guidance", "actionability_level"):
                handoff.pop(key, None)
    return {key: value for key, value in handoff.items() if value not in ("", [], {}, None)}


__all__ = [
    "build_narrowing_guidance",
    "build_retrieval_plan",
    "build_routing_handoff",
    "grounded_ambiguous_write_candidate",
    "grounded_write_execution_ready",
    "native_spawn_execution_ready",
    "summarize_routing_signals",
]

"""Packet-quality helpers for Odylith Context Engine context packets."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.context_engine import turn_context_runtime
from odylith.runtime.context_engine import tooling_context_routing as routing


def _list_rows(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in _list_rows(value) if isinstance(row, Mapping)]


def _pick_retained_docs(final_payload: Mapping[str, Any], retrieval_plan: Mapping[str, Any]) -> list[str]:
    for key in ("docs", "relevant_docs"):
        rows = [str(token).strip() for token in _list_rows(final_payload.get(key)) if str(token).strip()]
        if rows:
            return rows
    return [str(token).strip() for token in _list_rows(retrieval_plan.get("selected_docs")) if str(token).strip()]


def _retained_retrieval_plan(final_payload: Mapping[str, Any], retrieval_plan: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = final_payload.get("retrieval_plan", {})
    return candidate if isinstance(candidate, Mapping) else retrieval_plan


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _score_level(score: int) -> str:
    clamped = max(0, min(4, int(score)))
    if clamped >= 4:
        return "high"
    if clamped >= 2:
        return "medium"
    if clamped >= 1:
        return "low"
    return "none"


def _truncated_sections(final_payload: Mapping[str, Any]) -> list[str]:
    truncation = final_payload.get("truncation", {})
    if not isinstance(truncation, Mapping):
        return []
    rows: list[str] = []
    for key, value in truncation.items():
        if not isinstance(value, Mapping):
            continue
        if bool(value.get("truncated")) or bool(value.get("applied")) or _int_value(value.get("step_count")) > 0:
            token = str(key).strip()
            if token:
                rows.append(token)
    return sorted({token for token in rows})


def _compaction_pressure(final_payload: Mapping[str, Any], packet_metrics: Mapping[str, Any]) -> tuple[int, str]:
    sections = _truncated_sections(final_payload)
    truncation = final_payload.get("truncation", {})
    packet_budget = dict(truncation.get("packet_budget", {})) if isinstance(truncation, Mapping) else {}
    step_count = _int_value(packet_budget.get("step_count"))
    estimated_bytes = _int_value(packet_metrics.get("estimated_bytes"))
    budget_bytes = _int_value(packet_metrics.get("budget_bytes"))
    if not bool(packet_metrics.get("within_budget")):
        return 4, "high"
    if step_count >= 4 or len(sections) >= 3:
        return 3, "high"
    if budget_bytes and estimated_bytes >= int(budget_bytes * 0.85):
        return 2, "medium"
    if sections:
        return 1, "low"
    return 0, "none"


def _utility_level(score: int) -> str:
    clamped = max(0, min(100, int(score)))
    if clamped >= 75:
        return "high"
    if clamped >= 50:
        return "medium"
    if clamped >= 25:
        return "low"
    return "minimal"


def _token_efficiency_score(*, utility_score: int, estimated_tokens: int, retained_signal_count: int, within_budget: bool) -> int:
    if utility_score <= 0 or estimated_tokens <= 0 or retained_signal_count <= 0:
        return 0
    density = float(utility_score * retained_signal_count) / float(max(1, estimated_tokens))
    if density >= 0.12 and within_budget:
        return 4
    if density >= 0.08 and within_budget:
        return 3
    if density >= 0.05:
        return 2
    if density > 0:
        return 1
    return 0


def _guidance_source_token(row: Mapping[str, Any]) -> str:
    actionability = row.get("actionability", {})
    if not isinstance(actionability, Mapping):
        actionability = {}
    for candidate in (
        row.get("canonical_source"),
        actionability.get("read_path"),
        row.get("chunk_path"),
        row.get("chunk_id"),
    ):
        token = str(candidate or "").strip()
        if token:
            return token
    return ""


def _evidence_diversity_profile(
    *,
    selected_guidance_chunks: list[Mapping[str, Any]],
    selected_workstreams: list[Mapping[str, Any]],
    selected_components: list[Mapping[str, Any]],
    selected_docs: list[str],
    selected_tests: list[Mapping[str, Any]],
    selected_commands: list[str],
) -> dict[str, Any]:
    unique_guidance_sources = {
        _guidance_source_token(row)
        for row in selected_guidance_chunks
        if isinstance(row, Mapping) and _guidance_source_token(row)
    }
    unique_doc_paths = {str(token).strip() for token in selected_docs if str(token).strip()}
    unique_test_paths = {
        str(row.get("path", "")).strip()
        for row in selected_tests
        if isinstance(row, Mapping) and str(row.get("path", "")).strip()
    }
    unique_component_ids = {
        str(row.get("entity_id", "")).strip()
        for row in selected_components
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    }
    unique_workstream_ids = {
        str(row.get("entity_id", "")).strip()
        for row in selected_workstreams
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    }
    domain_count = sum(
        1
        for rows in (
            selected_guidance_chunks,
            selected_workstreams,
            selected_components,
            selected_docs,
            selected_tests,
            selected_commands,
        )
        if rows
    )
    duplicate_guidance_count = max(0, len(selected_guidance_chunks) - len(unique_guidance_sources))
    score = 0
    if domain_count >= 4:
        score += 2
    elif domain_count >= 2:
        score += 1
    if len(unique_guidance_sources) >= 2:
        score += 1
    if unique_doc_paths or unique_test_paths:
        score += 1
    if unique_component_ids or unique_workstream_ids:
        score += 1
    if duplicate_guidance_count and len(selected_guidance_chunks) > 1:
        score -= 1
    score = max(0, min(4, score))
    return {
        "score": score,
        "level": _score_level(score),
        "domain_count": domain_count,
        "unique_guidance_source_count": len(unique_guidance_sources),
        "unique_doc_count": len(unique_doc_paths),
        "unique_test_count": len(unique_test_paths),
        "unique_component_count": len(unique_component_ids),
        "unique_workstream_count": len(unique_workstream_ids),
        "duplicate_guidance_count": duplicate_guidance_count,
    }


def _context_density_profile(
    *,
    estimated_tokens: int,
    evidence_quality_score: int,
    actionability_score: int,
    direct_guidance_chunk_count: int,
    actionable_guidance_chunk_count: int,
    retained_signal_count: int,
    selected_domain_count: int,
    evidence_diversity_score: int,
    within_budget: bool,
    compaction_pressure_score: int,
) -> dict[str, Any]:
    high_yield_signal_count = (
        min(direct_guidance_chunk_count, 3) * 2
        + min(actionable_guidance_chunk_count, 3) * 2
        + evidence_quality_score
        + actionability_score
    )
    signal_mass = (
        high_yield_signal_count
        + min(retained_signal_count, 10)
        + min(selected_domain_count, 6)
        + (evidence_diversity_score * 2)
    )
    density_per_1k_tokens = round((float(signal_mass) * 1000.0) / float(max(1, estimated_tokens)), 2)
    high_yield_ratio = round(float(high_yield_signal_count) / float(max(1, retained_signal_count)), 3)
    score = 0
    if density_per_1k_tokens >= 18.0 and within_budget:
        score += 2
    elif density_per_1k_tokens >= 11.0:
        score += 1
    if high_yield_ratio >= 0.55:
        score += 1
    elif high_yield_ratio >= 0.35:
        score += 0
    if evidence_diversity_score >= 2:
        score += 1
    if compaction_pressure_score >= 3:
        score -= 1
    score = max(0, min(4, score))
    return {
        "score": score,
        "level": _score_level(score),
        "density_per_1k_tokens": density_per_1k_tokens,
        "high_yield_signal_ratio": high_yield_ratio,
        "signal_mass": signal_mass,
    }


def _reasoning_readiness_profile(
    *,
    packet_state: str,
    full_scan_recommended: bool,
    anchor_quality: str,
    ambiguity_class: str,
    evidence_quality_score: int,
    actionability_score: int,
    validation_pressure_score: int,
    context_density_score: int,
    evidence_diversity_score: int,
    within_budget: bool,
    compaction_pressure_score: int,
) -> dict[str, Any]:
    if full_scan_recommended or str(packet_state or "").strip().startswith("gated_"):
        return {
            "score": 0,
            "level": "none",
            "mode": "narrow_first",
            "deep_reasoning_ready": False,
        }
    score = 0
    if anchor_quality in {"explicit", "non_shared"}:
        score += 1
    if evidence_quality_score >= 3:
        score += 1
    if actionability_score >= 2:
        score += 1
    if context_density_score >= 2:
        score += 1
    if evidence_diversity_score >= 2:
        score += 1
    if not within_budget:
        score -= 1
    if compaction_pressure_score >= 3:
        score -= 1
    if ambiguity_class == "historical_fanout":
        score -= 1
    score = max(0, min(4, score))
    deep_reasoning_ready = (
        score >= 3
        and within_budget
        and anchor_quality in {"explicit", "non_shared"}
        and ambiguity_class not in {"historical_fanout", "close_competition"}
    )
    mode = "guarded"
    if deep_reasoning_ready and validation_pressure_score >= 3:
        mode = "validation_focused"
    elif deep_reasoning_ready:
        mode = "deep_grounded"
    elif score >= 2:
        mode = "bounded_analysis"
    return {
        "score": score,
        "level": _score_level(score),
        "mode": mode,
        "deep_reasoning_ready": deep_reasoning_ready,
    }


def _normalize_intent_text(value: Any) -> str:
    return " ".join(str(value or "").replace("-", " ").replace("_", " ").strip().lower().split())


def _intent_matches(value: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in value for phrase in phrases)


def _explicit_intent(payload: Mapping[str, Any]) -> str:
    turn_context = payload.get("turn_context", {})
    if isinstance(turn_context, Mapping):
        operator_ask = turn_context_runtime.operator_ask_text(turn_context)
        if operator_ask:
            return operator_ask
    direct = str(payload.get("intent", "")).strip()
    if direct:
        return direct
    session_payload = payload.get("session", {})
    if isinstance(session_payload, Mapping):
        turn_context = session_payload.get("turn_context", {})
        if isinstance(turn_context, Mapping):
            operator_ask = turn_context_runtime.operator_ask_text(turn_context)
            if operator_ask:
                return operator_ask
        return str(session_payload.get("intent", "")).strip()
    return ""


def _compact_packet_quality_payload(payload: Mapping[str, Any], *, packet_kind: str, packet_state: str) -> dict[str, Any]:
    compact_gated = str(packet_state or "").strip().startswith("gated_")
    if not compact_gated:
        return dict(payload)
    compact = {
        "packet_kind": str(payload.get("packet_kind", "")).strip(),
        "packet_state": str(payload.get("packet_state", "")).strip(),
        "selection_state": str(payload.get("selection_state", "")).strip(),
        "context_richness": str(payload.get("context_richness", "")).strip(),
        "accuracy_posture": str(payload.get("accuracy_posture", "")).strip(),
        "routing_confidence": str(payload.get("routing_confidence", "")).strip(),
        "anchor_quality": str(payload.get("anchor_quality", "")).strip(),
        "guidance_coverage": str(payload.get("guidance_coverage", "")).strip(),
        "ambiguity_class": str(payload.get("ambiguity_class", "")).strip(),
        "evidence_quality": dict(payload.get("evidence_quality", {}))
        if isinstance(payload.get("evidence_quality"), Mapping)
        else {},
        "actionability": dict(payload.get("actionability", {}))
        if isinstance(payload.get("actionability"), Mapping)
        else {},
        "validation_pressure": dict(payload.get("validation_pressure", {}))
        if isinstance(payload.get("validation_pressure"), Mapping)
        else {},
        "compaction_pressure": dict(payload.get("compaction_pressure", {}))
        if isinstance(payload.get("compaction_pressure"), Mapping)
        else {},
        "intent_profile": dict(payload.get("intent_profile", {}))
        if isinstance(payload.get("intent_profile"), Mapping)
        else {},
        "utility_profile": {
            "score": _int_value(dict(payload.get("utility_profile", {})).get("score"))
            if isinstance(payload.get("utility_profile"), Mapping)
            else 0,
            "level": str(dict(payload.get("utility_profile", {})).get("level", "")).strip()
            if isinstance(payload.get("utility_profile"), Mapping)
            else "",
            "token_efficiency": dict(dict(payload.get("utility_profile", {})).get("token_efficiency", {}))
            if isinstance(payload.get("utility_profile"), Mapping)
            and isinstance(dict(payload.get("utility_profile", {})).get("token_efficiency"), Mapping)
            else {},
        },
        "context_density": {
            "score": _int_value(dict(payload.get("context_density", {})).get("score")),
            "level": str(dict(payload.get("context_density", {})).get("level", "")).strip(),
        }
        if isinstance(payload.get("context_density"), Mapping)
        else {},
        "evidence_diversity": {
            "score": _int_value(dict(payload.get("evidence_diversity", {})).get("score")),
            "level": str(dict(payload.get("evidence_diversity", {})).get("level", "")).strip(),
            "domain_count": _int_value(dict(payload.get("evidence_diversity", {})).get("domain_count")),
        }
        if isinstance(payload.get("evidence_diversity"), Mapping)
        else {},
        "reasoning_readiness": {
            "score": _int_value(dict(payload.get("reasoning_readiness", {})).get("score")),
            "level": str(dict(payload.get("reasoning_readiness", {})).get("level", "")).strip(),
            "mode": str(dict(payload.get("reasoning_readiness", {})).get("mode", "")).strip(),
            "deep_reasoning_ready": bool(dict(payload.get("reasoning_readiness", {})).get("deep_reasoning_ready")),
        }
        if isinstance(payload.get("reasoning_readiness"), Mapping)
        else {},
        "reasoning_bias": str(payload.get("reasoning_bias", "")).strip(),
        "parallelism_hint": str(payload.get("parallelism_hint", "")).strip(),
        "native_spawn_ready": bool(payload.get("native_spawn_ready")),
        "truncation_applied": bool(payload.get("truncation_applied")),
        "full_scan_recommended": bool(payload.get("full_scan_recommended")),
        "within_budget": bool(payload.get("within_budget")),
    }
    return {key: value for key, value in compact.items() if value not in ("", [], {}, None)}


def _derive_intent_profile(
    *,
    payload: Mapping[str, Any],
    explicit_intent: str,
    packet_kind: str,
    packet_state: str,
    full_scan_recommended: bool,
    has_non_shared_anchor: bool,
    guidance_coverage: str,
    selected_docs: list[str],
    selected_tests: list[Mapping[str, Any]],
    selected_commands: list[str],
    selected_guidance_chunks: list[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_intent = _normalize_intent_text(explicit_intent)
    explicit = bool(normalized_intent)
    source = "explicit" if explicit else "derived"
    family = ""
    turn_context = payload.get("turn_context", {})
    if not isinstance(turn_context, Mapping):
        session_payload = payload.get("session", {})
        turn_context = session_payload.get("turn_context", {}) if isinstance(session_payload, Mapping) else {}
    fast_lane_family = turn_context_runtime.infer_turn_family(
        turn_context if isinstance(turn_context, Mapping) and turn_context else {"intent": explicit_intent}
    )
    if fast_lane_family == "ui_layout" or _intent_matches(
        normalized_intent,
        ("align", "full width", "layout", "move", "next to", "spacing", "truncate", "width"),
    ):
        family = "ui_layout"
    elif fast_lane_family == "surface_copy" or _intent_matches(
        normalized_intent,
        ("copy", "label", "rename", "text", "title", "wording"),
    ):
        family = "surface_copy"
    elif fast_lane_family == "surface_binding" or _intent_matches(
        normalized_intent,
        ("active item", "binding", "bound", "current release", "stale", "wrong release", "wrong status"),
    ):
        family = "surface_binding"
    elif _intent_matches(normalized_intent, ("validate", "validation", "verify", "regression", "test", "proof")):
        family = "validation"
    elif _intent_matches(normalized_intent, ("diagnose", "debug", "triage", "root cause", "investigate")):
        family = "diagnosis"
    elif _intent_matches(normalized_intent, ("review", "audit", "critique", "adjudicate")):
        family = "review"
    elif _intent_matches(normalized_intent, ("doc", "docs", "documentation", "runbook", "spec")):
        family = "docs"
    elif _intent_matches(normalized_intent, ("governance", "plan", "backlog", "traceability", "closeout", "sync")):
        family = "governance"
    elif _intent_matches(normalized_intent, ("architecture", "design", "topology", "invariant", "contract")):
        family = "architecture"
    elif _intent_matches(normalized_intent, ("analysis", "analyze", "research", "explore", "deep dive")):
        family = "analysis"
    elif _intent_matches(normalized_intent, ("implement", "implementation", "feature", "write", "patch", "fix", "refactor", "code")):
        family = "implementation"
    explicit_write_signal = _intent_matches(
        normalized_intent,
        ("implement", "implementation", "feature", "write", "patch", "fix", "refactor", "code"),
    )

    if not family:
        gated_packet = full_scan_recommended or str(packet_state or "").strip().startswith("gated_")
        if gated_packet:
            family = "analysis"
        elif (
            selected_tests
            and not selected_guidance_chunks
            and (selected_commands or len(selected_tests) >= max(1, len(selected_docs)))
        ):
            family = "validation"
        elif selected_docs and not selected_tests and not selected_commands and not selected_guidance_chunks:
            family = "docs"
        elif selected_commands or selected_guidance_chunks:
            family = "implementation"
        elif selected_docs and str(packet_kind or "").strip() in {"impact", "session_brief", "bootstrap_session"}:
            family = "implementation"
        elif str(packet_kind or "").strip() == "impact":
            family = "analysis"
        else:
            family = "analysis"

    grounded_write_shape = (
        not full_scan_recommended
        and not str(packet_state or "").strip().startswith("gated_")
        and bool(has_non_shared_anchor)
        and (str(guidance_coverage or "").strip() in {"direct", "anchored"} or bool(selected_guidance_chunks))
        and bool(selected_commands or selected_tests)
    )
    if family in {"analysis", "diagnosis", "review"} and grounded_write_shape and (not explicit or explicit_write_signal):
        family = "implementation" if (selected_commands or selected_guidance_chunks) else "validation"

    if family in {"implementation", "ui_layout", "surface_copy", "surface_binding"}:
        mode = "write_execution"
    elif family == "validation":
        mode = "validation_proof"
    elif family == "diagnosis":
        mode = "failure_analysis"
    elif family == "review":
        mode = "code_review"
    elif family == "docs":
        mode = "docs_alignment"
    elif family == "governance":
        mode = "governance_closeout"
    elif family == "architecture":
        mode = "architecture_grounding"
    else:
        mode = "scope_narrowing" if full_scan_recommended or str(packet_state or "").strip().startswith("gated_") else "read_analysis"

    if full_scan_recommended or str(packet_state or "").strip().startswith("gated_"):
        critical_path = "narrow_first"
    elif family in {"implementation", "ui_layout", "surface_copy", "surface_binding"}:
        critical_path = "implementation_first"
    elif family == "validation":
        critical_path = "validation_first"
    elif family == "docs":
        critical_path = "docs_after_write"
    elif family == "governance":
        critical_path = "governance_local"
    else:
        critical_path = "analysis_first"

    if explicit and family:
        confidence = "high"
    elif family in {"analysis", "implementation", "validation", "docs", "governance"} and (
        full_scan_recommended or str(packet_kind or "").strip() in {"impact", "session_brief", "bootstrap_session"}
    ):
        confidence = "medium"
    elif family:
        confidence = "low"
    else:
        confidence = "none"
    return {
        "family": family,
        "mode": mode,
        "critical_path": critical_path,
        "confidence": confidence,
        "explicit": explicit,
        "source": source,
    }


def summarize_packet_quality(
    *,
    packet_kind: str,
    packet_state: str,
    selection_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
    packet_metrics: Mapping[str, Any],
    final_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return compact packet-quality diagnostics suitable for payloads and timing."""

    payload = final_payload if isinstance(final_payload, Mapping) else {}
    retained_plan = _retained_retrieval_plan(payload, retrieval_plan)
    selected_guidance_chunks = _mapping_rows(retained_plan.get("selected_guidance_chunks"))
    selected_workstreams = _mapping_rows(retained_plan.get("selected_workstreams"))
    selected_components = _mapping_rows(payload.get("components"))
    selected_docs = _pick_retained_docs(payload, retained_plan)
    selected_tests = _mapping_rows(payload.get("recommended_tests")) or _mapping_rows(retained_plan.get("selected_tests"))
    selected_commands = [str(token).strip() for token in _list_rows(payload.get("recommended_commands")) if str(token).strip()]
    if not selected_commands:
        selected_commands = [
            str(token).strip() for token in _list_rows(retained_plan.get("selected_commands")) if str(token).strip()
        ]
    validation_bundle = dict(payload.get("validation_bundle", {})) if isinstance(payload.get("validation_bundle"), Mapping) else {}
    execution_profile = dict(payload.get("execution_profile", {})) if isinstance(payload.get("execution_profile"), Mapping) else {}
    strict_gate_commands = [
        str(token).strip()
        for token in _list_rows(validation_bundle.get("strict_gate_commands"))
        if str(token).strip()
    ]
    anchor_paths = [str(token).strip() for token in _list_rows(retained_plan.get("anchor_paths")) if str(token).strip()]
    if not anchor_paths:
        anchor_paths = [str(token).strip() for token in _list_rows(payload.get("changed_paths")) if str(token).strip()]
    workstream_selection = payload.get("workstream_selection", {})
    if not isinstance(workstream_selection, Mapping):
        workstream_selection = retained_plan
    shared_only_input = str(retained_plan.get("anchor_quality", "")).strip() == "shared_only"
    signal_summary = routing.summarize_routing_signals(
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
        selected_guidance_chunks=selected_guidance_chunks,
    )
    visible_domain_count = 1
    if _mapping_rows(payload.get("components")):
        visible_domain_count += 1
    if selected_workstreams:
        visible_domain_count += 1
    if selected_guidance_chunks:
        visible_domain_count += 1
    if selected_docs:
        visible_domain_count += 1
    if selected_tests:
        visible_domain_count += 1
    if selected_commands:
        visible_domain_count += 1
    evidence_consensus = str(signal_summary.get("evidence_consensus", "")).strip()
    guidance_coverage = str(signal_summary.get("guidance_coverage", "")).strip()
    anchor_quality = str(signal_summary.get("anchor_quality", "")).strip()
    ambiguity_class = str(signal_summary.get("ambiguity_class", "")).strip()
    selected_domains = [str(token).strip() for token in signal_summary.get("selected_domains", []) if str(token).strip()]
    workstream_candidate_count = int(signal_summary.get("workstream_candidate_count", 0) or 0)
    strong_workstream_candidate_count = int(signal_summary.get("strong_workstream_candidate_count", 0) or 0)
    direct_guidance_chunk_count = int(
        dict(signal_summary.get("evidence_summary", {})).get("direct_guidance_count", 0)
        if isinstance(signal_summary.get("evidence_summary"), Mapping)
        else 0
    )
    actionable_guidance_chunk_count = int(
        dict(signal_summary.get("actionability", {})).get("actionable_guidance_count", 0)
        if isinstance(signal_summary.get("actionability"), Mapping)
        else 0
    )
    evidence_profile = dict(signal_summary.get("evidence_profile", {})) if isinstance(signal_summary.get("evidence_profile"), Mapping) else {}
    actionability_profile = dict(signal_summary.get("actionability_profile", {})) if isinstance(signal_summary.get("actionability_profile"), Mapping) else {}
    validation_profile = dict(signal_summary.get("validation_profile", {})) if isinstance(signal_summary.get("validation_profile"), Mapping) else {}
    evidence_quality_score = _int_value(evidence_profile.get("score"))
    evidence_quality_level = str(evidence_profile.get("level", "")).strip() or _score_level(evidence_quality_score)
    actionability_score = _int_value(actionability_profile.get("score"))
    actionability_level = str(actionability_profile.get("level", "")).strip() or _score_level(actionability_score)
    validation_pressure_score = _int_value(validation_profile.get("score"))
    validation_pressure_level = str(validation_profile.get("level", "")).strip() or _score_level(validation_pressure_score)
    if full_scan_recommended or str(packet_state or "").strip().startswith("gated_"):
        richness = "narrowing"
    elif evidence_consensus == "strong" and guidance_coverage in {"direct", "anchored"} and (
        selected_commands or selected_tests
    ):
        richness = "rich"
    elif evidence_consensus in {"strong", "mixed"}:
        richness = "focused"
    else:
        richness = "shallow"
    accuracy_posture = "fail_closed"
    if selection_state == "explicit":
        accuracy_posture = "explicit_override"
    elif selection_state == "ambiguous" and anchor_quality == "non_shared":
        accuracy_posture = "anchored_but_ambiguous"
    elif anchor_quality == "non_shared" and evidence_consensus == "strong":
        accuracy_posture = "anchored_precision"
    elif anchor_quality == "shared_only":
        accuracy_posture = "broad_guarded"
    compaction_pressure_score, compaction_pressure_level = _compaction_pressure(payload, packet_metrics)
    truncated_sections = _truncated_sections(payload)
    retained_signal_count = (
        len(selected_guidance_chunks)
        + len(selected_docs)
        + len(selected_tests)
        + len(selected_commands)
        + len(selected_workstreams)
        + len(selected_components)
    )
    within_budget = bool(packet_metrics.get("within_budget"))
    evidence_diversity = _evidence_diversity_profile(
        selected_guidance_chunks=selected_guidance_chunks,
        selected_workstreams=selected_workstreams,
        selected_components=selected_components,
        selected_docs=selected_docs,
        selected_tests=selected_tests,
        selected_commands=selected_commands,
    )
    evidence_diversity_score = _int_value(evidence_diversity.get("score"))
    utility_raw_score = (
        (evidence_quality_score * 16)
        + (actionability_score * 14)
        + (validation_pressure_score * 8)
        + (min(direct_guidance_chunk_count, 3) * 6)
        + (min(actionable_guidance_chunk_count, 3) * 5)
        + (min(len(selected_docs), 3) * 4)
        + (min(len(selected_tests), 3) * 5)
        + (min(len(selected_commands), 3) * 5)
        + (min(len(selected_workstreams), 2) * 4)
        + (min(len(selected_components), 2) * 3)
        + (6 if within_budget else 0)
        + (evidence_diversity_score * 5)
        - (compaction_pressure_score * 6)
        - (12 if full_scan_recommended else 0)
        - (8 if shared_only_input else 0)
        - (min(_int_value(evidence_diversity.get("duplicate_guidance_count")), 3) * 4)
        - (6 if ambiguity_class == "historical_fanout" and selection_state != "explicit" else 0)
    )
    utility_score = max(0, min(100, int(utility_raw_score)))
    utility_level = _utility_level(utility_score)
    estimated_tokens = int(packet_metrics.get("estimated_tokens", 0) or 0)
    token_efficiency_score = _token_efficiency_score(
        utility_score=utility_score,
        estimated_tokens=estimated_tokens,
        retained_signal_count=retained_signal_count,
        within_budget=within_budget,
    )
    token_efficiency_level = _score_level(token_efficiency_score)
    density_per_1k_tokens = round((utility_score * 1000.0) / float(max(1, estimated_tokens)), 2)
    context_density = _context_density_profile(
        estimated_tokens=estimated_tokens,
        evidence_quality_score=evidence_quality_score,
        actionability_score=actionability_score,
        direct_guidance_chunk_count=direct_guidance_chunk_count,
        actionable_guidance_chunk_count=actionable_guidance_chunk_count,
        retained_signal_count=retained_signal_count,
        selected_domain_count=visible_domain_count,
        evidence_diversity_score=evidence_diversity_score,
        within_budget=within_budget,
        compaction_pressure_score=compaction_pressure_score,
    )
    reasoning_readiness = _reasoning_readiness_profile(
        packet_state=str(packet_state or "").strip(),
        full_scan_recommended=full_scan_recommended,
        anchor_quality=anchor_quality,
        ambiguity_class=ambiguity_class,
        evidence_quality_score=evidence_quality_score,
        actionability_score=actionability_score,
        validation_pressure_score=validation_pressure_score,
        context_density_score=_int_value(context_density.get("score")),
        evidence_diversity_score=evidence_diversity_score,
        within_budget=within_budget,
        compaction_pressure_score=compaction_pressure_score,
    )
    intent_profile = _derive_intent_profile(
        payload=payload,
        explicit_intent=_explicit_intent(payload),
        packet_kind=str(packet_kind or "").strip(),
        packet_state=str(packet_state or "").strip(),
        full_scan_recommended=full_scan_recommended,
        has_non_shared_anchor=str(signal_summary.get("anchor_quality", "")).strip() in {"explicit", "non_shared"},
        guidance_coverage=guidance_coverage,
        selected_docs=selected_docs,
        selected_tests=selected_tests,
        selected_commands=selected_commands,
        selected_guidance_chunks=selected_guidance_chunks,
    )
    route_ready = routing.grounded_write_execution_ready(
        packet_kind=str(packet_kind or "").strip(),
        packet_state=str(packet_state or "").strip(),
        full_scan_recommended=full_scan_recommended,
        narrowing_required=False,
        within_budget=within_budget,
        routing_confidence=str(signal_summary.get("routing_confidence", "")).strip(),
        has_non_shared_anchor=str(signal_summary.get("anchor_quality", "")).strip() in {"explicit", "non_shared"},
        ambiguity_class=ambiguity_class,
        guidance_coverage=guidance_coverage,
        intent_family=str(intent_profile.get("family", "")).strip(),
        actionability_score=actionability_score,
        validation_score=validation_pressure_score,
        context_density_score=_int_value(context_density.get("score")),
        evidence_quality_score=evidence_quality_score,
        direct_guidance_chunk_count=direct_guidance_chunk_count,
        actionable_guidance_chunk_count=actionable_guidance_chunk_count,
        selected_test_count=len(selected_tests),
        selected_command_count=len(selected_commands),
        selected_doc_count=len(selected_docs),
        strict_gate_command_count=len(strict_gate_commands),
        plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
        governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
    )
    native_spawn_ready = routing.native_spawn_execution_ready(
        route_ready=route_ready,
        full_scan_recommended=full_scan_recommended,
        narrowing_required=False,
        within_budget=within_budget,
        delegate_preference=str(execution_profile.get("delegate_preference", "")).strip(),
        model=str(execution_profile.get("model", "")).strip(),
        reasoning_effort=str(execution_profile.get("reasoning_effort", "")).strip(),
        agent_role=str(execution_profile.get("agent_role", "")).strip(),
        selection_mode=str(execution_profile.get("selection_mode", "")).strip(),
        selected_test_count=len(selected_tests),
        selected_command_count=len(selected_commands),
        selected_doc_count=len(selected_docs),
        strict_gate_command_count=len(strict_gate_commands),
        plan_binding_required=bool(validation_bundle.get("plan_binding_required")),
        governed_surface_sync_required=bool(validation_bundle.get("governed_surface_sync_required")),
    )
    payload = {
        "packet_kind": str(packet_kind or "").strip(),
        "packet_state": str(packet_state or "").strip(),
        "selection_state": str(selection_state or "").strip(),
        "context_richness": richness,
        "accuracy_posture": accuracy_posture,
        "routing_confidence": str(signal_summary.get("routing_confidence", "")).strip(),
        "anchor_quality": anchor_quality,
        "guidance_coverage": guidance_coverage,
        "evidence_consensus": evidence_consensus,
        "precision_score": int(signal_summary.get("precision_score", 0) or 0),
        "ambiguity_class": ambiguity_class,
        "evidence_quality": {
            "score": evidence_quality_score,
            "level": evidence_quality_level,
        },
        "evidence_quality_level": evidence_quality_level,
        "actionability": {
            "score": actionability_score,
            "level": actionability_level,
        },
        "actionability_level": actionability_level,
        "validation_pressure": {
            "score": validation_pressure_score,
            "level": validation_pressure_level,
        },
        "compaction_pressure": {
            "score": compaction_pressure_score,
            "level": compaction_pressure_level,
        },
        "intent_profile": intent_profile,
        "utility_profile": {
            "score": utility_score,
            "level": utility_level,
            "retained_signal_count": retained_signal_count,
            "density_per_1k_tokens": density_per_1k_tokens,
            "token_efficiency": {
                "score": token_efficiency_score,
                "level": token_efficiency_level,
            },
        },
        "utility_level": utility_level,
        "token_efficiency": {
            "score": token_efficiency_score,
            "level": token_efficiency_level,
        },
        "context_density": context_density,
        "evidence_diversity": evidence_diversity,
        "reasoning_readiness": reasoning_readiness,
        "reasoning_bias": str(signal_summary.get("reasoning_bias", "")).strip(),
        "parallelism_hint": str(signal_summary.get("parallelism_hint", "")).strip(),
        "native_spawn_ready": native_spawn_ready,
        "trimmed_sections": truncated_sections,
        "truncation_applied": bool(truncated_sections),
        "full_scan_recommended": bool(full_scan_recommended),
        "within_budget": within_budget,
        "estimated_bytes": int(packet_metrics.get("estimated_bytes", 0) or 0),
        "estimated_tokens": estimated_tokens,
        "anchor_count": len(anchor_paths),
        "selected_domain_count": visible_domain_count,
        "selected_guidance_chunk_count": len(selected_guidance_chunks),
        "direct_guidance_chunk_count": direct_guidance_chunk_count,
        "actionable_guidance_chunk_count": actionable_guidance_chunk_count,
        "selected_workstream_count": len(selected_workstreams),
        "workstream_candidate_count": workstream_candidate_count,
        "strong_workstream_candidate_count": strong_workstream_candidate_count,
        "retained_doc_count": len(selected_docs),
        "retained_test_count": len(selected_tests),
        "retained_command_count": len(selected_commands),
    }
    return _compact_packet_quality_payload(
        payload,
        packet_kind=str(packet_kind or "").strip(),
        packet_state=str(packet_state or "").strip(),
    )


__all__ = ["summarize_packet_quality"]

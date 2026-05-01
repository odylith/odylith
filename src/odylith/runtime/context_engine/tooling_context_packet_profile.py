"""Adaptive packet profile and budget-shaping policy for Context Engine packets."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.common.value_coercion import int_value as _int_value
from odylith.runtime.common.value_coercion import mapping_copy as _mapping_value
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.context_engine import tooling_context_budgeting as budgeting


def content_budget(
    budget_meta: Mapping[str, Any],
    *,
    trim_order_paths: Sequence[Sequence[str]] | None = None,
) -> dict[str, Any]:
    content = dict(budget_meta)
    content["max_bytes"] = int(content.get("content_max_bytes", content.get("max_bytes", 0)) or 0)
    content["max_tokens"] = int(content.get("content_max_tokens", content.get("max_tokens", 0)) or 0)
    if trim_order_paths:
        content["trim_order_paths"] = [
            tuple(str(segment or "").strip() for segment in path if str(segment or "").strip())
            for path in trim_order_paths
            if isinstance(path, Sequence)
        ]
    return content


def adaptive_packet_profile(
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


def apply_adaptive_budget_profile(
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


def reorder_trim_paths(
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


__all__ = [
    "adaptive_packet_profile",
    "apply_adaptive_budget_profile",
    "content_budget",
    "reorder_trim_paths",
]

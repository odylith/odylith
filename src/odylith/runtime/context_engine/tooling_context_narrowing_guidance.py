"""Narrowing guidance assembly for Context Engine routing packets."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.common.value_coercion import int_value
from odylith.runtime.context_engine import tooling_context_routing_support as routing_support

__all__ = ("build_narrowing_guidance",)

_SUGGESTED_NARROWING_INPUTS = (
    "Provide at least one implementation, test, contract, or manifest path.",
    "Pin an explicit workstream with `--workstream B-###` when the slice is known.",
    "Read the highest-signal guidance source directly when the packet exposes one.",
    "If narrowing still fails, run the printed fallback command and then read the named source directly.",
)


def _selected_mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _next_best_anchors(retrieval_plan: Mapping[str, Any]) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    for row in _selected_mapping_rows(retrieval_plan.get("selected_workstreams"))[:2]:
        entity_id = str(row.get("entity_id", "")).strip()
        if entity_id:
            anchors.append(
                {
                    "kind": "workstream",
                    "value": entity_id,
                    "reason": "Explicit workstream selection will unlock richer context without broad guessing.",
                }
            )
    for row in _selected_mapping_rows(retrieval_plan.get("selected_components"))[:2]:
        component_id = str(row.get("entity_id", "")).strip()
        if component_id:
            anchors.append(
                {
                    "kind": "component",
                    "value": component_id,
                    "reason": "A concrete component anchor is stronger than shared guidance files alone.",
                }
            )
    for row in _selected_mapping_rows(retrieval_plan.get("selected_guidance_chunks"))[:1]:
        actionability = row.get("actionability", {})
        canonical_source = str(row.get("canonical_source", "")).strip() or (
            str(actionability.get("read_path", "")).strip() if isinstance(actionability, Mapping) else ""
        )
        if canonical_source:
            anchors.append(
                {
                    "kind": "doc",
                    "value": canonical_source,
                    "reason": "Reading the highest-signal guidance source directly will tighten the slice faster than generic context expansion.",
                }
            )
    miss_recovery = retrieval_plan.get("miss_recovery", {})
    if isinstance(miss_recovery, Mapping) and isinstance(miss_recovery.get("recovered_docs"), list):
        for doc_path in miss_recovery.get("recovered_docs", [])[:1]:
            token = str(doc_path).strip()
            if token:
                anchors.append(
                    {
                        "kind": "doc",
                        "value": token,
                        "reason": "Miss recovery found a compact supporting source worth reading before widening the slice further.",
                    }
                )
    return anchors


def _guidance_reason(
    *,
    full_scan_reason: str,
    workstream_selection: Mapping[str, Any],
) -> str:
    reason = str(full_scan_reason or "").strip()
    if not reason:
        reason = str(workstream_selection.get("reason", "")).strip()
    return reason or "The current slice is still too broad to trust expanded context."


def _retained_paths(*, payload: Mapping[str, Any], retrieval_plan: Mapping[str, Any]) -> list[str]:
    return dedupe_strings(
        [
            *routing_support.normalized_string_list(payload.get("changed_paths")),
            *routing_support.normalized_string_list(payload.get("explicit_paths")),
            *routing_support.normalized_string_list(retrieval_plan.get("anchor_paths")),
        ]
    )


def _has_direct_guidance(retrieval_plan: Mapping[str, Any]) -> bool:
    selected_counts = (
        dict(retrieval_plan.get("selected_counts", {}))
        if isinstance(retrieval_plan.get("selected_counts"), Mapping)
        else {}
    )
    return bool(
        str(retrieval_plan.get("guidance_coverage", "")).strip() in {"direct", "anchored"}
        or int_value(selected_counts.get("guidance")) > 0
    )


def _has_validation_contract(
    *,
    payload: Mapping[str, Any],
    validation_bundle: Mapping[str, Any],
) -> bool:
    return bool(
        routing_support.normalized_string_list(payload.get("recommended_commands"))
        or (
            isinstance(payload.get("recommended_tests"), list)
            and any(isinstance(row, Mapping) for row in payload.get("recommended_tests", []))
        )
        or routing_support.count_or_list_len(
            validation_bundle,
            list_key="strict_gate_commands",
            count_key="strict_gate_command_count",
        )
        > 0
    )


def _has_governance_contract(
    *,
    validation_bundle: Mapping[str, Any],
    governance_obligations: Mapping[str, Any],
) -> bool:
    return bool(
        routing_support.count_or_list_len(
            governance_obligations,
            list_key="closeout_docs",
            count_key="closeout_doc_count",
        )
        > 0
        or bool(validation_bundle.get("plan_binding_required"))
        or bool(validation_bundle.get("governed_surface_sync_required"))
    )


def _has_actionable_target_resolution(payload: Mapping[str, Any]) -> bool:
    target_resolution = (
        dict(payload.get("target_resolution", {}))
        if isinstance(payload.get("target_resolution"), Mapping)
        else {}
    )
    if bool(target_resolution.get("requires_more_consumer_context")):
        return False
    candidate_targets = _selected_mapping_rows(target_resolution.get("candidate_targets"))
    return any(str(row.get("path", "") or row.get("ref", "")).strip() for row in candidate_targets)


def _exact_path_execution_ready(
    *,
    required: bool,
    packet_kind: str,
    packet_state: str,
    full_scan_recommended: bool,
    retrieval_plan: Mapping[str, Any],
    payload: Mapping[str, Any],
    retained_paths: list[str],
    has_direct_guidance: bool,
    has_validation_contract: bool,
    has_governance_contract: bool,
) -> bool:
    ambiguity_class = str(retrieval_plan.get("ambiguity_class", "")).strip()
    return bool(
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
            or int_value(retrieval_plan.get("precision_score")) >= 40
            or has_governance_contract
        )
    )


def _fallback_commands(
    *,
    required: bool,
    anchors: list[dict[str, str]],
    suppress_degraded_receipt: bool,
    fallback_scan: Mapping[str, Any],
    retained_paths: list[str],
) -> tuple[str, str]:
    if required and anchors:
        return routing_support.fallback_anchor_commands(anchors[0])
    if required and not suppress_degraded_receipt:
        return routing_support.fallback_scan_commands(
            fallback_scan=fallback_scan,
            retained_paths=retained_paths,
        )
    return "", ""


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
    anchors = _next_best_anchors(retrieval_plan)
    reason = _guidance_reason(
        full_scan_reason=full_scan_reason,
        workstream_selection=workstream_selection,
    )
    payload = dict(final_payload) if isinstance(final_payload, Mapping) else {}
    validation_bundle = routing_support.routing_validation_bundle(payload)
    governance_obligations = routing_support.routing_governance_obligations(payload)
    retained_paths = _retained_paths(payload=payload, retrieval_plan=retrieval_plan)
    direct_guidance = _has_direct_guidance(retrieval_plan)
    validation_contract = _has_validation_contract(
        payload=payload,
        validation_bundle=validation_bundle,
    )
    governance_contract = _has_governance_contract(
        validation_bundle=validation_bundle,
        governance_obligations=governance_obligations,
    )
    if _exact_path_execution_ready(
        required=required,
        packet_kind=packet_kind,
        packet_state=packet_state,
        full_scan_recommended=full_scan_recommended,
        retrieval_plan=retrieval_plan,
        payload=payload,
        retained_paths=retained_paths,
        has_direct_guidance=direct_guidance,
        has_validation_contract=validation_contract,
        has_governance_contract=governance_contract,
    ):
        required = False
        reason = "Exact-path retained evidence already bounds execution and closeout without broader narrowing."
    elif (
        required
        and str(packet_kind or "").strip() == "bootstrap_session"
        and retained_paths
        and _has_actionable_target_resolution(payload)
    ):
        required = False
        reason = "Turn-visible file targets already bound startup; no additional narrowing required."

    suppress_degraded_receipt = reason in {"working_tree_scope_degraded", "broad_shared_paths"} and bool(retained_paths)
    if suppress_degraded_receipt:
        reason = "Current shared/control-plane context still needs one concrete code, manifest, or contract anchor."

    next_fallback_command, next_fallback_followup = _fallback_commands(
        required=required,
        anchors=anchors,
        suppress_degraded_receipt=suppress_degraded_receipt,
        fallback_scan=dict(payload.get("fallback_scan", {})) if isinstance(payload.get("fallback_scan"), Mapping) else {},
        retained_paths=retained_paths,
    )
    return {
        "required": required,
        "reason": reason,
        "suggested_inputs": list(_SUGGESTED_NARROWING_INPUTS) if required else [],
        "next_best_anchors": anchors[:3],
        "next_fallback_command": next_fallback_command,
        "next_fallback_followup": next_fallback_followup,
    }

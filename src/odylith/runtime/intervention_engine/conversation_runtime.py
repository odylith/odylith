"""Conversation Runtime helpers for the Odylith intervention engine layer."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.governance import operator_readout
from odylith.runtime.governance import proof_state
from odylith.runtime.intervention_engine import claim_runtime
from odylith.runtime.intervention_engine import conversation_artifacts
from odylith.runtime.intervention_engine import conversation_closeout
from odylith.runtime.intervention_engine import conversation_common
from odylith.runtime.intervention_engine import conversation_metrics
from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import delivery_runtime


_SUPPLEMENTAL_PRIORITY = ("risks", "insight", "history")
_EXPLICIT_SIGNAL_PRIORITY = ("risks", "insight", "history")
_RISK_BOOL_KEYS = {
    "plan_binding_required",
    "governed_surface_sync_required",
    "narrowing_required",
    "requires_widening",
}
_RISK_COUNT_KEYS = {
    "validation_obligation_count",
    "diagram_watch_gap_count",
    "unresolved_question_count",
    "operator_consequence_count",
}
_HISTORY_KEY_HINTS = ("history", "historical", "reopen", "reopened", "supersed", "linked_bug", "bug")

compose_closeout_assist = conversation_closeout.compose_closeout_assist
visibility_feedback_requested = conversation_closeout.visibility_feedback_requested


def _signal_information_tokens(payload: Mapping[str, Any]) -> set[str]:
    rows: list[str] = []
    rows.extend(str(item) for item in payload.get("facts", []) or [])
    rows.extend(str(row.get("id", "")).strip() for row in payload.get("refs", []) or [] if isinstance(row, Mapping))
    rows.append(str(payload.get("plain_text", "")))
    return conversation_common.meaningful_tokens(*rows)


def _assist_information_tokens(payload: Mapping[str, Any]) -> set[str]:
    rows: list[str] = [str(payload.get("plain_text", "")), str(payload.get("style", ""))]
    rows.extend(str(row.get("id", "")).strip() for row in payload.get("updated_artifacts", []) or [] if isinstance(row, Mapping))
    rows.extend(str(row.get("id", "")).strip() for row in payload.get("affected_contracts", []) or [] if isinstance(row, Mapping))
    return conversation_common.meaningful_tokens(*rows)


def _signal_adds_new_information(*, signal: Mapping[str, Any], assist: Mapping[str, Any]) -> bool:
    if not signal.get("eligible"):
        return False
    if not assist.get("eligible"):
        return True
    assist_ref_ids = {
        str(row.get("id", "")).strip()
        for row in assist.get("updated_artifacts", []) or []
        if isinstance(row, Mapping) and str(row.get("id", "")).strip()
    }
    signal_ref_ids = {
        str(row.get("id", "")).strip()
        for row in signal.get("refs", []) or []
        if isinstance(row, Mapping) and str(row.get("id", "")).strip()
    }
    if signal_ref_ids and assist_ref_ids and signal_ref_ids.issubset(assist_ref_ids):
        if str(signal.get("kind", "")) in {"insight", "history"}:
            return False
    signal_tokens = _signal_information_tokens(signal)
    assist_tokens = _assist_information_tokens(assist)
    novel_tokens = signal_tokens - assist_tokens
    if str(signal.get("kind", "")) == "risks":
        return bool(novel_tokens) or str(signal.get("severity", "")).strip().lower() == "high"
    return len(novel_tokens) >= 2


def _suppressed_closeout_signal(payload: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    row = dict(payload)
    row["eligible"] = False
    row["text"] = ""
    row["plain_text"] = ""
    row["markdown_text"] = ""
    row["render_hint"] = "suppress"
    row["suppressed_reason"] = reason
    return row


def _suppressed_signal_payload(
    *,
    kind: str,
    metrics: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "eligible": False,
        "label": conversation_common.label(kind, markdown=False),
        "preferred_markdown_label": conversation_common.label(kind, markdown=True),
        "text": "",
        "plain_text": "",
        "markdown_text": "",
        "facts": [],
        "refs": [],
        "render_hint": "suppress",
        "confidence": "",
        "severity": "",
        "suppressed_reason": reason,
        "metrics": dict(metrics),
    }


def _signal_payload(
    *,
    kind: str,
    metrics: Mapping[str, Any],
    markdown_text: str,
    plain_text: str,
    facts: Sequence[str],
    refs: Sequence[Mapping[str, Any]],
    render_hint: str,
    confidence: str = "",
    severity: str = "",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "eligible": True,
        "label": conversation_common.label(kind, markdown=False),
        "preferred_markdown_label": conversation_common.label(kind, markdown=True),
        "text": markdown_text,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "facts": conversation_common.dedupe_strings(list(facts)),
        "refs": [dict(row) for row in refs],
        "render_hint": render_hint,
        "confidence": confidence,
        "severity": severity,
        "suppressed_reason": "",
        "metrics": dict(metrics),
    }


def _history_artifact_refs(
    *,
    request: Any,
    repo_root: Path | None,
    anchor_artifacts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    payload = conversation_common.request_context_payload(request)
    rows: list[dict[str, Any]] = []
    anchor_ids = {str(row.get("id", "")).strip() for row in anchor_artifacts}
    for key, value in conversation_common.recursive_items(payload):
        if not any(hint in key for hint in _HISTORY_KEY_HINTS):
            continue
        for token in conversation_common.recursive_strings(value):
            entity_id = _normalize_string(token)
            if entity_id in anchor_ids:
                continue
            if conversation_artifacts.is_workstream_id(entity_id):
                rows.append(conversation_artifacts.artifact_ref("workstream", entity_id))
            elif conversation_artifacts.is_bug_id(entity_id):
                rows.append(conversation_artifacts.artifact_ref("bug", entity_id))
            elif conversation_artifacts.is_diagram_id(entity_id):
                rows.append(conversation_artifacts.artifact_ref("diagram", entity_id))
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("kind")), str(row.get("id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:3]


def _tribunal_signal_refs(
    *,
    tribunal_context: Mapping[str, Any],
    anchor_artifacts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [dict(row) for row in anchor_artifacts[:2]]
    seen = {(str(row.get("kind")), str(row.get("id"))) for row in rows}
    for scope in tribunal_context.get("scope_signals", []) or []:
        if not isinstance(scope, Mapping):
            continue
        candidates = [
            *(scope.get("operator_readout", {}).get("proof_refs", []) if isinstance(scope.get("operator_readout"), Mapping) else []),
            *(scope.get("evidence_refs", []) if isinstance(scope.get("evidence_refs"), list) else []),
        ]
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            ref = conversation_artifacts.proof_ref_artifact(candidate)
            if ref is None:
                continue
            key = (str(ref.get("kind")), str(ref.get("id")))
            if key in seen:
                continue
            seen.add(key)
            rows.append(ref)
            if len(rows) >= 3:
                return rows
    return rows


def _risk_summary(request: Any, adoption: Mapping[str, Any]) -> tuple[list[str], str]:
    payload = conversation_common.request_context_payload(request)
    reasons: list[str] = []
    if bool(adoption.get("requires_widening")):
        reasons.append("the packet still wants widening")
    if bool(adoption.get("narrowing_required")):
        reasons.append("narrowing is still required")
    if bool(adoption.get("diagram_watch_gap_count")):
        reasons.append(conversation_common.count_phrase(int(adoption.get("diagram_watch_gap_count") or 0), "diagram watch gap"))
    for key, value in conversation_common.recursive_items(payload):
        if key in _RISK_BOOL_KEYS and bool(value):
            phrase = key.replace("_", " ")
            if phrase == "requires widening":
                phrase = "the packet still wants widening"
            elif phrase == "narrowing required":
                phrase = "narrowing is still required"
            reasons.append(phrase)
        if key in _RISK_COUNT_KEYS:
            try:
                count = int(value or 0)
            except (TypeError, ValueError):
                count = 0
            if count <= 0:
                continue
            if key == "validation_obligation_count":
                reasons.append(conversation_common.count_phrase(count, "validation obligation"))
            elif key == "diagram_watch_gap_count":
                reasons.append(conversation_common.count_phrase(count, "diagram watch gap"))
            elif key == "unresolved_question_count":
                reasons.append(conversation_common.count_phrase(count, "unresolved question"))
            elif key == "operator_consequence_count":
                reasons.append(conversation_common.count_phrase(count, "operator consequence"))
    reasons = conversation_common.dedupe_strings(reasons)
    severity = "high" if any("widening" in reason or "narrowing" in reason for reason in reasons) else "medium"
    return reasons, severity


def _compose_insight_signal(
    *,
    metrics: Mapping[str, Any],
    anchor_artifacts: Sequence[Mapping[str, Any]],
    tribunal_context: Mapping[str, Any],
) -> dict[str, Any]:
    systemic_brief = tribunal_context.get("systemic_brief", {})
    if not isinstance(systemic_brief, Mapping):
        systemic_brief = {}
    latent_causes = conversation_common.dedupe_strings([str(token) for token in systemic_brief.get("latent_causes", []) or []])
    if latent_causes and anchor_artifacts:
        refs = _tribunal_signal_refs(tribunal_context=tribunal_context, anchor_artifacts=anchor_artifacts)
        cause_phrase = conversation_common.join_items(latent_causes[:2])
        markdown_refs = conversation_common.join_items([str(row.get("markdown_ref", "")).strip() for row in refs[:2]])
        plain_refs = conversation_common.join_items([str(row.get("plain_ref", "")).strip() for row in refs[:2]])
        markdown_text = (
            f"{conversation_common.label('insight', markdown=True)} this is a delivery-proof problem: {cause_phrase}. "
            f"Keep {markdown_refs or 'the real anchors'} in frame before widening again."
        )
        plain_text = (
            f"{conversation_common.label('insight', markdown=False)} this is a delivery-proof problem: {cause_phrase}. "
            f"Keep {plain_refs or 'the real anchors'} in frame before widening again."
        )
        return _signal_payload(kind="insight", metrics=metrics, markdown_text=markdown_text, plain_text=plain_text, facts=latent_causes[:2], refs=refs[:2], render_hint="explicit_label", confidence="high")
    if not anchor_artifacts:
        return _suppressed_signal_payload(kind="insight", metrics=metrics, reason="no_anchor_artifacts")
    if metrics["governance_anchor_count"] <= 0 and metrics["focus_path_count"] <= 0:
        return _suppressed_signal_payload(kind="insight", metrics=metrics, reason="no_non_obvious_anchor")
    refs = list(anchor_artifacts[:2])
    markdown_refs = conversation_common.join_items([str(row.get("markdown_ref", "")).strip() for row in refs])
    plain_refs = conversation_common.join_items([str(row.get("plain_ref", "")).strip() for row in refs])
    facts = [
        "the key anchors were already present",
        "staying narrow changed the next move",
    ]
    if metrics["workstream_count"] > 0 and metrics["component_count"] > 0:
        markdown_text = (
            f"{conversation_common.label('insight', markdown=True)} the real work was already in {markdown_refs}, "
            "so widening here would have been theater."
        )
        plain_text = (
            f"{conversation_common.label('insight', markdown=False)} the real work was already in {plain_refs}, "
            "so widening here would have been theater."
        )
        return _signal_payload(
            kind="insight",
            metrics=metrics,
            markdown_text=markdown_text,
            plain_text=plain_text,
            facts=facts,
            refs=refs,
            render_hint="explicit_label",
            confidence="high",
        )
    markdown_text = (
        f"{conversation_common.label('insight', markdown=True)} the key anchors were already on the table, "
        "which is why this stayed smaller than it first looked."
    )
    plain_text = (
        f"{conversation_common.label('insight', markdown=False)} the key anchors were already on the table, "
        "which is why this stayed smaller than it first looked."
    )
    return _signal_payload(
        kind="insight",
        metrics=metrics,
        markdown_text=markdown_text,
        plain_text=plain_text,
        facts=facts,
        refs=refs,
        render_hint="ambient_inline",
        confidence="medium",
    )


def _compose_history_signal(
    *,
    metrics: Mapping[str, Any],
    history_refs: Sequence[Mapping[str, Any]],
    anchor_artifacts: Sequence[Mapping[str, Any]],
    tribunal_context: Mapping[str, Any],
) -> dict[str, Any]:
    if not history_refs:
        live_scope = next((row for row in tribunal_context.get("scope_signals", []) or [] if isinstance(row, Mapping) and row.get("case_refs")), None)
        if isinstance(live_scope, Mapping):
            refs = _tribunal_signal_refs(tribunal_context=tribunal_context, anchor_artifacts=anchor_artifacts)
            markdown_refs = conversation_common.join_items([str(row.get("markdown_ref", "")).strip() for row in refs[:2]])
            plain_refs = conversation_common.join_items([str(row.get("plain_ref", "")).strip() for row in refs[:2]])
            markdown_text = f"{conversation_common.label('history', markdown=True)} {markdown_refs or 'this slice'} already has an active case here, so treat the next move as a continuation, not a cold start."
            plain_text = f"{conversation_common.label('history', markdown=False)} {plain_refs or 'this slice'} already has an active case here, so treat the next move as a continuation, not a cold start."
            return _signal_payload(kind="history", metrics=metrics, markdown_text=markdown_text, plain_text=plain_text, facts=["a local case is linked to this scope"], refs=refs[:2], render_hint="explicit_label", confidence="medium")
    if not history_refs:
        return _suppressed_signal_payload(kind="history", metrics=metrics, reason="no_strong_prior")
    refs = list(history_refs[:2])
    markdown_refs = conversation_common.join_items([str(row.get("markdown_ref", "")).strip() for row in refs])
    plain_refs = conversation_common.join_items([str(row.get("plain_ref", "")).strip() for row in refs])
    facts = ["there is already history on this surface"]
    markdown_text = (
        f"{conversation_common.label('history', markdown=True)} this slice already has history in {markdown_refs}, "
        "so treat the next move as a continuation, not a cold start."
    )
    plain_text = (
        f"{conversation_common.label('history', markdown=False)} this slice already has history in {plain_refs}, "
        "so treat the next move as a continuation, not a cold start."
    )
    return _signal_payload(
        kind="history",
        metrics=metrics,
        markdown_text=markdown_text,
        plain_text=plain_text,
        facts=facts,
        refs=refs,
        render_hint="explicit_label",
        confidence="high",
    )


def _compose_risk_signal(
    *,
    request: Any,
    metrics: Mapping[str, Any],
    adoption: Mapping[str, Any],
    anchor_artifacts: Sequence[Mapping[str, Any]],
    tribunal_context: Mapping[str, Any],
) -> dict[str, Any]:
    tribunal_rows = [
        row for row in tribunal_context.get("scope_signals", []) or []
        if isinstance(row, Mapping)
        and operator_readout.scenario_priority(str(row.get("operator_readout", {}).get("primary_scenario", "")).strip()) < operator_readout.scenario_priority("clear_path")
    ]
    tribunal_rows.sort(
        key=lambda row: (
            operator_readout.scenario_priority(str(row.get("operator_readout", {}).get("primary_scenario", "")).strip()),
            operator_readout.severity_rank(str(row.get("operator_readout", {}).get("severity", "")).strip()),
        )
    )
    if tribunal_rows:
        scope = tribunal_rows[0]
        readout = dict(scope.get("operator_readout", {})) if isinstance(scope.get("operator_readout"), Mapping) else {}
        refs = _tribunal_signal_refs(tribunal_context=tribunal_context, anchor_artifacts=anchor_artifacts)
        scenario = str(operator_readout.humanize_operator_readout_token(readout.get("primary_scenario") or "clear_path") or "clear path").strip().lower()
        action = conversation_common.lower_sentence_start(str(readout.get("action", "")).strip())
        issue = str(readout.get("issue", "")).strip()
        body = action or issue or "do not let polish outrun proof"
        markdown_text = conversation_common.sentence_with_terminal_punctuation(
            f"{conversation_common.label('risks', markdown=True)} {scope.get('scope_label') or 'This slice'} is flagged for {scenario}, so {body}"
        )
        plain_text = conversation_common.sentence_with_terminal_punctuation(
            f"{conversation_common.label('risks', markdown=False)} {scope.get('scope_label') or 'This slice'} is flagged for {scenario}, so {body}"
        )
        return _signal_payload(kind="risks", metrics=metrics, markdown_text=markdown_text, plain_text=plain_text, facts=[issue or scenario, action], refs=refs[:2], render_hint="explicit_label", severity=str(readout.get('severity', '')).strip() or "watch")
    reasons, severity = _risk_summary(request, adoption)
    if not reasons:
        return _suppressed_signal_payload(kind="risks", metrics=metrics, reason="no_material_risk")
    risk_phrase = conversation_common.join_items(reasons[:3])
    refs = list(anchor_artifacts[:2])
    markdown_text = (
        f"{conversation_common.label('risks', markdown=True)} {risk_phrase}, so keep the next move grounded in evidence before polishing it."
    )
    plain_text = (
        f"{conversation_common.label('risks', markdown=False)} {risk_phrase}, so keep the next move grounded in evidence before polishing it."
    )
    return _signal_payload(
        kind="risks",
        metrics=metrics,
        markdown_text=markdown_text,
        plain_text=plain_text,
        facts=reasons,
        refs=refs,
        render_hint="explicit_label",
        severity=severity,
    )


def _claim_guard_from_tribunal_context(tribunal_context: Mapping[str, Any]) -> dict[str, Any]:
    for row in tribunal_context.get("scope_signals", []) if isinstance(tribunal_context.get("scope_signals"), list) else []:
        if not isinstance(row, Mapping):
            continue
        claim_guard = dict(row.get("claim_guard", {})) if isinstance(row.get("claim_guard"), Mapping) else {}
        if claim_guard:
            return claim_guard
    for row in tribunal_context.get("case_queue", []) if isinstance(tribunal_context.get("case_queue"), list) else []:
        if not isinstance(row, Mapping):
            continue
        claim_guard = dict(row.get("claim_guard", {})) if isinstance(row.get("claim_guard"), Mapping) else {}
        if claim_guard:
            return claim_guard
    return {}


def compose_conversation_bundle(
    *,
    request: Any,
    decision: Any,
    adoption: Mapping[str, Any],
    repo_root: Path | None = None,
    final_changed_paths: Sequence[str] | None = None,
    changed_path_source: str = "",
    turn_phase: str = "",
    assistant_summary: str = "",
) -> dict[str, Any]:
    context_payload = conversation_common.request_context_payload(request)
    metrics = conversation_metrics.evidence_metrics(request=request, decision=decision, adoption=adoption)
    context_rows = conversation_artifacts.context_artifact_rows(repo_root=repo_root, value=context_payload)
    anchor_artifacts = conversation_artifacts.request_anchor_artifacts(
        request=request,
        repo_root=repo_root,
        context_rows=context_rows,
    )
    history_refs = _history_artifact_refs(
        request=request,
        repo_root=repo_root,
        anchor_artifacts=anchor_artifacts,
    )
    tribunal_context = delivery_runtime.tribunal_context(
        context_payload=context_payload,
        repo_root=repo_root,
        anchor_artifacts=anchor_artifacts,
    )
    claim_guard = _claim_guard_from_tribunal_context(tribunal_context)
    claim_lint = proof_state.build_claim_lint(claim_guard)
    risks = claim_runtime.enforce_payload(
        _compose_risk_signal(
            request=request,
            metrics=metrics,
            adoption=adoption,
            anchor_artifacts=anchor_artifacts,
            tribunal_context=tribunal_context,
        ),
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface="chatter_risks",
    )
    insight = claim_runtime.enforce_payload(
        _compose_insight_signal(
            metrics=metrics,
            anchor_artifacts=anchor_artifacts,
            tribunal_context=tribunal_context,
        ),
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface="chatter_insight",
    )
    history = claim_runtime.enforce_payload(
        _compose_history_signal(
            metrics=metrics,
            history_refs=history_refs,
            anchor_artifacts=anchor_artifacts,
            tribunal_context=tribunal_context,
        ),
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface="chatter_history",
    )
    selected_signal = ""
    selected_signals: list[str] = []
    for key in _EXPLICIT_SIGNAL_PRIORITY:
        payload = {"risks": risks, "insight": insight, "history": history}[key]
        if payload["eligible"] and payload["render_hint"] == "explicit_label":
            selected_signals.append(key)
    if selected_signals:
        selected_signal = selected_signals[0]
    assist = claim_runtime.enforce_payload(
        compose_closeout_assist(
            request=request,
            decision=decision,
            adoption=adoption,
            repo_root=repo_root,
            final_changed_paths=final_changed_paths,
            changed_path_source=changed_path_source,
            metrics=metrics,
            context_rows=context_rows,
            assistant_summary=assistant_summary,
        ),
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface="chatter_assist",
    )
    closeout_signals = {
        "risks": dict(risks),
        "insight": dict(insight),
        "history": dict(history),
    }
    for payload in closeout_signals.values():
        if payload.get("eligible"):
            payload["render_hint"] = "supplemental_line"
    selected_supplemental = ""
    if assist.get("eligible"):
        if _normalize_token(assist.get("style")) == "visibility_continuity":
            for key, payload in closeout_signals.items():
                if payload.get("eligible"):
                    closeout_signals[key] = _suppressed_closeout_signal(payload, reason="visibility_continuity_assist_only")
        else:
            for key in _SUPPLEMENTAL_PRIORITY:
                payload = closeout_signals[key]
                if not payload["eligible"]:
                    continue
                if not _signal_adds_new_information(signal=payload, assist=assist):
                    closeout_signals[key] = _suppressed_closeout_signal(payload, reason="overlaps_assist")
                    continue
                if payload["eligible"]:
                    selected_supplemental = key
                    break
    else:
        for key, payload in closeout_signals.items():
            if payload.get("eligible"):
                closeout_signals[key] = _suppressed_closeout_signal(payload, reason="assist_suppressed")
    closeout_markdown_lines: list[str] = []
    closeout_plain_lines: list[str] = []
    if selected_supplemental:
        closeout_markdown_lines.append(closeout_signals[selected_supplemental]["markdown_text"])
        closeout_plain_lines.append(closeout_signals[selected_supplemental]["plain_text"])
    if assist.get("eligible"):
        closeout_markdown_lines.append(assist["markdown_text"])
        closeout_plain_lines.append(assist["plain_text"])
    claim_enforcement = claim_runtime.build_claim_enforcement_summary(
        claim_lint=claim_lint,
        ambient_payloads={"risks": risks, "insight": insight, "history": history},
        assist_payload=assist,
        supplemental_payload=closeout_signals.get(selected_supplemental, {}) if selected_supplemental else {},
    )
    intervention_bundle: dict[str, Any] = {}
    live_ambient_signals: dict[str, Any] = {}
    if repo_root is not None:
        effective_turn_phase = _normalize_token(turn_phase) or ("post_edit_checkpoint" if final_changed_paths else "prompt_submit")
        packet_summary = {}
        if getattr(request, "workstreams", None):
            packet_summary["workstreams"] = list(getattr(request, "workstreams", []))
        if getattr(request, "components", None):
            packet_summary["components"] = list(getattr(request, "components", []))
        if isinstance(getattr(request, "context_signals", {}), Mapping):
            context_packet = request.context_signals.get("context_packet")
            if isinstance(context_packet, Mapping):
                for key in ("bugs", "diagrams", "workstreams", "components"):
                    value = context_packet.get(key)
                    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                        packet_summary[key] = [str(item).strip() for item in value if str(item).strip()]
        context_packet_summary = conversation_common.nested_mapping(context_payload, "context_packet")
        execution_engine_summary = conversation_common.nested_mapping(context_payload, "execution_engine_summary")
        memory_summary = conversation_common.nested_mapping(context_payload, "memory_summary") or conversation_common.nested_mapping(context_payload, "memory_snapshot")
        visibility_summary = conversation_common.nested_mapping(context_payload, "visibility_summary") or conversation_common.nested_mapping(context_payload, "delivery_ledger")
        delivery_snapshot = conversation_common.nested_mapping(context_payload, "delivery_snapshot")
        live_bundle = conversation_surface.build_conversation_bundle(
            repo_root=Path(repo_root).expanduser().resolve(),
            observation={
                "host_family": (
                    str(getattr(request, "context_signals", {}).get("host_family", "")).strip()
                    if isinstance(getattr(request, "context_signals", {}), Mapping)
                    else ""
                ),
                "turn_phase": effective_turn_phase,
                "session_id": str(getattr(request, "session_id", "")).strip(),
                "prompt_excerpt": str(getattr(request, "prompt", "")).strip(),
                "assistant_summary": _normalize_string(assistant_summary)
                or str(closeout_signals.get(selected_supplemental, {}).get("plain_text", "")).strip(),
                "changed_paths": list(final_changed_paths or getattr(request, "candidate_paths", [])[:4]),
                "workstreams": getattr(request, "workstreams", []),
                "components": getattr(request, "components", []),
                "packet_summary": packet_summary,
                "context_packet_summary": context_packet_summary,
                "execution_engine_summary": execution_engine_summary,
                "memory_summary": memory_summary,
                "tribunal_summary": tribunal_context,
                "visibility_summary": visibility_summary,
                "delivery_snapshot": delivery_snapshot,
            },
        )
        intervention_bundle = dict(live_bundle.get("intervention_bundle", {}))
        live_ambient_signals = dict(live_bundle.get("ambient_signals", {}))

    return {
        "live_ambient_signals": live_ambient_signals,
        "ambient_signals": {
            "insight": insight,
            "history": history,
            "risks": risks,
            "claim_guard": claim_guard,
            "claim_lint": claim_lint,
            "claim_enforcement": claim_enforcement,
            "selected_signal": selected_signal,
            "selected_signals": selected_signals,
            "render_policy": {
                "ambient_by_default": True,
                "explicit_labels_rare": True,
                "one_signal_at_a_time": False,
                "max_signals_per_turn": 3,
                "dedupe_by_signal_kind": True,
                "dedupe_by_semantic_signature": True,
                "priority": list(_EXPLICIT_SIGNAL_PRIORITY),
                "claim_terms_require_lint": bool(claim_lint.get("blocked_terms")),
                "commentary_mode": str(metrics.get("commentary_mode", "")).strip(),
                "suppress_routing_receipts": bool(metrics.get("suppress_routing_receipts")),
                "surface_fast_lane": bool(metrics.get("surface_fast_lane")),
            },
        },
        "closeout_bundle": {
            "assist": assist,
            "insight": closeout_signals["insight"],
            "history": closeout_signals["history"],
            "risks": closeout_signals["risks"],
            "claim_guard": claim_guard,
            "claim_lint": claim_lint,
            "claim_enforcement": claim_enforcement,
            "selected_supplemental": selected_supplemental,
            "updated_artifacts": list(assist.get("updated_artifacts", [])),
            "plain_text": "\n".join(closeout_plain_lines),
            "markdown_text": "\n".join(closeout_markdown_lines),
            "render_policy": {
                "benchmark_safe": True,
                "ambient_by_default": True,
                "max_lines": 2,
                "supplemental_priority": list(_SUPPLEMENTAL_PRIORITY),
                "changed_path_source": assist.get("changed_path_source", ""),
                "claim_terms_require_lint": bool(claim_lint.get("blocked_terms")),
                "highest_truthful_claim": str(claim_lint.get("highest_truthful_claim", "")).strip(),
                "commentary_mode": str(metrics.get("commentary_mode", "")).strip(),
                "suppress_routing_receipts": bool(metrics.get("suppress_routing_receipts")),
                "surface_fast_lane": bool(metrics.get("surface_fast_lane")),
            },
        },
        "intervention_bundle": intervention_bundle,
    }

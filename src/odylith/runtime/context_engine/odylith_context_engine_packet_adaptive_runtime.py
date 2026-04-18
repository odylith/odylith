from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import odylith_context_engine_packet_architecture_runtime
from odylith.runtime.context_engine import odylith_context_engine_packet_runtime_bindings
from odylith.runtime.context_engine import odylith_context_engine_packet_session_runtime

def bind(host: Any) -> None:
    odylith_context_engine_packet_runtime_bindings.bind_packet_runtime(globals(), host)

def build_adaptive_coding_packet(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    intent: str = "",
    family_hint: str = "",
    workstream_hint: str = "",
    validation_command_hints: Sequence[str] = (),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    family = _normalize_family_hint(family_hint)
    attempts: list[dict[str, Any]] = []
    initial_source = "impact"
    retain_impact_internal_context = bool(
        family in _HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES
        or (
            str(workstream_hint or "").strip()
            and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
        )
    )
    impact_payload = build_impact_report(
        repo_root=root,
        changed_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=session_id,
        claimed_paths=claimed_paths,
        runtime_mode=runtime_mode,
        intent=intent,
        delivery_profile=_CODEX_HOT_PATH_PROFILE,
        family_hint=family_hint,
        workstream_hint=workstream_hint,
        validation_command_hints=validation_command_hints,
        retain_hot_path_internal_context=retain_impact_internal_context,
        skip_runtime_warmup=family == "guidance_behavior",
    )
    initial_trigger = _hot_path_auto_escalation_trigger(
        packet_kind="impact",
        family_hint=family_hint,
        payload=impact_payload,
    )
    attempts.append(
        {
            "stage": 1,
            "label": "compact_packet",
            "trigger": initial_trigger,
            "accepted": True,
            "route_ready": _hot_path_route_ready(impact_payload),
            "full_scan_recommended": _hot_path_full_scan_recommended(impact_payload),
            "routing_confidence": _hot_path_routing_confidence(impact_payload),
        }
    )
    should_escalate, reasons = _should_escalate_hot_path_to_session_brief(
        payload=impact_payload,
        family_hint=family_hint,
        workstream_hint=workstream_hint,
        validation_command_hints=validation_command_hints,
    )
    explicit_workstream_unresolved = bool(
        family == "explicit_workstream"
        and str(workstream_hint or "").strip()
        and str(_hot_path_workstream_selection(impact_payload).get("state", "")).strip() != "explicit"
    )
    if should_escalate and not explicit_workstream_unresolved:
        session_brief_payload = odylith_context_engine_packet_session_runtime.build_session_brief(
            repo_root=root,
            changed_paths=changed_paths,
            use_working_tree=use_working_tree,
            working_tree_scope="session" if str(working_tree_scope or "").strip() == "repo" else working_tree_scope,
            session_id=session_id,
            workstream=workstream_hint,
            intent=intent,
            claimed_paths=claimed_paths,
            runtime_mode=runtime_mode,
            delivery_profile=_CODEX_HOT_PATH_PROFILE,
            family_hint=family_hint,
            validation_command_hints=validation_command_hints,
            impact_override=impact_payload,
        )
        session_brief_accepted = _hot_path_packet_rank(session_brief_payload) >= _hot_path_packet_rank(impact_payload)
        attempts.append(
            {
                "stage": 2,
                "label": "expanded_context",
                "trigger": reasons[0] if reasons else initial_trigger,
                "accepted": session_brief_accepted,
                "route_ready": _hot_path_route_ready(session_brief_payload),
                "full_scan_recommended": _hot_path_full_scan_recommended(session_brief_payload),
                "routing_confidence": _hot_path_routing_confidence(session_brief_payload),
            }
        )
        payload = session_brief_payload if session_brief_accepted else impact_payload
        final_source = "session_brief" if session_brief_accepted else initial_source
        stage = "session_brief_rescue" if session_brief_accepted else "compact_success"
    else:
        if explicit_workstream_unresolved:
            reasons = _dedupe_strings([*reasons, "explicit_workstream_unresolved"])
        payload = impact_payload
        final_source = initial_source
        stage = "compact_success"
    current_trigger = _hot_path_auto_escalation_trigger(
        packet_kind=final_source,
        family_hint=family_hint,
        payload=payload,
    )
    architecture_rescue_applied = False
    if (
        current_trigger
        and family in _HOT_PATH_AUTO_ESCALATION_ARCHITECTURE_FAMILIES
        and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
    ):
        architecture_payload = odylith_context_engine_packet_architecture_runtime.build_architecture_audit(
            repo_root=root,
            changed_paths=changed_paths,
            use_working_tree=use_working_tree,
            working_tree_scope="session" if str(working_tree_scope or "").strip() == "repo" else working_tree_scope,
            session_id=session_id,
            claimed_paths=claimed_paths,
            runtime_mode=runtime_mode,
            detail_level="packet",
        )
        attempts.append(
            {
                "stage": 3,
                "label": "architecture_assist",
                "trigger": current_trigger,
                "accepted": bool(architecture_payload.get("resolved")),
                "route_ready": _hot_path_route_ready(payload),
                "full_scan_recommended": _hot_path_full_scan_recommended(payload),
                "routing_confidence": _hot_path_routing_confidence(payload),
            }
        )
        if bool(architecture_payload.get("resolved")):
            architecture_rescue_applied = True
            stage = "architecture_assist"
    current_trigger = _hot_path_auto_escalation_trigger(
        packet_kind=final_source,
        family_hint=family_hint,
        payload=payload,
    )
    if current_trigger and (
        not _hot_path_can_hold_local_narrowing_without_full_scan(
            family_hint=family_hint,
            payload=payload,
        )
        and (
        _hot_path_full_scan_recommended(payload)
        or (
            family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
            and not _hot_path_route_ready(payload)
            and not architecture_rescue_applied
        )
        )
    ):
        fallback_reason = _hot_path_full_scan_reason(payload) or "adaptive_full_scan_fallback"
        fallback_scan = _fallback_scan_payload(
            repo_root=root,
            reason=fallback_reason,
            query=str(intent or "").strip(),
            changed_paths=changed_paths,
            perform_scan=family not in _HOT_PATH_SUMMARY_ONLY_FALLBACK_FAMILIES,
            result_limit=8,
            delivery_profile=_CODEX_HOT_PATH_PROFILE,
        )
        attempts.append(
            {
                "stage": 4,
                "label": "full_scan_fallback",
                "trigger": current_trigger,
                "accepted": True,
                "route_ready": _hot_path_route_ready(payload),
                "full_scan_recommended": True,
                "routing_confidence": _hot_path_routing_confidence(payload),
            }
        )
        payload = _update_compact_hot_path_runtime_packet(
            packet_kind=final_source,
            payload=payload,
            full_scan_recommended=True,
            full_scan_reason=fallback_reason,
            fallback_scan=fallback_scan,
        )
        stage = "full_scan_fallback"
    adaptive_escalation = {
        "stage": stage,
        "initial_source": initial_source,
        "final_source": final_source,
        "auto_escalated": bool(should_escalate or architecture_rescue_applied or stage == "full_scan_fallback"),
        "reasons": _dedupe_strings([*reasons, initial_trigger, current_trigger]),
        "attempts": attempts,
    }
    if retain_impact_internal_context and final_source == "impact":
        payload = _update_compact_hot_path_runtime_packet(
            packet_kind="impact",
            payload=payload,
            retain_internal_context=False,
        )
    elif not _hot_path_payload_is_compact(payload):
        payload = _compact_hot_path_runtime_packet(
            packet_kind=final_source,
            payload=dict(payload),
        )
    selector_diagnostics = (
        dict(payload.pop("benchmark_selector_diagnostics", {}))
        if isinstance(payload.get("benchmark_selector_diagnostics"), Mapping)
        else {}
    )
    if selector_diagnostics:
        adaptive_escalation["benchmark_selector_diagnostics"] = selector_diagnostics
    return {
        "packet_source": final_source,
        "payload": payload,
        "adaptive_escalation": adaptive_escalation,
    }


def build_adaptive_coding_packet_reusing_daemon(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    intent: str = "",
    family_hint: str = "",
    workstream_hint: str = "",
    validation_command_hints: Sequence[str] = (),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    family = _normalize_family_hint(family_hint)
    attempts: list[dict[str, Any]] = []
    initial_source = "impact"
    retain_impact_internal_context = bool(
        family in _HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES
        or (
            str(workstream_hint or "").strip()
            and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
        )
    )
    impact_request = {
        "paths": [str(path).strip() for path in changed_paths if str(path).strip()],
        "use_working_tree": bool(use_working_tree),
        "working_tree_scope": str(working_tree_scope or "repo").strip() or "repo",
        "session_id": str(session_id or "").strip(),
        "claim_paths": [str(token).strip() for token in claimed_paths if str(token).strip()],
        "runtime_mode": str(runtime_mode or "auto").strip() or "auto",
        "intent": str(intent or "").strip(),
        "delivery_profile": _CODEX_HOT_PATH_PROFILE,
        "family_hint": str(family_hint or "").strip(),
        "workstream_hint": str(workstream_hint or "").strip(),
        "validation_command_hints": [str(token).strip() for token in validation_command_hints if str(token).strip()],
        "retain_hot_path_internal_context": retain_impact_internal_context,
    }
    impact_result = request_runtime_daemon(
        repo_root=root,
        command="impact",
        payload=impact_request,
    )
    if impact_result is None:
        adaptive = build_adaptive_coding_packet(
            repo_root=root,
            changed_paths=changed_paths,
            use_working_tree=use_working_tree,
            working_tree_scope=working_tree_scope,
            session_id=session_id,
            claimed_paths=claimed_paths,
            runtime_mode=runtime_mode,
            intent=intent,
            family_hint=family_hint,
            workstream_hint=workstream_hint,
            validation_command_hints=validation_command_hints,
        )
        adaptive["runtime_execution"] = _local_runtime_execution_summary(
            repo_root=root,
            command="impact",
            changed_paths=changed_paths,
            session_id=session_id,
            claimed_paths=claimed_paths,
            working_tree_scope=working_tree_scope,
        )
        return adaptive
    impact_payload, runtime_execution = impact_result
    any_daemon_reuse = bool(runtime_execution.get("workspace_daemon_reused"))
    initial_trigger = _hot_path_auto_escalation_trigger(
        packet_kind="impact",
        family_hint=family_hint,
        payload=impact_payload,
    )
    attempts.append(
        {
            "stage": 1,
            "label": "compact_packet",
            "trigger": initial_trigger,
            "accepted": True,
            "route_ready": _hot_path_route_ready(impact_payload),
            "full_scan_recommended": _hot_path_full_scan_recommended(impact_payload),
            "routing_confidence": _hot_path_routing_confidence(impact_payload),
        }
    )
    should_escalate, reasons = _should_escalate_hot_path_to_session_brief(
        payload=impact_payload,
        family_hint=family_hint,
        workstream_hint=workstream_hint,
        validation_command_hints=validation_command_hints,
    )
    explicit_workstream_unresolved = bool(
        family == "explicit_workstream"
        and str(workstream_hint or "").strip()
        and str(_hot_path_workstream_selection(impact_payload).get("state", "")).strip() != "explicit"
    )
    if should_escalate and not explicit_workstream_unresolved:
        session_scope = "session" if str(working_tree_scope or "").strip() == "repo" else str(working_tree_scope or "").strip()
        session_request = {
            "paths": [str(path).strip() for path in changed_paths if str(path).strip()],
            "use_working_tree": bool(use_working_tree),
            "working_tree_scope": session_scope or "session",
            "session_id": str(session_id or "").strip(),
            "workstream": str(workstream_hint or "").strip(),
            "intent": str(intent or "").strip(),
            "claim_paths": [str(token).strip() for token in claimed_paths if str(token).strip()],
            "runtime_mode": str(runtime_mode or "auto").strip() or "auto",
            "delivery_profile": _CODEX_HOT_PATH_PROFILE,
            "family_hint": str(family_hint or "").strip(),
            "validation_command_hints": [str(token).strip() for token in validation_command_hints if str(token).strip()],
        }
        session_result = request_runtime_daemon(
            repo_root=root,
            command="session-brief",
            payload=session_request,
        )
        if session_result is not None:
            session_brief_payload, session_runtime_execution = session_result
        else:
            session_brief_payload = odylith_context_engine_packet_session_runtime.build_session_brief(
                repo_root=root,
                changed_paths=changed_paths,
                use_working_tree=use_working_tree,
                working_tree_scope=session_scope or "session",
                session_id=session_id,
                workstream=workstream_hint,
                intent=intent,
                claimed_paths=claimed_paths,
                runtime_mode=runtime_mode,
                delivery_profile=_CODEX_HOT_PATH_PROFILE,
                family_hint=family_hint,
                validation_command_hints=validation_command_hints,
                impact_override=impact_payload,
            )
            session_runtime_execution = _local_runtime_execution_summary(
                repo_root=root,
                command="session-brief",
                changed_paths=changed_paths,
                session_id=session_id,
                claimed_paths=claimed_paths,
                working_tree_scope=session_scope or "session",
            )
        session_brief_accepted = _hot_path_packet_rank(session_brief_payload) >= _hot_path_packet_rank(impact_payload)
        attempts.append(
            {
                "stage": 2,
                "label": "expanded_context",
                "trigger": reasons[0] if reasons else initial_trigger,
                "accepted": session_brief_accepted,
                "route_ready": _hot_path_route_ready(session_brief_payload),
                "full_scan_recommended": _hot_path_full_scan_recommended(session_brief_payload),
                "routing_confidence": _hot_path_routing_confidence(session_brief_payload),
            }
        )
        payload = session_brief_payload if session_brief_accepted else impact_payload
        final_source = "session_brief" if session_brief_accepted else initial_source
        stage = "session_brief_rescue" if session_brief_accepted else "compact_success"
        if bool(session_runtime_execution.get("workspace_daemon_reused")):
            any_daemon_reuse = True
        if session_brief_accepted:
            runtime_execution = session_runtime_execution
    else:
        if explicit_workstream_unresolved:
            reasons = _dedupe_strings([*reasons, "explicit_workstream_unresolved"])
        payload = impact_payload
        final_source = initial_source
        stage = "compact_success"
    current_trigger = _hot_path_auto_escalation_trigger(
        packet_kind=final_source,
        family_hint=family_hint,
        payload=payload,
    )
    architecture_rescue_applied = False
    if (
        current_trigger
        and family in _HOT_PATH_AUTO_ESCALATION_ARCHITECTURE_FAMILIES
        and family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
    ):
        architecture_scope = "session" if str(working_tree_scope or "").strip() == "repo" else str(working_tree_scope or "").strip()
        architecture_request = {
            "paths": [str(path).strip() for path in changed_paths if str(path).strip()],
            "use_working_tree": bool(use_working_tree),
            "working_tree_scope": architecture_scope or "session",
            "session_id": str(session_id or "").strip(),
            "claim_paths": [str(token).strip() for token in claimed_paths if str(token).strip()],
            "runtime_mode": str(runtime_mode or "auto").strip() or "auto",
            "detail_level": "packet",
        }
        architecture_result = request_runtime_daemon(
            repo_root=root,
            command="architecture",
            payload=architecture_request,
        )
        if architecture_result is not None:
            architecture_payload, architecture_runtime_execution = architecture_result
        else:
            architecture_payload = odylith_context_engine_packet_architecture_runtime.build_architecture_audit(
                repo_root=root,
                changed_paths=changed_paths,
                use_working_tree=use_working_tree,
                working_tree_scope=architecture_scope or "session",
                session_id=session_id,
                claimed_paths=claimed_paths,
                runtime_mode=runtime_mode,
                detail_level="packet",
            )
            architecture_runtime_execution = _local_runtime_execution_summary(
                repo_root=root,
                command="architecture",
                changed_paths=changed_paths,
                session_id=session_id,
                claimed_paths=claimed_paths,
                working_tree_scope=architecture_scope or "session",
            )
        attempts.append(
            {
                "stage": 3,
                "label": "architecture_assist",
                "trigger": current_trigger,
                "accepted": bool(architecture_payload.get("resolved")),
                "route_ready": _hot_path_route_ready(payload),
                "full_scan_recommended": _hot_path_full_scan_recommended(payload),
                "routing_confidence": _hot_path_routing_confidence(payload),
            }
        )
        if bool(architecture_runtime_execution.get("workspace_daemon_reused")):
            any_daemon_reuse = True
        if bool(architecture_payload.get("resolved")):
            architecture_rescue_applied = True
            stage = "architecture_assist"
    current_trigger = _hot_path_auto_escalation_trigger(
        packet_kind=final_source,
        family_hint=family_hint,
        payload=payload,
    )
    if current_trigger and (
        not _hot_path_can_hold_local_narrowing_without_full_scan(
            family_hint=family_hint,
            payload=payload,
        )
        and (
        _hot_path_full_scan_recommended(payload)
        or (
            family not in _HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES
            and not _hot_path_route_ready(payload)
            and not architecture_rescue_applied
        )
        )
    ):
        fallback_reason = _hot_path_full_scan_reason(payload) or "adaptive_full_scan_fallback"
        fallback_scan = _fallback_scan_payload(
            repo_root=root,
            reason=fallback_reason,
            query=str(intent or "").strip(),
            changed_paths=changed_paths,
            perform_scan=family not in _HOT_PATH_SUMMARY_ONLY_FALLBACK_FAMILIES,
            result_limit=8,
            delivery_profile=_CODEX_HOT_PATH_PROFILE,
        )
        attempts.append(
            {
                "stage": 4,
                "label": "full_scan_fallback",
                "trigger": current_trigger,
                "accepted": True,
                "route_ready": _hot_path_route_ready(payload),
                "full_scan_recommended": True,
                "routing_confidence": _hot_path_routing_confidence(payload),
            }
        )
        payload = _update_compact_hot_path_runtime_packet(
            packet_kind=final_source,
            payload=payload,
            full_scan_recommended=True,
            full_scan_reason=fallback_reason,
            fallback_scan=fallback_scan,
        )
        stage = "full_scan_fallback"
    adaptive_escalation = {
        "stage": stage,
        "initial_source": initial_source,
        "final_source": final_source,
        "auto_escalated": bool(should_escalate or architecture_rescue_applied or stage == "full_scan_fallback"),
        "reasons": _dedupe_strings([*reasons, initial_trigger, current_trigger]),
        "attempts": attempts,
    }
    if retain_impact_internal_context and final_source == "impact":
        payload = _update_compact_hot_path_runtime_packet(
            packet_kind="impact",
            payload=payload,
            retain_internal_context=False,
        )
    elif not _hot_path_payload_is_compact(payload):
        payload = _compact_hot_path_runtime_packet(
            packet_kind=final_source,
            payload=dict(payload),
        )
    runtime_execution = dict(runtime_execution)
    runtime_execution["workspace_daemon_reused"] = bool(any_daemon_reuse)
    runtime_execution["mixed_local_fallback"] = bool(
        any_daemon_reuse and str(runtime_execution.get("source", "")).strip() != "workspace_daemon"
    )
    return {
        "packet_source": final_source,
        "payload": payload,
        "adaptive_escalation": adaptive_escalation,
        "runtime_execution": runtime_execution,
    }

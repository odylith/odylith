"""Subtask assembly helpers extracted from the subagent orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Sequence


def _host():
    from odylith.runtime.orchestration import subagent_orchestrator as host

    return host


def _slice_prompt(
    request: OrchestrationRequest,
    *,
    paths: Sequence[str],
    mode: OrchestrationMode,
    needs_write: bool,
    role: str,
    include_coordination: bool,
) -> str:
    host = _host()
    OrchestrationMode = host.OrchestrationMode

    scope = ", ".join(paths) if paths else "the grounded bounded scope"
    route_time = not include_coordination
    coordination_note = ""
    if include_coordination:
        coordination_note = {
            OrchestrationMode.PARALLEL_BATCH: "This slice is parallel-safe and disjoint from the other leaves.",
            OrchestrationMode.SERIAL_BATCH: "This slice is ordered; wait for its dependencies before integrating results.",
        }.get(mode, "Keep the work strictly bounded to this slice.")
    if not needs_write:
        body = f"Review only {scope} for this request: {request.prompt}"
        if coordination_note:
            body = f"{body} {coordination_note}"
        return f"{body} Do not edit files or speculate outside this scope."
    if role == "implementation":
        if route_time:
            return f"Implement only the bounded owned changes in {scope}. Do not edit files outside this scope."
        body = f"{request.prompt} Limit concrete implementation ownership to: {scope}."
        if coordination_note:
            body = f"{body} {coordination_note}"
        return f"{body} Do not edit files outside this scope."
    if role == "contract":
        if route_time:
            return f"Implement only the contract or schema-governed change in {scope}. Preserve compatibility."
        body = (
            f"Implement the contract or schema-governed slice in {scope}. "
            f"Preserve compatibility and reflect the intent of the main request: {request.prompt}"
        )
        return f"{body} {coordination_note}".strip()
    if role == "validation":
        body = f"Update focused validation coverage in {scope} for the bounded change already owned by the primary leaf."
        if coordination_note:
            body = f"{body} {coordination_note}"
        return f"{body} Do not edit runtime code outside this validation slice."
    if role == "docs":
        body = f"Update the documentation or operator guidance in {scope} so it accurately reflects the bounded change."
        if coordination_note:
            body = f"{body} {coordination_note}"
        return f"{body} Do not edit runtime code outside this documentation slice."
    if role == "governance":
        body = f"Refresh the governed artifacts, registry wiring, or Atlas diagrams in {scope} for the implemented change."
        if coordination_note:
            body = f"{body} {coordination_note}"
        return f"{body} Keep edits bounded to these governance surfaces."
    if route_time:
        return f"Handle only the bounded owned change in {scope}. Do not edit files outside this scope."
    body = f"{request.prompt} Handle only this bounded slice: {scope}."
    return f"{body} {coordination_note}".strip()


def _slice_deliverables(
    request: OrchestrationRequest,
    *,
    paths: Sequence[str],
    needs_write: bool,
    role: str,
) -> list[str]:
    scope = ", ".join(paths) if paths else "the bounded scope"
    if not needs_write:
        return [f"Provide findings only for {scope}"]
    if role == "validation":
        return [f"Update only {scope}", "Keep the focused validation green"]
    if role == "docs":
        return [f"Update only {scope}", "Reflect the implemented behavior accurately"]
    if role == "governance":
        return [f"Update only {scope}", "Refresh governed artifacts only for this slice"]
    if role == "contract":
        return [f"Update only {scope}", "Preserve compatibility for this contract-governed slice"]
    relevant_criteria = _relevant_acceptance_criteria(
        request.acceptance_criteria,
        paths=paths,
        all_paths=request.candidate_paths,
    )
    return [f"Update only {scope}", *relevant_criteria]


def _relevant_acceptance_criteria(
    criteria: Sequence[str],
    *,
    paths: Sequence[str],
    all_paths: Sequence[str] | None = None,
) -> list[str]:
    normalized_paths = [str(path).strip() for path in paths if str(path).strip()]
    if not criteria:
        return []
    if not normalized_paths:
        return [str(item).strip() for item in criteria if str(item).strip()][:3]

    path_specific: list[str] = []
    shared_guardrails: list[str] = []
    seen: set[str] = set()
    path_tokens: set[str] = set()
    comparison_paths = [str(path).strip() for path in (all_paths or normalized_paths) if str(path).strip()]
    basenames = [Path(path).name.lower() for path in comparison_paths]
    unique_basenames = {name for name in basenames if basenames.count(name) == 1}
    for path in normalized_paths:
        lowered = path.lower()
        path_tokens.add(lowered)
        basename = Path(path).name.lower()
        if basename in unique_basenames:
            path_tokens.add(basename)

    for raw in criteria:
        text = str(raw).strip()
        if not text:
            continue
        lowered = text.lower()
        if any(token and token in lowered for token in path_tokens):
            if text not in seen:
                path_specific.append(text)
                seen.add(text)
            continue
        if any(
            phrase in lowered
            for phrase in (
                "keep ",
                "preserve ",
                "compatible",
                "tests green",
                "validation",
                "no regress",
            )
        ):
            if text not in seen:
                shared_guardrails.append(text)
                seen.add(text)

    narrowed = path_specific[:2]
    if shared_guardrails:
        narrowed.extend(shared_guardrails[:1])
    if narrowed:
        return narrowed
    return [str(item).strip() for item in criteria if str(item).strip()][:2]


def _slice_owner(*, paths: Sequence[str], needs_write: bool) -> str:
    scope = ", ".join(paths) if paths else "the bounded scope"
    if not needs_write:
        return f"Own only the read-only analysis of {scope}; do not edit files outside that scope."
    return f"Own only {scope}; do not edit files outside that scope."


def _slice_goal(
    request: OrchestrationRequest,
    *,
    paths: Sequence[str],
    role: str,
    needs_write: bool,
) -> str:
    scope = ", ".join(paths) if paths else "the bounded scope"
    if not needs_write:
        return f"Produce the bounded analysis requested by the main prompt for {scope}."
    if role == "validation":
        return f"Deliver the focused validation updates for {scope} that prove the bounded implementation is safe."
    if role == "docs":
        return f"Align the documentation or operator guidance in {scope} with the implemented behavior."
    if role == "governance":
        return f"Refresh the governed artifacts in {scope} so traceability and policy stay accurate."
    if role == "contract":
        return f"Implement the contract-governed change in {scope} while preserving compatibility."
    return f"Implement the bounded portion of the main request in {scope}: {request.prompt}"


def _slice_expected_output(deliverables: Sequence[str]) -> str:
    if not deliverables:
        return "Hand back the bounded result for the owned scope."
    return "; ".join(deliverables)


def _termination_condition_for_leaf(
    *,
    subtask: SubtaskSlice,
    decision: leaf_router.RoutingDecision,
) -> str:
    if decision.close_after_result:
        close_rule = "Stop after the bounded handoff and let the main thread integrate the result, then close the agent."
    else:
        close_rule = "Stop after the bounded handoff and wait for explicit main-thread instructions."
    stale_rule = ""
    if decision.idle_timeout_minutes > 0 and decision.idle_timeout_action:
        stale_rule = (
            f" If the leaf remains `waiting on instruction` for {decision.idle_timeout_minutes} minutes or longer, "
            f"{decision.idle_timeout_action} and {decision.idle_timeout_escalation or 'resume locally'}."
        )
    return f"{decision.termination_expectation or close_rule}{stale_rule}"


def _prompt_contract_lines(subtask: SubtaskSlice) -> list[str]:
    return [
        "TASK CONTRACT",
        f"OWNER: {subtask.owner}",
        f"GOAL: {subtask.goal}",
        f"EXPECTED OUTPUT: {subtask.expected_output}",
        f"TERMINATION EXPECTATION: {subtask.termination_condition}",
    ]


def _spawn_task_message(subtask: SubtaskSlice, *, task_prompt: str) -> str:
    host = _host()
    _normalize_multiline_string = host._normalize_multiline_string
    leaf_router = host.leaf_router

    return leaf_router._build_host_message(  # noqa: SLF001
        subtask.route_runtime_banner_lines,
        subtask.prompt_contract_lines,
        ["TASK", _normalize_multiline_string(task_prompt)],
    )


def _completion_closeout_overrides(subtasks: Sequence[SubtaskSlice]) -> dict[str, Any]:
    delegated = [subtask for subtask in subtasks if subtask.route_close_agent_overrides]
    if not delegated:
        return {}
    reference = dict(delegated[0].route_close_agent_overrides)
    reference.update(
        {
            "id_source": "host_spawn_ledger",
            "close_all_delegated_leaves": True,
            "subtask_ids": [subtask.id for subtask in delegated],
            "completion_scope": "main_thread_work_complete",
        }
    )
    return reference


def _slice_task_kind(request: OrchestrationRequest, *, role: str) -> str:
    if not request.needs_write:
        return request.task_kind or "analysis"
    if role in {"validation", "docs", "governance"}:
        return "maintenance"
    if role == "contract" and request.task_kind not in {"feature_implementation", "implementation", "bugfix"}:
        return "implementation"
    return request.task_kind or "implementation"


def _slice_phase(request: OrchestrationRequest, *, role: str) -> str:
    if not request.needs_write:
        return request.phase or "analysis"
    if role in {"validation", "docs", "governance"}:
        return request.phase or "implementation"
    return request.phase or "implementation"


def _slice_correctness_critical(request: OrchestrationRequest, *, role: str) -> bool:
    if role in {"validation", "docs", "governance"}:
        return False
    return request.correctness_critical


def _slice_latency_sensitive(request: OrchestrationRequest, *, role: str) -> bool:
    if role in {"validation", "docs", "governance"}:
        return True
    return request.latency_sensitive


def _slice_accuracy_preference(request: OrchestrationRequest, *, role: str) -> str:
    if role in {"validation", "docs", "governance"}:
        return "accuracy"
    return request.accuracy_preference


def _slice_validation_commands(request: OrchestrationRequest, *, role: str) -> list[str]:
    if role in {"implementation", "contract", "validation", "mixed"}:
        return list(request.validation_commands)
    return []


def _build_subtasks(
    request: OrchestrationRequest,
    *,
    mode: OrchestrationMode,
    groups: Sequence[Sequence[str]],
) -> list[SubtaskSlice]:
    host = _host()
    OrchestrationMode = host.OrchestrationMode
    SubtaskSlice = host.SubtaskSlice
    _new_slice_id = host._new_slice_id
    _scope_role = host._scope_role
    _execution_group_kind = host._execution_group_kind

    ordered_groups = [list(group) for group in groups if group or request.prompt]
    subtasks: list[SubtaskSlice] = []
    planned_ids: list[tuple[str, str]] = []
    previous_id = ""
    for index, paths in enumerate(ordered_groups, start=1):
        slice_id = _new_slice_id(index)
        role = _scope_role(paths, needs_write=request.needs_write)
        execution_group_kind = _execution_group_kind(paths, needs_write=request.needs_write)
        dependency_ids: list[str] = []
        if mode is OrchestrationMode.SERIAL_BATCH and previous_id:
            dependency_ids = [previous_id]
        elif mode is OrchestrationMode.PARALLEL_BATCH and request.needs_write and execution_group_kind == "support":
            primary_ids = [planned_id for planned_id, group_kind in planned_ids if group_kind == "primary"]
            if primary_ids:
                dependency_ids = list(primary_ids)
            prior_support_id = next(
                (planned_id for planned_id, group_kind in reversed(planned_ids) if group_kind == "support"),
                "",
            )
            if prior_support_id and prior_support_id not in dependency_ids:
                dependency_ids.append(prior_support_id)
        previous_id = slice_id
        planned_ids.append((slice_id, execution_group_kind))
        deliverables = _slice_deliverables(request, paths=paths, needs_write=request.needs_write, role=role)
        subtasks.append(
            SubtaskSlice(
                id=slice_id,
                prompt=_slice_prompt(
                    request,
                    paths=paths,
                    mode=mode,
                    needs_write=request.needs_write,
                    role=role,
                    include_coordination=True,
                ),
                route_prompt=_slice_prompt(
                    request,
                    paths=paths,
                    mode=mode,
                    needs_write=request.needs_write,
                    role=role,
                    include_coordination=False,
                ),
                execution_group_kind=execution_group_kind,
                scope_role=role,
                task_kind=_slice_task_kind(request, role=role),
                phase=_slice_phase(request, role=role),
                correctness_critical=_slice_correctness_critical(request, role=role),
                latency_sensitive=_slice_latency_sensitive(request, role=role),
                accuracy_preference=_slice_accuracy_preference(request, role=role),
                owned_paths=list(paths) if request.needs_write else [],
                read_paths=list(paths) if not request.needs_write else list(paths),
                dependency_ids=dependency_ids,
                deliverables=deliverables,
                owner=_slice_owner(paths=paths, needs_write=request.needs_write),
                goal=_slice_goal(request, paths=paths, role=role, needs_write=request.needs_write),
                expected_output=_slice_expected_output(deliverables),
                validation_commands=_slice_validation_commands(request, role=role),
                merge_owner="main_thread",
                escalation_allowed=True,
            )
        )
    default_role = _scope_role(request.candidate_paths, needs_write=request.needs_write)
    deliverables = _slice_deliverables(
        request,
        paths=request.candidate_paths,
        needs_write=request.needs_write,
        role=default_role,
    )
    return subtasks or [
        SubtaskSlice(
            id=_new_slice_id(1),
            prompt=request.prompt,
            route_prompt=request.prompt,
            execution_group_kind=_execution_group_kind(request.candidate_paths, needs_write=request.needs_write),
            scope_role=default_role,
            task_kind=_slice_task_kind(request, role=default_role),
            phase=_slice_phase(request, role=default_role),
            correctness_critical=_slice_correctness_critical(request, role=default_role),
            latency_sensitive=_slice_latency_sensitive(request, role=default_role),
            accuracy_preference=_slice_accuracy_preference(request, role=default_role),
            owned_paths=list(request.candidate_paths) if request.needs_write else [],
            read_paths=list(request.candidate_paths),
            deliverables=deliverables,
            owner=_slice_owner(paths=request.candidate_paths, needs_write=request.needs_write),
            goal=_slice_goal(request, paths=request.candidate_paths, role=default_role, needs_write=request.needs_write),
            expected_output=_slice_expected_output(deliverables),
            validation_commands=_slice_validation_commands(request, role=default_role),
        )
    ]

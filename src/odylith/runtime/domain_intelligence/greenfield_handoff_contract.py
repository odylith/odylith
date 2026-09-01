"""Typed contracts for Greenfield implementation handoffs.

Canonical product meaning is already closed before these contracts are built.
This owner binds that meaning to implementation actions and stop policies with
explicit fields; validators never recover those obligations from prompt words.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string


PROJECT_HANDOFF_STEP_SCHEMA_VERSION = "odylith.greenfield.project-handoff-step.v1"
CODING_READINESS_SCHEMA_VERSION = "odylith.greenfield.coding-readiness.v1"

PROJECT_HANDOFF_STEP_SEQUENCE = (
    "choose_language",
    "create_plan",
    "build_slice",
    "prove_behavior",
    "refresh_governance",
)

_PROJECT_HANDOFF_REQUIRED_ACTIONS = {
    "choose_language": (
        "select_implementation_language",
        "record_runtime_assumptions",
        "define_test_approach",
        "record_tradeoffs",
    ),
    "create_plan": (
        "bind_first_release_work_item",
        "define_source_boundary",
        "name_target_files",
        "bind_proof_obligations",
        "list_validation_commands",
        "preserve_excluded_scope",
    ),
    "build_slice": (
        "bind_first_release_work_item",
        "restate_target_files",
        "build_accepted_first_path_only",
        "validate_inputs",
        "return_structured_result",
        "preserve_excluded_scope",
    ),
    "prove_behavior": (
        "bind_first_release_work_item",
        "prove_valid_input",
        "prove_missing_input",
        "prove_invalid_or_blocked_input",
        "prove_repeatability",
        "run_validation_commands",
        "stop_on_failed_validation",
    ),
    "refresh_governance": (
        "bind_first_release_work_item",
        "refresh_from_implemented_behavior",
        "cite_validation_results",
        "withhold_unproven_release_readiness",
    ),
}

_PROJECT_HANDOFF_STOP_POLICIES = {
    "choose_language": "decision_only_no_source_write",
    "create_plan": "plan_only_no_source_write",
    "build_slice": "bounded_slice_only",
    "prove_behavior": "fail_closed_on_validation",
    "refresh_governance": "no_unproven_release_readiness",
}

_PROOF_VALIDATION_CASES = (
    "valid_input",
    "missing_required_input",
    "invalid_or_blocked_input",
    "repeatability",
)

_CODING_READINESS_GATE_POLICIES = {
    "implementation_environment": "decide_before_source_plan",
    "source_boundary": "bind_before_source_edit",
    "scope_boundary": "preserve_exact_source_facts",
    "proof_boundary": "prove_before_governance_refresh",
}


def build_project_handoff_step_contract(
    *,
    step_id: str,
    project_title: str,
    accepted_first_path: str,
    first_release_workstream_refs: Sequence[str] = (),
    proof_boundary: str = "",
    visible_result: str = "",
    excluded_scope: Sequence[str] = (),
    component_refs: Sequence[str] = (),
    verification_commands: Sequence[str] = (),
) -> dict[str, Any]:
    """Bind one visible handoff step to explicit canonical facts and actions."""

    normalized_step = normalize_string(step_id)
    if normalized_step not in PROJECT_HANDOFF_STEP_SEQUENCE:
        raise ValueError(f"unsupported Greenfield handoff step: {normalized_step or '<empty>'}")
    title = _required_text(project_title, "project title")
    first_path = _required_text(accepted_first_path, "accepted first path")
    return {
        "schema_version": PROJECT_HANDOFF_STEP_SCHEMA_VERSION,
        "step_id": normalized_step,
        "semantic_authority": "typed_canonical_intent",
        "projection_policy": "structural_copy_only",
        "fact_bindings": {
            "project_title": title,
            "accepted_first_path": first_path,
            "first_release_workstream_refs": _normalized_strings(first_release_workstream_refs),
            "proof_boundary": _exact_text(proof_boundary),
            "visible_result": _exact_text(visible_result),
            "excluded_scope": _exact_strings(excluded_scope),
            "component_refs": _normalized_strings(component_refs),
            "verification_commands": _exact_strings(verification_commands),
        },
        "required_actions": list(_PROJECT_HANDOFF_REQUIRED_ACTIONS[normalized_step]),
        "validation_cases": (
            list(_PROOF_VALIDATION_CASES) if normalized_step == "prove_behavior" else []
        ),
        "stop_policy": _PROJECT_HANDOFF_STOP_POLICIES[normalized_step],
    }


def project_handoff_step_contract_issues(
    value: Any,
    *,
    expected_step_id: str,
) -> tuple[str, ...]:
    """Validate a handoff structurally without interpreting its visible prose."""

    if not isinstance(value, Mapping):
        return ("is missing its typed handoff contract",)
    expected = normalize_string(expected_step_id)
    if expected not in PROJECT_HANDOFF_STEP_SEQUENCE:
        return ("has an invalid expected handoff step",)
    issues: list[str] = []
    if normalize_string(value.get("schema_version")) != PROJECT_HANDOFF_STEP_SCHEMA_VERSION:
        issues.append("has an unsupported typed handoff contract version")
    if normalize_string(value.get("step_id")) != expected:
        issues.append("has a typed handoff step that does not match its sequence position")
    if normalize_string(value.get("semantic_authority")) != "typed_canonical_intent":
        issues.append("is not bound to typed canonical intent")
    if normalize_string(value.get("projection_policy")) != "structural_copy_only":
        issues.append("does not declare structural-only projection")
    bindings = value.get("fact_bindings")
    if not isinstance(bindings, Mapping):
        issues.append("is missing typed fact bindings")
        bindings = {}
    if not normalize_string(bindings.get("project_title")):
        issues.append("is missing its project-title binding")
    if not normalize_string(bindings.get("accepted_first_path")):
        issues.append("is missing its accepted-first-path binding")
    workstream_refs = _normalized_strings(bindings.get("first_release_workstream_refs"))
    if expected != "choose_language" and not workstream_refs:
        issues.append("is missing its first-release workstream binding")
    if expected == "prove_behavior" and not normalize_string(bindings.get("proof_boundary")):
        issues.append("is missing its proof-boundary binding")
    actions = _normalized_strings(value.get("required_actions"))
    if actions != _PROJECT_HANDOFF_REQUIRED_ACTIONS[expected]:
        issues.append("does not carry the exact required action contract")
    validation_cases = _normalized_strings(value.get("validation_cases"))
    expected_cases = _PROOF_VALIDATION_CASES if expected == "prove_behavior" else ()
    if validation_cases != expected_cases:
        issues.append("does not carry the exact validation-case contract")
    if normalize_string(value.get("stop_policy")) != _PROJECT_HANDOFF_STOP_POLICIES[expected]:
        issues.append("does not carry the required stop policy")
    return tuple(issues)


def build_coding_readiness_contract(
    *,
    workstream_id: str,
    workstream_title: str,
    release_selector: str,
    accepted_first_path: str,
    proof_boundary: str,
    evidence_requirements: Sequence[str] = (),
    operational_constraints: Sequence[str] = (),
    non_goals: Sequence[str] = (),
) -> dict[str, Any]:
    """Build the exact readiness decisions required before source work begins."""

    first_path = _required_text(accepted_first_path, "accepted first path")
    proof = _required_text(proof_boundary, "proof boundary")
    return {
        "schema_version": CODING_READINESS_SCHEMA_VERSION,
        "semantic_authority": "typed_canonical_intent",
        "projection_policy": "structural_copy_only",
        "implementation_target": {
            "workstream_id": normalize_string(workstream_id).upper(),
            "workstream_title": normalize_string(workstream_title),
            "release_selector": normalize_string(release_selector),
        },
        "source_facts": {
            "accepted_first_path": first_path,
            "proof_boundary": proof,
            "evidence_requirements": _exact_strings(evidence_requirements),
            "operational_constraints": _exact_strings(operational_constraints),
            "non_goals": _exact_strings(non_goals),
        },
        "gates": [
            {"gate_id": gate_id, "policy": policy}
            for gate_id, policy in _CODING_READINESS_GATE_POLICIES.items()
        ],
    }


def coding_readiness_contract_issues(
    value: Any,
    *,
    expected_workstream_id: str,
) -> tuple[str, ...]:
    """Validate readiness by field identity rather than prose or item count."""

    if not isinstance(value, Mapping):
        return ("operator next-steps preview is missing its typed coding-readiness contract",)
    issues: list[str] = []
    if normalize_string(value.get("schema_version")) != CODING_READINESS_SCHEMA_VERSION:
        issues.append("operator next-steps preview has an unsupported coding-readiness contract")
    if normalize_string(value.get("semantic_authority")) != "typed_canonical_intent":
        issues.append("operator next-steps readiness is not bound to typed canonical intent")
    if normalize_string(value.get("projection_policy")) != "structural_copy_only":
        issues.append("operator next-steps readiness does not declare structural-only projection")
    target = value.get("implementation_target")
    if not isinstance(target, Mapping):
        issues.append("operator next-steps readiness is missing its implementation target")
        target = {}
    expected_id = normalize_string(expected_workstream_id).upper()
    if normalize_string(target.get("workstream_id")).upper() != expected_id:
        issues.append("operator next-steps readiness drifted from the first implementation workstream")
    facts = value.get("source_facts")
    if not isinstance(facts, Mapping):
        issues.append("operator next-steps readiness is missing its source-fact bindings")
        facts = {}
    if not normalize_string(facts.get("accepted_first_path")):
        issues.append("operator next-steps readiness is missing the accepted first path")
    if not normalize_string(facts.get("proof_boundary")):
        issues.append("operator next-steps readiness is missing the proof boundary")
    gates = value.get("gates")
    gate_rows = (
        [row for row in gates if isinstance(row, Mapping)]
        if isinstance(gates, Sequence) and not isinstance(gates, (str, bytes))
        else []
    )
    actual_gate_policies = {
        normalize_string(row.get("gate_id")): normalize_string(row.get("policy"))
        for row in gate_rows
    }
    if actual_gate_policies != _CODING_READINESS_GATE_POLICIES:
        issues.append("operator next-steps readiness does not carry the exact gate contract")
    return tuple(issues)


def render_coding_readiness_gates(value: Mapping[str, Any]) -> list[str]:
    """Render human gates from an already validated structural contract."""

    issues = coding_readiness_contract_issues(
        value,
        expected_workstream_id=normalize_string(
            value.get("implementation_target", {}).get("workstream_id")
            if isinstance(value.get("implementation_target"), Mapping)
            else ""
        ),
    )
    if issues:
        raise ValueError("; ".join(issues))
    target = value["implementation_target"]
    facts = value["source_facts"]
    workstream_id = normalize_string(target.get("workstream_id"))
    workstream_title = normalize_string(target.get("workstream_title"))
    first_path = normalize_string(facts.get("accepted_first_path"))
    proof = normalize_string(facts.get("proof_boundary"))
    evidence = _exact_strings(facts.get("evidence_requirements"))
    constraints = _exact_strings(facts.get("operational_constraints"))
    non_goals = _exact_strings(facts.get("non_goals"))
    target_label = " ".join(value for value in (workstream_id, workstream_title) if value)
    scope_facts = [*constraints, *non_goals]
    evidence_clause = "; ".join(evidence) if evidence else "No additional evidence requirement was authored."
    scope_clause = (
        "; ".join(scope_facts)
        if scope_facts
        else "No operational constraint or excluded scope was authored."
    )
    return [
        "Choose and record the implementation language, runtime assumptions, dependency policy, and test toolchain before source planning.",
        f"Bind {target_label or 'the first implementation workstream'} to an explicit source boundary and target files while preserving the accepted first path exactly: {first_path}",
        f"Preserve the authored operating and scope boundary during planning and source edits: {scope_clause}",
        (
            "Require validation evidence before governed records refresh.\n"
            f"Authored proof boundary:\n{proof}\n"
            f"Evidence requirements:\n{evidence_clause}"
        ),
    ]


def _required_text(value: Any, label: str) -> str:
    text = _exact_text(value)
    if not text.strip():
        raise ValueError(f"Greenfield handoff contract requires {label}")
    return text


def _exact_text(value: Any) -> str:
    return value if isinstance(value, str) else str(value or "")


def _exact_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        rows = value
    else:
        rows = (value,)
    result: list[str] = []
    for row in rows:
        text = _exact_text(row)
        if text.strip() and text not in result:
            result.append(text)
    return tuple(result)


def _normalized_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        rows = value
    else:
        rows = (value,)
    result: list[str] = []
    for row in rows:
        text = normalize_string(row)
        if text and text not in result:
            result.append(text)
    return tuple(result)


__all__ = [
    "CODING_READINESS_SCHEMA_VERSION",
    "PROJECT_HANDOFF_STEP_SCHEMA_VERSION",
    "PROJECT_HANDOFF_STEP_SEQUENCE",
    "build_coding_readiness_contract",
    "build_project_handoff_step_contract",
    "coding_readiness_contract_issues",
    "project_handoff_step_contract_issues",
    "render_coding_readiness_gates",
]

"""Project component contracts directly from sealed Semantic Intent graph edges."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    require_semantic_intent_ir,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_identifiers import (
    semantic_artifact_identifier,
)


SEMANTIC_SYSTEM_POLICY_CUSTODY = "system_policy"
SEMANTIC_COMPONENT_CONTRACT_VERSION = (
    "odylith.greenfield.semantic-component-contract.v2"
)
_RELEASE_COMPONENT_SCOPES = frozenset({"first_path_required", "supporting"})


def semantic_evidence_tier(custody_state: str) -> str:
    """Map graph custody to the proposal evidence vocabulary without overclaiming."""

    return "user_intent" if custody_state == "source_fact" else "odylith_assumption"


def semantic_fact_custody_rows(
    facts: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Preserve exact graph custody on downstream meaning-bearing records."""

    return [
        {
            "fact_id": str(fact["fact_id"]),
            "custody_state": str(fact["custody"]),
        }
        for fact in sorted(
            facts,
            key=lambda row: (
                str(row["kind"]),
                int(row["order"]),
                str(row["fact_id"]),
            ),
        )
    ]


def semantic_component_rows_from_authority(
    authority: Any,
    *,
    project_slug: str,
) -> list[dict[str, Any]]:
    """Return complete component rows without interpreting system prose."""

    if not isinstance(authority, Mapping) or authority.get("origin") != "verified_semantic_intent_packet":
        raise ValueError("ProductCreateTransaction authority lacks Semantic Intent custody")
    evidence_sources = authority.get("evidence_sources")
    if not isinstance(evidence_sources, Mapping):
        raise ValueError("ProductCreateTransaction authority lacks Semantic Intent custody")
    semantic_intent = require_semantic_intent_ir(
        authority.get("semantic_intent"),
        evidence_sources=evidence_sources,
    )
    return semantic_component_rows(semantic_intent, project_slug=project_slug)


def semantic_component_rows(
    semantic_intent: Mapping[str, Any],
    *,
    project_slug: str,
) -> list[dict[str, Any]]:
    """Project typed systems and implementation edges into governance components."""

    facts = list(semantic_intent.get("facts", ()))
    relations = list(semantic_intent.get("relations", ()))
    by_id = {str(row["fact_id"]): row for row in facts}
    systems = sorted(
        (
            row
            for row in facts
            if row.get("kind") == "internal_system"
            and _attributes(row).get("release_scope") in _RELEASE_COMPONENT_SCOPES
        ),
        key=lambda row: int(row["order"]),
    )
    dependencies = _relation_targets(relations, kind="depends_on")
    implementations = _relation_targets(relations, kind="implements")
    constraints = _relation_targets(relations, kind="constrained_by")
    exclusions = _relation_targets(relations, kind="excludes")
    downstream = _downstream_systems(systems, dependencies)
    _require_release_implementation_coverage(
        facts=facts,
        systems=systems,
        implementations=implementations,
    )
    rows: list[dict[str, Any]] = []
    for system in systems:
        system_id = str(system["fact_id"])
        attributes = _attributes(system)
        implemented = tuple(
            by_id[target]
            for target in implementations.get(system_id, ())
            if target in by_id
        )
        steps = _implemented_facts(implemented, "workflow_step")
        direct_states = _implemented_facts(implemented, "state_object")
        direct_outputs = _implemented_facts(implemented, "visible_output")
        workflow_fact_ids = tuple(str(row["fact_id"]) for row in steps)
        workflow_labels = tuple(str(row["label"]) for row in steps)
        state_labels = tuple(str(row["label"]) for row in direct_states)
        output_labels = tuple(str(row["label"]) for row in direct_outputs)
        transition_labels = tuple(_state_label(row) for row in direct_states)
        dependency_labels = _ordered_unique(
            str(by_id[target]["label"])
            for target in dependencies.get(system_id, ())
            if target in by_id
        )
        dependency_input_labels = _ordered_unique(
            _dependency_input_label(by_id[target])
            for target in dependencies.get(system_id, ())
            if target in by_id
        )
        downstream_labels = tuple(
            str(by_id[target]["label"])
            for target in downstream.get(system_id, ())
            if target in by_id
        )
        label = str(system["label"])
        output_identity = {value.casefold() for value in output_labels}
        input_labels = _ordered_unique(
            _attributes(step).get("object", "")
            for step in steps
            if _attributes(step).get("object", "").casefold() not in output_identity
        )
        component_id = semantic_artifact_identifier(
            label,
            fallback=f"component-{len(rows) + 1}",
        )
        accepted_inputs = _sentence_list(
            input_labels + dependency_input_labels,
            fallback="Source-cited workflow facts",
        )
        result_labels = output_labels or state_labels or workflow_labels
        has_result = bool(result_labels)
        if attributes["release_scope"] == "first_path_required" and not has_result:
            raise ValueError(
                f"first-path semantic component `{label}` lacks an implemented result fact"
            )
        produced = (
            _sentence_list(
                (*output_labels, *transition_labels) or result_labels,
                fallback="",
            )
            if has_result
            else ""
        )
        boundary_interfaces = _boundary_interfaces(
            system_id=system_id,
            label=label,
            by_id=by_id,
            dependencies=dependencies,
            constraints=constraints,
            exclusions=exclusions,
            downstream=downstream,
        )
        upstream = _sentence_list(
            dependency_labels,
            fallback="Source-cited operator intent",
        )
        consumers = _sentence_list(downstream_labels, fallback="Release review")
        proof = attributes["proof"]
        proof_obligations = [proof]
        if has_result:
            proof_obligations.append(
                f"Blocked-path proof for {label}: reject invalid {accepted_inputs} before producing {produced}."
            )
        else:
            if attributes["release_scope"] != "supporting" or not boundary_interfaces:
                raise ValueError(
                    f"resultless semantic component `{label}` lacks a typed supporting boundary"
                )
            proof_obligations.append(
                f"Verify the typed boundary relations for {label}: "
                f"{_sentence_list(boundary_interfaces, fallback='')}."
            )
        if state_labels:
            proof_obligations.append(
                f"Reconstruct {_sentence_list(state_labels, fallback='')} and verify "
                f"{_sentence_list(output_labels or result_labels, fallback='')} from exact typed facts."
            )
        interfaces = (
            _interfaces(
                accepted_inputs=accepted_inputs,
                result_summary=produced,
                steps=steps,
            )
            if has_result
            else list(boundary_interfaces)
        )
        contract = {
            "schema_version": SEMANTIC_COMPONENT_CONTRACT_VERSION,
            "workflow_fact_ids": list(workflow_fact_ids),
            "workflow_labels": list(workflow_labels),
            "state_objects": list(state_labels),
            "visible_outputs": list(output_labels),
            "accepted_inputs": accepted_inputs,
            "upstream_truth": upstream,
            "downstream_consumers": consumers,
            "outside_boundary": attributes["outside_boundary"],
            "local_proof": proof_obligations,
            "unique_failure": attributes["risk"],
        }
        rows.append(
            {
                "component_id": component_id,
                "label": label,
                "kind": attributes["component_kind"],
                "intended_path": f"src/{project_slug}/{component_id.replace('-', '_')}",
                "responsibility": attributes["responsibility"],
                "boundary": attributes["boundary"],
                "result_summary": produced,
                "dependencies": [f"Depends on {value}." for value in dependency_labels],
                "interfaces": interfaces,
                "validation": proof_obligations,
                "risks": semantic_safety_risks(label, domain_risk=attributes["risk"]),
                "status": "planned",
                "qualification": "candidate",
                "custody_state": str(system["custody"]),
                "evidence_tier": semantic_evidence_tier(str(system["custody"])),
                "release_scope": attributes["release_scope"],
                "source_system_description": str(system["statement"]),
                "semantic_fact_id": system_id,
                "semantic_implements": [str(row["fact_id"]) for row in implemented],
                "semantic_fact_custody": semantic_fact_custody_rows((system, *implemented)),
                "component_contract": contract,
            }
        )
    return rows


def _require_release_implementation_coverage(
    *,
    facts: Sequence[Mapping[str, Any]],
    systems: Sequence[Mapping[str, Any]],
    implementations: Mapping[str, tuple[str, ...]],
) -> None:
    required_targets = {
        str(fact["fact_id"])
        for fact in facts
        if fact.get("kind") in {"workflow_step", "state_object", "visible_output"}
    }
    release_targets = {
        target
        for system in systems
        for target in implementations.get(str(system["fact_id"]), ())
    }
    missing = sorted(required_targets - release_targets)
    if missing:
        raise ValueError(
            "verified semantic release defers required workflow or visible-output ownership: "
            + ", ".join(missing)
        )


def semantic_safety_risks(subject: str, *, domain_risk: str) -> list[str]:
    """Attach fixed release-safety invariants without inferring domain meaning."""

    return [
        f"Delivery risk: {domain_risk}",
        f"Security posture: {subject} must enforce authorization, access control, credential isolation, and safe failure handling.",
        f"Policy and privacy posture: {subject} must preserve applicable policy, privacy, accessibility, retention, and safety evidence.",
    ]


def _relation_targets(
    relations: Sequence[Mapping[str, Any]],
    *,
    kind: str,
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[tuple[int, str]]] = {}
    for relation in relations:
        if relation.get("kind") != kind:
            continue
        grouped.setdefault(str(relation["subject_id"]), []).append(
            (int(relation["order"]), str(relation["object_id"]))
        )
    return {
        subject: tuple(target for _, target in sorted(values))
        for subject, values in grouped.items()
    }


def _downstream_systems(
    systems: Sequence[Mapping[str, Any]],
    dependencies: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    system_ids = {str(row["fact_id"]) for row in systems}
    result: dict[str, list[str]] = {}
    for consumer, targets in dependencies.items():
        if consumer not in system_ids:
            continue
        for target in targets:
            if target in system_ids:
                result.setdefault(target, []).append(consumer)
    return {key: tuple(value) for key, value in result.items()}


def _boundary_interfaces(
    *,
    system_id: str,
    label: str,
    by_id: Mapping[str, Mapping[str, Any]],
    dependencies: Mapping[str, tuple[str, ...]],
    constraints: Mapping[str, tuple[str, ...]],
    exclusions: Mapping[str, tuple[str, ...]],
    downstream: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Render exact typed boundary edges without inventing a result."""

    lines = [
        *(
            f"{by_id[target]['label']} depends on {label}"
            for target in downstream.get(system_id, ())
            if target in by_id
        ),
        *(
            f"{label} depends on {by_id[target]['label']}"
            for target in dependencies.get(system_id, ())
            if target in by_id
        ),
        *(
            f"{label} is constrained by {by_id[target]['label']}"
            for target in constraints.get(system_id, ())
            if target in by_id
        ),
        *(
            f"{label} excludes {by_id[target]['label']}"
            for target in exclusions.get(system_id, ())
            if target in by_id
        ),
    ]
    return _ordered_unique(lines)


def _state_label(fact: Mapping[str, Any]) -> str:
    attributes = _attributes(fact)
    before = attributes.get("from_state", "")
    after = attributes.get("to_state", "")
    label = str(fact["label"])
    return f"{label}: {before} to {after}" if before and after else label


def _implemented_facts(
    facts: Sequence[Mapping[str, Any]],
    kind: str,
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        sorted(
            (row for row in facts if row.get("kind") == kind),
            key=lambda row: (int(row["order"]), str(row["fact_id"])),
        )
    )


def _interfaces(
    *,
    accepted_inputs: str,
    result_summary: str,
    steps: Sequence[Mapping[str, Any]],
) -> list[str]:
    interfaces = [f"Accepts {accepted_inputs}.", f"Produces {result_summary}."]
    interfaces.extend(
        f"Implements {str(step['statement']).rstrip('.')}."
        for step in steps
    )
    return interfaces


def _dependency_input_label(fact: Mapping[str, Any]) -> str:
    label = str(fact["label"])
    if fact.get("kind") == "internal_system":
        return f"accepted result from {label}"
    return label


def _attributes(fact: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(row["name"]): str(row["value"]).strip()
        for row in fact.get("attributes", ())
        if isinstance(row, Mapping)
    }


def _ordered_unique(values: Sequence[str] | Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip(" .")
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _sentence_list(values: Sequence[str], *, fallback: str) -> str:
    cleaned = _ordered_unique(values)
    if not cleaned:
        return fallback
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


__all__ = [
    "SEMANTIC_SYSTEM_POLICY_CUSTODY",
    "SEMANTIC_COMPONENT_CONTRACT_VERSION",
    "semantic_component_rows",
    "semantic_component_rows_from_authority",
    "semantic_evidence_tier",
    "semantic_fact_custody_rows",
    "semantic_safety_risks",
]

"""Project one explicit implementation policy from sealed Semantic Intent facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    require_semantic_intent_ir,
    semantic_state_transition,
    semantic_state_transition_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_identifiers import (
    semantic_artifact_identifier,
)


SEMANTIC_SYSTEM_POLICY_CUSTODY = "system_policy"
SEMANTIC_COMPONENT_CONTRACT_VERSION = (
    "odylith.greenfield.semantic-component-contract.v9"
)
_IMPLEMENTATION_POLICY_ID = "implementation-policy.0"


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
    """Return component policy without adding it to Semantic Intent authority."""

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
    """Project one explicit implementation policy outside canonical meaning."""

    facts = list(semantic_intent.get("facts", ()))
    relations = list(semantic_intent.get("relations", ()))
    by_id = {str(row["fact_id"]): row for row in facts}
    steps = _facts_of_kind(facts, "workflow_step")
    states = _facts_of_kind(facts, "state_object")
    outputs = _facts_of_kind(facts, "visible_output")
    if not steps or not outputs:
        raise ValueError(
            "verified semantic projection requires workflow and visible-output facts"
        )
    input_entities = _relation_targets(relations, kind="input_entity")
    target_entities = _relation_targets(relations, kind="target_entity")
    produced_entities = _created_or_produced_entities_by_step(relations)
    accepted_entity_rows = _accepted_entity_rows(
        steps=steps,
        by_id=by_id,
        input_entities=input_entities,
        target_entities=target_entities,
        produced_entities=produced_entities,
    )
    state_entity_rows = _effect_entity_rows(states, by_id=by_id)
    output_entity_rows = _effect_entity_rows(outputs, by_id=by_id)
    workflow_fact_ids = tuple(str(row["fact_id"]) for row in steps)
    state_fact_ids = tuple(str(row["fact_id"]) for row in states)
    output_fact_ids = tuple(str(row["fact_id"]) for row in outputs)
    covered_fact_ids = (*workflow_fact_ids, *state_fact_ids, *output_fact_ids)
    workflow_labels = tuple(str(row["label"]) for row in steps)
    state_labels = tuple(str(row["label"]) for row in states)
    output_labels = tuple(str(row["label"]) for row in outputs)
    transition_labels = tuple(_state_label(row) for row in states)
    dependencies = _facts_of_kind(facts, "external_system")
    dependency_labels = _ordered_unique(str(row["label"]) for row in dependencies)
    accepted_inputs = _sentence_list(
        (*_entity_labels(accepted_entity_rows), *dependency_labels),
        fallback="Source-cited workflow facts",
    )
    result_summary = _sentence_list(
        (*output_labels, *transition_labels),
        fallback=_sentence_list(workflow_labels, fallback=""),
    )
    presentation = semantic_intent.get("presentation")
    if not isinstance(presentation, Mapping):
        raise ValueError("verified semantic projection lacks presentation metadata")
    title = str(presentation["title"])
    label = f"{title} First Path"
    component_id = semantic_artifact_identifier(
        f"{project_slug}-first-path",
        fallback="greenfield-first-path",
    )
    responsibility = (
        "Deliver the sealed first-path workflow: "
        f"{_sentence_list(workflow_labels, fallback='')}."
    )
    boundary = "Own only the covered workflow steps and their declared effects."
    outside_boundary = "Meaning not present in the sealed Semantic Intent graph."
    proof = "Prove every covered workflow step and declared effect from exact typed facts."
    risk = "Implementation could diverge from the sealed Semantic Intent graph."
    proof_obligations = [proof]
    if state_labels:
        proof_obligations.append(
            f"{_sentence_list((_state_proof(row) for row in states), fallback='')} "
            f"and verify {_sentence_list(output_labels, fallback='')} from exact typed facts."
        )
    projection_basis_fact_ids = tuple(str(row["fact_id"]) for row in facts)
    projection_basis_custody = semantic_fact_custody_rows(facts)
    product_boundaries = _facts_of_kind(facts, "product_boundary")
    contract = {
        "schema_version": SEMANTIC_COMPONENT_CONTRACT_VERSION,
        "implementation_policy_id": _IMPLEMENTATION_POLICY_ID,
        "component_role": "result_implementing",
        "covered_fact_ids": list(covered_fact_ids),
        "projection_basis_fact_ids": list(projection_basis_fact_ids),
        "workflow_fact_ids": list(workflow_fact_ids),
        "workflow_labels": list(workflow_labels),
        "state_objects": list(state_labels),
        "visible_outputs": list(output_labels),
        "accepted_input_entities": accepted_entity_rows,
        "accepted_inputs": accepted_inputs,
        "state_entities": state_entity_rows,
        "visible_output_entities": output_entity_rows,
        "product_boundaries": [str(row["statement"]) for row in product_boundaries],
        "upstream_truth": _sentence_list(
            dependency_labels,
            fallback="Source-cited operator intent",
        ),
        "downstream_consumers": "Release review",
        "outside_boundary": outside_boundary,
        "local_proof": proof_obligations,
        "unique_failure": risk,
    }
    return [
        {
            "component_id": component_id,
            "implementation_policy_id": _IMPLEMENTATION_POLICY_ID,
            "label": label,
            "kind": "service",
            "intended_path": f"src/{project_slug}/{component_id.replace('-', '_')}",
            "responsibility": responsibility,
            "boundary": boundary,
            "result_summary": result_summary,
            "dependencies": [f"Depends on {value}." for value in dependency_labels],
            "interfaces": _interfaces(
                accepted_inputs=accepted_inputs,
                result_summary=result_summary,
                steps=steps,
            ),
            "validation": proof_obligations,
            "risks": semantic_delivery_risks(domain_risk=risk),
            "status": "planned",
            "qualification": "candidate",
            "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
            "evidence_tier": semantic_evidence_tier(
                SEMANTIC_SYSTEM_POLICY_CUSTODY
            ),
            "release_scope": "first_path_required",
            "component_role": "result_implementing",
            "covered_fact_ids": list(covered_fact_ids),
            "projection_basis_fact_ids": list(projection_basis_fact_ids),
            "projection_basis_custody": projection_basis_custody,
            "component_contract": contract,
        }
    ]


def semantic_delivery_risks(*, domain_risk: str) -> list[str]:
    """Return the explicit risk carried by the plan-local component policy."""

    risk = str(domain_risk or "").strip()
    if not risk:
        raise ValueError("semantic component lacks its typed delivery risk")
    return [risk]


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


def _created_or_produced_entities_by_step(
    relations: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[str, ...]]:
    """Resolve internal entity identity through exact creation and output paths."""

    outputs_by_step = _relation_targets(relations, kind="produces")
    entities_by_output = _relation_targets(relations, kind="output_of")
    result: dict[str, tuple[str, ...]] = dict(
        _relation_targets(relations, kind="creates")
    )
    for step_id, output_ids in outputs_by_step.items():
        result[step_id] = tuple(
            (
                *result.get(step_id, ()),
                *(
            entity_id
                    for output_id in output_ids
                    for entity_id in entities_by_output.get(output_id, ())
                ),
            )
        )
    return result


def _accepted_entity_rows(
    *,
    steps: Sequence[Mapping[str, Any]],
    by_id: Mapping[str, Mapping[str, Any]],
    input_entities: Mapping[str, tuple[str, ...]],
    target_entities: Mapping[str, tuple[str, ...]],
    produced_entities: Mapping[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Project component inputs by entity id, never by matching labels."""

    rows: dict[str, dict[str, Any]] = {}
    produced_before_step: set[str] = set()
    for step in steps:
        step_id = str(step["fact_id"])
        for role, bindings in (
            ("input", input_entities.get(step_id, ())),
            ("target", target_entities.get(step_id, ())),
        ):
            for entity_id in bindings:
                if entity_id in produced_before_step:
                    continue
                entity = by_id.get(entity_id)
                if entity is None or entity.get("kind") != "entity":
                    raise ValueError(
                        f"workflow step `{step_id}` has a dangling typed entity binding"
                    )
                row = rows.setdefault(
                    entity_id,
                    {
                        "entity_id": entity_id,
                        "label": str(entity["label"]),
                        "roles": [],
                    },
                )
                if role not in row["roles"]:
                    row["roles"].append(role)
        produced_before_step.update(produced_entities.get(step_id, ()))
    return list(rows.values())


def _effect_entity_rows(
    effects: Sequence[Mapping[str, Any]],
    *,
    by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Bind each state or output effect to its canonical entity fact."""

    result: list[dict[str, str]] = []
    for effect in effects:
        entity_id = _attributes(effect).get("entity_id", "")
        entity = by_id.get(entity_id)
        if entity is None or entity.get("kind") != "entity":
            raise ValueError(
                f"semantic effect `{effect['fact_id']}` lacks canonical entity custody"
            )
        result.append(
            {
                "effect_fact_id": str(effect["fact_id"]),
                "entity_id": entity_id,
                "label": str(entity["label"]),
            }
        )
    return result


def _entity_labels(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Disambiguate equal display labels without collapsing distinct entity ids."""

    counts: dict[str, int] = {}
    for row in rows:
        label = str(row["label"])
        counts[label] = counts.get(label, 0) + 1
    return tuple(
        (
            f"{row['label']} [{row['entity_id']}]"
            if counts[str(row["label"])] > 1
            else str(row["label"])
        )
        for row in rows
    )


def _state_label(fact: Mapping[str, Any]) -> str:
    transition = semantic_state_transition(fact)
    label = str(fact["label"])
    if transition is None:
        return label
    return f"{label}: {semantic_state_transition_phrase(fact)}"


def _state_proof(fact: Mapping[str, Any]) -> str:
    transition = semantic_state_transition(fact)
    if transition is None:
        return f"Verify {str(fact['label']).strip()}"
    return f"Reconstruct {_state_label(fact)}"


def _facts_of_kind(
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
        f"Covers the “{str(step['label']).strip()}” workflow step."
        for step in steps
    )
    return interfaces


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
    "semantic_delivery_risks",
]

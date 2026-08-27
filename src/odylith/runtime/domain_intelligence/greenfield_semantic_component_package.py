"""Render Registry artifacts directly from verified Semantic Intent components."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import datetime as dt
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    semantic_state_transition,
    semantic_state_transition_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_traceability import (
    require_persisted_semantic_projection_plan,
    semantic_projection_component_rows,
    semantic_projection_diagram_rows,
    semantic_projection_workstream_rows,
)


SEMANTIC_COMPONENT_VALIDATION_VERSION = "odylith.greenfield.semantic-component-validation.v2"


@dataclass(frozen=True)
class SemanticComponentWriteResult:
    """Exact Registry paths written from a validated semantic component preview."""

    component_id: str
    label: str
    path: str
    registry_path: Path
    spec_path: Path
    validation_gate: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "label": self.label,
            "path": self.path,
            "registry_path": str(self.registry_path),
            "spec_path": str(self.spec_path),
            "validation_gate": dict(self.validation_gate),
        }


def semantic_component_authoring_inputs(
    *,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    diagram_ids: Sequence[str],
) -> tuple[dict[str, Any], ...]:
    """Bind typed component contracts to exact governed artifact identifiers."""

    plan = require_persisted_semantic_projection_plan(proposal)
    components = semantic_projection_component_rows(proposal)
    backlog = semantic_projection_workstream_rows(proposal)
    diagrams = semantic_projection_diagram_rows(proposal)
    plan_components = {
        _required_text(row, "component_id"): row
        for row in mapping_rows(plan.get("components"))
    }
    _validate_semantic_component_roles(plan)
    plan_workstreams = mapping_rows(plan.get("workstreams"))
    product_workstreams = tuple(
        row for row in plan_workstreams if row.get("kind") == "product"
    )
    if len(product_workstreams) != 1:
        raise ValueError("persisted semantic projection plan lacks one product workstream")
    diagram_plan_by_key = {
        _required_text(row, "key"): row
        for row in mapping_rows(plan.get("diagrams"))
    }
    if len(diagrams) != len(diagram_ids):
        raise ValueError("verified semantic component package lacks exact Atlas allocation")
    created = mapping_rows(backlog_result.get("created"))
    diagram_id_by_slug = {
        str(row.get("slug") or "").strip(): str(identifier).strip()
        for row, identifier in zip(diagrams, diagram_ids, strict=True)
    }
    created_id_by_title = {
        str(row.get("title") or "").strip(): str(row.get("idea_id") or "").strip()
        for row in created
    }
    inputs: list[dict[str, Any]] = []
    for component in components:
        component_id = _required_text(component, "component_id")
        label = _required_text(component, "label")
        proposal_contract = component.get("component_contract")
        if not isinstance(proposal_contract, Mapping):
            raise ValueError(f"verified semantic component `{label}` lacks its typed contract")
        component_plan = plan_components[component_id]
        child_workstreams = tuple(
            row
            for row in plan_workstreams
            if row.get("kind") == "component"
            and _strings(row.get("component_ids")) == (component_id,)
        )
        if len(plan_workstreams) == 1:
            workstream_plan = product_workstreams[0]
        elif len(child_workstreams) == 1:
            workstream_plan = child_workstreams[0]
        else:
            raise ValueError(
                f"verified semantic component `{label}` lacks one planned workstream"
            )
        workstream = _workstream_by_title(
            backlog,
            title=_required_text(workstream_plan, "title"),
        )
        workstream_title = _required_text(workstream, "title")
        workstream_id = created_id_by_title.get(workstream_title, "")
        if not workstream_id:
            raise ValueError(f"verified semantic component `{label}` lacks an exact created workstream")
        diagram_slugs = tuple(
            _required_text(diagram_plan_by_key[key], "slug")
            for key in _strings(workstream_plan.get("diagram_keys"))
        )
        linked_diagrams = tuple(
            diagram_id_by_slug[slug]
            for slug in diagram_slugs
            if slug in diagram_id_by_slug
        )
        if len(linked_diagrams) != len(diagram_slugs) or not linked_diagrams:
            raise ValueError(f"verified semantic component `{label}` lacks exact Atlas bindings")
        responsibility = _required_text(component, "responsibility")
        boundary = _required_text(component, "boundary")
        dependencies = _strings(component.get("dependencies")) or (
            f"Upstream truth: {_required_text(proposal_contract, 'upstream_truth')}",
        )
        artifact_contract = _artifact_component_contract(
            plan=plan,
            component_plan=component_plan,
            proposal_contract=proposal_contract,
        )
        interfaces = _required_strings(component, "interfaces")
        inputs.append(
            {
                "component_id": component_id,
                "label": label,
                "path": _required_text(component, "intended_path"),
                "kind": _required_text(component, "kind"),
                "category": "application",
                "status": _required_text(component, "status"),
                "qualification": _required_text(component, "qualification"),
                "owner": "repo",
                "product_layer": "application",
                "sources": ("verified_semantic_intent",),
                "workstreams": (workstream_id,),
                "diagrams": linked_diagrams,
                "responsibility": responsibility,
                "boundary": boundary,
                "dependencies": dependencies,
                "interfaces": interfaces,
                "validation": artifact_contract["local_proof"],
                "risks": _required_strings(component, "risks"),
                "implementation_handoff": {
                    "workstream_id": workstream_id,
                    "workstream_title": workstream_title,
                    "first_slice": responsibility,
                    "release_selector": str(release_selector).strip(),
                    "validation_gates": artifact_contract["local_proof"],
                    "verification_commands": ("odylith registry validate",),
                },
                "component_contract": artifact_contract,
                "implementation_policy_id": _required_text(
                    component, "implementation_policy_id"
                ),
                "covered_fact_ids": _required_strings(
                    component, "covered_fact_ids"
                ),
                "projection_basis_fact_ids": _required_strings(
                    component, "projection_basis_fact_ids"
                ),
                "projection_basis_custody": tuple(
                    dict(row)
                    for row in mapping_rows(
                        component.get("projection_basis_custody")
                    )
                ),
            }
        )
    return tuple(inputs)


def render_semantic_component_specs(
    *,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    diagram_ids: Sequence[str],
) -> dict[str, str]:
    """Render typed contracts without profiles, reparsing, or repair."""

    return {
        str(row["label"]): _render_component_spec(row)
        for row in semantic_component_authoring_inputs(
            proposal=proposal,
            release_selector=release_selector,
            backlog_result=backlog_result,
            diagram_ids=diagram_ids,
        )
    }


def preview_semantic_components(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    diagram_ids: Sequence[str],
) -> tuple[dict[str, Any], ...]:
    """Validate and preview exact graph-native Registry inputs without writes."""

    rows: list[dict[str, Any]] = []
    for authoring_input in semantic_component_authoring_inputs(
        proposal=proposal,
        release_selector=release_selector,
        backlog_result=backlog_result,
        diagram_ids=diagram_ids,
    ):
        component_id = str(authoring_input["component_id"])
        registry_entry = _registry_entry(authoring_input)
        validation_gate = {
            "version": SEMANTIC_COMPONENT_VALIDATION_VERSION,
            "status": "passed",
            "artifact_kind": "component",
            "mechanism": "exact_semantic_contract",
            "checks": [
                "typed_contract_complete",
                "registry_binding_exact",
                "spec_projection_exact",
            ],
        }
        rows.append(
            {
                "component_id": component_id,
                "label": authoring_input["label"],
                "path": authoring_input["path"],
                "registry_path": str(root / "odylith/registry/source/component_registry.v1.json"),
                "spec_path": str(
                    root / f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md"
                ),
                "validation_gate": validation_gate,
                "implementation_handoff": dict(authoring_input["implementation_handoff"]),
                "authoring_input": dict(authoring_input),
                "registry_entry": registry_entry,
                "what_it_is": registry_entry["what_it_is"],
            }
        )
    return tuple(rows)


def materialize_semantic_component_from_preview(
    *,
    root: Path,
    preview: Mapping[str, Any],
    rendered_component_specs: Mapping[str, str],
) -> SemanticComponentWriteResult:
    """Materialize an already validated graph-native component preview."""

    authoring_input = preview.get("authoring_input")
    registry_entry = preview.get("registry_entry")
    if not isinstance(authoring_input, Mapping) or not isinstance(registry_entry, Mapping):
        raise ValueError("compiled semantic component preview lacks its exact typed inputs")
    label = str(authoring_input.get("label") or "").strip()
    rendered = str(rendered_component_specs.get(label) or "").rstrip()
    if not rendered:
        raise ValueError(f"compiled semantic component spec missing for `{label}`")
    gate = preview.get("validation_gate")
    if not isinstance(gate, Mapping) or gate.get("status") != "passed":
        raise ValueError(f"compiled semantic component validation did not pass for `{label}`")
    return _write_semantic_component(
        root=root,
        registry_entry=registry_entry,
        spec_text=rendered,
        validation_gate=gate,
    )


def _write_semantic_component(
    *,
    root: Path,
    registry_entry: Mapping[str, Any],
    spec_text: str,
    validation_gate: Mapping[str, Any],
) -> SemanticComponentWriteResult:
    entry = dict(registry_entry)
    component_id = _required_text(entry, "component_id")
    label = _required_text(entry, "name")
    spec_ref = _required_text(entry, "spec_ref")
    expected_spec_ref = f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md"
    if spec_ref != expected_spec_ref:
        raise ValueError(
            f"compiled semantic component `{component_id}` has unexpected spec path `{spec_ref}`"
        )
    registry_path = root / "odylith/registry/source/component_registry.v1.json"
    registry = _read_registry(registry_path)
    components = registry.get("components")
    rows = components if isinstance(components, list) else []
    matches = [
        index
        for index, row in enumerate(rows)
        if isinstance(row, Mapping) and row.get("component_id") == component_id
    ]
    if len(matches) > 1:
        raise ValueError(f"Registry contains duplicate component `{component_id}`")
    if matches:
        rows[matches[0]] = entry
    else:
        rows.append(entry)
    registry["components"] = rows
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    spec_path = root / spec_ref
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(spec_text.rstrip() + "\n", encoding="utf-8")
    path_prefixes = entry.get("path_prefixes")
    path = (
        str(path_prefixes[0]).strip()
        if isinstance(path_prefixes, list) and path_prefixes
        else ""
    )
    return SemanticComponentWriteResult(
        component_id=component_id,
        label=label,
        path=path,
        registry_path=registry_path.relative_to(root),
        spec_path=spec_path.relative_to(root),
        validation_gate=dict(validation_gate),
    )


def _read_registry(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": "v1", "components": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"compiled Registry baseline is unreadable: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"compiled Registry baseline must be an object: {path}")
    return value


def _render_component_spec(row: Mapping[str, Any]) -> str:
    label = str(row["label"])
    contract = row["component_contract"]
    handoff = row["implementation_handoff"]
    state_objects = _strings(contract.get("state_objects"))
    visible_outputs = _strings(contract.get("visible_outputs"))
    state_transitions = _strings(contract.get("state_transitions"))
    proof_rows = _required_strings(contract, "local_proof")
    lines = [
        f"# {label}",
        "",
        (
            "> Plan-local implementation policy "
            f"`{row['implementation_policy_id']}` for `{row['component_id']}`, "
            "grounded in the listed Semantic Intent facts."
        ),
        "",
        f"## {label} Purpose",
        "",
        _sentence(row["responsibility"]),
        "",
        _component_interface_heading(
            label,
            stateful=bool(state_objects),
            has_outputs=bool(visible_outputs),
        ),
        "",
        "### Accepts",
        "",
        _bullets(_values(contract, "accepted_inputs")),
        "",
        "### Interfaces",
        "",
        _bullets(_strings(row["interfaces"])),
        "",
        f"## {label} Boundary and Handoff",
        "",
        f"- Boundary: {_sentence(row['boundary'])}",
        f"- Upstream truth: {_sentence(contract['upstream_truth'])}",
        f"- Downstream consumers: {_sentence(contract['downstream_consumers'])}",
        f"- Outside this boundary: {_sentence(contract['outside_boundary'])}",
        *_prefixed_bullets("Dependency", _strings(row["dependencies"])),
        (
            f"- Trace links: workstream `{handoff['workstream_id']}` and Atlas diagrams "
            f"{', '.join(f'`{value}`' for value in row['diagrams'])}."
        ),
        "",
        f"## {label} Proof and Failure",
        "",
        *_prefixed_bullets("Evidence", proof_rows),
        f"- Unique failure: {_sentence(contract['unique_failure'])}",
        *_prefixed_bullets("Risk", _strings(row["risks"])),
        "",
        "## Implementation Handoff",
        "",
        f"- Source boundary: `{row['path']}`",
        f"- First workstream: `{handoff['workstream_id']}` — {handoff['workstream_title']}",
        f"- First slice: {_sentence(handoff['first_slice'])}",
        f"- Release: `{handoff['release_selector']}`",
        f"- Atlas diagrams: {', '.join(f'`{value}`' for value in row['diagrams'])}",
        "",
        "## Feature History",
        "",
        (
            f"- {dt.date.today().isoformat()}: Registered from verified Semantic Intent "
            f"(Plan: [{handoff['workstream_id']}]"
            "(odylith/radar/radar.html?view=plan&workstream="
            f"{handoff['workstream_id']}))."
        ),
        "",
    ]
    if state_objects:
        insertion = lines.index("### Accepts")
        state_section = ["### State objects", "", _bullets(state_objects), ""]
        if state_transitions:
            state_section.extend(
                ["### State transitions", "", _bullets(state_transitions), ""]
            )
        lines[insertion:insertion] = state_section
    if visible_outputs:
        insertion = lines.index("### Interfaces")
        lines[insertion:insertion] = [
            "### Visible outputs",
            "",
            _bullets(visible_outputs),
            "",
        ]
    return "\n".join(lines)


def _registry_entry(row: Mapping[str, Any]) -> dict[str, Any]:
    component_id = str(row["component_id"])
    label = str(row["label"])
    responsibility = _sentence(row["responsibility"])
    return {
        "component_id": component_id,
        "name": label,
        "kind": row["kind"],
        "category": row["category"],
        "qualification": row["qualification"],
        "aliases": [],
        "path_prefixes": [row["path"]],
        "workstreams": list(row["workstreams"]),
        "diagrams": list(row["diagrams"]),
        "owner": row["owner"],
        "status": row["status"],
        "what_it_is": f"{label} is the planned {row['kind']} boundary for: {responsibility}",
        "why_tracked": (
            "Tracked because its plan-local contract is grounded in exact "
            "Semantic Intent facts for the first release."
        ),
        "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
        "sources": list(row["sources"]),
        "subcomponents": [],
        "product_layer": row["product_layer"],
    }


def _workstream_by_title(
    rows: Sequence[Mapping[str, Any]], *, title: str
) -> Mapping[str, Any]:
    matches = [row for row in rows if row.get("title") == title]
    if len(matches) != 1:
        raise ValueError(
            f"verified semantic component requires one exact workstream `{title}`"
        )
    return matches[0]


def _artifact_component_contract(
    *,
    plan: Mapping[str, Any],
    component_plan: Mapping[str, Any],
    proposal_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Project artifact copy from exact typed nodes, preserving plural axes."""

    node_by_id = {
        _required_text(row, "fact_id"): row
        for row in mapping_rows(plan.get("nodes"))
    }
    covered = tuple(
        node_by_id[fact_id]
        for fact_id in _strings(component_plan.get("covered_fact_ids"))
    )
    state_nodes = tuple(row for row in covered if row.get("kind") == "state_object")
    output_nodes = tuple(row for row in covered if row.get("kind") == "visible_output")
    state_objects = tuple(_required_text(row, "label") for row in state_nodes)
    visible_outputs = tuple(_required_text(row, "label") for row in output_nodes)
    transitions = tuple(
        transition
        for row in state_nodes
        if (transition := _state_transition(row))
    )
    component_role = _required_text(component_plan, "component_role")
    if _required_text(proposal_contract, "component_role") != component_role:
        raise ValueError("persisted semantic component role binding drifted")
    local_proof = list(_required_strings(proposal_contract, "local_proof"))
    return {
        "component_role": component_role,
        "accepted_inputs": _required_text(proposal_contract, "accepted_inputs"),
        "state_objects": state_objects,
        "visible_outputs": visible_outputs,
        "state_transitions": transitions,
        "upstream_truth": _required_text(proposal_contract, "upstream_truth"),
        "downstream_consumers": _required_text(
            proposal_contract,
            "downstream_consumers",
        ),
        "outside_boundary": _required_text(proposal_contract, "outside_boundary"),
        "local_proof": tuple(local_proof),
        "unique_failure": _required_text(proposal_contract, "unique_failure"),
        "stateful": bool(state_objects),
    }


def _validate_semantic_component_roles(
    plan: Mapping[str, Any],
) -> None:
    """Require one policy component to cover every delivery fact outside the graph."""

    nodes = mapping_rows(plan.get("nodes"))
    node_by_id = {
        _required_text(row, "fact_id"): row
        for row in nodes
    }
    components = mapping_rows(plan.get("components"))
    if len(components) != 1:
        raise ValueError(
            "persisted semantic projection requires one plan-local component policy"
        )
    component = components[0]
    component_id = _required_text(component, "component_id")
    policy_id = _required_text(component, "implementation_policy_id")
    if policy_id in node_by_id:
        raise ValueError(
            "persisted implementation policy must not masquerade as a semantic fact"
        )
    if _required_text(component, "release_scope") != "first_path_required":
        raise ValueError(
            f"persisted semantic component `{component_id}` has an invalid release scope"
        )
    if _required_text(component, "component_role") != "result_implementing":
        raise ValueError(
            f"persisted semantic component `{component_id}` has a mismatched policy role"
        )
    axes = plan.get("axes")
    if not isinstance(axes, Mapping):
        raise ValueError("persisted semantic projection plan lacks typed axes")
    required = {
        fact_id
        for key in (
            "workflow_step_fact_ids",
            "state_fact_ids",
            "visible_output_fact_ids",
        )
        for fact_id in _strings(axes.get(key))
    }
    covered = set(_strings(component.get("covered_fact_ids")))
    if covered != required:
        raise ValueError(
            f"persisted semantic component `{component_id}` coverage drifted"
        )
    if set(_strings(component.get("projection_basis_fact_ids"))) != set(node_by_id):
        raise ValueError(
            f"persisted semantic component `{component_id}` basis drifted"
        )


def _state_transition(node: Mapping[str, Any]) -> str:
    transition = semantic_state_transition(node)
    if transition is None:
        return ""
    return f"{_required_text(node, 'label')}: {semantic_state_transition_phrase(node)}"


def _plain_list(values: Sequence[str]) -> str:
    return ", ".join(values)


def _component_interface_heading(
    label: str,
    *,
    stateful: bool,
    has_outputs: bool,
) -> str:
    axes = "State, Outputs, and Interfaces" if stateful and has_outputs else "State and Interfaces" if stateful else "Outputs and Interfaces" if has_outputs else "Interfaces"
    return f"## {label} {axes}"


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise ValueError(f"verified semantic component lacks `{key}`")
    return value


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _required_strings(row: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values = _strings(row.get(key))
    if not values:
        raise ValueError(f"verified semantic component lacks `{key}`")
    return values


def _values(row: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = row.get(key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values = tuple(str(item).strip() for item in value if str(item).strip())
    else:
        text = str(value or "").strip()
        values = (text,) if text else ()
    if not values:
        raise ValueError(f"verified semantic component contract lacks `{key}`")
    return values


def _sentence(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if text.endswith((".", "?", "!")) else f"{text}."


def _bullets(values: Sequence[str]) -> str:
    return "\n".join(f"- {_sentence(value)}" for value in values)


def _prefixed_bullets(prefix: str, values: Sequence[str]) -> list[str]:
    return [f"- {prefix}: {_sentence(value)}" for value in values]


__all__ = [
    "SEMANTIC_COMPONENT_VALIDATION_VERSION",
    "SemanticComponentWriteResult",
    "materialize_semantic_component_from_preview",
    "preview_semantic_components",
    "render_semantic_component_specs",
    "semantic_component_authoring_inputs",
]

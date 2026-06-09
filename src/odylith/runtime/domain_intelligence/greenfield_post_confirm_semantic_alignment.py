"""Semantic model alignment checks for post-confirm greenfield packages."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values


def semantic_model_shape_issues(semantic: Mapping[str, Any]) -> list[str]:
    required = (
        "first_path_contract",
        "domain_ontology",
        "components",
        "workstreams",
        "diagram_event_graph",
        "proof_obligations",
    )
    issues = [
        f"GreenfieldSemanticModel missing `{key}`"
        for key in required
        if not isinstance(semantic.get(key), (Mapping, list))
    ]
    if clean_text(semantic.get("schema_version")) != "odylith.greenfield.semantic_model.v1":
        issues.append("GreenfieldSemanticModel schema_version is missing or unsupported")
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    events = first_path.get("events") if isinstance(first_path, Mapping) else None
    if not isinstance(events, list) or not events:
        issues.append("FirstPathContract must include structured first-path events")
    elif not any(isinstance(row, Mapping) and row.get("visible_result") for row in events):
        issues.append("FirstPathContract must identify at least one visible result event")
    if not clean_text(first_path.get("capability") if isinstance(first_path, Mapping) else ""):
        issues.append("FirstPathContract must preserve the accepted path capability")
    ontology = semantic.get("domain_ontology") if isinstance(semantic.get("domain_ontology"), Mapping) else {}
    if not clean_text(ontology.get("product_title") if isinstance(ontology, Mapping) else ""):
        issues.append("DomainOntology must carry the canonical product title")
    graph = semantic.get("diagram_event_graph") if isinstance(semantic.get("diagram_event_graph"), Mapping) else {}
    if not clean_text(graph.get("proof_checkpoint") if isinstance(graph, Mapping) else ""):
        issues.append("DiagramEventGraph must carry a readable proof checkpoint")
    proof_keys = {
        clean_text(row.get("key"))
        for row in mapping_rows(semantic.get("proof_obligations"))
        if clean_text(row.get("key"))
    }
    for key in ("first_path_contract", "release_boundary"):
        if key not in proof_keys:
            issues.append(f"GreenfieldSemanticModel missing `{key}` proof obligation")
    return issues


def semantic_component_alignment_issues(proposal: Mapping[str, Any], semantic: Mapping[str, Any]) -> list[str]:
    proposal_components = mapping_rows(proposal.get("components"))
    model_components = mapping_rows(semantic.get("components"))
    issues: list[str] = []
    proposal_by_id = {_component_id(row): row for row in proposal_components if _component_id(row)}
    model_by_id = {_component_id(row): row for row in model_components if _component_id(row)}
    if set(proposal_by_id) != set(model_by_id):
        missing = sorted(set(proposal_by_id) - set(model_by_id))
        extra = sorted(set(model_by_id) - set(proposal_by_id))
        if missing:
            issues.append(f"GreenfieldSemanticModel missing component contract(s): {', '.join(missing[:5])}")
        if extra:
            issues.append(f"GreenfieldSemanticModel has component contract(s) not rendered by proposal: {', '.join(extra[:5])}")
    for component_id, row in proposal_by_id.items():
        model = model_by_id.get(component_id)
        if not isinstance(model, Mapping):
            continue
        contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
        checks = {
            "label": clean_text(row.get("label")),
            "release_scope": clean_text(row.get("release_scope")),
            "owned_state": clean_text(contract.get("owned_state") if isinstance(contract, Mapping) else ""),
            "accepted_inputs": clean_text(contract.get("accepted_inputs") if isinstance(contract, Mapping) else ""),
            "produced_outputs": clean_text(contract.get("produced_outputs") if isinstance(contract, Mapping) else ""),
        }
        for key, expected in checks.items():
            actual = clean_text(model.get(key))
            if expected and actual != expected:
                issues.append(f"GreenfieldSemanticModel component `{component_id}` drifted from proposal `{key}`")
        proposal_proofs = tuple(
            clean_text(value)
            for value in text_values(contract.get("local_proof") if isinstance(contract, Mapping) else ())
            if clean_text(value)
        )
        model_proofs = tuple(clean_text(value) for value in text_values(model.get("proof_obligations")) if clean_text(value))
        if proposal_proofs and proposal_proofs != model_proofs:
            issues.append(f"GreenfieldSemanticModel component `{component_id}` proof obligations drifted from ComponentContract")
    proof_keys = {
        clean_text(row.get("key"))
        for row in mapping_rows(semantic.get("proof_obligations"))
    }
    for component_id, row in proposal_by_id.items():
        if clean_text(row.get("release_scope")) == "out_of_scope":
            continue
        if f"component_{component_id}" not in proof_keys:
            issues.append(f"GreenfieldSemanticModel missing proof obligation for active component `{component_id}`")
    return issues


def semantic_workstream_alignment_issues(proposal: Mapping[str, Any], semantic: Mapping[str, Any]) -> list[str]:
    proposal_rows = mapping_rows(proposal.get("backlog"))
    model_rows = mapping_rows(semantic.get("workstreams"))
    proposal_by_title = {clean_text(row.get("title")): row for row in proposal_rows if clean_text(row.get("title"))}
    model_by_title = {clean_text(row.get("title")): row for row in model_rows if clean_text(row.get("title"))}
    proposal_titles = set(proposal_by_title)
    model_titles = set(model_by_title)
    missing = sorted(proposal_titles - model_titles)
    extra = sorted(model_titles - proposal_titles)
    issues: list[str] = []
    if missing:
        issues.append(f"GreenfieldSemanticModel missing workstream contract(s): {', '.join(missing[:4])}")
    if extra:
        issues.append(f"GreenfieldSemanticModel has workstream contract(s) not rendered by proposal: {', '.join(extra[:4])}")
    for title in sorted(proposal_titles.intersection(model_titles)):
        proposal_row = proposal_by_title[title]
        model_row = model_by_title[title]
        checks = {
            "local_problem": clean_text(proposal_row.get("problem")),
            "first_slice": clean_text(proposal_row.get("recommended_first_slice")),
            "proof": " ".join(clean_text(value) for value in text_values(proposal_row.get("validation")) if clean_text(value)),
        }
        for key, expected in checks.items():
            actual = clean_text(model_row.get(key))
            if expected and actual != expected:
                issues.append(f"GreenfieldSemanticModel workstream `{title}` drifted from proposal `{key}`")
        proposal_components = tuple(clean_text(value) for value in text_values(proposal_row.get("component_focus")) if clean_text(value))
        model_components = tuple(clean_text(value) for value in text_values(model_row.get("component_ids")) if clean_text(value))
        if proposal_components and proposal_components != model_components:
            issues.append(f"GreenfieldSemanticModel workstream `{title}` component_ids drifted from proposal component_focus")
    return issues


def semantic_diagram_alignment_issues(proposal: Mapping[str, Any], semantic: Mapping[str, Any]) -> list[str]:
    graph = semantic.get("diagram_event_graph") if isinstance(semantic.get("diagram_event_graph"), Mapping) else {}
    active_components = {
        _component_id(row)
        for row in mapping_rows(proposal.get("components"))
        if _component_id(row) and _is_first_release_scope(row.get("release_scope"))
    }
    graph_components = {
        clean_text(value)
        for value in text_values(graph.get("component_sequence") if isinstance(graph, Mapping) else ())
        if clean_text(value)
    }
    issues: list[str] = []
    if active_components != graph_components:
        issues.append("DiagramEventGraph component sequence drifted from active ReleaseScope components")
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    first_path_events = tuple(
        clean_text(row.get("text"))
        for row in mapping_rows(first_path.get("events") if isinstance(first_path, Mapping) else ())
        if clean_text(row.get("text"))
    )
    graph_events = tuple(
        clean_text(row.get("text"))
        for row in mapping_rows(graph.get("events") if isinstance(graph, Mapping) else ())
        if clean_text(row.get("text"))
    )
    if first_path_events and graph_events != first_path_events:
        issues.append("DiagramEventGraph events drifted from FirstPathContract events")
    diagram_rows = mapping_rows(proposal.get("diagrams"))
    if not diagram_rows:
        issues.append("post-confirm completion requires in-memory Atlas diagram artifacts")
    for row in diagram_rows:
        if not clean_text(row.get("mermaid_source")):
            issues.append(f"Atlas diagram `{clean_text(row.get('title')) or clean_text(row.get('slug'))}` missing in-memory Mermaid source")
    return issues


def rendered_spec_alignment_issues(proposal: Mapping[str, Any], rendered_specs: Mapping[str, str]) -> list[str]:
    active_labels = {
        clean_text(row.get("label"))
        for row in mapping_rows(proposal.get("components"))
        if clean_text(row.get("label")) and _is_first_release_scope(row.get("release_scope"))
    }
    rendered_labels = {clean_text(label) for label in rendered_specs}
    issues: list[str] = []
    if active_labels and rendered_labels != active_labels:
        missing = sorted(active_labels - rendered_labels)
        extra = sorted(rendered_labels - active_labels)
        if missing:
            issues.append(f"prewrite Registry package missing rendered active component spec(s): {', '.join(missing[:5])}")
        if extra:
            issues.append(f"prewrite Registry package rendered component spec(s) outside active release scope: {', '.join(extra[:5])}")
    return issues


def _component_id(row: Mapping[str, Any]) -> str:
    return clean_text(row.get("component_id")) or clean_text(row.get("label")).casefold().replace(" ", "-")


def _is_first_release_scope(value: Any) -> bool:
    scope = clean_text(value).casefold()
    return scope not in {"deferred", "out_of_scope", "future", "external"}

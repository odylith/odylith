"""Atlas diagram helpers for confirmed greenfield proposals."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_confirmed_diagram_text as diagram_text
from odylith.runtime.domain_intelligence.greenfield_actor_labels import localize_leading_actor_reference
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_item
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import label_with_suffix
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_object_descriptor
from odylith.runtime.domain_intelligence.greenfield_deferral_predicates import terminal_deferral_subject
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import best_component_node_for_text
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import first_path_flowchart_mermaid
from odylith.runtime.domain_intelligence.greenfield_sequence_labeling import flow_label as wrapped_flow_label
from odylith.runtime.domain_intelligence.greenfield_sequence_labeling import header_body_label
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps


def confirmed_diagrams(
    *,
    label: str,
    components: list[dict[str, Any]],
    diagram_slugs: Mapping[str, str],
    workstream_titles: Mapping[str, str] | None = None,
    product_story: str = "",
    first_path: str = "",
    proof_boundary: str = "",
    state_object: str = "",
    evidence_record: str = "",
    human_actors: list[str] | None = None,
    external_systems: list[str] | None = None,
    internal_systems: list[str] | None = None,
    non_goals: list[str] | None = None,
    semantic_model: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    all_components = [dict(row) for row in components]
    release_components = [dict(row) for row in active_release_components(all_components)] if all_components else []
    component_rows = [
        {
            "name": str(row["label"]),
            "description": diagram_text.component_description(row),
        }
        for row in release_components
    ]
    titles = diagram_text.workstream_titles(label=label, components=release_components, provided=workstream_titles)
    actors = human_actors or [f"{label} product user"]
    externals = external_systems or []
    internals = internal_systems or [str(row.get("label", "")) for row in release_components]
    deferred_scope = non_goals or []
    component_phrase = diagram_text.component_phrase(release_components)
    actor_phrase = diagram_text.actor_phrase(actors, label=label)
    story_brief = diagram_text.brief_story(product_story, fallback=f"{label} gives {actor_phrase} one reviewable first path")
    display_first_path = localize_leading_actor_reference(
        first_path,
        actor_rows=actors,
        project_focus=label,
        fallback=f"{sentence_label(label)} user",
    )
    first_path_brief = diagram_text.brief_first_path(display_first_path)
    proof_brief = diagram_text.brief_proof_boundary(proof_boundary)
    state_label = diagram_text.brief_object_label(state_object, fallback=f"{label} state")
    evidence_label = diagram_text.brief_object_label(evidence_record, fallback=f"{label} evidence record")
    label_ref = sentence_label(label)
    release_responsibilities = label_with_suffix(label, "release 0.0.1 responsibilities")
    release_gate_ref = sentence_label(label_with_suffix(label, "release gate"))
    return [
        {
            "slug": diagram_slugs["context"],
            "title": "System Context View",
            "kind": "flowchart",
            "summary": diagram_text.sentence(
                f"{label} boundary view: {story_brief}; it shows {actor_phrase}, outside inputs, and {component_phrase} as the first-release ownership map"
            ),
            "read_guide": (
                f"Start with {actor_phrase}, then follow outside inputs into product-owned components. Treat anything outside "
                "the release boundary as a dependency or deferred claim until its contract is accepted."
            ),
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": [titles["program"], titles["workflow"], titles["boundary"]],
            "related_components": [str(row["component_id"]) for row in release_components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _context_mermaid(label=label, actors=actors, external_systems=externals, components=release_components),
        },
        {
            "slug": diagram_slugs["sequence"],
            "title": "First Path Sequence",
            "kind": "flowchart",
            "summary": diagram_text.sentence(
                (
                    f"This sequence shows what the first release must prove from {actor_phrase} through {component_phrase} "
                    f"to the visible outcome: {first_path_brief}"
                )
                if first_path_brief
                else (
                    f"This sequence shows what the first release must prove from {actor_phrase} through {component_phrase} to the visible outcome. "
                    "Use this view to check which responsibilities must preserve state, evidence, and blockers."
                )
            ),
            "read_guide": (
                f"Start with the first product action. Follow {actor_phrase} through each product responsibility. The release must still prove: "
                f"{proof_brief or 'the promised user-visible result'}."
            ),
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": [titles["workflow"], titles["boundary"]],
            "related_components": [str(row["component_id"]) for row in release_components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": first_path_flowchart_mermaid(
                label=label,
                actors=actors,
                components=release_components,
                first_path=display_first_path,
                semantic_model=semantic_model,
            ),
        },
        {
            "slug": diagram_slugs["state_evidence"],
            "title": "State and Evidence View",
            "kind": "flowchart",
            "summary": (
                f"Show how {state_label} becomes reviewable {label_ref} evidence in the first release. "
                f"The evidence record is {evidence_label}."
            ),
            "read_guide": (
                f"Read this as the {label_ref} state trail. Start with {actor_phrase}, then follow state, evidence, "
                "proof, and correction points before trusting the release claim."
            ),
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": [titles["workflow"], titles["boundary"], titles["proof"]],
            "related_components": [str(row["component_id"]) for row in release_components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _state_evidence_mermaid(
                label=label,
                state_object=state_label,
                evidence_record=evidence_label,
                components=release_components,
                actors=actors,
                first_path=display_first_path,
                proof_boundary=proof_boundary,
                semantic_model=semantic_model,
            ),
        },
        {
            "slug": diagram_slugs["component_boundaries"],
            "title": "Component Boundary View",
            "kind": "flowchart",
            "summary": (
                f"Shows which product systems own {release_responsibilities} and which dependencies stay outside. "
                f"Use it to separate {state_label}, {evidence_label}, and deferred scope before implementation expands."
            ),
            "read_guide": (
                "Read this as an ownership boundary map. Product-owned components sit inside the release boundary; "
                "external inputs and deferred capabilities stay outside until their contracts are accepted."
            ),
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": [titles["boundary"]],
            "related_components": [str(row["component_id"]) for row in release_components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _component_boundary_mermaid(
                label=label,
                components=all_components,
                external_systems=externals,
                non_goals=deferred_scope,
            ),
        },
        {
            "slug": diagram_slugs["ownership"],
            "title": "Ownership and Proof View",
            "kind": "flowchart",
            "summary": diagram_text.sentence(
                f"Trace release ownership for {label} from product-owned components to the product result supported by {state_label} and {evidence_label}"
            ),
            "read_guide": (
                f"Read from each state-owning or evidence-producing component toward the proof boundary. A box matters when it owns {label_ref} data, "
                "access, derivation, export, display, or review needed to trust the first release."
            ),
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": [titles["boundary"], titles["proof"]],
            "related_components": [str(row["component_id"]) for row in release_components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _ownership_mermaid(
                label=label,
                components=release_components,
                internal_systems=internals,
                proof_boundary=proof_boundary,
                semantic_model=semantic_model,
            ),
        },
        {
            "slug": diagram_slugs["proof_review"],
            "title": "Release Proof Review",
            "kind": "flowchart",
            "summary": diagram_text.sentence(
                f"Show which first-path result, state replay, evidence check, access proof, and release decision must exist before {label} trust increases"
            ),
            "read_guide": (
                f"Read this as the {release_gate_ref}. The product result, {state_label}, {evidence_label}, "
                "validation output, and release decision must all be present; deferred scope stays outside the claim."
            ),
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": [titles["proof"]],
            "related_components": [str(row["component_id"]) for row in release_components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _proof_review_mermaid(
                state_object=state_label,
                evidence_record=evidence_label,
                proof_boundary=proof_boundary,
                components=release_components,
                non_goals=deferred_scope,
                semantic_model=semantic_model,
            ),
        },
    ]


def _context_mermaid(
    *,
    label: str,
    actors: list[str],
    external_systems: list[str],
    components: list[dict[str, Any]],
) -> str:
    lines = ["flowchart LR"]
    first_component = _node_id("component", 1)
    product_node = "P"
    if components:
        lines.append(f'  {product_node}["{diagram_text.flow_label(label, limit=64)}<br/>product boundary"]')
    actor_rows = actors[:8]
    for index, actor in enumerate(actor_rows, start=1):
        node = _node_id("actor", index)
        target = best_component_node_for_text(actor, components=components) or (product_node if components else first_component)
        lines.append(f'  {node}["{diagram_text.flow_label(actor, limit=96)}"] --> {target}')
    if not components:
        lines.append(f'  {first_component}["{diagram_text.flow_label(label, limit=60)}<br/>product core"]')
    for index, component in enumerate(components[:7], start=1):
        node = _node_id("component", index)
        lines.append(f'  {node}["{diagram_text.flow_label(str(component.get("label", "")), limit=72)}"]')
        if index == 1 and components:
            lines.append(f"  {product_node} --> {node}")
        if index > 1:
            lines.append(f"  {_node_id('component', index - 1)} --> {node}")
    for index, external in enumerate(external_systems[:5], start=1):
        node = _node_id("external", index)
        target_component = best_component_node_for_text(external, components=components) or _adapter_node(components) or (product_node if components else first_component)
        external_label = _external_identity_label(external) or boundary_clause_item(external, limit=96) or external
        lines.append(f'  {node}["{diagram_text.flow_label(external_label, limit=96)}"] --> {target_component}')
    lines.extend(
        [
            "  classDef personStyle fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
            "  classDef boundary fill:#F8FAFC,stroke:#CBD5E1,color:#17233A,stroke-width:1px;",
            "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef external fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  class " + ",".join(_node_id("actor", index) for index in range(1, len(actor_rows) + 1)) + " personStyle;",
            "  class " + ",".join(_node_id("component", index) for index in range(1, max(1, min(len(components), 7)) + 1)) + " service;",
        ]
    )
    if components:
        lines.append(f"  class {product_node} boundary;")
    if external_systems:
        lines.append("  class " + ",".join(_node_id("external", index) for index in range(1, min(len(external_systems), 5) + 1)) + " external;")
    return "\n".join(lines) + "\n"


def _ownership_mermaid(
    *,
    label: str,
    components: list[dict[str, Any]],
    internal_systems: list[str],
    proof_boundary: str,
    semantic_model: Mapping[str, Any] | None = None,
) -> str:
    lines = ["flowchart TB"]
    if not components:
        lines.append(f'  product["{diagram_text.flow_label(label, limit=96)}<br/>product boundary"] --> proof["Release<br/>proof"]')
    for index, component in enumerate(components[:7], start=1):
        node = _node_id("owner", index)
        label_text = str(component.get("label", "")) or (internal_systems[index - 1] if index <= len(internal_systems) else f"Component {index}")
        lines.append(f'  {node}["{diagram_text.flow_label(label_text, limit=112)}"]')
        if index > 1:
            lines.append(f"  {_node_id('owner', index - 1)} --> {node}")
    proof_node = _node_id("proof", 1)
    proof_label = diagram_text.semantic_proof_checkpoint(semantic_model) or diagram_text.release_proof_label(proof_boundary) or "promised outcome"
    lines.append(f'  {proof_node}["Release proof<br/>{diagram_text.escape_label(diagram_text.trim(proof_label, 72))}"]')
    if components:
        lines.append(f"  {_node_id('owner', min(len(components), 7))} --> {proof_node}")
    lines.extend(
        [
            "  classDef owner fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef gate fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  class " + ",".join(_node_id("owner", index) for index in range(1, max(1, min(len(components), 7)) + 1)) + " owner;",
            "  class proof1 gate;",
        ]
    )
    return "\n".join(lines) + "\n"


def _state_evidence_mermaid(
    *,
    label: str,
    state_object: str,
    evidence_record: str,
    components: list[dict[str, Any]],
    actors: list[str],
    first_path: str,
    proof_boundary: str,
    semantic_model: Mapping[str, Any] | None = None,
) -> str:
    first_owner = diagram_text.component_label(components, 0, fallback="First path owner")
    evidence_owner = _component_label_for_text(evidence_record, components=components) or diagram_text.component_label(components, min(2, max(0, len(components) - 1)), fallback="Proof Review Component")
    review_owner = diagram_text.component_label(components, len(components) - 1, fallback="Review owner")
    actor_label = _first_action_label(
        first_path=first_path,
        semantic_model=semantic_model,
        fallback=actors[0] if actors else diagram_text.actor_phrase(actors, label=label),
    )
    proof_label = diagram_text.semantic_proof_checkpoint(semantic_model) or diagram_text.release_proof_label(proof_boundary) or "source-backed release check"
    state_descriptor = state_object_descriptor(state_object)
    lines = [
        "flowchart LR",
        f'  action["First action<br/>{actor_label}"] --> owner1["{_diagram_label(first_owner, limit=96, fallback="First path owner")}"]',
        f'  owner1 --> domain_state["{state_descriptor}<br/>{_diagram_label(state_object, limit=96, fallback="Tracked state")}"]',
        f'  domain_state --> owner2["{_diagram_label(evidence_owner, limit=96, fallback="Evidence owner")}"]',
        f'  owner2 --> evidence_record["Evidence record<br/>{_diagram_label(evidence_record, limit=96, fallback="Evidence record")}"]',
        f'  evidence_record --> owner3["{_diagram_label(review_owner, limit=96, fallback="Review owner")}"]',
        f'  owner3 --> review["Proof check<br/>{_diagram_label(proof_label, limit=120, fallback="Source-backed release check")}"]',
        '  review --> correction["Blocked or corrected<br/>path stays visible"]',
        "  classDef personActionStyle fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
        "  classDef owner fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
        "  classDef domainObjectStyle fill:#F5F3FF,stroke:#C4B5FD,color:#17233A,stroke-width:1px;",
        "  classDef evidence fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
        "  classDef review fill:#F8FAFC,stroke:#CBD5E1,color:#17233A,stroke-width:1px;",
        "  class action personActionStyle;",
        "  class owner1,owner2,owner3 owner;",
        "  class domain_state domainObjectStyle;",
        "  class evidence_record evidence;",
        "  class review,correction review;",
    ]
    return "\n".join(lines) + "\n"


def _first_action_label(
    *,
    first_path: str,
    semantic_model: Mapping[str, Any] | None,
    fallback: str,
) -> str:
    for step in sequence_event_steps(first_path, semantic_model=semantic_model, dedupe=True):
        action = action_chain_fragment(step) or step
        if action:
            return _diagram_label(action[:1].upper() + action[1:], limit=72, fallback="First path action")
    return _diagram_label(fallback, limit=72, fallback="First path action")


def _component_label_for_text(value: str, *, components: list[dict[str, Any]]) -> str:
    node = best_component_node_for_text(value, components=components)
    if not node.startswith("component"):
        return ""
    try:
        index = int(node.replace("component", "", 1)) - 1
    except ValueError:
        return ""
    return diagram_text.component_label(components, index, fallback="")


def _component_boundary_mermaid(
    *,
    label: str,
    components: list[dict[str, Any]],
    external_systems: list[str],
    non_goals: list[str],
) -> str:
    selected_components = [dict(row) for row in active_release_components(components)] if components else []
    selected_components = selected_components[:8] or [{"label": f"{label} product core", "kind": "service"}]
    deferred_components = [
        component
        for component in components
        if str(component.get("release_scope", "")).strip() in {"deferred", "out_of_scope", "external"}
    ][:3]
    boundary_label = label_with_suffix(label, "release boundary")
    lines = ["flowchart TB", f'  subgraph product["{_diagram_label(boundary_label, limit=96, fallback="Product boundary")}"]']
    for index, component in enumerate(selected_components, start=1):
        node = _node_id("boundary", index)
        component_label = str(component.get("label", "")) or f"Component {index}"
        lines.append(f'    {node}["{_identity_label(component_label, fallback=f"Component {index}")}"]')
        if index > 1:
            lines.append(f"    {_node_id('boundary', index - 1)} --> {node}")
    lines.append("  end")
    first_node = _node_id("boundary", 1)
    for index, external in enumerate(external_systems[:3], start=1):
        node = _node_id("input", index)
        target = _boundary_node_for_text(external, selected_components=selected_components, fallback=first_node)
        external_label = _external_identity_label(external) or boundary_clause_item(external, limit=80) or external
        lines.append(f'  {node}["External input<br/>{_diagram_label(external_label, limit=96, fallback="External input")}"] --> {target}')
    deferred_items: list[tuple[str, bool]] = [
        (str(component.get("label", "")).strip(), True)
        for component in deferred_components
        if str(component.get("label", "")).strip()
    ]
    deferred_items.extend((item, False) for item in non_goals)
    for index, (item, item_is_component) in enumerate(deferred_items[:3], start=1):
        node = _node_id("deferred", index)
        target = _boundary_node_for_text(item, selected_components=selected_components, fallback=first_node)
        deferred_label = diagram_text.deferred_scope_label(item, label=label)
        if item_is_component:
            deferred_text = _deferred_identity_label(deferred_label)
        else:
            deferred_text = _diagram_label(deferred_label, limit=112, fallback="Beyond accepted first path")
        lines.append(f'  {node}["Deferred scope<br/>{deferred_text}"] -. later .-> {target}')
    lines.extend(
        [
            "  classDef product fill:#F8FAFC,stroke:#CBD5E1,color:#17233A,stroke-width:1px;",
            "  classDef owned fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef external fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  classDef laterScopeStyle fill:#FEF2F2,stroke:#FCA5A5,color:#17233A,stroke-width:1px;",
            "  class " + ",".join(_node_id("boundary", index) for index in range(1, len(selected_components) + 1)) + " owned;",
        ]
    )
    if external_systems:
        lines.append("  class " + ",".join(_node_id("input", index) for index in range(1, min(len(external_systems), 3) + 1)) + " external;")
    if deferred_items:
        lines.append(
            "  class "
            + ",".join(_node_id("deferred", index) for index in range(1, min(len(deferred_items), 3) + 1))
            + " laterScopeStyle;"
        )
    return "\n".join(lines) + "\n"


def _proof_review_mermaid(
    *,
    state_object: str,
    evidence_record: str,
    proof_boundary: str,
    components: list[dict[str, Any]],
    non_goals: list[str],
    semantic_model: Mapping[str, Any] | None = None,
) -> str:
    proof_text = diagram_text.brief_proof_boundary(proof_boundary) or "promised user-visible result"
    proof_label = diagram_text.semantic_proof_checkpoint(semantic_model) or diagram_text.proof_checkpoint_label(proof_text) or "first-path evidence, state replay, blocked-path proof"
    proof_label = diagram_text.diagram_sentence_label(proof_label) or proof_label
    outcome_label = diagram_text.semantic_visible_result_label(semantic_model) or proof_label or "promised outcome"
    outcome_body = header_body_label("Visible result", outcome_label)
    evidence_label = diagram_text.proof_evidence_label(components=components, fallback=evidence_record)
    lines = [
        "flowchart LR",
        f'  outcome["Visible result<br/>{_diagram_label(outcome_body, limit=120, fallback="Promised outcome")}"] --> domain_state',
        f'  domain_state["Domain state<br/>{_diagram_label(state_object, limit=96, fallback="Domain state")}"] --> evidence_record',
        f'  evidence_record["Evidence record<br/>{_diagram_label(evidence_label, limit=160, fallback="Evidence record", width=80, max_lines=2)}"] --> proof_gate',
        f'  proof_gate["Proof checkpoint<br/>{_diagram_label(proof_label, limit=160, fallback="Proof checkpoint", width=80, max_lines=2)}"] --> release_decision',
        '  release_decision["Release decision<br/>accept, revise, or block"] --> release_claim',
        '  release_claim["Release claim<br/>matches the promised outcome"]',
        "  classDef outcomeClass fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
        "  classDef domainObjectStyle fill:#F5F3FF,stroke:#C4B5FD,color:#17233A,stroke-width:1px;",
        "  classDef evidence fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
        "  classDef gate fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
        "  class outcome outcomeClass;",
        "  class domain_state domainObjectStyle;",
        "  class evidence_record evidence;",
        "  class proof_gate,release_decision,release_claim gate;",
    ]
    if non_goals:
        deferred = diagram_text.deferred_scope_label(non_goals[0], fallback="beyond accepted first path")
        lines.insert(7, f'  deferred["Outside release<br/>{_diagram_label(deferred, limit=112, fallback="Beyond accepted first path")}"] -. not claimed .-> release_decision')
        lines.extend(
            [
                "  classDef laterScopeStyle fill:#FEF2F2,stroke:#FCA5A5,color:#17233A,stroke-width:1px;",
                "  class deferred laterScopeStyle;",
            ]
        )
    return "\n".join(lines) + "\n"


def _boundary_node_for_text(
    value: str,
    *,
    selected_components: list[dict[str, Any]],
    fallback: str,
) -> str:
    component_node = best_component_node_for_text(value, components=selected_components)
    if component_node.startswith("component"):
        try:
            index = int(component_node.replace("component", "", 1))
        except ValueError:
            return fallback
        return _node_id("boundary", index)
    return fallback


def _external_identity_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.split(":", 1)[0].strip()
    deferred_subject = terminal_deferral_subject(text)
    if deferred_subject:
        text = deferred_subject
    text = re.split(
        r"\s+\b(?:supplies|provides|stores|signs|sends|receives|imports|exports)\b\s+",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    return text if 2 <= len(text.split()) <= 7 else ""


def _adapter_node(components: list[dict[str, Any]]) -> str:
    for index, row in enumerate(components[:7], start=1):
        if str(row.get("kind", "")).casefold() == "adapter":
            return _node_id("component", index)
    return ""


def _node_id(prefix: str, index: int) -> str:
    return f"{prefix}{index}"


def _diagram_label(
    value: str,
    *,
    limit: int,
    fallback: str,
    width: int = 30,
    max_lines: int = 4,
) -> str:
    text = str(value or "").strip() or fallback
    return wrapped_flow_label(text, width=width, max_lines=max_lines, limit=limit) or diagram_text.escape_label(fallback)


def _identity_label(value: str, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    if len(text) <= 60:
        return _diagram_label(text, limit=128, fallback=fallback, width=80, max_lines=2)
    return _diagram_label(text, limit=128, fallback=fallback, width=34, max_lines=4)


def _deferred_identity_label(value: str) -> str:
    return _diagram_label(value, limit=128, fallback="Deferred component", width=34, max_lines=4)


__all__ = ["confirmed_diagrams"]

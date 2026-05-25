"""Atlas diagram helpers for confirmed greenfield proposals."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common import mermaid_text
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import finite_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_steps


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
) -> list[dict[str, Any]]:
    all_components = [dict(row) for row in components]
    release_components = [dict(row) for row in active_release_components(all_components)] if all_components else []
    component_rows = [
        {
            "name": str(row["label"]),
            "description": _component_description(row),
        }
        for row in release_components
    ]
    titles = _workstream_titles(label=label, components=release_components, provided=workstream_titles)
    actors = human_actors or [f"{label} product user"]
    externals = external_systems or []
    internals = internal_systems or [str(row.get("label", "")) for row in release_components]
    deferred_scope = non_goals or []
    component_phrase = _component_phrase(release_components)
    actor_phrase = _actor_phrase(actors, label=label)
    story_brief = _brief_story(product_story, fallback=f"{label} gives {actor_phrase} one reviewable first path")
    first_path_brief = _brief_first_path(first_path)
    proof_brief = _brief_proof_boundary(proof_boundary)
    state_label = _brief_object_label(state_object, fallback=f"{label} state")
    evidence_label = _brief_object_label(evidence_record, fallback=f"{label} evidence record")
    return [
        {
            "slug": diagram_slugs["context"],
            "title": "System Context View",
            "kind": "flowchart",
            "summary": _sentence(
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
            "kind": "sequenceDiagram",
            "summary": _sentence(
                (
                    f"This sequence shows what the first release must prove from {actor_phrase} through {component_phrase} "
                    f"to the reviewed outcome: {first_path_brief}"
                )
                if first_path_brief
                else (
                    f"This sequence shows what the first release must prove from {actor_phrase} through {component_phrase} to the reviewed outcome. "
                    "Use this view to check which responsibilities must preserve state, evidence, and blockers."
                )
            ),
            "read_guide": (
                f"Start with the user action. Follow {actor_phrase} through each product responsibility. The release proof must still match: "
                f"{proof_brief or 'the accepted proof boundary'}."
            ),
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": [titles["workflow"], titles["boundary"]],
            "related_components": [str(row["component_id"]) for row in release_components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _sequence_mermaid(label=label, actors=actors, components=release_components, first_path=first_path),
        },
        {
            "slug": diagram_slugs["state_evidence"],
            "title": "State and Evidence View",
            "kind": "flowchart",
            "summary": (
                f"Show how {state_label} becomes reviewable {label.lower()} evidence in the first release. "
                f"The evidence record is {evidence_label}."
            ),
            "read_guide": (
                f"Read this as the {label.lower()} state trail. Start with {actor_phrase}, then follow state, evidence, "
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
                proof_boundary=proof_boundary,
            ),
        },
        {
            "slug": diagram_slugs["component_boundaries"],
            "title": "Component Boundary View",
            "kind": "flowchart",
            "summary": (
                f"Shows which product systems own {label} release 0.0.1 responsibilities and which dependencies stay outside. "
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
            "summary": _sentence(
                f"Trace release ownership for {label} from product-owned components to the accepted proof boundary for {state_label} and {evidence_label}"
            ),
            "read_guide": (
                f"Read from each state or evidence owner toward the proof boundary. A box matters when it owns {label.lower()} data, "
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
            ),
        },
        {
            "slug": diagram_slugs["proof_review"],
            "title": "Release Proof Review",
            "kind": "flowchart",
            "summary": _sentence(
                f"Show which first-path result, state replay, evidence check, access proof, and release decision must exist before {label} trust increases"
            ),
            "read_guide": (
                f"Read this as the {label.lower()} release gate. The product result, {state_label}, {evidence_label}, "
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
            ),
        },
    ]


def _component_description(row: Mapping[str, Any]) -> str:
    responsibility = str(row.get("responsibility", "")).strip()
    boundary = str(row.get("boundary", "")).strip()
    label = str(row.get("label", "")).strip() or "Component"
    kind = _component_kind(row=row, label=label)
    responsibility_text = _responsibility_fragment(label=label, value=responsibility)
    boundary_text = _responsibility_fragment(label=label, value=boundary)
    subject = _component_subject(label=label, responsibility=responsibility_text, boundary=boundary_text)
    lead = _component_lead(label=label, subject=subject, kind=kind)
    review = _component_review_sentence(label=label, subject=subject, kind=kind)
    return f"{_sentence(lead)} {_sentence(review)}"


def _component_kind(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    label_text = label.casefold()
    if re.search(r"\b(adapter|connector|integration|provider|import|source)\b", label_text):
        return "adapter"
    if re.search(r"\b(client|surface|ui|portal|dashboard|app|view)\b", label_text):
        return "client"
    if kind in {"adapter", "client", "service"}:
        return kind
    return "service"


def _component_subject(*, label: str, responsibility: str, boundary: str) -> str:
    for candidate in (responsibility, boundary):
        subject = _clean_component_subject(candidate)
        if subject and not _shallow_component_subject(subject, label=label):
            return subject
    return _label_subject(label)


def _component_lead(*, label: str, subject: str, kind: str) -> str:
    if _looks_like_action_clause(subject):
        clause = finite_action_clause(subject)
        if _component_clause_explains_boundary(clause):
            return clause
        return f"Owns the product responsibility to {_base_initial_action_clause(clause)}"
    if re.match(
        r"^(?:maintains?|owns?|coordinates?|presents?|translates?|records?|tracks?|assembles?|computes?|"
        r"applies?|checks?|captures?|selects?|schedules?|summarizes?)\b",
        subject,
        flags=re.IGNORECASE,
    ):
        return finite_action_clause(subject)
    if kind == "adapter":
        if _is_workflow_like(label, subject):
            return f"Coordinates {subject} across outside systems and product-owned records while preserving provenance"
        return f"Translates {subject} inputs into product-owned records and preserves source provenance"
    if kind == "client":
        return f"Presents {subject} to users and captures the action or decision the product needs next"
    if _is_record_like(label, subject):
        return f"Maintains {subject} as a product-owned record with reviewable history"
    if _is_workflow_like(label, subject):
        return f"Coordinates {subject} so responsibility transfers, blocked states, and recovery paths stay visible"
    if _is_decision_like(label, subject):
        return f"Owns the rules or calculations for {subject}"
    return f"Owns {subject}"


def _component_clause_explains_boundary(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:owns?|owned|responsible|authority|boundary|state|record|version|source of truth|"
            r"receives?|produces?|records?|stores?|tracks?|links?|assembles?|derives?|controls?|"
            r"protects?|coordinates?|maintains?|preserves?)\b",
            value,
            re.IGNORECASE,
        )
    )


def _base_initial_action_clause(value: str) -> str:
    text = str(value or "").strip(" .")
    first, separator, rest = text.partition(" ")
    if not first:
        return text
    base = base_action_clause(f"{first} placeholder").partition(" ")[0] or first
    return f"{base} {rest.strip()}" if separator else base


def _component_review_sentence(*, label: str, subject: str, kind: str) -> str:
    if kind == "adapter":
        return "Reviewers need to see which source supplied the input and what normalized result entered the product"
    if kind == "client":
        return "Reviewers need to see what the user saw, submitted, corrected, or approved and which product state changed after that action"
    if _is_workflow_like(label, subject):
        return "Reviewers need to see each responsibility transfer, failure state, recovery action, and final outcome"
    if _is_record_like(label, subject):
        return "Reviewers need to see the versioned state, source evidence, and decisions that depended on this record"
    if _is_decision_like(label, subject):
        return "Reviewers need to see the inputs, rule version, result, and downstream decision that depended on it"
    return "Reviewers need to see what this boundary receives, produces, records, and makes available next"


def _clean_component_subject(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    text = re.split(r"\b(?:design pressure|domain evidence|relevant behavior)\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = text.split(";", 1)[0]
    text = re.sub(r"\bfor\s+the\s+accepted\s+first\s+(?:release\s+)?path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\band\s+proof\s+boundary\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bneeded\s+by\s+the\s+accepted\s+first\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthe\s+accepted\s+first\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\baccepted\s+first\s+release\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .,:;")
    return _lower_domain_phrase(_strip_component_type_suffix(text), preserve_mixed_case=True)


def _shallow_component_subject(subject: str, *, label: str) -> bool:
    text = subject.casefold().strip(" .")
    if not text:
        return True
    if text == label.casefold():
        return True
    if re.fullmatch(r"(?:this\s+)?(?:component\s+)?responsibility", text):
        return True
    return not re.search(r"[a-z0-9]", text)


def _label_subject(label: str) -> str:
    text = _compact_text(label).strip(" .")
    return _lower_domain_phrase(_strip_component_type_suffix(text) or label, preserve_mixed_case=False)


def _strip_component_type_suffix(value: str) -> str:
    return re.sub(
        r"\b(?:adapter|service|engine|surface|client|module|system|component)\b$",
        "",
        str(value or ""),
        flags=re.IGNORECASE,
    ).strip(" .")


def _lower_domain_phrase(value: str, *, preserve_mixed_case: bool) -> str:
    words = []
    for word in str(value or "").strip().split():
        if word.isupper() and len(word) > 1:
            words.append(word)
        elif preserve_mixed_case and any(char.isupper() for char in word[1:]):
            words.append(word)
        else:
            words.append(word[:1].lower() + word[1:])
    return " ".join(words)


def _is_record_like(label: str, subject: str) -> bool:
    return bool(
        re.search(
            r"\b(records?|ledgers?|stores?|registr(?:y|ies)|trails?|histor(?:y|ies)|snapshots?|status|states?|logs?|index(?:es|)|indices)\b",
            f"{label} {subject}",
            re.IGNORECASE,
        )
    )


def _is_workflow_like(label: str, subject: str) -> bool:
    return bool(
        re.search(
            r"\b(workflow|orchestrat\w*|queue|handoff|review|approval|coordination|routing)\b",
            f"{label} {subject}",
            re.IGNORECASE,
        )
    )


def _is_decision_like(label: str, subject: str) -> bool:
    return bool(
        re.search(
            r"\b(engine|scor\w*|rank\w*|pricing|detect\w*|classif\w*|estimate\w*|resolv\w*|deriv\w*|calculat\w*|rules?)\b",
            f"{label} {subject}",
            re.IGNORECASE,
        )
    )


def _sentence(value: str) -> str:
    text = display_text.strip_inline_markdown_emphasis_tokens(value).replace("`", "")
    text = " ".join(text.strip().split()).rstrip(".")
    if text:
        text = text[:1].upper() + text[1:]
    return f"{text}." if text else ""


def _brief_first_path(value: str) -> str:
    text = _compact_text(value)
    if not text:
        return ""
    text = re.sub(
        r"^the first complete path to prove should be\s*:?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^first complete path to prove should be\s*:?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^the first complete path (?:the product )?(?:must|should) prove (?:before broader scope )?is\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+(?:flow|journey|path)\s*:\s*.*$", "", text, flags=re.IGNORECASE)
    text = re.split(r"\s+\d+\.\s+", text, maxsplit=1)[0]
    text = text.split(". ", 1)[0]
    return _trim(text.strip(" .:"), 300)


def _brief_story(value: str, *, fallback: str) -> str:
    text = _compact_text(value)
    if not text:
        return _trim(fallback, 180)
    text = text.split(". ", 1)[0]
    text = re.sub(r"^product\s+story\s*:?\s*", "", text, flags=re.IGNORECASE).strip(" .:")
    return _trim(text or fallback, 220)


def _brief_proof_boundary(value: str) -> str:
    text = _compact_text(value)
    if not text:
        return ""
    text = re.sub(r"^what would count as evidence[^:]*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^release\s+[A-Za-z0-9_.-]+\s+succeeds\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the release succeeds\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.split(r"\bwhat must not be claimed yet\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = text.split(". ", 1)[0]
    return _trim(text.strip(" .:"), 150)


def _component_phrase(components: list[dict[str, Any]]) -> str:
    names = [str(row.get("label", "")).strip() for row in components[:3] if str(row.get("label", "")).strip()]
    if not names:
        return "the product-owned boundary"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _actor_phrase(actors: list[str], *, label: str) -> str:
    actor = str(actors[0] if actors else "").strip()
    actor = actor.split("—", 1)[0].split(":", 1)[0].strip()
    return actor or f"{label} user"


def _responsibility_fragment(*, label: str, value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    text = _strip_leading_label(label=label, text=text)
    owns_index = text.casefold().find(" owns ")
    if 0 <= owns_index <= 70:
        text = text[owns_index + len(" owns ") :].strip()
    if text.casefold().startswith("owns "):
        text = text[5:].strip()
    if text.casefold().startswith("responsible for "):
        text = text[len("responsible for ") :].strip()
    return text.strip(" .")


def _strip_leading_label(*, label: str, text: str) -> str:
    words = str(label or "").strip().split()
    if not words:
        return text
    for keep in range(len(words), 0, -1):
        pattern = r"^\s*" + r"[\s,/-]+".join(re.escape(word) for word in words[:keep]) + r"\b\s*"
        stripped = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip()
        if stripped != text.strip():
            if re.match(r"^(?:for|of|in|with|to|by|from|through|into|on|at)\b", stripped, flags=re.IGNORECASE):
                return text
            return stripped or text
    return text


def _lower_common_lead(value: str) -> str:
    text = str(value or "").strip()
    first, separator, rest = text.partition(" ")
    if not first:
        return text
    if first.isupper() or any(char.isupper() for char in first[1:]):
        return text
    lowered = first[:1].lower() + first[1:]
    return f"{lowered}{separator}{rest}" if separator else lowered


def _looks_like_action_clause(value: str) -> bool:
    text = str(value or "").strip()
    if re.match(
        r"^(?:review|approval|support)\s+(?:screen|view|surface|page|form|dashboard|queue|desk|center)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return looks_like_action_clause(value)


def _compact_text(value: str) -> str:
    return mermaid_text.clean_mermaid_text(value)


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
        lines.append(f'  {product_node}["{_flow_label(label, limit=64)}<br/>product boundary"]')
    for index, actor in enumerate(actors[:5], start=1):
        node = _node_id("actor", index)
        target = _best_component_node_for_text(actor, components=components) or (product_node if components else first_component)
        lines.append(f'  {node}["{_flow_label(actor, limit=96)}"] --> {target}')
    if not components:
        lines.append(f'  {first_component}["{_flow_label(label, limit=60)}<br/>product core"]')
    for index, component in enumerate(components[:7], start=1):
        node = _node_id("component", index)
        lines.append(f'  {node}["{_flow_label(str(component.get("label", "")), limit=72)}"]')
        if index == 1 and components:
            lines.append(f"  {product_node} --> {node}")
        if index > 1:
            lines.append(f"  {_node_id('component', index - 1)} --> {node}")
    for index, external in enumerate(external_systems[:5], start=1):
        node = _node_id("external", index)
        target_component = _best_component_node_for_text(external, components=components) or _adapter_node(components) or (product_node if components else first_component)
        lines.append(f'  {node}["{_flow_label(external, limit=96)}"] --> {target_component}')
    lines.extend(
        [
            "  classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
            "  classDef boundary fill:#F8FAFC,stroke:#CBD5E1,color:#17233A,stroke-width:1px;",
            "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef external fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  class " + ",".join(_node_id("actor", index) for index in range(1, min(len(actors), 5) + 1)) + " actor;",
            "  class " + ",".join(_node_id("component", index) for index in range(1, max(1, min(len(components), 7)) + 1)) + " service;",
        ]
    )
    if components:
        lines.append(f"  class {product_node} boundary;")
    if external_systems:
        lines.append("  class " + ",".join(_node_id("external", index) for index in range(1, min(len(external_systems), 5) + 1)) + " external;")
    return "\n".join(lines) + "\n"


def _sequence_mermaid(*, label: str, actors: list[str], components: list[dict[str, Any]], first_path: str) -> str:
    selected = [dict(row) for row in active_release_components(components)] if components else []
    selected = selected[:7] or [{"label": f"{label} product core"}]
    actor_rows = actors[:5] or [f"{label} user"]
    lines = [
        "sequenceDiagram",
        "  autonumber",
    ]
    for index, actor in enumerate(actor_rows, start=1):
        lines.append(f"  participant A{index} as {_participant_label(actor)}")
    for index, component in enumerate(selected, start=1):
        lines.append(f"  participant C{index} as {_participant_label(str(component.get('label', 'Component')))}")
    steps = _first_path_steps(first_path)
    if not steps:
        steps = ["Start the accepted first path", "Record product state and evidence", "Review the outcome and blockers"]
    visible_steps = steps[: min(14, max(10, len(selected) + 6))]
    for index, step in enumerate(visible_steps):
        actor_node = _step_actor(step, actors=actor_rows, fallback_index=min(index, len(actor_rows) - 1))
        component_node = _step_component(step, components=selected, fallback_index=min(index, len(selected) - 1))
        lines.append(f"  {actor_node}->>{component_node}: {_step_message(step)}")
        if index + 1 < len(visible_steps):
            next_component_node = _step_component(
                visible_steps[index + 1],
                components=selected,
                fallback_index=min(index + 1, len(selected) - 1),
            )
            if next_component_node != component_node:
                lines.append(f"  {component_node}->>{next_component_node}: {_handoff_message(visible_steps[index + 1])}")
    first_actor = "A1"
    final_component = _step_component(visible_steps[-1], components=selected, fallback_index=min(len(selected) - 1, len(visible_steps) - 1))
    lines.append(f"  {final_component}-->>{first_actor}: show outcome, evidence, and next action")
    return "\n".join(lines) + "\n"


def _best_component_node_for_text(value: str, *, components: list[dict[str, Any]]) -> str:
    scored: list[tuple[int, int, int, str]] = []
    terms = _domain_terms(value)
    if not terms:
        return ""
    for index, component in enumerate(components[:7], start=1):
        label_score = len(terms & _domain_terms(component.get("label", "")))
        component_text = " ".join(
            str(component.get(key, ""))
            for key in ("label", "source_system_description", "responsibility", "boundary")
        )
        body_score = len(terms & _domain_terms(component_text))
        score = label_score * 3 + body_score
        if score:
            scored.append((score, label_score, -index, _node_id("component", index)))
    scored.sort(reverse=True)
    return scored[0][3] if scored else ""


def _first_path_steps(value: str) -> list[str]:
    semantic_steps = list(first_path_steps(value))
    if semantic_steps:
        return semantic_steps
    text = _compact_text(value)
    if not text:
        return []
    action_pattern = (
        r"attaches?|checks?|confirms?|verifies?|opens?|reviews?|reads?|compares?|saves?|records?|creates?|submits?|receives?|assigns?|"
        r"captures?|collects?|completes?|enters?|logs?|gets?|resolves?|moves?|builds?|exports?|imports?|screens?|sees?|supplies?|provides?|routes?|validates?|"
        r"calculates?|chooses?|fetches?|finds?|groups?|highlights?|lets?|links?|orders?|ranks?|selects?|shows?|stores|"
        r"tracks?|decides?|votes?|approves?|rejects?|declines?|requests?|notifies?|publishes?|preserves?|hands?|sends?|schedules|explains?|closes?"
    )
    numbered = [part.strip(" .") for part in re.split(r"(?:^|\s)\d+[.)]\s*", text) if part.strip(" .")]
    if len(numbered) > 1:
        first = numbered[0]
        if ":" in first:
            first = first.rsplit(":", 1)[-1].strip(" .")
        steps = [first, *numbered[1:]] if first else numbered[1:]
        return [_sentence(step).rstrip(".") for step in steps if len(re.findall(r"[A-Za-z0-9]+", step)) >= 3]
    steps = [part.strip(" .") for part in re.split(r"(?<=[.!?])\s+|;\s+", text) if part.strip(" .")]
    expanded: list[str] = []
    for step in steps:
        expanded.extend(
            part.strip(" .")
            for part in re.split(r"\s+and\s+(?=(?:the\s+)?[A-Za-z]+\s+receives?\b)", step)
            if part.strip(" .")
        )
    steps = expanded
    split_steps: list[str] = []
    for step in steps:
        split_steps.extend(
            part.strip(" .")
            for part in re.split(
                rf",\s+(?=(?:and\s+)?(?:(?:{action_pattern})\b|(?:(?:the|a|an)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{action_pattern})\b))",
                step,
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        )
    steps = split_steps
    expanded_steps: list[str] = []
    for step in steps:
        expanded_steps.extend(
            part.strip(" .")
            for part in re.split(
                rf"\s+and\s+(?=(?:(?:{action_pattern})\b|(?:(?:the|a|an)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{action_pattern})\b))",
                step,
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        )
    steps = expanded_steps
    return [_sentence(step).rstrip(".") for step in steps if step]


def _step_actor(step: str, *, actors: list[str], fallback_index: int) -> str:
    if _starts_with_path_action(step):
        return "A1"
    axis_index = _step_axis_actor_index(step, rows=actors)
    if axis_index is not None:
        return f"A{axis_index + 1}"
    target = _best_index_for_text(step, rows=actors, default=fallback_index)
    return f"A{target + 1}"


def _step_axis_actor_index(step: str, *, rows: list[str]) -> int | None:
    text = _compact_text(step).casefold()
    direct_subjects: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("editor", "chair"), ("editor", "chair", "manager", "coordinator", "supervisor", "owner")),
        (("record owner", "clerk"), ("record owner", "clerk", "publisher", "records")),
        (("applicant", "submit", "request"), ("applicant", "submitter", "requester", "customer")),
        (("reviewer", "reviewers"), ("reviewer", "evaluator", "analyst", "inspector", "approver")),
        (("admin", "administrator"), ("admin", "administrator", "config", "maintainer", "support")),
    )
    for step_tokens, actor_tokens in direct_subjects:
        if not any(token in text for token in step_tokens):
            continue
        for index, row in enumerate(rows):
            row_text = row.casefold()
            if any(token in row_text for token in actor_tokens):
                return index
    axes: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("reviewer", "feedback", "score", "quality", "reproducibility"), ("reviewer", "evaluator", "analyst", "inspector", "approver")),
        (("editor", "chair", "screen", "assign", "compare", "decision"), ("editor", "chair", "manager", "coordinator", "supervisor", "owner")),
        (("applicant", "submit", "request", "receives"), ("applicant", "submitter", "requester", "customer")),
        (("admin", "configure", "policy", "template", "deadline", "permission"), ("admin", "administrator", "config", "maintainer", "support")),
    )
    for step_tokens, actor_tokens in axes:
        if not any(token in text for token in step_tokens):
            continue
        for index, row in enumerate(rows):
            row_text = row.casefold()
            if any(token in row_text for token in actor_tokens):
                return index
    return None


def _step_component(step: str, *, components: list[dict[str, Any]], fallback_index: int) -> str:
    label_rows = [str(component.get("label", "")) for component in components]
    rows = [
        " ".join(str(component.get(key, "")) for key in ("label", "source_system_description", "responsibility", "boundary"))
        for component in components
    ]
    axis_index = _step_axis_component_index(step, rows=label_rows)
    if axis_index is not None:
        return f"C{axis_index + 1}"
    target = _best_index_for_text(step, rows=rows, default=fallback_index)
    return f"C{target + 1}"


def _step_axis_component_index(step: str, *, rows: list[str]) -> int | None:
    text = _compact_text(step).casefold()
    entry_capture_action = bool(
        re.search(r"\b(log|logs|enter|enters|capture|captures|edit|edits|correct|corrects)\b", text)
        or re.search(r"\brecords?\b(?!\s+owner)", text)
    )
    if entry_capture_action and re.search(
        r"\b(entry|form|intake|capture|record|episode|observation)\b",
        text,
    ):
        for index, row in enumerate(rows):
            row_text = row.casefold()
            if re.search(r"\b(entry|intake|capture|form|record|episode|observation)\b", row_text):
                return index
    axes: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("import", "imports", "open", "opens", "intake", "required materials", "signal", "report"), ("intake", "import", "adapter", "request", "signal", "triage", "material")),
        (("verify", "verifies", "identity", "proof", "required materials", "current state"), ("intake", "import", "adapter", "request", "signal", "material", "baseline")),
        (("eligibility", "rule", "policy", "coverage", "exclusion"), ("eligibility", "screening", "rules", "coverage", "decision", "policy")),
        (("diagnostic", "diagnostics", "photo", "photos", "checklist", "finding", "findings"), ("evidence", "diagnostics", "checklist", "capture", "review")),
        (("price", "pricing", "cost", "quote"), ("pricing", "quote", "cost", "evidence")),
        (("receiving", "received", "variance", "variance explanation"), ("receiving", "variance", "review")),
        (("estimate", "estimated", "budget", "quantity", "recommendation", "recommended"), ("estimate", "quote", "cost", "budget", "recommendation", "quantity")),
        (("assign", "assigned", "assignment", "schedule", "schedules", "window", "conflict"), ("assignment", "schedule", "assignee", "conflict", "permission")),
        (("screen", "screens", "conflict", "conflicts"), ("assignment", "conflict", "permission", "access", "role")),
        (("handoff", "hands", "sends", "provider", "recipient", "approved payload", "external handoff"), ("handoff", "provider", "recipient", "order")),
        (("approval", "approve", "approved", "reject", "rejection", "approver"), ("approval", "ledger", "approver", "rationale")),
        (("notify", "notifies", "message", "communication", "terms", "response"), ("communication", "notification", "message", "log", "response")),
        (("follow-up", "followup", "required action", "due date"), ("follow-up", "followup", "action", "planner")),
        (("publish", "publishes", "public", "summary", "redacted", "publication"), ("publication", "public", "summary", "audit")),
        (("compares reviews", "compare reviews", "editor compares", "editorial decision", "makes a decision", "request revisions", "requests revisions"), ("decision", "workflow", "editorial", "revision")),
        (("close", "closes", "closure", "audit", "history", "replay"), ("closure", "audit", "record", "trail", "history", "retention")),
        (("publish", "published", "audit", "history", "replay"), ("audit", "trail", "history", "retention", "source-backed")),
        (("claim", "claims", "citation", "citations", "lineage", "traceability", "source-backed"), ("audit", "trail", "claim", "claims", "citation", "lineage", "source-backed")),
        (("open", "opens", "packet", "intake"), ("intake", "packet", "submission", "version")),
        (("onboarding", "onboard", "consent", "eligibility", "disclosure"), ("onboarding", "consent", "signup", "registration", "profile")),
        (("log", "logs", "logging"), ("logging", "log", "daily", "activity", "tracking", "progress")),
        (("reminder", "follow-up", "missed entry", "stale work", "safety", "guardrail"), ("reminder", "notification", "safety", "guardrail")),
        (("trend", "weekly", "check-in", "checkin", "off track", "progress"), ("trend", "weekly", "check-in", "review", "analytics")),
        (("baseline", "measurement", "metric", "initial value", "starting state"), ("baseline", "measurement", "capture", "metric")),
        (("target", "plan", "computed", "recomputed", "recompute", "adjustment"), ("target", "plan", "generation", "recommendation")),
        (("enter", "enters", "origin", "destination", "preference", "departure time"), ("intake", "capture", "adapter", "request", "entry")),
        (("calculate", "calculated"), ("calculation", "pricing", "quote", "cost", "estimate", "recommendation", "engine")),
        (("calculate", "price", "pricing", "cost", "quote"), ("quote", "pricing", "cost", "estimate")),
        (("fetch", "candidate options", "schedule", "departure", "transfer", "service alert"), ("schedule", "candidate", "option", "service")),
        (("rank", "ranks", "ranking", "highlight", "cheapest", "alternative", "alternatives"), ("ranking", "rank", "option", "engine")),
        (("choose", "select", "selected", "stores", "comparison evidence", "visible result"), ("review", "surface", "comparison", "selected")),
        (("context", "map", "source freshness", "freshness"), ("context", "location", "map", "viewer")),
        (("question", "follow-up", "followup", "response", "answer", "unresolved"), ("question", "response", "tracker", "issue", "follow-up")),
        (("compare", "comparison", "recommendation", "readiness"), ("comparison", "dashboard", "recommendation", "readiness")),
        (("feedback", "comment", "theme", "group"), ("feedback", "comment", "theme", "grouping")),
        (("feedback", "score", "scores", "rubric", "structured", "strength", "weakness", "reproducibility"), ("form", "scoring", "rubric", "assessment")),
        (("submit", "submission", "upload", "file"), ("submission", "intake", "version", "file")),
        (("screen", "assign", "conflict", "reviewer"), ("assignment", "conflict", "permission", "access", "role")),
        (("receives", "received", "notified", "notification"), ("notification", "deadline", "status", "dashboard", "view")),
        (("rationale", "vote", "motion", "final outcome", "outcome"), ("rationale", "vote", "outcome", "record")),
        (("decision", "decide", "approval", "reject"), ("decision", "approval", "outcome", "rationale", "record")),
        (("revision", "revise", "revisions", "resubmit"), ("revision", "round", "resubmission", "response")),
        (("deadline", "reminder", "overdue"), ("notification", "deadline", "status", "dashboard", "view")),
    )
    if re.search(r"\b(preserve|preserves|audit|history|replay)\b", text):
        for index, row in enumerate(rows):
            if any(_has_word(row, token) for token in ("audit", "trail", "history", "retention", "closure", "publication")):
                return index
        if rows:
            return len(rows) - 1
    if re.search(r"\b(calculat\w*|comput\w*|deriv\w*|validat\w*)\b", text) and _has_word(text, "evidence"):
        for index, row in enumerate(rows):
            if any(_has_word(row, token) for token in ("evidence", "quote", "pricing", "calculation", "estimate")):
                return index
    for step_tokens, component_tokens in axes:
        if not any(token in text for token in step_tokens):
            continue
        for index, row in enumerate(rows):
            if any(_has_word(row, token) for token in component_tokens):
                return index
    return None


def _has_word(value: str, token: str) -> bool:
    return bool(re.search(rf"\b{re.escape(token.casefold())}(?:s|es|ing|ed)?\b", value.casefold()))


def _best_index_for_text(value: str, *, rows: list[str], default: int) -> int:
    terms = _domain_terms(value)
    scored: list[tuple[int, int]] = []
    for index, row in enumerate(rows):
        score = len(terms & _domain_terms(row))
        if score:
            scored.append((score, -index))
    if not scored:
        return max(0, min(default, max(0, len(rows) - 1)))
    scored.sort(reverse=True)
    return -scored[0][1]


def _starts_with_path_action(step: str) -> bool:
    text = re.sub(r"^(?:and|then)\s+", "", _compact_text(step), flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?product\s+", "", text, flags=re.IGNORECASE)
    return bool(
        re.match(
            r"^(?:attaches?|checks?|confirms?|verifies?|opens?|reviews?|reads?|compares?|saves?|records?|creates?|submits?|receives?|assigns?|captures?|collects?|completes?|enters?|logs?|gets?|resolves?|moves?|exports?|imports?|screens?|routes?|validates?|calculates?|chooses?|fetches?|finds?|groups?|highlights?|lets?|links?|orders?|ranks?|selects?|shows?|sees?|stores|tracks?|decides?|votes?|approves?|rejects?|declines?|requests?|notifies?|publishes?|preserves?|hands?|sends?|schedules|explains?|closes?)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _step_message(value: str) -> str:
    text = re.sub(r"^(?:and|then)\s+", "", _strip_dangling_tail(_trim(value, 150)), flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?product\s+", "", text, flags=re.IGNORECASE)
    if text:
        text = text[:1].upper() + text[1:]
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(text, width=34, max_lines=4, limit=160)) or "advance accepted path"


def _handoff_message(next_step: str) -> str:
    focus = re.sub(r"^(?:and|then)\s+", "", _strip_dangling_tail(_trim(next_step, 90)), flags=re.IGNORECASE)
    focus = re.sub(r"^(?:a|an|the)\s+", "", focus, flags=re.IGNORECASE).strip(" .")
    focus = re.sub(r"^(?:the\s+)?product\s+", "", focus, flags=re.IGNORECASE).strip(" .")
    if not focus:
        focus = "next accepted action"
    focus = _imperative_handoff_focus(focus)
    if _starts_with_path_action(focus):
        label = f"next step: {focus[:1].lower()}{focus[1:]}"
    else:
        label = f"handoff: {focus[:1].lower()}{focus[1:]}"
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(label, width=34, max_lines=4, limit=160))


def _imperative_handoff_focus(value: str) -> str:
    text = _compact_text(value).strip(" .")
    replacements = {
        "adds": "add",
        "attaches": "attach",
        "assigns": "assign",
        "captures": "capture",
        "calculates": "calculate",
        "checks": "check",
        "chooses": "choose",
        "closes": "close",
        "collects": "collect",
        "compares": "compare",
        "completes": "complete",
        "confirms": "confirm",
        "creates": "create",
        "decides": "decide",
        "enters": "enter",
        "exports": "export",
        "fetches": "fetch",
        "finds": "find",
        "gets": "get",
        "groups": "group",
        "highlights": "highlight",
        "imports": "import",
        "notifies": "notify",
        "lets": "let",
        "links": "link",
        "logs": "log",
        "opens": "open",
        "orders": "order",
        "publishes": "publish",
        "ranks": "rank",
        "reads": "read",
        "receives": "receive",
        "records": "record",
        "requests": "request",
        "resolves": "resolve",
        "reviews": "review",
        "routes": "route",
        "saves": "save",
        "sees": "see",
        "selects": "select",
        "shows": "show",
        "screens": "screen",
        "sends": "send",
        "schedules": "schedule",
        "stores": "store",
        "submits": "submit",
        "tracks": "track",
        "validates": "validate",
        "verifies": "verify",
        "votes": "vote",
        "explains": "explain",
        "hands": "hand",
        "preserves": "preserve",
    }
    first, sep, rest = text.partition(" ")
    replacement = replacements.get(first.casefold())
    if replacement:
        text = f"{replacement}{sep}{rest}".strip()
    for source, target in replacements.items():
        text = re.sub(rf"([,;]\s+){re.escape(source)}\b", rf"\1{target}", text, flags=re.IGNORECASE)
    return text


def _domain_terms(value: object) -> set[str]:
    stop = {
        "accepted",
        "actor",
        "and",
        "app",
        "application",
        "boundary",
        "component",
        "evidence",
        "first",
        "from",
        "outcome",
        "path",
        "product",
        "proof",
        "record",
        "release",
        "result",
        "state",
        "system",
        "that",
        "the",
        "through",
        "with",
    }
    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _compact_text(str(value)).casefold()):
        token = raw.strip("-_")
        if token.endswith("ies") and len(token) > 5:
            token = f"{token[:-3]}y"
        elif token.endswith("ing") and len(token) > 6:
            token = token[:-3]
        elif token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
            token = token[:-1]
        if len(token) >= 4 and token not in stop:
            terms.add(token)
    return terms


def _ownership_mermaid(
    *,
    label: str,
    components: list[dict[str, Any]],
    internal_systems: list[str],
    proof_boundary: str,
) -> str:
    lines = ["flowchart TB"]
    if not components:
        lines.append(f'  product["{_flow_label(label, limit=96)}<br/>product boundary"] --> proof["Release<br/>proof"]')
    for index, component in enumerate(components[:7], start=1):
        node = _node_id("owner", index)
        label_text = str(component.get("label", "")) or (internal_systems[index - 1] if index <= len(internal_systems) else f"Component {index}")
        lines.append(f'  {node}["{_flow_label(label_text, limit=112)}"]')
        if index > 1:
            lines.append(f"  {_node_id('owner', index - 1)} --> {node}")
    proof_node = _node_id("proof", 1)
    lines.append(f'  {proof_node}["Proof boundary<br/>{_escape_label(_trim(proof_boundary, 52))}"]')
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
    proof_boundary: str,
) -> str:
    first_owner = _component_label(components, 0, fallback="First path owner")
    evidence_owner = _component_label_for_text(evidence_record, components=components) or _component_label(components, min(2, max(0, len(components) - 1)), fallback="Evidence owner")
    review_owner = _component_label(components, len(components) - 1, fallback="Review owner")
    actor_label = _short_label(_actor_phrase(actors, label=label))
    proof_label = _proof_checkpoint_label(_brief_proof_boundary(proof_boundary)) or "source-backed release check"
    lines = [
        "flowchart LR",
        f'  action["First action<br/>{actor_label}"] --> owner1["{_escape_label(first_owner)}"]',
        f'  owner1 --> state["State object<br/>{_escape_label(_trim(state_object, 62))}"]',
        f'  state --> owner2["{_escape_label(evidence_owner)}"]',
        f'  owner2 --> evidence["Evidence record<br/>{_escape_label(_trim(evidence_record, 62))}"]',
        f'  evidence --> owner3["{_escape_label(review_owner)}"]',
        f'  owner3 --> review["Proof check<br/>{_escape_label(_trim(proof_label, 62))}"]',
        '  review --> correction["Blocked or corrected<br/>path stays visible"]',
        "  classDef action fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
        "  classDef owner fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
        "  classDef state fill:#F5F3FF,stroke:#C4B5FD,color:#17233A,stroke-width:1px;",
        "  classDef evidence fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
        "  classDef review fill:#F8FAFC,stroke:#CBD5E1,color:#17233A,stroke-width:1px;",
        "  class action action;",
        "  class owner1,owner2,owner3 owner;",
        "  class state state;",
        "  class evidence evidence;",
        "  class review,correction review;",
    ]
    return "\n".join(lines) + "\n"


def _component_label_for_text(value: str, *, components: list[dict[str, Any]]) -> str:
    node = _best_component_node_for_text(value, components=components)
    if not node.startswith("component"):
        return ""
    try:
        index = int(node.replace("component", "", 1)) - 1
    except ValueError:
        return ""
    return _component_label(components, index, fallback="")


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
    lines = ["flowchart TB", f'  subgraph product["{_escape_label(_trim(label, 70))}<br/>release boundary"]']
    for index, component in enumerate(selected_components, start=1):
        node = _node_id("boundary", index)
        lines.append(f'    {node}["{_escape_label(_trim(str(component.get("label", "")) or f"Component {index}", 64))}"]')
        if index > 1:
            lines.append(f"    {_node_id('boundary', index - 1)} --> {node}")
    lines.append("  end")
    first_node = _node_id("boundary", 1)
    for index, external in enumerate(external_systems[:3], start=1):
        node = _node_id("input", index)
        target = _boundary_node_for_text(external, selected_components=selected_components, fallback=first_node)
        lines.append(f'  {node}["External input<br/>{_short_label(external)}"] --> {target}')
    deferred_items = [
        *(str(component.get("label", "")).strip() for component in deferred_components if str(component.get("label", "")).strip()),
        *non_goals,
    ]
    for index, item in enumerate(deferred_items[:3], start=1):
        node = _node_id("deferred", index)
        target = _boundary_node_for_text(item, selected_components=selected_components, fallback=first_node)
        lines.append(f'  {node}["Deferred scope<br/>{_escape_label(_trim(item, 64))}"] -. later .-> {target}')
    lines.extend(
        [
            "  classDef product fill:#F8FAFC,stroke:#CBD5E1,color:#17233A,stroke-width:1px;",
            "  classDef owned fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef external fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  classDef deferred fill:#FEF2F2,stroke:#FCA5A5,color:#17233A,stroke-width:1px;",
            "  class " + ",".join(_node_id("boundary", index) for index in range(1, len(selected_components) + 1)) + " owned;",
        ]
    )
    if external_systems:
        lines.append("  class " + ",".join(_node_id("input", index) for index in range(1, min(len(external_systems), 3) + 1)) + " external;")
    if deferred_items:
        lines.append("  class " + ",".join(_node_id("deferred", index) for index in range(1, min(len(deferred_items), 3) + 1)) + " deferred;")
    return "\n".join(lines) + "\n"


def _proof_review_mermaid(
    *,
    state_object: str,
    evidence_record: str,
    proof_boundary: str,
    components: list[dict[str, Any]],
    non_goals: list[str],
) -> str:
    proof_text = _brief_proof_boundary(proof_boundary) or "accepted proof boundary"
    proof_label = _proof_checkpoint_label(proof_text) or "first-path evidence, state replay, blocked-path proof"
    evidence_label = _proof_evidence_label(components=components, fallback=evidence_record)
    lines = [
        "flowchart LR",
        '  result["First-path<br/>outcome"] --> state',
        f'  state["Domain state<br/>{_escape_label(_trim(state_object, 58))}"] --> evidence',
        f'  evidence["Evidence record<br/>{_escape_label(_trim(evidence_label, 72))}"] --> validation',
        f'  validation["Proof checkpoint<br/>{_escape_label(proof_label)}"] --> decision',
        '  decision["Release decision<br/>accept, revise, or block"] --> release',
        '  release["Release claim<br/>stays inside proof boundary"]',
        "  classDef result fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
        "  classDef state fill:#F5F3FF,stroke:#C4B5FD,color:#17233A,stroke-width:1px;",
        "  classDef evidence fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
        "  classDef gate fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
        "  class result result;",
        "  class state state;",
        "  class evidence evidence;",
        "  class validation,decision,release gate;",
    ]
    if non_goals:
        deferred = _trim(non_goals[0], 64)
        lines.insert(7, f'  deferred["Outside release<br/>{_escape_label(deferred)}"] -. not claimed .-> decision')
        lines.extend(
            [
                "  classDef deferred fill:#FEF2F2,stroke:#FCA5A5,color:#17233A,stroke-width:1px;",
                "  class deferred deferred;",
            ]
        )
    return "\n".join(lines) + "\n"


def _proof_evidence_label(*, components: list[dict[str, Any]], fallback: str) -> str:
    for component in components:
        label = str(component.get("label", "")).strip()
        if re.search(r"\b(audit|trail|history|evidence|source-backed|version|provenance)\b", label, re.IGNORECASE):
            return f"{label} proof record"
    for component in components:
        label = str(component.get("label", "")).strip()
        if re.search(r"\b(record|log|attachment|source)\b", label, re.IGNORECASE):
            return f"{label} proof record"
    return fallback


def _proof_checkpoint_label(value: str) -> str:
    stop = {
        "accepted",
        "against",
        "actor",
        "action",
        "adjusted",
        "boundary",
        "can",
        "check",
        "choose",
        "complete",
        "completed",
        "completes",
        "create",
        "created",
        "done",
        "enriched",
        "enter",
        "enters",
        "finalized",
        "first",
        "gets",
        "imported",
        "lets",
        "losing",
        "operation",
        "operations",
        "operator",
        "path",
        "person",
        "published",
        "receive",
        "received",
        "receives",
        "release",
        "representative",
        "review",
        "reviewed",
        "reviewer",
        "reviews",
        "route",
        "replayed",
        "routed",
        "select",
        "selected",
        "start",
        "started",
        "starting",
        "succeeds",
        "through",
        "user",
        "uses",
        "view",
        "views",
        "when",
        "with",
        "without",
    }
    terms: list[str] = []
    seen: set[str] = set()
    raw_terms = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _compact_text(value).casefold())
    action_subject_verbs = {"choose", "compare", "complete", "enter", "import", "open", "record", "review", "select", "submit"}
    for position, raw in enumerate(raw_terms):
        token = raw.strip("-_")
        next_word = raw_terms[position + 1] if position + 1 < len(raw_terms) else ""
        next_action = raw_terms[position + 2] if position + 2 < len(raw_terms) else ""
        if next_word in {"can", "may", "must", "should", "will"} and next_action in action_subject_verbs:
            continue
        if token.endswith("ies") and len(token) > 5:
            token = f"{token[:-3]}y"
        elif token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
            token = token[:-1]
        if len(token) < 4 or token in stop or token in seen:
            continue
        seen.add(token)
        terms.append(token)
        if len(terms) >= 7:
            break
    if len(terms) < 3:
        return ""
    return ", ".join(terms)


def _boundary_node_for_text(
    value: str,
    *,
    selected_components: list[dict[str, Any]],
    fallback: str,
) -> str:
    component_node = _best_component_node_for_text(value, components=selected_components)
    if component_node.startswith("component"):
        try:
            index = int(component_node.replace("component", "", 1))
        except ValueError:
            return fallback
        return _node_id("boundary", index)
    return fallback


def _workstream_titles(
    *,
    label: str,
    components: list[dict[str, Any]],
    provided: Mapping[str, str] | None,
) -> dict[str, str]:
    first_component = _component_label(components, 0, fallback=label)
    second_component = _component_label(components, 1, fallback=label)
    third_component = _component_label(components, 2, fallback=label)
    titles = {
        "program": f"Establish {label} Program",
        "workflow": f"Prove {first_component}",
        "boundary": f"Define {second_component} Boundary",
        "proof": f"Prepare {third_component} Release Proof",
    }
    for key, value in (provided or {}).items():
        if key in titles and str(value).strip():
            titles[key] = str(value).strip()
    return titles


def _brief_object_label(value: str, *, fallback: str) -> str:
    text = _compact_text(value)
    if not text:
        return fallback
    first = text.split("—", 1)[0].split(". ", 1)[0].strip(" .:")
    patterns = (
        r"\b(?:primary\s+)?state\s+object\s+is\s+(?:a|an|the)?\s*(?P<label>[^.;:]+?)(?:\s+(?:that|which|who|where|tracks?|records?|stores?|captures?|moves?|starts?)\b|$)",
        r"^(?:a|an|the)\s+(?P<label>[A-Za-z][A-Za-z0-9 _/-]{2,80}?)\s+(?:tracks?|records?|stores?|captures?|moves?|starts?|keeps?)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, first, flags=re.IGNORECASE)
        if match:
            candidate = _compact_text(match.group("label")).strip(" .:")
            if candidate:
                return _trim(candidate, 72)
    first = re.sub(r"^(?:a|an|the)\s+", "", first, flags=re.IGNORECASE)
    return _trim(first or fallback, 72)


def _component_label(components: list[dict[str, Any]], index: int, *, fallback: str) -> str:
    if index < len(components):
        label = str(components[index].get("label", "")).strip()
        if label:
            return _trim(label, 72)
    return fallback


def _adapter_node(components: list[dict[str, Any]]) -> str:
    for index, row in enumerate(components[:7], start=1):
        if str(row.get("kind", "")).casefold() == "adapter":
            return _node_id("component", index)
    return ""


def _node_id(prefix: str, index: int) -> str:
    return f"{prefix}{index}"


def _short_label(value: str) -> str:
    text = str(value or "").split("—", 1)[0].split(":", 1)[0].strip() or "Actor"
    return _escape_label(_trim(text, 72))


def _flow_label(value: str, *, limit: int) -> str:
    text = str(value or "").split("—", 1)[0].split(":", 1)[0].strip() or "Item"
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(text, width=30, max_lines=4, limit=limit))


def _participant_label(value: str) -> str:
    text = str(value or "").split("—", 1)[0].split(":", 1)[0].strip()
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(text, width=24, max_lines=5, limit=120) or "Participant")


def _sequence_text(value: str) -> str:
    return _without_ellipsis(mermaid_text.wrap_sequence_note(_brief_first_path(value) or value))


def _escape_label(value: str) -> str:
    return mermaid_text.escape_mermaid_label(value)


def _without_ellipsis(value: str) -> str:
    return str(value or "").replace("…", "").replace("...", "").rstrip(" ,;:")


def _trim(value: str, limit: int) -> str:
    text = _compact_text(value)
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    return _strip_dangling_tail(clipped)


def _strip_dangling_tail(value: str) -> str:
    text = _compact_text(value).rstrip(" ,;:.")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|can|for|from|if|in|into|lets|must|of|on|or|should|the|tied|to|when|while|with|without)$",
            "",
            text,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:.")
        if cleaned == text:
            return cleaned
        text = cleaned


__all__ = ["confirmed_diagrams"]

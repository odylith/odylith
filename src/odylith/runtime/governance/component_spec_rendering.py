"""Render Registry component specs from concrete ownership contracts."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common import display_text
from odylith.runtime.common.prose_grammar import finite_action_clause
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    boundary_from_contract,
    dependencies_from_contract,
    interfaces_from_contract,
    responsibility_from_contract,
    risks_from_contract,
    validation_from_contract,
)


def sentence_fragment(value: str) -> str:
    text = display_text.strip_inline_markdown_emphasis_tokens(value)
    return " ".join(text.strip().split()).rstrip(".")


def build_component_spec(
    *,
    component_id: str,
    label: str,
    path: str,
    kind: str,
    status: str,
    sources: Sequence[str],
    workstreams: Sequence[str],
    diagrams: Sequence[str] = (),
    responsibility: str = "",
    boundary: str = "",
    dependencies: Sequence[str] = (),
    interfaces: Sequence[str] = (),
    validation: Sequence[str] = (),
    risks: Sequence[str] = (),
    qualification: str = "candidate",
    implementation_handoff: Mapping[str, Any] | None = None,
    component_contract: Mapping[str, Any] | None = None,
) -> str:
    handoff = implementation_handoff or {}
    contract = component_contract or {}
    has_contract = bool(contract)
    profile = _kind_profile(kind)
    normalized_sources = [str(item).strip() for item in sources if str(item).strip()]
    workstream_ids = [str(item).strip().upper() for item in workstreams if str(item).strip()]
    diagram_ids = [str(item).strip().upper() for item in diagrams if str(item).strip()]
    first_workstream = _handoff_text(handoff, "workstream_id") or (workstream_ids[0] if workstream_ids else "")
    first_workstream_title = _handoff_text(handoff, "workstream_title")
    first_slice = _handoff_text(handoff, "first_slice")
    wave_label = _handoff_text(handoff, "wave_label")
    wave_status = _handoff_text(handoff, "wave_status")
    release_selector = _handoff_text(handoff, "release_selector")
    handoff_validation = _handoff_list(handoff, "validation_gates")
    handoff_commands = _handoff_list(handoff, "verification_commands")

    responsibility_source = responsibility_from_contract(label, contract) if has_contract else responsibility
    responsibility_text = sentence_fragment(responsibility_source)
    responsibility_line = responsibility_text if has_contract else _responsibility_sentence(responsibility_text, default_verb=profile["default_verb"])
    boundary_source = boundary_from_contract(label, contract) if has_contract else boundary
    boundary_text = sentence_fragment(boundary_source) or responsibility_text
    evidence_text = _evidence_text(normalized_sources=normalized_sources, path=path)
    plan_link = _plan_link(first_workstream)
    related_workstreams = ", ".join(f"`{item}`" for item in workstream_ids) if workstream_ids else "none yet"
    related_diagrams = ", ".join(f"`{item}`" for item in diagram_ids) if diagram_ids else "none yet"
    proof_lines = _component_proof_lines(
        validation=validation_from_contract(contract) if has_contract else validation,
        handoff_validation=handoff_validation,
        label=label,
        boundary=boundary_text,
        responsibility=responsibility_line or responsibility_text,
    )
    interface_lines = _unique_lines(interfaces_from_contract(contract) if has_contract else interfaces or (profile["default_interface"],))
    dependency_lines = _dependency_lines(dependencies_from_contract(contract) if has_contract else dependencies or (profile["default_dependency"],))
    risk_lines = _unique_lines(risks_from_contract(label, contract) if has_contract else risks or (profile["default_risk"],))
    outside_boundary = _contract_outside_boundary_lines(contract) if has_contract else _outside_boundary_lines(boundary=boundary_text, profile=profile)
    contract_summary = (
        _contract_summary_from_contract(label=label, contract=contract)
        if has_contract
        else _contract_summary(
            label=label,
            responsibility=responsibility_line or responsibility_text,
            boundary=boundary_text,
            profile=profile,
            interfaces=interface_lines,
            dependencies=dependency_lines,
            proof_lines=proof_lines,
        )
    )
    role_paragraphs = (
        _component_contract_role_paragraphs(label=label, profile=profile, contract=contract)
        if has_contract
        else _component_role_paragraphs(
            label=label,
            profile=profile,
            responsibility=responsibility_line or responsibility_text,
            dependencies=dependency_lines,
            validation=proof_lines,
        )
    )

    return "\n".join(
        [
            f"# {label}",
            "",
            f"> Component planning record for `{component_id}`. {evidence_text}",
            "",
            "## Component Snapshot",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Component ID | `{component_id}` |",
            f"| Kind | `{kind}` |",
            f"| Status | `{status}` |",
            f"| Qualification | `{qualification}` |",
            f"| Evidence | {', '.join(normalized_sources) if normalized_sources else 'manifest'} |",
            f"| First source boundary | `{path}` |" if path else "| First source boundary | To be selected by the first technical plan |",
            f"| Workstreams | {related_workstreams} |",
            f"| Diagrams | {related_diagrams} |",
            "",
            "## Component Role",
            "",
            "\n\n".join(role_paragraphs),
            "",
            f"## {profile['boundary_heading']}",
            "",
            _paragraph(
                boundary_text
                or "The first technical plan must name the runtime, data, or interaction boundary before source writes."
            ),
            "",
            "### Owns",
            "",
            _bullet_lines((responsibility_line,) if responsibility_line else (profile["default_owns"],)),
            "",
            "### Outside Boundary",
            "",
            _bullet_lines(outside_boundary),
            "",
            f"## {profile['contract_heading']}",
            "",
            _paragraph(contract_summary),
            "",
            f"### {profile['interface_heading']}",
            "",
            _bullet_lines(interface_lines),
            "",
            "### Collaborators And Dependencies",
            "",
            _bullet_lines(dependency_lines),
            "",
            f"## {profile['proof_heading']}",
            "",
            _proof_table(proof_lines or (profile["default_validation"],), commands=handoff_commands),
            "",
            f"## {profile['risk_heading']}",
            "",
            _bullet_lines(risk_lines),
            "",
            f"## {profile['runway_heading']}",
            "",
            _runway_lines(
                path=path,
                first_workstream=first_workstream,
                first_workstream_title=first_workstream_title,
                wave_label=wave_label,
                wave_status=wave_status,
                release_selector=release_selector,
                first_slice=first_slice,
                label=label,
                local_proof=proof_lines[0] if proof_lines else "",
            ),
            "",
            "### Definition Of Done",
            "",
            _bullet_lines(_promotion_bar_lines(label=label, path=path, first_workstream=first_workstream, proof_lines=proof_lines)),
            "",
            "### Operator Verification",
            "",
            _command_lines(handoff_commands),
            "",
            "## Feature History",
            "",
            f"- {dt.date.today().isoformat()}: Registered `{component_id}` as a candidate component{plan_link}.",
            "",
        ]
    )


def _kind_profile(kind: str) -> dict[str, str]:
    token = str(kind or "").casefold()
    if token in {"application", "client", "surface", "ui", "frontend", "web"}:
        return {
            "boundary_heading": "Interaction Boundary",
            "contract_heading": "Interaction Contract",
            "interface_heading": "Screens, Commands, And Visible States",
            "proof_heading": "User-State Proof Matrix",
            "risk_heading": "Experience Failure Modes",
            "runway_heading": "First Interaction Slice",
            "role_noun": "human-facing interaction surface",
            "default_verb": "owns",
            "contract_intro": "This component owns what a human can initiate, inspect, recover from, and trust in the first slice.",
            "default_owns": "The first user-visible path, including normal, empty, degraded, and error states.",
            "default_interface": "A route, command, or view contract selected by the first implementation plan.",
            "default_dependency": "The domain contract that supplies state and the verification harness that proves visible behavior.",
            "default_validation": "Behavior proof covers the normal path plus at least one empty or degraded state.",
            "default_risk": "A misleading visible state can make an incomplete or unsafe workflow look production-ready.",
            "default_outside": "Domain calculations, persistence, provider adapters, and release proof unless this component boundary explicitly owns them.",
        }
    if token in {"tooling", "test", "harness"}:
        return {
            "boundary_heading": "Proof Harness Boundary",
            "contract_heading": "Harness Contract",
            "interface_heading": "Fixtures, Commands, And Reports",
            "proof_heading": "Release Proof Matrix",
            "risk_heading": "Harness Failure Modes",
            "runway_heading": "First Proof Slice",
            "role_noun": "proof and validation boundary",
            "default_verb": "proves",
            "contract_intro": "This component owns deterministic evidence that the first release claim is repeatable.",
            "default_owns": "Local fixtures, proof commands, evidence output, and release-readiness checks.",
            "default_interface": "A smoke, test, or validation command with deterministic inputs and readable output.",
            "default_dependency": "The first runtime slice and domain contract it proves; no production systems by default.",
            "default_validation": "The proof command fails closed on missing fixtures, stale surfaces, or skipped assertions.",
            "default_risk": "Weak or non-deterministic proof can let proposal text outrun implementation evidence.",
            "default_outside": "Production runtime behavior, live credentials, external systems, and source ownership outside proof fixtures.",
        }
    return {
        "boundary_heading": "Runtime Boundary",
        "contract_heading": "Runtime Contract",
        "interface_heading": "APIs, Schemas, Events, Or Module Contracts",
        "proof_heading": "Contract Proof Matrix",
        "risk_heading": "Runtime Failure Modes",
        "runway_heading": "First Runtime Slice",
        "role_noun": "runtime ownership boundary",
        "default_verb": "owns",
        "contract_intro": "This component owns the state, invariants, and integration contract other slices depend on.",
        "default_owns": "The first domain state model, commands, queries, invariants, and integration handoff.",
        "default_interface": "A command, query, schema, module, or event contract selected by the first technical plan.",
        "default_dependency": "Confirmed first-workflow semantics; external providers stay outside the boundary until planned.",
        "default_validation": "Valid state transition, invalid input rejection, and retry behavior are proven.",
        "default_risk": "A loose runtime boundary can couple adjacent slices or hide invariant failures.",
        "default_outside": "Presentation, deployment, proof harnesses, and external providers unless this component boundary explicitly owns them.",
    }


def _component_role_paragraphs(
    *,
    label: str,
    profile: Mapping[str, str],
    responsibility: str,
    dependencies: Sequence[str],
    validation: Sequence[str],
) -> tuple[str, ...]:
    role = profile.get("role_noun", "ownership boundary")
    paragraphs = [
        _paragraph(
            f"{label} is a {role}. "
            + (
                f"It {_lower_first(responsibility)}"
                if responsibility
                else "It needs the first implementation plan to name the concrete responsibility it owns"
            )
        )
    ]
    proof_bits = []
    if validation:
        proof_bits.append(f"Proof focus: {_lower_first(_strip_proof_prefix(validation[0]))}")
    if dependencies:
        proof_bits.append(f"Collaboration focus: {dependencies[0]}")
    if proof_bits:
        paragraphs.append(" ".join(_paragraph(bit) for bit in proof_bits if sentence_fragment(bit)))
    return tuple(paragraphs)


def _component_contract_role_paragraphs(
    *,
    label: str,
    profile: Mapping[str, str],
    contract: Mapping[str, Any],
) -> tuple[str, ...]:
    role = profile.get("role_noun", "ownership boundary")
    owned = sentence_fragment(str(contract.get("owned_state", "")))
    inputs = sentence_fragment(str(contract.get("accepted_inputs", "")))
    outputs = sentence_fragment(str(contract.get("produced_outputs", "")))
    proof = _first_text(contract.get("local_proof"))
    first = (
        f"{label} is a {role}. It owns {_lower_first(owned)}, accepts {_lower_first(inputs)}, and produces {_lower_first(outputs)}"
        if owned and inputs and outputs
        else f"{label} is a {role} with a local contract that must remain visible in implementation and review"
    )
    second = f"Its distinguishing proof is {_lower_first(proof)}" if proof else ""
    collaborators = _contract_collaborator_sentence(contract)
    return tuple(_paragraph(row) for row in (first, second, collaborators) if sentence_fragment(row))


def _contract_summary_from_contract(*, label: str, contract: Mapping[str, Any]) -> str:
    owned = sentence_fragment(str(contract.get("owned_state", "")))
    inputs = sentence_fragment(str(contract.get("accepted_inputs", "")))
    outputs = sentence_fragment(str(contract.get("produced_outputs", "")))
    states = sentence_fragment(str(contract.get("states_or_transitions", "")))
    outside = sentence_fragment(str(contract.get("outside_boundary", "")))
    proof = _first_text(contract.get("local_proof"))
    rows = [
        f"{label} owns {_lower_first(owned)}" if owned else "",
        f"It accepts {_lower_first(inputs)} and produces {_lower_first(outputs)}" if inputs and outputs else "",
        f"It can render, emit, or transition {_lower_first(states)}" if states else "",
        f"It refuses {_lower_first(outside)}" if outside else "",
        _contract_collaborator_sentence(contract),
        f"Its local proof is {proof}" if proof else "",
    ]
    return ". ".join(sentence_fragment(row) for row in rows if sentence_fragment(row))


def _contract_collaborator_sentence(contract: Mapping[str, Any]) -> str:
    upstream = sentence_fragment(str(contract.get("upstream_truth", "")))
    downstream = sentence_fragment(str(contract.get("downstream_consumers", "")))
    if upstream and downstream:
        return f"Upstream truth comes from {upstream}; downstream consumers are {downstream}"
    if upstream:
        return f"Upstream truth comes from {upstream}"
    if downstream:
        return f"Downstream consumers are {downstream}"
    return ""


def _contract_outside_boundary_lines(contract: Mapping[str, Any]) -> tuple[str, ...]:
    outside = sentence_fragment(str(contract.get("outside_boundary", "")))
    if not outside:
        return ()
    rows = [_strip_conjunction(sentence_fragment(part)) for part in re.split(r",|;", outside) if sentence_fragment(part)]
    return _unique_lines(rows or (outside,))


def _first_text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        for item in value:
            text = sentence_fragment(str(item))
            if text:
                return text
        return ""
    return sentence_fragment(str(value))


def _responsibility_sentence(value: str, *, default_verb: str) -> str:
    text = sentence_fragment(value)
    if not text:
        return ""
    clauses = [
        _responsibility_clause(part, default_verb=default_verb)
        for part in re.split(r"\s*;\s*", text)
        if part.strip()
    ]
    clauses = [clause for clause in clauses if clause]
    if not clauses:
        return ""
    if len(clauses) == 1:
        return _sentence_case(clauses[0])
    if len(clauses) == 2:
        return _sentence_case(f"{clauses[0]} and {clauses[1]}")
    return _sentence_case(f"{', '.join(clauses[:-1])}, and {clauses[-1]}")


def _responsibility_clause(value: str, *, default_verb: str) -> str:
    text = sentence_fragment(value)
    if not text:
        return ""
    return finite_action_clause(text, default_verb=default_verb, default_single_token=True)


def _dependency_lines(values: Sequence[str]) -> tuple[str, ...]:
    rows: list[str] = []
    for value in values:
        text = sentence_fragment(str(value))
        if not text:
            continue
        if re.match(r"^(domain evidence|design pressure|boundary pressure|release pressure|proof pressure)\s*:", text, flags=re.I):
            rows.append(_sentence_case(text))
            continue
        if _looks_like_sentence(text):
            rows.append(text)
        else:
            rows.append(f"Depends on {text} for state, behavior, evidence, or access this component does not own")
    return _unique_lines(rows)


def _looks_like_sentence(value: str) -> bool:
    if not re.search(r"\s", value):
        return False
    if re.search(
        r"\b(can|cannot|coordinates|depends|keeps|must|needs|owns|provides|produces|reads|receives|remains|requires|should|stays|uses|will|writes)\b",
        value,
        re.I,
    ):
        return True
    return bool(
        re.search(r"[.;:]", value)
        and len([part for part in value.split() if part.strip()]) >= 5
    )


def _component_heading(label: str, heading: str) -> str:
    label_text = sentence_fragment(label)
    heading_text = sentence_fragment(heading)
    if not label_text:
        return heading_text
    if not heading_text:
        return label_text
    label_words = {word.casefold().strip(".,:;()[]") for word in label_text.split()}
    structural_words = {
        "boundary",
        "contract",
        "failure",
        "failures",
        "first",
        "interaction",
        "matrix",
        "modes",
        "proof",
        "runtime",
        "slice",
    }
    heading_words = [
        word
        for word in heading_text.split()
        if word.casefold().strip(".,:;()[]") not in label_words
        or word.casefold().strip(".,:;()[]") in structural_words
    ]
    if heading_words:
        heading_text = " ".join(heading_words)
    return f"{label_text} {heading_text}"


def _contract_summary(
    *,
    label: str,
    responsibility: str,
    boundary: str,
    profile: Mapping[str, str],
    interfaces: Sequence[str],
    dependencies: Sequence[str],
    proof_lines: Sequence[str],
) -> str:
    rows: list[str] = []
    if responsibility:
        rows.append(f"Contract focus: {label} {_lower_first(responsibility)}")
    elif boundary:
        rows.append(f"Contract focus: {label} owns the boundary described above")
    if interfaces:
        rows.append(f"Primary interface: {interfaces[0]}")
    if dependencies:
        rows.append(f"Main collaboration: {dependencies[0]}")
    if proof_lines:
        rows.append(f"Proof obligation: {_lower_first(_strip_proof_prefix(proof_lines[0]))}")
    if rows:
        return ". ".join(row for row in rows if sentence_fragment(row))
    if boundary:
        return (
            f"{label} owns the boundary described above. "
            "Its first technical plan must turn that boundary into concrete interfaces and proof."
        )
    return profile["contract_intro"]


def _outside_boundary_lines(*, boundary: str, profile: Mapping[str, str]) -> tuple[str, ...]:
    exclusions = _extract_exclusions(boundary)
    if exclusions:
        return exclusions
    return (profile["default_outside"],)


def _extract_exclusions(boundary: str) -> tuple[str, ...]:
    rows: list[str] = []
    for clause in re.split(r"[.;]", boundary):
        match = re.search(r"\bexcludes?\b(?P<tail>.+)", clause, flags=re.IGNORECASE)
        if not match:
            continue
        tail = match.group("tail")
        for part in re.split(r",|;", tail):
            text = _sentence_case(_strip_conjunction(part))
            if text:
                rows.append(text)
    return _unique_lines(rows)


def _strip_conjunction(value: str) -> str:
    return sentence_fragment(re.sub(r"^(?:and|or)\s+", "", str(value or "").strip(), flags=re.IGNORECASE))


def _sentence_case(value: str) -> str:
    text = sentence_fragment(str(value))
    text = re.sub(r"^(also|only|the|a|an)\s+", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _lower_first(value: str) -> str:
    text = sentence_fragment(str(value))
    if not text:
        return ""
    return text[:1].lower() + text[1:]


def _promotion_bar_lines(
    *,
    label: str,
    path: str,
    first_workstream: str,
    proof_lines: Sequence[str],
) -> tuple[str, ...]:
    source = f"`{path}`" if path else "the source boundary named by the first technical plan"
    anchor = f"`{first_workstream}`" if first_workstream else "the first implementation plan"
    proof = (
        " and ".join(_brief_sentence(_strip_proof_prefix(line), limit=220) for line in proof_lines[:2])
        if proof_lines
        else "the listed component proof"
    )
    promotion_proof = (
        f"source-backed evidence for: {_lower_first(proof)}"
        if proof_lines
        else "the listed component proof"
    )
    return (
        f"{label} remains candidate until {anchor} lands source-backed behavior inside {source}.",
        f"Promotion requires {promotion_proof}; proposal text alone is not enough.",
        "The component record, implementation plan, architecture view, and project status must refresh from that proof before active status.",
    )


def _evidence_text(*, normalized_sources: Sequence[str], path: str) -> str:
    if "user_intent" in normalized_sources:
        anchor = f" Intended first source boundary: `{path}`." if path else ""
        return f"Planned from user-stated intent. No source-backed claim is made yet.{anchor}"
    if path:
        return f"Initially anchored by `{path}`."
    return "Initially anchored by Registry review."


def _paragraph(value: str) -> str:
    text = sentence_fragment(value)
    return f"{text}." if text else ""


def _bullet_lines(values: Sequence[str]) -> str:
    lines = [sentence_fragment(str(item)) for item in values if str(item).strip()]
    return "\n".join(f"- {line}." for line in lines)


def _proof_table(values: Sequence[str], *, commands: Sequence[str]) -> str:
    rows = ["| Claim | Required proof |", "| --- | --- |"]
    command_hint = _first_command_hint(commands)
    for value in values:
        claim = _sentence_case(_strip_proof_prefix(str(value)))
        if claim:
            rows.append(f"| {claim} | {command_hint} |")
    return "\n".join(rows)


def _first_command_hint(commands: Sequence[str]) -> str:
    for command in commands:
        text = " ".join(str(command).split()).strip()
        if text:
            if _is_odylith_context_or_sync_command(text):
                continue
            return f"`{text}`" if not text.startswith("run ") else text
    return "Source-backed proof named by the first implementation plan"


def _is_odylith_context_or_sync_command(value: str) -> bool:
    text = value.casefold()
    return "odylith context" in text or "odylith sync" in text or "odylith validate plan-" in text


def _component_proof_lines(
    *,
    validation: Sequence[str],
    handoff_validation: Sequence[str],
    label: str,
    boundary: str,
    responsibility: str,
) -> tuple[str, ...]:
    local = _unique_lines(validation)
    if local:
        return local
    keywords = _component_keywords(label=label, boundary=boundary, responsibility=responsibility)
    filtered = [
        line
        for line in handoff_validation
        if _line_mentions_component(line=line, keywords=keywords)
    ]
    return _unique_lines(filtered or handoff_validation[:2])


def _component_keywords(*, label: str, boundary: str, responsibility: str) -> set[str]:
    text = " ".join([label, boundary, responsibility]).casefold()
    words = set(re.findall(r"[a-z0-9][a-z0-9_-]{3,}", text))
    structural = {
        "application",
        "boundary",
        "candidate",
        "component",
        "contract",
        "first",
        "implementation",
        "project",
        "release",
        "source",
        "system",
        "technical",
        "workstream",
    }
    expanded: set[str] = set()
    for word in words:
        if word in structural:
            continue
        expanded.add(word)
        expanded.update(part for part in word.replace("_", "-").split("-") if len(part) >= 4 and part not in structural)
    return expanded


def _line_mentions_component(*, line: str, keywords: set[str]) -> bool:
    if not keywords:
        return False
    text = str(line).casefold()
    return any(keyword in text for keyword in keywords)


def _runway_lines(
    *,
    path: str,
    first_workstream: str,
    first_workstream_title: str,
    wave_label: str,
    wave_status: str,
    release_selector: str,
    first_slice: str,
    label: str = "",
    local_proof: str = "",
) -> str:
    lines = []
    if path:
        lines.append(f"Start inside `{path}` until the plan proves a narrower boundary.")
    else:
        lines.append("Choose the source boundary in the first technical plan before implementation starts.")
    if first_workstream and first_workstream_title:
        lines.append(f"Use `{first_workstream}` ({first_workstream_title}) as the implementation-plan anchor.")
        if local_proof and not _workstream_title_matches_component(first_workstream_title, label):
            lines.append(
                "This is a broad project workstream; the component still needs its narrower local proof: "
                f"{_brief_sentence(local_proof, limit=360)}."
            )
    elif first_workstream:
        lines.append(f"Use `{first_workstream}` as the implementation-plan anchor.")
    else:
        lines.append("Create a Radar-linked implementation plan before source writes.")
    if wave_label:
        status = f" ({wave_status})" if wave_status else ""
        lines.append(f"Wave: {wave_label}{status}.")
    if release_selector:
        lines.append(f"Release target: {release_selector}.")
    if first_slice:
        lines.append(f"First coding slice: {_brief_sentence(first_slice, limit=360)}.")
    lines.append("Promote this component from candidate only after source-backed proof refreshes the component record and project status.")
    return _bullet_lines(lines)


def _workstream_title_matches_component(title: str, label: str) -> bool:
    title_terms = _meaningful_terms(title)
    label_terms = _meaningful_terms(label)
    return bool(title_terms & label_terms)


def _meaningful_terms(value: str) -> set[str]:
    structural = {
        "anchor",
        "boundary",
        "component",
        "define",
        "first",
        "implementation",
        "plan",
        "project",
        "service",
        "surface",
        "view",
        "workstream",
    }
    return {
        word
        for word in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", sentence_fragment(value).casefold())
        if word not in structural
    }


def _brief_sentence(value: str, *, limit: int = 220) -> str:
    text = sentence_fragment(value)
    if not text:
        return ""
    if ". " in text:
        first = text.split(". ", 1)[0].strip()
        if len(first) >= min(45, limit):
            text = first
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit - 1)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    clipped = _strip_dangling_tail(clipped)
    return clipped


def _strip_dangling_tail(value: str) -> str:
    text = value.rstrip(" ,;:.")
    text = re.sub(
        r"\bby\s+(?:accepting|producing|using|recording|showing|validating)\b.*$",
        "",
        text,
        flags=re.I,
    ).rstrip(" ,;:.")
    text = re.sub(
        r"\band\s+(?:accepting|producing|using|recording|showing|validating)\b.*$",
        "",
        text,
        flags=re.I,
    ).rstrip(" ,;:.")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|for|from|if|in|into|of|on|or|required|the|to|when|while|with|without)$",
            "",
            text,
            flags=re.I,
        ).rstrip(" ,;:.")
        if cleaned == text:
            return cleaned
        text = cleaned


def _strip_proof_prefix(value: str) -> str:
    text = sentence_fragment(value)
    text = re.sub(
        r"^(?:contract|adapter|behavior|release|user-visible)?\s*proof\s+(?:must\s+)?(?:covers?|shows?|proves?)\s+",
        "",
        text,
        flags=re.I,
    ).strip()
    text = re.sub(r"^(?:first\s+)?proof\s+(?:must\s+)?shows?\s+", "", text, flags=re.I).strip()
    text = re.sub(r"^required\s+proof\s*:\s*", "", text, flags=re.I).strip()
    return text


def _command_lines(values: Sequence[str]) -> str:
    lines = [_command_bullet(line) for line in values if str(line).strip()]
    return "\n".join(lines) or "- Run the repo-native proof command selected by the first technical plan."


def _command_bullet(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if text.startswith("run "):
        return f"- {text}"
    return f"- `{text}`"


def _plan_link(first_workstream: str) -> str:
    if not first_workstream:
        return ""
    return f" (Plan: [{first_workstream}](odylith/radar/radar.html?view=plan&workstream={first_workstream}))"


def _handoff_text(handoff: Mapping[str, Any], key: str) -> str:
    return " ".join(str(handoff.get(key, "") or "").split()).strip()


def _handoff_list(handoff: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values = handoff.get(key)
    if not isinstance(values, (list, tuple)):
        return ()
    return tuple(" ".join(str(item or "").split()).strip() for item in values if str(item or "").strip())


def _unique_lines(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = sentence_fragment(str(value))
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return tuple(result)


__all__ = ["build_component_spec", "sentence_fragment"]

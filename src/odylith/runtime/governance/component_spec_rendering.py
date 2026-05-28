"""Render Registry component specs from concrete ownership contracts."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common import display_text
from odylith.runtime.common.prose_grammar import finite_action_clause
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    dependencies_from_contract,
    interfaces_from_contract,
    responsibility_from_contract,
    risks_from_contract,
    validation_from_contract,
)
from odylith.runtime.domain_intelligence.greenfield_text import text_values


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
    boundary_source = _contract_boundary_intro(label=label, profile=profile, contract=contract) if has_contract else boundary
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
    owns_lines = _contract_field_lines(contract, "owned_state") if has_contract else ((responsibility_line,) if responsibility_line else (profile["default_owns"],))
    accepts_lines = _contract_field_lines(contract, "accepted_inputs") if has_contract else ()
    produces_lines = _contract_field_lines(contract, "produced_outputs") if has_contract else ()
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
            _bullet_lines(owns_lines),
            "",
            "### Accepts",
            "",
            _bullet_lines(accepts_lines or ("The first implementation plan must name accepted inputs.",)),
            "",
            "### Produces",
            "",
            _bullet_lines(produces_lines or ("The first implementation plan must name produced outputs.",)),
            "",
            "### Refuses",
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
            _proof_table(
                proof_lines or (profile["default_validation"],),
                commands=handoff_commands,
                label=label,
                contract=contract if has_contract else {},
            ),
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
                local_proof=_proof_handle(label, proof_lines[0], index=1) if proof_lines else "",
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
        "contract_intro": "This component owns state, invariants, and the integration contract other slices depend on.",
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
    owned = _first_contract_item(str(contract.get("owned_state", "")))
    failure = sentence_fragment(str(contract.get("unique_failure", "")))
    proof = _first_text(contract.get("local_proof"))
    focus = f" for {_lower_first(owned)}" if owned else ""
    sentences = [f"{label} is a {role}{focus}"]
    if failure:
        sentences.append(f"It exists to make this failure testable: {_lower_first(failure)}")
    if proof:
        sentences.append(f"Its proof obligation is `{_proof_handle(label, proof, index=1)}`")
    else:
        sentences.append("Its proof obligation must be named by the first implementation plan")
    return (_paragraph(". ".join(sentences)),)


def _contract_summary_from_contract(*, label: str, contract: Mapping[str, Any]) -> str:
    states = sentence_fragment(str(contract.get("states_or_transitions", "")))
    proof_rows = tuple(_strip_proof_prefix(value) for value in text_values(contract.get("local_proof")))
    blocking = next((row for row in proof_rows if re.search(r"\b(block|reject|invalid|missing|stale|unauthorized)\b", row, re.I)), "")
    provenance = next((row for row in proof_rows if re.search(r"\b(provenance|replay|history|source|snapshot|rationale)\b", row, re.I)), "")
    rows = [
        f"{label} transitions through {_lower_first(states)}" if states else "",
        f"Blocking invariant: {_lower_first(blocking)}" if blocking else "",
        f"Traceability invariant: {_lower_first(provenance)}" if provenance and provenance != blocking else "",
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


def _contract_boundary_intro(*, label: str, profile: Mapping[str, str], contract: Mapping[str, Any]) -> str:
    owned = _first_contract_item(str(contract.get("owned_state", "")))
    role = profile.get("role_noun", "ownership boundary")
    if owned:
        return f"{label} is the {role} for {owned}; the structured contract below keeps state, inputs, outputs, transitions, and refusals separate"
    return f"{label} is the {role}; the structured contract below keeps state, inputs, outputs, transitions, and refusals separate"


def _contract_field_lines(contract: Mapping[str, Any], key: str) -> tuple[str, ...]:
    raw = sentence_fragment(str(contract.get(key, "")))
    if not raw:
        return ()
    rows = [_strip_conjunction(sentence_fragment(part)) for part in re.split(r",|;", raw) if sentence_fragment(part)]
    if len(rows) <= 1:
        return (raw,)
    return _unique_lines(rows)


def _first_contract_item(value: str) -> str:
    text = sentence_fragment(str(value))
    if not text:
        return ""
    head = re.split(r",|;", text, maxsplit=1)[0]
    return _strip_conjunction(head)


def _contract_outside_boundary_lines(contract: Mapping[str, Any]) -> tuple[str, ...]:
    outside = sentence_fragment(str(contract.get("outside_boundary", "")))
    if not outside:
        return ()
    return _outside_boundary_bucket_lines(outside)


def _outside_boundary_bucket_lines(outside: str) -> tuple[str, ...]:
    buckets = {
        "Refused domain responsibilities": [],
        "Sibling-owned state": [],
        "Forbidden runtime authorities": [],
    }
    current_label = ""
    for part in re.split(r";", outside):
        segment = sentence_fragment(part)
        if not segment:
            continue
        match = re.match(
            r"^(?P<label>refused domain responsibilities|sibling-owned state|forbidden runtime authorities)\s*:\s*(?P<body>.+)$",
            segment,
            flags=re.I,
        )
        if match:
            current_label = _bucket_label(match.group("label"))
            _extend_bucket(buckets[current_label], match.group("body"))
            continue
        for clause in re.split(r",", segment):
            text = _strip_conjunction(clause)
            if text:
                buckets[_classify_outside_clause(text, current_label)].append(text)
    if not buckets["Forbidden runtime authorities"]:
        buckets["Forbidden runtime authorities"].append("runtime implementation outside the accepted proof boundary")
    rows: list[str] = []
    for label, values in buckets.items():
        cleaned = _unique_lines(values)
        if cleaned:
            body = _join_phrase(cleaned)
            rows.append(f"{label}: {body}")
    return tuple(rows)


def _bucket_label(value: str) -> str:
    text = sentence_fragment(value).casefold()
    if text.startswith("sibling"):
        return "Sibling-owned state"
    if text.startswith("forbidden"):
        return "Forbidden runtime authorities"
    return "Refused domain responsibilities"


def _extend_bucket(target: list[str], body: str) -> None:
    for part in re.split(r",|;", body):
        text = _strip_conjunction(part)
        if text:
            target.append(text)


def _classify_outside_clause(value: str, current_label: str = "") -> str:
    text = sentence_fragment(value).casefold()
    if current_label and not re.search(r"\b(upstream|release|runtime|authority|mutation|source truth)\b", text):
        return current_label
    if "sibling" in text or "owned by" in text:
        return "Sibling-owned state"
    if re.search(r"\b(upstream source truth|release approval|runtime implementation|silent overwrite|mutation|provider truth)\b", text):
        return "Forbidden runtime authorities"
    if re.search(r"\b(state|record|comment|snapshot|marker|history|evidence|handoff)\b", text) and "authority" not in text:
        return "Sibling-owned state"
    return "Refused domain responsibilities"


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
        rows.append(f"Contract focus: {label} owns boundary described above")
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
            f"{label} owns boundary described above. "
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
    words = text.split()
    if len(words) >= 2 and words[0][:1].isupper() and words[1][:1].isupper():
        return text
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
    proof_handles = [_proof_handle(label, line, index=index) for index, line in enumerate(proof_lines[:3], start=1)]
    promotion_proof = ", ".join(f"`{handle}`" for handle in proof_handles) if proof_handles else "the listed component proof"
    return (
        f"{label} remains candidate until {anchor} lands source-backed behavior inside {source}.",
        f"Promotion requires source-backed {promotion_proof}; proposal text alone is not enough.",
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
    lines = [_sentence_case(sentence_fragment(str(item))) for item in values if str(item).strip()]
    return "\n".join(f"- {line}." for line in lines)


def _proof_table(
    values: Sequence[str],
    *,
    commands: Sequence[str],
    label: str,
    contract: Mapping[str, Any],
) -> str:
    rows = ["| Claim | Required proof |", "| --- | --- |"]
    used_handles: set[str] = set()
    for index, value in enumerate(values, start=1):
        claim = _sentence_case(_strip_proof_prefix(str(value)))
        if claim:
            required = _proof_requirement(
                claim=claim,
                label=label,
                contract=contract,
                index=index,
                commands=commands,
                used_handles=used_handles,
            )
            rows.append(f"| {claim} | {required} |")
    return "\n".join(rows)


def _proof_requirement(
    *,
    claim: str,
    label: str,
    contract: Mapping[str, Any],
    index: int,
    commands: Sequence[str],
    used_handles: set[str] | None = None,
) -> str:
    claim_text = sentence_fragment(claim).casefold()
    text = " ".join([claim, label, *text_values(contract)]).casefold()
    handle = _proof_handle(label, claim, index=index)
    if used_handles is not None:
        base_handle = handle
        suffix = 2
        while handle in used_handles:
            handle = f"{base_handle}_{suffix}"
            suffix += 1
        used_handles.add(handle)
    label_text = sentence_fragment(label).casefold()
    if re.search(r"\b(refus|boundary|sibling|outside|mutat|overwrite|rewrite)\b", claim_text):
        requirement = f"`{handle}` boundary test proving adjacent components cannot mutate this component's owned state"
    elif re.search(r"^\s*intake\s+proof\b", claim_text):
        requirement = (
            f"`{handle}` fixture with actor identity, submitted answers, required fields, validation context, "
            "missing-input blocker, accepted answer set, and downstream handoff"
        )
    elif re.search(r"^\s*ranking\s+proof\b", claim_text):
        requirement = (
            f"`{handle}` fixture with candidate options, comparison criteria, tie-break rule, ranked option list, "
            "selected option, ordered alternatives, explanation, and downstream handoff"
        )
    elif re.search(r"^\s*quote\s+proof\b", claim_text):
        requirement = (
            f"`{handle}` fixture with quote request, priced option, usage context, cost rule, calculated quote, "
            "cost breakdown, explanation, provenance reference, and downstream handoff"
        )
    elif re.search(r"^\s*plan\s+adjustment\s+proof\b", claim_text):
        requirement = (
            f"`{handle}` fixture with plan adjustment request, progress snapshot, status window, actor context, "
            "plan adjustment result, rationale, blocker signal, and downstream handoff"
        )
    elif re.match(r"\s*(?:invalid|missing|blocked|stale|unauthorized|malformed)\b", claim_text):
        requirement = (
            f"`{handle}` fixture showing missing, stale, unauthorized, or malformed input blocks trusted output and downstream handoff"
        )
    elif re.search(r"\b(check ledger|required checks?|rule references?|pass or block|reviewer comment)\b", claim_text):
        requirement = (
            f"`{handle}` fixture with reviewed item, rule reference, reviewer comment, pass or block outcome, "
            "blocker signal, and handoff evidence"
        )
    elif re.search(r"\b(provenance|replay|history|source|snapshot|audit)\b", claim_text):
        requirement = f"`{handle}` replay test linking persisted output to source evidence, validation context, and rationale"
    elif re.search(r"\b(blocker|blocked|reject|invalid|missing|stale|unauthorized|malformed|unresolved)\b", claim_text):
        requirement = (
            f"`{handle}` fixture showing missing, stale, unauthorized, or malformed input blocks trusted output and downstream handoff"
        )
    elif re.search(r"\b(target|recompute|computed|adjustment|plan|goal|recommendation)\b", f"{claim_text} {label_text}"):
        requirement = (
            f"`{handle}` fixture with plan adjustment request, progress snapshot, status window, actor context, "
            "plan adjustment result, rationale, blocker signal, and downstream handoff"
        )
    elif re.search(r"\b(intake|submitted answers|required-input|accepted answer set)\b", text):
        requirement = (
            f"`{handle}` fixture with actor identity, submitted answers, required fields, validation context, "
            "missing-input blocker, accepted answer set, and downstream handoff"
        )
    elif re.search(r"\b(candidate option|comparison criteria|ranking|selected option|ordered alternatives)\b", text):
        requirement = (
            f"`{handle}` fixture with candidate options, comparison criteria, tie-break rule, ranked option list, "
            "selected option, ordered alternatives, explanation, and downstream handoff"
        )
    elif re.search(r"\b(quote|pricing|cost rule|calculated amount|cost breakdown)\b", text):
        requirement = (
            f"`{handle}` fixture with quote request, priced option, usage context, cost rule, calculated quote, "
            "cost breakdown, explanation, provenance reference, and downstream handoff"
        )
    elif re.search(r"\b(privacy|retention|export|deletion|delete|consent|protected)\b", f"{claim_text} {label_text}"):
        requirement = (
            f"`{handle}` fixture with actor identity, consent history, protected-state reference, retention rule, "
            "export or deletion result, lifecycle marker, and audit event"
        )
    elif re.search(r"\b(provenance|replay|history|source|snapshot|rationale|audit)\b", text):
        requirement = f"`{handle}` replay test linking persisted output to source evidence, validation context, and rationale"
    else:
        requirement = f"`{handle}` contract fixture covering accepted input, state transition, produced output, blocker behavior, and handoff evidence"
    command_hint = _first_command_hint(commands, fallback=False)
    if command_hint:
        requirement = f"{requirement}; check with {command_hint}"
    return requirement


def _first_command_hint(commands: Sequence[str], *, fallback: bool = True) -> str:
    for command in commands:
        text = " ".join(str(command).split()).strip()
        if text:
            if _is_odylith_context_or_sync_command(text):
                continue
            return f"`{text}`" if not text.startswith("run ") else text
    return "Source-backed proof named by the first implementation plan" if fallback else ""


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
                f"`{local_proof}`."
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
        lines.append(f"First coding slice: {_brief_sentence(first_slice, limit=220)}.")
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


def _proof_handle(label: str, proof: str, *, index: int) -> str:
    proof_terms = _proof_handle_terms(proof)
    label_terms = _proof_handle_terms(label)
    terms = _unique_terms([*proof_terms, *label_terms])
    if terms:
        return "_".join([*terms[:4], str(index), "proof"])
    return f"component_contract_{index}_proof"


def _proof_handle_terms(value: str) -> list[str]:
    stopwords = {
        "able",
        "accepted",
        "actor",
        "and",
        "are",
        "before",
        "boundary",
        "can",
        "component",
        "contract",
        "downstream",
        "evidence",
        "for",
        "from",
        "handoff",
        "input",
        "its",
        "local",
        "missing",
        "must",
        "not",
        "output",
        "owned",
        "owns",
        "path",
        "proof",
        "release",
        "required",
        "result",
        "service",
        "source",
        "state",
        "the",
        "this",
        "to",
        "upstream",
        "when",
        "while",
        "with",
    }
    terms: list[str] = []
    for raw in re.findall(r"[a-z0-9][a-z0-9_-]*", str(value).casefold()):
        word = raw.replace("-", "_").strip("_")
        if len(word) < 3 or word in stopwords:
            continue
        if word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
            word = word[:-1]
        terms.append(word)
    return terms


def _unique_terms(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = str(value or "").strip()
        if term and term not in seen:
            seen.add(term)
            result.append(term)
    return result


def _command_lines(values: Sequence[str]) -> str:
    lines = [_command_bullet(line) for line in values if str(line).strip()]
    return "\n".join(lines) or "- Bind this component to a technical plan, then run that plan's concrete repo-native proof commands."


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


def _join_phrase(values: Sequence[str]) -> str:
    rows = [sentence_fragment(str(value)) for value in values if sentence_fragment(str(value))]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


__all__ = ["build_component_spec", "sentence_fragment"]

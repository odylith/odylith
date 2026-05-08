"""Render Registry component specs from concrete ownership contracts."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Mapping, Sequence


def sentence_fragment(value: str) -> str:
    return " ".join(str(value or "").strip().split()).rstrip(".")


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
) -> str:
    handoff = implementation_handoff or {}
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

    responsibility_text = sentence_fragment(responsibility)
    boundary_text = sentence_fragment(boundary) or responsibility_text
    evidence_text = _evidence_text(normalized_sources=normalized_sources, path=path)
    plan_link = _plan_link(first_workstream)
    related_workstreams = ", ".join(f"`{item}`" for item in workstream_ids) if workstream_ids else "none yet"
    related_diagrams = ", ".join(f"`{item}`" for item in diagram_ids) if diagram_ids else "none yet"
    proof_lines = _unique_lines([*validation, *handoff_validation])
    interface_lines = _unique_lines(interfaces or (profile["default_interface"],))
    dependency_lines = _unique_lines(dependencies or (profile["default_dependency"],))
    risk_lines = _unique_lines(risks or (profile["default_risk"],))
    outside_boundary = _outside_boundary_lines(boundary=boundary_text, profile=profile)
    contract_summary = _contract_summary(
        label=label,
        responsibility=responsibility_text,
        boundary=boundary_text,
        profile=profile,
    )

    return "\n".join(
        [
            f"# {label}",
            "",
            f"> Component-specific Registry dossier for `{component_id}`. {evidence_text}",
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
            f"## {_component_heading(label, profile['boundary_heading'])}",
            "",
            _paragraph(
                boundary_text
                or "The first technical plan must name the runtime, data, or interaction boundary before source writes."
            ),
            "",
            "### Owns",
            "",
            _bullet_lines((responsibility_text,) if responsibility_text else (profile["default_owns"],)),
            "",
            "### Outside Boundary",
            "",
            _bullet_lines(outside_boundary),
            "",
            f"## {_component_heading(label, profile['contract_heading'])}",
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
            f"## {_component_heading(label, profile['proof_heading'])}",
            "",
            _proof_table(proof_lines or (profile["default_validation"],), commands=handoff_commands),
            "",
            f"## {_component_heading(label, profile['risk_heading'])}",
            "",
            _bullet_lines(risk_lines),
            "",
            f"## {_component_heading(label, profile['runway_heading'])}",
            "",
            _runway_lines(
                path=path,
                first_workstream=first_workstream,
                first_workstream_title=first_workstream_title,
                wave_label=wave_label,
                wave_status=wave_status,
                release_selector=release_selector,
                first_slice=first_slice,
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
    if token in {"application", "ui", "frontend", "web"}:
        return {
            "boundary_heading": "Interaction Boundary",
            "contract_heading": "Interaction Contract",
            "interface_heading": "Screens, Commands, And Visible States",
            "proof_heading": "User-State Proof Matrix",
            "risk_heading": "Experience Failure Modes",
            "runway_heading": "First Interaction Slice",
            "contract_intro": "This component owns what a human can initiate, inspect, recover from, and trust in the first slice.",
            "default_owns": "The first user-visible path, including normal, empty, degraded, and error states.",
            "default_interface": "A route, command, or view contract selected by the first implementation plan.",
            "default_dependency": "The domain contract that supplies state and the verification harness that proves visible behavior.",
            "default_validation": "Behavior proof covers the normal path plus at least one empty or degraded state.",
            "default_risk": "A misleading visible state can make an incomplete or unsafe workflow look production-ready.",
            "default_outside": "Domain calculations, persistence, provider adapters, and release proof unless the Registry assigns them here.",
        }
    if token in {"tooling", "test", "harness"}:
        return {
            "boundary_heading": "Proof Harness Boundary",
            "contract_heading": "Harness Contract",
            "interface_heading": "Fixtures, Commands, And Reports",
            "proof_heading": "Release Proof Matrix",
            "risk_heading": "Harness Failure Modes",
            "runway_heading": "First Proof Slice",
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
        "contract_intro": "This component owns the state, invariants, and integration contract other slices depend on.",
        "default_owns": "The first domain state model, commands, queries, invariants, and integration handoff.",
        "default_interface": "A command, query, schema, module, or event contract selected by the first technical plan.",
        "default_dependency": "Confirmed first-workflow semantics; external providers stay outside the boundary until planned.",
        "default_validation": "Contract proof covers valid state transition, invalid input rejection, and retry behavior.",
        "default_risk": "A loose runtime boundary can couple adjacent slices or hide invariant failures.",
        "default_outside": "Presentation, deployment, proof harnesses, and external providers unless the component spec assigns them here.",
    }


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


def _contract_summary(*, label: str, responsibility: str, boundary: str, profile: Mapping[str, str]) -> str:
    if responsibility:
        return (
            f"{label} exists to {responsibility[0].lower() + responsibility[1:]}. "
            "Its contract is limited to the interfaces, dependencies, and proof obligations below."
        )
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
        for part in re.split(r",|\band\b|\bor\b", tail):
            text = _sentence_case(part)
            if text:
                rows.append(text)
    return _unique_lines(rows)


def _sentence_case(value: str) -> str:
    text = sentence_fragment(str(value))
    text = re.sub(r"^(also|only|the|a|an)\s+", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _promotion_bar_lines(
    *,
    label: str,
    path: str,
    first_workstream: str,
    proof_lines: Sequence[str],
) -> tuple[str, ...]:
    source = f"`{path}`" if path else "the source boundary named by the first technical plan"
    anchor = f"`{first_workstream}`" if first_workstream else "the first Radar-linked implementation plan"
    proof = " and ".join(proof_lines[:2]) if proof_lines else "the listed component proof"
    return (
        f"{label} remains candidate until {anchor} lands source-backed behavior inside {source}.",
        f"Promotion requires {proof} to pass against real source, not proposal text.",
        "Registry, Radar, Atlas, and Compass must refresh from that proof before the component is marked active.",
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
        claim = sentence_fragment(str(value))
        if claim:
            rows.append(f"| {claim} | {command_hint} |")
    return "\n".join(rows)


def _first_command_hint(commands: Sequence[str]) -> str:
    for command in commands:
        text = " ".join(str(command).split()).strip()
        if text:
            return f"`{text}`" if not text.startswith("run ") else text
    return "Repo-native proof named by the first technical plan"


def _runway_lines(
    *,
    path: str,
    first_workstream: str,
    first_workstream_title: str,
    wave_label: str,
    wave_status: str,
    release_selector: str,
    first_slice: str,
) -> str:
    lines = []
    if path:
        lines.append(f"Start inside `{path}` until the plan proves a narrower boundary.")
    else:
        lines.append("Choose the source boundary in the first technical plan before implementation starts.")
    if first_workstream and first_workstream_title:
        lines.append(f"Use `{first_workstream}` ({first_workstream_title}) as the implementation-plan anchor.")
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
        lines.append(f"First coding slice: {sentence_fragment(first_slice)}.")
    lines.append("Promote this component from candidate only after source-backed proof refreshes Registry and Compass.")
    return _bullet_lines(lines)


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

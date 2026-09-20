from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_package_evidence import _atlas_findings
from greenfield_matrix_package_evidence import _registry_findings
from greenfield_matrix_package_evidence import project_brief_readback_findings
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact


_PROPOSED_SPEC = """# Request Intake

## Component Snapshot
Proposed logical component; no implementation or deployment is asserted.

## Proposed responsibility
Retain requests for review.

## Proposed inputs and outputs
No component exchanges are proposed for this capability.

## Proposed verification
The submitted request can be retrieved.

## Source-event support
The coordinator submits a request; the actor retains ownership.

## Trace links
Canonical design row: /authored_semantics/provisional_design/components/0

## Feature History
Initial provisional design.
"""


def _registry_messages(text: str) -> list[str]:
    return [finding.message for finding in _registry_findings(
        package=SimpleNamespace(),
        artifacts=(RenderedArtifact("Registry component spec", "request-intake/CURRENT_SPEC.md", text),),
        proposal={"components": [{"component_id": "request-intake"}]},
    )]


def test_registry_evidence_accepts_explicitly_proposed_design_without_source_ownership() -> None:
    assert _registry_messages(_PROPOSED_SPEC) == []


@pytest.mark.parametrize("section", (
    "Component Snapshot", "Proposed responsibility", "Proposed inputs and outputs",
    "Proposed verification", "Source-event support", "Trace links", "Feature History",
))
@pytest.mark.parametrize("change", ("missing", "empty", "body_only"))
def test_registry_evidence_requires_real_nonempty_proposed_sections(section: str, change: str) -> None:
    heading = f"## {section}\n"
    before, tail = _PROPOSED_SPEC.split(heading, 1)
    body, separator, remainder = tail.partition("\n## ")
    suffix = separator + remainder
    replacement = {"missing": "", "empty": heading, "body_only": section + "\n" + body}[change]
    assert any(section in message for message in _registry_messages(before + replacement + suffix))


def test_registry_evidence_does_not_accept_superseded_source_owned_sections() -> None:
    obsolete = _PROPOSED_SPEC.replace("Proposed responsibility", "Source-custodied responsibility")
    assert any("Proposed responsibility" in message for message in _registry_messages(obsolete))


def test_atlas_edge_evidence_uses_the_canonical_mermaid_graph_parser() -> None:
    artifact = RenderedArtifact(
        surface="Atlas Mermaid",
        name="responsibility-map.mmd",
        text="graph LR\n  Intake[Request intake] --- Proof[Accepted proof]\n",
    )

    findings = _atlas_findings(
        artifacts=(artifact,),
        proposal={"diagrams": [{"diagram_id": "D-001"}]},
    )

    assert not any("no visible topology edge" in finding.message for finding in findings)


def test_atlas_edge_evidence_still_rejects_a_nodes_only_diagram() -> None:
    artifact = RenderedArtifact(
        surface="Atlas Mermaid",
        name="responsibility-map.mmd",
        text="graph LR\n  Intake[Request intake]\n  Proof[Accepted proof]\n",
    )

    findings = _atlas_findings(
        artifacts=(artifact,),
        proposal={"diagrams": [{"diagram_id": "D-001"}]},
    )

    assert any("neither a typed edge nor a distinct containment" in finding.message for finding in findings)


def test_atlas_evidence_accepts_distinct_authored_containment_without_an_edge() -> None:
    artifact = RenderedArtifact(
        surface="Atlas Mermaid",
        name="state-evidence.mmd",
        text=(
            'flowchart LR\n'
            '  subgraph accepted["Accepted project facts"]\n'
            '    state["Consent evidence"]\n'
            '  end\n'
        ),
    )
    findings = _atlas_findings(
        artifacts=(artifact,),
        proposal={
            "diagrams": [
                {
                    "slug": "state-evidence",
                    "projection_origin": "model_authored_typed_intent",
                    "diagram_boxes": [
                        {
                            "node_id": "accepted",
                            "label": "Accepted project facts",
                            "role": "Container",
                            "description": "Accepted fact container.",
                        },
                        {
                            "node_id": "state",
                            "label": "Consent evidence",
                            "role": "State object",
                            "description": "Accepted state.",
                        },
                    ],
                }
            ]
        },
    )

    assert not findings


def test_atlas_evidence_rejects_self_nested_authored_boundary() -> None:
    artifact = RenderedArtifact(
        surface="Atlas Mermaid",
        name="component-boundaries.mmd",
        text=(
            'flowchart LR\n'
            '  subgraph product["Shelter intake"]\n'
            '    component["Shelter intake"]\n'
            '  end\n'
            '  actor["Intake coordinator"] --> product\n'
        ),
    )
    findings = _atlas_findings(
        artifacts=(artifact,),
        proposal={
            "diagrams": [
                {
                    "slug": "component-boundaries",
                    "projection_origin": "model_authored_typed_intent",
                    "diagram_boxes": [
                        {
                            "node_id": "product",
                            "label": "Shelter intake",
                            "role": "Product boundary",
                            "description": "Product container.",
                        },
                        {
                            "node_id": "component",
                            "label": "Shelter intake",
                            "role": "Product-owned component",
                            "description": "Candidate component.",
                        },
                        {
                            "node_id": "actor",
                            "label": "Intake coordinator",
                            "role": "Human actor",
                            "description": "Accepted actor.",
                        },
                    ],
                }
            ]
        },
    )

    messages = [finding.message for finding in findings]
    assert messages == [
        "Atlas Mermaid `component-boundaries.mmd` repeats the product boundary as an identically named child component"
    ]


def _proof_brief(*, proposed: bool) -> tuple[dict[str, object], dict[str, object]]:
    statement = "Review one visible accepted decision."
    proof = f"Assumption — {statement}" if proposed else "The accepted decision has exact readback."
    rows: list[dict[str, str]] = [
        {"section": "Source excerpt", "must_capture": "A reviewer can inspect an accepted decision."},
        {"section": "User problem", "must_capture": "Accepted decisions need review."},
        {"section": "First path", "must_capture": "A reviewer records and inspects one decision."},
    ]
    if not proposed:
        rows.append({"section": "Visible result", "must_capture": "The accepted decision is visible."})
    rows.append({
        "section": "Proposed proof checkpoint" if proposed else "Proof",
        "must_capture": proof,
    })
    brief: dict[str, object] = {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "projection_origin": "model_authored_typed_intent",
        "project_name": "Decision Review",
        "purpose": "Accepted decisions need review.",
        "operating_principle": "A reviewer can inspect an accepted decision.",
        "project_outcome": proof if proposed else "The accepted decision is visible.",
        "blueprint_sections": rows,
        "coding_readiness_gates": [],
        "host_independent_paths": [],
    }
    intent: dict[str, object] = {
        "proof_boundary": "" if proposed else proof,
        "assumptions": (
            [{"applies_to": "proof_boundary", "statement": statement}] if proposed else []
        ),
        "evidence_requirements": [],
    }
    return brief, intent


def _proof_brief_record(brief: dict[str, object]) -> str:
    lines = [
        "# Decision Review Project Brief",
        "",
        "- schema: odylith.greenfield.project_brief.v1",
        "- origin: greenfield",
        "",
        "## Brief",
        f"- outcome: {brief['project_outcome']}",
        "- Source excerpt: “A reviewer can inspect an accepted decision.”",
        "",
        "## Project Design Board",
    ]
    for row in brief["blueprint_sections"]:
        label, value = row["section"], row["must_capture"]
        lines.append(f"- {label}: “{value}”" if label == "Source excerpt" else f"- {label}: {value}")
    return "\n".join(lines)


@pytest.mark.parametrize("proposed", (False, True), ids=("source-proof", "proposed-proof"))
def test_project_brief_accepts_exact_exclusive_proof_copy(proposed: bool) -> None:
    brief, intent = _proof_brief(proposed=proposed)

    assert project_brief_readback_findings(
        record_text=_proof_brief_record(brief), project_brief=brief, intent=intent
    ) == ()


@pytest.mark.parametrize("case", ("missing", "both", "duplicate", "invalid"))
def test_project_brief_rejects_invalid_proof_decisions(case: str) -> None:
    brief, intent = _proof_brief(proposed=True)
    if case == "missing":
        intent["assumptions"] = []
    elif case == "both":
        intent["proof_boundary"] = "Competing source proof."
    elif case == "duplicate":
        intent["assumptions"] = [*intent["assumptions"], dict(intent["assumptions"][0])]
    else:
        intent["assumptions"] = [{"applies_to": "proof_boundary", "statement": ""}]

    findings = project_brief_readback_findings(
        record_text=_proof_brief_record(brief), project_brief=brief, intent=intent
    )

    assert any("exclusive proof decision" in finding.message for finding in findings)


@pytest.mark.parametrize("proposed", (False, True), ids=("source-proof", "proposed-proof"))
@pytest.mark.parametrize("mutation", ("label", "value", "duplicate"))
def test_project_brief_requires_exact_proof_label_and_value(
    proposed: bool,
    mutation: str,
) -> None:
    brief, intent = _proof_brief(proposed=proposed)
    proof = brief["blueprint_sections"][-1]
    if mutation == "label":
        proof["section"] = "Proof" if proposed else "Proposed proof checkpoint"
    elif mutation == "value":
        proof["must_capture"] = "Mutated proof copy."
    else:
        brief["blueprint_sections"].append(dict(proof))

    assert project_brief_readback_findings(
        record_text=_proof_brief_record(brief), project_brief=brief, intent=intent
    )


@pytest.mark.parametrize("mutation", ("visible_result", "outcome"))
def test_proposed_project_brief_rejects_coordinated_fabricated_results(mutation: str) -> None:
    brief, intent = _proof_brief(proposed=True)
    if mutation == "visible_result":
        brief["blueprint_sections"].insert(-1, {
            "section": "Visible result",
            "must_capture": "A fabricated source result is visible.",
        })
    else:
        brief["project_outcome"] = "A fabricated source result is visible."

    findings = project_brief_readback_findings(
        record_text=_proof_brief_record(brief), project_brief=brief, intent=intent
    )

    assert any(
        "Visible result" in finding.message or "project outcome" in finding.message
        for finding in findings
    )


@pytest.mark.parametrize("evidence", (pytest.param(None, id="absent"), pytest.param([], id="empty")))
def test_project_brief_accepts_absent_or_empty_evidence_requirements(evidence: object) -> None:
    brief, intent = _proof_brief(proposed=True)
    if evidence is None:
        intent.pop("evidence_requirements")

    assert project_brief_readback_findings(
        record_text=_proof_brief_record(brief), project_brief=brief, intent=intent
    ) == ()


def test_project_brief_accepts_exact_nonempty_evidence_requirements() -> None:
    brief, intent = _proof_brief(proposed=True)
    intent["evidence_requirements"] = ["A signed decision.", "An immutable readback."]
    brief["blueprint_sections"].append({
        "section": "Required evidence",
        "must_capture": "A signed decision.\nAn immutable readback.",
    })

    assert project_brief_readback_findings(
        record_text=_proof_brief_record(brief), project_brief=brief, intent=intent
    ) == ()


@pytest.mark.parametrize("evidence", (None, "evidence", {"kind": "evidence"}))
def test_project_brief_rejects_malformed_present_evidence_requirements(evidence: object) -> None:
    brief, intent = _proof_brief(proposed=True)
    intent["evidence_requirements"] = evidence

    findings = project_brief_readback_findings(
        record_text=_proof_brief_record(brief), project_brief=brief, intent=intent
    )

    assert any("evidence_requirements" in finding.message for finding in findings)


@pytest.mark.parametrize("mutation", ("label", "value", "duplicate"))
def test_project_brief_requires_exact_nonempty_evidence_label_and_value(mutation: str) -> None:
    brief, intent = _proof_brief(proposed=True)
    intent["evidence_requirements"] = ["A signed decision."]
    evidence_row = {"section": "Required evidence", "must_capture": "A signed decision."}
    brief["blueprint_sections"].append(evidence_row)
    if mutation == "label":
        evidence_row["section"] = "Evidence"
    elif mutation == "value":
        evidence_row["must_capture"] = "A different record."
    else:
        brief["blueprint_sections"].append(dict(evidence_row))

    assert project_brief_readback_findings(
        record_text=_proof_brief_record(brief), project_brief=brief, intent=intent
    )

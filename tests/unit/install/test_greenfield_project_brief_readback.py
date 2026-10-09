from __future__ import annotations

import copy
import sys
from types import SimpleNamespace

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_preconfirm_matrix as matrix
from greenfield_matrix_package_evidence import project_brief_readback_findings


def _brief(*, governance: bool = False) -> dict[str, object]:
    brief: dict[str, object] = {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "projection_origin": "model_authored_typed_intent",
        "project_name": "Queue Review",
        "purpose": "Queue review is hard to audit.",
        "operating_principle": "Keep review evidence visible.",
        "project_outcome": "Reviewers can verify queue decisions.",
        "blueprint_sections": [
            {
                "section": "Accepted evidence excerpt",
                "must_capture": "Keep review evidence visible.",
            },
            {"section": "User problem", "must_capture": "Queue review is hard to audit."},
            {
                "section": "First path",
                "must_capture": "Reviewer records a queue decision.\nThe decision remains reviewable.",
            },
            {"section": "Visible result", "must_capture": "Reviewers can verify queue decisions."},
            {"section": "Proof", "must_capture": "Verify the retained queue decision."},
            {
                "section": "Required evidence",
                "must_capture": "Retained decision record.\nSigned reviewer acknowledgment.",
            },
            {
                "section": "Proposed assumptions",
                "must_capture": "Reviewer identity is available.\nAcceptance requires confirmation.",
            },
        ],
        "coding_readiness_gates": [],
        "host_independent_paths": [],
    }
    if governance:
        brief["coding_readiness_gates"] = ["Confirm the review boundary.\nRecord the decision."]
        brief["host_independent_paths"] = [{
            "path": "Project dashboard",
            "command": "odylith project review\n--workstream B-001",
            "works_in": "local repository",
            "use_when": "reviewing scope",
        }]
    return brief


def _intent() -> dict[str, object]:
    return {
        "proof_boundary": "Verify the retained queue decision.",
        "evidence_requirements": ["Retained decision record.", "Signed reviewer acknowledgment."],
    }


def _record(brief: dict[str, object]) -> str:
    lines = [
        "# Queue Review Project Brief",
        "",
        "- schema: odylith.greenfield.project_brief.v1",
        "- origin: greenfield",
        "",
        "## Brief",
        "- outcome: Reviewers can verify queue decisions.",
        "- Accepted evidence excerpt: “Keep review evidence visible.”",
        "",
        "## Project Design Board",
    ]
    for row in brief["blueprint_sections"]:
        label = row["section"]
        value = row["must_capture"]
        lines.append(
            f"- {label}: “{value}”"
            if label == "Accepted evidence excerpt"
            else f"- {label}: {value}"
        )
    gates = brief["coding_readiness_gates"]
    paths = brief["host_independent_paths"]
    if gates or paths:
        lines.extend(("", "## Governance Package"))
    if gates:
        lines.append("- coding readiness gates:")
        lines.extend(f"  - {gate}" for gate in gates)
    if paths:
        lines.append("- host-independent customization paths:")
        for path in paths:
            lines.append("  - " + " | ".join(path.values()))
    return "\n".join(lines)


def _count(tmp_path, brief: dict[str, object], text: str, intent: dict[str, object]) -> int:  # noqa: ANN001
    package = SimpleNamespace(
        proposal={"project_brief": brief, "components": [], "intent": intent},
        project_brief_record_text=text,
        backlog_result={},
        rendered_component_specs={},
        rendered_atlas_sources={},
        governed_readback=matrix.collect_governed_readback(tmp_path),
        source_launch_readback={},
        project_dashboard_preview={},
    )
    return matrix.collect_artifact_counts(
        repo_root=tmp_path,
        package=package,
        required_terms=(),
    ).project_brief_records


def test_empty_governance_brief_is_exact_and_shared_with_count(tmp_path) -> None:  # noqa: ANN001
    brief = _brief()
    intent = _intent()
    text = _record(brief)

    assert project_brief_readback_findings(record_text=text, project_brief=brief, intent=intent) == ()
    assert _count(tmp_path, brief, text, intent) == 1


def test_accepted_evidence_excerpt_rejects_retired_unquoted_or_mutated_copy(tmp_path) -> None:  # noqa: ANN001
    brief = _brief()
    intent = _intent()
    text = _record(brief)
    changed_rows = (
        text.replace("- Accepted evidence excerpt: “", "- principle: ", 1),
        text.replace("Accepted evidence excerpt", "Product outcome"),
        text.replace("“Keep review evidence visible.”", "Keep review evidence visible."),
        text.replace("Keep review evidence visible.", "Mutated review evidence."),
    )
    for changed in changed_rows:
        assert project_brief_readback_findings(
            record_text=changed, project_brief=brief, intent=intent
        )
        assert _count(tmp_path, brief, changed, intent) == 0

    retired = _brief()
    retired["blueprint_sections"][0]["section"] = "Product outcome"
    retired_text = _record(retired)
    findings = project_brief_readback_findings(
        record_text=retired_text, project_brief=retired, intent=intent
    )
    assert any(
        "missing `Accepted evidence excerpt`" in finding.message
        for finding in findings
    )
    assert _count(tmp_path, retired, retired_text, intent) == 0


def test_typed_proof_and_required_evidence_mutations_fail_readback(tmp_path) -> None:  # noqa: ANN001
    brief = _brief()
    intent = _intent()
    for label in ("Proof", "Required evidence"):
        changed = _record(brief).replace(f"- {label}: ", f"- {label}: mutated ")
        findings = project_brief_readback_findings(record_text=changed, project_brief=brief, intent=intent)

        assert any(f"`{label}`" in finding.message for finding in findings)
        assert _count(tmp_path, brief, changed, intent) == 0


def test_populated_governance_requires_exact_heading_and_values(tmp_path) -> None:  # noqa: ANN001
    brief = _brief(governance=True)
    intent = _intent()
    text = _record(brief)

    assert project_brief_readback_findings(record_text=text, project_brief=brief, intent=intent) == ()
    for changed in (
        text.replace("## Governance Package\n", ""),
        text.replace("Confirm the review boundary.", "Mutated gate."),
        text.replace("odylith project review", "mutated command"),
        text.replace("## Governance Package", "## Governance Package extra"),
        text.replace("  - Confirm the review boundary.", "   - Confirm the review boundary."),
        text + "\n## Governance Package\n  - unexpected row",
    ):
        assert project_brief_readback_findings(record_text=changed, project_brief=brief, intent=intent)
        assert _count(tmp_path, brief, changed, intent) == 0


def test_empty_governance_rejects_stray_or_mislabeled_content(tmp_path) -> None:  # noqa: ANN001
    brief = _brief()
    intent = _intent()
    text = _record(brief)
    for changed in (
        text + "\n## Governance Package\n",
        text + "\n## Governance package\n",
        text + "\n- coding readiness gates:\n",
    ):
        assert project_brief_readback_findings(record_text=changed, project_brief=brief, intent=intent)
        assert _count(tmp_path, brief, changed, intent) == 0
    mislabeled = text.replace("## Project Design Board", "## Project board")
    assert project_brief_readback_findings(record_text=mislabeled, project_brief=brief, intent=intent)
    assert _count(tmp_path, brief, mislabeled, intent) == 0


def test_multiline_board_values_require_exact_ordered_boundaries(tmp_path) -> None:  # noqa: ANN001
    brief = _brief()
    intent = _intent()
    text = _record(brief)

    assert project_brief_readback_findings(record_text=text, project_brief=brief, intent=intent) == ()
    for changed in (
        text.replace("The decision remains reviewable.", ""),
        text.replace("Acceptance requires confirmation.", "Acceptance requires confirmation.\nUnexpected suffix."),
        text.replace(
            "Retained decision record.\nSigned reviewer acknowledgment.",
            "Signed reviewer acknowledgment.\nRetained decision record.",
        ),
        text.replace("Signed reviewer acknowledgment.", ""),
    ):
        assert project_brief_readback_findings(record_text=changed, project_brief=brief, intent=intent)
        assert _count(tmp_path, brief, changed, intent) == 0


def test_canonical_intent_rejects_a_brief_that_omits_required_evidence(tmp_path) -> None:  # noqa: ANN001
    brief = _brief()
    intent = _intent()
    brief["blueprint_sections"] = [
        row for row in brief["blueprint_sections"] if row["section"] != "Required evidence"
    ]
    text = _record(brief)

    findings = project_brief_readback_findings(record_text=text, project_brief=brief, intent=intent)
    assert any("canonical `Required evidence`" in finding.message for finding in findings)
    assert _count(tmp_path, brief, text, intent) == 0


def test_canonical_intent_custody_rejects_missing_fields_and_duplicate_rows(tmp_path) -> None:  # noqa: ANN001
    brief = _brief()
    intent = _intent()
    text = _record(brief)
    for changed_intent in ({}, {"evidence_requirements": []}, {"proof_boundary": intent["proof_boundary"]}):
        assert project_brief_readback_findings(record_text=text, project_brief=brief, intent=changed_intent)
        assert _count(tmp_path, brief, text, changed_intent) == 0
    for label in ("Proof", "Required evidence"):
        duplicate = _brief()
        row = next(row for row in duplicate["blueprint_sections"] if row["section"] == label)
        duplicate["blueprint_sections"].append(dict(row))
        duplicate_text = _record(duplicate)
        assert project_brief_readback_findings(record_text=duplicate_text, project_brief=duplicate, intent=intent)
        assert _count(tmp_path, duplicate, duplicate_text, intent) == 0


def _narrative_fixture(*, governance: bool = False) -> tuple[dict, dict, str]:
    brief, intent = _brief(governance=governance), _intent()
    summary = "Queue Review helps reviewers record decisions with evidence and verify the published result."
    events = [
        {"order": 1, "event_quote": "The reviewer records a queue decision."},
        {"order": 2, "event_quote": "The publisher publishes the reviewed decision."},
        {"order": 3, "event_quote": "The reviewer verifies the published decision."},
    ]
    path = events[0]["event_quote"] + "\n" + events[2]["event_quote"]
    rationale = "Publication supplies the result required for verification."
    walkthrough = " ".join(row["event_quote"] for row in events) + "\n\n" + rationale
    intent.update({
        "summary": summary, "first_path": path, "product_story": brief["operating_principle"],
        "authored_semantics": {
            "version": "odylith.greenfield.authored-semantics.v19",
            "source_event_relations": events,
            "source_duty": {
                "ledger_receipt": {"ledger": {"version": "odylith.greenfield.source-duty-ledger.v9"}},
                "binding": {"first_path_actions": [{"event_order": 1}, {"event_order": 3}]},
            },
            "provisional_design": {
                "project_summary": summary,
                "first_run": {"event_orders": [1, 2, 3], "rationale": rationale},
            },
        },
    })
    brief["summary"] = summary
    next(row for row in brief["blueprint_sections"] if row["section"] == "First path")["must_capture"] = path
    brief["blueprint_sections"].insert(3, {"section": "Proposed walkthrough", "must_capture": walkthrough})
    lines = [
        "# Queue Review Project Brief", "", "## Brief", summary, "",
        "### First path", "", path, "", "### Proposed walkthrough", "", walkthrough, "",
        "<details>", "<summary>Evidence and assumptions</summary>", "", "## Project Design Board", "",
    ]
    for row in brief["blueprint_sections"]:
        if row["section"] not in {"First path", "Proposed walkthrough"}:
            lines.extend(["### " + row["section"], "", row["must_capture"], ""])
    if governance:
        lines.extend(["## Governance Package", ""])
        lines.extend("- " + gate for gate in brief["coding_readiness_gates"])
        lines.extend("- " + " | ".join(row.values()) for row in brief["host_independent_paths"])
    lines.extend([
        "", "</details>", "", "<details>", "<summary>Record metadata</summary>", "",
        "- schema: odylith.greenfield.project_brief.v1", "- origin: greenfield", "", "</details>",
    ])
    return brief, intent, "\n".join(lines)


def test_fresh_narrative_readback_preserves_declared_path_and_proposed_closure(tmp_path) -> None:  # noqa: ANN001
    for governance in (False, True):
        brief, intent, text = _narrative_fixture(governance=governance)
        assert project_brief_readback_findings(record_text=text, project_brief=brief, intent=intent) == ()
        assert _count(tmp_path, brief, text, intent) == 1
        assert text.count(brief["summary"]) == 1
        visible = text.split("<details>", 1)[0]
        assert "Accepted evidence excerpt" not in visible and "Why:" not in visible
        assert "The publisher publishes" not in visible.split("### Proposed walkthrough")[0]
        assert "The publisher publishes" in visible.split("### Proposed walkthrough")[1]


def test_fresh_narrative_rejects_rendered_tampering_and_open_metadata(tmp_path) -> None:  # noqa: ANN001
    brief, intent, text = _narrative_fixture(governance=True)
    for changed in (
        text.replace(brief["summary"], "An invented product."),
        text.replace("### First path", "### First run"),
        text.replace("The publisher publishes the reviewed decision.", ""),
        text.replace("<details>", "<details open>", 1),
        text.replace("<summary>Record metadata</summary>", "<summary>Metadata</summary>"),
        text.replace("- origin: greenfield", "- origin: other"),
        text.replace("### Proof\n\nVerify the retained queue decision.", "### Proof\n\nApproved without evidence."),
        text.replace("- Confirm the review boundary.", "- Skip review."),
        text.replace("## Brief\n", "- schema: exposed\n\n## Brief\n"),
    ):
        assert project_brief_readback_findings(record_text=changed, project_brief=brief, intent=intent)
        assert _count(tmp_path, brief, changed, intent) == 0


def test_fresh_narrative_rejects_joint_brief_and_text_reinterpretation() -> None:
    brief, intent, text = _narrative_fixture()
    for label, replacement in (
        ("First path", "The publisher publishes the reviewed decision."),
        ("Proposed walkthrough", "The reviewer verifies immediately."),
        ("Accepted evidence excerpt", "An invented authority approves everything."),
    ):
        changed = copy.deepcopy(brief)
        row = next(row for row in changed["blueprint_sections"] if row["section"] == label)
        original = row["must_capture"]
        row["must_capture"] = replacement
        assert project_brief_readback_findings(
            record_text=text.replace(original, replacement), project_brief=changed, intent=intent,
        )
    changed = copy.deepcopy(brief)
    changed["summary"] = "An invented product."
    assert project_brief_readback_findings(
        record_text=text.replace(brief["summary"], changed["summary"]), project_brief=changed, intent=intent,
    )


def test_fresh_narrative_cannot_bypass_retained_brief_authority() -> None:
    brief, intent, text = _narrative_fixture()
    intent["authored_semantics"]["source_duty"]["ledger_receipt"]["ledger"]["version"] = "odylith.greenfield.source-duty-ledger.v8"
    assert project_brief_readback_findings(record_text=text, project_brief=brief, intent=intent)


def test_fresh_narrative_malformed_event_identity_refuses_without_crashing() -> None:
    brief, intent, text = _narrative_fixture()
    for path in ("source_event_relations", "binding"):
        changed = copy.deepcopy(intent)
        semantics = changed["authored_semantics"]
        if path == "binding":
            semantics["source_duty"]["binding"]["first_path_actions"][0]["event_order"] = []
        else:
            semantics[path][0]["order"] = []
        assert project_brief_readback_findings(record_text=text, project_brief=brief, intent=changed)

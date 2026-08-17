from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_traceability


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
TRACEABILITY_PATH = DOMAIN_INTELLIGENCE / "greenfield_traceability.py"


def test_greenfield_traceability_terms_use_shared_domain_index(tmp_path: Path) -> None:
    source = TRACEABILITY_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import ordered_terms" in source
    assert "re.findall" not in source
    assert greenfield_traceability._semantic_tokens(
        "Status dashboards, status-window proofs, and source-backed audit trails."
    ) == {
        "audit",
        "backed",
        "dashboard",
        "proof",
        "source",
        "source-backed",
        "status",
        "status-window",
        "trail",
        "window",
    }

    proposal = {
        "backlog": [
            {"title": "Implement governed release path"},
            {"title": "Build window proof", "problem": "Make the window proof visible."},
        ],
        "components": [
            {
                "component_id": "status_windows",
                "label": "Status Windows",
            }
        ],
        "diagrams": [],
    }
    created_backlog = [
        {
            "idea_id": "B-001",
            "title": "Implement governed release path",
            "idea_path": str(tmp_path / "B-001.md"),
        },
        {
            "idea_id": "B-002",
            "title": "Build window proof",
            "idea_path": str(tmp_path / "B-002.md"),
        },
    ]

    plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=created_backlog,
        diagram_ids=[],
    )

    assert plan.component_workstreams["status-windows"] == ("B-001", "B-002")


def test_greenfield_traceability_splits_long_first_slice_lines() -> None:
    lines = greenfield_traceability._first_implementation_step_lines(
        "Prove one first-release path: enter parcel details, attach required document references, "
        "record fee status and contact information, submit the packet, receive completeness feedback, "
        "and review record, then let the reviewer publish a decision."
    )

    assert lines[0] == "First implementation step: Prove one first-release path."
    assert lines[1].startswith("Path actions: enter parcel details; attach required document references")
    assert lines[2].startswith("Completion check:")
    assert all(len(line) < 220 for line in lines)


def test_greenfield_traceability_does_not_repeat_first_step_label_as_step_body() -> None:
    lines = greenfield_traceability._first_implementation_step_lines(
        "First implementation step: record corridor request, check blocked constraints, confirm receiving-site readiness, "
        "publish safe operating status, record review evidence, and keep deferred integrations outside the release proof."
    )

    assert lines[0] != "First implementation step: First implementation step."
    assert lines[0].startswith("First implementation step: record corridor request")
    assert "First implementation step: First implementation step" not in "\n".join(lines)


def test_greenfield_traceability_long_scope_lines_avoid_clipped_cover_fragments() -> None:
    lines = greenfield_traceability._bounded_scope_lines(
        "Record corridor request, check blocked constraints, confirm receiving-site readiness, "
        "publish safe operating status, record review evidence, notify the receiving operator, "
        "capture the release decision rationale, verify replayable proof history, and keep deferred integrations "
        "outside the release proof."
    )

    assert lines[0].startswith("Record corridor request")
    assert lines[1].startswith("Completion proof:")
    assert "Completion proof covers" not in "\n".join(lines)


def test_greenfield_traceability_why_now_starts_with_workstream_focus() -> None:
    text = greenfield_traceability._why_now_text(
        row={},
        focus="Permit Packet Intake",
        first_slice="Submit one permit packet.",
    )

    assert text.startswith("Permit Packet Intake should land early")
    assert "accepted input and recovery behavior" in text
    assert not text.startswith("Do this before implementation expands")

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

from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_programs


ROOT = Path(__file__).resolve().parents[3]
PROGRAMS_SOURCE = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_programs.py"


def test_greenfield_program_wave_matching_uses_shared_term_index() -> None:
    source = PROGRAMS_SOURCE.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import ordered_terms" in source
    assert "re.findall" not in source
    assert 'r"[A-Za-z0-9][A-Za-z0-9_-]*"' not in source
    assert greenfield_programs._row_tokens("Windows") == {"window"}

    proposal = {
        "program": {
            "waves": [
                {"wave": 1, "label": "Trails", "summary": "Deliver trails."},
                {"wave": 2, "label": "Windows", "summary": "Deliver windows."},
            ]
        },
        "backlog": [
            {"title": "Project umbrella"},
            {"title": "Build window proof"},
            {"title": "Build trail proof"},
        ],
    }
    created_backlog = [
        {"idea_id": "B-001", "title": "Project umbrella"},
        {"idea_id": "B-002", "title": "Build window proof"},
        {"idea_id": "B-003", "title": "Build trail proof"},
    ]

    waves = greenfield_programs._assign_wave_members(
        proposal=proposal,
        created_backlog=created_backlog,
    )

    assert waves[0]["primary_workstreams"] == ["B-003"]
    assert waves[1]["primary_workstreams"] == ["B-002"]

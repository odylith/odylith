from __future__ import annotations

import json
import time
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from tests.unit.runtime.greenfield_proposal_fixtures import HIIT_CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


def test_hiit_greenfield_create_repairs_compact_path_and_quality_under_sixty_seconds(tmp_path: Path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(HIIT_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a guided HIIT interval training app",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
            "--json",
        ]
    )
    elapsed = time.perf_counter() - started
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    proposal = accepted["proposal"]
    first_path = proposal["semantic_model"]["first_path_contract"]
    generated_source = _generated_source_payload(tmp_path)

    assert elapsed < 60.0
    assert payload["post_confirm_quality_manifest"]["status"] == "passed"
    assert payload["post_confirm_quality_manifest"]["issue_count"] == 0
    assert payload["post_confirm_quality_manifest"]["quality_lenses"]["status"] == "passed"
    assert payload["post_confirm_quality_manifest"]["whole_project_elapsed_seconds"] < 60.0
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) == 3
    assert len(payload["diagrams"]) == 6
    assert [event["action"] for event in first_path["events"]] == [
        "chooses",
        "starts",
        "drives",
        "keeps",
        "marks",
        "saves",
    ]
    assert first_path["actor"] == "Trainee"
    assert first_path["visible_result"] == "Saved session in history with date, workout, and total time"
    assert next(row for row in proposal["components"] if row["label"] == "Workout Builder Service")["release_scope"] == "deferred"
    for banned in (
        "history with its date",
        "session to history",
        "choose a workout, starts it",
        "Trainee Following",
        '["Optional"]',
        "<br/>Optional",
        "Implementation slice:",
        "Workout Builder Service proves one complete user path",
    ):
        assert banned not in generated_source


def _generated_source_payload(root: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for source_root in (
            root / "odylith/runtime/source",
            root / "odylith/radar/source",
            root / "odylith/registry/source",
            root / "odylith/atlas/source",
        )
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix in {".json", ".jsonl", ".md", ".mmd"}
    )

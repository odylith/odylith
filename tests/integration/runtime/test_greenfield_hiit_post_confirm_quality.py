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

    started, rc, payload, compile_payload = _run_compiled_transaction_create(
        tmp_path,
        prompt="Draft a greenfield proposal for a guided HIIT interval training app",
        capsys=capsys,
    )
    elapsed = time.perf_counter() - started

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
    assert len(payload["components"]) == 4
    assert len(payload["diagrams"]) == 6
    transaction_package = compile_payload["transaction"]["prewrite_package"]
    assert payload["next_steps"] == transaction_package["next_steps_preview"]
    assert payload["diagrams"] == transaction_package["atlas_diagram_ids"]
    _assert_accepted_project_matches_transaction(
        accepted,
        transaction_package["accepted_project_preview"],
    )
    _assert_project_brief_matches_transaction(tmp_path, transaction_package["project_brief_record_text"], accepted_at=accepted["accepted_at"])
    _assert_committed_atlas_matches_transaction(tmp_path, transaction_package)
    _assert_compass_event_matches_transaction(
        tmp_path,
        payload["memory"]["event"],
        transaction_package["compass_memory_preview"],
    )
    _assert_committed_program_matches_transaction(tmp_path, transaction_package["program_result"])
    _assert_committed_registry_matches_transaction(tmp_path, transaction_package)
    _assert_committed_release_assignment_matches_transaction(
        tmp_path,
        release_assignment=transaction_package["release_assignment_result"],
        release_workstream_ids=transaction_package["release_workstream_ids"],
    )
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
    assert next(row for row in proposal["components"] if row["label"] == "Workout Builder Service")["release_scope"] == "supporting"
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


def _run_compiled_transaction_create(tmp_path: Path, *, prompt: str, capsys) -> tuple[float, int, dict, dict]:
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    compile_rc = greenfield_proposals.main(
        [
            "compile-transaction",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--output",
            transaction_file,
            "--release",
            "0.0.1",
            "--format",
            "json",
        ]
    )
    compile_output = capsys.readouterr().out
    assert compile_rc == 0, compile_output
    compile_payload = json.loads(compile_output)
    transaction_hash = str(compile_payload["product_create_transaction"]["transaction_hash"])
    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            transaction_file,
            "--transaction-hash",
            transaction_hash,
            "--confirm",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    return started, rc, payload, compile_payload


def _assert_committed_program_matches_transaction(tmp_path: Path, program_result: dict) -> None:
    umbrella_id = str(program_result["umbrella_id"]).strip().upper()
    program_path = tmp_path / "odylith/radar/source/programs" / f"{umbrella_id}.execution-waves.v1.json"
    committed = json.loads(program_path.read_text(encoding="utf-8"))

    assert committed["umbrella_id"] == umbrella_id
    assert committed["waves"] == program_result["waves"]


def _assert_committed_atlas_matches_transaction(tmp_path: Path, transaction_package: dict) -> None:
    atlas_sources = transaction_package["rendered_atlas_sources"]
    review_date = transaction_package["atlas_review_date"]
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    by_source = {
        str(row.get("source_mmd", "")): row
        for row in catalog.get("diagrams", [])
        if isinstance(row, dict)
    }

    for relative_path, source in atlas_sources.items():
        assert (tmp_path / relative_path).read_text(encoding="utf-8") == source
        assert by_source[relative_path]["last_reviewed_utc"] == review_date


def _assert_committed_registry_matches_transaction(tmp_path: Path, transaction_package: dict) -> None:
    registry_path = tmp_path / "odylith/registry/source/component_registry.v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    by_id = {
        str(row.get("component_id", "")): row
        for row in registry.get("components", [])
        if isinstance(row, dict)
    }
    rendered_specs = transaction_package["rendered_component_specs"]
    for preview in transaction_package["component_registry_preview"]:
        authoring_input = preview["authoring_input"]
        registry_entry = preview["registry_entry"]
        component_id = str(authoring_input["component_id"])
        label = str(authoring_input["label"])
        assert by_id[component_id] == registry_entry
        spec_path = tmp_path / registry_entry["spec_ref"]
        assert spec_path.read_text(encoding="utf-8") == rendered_specs[label].rstrip() + "\n"


def _assert_committed_release_assignment_matches_transaction(
    tmp_path: Path,
    *,
    release_assignment: dict,
    release_workstream_ids: list[str],
) -> None:
    event_log = tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl"
    committed_events = [
        json.loads(line)
        for line in event_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected_release_id = str(release_assignment["release"]["release_id"])
    expected_ids = [str(item).strip().upper() for item in release_workstream_ids]
    matching_ids = [
        str(event.get("workstream_id", "")).strip().upper()
        for event in committed_events
        if str(event.get("action", "")).strip() == "add"
        and str(event.get("release_id", "")).strip() == expected_release_id
    ]

    assert matching_ids == expected_ids


def _assert_accepted_project_matches_transaction(
    accepted_project: dict,
    accepted_project_preview: dict,
) -> None:
    expected = dict(accepted_project_preview)
    expected["accepted_at"] = accepted_project["accepted_at"]
    assert accepted_project == expected


def _assert_project_brief_matches_transaction(tmp_path: Path, project_brief_record_text: str, *, accepted_at: str) -> None:
    project_brief = (tmp_path / "odylith/runtime/source/project-brief.v1.md").read_text(encoding="utf-8")
    assert project_brief == _record_text_with_accepted_at(project_brief_record_text, accepted_at=accepted_at)


def _record_text_with_accepted_at(text: str, *, accepted_at: str) -> str:
    lines = str(text).rstrip().splitlines()
    return "\n".join(
        f"- accepted_at: {accepted_at}" if line.startswith("- accepted_at: ") else line
        for line in lines
    ).rstrip() + "\n"


def _assert_compass_event_matches_transaction(tmp_path: Path, event: dict, compass_memory_preview: dict) -> None:
    for key in (
        "kind",
        "summary",
        "author",
        "source",
        "workstreams",
        "context",
        "headline_hint",
        "evidence_tier",
        "work_category",
    ):
        if key in compass_memory_preview:
            assert event[key] == compass_memory_preview[key]
    assert event["components"]
    assert event["artifacts"] == _repo_relative_artifacts(tmp_path, compass_memory_preview.get("artifacts", []))
    assert event["ts_iso"] != "prewrite"


def _repo_relative_artifacts(tmp_path: Path, artifacts: list[str]) -> list[str]:
    normalized = []
    for artifact in artifacts:
        path = Path(str(artifact))
        if path.is_absolute():
            normalized.append(str(path.resolve().relative_to(tmp_path)))
        else:
            normalized.append(str(artifact)[2:] if str(artifact).startswith("./") else str(artifact))
    return normalized


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

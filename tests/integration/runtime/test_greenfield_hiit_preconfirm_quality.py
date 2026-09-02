from __future__ import annotations

import json
import time
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    combined_prompt_evidence_source,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)
from tests.unit.runtime.greenfield_proposal_fixtures import HIIT_CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


def test_hiit_greenfield_create_projects_model_authored_path_and_quality_under_sixty_seconds(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(HIIT_CONFIRMED_INTENT_TEXT, encoding="utf-8")

    prompt = "Draft a greenfield proposal for a guided HIIT interval training app"
    provider = _hiit_authoring_provider(prompt)
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (provider, "test-model", "low"),
    )

    started, rc, payload, transaction_payload = _run_proposed_transaction_create(
        tmp_path,
        prompt=prompt,
        capsys=capsys,
    )
    elapsed = time.perf_counter() - started

    assert rc == 0
    assert provider.calls == 1
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    proposal = accepted["proposal"]
    first_path = proposal["semantic_model"]["first_path_contract"]
    generated_source = _generated_source_payload(tmp_path)

    assert elapsed < 60.0
    assert payload["commit_manifest"]["status"] == "passed"
    assert payload["commit_manifest"]["issue_count"] == 0
    assert payload["commit_manifest"]["quality_lenses"] == {
        "status": "not_applicable",
        "lenses": {},
        "reason": "typed_structural_validation",
    }
    assert payload["commit_manifest"]["create_elapsed_seconds"] < 60.0
    assert "whole_project_elapsed_seconds" not in payload["commit_manifest"]
    assert len(payload["backlog"]) == 1
    assert len(payload["components"]) == 1
    assert len(payload["diagrams"]) == 4
    transaction_package = transaction_payload["prewrite_package"]
    assert payload["next_steps"] == transaction_package["next_steps_preview"]
    assert payload["diagrams"] == transaction_package["atlas_diagram_ids"]
    _assert_accepted_project_matches_transaction(
        accepted,
        transaction_package["accepted_project_preview"],
    )
    _assert_project_brief_matches_transaction(tmp_path, transaction_package["project_brief_record_text"])
    _assert_committed_atlas_matches_transaction(tmp_path, transaction_package)
    _assert_compass_event_matches_transaction(
        tmp_path,
        payload["memory"]["event"],
        transaction_package["compass_memory_preview"],
    )
    assert "program_result" not in transaction_package
    assert not list((tmp_path / "odylith/radar/source/programs").glob("*.execution-waves.v1.json"))
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
    assert first_path["actor"] == "trainee"
    assert first_path["visible_result"] == "session to history with date, workout, and total time"
    for banned in (
        "choose a workout, starts it",
        "Trainee Following",
        '["Optional"]',
        "<br/>Optional",
        "Implementation slice:",
        "Workout Builder Service proves one complete user path",
    ):
        assert banned not in generated_source


def _hiit_authoring_provider(prompt: str) -> StructuredAuthoringProvider:
    first_path = (
        "A trainee chooses a workout, starts it, the timer drives each work and rest interval "
        "with audio and on-screen cues, keeps the screen awake, marks the session complete, "
        "and saves the session to history with date, workout, and total time."
    )
    proof_boundary = (
        "Release 0.0.1 succeeds when a trainee can choose a preset interval workout, start it, "
        "follow each interval without touching the screen, complete the workout, and see the "
        "completed session in history with its date, workout, and total time."
    )
    intent = {
        "title": "PulseHIIT",
        "product_story": (
            "PulseHIIT helps a trainee start a guided high-intensity interval workout, follow "
            "hands-free timing and cues, and review the completed session afterward."
        ),
        "problem": (
            "A trainee needs hands-free interval timing and cues without repeatedly touching "
            "the screen."
        ),
        "opportunity": (
            "One guided path can turn a preset workout into a completed, reviewable session."
        ),
        "product_view": (
            "PulseHIIT guides the trainee through intervals and preserves the completed session "
            "in history."
        ),
        "state_object": "workout session",
        "first_path": first_path,
        "proof_boundary": proof_boundary,
        "customer": "trainee",
        "success_metrics": [proof_boundary],
        "evidence_requirements": [
            "Audio cues and on-screen cues must both be visible in the proof boundary."
        ],
        "operational_constraints": [
            "The workout can run locally without live coaching or wearable integrations."
        ],
        "human_actors": ["trainee"],
        "external_systems": ["device wake-lock"],
        "internal_systems": [
            "Workout library",
            "the timer",
            "Session history",
            "Workout builder",
        ],
        "assumptions": [
            "Release 0.0.1 starts with preset interval workouts before complex custom programming."
        ],
        "ambiguities": [],
        "non_goals": [],
    }
    relations = [
        {
            "actor_kind": "human",
            "actor_quote": "trainee",
            "actor_fact_quote": "trainee",
            "event_quote": "A trainee chooses a workout",
            "action_verb_quote": "chooses",
            "target_quote": "a workout",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "human",
            "actor_quote": "trainee",
            "actor_fact_quote": "trainee",
            "event_quote": "starts it",
            "action_verb_quote": "starts",
            "target_quote": "it",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_quote": "the timer",
            "owner_system_quote": "the timer",
            "event_quote": "the timer drives each work and rest interval with audio and on-screen cues",
            "action_verb_quote": "drives",
            "target_quote": "each work and rest interval",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_quote": "the timer",
            "owner_system_quote": "the timer",
            "event_quote": "keeps the screen awake",
            "action_verb_quote": "keeps",
            "target_quote": "the screen awake",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_quote": "the timer",
            "owner_system_quote": "the timer",
            "event_quote": "marks the session complete",
            "action_verb_quote": "marks",
            "target_quote": "the session complete",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_quote": "the timer",
            "owner_system_quote": "the timer",
            "event_quote": "saves the session to history with date, workout, and total time",
            "action_verb_quote": "saves",
            "target_quote": "the session",
            "visible_result_quote": "session to history with date, workout, and total time",
        },
    ]
    evidence = combined_prompt_evidence_source(
        prompt=prompt,
        edit_evidence=HIIT_CONFIRMED_INTENT_TEXT,
    )
    return StructuredAuthoringProvider(
        authored_response(
            intent,
            evidence_text=evidence,
            first_path_relations=relations,
            terminal_component_owner="the timer",
        )
    )


def _run_proposed_transaction_create(tmp_path: Path, *, prompt: str, capsys) -> tuple[float, int, dict, dict]:
    propose_rc = greenfield_proposals_cli.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--edit-evidence",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--format",
            "json",
        ]
    )
    propose_output = capsys.readouterr().out
    assert propose_rc == 0, propose_output
    propose_payload = json.loads(propose_output)
    transaction_hash = str(propose_payload["product_create_transaction"]["transaction_hash"])
    transaction_file = str(propose_payload["transaction_file"])
    transaction_payload = json.loads((tmp_path / transaction_file).read_text(encoding="utf-8"))
    started = time.perf_counter()
    rc = greenfield_proposals_cli.main(
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
    return started, rc, payload, transaction_payload


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
    assert accepted_project == accepted_project_preview


def _assert_project_brief_matches_transaction(tmp_path: Path, project_brief_record_text: str) -> None:
    project_brief = (tmp_path / "odylith/runtime/source/project-brief.v1.md").read_text(encoding="utf-8")
    assert project_brief == project_brief_record_text


def _assert_compass_event_matches_transaction(tmp_path: Path, event: dict, compass_memory_preview: dict) -> None:
    assert event == compass_memory_preview
    stream_path = tmp_path / "odylith/compass/runtime/agent-stream.v1.jsonl"
    stream_events = [
        json.loads(line)
        for line in stream_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert compass_memory_preview in stream_events


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

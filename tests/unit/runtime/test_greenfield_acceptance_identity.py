from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.domain_intelligence import greenfield_acceptance_identity
from odylith.runtime.domain_intelligence import proposal_memory


PRIOR_ACCEPTED_AT = "2026-07-09T08:00:00-07:00"
FRESH_ACCEPTED_AT = "2026-07-10T09:30:00-07:00"


def _acceptance_surfaces(
    *,
    path_root: Path,
    accepted_at: str,
    evidence: str = "Learner review evidence is accepted.",
) -> tuple[dict[str, object], str, dict[str, object]]:
    idea_path = path_root / "odylith/radar/source/ideas/B-001-choice-practice.md"
    brief_path = path_root / "odylith/runtime/source/project-brief.v1.md"
    accepted_project = {
        "schema_version": "odylith.accepted_project.v1",
        "origin": "greenfield",
        "evidence_tier": "user_intent",
        "accepted_at": accepted_at,
        "title": "Choice Practice Journal",
        "proposal": {"intent": {"summary": evidence}},
        "created": {
            "workstreams": [{"idea_id": "B-001", "idea_path": str(idea_path)}],
            "components": [{"component_id": "choice-journal"}],
            "diagrams": ["D-001"],
            "release_selector": "0.0.1",
            "release_id": "release-choice-practice-0-0-1",
        },
        "source_launch": {
            "verification_commands": ["./.odylith/bin/odylith validate"],
        },
        "validation_gate": {"status": "passed"},
    }
    project_brief = (
        "# Choice Practice Journal Project Brief\n\n"
        "- schema: odylith.greenfield.project_brief.v1\n"
        f"- accepted_at: {accepted_at}\n\n"
        "## Brief\n"
        f"- outcome: {evidence}\n"
    )
    compass_event = {
        "version": "v1",
        "kind": "decision",
        "summary": "Accepted greenfield proposal for Choice Practice Journal: 1 workstream.",
        "ts_iso": accepted_at,
        "author": "odylith",
        "source": "domain-intelligence",
        "workstreams": ["B-001"],
        "artifacts": [str(brief_path), str(idea_path)],
        "components": ["choice-journal"],
        "context": evidence,
        "headline_hint": "Greenfield proposal accepted for Choice Practice Journal",
        "evidence_tier": "user_intent",
        "work_category": "governance",
    }
    return accepted_project, project_brief, compass_event


def _persist_surfaces(
    root: Path,
    accepted_project: dict[str, object],
    project_brief: str,
    compass_event: dict[str, object],
) -> None:
    accepted_path = root / "odylith/runtime/source/accepted-project.v1.json"
    brief_path = root / "odylith/runtime/source/project-brief.v1.md"
    stream_path = root / agent_runtime_contract.AGENT_STREAM_PATH
    accepted_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    accepted_path.write_text(f"{json.dumps(accepted_project, sort_keys=True)}\n", encoding="utf-8")
    brief_path.write_text(project_brief, encoding="utf-8")
    stream_path.write_text(f"{json.dumps(compass_event, sort_keys=True)}\n", encoding="utf-8")


def _resolved_surfaces(
    accepted_project: dict[str, object],
    project_brief: str,
    compass_event: dict[str, object],
    *,
    accepted_at: str,
) -> tuple[dict[str, object], str, dict[str, object]]:
    accepted = {**accepted_project, "accepted_at": accepted_at}
    brief = proposal_memory.compiled_project_brief_record_text(project_brief, accepted_at=accepted_at)
    event = {**compass_event, "ts_iso": accepted_at}
    return accepted, brief, event


def test_identical_accepted_evidence_reuses_prior_timestamp_before_exact_write(tmp_path: Path) -> None:
    prior = _acceptance_surfaces(path_root=tmp_path, accepted_at=PRIOR_ACCEPTED_AT)
    _persist_surfaces(tmp_path, *prior)
    current = _acceptance_surfaces(path_root=tmp_path, accepted_at=FRESH_ACCEPTED_AT)

    resolved = greenfield_acceptance_identity.resolve_preconfirm_acceptance_timestamp(
        repo_root=tmp_path,
        fresh_accepted_at=FRESH_ACCEPTED_AT,
        accepted_project_preview=current[0],
        project_brief_record_text=current[1],
        compass_memory_preview=current[2],
    )
    accepted, brief, event = _resolved_surfaces(*current, accepted_at=resolved)
    result = proposal_memory.record_compiled_greenfield_acceptance(
        repo_root=tmp_path,
        accepted_project_preview=accepted,
        project_brief_record_text=brief,
        compass_memory_preview=event,
    )

    stream_path = tmp_path / agent_runtime_contract.AGENT_STREAM_PATH
    assert resolved == PRIOR_ACCEPTED_AT
    assert result["reused_existing"] is True
    assert len([line for line in stream_path.read_text(encoding="utf-8").splitlines() if line.strip()]) == 1
    assert json.loads((tmp_path / proposal_memory.ACCEPTED_PROJECT_SOURCE_PATH).read_text(encoding="utf-8")) == prior[0]
    assert (tmp_path / proposal_memory.PROJECT_BRIEF_SOURCE_PATH).read_text(encoding="utf-8") == prior[1]


def test_changed_accepted_evidence_with_stable_ids_keeps_fresh_timestamp(tmp_path: Path) -> None:
    prior = _acceptance_surfaces(path_root=tmp_path, accepted_at=PRIOR_ACCEPTED_AT)
    _persist_surfaces(tmp_path, *prior)
    current = _acceptance_surfaces(
        path_root=tmp_path,
        accepted_at=FRESH_ACCEPTED_AT,
        evidence="Learner and facilitator review evidence is accepted.",
    )

    resolved = greenfield_acceptance_identity.resolve_preconfirm_acceptance_timestamp(
        repo_root=tmp_path,
        fresh_accepted_at=FRESH_ACCEPTED_AT,
        accepted_project_preview=current[0],
        project_brief_record_text=current[1],
        compass_memory_preview=current[2],
    )
    result = proposal_memory.record_compiled_greenfield_acceptance(
        repo_root=tmp_path,
        accepted_project_preview=current[0],
        project_brief_record_text=current[1],
        compass_memory_preview=current[2],
    )

    stream_path = tmp_path / agent_runtime_contract.AGENT_STREAM_PATH
    assert resolved == FRESH_ACCEPTED_AT
    assert result["reused_existing"] is False
    assert len([line for line in stream_path.read_text(encoding="utf-8").splitlines() if line.strip()]) == 2


@pytest.mark.parametrize(
    "corruption",
    ["accepted_json", "accepted_duplicate_key", "brief_timestamp", "stream_json", "stream_timestamp"],
)
def test_malformed_or_inconsistent_prior_surfaces_do_not_reuse(
    tmp_path: Path,
    corruption: str,
) -> None:
    prior = _acceptance_surfaces(path_root=tmp_path, accepted_at=PRIOR_ACCEPTED_AT)
    _persist_surfaces(tmp_path, *prior)
    if corruption == "accepted_json":
        (tmp_path / proposal_memory.ACCEPTED_PROJECT_SOURCE_PATH).write_text("{broken\n", encoding="utf-8")
    elif corruption == "accepted_duplicate_key":
        (tmp_path / proposal_memory.ACCEPTED_PROJECT_SOURCE_PATH).write_text(
            '{"accepted_at":"2026-07-09T08:00:00-07:00","accepted_at":"2026-07-09T08:00:00-07:00"}\n',
            encoding="utf-8",
        )
    elif corruption == "brief_timestamp":
        (tmp_path / proposal_memory.PROJECT_BRIEF_SOURCE_PATH).write_text(
            prior[1].replace(PRIOR_ACCEPTED_AT, "2026-07-08T08:00:00-07:00"),
            encoding="utf-8",
        )
    elif corruption == "stream_json":
        (tmp_path / agent_runtime_contract.AGENT_STREAM_PATH).write_text("{broken\n", encoding="utf-8")
    else:
        mismatched_event = {**prior[2], "ts_iso": "2026-07-08T08:00:00-07:00"}
        (tmp_path / agent_runtime_contract.AGENT_STREAM_PATH).write_text(
            f"{json.dumps(mismatched_event, sort_keys=True)}\n",
            encoding="utf-8",
        )
    current = _acceptance_surfaces(path_root=tmp_path, accepted_at=FRESH_ACCEPTED_AT)

    resolved = greenfield_acceptance_identity.resolve_preconfirm_acceptance_timestamp(
        repo_root=tmp_path,
        fresh_accepted_at=FRESH_ACCEPTED_AT,
        accepted_project_preview=current[0],
        project_brief_record_text=current[1],
        compass_memory_preview=current[2],
    )

    assert resolved == FRESH_ACCEPTED_AT


def test_acceptance_identity_is_portable_between_target_and_staging_roots(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    staging_root = tmp_path / "stage"
    prior = _acceptance_surfaces(path_root=target_root, accepted_at=PRIOR_ACCEPTED_AT)
    _persist_surfaces(target_root, *prior)
    current = _acceptance_surfaces(path_root=staging_root, accepted_at=FRESH_ACCEPTED_AT)
    current_created = current[0]["created"]
    assert isinstance(current_created, dict)
    current_created["diagrams"] = ("D-001",)

    resolved = greenfield_acceptance_identity.resolve_preconfirm_acceptance_timestamp(
        repo_root=target_root,
        fresh_accepted_at=FRESH_ACCEPTED_AT,
        accepted_project_preview=current[0],
        project_brief_record_text=current[1],
        compass_memory_preview=current[2],
        portable_roots=(staging_root,),
    )

    assert resolved == PRIOR_ACCEPTED_AT


def test_acceptance_identity_rejects_untrusted_previous_stage_paths(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    previous_staging_root = tmp_path / "stale-stage"
    current_staging_root = tmp_path / "current-stage"
    prior = _acceptance_surfaces(path_root=previous_staging_root, accepted_at=PRIOR_ACCEPTED_AT)
    _persist_surfaces(target_root, *prior)
    current = _acceptance_surfaces(path_root=current_staging_root, accepted_at=FRESH_ACCEPTED_AT)

    resolved = greenfield_acceptance_identity.resolve_preconfirm_acceptance_timestamp(
        repo_root=target_root,
        fresh_accepted_at=FRESH_ACCEPTED_AT,
        accepted_project_preview=current[0],
        project_brief_record_text=current[1],
        compass_memory_preview=current[2],
        portable_roots=(current_staging_root,),
    )

    assert resolved == FRESH_ACCEPTED_AT


def test_acceptance_identity_preserves_verification_command_prefixes(tmp_path: Path) -> None:
    prior = _acceptance_surfaces(path_root=tmp_path, accepted_at=PRIOR_ACCEPTED_AT)
    _persist_surfaces(tmp_path, *prior)
    current = _acceptance_surfaces(path_root=tmp_path, accepted_at=FRESH_ACCEPTED_AT)
    source_launch = current[0]["source_launch"]
    assert isinstance(source_launch, dict)
    source_launch["verification_commands"] = [".odylith/bin/odylith validate"]

    resolved = greenfield_acceptance_identity.resolve_preconfirm_acceptance_timestamp(
        repo_root=tmp_path,
        fresh_accepted_at=FRESH_ACCEPTED_AT,
        accepted_project_preview=current[0],
        project_brief_record_text=current[1],
        compass_memory_preview=current[2],
    )

    assert resolved == FRESH_ACCEPTED_AT

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.governance import release_planning_contract
from odylith.runtime.governance import release_planning_view_model


_SECTIONS = (
    "Problem",
    "Customer",
    "Opportunity",
    "Proposed Solution",
    "Scope",
    "Non-Goals",
    "Risks",
    "Dependencies",
    "Success Metrics",
    "Validation",
    "Rollout",
    "Why Now",
    "Product View",
    "Impacted Components",
    "Interface Changes",
    "Migration/Compatibility",
    "Test Strategy",
    "Open Questions",
)


def _idea_text(*, idea_id: str, title: str, status: str) -> str:
    sections = "\n\n".join(f"## {section}\nDetails." for section in _SECTIONS)
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-04-08\n\n"
        "priority: P1\n\n"
        "commercial_value: 4\n\n"
        "product_impact: 4\n\n"
        "market_value: 4\n\n"
        "impacted_parts: release planning\n\n"
        "sizing: M\n\n"
        "complexity: Medium\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: release test fixture\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        "promoted_to_plan:\n\n"
        "workstream_type: standalone\n\n"
        "workstream_parent:\n\n"
        "workstream_children:\n\n"
        "workstream_depends_on:\n\n"
        "workstream_blocks:\n\n"
        "related_diagram_ids:\n\n"
        "workstream_reopens:\n\n"
        "workstream_reopened_by:\n\n"
        "workstream_split_from:\n\n"
        "workstream_split_into:\n\n"
        "workstream_merged_into:\n\n"
        "workstream_merged_from:\n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{sections}\n"
    )


def _write_release_note(*, repo_root: Path, version: str, title: str) -> None:
    notes_root = repo_root / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / f"v{version}.md").write_text(
        (
            "---\n"
            f"version: {version}\n"
            f"title: {title}\n"
            "---\n\n"
            f"# {title}\n\n"
            "Release summary.\n"
        ),
        encoding="utf-8",
    )


def _seed_release_repo(repo_root: Path) -> None:
    (repo_root / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_root = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    ideas_root.mkdir(parents=True, exist_ok=True)
    ideas_root.joinpath("2026-04-08-b-101.md").write_text(
        _idea_text(idea_id="B-101", title="Current release work", status="implementation"),
        encoding="utf-8",
    )
    ideas_root.joinpath("2026-04-08-b-102.md").write_text(
        _idea_text(idea_id="B-102", title="Next release work", status="planning"),
        encoding="utf-8",
    )
    ideas_root.joinpath("2026-04-08-b-103.md").write_text(
        _idea_text(idea_id="B-103", title="Parked release work", status="parked"),
        encoding="utf-8",
    )
    _write_release_note(repo_root=repo_root, version="0.1.11", title="Launch Title")


def _release_row(*, release_id: str, status: str = "active", version: str = "", tag: str = "", name: str = "") -> dict[str, str]:
    return {
        "release_id": release_id,
        "status": status,
        "version": version,
        "tag": tag,
        "name": name,
        "notes": "",
        "created_utc": "2026-04-08",
        "shipped_utc": "",
        "closed_utc": "",
    }


def test_validate_release_planning_payload_keeps_release_name_explicit_and_note_title_separate(tmp_path: Path) -> None:
    _write_release_note(repo_root=tmp_path, version="0.1.11", title="Launch Title")

    state, errors = release_planning_contract.validate_release_planning_payload(
        repo_root=tmp_path,
        idea_specs={},
        registry_document={
            "version": "v1",
            "updated_utc": "2026-04-08",
            "aliases": {},
            "releases": [_release_row(release_id="release-0-1-11", version="0.1.11", name="Wrong Title")],
        },
        event_documents=[],
    )

    assert errors == []
    release = state.release_for_selector("Wrong Title")
    assert release.release_id == "release-0-1-11"
    assert release.name == "Wrong Title"
    assert release.inherited_name == "Launch Title"
    assert release.effective_name == "Wrong Title"
    assert release.display_label == "Wrong Title"
    try:
        state.release_for_selector("Launch Title")
    except release_planning_contract.ReleaseSelectorError:
        pass
    else:  # pragma: no cover
        raise AssertionError("release-note title should not resolve as a release-planning name")


def test_validate_release_planning_payload_rejects_ambiguous_selectors(tmp_path: Path) -> None:
    _state, errors = release_planning_contract.validate_release_planning_payload(
        repo_root=tmp_path,
        idea_specs={},
        registry_document={
            "version": "v1",
            "updated_utc": "2026-04-08",
            "aliases": {},
            "releases": [
                _release_row(release_id="release-a", version="0.1.12"),
                _release_row(release_id="release-b", version="0.1.12"),
            ],
        },
        event_documents=[],
    )

    assert any("selector `0.1.12` is ambiguous across releases ['release-a', 'release-b']" in error for error in errors)


def test_validate_release_planning_payload_rejects_active_assignment_for_parked_workstream(tmp_path: Path) -> None:
    _state, errors = release_planning_contract.validate_release_planning_payload(
        repo_root=tmp_path,
        idea_specs={"B-103": SimpleNamespace(status="parked")},
        registry_document={
            "version": "v1",
            "updated_utc": "2026-04-08",
            "aliases": {"current": "release-a"},
            "releases": [_release_row(release_id="release-a")],
        },
        event_documents=[
            {
                "action": "add",
                "workstream_id": "B-103",
                "release_id": "release-a",
                "recorded_at": "2026-04-08T00:00:00Z",
            }
        ],
    )

    assert any("`B-103` with status `parked` cannot target active release `release-a`" in error for error in errors)


def test_release_authoring_round_trips_registry_and_event_history(tmp_path: Path) -> None:
    _seed_release_repo(tmp_path)

    assert (
        release_planning_authoring.main(
            ["--repo-root", str(tmp_path), "create", "release-0-1-11", "--version", "0.1.11", "--alias", "current"]
        )
        == 0
    )
    assert (
        release_planning_authoring.main(
            ["--repo-root", str(tmp_path), "create", "release-next", "--name", "Next Cut", "--alias", "next"]
        )
        == 0
    )
    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "add", "B-101", "current"]) == 0
    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "move", "B-101", "next"]) == 0
    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "remove", "B-101", "next"]) == 0

    registry_path = release_planning_contract.releases_registry_path(repo_root=tmp_path)
    registry_document, registry_errors = release_planning_contract.load_registry_document(path=registry_path)
    assert registry_errors == []
    assert registry_document["aliases"] == {"current": "release-0-1-11", "next": "release-next"}

    event_path = release_planning_contract.release_assignment_event_log_path(repo_root=tmp_path)
    event_documents, event_errors = release_planning_contract.load_assignment_event_documents(path=event_path)
    assert event_errors == []
    assert [row["action"] for row in event_documents] == ["add", "move", "remove"]
    assert event_documents[1]["from_release_id"] == "release-0-1-11"
    assert event_documents[1]["to_release_id"] == "release-next"

    payload, errors, state = release_planning_view_model.build_release_view_from_repo(
        repo_root=tmp_path,
        idea_specs={
            "B-101": SimpleNamespace(status="implementation"),
            "B-102": SimpleNamespace(status="planning"),
            "B-103": SimpleNamespace(status="parked"),
        },
    )
    assert errors == []
    assert state.release_for_selector("current release").release_id == "release-0-1-11"
    assert state.release_for_selector("next").release_id == "release-next"
    assert payload["current_release"]["effective_name"] == "0.1.11"
    assert payload["current_release"]["display_label"] == "0.1.11"
    assert payload["current_release"]["inherited_name"] == "Launch Title"
    assert payload["catalog"][0]["display_label"] == "0.1.11"
    assert "Removed from" in payload["workstreams"]["B-101"]["history_summary"]
    assert "Next Cut" in payload["workstreams"]["B-101"]["history_summary"]
    assert "release-next" not in payload["workstreams"]["B-101"]["history_summary"]
    assert "Launch Title" not in payload["workstreams"]["B-101"]["history_summary"]


def test_release_authoring_dry_run_does_not_write_and_noop_update_fails(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_release_repo(tmp_path)

    assert (
        release_planning_authoring.main(
            ["--repo-root", str(tmp_path), "create", "release-dry-run", "--alias", "current", "--dry-run"]
        )
        == 0
    )
    assert not release_planning_contract.releases_registry_path(repo_root=tmp_path).exists()

    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "create", "release-live"]) == 0
    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "update", "release-live"]) == 2

    output = capsys.readouterr().out
    assert "update is a no-op" in output


def test_release_view_payload_tracks_finished_removed_workstreams_as_completed_members(tmp_path: Path) -> None:
    state, errors = release_planning_contract.validate_release_planning_payload(
        repo_root=tmp_path,
        idea_specs={"B-101": SimpleNamespace(status="finished")},
        registry_document={
            "version": "v1",
            "updated_utc": "2026-04-08",
            "aliases": {"current": "release-a"},
            "releases": [_release_row(release_id="release-a")],
        },
        event_documents=[
            {
                "action": "add",
                "workstream_id": "B-101",
                "release_id": "release-a",
                "recorded_at": "2026-04-08T00:00:00Z",
            },
            {
                "action": "remove",
                "workstream_id": "B-101",
                "release_id": "release-a",
                "recorded_at": "2026-04-08T01:00:00Z",
            },
        ],
    )

    assert errors == []
    payload = release_planning_view_model.build_release_view_payload(state=state)
    release = payload["catalog"][0]
    assert release["active_workstreams"] == []
    assert release["completed_workstreams"] == ["B-101"]
    assert release["completed_workstream_count"] == 1


def test_release_authoring_add_finished_workstream_records_completed_member(tmp_path: Path) -> None:
    _seed_release_repo(tmp_path)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    ideas_root.joinpath("2026-04-08-b-104.md").write_text(
        _idea_text(idea_id="B-104", title="Finished release member", status="finished"),
        encoding="utf-8",
    )

    assert (
        release_planning_authoring.main(
            ["--repo-root", str(tmp_path), "create", "release-0-1-11", "--version", "0.1.11", "--alias", "current"]
        )
        == 0
    )
    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "add", "B-104", "current"]) == 0

    event_path = release_planning_contract.release_assignment_event_log_path(repo_root=tmp_path)
    event_documents, event_errors = release_planning_contract.load_assignment_event_documents(path=event_path)
    assert event_errors == []
    assert [row["action"] for row in event_documents] == ["add", "remove"]
    assert [row["release_id"] for row in event_documents] == ["release-0-1-11", "release-0-1-11"]

    payload, errors, _state = release_planning_view_model.build_release_view_from_repo(
        repo_root=tmp_path,
        idea_specs={"B-104": SimpleNamespace(status="finished")},
    )
    assert errors == []
    release = payload["current_release"]
    assert release["active_workstreams"] == []
    assert release["completed_workstreams"] == ["B-104"]
    assert payload["workstreams"]["B-104"]["active_release_id"] == ""
    assert payload["workstreams"]["B-104"]["history_summary"] == "Removed from 0.1.11"


def test_release_authoring_rejects_duplicate_completed_member_add(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_release_repo(tmp_path)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    ideas_root.joinpath("2026-04-08-b-104.md").write_text(
        _idea_text(idea_id="B-104", title="Finished release member", status="finished"),
        encoding="utf-8",
    )

    assert (
        release_planning_authoring.main(
            ["--repo-root", str(tmp_path), "create", "release-0-1-11", "--version", "0.1.11", "--alias", "current"]
        )
        == 0
    )
    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "add", "B-104", "current"]) == 0
    capsys.readouterr()

    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "add", "B-104", "current"]) == 2
    assert "already recorded as completed" in capsys.readouterr().out


def test_release_authoring_json_output_renders_list_and_show(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_release_repo(tmp_path)

    assert (
        release_planning_authoring.main(
            ["--repo-root", str(tmp_path), "create", "release-0-1-11", "--version", "0.1.11", "--alias", "current"]
        )
        == 0
    )
    capsys.readouterr()

    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "list", "--json"]) == 0
    list_payload = json.loads(capsys.readouterr().out)
    assert list_payload["command"] == "list"
    assert list_payload["releases"][0]["release_id"] == "release-0-1-11"
    assert list_payload["releases"][0]["aliases"] == ["current"]

    assert release_planning_authoring.main(["--repo-root", str(tmp_path), "show", "--json", "current"]) == 0
    show_payload = json.loads(capsys.readouterr().out)
    assert show_payload["command"] == "show"
    assert show_payload["release"]["release_id"] == "release-0-1-11"
    assert show_payload["release"]["effective_name"] == "0.1.11"
    assert show_payload["release"]["inherited_name"] == "Launch Title"


def test_release_create_json_emits_execution_governance_payload(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_release_repo(tmp_path)

    assert (
        release_planning_authoring.main(
            [
                "--repo-root",
                str(tmp_path),
                "create",
                "release-0-1-11",
                "--version",
                "0.1.11",
                "--alias",
                "current",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["execution_governance"]["admissibility"]["outcome"] == "admit"
    assert payload["execution_governance"]["contract"]["authoritative_lane"] == "governance.release_planning.authoritative"
    assert payload["execution_governance"]["contract"]["host_profile"]["host_family"]

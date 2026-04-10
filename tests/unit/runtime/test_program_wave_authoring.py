from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import program_wave_authoring


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


def _idea_text(
    *,
    idea_id: str,
    title: str,
    promoted_to_plan: str = "",
    execution_model: str = "standard",
    workstream_type: str = "standalone",
    workstream_parent: str = "",
    workstream_children: str = "",
) -> str:
    sections = "\n\n".join(f"## {section}\nDetails." for section in _SECTIONS)
    return (
        "---\n"
        "status: implementation\n"
        f"idea_id: {idea_id}\n"
        f"title: {title}\n"
        "date: 2026-04-09\n"
        "priority: P1\n"
        "commercial_value: 4\n"
        "product_impact: 4\n"
        "market_value: 4\n"
        "impacted_parts: execution program tests\n"
        "sizing: M\n"
        "complexity: Medium\n"
        "ordering_score: 100\n"
        "ordering_rationale: test fixture\n"
        "confidence: high\n"
        "founder_override: no\n"
        f"promoted_to_plan: {promoted_to_plan}\n"
        f"execution_model: {execution_model}\n"
        f"workstream_type: {workstream_type}\n"
        f"workstream_parent: {workstream_parent}\n"
        f"workstream_children: {workstream_children}\n"
        "workstream_depends_on:\n"
        "workstream_blocks:\n"
        "related_diagram_ids:\n"
        "workstream_reopens:\n"
        "workstream_reopened_by:\n"
        "workstream_split_from:\n"
        "workstream_split_into:\n"
        "workstream_merged_into:\n"
        "workstream_merged_from:\n"
        "supersedes:\n"
        "superseded_by:\n"
        "---\n\n"
        f"{sections}\n"
    )


def _write_plan(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-04-09\n\n"
            "Updated: 2026-04-09\n\n"
            "Goal: test\n\n"
            "Assumptions: test\n\n"
            "Constraints: test\n\n"
            "Reversibility: test\n\n"
            "Boundary Conditions: test\n\n"
            "## Context/Problem Statement\n- [ ] test\n"
        ),
        encoding="utf-8",
    )


def _seed_program_repo(repo_root: Path) -> None:
    (repo_root / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_root = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    ideas_root.mkdir(parents=True, exist_ok=True)

    umbrella_plan = "odylith/technical-plans/in-progress/2026-04-09-b-201.md"
    child_one_plan = "odylith/technical-plans/in-progress/2026-04-09-b-202.md"
    child_two_plan = "odylith/technical-plans/in-progress/2026-04-09-b-203.md"

    ideas_root.joinpath("2026-04-09-b-201.md").write_text(
        _idea_text(
            idea_id="B-201",
            title="Execution umbrella",
            promoted_to_plan=umbrella_plan,
            workstream_type="umbrella",
            workstream_children="B-202,B-203",
        ),
        encoding="utf-8",
    )
    ideas_root.joinpath("2026-04-09-b-202.md").write_text(
        _idea_text(
            idea_id="B-202",
            title="Contract engine",
            promoted_to_plan=child_one_plan,
            workstream_type="child",
            workstream_parent="B-201",
        ),
        encoding="utf-8",
    )
    ideas_root.joinpath("2026-04-09-b-203.md").write_text(
        _idea_text(
            idea_id="B-203",
            title="Policy middleware",
            promoted_to_plan=child_two_plan,
            workstream_type="child",
            workstream_parent="B-201",
        ),
        encoding="utf-8",
    )
    ideas_root.joinpath("2026-04-09-b-299.md").write_text(
        _idea_text(
            idea_id="B-299",
            title="Outsider",
            workstream_type="child",
            workstream_parent="B-999",
        ),
        encoding="utf-8",
    )

    _write_plan(repo_root / umbrella_plan)
    _write_plan(repo_root / child_one_plan)
    _write_plan(repo_root / child_two_plan)


def test_program_create_scaffolds_program_and_updates_execution_model(tmp_path: Path) -> None:
    _seed_program_repo(tmp_path)

    rc = program_wave_authoring.run_program(["--repo-root", str(tmp_path), "create", "B-201"])

    assert rc == 0
    idea_text = (
        tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-09-b-201.md"
    ).read_text(encoding="utf-8")
    assert "execution_model: umbrella_waves" in idea_text

    program_path = (
        tmp_path / "odylith" / "radar" / "source" / "programs" / "B-201.execution-waves.v1.json"
    )
    payload = json.loads(program_path.read_text(encoding="utf-8"))
    assert [wave["wave_id"] for wave in payload["waves"]] == ["W1", "W2"]
    assert payload["waves"][0]["status"] == "active"
    assert payload["waves"][0]["primary_workstreams"] == ["B-202"]
    assert payload["waves"][1]["depends_on"] == ["W1"]


def test_program_create_json_emits_execution_governance_payload(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_program_repo(tmp_path)

    rc = program_wave_authoring.run_program(["--repo-root", str(tmp_path), "create", "B-201", "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["execution_governance"]["admissibility"]["outcome"] == "admit"
    assert payload["execution_governance"]["contract"]["authoritative_lane"] == "governance.program_wave.authoritative"
    assert payload["execution_governance"]["contract"]["host_profile"]["host_family"]


def test_program_status_and_next_fail_closed_when_program_file_is_missing(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_program_repo(tmp_path)

    assert program_wave_authoring.run_program(["--repo-root", str(tmp_path), "status", "B-201", "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["wave_count"] == 0
    assert status_payload["unassigned_children"] == ["B-202", "B-203"]
    assert status_payload["next_command"] == "odylith program create B-201"

    assert program_wave_authoring.run_program(["--repo-root", str(tmp_path), "next", "B-201", "--json"]) == 0
    next_payload = json.loads(capsys.readouterr().out)
    assert next_payload["next_command"] == "odylith program create B-201"


def test_wave_assign_and_gate_add_round_trip_program_file(tmp_path: Path) -> None:
    _seed_program_repo(tmp_path)
    assert program_wave_authoring.run_program(["--repo-root", str(tmp_path), "create", "B-201"]) == 0

    assert program_wave_authoring.run_wave(["--repo-root", str(tmp_path), "unassign", "B-201", "W2", "B-203"]) == 0
    assert (
        program_wave_authoring.run_wave(
            ["--repo-root", str(tmp_path), "assign", "B-201", "W1", "B-203", "--role", "carried"]
        )
        == 0
    )
    assert (
        program_wave_authoring.run_wave(
            [
                "--repo-root",
                str(tmp_path),
                "gate-add",
                "B-201",
                "W1",
                "B-203",
                "--label",
                "Policy middleware gate",
            ]
        )
        == 0
    )

    payload = json.loads(
        (
            tmp_path / "odylith" / "radar" / "source" / "programs" / "B-201.execution-waves.v1.json"
        ).read_text(encoding="utf-8")
    )
    wave_one = next(wave for wave in payload["waves"] if wave["wave_id"] == "W1")
    assert wave_one["carried_workstreams"] == ["B-203"]
    assert wave_one["gate_refs"] == [
        {
            "workstream_id": "B-203",
            "plan_path": "odylith/technical-plans/in-progress/2026-04-09-b-203.md",
            "label": "Policy middleware gate",
        }
    ]


def test_wave_assign_rejects_non_child_workstream(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _seed_program_repo(tmp_path)
    assert program_wave_authoring.run_program(["--repo-root", str(tmp_path), "create", "B-201"]) == 0

    rc = program_wave_authoring.run_wave(
        ["--repo-root", str(tmp_path), "assign", "B-201", "W1", "B-299", "--role", "primary"]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "action `mutate_wave_assign` is `deny`" in output
    assert "violated precondition: required_scope:HC-authoritative-governed-scope" in output
    assert "nearest admissible alternative: odylith program status B-201" in output


def test_program_update_defers_activation_until_dependencies_are_complete(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_program_repo(tmp_path)
    assert program_wave_authoring.run_program(["--repo-root", str(tmp_path), "create", "B-201"]) == 0
    capsys.readouterr()

    rc = program_wave_authoring.run_program(
        ["--repo-root", str(tmp_path), "update", "B-201", "--activate-wave", "W2"]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "action `mutate_program_update` is `defer`" in output
    assert "violated precondition: wave `W2` depends on `W1`" in output
    assert "nearest admissible alternative: odylith program status B-201" in output


def test_wave_gate_add_denies_when_workstream_is_not_in_the_wave(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_program_repo(tmp_path)
    assert program_wave_authoring.run_program(["--repo-root", str(tmp_path), "create", "B-201"]) == 0
    capsys.readouterr()

    rc = program_wave_authoring.run_wave(
        [
            "--repo-root",
            str(tmp_path),
            "gate-add",
            "B-201",
            "W1",
            "B-203",
            "--label",
            "Policy middleware gate",
        ]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "action `mutate_wave_gate_add` is `deny`" in output
    assert "violated precondition: required_scope:HC-authoritative-governed-scope" in output
    assert "nearest admissible alternative: odylith wave assign B-201 W1 B-203 --role primary" in output


def test_wave_unassign_denies_noop_when_workstream_is_not_in_the_wave(
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    _seed_program_repo(tmp_path)
    assert program_wave_authoring.run_program(["--repo-root", str(tmp_path), "create", "B-201"]) == 0
    capsys.readouterr()

    rc = program_wave_authoring.run_wave(
        ["--repo-root", str(tmp_path), "unassign", "B-201", "W1", "B-203"]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "action `mutate_wave_unassign` is `deny`" in output
    assert "violated precondition: required_scope:HC-authoritative-governed-scope" in output
    assert "nearest admissible alternative: odylith wave status B-201 W1" in output

from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import validate_backlog_contract as gate


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
    promoted_to_plan: str,
    execution_model: str = "standard",
    workstream_type: str = "standalone",
    workstream_parent: str = "",
    workstream_children: str = "",
    workstream_depends_on: str = "",
) -> str:
    body_sections = "\n\n".join(
        f"## {section}\nGrounded fixture coverage for {section.lower()} in this synthetic workstream."
        for section in _SECTIONS
    )
    return (
        "status: implementation\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-03-10\n\n"
        "priority: P0\n\n"
        "commercial_value: 5\n\n"
        "product_impact: 5\n\n"
        "market_value: 5\n\n"
        "impacted_parts: execution waves\n\n"
        "sizing: M\n\n"
        "complexity: High\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: test rationale\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        f"execution_model: {execution_model}\n\n"
        f"workstream_type: {workstream_type}\n\n"
        f"workstream_parent: {workstream_parent}\n\n"
        f"workstream_children: {workstream_children}\n\n"
        f"workstream_depends_on: {workstream_depends_on}\n\n"
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
        f"{body_sections}\n"
    )


def _write_plan(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-03-10\n\n"
            "Updated: 2026-03-10\n\n"
            "Goal: test\n\n"
            "Assumptions: test\n\n"
            "Constraints: test\n\n"
            "Reversibility: test\n\n"
            "Boundary Conditions: test\n\n"
            "## Context/Problem Statement\n- [ ] test\n"
        ),
        encoding="utf-8",
    )


def _write_program(root: Path, payload: dict[str, object], *, umbrella_id: str = "B-201") -> Path:
    path = root / "odylith" / "radar" / "source" / "programs" / f"{umbrella_id}.execution-waves.v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _seed_execution_wave_repo(root: Path) -> None:
    (root / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    idea_dir = root / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    idea_dir.mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "radar" / "source" / "programs").mkdir(parents=True, exist_ok=True)

    umbrella_path = idea_dir / "2026-03-10-umbrella.md"
    child_path = idea_dir / "2026-03-10-child.md"
    umbrella_path.write_text(
        _idea_text(
            idea_id="B-201",
            title="Umbrella",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-10-b-201.md",
            execution_model="umbrella_waves",
            workstream_type="umbrella",
            workstream_children="B-202",
        ),
        encoding="utf-8",
    )
    child_path.write_text(
        _idea_text(
            idea_id="B-202",
            title="Child",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-10-b-202.md",
            workstream_type="child",
            workstream_parent="B-201",
            workstream_depends_on="B-201",
        ),
        encoding="utf-8",
    )

    _write_plan(root / "odylith" / "technical-plans" / "in-progress" / "2026-03-10-b-201.md")
    _write_plan(root / "odylith" / "technical-plans" / "in-progress" / "2026-03-10-b-202.md")

    _write_program(
        root,
        {
            "umbrella_id": "B-201",
            "version": "v1",
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "Wave 1",
                    "status": "active",
                    "summary": "summary",
                    "depends_on": [],
                    "primary_workstreams": ["B-202"],
                    "carried_workstreams": [],
                    "in_band_workstreams": [],
                    "gate_refs": [
                        {
                            "workstream_id": "B-202",
                            "plan_path": "odylith/technical-plans/in-progress/2026-03-10-b-202.md",
                            "label": "gate",
                        }
                    ],
                }
            ],
        },
    )

    backlog_index = root / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index.write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-03-10\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| - | B-201 | Umbrella | P0 | 100 | 5 | 5 | 5 | M | High | implementation | [umbrella]({umbrella_path}) |\n"
            f"| - | B-202 | Child | P0 | 100 | 5 | 5 | 5 | M | High | implementation | [child]({child_path}) |\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-201 (rank ?)\n"
            "- why now: seed.\n"
            "- expected outcome: seed.\n"
            "- tradeoff: seed.\n"
            "- deferred for now: seed.\n"
            "- ranking basis: No manual priority override; seed.\n"
        ),
        encoding="utf-8",
    )

    (root / "odylith" / "technical-plans" / "INDEX.md").write_text(
        (
            "# Plan Index\n\n"
            "## Active Plans\n\n"
            "| Plan | Status | Created | Updated | Backlog |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| `odylith/technical-plans/in-progress/2026-03-10-b-201.md` | In progress | 2026-03-10 | 2026-03-10 | `B-201` |\n"
            "| `odylith/technical-plans/in-progress/2026-03-10-b-202.md` | In progress | 2026-03-10 | 2026-03-10 | `B-202` |\n"
        ),
        encoding="utf-8",
    )


def test_validate_backlog_contract_passes_with_execution_wave_program(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    assert "backlog contract validation passed" in capsys.readouterr().out


def test_validate_backlog_contract_fails_when_execution_wave_gate_ref_uses_wrong_plan(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)
    program_path = tmp_path / "odylith" / "radar" / "source" / "programs" / "B-201.execution-waves.v1.json"
    program_path.write_text(
        program_path.read_text(encoding="utf-8").replace(
            '"plan_path": "odylith/technical-plans/in-progress/2026-03-10-b-202.md"',
            '"plan_path": "odylith/technical-plans/in-progress/2026-03-10-wrong.md"',
        ),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "wave `W1` gate ref `B-202` points to `odylith/technical-plans/in-progress/2026-03-10-wrong.md`" in out


def test_validate_backlog_contract_fails_when_umbrella_wave_program_is_missing(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)
    (tmp_path / "odylith" / "radar" / "source" / "programs" / "B-201.execution-waves.v1.json").unlink()

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    assert "missing execution wave program file" in capsys.readouterr().out


def test_validate_backlog_contract_fails_when_non_umbrella_owns_execution_model(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)
    umbrella_path = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "2026-03-10-umbrella.md"
    umbrella_path.write_text(
        umbrella_path.read_text(encoding="utf-8").replace("workstream_type: umbrella", "workstream_type: child"),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    assert "`execution_model=umbrella_waves` is only valid for umbrella workstreams" in capsys.readouterr().out


def test_validate_backlog_contract_fails_when_same_wave_assigns_duplicate_roles(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)
    _write_program(
        tmp_path,
        {
            "umbrella_id": "B-201",
            "version": "v1",
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "Wave 1",
                    "status": "active",
                    "summary": "summary",
                    "depends_on": [],
                    "primary_workstreams": ["B-202"],
                    "carried_workstreams": ["B-202"],
                    "in_band_workstreams": [],
                    "gate_refs": [
                        {
                            "workstream_id": "B-202",
                            "plan_path": "odylith/technical-plans/in-progress/2026-03-10-b-202.md",
                            "label": "gate",
                        }
                    ],
                }
            ],
        },
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    assert "assigns workstream `B-202` to both `primary` and `carried` roles" in capsys.readouterr().out


def test_validate_backlog_contract_fails_when_wave_depends_on_unknown_wave(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)
    _write_program(
        tmp_path,
        {
            "umbrella_id": "B-201",
            "version": "v1",
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "Wave 1",
                    "status": "active",
                    "summary": "summary",
                    "depends_on": ["W9"],
                    "primary_workstreams": ["B-202"],
                    "carried_workstreams": [],
                    "in_band_workstreams": [],
                    "gate_refs": [
                        {
                            "workstream_id": "B-202",
                            "plan_path": "odylith/technical-plans/in-progress/2026-03-10-b-202.md",
                            "label": "gate",
                        }
                    ],
                }
            ],
        },
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    assert "depends on unknown wave `W9`" in capsys.readouterr().out


def test_validate_backlog_contract_fails_when_gate_ref_targets_non_member_workstream(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)
    _write_program(
        tmp_path,
        {
            "umbrella_id": "B-201",
            "version": "v1",
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "Wave 1",
                    "status": "active",
                    "summary": "summary",
                    "depends_on": [],
                    "primary_workstreams": ["B-202"],
                    "carried_workstreams": [],
                    "in_band_workstreams": [],
                    "gate_refs": [
                        {
                            "workstream_id": "B-201",
                            "plan_path": "odylith/technical-plans/in-progress/2026-03-10-b-201.md",
                            "label": "gate",
                        }
                    ],
                }
            ],
        },
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    assert "gate ref workstream `B-201` is not a member of that wave" in capsys.readouterr().out


def test_validate_backlog_contract_fails_when_program_file_is_orphaned(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)
    umbrella_path = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "2026-03-10-umbrella.md"
    umbrella_path.write_text(
        umbrella_path.read_text(encoding="utf-8").replace("execution_model: umbrella_waves", "execution_model: standard"),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    assert "no umbrella idea currently opts into `umbrella_waves` for this file" in capsys.readouterr().out


def test_validate_backlog_contract_fails_when_wave_member_topology_is_not_reciprocal(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_execution_wave_repo(tmp_path)
    umbrella_path = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "2026-03-10-umbrella.md"
    umbrella_path.write_text(
        umbrella_path.read_text(encoding="utf-8").replace("workstream_children: B-202", "workstream_children:"),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    assert "missing reciprocal `workstream_children` entry `B-202`" in capsys.readouterr().out

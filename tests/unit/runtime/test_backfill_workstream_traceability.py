from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import backfill_workstream_traceability as autofix
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


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
    status: str,
    promoted_to_plan: str,
    workstream_type: str = "",
    workstream_parent: str = "",
    workstream_children: str = "",
    workstream_reopens: str = "",
    workstream_reopened_by: str = "",
    workstream_split_from: str = "",
    workstream_split_into: str = "",
    workstream_merged_into: str = "",
    workstream_merged_from: str = "",
) -> str:
    section_bodies = {
        "Problem": "Traceability fixtures need realistic Radar detail before autofill runs.",
        "Customer": "Maintainers validating Radar topology inference from fixture repos.",
        "Opportunity": "Meaningful fixture prose keeps traceability autofill aligned with validation.",
        "Product View": "Autofill should reject weak ideas without breaking valid fixture repositories.",
        "Success Metrics": "- Traceability autofill validates governed workstream truth.\n- Report writes remain deterministic.",
    }
    sections = "\n\n".join(
        [
            f"## {name}\n{section_bodies.get(name, 'Fixture body for traceability autofill validation.')}"
            for name in _SECTIONS
        ]
    )
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-03-01\n\n"
        "priority: P0\n\n"
        "commercial_value: 5\n\n"
        "product_impact: 5\n\n"
        "market_value: 5\n\n"
        "impacted_parts: control grid\n\n"
        "sizing: L\n\n"
        "complexity: VeryHigh\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: baseline\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        f"workstream_type: {workstream_type}\n\n"
        f"workstream_parent: {workstream_parent}\n\n"
        f"workstream_children: {workstream_children}\n\n"
        "workstream_depends_on: \n\n"
        "workstream_blocks: \n\n"
        "related_diagram_ids: \n\n"
        f"workstream_reopens: {workstream_reopens}\n\n"
        f"workstream_reopened_by: {workstream_reopened_by}\n\n"
        f"workstream_split_from: {workstream_split_from}\n\n"
        f"workstream_split_into: {workstream_split_into}\n\n"
        f"workstream_merged_into: {workstream_merged_into}\n\n"
        f"workstream_merged_from: {workstream_merged_from}\n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{sections}\n"
    )


def _seed_repo(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)

    umbrella = ideas_dir / "2026-03-01-umbrella.md"
    umbrella.write_text(
        _idea_text(
            idea_id="B-021",
            title="Umbrella",
            status="planning",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-01-umbrella.md",
            workstream_type="umbrella",
            workstream_children="B-033",
        ),
        encoding="utf-8",
    )

    child = ideas_dir / "2026-03-01-child.md"
    child.write_text(
        _idea_text(
            idea_id="B-033",
            title="Traceability Upgrade",
            status="planning",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-01-child.md",
            workstream_type="child",
        ),
        encoding="utf-8",
    )

    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)
    for path in [
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-umbrella.md",
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-child.md",
    ]:
        path.write_text(
            "Status: In progress\n\nCreated: 2026-03-01\n\nUpdated: 2026-03-01\n\nGoal: x\n\nAssumptions: x\n\nConstraints: x\n\nReversibility: x\n\nBoundary Conditions: x\n\n## Context/Problem Statement\n- [ ] x\n",
            encoding="utf-8",
        )

    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "workstream-dependency-map.mmd").write_text(
        "flowchart LR\n  B-021 --> B-033\n",
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "diagrams": [
                    {
                        "diagram_id": "D-003",
                        "slug": "dep-map",
                        "title": "dep",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "platform",
                        "last_reviewed_utc": "2026-03-01",
                        "source_mmd": "odylith/atlas/source/workstream-dependency-map.mmd",
                        "source_svg": "odylith/atlas/source/workstream-dependency-map.mmd",
                        "source_png": "odylith/atlas/source/workstream-dependency-map.mmd",
                        "change_watch_paths": ["odylith/radar/source/ideas/2026-03"],
                        "summary": "dep",
                        "components": [{"name": "a", "description": "b"}],
                        "related_backlog": [str(child)],
                        "related_plans": ["odylith/technical-plans/in-progress/2026-03-01-child.md"],
                        "related_docs": ["consumer_repo.yaml"],
                        "related_code": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return umbrella, child


def test_backfill_infers_parent_dependencies_and_diagrams(tmp_path: Path) -> None:
    _, child_path = _seed_repo(tmp_path)

    rc = autofix.main(
        [
            "--repo-root",
            str(tmp_path),
            "--report",
            "odylith/radar/traceability-autofix-report.v1.json",
        ]
    )
    assert rc == 0

    spec = backlog_contract._parse_idea_spec(child_path)
    assert spec.metadata.get("workstream_parent") == "B-021"
    assert spec.metadata.get("workstream_depends_on") == "B-021"
    assert spec.metadata.get("related_diagram_ids") == "D-003"

    report = json.loads((tmp_path / "odylith" / "radar" / "traceability-autofix-report.v1.json").read_text(encoding="utf-8"))
    assert report["summary"]["fields_filled"] >= 3


def test_backfill_does_not_overwrite_without_force(tmp_path: Path) -> None:
    _, child_path = _seed_repo(tmp_path)
    text = child_path.read_text(encoding="utf-8")
    child_path.write_text(text.replace("workstream_parent: ", "workstream_parent: B-999"), encoding="utf-8")

    rc = autofix.main(["--repo-root", str(tmp_path)])
    assert rc == 0

    spec = backlog_contract._parse_idea_spec(child_path)
    assert spec.metadata.get("workstream_parent") == "B-999"
    report = json.loads((tmp_path / "odylith" / "radar" / "traceability-autofix-report.v1.json").read_text(encoding="utf-8"))
    assert report["summary"]["conflicts"] >= 0


def test_backfill_report_generated_utc_stable_when_no_content_changes(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    report_path = tmp_path / "odylith" / "radar" / "traceability-autofix-report.v1.json"

    rc = autofix.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    first = json.loads(report_path.read_text(encoding="utf-8"))
    first_mtime_ns = report_path.stat().st_mtime_ns

    rc = autofix.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    second = json.loads(report_path.read_text(encoding="utf-8"))
    second_mtime_ns = report_path.stat().st_mtime_ns

    assert first["generated_utc"] == second["generated_utc"]
    assert first_mtime_ns == second_mtime_ns


def test_backfill_reports_current_when_report_payload_is_unchanged(tmp_path: Path, capsys) -> None:
    _seed_repo(tmp_path)

    rc = autofix.main(["--repo-root", str(tmp_path)])
    assert rc == 0

    rc = autofix.main(["--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert rc == 0
    assert "- report_status: current" in output


def test_backfill_writes_only_canonical_odylith_report(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    rc = autofix.main(["--repo-root", str(tmp_path), "--report", "odylith/radar/traceability-autofix-report.v1.json"])
    assert rc == 0
    assert (tmp_path / "odylith" / "radar" / "traceability-autofix-report.v1.json").exists()
    assert not (tmp_path / "backlog").exists()


def test_backfill_does_not_flag_optional_topology_for_standalone(tmp_path: Path) -> None:
    _, child_path = _seed_repo(tmp_path)
    child_text = child_path.read_text(encoding="utf-8")
    child_path.write_text(
        child_text.replace("workstream_type: child", "workstream_type: standalone"),
        encoding="utf-8",
    )

    rc = autofix.main(["--repo-root", str(tmp_path)])
    assert rc == 0

    report = json.loads((tmp_path / "odylith" / "radar" / "traceability-autofix-report.v1.json").read_text(encoding="utf-8"))
    unresolved = [
        row for row in report.get("fields_unresolved", [])
        if isinstance(row, dict) and row.get("idea_id") == "B-033"
    ]
    unresolved_fields = {str(row.get("field", "")).strip() for row in unresolved}
    assert "workstream_parent" not in unresolved_fields
    assert "workstream_children" not in unresolved_fields


def test_backfill_skips_conflict_when_explicit_diagram_ids_are_superset(tmp_path: Path) -> None:
    umbrella_path, _child_path = _seed_repo(tmp_path)
    umbrella_text = umbrella_path.read_text(encoding="utf-8")
    umbrella_path.write_text(
        umbrella_text.replace(
            "related_diagram_ids: \n\n",
            "related_diagram_ids: D-002,D-003\n\n",
        ),
        encoding="utf-8",
    )

    rc = autofix.main(["--repo-root", str(tmp_path)])
    assert rc == 0

    report = json.loads((tmp_path / "odylith" / "radar" / "traceability-autofix-report.v1.json").read_text(encoding="utf-8"))
    conflicts = [
        row for row in report.get("conflicts_skipped", [])
        if isinstance(row, dict) and row.get("idea_id") == "B-021" and row.get("field") == "related_diagram_ids"
    ]
    assert conflicts == []


def test_backfill_infers_lineage_reciprocal_when_unambiguous(tmp_path: Path) -> None:
    umbrella_path, child_path = _seed_repo(tmp_path)
    child_text = child_path.read_text(encoding="utf-8")
    child_path.write_text(
        child_text.replace(
            "workstream_reopens: \n\n",
            "workstream_reopens: B-021\n\n",
        ),
        encoding="utf-8",
    )

    rc = autofix.main(["--repo-root", str(tmp_path)])
    assert rc == 0

    umbrella_spec = backlog_contract._parse_idea_spec(umbrella_path)
    assert umbrella_spec.metadata.get("workstream_reopened_by") == "B-033"


def test_backfill_leaves_lineage_blank_when_reciprocal_is_ambiguous(tmp_path: Path) -> None:
    umbrella_path, child_path = _seed_repo(tmp_path)
    ideas_dir = child_path.parent
    sibling_path = ideas_dir / "2026-03-01-sibling.md"
    sibling_path.write_text(
        _idea_text(
            idea_id="B-034",
            title="Sibling Traceability",
            status="planning",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-01-sibling.md",
            workstream_type="child",
            workstream_reopens="B-021",
        ),
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-sibling.md").write_text(
        "Status: In progress\n",
        encoding="utf-8",
    )
    child_text = child_path.read_text(encoding="utf-8")
    child_path.write_text(
        child_text.replace(
            "workstream_reopens: \n\n",
            "workstream_reopens: B-021\n\n",
        ),
        encoding="utf-8",
    )

    rc = autofix.main(
        [
            "--repo-root",
            str(tmp_path),
            "--report",
            "odylith/radar/traceability-autofix-report.v1.json",
        ]
    )
    assert rc == 0

    umbrella_spec = backlog_contract._parse_idea_spec(umbrella_path)
    assert umbrella_spec.metadata.get("workstream_reopened_by", "") == ""
    report = json.loads((tmp_path / "odylith" / "radar" / "traceability-autofix-report.v1.json").read_text(encoding="utf-8"))
    unresolved = report.get("fields_unresolved", [])
    assert any(
        row.get("idea_id") == "B-021"
        and row.get("field") == "workstream_reopened_by"
        for row in unresolved
        if isinstance(row, dict)
    )

from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import sync_session
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


def _repo_rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _seed_product_repo_shape(root: Path) -> None:
    (root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    registry_root = root / "odylith" / "registry" / "source"
    registry_root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname = \"odylith\"\nversion = \"0.1.11\"\n",
        encoding="utf-8",
    )
    (registry_root / "component_registry.v1.json").write_text("{\"components\": []}\n", encoding="utf-8")


def _idea_text(
    *,
    idea_id: str,
    title: str,
    date: str,
    status: str,
    priority: str,
    commercial_value: int,
    product_impact: int,
    market_value: int,
    sizing: str,
    complexity: str,
    ordering_score: int,
    founder_override: str,
    promoted_to_plan: str,
    workstream_type: str = "standalone",
    workstream_parent: str = "",
    workstream_children: str = "",
    workstream_reopens: str = "",
    workstream_reopened_by: str = "",
    workstream_split_from: str = "",
    workstream_split_into: str = "",
    workstream_merged_into: str = "",
    workstream_merged_from: str = "",
) -> str:
    body_sections = "\n\n".join([f"## {section}\nDetails." for section in _SECTIONS])
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        f"date: {date}\n\n"
        f"priority: {priority}\n\n"
        f"commercial_value: {commercial_value}\n\n"
        f"product_impact: {product_impact}\n\n"
        f"market_value: {market_value}\n\n"
        "impacted_parts: test surface\n\n"
        f"sizing: {sizing}\n\n"
        f"complexity: {complexity}\n\n"
        f"ordering_score: {ordering_score}\n\n"
        "ordering_rationale: test rationale\n\n"
        "confidence: high\n\n"
        f"founder_override: {founder_override}\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        f"workstream_type: {workstream_type}\n\n"
        f"workstream_parent: {workstream_parent}\n\n"
        f"workstream_children: {workstream_children}\n\n"
        "workstream_depends_on:\n\n"
        "workstream_blocks:\n\n"
        "related_diagram_ids:\n\n"
        f"workstream_reopens: {workstream_reopens}\n\n"
        f"workstream_reopened_by: {workstream_reopened_by}\n\n"
        f"workstream_split_from: {workstream_split_from}\n\n"
        f"workstream_split_into: {workstream_split_into}\n\n"
        f"workstream_merged_into: {workstream_merged_into}\n\n"
        f"workstream_merged_from: {workstream_merged_from}\n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{body_sections}\n"
    )


def _seed_minimal_repo(root: Path, *, product_repo: bool = False) -> tuple[Path, Path]:
    if product_repo:
        _seed_product_repo_shape(root)
    else:
        (root / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    idea_dir = root / "odylith" / "radar" / "source" / "ideas" / "2026-02"
    idea_dir.mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)

    queued_path = idea_dir / "2026-02-27-backlog-bootstrap.md"
    queued_path.write_text(
        _idea_text(
            idea_id="B-101",
            title="Backlog Bootstrap",
            date="2026-02-27",
            status="queued",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=3,
            sizing="L",
            complexity="High",
            ordering_score=89,
            founder_override="no",
            promoted_to_plan="",
        ),
        encoding="utf-8",
    )

    plan_path = root / "odylith" / "technical-plans" / "in-progress" / "2026-02-23-promoted.md"
    plan_path.write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-02-23\n\n"
            "Updated: 2026-02-23\n\n"
            "Goal: test\n\n"
            "Assumptions: test\n\n"
            "Constraints: test\n\n"
            "Reversibility: test\n\n"
            "Boundary Conditions: test\n\n"
            "## Context/Problem Statement\n- [ ] test\n"
        ),
        encoding="utf-8",
    )

    implementation_path = idea_dir / "2026-02-23-promoted.md"
    implementation_path.write_text(
        _idea_text(
            idea_id="B-102",
            title="Promoted Work",
            date="2026-02-23",
            status="implementation",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=4,
            sizing="L",
            complexity="High",
            ordering_score=95,
            founder_override="no",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-02-23-promoted.md",
        ),
        encoding="utf-8",
    )

    backlog_index = root / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index.write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-02-27\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| 1 | B-101 | Backlog Bootstrap | P1 | 89 | 4 | 4 | 3 | L | High | queued | [bootstrap]({_repo_rel(root, queued_path)}) |\n\n"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| - | B-102 | Promoted Work | P1 | 95 | 4 | 4 | 4 | L | High | implementation | [promoted]({_repo_rel(root, implementation_path)}) |\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-101 (rank 1)\n"
            "- why now: seed baseline.\n"
            "- expected outcome: quality uplift.\n"
            "- tradeoff: low risk.\n"
            "- deferred for now: none.\n"
            "- ranking basis: No manual priority override; score-based rank.\n"
        ),
        encoding="utf-8",
    )

    plan_index = root / "odylith" / "technical-plans" / "INDEX.md"
    plan_index.write_text(
        (
            "# Plan Index\n\n"
            "## Active Plans\n\n"
            "| Plan | Status | Created | Updated | Backlog |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| `odylith/technical-plans/in-progress/2026-02-23-promoted.md` | In progress | 2026-02-23 | 2026-02-23 | `B-102` |\n"
        ),
        encoding="utf-8",
    )
    return implementation_path, queued_path


def _add_parked_seed(root: Path) -> tuple[Path, Path]:
    idea_dir = root / "odylith" / "radar" / "source" / "ideas" / "2026-02"
    parked_filename = "2026-02-27-parked-work.md"
    parked_path = idea_dir / parked_filename
    parked_path.write_text(
        _idea_text(
            idea_id="B-103",
            title="Parked Work",
            date="2026-02-27",
            status="parked",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=3,
            sizing="L",
            complexity="High",
            ordering_score=89,
            founder_override="no",
            promoted_to_plan="",
        ),
        encoding="utf-8",
    )

    parked_plan_path = root / "odylith" / "technical-plans" / "parked" / "2026-02" / parked_filename
    parked_plan_path.parent.mkdir(parents=True, exist_ok=True)
    parked_plan_path.write_text(
        (
            "Status: Parked\n\n"
            "Created: 2026-02-27\n\n"
            "Updated: 2026-02-28\n\n"
            "Goal: parked test\n\n"
            "Assumptions: parked test\n\n"
            "Constraints: parked test\n\n"
            "Reversibility: parked test\n\n"
            "Boundary Conditions: parked test\n\n"
            "## Context/Problem Statement\n- [x] parked test\n"
        ),
        encoding="utf-8",
    )

    backlog_index = root / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_text = backlog_index.read_text(encoding="utf-8").replace(
        "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
        "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n",
        "## Parked (No Active Plan)\n\n"
        "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        f"| - | B-103 | Parked Work | P1 | 89 | 4 | 4 | 3 | L | High | parked | [parked]({parked_path}) |\n\n"
        "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
        "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n",
    )
    backlog_index.write_text(backlog_text, encoding="utf-8")
    return parked_path, parked_plan_path


def test_backlog_contract_passes_with_valid_seed(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path)

    rc = gate.main(
        [
            "--repo-root",
            str(tmp_path),
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--backlog-index",
            "odylith/radar/source/INDEX.md",
            "--plan-index",
            "odylith/technical-plans/INDEX.md",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog contract validation passed" in out
    assert "- releases: 0" in out
    assert "- active release targets: 0" in out


def test_backlog_contract_rejects_product_repo_workstream_title_prefix(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path, product_repo=True)
    prefixed_path = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-02" / "2026-02-27-backlog-bootstrap.md"
    prefixed_path.write_text(
        prefixed_path.read_text(encoding="utf-8").replace(
            "title: Backlog Bootstrap",
            "title: Odylith Backlog Bootstrap",
        ),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "must not start with `Odylith`" in out


def test_backlog_contract_fails_closed_on_invalid_release_planning_truth(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path)
    releases_root = tmp_path / "odylith" / "radar" / "source" / "releases"
    releases_root.mkdir(parents=True, exist_ok=True)
    (releases_root / "releases.v1.json").write_text(
        (
            "{\n"
            '  "version": "v1",\n'
            '  "updated_utc": "2026-04-08",\n'
            '  "aliases": {\n'
            '    "current": "release-0-1-11"\n'
            "  },\n"
            '  "releases": [\n'
            "    {\n"
            '      "release_id": "release-0-1-11",\n'
            '      "status": "shipped",\n'
            '      "version": "0.1.11",\n'
            '      "tag": "v0.1.11",\n'
            '      "name": "",\n'
            '      "notes": "",\n'
            '      "created_utc": "2026-04-08",\n'
            '      "shipped_utc": "2026-04-08",\n'
            '      "closed_utc": ""\n'
            "    }\n"
            "  ]\n"
            "}\n"
        ),
        encoding="utf-8",
    )
    (releases_root / "release-assignment-events.v1.jsonl").write_text("", encoding="utf-8")

    rc = gate.main(["--repo-root", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 2
    assert "backlog contract validation FAILED" in out
    assert "alias `current` cannot point to terminal release `release-0-1-11`" in out


def test_backlog_contract_allows_repo_relative_equivalent_links_from_another_checkout(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    source_root = tmp_path / "source"
    relocated_root = tmp_path / "relocated"
    source_root.mkdir()
    relocated_root.mkdir()
    source_implementation_path, source_queued_path = _seed_minimal_repo(source_root)
    relocated_implementation_path, relocated_queued_path = _seed_minimal_repo(relocated_root)

    backlog_index = relocated_root / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index.write_text(
        backlog_index.read_text(encoding="utf-8")
        .replace(_repo_rel(relocated_root, relocated_queued_path), str(source_queued_path))
        .replace(_repo_rel(relocated_root, relocated_implementation_path), str(source_implementation_path)),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(relocated_root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog contract validation passed" in out


def test_backlog_contract_rejects_relocated_link_when_relative_target_differs(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    source_root = tmp_path / "source"
    relocated_root = tmp_path / "relocated"
    source_root.mkdir()
    relocated_root.mkdir()
    source_implementation_path, _source_queued_path = _seed_minimal_repo(source_root)
    _relocated_implementation_path, relocated_queued_path = _seed_minimal_repo(relocated_root)

    backlog_index = relocated_root / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index.write_text(
        backlog_index.read_text(encoding="utf-8").replace(
            _repo_rel(relocated_root, relocated_queued_path),
            str(source_implementation_path),
        ),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(relocated_root)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "link for `B-101` must resolve under repo root" in out


def test_index_snapshots_round_trip_clean_empty_errors_from_cache(tmp_path: Path) -> None:
    _seed_minimal_repo(tmp_path)

    backlog_path = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    plan_path = tmp_path / "odylith" / "technical-plans" / "INDEX.md"

    backlog_snapshot = gate.load_backlog_index_snapshot(backlog_path)
    plan_snapshot = gate.load_plan_index_snapshot(plan_path)
    assert backlog_snapshot["finished"]["error"] == ""
    assert plan_snapshot["active"]["error"] == ""

    cached_backlog_snapshot = gate.load_backlog_index_snapshot(backlog_path)
    cached_plan_snapshot = gate.load_plan_index_snapshot(plan_path)
    assert cached_backlog_snapshot["finished"]["error"] == ""
    assert cached_plan_snapshot["active"]["error"] == ""


def test_rows_as_mapping_treats_none_error_as_clean_section() -> None:
    rows = gate.rows_as_mapping(
        section={
            "headers": ["idea_id", "title"],
            "rows": [["B-101", "Example"]],
            "error": None,
        },
        expected_headers=("idea_id", "title"),
    )
    assert rows == [{"idea_id": "B-101", "title": "Example"}]


def test_validate_backlog_index_treats_none_section_errors_as_empty(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path)
    ideas, idea_errors = gate._validate_idea_specs(tmp_path / "odylith" / "radar" / "source" / "ideas")  # noqa: SLF001
    assert idea_errors == []

    snapshot = gate._build_backlog_index_snapshot(tmp_path / "odylith" / "radar" / "source" / "INDEX.md")  # noqa: SLF001
    snapshot["active"]["error"] = None
    snapshot["execution"]["error"] = None
    snapshot["finished"]["error"] = None
    snapshot["parked"]["error"] = None
    monkeypatch.setattr(gate, "load_backlog_index_snapshot", lambda _path: snapshot)

    active_ids, execution_ids, parked_ids, finished_ids, active_ranks, errors = gate._validate_backlog_index(  # noqa: SLF001
        backlog_index=tmp_path / "odylith" / "radar" / "source" / "INDEX.md",
        ideas=ideas,
        repo_root=tmp_path,
    )

    assert errors == []
    assert active_ids == {"B-101"}
    assert execution_ids == {"B-102"}
    assert parked_ids == set()
    assert finished_ids == set()
    assert active_ranks == {"B-101": 1}


def test_validate_plan_index_treats_none_section_errors_as_empty(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path)
    ideas, idea_errors = gate._validate_idea_specs(tmp_path / "odylith" / "radar" / "source" / "ideas")  # noqa: SLF001
    assert idea_errors == []

    snapshot = gate._build_plan_index_snapshot(tmp_path / "odylith" / "technical-plans" / "INDEX.md")  # noqa: SLF001
    snapshot["active"]["error"] = None
    snapshot["parked"]["headers"] = list(gate._PLAN_COLS)  # noqa: SLF001
    snapshot["parked"]["rows"] = []
    snapshot["parked"]["error"] = None
    monkeypatch.setattr(gate, "load_plan_index_snapshot", lambda _path: snapshot)

    errors = gate._validate_plan_index(  # noqa: SLF001
        plan_index=tmp_path / "odylith" / "technical-plans" / "INDEX.md",
        execution_ids={"B-102"},
        parked_ids=set(),
        ideas=ideas,
        repo_root=tmp_path,
    )

    assert errors == []


def test_validate_idea_specs_reuses_active_sync_session_snapshot(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path)
    idea_root = tmp_path / "odylith" / "radar" / "source" / "ideas"
    parse_calls = 0
    original = gate._parse_idea_spec  # noqa: SLF001

    def _counted_parse(path: Path):  # noqa: ANN202
        nonlocal parse_calls
        parse_calls += 1
        return original(path)

    monkeypatch.setattr(gate, "_parse_idea_spec", _counted_parse)

    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    with sync_session.activate_sync_session(session):
        first_ideas, first_errors = gate._validate_idea_specs(idea_root)  # noqa: SLF001
        second_ideas, second_errors = gate._validate_idea_specs(idea_root)  # noqa: SLF001

    assert first_errors == []
    assert second_errors == []
    assert sorted(first_ideas) == sorted(second_ideas)
    assert parse_calls == 2


def test_backlog_contract_fails_when_promoted_to_plan_missing(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, _ = _seed_minimal_repo(tmp_path)
    text = implementation_path.read_text(encoding="utf-8")
    implementation_path.write_text(text.replace("promoted_to_plan: odylith/technical-plans/in-progress/2026-02-23-promoted.md", "promoted_to_plan:"), encoding="utf-8")

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "`implementation` idea missing `promoted_to_plan`" in out


def test_backlog_contract_fails_on_score_mismatch_without_override(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _, queued_path = _seed_minimal_repo(tmp_path)
    text = queued_path.read_text(encoding="utf-8")
    queued_path.write_text(text.replace("ordering_score: 89", "ordering_score: 88"), encoding="utf-8")

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "does not match formula" in out


def test_backlog_contract_allows_score_mismatch_with_founder_override(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _, queued_path = _seed_minimal_repo(tmp_path)
    text = queued_path.read_text(encoding="utf-8")
    text = text.replace("ordering_score: 89", "ordering_score: 88")
    text = text.replace("founder_override: no", "founder_override: yes")
    queued_path.write_text(text, encoding="utf-8")
    backlog_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_text = backlog_index.read_text(encoding="utf-8").replace(
            "| 1 | B-101 | Backlog Bootstrap | P1 | 89 |",
            "| 1 | B-101 | Backlog Bootstrap | P1 | 88 |",
    )
    backlog_text = backlog_text.replace(
        "- ranking basis: No manual priority override; score-based rank.",
        "- ranking basis: Manual priority override for sequencing; review checkpoint 2026-03-15.",
    )
    backlog_index.write_text(backlog_text, encoding="utf-8")

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog contract validation passed" in out


def test_backlog_contract_passes_with_parked_plan_section(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path)
    _parked_path, parked_plan_path = _add_parked_seed(tmp_path)
    plan_index = tmp_path / "odylith" / "technical-plans" / "INDEX.md"
    plan_index.write_text(
        plan_index.read_text(encoding="utf-8")
        + (
            "\n\n## Parked Plans\n\n"
            "| Plan | Status | Created | Updated | Backlog |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"| `odylith/technical-plans/parked/2026-02/{parked_plan_path.name}` | Parked | 2026-02-27 | 2026-02-28 | `B-103` |\n"
        ),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog contract validation passed" in out
    assert "- parked ideas: 1" in out


def test_backlog_contract_fails_when_parked_plan_section_missing(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path)
    _add_parked_seed(tmp_path)

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "missing section `## Parked Plans`" in out


def test_backlog_contract_fails_when_founder_override_has_no_review_date(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _, queued_path = _seed_minimal_repo(tmp_path)
    text = queued_path.read_text(encoding="utf-8")
    text = text.replace("founder_override: no", "founder_override: yes")
    queued_path.write_text(text, encoding="utf-8")
    backlog_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_text = backlog_index.read_text(encoding="utf-8").replace(
        "- ranking basis: No manual priority override; score-based rank.",
        "- ranking basis: manual priority override applied.",
    )
    backlog_index.write_text(backlog_text, encoding="utf-8")

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "review checkpoint date" in out


def test_backlog_contract_fails_when_active_rationale_heading_rank_mismatch(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_minimal_repo(tmp_path)
    backlog_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    text = backlog_index.read_text(encoding="utf-8")
    backlog_index.write_text(
        text.replace("### B-101 (rank 1)", "### B-101 (rank 2)"),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "must be exactly `### B-101 (rank 1)`" in out


def test_backlog_contract_fails_when_execution_rows_not_score_sorted(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, _ = _seed_minimal_repo(tmp_path)

    idea_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-02"
    second_exec_idea = idea_dir / "2026-02-24-second-promoted.md"
    second_exec_idea.write_text(
        _idea_text(
            idea_id="B-103",
            title="Second Promoted Work",
            date="2026-02-24",
            status="implementation",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=4,
            sizing="L",
            complexity="High",
            ordering_score=80,
            founder_override="no",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-02-24-second-promoted.md",
        ),
        encoding="utf-8",
    )

    second_plan = tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-02-24-second-promoted.md"
    second_plan.write_text("Status: In progress\n", encoding="utf-8")

    backlog_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    text = backlog_index.read_text(encoding="utf-8")
    insertion = (
        f"| - | B-103 | Second Promoted Work | P1 | 80 | 4 | 4 | 4 | L | High | implementation | [promoted-2]({_repo_rel(tmp_path, second_exec_idea)}) |\n"
        f"| - | B-102 | Promoted Work | P1 | 95 | 4 | 4 | 4 | L | High | implementation | [promoted]({_repo_rel(tmp_path, implementation_path)}) |"
    )
    text = text.replace(
        f"| - | B-102 | Promoted Work | P1 | 95 | 4 | 4 | 4 | L | High | implementation | [promoted]({_repo_rel(tmp_path, implementation_path)}) |",
        insertion,
    )
    backlog_index.write_text(text, encoding="utf-8")

    plan_index = tmp_path / "odylith" / "technical-plans" / "INDEX.md"
    plan_text = plan_index.read_text(encoding="utf-8")
    plan_text += (
        "| `odylith/technical-plans/in-progress/2026-02-24-second-promoted.md` | In progress | 2026-02-24 | 2026-02-24 | `B-103` |\n"
    )
    plan_index.write_text(plan_text, encoding="utf-8")

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "execution ranking score inversion" in out


def test_backlog_contract_fails_when_execution_status_priority_is_violated(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, _ = _seed_minimal_repo(tmp_path)

    idea_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-02"
    planning_idea = idea_dir / "2026-02-24-planning-promoted.md"
    planning_idea.write_text(
        _idea_text(
            idea_id="B-103",
            title="Planning Promoted Work",
            date="2026-02-24",
            status="planning",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=4,
            sizing="L",
            complexity="High",
            ordering_score=100,
            founder_override="no",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-02-24-planning-promoted.md",
        ),
        encoding="utf-8",
    )

    planning_plan = tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-02-24-planning-promoted.md"
    planning_plan.write_text("Status: In progress\n", encoding="utf-8")

    backlog_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    text = backlog_index.read_text(encoding="utf-8")
    insertion = (
        f"| - | B-103 | Planning Promoted Work | P1 | 100 | 4 | 4 | 4 | L | High | planning | [planning]({_repo_rel(tmp_path, planning_idea)}) |\n"
        f"| - | B-102 | Promoted Work | P1 | 95 | 4 | 4 | 4 | L | High | implementation | [promoted]({_repo_rel(tmp_path, implementation_path)}) |"
    )
    text = text.replace(
        f"| - | B-102 | Promoted Work | P1 | 95 | 4 | 4 | 4 | L | High | implementation | [promoted]({_repo_rel(tmp_path, implementation_path)}) |",
        insertion,
    )
    backlog_index.write_text(text, encoding="utf-8")

    plan_index = tmp_path / "odylith" / "technical-plans" / "INDEX.md"
    plan_text = plan_index.read_text(encoding="utf-8")
    plan_text += (
        "| `odylith/technical-plans/in-progress/2026-02-24-planning-promoted.md` | In progress | 2026-02-24 | 2026-02-24 | `B-103` |\n"
    )
    plan_index.write_text(plan_text, encoding="utf-8")

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "execution ordering violation" in out


def test_backlog_contract_allows_execution_ordering_override_with_founder_override(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, _ = _seed_minimal_repo(tmp_path)

    idea_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-02"
    planning_idea = idea_dir / "2026-02-24-planning-promoted.md"
    planning_idea.write_text(
        _idea_text(
            idea_id="B-103",
            title="Planning Promoted Work",
            date="2026-02-24",
            status="planning",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=4,
            sizing="L",
            complexity="High",
            ordering_score=100,
            founder_override="yes",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-02-24-planning-promoted.md",
        ),
        encoding="utf-8",
    )
    planning_plan = tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-02-24-planning-promoted.md"
    planning_plan.write_text("Status: In progress\n", encoding="utf-8")

    backlog_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    text = backlog_index.read_text(encoding="utf-8")
    insertion = (
        f"| - | B-103 | Planning Promoted Work | P1 | 100 | 4 | 4 | 4 | L | High | planning | [planning]({_repo_rel(tmp_path, planning_idea)}) |\n"
        f"| - | B-102 | Promoted Work | P1 | 95 | 4 | 4 | 4 | L | High | implementation | [promoted]({_repo_rel(tmp_path, implementation_path)}) |"
    )
    text = text.replace(
        f"| - | B-102 | Promoted Work | P1 | 95 | 4 | 4 | 4 | L | High | implementation | [promoted]({_repo_rel(tmp_path, implementation_path)}) |",
        insertion,
    )
    text += (
        "\n### B-103 (rank -)\n"
        "- why now: founder priority.\n"
        "- expected outcome: immediate.\n"
        "- tradeoff: accepted.\n"
        "- deferred for now: none.\n"
        "- ranking basis: Manual priority override for execution sequencing; review checkpoint 2026-03-15.\n"
    )
    backlog_index.write_text(text, encoding="utf-8")

    plan_index = tmp_path / "odylith" / "technical-plans" / "INDEX.md"
    plan_text = plan_index.read_text(encoding="utf-8")
    plan_text += (
        "| `odylith/technical-plans/in-progress/2026-02-24-planning-promoted.md` | In progress | 2026-02-24 | 2026-02-24 | `B-103` |\n"
    )
    plan_index.write_text(plan_text, encoding="utf-8")

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog contract validation passed" in out


def test_backlog_contract_fails_when_lineage_single_field_has_multiple_ids(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, _ = _seed_minimal_repo(tmp_path)
    text = implementation_path.read_text(encoding="utf-8")
    implementation_path.write_text(
        text.replace(
            "workstream_reopens: \n\n",
            "workstream_reopens: B-101,B-999\n\n",
        ),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "`workstream_reopens` expects a single B-id" in out


def test_backlog_contract_fails_when_lineage_target_missing(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, _ = _seed_minimal_repo(tmp_path)
    text = implementation_path.read_text(encoding="utf-8")
    implementation_path.write_text(
        text.replace(
            "workstream_split_from: \n\n",
            "workstream_split_from: B-999\n\n",
        ),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "`workstream_split_from` references missing workstream `B-999`" in out


def test_backlog_contract_fails_when_reopen_reciprocal_link_missing(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, _queued_path = _seed_minimal_repo(tmp_path)
    text = implementation_path.read_text(encoding="utf-8")
    implementation_path.write_text(
        text.replace(
            "workstream_reopens: \n\n",
            "workstream_reopens: B-101\n\n",
        ),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "missing reciprocal `workstream_reopened_by: B-102`" in out


def test_backlog_contract_fails_when_child_parent_is_not_listed_by_parent(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, _queued_path = _seed_minimal_repo(tmp_path)
    implementation_path.write_text(
        _idea_text(
            idea_id="B-102",
            title="Promoted Work",
            date="2026-02-23",
            status="implementation",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=4,
            sizing="L",
            complexity="High",
            ordering_score=95,
            founder_override="no",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-02-23-promoted.md",
            workstream_type="child",
            workstream_parent="B-101",
        ),
        encoding="utf-8",
    )

    rc = gate.main(
        [
            "--repo-root",
            str(tmp_path),
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--backlog-index",
            "odylith/radar/source/INDEX.md",
            "--plan-index",
            "odylith/technical-plans/INDEX.md",
        ]
    )
    assert rc == 2
    assert "missing reciprocal `workstream_children` entry `B-102`" in capsys.readouterr().out


def test_backlog_contract_fails_when_parent_lists_child_with_mismatched_parent(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, queued_path = _seed_minimal_repo(tmp_path)
    queued_path.write_text(
        _idea_text(
            idea_id="B-101",
            title="Backlog Bootstrap",
            date="2026-02-27",
            status="queued",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=3,
            sizing="L",
            complexity="High",
            ordering_score=89,
            founder_override="no",
            promoted_to_plan="",
            workstream_children="B-102",
        ),
        encoding="utf-8",
    )
    implementation_path.write_text(
        _idea_text(
            idea_id="B-102",
            title="Promoted Work",
            date="2026-02-23",
            status="implementation",
            priority="P1",
            commercial_value=4,
            product_impact=4,
            market_value=4,
            sizing="L",
            complexity="High",
            ordering_score=95,
            founder_override="no",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-02-23-promoted.md",
            workstream_type="child",
            workstream_parent="B-999",
        ),
        encoding="utf-8",
    )

    rc = gate.main(
        [
            "--repo-root",
            str(tmp_path),
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--backlog-index",
            "odylith/radar/source/INDEX.md",
            "--plan-index",
            "odylith/technical-plans/INDEX.md",
        ]
    )
    assert rc == 2
    out = capsys.readouterr().out
    assert "`workstream_parent` references missing workstream `B-999`" in out
    assert "`workstream_parent` must be `B-101` to match `B-101.workstream_children`" in out


def test_backlog_contract_fails_when_lineage_cycle_detected(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    implementation_path, queued_path = _seed_minimal_repo(tmp_path)
    queued_text = queued_path.read_text(encoding="utf-8")
    queued_path.write_text(
        queued_text.replace(
            "workstream_reopens: \n\n",
            "workstream_reopens: B-102\n\n",
        ),
        encoding="utf-8",
    )
    implementation_text = implementation_path.read_text(encoding="utf-8")
    implementation_path.write_text(
        implementation_text.replace(
            "workstream_reopens: \n\n",
            "workstream_reopens: B-101\n\n",
        ),
        encoding="utf-8",
    )

    rc = gate.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "lineage cycle detected" in out

"""Missing active-plan rows require an explicit, safe reciprocal binding."""

from pathlib import Path

import pytest

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import reconcile_plan_workstream_binding as reconcile
from odylith.runtime.governance import validate_backlog_contract as backlog
from odylith.runtime.governance import validate_plan_workstream_binding as binding
from test_reconcile_plan_workstream_binding import _idea_text, _write_backlog_index, _write_plan_index


PLAN = "odylith/technical-plans/in-progress/2026-09/2026-09-09-assessment.md"
INDEX = "odylith/technical-plans/INDEX.md"
RADAR = "odylith/radar/source/INDEX.md"
IDEAS = "odylith/radar/source/ideas/2026-09"
IDEA = f"{IDEAS}/2026-09-09-assessment.md"
METADATA = "Status: In progress\nCreated: 2026-07-20\nUpdated: 2026-09-09\nBacklog: B-202\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _write_plan_index(
        tmp_path, backlog_id="B-201",
        plan_rel="odylith/technical-plans/in-progress/2026-03-03-existing.md",
    )
    plan = tmp_path / PLAN
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(METADATA + "\n## Goal\nQualify the published predecessor.\n", encoding="utf-8")
    idea = tmp_path / IDEA
    idea.parent.mkdir(parents=True, exist_ok=True)
    idea.write_text(_idea_text(
        idea_id="B-202", title="Compatibility assessment", date="2026-09-09",
        status="implementation", promoted_to_plan=PLAN,
    ), encoding="utf-8")
    _write_backlog_index(
        tmp_path, section="execution",
        row="| - | B-202 | Compatibility assessment | P1 | 100 | 4 | 4 | 4 | M | Medium | implementation | [idea](ideas/2026-09/2026-09-09-assessment.md) |",
    )
    assert backlog._validate_idea_specs(tmp_path / IDEAS)[1] == []
    return tmp_path


def _run(repo: Path, *, plans: tuple[str, ...] = (PLAN,)):
    return reconcile.reconcile_plan_workstream_binding(
        repo_root=repo, plan_index_path=repo / INDEX, backlog_index_path=repo / RADAR,
        ideas_root=repo / IDEAS, stream_path=repo / ".odylith/runtime/test-stream.jsonl",
        changed_paths=plans, author="fixture", source="fixture",
    )


def _authored_state(repo: Path) -> dict[str, tuple[bytes, int]]:
    return {
        name: ((repo / name).read_bytes(), (repo / name).stat().st_mode)
        for name in (INDEX, PLAN, RADAR, IDEA)
    }


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("populated", [True, False])
def test_registers_exact_authored_row_preserving_other_bytes_and_mode(
    repo: Path, newline: str, populated: bool,
) -> None:
    index = repo / INDEX
    content = index.read_text(encoding="utf-8")
    if not populated:
        content = "\n".join(line for line in content.split("\n") if "`B-201`" not in line)
    content += "\nAn authored note remains here.\n\n## Completed\n\nHistorical text.\n"
    index.write_bytes(content.replace("\n", newline).encode("utf-8"))
    index.chmod(0o640)
    before = _authored_state(repo)

    decisions, successors = _run(repo)

    expected = f"| `{PLAN}` | In progress | 2026-07-20 | 2026-09-09 | `B-202` |{newline}".encode()
    after = _authored_state(repo)
    assert after[INDEX][0].count(expected) == 1
    assert after[INDEX][0].replace(expected, b"", 1) == before[INDEX][0]
    assert after[INDEX][1] == before[INDEX][1]
    for name in (PLAN, RADAR, IDEA):
        assert after[name] == before[name]
    assert len(decisions) == 1 and successors == []
    assert decisions[0].action == "registered_active_plan_row"
    assert decisions[0].backlog_before == decisions[0].backlog_after == "B-202"
    assert governance.parse_plan_active_rows(index)[-1] == {
        "Plan": PLAN, "Status": "In progress", "Created": "2026-07-20",
        "Updated": "2026-09-09", "Backlog": "B-202",
    }
    assert binding.validate_plan_workstream_binding(
        repo_root=repo, plan_index_path=index, ideas_root=repo / IDEAS, changed_paths=(PLAN,),
    ) == []
    assert _run(repo) == ([], [])
    assert index.read_bytes() == after[INDEX][0]
    assert index.stat().st_mode == after[INDEX][1]


@pytest.mark.parametrize("metadata", [
    METADATA.replace("Status: In progress\n", ""),
    METADATA.replace("Created: 2026-07-20\n", ""),
    METADATA.replace("Updated: 2026-09-09\n", ""),
    METADATA.replace("Backlog: B-202\n", ""),
    METADATA.replace("In progress", "Done"),
    METADATA.replace("In progress", "Parked"),
    METADATA.replace("2026-07-20", "2026-02-30"),
    METADATA.replace("2026-09-09", "20260909"),
    METADATA.replace("2026-09-09", "2026-07-19"),
    METADATA.replace("B-202", "B-202,B-201"),
    METADATA.replace("B-202", "B-999"),
    METADATA + "Backlog: B-201\n",
    METADATA + "Status: In progress\n",
])
def test_rejects_missing_invalid_or_duplicate_authored_metadata(repo: Path, metadata: str) -> None:
    (repo / PLAN).write_text(metadata + "\n## Goal\nRetain authored intent.\n", encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError):
        _run(repo)

    assert _authored_state(repo) == before


@pytest.mark.parametrize(("old", "new"), [
    ("status: implementation", "status: queued"),
    ("status: implementation", "status: finished"),
    ("status: implementation", "status: parked"),
    (f"promoted_to_plan: {PLAN}", "promoted_to_plan: odylith/technical-plans/done/old.md"),
])
def test_requires_already_active_exact_reciprocal_workstream(repo: Path, old: str, new: str) -> None:
    idea = repo / IDEA
    idea.write_text(idea.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError):
        _run(repo)

    assert _authored_state(repo) == before
    assert list((repo / IDEAS).glob("*.md")) == [idea]


@pytest.mark.parametrize(("old", "new"), [
    ("## Active Plans", "## Missing Active Plans"),
    ("## Active Plans", "## Active Plans\n\n## Active Plans"),
    ("| Created | Updated |", "| Created | Unknown |"),
    ("| --- | --- | --- | --- | --- |", ""),
    ("| `B-201` |", "| `B-201` | extra |"),
    ("| `B-201` |", "| `B-202` |"),
    ("| `B-201` |", "| `B-201` |\n\n| forged | In progress | 2026-01-01 | 2026-01-01 | `B-203` |"),
])
def test_rejects_malformed_or_conflicting_index_without_rebuilding_it(
    repo: Path, old: str, new: str,
) -> None:
    index = repo / INDEX
    index.write_text(index.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError):
        _run(repo)

    assert _authored_state(repo) == before


@pytest.mark.parametrize("outside_active", [True, False])
def test_registration_rejects_symlink_identity(repo: Path, outside_active: bool) -> None:
    plan = repo / PLAN
    target = repo / "outside.md" if outside_active else plan.parent / "other.md"
    plan.rename(target)
    plan.symlink_to(target)
    before = _authored_state(repo)

    with pytest.raises(ValueError, match="regular file inside the active-plan tree"):
        reconcile._prepare_active_plan_registration(
            repo_root=repo, plan_index_path=repo / INDEX, plan_paths=(PLAN,),
            ideas=backlog._validate_idea_specs(repo / IDEAS)[0],
        )

    assert _authored_state(repo) == before


def test_deleted_unindexed_plan_does_not_request_registration(repo: Path) -> None:
    (repo / PLAN).unlink()
    before = (repo / INDEX).read_bytes()

    assert _run(repo) == ([], [])

    assert (repo / INDEX).read_bytes() == before


def test_registration_rejects_index_target_outside_repo(repo: Path) -> None:
    outside_index = repo.parent / f"{repo.name}-outside-index.md"
    before = (repo / INDEX).read_bytes()
    outside_index.write_bytes(before)

    with pytest.raises(ValueError, match="index outside the repository"):
        reconcile._prepare_active_plan_registration(
            repo_root=repo, plan_index_path=outside_index, plan_paths=(PLAN,),
            ideas=backlog._validate_idea_specs(repo / IDEAS)[0],
        )

    assert outside_index.read_bytes() == before
    assert (repo / INDEX).read_bytes() == before


@pytest.mark.parametrize(("key", "valid", "conflicting"), [
    ("promoted_to_plan", PLAN, "odylith/technical-plans/in-progress/other.md"),
    ("status", "implementation", "finished"),
    ("idea_id", "B-202", "B-299"),
])
def test_duplicate_relevant_workstream_metadata_is_not_last_value_wins(
    repo: Path, key: str, valid: str, conflicting: str,
) -> None:
    idea = repo / IDEA
    idea.write_text(idea.read_text(encoding="utf-8").replace(
        f"{key}: {valid}", f"{key}: {conflicting}\n{key}: {valid}",
    ), encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError, match="duplicate metadata key"):
        _run(repo)

    assert _authored_state(repo) == before


@pytest.mark.parametrize("delimiter", ["|", "\n", "\r", "`"])
def test_table_delimiter_in_plan_path_is_rejected_without_index_write(repo: Path, delimiter: str) -> None:
    path = PLAN.replace("assessment.md", f"assessment{delimiter}alternate.md")
    (repo / PLAN).rename(repo / path)
    idea = repo / IDEA
    idea.write_text(idea.read_text(encoding="utf-8").replace(PLAN, path), encoding="utf-8")
    index_before = (repo / INDEX).read_bytes()

    with pytest.raises(ValueError, match="unsafe table delimiters"):
        _run(repo, plans=(path,))

    assert (repo / INDEX).read_bytes() == index_before


@pytest.mark.parametrize("later_status", ["Done", "In progress"])
def test_missing_registration_batch_is_validated_before_one_index_write(repo: Path, later_status: str) -> None:
    later = PLAN.replace("assessment.md", "z-later.md")
    (repo / later).write_text(
        METADATA.replace("B-202", "B-203").replace("In progress", later_status), encoding="utf-8",
    )
    later_idea = repo / IDEAS / "2026-09-09-later.md"
    later_idea.write_text(_idea_text(
        idea_id="B-203", title="Later assessment", date="2026-09-09",
        status="implementation", promoted_to_plan=later,
    ), encoding="utf-8")
    radar = repo / RADAR
    content = radar.read_text(encoding="utf-8")
    first_row = next(line for line in content.splitlines() if "| B-202 |" in line)
    later_row = first_row.replace("B-202", "B-203").replace("2026-09-09-assessment.md", "2026-09-09-later.md")
    radar.write_text(content.replace(first_row, first_row + "\n" + later_row), encoding="utf-8")
    before = _authored_state(repo)

    if later_status == "Done":
        with pytest.raises(ValueError, match="Status: In progress"):
            _run(repo, plans=(PLAN, later))
        assert _authored_state(repo) == before
    else:
        decisions, successors = _run(repo, plans=(PLAN, later))
        assert [row.plan_path for row in decisions] == [PLAN, later]
        assert successors == []
        assert [row["Backlog"] for row in governance.parse_plan_active_rows(repo / INDEX)] == ["B-201", "B-202", "B-203"]
        for name in (PLAN, RADAR, IDEA):
            assert _authored_state(repo)[name] == before[name]


@pytest.mark.parametrize("hardlink", [False, True])
def test_in_repo_index_alias_is_rejected(repo: Path, hardlink: bool) -> None:
    index = repo / INDEX
    target = index.with_name("unrelated-index.md")
    if hardlink:
        target.hardlink_to(index)
    else:
        index.rename(target)
        index.symlink_to(target)
    before = target.read_bytes()

    with pytest.raises(ValueError, match="index alias"):
        _run(repo)

    assert target.read_bytes() == before


def test_index_parent_symlink_is_rejected(repo: Path) -> None:
    alias = repo / "index-alias"
    alias.symlink_to((repo / INDEX).parent, target_is_directory=True)
    before = (repo / INDEX).read_bytes()

    with pytest.raises(ValueError, match="index alias"):
        reconcile._prepare_active_plan_registration(
            repo_root=repo, plan_index_path=alias / "INDEX.md", plan_paths=(PLAN,),
            ideas=backlog._validate_idea_specs(repo / IDEAS)[0],
        )

    assert (repo / INDEX).read_bytes() == before


def test_cli_does_not_resolve_away_index_alias_before_registration(repo: Path) -> None:
    index = repo / INDEX
    target = index.with_name("unrelated-index.md")
    index.rename(target)
    index.symlink_to(target)
    before = target.read_bytes()

    assert reconcile.main(["--repo-root", str(repo), PLAN]) == 2

    assert target.read_bytes() == before


def _stale_execution_row(
    repo: Path, *, section: str = "finished", status: str = "implementation", newline: str = "\n", registered: bool = True,
) -> str:
    if registered:
        _run(repo)
    idea = repo / IDEA
    idea.write_text(idea.read_text(encoding="utf-8").replace("status: implementation", f"status: {status}"), encoding="utf-8")
    row = "| - | B-202 | Compatibility assessment | P1 | 100 | 4 | 4 | 4 | M | Medium | finished | [idea](ideas/2026-09/2026-09-09-assessment.md) |"
    index = _write_backlog_index(repo, section=section, row=row)
    content = index.read_text(encoding="utf-8") + "\n## Historical notes\n\nLeave this authored history alone.\n"
    index.write_bytes(content.replace("\n", newline).encode("utf-8"))
    index.chmod(0o640)
    return row


@pytest.mark.parametrize("section", ["finished", "execution"])
@pytest.mark.parametrize("status", ["planning", "implementation"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("registered", [True, False])
def test_reconciles_existing_active_idea_status_and_execution_placement(
    repo: Path, section: str, status: str, newline: str, registered: bool,
) -> None:
    old_row = _stale_execution_row(repo, section=section, status=status, newline=newline, registered=registered)
    before = _authored_state(repo)

    decisions, successors = _run(repo)

    assert successors == []
    assert [row.action for row in decisions] == (
        ([] if registered else ["registered_active_plan_row"]) + ["repair_execution_section_status"]
    )
    after = _authored_state(repo)
    new_row = old_row.replace("| finished |", f"| {status} |")
    assert after[RADAR][0].replace((new_row + newline).encode(), b"", 1) == before[RADAR][0].replace((old_row + newline).encode(), b"", 1)
    assert after[RADAR][1] == before[RADAR][1]
    for name in (PLAN, IDEA):
        assert after[name] == before[name]
    registration = b"" if registered else f"| `{PLAN}` | In progress | 2026-07-20 | 2026-09-09 | `B-202` |\n".encode()
    assert after[INDEX][0].replace(registration, b"", 1) == before[INDEX][0]
    assert after[INDEX][1] == before[INDEX][1]
    snapshot = backlog.load_backlog_index_snapshot(repo / RADAR)
    assert backlog.rows_as_mapping(section=snapshot["finished"]) == []
    rows = backlog.rows_as_mapping(section=snapshot["execution"])
    assert len(rows) == 1 and rows[0]["idea_id"] == "B-202" and rows[0]["status"] == status
    assert _run(repo) == ([], [])
    assert _authored_state(repo) == after


@pytest.mark.parametrize("damage", [
    "duplicate", "missing_target", "bad_header", "bad_separator", "duplicate_heading",
    "delimiter", "newline", "noncontiguous", "duplicate_across_sections",
])
def test_execution_relocation_rejects_ambiguous_or_malformed_tables(repo: Path, damage: str) -> None:
    row = _stale_execution_row(repo)
    index = repo / RADAR
    text = index.read_text(encoding="utf-8")
    heading = "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)"
    if damage == "duplicate":
        text = text.replace(row, row + "\n" + row)
    elif damage == "missing_target":
        text = text.replace(row, "")
    elif damage == "bad_header":
        text = text.replace("| status | link |", "| invalid | link |")
    elif damage == "bad_separator":
        text = text.replace("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |", "")
    elif damage == "duplicate_heading":
        text = text.replace(heading, heading + "\n\n" + heading)
    elif damage in {"delimiter", "newline"}:
        text = text.replace("Compatibility assessment", "Compatibility|assessment" if damage == "delimiter" else "Compatibility\nassessment")
    elif damage == "noncontiguous":
        text = text.replace(row, "An interleaved note.\n" + row)
    else:
        separator = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        text = text.replace(separator, separator + "\n" + row, 1)
    index.write_text(text, encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError):
        _run(repo)

    assert _authored_state(repo) == before


@pytest.mark.parametrize("hardlink", [False, True])
def test_execution_relocation_rejects_radar_index_aliases(repo: Path, hardlink: bool) -> None:
    _stale_execution_row(repo)
    index = repo / RADAR
    target = index.with_name("unrelated-index.md")
    if hardlink:
        target.hardlink_to(index)
    else:
        index.rename(target)
        index.symlink_to(target)
    before = _authored_state(repo)

    with pytest.raises(ValueError, match="alias"):
        _run(repo)

    assert _authored_state(repo) == before


def test_execution_relocation_requires_unambiguous_reciprocal_active_idea(repo: Path) -> None:
    _stale_execution_row(repo)
    idea = repo / IDEA
    idea.write_text(idea.read_text(encoding="utf-8").replace(
        f"promoted_to_plan: {PLAN}", f"promoted_to_plan: other.md\npromoted_to_plan: {PLAN}",
    ), encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError, match="duplicate metadata"):
        _run(repo)

    assert _authored_state(repo) == before


def test_execution_relocation_does_not_reinterpret_a_nonreciprocal_active_idea(repo: Path) -> None:
    _stale_execution_row(repo)
    idea = repo / IDEA
    idea.write_text(idea.read_text(encoding="utf-8").replace(f"promoted_to_plan: {PLAN}", "promoted_to_plan: other.md"), encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError, match="reciprocal"):
        _run(repo)

    assert _authored_state(repo) == before


def test_execution_relocation_preserves_siblings_and_existing_order(repo: Path) -> None:
    old_row = _stale_execution_row(repo)
    index = repo / RADAR
    siblings = [
        "| - | B-200 |  Earlier work  | P1 | 150 | 4 | 4 | 4 | M | Medium | implementation | [old](other.md) |",
        "| - | B-300 |  Later work  | P1 | 90 | 4 | 4 | 4 | M | Medium | implementation | [new](another.md) |",
    ]
    snapshot = backlog.load_backlog_index_snapshot(index)
    lines = index.read_text(encoding="utf-8").splitlines(keepends=True)
    start, _end = reconcile._find_section_bounds(lines, "## " + snapshot["execution"]["section_title"])
    lines[start + 4:start + 4] = [row + "\n" for row in siblings]
    index.write_text("".join(lines), encoding="utf-8")
    before = index.read_bytes()

    assert len(_run(repo)[0]) == 1

    after = index.read_bytes()
    new_row = old_row.replace("| finished |", "| implementation |")
    assert before.replace((old_row + "\n").encode(), b"") == after.replace((new_row + "\n").encode(), b"")
    rows = backlog.rows_as_mapping(section=backlog.load_backlog_index_snapshot(index)["execution"])
    assert [row["idea_id"] for row in rows] == ["B-200", "B-202", "B-300"]
    assert _run(repo) == ([], []) and index.read_bytes() == after


def test_execution_relocation_prevalidates_later_active_binding_before_any_write(repo: Path) -> None:
    _stale_execution_row(repo)
    second_plan = PLAN.replace("assessment.md", "second.md")
    (repo / second_plan).write_text(METADATA.replace("B-202", "B-203"), encoding="utf-8")
    second_idea = repo / IDEAS / "2026-09-09-second.md"
    second_idea.write_text(_idea_text(
        idea_id="B-203", title="Separate authored assessment", date="2026-09-09",
        status="implementation", promoted_to_plan="other.md",
    ), encoding="utf-8")
    index = repo / INDEX
    index.write_text(index.read_text(encoding="utf-8") +
                     f"| `{second_plan}` | In progress | 2026-07-20 | 2026-09-09 | `B-203` |\n", encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError, match="reciprocal"):
        _run(repo, plans=(PLAN, second_plan))

    assert _authored_state(repo) == before


def test_execution_relocation_cli_does_not_resolve_away_radar_alias(repo: Path) -> None:
    _stale_execution_row(repo)
    index = repo / RADAR
    target = index.with_name("unrelated-index.md")
    index.rename(target)
    index.symlink_to(target)
    before = _authored_state(repo)

    assert reconcile.main(["--repo-root", str(repo), PLAN]) == 2

    assert _authored_state(repo) == before


def test_correct_execution_status_does_not_normalize_unrelated_rank(repo: Path) -> None:
    _run(repo)
    index = repo / RADAR
    index.write_text(index.read_text(encoding="utf-8").replace("| - | B-202 |", "| 2 | B-202 |"), encoding="utf-8")
    before = _authored_state(repo)

    assert _run(repo) == ([], [])

    assert _authored_state(repo) == before


@pytest.mark.parametrize("duplicate_plan", [False, True])
def test_execution_relocation_requires_unique_indexed_plan_binding(repo: Path, duplicate_plan: bool) -> None:
    _stale_execution_row(repo)
    index = repo / INDEX
    content = index.read_text(encoding="utf-8")
    row = next(line for line in content.splitlines() if f"`{PLAN}`" in line)
    index.write_text(content + (row if duplicate_plan else row.replace(PLAN, PLAN + ".other")) + "\n", encoding="utf-8")
    before = _authored_state(repo)

    with pytest.raises(ValueError, match="unique indexed"):
        _run(repo)

    assert _authored_state(repo) == before


@pytest.mark.parametrize("section", ["finished", "execution"])
def test_cli_registration_converges_radar_without_a_second_repair(repo: Path, section: str, capsys) -> None:
    _stale_execution_row(repo, section=section, registered=False)

    assert reconcile.main(["--repo-root", str(repo), PLAN]) == 0

    assert "decisions: 2" in capsys.readouterr().out
    snapshot = backlog.load_backlog_index_snapshot(repo / RADAR)
    assert backlog.rows_as_mapping(section=snapshot["finished"]) == []
    assert [(row["idea_id"], row["status"]) for row in backlog.rows_as_mapping(section=snapshot["execution"])] == [
        ("B-202", "implementation"),
    ]
    before = _authored_state(repo)
    assert reconcile.main(["--repo-root", str(repo), PLAN]) == 0
    assert "decisions: 0" in capsys.readouterr().out
    assert _authored_state(repo) == before


@pytest.mark.parametrize("registration", [True, False])
@pytest.mark.parametrize("damage", ["separator", "symlink", "hardlink", "missing_row"])
def test_cli_preflights_radar_before_registration_or_queued_idea_write(repo: Path, registration: bool, damage: str) -> None:
    row = _stale_execution_row(repo, registered=not registration)
    if not registration:
        idea = repo / IDEA
        idea.write_text(idea.read_text(encoding="utf-8").replace("status: implementation", "status: queued"), encoding="utf-8")
        row = row.replace("| - |", "| 1 |", 1).replace("| finished |", "| queued |")
        _write_backlog_index(repo, section="active", row=row)
    index = repo / RADAR
    if damage == "separator":
        index.write_text(index.read_text(encoding="utf-8").replace("| --- |", "| invalid |", 1), encoding="utf-8")
    elif damage == "missing_row":
        index.write_text(index.read_text(encoding="utf-8").replace(row, ""), encoding="utf-8")
    else:
        target = index.with_name("unrelated-index.md")
        if damage == "hardlink":
            target.hardlink_to(index)
        else:
            index.rename(target)
            index.symlink_to(target)
    before = _authored_state(repo)

    assert reconcile.main(["--repo-root", str(repo), PLAN]) == 2

    assert _authored_state(repo) == before


def test_registration_and_later_queued_transition_share_one_preflight(repo: Path) -> None:
    _stale_execution_row(repo, registered=False)
    later = PLAN.replace("assessment.md", "z-queued.md")
    (repo / later).write_text(METADATA.replace("B-202", "B-203"), encoding="utf-8")
    later_idea = repo / IDEAS / "2026-09-09-queued.md"
    later_idea.write_text(_idea_text(
        idea_id="B-203", title="Separate queued assessment", date="2026-09-09",
        status="queued", promoted_to_plan="",
    ), encoding="utf-8")
    index = repo / INDEX
    index.write_text(index.read_text(encoding="utf-8") +
                     f"| `{later}` | In progress | 2026-07-20 | 2026-09-09 | `B-203` |\n", encoding="utf-8")
    radar = repo / RADAR
    content = radar.read_text(encoding="utf-8")
    separator = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    queued = "| 1 | B-203 | Separate queued assessment | P1 | invalid | 4 | 4 | 4 | M | Medium | queued | [idea](ideas/2026-09/2026-09-09-queued.md) |"
    radar.write_text(content.replace(separator, separator + "\n" + queued, 1), encoding="utf-8")
    before = _authored_state(repo)
    later_before = later_idea.read_bytes()

    assert reconcile.main(["--repo-root", str(repo), PLAN, later]) == 2

    assert _authored_state(repo) == before
    assert later_idea.read_bytes() == later_before

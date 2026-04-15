from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import reconcile_plan_workstream_binding as reconcile
from odylith.runtime.governance import validate_backlog_contract


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


def _seed_component_registry(root: Path, *, feature_history_workstream: str = "B-201") -> None:
    spec_dir = root / "odylith" / "registry" / "source" / "components" / "governance-engine"
    spec_dir.mkdir(parents=True, exist_ok=True)
    plan_page = root / "odylith" / "radar" / "radar.html"
    plan_page.parent.mkdir(parents=True, exist_ok=True)
    plan_page.write_text(f"<html><body>{feature_history_workstream}</body></html>\n", encoding="utf-8")
    (spec_dir / "CURRENT_SPEC.md").write_text(
        (
            "Last updated: 2026-03-04\n\n"
            "## Feature History\n"
            "- 2026-03-04: Seed fixture. "
            f"(Plan: [{feature_history_workstream}](odylith/radar/radar.html?view=plan&workstream={feature_history_workstream}))\n"
        ),
        encoding="utf-8",
    )
    contracts_dir = root / "odylith" / "registry" / "source"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    (contracts_dir / "component_registry.v1.json").write_text(
        (
            "{\n"
            "  \"version\": \"v1\",\n"
            "  \"components\": [\n"
            "    {\n"
            "      \"component_id\": \"governance-engine\",\n"
            "      \"name\": \"Governance Engine\",\n"
            "      \"kind\": \"system\",\n"
            "      \"category\": \"governance_engine\",\n"
            "      \"qualification\": \"curated\",\n"
            "      \"aliases\": [\"governance\", \"plan-binding\"],\n"
            "      \"path_prefixes\": [\"src/odylith/runtime/governance/reconcile_plan_workstream_binding.py\", \"odylith/radar/source/INDEX.md\", \"odylith/technical-plans/\", \"odylith/radar/source/ideas/\"],\n"
            "      \"workstreams\": [\"B-201\", \"B-300\", \"B-301\"],\n"
            "      \"diagrams\": [],\n"
            "      \"owner\": \"platform\",\n"
            "      \"status\": \"active\",\n"
            "      \"what_it_is\": \"Governance reconciliation and successor-binding orchestration.\",\n"
            "      \"why_tracked\": \"Captures odylith/technical-plans/workstream lifecycle transitions under policy enforcement.\",\n"
            "      \"spec_ref\": \"odylith/registry/source/components/governance-engine/CURRENT_SPEC.md\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
        ),
        encoding="utf-8",
    )


def _idea_text(
    *,
    idea_id: str,
    title: str,
    date: str,
    status: str,
    promoted_to_plan: str,
) -> str:
    sections = "\n\n".join(
        f"## {section}\nGrounded fixture coverage for {section.lower()} in this synthetic workstream."
        for section in _SECTIONS
    )
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        f"date: {date}\n\n"
        "priority: P1\n\n"
        "commercial_value: 4\n\n"
        "product_impact: 4\n\n"
        "market_value: 4\n\n"
        "impacted_parts: governance\n\n"
        "sizing: M\n\n"
        "complexity: Medium\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: deterministic governance\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        "workstream_type: child\n\n"
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


def _write_plan_index(root: Path, *, backlog_id: str, plan_rel: str) -> Path:
    path = root / "odylith" / "technical-plans" / "INDEX.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "# Plan Index\n\n"
            "Last updated (UTC): 2026-03-03\n\n"
            "## Active Plans\n\n"
            "| Plan | Status | Created | Updated | Backlog |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"| `{plan_rel}` | In progress | 2026-03-03 | 2026-03-03 | `{backlog_id}` |\n"
        ),
        encoding="utf-8",
    )
    plan_path = root / plan_rel
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("Status: In progress\n", encoding="utf-8")
    return path


def _write_backlog_index(
    root: Path,
    *,
    row: str,
    section: str,
    execution_section_title: str = "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)",
) -> Path:
    active_row = row if section == "active" else ""
    execution_row = row if section == "execution" else ""
    finished_row = row if section == "finished" else ""
    path = root / "odylith" / "radar" / "source" / "INDEX.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-03-03\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"{active_row}\n\n"
            f"{execution_section_title}\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"{execution_row}\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"{finished_row}\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-201 (rank 1)\n"
            "- why now: seed.\n"
            "- expected outcome: governance.\n"
            "- tradeoff: low.\n"
            "- deferred for now: none.\n"
            "- ranking basis: No manual priority override; score-based rank.\n"
        ),
        encoding="utf-8",
    )
    return path


def test_reconcile_queued_binding_advances_to_planning_without_implementation_evidence(tmp_path: Path) -> None:
    _seed_component_registry(tmp_path)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_root.mkdir(parents=True, exist_ok=True)
    idea_path = ideas_root / "2026-03-03-governance-queue.md"
    idea_path.write_text(
        _idea_text(
            idea_id="B-201",
            title="Governance Queue",
            date="2026-03-03",
            status="queued",
            promoted_to_plan="",
        ),
        encoding="utf-8",
    )
    plan_rel = "odylith/technical-plans/in-progress/2026-03-03-governance-plan.md"
    plan_index_path = _write_plan_index(tmp_path, backlog_id="B-201", plan_rel=plan_rel)
    backlog_row = f"| 1 | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | queued | [idea]({_repo_rel(tmp_path, idea_path)}) |"
    backlog_index_path = _write_backlog_index(tmp_path, row=backlog_row, section="active")
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"

    decisions, successors = reconcile.reconcile_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index_path,
        backlog_index_path=backlog_index_path,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        stream_path=stream_path,
        changed_paths=(plan_rel,),
        author="test",
        source="test",
    )

    assert successors == []
    assert any(row.action == "queued_to_planning" for row in decisions)
    updated_idea = idea_path.read_text(encoding="utf-8")
    assert "status: planning" in updated_idea
    assert f"promoted_to_plan: {plan_rel}" in updated_idea
    backlog_text = backlog_index_path.read_text(encoding="utf-8")
    assert "| - | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | planning |" in backlog_text


def test_reconcile_queued_binding_advances_to_implementation_with_evidence(tmp_path: Path) -> None:
    _seed_component_registry(tmp_path)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_root.mkdir(parents=True, exist_ok=True)
    idea_path = ideas_root / "2026-03-03-governance-queue.md"
    idea_path.write_text(
        _idea_text(
            idea_id="B-201",
            title="Governance Queue",
            date="2026-03-03",
            status="queued",
            promoted_to_plan="",
        ),
        encoding="utf-8",
    )
    plan_rel = "odylith/technical-plans/in-progress/2026-03-03-governance-plan.md"
    plan_index_path = _write_plan_index(tmp_path, backlog_id="B-201", plan_rel=plan_rel)
    backlog_row = f"| 1 | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | queued | [idea]({_repo_rel(tmp_path, idea_path)}) |"
    backlog_index_path = _write_backlog_index(tmp_path, row=backlog_row, section="active")
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"

    decisions, _successors = reconcile.reconcile_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index_path,
        backlog_index_path=backlog_index_path,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        stream_path=stream_path,
        changed_paths=(plan_rel, "src/odylith/runtime/governance/agent_governance_intelligence.py"),
        author="test",
        source="test",
    )

    assert any(row.action == "queued_to_implementation" for row in decisions)
    updated_idea = idea_path.read_text(encoding="utf-8")
    assert "status: implementation" in updated_idea
    backlog_text = backlog_index_path.read_text(encoding="utf-8")
    assert "| - | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | implementation |" in backlog_text


def test_reconcile_repairs_existing_implementation_row_stranded_in_active_backlog(tmp_path: Path) -> None:
    _seed_component_registry(tmp_path)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_root.mkdir(parents=True, exist_ok=True)
    plan_rel = "odylith/technical-plans/in-progress/2026-03-03-governance-plan.md"
    idea_path = ideas_root / "2026-03-03-governance-queue.md"
    idea_path.write_text(
        _idea_text(
            idea_id="B-201",
            title="Governance Queue",
            date="2026-03-03",
            status="implementation",
            promoted_to_plan=plan_rel,
        ),
        encoding="utf-8",
    )
    plan_index_path = _write_plan_index(tmp_path, backlog_id="B-201", plan_rel=plan_rel)
    backlog_row = f"| 1 | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | queued | [idea]({_repo_rel(tmp_path, idea_path)}) |"
    backlog_index_path = _write_backlog_index(tmp_path, row=backlog_row, section="active")
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"

    decisions, _successors = reconcile.reconcile_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index_path,
        backlog_index_path=backlog_index_path,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        stream_path=stream_path,
        changed_paths=(plan_rel,),
        author="test",
        source="test",
    )

    assert any(row.action == "repair_execution_section_status" for row in decisions)
    backlog_text = backlog_index_path.read_text(encoding="utf-8")
    assert "| 1 | B-201 |" not in backlog_text
    assert "| - | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | implementation |" in backlog_text


def test_reconcile_repairs_existing_implementation_row_with_current_execution_heading(tmp_path: Path) -> None:
    _seed_component_registry(tmp_path)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_root.mkdir(parents=True, exist_ok=True)
    plan_rel = "odylith/technical-plans/in-progress/2026-03-03-governance-plan.md"
    idea_path = ideas_root / "2026-03-03-governance-queue.md"
    idea_path.write_text(
        _idea_text(
            idea_id="B-201",
            title="Governance Queue",
            date="2026-03-03",
            status="implementation",
            promoted_to_plan=plan_rel,
        ),
        encoding="utf-8",
    )
    plan_index_path = _write_plan_index(tmp_path, backlog_id="B-201", plan_rel=plan_rel)
    backlog_row = f"| 1 | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | queued | [idea]({_repo_rel(tmp_path, idea_path)}) |"
    backlog_index_path = _write_backlog_index(
        tmp_path,
        row=backlog_row,
        section="active",
        execution_section_title="## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress` or an active parent wave)",
    )
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"

    decisions, _successors = reconcile.reconcile_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index_path,
        backlog_index_path=backlog_index_path,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        stream_path=stream_path,
        changed_paths=(plan_rel,),
        author="test",
        source="test",
    )

    assert any(row.action == "repair_execution_section_status" for row in decisions)
    backlog_text = backlog_index_path.read_text(encoding="utf-8")
    assert "| - | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | implementation |" in backlog_text


def test_reconcile_repair_keeps_backlog_index_contract_valid(tmp_path: Path) -> None:
    _seed_component_registry(tmp_path)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_root.mkdir(parents=True, exist_ok=True)
    plan_rel = "odylith/technical-plans/in-progress/2026-03-03-governance-plan.md"

    implementation_idea = ideas_root / "2026-03-03-governance-queue.md"
    implementation_idea.write_text(
        _idea_text(
            idea_id="B-201",
            title="Governance Queue",
            date="2026-03-03",
            status="implementation",
            promoted_to_plan=plan_rel,
        ),
        encoding="utf-8",
    )
    queued_idea = ideas_root / "2026-03-03-next-up.md"
    queued_idea.write_text(
        _idea_text(
            idea_id="B-202",
            title="Next Up",
            date="2026-03-03",
            status="queued",
            promoted_to_plan="",
        ),
        encoding="utf-8",
    )
    existing_execution_idea = ideas_root / "2026-03-01-existing-implementation.md"
    existing_execution_idea.write_text(
        _idea_text(
            idea_id="B-300",
            title="Existing Execution",
            date="2026-03-01",
            status="implementation",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-01-existing-plan.md",
        ),
        encoding="utf-8",
    )

    plan_index_path = _write_plan_index(tmp_path, backlog_id="B-201", plan_rel=plan_rel)
    backlog_index_path = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_index_path.write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-03-03\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| 1 | B-202 | Next Up | P1 | 100 | 4 | 4 | 4 | M | Medium | queued | [idea]({_repo_rel(tmp_path, queued_idea)}) |\n"
            f"| 2 | B-201 | Governance Queue | P1 | 100 | 4 | 4 | 4 | M | Medium | queued | [idea]({_repo_rel(tmp_path, implementation_idea)}) |\n\n"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress` or an active parent wave)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| - | B-300 | Existing Execution | P1 | 100 | 4 | 4 | 4 | M | Medium | implementation | [idea]({_repo_rel(tmp_path, existing_execution_idea)}) |\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-202 (rank 1)\n"
            "- why now: seed.\n"
            "- expected outcome: governance.\n"
            "- tradeoff: low.\n"
            "- deferred for now: none.\n"
            "- ranking basis: No manual priority override; score-based rank.\n\n"
            "### B-201 (rank 2)\n"
            "- why now: seed.\n"
            "- expected outcome: governance.\n"
            "- tradeoff: low.\n"
            "- deferred for now: none.\n"
            "- ranking basis: No manual priority override; score-based rank.\n"
        ),
        encoding="utf-8",
    )
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"

    decisions, _successors = reconcile.reconcile_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index_path,
        backlog_index_path=backlog_index_path,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        stream_path=stream_path,
        changed_paths=(plan_rel,),
        author="test",
        source="test",
    )

    assert any(row.action == "repair_execution_section_status" for row in decisions)
    backlog_text = backlog_index_path.read_text(encoding="utf-8")
    assert "### B-202 (rank 1)" in backlog_text
    assert backlog_text.index("| - | B-201 | Governance Queue | P1 | 100 |") < backlog_text.index(
        "| - | B-300 | Existing Execution | P1 | 100 |"
    )

    ideas, errors = validate_backlog_contract._validate_idea_specs(ideas_root)
    assert errors == []
    *_unused, validate_errors = validate_backlog_contract._validate_backlog_index(
        backlog_index=backlog_index_path,
        ideas=ideas,
        repo_root=tmp_path,
    )
    assert validate_errors == []


def test_reconcile_finished_binding_creates_successor_and_rebinds_plan(tmp_path: Path) -> None:
    _seed_component_registry(tmp_path, feature_history_workstream="B-300")
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_root.mkdir(parents=True, exist_ok=True)
    done_plan_rel = "odylith/technical-plans/done/2026-03/2026-03-01-complete.md"
    done_plan_path = tmp_path / done_plan_rel
    done_plan_path.parent.mkdir(parents=True, exist_ok=True)
    done_plan_path.write_text("Status: Done\n", encoding="utf-8")

    finished_idea = ideas_root / "2026-03-01-finished-governance.md"
    finished_idea.write_text(
        _idea_text(
            idea_id="B-300",
            title="Finished Governance",
            date="2026-03-01",
            status="finished",
            promoted_to_plan=done_plan_rel,
        ),
        encoding="utf-8",
    )
    plan_rel = "odylith/technical-plans/in-progress/2026-03-03-successor-plan.md"
    plan_index_path = _write_plan_index(tmp_path, backlog_id="B-300", plan_rel=plan_rel)
    backlog_row = f"| - | B-300 | Finished Governance | P1 | 100 | 4 | 4 | 4 | M | Medium | finished | [idea]({_repo_rel(tmp_path, finished_idea)}) |"
    backlog_index_path = _write_backlog_index(tmp_path, row=backlog_row, section="finished")
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"

    decisions, successors = reconcile.reconcile_plan_workstream_binding(
        repo_root=tmp_path,
        plan_index_path=plan_index_path,
        backlog_index_path=backlog_index_path,
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        stream_path=stream_path,
        changed_paths=(plan_rel,),
        author="test",
        source="test",
    )

    assert any(row.action == "finished_to_successor" for row in decisions)
    assert len(successors) == 1
    successor = successors[0]
    assert successor.source_workstream == "B-300"
    assert successor.successor_workstream == "B-301"

    successor_path = Path(successor.idea_path)
    assert successor_path.is_file()
    successor_text = successor_path.read_text(encoding="utf-8")
    assert "idea_id: B-301" in successor_text
    assert "workstream_reopens: B-300" in successor_text

    source_text = finished_idea.read_text(encoding="utf-8")
    assert "workstream_reopened_by: B-301" in source_text

    plan_index_text = plan_index_path.read_text(encoding="utf-8")
    assert f"| `{plan_rel}` | In progress | 2026-03-03 | 2026-03-03 | `B-301` |" in plan_index_text

    backlog_text = backlog_index_path.read_text(encoding="utf-8")
    assert "| - | B-301 |" in backlog_text
    assert "| planning |" in backlog_text
    assert "](odylith/radar/source/ideas/" in backlog_text
    assert "](/" not in backlog_text

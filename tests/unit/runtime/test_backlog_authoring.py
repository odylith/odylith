from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import backlog_authoring


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
_CORE_SECTION_BODIES = {
    "Problem": "Seed workstream problem detail is grounded enough for validation.",
    "Customer": "Maintainers who need the seeded workstream record to stay valid.",
    "Opportunity": "Keep test backlog fixtures realistic while exercising create behavior.",
    "Product View": "Test fixtures should model real Radar records instead of placeholders.",
    "Success Metrics": "- Seed records validate with real detail.\n- Create tests start from valid backlog truth.",
}


def _repo_rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _grounded_backlog_args() -> list[str]:
    return [
        "--problem",
        "Grounded backlog problem with enough detail to guide implementation.",
        "--customer",
        "Operators who need a real workstream record during Radar validation.",
        "--opportunity",
        "Create the workstream with real detail instead of boilerplate.",
        "--product-view",
        "Backlog records should read like product truth, not a title template.",
        "--success-metrics",
        "- The workstream renders with real detail.\n- The backlog contract stays valid.",
    ]


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
    ordering_score: int,
) -> str:
    body_sections = "\n\n".join(
        [
            f"## {section}\n{_CORE_SECTION_BODIES.get(section, 'Fixture section body for backlog tests.')}"
            for section in _SECTIONS
        ]
    )
    return (
        "status: queued\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        f"date: {date}\n\n"
        "priority: P1\n\n"
        "commercial_value: 4\n\n"
        "product_impact: 4\n\n"
        "market_value: 3\n\n"
        "impacted_parts: odylith\n\n"
        "sizing: M\n\n"
        "complexity: Medium\n\n"
        f"ordering_score: {ordering_score}\n\n"
        "ordering_rationale: seed rationale\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        "promoted_to_plan:\n\n"
        "execution_model: standard\n\n"
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
        f"{body_sections}\n"
    )


def _seed_backlog_repo(root: Path) -> Path:
    _seed_product_repo_shape(root)
    idea_dir = root / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    idea_dir.mkdir(parents=True, exist_ok=True)
    seed_path = idea_dir / "2026-03-30-seed-workstream.md"
    seed_path.write_text(
        _idea_text(
            idea_id="B-101",
            title="Seed Workstream",
            date="2026-03-30",
            ordering_score=100,
        ),
        encoding="utf-8",
    )
    backlog_index = root / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index.parent.mkdir(parents=True, exist_ok=True)
    backlog_index.write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-03-30\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| 1 | B-101 | Seed Workstream | P1 | 100 | 4 | 4 | 3 | M | Medium | queued | [seed]({_repo_rel(root, seed_path)}) |\n\n"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-101 (rank 1)\n"
            "- why now: seed baseline.\n"
            "- expected outcome: quality uplift.\n"
            "- tradeoff: low risk.\n"
            "- deferred for now: none.\n"
            "- ranking basis: no manual priority override; score-based rank.\n"
        ),
        encoding="utf-8",
    )
    return backlog_index


def test_backlog_create_dry_run_batch_is_non_mutating_and_deterministic(tmp_path: Path, capsys) -> None:
    backlog_index = _seed_backlog_repo(tmp_path)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas"
    baseline_index = backlog_index.read_text(encoding="utf-8")

    rc = backlog_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--title",
            "First queued item",
            "--title",
            "Second queued item",
            *_grounded_backlog_args(),
            "--dry-run",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["dry_run"] is True
    assert [row["idea_id"] for row in payload["created"]] == ["B-102", "B-103"]
    assert backlog_index.read_text(encoding="utf-8") == baseline_index
    assert not any(path.name.startswith("2026-03-30-first-queued-item") for path in ideas_root.rglob("*.md"))
    assert not any(path.name.startswith("2026-03-30-second-queued-item") for path in ideas_root.rglob("*.md"))


def test_backlog_create_requires_override_review_date(tmp_path: Path, capsys) -> None:
    _seed_backlog_repo(tmp_path)

    rc = backlog_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--title",
            "Manual priority override item",
            *_grounded_backlog_args(),
            "--founder-override",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 2
    assert "--override-review-date is required" in output


def test_backlog_create_writes_queued_item_and_updates_index(tmp_path: Path) -> None:
    backlog_index = _seed_backlog_repo(tmp_path)

    rc = backlog_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--title",
            "Portable guidance cleanup",
            *_grounded_backlog_args(),
            "--founder-override",
            "--override-review-date",
            "2026-04-15",
                "--override-note",
                "Promote this above the seed workstream.",
                "--ordering-score",
                "101",
            ]
        )

    assert rc == 0
    created_paths = sorted((tmp_path / "odylith" / "radar" / "source" / "ideas").rglob("*portable-guidance-cleanup*.md"))
    assert len(created_paths) == 1
    created_text = created_paths[0].read_text(encoding="utf-8")
    assert "idea_id: B-102" in created_text
    assert "title: Portable guidance cleanup" in created_text

    index_text = backlog_index.read_text(encoding="utf-8")
    assert "| 1 | B-102 | Portable guidance cleanup | P1 | 101 | 3 | 3 | 3 | M | Medium | queued |" in index_text
    assert "[portable-guidance-cleanup](odylith/radar/source/ideas/" in index_text
    assert "### B-102 (rank 1)" in index_text
    assert "Review checkpoint: 2026-04-15." in index_text
    assert "Last updated (UTC): " in index_text


def test_backlog_create_rejects_non_governed_backlog_index_override(tmp_path: Path, capsys) -> None:
    _seed_backlog_repo(tmp_path)
    outside_index = tmp_path / "INDEX.md"
    outside_index.write_text("# Outside\n", encoding="utf-8")

    rc = backlog_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--backlog-index",
            str(outside_index),
            "--title",
            "Escaped backlog write",
            *_grounded_backlog_args(),
        ]
    )
    output = capsys.readouterr().out

    assert rc == 2
    assert "--backlog-index must resolve to `odylith/radar/source/INDEX.md`" in output


def test_backlog_create_rejects_non_governed_ideas_root_override(tmp_path: Path, capsys) -> None:
    _seed_backlog_repo(tmp_path)
    escaped_ideas = tmp_path / "elsewhere" / "ideas"
    escaped_ideas.mkdir(parents=True, exist_ok=True)

    rc = backlog_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--ideas-root",
            str(escaped_ideas),
            "--title",
            "Escaped idea write",
            *_grounded_backlog_args(),
        ]
    )
    output = capsys.readouterr().out

    assert rc == 2
    assert "--ideas-root must resolve to `odylith/radar/source/ideas`" in output


def test_backlog_create_normalizes_product_repo_title_prefix(tmp_path: Path) -> None:
    backlog_index = _seed_backlog_repo(tmp_path)

    rc = backlog_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--title",
            "Odylith Radar Workstream Title Prefix Normalization",
            *_grounded_backlog_args(),
        ]
    )

    assert rc == 0
    created_paths = sorted(
        (tmp_path / "odylith" / "radar" / "source" / "ideas").rglob("*radar-workstream-title-prefix-normalization*.md")
    )
    assert len(created_paths) == 1
    created_text = created_paths[0].read_text(encoding="utf-8")
    assert "title: Radar Workstream Title Prefix Normalization" in created_text
    assert "title: Odylith Radar Workstream Title Prefix Normalization" not in created_text

    index_text = backlog_index.read_text(encoding="utf-8")
    assert "| B-102 | Radar Workstream Title Prefix Normalization |" in index_text
    assert "| B-102 | Odylith Radar Workstream Title Prefix Normalization |" not in index_text


def test_backlog_create_rejects_boilerplate_core_detail(tmp_path: Path, capsys) -> None:
    _seed_backlog_repo(tmp_path)

    rc = backlog_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--title",
            "Boilerplate detail rejection",
            "--problem",
            "Odylith needs an explicit workstream for Boilerplate detail rejection instead of leaving the slice implicit.",
            "--customer",
            "Odylith maintainers and operators who need this capability to exist as governed product truth.",
            "--opportunity",
            "Bound Boilerplate detail rejection as a queued workstream so implementation can attach to one clear source record.",
            "--product-view",
            "If the team is already acting as if this work exists, the backlog should say so explicitly.",
            "--success-metrics",
            "- The workstream is specific enough to guide implementation and validation without further backlog surgery.",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 2
    assert "core detail section `## Problem` still uses backlog-create boilerplate" in output

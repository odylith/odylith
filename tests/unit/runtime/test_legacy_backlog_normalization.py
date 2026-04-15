from __future__ import annotations

import datetime as dt
from pathlib import Path

from odylith.runtime.governance import legacy_backlog_normalization

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


def _idea_text(*, idea_id: str, title: str, founder_override: str) -> str:
    body_sections = "\n\n".join(
        f"## {section}\nGrounded fixture coverage for {section.lower()} in this synthetic workstream."
        for section in _SECTIONS
    )
    return (
        "status: queued\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-04-06\n\n"
        "priority: P1\n\n"
        "commercial_value: 4\n\n"
        "product_impact: 4\n\n"
        "market_value: 4\n\n"
        "impacted_lanes: both\n\n"
        "impacted_parts: odylith\n\n"
        "sizing: M\n\n"
        "complexity: Medium\n\n"
        "ordering_score: 80\n\n"
        "ordering_rationale: normalization fixture\n\n"
        "confidence: high\n\n"
        f"founder_override: {founder_override}\n\n"
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
        f"{body_sections}\n"
    )


def _seed_repo(tmp_path: Path, *, founder_override: str, rationale_lines: list[str], title: str = "Legacy Sync Fix") -> Path:
    repo_root = tmp_path / "repo"
    idea_dir = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    idea_dir.mkdir(parents=True, exist_ok=True)
    idea_path = idea_dir / "2026-04-06-legacy-sync-fix.md"
    idea_path.write_text(
        _idea_text(idea_id="B-101", title=title, founder_override=founder_override),
        encoding="utf-8",
    )
    backlog_index = repo_root / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index.write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-04-06\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 1 | B-101 | Legacy Sync Fix | P1 | 80 | 4 | 4 | 4 | M | Medium | both | queued | [idea](odylith/radar/source/ideas/2026-04/2026-04-06-legacy-sync-fix.md) |\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-101 (rank 1)\n"
            + "\n".join(rationale_lines)
            + "\n"
        ),
        encoding="utf-8",
    )
    return repo_root


def test_normalize_legacy_backlog_index_preserves_existing_prose_and_adds_missing_defaults(tmp_path: Path) -> None:
    repo_root = _seed_repo(
        tmp_path,
        founder_override="no",
        rationale_lines=["- why now: operator supplied context stays intact."],
    )

    result = legacy_backlog_normalization.normalize_legacy_backlog_index(
        repo_root=repo_root,
        today=dt.date(2026, 4, 6),
    )
    text = (repo_root / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8")
    idea_text = (
        repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-06-legacy-sync-fix.md"
    ).read_text(encoding="utf-8")

    assert result.changed is True
    assert result.normalized_idea_specs == ("2026-04-06-legacy-sync-fix",)
    assert result.normalized_table_sections == ("active", "finished")
    assert "impacted_lanes" not in text
    assert "impacted_lanes" not in idea_text
    assert "operator supplied context stays intact." in text
    assert "- expected outcome: clearer product truth and faster follow-on implementation planning." in text
    assert "- tradeoff: queued with sizing and complexity assumptions that should be validated when implementation begins." in text
    assert "- deferred for now: deeper scope decomposition waits until the implementation owner starts the workstream." in text
    assert "- ranking basis: score-based rank; no manual priority override." in text


def test_normalize_legacy_backlog_index_backfills_override_review_checkpoint(tmp_path: Path) -> None:
    repo_root = _seed_repo(
        tmp_path,
        founder_override="yes",
        rationale_lines=[
            "- why now: keep the current rationale body.",
            "- expected outcome: preserve intent.",
            "- tradeoff: accept manual ordering.",
            "- deferred for now: later cleanup.",
            "- ranking basis: score-based rank; no manual priority override.",
        ],
    )

    result = legacy_backlog_normalization.normalize_legacy_backlog_index(
        repo_root=repo_root,
        today=dt.date(2026, 4, 6),
    )
    text = (repo_root / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8")
    idea_text = (
        repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-06-legacy-sync-fix.md"
    ).read_text(encoding="utf-8")

    assert result.changed is True
    assert "impacted_lanes" not in text
    assert "impacted_lanes" not in idea_text
    assert "keep the current rationale body." in text
    assert "Manual priority override applied to keep this workstream in a deliberate queue position." in text
    assert "Review checkpoint: 2026-04-06." in text
    assert "no manual priority override" not in text


def test_backlog_next_action_prefers_metadata_repairs_over_hidden_rationale_noise() -> None:
    action = legacy_backlog_normalization.backlog_next_action(
        errors=(
            "odylith/radar/source/ideas/2026-04/b-052.md: `ordering_score` (94) does not match formula (100)",
            "odylith/radar/source/INDEX.md: reorder rationale for `B-052` missing `- ranking basis:`",
        )
    )

    assert "metadata, status, and plan bindings" in action
    assert "--check-only" in action
    assert "normalized rationale blocks" not in action

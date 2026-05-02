from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith import cli
from odylith.runtime.governance import casebook_release_closeout
from odylith.runtime.governance import release_planning_authoring


def _write_release(repo_root: Path, *, status: str) -> None:
    release_path = repo_root / "odylith" / "radar" / "source" / "releases" / "releases.v1.json"
    release_path.parent.mkdir(parents=True, exist_ok=True)
    release_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "updated_utc": "2026-05-02",
                "aliases": {"current": "release-0-1-13"},
                "releases": [
                    {
                        "release_id": "release-0-1-13",
                        "status": status,
                        "version": "0.1.13",
                        "tag": "v0.1.13",
                        "name": "",
                        "notes": "",
                        "created_utc": "2026-05-01",
                        "shipped_utc": "2026-05-02" if status in {"shipped", "closed"} else "",
                        "closed_utc": "2026-05-02" if status == "closed" else "",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_bug(repo_root: Path, *, verification: str = "Focused release proof passed.") -> Path:
    bug_root = repo_root / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    path = bug_root / "2026-05-02-example-fixed-pending-release.md"
    lines = [
        "- Bug ID: CB-001",
        "",
        "- Status: FixedPendingRelease",
        "",
        "- Fixed: Pending",
        "",
        "- Created: 2026-05-02",
        "",
        "- Severity: P1",
        "",
        "- Reproducibility: High",
        "",
        "- Type: Product",
        "",
        "- Description: Release closeout fixture.",
        "",
        "- GitHub Status: fixed_pending_release",
        "",
        "- Fixed In: 0.1.13",
        "",
        "- Public Response: pending",
        "",
    ]
    if verification:
        lines.extend(["- Verification: " + verification, ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _seed_release_authoring_repo(repo_root: Path) -> None:
    (repo_root / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-05"
    ideas.mkdir(parents=True, exist_ok=True)
    section_text = "Grounded fixture coverage proves the release planning contract."
    ideas.joinpath("2026-05-02-b-101.md").write_text(
        "\n\n".join(
            [
                "status: implementation",
                "idea_id: B-101",
                "title: Release fixture",
                "date: 2026-05-02",
                "priority: P1",
                "commercial_value: 4",
                "product_impact: 4",
                "market_value: 4",
                "impacted_parts: release planning",
                "sizing: M",
                "complexity: Medium",
                "ordering_score: 100",
                "ordering_rationale: release fixture",
                "confidence: high",
                "founder_override: no",
                "promoted_to_plan:",
                "workstream_type: standalone",
                "workstream_parent:",
                "workstream_children:",
                "workstream_depends_on:",
                "workstream_blocks:",
                "related_diagram_ids:",
                "workstream_reopens:",
                "workstream_reopened_by:",
                "workstream_split_from:",
                "workstream_split_into:",
                "workstream_merged_into:",
                "workstream_merged_from:",
                "supersedes:",
                "superseded_by:",
                f"## Problem\n{section_text}",
                f"## Customer\n{section_text}",
                f"## Opportunity\n{section_text}",
                f"## Proposed Solution\n{section_text}",
                f"## Scope\n{section_text}",
                f"## Non-Goals\n{section_text}",
                f"## Risks\n{section_text}",
                f"## Dependencies\n{section_text}",
                f"## Success Metrics\n{section_text}",
                f"## Validation\n{section_text}",
                f"## Rollout\n{section_text}",
                f"## Why Now\n{section_text}",
                f"## Product View\n{section_text}",
                "## Impacted Components\nrelease",
                f"## Interface Changes\n{section_text}",
                f"## Migration/Compatibility\n{section_text}",
                f"## Test Strategy\n{section_text}",
                f"## Open Questions\n{section_text}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_casebook_release_closeout_keeps_bugs_pending_until_release_is_shipped(tmp_path: Path) -> None:
    _write_release(tmp_path, status="active")
    bug_path = _write_bug(tmp_path)

    plan = casebook_release_closeout.apply_casebook_release_closeout(repo_root=tmp_path, release="current")

    assert [item.bug_id for item in plan.pending] == ["CB-001"]
    assert plan.closable == ()
    assert plan.changed_paths == ()
    assert "- Status: FixedPendingRelease" in bug_path.read_text(encoding="utf-8")


def test_casebook_release_closeout_closes_eligible_bugs_after_shipped_release(tmp_path: Path) -> None:
    _write_release(tmp_path, status="shipped")
    bug_path = _write_bug(tmp_path)

    plan = casebook_release_closeout.apply_casebook_release_closeout(repo_root=tmp_path, release="current")

    text = bug_path.read_text(encoding="utf-8")
    assert [item.bug_id for item in plan.closable] == ["CB-001"]
    assert "- Status: Closed" in text
    assert "- Fixed: Released" in text
    assert "- GitHub Status: fixed_released" in text
    assert "- Public Response: closed" in text
    assert "- Fixed In: 0.1.13" in text
    assert "odylith/casebook/bugs/INDEX.md" in plan.changed_paths


def test_casebook_release_closeout_blocks_shipped_release_when_validation_evidence_is_missing(tmp_path: Path) -> None:
    _write_release(tmp_path, status="shipped")
    _write_bug(tmp_path, verification="")

    with pytest.raises(casebook_release_closeout.CasebookReleaseCloseoutError):
        casebook_release_closeout.apply_casebook_release_closeout(repo_root=tmp_path, release="current")


def test_release_casebook_closeout_cli_applies_only_with_apply_flag(tmp_path: Path, capsys) -> None:
    _write_release(tmp_path, status="shipped")
    bug_path = _write_bug(tmp_path)

    dry_run_rc = cli.main(["release", "casebook-closeout", "--repo-root", str(tmp_path), "--release", "current", "--json"])
    dry_run_payload = json.loads(capsys.readouterr().out)
    assert dry_run_rc == 0
    assert dry_run_payload["applied"] is False
    assert "- Status: FixedPendingRelease" in bug_path.read_text(encoding="utf-8")

    apply_rc = cli.main(
        [
            "release",
            "casebook-closeout",
            "--repo-root",
            str(tmp_path),
            "--release",
            "current",
            "--apply",
            "--json",
        ]
    )
    apply_payload = json.loads(capsys.readouterr().out)
    assert apply_rc == 0
    assert apply_payload["applied"] is True
    assert "- Status: Closed" in bug_path.read_text(encoding="utf-8")


def test_release_update_to_shipped_runs_casebook_closeout_automatically(tmp_path: Path, capsys) -> None:
    _seed_release_authoring_repo(tmp_path)
    _write_bug(tmp_path)
    assert release_planning_authoring.main(
        ["--repo-root", str(tmp_path), "create", "release-0-1-13", "--version", "0.1.13"]
    ) == 0
    capsys.readouterr()

    rc = release_planning_authoring.main(
        ["--repo-root", str(tmp_path), "update", "release-0-1-13", "--status", "shipped", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["casebook_release_closeout"]["release_state"] == "shipped"
    assert payload["casebook_release_closeout"]["changed_paths"]
    bug_text = (tmp_path / "odylith/casebook/bugs/2026-05-02-example-fixed-pending-release.md").read_text(
        encoding="utf-8"
    )
    assert "- Status: Closed" in bug_text

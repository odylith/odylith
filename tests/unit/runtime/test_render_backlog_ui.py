from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import render_backlog_ui


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_rewrite_section_text_normalizes_removed_plain_paths() -> None:
    text = "See odylith/casebook/SPEC.md and scripts/compass_dashboard_runtime.py."
    rewritten = render_backlog_ui._rewrite_section_text(repo_root=REPO_ROOT, text=text)

    assert "odylith/casebook/SPEC.md" not in rewritten
    assert "scripts/compass_dashboard_runtime.py" not in rewritten
    assert "odylith/registry/source/components/casebook/CURRENT_SPEC.md" in rewritten
    assert "odylith/registry/source/components/compass/CURRENT_SPEC.md" in rewritten


def test_rewrite_section_text_rewrites_removed_pytest_commands() -> None:
    text = "Run `pytest -q tests/scripts/test_sync_workstream_artifacts.py`."
    rewritten = render_backlog_ui._rewrite_section_text(repo_root=REPO_ROOT, text=text)

    assert "tests/scripts/test_sync_workstream_artifacts.py" not in rewritten
    assert "`odylith sync --repo-root . --check-only --runtime-mode standalone`" in rewritten


def test_rewrite_section_text_rewrites_removed_snapshot_command() -> None:
    text = "Point maintainers to python -m scripts.run_clean_snapshot_strict_sync --repo-root . when needed."
    rewritten = render_backlog_ui._rewrite_section_text(repo_root=REPO_ROOT, text=text)

    assert "python -m scripts.run_clean_snapshot_strict_sync" not in rewritten
    assert "odylith sync --check-only --check-clean --runtime-mode standalone --repo-root ." in rewritten


def test_render_plan_html_normalizes_legacy_meta_row_paths(tmp_path: Path) -> None:
    repo_root = tmp_path
    plan_path = repo_root / "odylith" / "technical-plans" / "in-progress" / "2026-03-26-test-plan.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(
        "\n".join(
            (
                "# Test Plan",
                "",
                "Status: In progress",
                "Created: 2026-03-26",
                "Updated: 2026-03-26",
                "Goal: Break `scripts/render_compass_dashboard.py` into focused modules.",
                "Assumptions: `odylith/surfaces/DASHBOARD_SPEC.md` is stale and must not survive.",
                "Boundary Conditions: `python -m scripts.run_clean_snapshot_strict_sync --repo-root .` is retired.",
                "",
                "## Validation",
                "- Run `pytest -q tests/scripts/test_sync_workstream_artifacts.py`.",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    html = render_backlog_ui._render_plan_html(
        repo_root=repo_root,
        index_output_path=repo_root / "odylith" / "radar" / "radar.html",
        entry={
            "idea_id": "B-999",
            "title": "Renderer Cutover",
            "promoted_to_plan_file": "odylith/technical-plans/in-progress/2026-03-26-test-plan.md",
        },
    )

    assert "scripts/render_compass_dashboard.py" not in html
    assert "odylith/surfaces/DASHBOARD_SPEC.md" not in html
    assert "python -m scripts.run_clean_snapshot_strict_sync" not in html
    assert "tests/scripts/test_sync_workstream_artifacts.py" not in html
    assert "odylith/registry/source/components/compass/CURRENT_SPEC.md" in html
    assert "odylith/registry/source/components/dashboard/CURRENT_SPEC.md" in html
    assert "odylith sync --check-only --check-clean --runtime-mode standalone --repo-root ." in html
    assert "odylith sync --repo-root . --check-only --runtime-mode standalone" in html


def test_render_backlog_ui_uses_diagram_owner_aware_atlas_links() -> None:
    html = render_backlog_ui._render_html(
        payload={
            "entries": [],
            "detail_manifest": [],
            "tooltip_lookup": {
                "diagram_related_workstreams": {
                    "D-001": ["B-001"],
                }
            },
        }
    )

    assert "const diagramWorkstreamLookup = sanitizeLookupListObject(rawTooltipLookup.diagram_related_workstreams);" in html
    assert "function atlasDiagramHref(diagramId, selectedIdeaId)" in html
    assert 'return `../../odylith/index.html?tab=atlas&diagram=${encodeURIComponent(token)}`;' in html
    assert 'owners.includes(workstreamId)' in html


def test_render_backlog_ui_uses_meaningful_hero_kicker() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "Priority Queue and Workstream Status" in html
    assert "See what is queued, active, parked, and finished, backed by repo workstream specs and delivery evidence." in html
    assert "Governed Workstream Queue" not in html
    assert "Local Generated View" not in html

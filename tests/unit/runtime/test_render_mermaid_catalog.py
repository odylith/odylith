from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import render_mermaid_catalog as renderer


def test_render_mermaid_catalog_uses_relative_tooling_shell_href_for_workstream_pills() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert 'const TOOLING_BASE_HREF = "../index.html";' in html
    assert 'a.href = `${TOOLING_BASE_HREF}?tab=radar&workstream=${encodeURIComponent(id)}`;' in html
    assert "../odylith/index.html" not in html


def test_render_mermaid_catalog_workstream_pills_use_shared_workstream_button_contract() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert ".artifact-list a.workstream-pill-link {" in html
    assert (
        f"padding: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING});"
    ) in html
    assert (
        f"font-size: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE});"
    ) in html
    assert (
        f"font-weight: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT});"
    ) in html


def test_render_mermaid_catalog_normalizes_mismatched_selected_diagram_workstream_filter() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert "function diagramMatchesWorkstream(diagram, workstreamId)" in html
    assert "function normalizeSelectedDiagramWorkstreamFilter()" in html
    assert "normalizeSelectedDiagramWorkstreamFilter();" in html
    assert 'if (workstreamFilter !== "all" && !diagramMatchesWorkstream(fallback, workstreamFilter)) {' in html
    assert 'workstreamFilter = "all";' in html
    assert "applyFilters();" in html
    assert "return;" in html


def test_render_mermaid_catalog_indexes_diagram_ids_for_short_search_tokens() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert "diagram.diagram_id," in html
    assert "diagramToken," in html


def test_render_mermaid_catalog_defaults_to_newest_diagram_sort_filter() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert 'id="sortFilter"' in html
    assert 'id="sortWorkstreamFilters"' in html
    assert "grid-template-columns: 400px minmax(0, 1fr);" in html
    assert "grid-template-columns: minmax(150px, 0.78fr) minmax(190px, 1fr);" in html
    assert '<option value="newest">Newest Diagram</option>' in html
    assert 'let sortFilter = "newest";' in html
    assert 'const SORT_TOKENS = new Set(["newest", "oldest", "reviewed", "title", "freshness"]);' in html
    assert "function sortDiagrams(rows)" in html
    assert "applyFilters({ normalizeWorkstreamFilter: false });" in html
    assert "activeList = sortDiagrams(allDiagrams.filter((diagram) => {" in html
    assert 'button.setAttribute("data-diagram-reviewed", diagram.last_reviewed_utc || "");' in html


def test_render_mermaid_catalog_prefers_readable_initial_view() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert "let initialFactor = 0.98;" in html
    assert "const MIN_INITIAL_FIT_FACTOR = 0.94;" in html
    assert "initialFactor = clamp(rawOverrideFactor, MIN_INITIAL_FIT_FACTOR, initialFactor);" in html
    assert "scale = clamp(rawFitScale, MIN_SCALE, MAX_SCALE);" in html


def test_render_mermaid_catalog_uses_specific_surface_header_copy() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert "Live Architecture Maps" in html
    assert "Browse diagrams tied to components, workstreams, and freshness." in html
    assert "Living Diagram System" not in html


def test_render_mermaid_catalog_uses_casebook_style_detail_fact_cards() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert ".diagram-facts {" in html
    assert "grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));" in html
    assert 'data-fact="diagram-id"' in html
    assert "Diagram ID" in html
    assert "Reviewed" in html
    assert 'id="diagramFreshnessCard"' in html
    assert 'button.setAttribute("data-diagram", diagram.diagram_id);' in html
    assert ".hero {" in html
    assert "display: grid;" in html
    assert "justify-content: flex-start;" in html
    assert "width: 100%;" in html
    assert html.index('data-fact="diagram-id"') < html.index('data-fact="kind"')
    assert html.index('data-fact="diagram-id"') < html.index('data-fact="status"')


def test_render_mermaid_catalog_sizes_image_box_from_diagram_dimensions() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert "function applyImageBoxSizing(diagram)" in html
    assert 'imageEl.style.width = `${dims.width}px`;' in html
    assert 'imageEl.style.height = `${dims.height}px`;' in html
    assert "applyImageBoxSizing(diagram);" in html


def test_render_mermaid_catalog_omits_empty_placeholder_copy() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert "No linked artifacts." not in html
    assert "None." not in html
    assert "No diagrams match current filters." not in html


def test_load_catalog_allows_empty_consumer_catalog(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps({"version": "v1", "diagrams": []}) + "\n", encoding="utf-8")

    diagrams, errors, stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert diagrams == []
    assert errors == []
    assert stats == {"total": 0, "fresh": 0, "stale": 0}


def test_load_catalog_rejects_empty_product_catalog(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.0'\n", encoding="utf-8")
    (repo_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog Index\n", encoding="utf-8")
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        json.dumps({"version": "v1", "components": []}) + "\n",
        encoding="utf-8",
    )
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps({"version": "v1", "diagrams": []}) + "\n", encoding="utf-8")

    diagrams, errors, stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert diagrams == []
    assert errors == [f"{catalog_path}: `diagrams` list is empty"]
    assert stats == {"total": 0, "fresh": 0, "stale": 0}


def test_load_catalog_enriches_related_backlog_entries_with_front_matter_metadata(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "sample.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "sample.svg"
    backlog_path = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "sample.md"
    plan_path = repo_root / "odylith" / "technical-plans" / "done" / "2026-04" / "sample.md"
    doc_path = repo_root / "docs" / "sample.md"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, backlog_path, plan_path, doc_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text("graph TD\nA-->B\n", encoding="utf-8")
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    backlog_path.write_text(
        "idea_id: B-321\n"
        "title: Atlas Hot Path\n"
        "status: done\n"
        "\n"
        "## Summary\n",
        encoding="utf-8",
    )
    plan_path.write_text("# Plan\n", encoding="utf-8")
    doc_path.write_text("# Doc\n", encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-321",
                        "slug": "atlas-hot-path",
                        "title": "Atlas Hot Path",
                        "kind": "architecture",
                        "status": "active",
                        "owner": "freedom-research",
                        "summary": "Keep atlas render latency low.",
                        "source_mmd": "odylith/atlas/source/diagrams/sample.mmd",
                        "source_svg": "odylith/atlas/source/diagrams/sample.svg",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["odylith/atlas/source/diagrams/sample.mmd"],
                        "components": [{"name": "atlas", "description": "Atlas surface"}],
                        "related_backlog": ["odylith/radar/source/ideas/2026-04/sample.md"],
                        "related_plans": ["odylith/technical-plans/done/2026-04/sample.md"],
                        "related_docs": ["docs/sample.md"],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagrams, errors, stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert errors == []
    assert stats == {"total": 1, "fresh": 1, "stale": 0}
    assert diagrams[0]["related_backlog"] == [
        {
            "file": "odylith/radar/source/ideas/2026-04/sample.md",
            "href": "../radar/source/ideas/2026-04/sample.md",
            "idea_id": "B-321",
            "title": "Atlas Hot Path",
        }
    ]


def test_load_catalog_uses_reviewed_watch_fingerprints_over_mtime_for_freshness(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "demo.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "demo.svg"
    png_path = repo_root / "odylith" / "atlas" / "source" / "demo.png"
    watched_path = repo_root / "README.md"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, png_path, watched_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text("flowchart TD\n  A-->B\n", encoding="utf-8")
    svg_path.write_text("<svg viewBox='0 0 10 10'></svg>\n", encoding="utf-8")
    png_path.write_bytes(b"png")
    watched_path.write_text("# Demo\n", encoding="utf-8")
    current_watch_fingerprints = renderer.diagram_freshness.watched_path_fingerprints(
        repo_root=repo_root,
        watched_paths=("README.md",),
        resolve_path=lambda token: (repo_root / token).resolve(),
        cache=renderer.diagram_freshness.ContentFingerprintCache(),
    )
    watched_path.touch()
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "slug": "demo",
                        "title": "Demo",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "product",
                        "summary": "Demo diagram",
                        "source_mmd": "odylith/atlas/source/demo.mmd",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["README.md"],
                        "reviewed_watch_fingerprints": current_watch_fingerprints,
                        "components": [{"name": "atlas", "description": "Atlas surface"}],
                        "related_backlog": ["README.md"],
                        "related_plans": ["README.md"],
                        "related_docs": ["README.md"],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagrams, errors, stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert errors == []
    assert stats == {"total": 1, "fresh": 1, "stale": 0}
    assert diagrams[0]["freshness"] == "fresh"
    assert diagrams[0]["stale_reasons"] == []


def test_workstream_title_entries_reuse_enriched_backlog_metadata_without_rereading_files(monkeypatch) -> None:
    monkeypatch.setattr(
        renderer,
        "_read_backlog_front_matter_fields",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("backlog file reread should not be needed")),
    )

    entries = renderer._workstream_title_entries(  # noqa: SLF001
        repo_root=Path("/tmp/unused"),
        diagrams=[
            {
                "related_backlog": [
                    {
                        "file": "odylith/radar/source/ideas/2026-04/sample.md",
                        "idea_id": "B-321",
                        "title": "Atlas Hot Path",
                    }
                ]
            }
        ],
        delivery_intelligence={},
    )

    assert entries == [{"idea_id": "B-321", "title": "Atlas Hot Path"}]


def test_render_mermaid_catalog_skips_rebuild_when_inputs_are_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps({"version": "v1", "diagrams": []}) + "\n", encoding="utf-8")

    monkeypatch.setattr(renderer, "_load_delivery_surface_payload", lambda **kwargs: {})  # noqa: ARG005

    first_rc = renderer.main(["--repo-root", str(repo_root)])
    assert first_rc == 0

    monkeypatch.setattr(
        renderer,
        "_load_component_index",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("catalog rebuild should have been skipped")),
    )

    second_rc = renderer.main(["--repo-root", str(repo_root)])

    assert second_rc == 0


def test_repo_atlas_catalog_titles_do_not_repeat_product_prefix() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    diagrams = payload.get("diagrams", []) if isinstance(payload, dict) else []

    prefixed = [
        f"{row.get('diagram_id', '')}: {row.get('title', '')}"
        for row in diagrams
        if isinstance(row, dict) and str(row.get("title", "")).startswith("Odylith ")
    ]

    assert prefixed == []


def test_meaningful_active_diagram_touches_require_promoted_scope_signal() -> None:
    active = renderer._meaningful_active_diagram_touches(  # noqa: SLF001
        delivery_intelligence={
            "workstreams": {
                "B-040": {
                    "scope_id": "B-040",
                    "scope_signal": {
                        "rank": 1,
                        "rung": "R1",
                        "token": "background_trace",
                        "promoted_default": False,
                    },
                    "evidence_context": {
                        "linked_diagrams": ["D-028"],
                    },
                },
                "B-071": {
                    "scope_id": "B-071",
                    "scope_signal": {
                        "rank": 4,
                        "rung": "R4",
                        "token": "actionable_priority",
                        "promoted_default": True,
                    },
                    "evidence_context": {
                        "linked_diagrams": ["D-028"],
                    },
                },
            }
        }
    )

    assert active == {"D-028": {"B-071"}}

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from odylith.runtime.surfaces import atlas_box_explanations
from odylith.runtime.surfaces import atlas_diagram_intelligence
from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import render_mermaid_catalog as renderer
from odylith.runtime.surfaces import scaffold_mermaid_diagram


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
    assert "function diagramSearchTokens(value)" in html
    assert "function diagramMatchesExactSearchToken(diagram, needle, normalizedNeedle)" in html
    assert "...diagramSearchTokens(diagram.diagram_id)," in html
    assert "exactSearchIndex >= 0 ? exactSearchIndex : 0" in html
    assert 'const unpadded = numeric.replace(/^0+/, "") || "0";' in html


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
    assert ".main {\n        order: 1;" in html
    assert ".sidebar {\n        order: 2;" in html
    assert "justify-content: flex-end;" in html
    assert '<option value="newest">Newest Diagram</option>' in html
    assert 'let sortFilter = "newest";' in html
    assert 'const SORT_TOKENS = new Set(["newest", "oldest", "reviewed", "title", "freshness"]);' in html
    assert "function sortDiagrams(rows)" in html
    assert "applyFilters({ normalizeWorkstreamFilter: false, userIntent: true });" in html
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

    assert "let initialFactor = 1.0;" in html
    assert "const MIN_INITIAL_FIT_FACTOR = 0.94;" in html
    assert "initialFactor = clamp(rawOverrideFactor, MIN_INITIAL_FIT_FACTOR, initialFactor);" in html
    assert "function stageFitPadding()" in html
    assert "const padding = stageFitPadding();" in html
    assert "scale = clamp(rawFitScale, MIN_SCALE, MAX_SCALE);" in html


def test_render_mermaid_catalog_keeps_viewer_stage_plain_white() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert ".viewer-stage::before" not in html
    assert "linear-gradient(90deg, rgba(20, 184, 166, 0.055)" not in html
    assert "background-size: 100% 100%, 42px 42px, 42px 42px, auto;" not in html
    assert "background: #ffffff;" in html


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
    assert "justify-content: flex-end;" in html
    assert "width: 100%;" in html
    assert html.index('data-fact="diagram-id"') < html.index('data-fact="kind"')
    assert html.index('data-fact="diagram-id"') < html.index('data-fact="status"')


def test_render_mermaid_catalog_explains_diagram_and_moves_context_to_bottom_list() -> None:
    html = renderer._render_html(  # noqa: SLF001
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={"component_titles": {"credit-liquidity-core": "Credit And Liquidity Core"}},
        generated_utc="2026-03-27T05:42:32Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert "What This Diagram Shows" in html
    assert '<summary class="artifact-label">How to read this diagram</summary>' in html
    assert '<details class="diagram-guide-panel read-guide">' in html
    assert 'id="diagramReadGuide"' in html
    assert "function diagramReadGuide(diagram)" in html
    assert 'diagram.diagram_boxes.filter((box) => box && typeof box === "object" && String(box.description ?? "").trim())' in html
    assert "const catalogGuide = String(diagram && diagram.read_guide ? diagram.read_guide : \"\").trim();" in html
    assert "return catalogGuide;" in html
    assert "Read this as a first-path rehearsal" not in html
    assert "Read this as a boundary map" not in html
    assert ".diagram-guide-panel:has(> .summary:empty)" in html
    assert ".diagram-guide-panel:has(> .read-guide-body:empty)" in html
    assert ".artifact-group:has(> #ownerWorkstreamLinks:empty)" in html
    assert ".artifact-group:has(> #activeWorkstreamLinks:empty)" in html
    assert ".section:has(> .artifact-group > #ownerWorkstreamLinks:empty):has(> .artifact-group > #activeWorkstreamLinks:empty):has(> #historicalWorkstreamGroup[hidden])" in html
    assert "component cards to decode" not in html


    assert ".summary {" in html
    assert ".read-guide-body {" in html
    assert "Boxes In This Diagram" in html
    assert 'id="diagramBoxList"' in html
    assert "function renderDiagramBoxes(diagram, sectionEl, listEl)" in html
    assert "diagram-box-row" in html
    assert ".diagram-box-role {\n  --label-bg: #f6faf7;" in html
    assert "border-radius: 4px;" in html
    assert "padding: 3px 8px;" in html
    assert "font-size: 11px;" in html
    assert "white-space: normal;" in html
    assert "border-radius: 999px;\n      padding: 1px 7px;\n      color: #446179;" not in html
    assert '<details class="ownership-section">' in html
    assert '<summary class="artifact-label">Owning components</summary>' in html
    assert '<div id="componentList" class="component-list"></div>' in html
    assert "const componentTitleLookup = sanitizeLookupObject(tooltipLookup.component_titles);" in html
    assert "function componentDisplayName(value)" in html
    assert all(name not in html for name in ("componentResponsibilityText", "componentNameWords", "stripLeadingComponentName", "escapeRegExp"))
    assert "Named responsibility in this diagram." not in html
    assert "body.textContent = description;" in html
    assert "component-token" in html
    assert "component-description" in html
    assert "grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));" in html
    assert "diagram-guide-grid" in html
    assert ".diagram-box-section[hidden]" in html
    assert '<details class="section linked-context-section">' in html
    assert '<summary class="artifact-label">Linked records</summary>' in html
    assert '<div class="engineering-context-list">' in html
    assert ".details-grid {" in html
    assert "grid-template-columns: minmax(0, 1fr);" in html
    assert ".linked-context-section .artifact-group {" in html
    assert "grid-template-columns: minmax(150px, 210px) minmax(0, 1fr);" in html
    assert ".linked-context-section .artifact-group:last-child" in html
    assert ".linked-context-section .artifact-list {\n      max-height: none;" in html
    assert "grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));" not in html
    assert html.index('<article class="section diagram-explanation-section">') < html.index(
        '<details class="section linked-context-section">'
    )


def test_load_catalog_requires_png_for_catalog_diagrams(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "sample.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "sample.svg"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text("flowchart TD\n  A-->B\n", encoding="utf-8")
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-404",
                        "slug": "missing-png",
                        "title": "Missing PNG",
                        "kind": "flowchart",
                        "status": "draft",
                        "owner": "freedom-research",
                        "summary": "Catalog record should fail when PNG is missing.",
                        "source_mmd": "odylith/atlas/source/diagrams/sample.mmd",
                        "source_svg": "odylith/atlas/source/diagrams/sample.svg",
                        "source_png": "odylith/atlas/source/diagrams/sample.png",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["odylith/atlas/source/diagrams/sample.mmd"],
                        "components": [{"name": "atlas", "description": "Atlas rendered diagram contract."}],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    _diagrams, errors, _stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert any("source_png does not exist" in error for error in errors)


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

    assert "function applyImageBoxSizing()" in html
    assert 'imageEl.style.width = dims ? `${dims.width}px` : "";' in html
    assert 'imageEl.style.height = dims ? `${dims.height}px` : "";' in html
    assert "applyImageBoxSizing();" in html


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
                        "read_guide": "Start at Atlas, then follow the freshness checks into the linked implementation paths.",
                        "diagram_boxes": [
                                {
                                    "label": "**Atlas renderer**",
                                    "role": "Surface",
                                    "description": "Builds the **operator-facing catalog** from governed diagram source.",
                                }
                        ],
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
    assert diagrams[0]["read_guide"] == (
        "Start at Atlas, then follow the freshness checks into the linked implementation paths."
    )
    assert diagrams[0]["diagram_boxes"] == [
        {
            "label": "Atlas renderer",
            "role": "Surface",
            "description": "Builds the operator-facing catalog from governed diagram source.",
        }
    ]


def test_attach_workstream_relationships_preserves_backlog_derived_owners() -> None:
    diagrams = [
        {
            "diagram_id": "D-321",
            "related_workstreams": [],
            "related_backlog": [
                {
                    "file": "odylith/radar/source/ideas/2026-04/sample.md",
                    "idea_id": "B-321",
                    "title": "Atlas Hot Path",
                }
            ],
        }
    ]

    renderer._attach_diagram_workstream_relationships(  # noqa: SLF001
        diagrams=diagrams,
        traceability_graph={},
        delivery_intelligence={},
    )

    assert diagrams[0]["owner_workstreams"] == ["B-321"]
    assert diagrams[0]["related_workstreams"] == ["B-321"]


def test_load_catalog_allows_atlas_first_draft_without_related_links(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "draft.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "draft.svg"
    png_path = repo_root / "odylith" / "atlas" / "source" / "draft.png"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, png_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text("flowchart TD\n  A-->B\n", encoding="utf-8")
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    png_path.write_bytes(b"png")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-777",
                        "slug": "draft",
                        "title": "Draft Diagram",
                        "kind": "flowchart",
                        "status": "draft",
                        "owner": "product",
                        "summary": "Atlas-first draft.",
                        "source_mmd": "odylith/atlas/source/draft.mmd",
                        "source_svg": "odylith/atlas/source/draft.svg",
                        "source_png": "odylith/atlas/source/draft.png",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["odylith/atlas/source/draft.mmd"],
                        "components": [{"name": "draft", "description": "Draft boundary"}],
                        "related_backlog": [],
                        "related_plans": [],
                        "related_docs": [],
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
    assert diagrams[0]["status"] == "draft"
    assert diagrams[0]["related_backlog"] == []
    assert diagrams[0]["related_plans"] == []
    assert diagrams[0]["related_docs"] == []


def test_atlas_scaffold_default_read_guide_names_diagram_and_components() -> None:
    guide = scaffold_mermaid_diagram._default_read_guide(  # noqa: SLF001
        title="Checkout Settlement Flow",
        kind="flowchart",
        components=[
            {"name": "checkout", "description": "Checkout surface"},
            {"name": "settlement", "description": "Settlement ledger"},
        ],
    )

    assert "Checkout Settlement Flow" in guide
    assert "boundary map" in guide
    assert "product-owned responsibilities" in guide
    assert "Key owned boundaries: checkout, settlement." in guide
    assert "component cards to decode" not in guide


def test_load_catalog_omits_unauthored_box_explanations(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "sample.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "sample.svg"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text(
        "\n".join(
            [
                "flowchart TB",
                "  subgraph SourceTruth[Source truth]",
                "    A[Catalog] --> B[Renderer]",
                "  end",
                "",
            ]
        ),
        encoding="utf-8",
    )
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-322",
                        "slug": "atlas-box-rules",
                        "title": "Atlas Box Rules",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "freedom-research",
                        "summary": "Shows the Atlas box explanation rule.",
                        "source_mmd": "odylith/atlas/source/diagrams/sample.mmd",
                        "source_svg": "odylith/atlas/source/diagrams/sample.svg",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["odylith/atlas/source/diagrams/sample.mmd"],
                        "components": [{"name": "atlas", "description": "Atlas surface."}],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagrams, errors, _stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert errors == []
    assert [box["label"] for box in diagrams[0]["diagram_boxes"]] == ["Source truth", "Catalog", "Renderer"]
    assert all(box["role"] == box["description"] == "" for box in diagrams[0]["diagram_boxes"])
    assert diagrams[0]["summary"] == "Shows the Atlas box explanation rule."
    assert diagrams[0]["read_guide"] == ""


def test_load_catalog_strips_markdown_emphasis_from_visible_payload_fields(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "emphasis.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "emphasis.svg"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text(
        "\n".join(
            [
                "flowchart LR",
                '  A["**Primary actor**"] --> B["__Review record__"]',
                '  B --> C["Outcome evidence"]',
            ]
        ),
        encoding="utf-8",
    )
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-425",
                        "slug": "emphasis-cleanup",
                        "title": "**Evidence Flow**",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "product",
                        "summary": "**Primary actor** moves a reviewed record into evidence.",
                        "read_guide": "Read from **Primary actor** to __Outcome evidence__.",
                        "diagram_boxes": [
                            {
                                "label": "**Primary actor**",
                                "role": "__Actor__",
                                "description": "**Primary actor** starts with a concrete request and needs a visible outcome.",
                            }
                        ],
                        "source_mmd": "odylith/atlas/source/diagrams/emphasis.mmd",
                        "source_svg": "odylith/atlas/source/diagrams/emphasis.svg",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["odylith/atlas/source/diagrams/emphasis.mmd"],
                        "components": [
                            {
                                "name": "**Review record**",
                                "description": "__Owns__ the reviewed state and evidence needed for release proof.",
                            }
                        ],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagrams, errors, _stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert errors == []
    rendered = json.dumps(diagrams[0])
    assert "**" not in rendered
    assert "__" not in rendered
    assert diagrams[0]["title"] == "Evidence Flow"
    assert diagrams[0]["summary"] == "Primary actor moves a reviewed record into evidence."
    assert diagrams[0]["read_guide"] == "Read from Primary actor to Outcome evidence."
    assert diagrams[0]["components"] == [
        {
            "name": "Review record",
            "description": "Owns the reviewed state and evidence needed for release proof.",
        }
    ]
    by_label = {box["label"]: box for box in diagrams[0]["diagram_boxes"]}
    assert set(by_label) == {"Primary actor", "Review record", "Outcome evidence"}
    assert by_label["Primary actor"]["role"] == "Actor"
    assert by_label["Primary actor"]["description"] == (
        "Primary actor starts with a concrete request and needs a visible outcome."
    )
    assert all(by_label[label]["role"] == by_label[label]["description"] == "" for label in ("Review record", "Outcome evidence"))


def test_load_catalog_sanitizes_legacy_greenfield_component_descriptions(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "legacy.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "legacy.svg"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text(
        "\n".join(
            [
                "flowchart LR",
                "  Audio[Audio Capture And Pre-processing Service]",
                "  Pitch[Pitch And Onset Detection Engine]",
                "  Proof[Proof boundary]",
                "  Audio --> Pitch --> Proof",
            ]
        ),
        encoding="utf-8",
    )
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    long_path = (
        "For release 0.0.1, it receives or produces the domain information needed by this first path: "
        "1. User opens the product and starts a take. Reviewers trust it only when the proof boundary is visible."
    )
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-424",
                        "slug": "legacy-greenfield",
                        "title": "First Path Sequence",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "repo",
                        "summary": "Shows the first path.",
                        "source_mmd": "odylith/atlas/source/diagrams/legacy.mmd",
                        "source_svg": "odylith/atlas/source/diagrams/legacy.svg",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["odylith/atlas/source/diagrams/legacy.mmd"],
                        "components": [
                            {
                                "name": "Audio Capture And Pre-processing Service",
                                "description": (
                                    "Audio capture and pre-processing owns microphone or line-in to mono PCM. "
                                    + long_path
                                ),
                            },
                            {
                                "name": "Pitch And Onset Detection Engine",
                                "description": (
                                    "Pitch and onset detection engine owns performs frame-level pitch tracking. "
                                    + long_path
                                ),
                            },
                        ],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagrams, errors, _stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert errors == []
    rendered = json.dumps(diagrams[0])
    assert "User opens the product" not in rendered
    assert "For release 0.0.1, it receives or produces" not in rendered
    assert "owns performs" not in rendered
    assert diagrams[0]["components"] == [
        {
            "name": "Audio Capture And Pre-processing Service",
            "description": "Owns microphone or line-in to mono PCM.",
        },
        {
            "name": "Pitch And Onset Detection Engine",
            "description": "Performs frame-level pitch tracking.",
        },
    ]
    assert [box["label"] for box in diagrams[0]["diagram_boxes"]] == [
        "Audio Capture And Pre-processing Service", "Pitch And Onset Detection Engine", "Proof boundary",
    ]
    assert all(box["role"] == box["description"] == "" for box in diagrams[0]["diagram_boxes"])


def test_atlas_inventory_keeps_labeled_relationships_as_graph_facts() -> None:
    source = '\n'.join(
        [
            'flowchart LR',
            '  w1["B-119 W1"] -->|proves| w2["B-120 W2"]',
            '  w1 --> runner["Benchmark runner"]',
            '  w2 -->|closes| w3["B-121 W3"]',
        ]
    )
    found = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)
    graph = atlas_diagram_intelligence.parse_mermaid_graph(source)

    assert [box.label for box in found] == ["B-119 W1", "B-120 W2", "Benchmark runner", "B-121 W3"]
    assert all(box.role == box.description == "" for box in found)
    assert [(edge.source_id, edge.target_id, edge.label) for edge in graph.edges] == [
        ("w1", "w2", "proves"), ("w1", "runner", ""), ("w2", "w3", "closes"),
    ]


def test_atlas_diagram_intelligence_preserves_authored_state_model_copy() -> None:
    source = "\n".join(
        [
            "stateDiagram-v2",
            "  [*] --> Unknown",
            "  Unknown --> Monitored: sensor calibrated",
            "  Monitored --> NeedsWater: moisture below target",
            "  NeedsWater --> Blocked: sensor fault",
        ]
    )
    summary = "Defines the first plant status transitions."
    read_guide = "Stable status requires evidence."
    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="Plant Care State Model",
        kind="state",
        summary=summary,
        read_guide=read_guide,
        source_text=source,
    )

    assert vars(narrative) == {"summary": summary, "read_guide": read_guide}
    assert len(atlas_diagram_intelligence.parse_mermaid_graph(source).edges) == 4


def test_atlas_diagram_intelligence_preserves_useful_authored_migration_copy() -> None:
    source = "\n".join(
        [
            "flowchart TB",
            '  operator["Operator command<br/>install / upgrade / reinstall / doctor / release migration-gate"]',
            '  resolver["Resolve target release<br/>version, manifest, schema, verification inputs"]',
            '  classifier["Repo scenario classifier<br/>pin, launcher, state, runtime pointer, ledger, source-local, legacy roots"]',
            '  registry["Migration registry<br/>MigrationDefinition contracts"]',
            '  planner["MigrationPlan<br/>selected, skipped, blocked, satisfied-unrecorded, ledger-stale"]',
            '  dryrun["Dry-run and JSON report<br/>scenario, write set, rollback scope, plan fingerprint"]',
            '  apply["Upgrade/apply execution<br/>uses the same plan"]',
            '  ledger["Durable migration ledger<br/>predicate evidence, planned/actual writes, verification"]',
            '  doctor["Doctor observability<br/>pending, blocked, stale, repair-only cleanup"]',
            '  gate["Release migration gate<br/>manifest coverage, fixtures, bypass scan"]',
            '  block["Fail closed before runtime mutation"]',
            '  surfaces["Post-upgrade surfaces<br/>dashboard refresh is separate from migration"]',
            "  operator --> resolver --> classifier --> registry --> planner",
            "  planner --> dryrun",
            "  planner --> apply",
            "  planner --> doctor",
            "  planner --> gate",
            '  planner -->|"blocked or ledger_stale"| block',
            '  apply -->|"selected automatic migration"| ledger',
            '  apply -->|"satisfied_unrecorded"| ledger',
            "  apply --> surfaces",
            '  gate -->|"missing definition, missing fixture, direct bypass"| block',
        ]
    )
    summary = (
        "Install, upgrade, reinstall, doctor, and release gate commands all resolve to one migration plan "
        "before any runtime mutation."
    )
    read_guide = (
        "Read the center column from top to bottom first. It turns an operator command into one shared "
        "MigrationPlan. Then read the branches from MigrationPlan: dry-run previews the plan, upgrade applies it, "
        "doctor explains current health, the release gate checks release readiness, and any unsafe state stops before "
        "runtime files change."
    )

    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="Migration Runtime Upgrade Transaction Flow",
        kind="flowchart",
        summary=summary,
        read_guide=read_guide,
        source_text=source,
    )
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)
    assert narrative.summary == summary
    assert narrative.read_guide == read_guide
    assert {box.label for box in boxes} >= {
        "Operator command", "MigrationPlan", "Upgrade/apply execution",
        "Durable migration ledger", "Fail closed before runtime mutation",
    }
    assert all(box.role == box.description == "" for box in boxes)


def test_atlas_diagram_intelligence_does_not_invent_flow_copy_from_graph() -> None:
    source = "\n".join(
        [
            "flowchart LR",
            '  source["Source verification note: bytes and mode 0640"] --> copier',
            '  copier["Archive Copier: write exact bytes"] --> target',
            '  target["New target note: current mode 0644"] --> verify',
            '  verify["Compare SHA-256 and permission mode"] --> pass',
            '  verify --> fail["Mode preservation fails: planned fix"]',
        ]
    )
    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="Archive record copy and permission verification",
        kind="flowchart",
        summary="",
        read_guide="",
        source_text=source,
    )

    assert narrative == atlas_diagram_intelligence.DiagramNarrative("", "")
    assert len(atlas_diagram_intelligence.parse_mermaid_graph(source).edges) == 5


def test_atlas_diagram_intelligence_keeps_d001_source_summary_without_label_matching() -> None:
    source = "\n".join(
        [
            "flowchart LR",
            '  source["Source verification note: bytes and mode 0640"] --> copier',
            '  copier["Archive Copier: write exact bytes"] --> target',
            '  target["New target note: current mode 0644"] --> verify',
            '  verify["Compare SHA-256 and permission mode"] --> pass',
        ]
    )
    summary = (
        "A local single-file copy moves exact note bytes to a target, then compares permissions "
        "against the source. The observed current mode mismatch remains an explicit verification failure."
    )
    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="Archive record copy and permission verification",
        kind="flowchart",
        summary=summary,
        read_guide="",
        source_text=source,
    )

    assert narrative.summary == summary
    assert narrative.read_guide == ""
    assert "controlled decision at" not in narrative.summary


def test_atlas_diagram_intelligence_preserves_legacy_greenfield_source_facts() -> None:
    summary = (
        "Walk the accepted first path in product terms: The first complete path the product must prove is the solo "
        "monophonic instrument single take, offline analysis flow: 1. User opens LiveScore and taps Record. "
        "2. User plays a roughly 30-second monophonic line. 3. User taps Stop."
    )
    read_guide = (
        "Read First Path Sequence from top to bottom. Each lane is an actor or component; messages are calls, "
        "handoffs, or proof events. Use the component cards to decode Audio Capture before following the links."
    )
    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="First Path Sequence",
        kind="sequenceDiagram",
        summary=summary,
        read_guide=read_guide,
        source_text="sequenceDiagram\n  participant A as User\n  participant B as Product\n  A->>B: start\n",
    )

    assert narrative.summary == summary
    assert narrative.read_guide == read_guide
    assert "User opens LiveScore and taps Record" in narrative.summary
    assert "Start with the first product action" not in narrative.read_guide


def test_atlas_diagram_intelligence_does_not_claim_control_or_proof_for_empty_source_copy() -> None:
    source = "\n".join(
        [
            "flowchart TB",
            '  input["Selected source"] --> control',
            '  control{"Control choice?"} -->|"ready"| proof',
            '  control -->|"blocked"| stop',
            '  proof["Proof receipt"] --> outcome',
        ]
    )
    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="Release path",
        kind="flowchart",
        summary="",
        read_guide="",
        source_text=source,
    )

    assert narrative.summary == ""
    assert narrative.read_guide == ""


def test_load_catalog_rejects_thin_diagram_box_copy(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "thin.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "thin.svg"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text("flowchart TB\n  A[Catalog]\n", encoding="utf-8")
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-323",
                        "slug": "thin-box-copy",
                        "title": "Thin Box Copy",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "freedom-research",
                        "summary": "Shows thin box copy rejection.",
                        "source_mmd": "odylith/atlas/source/diagrams/thin.mmd",
                        "source_svg": "odylith/atlas/source/diagrams/thin.svg",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["odylith/atlas/source/diagrams/thin.mmd"],
                        "components": [{"name": "atlas", "description": "Atlas surface."}],
                        "diagram_boxes": [
                            {
                                "label": "Catalog",
                                "role": "Source",
                                "description": "Catalog.",
                            }
                        ],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    _diagrams, errors, _stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert any("description must explain the box in a complete sentence" in error for error in errors)


def test_load_catalog_rejects_mechanical_diagram_box_copy(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    mmd_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "mechanical.mmd"
    svg_path = repo_root / "odylith" / "atlas" / "source" / "diagrams" / "mechanical.svg"
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    for path in (mmd_path, svg_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text("flowchart TB\n  Owner[Product owner] --> Core[Record core]\n", encoding="utf-8")
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-324",
                        "slug": "mechanical-box-copy",
                        "title": "Mechanical Box Copy",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "freedom-research",
                        "summary": "Shows mechanical box copy rejection.",
                        "source_mmd": "odylith/atlas/source/diagrams/mechanical.mmd",
                        "source_svg": "odylith/atlas/source/diagrams/mechanical.svg",
                        "last_reviewed_utc": dt.date.today().isoformat(),
                        "change_watch_paths": ["odylith/atlas/source/diagrams/mechanical.mmd"],
                        "components": [{"name": "atlas", "description": "Atlas surface."}],
                        "diagram_boxes": [
                            {
                                "label": "Product owner",
                                "role": "Start",
                                "description": (
                                    "Product owner is part of the path; incoming arrows show what must "
                                    "be true before it runs, and outgoing arrows show what it enables next."
                                ),
                            }
                        ],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    _diagrams, errors, _stats = renderer._load_catalog(  # noqa: SLF001
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=repo_root / "odylith" / "atlas" / "atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert any("description must explain project meaning, not diagram mechanics" in error for error in errors)


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

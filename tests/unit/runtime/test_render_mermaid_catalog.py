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
    assert "How To Read This View" in html
    assert 'id="diagramReadGuide"' in html
    assert "function diagramReadGuide(diagram)" in html
    assert "const catalogGuide = String(diagram && diagram.read_guide ? diagram.read_guide : \"\").trim();" in html
    assert "if (catalogGuide) {" in html
    assert "Start with the named entrypoints, then follow each arrow to the next decision, action, proof, or recovery point." in html
    assert "Boxes In This Diagram" in html
    assert 'id="diagramBoxList"' in html
    assert "function renderDiagramBoxes(diagram)" in html
    assert "diagram-box-row" in html
    assert ".diagram-box-role {\n  --label-bg: #f6faf7;" in html
    assert "border-radius: 4px;" in html
    assert "padding: 3px 8px;" in html
    assert "font-size: 11px;" in html
    assert "white-space: normal;" in html
    assert "border-radius: 999px;\n      padding: 1px 7px;\n      color: #446179;" not in html
    assert "Owning Components" in html
    assert "const componentTitleLookup = sanitizeLookupObject(tooltipLookup.component_titles);" in html
    assert "function componentDisplayName(value)" in html
    assert "component-token" in html
    assert "diagram-guide-grid" in html
    assert ".diagram-box-section[hidden]" in html
    assert '<article class="section linked-context-section">' in html
    assert '<div class="engineering-context-list">' in html
    assert ".details-grid {" in html
    assert "grid-template-columns: minmax(0, 1fr);" in html
    assert ".linked-context-section .artifact-group {" in html
    assert "grid-template-columns: minmax(150px, 210px) minmax(0, 1fr);" in html
    assert ".linked-context-section .artifact-group:last-child" in html
    assert ".linked-context-section .artifact-list {\n      max-height: none;" in html
    assert "grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));" not in html
    assert html.index('<article class="section diagram-explanation-section">') < html.index(
        '<article class="section linked-context-section">'
    )


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
                        "read_guide": "Start at Atlas, then follow the freshness checks into the linked implementation paths.",
                        "diagram_boxes": [
                                {
                                    "label": "Atlas renderer",
                                    "role": "Surface",
                                    "description": "Builds the operator-facing catalog from governed diagram source.",
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
    assert "named entrypoint" in guide
    assert "checkout, settlement" in guide


def test_load_catalog_derives_container_and_inner_box_explanations(tmp_path: Path) -> None:
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
    boxes = diagrams[0]["diagram_boxes"]
    assert [box["label"] for box in boxes] == ["Source truth", "Catalog", "Renderer"]
    assert boxes[0]["role"] == "Container"
    assert boxes[1]["role"] == "Source truth"
    assert "boxes inside it" in boxes[0]["description"]
    assert "Catalog stores the source information" in boxes[1]["description"]
    assert "hands off to Renderer" in boxes[1]["description"]
    assert "This box represents" not in boxes[1]["description"]


def test_atlas_box_explanations_generate_action_oriented_node_copy() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "flowchart LR",
                "  PlantOwner[Plant owner] --> Plant[One potted plant]",
                "  Plant --> Sensor[Plant sensing unit]",
                "  Sensor --> Decision[Care decision core]",
                "  Decision --> Doser[Liquid dosing controller]",
                "  Doser --> Log[Care event log]",
                "  Log --> Interface[Owner status interface]",
                "",
            ]
        )
    )
    by_label = {box.label: box.description for box in boxes}

    assert "makes or accepts the decisions" in by_label["Plant owner"]
    assert "hands off to One potted plant" in by_label["Plant owner"]
    assert "object whose state changes" in by_label["One potted plant"]
    assert "hands off to Plant sensing unit" in by_label["One potted plant"]
    assert "measures the current state" in by_label["Plant sensing unit"]
    assert "hands off to Care decision core" in by_label["Plant sensing unit"]
    assert "decides whether the next action is allowed" in by_label["Care decision core"]
    assert "hands off to Liquid dosing controller" in by_label["Care decision core"]
    assert "performs the bounded action" in by_label["Liquid dosing controller"]
    assert "hands off to Care event log" in by_label["Liquid dosing controller"]
    assert "records the evidence needed" in by_label["Care event log"]
    assert "hands off to Owner status interface" in by_label["Care event log"]
    assert "shows the current state" in by_label["Owner status interface"]
    assert all("This box represents" not in description for description in by_label.values())


def test_atlas_diagram_intelligence_explains_state_model_transitions() -> None:
    source = "\n".join(
        [
            "stateDiagram-v2",
            "  [*] --> Unknown",
            "  Unknown --> Monitored: sensor calibrated",
            "  Monitored --> NeedsWater: moisture below target",
            "  Monitored --> NutrientDue: interval elapsed",
            "  NeedsWater --> Dosing: reservoir available",
            "  NutrientDue --> Dosing: diluted dose allowed",
            "  Dosing --> AbsorptionWait: capped pump complete",
            "  AbsorptionWait --> Stable: recheck inside band",
            "  AbsorptionWait --> Blocked: still dry after limit",
            "  NeedsWater --> Blocked: sensor or reservoir fault",
            "  NutrientDue --> Blocked: reservoir or schedule fault",
            "  Stable --> Monitored: next sample interval",
            "  Blocked --> Monitored: owner recovery verified",
        ]
    )

    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="Plant Care State Model",
        kind="state",
        summary="Defines the first plant status transitions.",
        read_guide="Stable status requires evidence.",
        source_text=source,
    )
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(source)
    by_label = {box.label: box.description for box in boxes}

    assert narrative.generated is True
    assert "Unknown" in narrative.summary
    assert "Monitored" in narrative.summary
    assert "Dosing" in narrative.summary
    assert "Blocked" in narrative.summary
    assert "moisture below target" in narrative.summary
    assert "Read this as a guarded loop" in narrative.read_guide
    assert "At Monitored" in narrative.read_guide
    assert "moisture below target leads to Needs Water" in narrative.read_guide
    assert "Blocked means the system should stop" in narrative.read_guide
    assert "starts the path" in by_label["Unknown"]
    assert "branch point" in by_label["Monitored"]
    assert "performs the bounded action" in by_label["Dosing"]
    assert "stops normal progress" in by_label["Blocked"]
    assert all("This box represents" not in description for description in by_label.values())


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
    roles = {box.label: box.role for box in boxes}

    assert narrative.generated is False
    assert narrative.summary == summary
    assert narrative.read_guide == read_guide
    assert roles["Operator command"] == "Start"
    assert roles["MigrationPlan"] == "Decision"
    assert roles["Upgrade/apply execution"] == "Action"
    assert roles["Durable migration ledger"] == "Evidence"
    assert roles["Fail closed before runtime mutation"] == "Safety stop"


def test_atlas_diagram_intelligence_generates_human_flow_copy_without_label_soup() -> None:
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
            "  operator --> resolver --> classifier --> registry --> planner",
            "  planner --> dryrun",
            "  planner --> apply",
            "  planner --> doctor",
            "  planner --> gate",
            '  planner -->|"blocked or ledger_stale"| block',
            '  apply -->|"selected automatic migration"| ledger',
            '  gate -->|"missing definition, missing fixture, direct bypass"| block',
        ]
    )

    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="Migration Runtime Upgrade Transaction Flow",
        kind="flowchart",
        summary="Shows a flow.",
        read_guide="Read the arrows.",
        source_text=source,
    )

    copy = f"{narrative.summary}\n{narrative.read_guide}"
    assert narrative.generated is True
    assert "This diagram follows" not in copy
    assert "none named" not in copy
    assert "This view shows" not in copy
    assert "This diagram shows" not in copy
    assert "shows how" not in copy.casefold()
    assert "Operator command to MigrationPlan" in narrative.summary
    assert "Resolve target release" in narrative.summary
    assert "Fail closed before runtime mutation" in narrative.summary
    assert "Durable migration ledger" in narrative.summary
    assert "Read the main spine first" in narrative.read_guide
    assert "Read Durable migration ledger as the evidence boundary" in narrative.read_guide
    assert "Read Resolve target release as the evidence boundary" not in narrative.read_guide
    assert "selected, skipped, blocked, satisfied-unrecorded" not in narrative.summary


def test_atlas_diagram_intelligence_explains_surface_dag_control_and_proof_boundary() -> None:
    source = "\n".join(
        [
            "flowchart TB",
            '  sync["Selective sync or owned-surface refresh"]',
            '  order["Surface order"]',
            '  fingerprint["Surface fingerprint DAG"]',
            '  reusable{"Outputs reusable?"}',
            '  reuse["Reuse current rendered bytes"]',
            '  workers["Per-surface workers"]',
            '  compass["Compass DAG"]',
            '  radar["Radar DAG"]',
            '  atlasChoice{"Atlas refresh mode?"}',
            '  atlasSync["Atlas sync"]',
            '  atlasRender["Atlas render"]',
            '  registry["Registry DAG"]',
            '  accountability["Public accountability"]',
            '  browser["Surface browser matrix"]',
            '  check["Selective sync + sync --check-only"]',
            "  sync --> order --> fingerprint --> reusable",
            '  reusable -- "yes" --> reuse',
            '  reusable -- "no" --> workers',
            "  workers --> compass",
            "  workers --> radar",
            "  workers --> atlasChoice",
            "  workers --> registry",
            '  atlasChoice -- "--atlas-sync" --> atlasSync --> accountability',
            '  atlasChoice -- "render only" --> atlasRender --> browser',
            "  registry --> check",
        ]
    )

    narrative = atlas_diagram_intelligence.build_diagram_narrative(
        title="Discipline Surface DAGs And Release Proof",
        kind="flowchart",
        summary="This view shows how Odylith Discipline state reaches workers.",
        read_guide="Read from Odylith Discipline state through the arrows.",
        source_text=source,
    )

    copy = f"{narrative.summary}\n{narrative.read_guide}"
    assert narrative.generated is True
    assert "This view shows" not in copy
    assert "Outputs reusable?" in narrative.summary
    assert "Per-surface workers is the fan-out point" in narrative.summary
    assert "Public accountability" in narrative.summary
    assert "Surface browser matrix" in narrative.summary
    assert "--atlas-sync\" --> atlasSync" not in copy
    assert "Use the labeled edges as gates" in narrative.read_guide
    assert "those nodes explain why the final outcome can be trusted" in narrative.read_guide


def test_atlas_box_explanations_infer_common_governance_surface_actions() -> None:
    boxes = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        "\n".join(
            [
                "flowchart LR",
                "  Product[Odylith product] --> Radar[Radar]",
                "  Radar --> Plans[Technical Plans]",
                "  Plans --> Atlas[Atlas topology map]",
                "  Atlas --> Compass[Compass status]",
                "  Compass --> Router[Subagent Router]",
                "  Router --> Orchestrator[Subagent Orchestrator]",
                "  Orchestrator --> Handshake[Context-to-Execution handshake]",
                "",
            ]
        )
    )
    by_label = {box.label: box.description for box in boxes}

    assert "defines the product scope" in by_label["Odylith product"]
    assert "hands off to Radar" in by_label["Odylith product"]
    assert "tracks the work choices" in by_label["Radar"]
    assert "hands off to Technical Plans" in by_label["Radar"]
    assert "turns selected work into an implementation path" in by_label["Technical Plans"]
    assert "hands off to Atlas topology map" in by_label["Technical Plans"]
    assert "shows the system shape" in by_label["Atlas topology map"]
    assert "hands off to Compass status" in by_label["Atlas topology map"]
    assert "summarizes current runtime state" in by_label["Compass status"]
    assert "hands off to Subagent Router" in by_label["Compass status"]
    assert "chooses where work should go next" in by_label["Subagent Router"]
    assert "hands off to Subagent Orchestrator" in by_label["Subagent Router"]
    assert "coordinates bounded work" in by_label["Subagent Orchestrator"]
    assert "passes agreed state across a boundary" in by_label["Context-to-Execution handshake"]
    assert "reached after Subagent Orchestrator" in by_label["Context-to-Execution handshake"]
    assert all("concrete step" not in description for description in by_label.values())


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

from __future__ import annotations

import json
from pathlib import Path

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

"""Atlas box metadata has one literal-text presentation owner."""

import inspect

from odylith.runtime.surfaces import atlas_detail_layout as details
from odylith.runtime.surfaces import render_mermaid_catalog as catalog


def test_catalog_delegates_box_metadata_without_a_second_text_interpreter() -> None:
    source = inspect.getsource(catalog)
    assert "function renderDiagramBoxes(" not in source
    assert "renderDiagramBoxes(diagram, diagramBoxesSectionEl, diagramBoxListEl);" in source
    runtime = details.DETAIL_RUNTIME_HELPERS_JS
    assert "function renderDiagramBoxes(diagram, sectionEl, listEl)" in runtime
    assert "displayText(box." not in runtime
    for field in ("label", "role", "description"):
        assert f"String(box.{field} ?? \"\")" in runtime
    html = catalog._render_html(
        diagrams=[], stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21, tooltip_lookup={}, generated_utc="2026-09-08T00:00:00Z",
        brand_head_html="", tooling_base_href="../index.html",
    )
    assert html.count("function renderDiagramBoxes(") == 1
    assert "__ODYLITH_ATLAS_DETAIL_RUNTIME_HELPERS__" not in html


def test_catalog_optional_details_round_trip_without_text_interpretation() -> None:
    from odylith.runtime.surfaces import atlas_box_explanations as boxes
    raw = [{
        'label': 'Intake support', 'role': 'Proposed component',
        'description': 'Preserves the complete requested intake record and its authorization boundary.',
        'details': [{'label': 'Boundary check — café', 'text': 'Keep **exact** <tag> & `proof`.\nPreserve the final 日本語 condition.'}],
    }]
    errors = []
    normalized = boxes.normalize_catalog_diagram_boxes(raw_boxes=raw, context='test', errors=errors)
    assert errors == []
    merged = boxes.merge_diagram_box_explanations(source_text='flowchart LR\n intake["Intake support"]\n', catalog_boxes=normalized)
    assert merged[0]['details'] == raw[0]['details']
    assert merged[0]['description'] == raw[0]['description']
    merged[0]['details'][0]['text'] = 'Changed.'
    assert normalized[0].details[0]['text'] == raw[0]['details'][0]['text']
    assert 'details' not in boxes.DiagramBoxExplanation('Legacy', 'Component', 'Existing description.').as_dict()


def test_empty_optional_details_stay_optional_and_malformed_details_refuse() -> None:
    from odylith.runtime.surfaces import atlas_box_explanations as boxes
    raw = {'label': 'Intake support', 'description': 'Preserves the complete requested intake record and its authorization boundary.'}
    for value in (None, {}, 'copy', [None], [{'label': 'Check', 'text': ' '}], [{'label': 'Check', 'text': 'Exact.', 'extra': 1}]):
        errors = []
        assert boxes.normalize_catalog_diagram_boxes(raw_boxes=[{**raw, 'details': value}], context='test', errors=errors) == ()
        assert errors and all('details' in error for error in errors)
    errors = []
    row = boxes.normalize_catalog_diagram_boxes(raw_boxes=[{**raw, 'details': []}], context='test', errors=errors)[0]
    assert errors == [] and row.as_dict()['details'] == []


def test_box_detail_renderer_uses_native_disclosure_and_inert_text() -> None:
    runtime = details.DETAIL_RUNTIME_HELPERS_JS
    assert 'document.createElement("details")' in runtime
    assert 'document.createElement("summary")' in runtime
    assert 'label.textContent = String(detail.label ?? "")' in runtime
    assert 'text.textContent = String(detail.text ?? "")' in runtime
    assert '.innerHTML' not in runtime

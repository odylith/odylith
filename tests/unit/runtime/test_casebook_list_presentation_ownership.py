"""Casebook list markup has one owner included in generated-surface freshness."""

import inspect

from odylith.runtime.surfaces import casebook_list_presentation_runtime as presentation
from odylith.runtime.surfaces import render_casebook_dashboard as renderer


def test_casebook_list_presentation_is_adopted_without_a_second_empty_owner() -> None:
    source = inspect.getsource(renderer)
    assert "No Casebook entries match the current filters." not in source
    assert "bugList.innerHTML = rows.map" not in source
    assert "totalCount: bugSummaries.length" in source
    html = renderer._render_html(payload={"bugs": []})
    assert html.count("function casebookListPresentation(") == 1
    assert "__CASEBOOK_LIST_PRESENTATION__" not in html
    assert "bugList.innerHTML = presentation.listHtml;" in html
    assert "detailPane.innerHTML = presentation.detailHtml;" in html
    assert "detailRenderToken += 1;" in html


def test_casebook_presentation_changes_invalidate_refresh_fingerprint(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    owner = tmp_path / "casebook_list_presentation_runtime.py"
    owner.write_text("first presentation", encoding="utf-8")
    monkeypatch.setattr(presentation, "__file__", str(owner))
    before = renderer._refresh_guard_code_fingerprint()
    owner.write_text("updated presentation", encoding="utf-8")
    assert renderer._refresh_guard_code_fingerprint() != before

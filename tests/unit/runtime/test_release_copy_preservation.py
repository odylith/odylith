"""Release copy survives loading, installer fallback and shell presentation intact."""

from html import escape
from pathlib import Path

import pytest

from odylith.install.release_assets import _release_highlights
from odylith.runtime.release_notes import load_release_notes_source
from odylith.runtime.surfaces.tooling_dashboard_release_presenter import render_release_spotlight_html


COMPLETE_COPY = (
    "Operators can review the affected components, compare the proposed record changes, "
    "inspect the source references, and verify the published result before starting "
    "the next workstream. The same review includes responsibility boundaries and "
    "recovery obligations; it does not grant permission to replace consumer-authored records."
)


@pytest.mark.parametrize("field", ["title", "summary", "note_link_label", "external_link_label", "reopen_label"])
def test_authored_scalar_keeps_late_constraint(tmp_path: Path, field: str) -> None:
    path = tmp_path / "odylith/runtime/source/release-notes/v7.2.1.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"---\n{field}: {COMPLETE_COPY}\n---\n\n# Release\n", encoding="utf-8")
    note = load_release_notes_source(repo_root=tmp_path, version="7.2.1")
    assert note is not None
    assert getattr(note, field) == COMPLETE_COPY


@pytest.mark.parametrize("location", ["front_matter", "body"])
def test_authored_highlight_keeps_late_constraint(tmp_path: Path, location: str) -> None:
    path = tmp_path / "odylith/runtime/source/release-notes/v7.2.1.md"
    path.parent.mkdir(parents=True)
    content = (
        f"---\nhighlights:\n  - {COMPLETE_COPY}\n---\n\n# Release\n"
        if location == "front_matter" else f"# Release\n\n- {COMPLETE_COPY}\n"
    )
    path.write_text(content, encoding="utf-8")
    note = load_release_notes_source(repo_root=tmp_path, version="7.2.1")
    assert note is not None
    assert note.highlights == (COMPLETE_COPY,)


@pytest.mark.parametrize("location", ["explicit", "body"])
def test_installer_keeps_selected_highlights_complete_and_count_bounded(location: str) -> None:
    items = [COMPLETE_COPY, "A second complete point.", "A third complete point.", "An unselected point."]
    kwargs = {"explicit": items} if location == "explicit" else {"body": "\n".join(f"- {item}" for item in items)}
    assert _release_highlights(**kwargs) == tuple(items[:3])


@pytest.mark.parametrize("field", ["title", "summary", "detail", "highlights", "release_body", "notes_label"])
def test_presenter_preserves_selected_copy(field: str) -> None:
    story = {"show": True, "from_version": "7.2.0", "to_version": "7.2.1", "notes_url": "https://example.invalid/notes"}
    story[field] = [COMPLETE_COPY] if field == "highlights" else COMPLETE_COPY
    rendered = render_release_spotlight_html({"release_spotlight": story})
    assert escape(COMPLETE_COPY) in rendered
    assert "..." not in rendered


def test_empty_spotlight_remains_absent() -> None:
    assert render_release_spotlight_html({}) == ""


def test_explicit_highlight_and_summary_precede_optional_body_detail() -> None:
    story = {
        "show": True, "from_version": "7.2.0", "to_version": "7.2.1",
        "highlights": ["One authored highlight."], "summary": "The authored summary.",
        "detail": COMPLETE_COPY,
    }
    rendered = render_release_spotlight_html({"release_spotlight": story})
    assert "One authored highlight." in rendered
    assert "The authored summary." in rendered
    assert COMPLETE_COPY not in rendered

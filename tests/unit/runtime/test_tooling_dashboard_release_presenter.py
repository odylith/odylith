"""Coverage for tooling-dashboard release spotlight rendering."""

from __future__ import annotations

from odylith.runtime.surfaces import tooling_dashboard_release_presenter


def test_render_release_spotlight_preserves_sparse_release_body_without_invented_bullets() -> None:
    html = tooling_dashboard_release_presenter.render_release_spotlight_html(
        {
            "release_spotlight": {
                "show": True,
                "from_version": "0.1.10",
                "to_version": "0.1.11",
                "release_body": (
                    "One cleaner upgrade closeout keeps the pinned runtime and repo pin aligned.\n\n"
                    "Release proof stays easier to trust because the popup no longer opens without the actual release story."
                ),
            }
        }
    )

    assert '<ul class="upgrade-spotlight-list">' not in html
    assert "One cleaner upgrade closeout keeps the pinned runtime and repo pin aligned." in html
    assert "Release proof stays easier to trust because the popup no longer opens without the actual release story." in html


def test_render_release_spotlight_keeps_summary_once_and_highlights_in_details() -> None:
    html = tooling_dashboard_release_presenter.render_release_spotlight_html(
        {
            "release_spotlight": {
                "show": True,
                "from_version": "0.1.10",
                "to_version": "0.1.11",
                "summary": "Compass refresh and release proof now tell the truth faster.",
                "highlights": ["The spotlight keeps two concise takeaways instead of opening blank."],
            }
        }
    )

    assert "Compass refresh and release proof now tell the truth faster." in html
    assert "The spotlight keeps two concise takeaways instead of opening blank." in html
    assert html.count("Compass refresh and release proof now tell the truth faster.") == 1
    assert '<p class="upgrade-spotlight-story-summary">' in html
    assert '<details class="upgrade-spotlight-details"><summary>What changed</summary>' in html
    assert '<details class="upgrade-spotlight-details" open' not in html


def test_all_supplied_highlights_and_single_source_metadata_survive_closed_details() -> None:
    summary = "Exact authored purpose & outcome."
    highlights = [f"Exact supplied highlight {index}." for index in range(7)]
    rendered = tooling_dashboard_release_presenter.render_release_spotlight_html({"release_spotlight": {
        "show": True, "from_version": "0.1.14", "to_version": "0.1.15",
        "title": "Exact authored title", "summary": summary,
        "highlights": [summary, *highlights, highlights[0]],
        "release_published_at": "2026-10-06T12:30:00Z", "notes_url": "https://example.com/exact-notes",
    }})
    assert '<h2 id="upgradeSpotlightTitle" class="upgrade-spotlight-title">Exact authored title</h2>' in rendered
    assert rendered.count("Exact authored purpose &amp; outcome.") == 1
    assert rendered.count("2026-10-06") == 1
    assert rendered.count("v0.1.14 -&gt; v0.1.15") == 1
    assert "upgrade-spotlight-title-version" not in rendered
    for item in highlights:
        assert rendered.count(item) == 1
    assert rendered.index(highlights[-1]) < rendered.index("</details>")
    assert 'href="https://example.com/exact-notes"' in rendered
    assert rendered.index("</details>") < rendered.index('class="upgrade-spotlight-link"')
    assert 'id="upgradeSpotlightDismiss"' in rendered
    assert 'id="upgradeSpotlightBackdrop"' in rendered
    assert 'role="dialog" aria-modal="true"' in rendered


def test_empty_or_incomplete_upgrade_payload_has_no_modal() -> None:
    for story in ({}, {"show": False}, {"show": True, "to_version": "0.1.15"}):
        assert tooling_dashboard_release_presenter.render_release_spotlight_html({"release_spotlight": story}) == ""


def test_distinct_authored_detail_survives_alongside_summary_and_highlight() -> None:
    story = {
        "show": True, "from_version": "0.1.14", "to_version": "0.1.15",
        "summary": "Exact authored primary summary.",
        "highlights": ["Exact authored highlight."],
        "detail": "Exact separate authored detail & evidence.",
    }
    rendered = tooling_dashboard_release_presenter.render_release_spotlight_html({"release_spotlight": story})
    assert rendered.count(story["summary"]) == 1
    assert rendered.count(story["highlights"][0]) == 1
    assert rendered.count("Exact separate authored detail &amp; evidence.") == 1
    assert rendered.index("<details") < rendered.index("Exact separate authored detail") < rendered.index("</details>")
    for duplicate in (story["summary"], story["highlights"][0]):
        story["detail"] = duplicate
        rendered = tooling_dashboard_release_presenter.render_release_spotlight_html({"release_spotlight": story})
        assert rendered.count(duplicate) == 1

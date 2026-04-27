"""Coverage for tooling-dashboard release spotlight rendering."""

from __future__ import annotations

from odylith.runtime.surfaces import tooling_dashboard_release_presenter


def test_render_release_spotlight_promotes_sparse_release_copy_into_two_bullets() -> None:
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

    assert '<ul class="upgrade-spotlight-list">' in html
    assert "One cleaner upgrade closeout keeps the pinned runtime and repo pin aligned." in html
    assert "Release proof stays easier to trust because the popup no longer opens without the actual release story." in html


def test_render_release_spotlight_uses_summary_as_a_bullet_when_needed() -> None:
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
    assert "upgrade-spotlight-story-summary" not in html

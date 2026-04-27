from __future__ import annotations

from odylith.runtime.surfaces import dashboard_shell_links


def test_radar_workstream_href_uses_canonical_radar_route() -> None:
    assert dashboard_shell_links.radar_workstream_href("B-025") == "?tab=radar&workstream=B-025"
    assert dashboard_shell_links.radar_workstream_href("B-025", view="plan") == "?tab=radar&workstream=B-025&view=plan"


def test_shell_href_preserves_existing_non_radar_scope_rules() -> None:
    assert dashboard_shell_links.shell_href(tab="compass", workstream="B-025", view="plan") == "?tab=compass&scope=B-025"
    assert dashboard_shell_links.shell_href(tab="registry", component="radar", view="plan") == "?tab=registry&component=radar"

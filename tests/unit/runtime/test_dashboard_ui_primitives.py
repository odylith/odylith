from __future__ import annotations

import re

from odylith.runtime.surfaces import dashboard_ui_primitives as ui


def test_action_chip_surface_css_expands_selector_lists_per_member() -> None:
    css = ui.action_chip_surface_css(selector=".pill, .chip-link")

    assert ".pill, .chip-link {" in css
    assert re.search(
        r"\.pill:hover,\s*\.chip-link:hover,\s*\.pill:focus-visible,\s*\.chip-link:focus-visible\s*\{",
        css,
    )
    assert re.search(r"\.pill:focus-visible,\s*\.chip-link:focus-visible\s*\{", css)
    assert ".pill, .chip-link:hover" not in css
    assert ".pill, .chip-link:focus-visible" not in css


def test_detail_action_chip_css_inherits_dashboard_font_family() -> None:
    css = ui.detail_action_chip_css(selector=".chip-link")

    assert re.search(
        r"\.chip-link\s*\{[^}]*font-family:\s*inherit;[^}]*color:\s*var\(--chip-link-text\);[^}]*font-size:\s*11px;[^}]*line-height:\s*1;[^}]*letter-spacing:\s*0\.01em;[^}]*font-weight:\s*700;",
        css,
        flags=re.S,
    )


def test_shell_tab_surface_css_normalizes_selector_lists_for_all_states() -> None:
    css = ui.shell_tab_surface_css(
        selector=".tab, .tab-alt",
        active_selector='.tab[aria-selected="true"], .tab-alt[aria-selected="true"]',
    )

    assert ".tab, .tab-alt {" in css
    assert "border-radius: 14px 14px 0 0;" in css
    assert "border-bottom: 0;" in css
    assert "margin-bottom: -1px;" in css
    assert "z-index: 1;" in css
    assert re.search(
        r"\.tab:hover,\s*\.tab-alt:hover,\s*\.tab:focus-visible,\s*\.tab-alt:focus-visible\s*\{",
        css,
    )
    assert '.tab[aria-selected="true"], .tab-alt[aria-selected="true"] {' in css
    assert "z-index: 2;" in css
    assert ".tab, .tab-alt:focus-visible" not in css

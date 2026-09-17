"""Native handoff disclosures keep full source-bound prompts usable without JS."""

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import preview_project_dashboard_payload
from odylith.runtime.project_intelligence.assets import load_project_tab_css
from odylith.runtime.project_intelligence.presenter import render_project_html
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _browser, _failure_screenshot_path, _new_page, _static_server,
)
from tests.unit.runtime.test_greenfield_authored_project_dashboard import (
    _accepted_preview, _proposal, _source_launch_context,
)
from tests.unit.runtime.test_greenfield_scoped_readiness import DECISION, _package


@pytest.mark.parametrize("width", [1440, 430])
@pytest.mark.parametrize("javascript_enabled", [True, False])
@pytest.mark.parametrize("unresolved", [False, True])
def test_project_handoff_disclosure_preserves_complete_selectable_prompts(
    tmp_path: Path, width: int, javascript_enabled: bool, unresolved: bool,
) -> None:
    proposal = _proposal()
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal,
        accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    if unresolved:
        payload = _package(tmp_path, decisions=[DECISION]).project_dashboard_preview
        assert all(DECISION["decision"] in row["prompt"] for row in payload["host_handoff_prompts"])
    html = render_project_html({"project_intelligence": payload})
    (tmp_path / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<style>{load_project_tab_css()}</style></head><body>{html}</body></html>',
        encoding="utf-8",
    )
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            with browser.new_context(
                viewport={"width": width, "height": 1100 if width == 1440 else 932},
                java_script_enabled=javascript_enabled,
            ) as context:
                with _new_page(context) as (page, observation):
                    page.goto(base_url + "/index.html", wait_until="domcontentloaded")
                    open_items = page.locator(".project-open-card li")
                    assert open_items.all_text_contents() == [
                        " ".join(item.split()) for item in payload["open"]
                    ]
                    assert all(item.is_visible() for item in open_items.all())
                    cards = page.locator(".project-host-prompt")
                    assert cards.count() == len(payload["host_handoff_prompts"]) == 5
                    capture = _failure_screenshot_path(f"project-handoff-{width}-js-{javascript_enabled}-unresolved-{unresolved}-closed")
                    if capture is not None:
                        capture.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(capture), full_page=True)
                    closed_height = page.locator(".project-host-handoff").bounding_box()["height"]
                    for index, row in enumerate(payload["host_handoff_prompts"]):
                        card = cards.nth(index)
                        code = card.locator("code")
                        summary = card.locator("summary")
                        assert card.locator("h4").is_visible()
                        assert card.locator("p").is_visible()
                        assert card.locator("span").filter(has_text="Produces:").is_visible()
                        assert card.locator("span").filter(has_text="Stops:").is_visible()
                        assert not code.is_visible()
                        summary.focus()
                        page.keyboard.press("Enter")
                        assert code.is_visible()
                        assert code.text_content() == row["prompt"]
                        selected = code.evaluate("""element => {
                            const range = document.createRange();
                            range.selectNodeContents(element);
                            const selection = window.getSelection();
                            selection.removeAllRanges();
                            selection.addRange(range);
                            return selection.toString();
                        }""")
                        assert selected == row["prompt"]
                        assert card.evaluate("element => element.scrollWidth <= element.clientWidth")
                        page.keyboard.press("Space")
                        assert not code.is_visible()
                    page.locator(".project-host-prompt summary").evaluate_all(
                        "elements => elements.forEach(element => element.click())"
                    )
                    open_height = page.locator(".project-host-handoff").bounding_box()["height"]
                    assert closed_height < open_height * 0.6
                    assert cards.locator("details[open]").count() == 5
                    capture = _failure_screenshot_path(f"project-handoff-{width}-js-{javascript_enabled}-unresolved-{unresolved}")
                    if capture is not None:
                        capture.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(capture), full_page=True)
                    _assert_clean_page(page, observation)

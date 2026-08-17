"""Headless browser proof for generated greenfield governance surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.parse import urlparse

from local_release_smoke import _serve_directory


BROWSER_SURFACE_PROOF_SCOPE = "per_case_headless_generated_surface_state_matrix"
BROWSER_PROJECT_MOBILE_VIEWPORT = {"width": 430, "height": 932}
BROWSER_SURFACE_EXPECTATIONS = (
    ("radar", "#frame-radar", "h1", "Backlog Workstream Radar"),
    ("registry", "#frame-registry", "h1", "Component Registry"),
    ("casebook", "#frame-casebook", ".hero-title", "Casebook"),
    ("atlas", "#frame-atlas", "h1", "Atlas"),
    ("compass", "#frame-compass", "h1", "Executive Compass"),
)


def browser_runtime_preflight_issues() -> tuple[str, ...]:
    """Verify that the exact proof interpreter can launch Chromium."""

    try:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore[import-not-found]
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - environment-dependent release proof
        return (f"Playwright is unavailable for browser surface proof: {type(exc).__name__}: {exc}",)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except PlaywrightError as exc:
        return (f"browser surface proof failed to launch Chromium during preflight: {exc}",)
    return ()


def browser_surface_proof_issues(*, repo_root: Path, timeout_ms: int = 15000) -> tuple[str, ...]:
    """Return browser-level generated-surface state issues for a generated repo."""

    try:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore[import-not-found]
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - environment-dependent release proof
        return (f"Playwright is unavailable for browser surface proof: {type(exc).__name__}: {exc}",)

    root = Path(repo_root).expanduser().resolve()
    server, base_url = _serve_directory(root)
    issues: list[str] = []
    try:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(viewport={"width": 1440, "height": 1100})
                    try:
                        issues.extend(
                            _project_generated_state_issues(
                                context=context,
                                base_url=base_url,
                                timeout_ms=timeout_ms,
                            )
                        )
                        for tab, frame_selector, heading_selector, heading_text in BROWSER_SURFACE_EXPECTATIONS:
                            issues.extend(
                                _route_surface_issues(
                                    context=context,
                                    base_url=base_url,
                                    tab=tab,
                                    frame_selector=frame_selector,
                                    heading_selector=heading_selector,
                                    heading_text=heading_text,
                                    timeout_ms=timeout_ms,
                                )
                            )
                        issues.extend(
                            _atlas_generated_state_issues(
                                context=context,
                                base_url=base_url,
                                timeout_ms=timeout_ms,
                            )
                        )
                        issues.extend(
                            _invalid_route_recovery_issues(
                                context=context,
                                base_url=base_url,
                                timeout_ms=timeout_ms,
                            )
                        )
                        issues.extend(
                            _empty_filter_state_issues(
                                context=context,
                                base_url=base_url,
                                timeout_ms=timeout_ms,
                            )
                        )
                    finally:
                        context.close()
                    mobile_context = browser.new_context(viewport=BROWSER_PROJECT_MOBILE_VIEWPORT)
                    try:
                        issues.extend(
                            f"mobile viewport: {issue}"
                            for issue in _project_generated_state_issues(
                                context=mobile_context,
                                base_url=base_url,
                                timeout_ms=timeout_ms,
                            )
                        )
                    finally:
                        mobile_context.close()
                finally:
                    browser.close()
        except PlaywrightError as exc:
            issues.append(f"browser surface proof failed to launch or run Chromium: {exc}")
    finally:
        server.shutdown()
        server.server_close()
    return tuple(dict.fromkeys(issue for issue in issues if str(issue).strip()))


def _route_surface_issues(
    *,
    context: Any,
    base_url: str,
    tab: str,
    frame_selector: str,
    heading_selector: str,
    heading_text: str,
    timeout_ms: int,
) -> tuple[str, ...]:
    issues: list[str] = []
    page, runtime_issues = _new_page(context, issue_prefix=f"browser surface {tab}")
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab={tab}", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append(f"browser surface {tab} did not load shell route")
            return tuple(issues)
        page.locator(f"#tab-{tab}").wait_for(timeout=timeout_ms)
        if page.locator(f"#tab-{tab}").get_attribute("aria-selected") != "true":
            issues.append(f"browser surface {tab} did not select its shell tab")
        page.frame_locator(frame_selector).locator(heading_selector, has_text=heading_text).wait_for(timeout=timeout_ms)
    except Exception as exc:
        issues.append(f"browser surface {tab} failed routed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _project_generated_state_issues(*, context: Any, base_url: str, timeout_ms: int) -> tuple[str, ...]:
    page, runtime_issues = _new_page(context, issue_prefix="browser surface project generated state")
    issues: list[str] = []
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab=project", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append("browser surface project did not load shell route")
            return tuple(issues)
        page.locator("#tab-project").wait_for(timeout=timeout_ms)
        if page.locator("#tab-project").get_attribute("aria-selected") != "true":
            issues.append("browser surface project did not select its shell tab")
        page.locator("#pane-project .project-surface").wait_for(timeout=timeout_ms)
        page.locator("#pane-project .project-product-story").wait_for(timeout=timeout_ms)
        page.locator("#pane-project .project-host-handoff").wait_for(timeout=timeout_ms)
        project_state = page.locator("#pane-project").evaluate(
            """(node) => {
                const prompts = Array.from(node.querySelectorAll(".project-host-prompt"));
                const promptRows = prompts.map((item) => ({
                  step_id: String(item.dataset.stepId || "").trim(),
                  label: String(item.querySelector("h4")?.innerText || "").trim(),
                  when: String(item.querySelector("p")?.innerText || "").trim(),
                  prompt: String(item.querySelector("code")?.innerText || "").trim(),
                  result: String(
                    item.querySelector(".project-host-prompt-result")?.innerText || ""
                  ).replace(/^Produces:\\s*/, "").trim(),
                  stop: String(
                    item.querySelector(".project-host-prompt-stop")?.innerText || ""
                  ).replace(/^Stops:\\s*/, "").trim()
                }));
                const storyBodies = Array.from(node.querySelectorAll(".project-story-contract-card p"))
                  .map((item) => String(item.innerText || "").trim())
                  .filter(Boolean);
                const storyRows = Array.from(node.querySelectorAll(".project-story-contract-card"))
                  .map((item) => ({
                    label: String(item.querySelector("h3")?.innerText || "").trim(),
                    semantic_slot: String(item.dataset.semanticSlot || "").trim(),
                    body: String(item.querySelector("p")?.innerText || "").trim()
                  }))
                  .filter((item) => item.label || item.body);
                const clippedText = Array.from(
                  node.querySelectorAll("h1, h2, h3, h4, p, li, td, th, code, strong, span")
                ).filter((item) => {
                  let current = item;
                  while (current && node.contains(current)) {
                    const style = window.getComputedStyle(current);
                    if (style.display === "none" || style.visibility === "hidden") return false;
                    const clipsX = style.overflowX === "hidden" || style.overflowX === "clip";
                    const clipsY = style.overflowY === "hidden" || style.overflowY === "clip";
                    const lineClamp = Number.parseInt(style.webkitLineClamp || "0", 10);
                    if ((clipsX && current.scrollWidth > current.clientWidth + 1)
                      || (clipsY && current.scrollHeight > current.clientHeight + 1)
                      || lineClamp > 0) return true;
                    current = current.parentElement;
                  }
                  return false;
                });
                const text = String(node.innerText || "");
                return {
                  promptCount: prompts.length,
                  promptRows,
                  storyBodyCount: storyBodies.length,
                  distinctStoryBodyCount: new Set(
                    storyBodies.map((body) => body.toLocaleLowerCase())
                  ).size,
                  storyRows,
                  clippedTextCount: clippedText.length,
                  hasPromptGrid: Boolean(node.querySelector(".project-host-prompt-grid")),
                  hasBlankState: text.includes("Project not defined yet"),
                  maxPromptOverflow: prompts.reduce(
                    (max, card) => Math.max(max, card.scrollWidth - card.clientWidth),
                    0
                  ),
                  paneOverflow: node.scrollWidth - node.clientWidth
                };
            }"""
        )
        payload_state = page.evaluate(
            """() => {
                const payload = window.__ODYLITH_TOOLING_DATA__ || {};
                const project = payload && payload.project_intelligence || {};
                const prompts = Array.isArray(project.host_handoff_prompts)
                  ? project.host_handoff_prompts
                  : [];
                const storyRows = project && project.product_story
                  && Array.isArray(project.product_story.release_contract)
                  ? project.product_story.release_contract
                  : [];
                return {
                  origin: project && project.projection && project.projection.origin || "",
                  promptCount: prompts.length,
                  emptyPrompts: prompts.filter((row) => !String(row && row.prompt || "").trim()).length,
                  promptRows: prompts,
                  storyRows
                };
            }"""
        )
        issues.extend(
            _project_state_assertion_issues(
                payload_origin=str(payload_state.get("origin", "") if isinstance(payload_state, dict) else ""),
                payload_prompt_count=int(payload_state.get("promptCount", 0) if isinstance(payload_state, dict) else 0),
                empty_payload_prompts=int(payload_state.get("emptyPrompts", 0) if isinstance(payload_state, dict) else 0),
                rendered_prompt_count=int(project_state.get("promptCount", 0) if isinstance(project_state, dict) else 0),
                has_prompt_grid=bool(project_state.get("hasPromptGrid", False) if isinstance(project_state, dict) else False),
                has_blank_state=bool(project_state.get("hasBlankState", False) if isinstance(project_state, dict) else False),
                max_prompt_overflow=int(project_state.get("maxPromptOverflow", 0) if isinstance(project_state, dict) else 0),
                pane_overflow=int(project_state.get("paneOverflow", 0) if isinstance(project_state, dict) else 0),
                clipped_text_count=int(
                    project_state.get("clippedTextCount", 0) if isinstance(project_state, dict) else 0
                ),
                rendered_story_rows=(
                    project_state.get("storyRows", ()) if isinstance(project_state, dict) else ()
                ),
                payload_story_rows=(
                    payload_state.get("storyRows", ()) if isinstance(payload_state, dict) else ()
                ),
                rendered_prompt_rows=(
                    project_state.get("promptRows", ()) if isinstance(project_state, dict) else ()
                ),
                payload_prompt_rows=(
                    payload_state.get("promptRows", ()) if isinstance(payload_state, dict) else ()
                ),
            )
        )
    except Exception as exc:
        issues.append(f"browser surface project generated state failed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _project_state_assertion_issues(
    *,
    payload_origin: str,
    payload_prompt_count: int,
    empty_payload_prompts: int,
    rendered_prompt_count: int,
    has_prompt_grid: bool,
    has_blank_state: bool,
    max_prompt_overflow: int,
    pane_overflow: int,
    clipped_text_count: int = 0,
    rendered_story_rows: Any = (),
    payload_story_rows: Any = (),
    rendered_prompt_rows: Any = (),
    payload_prompt_rows: Any = (),
) -> tuple[str, ...]:
    issues: list[str] = []
    if payload_origin != "accepted greenfield project":
        issues.append("browser surface project payload is not accepted greenfield project state")
    if payload_prompt_count < 1:
        issues.append("browser surface project payload exposes no graph-bound handoff prompts")
    if empty_payload_prompts:
        issues.append("browser surface project payload contains empty implementation prompt text")
    if rendered_prompt_count < 1:
        issues.append("browser surface project rendered no graph-bound handoff prompt cards")
    if not has_prompt_grid:
        issues.append("browser surface project did not render the implementation prompt grid")
    if has_blank_state:
        issues.append("browser surface project rendered the blank project state after commit-only create")
    rendered_prompts = _typed_prompt_rows(rendered_prompt_rows)
    payload_prompts = _typed_prompt_rows(payload_prompt_rows)
    if rendered_prompts != payload_prompts:
        issues.append("browser surface project handoff prompts drift from the accepted typed dashboard")
    prompt_ids = [row[0] for row in payload_prompts]
    if len(set(prompt_ids)) != len(prompt_ids):
        issues.append("browser surface project repeats a typed handoff prompt step")
    if any(not field for row in payload_prompts for field in row):
        issues.append("browser surface project contains an incomplete typed handoff prompt")
    if max_prompt_overflow > 4:
        issues.append("browser surface project implementation prompt cards overflow their containers")
    if pane_overflow > 4:
        issues.append("browser surface project pane overflows horizontally")
    rendered = _typed_story_rows(rendered_story_rows)
    payload = _typed_story_rows(payload_story_rows)
    if rendered != payload:
        issues.append("browser surface project story cards drift from the accepted typed dashboard")
    required_slots = {"workflow_facts", "visible_outputs", "component_boundaries"}
    observed_slots = {row[1] for row in payload}
    if not required_slots <= observed_slots:
        issues.append("browser surface project omits required typed graph story cards")
    if len(observed_slots) != len(payload):
        issues.append("browser surface project repeats a typed graph story card")
    if any(not row[2] for row in payload):
        issues.append("browser surface project contains an empty typed graph story card")
    if clipped_text_count:
        issues.append("browser surface project clips visible text")
    return tuple(issues)


def _typed_story_rows(value: Any) -> tuple[tuple[str, str, str], ...]:
    rows = value if isinstance(value, (list, tuple)) else ()
    return tuple(
        (
            str(row.get("label") or "").strip().casefold(),
            str(row.get("semantic_slot") or "").strip(),
            str(row.get("body") or "").strip(),
        )
        for row in rows
        if isinstance(row, dict)
    )


def _typed_prompt_rows(value: Any) -> tuple[tuple[str, str, str, str, str, str], ...]:
    rows = value if isinstance(value, (list, tuple)) else ()
    return tuple(
        (
            str(row.get("step_id") or "").strip(),
            str(row.get("label") or "").strip(),
            str(row.get("when") or "").strip(),
            str(row.get("prompt") or "").strip(),
            str(row.get("result") or "").strip(),
            str(row.get("stop") or row.get("stop_condition") or "").strip(),
        )
        for row in rows
        if isinstance(row, dict)
    )


def _invalid_route_recovery_issues(*, context: Any, base_url: str, timeout_ms: int) -> tuple[str, ...]:
    issues: list[str] = []
    issues.extend(
        _active_selection_recovery_issues(
            context=context,
            base_url=f"{base_url}/odylith/index.html?tab=radar&workstream=B-999999",
            surface="radar invalid workstream",
            frame_selector="#frame-radar",
            active_selector="button[data-idea-id].active",
            active_attribute="data-idea-id",
            invalid_value="B-999999",
            detail_selector='#detail [data-kpi="workstream-id"] .v',
            timeout_ms=timeout_ms,
        )
    )
    issues.extend(
        _active_selection_recovery_issues(
            context=context,
            base_url=f"{base_url}/odylith/index.html?tab=registry&component=does-not-exist",
            surface="registry invalid component",
            frame_selector="#frame-registry",
            active_selector="button[data-component].active",
            active_attribute="data-component",
            invalid_value="does-not-exist",
            detail_selector="#detail .component-name",
            timeout_ms=timeout_ms,
        )
    )
    issues.extend(_atlas_invalid_route_issues(context=context, base_url=base_url, timeout_ms=timeout_ms))
    issues.extend(_casebook_invalid_route_issues(context=context, base_url=base_url, timeout_ms=timeout_ms))
    issues.extend(_compass_invalid_route_issues(context=context, base_url=base_url, timeout_ms=timeout_ms))
    issues.extend(_unknown_tab_recovery_issues(context=context, base_url=base_url, timeout_ms=timeout_ms))
    return tuple(issues)


def _active_selection_recovery_issues(
    *,
    context: Any,
    base_url: str,
    surface: str,
    frame_selector: str,
    active_selector: str,
    active_attribute: str,
    invalid_value: str,
    detail_selector: str,
    timeout_ms: int,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(context, issue_prefix=f"browser surface {surface}")
    issues: list[str] = []
    try:
        response = page.goto(base_url, wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append(f"browser surface {surface} did not load invalid route")
            return tuple(issues)
        frame = page.frame_locator(frame_selector)
        frame.locator(active_selector).wait_for(timeout=timeout_ms)
        active = str(frame.locator(active_selector).first.get_attribute(active_attribute) or "").strip()
        if not active or active.lower() == invalid_value.lower():
            issues.append(f"browser surface {surface} did not recover to a valid selection")
        frame.locator(detail_selector).wait_for(timeout=timeout_ms)
    except Exception as exc:
        issues.append(f"browser surface {surface} failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _casebook_invalid_route_issues(*, context: Any, base_url: str, timeout_ms: int) -> tuple[str, ...]:
    page, runtime_issues = _new_page(context, issue_prefix="browser surface casebook invalid bug")
    issues: list[str] = []
    try:
        response = page.goto(
            f"{base_url}/odylith/index.html?tab=casebook&bug=missing-bug-route",
            wait_until="domcontentloaded",
        )
        if response is None or not response.ok:
            issues.append("browser surface casebook invalid bug did not load invalid route")
            return tuple(issues)
        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=timeout_ms)
        if casebook.locator("button.bug-row").count() > 0:
            casebook.locator("button.bug-row.active").wait_for(timeout=timeout_ms)
            active = str(
                casebook.locator("button.bug-row.active").first.get_attribute("data-bug") or ""
            ).strip()
            if not active or active == "missing-bug-route":
                issues.append("browser surface casebook invalid bug did not recover to a valid selection")
            casebook.locator("#detailPane .detail-title").wait_for(timeout=timeout_ms)
        else:
            casebook.locator("#listMeta", has_text="0 visible").wait_for(timeout=timeout_ms)
            casebook.locator("#detailPane", has_text="Select a different filter").wait_for(timeout=timeout_ms)
    except Exception as exc:
        issues.append(f"browser surface casebook invalid bug failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _atlas_generated_state_issues(*, context: Any, base_url: str, timeout_ms: int) -> tuple[str, ...]:
    page, runtime_issues = _new_page(context, issue_prefix="browser surface atlas generated state")
    issues: list[str] = []
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append("browser surface atlas generated state did not load shell route")
            return tuple(issues)
        frame = _content_frame(page=page, frame_selector="#frame-atlas", timeout_ms=timeout_ms)
        if frame is None:
            issues.append("browser surface atlas generated state did not expose iframe content")
            return tuple(issues)
        frame.locator("button[data-diagram]").first.wait_for(timeout=timeout_ms)
        frame.locator(".diagram-item.active button[data-diagram]").first.wait_for(timeout=timeout_ms)
        frame.locator("#viewerImage[src]").first.wait_for(timeout=timeout_ms)
        frame.wait_for_function(
            """() => {
                const image = document.querySelector("#viewerImage");
                return Boolean(image && image.getAttribute("src") && image.complete);
            }""",
            timeout=timeout_ms,
        )
        active_button = frame.locator(".diagram-item.active button[data-diagram]").first
        image_state = frame.locator("#viewerImage").first.evaluate(
            """(image) => ({
                loaded: Boolean(image.complete && (image.naturalWidth || image.naturalHeight)),
                src: String(image.currentSrc || image.src || "")
            })"""
        )
        issues.extend(
            _atlas_state_assertion_issues(
                diagram_count=frame.locator("button[data-diagram]").count(),
                stat_total_text=str(frame.locator("#statTotal").inner_text(timeout=timeout_ms)),
                active_diagram=str(active_button.get_attribute("data-diagram") or ""),
                displayed_diagram=str(frame.locator("#diagramId").inner_text(timeout=timeout_ms)),
                displayed_title=str(frame.locator("#diagramTitle").inner_text(timeout=timeout_ms)),
                image_src=str(image_state.get("src", "") if isinstance(image_state, dict) else ""),
                image_loaded=bool(image_state.get("loaded", False) if isinstance(image_state, dict) else False),
            )
        )
    except Exception as exc:
        issues.append(f"browser surface atlas generated state failed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _atlas_invalid_route_issues(*, context: Any, base_url: str, timeout_ms: int) -> tuple[str, ...]:
    page, runtime_issues = _new_page(context, issue_prefix="browser surface atlas invalid diagram")
    issues: list[str] = []
    invalid_diagram = "D-999999"
    try:
        response = page.goto(
            f"{base_url}/odylith/index.html?tab=atlas&diagram={invalid_diagram}",
            wait_until="domcontentloaded",
        )
        if response is None or not response.ok:
            issues.append("browser surface atlas invalid diagram did not load invalid route")
            return tuple(issues)
        frame = _content_frame(page=page, frame_selector="#frame-atlas", timeout_ms=timeout_ms)
        if frame is None:
            issues.append("browser surface atlas invalid diagram did not expose iframe content")
            return tuple(issues)
        frame.locator("button[data-diagram]").first.wait_for(timeout=timeout_ms)
        frame.locator("#diagramId").wait_for(timeout=timeout_ms)
        displayed = str(frame.locator("#diagramId").inner_text(timeout=timeout_ms)).strip()
        if not displayed or displayed.upper() == invalid_diagram:
            issues.append("browser surface atlas invalid diagram did not recover to a valid diagram")
        frame.locator("#viewerImage[src]").first.wait_for(timeout=timeout_ms)
    except Exception as exc:
        issues.append(f"browser surface atlas invalid diagram failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _compass_invalid_route_issues(*, context: Any, base_url: str, timeout_ms: int) -> tuple[str, ...]:
    page, runtime_issues = _new_page(context, issue_prefix="browser surface compass invalid query")
    issues: list[str] = []
    try:
        response = page.goto(
            f"{base_url}/odylith/index.html?tab=compass&scope=B-999999&window=999h&date=tomorrow",
            wait_until="domcontentloaded",
        )
        if response is None or not response.ok:
            issues.append("browser surface compass invalid query did not load invalid route")
            return tuple(issues)
        compass = page.frame_locator("#frame-compass")
        compass.locator("h1", has_text="Executive Compass").wait_for(timeout=timeout_ms)
        compass.locator("#scope-pill", has_text="Global").wait_for(timeout=timeout_ms)
        compass.locator("button[data-window].active").first.wait_for(timeout=timeout_ms)
    except Exception as exc:
        issues.append(f"browser surface compass invalid query failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _unknown_tab_recovery_issues(*, context: Any, base_url: str, timeout_ms: int) -> tuple[str, ...]:
    page, runtime_issues = _new_page(context, issue_prefix="browser shell unknown tab")
    issues: list[str] = []
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab=radar", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append("browser shell unknown tab could not load Radar for a recovery token")
            return tuple(issues)
        radar = page.frame_locator("#frame-radar")
        radar.locator("button[data-idea-id].active").wait_for(timeout=timeout_ms)
        active = str(radar.locator("button[data-idea-id].active").first.get_attribute("data-idea-id") or "").strip()
        if not active:
            issues.append("browser shell unknown tab could not derive a Radar recovery token")
            return tuple(issues)
        response = page.goto(
            f"{base_url}/odylith/index.html?tab=missing-surface&workstream={quote(active, safe='')}",
            wait_until="domcontentloaded",
        )
        if response is None or not response.ok:
            issues.append("browser shell unknown tab did not load")
            return tuple(issues)
        page.locator("#tab-radar").wait_for(timeout=timeout_ms)
        if page.locator("#tab-radar").get_attribute("aria-selected") != "true":
            issues.append("browser shell unknown tab did not recover to Radar")
        page.frame_locator("#frame-radar").locator("h1", has_text="Backlog Workstream Radar").wait_for(
            timeout=timeout_ms
        )
        page.frame_locator("#frame-radar").locator(
            '#detail [data-kpi="workstream-id"] .v',
            has_text=active,
        ).wait_for(timeout=timeout_ms)
    except Exception as exc:
        issues.append(f"browser shell unknown tab failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _empty_filter_state_issues(*, context: Any, base_url: str, timeout_ms: int) -> tuple[str, ...]:
    page, runtime_issues = _new_page(context, issue_prefix="browser surface casebook empty filter")
    issues: list[str] = []
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append("browser surface casebook empty filter did not load")
            return tuple(issues)
        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=timeout_ms)
        casebook.locator("#searchInput").fill("zzzzzz-no-casebook-match")
        casebook.locator("#listMeta", has_text="0 visible").wait_for(timeout=timeout_ms)
        casebook.locator("#detailPane", has_text="Select a different filter").wait_for(timeout=timeout_ms)
    except Exception as exc:
        issues.append(f"browser surface casebook empty filter failed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _content_frame(*, page: Any, frame_selector: str, timeout_ms: int) -> Any | None:
    frame_element = page.locator(frame_selector).element_handle(timeout=timeout_ms)
    if frame_element is None:
        return None
    return frame_element.content_frame()


def _atlas_state_assertion_issues(
    *,
    diagram_count: int,
    stat_total_text: str,
    active_diagram: str,
    displayed_diagram: str,
    displayed_title: str,
    image_src: str,
    image_loaded: bool,
) -> tuple[str, ...]:
    issues: list[str] = []
    if diagram_count <= 0:
        issues.append("browser surface atlas rendered no generated diagram buttons")
    stat_total = _non_negative_int(stat_total_text)
    if stat_total <= 0:
        issues.append("browser surface atlas rendered no generated diagram count")
    elif diagram_count > 0 and stat_total != diagram_count:
        issues.append("browser surface atlas generated diagram count disagrees with rendered list")
    active = str(active_diagram or "").strip()
    displayed = str(displayed_diagram or "").strip()
    if not active:
        issues.append("browser surface atlas has no active generated diagram")
    if not displayed:
        issues.append("browser surface atlas did not hydrate the selected diagram id")
    elif active and displayed.upper() != active.upper():
        issues.append("browser surface atlas selected diagram id disagrees with active list state")
    if len(str(displayed_title or "").strip().split()) < 2:
        issues.append("browser surface atlas did not hydrate a meaningful generated diagram title")
    parsed = urlparse(str(image_src or ""))
    if "/odylith/atlas/source/" not in (parsed.path or "") or not (parsed.path or "").endswith((".svg", ".png")):
        issues.append("browser surface atlas viewer did not load a generated diagram asset")
    if not image_loaded:
        issues.append("browser surface atlas generated diagram asset did not finish loading")
    return tuple(issues)


def _non_negative_int(value: str) -> int:
    try:
        number = int(str(value or "").strip())
    except ValueError:
        return 0
    return max(0, number)


def _new_page(context: Any, *, issue_prefix: str) -> tuple[Any, Any]:
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []
    bad_responses: list[str] = []

    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on("requestfailed", lambda request: _record_request_failure(request, failed_requests))
    page.on("response", lambda response: _record_bad_response(response, bad_responses))

    def _runtime_issues() -> tuple[str, ...]:
        issues: list[str] = []
        issues.extend(f"{issue_prefix} console error: {message}" for message in console_errors)
        issues.extend(f"{issue_prefix} page error: {message}" for message in page_errors)
        issues.extend(f"{issue_prefix} request failed: {message}" for message in failed_requests)
        issues.extend(f"{issue_prefix} bad response: {message}" for message in bad_responses)
        return tuple(issues)

    return page, _runtime_issues


def _record_request_failure(request: Any, failed_requests: list[str]) -> None:
    url = str(getattr(request, "url", "") or "")
    if not url or url.startswith(("about:", "data:", "blob:")):
        return
    failure = getattr(request, "failure", None)
    failure_payload = failure() if callable(failure) else {}
    error_text = str(failure_payload.get("errorText", "") if isinstance(failure_payload, dict) else "").strip()
    resource_type = str(getattr(request, "resource_type", "") or "").strip().lower()
    if _is_expected_local_abort(url=url, error_text=error_text, resource_type=resource_type):
        return
    failed_requests.append(f"{request.method} {url} {error_text}".strip())


def _record_bad_response(response: Any, bad_responses: list[str]) -> None:
    url = str(getattr(response, "url", "") or "")
    if not url.startswith("http://127.0.0.1:"):
        return
    status = int(getattr(response, "status", 0) or 0)
    if status >= 400:
        bad_responses.append(f"{status} {url}")


def _is_expected_local_abort(*, url: str, error_text: str, resource_type: str) -> bool:
    lowered = error_text.lower()
    if "abort" not in lowered and "err_aborted" not in lowered:
        return False
    parsed = urlparse(url)
    path = parsed.path or ""
    if parsed.hostname != "127.0.0.1" or not path.startswith("/odylith/"):
        return False
    if resource_type == "document" and path.endswith(".html"):
        return True
    if path.startswith("/odylith/compass/runtime/") and path.endswith((".json", ".js")):
        return True
    detail_markers = (
        "/backlog-detail-shard-",
        "/backlog-document-shard-",
        "/registry-detail-shard-",
        "/casebook-detail-shard-",
    )
    return path.endswith(".v1.js") and any(marker in path for marker in detail_markers)


__all__ = [
    "BROWSER_SURFACE_EXPECTATIONS",
    "BROWSER_SURFACE_PROOF_SCOPE",
    "browser_surface_proof_issues",
]

"""Headless browser proof for generated greenfield governance surfaces."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from greenfield_browser_authored_contract import (
    prove_authored_event_disclosure,
    atlas_degraded_state_assertion_issues as _atlas_degraded_state_assertion_issues,
    atlas_diagram_coverage_issues as _atlas_diagram_coverage_issues,
    atlas_error_state_assertion_issues as _atlas_error_state_assertion_issues,
    atlas_state_assertion_issues as _atlas_state_assertion_issues,
)
from greenfield_browser_authored_contract import (
    expected_proof_card,
    generated_tree_path_leak_issues as _generated_tree_path_leak_issues,
    project_state_assertion_issues as _project_state_assertion_issues,
    project_story_binding_issues as _project_story_binding_issues,
    story_rows_match_payload,
)
from greenfield_browser_capture import capture_state_screenshot as _capture_state_screenshot
from greenfield_browser_atlas_readability import prove_atlas_native_reading
from greenfield_browser_layout import layout_assertion_issues as _layout_assertion_issues
from greenfield_browser_layout import layout_issues as _layout_issues
from greenfield_browser_selection_proof import prove_clicked_selection, prove_missing_selection, reveal_selection_detail, wait_for_selection_route
from local_release_smoke import _serve_directory

BROWSER_SURFACE_PROOF_SCOPE = "per_case_headless_generated_surface_state_matrix"
BROWSER_VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1100},
    "mobile": {"width": 430, "height": 932},
}
BROWSER_PROJECT_MOBILE_VIEWPORT = BROWSER_VIEWPORTS["mobile"]
BROWSER_SURFACE_EXPECTATIONS = (
    ("radar", "#frame-radar", "h1", "Backlog Workstream Radar"),
    ("registry", "#frame-registry", "h1", "Component Registry"),
    ("casebook", "#frame-casebook", ".hero-title", "Casebook"),
    ("atlas", "#frame-atlas", "h1", "Atlas"),
    ("compass", "#frame-compass", "h1", "Executive Compass"),
)
BROWSER_REQUIRED_SURFACE_STATES = {
    "project": ("normal", "degraded"),
    "radar": ("normal", "empty", "degraded", "invalid-recovery"),
    "registry": ("normal", "empty", "degraded", "invalid-recovery"),
    "casebook": ("normal", "empty", "invalid-recovery"),
    "atlas": ("normal", "degraded", "error", "invalid-recovery"),
    "compass": ("normal", "degraded", "invalid-recovery"),
    "shell": ("normal", "invalid-recovery"),
}
BROWSER_REQUIRED_COVERAGE = frozenset(
    (viewport, surface, state)
    for viewport in BROWSER_VIEWPORTS
    for surface, states in BROWSER_REQUIRED_SURFACE_STATES.items()
    for state in states
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
            try:
                for viewport_name, viewport in BROWSER_VIEWPORTS.items():
                    context = browser.new_context(
                        viewport=viewport,
                        has_touch=viewport_name == "mobile",
                        is_mobile=viewport_name == "mobile",
                    )
                    context.close()
            finally:
                browser.close()
    except PlaywrightError as exc:
        return (f"browser surface proof failed to launch Chromium during preflight: {exc}",)
    return ()


def browser_surface_proof_issues(
    *,
    repo_root: Path,
    timeout_ms: int = 15000,
    screenshot_output_dir: Path | None = None,
) -> tuple[str, ...]:
    """Return browser-level generated-surface state issues for a generated repo."""

    root = Path(repo_root).expanduser().resolve()
    path_issues = _generated_tree_path_leak_issues(root)
    try:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore[import-not-found]
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - environment-dependent release proof
        return (*path_issues, f"Playwright is unavailable for browser surface proof: {type(exc).__name__}: {exc}")

    server, base_url = _serve_directory(root)
    issues: list[str] = list(path_issues)
    covered: set[tuple[str, str, str]] = set()
    if screenshot_output_dir is None:
        issues.append("browser surface proof requires a retained screenshot output directory")
    try:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    for viewport_name, viewport in BROWSER_VIEWPORTS.items():
                        context = browser.new_context(
                            viewport=viewport,
                            has_touch=viewport_name == "mobile",
                            is_mobile=viewport_name == "mobile",
                        )
                        try:
                            viewport_issues = _viewport_surface_issues(
                                context=context,
                                base_url=base_url,
                                viewport=viewport_name,
                                timeout_ms=timeout_ms,
                                screenshot_output_dir=screenshot_output_dir,
                                covered=covered,
                            )
                            issues.extend(f"{viewport_name} viewport: {issue}" for issue in viewport_issues)
                        finally:
                            context.close()
                finally:
                    browser.close()
        except PlaywrightError as exc:
            issues.append(f"browser surface proof failed to launch or run Chromium: {exc}")
    finally:
        server.shutdown()
        server.server_close()
    issues.extend(_missing_coverage_issues(covered))
    return tuple(dict.fromkeys(issue for issue in issues if str(issue).strip()))


def _viewport_surface_issues(
    *,
    context: Any,
    base_url: str,
    viewport: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None,
    covered: set[tuple[str, str, str]],
) -> tuple[str, ...]:
    issues: list[str] = []
    issues.extend(
        _project_generated_state_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cells=((viewport, "project", "normal"), (viewport, "shell", "normal")),
            covered=covered,
        )
    )
    issues.extend(_project_degraded_state_issues(
        context=context, base_url=base_url, timeout_ms=timeout_ms,
        screenshot_output_dir=screenshot_output_dir,
        coverage_cell=(viewport, "project", "degraded"), covered=covered,
    ))
    for tab, frame_selector, heading_selector, heading_text in BROWSER_SURFACE_EXPECTATIONS:
        if tab == "atlas":
            continue
        issues.extend(
            _route_surface_issues(
                context=context,
                base_url=base_url,
                tab=tab,
                frame_selector=frame_selector,
                heading_selector=heading_selector,
                heading_text=heading_text,
                timeout_ms=timeout_ms,
                screenshot_output_dir=screenshot_output_dir,
                coverage_cell=(viewport, tab, "normal"),
                covered=covered,
            )
        )
    issues.extend(
        _atlas_generated_state_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "atlas", "normal"),
            covered=covered,
        )
    )
    issues.extend(
        _atlas_generated_state_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "atlas", "error"),
            covered=covered,
            degrade_svg=True,
            fail_png=True,
        )
    )
    issues.extend(
        _atlas_generated_state_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "atlas", "degraded"),
            covered=covered,
            degrade_svg=True,
        )
    )
    issues.extend(
        _invalid_route_recovery_issues(
            context=context,
            base_url=base_url,
            viewport=viewport,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            covered=covered,
        )
    )
    issues.extend(
        _empty_filter_state_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "casebook", "empty"),
            covered=covered,
        )
    )
    for surface, frame_selector, heading, query, empty, rows, shard in (
        ("radar", "#frame-radar", "Backlog Workstream Radar", "#query", "#detail-empty[role='status']", "button[data-idea-id]", "**/backlog-detail-shard-*.v1.js"),
        ("registry", "#frame-registry", "Component Registry", "#search", "#detail .empty[role='status']", "button[data-component]", "**/registry-detail-shard-*.v1.js"),
    ):
        issues.extend(_surface_variant_issues(
            context=context, base_url=base_url, surface=surface, frame_selector=frame_selector,
            heading=heading, query_selector=query, empty_selector=empty,
            row_selector=rows, shard_pattern=shard, state="empty", timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, surface, "empty"), covered=covered,
        ))
        issues.extend(_surface_variant_issues(
            context=context, base_url=base_url, surface=surface, frame_selector=frame_selector,
            heading=heading, query_selector=query, empty_selector=empty,
            row_selector=rows, shard_pattern=shard, state="degraded", timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, surface, "degraded"), covered=covered,
        ))
    issues.extend(_compass_degraded_state_issues(
        context=context, base_url=base_url, timeout_ms=timeout_ms,
        screenshot_output_dir=screenshot_output_dir,
        coverage_cell=(viewport, "compass", "degraded"), covered=covered,
    ))
    return tuple(issues)


def _missing_coverage_issues(covered: set[tuple[str, str, str]]) -> tuple[str, ...]:
    return tuple(
        f"browser surface proof skipped required coverage cell: {'/'.join(cell)}"
        for cell in sorted(BROWSER_REQUIRED_COVERAGE - covered)
    )


def _project_degraded_state_issues(
    *, context: Any, base_url: str, timeout_ms: int, screenshot_output_dir: Path | None,
    coverage_cell: tuple[str, str, str], covered: set[tuple[str, str, str]] | None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context, issue_prefix="browser surface project degraded state",
        screenshot_output_dir=screenshot_output_dir, coverage_cells=(coverage_cell,), covered=covered,
    )
    issues: list[str] = []
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab=project", wait_until="domcontentloaded")
        if response is None or not response.ok:
            return ("browser surface project degraded state did not load",)
        _dismiss_shell_obstructions(page)
        page.locator("#pane-project .project-surface").wait_for(timeout=timeout_ms)
        page.locator("#pane-project .project-open-questions").evaluate_all("nodes => nodes.forEach(node => {node.open = true;})")
        state = page.locator("#pane-project").evaluate(
            """node => {
              const project = window.__ODYLITH_TOOLING_DATA__?.project_intelligence || {};
              const authored = Object.hasOwn(project, "authored_facts");
              const visible = selector => [...node.querySelectorAll(selector)].filter(n => n.getClientRects().length).map(n => n.innerText.trim()).join(" ");
              const signals = authored ? [...(project.delta || []), ...(project.contradictions || []), ...(project.degraded_state || [])] : (project.degraded_state || []);
              const rows = [...signals, ...(authored ? [project.current, project.trust_note, ...(project.open || []), ...(project.blockers || []).map(row => row[0])] : [])]
                .map(value => String(value || "").trim()).filter(value => value && !value.startsWith("No degraded source condition"));
              return {rows, text: String(node.innerText || ""), authored,
                expected: [project.current || "", project.trust_note || ""],
                visible: [visible(".project-hero .project-status"), visible(".project-trust .project-panel-head p")]};
            }"""
        )
        rows = state.get("rows", []) if isinstance(state, dict) else []
        text = str(state.get("text", "") if isinstance(state, dict) else "")
        if not rows or any(str(row) not in text for row in rows):
            issues.append("browser surface project does not visibly explain its degraded proof boundary")
        if isinstance(state, dict) and state.get("authored") and (not all(state.get("expected", [])) or state.get("visible") != state.get("expected")):
            issues.append("browser surface project does not visibly preserve its exact status and evidence boundary")
        issues.extend(_layout_issues(page.locator("body"), label="project degraded state"))
    except Exception as exc:
        issues.append(f"browser surface project degraded state failed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _surface_variant_issues(
    *, context: Any, base_url: str, surface: str, frame_selector: str, heading: str,
    query_selector: str, empty_selector: str, row_selector: str, shard_pattern: str,
    state: str, timeout_ms: int, screenshot_output_dir: Path | None,
    coverage_cell: tuple[str, str, str], covered: set[tuple[str, str, str]] | None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context, issue_prefix=f"browser surface {surface} {state} state",
        screenshot_output_dir=screenshot_output_dir, coverage_cells=(coverage_cell,), covered=covered,
    )
    issues: list[str] = []
    try:
        if state == "degraded":
            global_name = "__ODYLITH_BACKLOG_DETAIL_SHARDS__" if surface == "radar" else "__ODYLITH_REGISTRY_DETAIL_SHARDS__"
            page.route(shard_pattern, lambda route: route.fulfill(
                status=200, content_type="application/javascript",
                body=f'window["{global_name}"] = window["{global_name}"] || {{}};',
            ))
        response = page.goto(f"{base_url}/odylith/index.html?tab={surface}", wait_until="domcontentloaded")
        if response is None or not response.ok:
            return (f"browser surface {surface} {state} state did not load",)
        _dismiss_shell_obstructions(page)
        frame = page.frame_locator(frame_selector)
        frame.locator("h1", has_text=heading).wait_for(timeout=timeout_ms)
        if state == "empty":
            frame.locator(query_selector).fill("zzzzzz-no-generated-surface-match")
            status = frame.locator(empty_selector)
            status.wait_for(state="visible", timeout=timeout_ms)
            if frame.locator(f"{row_selector}:visible").count() or len(status.inner_text().split()) < 3:
                issues.append(f"browser surface {surface} does not expose an explanatory empty state")
        else:
            status = frame.locator("#detail [role='status']")
            status.wait_for(state="visible", timeout=timeout_ms)
            if "unavailable" not in status.inner_text().casefold():
                issues.append(f"browser surface {surface} does not explain degraded detail availability")
        issues.extend(_layout_issues(frame.locator("body"), label=f"{surface} {state} state"))
    except Exception as exc:
        issues.append(f"browser surface {surface} {state} state failed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _compass_degraded_state_issues(
    *, context: Any, base_url: str, timeout_ms: int, screenshot_output_dir: Path | None,
    coverage_cell: tuple[str, str, str], covered: set[tuple[str, str, str]] | None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context, issue_prefix="browser surface compass degraded state",
        screenshot_output_dir=screenshot_output_dir, coverage_cells=(coverage_cell,), covered=covered,
    )
    issues: list[str] = []
    try:
        page.route("**/compass/runtime/current.v1.js*", lambda route: route.fulfill(
            status=200, content_type="application/javascript", body="window.__ODYLITH_COMPASS_RUNTIME__ = null;",
        ))
        page.route("**/compass/runtime/current.v1.json*", lambda route: route.fulfill(
            status=200, content_type="application/json", body="null",
        ))
        response = page.goto(f"{base_url}/odylith/index.html?tab=compass", wait_until="domcontentloaded")
        if response is None or not response.ok:
            return ("browser surface compass degraded state did not load",)
        _dismiss_shell_obstructions(page)
        frame = page.frame_locator("#frame-compass")
        fallback = frame.locator("#kpi-grid", has_text="Runtime Unavailable")
        fallback.wait_for(timeout=timeout_ms)
        frame.locator("#digest-list", has_text="Current information is unavailable").wait_for(timeout=timeout_ms)
        issues.extend(_layout_issues(frame.locator("body"), label="compass degraded state"))
    except Exception as exc:
        issues.append(f"browser surface compass degraded state failed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _route_surface_issues(
    *,
    context: Any,
    base_url: str,
    tab: str,
    frame_selector: str,
    heading_selector: str,
    heading_text: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cell: tuple[str, str, str] = ("desktop", "radar", "normal"),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
    issues: list[str] = []
    page, runtime_issues = _new_page(
        context,
        issue_prefix=f"browser surface {tab}",
        screenshot_output_dir=screenshot_output_dir,
        coverage_cells=(coverage_cell,),
        covered=covered,
    )
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab={tab}", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append(f"browser surface {tab} did not load shell route")
            return tuple(issues)
        _dismiss_shell_obstructions(page)
        page.locator(f"#tab-{tab}").wait_for(timeout=timeout_ms)
        if page.locator(f"#tab-{tab}").get_attribute("aria-selected") != "true":
            issues.append(f"browser surface {tab} did not select its shell tab")
        frame = page.frame_locator(frame_selector)
        frame.locator(heading_selector, has_text=heading_text).wait_for(timeout=timeout_ms)
        issues.extend(_layout_issues(page.locator("body"), label="tooling shell"))
        issues.extend(_layout_issues(frame.locator("body"), label=tab))
    except Exception as exc:
        issues.append(f"browser surface {tab} failed routed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _project_generated_state_issues(
    *,
    context: Any,
    base_url: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cells: tuple[tuple[str, str, str], ...] = (("desktop", "project", "normal"),),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context,
        issue_prefix="browser surface project generated state",
        screenshot_output_dir=screenshot_output_dir,
        coverage_cells=coverage_cells,
        covered=covered,
    )
    issues: list[str] = []
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab=project", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append("browser surface project did not load shell route")
            return tuple(issues)
        _dismiss_shell_obstructions(page)
        page.locator("#tab-project").wait_for(timeout=timeout_ms)
        if page.locator("#tab-project").get_attribute("aria-selected") != "true":
            issues.append("browser surface project did not select its shell tab")
        page.locator("#pane-project .project-surface").wait_for(timeout=timeout_ms)
        page.locator("#pane-project .project-product-story").wait_for(timeout=timeout_ms)
        handoff = page.locator("#pane-project .project-host-handoff")
        if handoff.evaluate("node => node.tagName === 'DETAILS'", timeout=timeout_ms):
            if handoff.get_attribute("open") is not None or handoff.locator(".project-host-prompt-grid").is_visible():
                issues.append("browser surface project implementation details are not initially compact and closed")
            handoff.locator(":scope > summary").focus()
            page.keyboard.press("Enter")
        issues.extend(_layout_issues(page.locator("body"), label="tooling shell"))
        project_state = page.locator("#pane-project").evaluate(
            """(node) => {
                const prompts = Array.from(node.querySelectorAll(".project-host-prompt"));
                const storyBodies = Array.from(node.querySelectorAll(".project-story-contract-body"))
                  .map((item) => String(item.innerText || "").trim())
                  .filter(Boolean);
                const storyRows = Array.from(node.querySelectorAll(".project-story-contract-card"))
                  .map((item) => ({
                    label: String(item.querySelector("h3")?.innerText || "").trim(),
                    semantic_slot: String(item.dataset.semanticSlot || "").trim(),
                    body: String(item.querySelector(".project-story-contract-body")?.innerText || "").trim()
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
                const projectPayload = (window.__ODYLITH_TOOLING_DATA__ || {}).project_intelligence || {};
                const expectedPromptLabels = (Array.isArray(projectPayload.host_handoff_prompts)
                  ? projectPayload.host_handoff_prompts
                  : [])
                  .map((row) => String(row && row.label || "").trim())
                  .filter(Boolean);
                return {
                  promptCount: prompts.length,
                  storyBodyCount: storyBodies.length,
                  distinctStoryBodyCount: new Set(
                    storyBodies.map((body) => body.toLocaleLowerCase())
                  ).size,
                  storyRows,
                  clippedTextCount: clippedText.length,
                  hasPromptGrid: Boolean(node.querySelector(".project-host-prompt-grid")),
                  hasBlankState: text.includes("Project not defined yet"),
                  hasImplementationPrompts: expectedPromptLabels.length >= 5
                    && expectedPromptLabels.every((label) => text.includes(label)),
                  maxPromptOverflow: prompts.reduce(
                    (max, card) => Math.max(max, card.scrollWidth - card.clientWidth),
                    0
                  ),
                  paneOverflow: node.scrollWidth - node.clientWidth
                };
            }"""
        )
        authored_structure, disclosure_issues = prove_authored_event_disclosure(page.locator("#pane-project"), timeout_ms=timeout_ms)
        issues.extend(disclosure_issues)
        payload_state = page.evaluate(
            """() => {
                const payload = window.__ODYLITH_TOOLING_DATA__ || {};
                const project = payload && payload.project_intelligence || {};
                const prompts = Array.isArray(project.host_handoff_prompts)
                  ? project.host_handoff_prompts
                  : [];
                return {
                  origin: project && project.projection && project.projection.origin || "",
                  promptCount: prompts.length,
                  emptyPrompts: prompts.filter((row) => !String(row && row.prompt || "").trim()).length,
                  storyRows: project && project.product_story
                    && Array.isArray(project.product_story.release_contract)
                    ? project.product_story.release_contract
                    : [],
                  authoredFacts: project && project.authored_facts || {}
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
                has_implementation_prompts=bool(
                    project_state.get("hasImplementationPrompts", False) if isinstance(project_state, dict) else False
                ),
                max_prompt_overflow=int(project_state.get("maxPromptOverflow", 0) if isinstance(project_state, dict) else 0),
                pane_overflow=int(project_state.get("paneOverflow", 0) if isinstance(project_state, dict) else 0),
                rendered_story_body_count=int(
                    project_state.get("storyBodyCount", 0) if isinstance(project_state, dict) else 0
                ),
                distinct_story_body_count=int(
                    project_state.get("distinctStoryBodyCount", 0) if isinstance(project_state, dict) else 0
                ),
                clipped_text_count=int(
                    project_state.get("clippedTextCount", 0) if isinstance(project_state, dict) else 0
                ),
                story_rows=(
                    project_state.get("storyRows", ()) if isinstance(project_state, dict) else ()
                ),
                payload_story_rows=(
                    payload_state.get("storyRows", ()) if isinstance(payload_state, dict) else ()
                ),
                authored_structure=authored_structure,
                payload_authored_facts=(
                    payload_state.get("authoredFacts", {}) if isinstance(payload_state, dict) else {}
                ),
            )
        )
    except Exception as exc:
        issues.append(f"browser surface project generated state failed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _invalid_route_recovery_issues(
    *,
    context: Any,
    base_url: str,
    viewport: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
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
            detail_attribute="", query_key="workstream", empty_selector='#detail-empty[role="status"]',
            empty_heading="No matching workstreams",
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "radar", "invalid-recovery"),
            covered=covered,
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
            detail_selector="#detail:has(.component-name)", detail_attribute="data-selected-component",
            query_key="component", empty_selector='#detail .empty[role="status"]',
            empty_heading="No matching components",
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "registry", "invalid-recovery"),
            covered=covered,
        )
    )
    issues.extend(
        _atlas_invalid_route_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "atlas", "invalid-recovery"),
            covered=covered,
        )
    )
    issues.extend(
        _casebook_invalid_route_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "casebook", "invalid-recovery"),
            covered=covered,
        )
    )
    issues.extend(
        _compass_invalid_route_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "compass", "invalid-recovery"),
            covered=covered,
        )
    )
    issues.extend(
        _unknown_tab_recovery_issues(
            context=context,
            base_url=base_url,
            timeout_ms=timeout_ms,
            screenshot_output_dir=screenshot_output_dir,
            coverage_cell=(viewport, "shell", "invalid-recovery"),
            covered=covered,
        )
    )
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
    detail_attribute: str,
    query_key: str,
    empty_selector: str,
    empty_heading: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cell: tuple[str, str, str] = ("desktop", "radar", "invalid-recovery"),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context,
        issue_prefix=f"browser surface {surface}",
        screenshot_output_dir=screenshot_output_dir,
        coverage_cells=(coverage_cell,),
        covered=covered,
    )
    issues: list[str] = []
    try:
        response = page.goto(base_url, wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append(f"browser surface {surface} did not load invalid route")
            return tuple(issues)
        _dismiss_shell_obstructions(page)
        frame = page.frame_locator(frame_selector)
        issues.extend(prove_missing_selection(
            page=page, frame=frame, query_key=query_key, invalid=invalid_value,
            active_selector=active_selector, empty_selector=empty_selector,
            empty_heading=empty_heading, timeout_ms=timeout_ms,
        ))
        issues.extend(prove_clicked_selection(
            page=page, frame=frame, query_key=query_key, active_selector=active_selector,
            active_attribute=active_attribute, detail_selector=detail_selector,
            detail_attribute=detail_attribute, timeout_ms=timeout_ms,
        ))
        issues.extend(_layout_issues(page.locator("body"), label="tooling shell"))
        issues.extend(_layout_issues(frame.locator("body"), label=coverage_cell[1]))
    except Exception as exc:
        issues.append(f"browser surface {surface} failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _casebook_invalid_route_issues(
    *,
    context: Any,
    base_url: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cell: tuple[str, str, str] = ("desktop", "casebook", "invalid-recovery"),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context, issue_prefix="browser surface casebook invalid bug",
        screenshot_output_dir=screenshot_output_dir, coverage_cells=(coverage_cell,), covered=covered,
    )
    issues: list[str] = []
    try:
        response = page.goto(
            f"{base_url}/odylith/index.html?tab=casebook&bug=missing-bug-route", wait_until="domcontentloaded",
        )
        if response is None or not response.ok:
            issues.append("browser surface casebook invalid bug did not load invalid route")
            return tuple(issues)
        _dismiss_shell_obstructions(page)
        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=timeout_ms)
        if casebook.locator("button.bug-row").count() > 0:
            issues.extend(prove_missing_selection(
                page=page, frame=casebook, query_key="bug", invalid="missing-bug-route",
                active_selector="button.bug-row.active", empty_selector="#detailPane [role='status']",
                empty_heading="The requested bug is unavailable", timeout_ms=timeout_ms,
            ))
            issues.extend(prove_clicked_selection(
                page=page, frame=casebook, query_key="bug", active_selector="button.bug-row.active",
                active_attribute="data-bug",
                detail_selector="#detailPane [data-summary-field='Bug ID'] .summary-fact-value",
                detail_attribute="", timeout_ms=timeout_ms,
            ))
        else:
            empty_status = casebook.locator("#detailPane [role='status']")
            empty_status.wait_for(timeout=timeout_ms)
            if len(str(empty_status.inner_text(timeout=timeout_ms)).split()) < 3:
                issues.append("browser surface casebook invalid route does not explain its empty recovery")
        issues.extend(_layout_issues(page.locator("body"), label="tooling shell"))
        issues.extend(_layout_issues(casebook.locator("body"), label="casebook"))
    except Exception as exc:
        issues.append(f"browser surface casebook invalid bug failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _atlas_generated_state_issues(
    *,
    context: Any,
    base_url: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cell: tuple[str, str, str] = ("desktop", "atlas", "normal"),
    covered: set[tuple[str, str, str]] | None = None,
    degrade_svg: bool = False,
    fail_png: bool = False,
    initial_diagram: str = "",
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context,
        issue_prefix="browser surface atlas generated state",
        screenshot_output_dir=screenshot_output_dir,
        coverage_cells=(coverage_cell,),
        covered=covered,
    )
    issues: list[str] = []
    try:
        if degrade_svg:
            page.route(
                "**/odylith/atlas/source/*.svg",
                lambda route: route.fulfill(
                    status=200,
                    content_type="image/svg+xml",
                    body="<svg",
                ),
            )
        if fail_png:
            page.route(
                "**/odylith/atlas/source/*.png",
                lambda route: route.fulfill(status=200, content_type="image/png", body="broken"),
            )
        selected = f"&diagram={quote(initial_diagram)}" if initial_diagram else ""
        response = page.goto(
            f"{base_url}/odylith/index.html?tab=atlas{selected}", wait_until="domcontentloaded"
        )
        if response is None or not response.ok:
            issues.append("browser surface atlas generated state did not load shell route")
            return tuple(issues)
        _dismiss_shell_obstructions(page)
        frame = _content_frame(page=page, frame_selector="#frame-atlas", timeout_ms=timeout_ms)
        if frame is None:
            issues.append("browser surface atlas generated state did not expose iframe content")
            return tuple(issues)
        buttons = frame.locator("button[data-diagram]")
        buttons.first.wait_for(timeout=timeout_ms)
        if initial_diagram:
            issues.extend(prove_missing_selection(
                page=page, frame=frame, query_key="diagram", invalid=initial_diagram,
                active_selector=".diagram-item.active button[data-diagram]",
                empty_selector="#atlasEmptyState", timeout_ms=timeout_ms,
                empty_heading="No matching diagrams",
            ))
        diagram_count = buttons.count()
        expected_diagrams: list[str] = []
        visited_diagrams: list[str] = []
        for index in range(diagram_count):
            button = buttons.nth(index)
            expected = str(button.get_attribute("data-diagram") or "").strip()
            expected_diagrams.append(expected)
            button.click()
            frame.wait_for_function(
                """(diagramId) => String(document.querySelector("#diagramId")?.textContent || "").trim().toUpperCase() === diagramId.toUpperCase()""",
                arg=expected,
                timeout=timeout_ms,
            )
            active_button = frame.locator(".diagram-item.active button[data-diagram]").first
            wait_for_selection_route(page, "diagram", expected, timeout_ms)
            displayed = str(frame.locator("#diagramId").inner_text(timeout=timeout_ms)).strip()
            visited_diagrams.append(displayed)
            if fail_png:
                error = frame.locator("#viewerAssetError").first
                error.wait_for(state="visible", timeout=timeout_ms)
                error_state = error.evaluate(
                    """(alert) => ({
                        role: alert.getAttribute("role") || "",
                        text: alert.textContent || "",
                        visible: !alert.hidden,
                        imageHidden: Boolean(document.querySelector("#viewerImage")?.hidden)
                    })"""
                )
                issues.extend(
                    _atlas_error_state_assertion_issues(
                        alert_text=str(error_state.get("text", "")),
                        alert_role=str(error_state.get("role", "")),
                        alert_visible=bool(error_state.get("visible", False)),
                        image_hidden=bool(error_state.get("imageHidden", False)),
                    )
                )
                continue
            frame.wait_for_function(
                """() => {
                    const image = document.querySelector("#viewerImage");
                    return Boolean(image && image.complete && (image.naturalWidth || image.naturalHeight));
                }""",
                timeout=timeout_ms,
            )
            image_state = frame.locator("#viewerImage").first.evaluate(
                """(image) => ({
                    fallbackApplied: image.dataset.fallbackApplied === "1",
                    loaded: Boolean(image.complete && (image.naturalWidth || image.naturalHeight)),
                    src: String(image.currentSrc || image.src || "")
                })"""
            )
            issues.extend(
                _atlas_state_assertion_issues(
                    diagram_count=diagram_count,
                    stat_total_text=str(frame.locator("#statTotal").inner_text(timeout=timeout_ms)),
                    active_diagram=str(active_button.get_attribute("data-diagram") or ""),
                    displayed_diagram=displayed,
                    displayed_title=str(frame.locator("#diagramTitle").inner_text(timeout=timeout_ms)),
                    image_src=str(image_state.get("src", "") if isinstance(image_state, dict) else ""),
                    image_loaded=bool(image_state.get("loaded", False) if isinstance(image_state, dict) else False),
                )
            )
            issues.extend(
                prove_atlas_native_reading(
                    page=page,
                    frame=frame,
                    expected_diagram=expected,
                    timeout_ms=timeout_ms,
                    screenshot_output_dir=screenshot_output_dir,
                    coverage_cell=coverage_cell,
                )
            )
            if degrade_svg:
                issues.extend(
                    _atlas_degraded_state_assertion_issues(
                        image_src=str(image_state.get("src", "") if isinstance(image_state, dict) else ""),
                        image_loaded=bool(image_state.get("loaded", False) if isinstance(image_state, dict) else False),
                        fallback_applied=bool(
                            image_state.get("fallbackApplied", False)
                            if isinstance(image_state, dict)
                            else False
                        ),
                    )
                )
        issues.extend(_atlas_diagram_coverage_issues(expected_diagrams, visited_diagrams))
        issues.extend(_layout_issues(page.locator("body"), label="tooling shell"))
        issues.extend(_layout_issues(frame.locator("body"), label="atlas"))
    except Exception as exc:
        issues.append(f"browser surface atlas generated state failed render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _atlas_invalid_route_issues(
    *,
    context: Any,
    base_url: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cell: tuple[str, str, str] = ("desktop", "atlas", "invalid-recovery"),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
    return _atlas_generated_state_issues(
        context=context,
        base_url=base_url,
        timeout_ms=timeout_ms,
        screenshot_output_dir=screenshot_output_dir,
        coverage_cell=coverage_cell,
        covered=covered,
        initial_diagram="D-999999",
    )


def _compass_invalid_route_issues(
    *,
    context: Any,
    base_url: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cell: tuple[str, str, str] = ("desktop", "compass", "invalid-recovery"),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context,
        issue_prefix="browser surface compass invalid query",
        screenshot_output_dir=screenshot_output_dir,
        coverage_cells=(coverage_cell,),
        covered=covered,
    )
    issues: list[str] = []
    try:
        response = page.goto(
            f"{base_url}/odylith/index.html?tab=compass&scope=B-999999&window=999h&date=tomorrow",
            wait_until="domcontentloaded",
        )
        if response is None or not response.ok:
            issues.append("browser surface compass invalid query did not load invalid route")
            return tuple(issues)
        _dismiss_shell_obstructions(page)
        compass = page.frame_locator("#frame-compass")
        compass.locator("h1", has_text="Executive Compass").wait_for(timeout=timeout_ms)
        compass.locator("#scope-pill", has_text="Global").wait_for(timeout=timeout_ms)
        compass.locator("button[data-window].active").first.wait_for(timeout=timeout_ms)
        issues.extend(_layout_issues(page.locator("body"), label="tooling shell"))
        issues.extend(_layout_issues(compass.locator("body"), label="compass"))
    except Exception as exc:
        issues.append(f"browser surface compass invalid query failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _unknown_tab_recovery_issues(
    *,
    context: Any,
    base_url: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cell: tuple[str, str, str] = ("desktop", "shell", "invalid-recovery"),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context,
        issue_prefix="browser shell unknown tab",
        screenshot_output_dir=screenshot_output_dir,
        coverage_cells=(coverage_cell,),
        covered=covered,
    )
    issues: list[str] = []
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab=radar", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append("browser shell unknown tab could not load Radar for a recovery token")
            return tuple(issues)
        _dismiss_shell_obstructions(page)
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
        _dismiss_shell_obstructions(page)
        page.locator("#tab-radar").wait_for(timeout=timeout_ms)
        if page.locator("#tab-radar").get_attribute("aria-selected") != "true":
            issues.append("browser shell unknown tab did not recover to Radar")
        page.frame_locator("#frame-radar").locator("h1", has_text="Backlog Workstream Radar").wait_for(
            timeout=timeout_ms
        )
        reveal_selection_detail(page.frame_locator("#frame-radar").locator(
            '#detail [data-kpi="workstream-id"] .v', has_text=active,
        ), timeout_ms=timeout_ms)
        issues.extend(_layout_issues(page.locator("body"), label="tooling shell"))
    except Exception as exc:
        issues.append(f"browser shell unknown tab failed recovery render: {type(exc).__name__}: {exc}")
    finally:
        issues.extend(runtime_issues())
        page.close()
    return tuple(issues)


def _empty_filter_state_issues(
    *,
    context: Any,
    base_url: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None = None,
    coverage_cell: tuple[str, str, str] = ("desktop", "casebook", "empty"),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[str, ...]:
    page, runtime_issues = _new_page(
        context,
        issue_prefix="browser surface casebook empty filter",
        screenshot_output_dir=screenshot_output_dir,
        coverage_cells=(coverage_cell,),
        covered=covered,
    )
    issues: list[str] = []
    try:
        response = page.goto(f"{base_url}/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
        if response is None or not response.ok:
            issues.append("browser surface casebook empty filter did not load")
            return tuple(issues)
        _dismiss_shell_obstructions(page)
        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=timeout_ms)
        casebook.locator("#searchInput").fill("zzzzzz-no-casebook-match")
        casebook.locator("#listMeta").wait_for(timeout=timeout_ms)
        casebook.locator("#detailPane [role='status']").wait_for(timeout=timeout_ms)
        if casebook.locator("button.bug-row:visible").count():
            issues.append("browser surface casebook empty filter still renders matching entries")
        empty_copy = str(casebook.locator("#detailPane [role='status']").inner_text(timeout=timeout_ms)).strip()
        if len(empty_copy.split()) < 3:
            issues.append("browser surface casebook empty filter does not explain the empty state")
        issues.extend(_layout_issues(page.locator("body"), label="tooling shell"))
        issues.extend(_layout_issues(casebook.locator("body"), label="casebook"))
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


def _dismiss_shell_obstructions(page: Any) -> None:
    """Expose the selected surface before layout checks and retained screenshots."""

    page.wait_for_load_state("networkidle")
    for selector in ("#upgradeSpotlightDismiss", "#welcomeDismiss", "#gridBriefClose", "#odylithClose"):
        control = page.locator(selector)
        if control.count() and control.first.is_visible():
            control.first.click()


def _new_page(
    context: Any,
    *,
    issue_prefix: str,
    screenshot_output_dir: Path | None = None,
    screenshot_name: str = "",
    coverage_cells: tuple[tuple[str, str, str], ...] = (),
    covered: set[tuple[str, str, str]] | None = None,
) -> tuple[Any, Any]:
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
        if screenshot_output_dir is not None:
            names = tuple("-".join(cell) for cell in coverage_cells) or (screenshot_name,)
            for name in names:
                try:
                    _capture_state_screenshot(
                        page=page,
                        output_dir=screenshot_output_dir,
                        state_name=name,
                    )
                except Exception as exc:
                    issues.append(f"{issue_prefix} screenshot capture failed: {type(exc).__name__}: {exc}")
                    continue
                if covered is not None:
                    covered.update(cell for cell in coverage_cells if "-".join(cell) == name)
        elif coverage_cells:
            issues.append(f"{issue_prefix} has no retained screenshot destination")
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


__all__ = ["BROWSER_REQUIRED_COVERAGE", "BROWSER_REQUIRED_SURFACE_STATES", "BROWSER_SURFACE_EXPECTATIONS", "BROWSER_SURFACE_PROOF_SCOPE", "BROWSER_VIEWPORTS", "browser_surface_proof_issues"]

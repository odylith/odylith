from __future__ import annotations

from odylith.runtime.surfaces import compass_dashboard_frontend_contract
from odylith.runtime.surfaces import compass_dashboard_shell


def test_render_shell_references_split_compass_assets_and_inline_bootstrap() -> None:
    html = compass_dashboard_shell._render_shell_html(  # noqa: SLF001
        payload={
            "brand_head_html": "<meta name='application-name' content='Odylith' />",
            "base_style_href": "compass-style-base.v1.css",
            "execution_wave_style_href": "compass-style-execution-waves.v1.css",
            "surface_style_href": "compass-style-surface.v1.css",
            "shared_js_href": "compass-shared.v1.js",
            "state_js_href": "compass-state.v1.js",
            "summary_js_href": "compass-summary.v1.js",
            "timeline_js_href": "compass-timeline.v1.js",
            "waves_js_href": "compass-waves.v1.js",
            "workstreams_js_href": "compass-workstreams.v1.js",
            "ui_runtime_js_href": "compass-ui-runtime.v1.js",
            "runtime_js_href": "runtime/current.v1.js",
        }
    )

    assert '<link rel="stylesheet" href="compass-style-base.v1.css" />' in html
    assert '<link rel="stylesheet" href="compass-style-execution-waves.v1.css" />' in html
    assert '<link rel="stylesheet" href="compass-style-surface.v1.css" />' in html
    assert '<script src="compass-shared.v1.js"></script>' in html
    assert '<script src="compass-state.v1.js"></script>' in html
    assert '<script src="compass-summary.v1.js"></script>' in html
    assert '<script src="compass-timeline.v1.js"></script>' in html
    assert '<script src="compass-waves.v1.js"></script>' in html
    assert '<script src="compass-workstreams.v1.js"></script>' in html
    assert '<script src="compass-ui-runtime.v1.js"></script>' in html
    assert '<script src="runtime/current.v1.js"></script>' in html
    assert "Delivery Posture and Risk Brief" in html
    assert "Current workstream direction, risks, and runtime evidence across Radar, plans, bugs, and Atlas traceability." in html
    assert "Repo-Aware Generated View" not in html
    assert 'const SHELL = JSON.parse(document.getElementById("compassShellData").textContent);' in html
    assert 'window.__ODYLITH_COMPASS_SHELL__ = SHELL && typeof SHELL === "object" ? SHELL : {};' in html
    assert "init();" in html


def test_shared_compass_asset_preserves_legacy_digest_fallback_logic() -> None:
    shared_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-shared.v1.js")
    summary_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-summary.v1.js")

    assert 'const hasScopedSelection = WORKSTREAM_RE.test(String(state && state.workstream ? state.workstream : "").trim());' in shared_js
    assert 'if (hasScopedSelection && scopedReady) return scopedReady;' in shared_js
    assert 'if (globalReady && (globalReadySource === "provider" || globalReadySource === "cache")) return globalReady;' in shared_js
    assert 'if (globalReady) return globalReady;' in shared_js
    assert 'if (hasScopedSelection && scopedBrief) return scopedBrief;' in shared_js
    assert 'if (scopedReady && (scopedReadySource === "provider" || scopedReadySource === "cache")) return scopedReady;' in shared_js
    assert 'if (scopedReady) return scopedReady;' in shared_js
    assert 'if (legacyLines.length) {' in shared_js
    assert 'return legacyDigestToBrief(legacyLines, payload && payload.generated_utc);' in shared_js
    assert 'source === "provider" || source === "cache" || source === "deterministic"' in summary_js
    assert "Deterministic local brief" in summary_js
    assert "No critical blended risks in current payload." not in summary_js
    assert "No validated AI-authored standup brief is available for this view." not in summary_js
    assert "No validated narrative bullets available for this section." not in summary_js
    assert "No standup brief available for this view." not in summary_js
    assert 'return String(value ?? "")' in shared_js


def test_workstream_and_registry_links_stay_cross_surface_and_without_footer_actions() -> None:
    workstreams_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-workstreams.v1.js")

    assert 'const radarHref = `../index.html?tab=radar&workstream=${encodeURIComponent(item.ideaId)}`;' in workstreams_js
    assert '<td class="ws-col-id"><a class="ws-id-btn" href="${escapeHtml(radarHref)}" target="_top" data-ws-id="${escapeHtml(item.ideaId)}"' in workstreams_js
    assert 'workstreamTooltipAttrs(item.ideaId, workstreamTitles, `Open radar for ${item.ideaId}`)' in workstreams_js
    assert 'const componentHref = `../index.html?tab=registry&component=${encodeURIComponent(item.component_id)}`;' in workstreams_js
    assert '<strong>Registry components:</strong> ${registryComponentLinks}' in workstreams_js
    assert '<a class="chip chip-link" href="${escapeHtml(componentHref)}" target="_top"${registryComponentTooltipAttrs(item, `Open registry for ${item.component_id}`)}>${escapeHtml(item.component_id)}</a>' in workstreams_js
    assert 'registryComponents.map((item) => `${item.name} (${item.component_id})`).join(", ")' not in workstreams_js
    assert '<div class="ws-links">' not in workstreams_js
    assert '>Compass Scope</a>' not in workstreams_js
    assert '>Radar</a>' not in workstreams_js
    assert '>Atlas</a>' not in workstreams_js
    assert '>Plan</a>' not in workstreams_js


def test_summary_and_timeline_assets_preserve_risk_and_component_spec_context() -> None:
    summary_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-summary.v1.js")
    timeline_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-timeline.v1.js")

    assert 'riskRows.bugs.length + riskRows.selfHost.length + riskRows.traceCritical.length + riskRows.stale.length' in summary_js
    assert 'consumerTruthRoots().component_specs' in timeline_js
    assert 'consumerTruthRoots().runbooks' in timeline_js
    assert 'file.startsWith("odylith/registry/source/components/") && file.endsWith("/CURRENT_SPEC.md")' in timeline_js
    assert 'return `Why now: ${toSentence(clipFocusText(whyText, 220))}`;' in timeline_js
    assert 'return `Target outcome: ${toSentence(clipFocusText(proposedSolution, 230))}`;' in timeline_js
    assert 'return "Target outcome: make the expanded Timeline Audit card explain intent, the change summary, and implementation evidence in a stable order.";' in timeline_js
    assert 'return "Reordered and relabeled the expanded audit card so it opens with Intent, then Summary of Change, then Implemented.";' in timeline_js
    assert 'return "Reordered and relabeled the expanded audit card so it now reads Intent, Summary of Change, Implemented, and then Files.";' in timeline_js
    assert 'return "Closed the loop between plan state and rendered dashboards so the visible lifecycle state matches the source change.";' in timeline_js
    assert 'return "Scope note: this transaction captures the checkpoint and propagates evidence; it is not the runtime cutover itself.";' in timeline_js
    assert "Intent pressure:" not in timeline_js
    assert 'sections.push({ title: "Summary", items: identityItems });' not in timeline_js
    assert 'sections.push({ title: "Intent", items: intentItems });' in timeline_js
    assert 'sections.push({ title: "Summary of Change", items: summarySectionItems });' in timeline_js
    assert 'sections.push({ title: "Context", items: contextItems });' not in timeline_js
    intent_idx = timeline_js.index('sections.push({ title: "Intent", items: intentItems });')
    summary_idx = timeline_js.index('sections.push({ title: "Summary of Change", items: summarySectionItems });')
    implemented_idx = timeline_js.index('sections.push({ title: "Implemented", items: implementedItems });')
    assert intent_idx < summary_idx < implemented_idx

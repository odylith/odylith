from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import compass_dashboard_frontend_contract
from odylith.runtime.surfaces import compass_dashboard_shell
from odylith.runtime.surfaces import dashboard_ui_primitives


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_render_shell_references_split_compass_assets_and_inline_bootstrap() -> None:
    html = compass_dashboard_shell._render_shell_html(  # noqa: SLF001
        payload={
            "brand_head_html": "<meta name='application-name' content='Odylith' />",
            "base_style_href": "compass-style-base.v1.css",
            "execution_wave_style_href": "compass-style-execution-waves.v1.css",
            "surface_style_href": "compass-style-surface.v1.css",
            "shared_js_href": "compass-shared.v1.js",
            "runtime_truth_js_href": "compass-runtime-truth.v1.js",
            "state_js_href": "compass-state.v1.js",
            "summary_js_href": "compass-summary.v1.js",
            "timeline_js_href": "compass-timeline.v1.js",
            "waves_js_href": "compass-waves.v1.js",
            "releases_js_href": "compass-releases.v1.js",
            "workstreams_js_href": "compass-workstreams.v1.js",
            "ui_runtime_js_href": "compass-ui-runtime.v1.js",
            "runtime_js_href": "runtime/current.v1.js",
        }
    )

    assert '<link rel="stylesheet" href="compass-style-base.v1.css" />' in html
    assert '<link rel="stylesheet" href="compass-style-execution-waves.v1.css" />' in html
    assert '<link rel="stylesheet" href="compass-style-surface.v1.css" />' in html
    assert '<script src="compass-shared.v1.js"></script>' in html
    assert '<script src="compass-runtime-truth.v1.js"></script>' in html
    assert '<script src="compass-state.v1.js"></script>' in html
    assert '<script src="compass-summary.v1.js"></script>' in html
    assert '<script src="compass-timeline.v1.js"></script>' in html
    assert '<script src="compass-waves.v1.js"></script>' in html
    assert '<script src="compass-releases.v1.js"></script>' in html
    assert '<script src="compass-workstreams.v1.js"></script>' in html
    assert '<script src="compass-ui-runtime.v1.js"></script>' in html
    assert '<script src="runtime/current.v1.js"></script>' in html
    assert "Delivery Posture and Risk Brief" not in html
    assert "Current workstream direction, risks, and runtime evidence across Radar, plans, bugs, and Atlas traceability." in html
    assert 'id="release-groups-host"' in html
    assert '<div class="card-title-row standup-brief-title-row">' in html
    assert '<button class="pill subtle" id="copy-brief" type="button">Copy Brief</button>' in html
    assert '<div id="brief-copy-status" class="brief-copy-status hidden" role="status" aria-live="polite"></div>' in html
    assert html.index('<h2>Standup Brief</h2>') < html.index('id="copy-brief"')
    assert html.index('id="copy-brief"') < html.index('id="brief-copy-status"')
    assert html.index('id="brief-copy-status"') < html.index('id="digest-list"')
    assert "Repo-Aware Generated View" not in html
    assert 'const SHELL = JSON.parse(document.getElementById("compassShellData").textContent);' in html
    assert 'window.__ODYLITH_COMPASS_SHELL__ = SHELL && typeof SHELL === "object" ? SHELL : {};' in html
    assert "init();" in html


def test_shared_compass_asset_preserves_legacy_digest_fallback_logic() -> None:
    shared_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-shared.v1.js")
    runtime_truth_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-runtime-truth.v1.js")
    summary_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-summary.v1.js")
    state_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-state.v1.js")

    assert "const scopedWorkstream = WORKSTREAM_RE.test(" in shared_js
    assert "const hasScopedSelection = Boolean(scopedWorkstream);" in shared_js
    assert 'if (hasScopedSelection && scopedReady) return scopedReady;' in shared_js
    assert 'if (globalReady && (globalReadySource === "provider" || globalReadySource === "cache")) return globalReady;' in shared_js
    assert 'if (globalReady) return globalReady;' in shared_js
    assert 'if (hasScopedSelection && scopedBrief) return scopedBrief;' in shared_js
    assert 'if (scopedReady && (scopedReadySource === "provider" || scopedReadySource === "cache")) return scopedReady;' in shared_js
    assert 'if (scopedReady) return scopedReady;' in shared_js
    assert 'if (legacyLines.length) {' in shared_js
    assert 'return legacyDigestToBrief(legacyLines, payload && payload.generated_utc);' in shared_js
    assert "function radarWorkstreamHref(workstreamId, options = {})" in shared_js
    assert 'const view = String(options && options.view ? options.view : "").trim().toLowerCase();' in shared_js
    assert 'if (WORKSTREAM_RE.test(token)) params.set("workstream", token);' in shared_js
    assert 'if (view) params.set("view", view);' in shared_js
    assert 'return `../index.html?${params.toString()}`;' in shared_js
    assert 'const href = radarWorkstreamHref(ideaId, { view: "plan" });' in shared_js
    assert "async function reconcileRuntimePayloadWithSourceTruth(payload)" in runtime_truth_js
    assert "governed source-truth snapshot" in runtime_truth_js
    assert 'const sourceTruthHref = String(compassShell().source_truth_href || "").trim();' in runtime_truth_js
    assert "function sourceTruthPayloadIsUsable(sourceTruth)" in runtime_truth_js
    assert "if (!sourceTruthPayloadIsUsable(normalizedSourceTruth)) continue;" in runtime_truth_js
    assert "const historyDates = knownHistoryDateTokens(payload);" in state_js
    assert "const minDate = historyDates.length" in state_js
    assert "? historyDates[historyDates.length - 1]" in state_js
    assert 'source === "provider" || source === "cache" || source === "deterministic"' in summary_js
    assert "AI narrative · provider" not in summary_js
    assert "AI narrative · cache" not in summary_js
    assert "last known good cache" not in summary_js
    assert "Deterministic local brief" not in summary_js
    assert "No critical blended risks in current payload." not in summary_js
    assert "No validated AI-authored standup brief is available for this view." not in summary_js
    assert "No validated narrative bullets available for this section." not in summary_js
    assert "No standup brief available for this view." not in summary_js
    assert 'return String(value ?? "")' in shared_js


def test_workstream_and_registry_links_stay_cross_surface_and_without_footer_actions() -> None:
    shared_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-shared.v1.js")
    workstreams_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-workstreams.v1.js")
    releases_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-releases.v1.js")
    waves_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-waves.v1.js")
    base_template = (
        REPO_ROOT
        / "src"
        / "odylith"
        / "runtime"
        / "surfaces"
        / "templates"
        / "compass_dashboard"
        / "compass-style-base.v1.css"
    ).read_text(encoding="utf-8")

    assert "function radarWorkstreamHref(workstreamId, options = {})" in shared_js
    assert 'execution-wave-card-shell execution-wave-card-shell-full-copy' in shared_js
    assert 'const radarHref = radarWorkstreamHref(item.ideaId);' in workstreams_js
    assert '<td class="ws-col-id"><div class="ws-id-stack"><a class="ws-id-btn" href="${escapeHtml(radarHref)}" target="_top" data-ws-id="${escapeHtml(item.ideaId)}"' in workstreams_js
    assert 'workstreamTooltipAttrs(item.ideaId, workstreamTitles, `Open radar for ${item.ideaId}`)' in workstreams_js
    assert 'const componentHref = `../index.html?tab=registry&component=${encodeURIComponent(item.component_id)}`;' in workstreams_js
    assert '<strong>Registry components:</strong> ${registryComponentLinks}' in workstreams_js
    assert '<a class="chip chip-link" href="${escapeHtml(componentHref)}" target="_top"${registryComponentTooltipAttrs(item, `Open registry for ${item.component_id}`)}>${escapeHtml(item.component_id)}</a>' in workstreams_js
    assert 'registryComponents.map((item) => `${item.name} (${item.component_id})`).join(", ")' not in workstreams_js
    assert '<div class="ws-links">' not in workstreams_js
    assert '<div class="ws-id-stack"><a class="ws-id-btn"' in workstreams_js
    assert "function compassWorkstreamReleaseLabel(release)" in workstreams_js
    assert "function compassGovernanceRepresentedWorkstreamIds(payload)" in workstreams_js
    assert "executionWavePrograms(payload).forEach((program) => {" in workstreams_js
    assert "addWorkstreamRefList(release && release.active_workstreams);" in workstreams_js
    assert "addWorkstreamRefList(release && release.completed_workstreams);" in workstreams_js
    assert 'const removedSummary = `Removed from ${compassWorkstreamReleaseLabel(release)}`;' in workstreams_js
    assert 'if (WORKSTREAM_RE.test(ideaId) && status === "finished" && releaseHistorySummary === removedSummary)' in workstreams_js
    assert 'scopedRows.filter((row) => !representedIds.has(String(row && row.idea_id ? row.idea_id : "").trim()))' in workstreams_js
    assert "const rows = scopedRows;" not in workstreams_js
    assert "function numericProgressOrNull(value)" in workstreams_js
    assert '${item.releaseLabel ? `<span class="chip subtle">${escapeHtml(item.releaseLabel)}</span>` : ""}' in workstreams_js
    assert 'Release ${item.releaseLabel}' not in workstreams_js
    assert 'Release: ${escapeHtml(selected.releaseLabel)}' not in workstreams_js
    assert 'style="margin-left:8px;"' not in workstreams_js
    assert 'return radarWorkstreamHref(value);' in workstreams_js
    assert "timelineScopeHref(" not in workstreams_js
    assert "`Open scope for ${id}`" not in workstreams_js
    assert '`Open radar for ${id}`' in workstreams_js
    assert 'href="${escapeHtml(radarWorkstreamHref(id))}"' in workstreams_js
    assert '>Compass Scope</a>' not in workstreams_js
    assert '>Radar</a>' not in workstreams_js
    assert '>Atlas</a>' not in workstreams_js
    assert '>Plan</a>' not in workstreams_js
    assert "function renderReleaseGroups(payload, state)" in releases_js
    assert "<h2>Release Targets</h2>" in releases_js
    assert "Targeted Workstreams" in releases_js
    assert "Completed Workstreams" in releases_js
    assert 'group.status === "planned"' in releases_js
    assert 'group.status === "draft"' in releases_js
    assert 'return groups;' in releases_js
    assert 'const currentOnlyGroups = currentReleaseId' not in releases_js
    assert "No targeted workstreams." in releases_js
    assert "Removed from ${compassReleaseDisplayName(release)}" in releases_js
    assert "completed_workstreams" in releases_js
    assert "execution-wave-program-stack execution-wave-program-stack-release" in releases_js
    assert "function compassReleaseDisplayName(release)" in releases_js
    assert "function numericProgressOrNull(value)" in releases_js
    assert 'if (value === null || value === undefined || value === "") return null;' in releases_js
    assert "function numericProgressOrNull(value)" in waves_js
    assert '<article class="card execution-waves-card"><h2>Programs</h2><div id="execution-waves" class="muted"></div></article>' in waves_js
    assert 'if (value === null || value === undefined || value === "") return null;' in waves_js
    assert 'Object.prototype.hasOwnProperty.call(plan, "display_progress_ratio")' in waves_js
    assert '${renderMemberChip(ideaId, { selected: ideaId === scopedWorkstream })}' in releases_js
    assert '${titleChips.join("")}' in releases_js
    assert '<div class="execution-wave-member-head">' in releases_js
    assert '<div class="execution-wave-member-title-chips">' in releases_js
    assert '<div class="execution-wave-title-row">' not in releases_js
    assert 'Current Release</span>' in releases_js
    assert 'const metaChips = [' in releases_js
    assert "Release-owned targeted workstreams for this release." not in releases_js
    assert "Release-owned targeted workstreams for this selection." not in releases_js
    assert "execution-wave-focus-grid" not in releases_js
    assert 'progressLabel ? `<span class="label execution-wave-label wave-progress-chip">${escapeHtml(progressLabel)}</span>` : ""' in releases_js
    assert releases_js.index('${titleChips.join("")}') < releases_js.index('<div class="execution-wave-title">${escapeHtml(title)}</div>')
    assert releases_js.index('const metaChips = [') < releases_js.index('progressLabel ? `<span class="label execution-wave-label wave-progress-chip">${escapeHtml(progressLabel)}</span>` : ""')
    assert "execution-wave-focus-title" not in releases_js
    assert "`Open radar for ${token}`" in releases_js
    assert 'href="${escapeHtml(radarWorkstreamHref(token))}"' in releases_js
    assert "compassScopeHref(token, state)" not in releases_js
    assert "`Scope to ${token}`" not in releases_js
    assert "const progressKnown = progressRatio !== null;" in workstreams_js
    assert 'const progressLabel = String(plan && plan.display_progress_label ? plan.display_progress_label : "").trim();' in workstreams_js
    assert 'const progressCellLabel = progressKnown ? `${progressPct}%` : (progressLabel || "n/a");' in workstreams_js
    assert "All current workstreams are already represented in Programs or Release Targets." in workstreams_js
    assert "No active workstreams in this scope." in workstreams_js
    assert "`Open radar for ${token}`" in waves_js
    assert 'href="${escapeHtml(radarWorkstreamHref(token))}"' in waves_js
    assert "compassScopeHref(token, state)" not in waves_js
    assert "`Scope to ${token}`" not in waves_js
    assert 'contextChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${waveCount}-wave program`)}</span>`);' not in waves_js
    assert "const sectionChips = [];" in waves_js
    assert 'sectionChips.push(`<span class="label execution-wave-label wave-status-active">${escapeHtml(`${sectionActiveCount} active`)}</span>`);' in waves_js
    execution_wave_css = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-style-execution-waves.v1.css")
    base_css = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-style-base.v1.css")
    expected_stats_grid_css = dashboard_ui_primitives.kpi_grid_layout_css(container_selector=".stats")
    expected_stat_card_css = dashboard_ui_primitives.kpi_card_surface_css(card_selector=".stat")
    expected_stat_typography_css = dashboard_ui_primitives.governance_kpi_label_value_css(
        label_selector=".stat .kpi-label",
        value_selector=".stat .kpi-value",
    )
    expected_card_surface_css = dashboard_ui_primitives.panel_surface_css(
        selector=".card",
        padding="12px",
        radius_px=14,
        gap_px=8,
        border_color="#dbeafe",
        background="linear-gradient(180deg, #ffffff, #fbfdff)",
        shadow="0 6px 18px rgba(15, 23, 42, 0.04)",
    )
    assert "__ODYLITH_COMPASS_KPI_GRID_CONTRACT__" in base_template
    assert "__ODYLITH_COMPASS_KPI_CARD_CONTRACT__" in base_template
    assert "__ODYLITH_COMPASS_KPI_TYPOGRAPHY_CONTRACT__" in base_template
    assert "__ODYLITH_COMPASS_CARD_SURFACE_CONTRACT__" in base_template
    assert ".stats {\n  display: grid;" not in base_template
    assert ".stat {\n  border: 1px solid #dbeafe;" not in base_template
    assert ".stat .kpi-label {" not in base_template
    assert ".card {\n  border: 1px solid #dbeafe;" not in base_template
    assert ".ws-id-stack {" in base_css
    assert "width: 240px;" in base_css
    assert "__ODYLITH_COMPASS_KPI_GRID_CONTRACT__" not in base_css
    assert "__ODYLITH_COMPASS_KPI_CARD_CONTRACT__" not in base_css
    assert "__ODYLITH_COMPASS_KPI_TYPOGRAPHY_CONTRACT__" not in base_css
    assert "__ODYLITH_COMPASS_CARD_SURFACE_CONTRACT__" not in base_css
    assert expected_stats_grid_css in base_css
    assert expected_stat_card_css in base_css
    assert expected_stat_typography_css in base_css
    assert expected_card_surface_css in base_css
    assert ".card.release-groups-card .execution-wave-board {" not in base_css
    assert ".stat.stat-release-only {" not in base_css
    assert ".stat.stat-release-only .kpi-value {" not in base_css
    assert "--surface-identifier-chip-padding: 2px 10px;" in base_css
    assert "--surface-identifier-font-size: 14px;" in base_css
    assert "--surface-identifier-font-weight: 500;" in base_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING};"
    ) in base_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE};"
    ) in base_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT};"
    ) in base_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_PADDING_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_PADDING};"
    ) in base_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_SIZE_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_SIZE};"
    ) in base_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT};"
    ) in base_css
    assert ".pill, .ws-id-btn, .chip-link {" not in base_css
    assert ".pill, .chip-link:not(.workstream-id-chip):not(.execution-wave-chip-link) {" in base_css
    assert ".ws-id-btn {" in base_css
    assert ".ws-id-btn, .workstream-id-chip {" in base_css
    assert (
        "padding: "
        f"var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_PADDING_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_PADDING});"
    ) in base_css
    assert (
        "font-size: "
        f"var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_SIZE});"
    ) in base_css
    assert (
        "font-weight: "
        f"var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT});"
    ) in base_css
    assert (
        "padding: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING});"
    ) in base_css
    assert ".workstream-id-chip {" in base_css
    assert ".standup-brief-sheet {" in base_css
    assert "gap: 10px;" in base_css
    assert ".standup-brief-sections > .brief-section:first-child {" in base_css
    assert "padding-top: 4px;" in base_css
    assert (
        "font-size: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE});"
    ) in base_css
    assert (
        "font-weight: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT});"
    ) in base_css
    assert ".digest-link,\n    .brief-inline-link {" in base_css
    assert ".execution-wave-program-stack-release .execution-wave-section-title {" in execution_wave_css
    assert ".execution-wave-program-stack:not(.execution-wave-program-stack-release) .execution-wave-section {" in execution_wave_css
    assert "border-color: #dbeafe;" in execution_wave_css
    assert "background: linear-gradient(180deg, #f9fbff 0%, #ffffff 100%);" in execution_wave_css
    assert ".execution-wave-program-stack-release .execution-wave-section {" in execution_wave_css
    assert "border-color: #dbe9df;" in execution_wave_css
    assert "background: linear-gradient(180deg, #fbfdfa 0%, #ffffff 100%);" in execution_wave_css
    assert ".execution-wave-program-stack-release .execution-wave-section-toggle-triangle::before {" in execution_wave_css
    assert "border-color: transparent transparent transparent #0f766e;" in execution_wave_css
    assert ".execution-wave-program-stack-release .execution-wave-panel {" in execution_wave_css
    assert "border-color: #e2ece5;" in execution_wave_css
    assert "font-size: 14px;" in execution_wave_css
    assert ".execution-wave-program-stack-release .execution-wave-title {" in execution_wave_css
    assert "font-size: 12px;" in execution_wave_css
    assert ".execution-wave-program-stack-release .execution-wave-member-head {" in execution_wave_css
    assert ".execution-wave-program-stack-release .execution-wave-member-title-chips {" in execution_wave_css
    assert ".execution-wave-program-stack-release .execution-wave-board {" not in execution_wave_css
    assert ".execution-wave-program-stack-release .execution-wave-section-body {" in execution_wave_css
    assert ".ws-wave-chip-row {" in execution_wave_css
    assert ".card.execution-waves-card {" in base_css
    assert "border-color: #bfd5f3;" in base_css
    assert "background: linear-gradient(180deg, #edf4ff 0%, #f8fbff 100%);" in base_css
    assert ".card.release-groups-card {" in base_css
    assert "border-color: #cfe4d1;" in base_css
    assert "background: linear-gradient(180deg, #f2faf1 0%, #fbfefb 100%);" in base_css
    assert (
        "padding: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING});"
    ) in execution_wave_css
    assert (
        "font-size: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE});"
    ) in execution_wave_css
    assert (
        "font-weight: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT});"
    ) in execution_wave_css


def test_summary_and_timeline_assets_preserve_risk_and_component_spec_context() -> None:
    summary_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-summary.v1.js")
    timeline_js = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-timeline.v1.js")

    assert 'riskRows.bugs.length + riskRows.selfHost.length + riskRows.traceCritical.length + riskRows.stale.length' in summary_js
    assert 'rows.push(["Current Release", currentReleaseLabel, "stat-release-only"])' in summary_js
    assert 'rows.push(["Active Waves"' not in summary_js
    assert 'rows.push(["Next Release", nextReleaseLabel]);' not in summary_js
    assert 'rows.push([null, currentReleaseLabel, "stat-release-only"])' not in summary_js
    assert 'const nameLabel = String(releaseRow.name || "").trim();' in summary_js
    assert 'const versionLabel = String(releaseRow.version || "").trim();' in summary_js
    assert 'const tagLabel = String(releaseRow.tag || "").trim();' in summary_js
    assert 'return /^v\\d/.test(tagLabel) ? tagLabel.slice(1) : tagLabel;' in summary_js
    assert 'return versionLabel.startsWith("v") ? versionLabel : `v${versionLabel}`;' not in summary_js
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

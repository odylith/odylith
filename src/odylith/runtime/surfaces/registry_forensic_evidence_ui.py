"""Registry forensic-evidence UI snippets.

The Registry renderer owns the data payload. This module owns the lower
forensic evidence surface so the oversized renderer does not keep absorbing
event-list markup, CSS, and browser behavior.
"""

from __future__ import annotations

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import governance_surface_theme
from odylith.runtime.surfaces import registry_typography_ui


def markup() -> str:
    """Return the static forensic-evidence shell used by Registry."""

    return """
        <div id="chronology-anchor" class="timeline-head forensic-evidence-head">
          <span>Forensic Evidence</span>
          <span id="timelineCount">0 events</span>
        </div>
        <section id="timeline" class="timeline" aria-live="polite"></section>
""".strip()


def css() -> str:
    """Return forensic-evidence CSS for the Registry detail panel."""

    workstream_chip_css = dashboard_ui_primitives.surface_workstream_button_chip_css(
        selector=".forensic-workstream-chip",
    )
    artifact_chip_css = dashboard_ui_primitives.detail_action_chip_css(
        selector=".artifact",
        border_color="#cbd5e1",
        background="#f8fafc",
        color="#334155",
        hover_border_color="#94a3b8",
        hover_background="#eef2f7",
        hover_color="#1f2937",
    )
    artifact_overflow_css = dashboard_ui_primitives.detail_action_chip_css(
        selector=".forensic-artifact-overflow-summary",
        border_color="#cbd5e1",
        background="#f8fafc",
        color="#334155",
        hover_border_color="#94a3b8",
        hover_background="#eef2f7",
        hover_color="#1f2937",
    )
    health_card_surface_css = governance_surface_theme.quiet_panel_surface_css(
        selector=".forensic-health-card",
        gap_px=5,
    )
    coverage_strip_surface_css = governance_surface_theme.metric_strip_surface_css(
        selector=".forensic-coverage-strip",
    )
    coverage_item_surface_css = governance_surface_theme.metric_strip_item_css(
        selector=".forensic-stat",
    )
    latest_surface_css = governance_surface_theme.evidence_note_surface_css(
        selector=".forensic-latest",
    )
    grouped_row_surface_css = governance_surface_theme.evidence_list_row_surface_css(
        selector=".forensic-group-row",
    )
    forensic_typography_css = registry_typography_ui.forensic_digest_typography_css()
    return "\n\n".join((r"""
    .timeline-head {
      border-bottom: 1px solid var(--line);
      padding: 12px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .timeline {
      margin: 0;
      padding: 12px 14px 14px;
      display: grid;
      gap: 12px;
      background: linear-gradient(180deg, #ffffff, #fcfeff);
      min-width: 0;
    }
    .forensic-digest {
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    __ODYLITH_FORENSIC_HEALTH_CARD_SURFACE__
    .forensic-health-copy {
      margin: 0;
      overflow-wrap: anywhere;
    }
    __ODYLITH_FORENSIC_COVERAGE_STRIP_SURFACE__
    __ODYLITH_FORENSIC_COVERAGE_ITEM_SURFACE__
    .forensic-stat + .forensic-stat {
      border-left: 1px solid #e5eefb;
    }
    .forensic-stat-label {
      white-space: nowrap;
    }
    @media (max-width: 760px) {
      .forensic-coverage-strip {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .forensic-stat + .forensic-stat {
        border-left: 0;
        border-top: 1px solid #e5eefb;
      }
    }
    __ODYLITH_FORENSIC_LATEST_SURFACE__
    __ODYLITH_FORENSIC_GROUP_ROW_SURFACE__
    .forensic-latest {
      grid-template-columns: minmax(0, 1fr);
    }
    .forensic-latest.diagnostic {
      border-color: #f8d88a;
      border-left-color: #f5c76c;
      background: #fffaf0;
    }
    .forensic-row-top {
      min-width: 0;
    }
    .forensic-row-top {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
    }
    .forensic-meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      min-width: 0;
      align-items: center;
    }
    .forensic-meta-item {
      white-space: nowrap;
    }
    .forensic-meta-item + .forensic-meta-item::before {
      content: "/";
      color: #94a3b8;
      margin-right: 8px;
    }
    .forensic-summary {
      margin: 0;
      overflow-wrap: anywhere;
    }
    .forensic-group-disclosure {
      border: 1px solid #dbeafe;
      border-radius: 12px;
      background: #ffffff;
      min-width: 0;
      overflow: hidden;
    }
    .forensic-group-disclosure > summary {
      cursor: pointer;
      list-style: none;
      padding: 10px 11px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .forensic-group-disclosure > summary::-webkit-details-marker {
      display: none;
    }
    .forensic-group-disclosure[open] > summary {
      border-bottom: 1px solid #e5eefb;
      background: #fbfdff;
    }
    .forensic-evidence-list {
      display: grid;
      gap: 0;
      min-width: 0;
      padding: 0;
    }
    .forensic-group-row {
      grid-template-columns: minmax(0, 1fr);
      --surface-workstream-button-padding: 1px 8px;
      --surface-deep-link-button-padding: 2px 9px;
    }
    .forensic-group-meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }
    .forensic-group-meta-item {
      white-space: nowrap;
    }
    .forensic-group-meta-item + .forensic-group-meta-item::before {
      content: "/";
      color: #94a3b8;
      margin-right: 8px;
    }
    .forensic-token-row,
    .artifact-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
      max-width: 100%;
    }
""".replace("__ODYLITH_FORENSIC_HEALTH_CARD_SURFACE__", health_card_surface_css)
        .replace("__ODYLITH_FORENSIC_COVERAGE_STRIP_SURFACE__", coverage_strip_surface_css)
        .replace("__ODYLITH_FORENSIC_COVERAGE_ITEM_SURFACE__", coverage_item_surface_css)
        .replace("__ODYLITH_FORENSIC_LATEST_SURFACE__", latest_surface_css)
        .replace("__ODYLITH_FORENSIC_GROUP_ROW_SURFACE__", grouped_row_surface_css),
        forensic_typography_css,
        workstream_chip_css,
        artifact_chip_css,
        artifact_overflow_css,
        r"""
    .forensic-workstream-chip {
      flex: 0 1 auto;
      max-width: 100%;
    }
    .artifact {
      justify-content: flex-start;
      flex: 0 1 auto;
      max-width: 100%;
      white-space: normal;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .forensic-artifact-disclosure {
      display: inline-flex;
      flex-direction: column;
      gap: 6px;
      max-width: 100%;
    }
    .forensic-artifact-disclosure > summary {
      list-style: none;
    }
    .forensic-artifact-disclosure > summary::-webkit-details-marker {
      display: none;
    }
    .forensic-artifact-disclosure-panel {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      max-width: 100%;
      padding-top: 2px;
    }
""")).strip()


def runtime_js() -> str:
    """Return browser runtime for rendering Registry forensic events."""

    return r"""
    const FORENSIC_DIGEST_WORKSTREAM_LIMIT = 4;
    const FORENSIC_DIGEST_ARTIFACT_LIMIT = 2;
    const FORENSIC_DIGEST_GROUP_LIMIT = 4;

    function forensicEventCountLabel(count) {
      const value = Number(count || 0);
      return `${value} ${pluralize(value, "event", "events")}`;
    }

    function forensicNormalizeText(value) {
      return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
    }

    function forensicEvidenceEvents(row) {
      return row && Array.isArray(row.timeline) ? row.timeline : [];
    }

    function forensicEventTimestamp(event) {
      return String(event && event.ts_iso || "").trim();
    }

    function forensicNewestEvent(events) {
      const rows = Array.isArray(events) ? events : [];
      return rows.reduce((newest, event) => {
        if (!newest) return event;
        return forensicEventTimestamp(event) > forensicEventTimestamp(newest) ? event : newest;
      }, null);
    }

    function forensicCoverageMetric(coverage, key) {
      const value = Number(coverage && coverage[key] || 0);
      return Number.isFinite(value) ? value : 0;
    }

    function forensicEventSignature(event) {
      const workstreams = (Array.isArray(event && event.workstreams) ? event.workstreams : [])
        .map((item) => String(item || "").trim())
        .filter(Boolean)
        .sort()
        .join(",");
      const artifacts = (Array.isArray(event && event.artifacts) ? event.artifacts : [])
        .map((item) => String(item && (item.path || item.href) || "").trim())
        .filter(Boolean)
        .sort()
        .join(",");
      return [
        forensicNormalizeText(event && event.kind),
        forensicNormalizeText(event && event.summary),
        workstreams,
        artifacts,
      ].join("|");
    }

    function forensicUniqueEvents(events) {
      const unique = [];
      const seen = new Set();
      (Array.isArray(events) ? events : []).forEach((event) => {
        const signature = forensicEventSignature(event);
        if (!signature || seen.has(signature)) return;
        seen.add(signature);
        unique.push(event);
      });
      return unique;
    }

    function forensicIsDiagnosticEvent(event) {
      const kind = forensicNormalizeText(event && event.kind);
      const summary = forensicNormalizeText(event && event.summary);
      return (
        kind.includes("intervention_")
        || kind.includes("hook")
        || kind.includes("teaser")
        || kind.includes("assist")
        || summary.includes("hidden hook")
        || summary.includes("non-visible")
      );
    }

    function forensicEvidenceChannel(event) {
      const kind = forensicNormalizeText(event && event.kind);
      const summary = forensicNormalizeText(event && event.summary);
      if (forensicIsDiagnosticEvent(event)) return "Diagnostic signal";
      if (kind.includes("spec") || kind.includes("history") || summary.includes("spec")) return "Spec history";
      if (kind.includes("validation") || kind.includes("benchmark") || kind.includes("proof")) return "Proof and validation";
      if (kind.includes("path") || kind.includes("source") || kind.includes("workspace")) return "Source and path evidence";
      if (kind.includes("implementation") || kind.includes("decision") || kind.includes("workstream")) return "Workstream evidence";
      if (Array.isArray(event && event.workstreams) && event.workstreams.length) return "Workstream evidence";
      if (Array.isArray(event && event.artifacts) && event.artifacts.length) return "Source and path evidence";
      return "Evidence signal";
    }

    function forensicMaterialEvents(events) {
      return (Array.isArray(events) ? events : []).filter((event) => !forensicIsDiagnosticEvent(event));
    }

    function forensicEvidenceHealthSummary(events, forensicCoverage) {
      const rows = Array.isArray(events) ? events : [];
      if (!rows.length) return "No mapped forensic evidence is attached yet.";
      const material = forensicMaterialEvents(rows);
      const diagnosticCount = Math.max(0, rows.length - material.length);
      const channelCount = new Set(rows.map(forensicEvidenceChannel)).size;
      if (material.length) {
        const supportBits = [
          forensicCoverageMetric(forensicCoverage, "mapped_workstream_evidence_count") ? "workstream-linked" : "",
          forensicCoverageMetric(forensicCoverage, "spec_history_event_count") ? "spec-history" : "",
        ].filter(Boolean).join(" and ");
        const supportText = supportBits ? ` Coverage includes ${supportBits} evidence.` : "";
        const diagnosticText = diagnosticCount ? ` Diagnostic/internal signals are kept in grouped details.` : "";
        return `${material.length} material ${pluralize(material.length, "signal", "signals")} linked across ${channelCount} ${pluralize(channelCount, "channel", "channels")}.${supportText}${diagnosticText}`;
      }
      return "Only diagnostic/internal signals are attached. Treat this as supporting context until workstream, spec, source, or path evidence appears.";
    }

    function renderForensicHealth(events, forensicCoverage) {
      return `
        <article class="forensic-health-card">
          <p class="forensic-health-title">Evidence health</p>
          <p class="forensic-health-copy">${escapeHtml(forensicEvidenceHealthSummary(events, forensicCoverage))}</p>
        </article>
      `;
    }

    function forensicCoverageStrip(events, forensicCoverage, rawCount = null) {
      const materialCount = forensicMaterialEvents(events).length;
      const facts = [
        ["Events", rawCount === null ? events.length : Number(rawCount || 0)],
        ["Material", materialCount],
        ["Workstreams", forensicCoverageMetric(forensicCoverage, "mapped_workstream_evidence_count")],
        ["Spec", forensicCoverageMetric(forensicCoverage, "spec_history_event_count")],
        ["Path", forensicCoverageMetric(forensicCoverage, "recent_path_match_count")],
      ];
      return `
        <div class="forensic-coverage-strip" aria-label="Forensic coverage counts">
          ${facts.map(([label, value]) => `
            <div class="forensic-stat">
              <p class="forensic-stat-label">${escapeHtml(label)}</p>
              <p class="forensic-stat-value">${escapeHtml(String(value))}</p>
            </div>
          `).join("")}
        </div>
      `;
    }

    function forensicWorkstreamLink(workstream) {
      const token = String(workstream || "").trim();
      if (!token) return "";
      return `<a class="forensic-workstream-chip" href="${escapeHtml(hrefRadar(token))}" target="_top" data-tooltip="Workstream ${escapeHtml(token)}. Open Radar context.">${escapeHtml(token)}</a>`;
    }

    function forensicArtifactLink(item) {
      const path = String(item && item.path || "").trim();
      const href = String(item && (item.href || item.path) || "").trim();
      if (!path && !href) return "";
      return `<a class="artifact" href="${escapeHtml(href || path)}" target="_top" data-tooltip="Artifact evidence path for this event.">${escapeHtml(path || "artifact")}</a>`;
    }

    function forensicOverflowLabel(count, noun) {
      const value = Number(count || 0);
      if (value <= 0) return "";
      return `<span class="label">+${escapeHtml(String(value))} ${escapeHtml(pluralize(value, noun, `${noun}s`))}</span>`;
    }

    function forensicLimitedWorkstreams(workstreams, limit = FORENSIC_DIGEST_WORKSTREAM_LIMIT) {
      const tokens = [];
      const seen = new Set();
      (Array.isArray(workstreams) ? workstreams : []).forEach((workstream) => {
        const token = String(workstream || "").trim();
        if (!token || seen.has(token)) return;
        seen.add(token);
        tokens.push(token);
      });
      const visible = tokens.slice(0, limit);
      const overflow = Math.max(0, tokens.length - visible.length);
      return {
        count: tokens.length,
        html: [
          ...visible.map(forensicWorkstreamLink),
          forensicOverflowLabel(overflow, "workstream"),
        ].filter(Boolean).join(""),
      };
    }

    function forensicLimitedArtifacts(artifacts, limit = FORENSIC_DIGEST_ARTIFACT_LIMIT) {
      const rows = [];
      const seen = new Set();
      (Array.isArray(artifacts) ? artifacts : []).forEach((item) => {
        const path = String(item && item.path || item && item.href || "").trim();
        if (!path || seen.has(path)) return;
        seen.add(path);
        rows.push(item);
      });
      if (Number(limit || 0) <= 0) {
        return {
          count: rows.length,
          html: forensicArtifactDisclosure(rows, rows.length),
        };
      }
      const visible = rows.slice(0, limit);
      const hidden = rows.slice(limit);
      return {
        count: rows.length,
        html: [
          ...visible.map(forensicArtifactLink),
          forensicArtifactDisclosure(hidden, hidden.length),
        ].filter(Boolean).join(""),
      };
    }

    function forensicArtifactDisclosure(rows, count) {
      const safeRows = Array.isArray(rows) ? rows : [];
      const total = Number(count || safeRows.length || 0);
      if (!safeRows.length || total <= 0) return "";
      return `
        <details class="forensic-artifact-disclosure">
          <summary class="forensic-artifact-overflow-summary">+${escapeHtml(String(total))} ${escapeHtml(pluralize(total, "artifact", "artifacts"))}</summary>
          <div class="forensic-artifact-disclosure-panel">
            ${safeRows.map(forensicArtifactLink).join("")}
          </div>
        </details>
      `;
    }

    function forensicEvidenceGroups(events) {
      const groups = [];
      const byKind = new Map();
      (Array.isArray(events) ? events : []).forEach((event) => {
        const channel = forensicEvidenceChannel(event);
        if (!byKind.has(channel)) {
          const group = { channel, count: 0, latest: event, workstreams: [], artifacts: [], diagnostic: channel === "Diagnostic signal" };
          byKind.set(channel, group);
          groups.push(group);
        }
        const group = byKind.get(channel);
        group.count += 1;
        if (!group.latest || forensicEventTimestamp(event) > forensicEventTimestamp(group.latest)) {
          group.latest = event;
        }
        group.workstreams.push(...(Array.isArray(event.workstreams) ? event.workstreams : []));
        group.artifacts.push(...(Array.isArray(event.artifacts) ? event.artifacts : []));
      });
      return groups.sort((left, right) => {
        if (left.diagnostic !== right.diagnostic) return left.diagnostic ? 1 : -1;
        const leftTimestamp = forensicEventTimestamp(left.latest);
        const rightTimestamp = forensicEventTimestamp(right.latest);
        if (leftTimestamp === rightTimestamp) return String(left.channel).localeCompare(String(right.channel));
        return rightTimestamp > leftTimestamp ? 1 : -1;
      });
    }

    function renderForensicTokenRow(workstreams, artifacts, options = {}) {
      const workstreamLimit = Number(
        Object.prototype.hasOwnProperty.call(options, "workstreamLimit")
          ? options.workstreamLimit
          : FORENSIC_DIGEST_WORKSTREAM_LIMIT
      );
      const artifactLimit = Number(
        Object.prototype.hasOwnProperty.call(options, "artifactLimit")
          ? options.artifactLimit
          : FORENSIC_DIGEST_ARTIFACT_LIMIT
      );
      const workstreamPreview = forensicLimitedWorkstreams(workstreams, workstreamLimit);
      const artifactPreview = forensicLimitedArtifacts(artifacts, artifactLimit);
      const html = [workstreamPreview.html, artifactPreview.html].filter(Boolean).join("");
      return html ? `<div class="forensic-token-row">${html}</div>` : "";
    }

    function forensicDisplaySummary(event, maxLength = 260) {
      const summary = String(event && event.summary || "(no summary)").replace(/\s+/g, " ").trim();
      const limit = Number(maxLength || 0);
      if (!limit || summary.length <= limit) return summary;
      const clipped = summary.slice(0, Math.max(0, limit - 3)).replace(/\s+\S*$/, "").trim();
      return `${clipped || summary.slice(0, Math.max(0, limit - 3)).trim()}...`;
    }

    function renderForensicLatestEvent(event, options = {}) {
      if (!event) {
        return '<article class="forensic-latest"><p class="empty">No mapped forensic evidence is attached yet.</p></article>';
      }
      const diagnosticOnly = Boolean(options.diagnosticOnly);
      const heading = diagnosticOnly ? "Latest diagnostic signal" : "Latest material signal";
      const className = diagnosticOnly ? "forensic-latest diagnostic" : "forensic-latest";
      return `
        <article class="${className}">
          <p class="forensic-eyebrow">${escapeHtml(heading)}</p>
          <div class="forensic-meta-row">
            <span class="forensic-meta-item" data-tooltip="Evidence channel.">${escapeHtml(forensicEvidenceChannel(event))}</span>
            <span class="forensic-meta-item" data-tooltip="Component-link confidence for this event.">confidence ${escapeHtml(event.confidence || "none")}</span>
            <span class="forensic-meta-item">${escapeHtml(event.ts_iso || "No timestamp")}</span>
          </div>
          <p class="forensic-summary">${escapeHtml(forensicDisplaySummary(event))}</p>
          ${renderForensicTokenRow(event.workstreams, event.artifacts, { artifactLimit: 0 })}
        </article>
      `;
    }

    function renderForensicGroups(events) {
      const groups = forensicEvidenceGroups(events);
      if (!groups.length) return "";
      const visibleGroups = groups.slice(0, FORENSIC_DIGEST_GROUP_LIMIT);
      const overflow = Math.max(0, groups.length - visibleGroups.length);
      return `
        <details class="forensic-group-disclosure">
          <summary>
            <span>Grouped evidence</span>
            <span>${escapeHtml(String(groups.length))} ${escapeHtml(pluralize(groups.length, "channel", "channels"))}${overflow ? ` - +${escapeHtml(String(overflow))} more` : ""}</span>
          </summary>
          <div class="forensic-evidence-list">
            ${visibleGroups.map((group) => `
              <article class="forensic-group-row">
                <div class="forensic-group-meta">
                  <span class="forensic-group-channel">${escapeHtml(group.channel)}</span>
                  <span class="forensic-group-meta-item">${escapeHtml(forensicEventCountLabel(group.count))}</span>
                  <span class="forensic-group-meta-item">${escapeHtml(group.latest && group.latest.ts_iso || "No timestamp")}</span>
                </div>
                <p class="forensic-summary">${escapeHtml(forensicDisplaySummary(group.latest))}</p>
                ${renderForensicTokenRow(group.workstreams, group.artifacts, { artifactLimit: 0 })}
              </article>
            `).join("")}
          </div>
        </details>
      `;
    }

    function renderTimeline(row) {
      const rawEvents = forensicEvidenceEvents(row);
      const events = forensicUniqueEvents(rawEvents);
      const forensicCoverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
      const materialEvents = forensicMaterialEvents(events);
      const headlineEvents = materialEvents.length ? materialEvents : events;
      const latestEvent = forensicNewestEvent(headlineEvents);
      const diagnosticOnly = Boolean(!materialEvents.length && events.length);
      timelineCountEl.textContent = forensicEventCountLabel(rawEvents.length);
      timelineEl.innerHTML = `
        <section class="forensic-digest">
          ${renderForensicHealth(events, forensicCoverage)}
          ${forensicCoverageStrip(events, forensicCoverage, rawEvents.length)}
          ${renderForensicLatestEvent(latestEvent, { diagnosticOnly })}
          ${renderForensicGroups(events)}
        </section>
      `;
    }
""".strip()

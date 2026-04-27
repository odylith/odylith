"""Registry forensic-evidence UI snippets.

The Registry renderer owns the data payload. This module owns the lower
forensic evidence surface so the oversized renderer does not keep absorbing
event-list markup, CSS, and browser behavior.
"""

from __future__ import annotations

from odylith.runtime.surfaces import dashboard_ui_primitives


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
        color="#334155",
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
    artifact_overflow_chip_css = dashboard_ui_primitives.detail_action_chip_css(
        selector=".forensic-artifact-overflow-summary",
        border_color="#cbd5e1",
        background="#f8fafc",
        color="#334155",
        hover_border_color="#94a3b8",
        hover_background="#eef2f7",
        hover_color="#1f2937",
    )
    artifact_overflow_caret_css = dashboard_ui_primitives.details_disclosure_caret_css(
        details_selector=".forensic-artifact-disclosure",
        label_selector=".forensic-artifact-overflow-summary",
        color="#64748b",
        size_px=11,
        gap_px=6,
    )
    coverage_grid_css = dashboard_ui_primitives.kpi_grid_layout_css(
        container_selector=".forensic-coverage-strip",
        gap_px=8,
        margin_top="0",
    )
    coverage_card_css = dashboard_ui_primitives.kpi_card_surface_css(
        card_selector=".forensic-stat",
    )
    coverage_typography_css = dashboard_ui_primitives.governance_kpi_label_value_css(
        label_selector=".forensic-stat-label",
        value_selector=".forensic-stat-value",
    )

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
""",
        coverage_grid_css,
        coverage_card_css,
        coverage_typography_css,
        r"""
    .forensic-latest,
    .forensic-group-row {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      padding: 11px;
      display: grid;
      gap: 8px;
      min-width: 0;
    }
    .forensic-latest {
      grid-template-columns: minmax(0, 1fr);
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
    .forensic-summary {
      margin: 0;
      overflow-wrap: anywhere;
    }
    .forensic-summary {
      color: #27445e;
      font-size: 15px;
      line-height: 1.45;
    }
    .forensic-evidence-list {
      display: grid;
      gap: 8px;
      min-width: 0;
    }
    .forensic-group-row {
      grid-template-columns: minmax(0, 1fr);
    }
    .forensic-token-row,
    .artifact-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
      max-width: 100%;
    }
""",
        workstream_chip_css,
        artifact_chip_css,
        artifact_overflow_chip_css,
        artifact_overflow_caret_css,
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
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
      max-width: 100%;
    }
    .forensic-artifact-overflow-summary {
      flex: 0 1 auto;
      max-width: 100%;
      list-style: none;
      white-space: normal;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .forensic-artifact-disclosure-panel {
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
      max-width: 100%;
    }
    .forensic-artifact-disclosure:not([open]) .forensic-artifact-disclosure-panel {
      display: none;
    }
    .forensic-artifact-disclosure[open] .forensic-artifact-disclosure-panel {
      display: flex;
    }
""")).strip()


def runtime_js() -> str:
    """Return browser runtime for rendering Registry forensic events."""

    return r"""
    const FORENSIC_DIGEST_WORKSTREAM_LIMIT = 4;
    const FORENSIC_DIGEST_ARTIFACT_LIMIT = 2;

    function forensicEventCountLabel(count) {
      const value = Number(count || 0);
      return `${value} ${pluralize(value, "event", "events")}`;
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

    function forensicCoverageStrip(events, forensicCoverage) {
      const facts = [
        ["Events", events.length],
        ["Explicit", forensicCoverageMetric(forensicCoverage, "explicit_event_count")],
        ["Path matches", forensicCoverageMetric(forensicCoverage, "recent_path_match_count")],
        ["Workstream evidence", forensicCoverageMetric(forensicCoverage, "mapped_workstream_evidence_count")],
        ["Spec history", forensicCoverageMetric(forensicCoverage, "spec_history_event_count")],
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

    function forensicArtifactOverflowDisclosure(items, overflow) {
      const value = Number(overflow || 0);
      if (value <= 0 || !Array.isArray(items) || !items.length) return "";
      return `
        <details class="forensic-artifact-disclosure">
          <summary class="forensic-artifact-overflow-summary" data-tooltip="Show hidden artifact evidence paths.">+${escapeHtml(String(value))} ${escapeHtml(pluralize(value, "artifact", "artifacts"))}</summary>
          <div class="forensic-artifact-disclosure-panel artifact-list">
            ${items.map(forensicArtifactLink).filter(Boolean).join("")}
          </div>
        </details>
      `;
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
      const visible = rows.slice(0, limit);
      const hidden = rows.slice(limit);
      const overflow = Math.max(0, rows.length - visible.length);
      return {
        count: rows.length,
        html: [
          ...visible.map(forensicArtifactLink),
          forensicArtifactOverflowDisclosure(hidden, overflow),
        ].filter(Boolean).join(""),
      };
    }

    function forensicEvidenceGroups(events) {
      const groups = [];
      const byKind = new Map();
      (Array.isArray(events) ? events : []).forEach((event) => {
        const kind = String(event && event.kind || "unknown").trim().toLowerCase() || "unknown";
        if (!byKind.has(kind)) {
          const group = { kind, count: 0, latest: event, workstreams: [], artifacts: [] };
          byKind.set(kind, group);
          groups.push(group);
        }
        const group = byKind.get(kind);
        group.count += 1;
        if (!group.latest || forensicEventTimestamp(event) > forensicEventTimestamp(group.latest)) {
          group.latest = event;
        }
        group.workstreams.push(...(Array.isArray(event.workstreams) ? event.workstreams : []));
        group.artifacts.push(...(Array.isArray(event.artifacts) ? event.artifacts : []));
      });
      return groups;
    }

    function renderForensicTokenRow(workstreams, artifacts, options = {}) {
      const workstreamLimit = Number(options.workstreamLimit || FORENSIC_DIGEST_WORKSTREAM_LIMIT);
      const artifactLimit = Number(options.artifactLimit || FORENSIC_DIGEST_ARTIFACT_LIMIT);
      const workstreamPreview = forensicLimitedWorkstreams(workstreams, workstreamLimit);
      const artifactPreview = forensicLimitedArtifacts(artifacts, artifactLimit);
      const html = [workstreamPreview.html, artifactPreview.html].filter(Boolean).join("");
      return html ? `<div class="forensic-token-row">${html}</div>` : "";
    }

    function renderForensicLatestEvent(event) {
      if (!event) {
        return '<article class="forensic-latest"><p class="empty">No mapped forensic events are attached yet.</p></article>';
      }
      return `
        <article class="forensic-latest">
          <div class="forensic-row-top">
            <span class="label" data-tooltip="Codex stream event kind.">${escapeHtml(eventKindLabel(event.kind))}</span>
            <span class="label" data-tooltip="Component-link confidence for this event.">confidence: ${escapeHtml(event.confidence || "none")}</span>
            <span class="label">${escapeHtml(event.ts_iso || "No timestamp")}</span>
          </div>
          <p class="forensic-summary">${escapeHtml(event.summary || "(no summary)")}</p>
          ${renderForensicTokenRow(event.workstreams, event.artifacts)}
        </article>
      `;
    }

    function renderForensicGroups(events) {
      const groups = forensicEvidenceGroups(events);
      if (!groups.length) return "";
      return `
        <div class="forensic-evidence-list">
          ${groups.map((group) => `
            <article class="forensic-group-row">
              <div class="forensic-row-top">
                <span class="label">${escapeHtml(eventKindLabel(group.kind))}</span>
                <span class="label">${escapeHtml(forensicEventCountLabel(group.count))}</span>
              </div>
              <p class="forensic-summary">${escapeHtml(group.latest && group.latest.summary || "(no summary)")}</p>
              ${renderForensicTokenRow(group.workstreams, group.artifacts)}
            </article>
          `).join("")}
        </div>
      `;
    }

    function renderTimeline(row) {
      const events = forensicEvidenceEvents(row);
      const forensicCoverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
      const latestEvent = forensicNewestEvent(events);
      timelineCountEl.textContent = forensicEventCountLabel(events.length);
      timelineEl.innerHTML = `
        <section class="forensic-digest">
          ${forensicCoverageStrip(events, forensicCoverage)}
          ${renderForensicLatestEvent(latestEvent)}
          ${renderForensicGroups(events)}
        </section>
      `;
    }
""".strip()

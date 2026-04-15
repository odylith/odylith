"""HTML and rich-text helpers extracted from the backlog renderer."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.surfaces import backlog_rich_text
from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import dashboard_ui_runtime_primitives
from odylith.runtime.surfaces import execution_wave_ui_runtime_primitives


def _host():
    from odylith.runtime.surfaces import render_backlog_ui as host

    return host


def _normalize_inline_repo_token(*, repo_root: Path, token: str) -> str:
    host = _host()
    normalized = host.workstream_inference.normalize_repo_token(str(token or "").strip(), repo_root=repo_root)
    collapsed = str(normalized or "").strip().strip(".,;:")
    if not collapsed or " " in collapsed or "<" in collapsed or ">" in collapsed:
        return ""
    if collapsed.startswith("http://") or collapsed.startswith("https://"):
        return ""
    return collapsed


def _render_section_body(*, repo_root: Path, lines: list[str]) -> str:
    return backlog_rich_text.render_section_body(repo_root=repo_root, lines=lines)


def _extract_traceability_path_tokens(text: str) -> list[str]:
    host = _host()
    tokens: list[str] = []
    for match in host._TRACEABILITY_PATH_LINK_RE.finditer(text):  # noqa: SLF001
        token = str(match.group(1)).strip()
        if token:
            tokens.append(token)
    for match in host._TRACEABILITY_PATH_CODE_RE.finditer(text):  # noqa: SLF001
        token = str(match.group(1)).strip()
        if token:
            tokens.append(token)
    return tokens


def _normalize_traceability_path(*, repo_root: Path, token: str) -> str:
    return _normalize_inline_repo_token(repo_root=repo_root, token=token)


def _collect_plan_traceability_paths(
    *,
    repo_root: Path,
    sections: list[tuple[str, list[str]]],
) -> dict[str, list[str]]:
    host = _host()
    raw_traceability_lines: list[str] = []
    for title, lines in sections:
        if title.strip().lower() == host._TRACEABILITY_SECTION_NAME.lower():  # noqa: SLF001
            raw_traceability_lines = lines
            break
    if not raw_traceability_lines:
        return {}

    bucket: str | None = None
    grouped: dict[str, list[str]] = {label: [] for label in host._TRACEABILITY_BUCKETS}  # noqa: SLF001
    for line in raw_traceability_lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            candidate = stripped[4:].strip()
            bucket = candidate if candidate in grouped else None
            continue
        if bucket is None:
            continue
        if not stripped:
            continue
        if not stripped.lstrip().startswith("- "):
            continue
        body = stripped.lstrip()[2:].strip()
        body = host._TRACEABILITY_CHECKBOX_PREFIX_RE.sub("", body).strip()  # noqa: SLF001
        for token in _extract_traceability_path_tokens(body):
            normalized = _normalize_traceability_path(repo_root=repo_root, token=token)
            if normalized:
                grouped[bucket].append(normalized)

    collapsed: dict[str, list[str]] = {}
    for label, values in grouped.items():
        deduped = sorted(set(values))
        if deduped:
            collapsed[label] = deduped
    return collapsed


def _render_html(*, payload: dict[str, object]) -> str:
    data_blob = json.dumps(payload, ensure_ascii=True, indent=2)
    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Backlog Workstream Radar</title>
  __ODYLITH_BRAND_HEAD__
  <style>
    :root {
      --bg-a: #f0f9ff;
      --bg-b: #ecfeff;
      --ink: #0b1324;
      --ink-soft: #334155;
      --ink-muted: #64748b;
      --line: #c7d2fe;
      --line-strong: #94a3b8;
      --panel: #ffffff;
      --panel-alt: #f8fafc;
      --brand: #0f766e;
      --brand-2: #1d4ed8;
      --warn: #b45309;
      --ok: #166534;
      --focus: #2563eb;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background:
        radial-gradient(circle at 8% -10%, #dbeafe 0%, transparent 42%),
        radial-gradient(circle at 94% 0%, #ccfbf1 0%, transparent 38%),
        linear-gradient(180deg, var(--bg-a), var(--bg-b));
      min-height: 100vh;
    }
    __ODYLITH_PAGE_BODY__
    __ODYLITH_SURFACE_SHELL_ROOT__

    __ODYLITH_SURFACE_SHELL__

    __ODYLITH_HERO_PANEL__

    __ODYLITH_HEADER_TYPOGRAPHY__

    __ODYLITH_KPI_GRID_LAYOUT__

    __ODYLITH_STAT_CARD_SURFACE__

    __ODYLITH_KPI_TYPOGRAPHY__

    __ODYLITH_STICKY_FILTER_BAR__

    .meta {
      margin: 6px 0 12px;
    }
    __ODYLITH_RADAR_META_COPY__

    .execution-legend {
      margin: -3px 0 12px;
      padding: 8px 10px;
      border: 1px solid #dbeafe;
      border-radius: 10px;
      background: #f8fbff;
    }

    .analytics-panel {
      margin-bottom: 12px;
      border: 1px solid #bfdbfe;
      border-radius: 14px;
      background: linear-gradient(180deg, #f8fbff, #ffffff);
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
      overflow: hidden;
    }

    .analytics-toggle {
      list-style: none;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      cursor: pointer;
      user-select: none;
      border-bottom: 1px solid transparent;
      background: linear-gradient(180deg, #f8fbff, #ffffff);
    }

    .analytics-toggle::-webkit-details-marker {
      display: none;
    }

    .analytics-panel[open] .analytics-toggle {
      border-bottom-color: #dbeafe;
    }

    .analytics-toggle-copy {
      display: grid;
      gap: 2px;
    }

    .analytics-toggle-title {
    }
    __ODYLITH_RADAR_ANALYTICS_TITLE__

    .analytics-toggle-sub {
    }

    .analytics-toggle-hint {
      border: 1px solid #bfdbfe;
      background: #eff6ff;
      border-radius: 999px;
      padding: 4px 8px;
      white-space: nowrap;
    }

    .analytics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      padding: 10px;
    }

    .graph-card {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 14px;
      padding: 10px 11px;
      box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
    }

    .graph-head {
    }

    .graph-sub {
      margin: 4px 0 8px;
    }

    .graph-empty {
      border: 1px dashed #cbd5e1;
      border-radius: 10px;
      padding: 9px 8px;
      text-align: center;
      background: #f8fafc;
    }

    .chart-wrap {
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      background: #f8fafc;
      padding: 6px 6px 4px;
    }

    .chart-svg {
      width: 100%;
      height: auto;
      display: block;
    }

    .chart-axis {
    }
    __ODYLITH_RADAR_CHART_AXIS_TYPOGRAPHY__

    .chart-grid {
      stroke: #e2e8f0;
      stroke-width: 1;
    }

    .chart-line-primary {
      fill: none;
      stroke: #0f766e;
      stroke-width: 2.2;
    }

    .chart-line-secondary {
      fill: none;
      stroke: #2563eb;
      stroke-width: 2.2;
      stroke-dasharray: 5 4;
    }

    .chart-bar-primary {
      fill: rgba(37, 99, 235, 0.28);
    }

    .chart-point-primary {
      fill: #0f766e;
    }

    .chart-point-secondary {
      fill: #2563eb;
    }

    .chart-legend {
      margin-top: 8px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
    }

    .graph-note {
      margin-top: 8px;
    }

    .topology-board {
      --topology-label-column: 170px;
      --topology-count-column: 36px;
      border: 1px solid #dbeafe;
      border-radius: 12px;
      background: linear-gradient(180deg, #f8fbff, #ffffff);
      padding: 10px;
      display: grid;
      gap: 10px;
    }

    .topology-relations-panel {
      border: 1px solid #dbeafe;
      border-radius: 11px;
      background: #ffffff;
      overflow: hidden;
    }

    .topology-relations-panel > summary {
      list-style: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 8px 10px;
      user-select: none;
    }

    .topology-relations-summary {
    }

    .topology-relations {
      display: grid;
      border-top: 1px solid #e2e8f0;
    }

    .topology-relations-empty {
      border: 1px solid #dbeafe;
      border-radius: 11px;
      background: #ffffff;
      padding: 10px;
    }

    .topology-rel-row {
      display: grid;
      grid-template-columns: var(--topology-label-column) var(--topology-count-column) minmax(0, 1fr);
      gap: 10px;
      align-items: center;
      padding: 8px 10px;
      border-top: 1px solid #e2e8f0;
    }

    .topology-rel-row:first-child {
      border-top: none;
    }

    .topology-rel-title {
      grid-column: 1;
    }

    .topology-rel-count {
      grid-column: 2;
      justify-self: end;
    }

    .topology-rel-body {
      grid-column: 3;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
      min-height: 28px;
    }

    .topology-rel-empty {
      padding-top: 2px;
    }

    __ODYLITH_EXECUTION_WAVE_CSS__

    .warning-list {
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 8px;
    }

    .warning-item {
      border: 1px solid #fed7aa;
      border-radius: 10px;
      background: #fffaf5;
      padding: 8px 9px;
    }

    .warning-title {
      margin: 0;
    }

    .warning-action {
      margin: 4px 0 0;
    }

    .warning-meta {
      margin: 4px 0 0;
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      white-space: nowrap;
    }

    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      display: inline-block;
      background: #cbd5e1;
    }

    .mix-toggle {
      display: inline-flex;
      gap: 6px;
      margin-bottom: 8px;
    }

    __ODYLITH_RADAR_MIX_TOGGLE_BUTTON__

    __ODYLITH_RADAR_WORKSPACE_LAYOUT__
    .workspace {
      min-height: 560px;
    }

    .list-panel,
    .detail-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
      overflow: hidden;
    }

    .panel-head {
      padding: 12px 14px;
      border-bottom: 1px solid #e2e8f0;
      background: linear-gradient(180deg, #f8fafc, #ffffff);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }

    .list {
      max-height: 640px;
      overflow: auto;
      padding: 6px;
      background: var(--panel-alt);
    }

    .list-spacer {
      pointer-events: none;
    }

    .list-section-head {
      margin: 8px 4px 8px;
      padding: 6px 10px;
      border: 1px solid #dbeafe;
      border-radius: 10px;
      background: #eff6ff;
    }
    __ODYLITH_RADAR_SECONDARY_TYPOGRAPHY__
    __ODYLITH_RADAR_LABEL_SEMANTICS__

    .row {
      width: 100%;
      text-align: left;
      border: 1px solid #d6dce8;
      border-radius: 12px;
      background: #ffffff;
      padding: 10px 10px 9px;
      margin-bottom: 8px;
      scroll-margin-top: 104px;
      cursor: pointer;
      transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
    }

    .row:hover {
      border-color: #93c5fd;
      box-shadow: 0 8px 18px rgba(15, 23, 42, 0.09);
      transform: translateY(-1px);
    }

    .row.active {
      border-color: #1d4ed8;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.22);
    }

    .row-top {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 7px;
    }

    __ODYLITH_RADAR_RANK_CHIP_SURFACE__
    __ODYLITH_RADAR_RANK_CHIP_TYPOGRAPHY__

    .row-title {
    }
    __ODYLITH_RADAR_ROW_TITLE__

    .row-id {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    __ODYLITH_RADAR_ROW_ID__

    .row-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 7px;
      flex-wrap: wrap;
    }

    .row-foot {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .row-chips,
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .row-chips {
      margin: 0;
    }

    .row-chips-end {
      margin-left: auto;
      justify-content: flex-end;
    }

    __ODYLITH_RADAR_CHIP_SURFACE__
    __ODYLITH_RADAR_CHIP_TYPOGRAPHY__

    __ODYLITH_RADAR_CHIP_LINK_CONTRACT__

    .detail {
      padding: 16px 18px 18px;
      display: grid;
      gap: 14px;
    }

    .detail-header {
      border: 1px solid #d7e3f6;
      border-radius: 14px;
      padding: 14px 16px;
      background: linear-gradient(170deg, #f8fafc, #ffffff 65%, #eff6ff);
    }

    __ODYLITH_DETAIL_IDENTITY_TYPOGRAPHY__

    .chips {
      margin-top: 12px;
      margin-bottom: 0;
    }

    .kpis {
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
    }

    .kpi.kpi-section .k,
    .kpi.kpi-section .v {
      color: inherit;
    }

    __ODYLITH_RADAR_DETAIL_KPI_SURFACE__
    __ODYLITH_RADAR_DETAIL_KPI_TYPOGRAPHY__

    .meter {
      margin-top: 14px;
    }

    .meter-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }

    .bar {
      margin-top: 6px;
      height: 10px;
      border-radius: 999px;
      background: #e2e8f0;
      overflow: hidden;
    }

    .fill {
      height: 100%;
      background: linear-gradient(90deg, var(--brand), var(--brand-2));
    }

    .block {
      margin-top: 0;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 14px 16px;
      background: #ffffff;
    }

    __ODYLITH_RADAR_OPERATOR_READOUT_LAYOUT__
    __ODYLITH_RADAR_OPERATOR_READOUT_LABEL__
    __ODYLITH_RADAR_OPERATOR_READOUT_COPY__
    __ODYLITH_RADAR_OPERATOR_READOUT_META__

    .split-grid {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .split-card {
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      background: #f8fafc;
      padding: 12px 14px;
      min-width: 0;
    }

    .block h3 {
      margin: 0 0 10px;
    }
    __ODYLITH_RADAR_BLOCK_HEADING__
    .block .trace-subhead {
      margin: 2px 0 8px;
    }
    __ODYLITH_RADAR_TRACE_SUBHEAD__

    .block p {
      margin: 0;
      line-height: 1.6;
      font-size: 16px;
      color: #1e293b;
    }

    .bullets {
      margin: 0;
      padding-left: 20px;
      font-size: 16px;
      line-height: 1.6;
      color: #1e293b;
    }

    .bullets li {
      margin-bottom: 7px;
    }

    .split-card .bullets {
      padding-left: 18px;
    }

    .split-card .bullets li {
      margin-bottom: 6px;
    }

    __ODYLITH_RADAR_READABLE_COPY__

    .links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      font-size: 12px;
    }

    .links a {
      color: #4d6480;
      text-decoration: none;
      border-bottom: 1px dotted #bfd0e0;
    }

    .links a:hover { color: #334962; }

    .empty,
    .drawer-empty {
      padding: 24px;
      border: 1px dashed var(--line);
      border-radius: 14px;
      background: #fff;
      color: var(--ink-muted);
      text-align: center;
      line-height: 1.5;
    }

    .drawer-empty {
      margin: 14px;
    }

    .controls input,
    .controls select {
      min-width: 0;
    }

    __ODYLITH_RADAR_TOOLTIP_SURFACE__

    @media (max-width: 1100px) {
      .analytics {
        grid-template-columns: 1fr;
      }
      .workspace {
        grid-template-columns: 1fr;
      }
      .list {
        max-height: 340px;
      }
    }

    @media (max-width: 920px) {
      .controls {
        grid-template-columns: 1fr 1fr;
      }
      .topology-rel-row {
        grid-template-columns: 1fr;
        align-items: start;
      }
      .topology-rel-title,
      .topology-rel-count,
      .topology-rel-body {
        grid-column: 1;
      }
      .topology-rel-count {
        justify-self: start;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="kicker">Priority Queue and Workstream Status</div>
      <h1>Backlog Workstream Radar</h1>
      <p class="subtitle">See what is queued, active, parked, and finished, backed by repo workstream specs and delivery evidence.</p>
      <div class="stats" id="stats"></div>
    </section>

    <details class="analytics-panel" id="analytics-panel">
      <summary class="analytics-toggle">
        <span class="analytics-toggle-copy">
          <span class="analytics-toggle-title">Delivery Analytics</span>
          <span class="analytics-toggle-sub">Optional trend charts for velocity, cycle time, and mix.</span>
        </span>
        <span class="analytics-toggle-hint" id="analytics-toggle-hint">Show</span>
      </summary>
      <section class="analytics" id="analytics">
        <article class="graph-card">
          <h2 class="graph-head">Execution Velocity</h2>
          <p class="graph-sub">Weekly finished count + 4-week moving average</p>
          <div id="graph-velocity"></div>
        </article>
        <article class="graph-card">
          <h2 class="graph-head">Cycle Time Trend</h2>
          <p class="graph-sub">Weekly median and P85 execution days</p>
          <div id="graph-cycle"></div>
        </article>
        <article class="graph-card">
          <h2 class="graph-head">Delivery Mix Over Time</h2>
          <p class="graph-sub">Weekly finished throughput split by complexity or size</p>
          <div class="mix-toggle" id="mix-toggle">
            <button id="mix-by-complexity" type="button" class="active">Complexity</button>
            <button id="mix-by-size" type="button">Size</button>
          </div>
          <div id="graph-mix"></div>
        </article>
      </section>
    </details>

    <section class="controls">
      <input id="query" placeholder="Search title, ID, rationale, impacted parts..." />
      <select id="lane">
        <option value="all">All Sections</option>
        <option value="execution">Delivery Pipeline</option>
        <option value="parked">Parked</option>
        <option value="active">Idea Stage (Ranked Active)</option>
        <option value="finished">Finished</option>
      </select>
      <select id="section" aria-hidden="true" tabindex="-1" style="position:absolute;inline-size:1px;block-size:1px;opacity:0.01;padding:0;border:0">
        <option value="all">All Sections</option>
        <option value="execution">Delivery Pipeline</option>
        <option value="parked">Parked</option>
        <option value="active">Idea Stage (Ranked Active)</option>
        <option value="finished">Finished</option>
      </select>
      <select id="type">
        <option value="all">All Types</option>
        <option value="umbrella">Umbrella</option>
        <option value="child">Child</option>
      </select>
      <select id="phase">
        <option value="all">All Phases</option>
        <option value="planning">Planning</option>
        <option value="implementation">Implementation</option>
      </select>
      <select id="activity">
        <option value="all">All Activity</option>
        <option value="active">Signal: Active</option>
        <option value="quiet">Signal: Quiet</option>
      </select>
      <select id="priority">
        <option value="all">All Priorities</option>
      </select>
      <select id="release">
        <option value="all">All Releases</option>
      </select>
      <select id="sort">
        <option value="rank">Sort: Rank</option>
        <option value="score">Sort: Score</option>
        <option value="date">Sort: Date</option>
      </select>
    </section>

    <div class="execution-legend">
      Delivery Pipeline is two-dimensional:
      <strong>Phase</strong> (<strong>Planning</strong> or <strong>Implementation</strong>) and
      <strong>Execution Signal</strong> (planning shows <strong>Plan: Active/Quiet</strong>;
      implementation shows <strong>Live: Active/Quiet</strong>).
    </div>

    <div class="meta" id="meta"></div>
    <section class="workspace">
      <aside class="list-panel">
        <div class="panel-head">
          <span>Delivery Pipeline · Parked · Idea Stage · Finished</span>
        </div>
        <div class="list" id="list"></div>
      </aside>

      <section class="detail-panel">
        <div class="panel-head">Selected Workstream Detail</div>
        <div class="drawer-empty" id="detail-empty" hidden></div>
        <article class="detail" id="detail" hidden></article>
      </section>
    </section>
    <div class="empty" id="empty" hidden></div>
  </main>

  <script id="backlogData" type="application/json">__DATA__</script>
  <script>
    (async () => {
    const DATA = JSON.parse(document.getElementById("backlogData").textContent);
    const assetLoadCache = new Map();
    function loadScriptAsset(href) {
      const token = String(href || "").trim();
      if (!token) return Promise.resolve();
      const resolvedHref = new URL(token, window.location.href).toString();
      if (assetLoadCache.has(resolvedHref)) {
        return assetLoadCache.get(resolvedHref);
      }
      const promise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = resolvedHref;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`failed to load asset ${resolvedHref}`));
        document.head.appendChild(script);
      });
      assetLoadCache.set(resolvedHref, promise);
      return promise;
    }
    function detailManifest() {
      const payload = DATA.detail_manifest;
      return payload && typeof payload === "object" ? payload : {};
    }
    function standaloneManifest() {
      const payload = window.__ODYLITH_BACKLOG_STANDALONE_MANIFEST__;
      return payload && typeof payload === "object" ? payload : {};
    }
    async function ensureStandaloneManifestLoaded() {
      const existing = standaloneManifest();
      if (Object.keys(existing).length) return existing;
      const href = String(DATA.standalone_manifest_href || "").trim();
      if (!href) return {};
      await loadScriptAsset(href);
      return standaloneManifest();
    }
    async function loadStandaloneDocument(viewToken, workstreamToken) {
      const key = `${String(viewToken || "").trim()}:${String(workstreamToken || "").trim()}`;
      const loadedDocs = window.__ODYLITH_BACKLOG_DOCUMENT_SHARDS__ || {};
      if (typeof loadedDocs[key] === "string" && loadedDocs[key].trim()) {
        return loadedDocs[key];
      }
      const manifest = await ensureStandaloneManifestLoaded();
      const shardHref = String(manifest[key] || "").trim();
      if (!shardHref) return "";
      await loadScriptAsset(shardHref);
      const resolved = window.__ODYLITH_BACKLOG_DOCUMENT_SHARDS__ || {};
      return typeof resolved[key] === "string" ? resolved[key] : "";
    }
    async function loadDetailEntry(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) return null;
      const loaded = window.__ODYLITH_BACKLOG_DETAIL_SHARDS__ || {};
      if (loaded[token] && typeof loaded[token] === "object") {
        return loaded[token];
      }
      const shardHref = String(detailManifest()[token] || "").trim();
      if (!shardHref) return null;
      await loadScriptAsset(shardHref);
      const resolved = window.__ODYLITH_BACKLOG_DETAIL_SHARDS__ || {};
      return resolved[token] && typeof resolved[token] === "object" ? resolved[token] : null;
    }
    async function loadRuntimePayload(path, params = {}) {
      const dataSource = DATA.data_source && typeof DATA.data_source === "object" ? DATA.data_source : {};
      const base = String(dataSource.runtime_base_url || "").trim();
      const protocol = String(window.location.protocol || "").toLowerCase();
      if (!base || protocol === "file:") return null;
      try {
        const url = new URL(path.replace(/^\\/+/, ""), base.endsWith("/") ? base : `${base}/`);
        Object.entries(params || {}).forEach(([key, value]) => {
          if (value === undefined || value === null || value === "") return;
          url.searchParams.set(key, String(value));
        });
        const response = await fetch(url.toString(), { headers: { "Accept": "application/json" } });
        if (!response.ok) return null;
        return await response.json();
      } catch (_error) {
        return null;
      }
    }
    function createStaticSnapshotBacklogDataSource() {
      return {
        backend: "staticSnapshot",
        async loadManifest() {
          return {
            detail: detailManifest(),
            documents: await ensureStandaloneManifestLoaded(),
          };
        },
        async loadList(_params = {}) {
          return Array.isArray(DATA.entries) ? DATA.entries.slice() : [];
        },
        async loadDetail(id) {
          return loadDetailEntry(id);
        },
        async loadDocument(request = {}) {
          return loadStandaloneDocument(request.view, request.id);
        },
        prefetch(id) {
          void loadDetailEntry(id);
        },
      };
    }
    function createRuntimeBacklogDataSource() {
      const fallback = createStaticSnapshotBacklogDataSource();
      return {
        backend: "runtime",
        async loadManifest() {
          const payload = await loadRuntimePayload("surfaces/backlog/manifest");
          if (payload && typeof payload === "object") return payload;
          return fallback.loadManifest();
        },
        async loadList(params = {}) {
          const payload = await loadRuntimePayload("surfaces/backlog/list", params);
          if (payload && Array.isArray(payload.entries)) return payload.entries;
          return fallback.loadList(params);
        },
        async loadDetail(id) {
          const payload = await loadRuntimePayload("surfaces/backlog/detail", { workstream: id });
          if (payload && typeof payload === "object") return payload;
          return fallback.loadDetail(id);
        },
        async loadDocument(request = {}) {
          const payload = await loadRuntimePayload("surfaces/backlog/document", {
            workstream: request.id,
            view: request.view,
          });
          if (payload && typeof payload.html === "string") return payload.html;
          return fallback.loadDocument(request);
        },
        prefetch(id) {
          void this.loadDetail(id);
        },
      };
    }
    function createBacklogDataSource() {
      const dataSource = DATA.data_source && typeof DATA.data_source === "object" ? DATA.data_source : {};
      const preferred = String(dataSource.preferred_backend || "").trim();
      if (preferred === "runtime") {
        return createRuntimeBacklogDataSource();
      }
      return createStaticSnapshotBacklogDataSource();
    }
    const backlogDataSource = createBacklogDataSource();
    function copyElementAttributes(target, source) {
      if (!target || !source) return;
      for (const attr of Array.from(target.attributes || [])) {
        target.removeAttribute(attr.name);
      }
      for (const attr of Array.from(source.attributes || [])) {
        target.setAttribute(attr.name, attr.value);
      }
    }
    function appendStandaloneNodes(target, nodes) {
      for (const node of nodes) {
        if (node.nodeType === Node.ELEMENT_NODE && node.tagName.toLowerCase() === "script") {
          const script = document.createElement("script");
          for (const attr of Array.from(node.attributes || [])) {
            script.setAttribute(attr.name, attr.value);
          }
          if (node.textContent) {
            script.textContent = node.textContent;
          }
          target.appendChild(script);
          continue;
        }
        target.appendChild(document.importNode(node, true));
      }
    }
    function replaceStandaloneDocument(standaloneHtml) {
      const parser = new DOMParser();
      const parsed = parser.parseFromString(standaloneHtml, "text/html");
      if (!parsed || !parsed.documentElement || !parsed.body) {
        return false;
      }
      const nextRoot = parsed.documentElement;
      const nextHead = parsed.head || parsed.createElement("head");
      const nextBody = parsed.body;
      const nextHeadNodes = Array.from(nextHead.childNodes || []);
      const nextBodyNodes = Array.from(nextBody.childNodes || []);
      copyElementAttributes(document.documentElement, nextRoot);
      copyElementAttributes(document.head, nextHead);
      copyElementAttributes(document.body, nextBody);
      document.title = parsed.title || document.title;
      document.head.replaceChildren();
      document.body.replaceChildren();
      appendStandaloneNodes(document.head, nextHeadNodes);
      appendStandaloneNodes(document.body, nextBodyNodes);
      return true;
    }
    const urlParams = new URLSearchParams(window.location.search);
    const workstreamParam = (urlParams.get("workstream") || "").trim().toUpperCase();
    const viewParam = (urlParams.get("view") || "").trim().toLowerCase();
    if ((viewParam === "spec" || viewParam === "plan") && workstreamParam) {
      const standaloneHtml = await backlogDataSource.loadDocument({ id: workstreamParam, view: viewParam });
      if (typeof standaloneHtml === "string" && standaloneHtml.trim()) {
        try {
          if (window.parent && window.parent !== window) {
            window.parent.postMessage({
              type: "odylith-radar-navigate",
              state: { workstream: workstreamParam, view: viewParam },
            }, "*");
          }
        } catch (_error) {
          // Ignore parent-shell sync failures; standalone rendering must still work.
        }
        replaceStandaloneDocument(standaloneHtml);
        return;
      }
    }

    const state = {
      query: "",
      section: "all",
      phase: "all",
      type: "all",
      activity: "all",
      priority: "all",
      release: "all",
      sort: "rank",
      mixBy: "complexity",
      selectedIdeaId: ""
    };

    const el = {
      stats: document.getElementById("stats"),
      query: document.getElementById("query"),
      section: document.getElementById("lane"),
      legacySection: document.getElementById("section"),
      phase: document.getElementById("phase"),
      type: document.getElementById("type"),
      activity: document.getElementById("activity"),
      priority: document.getElementById("priority"),
      release: document.getElementById("release"),
      sort: document.getElementById("sort"),
      meta: document.getElementById("meta"),
      analyticsPanel: document.getElementById("analytics-panel"),
      analyticsToggleHint: document.getElementById("analytics-toggle-hint"),
      graphVelocity: document.getElementById("graph-velocity"),
      graphCycle: document.getElementById("graph-cycle"),
      graphMix: document.getElementById("graph-mix"),
      mixByComplexity: document.getElementById("mix-by-complexity"),
      mixBySize: document.getElementById("mix-by-size"),
      list: document.getElementById("list"),
      detail: document.getElementById("detail"),
      detailEmpty: document.getElementById("detail-empty"),
      empty: document.getElementById("empty")
    };
    __ODYLITH_RADAR_QUICK_TOOLTIP_RUNTIME__

    const ANALYTICS_OPEN_PREF_KEY = "odylith.backlog.analytics.open.v1";

    const loadedList = await backlogDataSource.loadList({});
    const all = Array.isArray(loadedList) ? loadedList : [];
    const allIdeaIds = new Set(all.map((row) => String(row.idea_id || "").trim().toUpperCase()).filter(Boolean));
    const BACKLOG_LIST_WINDOW_THRESHOLD = 180;
    const BACKLOG_LIST_OVERSCAN = 24;
    const BACKLOG_LIST_ROW_HEIGHT = 88;
    const BACKLOG_LIST_HEADER_HEIGHT = 40;
    let latestRenderedRows = [];
    let latestListWindowKey = "";
    let listScrollFrame = 0;
    const WORKSTREAM_ID_COMPACT_RE = /^B?-?(\\d{1,})$/i;

    function handleLinkedWorkstreamClick(event) {
      const trigger = event.target.closest("[data-link-idea]");
      if (!trigger) return;
      event.preventDefault();
      const ideaId = String(trigger.getAttribute("data-link-idea") || "").trim();
      if (!selectIdea(ideaId, { reveal: true })) return;
      render();
      el.detail?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    el.detail.addEventListener("click", handleLinkedWorkstreamClick);
    if (el.analyticsPanel) {
      el.analyticsPanel.addEventListener("toggle", () => {
        syncAnalyticsToggleHint();
        try {
          window.localStorage.setItem(ANALYTICS_OPEN_PREF_KEY, el.analyticsPanel.open ? "1" : "0");
        } catch (_error) {
          // ignore localStorage write failures
        }
        void renderAnalytics(sortRows(applyFilters()));
      });
    }
    el.list.addEventListener("scroll", () => {
      if (latestRenderedRows.length <= BACKLOG_LIST_WINDOW_THRESHOLD) return;
      if (listScrollFrame) return;
      listScrollFrame = window.requestAnimationFrame(() => {
        listScrollFrame = 0;
        renderList(latestRenderedRows, { fromScroll: true });
      });
    });

    function uniqueValues(field) {
      return [...new Set(all.map((row) => String(row[field] || "").trim()).filter(Boolean))].sort();
    }

    function stageLabel(value) {
      const token = String(value || "").trim().toLowerCase();
      if (token === "queued") return "idea";
      return token || "unknown";
    }

    function normalizeSearchToken(value) {
      return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "");
    }

    function canonicalizeIdeaId(value) {
      const token = String(value || "").trim().toUpperCase();
      if (!token) return "";
      if (allIdeaIds.has(token)) return token;
      const compact = token.match(WORKSTREAM_ID_COMPACT_RE);
      if (!compact) return "";
      const normalized = `B-${compact[1].padStart(3, "0")}`;
      return allIdeaIds.has(normalized) ? normalized : "";
    }

    function isExactIdeaIdQuery(query) {
      return Boolean(canonicalizeIdeaId(query));
    }

    function rowMatchesQuery(row, query, exactIdeaQuery) {
      if (!query) return true;
      const canonicalIdeaQuery = exactIdeaQuery ? canonicalizeIdeaId(query) : "";
      const ideaId = String(row.idea_id || "").trim().toUpperCase();
      if (canonicalIdeaQuery) {
        return ideaId === canonicalIdeaQuery;
      }
      const textParts = [
        row.idea_id,
        row.title,
        row.ordering_rationale,
        row.rationale_text,
        Array.isArray(row.rationale_bullets) ? row.rationale_bullets.join(" ") : "",
      ];
      const hay = String(row.search_text || textParts.join(" ")).toLowerCase();
      if (hay.includes(query)) return true;
      const normalizedQuery = normalizeSearchToken(query);
      if (!normalizedQuery) return false;
      return normalizeSearchToken(textParts.join(" ")).includes(normalizedQuery);
    }

    function rowMatchesFilters(row, options = {}) {
      const query = String(options.query ?? state.query).trim().toLowerCase();
      const exactIdeaQuery = Boolean(options.exactIdeaQuery ?? isExactIdeaIdQuery(query));
      if (state.section !== "all" && row.section !== state.section) return false;
      if (state.phase !== "all") {
        if (row.section !== "execution") return false;
        if (stageLabel(row.status) !== state.phase) return false;
      }
      if (state.type !== "all" && workstreamTypeInfo(row).type !== state.type) return false;
      if (state.activity !== "all") {
        if (row.section !== "execution") return false;
        const stateToken = normalizeExecutionState(row.execution_state);
        const activity = (
          stateToken === "actively_executing"
          || stateToken === "planning_active"
        ) ? "active" : "quiet";
        if (activity !== state.activity) return false;
      }
      if (state.priority !== "all" && row.priority !== state.priority) return false;
      if (state.release !== "all" && workstreamActiveReleaseId(row) !== state.release) return false;
      return rowMatchesQuery(row, query, exactIdeaQuery);
    }

    function prettyLabel(value) {
      const token = String(value || "").trim();
      if (!token) return "-";
      if (token.includes("-")) return token;
      return token.charAt(0).toUpperCase() + token.slice(1);
    }

    function syncParentShellSelection() {
      try {
        if (!window.parent || window.parent === window) return;
        window.parent.postMessage({
          type: "odylith-radar-navigate",
          state: {
            workstream: String(state.selectedIdeaId || "").trim(),
            view: "",
          },
        }, "*");
      } catch (_error) {
        // Ignore parent-shell sync failures; local radar interactions must still work.
      }
    }

    function formatCompactTimestamp(value) {
      const token = String(value || "").trim();
      if (!token) return "-";
      const parsed = Date.parse(token);
      if (Number.isNaN(parsed)) return token;
      const ts = new Date(parsed);
      const formatter = new Intl.DateTimeFormat([], {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZoneName: "short",
      });
      const partLookup = Object.fromEntries(
        formatter.formatToParts(ts).map((part) => [part.type, part.value]),
      );
      return [
        partLookup.month || "",
        partLookup.day || "",
        (partLookup.hour && partLookup.minute) ? `${partLookup.hour}:${partLookup.minute}` : "",
        partLookup.timeZoneName || "",
      ].filter(Boolean).join(" ");
    }

    function seedSelect(select, values, formatter) {
      values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = formatter ? formatter(value) : value;
        select.appendChild(option);
      });
    }

    seedSelect(el.priority, uniqueValues("priority"));
    seedSelect(
      el.release,
      releaseCatalog()
        .map((row) => String(row && row.release_id ? row.release_id : "").trim())
        .filter(Boolean),
      (value) => {
        const release = releaseCatalog().find((row) => String(row && row.release_id ? row.release_id : "").trim() === value) || {};
        return releaseLabel(release) || value;
      },
    );

    function syncFilterControls() {
      el.query.value = state.query;
      el.section.value = state.section;
      if (el.legacySection) el.legacySection.value = state.section;
      el.phase.value = state.phase;
      el.type.value = state.type;
      el.activity.value = state.activity;
      el.priority.value = state.priority;
      el.release.value = state.release;
    }

    // Explicit deep-link navigation must reveal the requested workstream instead of
    // silently falling back to the first row that still matches stale filters.
    function revealIdeaSelection(ideaId) {
      const row = all.find((candidate) => String(candidate.idea_id || "").trim() === ideaId);
      if (!row) return false;
      const query = String(state.query || "").trim().toLowerCase();
      const exactIdeaQuery = isExactIdeaIdQuery(query);
      if (!rowMatchesQuery(row, query, exactIdeaQuery)) {
        state.query = "";
      }
      if (!rowMatchesFilters(row, { query: "", exactIdeaQuery: false })) {
        if (state.section !== "all" && row.section !== state.section) {
          state.section = "all";
        }
        if (state.phase !== "all") {
          if (row.section !== "execution" || stageLabel(row.status) !== state.phase) {
            state.phase = "all";
          }
        }
        if (state.activity !== "all") {
          const stateToken = normalizeExecutionState(row.execution_state);
          const activity = (
            stateToken === "actively_executing"
            || stateToken === "planning_active"
          ) ? "active" : "quiet";
          if (row.section !== "execution" || activity !== state.activity) {
            state.activity = "all";
          }
        }
        if (state.type !== "all" && workstreamTypeInfo(row).type !== state.type) {
          state.type = "all";
        }
        if (state.priority !== "all" && row.priority !== state.priority) {
          state.priority = "all";
        }
      }
      syncFilterControls();
      return true;
    }

    function selectIdea(ideaId, options = {}) {
      const token = canonicalizeIdeaId(ideaId);
      if (!token || !allIdeaIds.has(token)) return false;
      if (options.reveal) {
        revealIdeaSelection(token);
      }
      state.selectedIdeaId = token;
      return true;
    }

    function escapeHtml(value) {
      return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function tooltipLookupPayload() {
      const payload = DATA.tooltip_lookup;
      return payload && typeof payload === "object" ? payload : {};
    }

    function sanitizeLookupObject(value) {
      const lookup = Object.create(null);
      if (!value || typeof value !== "object") return lookup;
      Object.entries(value).forEach(([keyRaw, valueRaw]) => {
        const key = String(keyRaw || "").trim();
        const text = String(valueRaw || "").trim();
        if (!key || !text) return;
        lookup[key] = text;
      });
      return lookup;
    }

    function sanitizeLookupListObject(value) {
      const lookup = Object.create(null);
      if (!value || typeof value !== "object") return lookup;
      Object.entries(value).forEach(([keyRaw, valueRaw]) => {
        const key = normalizeDiagramId(keyRaw);
        if (!key || !Array.isArray(valueRaw)) return;
        const tokens = normalizeIdList(valueRaw);
        if (!tokens.length) return;
        lookup[key] = tokens;
      });
      return lookup;
    }

    function normalizeDiagramId(value) {
      let token = String(value || "").trim().toUpperCase();
      if (!token) return "";
      if (token.startsWith("DIAGRAM:")) {
        token = token.slice("DIAGRAM:".length).trim();
      }
      if (/^D-\\d{3,}$/.test(token)) {
        return token;
      }
      const compact = token.match(/^D(\\d{3,})$/);
      if (compact) {
        return `D-${compact[1]}`;
      }
      return "";
    }

    const rawTooltipLookup = tooltipLookupPayload();
    const workstreamTitleLookup = sanitizeLookupObject(rawTooltipLookup.workstream_titles);
    const diagramTitleLookup = sanitizeLookupObject(rawTooltipLookup.diagram_titles);
    const componentTitleLookup = sanitizeLookupObject(rawTooltipLookup.component_titles);
    const diagramWorkstreamLookup = sanitizeLookupListObject(rawTooltipLookup.diagram_related_workstreams);

    function workstreamTooltip(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) return "";
      return workstreamTitleLookup[token] || token;
    }

    function diagramTooltip(diagramId) {
      const token = normalizeDiagramId(diagramId);
      if (!token) return "";
      return diagramTitleLookup[token] || token;
    }

    function atlasDiagramHref(diagramId, selectedIdeaId) {
      const token = normalizeDiagramId(diagramId);
      if (!token) return "../../odylith/index.html?tab=atlas";
      const workstreamId = String(selectedIdeaId || "").trim();
      const owners = Array.isArray(diagramWorkstreamLookup[token]) ? diagramWorkstreamLookup[token] : [];
      if (workstreamId && owners.includes(workstreamId)) {
        return `../../odylith/index.html?tab=atlas&workstream=${encodeURIComponent(workstreamId)}&diagram=${encodeURIComponent(token)}`;
      }
      return `../../odylith/index.html?tab=atlas&diagram=${encodeURIComponent(token)}`;
    }

    function componentTooltip(componentId, fallback = "") {
      const token = String(componentId || "").trim().toLowerCase();
      const fallbackText = String(fallback || "").trim();
      if (!token) return fallbackText;
      return componentTitleLookup[token] || fallbackText || token;
    }

    function syncAnalyticsToggleHint() {
      const expanded = Boolean(el.analyticsPanel && el.analyticsPanel.open);
      if (el.analyticsToggleHint) {
        el.analyticsToggleHint.textContent = expanded ? "Hide" : "Show";
      }
    }

    function setAnalyticsExpanded(expanded) {
      if (!el.analyticsPanel) return;
      el.analyticsPanel.open = Boolean(expanded);
      syncAnalyticsToggleHint();
    }

    function loadAnalyticsPreference() {
      let saved = "";
      try {
        saved = String(window.localStorage.getItem(ANALYTICS_OPEN_PREF_KEY) || "").trim();
      } catch (_error) {
        saved = "";
      }
      if (saved === "1") {
        setAnalyticsExpanded(true);
        return;
      }
      if (saved === "0") {
        setAnalyticsExpanded(false);
        return;
      }
      syncAnalyticsToggleHint();
    }

    function statBlock(label, value, options = {}) {
      const releaseOnly = Boolean(options && options.releaseOnly);
      const classes = releaseOnly ? "stat stat-release-only" : "stat";
      const labelHtml = label ? `<div class="label">${escapeHtml(label)}</div>` : "";
      return `<div class="${classes}">${labelHtml}<div class="value">${escapeHtml(value)}</div></div>`;
    }

    function summarizeVisibleSections(rows) {
      const counts = {
        queued: 0,
        execution: 0,
        parked: 0,
        finished: 0,
      };
      (Array.isArray(rows) ? rows : []).forEach((row) => {
        const section = String(row && row.section ? row.section : "").trim().toLowerCase();
        if (section === "execution") {
          counts.execution += 1;
          return;
        }
        if (section === "parked") {
          counts.parked += 1;
          return;
        }
        if (section === "finished") {
          counts.finished += 1;
          return;
        }
        if (section === "active") {
          counts.queued += 1;
        }
      });
      return counts;
    }

    function summaryStatRows(rows, waveSummary) {
      const counts = summarizeVisibleSections(rows);
      const wavePrograms = Number(waveSummary && waveSummary.program_count ? waveSummary.program_count : 0);
      const activeWaves = Number(waveSummary && waveSummary.active_wave_count ? waveSummary.active_wave_count : 0);
      const traceability = traceabilityPayload();
      const currentRelease = traceability && traceability.current_release && typeof traceability.current_release === "object"
        ? traceability.current_release
        : {};
      const statRows = [
        statBlock("Index Updated", DATA.index_updated_display || "-"),
        statBlock("Queued", counts.queued),
        statBlock("Execution", counts.execution),
        statBlock("Parked", counts.parked),
        statBlock("Finished", counts.finished),
      ];
      if (wavePrograms > 0) {
        statRows.push(statBlock("Active Waves", activeWaves));
      }
      if (releaseCardLabel(currentRelease)) {
        statRows.push(statBlock("Target Release", releaseCardLabel(currentRelease), { releaseOnly: true }));
      }
      return statRows;
    }

    function parseIsoDateToken(value) {
      const token = String(value || "").trim();
      if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(token)) return null;
      const parsed = new Date(`${token}T00:00:00Z`);
      if (Number.isNaN(parsed.getTime())) return null;
      return parsed;
    }

    function toIsoDate(value) {
      return value.toISOString().slice(0, 10);
    }

    function toWeekBucket(value) {
      const copy = new Date(value.getTime());
      const day = (copy.getUTCDay() + 6) % 7;
      copy.setUTCDate(copy.getUTCDate() - day);
      return toIsoDate(copy);
    }

    function fromIsoDateToken(value) {
      return parseIsoDateToken(value);
    }

    function shiftDays(value, days) {
      const copy = new Date(value.getTime());
      copy.setUTCDate(copy.getUTCDate() + days);
      return copy;
    }

    function resolveFinishedDate(row) {
      return parseIsoDateToken(
        row.execution_end_date_display
        || row.execution_end_date
        || row.finished_sort_date_display
        || row.finished_sort_date
        || row.idea_date_display
        || row.idea_date
      );
    }

    function resolveExecutionDays(row) {
      const direct = String(row.execution_duration_days || "").trim();
      if (/^\\d+$/.test(direct)) return Number.parseInt(direct, 10);
      const start = parseIsoDateToken(row.execution_start_date_display || row.execution_start_date);
      const end = parseIsoDateToken(row.execution_end_date_display || row.execution_end_date);
      if (!start || !end) return null;
      const delta = Math.floor((end.getTime() - start.getTime()) / 86400000);
      return delta >= 0 ? delta : null;
    }

    function movingAverage(values, windowSize) {
      const out = [];
      for (let idx = 0; idx < values.length; idx += 1) {
        const left = Math.max(0, idx - windowSize + 1);
        const window = values.slice(left, idx + 1);
        const avg = window.reduce((acc, item) => acc + item, 0) / window.length;
        out.push(Number(avg.toFixed(2)));
      }
      return out;
    }

    function percentile(values, p) {
      if (!values.length) return 0;
      const sorted = [...values].sort((a, b) => a - b);
      const pos = Math.max(0, Math.ceil((p / 100) * sorted.length) - 1);
      return sorted[Math.min(pos, sorted.length - 1)];
    }

    function niceCeil(value) {
      if (!Number.isFinite(value) || value <= 0) return 1;
      if (value <= 5) return Math.ceil(value);
      if (value <= 20) return Math.ceil(value / 2) * 2;
      return Math.ceil(value / 5) * 5;
    }

    function buildRecentWeekWindow(rows, weeksCount) {
      let anchor = new Date();
      rows.forEach((row) => {
        const finished = resolveFinishedDate(row);
        if (finished && finished > anchor) anchor = finished;
      });
      const anchorWeek = fromIsoDateToken(toWeekBucket(anchor)) || new Date();
      const window = [];
      for (let idx = weeksCount - 1; idx >= 0; idx -= 1) {
        const weekDate = shiftDays(anchorWeek, -7 * idx);
        const week = toIsoDate(weekDate);
        window.push({ week, label: week.slice(5) });
      }
      return window;
    }

    function buildVelocitySeries(rows, window) {
      const counts = new Map();
      rows
        .filter((row) => row.section === "finished")
        .forEach((row) => {
          const finished = resolveFinishedDate(row);
          if (!finished) return;
          const week = toWeekBucket(finished);
          counts.set(week, (counts.get(week) || 0) + 1);
        });
      const ordered = window.map((item) => ({
        week: item.week,
        label: item.label,
        count: counts.get(item.week) || 0,
      }));
      const ma = movingAverage(ordered.map((item) => item.count), 4);
      return ordered.map((item, idx) => ({ ...item, movingAvg: ma[idx] }));
    }

    function buildCycleSeries(rows, window) {
      const buckets = new Map();
      rows
        .filter((row) => row.section === "finished")
        .forEach((row) => {
          const finished = resolveFinishedDate(row);
          const days = resolveExecutionDays(row);
          if (!finished || days === null) return;
          const week = toWeekBucket(finished);
          const values = buckets.get(week) || [];
          values.push(days);
          buckets.set(week, values);
        });
      return window.map((item) => {
        const values = buckets.get(item.week) || [];
        if (!values.length) {
          return { week: item.week, label: item.label, median: null, p85: null, samples: 0 };
        }
        return {
          week: item.week,
          label: item.label,
          median: percentile(values, 50),
          p85: percentile(values, 85),
          samples: values.length,
        };
      });
    }

    function buildMixSeries(rows, byField, window) {
      const weekly = new Map();
      const totals = new Map();
      const weekSet = new Set(window.map((item) => item.week));
      rows
        .filter((row) => row.section === "finished")
        .forEach((row) => {
          const finished = resolveFinishedDate(row);
          if (!finished) return;
          const week = toWeekBucket(finished);
          if (!weekSet.has(week)) return;
          const categoryRaw = String(row[byField] || "").trim();
          const category = categoryRaw || "unknown";
          const weekBucket = weekly.get(week) || new Map();
          weekBucket.set(category, (weekBucket.get(category) || 0) + 1);
          weekly.set(week, weekBucket);
          totals.set(category, (totals.get(category) || 0) + 1);
        });

      const topCategories = [...totals.entries()]
        .sort((a, b) => {
          if (b[1] !== a[1]) return b[1] - a[1];
          return String(a[0]).localeCompare(String(b[0]));
        })
        .slice(0, 4)
        .map(([label]) => label);
      if (!topCategories.length) {
        return {
          weeks: window.map((item) => item.week),
          labels: window.map((item) => item.label),
          categories: [],
          values: [],
          totalFinished: 0,
          activeWeeks: 0,
        };
      }
      const categories = totals.size > topCategories.length ? [...topCategories, "other"] : [...topCategories];
      const weeks = window.map((item) => item.week);
      const labels = window.map((item) => item.label);

      let totalFinished = 0;
      let activeWeeks = 0;
      const values = weeks.map((week) => {
        const bucket = weekly.get(week) || new Map();
        const row = {};
        let other = 0;
        let weekTotal = 0;
        bucket.forEach((count, key) => {
          if (topCategories.includes(key)) {
            row[key] = count;
            weekTotal += count;
          } else {
            other += count;
          }
        });
        if (categories.includes("other")) {
          row.other = other;
          weekTotal += other;
        }
        totalFinished += weekTotal;
        if (weekTotal > 0) activeWeeks += 1;
        return row;
      });

      return { weeks, labels, categories, values, totalFinished, activeWeeks };
    }

    function buildPath(points, getX, getY, key) {
      const path = [];
      let open = false;
      points.forEach((point, idx) => {
        const value = point[key];
        if (!Number.isFinite(value)) {
          open = false;
          return;
        }
        path.push(`${open ? "L" : "M"}${getX(idx)},${getY(value)}`);
        open = true;
      });
      return path.join(" ");
    }

    function renderLineChart(target, points, config) {
      if (!points.length) {
        target.innerHTML = "";
        return;
      }
      const finiteValues = points
        .flatMap((point) => [point[config.primaryKey], point[config.secondaryKey]])
        .filter((value) => Number.isFinite(value));
      if (!finiteValues.length) {
        target.innerHTML = "";
        return;
      }
      const width = 560;
      const height = 220;
      const margin = { top: 12, right: 10, bottom: 30, left: 38 };
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const xAt = (idx) => (
        points.length <= 1
          ? margin.left + (plotWidth / 2)
          : margin.left + ((idx / (points.length - 1)) * plotWidth)
      );

      const yMax = niceCeil(Math.max(...finiteValues));
      const yAt = (value) => margin.top + ((yMax - value) / yMax) * plotHeight;

      const primaryPath = buildPath(points, xAt, yAt, config.primaryKey);
      const secondaryPath = buildPath(points, xAt, yAt, config.secondaryKey);
      const yTicks = [...new Set([0, Number((yMax / 2).toFixed(1)), yMax])];
      const xLabelStep = Math.max(1, Math.ceil(points.length / 6));

      const gridHtml = yTicks
        .map((tick) => {
          const y = yAt(tick);
          return `
            <line class="chart-grid" x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" />
            <text class="chart-axis" x="${margin.left - 6}" y="${y + 3}" text-anchor="end">${tick}</text>
          `;
        })
        .join("");

      const barsHtml = config.barsKey
        ? points
          .map((point, idx) => {
            const value = point[config.barsKey];
            if (!Number.isFinite(value) || value <= 0) return "";
            const slotWidth = points.length <= 1 ? plotWidth : plotWidth / points.length;
            const barWidth = Math.max(7, slotWidth * 0.62);
            const x = points.length <= 1
              ? margin.left + (plotWidth / 2) - (barWidth / 2)
              : margin.left + (idx * slotWidth) + ((slotWidth - barWidth) / 2);
            const y = yAt(value);
            const h = (margin.top + plotHeight) - y;
            return `<rect class="chart-bar-primary" x="${x}" y="${y}" width="${barWidth}" height="${Math.max(1, h)}"></rect>`;
          })
          .join("")
        : "";

      const xLabelsHtml = points
        .map((point, idx) => {
          if (idx % xLabelStep !== 0 && idx !== points.length - 1) return "";
          return `<text class="chart-axis" x="${xAt(idx)}" y="${height - 8}" text-anchor="middle">${escapeHtml(point.label)}</text>`;
        })
        .join("");

      const primaryPoints = points
        .map((point, idx) => (
          Number.isFinite(point[config.primaryKey])
            ? `<circle class="chart-point-primary" cx="${xAt(idx)}" cy="${yAt(point[config.primaryKey])}" r="3"></circle>`
            : ""
        ))
        .join("");
      const secondaryPoints = points
        .map((point, idx) => (
          Number.isFinite(point[config.secondaryKey])
            ? `<circle class="chart-point-secondary" cx="${xAt(idx)}" cy="${yAt(point[config.secondaryKey])}" r="3"></circle>`
            : ""
        ))
        .join("");

      target.innerHTML = `
        <div class="chart-wrap">
          <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(config.ariaLabel)}">
            ${gridHtml}
            ${barsHtml}
            <path class="chart-line-primary" d="${primaryPath}"></path>
            <path class="chart-line-secondary" d="${secondaryPath}"></path>
            ${primaryPoints}
            ${secondaryPoints}
            ${xLabelsHtml}
          </svg>
        </div>
        <div class="chart-legend">
          <span class="legend-item"><span class="legend-dot" style="background:#0f766e"></span>${escapeHtml(config.primaryLabel)}</span>
          <span class="legend-item"><span class="legend-dot" style="background:#2563eb"></span>${escapeHtml(config.secondaryLabel)}</span>
          ${config.barsLabel ? `<span class="legend-item"><span class="legend-dot" style="background:rgba(37,99,235,0.55)"></span>${escapeHtml(config.barsLabel)}</span>` : ""}
        </div>
        ${config.summaryText ? `<div class="graph-note">${escapeHtml(config.summaryText)}</div>` : ""}
      `;
    }

    function renderMixChart(target, mixData, byField) {
      if (!mixData.weeks.length || !mixData.categories.length) {
        target.innerHTML = "";
        return;
      }
      const width = 560;
      const height = 220;
      const margin = { top: 12, right: 10, bottom: 30, left: 38 };
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const palette = ["#0f766e", "#2563eb", "#ea580c", "#7c3aed", "#dc2626"];
      const colorByCategory = new Map(mixData.categories.map((category, idx) => [category, palette[idx % palette.length]]));

      const totalsByWeek = mixData.values.map((row) =>
        mixData.categories.reduce((sum, category) => sum + Number(row[category] || 0), 0)
      );
      const yMax = Math.max(1, ...totalsByWeek);
      const xLabelStep = Math.max(1, Math.ceil(mixData.weeks.length / 6));

      const barGap = 8;
      const slotWidth = plotWidth / mixData.weeks.length;
      const barWidth = Math.max(10, slotWidth - barGap);

      const yAt = (value) => margin.top + ((yMax - value) / yMax) * plotHeight;
      const yTicks = [0, Math.round(yMax / 2), yMax];

      const gridHtml = yTicks
        .map((tick) => {
          const y = yAt(tick);
          return `
            <line class="chart-grid" x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" />
            <text class="chart-axis" x="${margin.left - 6}" y="${y + 3}" text-anchor="end">${tick}</text>
          `;
        })
        .join("");

      const barsHtml = mixData.weeks
        .map((week, idx) => {
          const row = mixData.values[idx];
          let running = 0;
          const x = margin.left + idx * slotWidth + Math.max(0, (slotWidth - barWidth) / 2);
          const segments = mixData.categories.map((category) => {
            const count = Number(row[category] || 0);
            if (!count) return "";
            const yBottom = yAt(running);
            running += count;
            const yTop = yAt(running);
            const heightRect = Math.max(1, yBottom - yTop);
            return `<rect x="${x}" y="${yTop}" width="${barWidth}" height="${heightRect}" fill="${colorByCategory.get(category)}"></rect>`;
          }).join("");
          return segments;
        })
        .join("");

      const xLabelsHtml = mixData.weeks
        .map((week, idx) => {
          if (idx % xLabelStep !== 0 && idx !== mixData.weeks.length - 1) return "";
          const x = margin.left + idx * slotWidth + (slotWidth / 2);
          const label = Array.isArray(mixData.labels) ? mixData.labels[idx] : week.slice(5);
          return `<text class="chart-axis" x="${x}" y="${height - 8}" text-anchor="middle">${escapeHtml(label)}</text>`;
        })
        .join("");

      const legendHtml = mixData.categories
        .map((category) => {
          const label = category === "other" ? "Other" : category;
          return `<span class="legend-item"><span class="legend-dot" style="background:${colorByCategory.get(category)}"></span>${escapeHtml(label)}</span>`;
        })
        .join("");

      target.innerHTML = `
        <div class="chart-wrap">
          <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Delivery mix by ${escapeHtml(byField)} over time">
            ${gridHtml}
            ${barsHtml}
            ${xLabelsHtml}
          </svg>
        </div>
        <div class="chart-legend">${legendHtml}</div>
        <div class="graph-note">Last ${mixData.weeks.length}w: ${mixData.totalFinished} completed across ${mixData.activeWeeks} active week(s).</div>
      `;
    }

    function syncMixToggleUi() {
      const complexityActive = state.mixBy === "complexity";
      el.mixByComplexity.classList.toggle("active", complexityActive);
      el.mixBySize.classList.toggle("active", !complexityActive);
    }

    function renderGraphs(rows) {
      const weekWindow = buildRecentWeekWindow(rows, 12);
      const velocity = buildVelocitySeries(rows, weekWindow);
      const velocityTotal = velocity.reduce((sum, item) => sum + Number(item.count || 0), 0);
      const velocityAvg = (velocityTotal / Math.max(1, velocity.length)).toFixed(2);
      renderLineChart(el.graphVelocity, velocity, {
        primaryKey: "count",
        secondaryKey: "movingAvg",
        primaryLabel: "Finished/week",
        secondaryLabel: "4-week moving avg",
        barsKey: "count",
        barsLabel: "Finished bars",
        ariaLabel: "Execution velocity trend",
        summaryText: `Last ${velocity.length}w: ${velocityTotal} completed · avg ${velocityAvg}/week.`,
      });

      const cycle = buildCycleSeries(rows, weekWindow);
      const weeksWithSamples = cycle.filter((item) => item.samples > 0).length;
      const latestCycle = [...cycle].reverse().find((item) => item.samples > 0);
      const lowSample = cycle.reduce((sum, item) => sum + Number(item.samples || 0), 0) < 3;
      renderLineChart(el.graphCycle, cycle, {
        primaryKey: "median",
        secondaryKey: "p85",
        primaryLabel: "Median days",
        secondaryLabel: "P85 days",
        ariaLabel: "Cycle time trend",
        summaryText: latestCycle
          ? `Weeks with samples: ${weeksWithSamples}/${cycle.length} · latest median ${latestCycle.median}d, p85 ${latestCycle.p85}d${lowSample ? " (low sample confidence)." : "."}`
          : "",
      });

      syncMixToggleUi();
      const field = state.mixBy === "size" ? "sizing" : "complexity";
      renderMixChart(el.graphMix, buildMixSeries(rows, field, weekWindow), field);
    }

    function renderAnalytics(rows) {
      if (!el.analyticsPanel || !el.analyticsPanel.open) {
        el.graphVelocity.innerHTML = "";
        el.graphCycle.innerHTML = "";
        el.graphMix.innerHTML = "";
        syncMixToggleUi();
        return;
      }
      renderGraphs(rows);
    }

    function applyFilters() {
      const q = state.query.trim().toLowerCase();
      const exactIdeaQuery = isExactIdeaIdQuery(q);
      return all.filter((row) => rowMatchesFilters(row, { query: q, exactIdeaQuery }));
    }

    function scopeSignalRank(row) {
      const signal = row && typeof row.scope_signal === "object" ? row.scope_signal : {};
      const numeric = Number(signal.rank);
      if (Number.isFinite(numeric)) return numeric;
      const rung = String(signal.rung || "").trim().toUpperCase();
      if (/^R\\d+$/.test(rung)) return Number.parseInt(rung.slice(1), 10);
      const direct = Number(row && row.scope_signal_rank);
      return Number.isFinite(direct) ? direct : 0;
    }

    function sortRows(rows) {
      const sectionOrder = { execution: 0, parked: 1, active: 2, finished: 3 };
      const executionStatusOrder = { implementation: 0, planning: 1 };
      const executionStateOrder = {
        actively_executing: 0,
        planning_active: 1,
        planned_only: 2,
        implementation_no_live_signal: 2,
        inactive: 3,
      };
      const copy = [...rows];
      copy.sort((a, b) => {
        if (a.section !== b.section) return (sectionOrder[a.section] ?? 99) - (sectionOrder[b.section] ?? 99);
        if (a.section !== "finished") {
          const rankDelta = scopeSignalRank(b) - scopeSignalRank(a);
          if (rankDelta !== 0) return rankDelta;
        }
        if (a.section === "execution") {
          const leftState = executionStateOrder[normalizeExecutionState(a.execution_state)] ?? 99;
          const rightState = executionStateOrder[normalizeExecutionState(b.execution_state)] ?? 99;
          if (leftState !== rightState) return leftState - rightState;
          const left = executionStatusOrder[String(a.status || "").toLowerCase()] ?? 99;
          const right = executionStatusOrder[String(b.status || "").toLowerCase()] ?? 99;
          if (left !== right) return left - right;
          if (b.ordering_score !== a.ordering_score) return b.ordering_score - a.ordering_score;
          if (state.sort === "date") {
            const dateCmp = String(b.date).localeCompare(String(a.date));
            if (dateCmp !== 0) return dateCmp;
          }
        }
        if (a.section === "finished") {
          const completedCmp = String(b.finished_sort_date || b.date).localeCompare(
            String(a.finished_sort_date || a.date)
          );
          if (completedCmp !== 0) return completedCmp;
          const planDateCmp = String(b.plan_file_date || "").localeCompare(
            String(a.plan_file_date || "")
          );
          if (planDateCmp !== 0) return planDateCmp;
          const updatedCmp = String(b.plan_updated_date || "").localeCompare(
            String(a.plan_updated_date || "")
          );
          if (updatedCmp !== 0) return updatedCmp;
        }
        if (a.section === "parked") {
          const updatedCmp = String(b.plan_updated_date || "").localeCompare(
            String(a.plan_updated_date || "")
          );
          if (updatedCmp !== 0) return updatedCmp;
          const dateCmp = String(b.date).localeCompare(String(a.date));
          if (dateCmp !== 0) return dateCmp;
        }
        if (a.section !== "finished" && (state.sort === "score" || a.section === "execution")) {
          if (b.ordering_score !== a.ordering_score) return b.ordering_score - a.ordering_score;
        } else if (a.section !== "finished" && state.sort === "date") {
          const dateCmp = String(b.date).localeCompare(String(a.date));
          if (dateCmp !== 0) return dateCmp;
        }
        if (a.rank_num !== b.rank_num) return a.rank_num - b.rank_num;
        return String(a.idea_id).localeCompare(String(b.idea_id));
      });
      return copy;
    }

    function statusChipClass(status) {
      const token = stageLabel(status);
      if (token === "planning") return "status-chip status-planning";
      if (token === "implementation") return "status-chip status-implementation";
      if (token === "parked") return "status-chip status-parked";
      if (token === "finished") return "status-chip status-finished";
      return "status-chip";
    }

    function executionStageLabel(status) {
      const token = stageLabel(status);
      if (token === "planning") return "Planning";
      if (token === "implementation") return "Implementation";
      if (token === "finished") return "Finished";
      if (token === "idea") return "Idea";
      return prettyLabel(token);
    }

    function normalizeExecutionState(value) {
      const token = String(value || "").trim().toLowerCase();
      if (
        token === "actively_executing"
        || token === "planning_active"
        || token === "planned_only"
        || token === "implementation_no_live_signal"
        || token === "inactive"
      ) {
        return token;
      }
      return "inactive";
    }

    function executionStateLabel(value) {
      const token = normalizeExecutionState(value);
      if (token === "actively_executing") return "Live: Active";
      if (token === "planning_active") return "Plan: Active";
      if (token === "planned_only") return "Plan: Quiet";
      if (token === "implementation_no_live_signal") return "Live: Quiet";
      return "Live: Quiet";
    }

    function executionSignalTooltip(status, value, activeWindowMinutes) {
      const stage = executionStageLabel(status);
      const token = normalizeExecutionState(value);
      const windowMinutes = Number.isFinite(Number(activeWindowMinutes)) && Number(activeWindowMinutes) > 0
        ? Math.round(Number(activeWindowMinutes))
        : 15;
      const activityLabel = stage === "Planning"
        ? "odylith/technical-plans/spec activity"
        : (stage === "Implementation" ? "code/test activity" : "workstream activity");
      if (token === "actively_executing" || token === "planning_active") {
        return `${stage} phase with active ${activityLabel} in the last ${windowMinutes} minutes.`;
      }
      return `${stage} phase with quiet ${activityLabel} in the last ${windowMinutes} minutes.`;
    }

    function executionActiveWindowMinutes(meta) {
      const raw = meta && typeof meta === "object" ? Number(meta.active_window_minutes) : NaN;
      if (Number.isFinite(raw) && raw > 0) {
        return Math.round(raw);
      }
      return 15;
    }

    function executionStateClass(value) {
      const token = normalizeExecutionState(value);
      if (token === "actively_executing") return "exec-actively-executing";
      if (token === "planning_active") return "exec-planning-active";
      if (token === "planned_only") return "exec-planned-only";
      if (token === "implementation_no_live_signal") return "exec-implementation-no-live-signal";
      if (token === "inactive") return "exec-signal-quiet";
      return "";
    }

    function sectionBadgeInfo(row) {
      const section = String(row && row.section ? row.section : "").trim().toLowerCase();
      if (section === "execution") {
        return { label: "Pipeline", chipClassName: "rank-chip-execution", kpiClassName: "kpi-section-execution" };
      }
      if (section === "finished") {
        return { label: "Finished", chipClassName: "rank-chip-finished", kpiClassName: "kpi-section-finished" };
      }
      if (section === "parked") {
        return { label: "Parked", chipClassName: "rank-chip-parked", kpiClassName: "kpi-section-parked" };
      }
      return { label: `Rank #${row.rank}`, chipClassName: "rank-chip-active", kpiClassName: "kpi-section-active" };
    }

    function rowHtml(row) {
      const sectionBadge = sectionBadgeInfo(row);
      const activeClass = row.idea_id === state.selectedIdeaId ? "active" : "";
      const ageRaw = String(row.idea_age_days || "-");
      const ageLabel = /^\\d+$/.test(ageRaw) ? `${ageRaw}d` : ageRaw;
      const executionDaysRaw = String(row.execution_duration_days || row.execution_age_days || "-");
      const executionDays = /^\\d+$/.test(executionDaysRaw) ? `${executionDaysRaw}d` : "n/a";
      const wsType = workstreamTypeInfo(row);
      const typeChips = (() => {
        if (wsType.type === "umbrella") {
          return `<span class="chip ws-umbrella">Umbrella</span>`;
        }
        if (wsType.type === "child") {
          const parentToken = compactWorkstreamId(wsType.parent);
          const childLabel = parentToken ? `↳ ${parentToken}` : "↳";
          const parentTooltip = workstreamTooltip(wsType.parent);
          const tooltip = parentTooltip ? `Parent workstream: ${parentTooltip}` : "";
          const tooltipAttrs = tooltip
            ? ` data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}"`
            : "";
          return `<span class="chip ws-child"${tooltipAttrs}>${escapeHtml(childLabel)}</span>`;
        }
        return "";
      })();
      const executionState = String(row.execution_state || "").trim().toLowerCase();
      const executionMeta = row.execution_state_meta && typeof row.execution_state_meta === "object"
        ? row.execution_state_meta
        : {};
      const activeWindowMinutes = executionActiveWindowMinutes(executionMeta);
      const stageChip = row.section === "execution" || row.section === "parked"
        ? `<span class="chip ${escapeHtml(statusChipClass(row.status))}" data-tooltip="Canonical backlog stage for this workstream.">${escapeHtml(executionStageLabel(row.status))}</span>`
        : "";
      const executionChip = row.section === "execution"
        ? `<span class="chip execution-chip ${escapeHtml(executionStateClass(executionState))}" data-tooltip="${escapeHtml(executionSignalTooltip(row.status, executionState, activeWindowMinutes))}">${escapeHtml(executionStateLabel(executionState))}</span>`
        : "";
      const releaseChip = workstreamActiveReleaseLabel(row)
        ? `<span class="chip" data-tooltip="Active target release for this workstream.">${escapeHtml(workstreamActiveReleaseLabel(row))}</span>`
        : "";
      const waveChips = executionWaveRoleChips(row);
      const footerChips = `${waveChips}${typeChips}${stageChip}${executionChip}${releaseChip}`;
      return `
        <button class="row ${activeClass}" data-idea-id="${escapeHtml(row.idea_id)}">
          <div class="row-top">
            <span class="rank-chip ${escapeHtml(sectionBadge.chipClassName)}">${escapeHtml(sectionBadge.label)}</span>
            <strong class="row-title">${escapeHtml(row.title)}</strong>
          </div>
          <div class="row-meta">
            <p class="row-id">${escapeHtml(row.idea_id)}</p>
            <div class="row-chips row-chips-end">
              <span class="chip">Age ${escapeHtml(ageLabel)}</span>
              <span class="chip">Exec ${escapeHtml(executionDays)}</span>
            </div>
          </div>
          <div class="row-foot">
            ${footerChips ? `<div class="row-chips row-chips-end">${footerChips}</div>` : ""}
          </div>
        </button>
      `;
    }

    function sectionLabel(section) {
      if (section === "execution") return "Delivery Pipeline";
      if (section === "active") return "Idea Stage";
      if (section === "parked") return "Parked";
      if (section === "finished") return "Finished";
      return "Other";
    }

    function backlogListItemHeight(item) {
      return item && item.kind === "header" ? BACKLOG_LIST_HEADER_HEIGHT : BACKLOG_LIST_ROW_HEIGHT;
    }

    function buildBacklogListItems(rows) {
      const sectionOrder = ["execution", "parked", "active", "finished"];
      const items = [];
      sectionOrder.forEach((sectionKey) => {
        const grouped = rows.filter((row) => row.section === sectionKey);
        if (!grouped.length) return;
        items.push({
          kind: "header",
          key: `header:${sectionKey}`,
          sectionKey,
          label: sectionLabel(sectionKey),
          count: grouped.length,
        });
        grouped.forEach((row) => {
          items.push({ kind: "row", key: `row:${row.idea_id}`, row });
        });
      });
      const ungrouped = rows.filter((row) => !sectionOrder.includes(String(row.section || "")));
      if (ungrouped.length) {
        items.push({
          kind: "header",
          key: "header:other",
          sectionKey: "other",
          label: "Other",
          count: ungrouped.length,
        });
        ungrouped.forEach((row) => {
          items.push({ kind: "row", key: `row:${row.idea_id}`, row });
        });
      }
      return items;
    }

    function backlogListOffsetForIndex(items, index) {
      let offset = 0;
      for (let cursor = 0; cursor < index; cursor += 1) {
        offset += backlogListItemHeight(items[cursor]);
      }
      return offset;
    }

    function ensureBacklogSelectionVisible(items, selectedIdeaId) {
      if (items.length <= BACKLOG_LIST_WINDOW_THRESHOLD) return;
      const selectedIndex = items.findIndex((item) => item.kind === "row" && item.row.idea_id === selectedIdeaId);
      if (selectedIndex < 0) return;
      const viewportHeight = Math.max(1, Number(el.list.clientHeight || 640));
      const scrollTop = Number(el.list.scrollTop || 0);
      const top = backlogListOffsetForIndex(items, selectedIndex);
      const bottom = top + BACKLOG_LIST_ROW_HEIGHT;
      if (top >= scrollTop && bottom <= (scrollTop + viewportHeight)) return;
      el.list.scrollTop = Math.max(0, top - Math.max(24, Math.round(viewportHeight * 0.3)));
    }

    function elementFullyVisibleWithinContainer(container, element) {
      if (!container || !element) return false;
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      return elementRect.top >= containerRect.top && elementRect.bottom <= containerRect.bottom;
    }

    function resolveBacklogListWindow(items) {
      if (items.length <= BACKLOG_LIST_WINDOW_THRESHOLD) {
        return { beforePx: 0, afterPx: 0, items, key: `all:${items.length}` };
      }
      const viewportHeight = Math.max(1, Number(el.list.clientHeight || 640));
      const scrollTop = Number(el.list.scrollTop || 0);
      const startPx = Math.max(0, scrollTop - (BACKLOG_LIST_OVERSCAN * BACKLOG_LIST_ROW_HEIGHT));
      const endPx = scrollTop + viewportHeight + (BACKLOG_LIST_OVERSCAN * BACKLOG_LIST_ROW_HEIGHT);
      let cursorPx = 0;
      let startIndex = 0;
      while (startIndex < items.length) {
        const nextPx = cursorPx + backlogListItemHeight(items[startIndex]);
        if (nextPx >= startPx) break;
        cursorPx = nextPx;
        startIndex += 1;
      }
      const beforePx = cursorPx;
      let endIndex = startIndex;
      while (endIndex < items.length && cursorPx < endPx) {
        cursorPx += backlogListItemHeight(items[endIndex]);
        endIndex += 1;
      }
      let afterPx = 0;
      for (let cursor = endIndex; cursor < items.length; cursor += 1) {
        afterPx += backlogListItemHeight(items[cursor]);
      }
      return {
        beforePx,
        afterPx,
        items: items.slice(startIndex, endIndex),
        key: `${startIndex}:${endIndex}`,
      };
    }

    function renderList(rows, options = {}) {
      latestRenderedRows = Array.isArray(rows) ? rows.slice() : [];
      if (!rows.length) {
        el.list.innerHTML = "";
        state.selectedIdeaId = "";
        latestListWindowKey = "empty";
        return;
      }
      if (!rows.some((row) => row.idea_id === state.selectedIdeaId)) {
        state.selectedIdeaId = rows[0].idea_id;
      }
      const items = buildBacklogListItems(rows);
      if (!options.fromScroll && !options.preserveListScroll) {
        ensureBacklogSelectionVisible(items, state.selectedIdeaId);
      }
      const windowed = resolveBacklogListWindow(items);
      if (options.fromScroll && windowed.key === latestListWindowKey) {
        return;
      }
      latestListWindowKey = windowed.key;
      const chunks = [];
      if (windowed.beforePx > 0) {
        chunks.push(`<div class="list-spacer" aria-hidden="true" style="height:${windowed.beforePx}px"></div>`);
      }
      windowed.items.forEach((item) => {
        if (item.kind === "header") {
          const sectionClass = item.sectionKey === "other" ? "" : ` list-section-${escapeHtml(item.sectionKey)}`;
          chunks.push(
            `<div class="list-section-head${sectionClass}">${escapeHtml(item.label)} (${item.count})</div>`
          );
          return;
        }
        chunks.push(rowHtml(item.row));
      });
      if (windowed.afterPx > 0) {
        chunks.push(`<div class="list-spacer" aria-hidden="true" style="height:${windowed.afterPx}px"></div>`);
      }
      el.list.innerHTML = chunks.join("");
      el.list.querySelectorAll(".row").forEach((button) => {
        button.addEventListener("click", () => {
          const preserveListScroll = elementFullyVisibleWithinContainer(el.list, button);
          selectIdea(button.dataset.ideaId || "");
          render({ preserveListScroll });
        });
        const ideaId = String(button.dataset.ideaId || "").trim();
        if (ideaId) {
          button.addEventListener("mouseenter", () => {
            backlogDataSource.prefetch(ideaId);
          });
          button.addEventListener("focus", () => {
            backlogDataSource.prefetch(ideaId);
          });
        }
      });
    }

    function toBulletHtml(row) {
      const bullets = Array.isArray(row.rationale_bullets) ? row.rationale_bullets.filter(Boolean) : [];
      const lines = bullets.length ? bullets : [row.ordering_rationale || "No decision basis recorded."];
      if (lines.length === 1) {
        return `<p>${escapeHtml(lines[0])}</p>`;
      }
      return `<ul class="bullets">${lines.map((line) => renderDecisionBasisLine(line)).join("")}</ul>`;
    }

    function decisionBasisLabel(label) {
      const token = String(label || "").trim().toLowerCase();
      if (token === "why now" || token === "why this moved") return "Why now";
      if (token === "expected outcome" || token === "expected value capture") return "Expected outcome";
      if (token === "tradeoff" || token === "cost/risk tradeoff") return "Tradeoff";
      if (token === "deferred for now" || token === "what is deferred and why") return "Deferred for now";
      if (token === "ranking basis" || token === "override note") return "Ranking basis";
      return humanizeToken(label);
    }

    function renderDecisionBasisLine(line) {
      const raw = String(line || "").trim();
      const match = raw.match(/^([^:]+):\\s*(.+)$/);
      if (!match) return `<li>${escapeHtml(raw)}</li>`;
      const [, label, body] = match;
      return `<li>${escapeHtml(decisionBasisLabel(label))}: ${escapeHtml(body)}</li>`;
    }

    function splitInlineBulletText(value) {
      const raw = String(value || "").trim();
      if (!raw) return [];
      const normalized = raw.replace(/\\s+/g, " ").trim();
      const looksLikeInlineList = normalized.startsWith("- ")
        || normalized.includes(". - ")
        || normalized.includes("; - ")
        || normalized.includes("? - ")
        || normalized.includes("! - ");
      if (!looksLikeInlineList) return [];
      const body = normalized.startsWith("- ") ? normalized.slice(2) : normalized;
      return body
        .split(/\\s+-\\s+/)
        .map((token) => token.trim())
        .filter(Boolean);
    }

    function successMetricsHtml(row) {
      const renderedHtml = String(row && row.success_metrics_html || "").trim();
      if (renderedHtml) {
        return `<div class="detail-copy">${renderedHtml}</div>`;
      }
      const explicitMetrics = Array.isArray(row.success_metrics_items)
        ? row.success_metrics_items.map((token) => String(token || "").trim()).filter(Boolean)
        : [];
      const raw = String(row.success_metrics || "").trim();
      const inlineMetrics = explicitMetrics.length ? [] : splitInlineBulletText(raw);
      const metrics = explicitMetrics.length ? explicitMetrics : inlineMetrics;
      const shouldRenderList = explicitMetrics.length > 0
        || metrics.length > 1
        || (metrics.length === 1 && raw.startsWith("- "));
      if (shouldRenderList) {
        return `<div class="detail-copy"><ul class="bullets">${metrics.map((metric) => `<li>${escapeHtml(metric)}</li>`).join("")}</ul></div>`;
      }
      return `<div class="detail-copy"><p>${escapeHtml(raw || "Not captured in the idea spec yet.")}</p></div>`;
    }

    function summarySectionHtml(value, fallback, renderedHtml = "") {
      const rich = String(renderedHtml || "").trim();
      if (rich) {
        return `<div class="detail-copy">${rich}</div>`;
      }
      const raw = String(value || "").trim();
      const bullets = splitInlineBulletText(raw);
      if (bullets.length) {
        return `<div class="detail-copy"><ul class="bullets">${bullets.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul></div>`;
      }
      return `<div class="detail-copy"><p>${escapeHtml(raw || fallback || "Not captured in the idea spec yet.")}</p></div>`;
    }

    function normalizeIdList(values) {
      if (!Array.isArray(values)) return [];
      const intentionalEmptyTokens = new Set(["none", "n/a", "na", "null", "nil", "-"]);
      return values
        .map((value) => String(value || "").trim())
        .filter((token) => token && !intentionalEmptyTokens.has(token.toLowerCase()));
    }

    function normalizeDiagramIdList(values) {
      const normalized = [];
      const seen = new Set();
      normalizeIdList(values)
        .map((token) => normalizeDiagramId(token))
        .forEach((token) => {
          if (!token || seen.has(token)) return;
          seen.add(token);
          normalized.push(token);
        });
      return normalized;
    }

    function traceabilityPayload() {
      const payload = DATA.traceability_index || DATA.traceability_graph;
      return payload && typeof payload === "object" ? payload : {};
    }

    function workstreamTrace(ideaId) {
      const payload = traceabilityPayload();
      const rows = Array.isArray(payload.workstreams) ? payload.workstreams : [];
      return rows.find((row) => row.idea_id === ideaId) || null;
    }

    function releaseCatalog() {
      const payload = traceabilityPayload();
      return Array.isArray(payload.releases) ? payload.releases : [];
    }

    function releaseLabel(row) {
      const release = row && typeof row === "object" ? row : {};
      const nameLabel = String(release.effective_name || release.name || "").trim();
      if (nameLabel) return nameLabel;
      const versionLabel = String(release.version || release.display_label || "").trim();
      if (versionLabel) return /^v\\d/.test(versionLabel) ? versionLabel.slice(1) : versionLabel;
      const tagLabel = String(release.tag || "").trim();
      if (tagLabel) return /^v\\d/.test(tagLabel) ? tagLabel.slice(1) : tagLabel;
      return String(release.release_id || "").trim();
    }

    function releaseCardLabel(row) {
      return releaseLabel(row);
    }

    function workstreamActiveRelease(row) {
      const trace = workstreamTrace(row.idea_id) || {};
      return trace && trace.active_release && typeof trace.active_release === "object"
        ? trace.active_release
        : {};
    }

    function workstreamActiveReleaseId(row) {
      const trace = workstreamTrace(row.idea_id) || {};
      const activeRelease = workstreamActiveRelease(row);
      return String(trace.active_release_id || activeRelease.release_id || "").trim();
    }

    function workstreamActiveReleaseLabel(row) {
      return releaseLabel(workstreamActiveRelease(row));
    }

    function executionWavePayload() {
      const payload = DATA.execution_waves;
      if (payload && typeof payload === "object") {
        return payload;
      }
      return { summary: {}, programs: [], workstreams: {} };
    }

    function executionWavePrograms() {
      const payload = executionWavePayload();
      return Array.isArray(payload.programs) ? payload.programs : [];
    }

    function executionWaveProgramByUmbrella(umbrellaId) {
      const token = String(umbrellaId || "").trim();
      if (!token) return null;
      return executionWavePrograms().find((row) => String(row && row.umbrella_id ? row.umbrella_id : "").trim() === token) || null;
    }

    function workstreamWavePrograms(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) return [];
      const payload = executionWavePayload();
      const byWorkstream = payload && payload.workstreams && typeof payload.workstreams === "object"
        ? payload.workstreams
        : {};
      return Array.isArray(byWorkstream[token]) ? byWorkstream[token] : [];
    }

    __ODYLITH_EXECUTION_WAVE_RUNTIME_JS__

    function executionWaveRoleChips(row) {
      const trace = workstreamTrace(row.idea_id) || {};
      const workstreamType = String(trace.workstream_type || row.workstream_type || "").trim().toLowerCase();
      const directProgram = workstreamType === "umbrella" ? executionWaveProgramByUmbrella(row.idea_id) : null;
      if (directProgram) {
        const waveCount = Number(directProgram.wave_count || 0);
        const activeCount = Number(directProgram.active_wave_count || 0);
        const nextWave = directProgram.next_wave && typeof directProgram.next_wave === "object"
          ? String(directProgram.next_wave.wave_id || directProgram.next_wave.label || "").trim()
          : "";
        return [
          waveCount > 0 ? `<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${waveCount}-wave program`)}</span>` : "",
          activeCount > 0 ? `<span class="label execution-wave-label wave-status-active">${escapeHtml(`${activeCount} active`)}</span>` : "",
          nextWave ? `<span class="label execution-wave-label wave-status-planned">${escapeHtml(`Next ${nextWave}`)}</span>` : "",
        ].filter(Boolean).join("");
      }

      const programContexts = workstreamWavePrograms(row.idea_id);
      if (!programContexts.length) return "";
      const primary = programContexts[0];
      const activeClass = primary.has_active_wave ? "wave-status-active" : (primary.has_next_wave ? "wave-status-planned" : "wave-status-other");
      const waveLabel = String(primary.wave_span_label || "").trim();
      const roleLabel = String(primary.role_label || "").trim();
      const umbrellaId = String(primary.umbrella_id || "").trim();
      return [
        waveLabel ? `<span class="label execution-wave-label ${escapeHtml(activeClass)}">${escapeHtml(waveLabel)}</span>` : "",
        roleLabel ? `<span class="label execution-wave-label wave-role-chip">${escapeHtml(roleLabel)}</span>` : "",
        umbrellaId ? `<span class="label execution-wave-label wave-program-chip">${escapeHtml(umbrellaId)}</span>` : "",
      ].filter(Boolean).join("");
    }

    function workstreamTypeInfo(row) {
      const trace = workstreamTrace(row.idea_id) || {};
      const rawType = String(trace.workstream_type || row.workstream_type || "").trim().toLowerCase();
      const parent = String(trace.workstream_parent || row.workstream_parent || "").trim();
      if (rawType === "umbrella") {
        return { type: "umbrella", label: "Umbrella", parent: "" };
      }
      if (rawType === "child") {
        return { type: "child", label: "Child", parent };
      }
      return { type: "standalone", label: "", parent: "" };
    }

    function compactWorkstreamId(token) {
      const raw = String(token || "").trim();
      const matched = raw.match(/^B-(\\d+)$/);
      if (matched) {
        return `B${matched[1]}`;
      }
      return raw;
    }

    function warningItems() {
      const payload = traceabilityPayload();
      const rich = Array.isArray(payload.warning_items) ? payload.warning_items : [];
      if (rich.length) {
        return rich.map((entry) => ({
          idea_id: String(entry.idea_id || "").trim(),
          severity: String(entry.severity || "warning").trim() || "warning",
          audience: String(entry.audience || "operator").trim() || "operator",
          surface_visibility: String(entry.surface_visibility || "").trim(),
          category: String(entry.category || "general").trim() || "general",
          message: String(entry.message || "").trim(),
          action: String(entry.action || "").trim(),
          source: String(entry.source || "").trim(),
        })).filter((entry) => entry.message);
      }
      const legacy = Array.isArray(payload.warnings) ? payload.warnings : [];
      return legacy
        .map((message) => String(message || "").trim())
        .filter(Boolean)
        .map((message) => ({
          idea_id: "",
          severity: "warning",
          audience: "operator",
          surface_visibility: "default",
          category: "legacy",
          message,
          action: "Inspect traceability graph diagnostics and corresponding source files.",
          source: "",
        }));
    }

    function isDefaultSurfaceWarning(entry) {
      const severity = String(entry && entry.severity || "warning").trim().toLowerCase();
      const audience = String(entry && entry.audience || "operator").trim().toLowerCase() || "operator";
      let visibility = String(entry && entry.surface_visibility || "").trim().toLowerCase();
      if (!visibility) {
        visibility = audience === "maintainer" || !["warning", "error"].includes(severity)
          ? "diagnostics"
          : "default";
      }
      return visibility === "default"
        && audience !== "maintainer"
        && ["warning", "error"].includes(severity);
    }

    function warningItemsForIdea(ideaId) {
      const rows = warningItems();
      return rows.filter(
        (entry) => String(entry.idea_id || "") === String(ideaId || "")
          && isDefaultSurfaceWarning(entry)
      );
    }

    function workstreamLinkChip(ideaId, tone = "") {
      const token = String(ideaId || "").trim();
      if (!token) return "";
      const tooltip = workstreamTooltip(token);
      return `<button type="button" class="chip chip-link entity-id-chip ${escapeHtml(tone)}" data-link-idea="${escapeHtml(token)}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}">${escapeHtml(token)}</button>`;
    }

    function renderWorkstreamLinkSet(items, tone = "") {
      const values = normalizeIdList(items);
      if (!values.length) return `<span class="chip">None</span>`;
      return values.map((token) => workstreamLinkChip(token, tone)).join("");
    }

    function renderDiagramLinkSet(items, selectedIdeaId) {
      const values = normalizeDiagramIdList(items);
      if (!values.length) return "";
      return values
        .map((diagramId) => {
          const href = atlasDiagramHref(diagramId, selectedIdeaId);
          const tooltip = diagramTooltip(diagramId);
          return `<a class="chip chip-link entity-id-chip chip-topology-diagram" href="${escapeHtml(href)}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}" target="_top">${escapeHtml(diagramId)}</a>`;
        })
        .join("");
    }

    function compassScopeHref(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) {
        return "../../odylith/index.html?tab=compass";
      }
      return `../../odylith/index.html?tab=compass&workstream=${encodeURIComponent(token)}&date=live`;
    }

    function registryComponentsForRow(row) {
      const values = Array.isArray(row && row.registry_components) ? row.registry_components : [];
      const deduped = [];
      const seen = new Set();
      values.forEach((item) => {
        const componentId = String(item && item.component_id ? item.component_id : "").trim().toLowerCase();
        if (!componentId || seen.has(componentId)) return;
        seen.add(componentId);
        const name = String(item && item.name ? item.name : componentId).trim() || componentId;
        deduped.push({ component_id: componentId, name });
      });
      return deduped;
    }

    function registryHrefForRow(row) {
      const components = registryComponentsForRow(row);
      if (!components.length) {
        return "../../odylith/index.html?tab=registry";
      }
      return `../../odylith/index.html?tab=registry&component=${encodeURIComponent(components[0].component_id)}`;
    }

    function registryComponentHref(component) {
      const componentId = String(component && component.component_id || "").trim().toLowerCase();
      if (!componentId) {
        return "../../odylith/index.html?tab=registry";
      }
      return `../../odylith/index.html?tab=registry&component=${encodeURIComponent(componentId)}`;
    }

    function renderRegistryComponentLinkSet(row) {
      const components = registryComponentsForRow(row);
      if (!components.length) return "";
      return components
        .map((component) => {
          const componentId = String(component && component.component_id || "").trim().toLowerCase();
          const label = String(component && component.name || componentId || "Component").trim() || "Component";
          const tooltip = componentTooltip(componentId, `${label} (${componentId})`);
          return `<a class="chip chip-link chip-registry-component" href="${escapeHtml(registryComponentHref(component))}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}" target="_top">${escapeHtml(label)}</a>`;
        })
        .join("");
    }

    function topologyRelationRow({ title, count, bodyHtml }) {
      const body = String(bodyHtml || "").trim()
        || `<span class="topology-rel-empty">None</span>`;
      return `
        <div class="topology-rel-row">
          <span class="topology-rel-title">${escapeHtml(title)}</span>
          <span class="topology-rel-count">${escapeHtml(String(count))}</span>
          <div class="topology-rel-body">${body}</div>
        </div>
      `;
    }

    function renderTopologyBoard(
      selectedIdeaId,
      parents,
      children,
      dependsOn,
      blocks,
      diagrams,
      reopens,
      reopenedBy,
      splitFrom,
      splitInto,
      mergedInto,
      mergedFrom
    ) {
      const parentValues = normalizeIdList(parents);
      const childrenValues = normalizeIdList(children);
      const dependsValues = normalizeIdList(dependsOn);
      const blocksValues = normalizeIdList(blocks);
      const diagramValues = normalizeDiagramIdList(diagrams);
      const reopensValues = normalizeIdList(reopens);
      const reopenedByValues = normalizeIdList(reopenedBy);
      const splitFromValues = normalizeIdList(splitFrom);
      const splitIntoValues = normalizeIdList(splitInto);
      const mergedIntoValues = normalizeIdList(mergedInto);
      const mergedFromValues = normalizeIdList(mergedFrom);
      const totalLinks =
        parentValues.length
        + childrenValues.length
        + dependsValues.length
        + blocksValues.length
        + diagramValues.length
        + reopensValues.length
        + reopenedByValues.length
        + splitFromValues.length
        + splitIntoValues.length
        + mergedIntoValues.length
        + mergedFromValues.length;

      const relationItems = [
        {
          title: "Parent",
          count: parentValues.length,
          bodyHtml: renderWorkstreamLinkSet(parentValues, "chip-topology-parent"),
        },
        {
          title: "Children",
          count: childrenValues.length,
          bodyHtml: renderWorkstreamLinkSet(childrenValues, "chip-topology-parent"),
        },
        {
          title: "Depends On",
          count: dependsValues.length,
          bodyHtml: renderWorkstreamLinkSet(dependsValues, "chip-topology-depends"),
        },
        {
          title: "Blocks",
          count: blocksValues.length,
          bodyHtml: renderWorkstreamLinkSet(blocksValues, "chip-topology-blocks"),
        },
        {
          title: "Related Diagrams",
          count: diagramValues.length,
          bodyHtml: renderDiagramLinkSet(diagramValues, selectedIdeaId) || `<span class="topology-rel-empty">None</span>`,
        },
        {
          title: "Reopens",
          count: reopensValues.length,
          bodyHtml: renderWorkstreamLinkSet(reopensValues, "chip-topology-parent"),
        },
        {
          title: "Reopened By",
          count: reopenedByValues.length,
          bodyHtml: renderWorkstreamLinkSet(reopenedByValues, "chip-topology-parent"),
        },
        {
          title: "Split From",
          count: splitFromValues.length,
          bodyHtml: renderWorkstreamLinkSet(splitFromValues, "chip-topology-depends"),
        },
        {
          title: "Split Into",
          count: splitIntoValues.length,
          bodyHtml: renderWorkstreamLinkSet(splitIntoValues, "chip-topology-depends"),
        },
        {
          title: "Merged Into",
          count: mergedIntoValues.length,
          bodyHtml: renderWorkstreamLinkSet(mergedIntoValues, "chip-topology-blocks"),
        },
        {
          title: "Merged From",
          count: mergedFromValues.length,
          bodyHtml: renderWorkstreamLinkSet(mergedFromValues, "chip-topology-blocks"),
        },
      ];
      const visibleRelationItems = relationItems.filter((item) => Number(item.count || 0) > 0);
      const relationRows = visibleRelationItems.map((item) => topologyRelationRow(item)).join("");
      const linkedRelationTypes = [
        parentValues,
        childrenValues,
        dependsValues,
        blocksValues,
        diagramValues,
        reopensValues,
        reopenedByValues,
        splitFromValues,
        splitIntoValues,
        mergedIntoValues,
        mergedFromValues,
      ].filter((values) => Array.isArray(values) && values.length > 0).length;

      return `
        <div class="topology-board">
          ${visibleRelationItems.length ? `
            <details class="topology-relations-panel">
              <summary>
                <span class="topology-relations-toggle">Relations</span>
                <span class="topology-relations-summary">${escapeHtml(String(linkedRelationTypes))} linked types · ${escapeHtml(String(totalLinks))} links</span>
              </summary>
              <div class="topology-relations">
                ${relationRows}
              </div>
            </details>
          ` : `<div class="topology-relations-empty">No linked relationships.</div>`}
        </div>
      `;
    }

    function resolveTopologyForIdea(ideaId, fallback = {}) {
      const token = String(ideaId || "").trim();
      const fallbackParents = normalizeIdList(fallback.parents);
      const fallbackChildren = normalizeIdList(fallback.children);
      const fallbackDepends = normalizeIdList(fallback.depends_on);
      const fallbackBlocks = normalizeIdList(fallback.blocks);
      const fallbackReopens = normalizeIdList(fallback.reopens);
      const fallbackReopenedBy = normalizeIdList(fallback.reopened_by);
      const fallbackSplitFrom = normalizeIdList(fallback.split_from);
      const fallbackSplitInto = normalizeIdList(fallback.split_into);
      const fallbackMergedInto = normalizeIdList(fallback.merged_into);
      const fallbackMergedFrom = normalizeIdList(fallback.merged_from);
      if (!token) {
        return {
          parents: fallbackParents,
          children: fallbackChildren,
          depends_on: fallbackDepends,
          blocks: fallbackBlocks,
          reopens: fallbackReopens,
          reopened_by: fallbackReopenedBy,
          split_from: fallbackSplitFrom,
          split_into: fallbackSplitInto,
          merged_into: fallbackMergedInto,
          merged_from: fallbackMergedFrom,
        };
      }

      const payload = traceabilityPayload();
      const edges = Array.isArray(payload.edges) ? payload.edges : [];
      const parentSet = new Set();
      const childSet = new Set();
      const dependsSet = new Set();
      const blocksSet = new Set();
      const reopensSet = new Set();
      const reopenedBySet = new Set();
      const splitFromSet = new Set();
      const splitIntoSet = new Set();
      const mergedIntoSet = new Set();
      const mergedFromSet = new Set();
      edges.forEach((edge) => {
        const source = String(edge.source || "").trim();
        const target = String(edge.target || "").trim();
        const kind = String(edge.edge_type || "").trim();
        if (!source || !target) return;
        if (kind === "parent_child") {
          if (source === token) childSet.add(target);
          if (target === token) parentSet.add(source);
          return;
        }
        if (kind === "depends_on" && target === token) {
          dependsSet.add(source);
          return;
        }
        if (kind === "blocks" && source === token) {
          blocksSet.add(target);
          return;
        }
        if (kind === "reopens") {
          if (source === token) reopensSet.add(target);
          if (target === token) reopenedBySet.add(source);
          return;
        }
        if (kind === "split") {
          if (source === token) splitIntoSet.add(target);
          if (target === token) splitFromSet.add(source);
          return;
        }
        if (kind === "merge") {
          if (source === token) mergedIntoSet.add(target);
          if (target === token) mergedFromSet.add(source);
        }
      });

      const edgeParents = [...parentSet].sort();
      const edgeChildren = [...childSet].sort();
      const edgeDepends = [...dependsSet].sort();
      const edgeBlocks = [...blocksSet].sort();
      const edgeReopens = [...reopensSet].sort();
      const edgeReopenedBy = [...reopenedBySet].sort();
      const edgeSplitFrom = [...splitFromSet].sort();
      const edgeSplitInto = [...splitIntoSet].sort();
      const edgeMergedInto = [...mergedIntoSet].sort();
      const edgeMergedFrom = [...mergedFromSet].sort();

      return {
        parents: edgeParents.length ? edgeParents : fallbackParents,
        children: edgeChildren.length ? edgeChildren : fallbackChildren,
        depends_on: edgeDepends.length ? edgeDepends : fallbackDepends,
        blocks: edgeBlocks.length ? edgeBlocks : fallbackBlocks,
        reopens: edgeReopens.length ? edgeReopens : fallbackReopens,
        reopened_by: edgeReopenedBy.length ? edgeReopenedBy : fallbackReopenedBy,
        split_from: edgeSplitFrom.length ? edgeSplitFrom : fallbackSplitFrom,
        split_into: edgeSplitInto.length ? edgeSplitInto : fallbackSplitInto,
        merged_into: edgeMergedInto.length ? edgeMergedInto : fallbackMergedInto,
        merged_from: edgeMergedFrom.length ? edgeMergedFrom : fallbackMergedFrom,
      };
    }

    function renderExecutionWaveMemberChip(ideaId, options = {}) {
      const token = String(ideaId || "").trim();
      if (!token) return "";
      const tooltip = workstreamTooltip(token);
      const tone = options && options.selected ? " wave-member-selected" : "";
      return `<button type="button" class="chip chip-link entity-id-chip execution-wave-chip-link${tone}" data-link-idea="${escapeHtml(token)}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}">${escapeHtml(token)}</button>`;
    }

    function renderExecutionWaveDetailSection(selected) {
      const directProgram = executionWaveProgramByUmbrella(selected.idea_id);
      const entries = [];
      if (directProgram) {
        entries.push({ program: directProgram, context: null });
      } else {
        const contexts = workstreamWavePrograms(selected.idea_id);
        contexts.forEach((context) => {
          const program = executionWaveProgramByUmbrella(context.umbrella_id);
          if (program) entries.push({ program, context });
        });
      }
      if (!entries.length) return "";

      const primaryEntry = entries[0] || {};
      const primaryProgram = primaryEntry.program && typeof primaryEntry.program === "object" ? primaryEntry.program : {};
      const primaryContext = primaryEntry.context && typeof primaryEntry.context === "object" ? primaryEntry.context : null;
      const programCount = entries.length;
      const activeWaveCount = entries.reduce((count, entry) => count + Number(entry && entry.program && entry.program.active_wave_count ? entry.program.active_wave_count : 0), 0);
      const waveCount = entries.reduce((count, entry) => count + Number(entry && entry.program && entry.program.wave_count ? entry.program.wave_count : 0), 0);
      const programLabel = `${String(primaryProgram.umbrella_title || primaryProgram.umbrella_id || "").trim()} (${String(primaryProgram.umbrella_id || "").trim()})`;
      const contextLine = primaryContext
        ? `This workstream participates across ${String(primaryContext.wave_span_label || "").trim() || "the program"} as ${String(primaryContext.role_label || "").trim() || "a member"}.`
        : "Umbrella-owned execution waves for this program.";
      const numericProgressOrNull = (value) => {
        if (value === null || value === undefined || value === "") return null;
        const numericValue = Number(value);
        return Number.isFinite(numericValue) ? numericValue : null;
      };
      const workstreamStatusById = new Map(
        (Array.isArray(DATA.entries) ? DATA.entries : [])
          .map((row) => {
            const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
            const status = String(row && row.status ? row.status : "").trim().toLowerCase();
            return [ideaId, status || ""];
          })
          .filter(([ideaId]) => ideaId)
      );
      const workstreamProgressById = new Map(
        (Array.isArray(DATA.entries) ? DATA.entries : [])
          .map((row) => {
            const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
            const plan = row && typeof row.plan === "object" ? row.plan : {};
            const progressRatio = numericProgressOrNull(
              Object.prototype.hasOwnProperty.call(plan, "display_progress_ratio")
                ? plan.display_progress_ratio
                : (Object.prototype.hasOwnProperty.call(plan, "progress_ratio") ? plan.progress_ratio : null)
            );
            return [ideaId, progressRatio];
          })
          .filter(([ideaId]) => ideaId)
      );
      const resolveWorkstreamStatus = (member) => {
        const ideaId = String(member && (member.idea_id || member.workstream_id) ? (member.idea_id || member.workstream_id) : "").trim();
        if (!ideaId || !workstreamStatusById.has(ideaId)) return "";
        return workstreamStatusById.get(ideaId);
      };
      const resolveWorkstreamProgress = (member) => {
        const ideaId = String(member && (member.idea_id || member.workstream_id) ? (member.idea_id || member.workstream_id) : "").trim();
        if (!ideaId || !workstreamProgressById.has(ideaId)) return null;
        return workstreamProgressById.get(ideaId);
      };
      const summaryLine = programCount === 1
        ? executionWaveSummaryLine(primaryProgram, { resolveWorkstreamStatus })
        : `${programCount} programs · ${activeWaveCount} active waves · ${waveCount} total waves`;
      const sectionChips = [];
      if (programCount > 1) {
        sectionChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${programCount} programs`)}</span>`);
      } else if (Number(primaryProgram.wave_count || 0) > 0) {
        sectionChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${Number(primaryProgram.wave_count || 0)}-wave program`)}</span>`);
        const programProgress = executionWaveProgramProgress(primaryProgram, { resolveWorkstreamStatus, resolveWorkstreamProgress });
        if (programProgress.percent) {
          sectionChips.push(`<span class="label execution-wave-label wave-progress-chip">${escapeHtml(`Overall ${programProgress.percent} progress`)}</span>`);
        }
      }
      if (activeWaveCount > 0) {
        sectionChips.push(`<span class="label execution-wave-label wave-status-active">${escapeHtml(`${activeWaveCount} active`)}</span>`);
      }
      if (primaryContext) {
        const waveSpan = String(primaryContext.wave_span_label || "").trim();
        const roleLabel = String(primaryContext.role_label || "").trim();
        if (waveSpan) sectionChips.push(`<span class="label execution-wave-label wave-status-planned">${escapeHtml(waveSpan)}</span>`);
        if (roleLabel) sectionChips.push(`<span class="label execution-wave-label wave-role-chip">${escapeHtml(roleLabel)}</span>`);
      }

      return renderExecutionWaveSection(
        {
          title: "Execution Waves",
          entries,
          selectedWorkstreamId: selected.idea_id,
          programLabel,
          contextLine,
          summaryLine,
          sectionChips,
        },
        {
          escapeHtml,
          emptyStateClass: "execution-wave-empty",
          renderMemberChip: renderExecutionWaveMemberChip,
          resolveWorkstreamStatus,
          resolveWorkstreamProgress,
          selectedBadgeLabel: "Selected",
          selectedCardClass: "is-member",
        },
      );
    }

    async function renderDetail(rows) {
      const selectedSummary = rows.find((row) => row.idea_id === state.selectedIdeaId);
      if (!selectedSummary) {
        el.detail.hidden = true;
        el.detailEmpty.hidden = true;
        el.detail.innerHTML = "";
        return;
      }
      el.detail.hidden = false;
      el.detailEmpty.hidden = true;
      el.detail.innerHTML = "";
      const loadedDetail = await backlogDataSource.loadDetail(selectedSummary.idea_id);
      if (String(state.selectedIdeaId || "").trim() !== String(selectedSummary.idea_id || "").trim()) {
        return;
      }
      const selected = loadedDetail && typeof loadedDetail === "object"
        ? { ...selectedSummary, ...loadedDetail }
        : selectedSummary;

      const sectionBadge = sectionBadgeInfo(selected);
      const rankingClass = selected.founder_override === "yes" ? "founder-override" : "score-ordered";
      const rankingText = selected.founder_override === "yes" ? "Priority Override" : "Score Ordered";
      const scoreWidth = Math.max(3, Math.min(100, selected.ordering_score));
      const statusClass = statusChipClass(selected.status);
      const stageDisplay = executionStageLabel(selected.status);
      const executionState = String(selected.execution_state || "").trim().toLowerCase();
      const executionMeta = selected.execution_state_meta && typeof selected.execution_state_meta === "object"
        ? selected.execution_state_meta
        : {};
      const activeWindowMinutes = executionActiveWindowMinutes(executionMeta);
      const executionSignalAt = String(executionMeta.source_ts_iso || "").trim();
      const executionSignalLabel = formatCompactTimestamp(executionSignalAt);
      const executionSignalChip = selected.section === "execution"
        ? `<span class="chip execution-chip ${escapeHtml(executionStateClass(executionState))}" data-tooltip="${escapeHtml(executionSignalTooltip(selected.status, executionState, activeWindowMinutes))}">${escapeHtml(executionStateLabel(executionState))}</span>`
        : "";
      const trace = workstreamTrace(selected.idea_id) || {};
      const activeRelease = workstreamActiveRelease(selected);
      const activeReleaseLabel = releaseLabel(activeRelease);
      const fallbackTopology = {
        parents: trace.workstream_parent || selected.workstream_parent || "",
        children: Array.isArray(trace.workstream_children) ? trace.workstream_children : (Array.isArray(selected.workstream_children) ? selected.workstream_children : []),
        depends_on: Array.isArray(trace.workstream_depends_on) ? trace.workstream_depends_on : (Array.isArray(selected.workstream_depends_on) ? selected.workstream_depends_on : []),
        blocks: Array.isArray(trace.workstream_blocks) ? trace.workstream_blocks : (Array.isArray(selected.workstream_blocks) ? selected.workstream_blocks : []),
        reopens: trace.workstream_reopens || (Array.isArray(selected.workstream_reopens) ? selected.workstream_reopens : []),
        reopened_by: trace.workstream_reopened_by || (Array.isArray(selected.workstream_reopened_by) ? selected.workstream_reopened_by : []),
        split_from: trace.workstream_split_from || (Array.isArray(selected.workstream_split_from) ? selected.workstream_split_from : []),
        split_into: Array.isArray(trace.workstream_split_into) ? trace.workstream_split_into : (Array.isArray(selected.workstream_split_into) ? selected.workstream_split_into : []),
        merged_into: trace.workstream_merged_into || (Array.isArray(selected.workstream_merged_into) ? selected.workstream_merged_into : []),
        merged_from: Array.isArray(trace.workstream_merged_from) ? trace.workstream_merged_from : (Array.isArray(selected.workstream_merged_from) ? selected.workstream_merged_from : []),
      };
      const resolvedTopology = resolveTopologyForIdea(selected.idea_id, fallbackTopology);
      const parents = normalizeIdList(resolvedTopology.parents);
      const children = normalizeIdList(resolvedTopology.children);
      const dependsOn = normalizeIdList(resolvedTopology.depends_on);
      const blocks = normalizeIdList(resolvedTopology.blocks);
      const reopens = normalizeIdList(resolvedTopology.reopens);
      const reopenedBy = normalizeIdList(resolvedTopology.reopened_by);
      const splitFrom = normalizeIdList(resolvedTopology.split_from);
      const splitInto = normalizeIdList(resolvedTopology.split_into);
      const mergedInto = normalizeIdList(resolvedTopology.merged_into);
      const mergedFrom = normalizeIdList(resolvedTopology.merged_from);
      const diagrams = Array.isArray(trace.related_diagram_ids) ? trace.related_diagram_ids : (Array.isArray(selected.related_diagram_ids) ? selected.related_diagram_ids : []);
      const scopedWarnings = warningItemsForIdea(selected.idea_id);
      const graphWarnings = scopedWarnings;
      const warningsSectionHtml = graphWarnings.length
        ? `
        <section class="block">
          <h3>Warnings</h3>
          <p><strong>Warnings scoped to this workstream:</strong></p>
          <ul class="warning-list">${
            graphWarnings.slice(0, 8).map((item) => {
              const category = String(item.category || "general").trim();
              const severity = String(item.severity || "warning").trim();
              const message = String(item.message || "").trim();
              const action = String(item.action || "").trim();
              const source = String(item.source || "").trim();
              const metaBits = [
                category ? `category: ${category}` : "",
                severity ? `severity: ${severity}` : "",
                source ? `source: ${source}` : "",
              ].filter(Boolean);
              return `
                <li class="warning-item">
                  <p class="warning-title">${escapeHtml(message || "Warning")}</p>
                  ${action ? `<p class="warning-action"><strong>Action:</strong> ${escapeHtml(action)}</p>` : ""}
                  ${metaBits.length ? `<p class="warning-meta">${escapeHtml(metaBits.join(" · "))}</p>` : ""}
                </li>
              `;
            }).join("")
          }</ul>
        </section>
      `
        : "";

      const topologyBoardHtml = renderTopologyBoard(
        selected.idea_id,
        parents,
        children,
        dependsOn,
        blocks,
        diagrams,
        reopens,
        reopenedBy,
        splitFrom,
        splitInto,
        mergedInto,
        mergedFrom,
      );
      const registryComponents = registryComponentsForRow(selected);
      const registryComponentLinksHtml = renderRegistryComponentLinkSet(selected);
      const executionWaveSectionHtml = renderExecutionWaveDetailSection(selected);
      const implementedSummary = String(selected.implemented_summary || "").trim();
      const implementedSummaryHtml = implementedSummary
        ? `
        <section class="block">
          <h3>Implemented Summary</h3>
          ${summarySectionHtml(implementedSummary, "Not captured in the idea spec yet.", selected.implemented_summary_html)}
        </section>
      `
        : "";
      el.detail.innerHTML = `
        <header class="detail-header">
          <h2 class="detail-title">${escapeHtml(selected.title)}</h2>
          <div class="kpis">
            <div class="kpi" data-kpi="workstream-id"><div class="k">Workstream ID</div><div class="v">${escapeHtml(selected.idea_id)}</div></div>
            <div class="kpi kpi-section ${escapeHtml(sectionBadge.kpiClassName)}" data-kpi="workstream-placement"><div class="k">Placement</div><div class="v">${escapeHtml(sectionBadge.label)}</div></div>
            <div class="kpi"><div class="k">Ordering Score</div><div class="v">${escapeHtml(selected.ordering_score)}</div></div>
            <div class="kpi"><div class="k">Created Date</div><div class="v">${escapeHtml(selected.idea_date_display || selected.idea_date || "-")}</div></div>
            <div class="kpi"><div class="k">Age (days)</div><div class="v">${escapeHtml(selected.idea_age_days || "-")}</div></div>
            <div class="kpi"><div class="k">Execution Start</div><div class="v">${escapeHtml(selected.execution_start_date_display || selected.execution_start_date || "-")}</div></div>
            <div class="kpi"><div class="k">Execution End</div><div class="v">${escapeHtml(selected.execution_end_date_display || selected.execution_end_date || "-")}</div></div>
            <div class="kpi"><div class="k">Execution Days</div><div class="v">${escapeHtml(selected.execution_duration_days || selected.execution_age_days || "-")}</div></div>
            <div class="kpi"><div class="k">Live Signal At</div><div class="v v-compact" title="${escapeHtml(executionSignalAt || "-")}">${escapeHtml(executionSignalLabel)}</div></div>
            <div class="kpi"><div class="k">Confidence</div><div class="v">${escapeHtml(selected.confidence || "-")}</div></div>
          </div>
          <div class="chips">
            <span class="chip chip-priority">${escapeHtml(selected.priority)}</span>
            <span class="chip ${statusClass}">${escapeHtml(stageDisplay)}</span>
            ${executionSignalChip}
            ${activeReleaseLabel ? `<span class="chip">${escapeHtml(activeReleaseLabel)}</span>` : ""}
            <span class="chip chip-sizing">${escapeHtml(selected.sizing)} / ${escapeHtml(selected.complexity)}</span>
            <span class="chip ${rankingClass}">${rankingText}</span>
          </div>
          <div class="meter">
            <div class="meter-head">
              <span>Score Signal</span><strong>${escapeHtml(selected.ordering_score)}</strong>
            </div>
            <div class="bar"><div class="fill" style="width: ${scoreWidth}%"></div></div>
          </div>
        </header>

        <section class="block">
          <h3>Traceability</h3>
          <div class="links">
            <a href="${escapeHtml(selected.idea_ui_href || selected.idea_href)}">Workstream Spec</a>
            ${
              selected.promoted_to_plan_ui_href
                ? `<a href="${escapeHtml(selected.promoted_to_plan_ui_href)}">Technical Implementation Plan</a>`
                : ""
            }
            <a href="${escapeHtml(compassScopeHref(selected.idea_id))}" target="_top">Compass Scope</a>
            <a href="${escapeHtml(registryHrefForRow(selected))}" target="_top">Registry</a>
          </div>
          ${activeReleaseLabel ? `<p class="trace-subhead">Release Target</p><p>${escapeHtml(activeReleaseLabel)}</p>` : ""}
          ${registryComponents.length ? `
            <p class="trace-subhead">Registry Components</p>
            <div class="topology-rel-body">${registryComponentLinksHtml}</div>
          ` : ""}
        </section>

        <section class="block">
          <h3>Topology</h3>
          ${topologyBoardHtml}
        </section>

        ${executionWaveSectionHtml}

        ${warningsSectionHtml}

        ${implementedSummaryHtml}

        <section class="block block-problem">
          <h3>Problem</h3>
          ${summarySectionHtml(selected.problem, "Not captured in the idea spec yet.", selected.problem_html)}
        </section>

        <section class="block">
          <div class="split-grid">
            <article class="split-card">
              <h3>Product View</h3>
              ${summarySectionHtml(selected.founder_pov, "Not captured in the idea spec yet.", selected.founder_pov_html)}
            </article>
            <article class="split-card">
              <h3>Decision Basis</h3>
              ${toBulletHtml(selected)}
            </article>
          </div>
        </section>

        <section class="block">
          <h3>Customer</h3>
          ${summarySectionHtml(selected.customer, "Not captured in the idea spec yet.", selected.customer_html)}
        </section>

        <section class="block">
          <h3>Opportunity</h3>
          ${summarySectionHtml(selected.opportunity, "Not captured in the idea spec yet.", selected.opportunity_html)}
        </section>

        <section class="block">
          <h3>Success Metrics</h3>
          ${successMetricsHtml(selected)}
        </section>

        <section class="block">
          <h3>Ordering Rationale</h3>
          <p>${escapeHtml(selected.ordering_rationale || "No ordering rationale recorded.")}</p>
        </section>

        <section class="block">
          <h3>Impacted Parts</h3>
          <p>${escapeHtml(selected.impacted_parts || "Not specified.")}</p>
        </section>
      `;
    }

    function render(options = {}) {
      const filtered = sortRows(applyFilters());
      if (filtered.length && !filtered.some((item) => item.idea_id === state.selectedIdeaId)) {
        state.selectedIdeaId = String(filtered[0].idea_id || "");
      }
      const executionWaveSummary = executionWavePayload().summary || {};
      el.stats.innerHTML = summaryStatRows(filtered, executionWaveSummary).join("");

      el.meta.textContent = `Showing ${filtered.length} of ${all.length} workstreams · Source: ${DATA.index_file}`;
      void renderAnalytics(filtered);
      renderList(filtered, { preserveListScroll: Boolean(options.preserveListScroll) });
      void renderDetail(filtered);
      el.empty.hidden = true;
      if (!filtered.length) {
        el.detail.hidden = true;
        el.detailEmpty.hidden = true;
      }

      syncParentShellSelection();
    }

    function bind(element, key) {
      element.addEventListener("input", () => {
        state[key] = element.value;
        render();
      });
      element.addEventListener("change", () => {
        state[key] = element.value;
        render();
      });
    }

    bind(el.query, "query");
    bind(el.section, "section");
    bind(el.legacySection, "section");
    bind(el.phase, "phase");
    bind(el.type, "type");
    bind(el.activity, "activity");
    bind(el.priority, "priority");
    bind(el.release, "release");
    bind(el.sort, "sort");

    el.mixByComplexity.addEventListener("click", () => {
      state.mixBy = "complexity";
      render();
    });
    el.mixBySize.addEventListener("click", () => {
      state.mixBy = "size";
      render();
    });

    loadAnalyticsPreference();
    if (workstreamParam) {
      selectIdea(workstreamParam, { reveal: true });
    }
    if (viewParam === "graph") {
      setAnalyticsExpanded(true);
    }

    render();

    if (viewParam === "graph") {
      document.getElementById("analytics-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    })();
  </script>
</body>
</html>
"""
    header_typography_css = dashboard_ui_primitives.header_typography_css(
        kicker_selector=".kicker",
        title_selector="h1",
        subtitle_selector=".subtitle",
        subtitle_max_width="100%",
        mobile_breakpoint_px=760,
        mobile_title_size_px=22,
        mobile_subtitle_size_px=13,
    )
    page_body_css = dashboard_ui_primitives.page_body_typography_css(
        selector="body",
    )
    surface_shell_root_css = dashboard_ui_primitives.standard_surface_shell_root_css()
    surface_shell_css = dashboard_ui_primitives.standard_surface_shell_css(
        selector=".shell",
    )
    hero_panel_css = dashboard_ui_primitives.hero_panel_css(
        container_selector=".hero",
        margin_bottom="16px",
    )
    sticky_filter_css = dashboard_ui_primitives.sticky_filter_bar_css(
        container_selector=".controls",
        columns="minmax(220px, 1.8fr) repeat(7, minmax(0, 1fr))",
        field_selector=".controls input, .controls select",
        focus_selector=".controls input:focus, .controls select:focus",
        top_px=10,
    )
    stat_card_surface_css = "\n\n".join(
        (
            dashboard_ui_primitives.kpi_card_surface_css(
                card_selector=".stat",
            ),
        )
    )
    kpi_grid_layout_css = dashboard_ui_primitives.kpi_grid_layout_css(
        container_selector=".stats",
    )
    detail_identity_css = dashboard_ui_primitives.detail_identity_typography_css(
        title_selector=".detail-title",
        subtitle_selector=".detail-header .detail-subtitle",
        title_size_px=24,
        medium_title_size_px=22,
        small_title_size_px=19,
    )
    kpi_typography_css = dashboard_ui_primitives.governance_kpi_label_value_css(
        label_selector=".stat .label",
        value_selector=".stat .value",
    )
    radar_operator_readout_layout_css = "\n\n".join(
        (
            dashboard_ui_primitives.operator_readout_host_shell_css(
                shell_selector=".operator-readout-shell",
                heading_selector=".operator-readout-shell .operator-readout-shell-heading",
                body_selector=".operator-readout-shell .operator-readout-shell-body",
            ),
            dashboard_ui_primitives.operator_readout_host_heading_css(
                selector=".operator-readout-shell .operator-readout-shell-heading",
            ),
            dashboard_ui_primitives.operator_readout_layout_css(
                container_selector=".operator-readout",
                meta_selector=".operator-readout-meta",
                main_selector=".operator-readout-main",
                details_selector=".operator-readout-details",
                section_selector=".operator-readout-section",
                proof_selector=".operator-readout-proof",
                footnote_selector=".operator-readout-footnote",
            ),
        )
    )
    radar_operator_readout_label_css = dashboard_ui_primitives.operator_readout_label_typography_css(
        selector=".operator-readout-label",
    )
    radar_operator_readout_copy_css = dashboard_ui_primitives.operator_readout_copy_typography_css(
        selector=".operator-readout-copy",
        color="#27445e",
        line_height=1.55,
    )
    radar_operator_readout_meta_css = "\n\n".join(
        (
            dashboard_ui_primitives.operator_readout_meta_pill_css(
                selector=".operator-readout-meta-item",
            ),
            dashboard_ui_primitives.operator_readout_meta_semantic_css(
                selector=".operator-readout-meta-item",
            ),
        )
    )
    radar_readable_copy_css = "\n\n".join(
        (
            dashboard_ui_primitives.content_copy_css(
                selectors=(
                    ".meta-row-val",
                    ".block p",
                    ".block ul",
                    ".block li",
                    ".bullets",
                    ".bullets li",
                    ".detail-copy p",
                    ".detail-copy ul",
                    ".detail-copy li",
                    ".detail-copy .check-text",
                    ".analytics-toggle-sub",
                    ".graph-sub",
                    ".graph-empty",
                ),
            ),
            dashboard_ui_primitives.code_typography_css(
                selector=".detail-copy .code",
            ),
            """
.block.block-problem {
  border-color: #bfdbfe;
  background: linear-gradient(180deg, #f8fbff, #ffffff 70%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.detail-copy {
  display: grid;
  gap: 12px;
}

.detail-copy > * {
  margin: 0;
}

.detail-copy > p {
  max-width: 100%;
}

.detail-copy ul {
  margin: 0;
  padding-left: 22px;
  display: grid;
  gap: 10px;
}

.detail-copy li {
  margin: 0;
}

.detail-copy a {
  color: #1d4ed8;
  text-decoration: none;
  border-bottom: 1px solid #bfdbfe;
}

.detail-copy a:hover {
  border-bottom-color: #60a5fa;
}

.detail-copy code {
  font-family: ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 0.92em;
  color: #1e3a8a;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  padding: 0.08em 0.38em;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.detail-copy .code {
  margin: 0;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #0f172a;
  padding: 12px 13px;
  overflow: auto;
}

.detail-copy .code code {
  background: none;
  border: 0;
  border-radius: 0;
  color: inherit;
  padding: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.detail-copy .checklist {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-copy .check-item {
  --level: 0;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding-left: calc(var(--level) * 28px);
}

.detail-copy .check-text {
  min-width: 0;
}

.detail-copy .check-box {
  width: 16px;
  height: 16px;
  margin: 2px 0 0;
  accent-color: #0f766e;
  cursor: default;
  flex: 0 0 auto;
}

.detail-copy .check-box:disabled {
  opacity: 1;
}
            """.strip(),
        )
    )
    meta_supporting_css = dashboard_ui_primitives.supporting_copy_typography_css(
        selector=".meta",
        color="var(--ink-muted)",
        size_px=13,
        line_height=1.45,
    )
    passive_chip_surface_css = dashboard_ui_primitives.label_surface_css(
        selector="span.chip",
        min_height_px=0,
        padding="4px 10px",
        background="#f7faf8",
        border_color="#dce4de",
        color="#56687d",
        border_radius_px=4,
        border_width_px=1,
    )
    rank_chip_surface_css = "\n\n".join(
        (
            dashboard_ui_primitives.label_surface_css(
                selector=".rank-chip",
                min_height_px=0,
                padding="4px 10px",
                background="#edf7f1",
                border_color="#d6e3d9",
                color="#1e3a8a",
                border_radius_px=4,
                border_width_px=1,
            ),
            ".rank-chip {\n  min-width: 64px;\n  flex-shrink: 0;\n  font-variant-numeric: tabular-nums;\n}".strip(),
        )
    )
    chip_label_css = dashboard_ui_primitives.label_badge_typography_css(
        selector="span.chip",
        color="#334155",
        size_px=11,
    )
    rank_chip_css = dashboard_ui_primitives.label_badge_typography_css(
        selector=".rank-chip",
        color="#1e3a8a",
        size_px=11,
        line_height=1.0,
    )
    row_title_css = dashboard_ui_primitives.card_title_typography_css(
        selector=".row-title",
        color="var(--ink)",
        size_px=14,
        line_height=1.3,
        margin="0",
    )
    row_id_css = dashboard_ui_primitives.mono_identifier_typography_css(
        selector=".row-id",
        color="var(--ink-muted)",
        margin="0",
    )
    analytics_title_css = dashboard_ui_primitives.card_title_typography_css(
        selector=".analytics-toggle-title, .graph-head",
        color="var(--ink)",
        size_px=14,
        line_height=1.3,
        margin="0",
    )
    detail_kpi_surface_css = dashboard_ui_primitives.kpi_card_surface_css(
        card_selector=".kpi",
        padding="9px 12px",
    )
    detail_kpi_typography_css = dashboard_ui_primitives.governance_kpi_label_value_css(
        label_selector=".kpi .k",
        value_selector=".kpi .v",
        label_size_px=11,
        label_line_height=1.05,
        label_letter_spacing_em=0.06,
        value_size_px=17,
        value_line_height=1.05,
        value_letter_spacing_em=-0.01,
    )
    workspace_layout_css = dashboard_ui_primitives.split_detail_workspace_css(
        selector=".workspace",
        left_min_px=300,
        left_max_px=380,
    )
    chart_axis_css = dashboard_ui_primitives.chart_axis_typography_css(
        selector=".chart-axis",
    )
    chip_link_contract_css = "\n\n".join(
        (
            dashboard_ui_primitives.detail_action_chip_css(
                selector=".chip-link:not(.entity-id-chip):not(.execution-wave-chip-link)",
            ),
            dashboard_ui_primitives.surface_workstream_button_chip_css(
                selector=".entity-id-chip",
            ),
        )
    )
    mix_toggle_button_css = dashboard_ui_primitives.detail_toggle_chip_css(
        selector=".mix-toggle button",
        active_selector=".mix-toggle button.active",
        border_color="#cbd5e1",
        background="#ffffff",
        color="#334155",
        hover_border_color="#b9c7d8",
        hover_background="#f8fafc",
        hover_color="#1f2937",
        active_border_color="#0f766e",
        active_background="#ecfeff",
        active_color="#0f766e",
        active_hover_border_color="#0f766e",
        active_hover_background="#dbfffb",
        active_hover_color="#0f766e",
    )
    radar_label_semantic_css = "\n\n".join(
        (
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".list-section-head",
                background="#f5f7fb",
                border_color="#d8e2ec",
                color="#5d6f83",
            ),
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".list-section-head.list-section-execution",
                background="#eef2f7",
                border_color="#d5ddea",
                color="#5b697d",
            ),
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".list-section-head.list-section-active",
                background="#f4f1f9",
                border_color="#e1dbeb",
                color="#6a627c",
            ),
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".list-section-head.list-section-finished",
                background="#f3f5ee",
                border_color="#dce2d2",
                color="#68725b",
            ),
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".list-section-head.list-section-parked",
                background="#f4f3f1",
                border_color="#e2ddd6",
                color="#75695d",
            ),
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".kpi.kpi-section.kpi-section-active",
                background="#f4f1f9",
                border_color="#e1dbeb",
                color="#6a627c",
            ),
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".kpi.kpi-section.kpi-section-execution",
                background="#eef2f7",
                border_color="#d5ddea",
                color="#5b697d",
            ),
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".kpi.kpi-section.kpi-section-finished",
                background="#f3f5ee",
                border_color="#dce2d2",
                color="#68725b",
            ),
            dashboard_ui_primitives.subtle_labeled_surface_tone_css(
                selector=".kpi.kpi-section.kpi-section-parked",
                background="#f4f3f1",
                border_color="#e2ddd6",
                color="#75695d",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".rank-chip",
                background="#eef2f7",
                border_color="#d8e1eb",
                color="#56687d",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".rank-chip.rank-chip-active",
                background="#f4f1f9",
                border_color="#e1dbeb",
                color="#6a627c",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".rank-chip.rank-chip-execution",
                background="#eef2f7",
                border_color="#d5ddea",
                color="#5b697d",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".rank-chip.rank-chip-finished",
                background="#f3f5ee",
                border_color="#dce2d2",
                color="#68725b",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".rank-chip.rank-chip-parked",
                background="#f4f3f1",
                border_color="#e2ddd6",
                color="#75695d",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip",
                background="#f7f8fb",
                border_color="#e0e6ee",
                color="#56687d",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.chip-priority",
                background="#f7eff6",
                border_color="#e8d9e7",
                color="#795770",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.chip-sizing",
                background="#f5f3f8",
                border_color="#e2dceb",
                color="#675e78",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.status-chip",
                background="#f2f5fa",
                border_color="#dbe3ee",
                color="#566983",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.status-planning",
                background="#eef3fb",
                border_color="#d3deef",
                color="#5a7096",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.status-implementation",
                background="#fbf1e8",
                border_color="#ecd7bf",
                color="#8f6543",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.status-finished",
                background="#eff7ef",
                border_color="#d5e5d5",
                color="#57745c",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.status-parked",
                background="#f5f2ee",
                border_color="#e6ddd2",
                color="#7a6858",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.execution-chip",
                background="#f1f5fa",
                border_color="#d8e1ea",
                color="#566a80",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.exec-actively-executing",
                background="#ebf7f3",
                border_color="#cbe6db",
                color="#3f7668",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.exec-planning-active",
                background="#edf7fb",
                border_color="#cee5ef",
                color="#4f7389",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.exec-planned-only",
                background="#f3f1fb",
                border_color="#ddd8ef",
                color="#6b608d",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.exec-implementation-no-live-signal, .chip.exec-signal-quiet",
                background="#fbf4e8",
                border_color="#eadbbe",
                color="#8b6d41",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.ws-umbrella",
                background="#f1eff8",
                border_color="#ddd6ec",
                color="#6b5d84",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.ws-child",
                background="#eef7f5",
                border_color="#cee4df",
                color="#4a736a",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.ws-parent",
                background="#f6f7fa",
                border_color="#dbe2ea",
                color="#5b6a79",
            ),
            ".chip.ws-parent {\n  font-weight: 600;\n}".strip(),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.score-ordered",
                background="#f1f4fa",
                border_color="#d9e0ed",
                color="#596a81",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip.founder-override",
                background="#fbf0ea",
                border_color="#ecd2c1",
                color="#8f5b45",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip-topology-source",
                background="#eef2fa",
                border_color="#d6dff0",
                color="#5a6a8b",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip-topology-parent",
                background="#eef7f5",
                border_color="#cee4de",
                color="#4a7369",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip-topology-depends",
                background="#f5f1fb",
                border_color="#e1d9ef",
                color="#6c628a",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".chip-topology-blocks",
                background="#faf2ea",
                border_color="#ecd8c1",
                color="#8c6947",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".chip-link",
                border_color="#c9d4e1",
                background="#f5f7fb",
                color="#536579",
                hover_border_color="#b4c3d3",
                hover_background="#edf1f7",
                hover_color="#3b4d61",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".chip-link.chip-topology-source",
                border_color="#c7d4ec",
                background="#eef2fa",
                color="#586a89",
                hover_border_color="#b4c4e0",
                hover_background="#e6edf8",
                hover_color="#41516d",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".chip-link.chip-topology-parent",
                border_color="#c7e0d9",
                background="#eef7f5",
                color="#4c7369",
                hover_border_color="#b7d4cb",
                hover_background="#e5f3ef",
                hover_color="#375b54",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".chip-link.chip-topology-depends",
                border_color="#d9cfea",
                background="#f5f1fb",
                color="#6c6289",
                hover_border_color="#cdbfe2",
                hover_background="#eee8f8",
                hover_color="#53496f",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".chip-link.chip-topology-blocks",
                border_color="#e7d3be",
                background="#faf2ea",
                color="#8a6948",
                hover_border_color="#dcc3a8",
                hover_background="#f5eadf",
                hover_color="#694d31",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".chip-link.chip-topology-diagram",
                border_color="#d0d8e5",
                background="#f1f4f9",
                color="#58708a",
                hover_border_color="#c0cad9",
                hover_background="#eaedf4",
                hover_color="#42566c",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".chip-link.chip-registry-component",
                border_color="#d8dde3",
                background="#f7f7f8",
                color="#626d77",
                hover_border_color="#c7cfd8",
                hover_background="#f0f2f4",
                hover_color="#47515c",
            ),
        )
    )
    block_heading_css = dashboard_ui_primitives.section_heading_css(
        selector=".block h3",
        color="#334155",
        size_px=13,
        letter_spacing_em=0.08,
        margin="0 0 8px",
    )
    trace_subhead_css = dashboard_ui_primitives.auxiliary_heading_css(
        selector=".block .trace-subhead",
        color="#475569",
        size_px=11,
        line_height=1.2,
        letter_spacing_em=0.07,
        margin="14px 0 8px",
    )
    radar_secondary_typography_css = "\n\n".join(
        (
            dashboard_ui_primitives.caption_typography_css(
                selector=".execution-legend",
                color="#334155",
                size_px=12,
                line_height=1.45,
            ),
            dashboard_ui_primitives.button_typography_css(
                selector=".analytics-toggle-hint",
                color="#334155",
                size_px=11,
                line_height=1.0,
                weight=700,
            ),
            dashboard_ui_primitives.caption_typography_css(
                selector=".chart-legend, .graph-note, .topology-relations-empty, .topology-rel-empty, .warning-meta",
                color="#475569",
                size_px=12,
                line_height=1.45,
            ),
            dashboard_ui_primitives.caption_typography_css(
                selector=".topology-rel-count",
                color="#334155",
                size_px=11,
                line_height=1.0,
                weight=800,
                letter_spacing_em=0.03,
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".topology-relations-panel > summary, .topology-rel-title",
                color="#475569",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.details_disclosure_caret_css(
                details_selector=".topology-relations-panel",
                label_selector=".topology-relations-toggle",
                color="#64748b",
                size_px=11,
                gap_px=6,
            ),
            dashboard_ui_primitives.label_badge_typography_css(
                selector=".topology-relations-summary",
                color="#334155",
                size_px=11,
                line_height=1.0,
                letter_spacing_em=0.03,
                weight=800,
                text_transform="none",
            ),
            dashboard_ui_primitives.value_emphasis_typography_css(
                selector=".kpi .v.v-compact",
                color="var(--ink)",
                size_px=14,
                line_height=1.2,
                weight=600,
                letter_spacing_em=-0.01,
                white_space="normal",
                overflow_wrap="anywhere",
                word_break="normal",
                text_wrap="balance",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".warning-title",
                color="#9a3412",
                size_px=12,
                line_height=1.45,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.caption_typography_css(
                selector=".warning-action",
                color="#1f2937",
                size_px=12,
                line_height=1.45,
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".meter-head",
                color="var(--ink-muted)",
                size_px=13,
                line_height=1.2,
                weight=600,
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".panel-head",
                color="var(--ink-muted)",
                size_px=12,
                line_height=1.2,
                letter_spacing_em=0.08,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".list-section-head",
                color="#5d6f83",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
        )
    )
    tooltip_surface_css, tooltip_runtime_js = dashboard_ui_runtime_primitives.quick_tooltip_bundle()
    execution_wave_css = execution_wave_ui_runtime_primitives.execution_wave_component_css()
    execution_wave_runtime_js = execution_wave_ui_runtime_primitives.execution_wave_runtime_helpers_js()
    return (
        template.replace("__ODYLITH_PAGE_BODY__", page_body_css)
        .replace("__ODYLITH_SURFACE_SHELL_ROOT__", surface_shell_root_css)
        .replace("__ODYLITH_SURFACE_SHELL__", surface_shell_css)
        .replace("__ODYLITH_BRAND_HEAD__", str(payload.get("brand_head_html", "")).strip())
        .replace("__ODYLITH_HERO_PANEL__", hero_panel_css)
        .replace("__ODYLITH_HEADER_TYPOGRAPHY__", header_typography_css)
        .replace("__ODYLITH_KPI_GRID_LAYOUT__", kpi_grid_layout_css)
        .replace("__ODYLITH_STAT_CARD_SURFACE__", stat_card_surface_css)
        .replace("__ODYLITH_STICKY_FILTER_BAR__", sticky_filter_css)
        .replace("__ODYLITH_DETAIL_IDENTITY_TYPOGRAPHY__", detail_identity_css)
        .replace("__ODYLITH_KPI_TYPOGRAPHY__", kpi_typography_css)
        .replace("__ODYLITH_RADAR_CHART_AXIS_TYPOGRAPHY__", chart_axis_css)
        .replace("__ODYLITH_RADAR_META_COPY__", meta_supporting_css)
        .replace("__ODYLITH_EXECUTION_WAVE_CSS__", execution_wave_css)
        .replace("__ODYLITH_EXECUTION_WAVE_RUNTIME_JS__", execution_wave_runtime_js)
        .replace("__ODYLITH_RADAR_OPERATOR_READOUT_LAYOUT__", "")
        .replace("__ODYLITH_RADAR_OPERATOR_READOUT_LABEL__", "")
        .replace("__ODYLITH_RADAR_OPERATOR_READOUT_COPY__", "")
        .replace("__ODYLITH_RADAR_OPERATOR_READOUT_META__", "")
        .replace("__ODYLITH_RADAR_OPERATOR_READOUT_RUNTIME_JS__", "")
        .replace("__ODYLITH_RADAR_READABLE_COPY__", radar_readable_copy_css)
        .replace("__ODYLITH_RADAR_CHIP_SURFACE__", passive_chip_surface_css)
        .replace("__ODYLITH_RADAR_CHIP_TYPOGRAPHY__", chip_label_css)
        .replace("__ODYLITH_RADAR_RANK_CHIP_SURFACE__", rank_chip_surface_css)
        .replace("__ODYLITH_RADAR_RANK_CHIP_TYPOGRAPHY__", rank_chip_css)
        .replace("__ODYLITH_RADAR_ROW_TITLE__", row_title_css)
        .replace("__ODYLITH_RADAR_ROW_ID__", row_id_css)
        .replace("__ODYLITH_RADAR_ANALYTICS_TITLE__", analytics_title_css)
        .replace("__ODYLITH_RADAR_DETAIL_KPI_SURFACE__", detail_kpi_surface_css)
        .replace("__ODYLITH_RADAR_DETAIL_KPI_TYPOGRAPHY__", detail_kpi_typography_css)
        .replace("__ODYLITH_RADAR_WORKSPACE_LAYOUT__", workspace_layout_css)
        .replace("__ODYLITH_RADAR_MIX_TOGGLE_BUTTON__", mix_toggle_button_css)
        .replace("__ODYLITH_RADAR_CHIP_LINK_CONTRACT__", chip_link_contract_css)
        .replace("__ODYLITH_RADAR_BLOCK_HEADING__", block_heading_css)
        .replace("__ODYLITH_RADAR_TRACE_SUBHEAD__", trace_subhead_css)
        .replace("__ODYLITH_RADAR_SECONDARY_TYPOGRAPHY__", radar_secondary_typography_css)
        .replace("__ODYLITH_RADAR_LABEL_SEMANTICS__", radar_label_semantic_css)
        .replace("__ODYLITH_RADAR_TOOLTIP_SURFACE__", tooltip_surface_css)
        .replace("__ODYLITH_RADAR_QUICK_TOOLTIP_RUNTIME__", tooltip_runtime_js)
        .replace("__STANDALONE_PAGES_HREF__", "standalone-pages.v1.js")
        .replace("__DATA__", data_blob)
    )

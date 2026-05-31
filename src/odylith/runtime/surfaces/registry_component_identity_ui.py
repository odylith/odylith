"""Component identity UI fragments for the Registry dashboard."""

from __future__ import annotations


def css() -> str:
    return """
.component-btn {
  min-height: 104px;
  align-content: start;
}

.component-card-title,
.component-meta {
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.summary-row {
  min-width: 0;
  overflow-wrap: anywhere;
}

.summary-artifact-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.artifact-compact {
  max-width: min(100%, 420px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: normal;
}

.component-identity {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.component-name {
  overflow-wrap: anywhere;
  word-break: normal;
}

.component-full-name {
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow-wrap: anywhere;
}

.component-id-line {
  color: #48617f;
  font-size: 12px;
  -webkit-line-clamp: 1;
}
""".strip()


def runtime_js() -> str:
    return """
function componentKind(row) {
  return humanizeToken(row && row.kind || "").trim();
}

function componentRawName(row) {
  return String(row && (row.name || row.component_id) || "").replace(/\\s+/g, " ").trim();
}

function componentCompactName(row, limit = 64) {
  const raw = componentRawName(row);
  if (!raw) return "Component";
  const kind = componentKind(row);
  let candidate = raw;
  if (candidate.length > limit) {
    const relativeClause = candidate.match(/\\s+(?:that|which|who|where|when|whose)\\s+/i);
    if (relativeClause && relativeClause.index >= 12) {
      candidate = candidate.slice(0, relativeClause.index).replace(/[ ,;:-]+$/, "").trim();
    }
  }
  if (
    kind
    && candidate
    && candidate !== raw
    && raw.toLowerCase().endsWith(` ${kind.toLowerCase()}`)
    && !candidate.toLowerCase().endsWith(` ${kind.toLowerCase()}`)
  ) {
    candidate = `${candidate} ${kind}`;
  }
  return clipText(candidate || raw, limit);
}

function componentFullIdentity(row) {
  const raw = componentRawName(row);
  const componentId = String(row && row.component_id || "").trim();
  if (raw && componentId && raw.toLowerCase() !== componentId.toLowerCase()) {
    return `${raw} (${componentId})`;
  }
  return raw || componentId || "Component";
}

function componentIdPreview(componentId, limit = 54) {
  return clipText(String(componentId || "").trim(), limit);
}

function componentComparableIdentity(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\\s+/g, " ").trim();
}

function componentDisplayIdLine(row, displayName) {
  const componentId = String(row && row.component_id || "").trim();
  if (!componentId) return "";
  const displayed = String(displayName || componentRawName(row) || "").trim();
  if (componentComparableIdentity(componentId) === componentComparableIdentity(displayed)) return "";
  return `<p class="component-full-name component-id-line">${escapeHtml(componentId)}</p>`;
}

function compactPathLabel(path, fallback = "Artifact") {
  const raw = String(path || "").trim();
  if (!raw) return fallback;
  if (raw.endsWith("/CURRENT_SPEC.md")) return "Component spec";
  if (raw.startsWith("src/")) return "Source boundary";
  return clipText(basenamePath(raw) || raw, 54);
}

function compactRegistryNarrative(value, row, limit = 420) {
  let text = String(value || "").replace(/\\s+/g, " ").trim();
  if (!text) return "";
  const rawName = componentRawName(row);
  const compactName = componentCompactName(row, 72);
  if (rawName && compactName && rawName !== compactName) {
    text = text.split(rawName).join(compactName);
  }
  return clipText(text, limit);
}

function splitInitialSourceBoundary(value) {
  const raw = String(value || "").replace(/\\s+/g, " ").trim();
  if (!raw) return { body: "", source: "" };
  const match = raw.match(/\\bInitial source boundary:\\s*(.+)$/i);
  if (!match) return { body: raw, source: "" };
  const body = raw.slice(0, match.index).trim().replace(/[. ]*$/, ".");
  const source = String(match[1] || "").trim().replace(/[. ]+$/, "");
  return { body, source };
}

function summaryTextRow(title, body) {
  const text = String(body || "").trim();
  return `<p class="summary-row"><strong>${escapeHtml(title)}:</strong> ${escapeHtml(text || "Not documented.")}</p>`;
}

function summaryArtifactRow(title, path, label) {
  const token = String(path || "").trim();
  if (!token) return "";
  return `
    <div class="summary-row summary-artifact-row">
      <strong>${escapeHtml(title)}:</strong>
      <span class="artifact-list">
        ${artifactChip(
          { path: token, href: token },
          token,
          "artifact artifact-compact",
          label || compactPathLabel(token, title),
        )}
      </span>
    </div>
  `;
}

function renderComponentListButton(row, selectedId) {
  const categoryToken = String(row.category || "").trim().toLowerCase();
  const coverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
  const fullIdentity = componentFullIdentity(row);
  const eventCount = Number(row.timeline_count || 0);
  const metaText = [componentIdPreview(row.component_id), humanizeToken(row.kind), humanizeToken(row.status || "active"), forensicCoverageLabel(coverage), `${eventCount} ${pluralize(eventCount, "event", "events")}`].filter(Boolean).join(" · ");
  return `
    <li>
      <button type="button" class="component-btn${row.component_id === selectedId ? " active" : ""}" data-component="${escapeHtml(row.component_id)}" title="${escapeHtml(fullIdentity)}" aria-label="${escapeHtml(fullIdentity)}">
        <span class="component-card-title">${escapeHtml(componentCompactName(row, 58))}</span>
        <span class="component-meta" title="${escapeHtml(fullIdentity)}">${escapeHtml(metaText)}</span>
        <span class="inline">
          <span class="label ${escapeHtml(toneClassForCategory(categoryToken))}">${escapeHtml(humanizeToken(categoryToken))}</span>
          <span class="label">${escapeHtml(humanizeToken(row.qualification || "curated"))}</span>
        </span>
      </button>
    </li>
  `;
}
""".strip()

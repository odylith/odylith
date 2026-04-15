"""Shared execution-wave UI primitives for generated dashboard surfaces.

Radar and Compass both render the same umbrella-owned execution-wave data, so
their section/card UX should not diverge through copy-pasted markup and CSS.
This module centralizes the shared visual contract and the browser-side helper
functions that render the canonical Radar execution-wave component.

Surface-specific renderers still own:
- payload lookup and scoping policy,
- workstream-chip navigation targets,
- where the component is mounted within the page.

The shared bundle owns:
- section and card layout,
- label/chip/status visual semantics,
- focus/header/card markup,
- collapse labels and summary text structure.
"""

from __future__ import annotations

from odylith.runtime.surfaces import dashboard_ui_primitives


def execution_wave_component_css(*, section_header_variant: str = "") -> str:
    """Return the shared execution-wave CSS bundle.

    The layout and tones intentionally mirror the current Radar implementation
    so Compass can reuse the exact same component contract instead of keeping a
    near-identical fork.
    """

    header_variant = str(section_header_variant or "").strip().lower()

    layout_css = """
.execution-wave-board {
  display: grid;
  gap: 14px;
}

.execution-wave-section {
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: linear-gradient(180deg, #f9fbff 0%, #ffffff 100%);
  overflow: hidden;
}

.execution-wave-program-stack {
  display: grid;
  gap: 24px;
}

.execution-wave-section summary {
  list-style: none;
}

.execution-wave-section summary::-webkit-details-marker {
  display: none;
}

.execution-wave-section-summary {
  cursor: pointer;
  padding: 16px 18px;
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.execution-wave-section-summary-compass {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px 16px;
}

.execution-wave-section-summary:hover {
  background: #f8fbff;
}

.execution-wave-section[open] .execution-wave-section-summary {
  border-bottom: 1px solid #dbeafe;
  background: linear-gradient(180deg, #f9fbff 0%, #ffffff 100%);
}

.execution-wave-section-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
  flex: 1 1 320px;
}

.execution-wave-section-line {
  color: #27445e;
  line-height: 1.55;
}

.execution-wave-section-line-muted {
  color: var(--ink-muted);
}

.execution-wave-section-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}

.execution-wave-section-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.execution-wave-section-meta-bottom {
  grid-column: 1 / -1;
  justify-content: flex-start;
  align-items: flex-start;
}

.execution-wave-section-toggle-triangle {
  width: 12px;
  min-width: 12px;
  height: 12px;
  align-self: start;
  justify-self: end;
}

.execution-wave-section-toggle-triangle::before {
  content: "";
  display: block;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 5px 0 5px 7px;
  border-color: transparent transparent transparent #1d4ed8;
  transform-origin: 35% 50%;
  transition: transform 120ms ease;
}

.execution-wave-section[open] .execution-wave-section-toggle-triangle::before {
  transform: rotate(90deg);
}

.execution-wave-section-body {
  padding: 16px 18px 18px;
  display: grid;
  gap: 16px;
}

.execution-wave-focus {
  border: 1px solid #c8dbee;
  border-radius: 14px;
  background: linear-gradient(135deg, #f9fbff 0%, #ffffff 58%, #f3faf7 100%);
  padding: 16px 18px;
}

.execution-wave-focus-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
}

.execution-wave-focus-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.execution-wave-focus-title {
  color: var(--ink);
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.execution-wave-focus-line {
  color: #27445e;
  line-height: 1.6;
  max-width: 70ch;
}

.execution-wave-focus-line-muted {
  color: var(--ink-muted);
}

.execution-wave-focus-stat-rail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  align-items: flex-start;
}

.execution-wave-sequence {
  display: grid;
  gap: 12px;
}

.execution-wave-card {
  position: relative;
  border: 1px solid #dbe5f1;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  overflow: hidden;
}

.execution-wave-card summary {
  list-style: none;
}

.execution-wave-card summary::-webkit-details-marker {
  display: none;
}

.execution-wave-card.is-member {
  border-color: #93c5fd;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.execution-wave-card.wave-status-active {
  border-color: #bfdbfe;
  background: linear-gradient(180deg, #f5faff 0%, #ffffff 100%);
}

.execution-wave-card.is-current-wave {
  border-color: #60a5fa;
  background: linear-gradient(135deg, #eff6ff 0%, #ffffff 56%, #ecfeff 100%);
  box-shadow: 0 18px 40px -32px rgba(37, 99, 235, 0.55);
}

.execution-wave-card-summary {
  cursor: pointer;
  padding: 14px 16px;
}

.execution-wave-card-summary:hover {
  background: #f8fbff;
}

.execution-wave-card[open] .execution-wave-card-summary {
  background: linear-gradient(180deg, #f9fbff 0%, #ffffff 100%);
  border-bottom: 1px solid #dbeafe;
}

.execution-wave-card.is-current-wave .execution-wave-card-summary {
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.92) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.execution-wave-card.is-current-wave .execution-wave-card-summary:hover {
  background: linear-gradient(180deg, #eaf3ff 0%, #ffffff 100%);
}

.execution-wave-card.is-current-wave[open] .execution-wave-card-summary {
  background: linear-gradient(180deg, #eaf3ff 0%, #ffffff 100%);
  border-bottom: 1px solid #bfdbfe;
}

.execution-wave-card-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
}

.execution-wave-card-shell-full-copy {
  grid-template-areas:
    "title meta"
    "sub sub"
    "compact compact";
  row-gap: 8px;
}

.execution-wave-card-copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.execution-wave-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.execution-wave-card-shell-full-copy .execution-wave-title-row {
  grid-area: title;
  min-width: 0;
}

.execution-wave-title {
  color: var(--ink);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.01em;
  min-width: 0;
}

.execution-wave-sub {
  color: #27445e;
  line-height: 1.6;
  max-width: 72ch;
}

.execution-wave-card-shell-full-copy .execution-wave-sub {
  grid-area: sub;
  max-width: none;
  min-width: 0;
}

.execution-wave-compact {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
}

.execution-wave-card-shell-full-copy .execution-wave-compact {
  grid-area: compact;
  min-width: 0;
}

.execution-wave-compact-line {
  color: var(--ink-muted);
  line-height: 1.45;
  font-size: 13px;
}

.execution-wave-compact-line-strong {
  color: #35506b;
  font-weight: 600;
}

.execution-wave-card.is-current-wave .execution-wave-compact-line-strong {
  color: #1e3a8a;
}

.execution-wave-card-meta {
  display: grid;
  gap: 10px;
  justify-items: end;
  align-content: start;
  min-width: 180px;
}

.execution-wave-card-shell-full-copy .execution-wave-card-meta {
  grid-area: meta;
}

.execution-wave-card-stat-rail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  max-width: 240px;
}

.execution-wave-card-toggle-line {
  display: flex;
  justify-content: flex-end;
}

.execution-wave-card-body {
  padding: 12px 16px 16px;
  display: grid;
  gap: 12px;
}

.execution-wave-body-grid {
  display: grid;
  gap: 10px;
}

.execution-wave-body-grid-top {
  grid-template-columns: minmax(0, 1fr);
}

.execution-wave-body-grid-members {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

@media (max-width: 1280px) {
  .execution-wave-body-grid-members {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.execution-wave-panel {
  border: 1px solid #e3ebf5;
  border-radius: 12px;
  background: #f8fbff;
  padding: 12px;
  display: grid;
  gap: 8px;
  align-content: start;
  min-width: 0;
}

.execution-wave-support-panel {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  grid-column: 1 / -1;
}

.execution-wave-highlight {
  display: grid;
  gap: 4px;
}

.execution-wave-highlight-label,
.execution-wave-group-label {
  color: #6a7e96;
  font-size: 11px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  line-height: 1.2;
}

.execution-wave-highlight-copy {
  color: #27445e;
  line-height: 1.55;
}

.execution-wave-highlight-copy-strong {
  color: #1e3a8a;
  font-weight: 600;
}

.execution-wave-group-body {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
  align-content: flex-start;
  min-height: 28px;
}

.execution-wave-gates {
  display: grid;
  gap: 10px;
}

.execution-wave-gate {
  border: 1px solid #d9e5f2;
  border-radius: 11px;
  background: #ffffff;
  padding: 10px 11px;
}

.execution-wave-gate-label {
  color: #27445e;
  line-height: 1.55;
}

.execution-wave-gate-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

@media (max-width: 900px) {
  .execution-wave-section-summary,
  .execution-wave-section-body {
    padding-left: 14px;
    padding-right: 14px;
  }

  .execution-wave-focus,
  .execution-wave-card-summary,
  .execution-wave-card-body {
    padding-left: 14px;
    padding-right: 14px;
  }

  .execution-wave-focus-grid,
  .execution-wave-card-shell {
    grid-template-columns: minmax(0, 1fr);
  }

  .execution-wave-card-shell-full-copy {
    grid-template-areas:
      "title"
      "meta"
      "sub"
      "compact";
  }

  .execution-wave-body-grid-members {
    grid-template-columns: minmax(0, 1fr);
  }

  .execution-wave-focus-stat-rail,
  .execution-wave-card-stat-rail,
  .execution-wave-section-meta {
    justify-content: flex-start;
  }

  .execution-wave-section-summary-compass {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .execution-wave-section-meta-bottom {
    justify-content: flex-start;
  }

  .execution-wave-card-meta,
  .execution-wave-card-toggle-line {
    justify-items: start;
    justify-content: flex-start;
    min-width: 0;
  }
}
""".strip()

    supporting_css = "\n\n".join(
        (
            dashboard_ui_primitives.section_heading_css(
                selector=".execution-wave-section-title",
                color="#334155",
                size_px=13,
                letter_spacing_em=0.08,
                margin="0",
            ),
            dashboard_ui_primitives.caption_typography_css(
                selector=".execution-wave-empty",
                color="#475569",
                size_px=12,
                line_height=1.45,
            ),
            dashboard_ui_primitives.label_surface_css(
                selector=".label.execution-wave-label",
            ),
            dashboard_ui_primitives.label_badge_typography_css(
                selector=".label.execution-wave-label",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".label.execution-wave-label.wave-status-active",
                background="#ecfeff",
                border_color="#99f6e4",
                color="#0f766e",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".label.execution-wave-label.wave-status-planned",
                background="#eff6ff",
                border_color="#bfdbfe",
                color="#1d4ed8",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".label.execution-wave-label.wave-status-blocked",
                background="#fff7ed",
                border_color="#fdba74",
                color="#c2410c",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".label.execution-wave-label.wave-status-complete",
                background="#ecfdf5",
                border_color="#86efac",
                color="#166534",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".label.execution-wave-label.wave-current-chip",
                background="#dbeafe",
                border_color="#60a5fa",
                color="#1e3a8a",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".label.execution-wave-label.wave-progress-chip",
                background="#f7f5ea",
                border_color="#ddd6ae",
                color="#6b5f2a",
            ),
            dashboard_ui_primitives.surface_workstream_button_chip_css(
                selector=".execution-wave-chip-link",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".execution-wave-chip-link.wave-member-selected",
                background="#dbeafe",
                border_color="#93c5fd",
                color="#1e3a8a",
                hover_border_color="#60a5fa",
                hover_background="#cfe3ff",
                hover_color="#1d4ed8",
            ),
            """
.execution-wave-plan-link {
  cursor: pointer;
}

.execution-wave-plan-link:hover,
.execution-wave-plan-link:focus-visible {
  --label-border: #bfdbfe;
  --label-bg: #eef6ff;
  --label-text: #1e3a8a;
}

.execution-wave-plan-link:focus-visible {
  outline: 2px solid #bfdbfe;
  outline-offset: 1px;
}
""".strip(),
        )
    )
    return "\n\n".join((layout_css, supporting_css))


def execution_wave_runtime_helpers_js() -> str:
    """Return shared browser-side helpers for execution-wave rendering."""

    return """
function waveStatusChipClass(status) {
  const token = String(status || "").trim().toLowerCase();
  if (token === "active") return "wave-status-active";
  if (token === "planned") return "wave-status-planned";
  if (token === "blocked") return "wave-status-blocked";
  if (token === "complete") return "wave-status-complete";
  return "wave-status-other";
}

function executionWavePercent(numerator, denominator) {
  const value = Number(numerator || 0);
  const total = Number(denominator || 0);
  if (!Number.isFinite(value) || !Number.isFinite(total) || total <= 0) return "";
  const boundedValue = Math.min(Math.max(value, 0), total);
  return `${Math.round((boundedValue / total) * 100)}%`;
}

function executionWaveProgressRatio(value) {
  const ratio = Number(value);
  if (!Number.isFinite(ratio)) return null;
  return Math.min(Math.max(ratio, 0), 1);
}

function executionWaveRefIdeaId(ref) {
  if (!ref || typeof ref !== "object") return "";
  return String(ref.idea_id || ref.workstream_id || "").trim();
}

function executionWaveResolvedStatus(ref, options = {}) {
  const explicitStatus = String(ref && ref.status ? ref.status : "").trim().toLowerCase();
  if (explicitStatus) return explicitStatus;
  const resolveWorkstreamStatus = typeof options.resolveWorkstreamStatus === "function"
    ? options.resolveWorkstreamStatus
    : null;
  if (!resolveWorkstreamStatus) return "";
  const resolvedStatus = String(resolveWorkstreamStatus(ref) || "").trim().toLowerCase();
  return resolvedStatus;
}

function executionWaveResolvedProgress(ref, options = {}) {
  const resolveWorkstreamProgress = typeof options.resolveWorkstreamProgress === "function"
    ? options.resolveWorkstreamProgress
    : null;
  if (!resolveWorkstreamProgress) return null;
  return executionWaveProgressRatio(resolveWorkstreamProgress(ref));
}

function executionWaveStatusIsClosed(status) {
  return status === "finished" || status === "complete" || status === "parked" || status === "superseded";
}

function executionWaveWorkstreamCompletion(workstreams, options = {}) {
  const rows = Array.isArray(workstreams) ? workstreams : [];
  let totalCount = 0;
  let completeCount = 0;
  rows.forEach((row) => {
    const ideaId = executionWaveRefIdeaId(row);
    if (!ideaId) return;
    totalCount += 1;
    const status = executionWaveResolvedStatus(row, options);
    if (executionWaveStatusIsClosed(status)) {
      completeCount += 1;
    }
  });
  return {
    totalCount,
    completeCount,
    progress_ratio: totalCount > 0 ? (completeCount / totalCount) : 0,
    percent: executionWavePercent(completeCount, totalCount),
  };
}

function executionWaveWorkstreamProgress(workstreams, options = {}) {
  const rows = Array.isArray(workstreams) ? workstreams : [];
  let totalCount = 0;
  let progressTotal = 0;
  rows.forEach((row) => {
    const ideaId = executionWaveRefIdeaId(row);
    if (!ideaId) return;
    totalCount += 1;
    const explicitProgress = executionWaveResolvedProgress(row, options);
    if (explicitProgress !== null) {
      progressTotal += explicitProgress;
      return;
    }
    const status = executionWaveResolvedStatus(row, options);
    progressTotal += executionWaveStatusIsClosed(status) ? 1 : 0;
  });
  return {
    totalCount,
    progress_ratio: totalCount > 0 ? (progressTotal / totalCount) : 0,
    percent: executionWavePercent(progressTotal, totalCount),
  };
}

function executionWaveWaveCompletion(wave, options = {}) {
  if (!wave || typeof wave !== "object") {
    return { totalCount: 0, completeCount: 0, progress_ratio: 0, percent: "" };
  }
  const gateRefs = Array.isArray(wave.gate_refs) ? wave.gate_refs : [];
  if (gateRefs.length) return executionWaveWorkstreamCompletion(gateRefs, options);
  const allMembers = Array.isArray(wave.all_workstreams) ? wave.all_workstreams : [];
  return executionWaveWorkstreamCompletion(allMembers, options);
}

function executionWaveWaveProgress(wave, options = {}) {
  if (!wave || typeof wave !== "object") {
    return { totalCount: 0, progress_ratio: 0, percent: "" };
  }
  const gateRefs = Array.isArray(wave.gate_refs) ? wave.gate_refs : [];
  if (gateRefs.length) return executionWaveWorkstreamProgress(gateRefs, options);
  const allMembers = Array.isArray(wave.all_workstreams) ? wave.all_workstreams : [];
  return executionWaveWorkstreamProgress(allMembers, options);
}

function executionWaveProgramCompletion(program, options = {}) {
  if (!program || typeof program !== "object") {
    return { totalCount: 0, completeCount: 0, progress_ratio: 0, percent: "" };
  }
  const waves = Array.isArray(program.waves) ? program.waves : [];
  const dedupedMembers = [];
  const seen = new Set();
  waves.forEach((wave) => {
    const gateRefs = Array.isArray(wave && wave.gate_refs) ? wave.gate_refs : [];
    const members = gateRefs.length
      ? gateRefs
      : (Array.isArray(wave && wave.all_workstreams) ? wave.all_workstreams : []);
    members.forEach((member) => {
      const ideaId = executionWaveRefIdeaId(member);
      if (!ideaId || seen.has(ideaId)) return;
      seen.add(ideaId);
      dedupedMembers.push(member);
    });
  });
  return executionWaveWorkstreamCompletion(dedupedMembers, options);
}

function executionWaveProgramProgress(program, options = {}) {
  if (!program || typeof program !== "object") {
    return { totalCount: 0, progress_ratio: 0, percent: "" };
  }
  const waves = Array.isArray(program.waves) ? program.waves : [];
  const dedupedMembers = [];
  const seen = new Set();
  waves.forEach((wave) => {
    const gateRefs = Array.isArray(wave && wave.gate_refs) ? wave.gate_refs : [];
    const members = gateRefs.length
      ? gateRefs
      : (Array.isArray(wave && wave.all_workstreams) ? wave.all_workstreams : []);
    members.forEach((member) => {
      const ideaId = executionWaveRefIdeaId(member);
      if (!ideaId || seen.has(ideaId)) return;
      seen.add(ideaId);
      dedupedMembers.push(member);
    });
  });
  return executionWaveWorkstreamProgress(dedupedMembers, options);
}

function executionWaveSummaryLine(program, options = {}) {
  if (!program || typeof program !== "object") return "";
  const currentWave = program.current_wave && typeof program.current_wave === "object"
    ? String(program.current_wave.label || program.current_wave.wave_id || "").trim()
    : "";
  const active = Array.isArray(program.active_waves)
    ? program.active_waves.map((row) => String(row && row.label ? row.label : "").trim()).filter(Boolean)
    : [];
  const blocked = Array.isArray(program.blocked_waves)
    ? program.blocked_waves.map((row) => String(row && row.label ? row.label : "").trim()).filter(Boolean)
    : [];
  const nextWave = program.next_wave && typeof program.next_wave === "object"
    ? String(program.next_wave.label || "").trim()
    : "";
  const programCompletion = executionWaveProgramCompletion(program, options);
  const parts = [];
  if (currentWave) parts.push(`Current: ${currentWave}`);
  if (active.length) {
    const otherActive = currentWave ? active.filter((label) => label !== currentWave) : active;
    if (!currentWave) parts.push(`Active now: ${active.join(", ")}`);
    else if (otherActive.length) parts.push(`Also active: ${otherActive.join(", ")}`);
  }
  if (nextWave && nextWave !== currentWave) parts.push(`Next: ${nextWave}`);
  if (blocked.length) parts.push(`Blocked: ${blocked.join(", ")}`);
  if (programCompletion.totalCount > 0) parts.push(`Closed gate workstreams: ${programCompletion.completeCount}/${programCompletion.totalCount}`);
  return parts.join(" · ");
}

function renderExecutionWaveMemberChips(members, selectedWorkstreamId, options = {}) {
  const rows = Array.isArray(members) ? members : [];
  const emptyStateClass = String(options.emptyStateClass || "execution-wave-empty").trim() || "execution-wave-empty";
  const renderMemberChip = typeof options.renderMemberChip === "function"
    ? options.renderMemberChip
    : null;
  if (!rows.length) return `<span class="${emptyStateClass}">None</span>`;
  if (!renderMemberChip) return `<span class="${emptyStateClass}">None</span>`;
  return rows
    .map((member) => {
      const ideaId = String(member && member.idea_id ? member.idea_id : "").trim();
      if (!ideaId) return "";
      return renderMemberChip(ideaId, { selected: ideaId === String(selectedWorkstreamId || "").trim() });
    })
    .filter(Boolean)
    .join("");
}

function renderExecutionWaveGateRows(gateRefs, selectedWorkstreamId, options = {}) {
  const rows = Array.isArray(gateRefs) ? gateRefs : [];
  const escapeHtml = typeof options.escapeHtml === "function" ? options.escapeHtml : (value) => String(value || "");
  const emptyStateClass = String(options.emptyStateClass || "execution-wave-empty").trim() || "execution-wave-empty";
  const renderMemberChip = typeof options.renderMemberChip === "function"
    ? options.renderMemberChip
    : null;
  const planHrefForPath = typeof options.planHrefForPath === "function"
    ? options.planHrefForPath
    : () => "";
  if (!rows.length) return `<span class="${emptyStateClass}">No explicit gate refs.</span>`;
  return rows
    .map((gate) => {
      const ideaId = String(gate && gate.workstream_id ? gate.workstream_id : "").trim();
      const label = String(gate && gate.label ? gate.label : "").trim();
      const planPath = String(gate && gate.plan_path ? gate.plan_path : "").trim();
      const planLabel = planPath ? planPath.split("/").pop() : "";
      const planHref = planPath ? String(planHrefForPath(planPath) || "").trim() : "";
      const chips = [];
      if (renderMemberChip && ideaId) {
        chips.push(renderMemberChip(ideaId, { selected: ideaId === String(selectedWorkstreamId || "").trim() }));
      }
      if (planLabel) {
        if (planHref) {
          chips.push(`<a class="label execution-wave-label wave-chip-program execution-wave-plan-link" href="${escapeHtml(planHref)}" target="_top">${escapeHtml(planLabel)}</a>`);
        } else {
          chips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(planLabel)}</span>`);
        }
      }
      return `
        <div class="execution-wave-gate">
          <div class="execution-wave-gate-label">${escapeHtml(label || "Gate reference")}</div>
          ${chips.length ? `<div class="execution-wave-gate-meta">${chips.join("")}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function renderExecutionWaveProgram(program, selectedWorkstreamId, context, options = {}) {
  if (!program || typeof program !== "object") return "";
  const escapeHtml = typeof options.escapeHtml === "function" ? options.escapeHtml : (value) => String(value || "");
  const waves = Array.isArray(program.waves) ? program.waves : [];
  if (!waves.length) return "";
  const showProgramFocusTitle = options.hideProgramFocusTitle !== true;

  const contextMeta = context && typeof context === "object" ? context : null;
  const selectedWorkstream = String(selectedWorkstreamId || "").trim();
  const currentWaveId = program.current_wave && typeof program.current_wave === "object"
    ? String(program.current_wave.wave_id || "").trim()
    : "";
  const selectedBadgeLabel = String(options.selectedBadgeLabel || "Selected").trim() || "Selected";
  const selectedCardClass = String(options.selectedCardClass || "is-member").trim() || "is-member";
  const selectedNoteBuilder = typeof options.selectedNoteText === "function"
    ? options.selectedNoteText
    : () => String(options.selectedNoteText || "").trim();

  const contextChips = [];
  if (contextMeta) {
    const waveSpan = String(contextMeta.wave_span_label || "").trim();
    const roleLabel = String(contextMeta.role_label || "").trim();
    if (waveSpan) contextChips.push(`<span class="label execution-wave-label wave-status-active">${escapeHtml(waveSpan)}</span>`);
    if (roleLabel) contextChips.push(`<span class="label execution-wave-label wave-role-chip">${escapeHtml(roleLabel)}</span>`);
    if (contextMeta.has_next_wave) contextChips.push('<span class="label execution-wave-label wave-status-planned">Next relevant</span>');
  }

  const cardsHtml = waves.map((wave) => {
    const primaryMembers = Array.isArray(wave.primary_workstreams) ? wave.primary_workstreams : [];
    const carriedMembers = Array.isArray(wave.carried_workstreams) ? wave.carried_workstreams : [];
    const inBandMembers = Array.isArray(wave.in_band_workstreams) ? wave.in_band_workstreams : [];
    const allMembers = Array.isArray(wave.all_workstreams) ? wave.all_workstreams : [];
    const isSelectedMember = allMembers.some((member) => String(member && member.idea_id ? member.idea_id : "").trim() === selectedWorkstream);
    const gateRefs = Array.isArray(wave.gate_refs) ? wave.gate_refs : [];
    const summary = String(wave.summary || "").trim();
    const waveLabel = String(wave.label || wave.wave_id || "").trim();
    const waveStatus = String(wave.status_label || wave.status || "").trim();
    const waveTone = waveStatusChipClass(wave.status);
    const compactSummaryLine = String(wave.compact_summary_line || "").trim();
    const gatePreview = String(wave.gate_preview_summary || "").trim();
    const dependsOnLabels = Array.isArray(wave.depends_on_labels)
      ? wave.depends_on_labels.map((token) => String(token || "").trim()).filter(Boolean)
      : [];
    const isCurrentWave = Boolean(wave.is_current_wave) || (
      currentWaveId && currentWaveId === String(wave.wave_id || "").trim()
    );
    const totalWaveCount = Number(program.wave_count || waves.length || 0);
    const sequenceCount = Number(wave.sequence || 0);
    const sequenceChip = `${sequenceCount} of ${totalWaveCount}`;
    const waveProgress = executionWaveWaveProgress(wave, options);
    const progressChip = waveProgress.percent ? `${waveProgress.percent} progress` : "";
    const openAttr = "";
    const selectedNote = isSelectedMember ? String(selectedNoteBuilder(selectedWorkstream, contextMeta) || "").trim() : "";
    const supportBlocks = [];
    if (gatePreview) {
      supportBlocks.push(`
        <div class="execution-wave-highlight">
          <div class="execution-wave-highlight-label">Gate focus</div>
          <div class="execution-wave-highlight-copy">${escapeHtml(gatePreview)}</div>
        </div>
      `);
    }
    if (selectedNote) {
      supportBlocks.push(`
        <div class="execution-wave-highlight">
          <div class="execution-wave-highlight-label">Selected scope</div>
          <div class="execution-wave-highlight-copy execution-wave-highlight-copy-strong">${escapeHtml(selectedNote)}</div>
        </div>
      `);
    }
    const supportPanelHtml = supportBlocks.length
      ? `<div class="execution-wave-panel execution-wave-support-panel">${supportBlocks.join("")}</div>`
      : "";
    const dependsOnHtml = dependsOnLabels.length
      ? dependsOnLabels.map((label) => `<span class="label execution-wave-label wave-status-planned">${escapeHtml(label)}</span>`).join("")
      : '<span class="execution-wave-empty">Starts here</span>';
    const memberPanelsHtml = [
      { label: "Depends On", contentHtml: dependsOnHtml },
      { label: "Primary", contentHtml: renderExecutionWaveMemberChips(primaryMembers, selectedWorkstream, options) },
      { label: "Carried", contentHtml: renderExecutionWaveMemberChips(carriedMembers, selectedWorkstream, options) },
      { label: "In Band", contentHtml: renderExecutionWaveMemberChips(inBandMembers, selectedWorkstream, options) },
    ]
      .map(({ label, contentHtml }) => `
        <div class="execution-wave-panel">
          <div class="execution-wave-group-label">${escapeHtml(label)}</div>
          <div class="execution-wave-group-body">${contentHtml}</div>
        </div>
      `)
      .join("");
    const cardClassNames = ["execution-wave-card", escapeHtml(waveTone)];
    if (isSelectedMember) cardClassNames.push(escapeHtml(selectedCardClass));
    if (isCurrentWave) cardClassNames.push("is-current-wave");
    return `
      <details class="${cardClassNames.join(" ")}"${openAttr}>
        <summary class="execution-wave-card-summary">
          <div class="execution-wave-card-shell execution-wave-card-shell-full-copy">
            <div class="execution-wave-title-row">
              <div class="execution-wave-title">${escapeHtml(waveLabel)}</div>
              <span class="label execution-wave-label wave-chip-program">${escapeHtml(sequenceChip)}</span>
              ${progressChip ? `<span class="label execution-wave-label wave-progress-chip">${escapeHtml(progressChip)}</span>` : ""}
            </div>
            <div class="execution-wave-card-meta">
              <div class="execution-wave-card-stat-rail">
                ${isCurrentWave ? '<span class="label execution-wave-label wave-current-chip">Current wave</span>' : ""}
                <span class="label execution-wave-label ${escapeHtml(waveTone)}">${escapeHtml(waveStatus)}</span>
                <span class="label execution-wave-label wave-program-chip">${escapeHtml(`${Number(wave.member_count || 0)} member${Number(wave.member_count || 0) === 1 ? "" : "s"}`)}</span>
                ${gateRefs.length ? `<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${gateRefs.length} gate${gateRefs.length === 1 ? "" : "s"}`)}</span>` : ""}
                ${isSelectedMember ? `<span class="label execution-wave-label wave-role-chip">${escapeHtml(selectedBadgeLabel)}</span>` : ""}
              </div>
            </div>
            <div class="execution-wave-sub">${escapeHtml(summary || "No wave summary recorded.")}</div>
            ${compactSummaryLine ? `<div class="execution-wave-compact"><div class="execution-wave-compact-line execution-wave-compact-line-strong">${escapeHtml(compactSummaryLine)}</div></div>` : ""}
          </div>
        </summary>
        <div class="execution-wave-card-body">
          ${supportPanelHtml ? `<div class="execution-wave-body-grid execution-wave-body-grid-top">${supportPanelHtml}</div>` : ""}
          <div class="execution-wave-body-grid execution-wave-body-grid-members">
            ${memberPanelsHtml}
          </div>
          ${gateRefs.length ? `<div class="execution-wave-panel"><div class="execution-wave-group-label">Gate Checks</div><div class="execution-wave-gates">${renderExecutionWaveGateRows(gateRefs, selectedWorkstream, options)}</div></div>` : ""}
        </div>
      </details>
    `;
  }).join("");

  const summaryLine = executionWaveSummaryLine(program, options);
  const umbrellaTitle = String(program.umbrella_title || "").trim();
  const umbrellaId = String(program.umbrella_id || "").trim();
  const programLabel = umbrellaTitle && umbrellaId
    ? `${umbrellaTitle} (${umbrellaId})`
    : (umbrellaTitle || umbrellaId);
  const contextLine = contextMeta
    ? `This workstream participates across ${String(contextMeta.wave_span_label || "").trim() || "the program"} as ${String(contextMeta.role_label || "").trim() || "a member"}.`
    : "Umbrella-owned execution waves for this program.";

  return `
    <div class="execution-wave-board">
      <div class="execution-wave-focus">
        <div class="execution-wave-focus-grid">
          <div class="execution-wave-focus-copy">
            ${showProgramFocusTitle ? `<div class="execution-wave-focus-title">${escapeHtml(programLabel)}</div>` : ""}
            <div class="execution-wave-focus-line">${escapeHtml(contextLine)}</div>
            ${summaryLine ? `<div class="execution-wave-focus-line execution-wave-focus-line-muted">${escapeHtml(summaryLine)}</div>` : ""}
          </div>
          ${contextChips.length ? `<div class="execution-wave-focus-stat-rail">${contextChips.join("")}</div>` : ""}
        </div>
      </div>
      <div class="execution-wave-sequence">${cardsHtml}</div>
    </div>
  `;
}

function renderExecutionWaveSection(sectionModel, options = {}) {
  const section = sectionModel && typeof sectionModel === "object" ? sectionModel : {};
  const entries = Array.isArray(section.entries) ? section.entries : [];
  if (!entries.length) return "";
  const escapeHtml = typeof options.escapeHtml === "function" ? options.escapeHtml : (value) => String(value || "");
  const sectionTitle = String(section.title || "Execution Waves").trim() || "Execution Waves";
  const programLabel = String(section.programLabel || "").trim();
  const contextLine = String(section.contextLine || "").trim();
  const summaryLine = String(section.summaryLine || "").trim();
  const selectedWorkstreamId = String(section.selectedWorkstreamId || "").trim();
  const sectionChips = Array.isArray(section.sectionChips)
    ? section.sectionChips.filter((row) => String(row || "").trim())
    : [];
  const boardWrapperClass = String(options.boardWrapperClass || "").trim();
  const boardsHtml = entries
    .map((entry) => renderExecutionWaveProgram(
      entry && entry.program ? entry.program : null,
      selectedWorkstreamId,
      entry && entry.context ? entry.context : null,
      options,
    ))
    .filter(Boolean)
    .map((boardHtml) => (
      boardWrapperClass
        ? `<div class="${escapeHtml(boardWrapperClass)}">${boardHtml}</div>`
        : boardHtml
    ))
    .join("");
  if (!boardsHtml) return "";
  const openAttr = section.openByDefault ? " open" : "";
  const sectionHeaderVariant = String(options.sectionHeaderVariant || "").trim().toLowerCase();
  if (sectionHeaderVariant === "compass") {
    return `
      <section class="block">
        <details class="execution-wave-section"${openAttr}>
          <summary class="execution-wave-section-summary execution-wave-section-summary-compass">
            <div class="execution-wave-section-copy">
              <div class="execution-wave-section-title">${escapeHtml(sectionTitle)}</div>
              ${programLabel ? `<div class="execution-wave-section-line">${escapeHtml(programLabel)}</div>` : ""}
              ${contextLine ? `<div class="execution-wave-section-line">${escapeHtml(contextLine)}</div>` : ""}
              ${summaryLine ? `<div class="execution-wave-section-line execution-wave-section-line-muted">${escapeHtml(summaryLine)}</div>` : ""}
            </div>
            <span class="execution-wave-section-toggle execution-wave-section-toggle-triangle" aria-hidden="true"></span>
            ${sectionChips.length ? `<div class="execution-wave-section-meta execution-wave-section-meta-bottom">${sectionChips.join("")}</div>` : ""}
          </summary>
          <div class="execution-wave-section-body">${boardsHtml}</div>
        </details>
      </section>
    `;
  }
  return `
    <section class="block">
      <details class="execution-wave-section"${openAttr}>
        <summary class="execution-wave-section-summary">
          <div class="execution-wave-section-copy">
            <div class="execution-wave-section-title">${escapeHtml(sectionTitle)}</div>
            ${programLabel ? `<div class="execution-wave-section-line">${escapeHtml(programLabel)}</div>` : ""}
            ${contextLine ? `<div class="execution-wave-section-line">${escapeHtml(contextLine)}</div>` : ""}
            ${summaryLine ? `<div class="execution-wave-section-line execution-wave-section-line-muted">${escapeHtml(summaryLine)}</div>` : ""}
          </div>
          <div class="execution-wave-section-meta">
            ${sectionChips.join("")}
            <span class="execution-wave-section-toggle execution-wave-section-toggle-triangle" aria-hidden="true"></span>
          </div>
        </summary>
        <div class="execution-wave-section-body">${boardsHtml}</div>
      </details>
    </section>
  `;
}
""".strip()


__all__ = [
    "execution_wave_component_css",
    "execution_wave_runtime_helpers_js",
]

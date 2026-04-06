from __future__ import annotations

import re

from odylith.runtime.surfaces import execution_wave_ui_runtime_primitives as execution_wave_ui


def test_execution_wave_component_css_matches_shared_contract() -> None:
    css = execution_wave_ui.execution_wave_component_css()

    assert ".execution-wave-section" in css
    assert ".execution-wave-card" in css
    assert ".execution-wave-card.is-member" in css
    assert ".execution-wave-card.wave-status-active" in css
    assert ".execution-wave-card.is-current-wave" in css
    assert ".execution-wave-focus-grid" in css
    assert ".execution-wave-card-shell" in css
    assert ".execution-wave-panel" in css
    assert ".execution-wave-chip-link" in css
    assert ".execution-wave-chip-link.wave-member-selected" in css
    assert ".label.execution-wave-label" in css
    assert ".label.execution-wave-label.wave-status-active" in css
    assert ".label.execution-wave-label.wave-current-chip" in css
    assert ".label.execution-wave-label.wave-progress-chip" in css
    assert ".chip.wave-chip" not in css
    assert ".chip.wave-status-active" not in css
    assert ".chip.wave-status-planned" not in css
    assert ".chip.wave-chip-program" not in css
    assert ".chip.wave-role-chip" not in css
    assert ".chip.wave-member-selected" not in css
    assert "box-shadow: inset 0 0 0 1px" not in css
    assert re.search(
        r"\.label\.execution-wave-label\s*\{[^}]*border:\s*1px solid var\(--label-border\);[^}]*border-radius:\s*4px;[^}]*padding:\s*4px 10px;",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.execution-wave-chip-link\s*\{[^}]*font-family:\s*inherit;[^}]*color:\s*var\(--chip-link-text\);[^}]*font-size:\s*11px;[^}]*line-height:\s*1;[^}]*letter-spacing:\s*0\.01em;[^}]*font-weight:\s*700;",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.execution-wave-body-grid-top\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\);",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.execution-wave-body-grid-members\s*\{[^}]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\);",
        css,
        flags=re.S,
    )
    assert re.search(
        r"@media\s*\(max-width:\s*1280px\)\s*\{[^}]*\.execution-wave-body-grid-members\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\);",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.execution-wave-panel\s*\{[^}]*display:\s*grid;[^}]*gap:\s*8px;[^}]*align-content:\s*start;[^}]*min-width:\s*0;",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.execution-wave-card-body\s*\{[^}]*padding:\s*12px 16px 16px;[^}]*display:\s*grid;[^}]*gap:\s*12px;",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.execution-wave-support-panel\s*\{[^}]*grid-column:\s*1\s*/\s*-1;",
        css,
        flags=re.S,
    )
    assert re.search(
        r"\.execution-wave-group-body\s*\{[^}]*display:\s*flex;[^}]*flex-wrap:\s*wrap;[^}]*gap:\s*8px;[^}]*align-items:\s*flex-start;[^}]*align-content:\s*flex-start;[^}]*min-height:\s*28px;",
        css,
        flags=re.S,
    )
    assert "@media (max-width: 900px)" in css
    assert re.search(
        r"@media\s*\(max-width:\s*900px\)\s*\{.*?\.execution-wave-body-grid-members\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\);",
        css,
        flags=re.S,
    )


def test_execution_wave_runtime_helpers_expose_shared_renderer() -> None:
    runtime = execution_wave_ui.execution_wave_runtime_helpers_js()

    assert "function waveStatusChipClass(status)" in runtime
    assert "function executionWavePercent(numerator, denominator)" in runtime
    assert "function executionWaveProgressRatio(value)" in runtime
    assert "function executionWaveRefIdeaId(ref)" in runtime
    assert "function executionWaveResolvedStatus(ref, options = {})" in runtime
    assert "function executionWaveResolvedProgress(ref, options = {})" in runtime
    assert "function executionWaveStatusIsClosed(status)" in runtime
    assert "function executionWaveWorkstreamCompletion(workstreams, options = {})" in runtime
    assert "function executionWaveWorkstreamProgress(workstreams, options = {})" in runtime
    assert "function executionWaveWaveCompletion(wave, options = {})" in runtime
    assert "function executionWaveWaveProgress(wave, options = {})" in runtime
    assert "function executionWaveProgramCompletion(program, options = {})" in runtime
    assert "function executionWaveProgramProgress(program, options = {})" in runtime
    assert "function executionWaveSummaryLine(program, options = {})" in runtime
    assert "function renderExecutionWaveProgram(program, selectedWorkstreamId, context, options = {})" in runtime
    assert "function renderExecutionWaveSection(sectionModel, options = {})" in runtime
    assert "const currentWave = program.current_wave" in runtime
    assert "const currentWaveId = program.current_wave" in runtime
    assert "const showProgramFocusTitle = options.hideProgramFocusTitle !== true;" in runtime
    assert 'const boardWrapperClass = String(options.boardWrapperClass || "").trim();' in runtime
    assert 'return status === "finished" || status === "complete" || status === "parked" || status === "superseded";' in runtime
    assert 'if (executionWaveStatusIsClosed(status)) {' in runtime
    assert 'const resolveWorkstreamStatus = typeof options.resolveWorkstreamStatus === "function"' in runtime
    assert 'const resolveWorkstreamProgress = typeof options.resolveWorkstreamProgress === "function"' in runtime
    assert "const programCompletion = executionWaveProgramCompletion(program, options);" in runtime
    assert "execution-wave-card-stat-rail" in runtime
    assert "wave-current-chip" in runtime
    assert 'Current: ${currentWave}' in runtime
    assert 'Closed gate workstreams: ${programCompletion.completeCount}/${programCompletion.totalCount}' in runtime
    assert "execution-wave-body-grid-members" in runtime
    assert "const waveProgress = executionWaveWaveProgress(wave, options);" in runtime
    assert 'const progressChip = waveProgress.percent ? `${waveProgress.percent} progress` : "";' in runtime
    assert '${progressChip ? `<span class="label execution-wave-label wave-progress-chip">${escapeHtml(progressChip)}</span>` : ""}' in runtime
    assert '${showProgramFocusTitle ? `<div class="execution-wave-focus-title">${escapeHtml(programLabel)}</div>` : ""}' in runtime
    assert '{ label: "Depends On", contentHtml: dependsOnHtml }' in runtime
    assert '? `<div class="execution-wave-body-grid execution-wave-body-grid-top">${supportPanelHtml}</div>` : ""' in runtime
    assert '? `<div class="${escapeHtml(boardWrapperClass)}">${boardHtml}</div>`' in runtime
    assert 'String(options.selectedNoteText || "").trim()' in runtime
    assert "execution-wave-highlight-label\">Selected scope" in runtime
    assert "Selected workstream participates here." not in runtime

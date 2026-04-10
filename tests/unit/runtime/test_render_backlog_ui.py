from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import render_backlog_ui


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_rewrite_section_text_normalizes_removed_plain_paths() -> None:
    text = "See odylith/casebook/SPEC.md and scripts/compass_dashboard_runtime.py."
    rewritten = render_backlog_ui._rewrite_section_text(repo_root=REPO_ROOT, text=text)

    assert "odylith/casebook/SPEC.md" not in rewritten
    assert "scripts/compass_dashboard_runtime.py" not in rewritten
    assert "odylith/registry/source/components/casebook/CURRENT_SPEC.md" in rewritten
    assert "odylith/registry/source/components/compass/CURRENT_SPEC.md" in rewritten


def test_rewrite_section_text_rewrites_removed_pytest_commands() -> None:
    text = "Run `pytest -q tests/scripts/test_sync_workstream_artifacts.py`."
    rewritten = render_backlog_ui._rewrite_section_text(repo_root=REPO_ROOT, text=text)

    assert "tests/scripts/test_sync_workstream_artifacts.py" not in rewritten
    assert "`odylith sync --repo-root . --check-only --runtime-mode standalone`" in rewritten


def test_rewrite_section_text_rewrites_removed_snapshot_command() -> None:
    text = "Point maintainers to python -m scripts.run_clean_snapshot_strict_sync --repo-root . when needed."
    rewritten = render_backlog_ui._rewrite_section_text(repo_root=REPO_ROOT, text=text)

    assert "python -m scripts.run_clean_snapshot_strict_sync" not in rewritten
    assert "odylith sync --check-only --check-clean --runtime-mode standalone --repo-root ." in rewritten


def test_render_plan_html_normalizes_legacy_meta_row_paths(tmp_path: Path) -> None:
    repo_root = tmp_path
    plan_path = repo_root / "odylith" / "technical-plans" / "in-progress" / "2026-03-26-test-plan.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(
        "\n".join(
            (
                "# Test Plan",
                "",
                "Status: In progress",
                "Created: 2026-03-26",
                "Updated: 2026-03-26",
                "Goal: Break `scripts/render_compass_dashboard.py` into focused modules.",
                "Assumptions: `odylith/surfaces/DASHBOARD_SPEC.md` is stale and must not survive.",
                "Boundary Conditions: `python -m scripts.run_clean_snapshot_strict_sync --repo-root .` is retired.",
                "",
                "## Validation",
                "- Run `pytest -q tests/scripts/test_sync_workstream_artifacts.py`.",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    html = render_backlog_ui._render_plan_html(
        repo_root=repo_root,
        index_output_path=repo_root / "odylith" / "radar" / "radar.html",
        entry={
            "idea_id": "B-999",
            "title": "Renderer Cutover",
            "promoted_to_plan_file": "odylith/technical-plans/in-progress/2026-03-26-test-plan.md",
        },
    )

    assert "scripts/render_compass_dashboard.py" not in html
    assert "odylith/surfaces/DASHBOARD_SPEC.md" not in html
    assert "python -m scripts.run_clean_snapshot_strict_sync" not in html
    assert "tests/scripts/test_sync_workstream_artifacts.py" not in html
    assert "odylith/registry/source/components/compass/CURRENT_SPEC.md" in html
    assert "odylith/registry/source/components/dashboard/CURRENT_SPEC.md" in html
    assert "odylith sync --check-only --check-clean --runtime-mode standalone --repo-root ." in html
    assert "odylith sync --repo-root . --check-only --runtime-mode standalone" in html
    assert "<code>odylith/registry/source/components/compass/CURRENT_SPEC.md</code>" in html
    assert "<code>odylith/registry/source/components/dashboard/CURRENT_SPEC.md</code>" in html
    assert "<code>odylith sync --check-only --check-clean --runtime-mode standalone --repo-root .</code>" in html


def test_render_idea_spec_html_uses_rich_text_for_decision_basis_and_implemented_summary(tmp_path: Path) -> None:
    repo_root = tmp_path
    idea_path = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-08-example.md"
    idea_path.parent.mkdir(parents=True)
    idea_path.write_text(
        "\n".join(
            (
                "---",
                "status: implementation",
                "idea_id: B-999",
                "title: Example",
                "date: 2026-04-08",
                "priority: P1",
                "commercial_value: 3",
                "product_impact: 3",
                "market_value: 3",
                "sizing: M",
                "complexity: Medium",
                "ordering_score: 42",
                "confidence: high",
                "founder_override: no",
                "---",
                "",
                "## Problem",
                "Example problem.",
                "",
                "## Customer",
                "- Primary: operators.",
                "",
                "## Opportunity",
                "Example opportunity.",
                "",
                "## Product View",
                "Example view.",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    html = render_backlog_ui._render_idea_spec_html(
        repo_root=repo_root,
        index_output_path=repo_root / "odylith" / "radar" / "radar.html",
        entry={
            "idea_id": "B-999",
            "title": "Example",
            "priority": "P1",
            "status": "implementation",
            "ordering_score": 42,
            "idea_file": "odylith/radar/source/ideas/2026-04/2026-04-08-example.md",
            "rationale_bullets": ["Run `pytest -q tests/scripts/test_sync_workstream_artifacts.py`."],
            "implemented_summary": "Point maintainers to `python -m scripts.run_clean_snapshot_strict_sync --repo-root .` when needed.",
        },
    )

    assert "tests/scripts/test_sync_workstream_artifacts.py" not in html
    assert "python -m scripts.run_clean_snapshot_strict_sync" not in html
    assert "<code>odylith sync --repo-root . --check-only --runtime-mode standalone</code>" in html
    assert "<code>odylith sync --check-only --check-clean --runtime-mode standalone --repo-root .</code>" in html


def test_render_idea_spec_html_places_product_view_below_problem(tmp_path: Path) -> None:
    repo_root = tmp_path
    idea_path = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-08-order-example.md"
    idea_path.parent.mkdir(parents=True)
    idea_path.write_text(
        "\n".join(
            (
                "---",
                "status: implementation",
                "idea_id: B-998",
                "title: Example",
                "date: 2026-04-08",
                "priority: P1",
                "commercial_value: 3",
                "product_impact: 3",
                "market_value: 3",
                "sizing: M",
                "complexity: Medium",
                "ordering_score: 42",
                "confidence: high",
                "founder_override: no",
                "---",
                "",
                "## Problem",
                "Example problem.",
                "",
                "## Customer",
                "Example customer.",
                "",
                "## Product View",
                "Example view.",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    html = render_backlog_ui._render_idea_spec_html(
        repo_root=repo_root,
        index_output_path=repo_root / "odylith" / "radar" / "radar.html",
        entry={
            "idea_id": "B-998",
            "title": "Example",
            "priority": "P1",
            "status": "implementation",
            "ordering_score": 42,
            "idea_file": "odylith/radar/source/ideas/2026-04/2026-04-08-order-example.md",
            "rationale_bullets": ["why now: Example rationale."],
        },
    )

    problem_idx = html.index("<h2>Problem</h2>")
    product_idx = html.index("<h2>Product View</h2>")
    decision_idx = html.index("<h2>Decision Basis</h2>")
    customer_idx = html.index("<h2>Customer</h2>")

    assert problem_idx < product_idx < customer_idx
    assert problem_idx < decision_idx < customer_idx


def test_render_section_body_splits_dense_single_paragraph_prose() -> None:
    html = render_backlog_ui._render_section_body(
        repo_root=REPO_ROOT,
        lines=[
            "`v0.1.9` reached GA on 2026-04-07, but the release lane still carried several truths that should not become permanent operating posture.",
            "Fresh downstream sync feedback on 2026-04-07 added another trust slice: operator-facing sync behavior is stronger than its public surface suggests, but it still hides supported controls and can rewrite unchanged generated JSON artifacts in ways that make file mtimes disagree with embedded `generated_utc`.",
            "Another downstream packet the same day exposed a Compass refresh trust gap: bounded refresh behaved as designed, but Compass still advertised an older deeper rerender path that shared the same hard dashboard timeout.",
            "Release prep on 2026-04-08 exposed one more maintainer truth: PR `pytest` and `candidate-proof` still carried unit tests that silently depended on a live Codex host runtime or a local `codex` binary.",
        ],
    )

    assert html.count("<p>") == 4
    assert "<code>generated_utc</code>" in html
    assert "bounded refresh" in html
    assert "<code>pytest</code>" in html


def test_render_section_body_keeps_wrapped_bullets_in_single_list_item() -> None:
    html = render_backlog_ui._render_section_body(
        repo_root=REPO_ROOT,
        lines=[
            "- Primary: operators relying on `doctor --repair` or",
            "  `reinstall --latest` to recover the repo in place.",
            "- Secondary: maintainers proving the release path.",
        ],
    )

    assert "<ul>" in html
    assert "<li>Primary: operators relying on <code>doctor --repair</code> or <code>reinstall --latest</code> to recover the repo in place.</li>" in html
    assert "<li>Secondary: maintainers proving the release path.</li>" in html


def test_render_section_body_keeps_command_only_checklist_items_inline_and_wrapped() -> None:
    html = render_backlog_ui._render_section_body(
        repo_root=REPO_ROOT,
        lines=[
            "- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py`",
        ],
    )

    assert '<div class="check-text"><code>PYTHONPATH=src python -m pytest -q' in html
    assert "PYTHONPATH=src python -m pytest -q" in html
    assert '<pre class="code"><code>' not in html


def test_render_backlog_ui_uses_diagram_owner_aware_atlas_links() -> None:
    html = render_backlog_ui._render_html(
        payload={
            "entries": [],
            "detail_manifest": [],
            "tooltip_lookup": {
                "diagram_related_workstreams": {
                    "D-001": ["B-001"],
                }
            },
        }
    )

    assert "const diagramWorkstreamLookup = sanitizeLookupListObject(rawTooltipLookup.diagram_related_workstreams);" in html
    assert "function atlasDiagramHref(diagramId, selectedIdeaId)" in html
    assert 'return `../../odylith/index.html?tab=atlas&diagram=${encodeURIComponent(token)}`;' in html
    assert 'owners.includes(workstreamId)' in html


def test_render_backlog_ui_uses_meaningful_hero_kicker() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "Priority Queue and Workstream Status" in html
    assert "See what is queued, active, parked, and finished, backed by repo workstream specs and delivery evidence." in html
    assert "Governed Workstream Queue" not in html
    assert "Local Generated View" not in html


def test_render_backlog_ui_curates_warning_cards_from_shared_traceability_policy() -> None:
    html = render_backlog_ui._render_html(
        payload={
            "entries": [],
            "warning_items": [
                {
                    "idea_id": "B-022",
                    "severity": "info",
                    "audience": "maintainer",
                    "surface_visibility": "diagnostics",
                    "category": "topology_conflict",
                    "message": "B-022: autofix skipped `workstream_split_into` due to metadata conflict",
                }
            ],
        }
    )

    assert "function isDefaultSurfaceWarning(entry)" in html
    assert 'surface_visibility: String(entry.surface_visibility || "").trim()' in html
    assert '&& isDefaultSurfaceWarning(entry)' in html


def test_render_backlog_ui_normalizes_compact_workstream_search_queries() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert 'const WORKSTREAM_ID_COMPACT_RE = /^B?-?(\\d{1,})$/i;' in html
    assert "function normalizeSearchToken(value)" in html
    assert "function canonicalizeIdeaId(value)" in html
    assert 'const normalized = `B-${compact[1].padStart(3, "0")}`;' in html
    assert "return Boolean(canonicalizeIdeaId(query));" in html
    assert "const canonicalIdeaQuery = exactIdeaQuery ? canonicalizeIdeaId(query) : \"\";" in html
    assert "return normalizeSearchToken(textParts.join(\" \")).includes(normalizedQuery);" in html
    assert "const token = canonicalizeIdeaId(ideaId);" in html


def test_render_backlog_ui_omits_empty_placeholder_copy() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "Select a workstream from the ranked list." not in html
    assert "No workstreams match current filters." not in html
    assert "Loading workstream detail…" not in html
    assert "No finished execution data yet." not in html
    assert "No completed execution samples in this window." not in html
    assert "Open analytics to load trend data." not in html


def test_render_backlog_ui_promotes_workstream_id_into_detail_kpi_grid() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert 'data-kpi="workstream-id"' in html
    assert 'data-kpi="workstream-placement"' in html
    assert "Workstream ID" in html
    assert "Placement" in html
    assert "function sectionBadgeInfo(row)" in html
    assert '<header class="detail-header">\n          <h2 class="detail-title">${escapeHtml(selected.title)}</h2>' in html
    assert '<header class="detail-header">\n          <span class="rank-chip' not in html
    assert '<div class="kpi" data-kpi="workstream-id"><div class="k">Workstream ID</div><div class="v">${escapeHtml(selected.idea_id)}</div></div>' in html
    assert '<div class="kpi kpi-section ${escapeHtml(sectionBadge.kpiClassName)}" data-kpi="workstream-placement"><div class="k">Placement</div><div class="v">${escapeHtml(sectionBadge.label)}</div></div>' in html
    assert '.kpi.kpi-section .k,\n    .kpi.kpi-section .v {\n      color: inherit;\n    }' in html
    assert ".kpi.kpi-section.kpi-section-execution {" in html
    assert ".kpi.kpi-section.kpi-section-active {" in html
    assert ".kpi.kpi-section.kpi-section-finished {" in html
    assert ".kpi.kpi-section.kpi-section-parked {" in html
    assert 'class="detail-id"' not in html
    assert html.index('data-kpi="workstream-id"') < html.index('<div class="chips">')
    assert html.index('data-kpi="workstream-placement"') < html.index("Ordering Score")


def test_render_backlog_ui_orders_traceability_links_with_spec_first() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    spec_idx = html.index(">Workstream Spec</a>")
    plan_idx = html.index(">Technical Implementation Plan</a>")
    compass_idx = html.index(">Compass Scope</a>")
    registry_idx = html.index(">Registry</a>")

    assert spec_idx < plan_idx < compass_idx < registry_idx


def test_render_backlog_ui_places_product_view_below_problem() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    problem_idx = html.index("<h3>Problem</h3>")
    product_idx = html.index("<h3>Product View</h3>")
    decision_idx = html.index("<h3>Decision Basis</h3>")
    customer_idx = html.index("<h3>Customer</h3>")

    assert problem_idx < product_idx < customer_idx
    assert problem_idx < decision_idx < customer_idx


def test_render_backlog_ui_includes_release_filters_summary_cards_and_release_chips() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert '<select id="type">' in html
    assert '<option value="umbrella">Umbrella</option>' in html
    assert '<option value="child">Child</option>' in html
    assert 'type: "all",' in html
    assert 'type: document.getElementById("type"),' in html
    assert 'if (state.type !== "all" && workstreamTypeInfo(row).type !== state.type) return false;' in html
    assert 'if (state.type !== "all" && workstreamTypeInfo(row).type !== state.type) {' in html
    assert 'el.type.value = state.type;' in html
    assert 'bind(el.type, "type");' in html
    assert "grid-template-columns: minmax(220px, 1.8fr) repeat(7, minmax(0, 1fr));" in html
    assert ".controls input,\n    .controls select {\n      min-width: 0;\n    }" in html
    assert 'if (state.release !== "all" && workstreamActiveReleaseId(row) !== state.release) return false;' in html
    assert "seedSelect(\n      el.release," in html
    assert "Active target release for this workstream." in html
    assert 'const nameLabel = String(release.effective_name || release.name || "").trim();' in html
    assert 'const versionLabel = String(release.version || release.display_label || "").trim();' in html
    assert 'escapeHtml(workstreamActiveReleaseLabel(row))' in html
    assert "Release ${workstreamActiveReleaseLabel(row)}" not in html
    assert "function releaseCardLabel(row)" in html
    assert 'statRows.push(statBlock("Current Release", releaseCardLabel(currentRelease), { releaseOnly: true }));' in html
    assert 'statRows.push(statBlock("", releaseCardLabel(currentRelease), { releaseOnly: true }));' not in html
    assert 'statRows.push(statBlock("Wave Programs"' not in html
    assert 'statRows.push(statBlock("Active Waves", activeWaves));' in html
    assert html.index('statRows.push(statBlock("Active Waves", activeWaves));') < html.index('statRows.push(statBlock("Current Release", releaseCardLabel(currentRelease), { releaseOnly: true }));')
    assert 'statRows.push(statBlock("Next Release", releaseCardLabel(nextRelease)));' not in html
    assert "versionLabel.startsWith(\"v\") ? versionLabel : `v${versionLabel}`" not in html
    assert ".stat.stat-release-only {" not in html
    assert ".stat.stat-release-only .value {" not in html
    assert "Next Release" not in html
    assert "Release Target" in html


def test_render_backlog_ui_topology_focus_does_not_repeat_selected_label() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert '<span class="topology-focus-title">Selected</span>' not in html
    assert 'selector=".topology-focus-title, .topology-relations-panel > summary, .topology-rel-title"' not in html
    assert ".topology-focus-title {" not in html


def test_render_backlog_ui_matches_compass_shell_width_and_favors_detail_workspace() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})
    compass_css = (
        REPO_ROOT / "src" / "odylith" / "runtime" / "surfaces" / "templates" / "compass_dashboard" / "compass-style-base.v1.css"
    ).read_text(encoding="utf-8")

    assert ".shell {" in html
    assert "--surface-shell-max-width: 1320px;" in html
    assert "max-width: var(--surface-shell-max-width, 1320px);" in html
    assert "__ODYLITH_STANDARD_SURFACE_SHELL_MAX_WIDTH__" in compass_css
    assert ".workspace {" in html
    assert "grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);" in html


def test_render_backlog_ui_sorts_default_sections_by_scope_signal_rank() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "function scopeSignalRank(row)" in html
    assert "const rankDelta = scopeSignalRank(b) - scopeSignalRank(a);" in html
    assert "if (rankDelta !== 0) return rankDelta;" in html


def test_render_backlog_ui_uses_shared_workstream_button_contract_for_workstream_ids() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "class=\"chip chip-link entity-id-chip" in html
    assert ".chip-link:not(.entity-id-chip):not(.execution-wave-chip-link) {" in html
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING};"
    ) in html
    assert ".entity-id-chip {" in html
    assert (
        "padding: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING});"
    ) in html
    assert (
        "font-size: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE});"
    ) in html
    assert (
        "font-weight: "
        f"var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT});"
    ) in html


def test_render_backlog_ui_topology_board_does_not_render_selected_focus_strip() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert '<div class="topology-focus">' not in html
    assert ".topology-focus {" not in html
    assert ".topology-focus .chip-topology-source {" not in html
    assert ".topology-focus," not in html
    assert ".row-id {" in html
    assert "font-family: ui-monospace" in html


def test_render_backlog_ui_uses_full_width_copy_and_consistent_detail_spacing() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert ".detail {" in html
    assert "padding: 16px 18px 18px;" in html
    assert "display: grid;" in html
    assert ".block {" in html
    assert "margin-top: 0;" in html
    assert "padding: 14px 16px;" in html
    assert ".detail-copy > p {" in html
    assert "max-width: 100%;" in html


def test_render_backlog_ui_keeps_unknown_execution_wave_progress_unknown() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "const numericProgressOrNull = (value) => {" in html
    assert 'if (value === null || value === undefined || value === "") return null;' in html
    assert 'Object.prototype.hasOwnProperty.call(plan, "display_progress_ratio")' in html

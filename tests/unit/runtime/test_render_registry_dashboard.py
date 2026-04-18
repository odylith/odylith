from __future__ import annotations

import json
import re
from pathlib import Path
import subprocess
import time

from odylith.runtime.evaluation import odylith_ablation
from odylith.runtime.surfaces import dashboard_time
from odylith.runtime.surfaces import render_registry_dashboard as renderer


def _extract_generated_utc(payload_js: str) -> str:
    match = re.search(r'"generated_utc"\s*:\s*"([^"]+)"', payload_js)
    assert match is not None
    return match.group(1)


def _load_registry_payload(root: Path) -> dict[str, object]:
    payload_js = (root / "odylith" / "registry" / "registry-payload.v1.js").read_text(encoding="utf-8")
    return json.loads(payload_js.split(" = ", 1)[1].rsplit(";", 1)[0])


def _extract_window_merge_payload(path: Path) -> dict[str, object]:
    js_text = path.read_text(encoding="utf-8")
    match = re.search(
        r"Object\.assign\(window\[[^\]]+\] \|\| \{\}, (?P<payload>\{.*\})\);\s*$",
        js_text,
        flags=re.S,
    )
    assert match is not None
    return json.loads(match.group("payload"))


def _bundle_registry_text(root: Path) -> str:
    parts = [
        (root / "odylith" / "registry" / "registry.html").read_text(encoding="utf-8"),
        (root / "odylith" / "registry" / "registry-payload.v1.js").read_text(encoding="utf-8"),
        (root / "odylith" / "registry" / "registry-app.v1.js").read_text(encoding="utf-8"),
    ]
    for path in sorted((root / "odylith" / "registry").glob("registry-detail-shard-*.v1.js")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _seed_repo(tmp_path: Path) -> None:
    profile_path = tmp_path / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": tmp_path.name,
                "truth_roots": {
                    "casebook_bugs": "odylith/casebook/bugs",
                    "component_registry": "odylith/registry/source/component_registry.v1.json",
                    "component_specs": "odylith/registry/source/components",
                    "radar_source": "odylith/radar/source",
                    "runbooks": "consumer-runbooks",
                    "technical_plans": "odylith/technical-plans",
                },
                "surface_roots": {
                    "product_root": "odylith",
                    "runtime_root": ".odylith",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "radar" / "CURRENT_SPEC.md"
    odylith_spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "odylith" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    odylith_spec_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path = tmp_path / "odylith" / "radar" / "radar.html"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("<html><body>B-901</body></html>\n", encoding="utf-8")
    spec_path.write_text(
        (
            "# Radar Component Spec\n\n"
            "Last updated: 2026-03-04\n\n"
            "## Purpose\nRadar surface.\n\n"
            "## Skill Triggers\n"
            "### Baseline\n"
            "- `delivery-governance-surface-ops`\n"
            "  - Trigger phrases:\n"
            '    - "sync workstreams"\n'
            '    - "refresh backlog radar"\n'
            "### Deep\n"
            "- `odylith-grid`\n"
            "  - Trigger phrases:\n"
            '    - "enforce critical odylith policies"\n\n'
            "## Requirements Trace\n"
            "This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.\n\n"
            "<!-- registry-requirements:start -->\n"
            "- **2026-03-04 · Decision:** Tightened Radar rendering semantics.\n"
            "  - Scope: B-901\n"
            "  - Evidence: src/odylith/runtime/surfaces/render_backlog_ui.py\n"
            "<!-- registry-requirements:end -->\n\n"
            "## Feature History\n"
            "- 2026-03-04: Added fail-closed execution signal framing for planning vs implementation. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )
    odylith_spec_path.write_text(
        (
            "# Odylith Component Spec\n\n"
            "Last updated: 2026-03-22\n\n"
            "## Feature History\n"
            "- 2026-03-22: Added Odylith umbrella baseline. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )
    runbook_path = tmp_path / "consumer-runbooks" / "topology-auditor.md"
    runbook_path.parent.mkdir(parents=True, exist_ok=True)
    runbook_path.write_text("# Topology Auditor\n\nRunbook body.\n", encoding="utf-8")
    dev_doc_path = tmp_path / "docs" / "platform-maintainer-guide.md"
    dev_doc_path.parent.mkdir(parents=True, exist_ok=True)
    dev_doc_path.write_text("# Platform Maintainer Guide\n\nDeveloper doc body.\n", encoding="utf-8")

    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "components": [
                    {
                        "component_id": "radar",
                        "name": "Radar",
                        "kind": "composite",
                        "category": "governance_surface",
                        "qualification": "curated",
                        "aliases": ["backlog-radar"],
                        "path_prefixes": ["src/odylith/runtime/surfaces/render_backlog_ui.py"],
                        "workstreams": ["B-901"],
                        "diagrams": ["D-100"],
                        "owner": "platform",
                        "status": "active",
                        "what_it_is": "Backlog radar surface.",
                        "why_tracked": "Primary planning governance view.",
                        "spec_ref": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
                        "product_layer": "evidence_surface",
                    },
                    {
                        "component_id": "odylith",
                        "name": "Odylith",
                        "kind": "platform",
                        "category": "governance_engine",
                        "qualification": "curated",
                        "aliases": ["odylith-platform"],
                        "path_prefixes": ["odylith/registry/source/component_registry.v1.json"],
                        "workstreams": ["B-901"],
                        "diagrams": ["D-100"],
                        "owner": "platform",
                        "status": "active",
                        "what_it_is": "Installable platform umbrella.",
                        "why_tracked": "Tracks the composed Odylith product boundary.",
                        "spec_ref": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
                        "subcomponents": ["radar"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "diagrams": [
                    {
                        "diagram_id": "D-100",
                        "title": "Example",
                        "components": [{"name": "Radar", "description": "Dashboard"}],
                        "related_workstreams": ["B-901"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "2026-03-04-example.md").write_text(
        (
            "status: planning\n\n"
            "idea_id: B-901\n\n"
            "title: Example\n\n"
            "date: 2026-03-04\n\n"
            "priority: P0\n\n"
            "commercial_value: 5\n\n"
            "product_impact: 5\n\n"
            "market_value: 5\n\n"
            "impacted_parts: x\n\n"
            "sizing: L\n\n"
            "complexity: VeryHigh\n\n"
            "ordering_score: 100\n\n"
            "ordering_rationale: x\n\n"
            "confidence: high\n\n"
            "founder_override: no\n\n"
            "promoted_to_plan: odylith/technical-plans/in-progress/2026-03-04-example.md\n\n"
            "workstream_type: standalone\n\n"
            "workstream_parent:\n\n"
            "workstream_children:\n\n"
            "workstream_depends_on:\n\n"
            "workstream_blocks:\n\n"
            "related_diagram_ids: D-100\n\n"
            "workstream_reopens:\n\n"
            "workstream_reopened_by:\n\n"
            "workstream_split_from:\n\n"
            "workstream_split_into:\n\n"
            "workstream_merged_into:\n\n"
            "workstream_merged_from:\n\n"
            "supersedes:\n\n"
            "superseded_by:\n\n"
            "## Problem\nRegistry render fixtures need meaningful Radar detail.\n\n"
            "## Customer\nMaintainers validating Registry dashboard fixture rendering.\n\n"
            "## Opportunity\nMeaningful fixture prose keeps Registry rendering aligned with validation.\n\n"
            "## Proposed Solution\nBody\n\n"
            "## Scope\nBody\n\n"
            "## Non-Goals\nBody\n\n"
            "## Risks\nBody\n\n"
            "## Dependencies\nBody\n\n"
            "## Success Metrics\n- Registry fixture records validate cleanly.\n- Dashboard rendering remains deterministic.\n\n"
            "## Validation\nBody\n\n"
            "## Rollout\nBody\n\n"
            "## Why Now\nBody\n\n"
            "## Product View\nRegistry should reject weak ideas without breaking valid render fixtures.\n\n"
            "## Impacted Components\n`Radar`\n\n"
            "## Interface Changes\nBody\n\n"
            "## Migration/Compatibility\nBody\n\n"
            "## Test Strategy\nBody\n\n"
            "## Open Questions\nBody\n"
        ),
        encoding="utf-8",
    )
    traceability_graph_path = tmp_path / "odylith" / "radar" / "traceability-graph.v1.json"
    traceability_graph_path.parent.mkdir(parents=True, exist_ok=True)
    traceability_graph_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-05T00:00:00Z",
                "workstreams": [
                    {
                        "idea_id": "B-901",
                        "plan_traceability": {
                            "runbooks": ["consumer-runbooks/topology-auditor.md"],
                            "developer_docs": ["docs/platform-maintainer-guide.md"],
                            "code_references": ["src/odylith/runtime/surfaces/render_backlog_ui.py"],
                        },
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "kind": "implementation",
                "summary": "Updated radar rendering behavior.",
                "workstreams": ["B-901"],
                "artifacts": ["src/odylith/runtime/surfaces/render_backlog_ui.py"],
                "components": ["radar"],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _init_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Codex"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "codex@example.com"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)


def test_render_registry_dashboard_happy_path(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    html = _bundle_registry_text(tmp_path)
    payload = _load_registry_payload(tmp_path)
    assert payload["data_source"]["available_backends"] == ["runtime", "staticSnapshot"]
    assert payload["runtime_contract"]["surface"] == "registry"
    assert payload["runtime_contract"]["cache_hit"] is False
    assert payload["runtime_contract"]["built_from"] == "surface_render"
    assert "odylith_runtime" in payload
    assert "advisory_depth" in payload["odylith_runtime"]
    assert "evaluation_benchmark_satisfaction_rate" in payload["odylith_runtime"]
    assert "advisory_freshness_bucket" in payload["odylith_runtime"]
    assert "advisory_evidence_strength_level" in payload["odylith_runtime"]
    assert "packet_alignment_rate" in payload["odylith_runtime"]
    assert "packet_alignment_state" in payload["odylith_runtime"]
    assert "high_yield_rate" in payload["odylith_runtime"]
    assert "yield_state" in payload["odylith_runtime"]
    summary_row = next(row for row in payload["components"] if row["component_id"] == "radar")
    assert "spec_markdown" not in summary_row
    assert "timeline" not in summary_row
    assert summary_row["product_layer"] == "evidence_surface"
    assert payload["detail_manifest"]["radar"].startswith("registry-detail-shard-")
    detail_row = _extract_window_merge_payload(
        tmp_path / "odylith" / "registry" / payload["detail_manifest"]["radar"]
    )["radar"]
    assert detail_row["diagram_details"] == [{"diagram_id": "D-100", "title": "Example"}]
    assert "Radar Component Spec" in detail_row["spec_markdown"]
    assert detail_row["product_layer"] == "evidence_surface"
    odylith_detail = _extract_window_merge_payload(
        tmp_path / "odylith" / "registry" / payload["detail_manifest"]["odylith"]
    )["odylith"]
    assert odylith_detail["subcomponents"] == ["radar"]
    assert odylith_detail["subcomponent_details"] == [{"component_id": "radar", "name": "Radar"}]
    assert "function createRegistryDataSource()" in html
    assert 'return "component forensics";' in html
    assert "const REGISTRY_LIST_WINDOW_THRESHOLD = 160;" in html
    assert 'href="../surfaces/brand/manifest.json"' in html
    assert 'href="../surfaces/brand/favicon/favicon.svg"' in html
    assert "Product Layer" in html
    assert "Subcomponents" in html
    retired_surface_label = "Sen" "tinel"
    assert retired_surface_label not in html
    assert "Advisory Evidence" not in html
    assert "Packet Alignment" not in html
    assert "Evidence Yield" not in html
    assert "Context Density" not in html
    assert "Runtime Backed" not in html
    assert "Benchmark Satisfaction" not in html
    assert "function resolveRegistryListWindow(items)" in html
    assert "function elementFullyVisibleWithinContainer(container, element)" in html
    assert "if (!options.fromScroll && !options.preserveListScroll) {" in html
    assert "ensureRegistrySelectionVisible(renderItems, selectedId);" in html
    assert "const preserveListScroll = elementFullyVisibleWithinContainer(listEl, node);" in html
    assert "applyState(id, { push: true, preserveListScroll });" in html
    assert "function normalizeSearchToken(value)" in html
    assert "function componentExactMatch(row, needle)" in html
    assert "const compactNeedle = normalizeSearchToken(normalizedNeedle);" in html
    assert "const exactTokens = [componentId, name, ...aliases.map((alias) => String(alias || \"\").trim().toLowerCase())]" in html
    assert "return exactTokens.includes(compactNeedle);" in html
    assert 'const normalizedNeedle = normalizeSearchToken(needle);' in html
    assert 'const exactIdMatches = scoped.filter((row) => componentExactMatch(row, needle) && String(row.component_id || "").trim().toLowerCase() === needle);' in html
    assert "if (exactIdMatches.length) return exactIdMatches;" in html
    assert 'const exactNameMatches = scoped.filter((row) => componentExactMatch(row, needle) && String(row.name || "").trim().toLowerCase() === needle);' in html
    assert "if (exactNameMatches.length) return exactNameMatches;" in html
    assert "const exactAliasMatches = scoped.filter((row) => {" in html
    assert "if (exactAliasMatches.length) return exactAliasMatches;" in html
    assert "const normalizedExactMatches = normalizedNeedle" in html
    assert "if (normalizedExactMatches.length) return normalizedExactMatches;" in html
    assert "const searchText = componentSearchText(row);" in html
    assert "return normalizeSearchToken(searchText).includes(normalizedNeedle);" in html
    assert ".list-spacer" in html
    assert 'function enforceShellOwnedSurfaceAccess() {' in html
    assert 'const expectedFrameId = "frame-registry";' in html
    assert 'nextParams.set("tab", "registry");' in html
    assert '"target":"component","sources":["component"]' in html
    assert "Component Registry" in html
    assert "Search component, alias, owner" in html
    assert 'id="resetFilters"' in html
    assert "Qualification" in html
    assert "Category" in html
    assert '"diagram_details": [{"diagram_id": "D-100", "title": "Example"}]' in html
    assert 'tooltip: `${diagramTitle}. Open Atlas context.`' in html
    assert "Diagram D-100. Open Atlas context." not in html
    assert 'id="qualificationFilter"' in html
    assert 'id="categoryFilter"' in html
    assert "context-section" in html
    assert "context-toggle-label" in html
    assert re.search(r'class="[^"]*context-toggle(?:\s|")', html) is None
    assert "Surface Links" not in html
    assert "Navigation shortcuts into Radar, Atlas, Compass, and Odylith." not in html
    assert "component-list" in html
    assert "registry-hero" in html
    assert "registry-filters-shell" in html
    assert "Component Ownership and Evidence Map" in html
    assert "See what exists, who owns it, and which specs, workstreams, and diagrams back it." in html
    assert "No components match current search or filters." not in html
    assert "No component selected." not in html
    assert "Loading component detail…" not in html
    assert "Loading component timeline…" not in html
    assert "No change events mapped to this component yet." not in html
    assert "Governed Component Inventory" not in html
    assert "Local Generated View" not in html
    assert "hero-controls" not in html
    assert re.search(r"\.registry-filters-shell\s*\{[^}]*position:\s*sticky;[^}]*top:\s*10px;", html, flags=re.S)
    assert re.search(r"\.registry-controls\s*\{[^}]*position:\s*static;[^}]*top:\s*auto;", html, flags=re.S)
    assert re.search(r"\.registry-title\s*\{[^}]*font-size:\s*31px;", html, flags=re.S)
    assert re.search(r"\.component-name\s*\{[^}]*font-size:\s*24px;[^}]*line-height:\s*1\.15;", html, flags=re.S)
    assert re.search(r"\.workspace\s*\{[^}]*grid-template-columns:\s*minmax\(330px,\s*420px\) minmax\(0,\s*1fr\);[^}]*gap:\s*12px;[^}]*align-items:\s*start;", html, flags=re.S)
    assert re.search(r"\.kpi-label\s*\{[^}]*font-size:\s*12px;[^}]*line-height:\s*1\.15;[^}]*letter-spacing:\s*0\.06em;", html, flags=re.S)
    assert re.search(r"\.kpi-value\s*\{[^}]*font-size:\s*23px;[^}]*line-height:\s*1;[^}]*letter-spacing:\s*-0\.01em;", html, flags=re.S)
    assert "Triggers:" in html
    assert "Trigger Tiers:" not in html
    assert "structured baseline/deep" not in html
    assert 'renderTriggerTier("Baseline", baselineTriggers)' not in html
    assert 'renderTriggerTier("Deep", deepTriggers)' not in html
    assert "sync workstreams" in html
    assert "refresh backlog radar" in html
    assert "enforce critical odylith policies" in html
    assert "trigger-expand" in html
    assert "trigger-summary-title" in html
    assert "trigger-title" not in html
    assert '${escapeHtml(String(triggerPhrases.length))} phrase${triggerPhrases.length === 1 ? "" : "s"}' in html
    assert re.search(r"\.trigger-expand\s*\{[^}]*border:\s*1px solid #d9e6fa;[^}]*border-radius:\s*8px;", html, flags=re.S)
    assert re.search(r"\.trigger-expand > summary\s*\{[^}]*display:\s*flex;[^}]*align-items:\s*center;", html, flags=re.S)
    assert re.search(r"\.trigger-summary-title::before\s*\{[^}]*content:\s*\"▸\";[^}]*font-size:\s*11px;", html, flags=re.S)
    assert re.search(r"\.trigger-expand\[open\]\s*\.trigger-summary-title::before\s*\{[^}]*transform:\s*rotate\(90deg\);", html, flags=re.S)
    assert re.search(r"\.trigger-list\s*\{[^}]*padding:\s*0 10px 10px 28px;[^}]*list-style:\s*square;", html, flags=re.S)
    assert "function extractTriggerPhrases(markdown, triggerTiers)" in html
    assert "function normalizeTriggerTierRows(value)" not in html
    assert "component-token" not in html
    assert re.search(r"\.trigger-list,\s*\.trigger-list li,\s*\.spec-doc p,\s*\.spec-doc ul,\s*\.spec-doc li\s*\{[^}]*font-size:\s*15px;[^}]*line-height:\s*1\.55;[^}]*color:\s*#27445e;", html, flags=re.S)
    assert re.search(r"\.summary-row\s*\{[^}]*font-size:\s*15px;[^}]*line-height:\s*1\.55;[^}]*color:\s*#27445e;[^}]*font-weight:\s*400;", html, flags=re.S)
    assert re.search(r"\.summary-row strong\s*\{[^}]*font-size:\s*inherit;[^}]*line-height:\s*inherit;[^}]*color:\s*#22496f;[^}]*font-weight:\s*700;", html, flags=re.S)
    assert ".detail-disclosure-title {" in html
    assert re.search(r"\.detail-disclosure-title\s*\{[^}]*color:\s*#22496f;[^}]*font-size:\s*15px;[^}]*line-height:\s*1\.55;[^}]*letter-spacing:\s*0em;[^}]*font-weight:\s*700;", html, flags=re.S)
    assert 'class="context-k context-toggle-label"' not in html
    assert '<div class="context-head">\n              <span class="detail-disclosure-title context-toggle-label">Topology</span>\n            </div>' in html
    assert 'class="detail-chip-label' not in html
    assert re.search(r"\.label\s*\{[^}]*border:\s*1px solid var\(--label-border\);[^}]*border-radius:\s*4px;[^}]*padding:\s*4px 10px;", html, flags=re.S)
    assert re.search(
        r"\.action-chip\s*\{[^}]*--chip-link-border:\s*var\(--action-border\);[^}]*--chip-link-bg:\s*var\(--action-bg\);[^}]*--chip-link-text:\s*var\(--action-text\);[^}]*min-height:\s*0px;[^}]*padding:\s*var\(--surface-deep-link-button-padding,\s*4px 12px\);[^}]*border-radius:\s*999px;[^}]*border:\s*1px solid var\(--chip-link-border\);[^}]*background:\s*var\(--chip-link-bg\);[^}]*color:\s*var\(--chip-link-text\);",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.action-chip\s*\{[^}]*font-size:\s*var\(--surface-deep-link-button-font-size,\s*11px\);[^}]*line-height:\s*1;[^}]*letter-spacing:\s*0\.01em;[^}]*font-weight:\s*var\(--surface-deep-link-button-font-weight,\s*700\);",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.detail-action-chip\s*\{[^}]*min-height:\s*0px;[^}]*padding:\s*var\(--surface-deep-link-button-padding,\s*4px 12px\);[^}]*border-radius:\s*999px;[^}]*border:\s*1px solid var\(--chip-link-border\);",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.detail-action-chip\s*\{[^}]*font-size:\s*var\(--surface-deep-link-button-font-size,\s*11px\);[^}]*line-height:\s*1;[^}]*letter-spacing:\s*0\.01em;[^}]*font-weight:\s*var\(--surface-deep-link-button-font-weight,\s*700\);",
        html,
        flags=re.S,
    )
    assert ".detail-chip-label {" not in html
    assert ".detail-chip-label.tone-gov {" not in html
    assert re.search(r"\.action-chip\.active\s*\{[^}]*border-color:\s*#1d4a8f;[^}]*background:\s*#deebff;[^}]*color:\s*#1d4ed8;", html, flags=re.S)
    assert not re.search(r"\.action-chip\.active\s*\{[^}]*box-shadow:", html, flags=re.S)
    assert re.search(r"\.component-btn\.active\s*\{[^}]*border-color:\s*var\(--line-strong\);[^}]*background:\s*#eaf3ff;", html, flags=re.S)
    assert not re.search(r"\.component-btn\.active\s*\{[^}]*box-shadow:", html, flags=re.S)
    assert re.search(r"html,\s*body\s*\{[^}]*min-height:\s*100%;", html, flags=re.S)
    assert not re.search(r"html,\s*body\s*\{[^}]*overflow:\s*hidden;", html, flags=re.S)
    assert re.search(r"\.list-panel\s*\{[^}]*max-height:\s*calc\(100vh\s*-\s*188px\);", html, flags=re.S)
    assert re.search(r"\.component-list\s*\{[^}]*max-height:\s*none;", html, flags=re.S)
    assert "list-panel" in html
    assert "detail-panel" in html
    assert not re.search(r"\.timeline\s*\{[^}]*overflow:\s*auto;", html, flags=re.S)
    component_button_html = re.findall(r'<button type="button" class="component-btn[^"]*"[^>]*>', html)
    assert component_button_html


def test_render_registry_dashboard_forensic_evidence_uses_digest_first_contract(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    stream_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "kind": "intervention_card",
                "summary": "Radar already has a governed slice for B-901.",
                "ts_iso": "2026-04-01T00:00:00Z",
                "workstreams": ["B-901", "B-902", "B-903", "B-904", "B-905", "B-906"],
                "artifacts": [
                    "src/odylith/runtime/surfaces/render_backlog_ui.py",
                    "odylith/registry/source/components/radar/CURRENT_SPEC.md",
                    "odylith/technical-plans/in-progress/2026-03-04-example.md",
                ],
                "components": ["radar"],
                "confidence": "high",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    payload = _load_registry_payload(tmp_path)
    detail_row = _extract_window_merge_payload(
        tmp_path / "odylith" / "registry" / payload["detail_manifest"]["radar"]
    )["radar"]
    raw_event = next(row for row in detail_row["timeline"] if row["kind"] == "intervention_card")
    assert len(raw_event["workstreams"]) == 6
    assert len(raw_event["artifacts"]) == 3

    html = _bundle_registry_text(tmp_path)
    assert '<section id="timeline" class="timeline" aria-live="polite"></section>' in html
    assert "const FORENSIC_DIGEST_WORKSTREAM_LIMIT = 4;" in html
    assert "const FORENSIC_DIGEST_ARTIFACT_LIMIT = 2;" in html
    assert "function forensicNewestEvent(events)" in html
    assert "const latestEvent = forensicNewestEvent(events);" in html
    assert "function forensicLimitedWorkstreams(workstreams, limit = FORENSIC_DIGEST_WORKSTREAM_LIMIT)" in html
    assert "function forensicLimitedArtifacts(artifacts, limit = FORENSIC_DIGEST_ARTIFACT_LIMIT)" in html
    assert 'forensicOverflowLabel(overflow, "workstream")' in html
    assert "function forensicArtifactOverflowDisclosure(items, overflow)" in html
    assert "forensicArtifactOverflowDisclosure(hidden, overflow)" in html
    assert "forensic-token-link" not in html
    assert "forensic-overflow" not in html
    assert '<a class="forensic-workstream-chip"' in html
    assert re.search(
        r"\.forensic-workstream-chip\s*\{[^}]*--chip-link-border:\s*#b9c7db;[^}]*--chip-link-bg:\s*#f3f6fb;[^}]*--chip-link-text:\s*#334155;",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-workstream-chip\s*\{[^}]*padding:\s*var\(--surface-workstream-button-padding,\s*1px 8px\);",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-workstream-chip\s*\{[^}]*font-size:\s*var\(--surface-workstream-button-font-size,\s*12px\);[^}]*font-weight:\s*var\(--surface-workstream-button-font-weight,\s*500\);",
        html,
        flags=re.S,
    )
    assert not re.search(r"\.forensic-workstream-chip\s*\{[^}]*#8cb8f4", html, flags=re.S)
    assert not re.search(r"\.forensic-workstream-chip\s*\{[^}]*#eaf3ff", html, flags=re.S)
    assert not re.search(r"\.forensic-workstream-chip\s*\{[^}]*#1f4795", html, flags=re.S)
    assert re.search(
        r"\.artifact\s*\{[^}]*--chip-link-border:\s*#cbd5e1;[^}]*--chip-link-bg:\s*#f8fafc;[^}]*--chip-link-text:\s*#334155;",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.artifact\s*\{[^}]*padding:\s*var\(--surface-deep-link-button-padding,\s*4px 12px\);",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.artifact\s*\{[^}]*font-size:\s*var\(--surface-deep-link-button-font-size,\s*11px\);[^}]*font-weight:\s*var\(--surface-deep-link-button-font-weight,\s*700\);",
        html,
        flags=re.S,
    )
    assert '<details class="forensic-artifact-disclosure">' in html
    assert '<summary class="forensic-artifact-overflow-summary"' in html
    assert '<div class="forensic-artifact-disclosure-panel artifact-list">' in html
    assert re.search(
        r"\.forensic-artifact-overflow-summary\s*\{[^}]*--chip-link-border:\s*#cbd5e1;[^}]*--chip-link-bg:\s*#f8fafc;[^}]*--chip-link-text:\s*#334155;",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-artifact-overflow-summary\s*\{[^}]*padding:\s*var\(--surface-deep-link-button-padding,\s*4px 12px\);",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-artifact-overflow-summary\s*\{[^}]*font-size:\s*var\(--surface-deep-link-button-font-size,\s*11px\);[^}]*font-weight:\s*var\(--surface-deep-link-button-font-weight,\s*700\);",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-artifact-disclosure:not\(\[open\]\)\s*\.forensic-artifact-disclosure-panel\s*\{[^}]*display:\s*none;",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-artifact-disclosure\[open\]\s*\.forensic-artifact-disclosure-panel\s*\{[^}]*display:\s*flex;",
        html,
        flags=re.S,
    )
    assert not re.search(r"\.artifact\s*\{[^}]*border:\s*1px solid #d4e2f7;", html, flags=re.S)
    assert re.search(
        r"\.forensic-coverage-strip\s*\{[^}]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(150px,\s*1fr\)\);",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-stat\s*\{[^}]*border:\s*1px solid #dbeafe;[^}]*border-radius:\s*12px;[^}]*background:\s*#ffffff;[^}]*grid-template-rows:\s*2\.35em auto;",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-stat-label\s*\{[^}]*font-size:\s*12px;[^}]*text-transform:\s*uppercase;",
        html,
        flags=re.S,
    )
    assert re.search(
        r"\.forensic-stat-value\s*\{[^}]*font-size:\s*23px;[^}]*font-weight:\s*700;",
        html,
        flags=re.S,
    )
    assert not re.search(r"\.forensic-stat\s*\{[^}]*border:\s*1px solid #d7e4f6;", html, flags=re.S)
    assert not re.search(r"\.forensic-stat\s*\{[^}]*background:\s*#f8fbff;", html, flags=re.S)
    assert not re.search(r"\.forensic-stat\s*\{[^}]*padding:\s*8px 9px;", html, flags=re.S)
    assert "renderForensicRawEvent" not in html
    assert "renderForensicRawLog" not in html
    assert "forensic-raw-log" not in html
    assert "forensic-raw-events" not in html
    assert "Raw event log" not in html
    assert "No scope" not in html
    assert "No artifacts" not in html
    assert "event-summary" not in html
    assert "event-top" not in html

    latest_match = re.search(
        r"function renderForensicLatestEvent\(event\)(?P<body>.*?)function renderForensicGroups",
        html,
        flags=re.S,
    )
    assert latest_match is not None
    latest_body = latest_match.group("body")
    assert "No scope" not in latest_body
    assert "No artifacts" not in latest_body

    groups_match = re.search(
        r"function renderForensicGroups\(events\)(?P<body>.*?)function renderTimeline",
        html,
        flags=re.S,
    )
    assert groups_match is not None
    groups_body = groups_match.group("body")
    assert "No scope" not in groups_body
    assert "No artifacts" not in groups_body

    assert re.search(
        r"\.forensic-latest,\s*\.forensic-group-row\s*\{[^}]*border-radius:\s*8px;",
        html,
        flags=re.S,
    )
    assert not re.search(
        r"\.forensic-(?:latest|group-row)[^{]*\{[^}]*border-radius:\s*(?:9|1[0-9]|[2-9][0-9])px",
        html,
    )


def test_render_registry_dashboard_uses_consumer_registry_truth_root_when_profile_overrides_manifest(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    consumer_spec_path = tmp_path / "consumer-registry" / "source" / "components" / "registry" / "CURRENT_SPEC.md"
    consumer_spec_path.parent.mkdir(parents=True, exist_ok=True)
    consumer_spec_path.write_text(
        (
            "# Consumer Registry Note\n\n"
            "Last updated: 2026-03-04\n\n"
            "## Feature History\n"
            "- 2026-03-04: Added consumer registry fixture. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )
    consumer_manifest = tmp_path / "consumer-registry" / "source" / "component_registry.v1.json"
    consumer_manifest.parent.mkdir(parents=True, exist_ok=True)
    consumer_manifest.write_text(
        json.dumps(
            {
                "version": "v1",
                "components": [
                    {
                        "component_id": "consumer-registry",
                        "name": "Consumer Registry",
                        "kind": "composite",
                        "category": "governance_surface",
                        "qualification": "curated",
                        "aliases": ["consumer-reg"],
                        "path_prefixes": ["consumer-registry/source/components/registry/CURRENT_SPEC.md"],
                        "workstreams": ["B-901"],
                        "diagrams": ["D-100"],
                        "owner": "consumer",
                        "status": "active",
                        "what_it_is": "Consumer-owned registry surface.",
                        "why_tracked": "Verifies consumer profile manifest selection.",
                        "spec_ref": "consumer-registry/source/components/registry/CURRENT_SPEC.md",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    profile_path = tmp_path / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": "consumer-repo",
                "truth_roots": {
                    "component_registry": "consumer-registry/source/component_registry.v1.json",
                    "component_specs": "consumer-registry/source/components",
                    "runbooks": "consumer-runbooks",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html", "--runtime-mode", "standalone"])
    assert rc == 0

    payload = _load_registry_payload(tmp_path)
    component_ids = [str(row["component_id"]) for row in payload["components"]]
    assert component_ids == ["consumer-registry"]
    assert payload["consumer_truth_roots"]["component_registry"] == "consumer-registry/source/component_registry.v1.json"


def test_render_registry_dashboard_hides_odylith_umbrella_when_disabled(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    odylith_ablation.write_odylith_switch(repo_root=tmp_path, enabled=False, note="ablation")

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    payload = _load_registry_payload(tmp_path)
    component_ids = [str(row["component_id"]) for row in payload["components"]]
    assert "odylith" not in component_ids
    radar_row = next(row for row in payload["components"] if row["component_id"] == "radar")
    assert radar_row["product_layer"] == ""
    detail_row = _extract_window_merge_payload(
        tmp_path / "odylith" / "registry" / payload["detail_manifest"]["radar"]
    )["radar"]
    assert detail_row["product_layer"] == ""
    assert detail_row["subcomponents"] == []


def test_render_registry_dashboard_compacts_delivery_intelligence_payload(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_repo(tmp_path)

    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **_kwargs: {
            "summary": {"headline": "unused"},
            "workstreams": {"B-901": {"unused": True}},
                "components": {
                    "radar": {
                        "confidence": "high",
                        "operator_readout": {"headline": "Radar is converging."},
                        "posture_mode": "converging",
                        "proof_state": {
                            "lane_id": "proof-state-control-plane",
                            "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                            "proof_status": "fixed_in_code",
                        },
                        "proof_state_resolution": {
                            "state": "resolved",
                            "lane_ids": ["proof-state-control-plane"],
                        },
                        "claim_guard": {
                            "highest_truthful_claim": "fixed in code",
                            "blocked_terms": ["fixed", "cleared", "resolved"],
                        },
                        "scope_signal": {
                            "rank": 4,
                            "rung": "R4",
                            "token": "actionable_priority",
                            "label": "Actionable priority",
                            "reasons": ["An open warning or operator recommendation is still unresolved."],
                            "caps": [],
                            "promoted_default": True,
                            "budget_class": "escalated_reasoning",
                        },
                        "trajectory": "steady",
                        "diagnostics": ["unused"],
                        "evidence_refs": [{"surface": "radar", "value": "B-901"}],
                    }
                },
        },
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])

    assert rc == 0
    payload = _load_registry_payload(tmp_path)
    assert payload["delivery_intelligence"] == {
        "components": {
            "radar": {
                "confidence": "high",
                "claim_guard": {
                    "blocked_terms": ["fixed", "cleared", "resolved"],
                    "highest_truthful_claim": "fixed in code",
                },
                "operator_readout": {"headline": "Radar is converging."},
                "posture_mode": "converging",
                "proof_state": {
                    "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                    "lane_id": "proof-state-control-plane",
                    "proof_status": "fixed_in_code",
                },
                "proof_state_resolution": {
                    "state": "resolved",
                    "lane_ids": ["proof-state-control-plane"],
                },
                "scope_signal": {
                    "rank": 4,
                    "rung": "R4",
                    "token": "actionable_priority",
                    "label": "Actionable priority",
                    "reasons": ["An open warning or operator recommendation is still unresolved."],
                    "caps": [],
                    "promoted_default": True,
                    "budget_class": "escalated_reasoning",
                },
                "trajectory": "steady",
            }
        }
    }
    html = _bundle_registry_text(tmp_path)
    assert "Live Status" not in html
    assert "Product Summary" not in html
    assert "Current live risk is still centered on " not in html
    assert "Safest current claim: " not in html
    assert "Proof Control" not in html
    assert "Live Blocker" not in html
    assert "Current blocker:" not in html
    assert "Fingerprint:" not in html
    assert "Frontier:" not in html
    assert "Evidence tier:" not in html
    assert "Truthful claim:" not in html
    assert "Deployment truth:" not in html


def test_render_registry_dashboard_surfaces_proof_resolution_when_no_dominant_lane(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)

    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **_kwargs: {
            "components": {
                "radar": {
                    "operator_readout": {"headline": "Radar needs a tighter blocker read."},
                    "proof_state": {},
                    "proof_state_resolution": {
                        "state": "ambiguous",
                        "lane_ids": ["lane-a", "lane-b"],
                    },
                    "claim_guard": {},
                }
            }
        },
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])

    assert rc == 0
    payload = _load_registry_payload(tmp_path)
    assert payload["delivery_intelligence"]["components"]["radar"]["proof_state_resolution"] == {
        "state": "ambiguous",
        "lane_ids": ["lane-a", "lane-b"],
    }
    html = _bundle_registry_text(tmp_path)
    assert "Current live risk is still split across more than one blocker path for this component." not in html
    assert "No dominant proof lane is resolved for this component." not in html


def test_render_registry_dashboard_surfaces_baseline_forensic_only_components(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    atlas_spec = tmp_path / "odylith" / "registry" / "source" / "components" / "atlas" / "CURRENT_SPEC.md"
    atlas_spec.parent.mkdir(parents=True, exist_ok=True)
    atlas_spec.write_text(
        (
            "# Atlas Component Spec\n\n"
            "Last updated: 2026-03-04\n\n"
            "## Feature History\n"
            "- 2026-03-04: Added Atlas baseline for empty forensic coverage tests. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["components"].append(
        {
            "component_id": "atlas",
            "name": "Atlas",
            "kind": "composite",
            "category": "governance_surface",
            "qualification": "curated",
            "aliases": ["mermaid-atlas"],
            "path_prefixes": ["src/odylith/runtime/surfaces/render_mermaid_catalog.py"],
            "workstreams": ["B-901"],
            "diagrams": ["D-100"],
            "owner": "platform",
            "status": "active",
            "what_it_is": "Atlas surface.",
            "why_tracked": "Architecture traceability surface.",
            "spec_ref": "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
        }
    )
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.write_text("", encoding="utf-8")

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    html = _bundle_registry_text(tmp_path)
    assert '"status": "baseline_forensic_only"' in html or '"status":"baseline_forensic_only"' in html
    assert '"spec_history_event_count": 1' in html or '"spec_history_event_count":1' in html
    assert (
        '"empty_reasons": ["no_explicit_event", "no_recent_path_match", "no_mapped_workstream_evidence"]' in html
        or '"empty_reasons":["no_explicit_event","no_recent_path_match","no_mapped_workstream_evidence"]' in html
    )
    assert "Baseline forensic only" in html
    assert "Feature history" in html
    assert "Added Atlas baseline for empty forensic coverage tests." in html
    assert "no explicit event" in html
    assert "no recent path match" in html
    assert "no mapped workstream evidence" in html


def test_render_registry_dashboard_supports_markdown_tables_in_specs(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "radar" / "CURRENT_SPEC.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8")
        + "\n## Capability Matrix\n\n"
        + "| Tier | Allowed envs |\n"
        + "| --- | --- |\n"
        + "| `free` | `test` |\n"
        + "| `team` | `test`, `staging` |\n",
        encoding="utf-8",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    html = _bundle_registry_text(tmp_path)
    assert ".spec-table-scroll" in html
    assert ".spec-table thead th" in html
    assert 'const parseMarkdownTableCells = (value) =>' in html
    assert 'const isMarkdownTableSeparator = (value) =>' in html
    assert '<div class="spec-table-scroll"><table class="spec-table"><thead><tr>' in html
    assert "| Tier | Allowed envs |" in html


def test_chunk_registry_items_scales_across_large_item_counts() -> None:
    for count in (1000, 5000, 10000):
        items = {
            f"component-{index:05d}": {"component_id": f"component-{index:05d}"}
            for index in range(count)
        }
        manifest, shards = renderer._chunk_registry_items(  # noqa: SLF001
            items=items,
            shard_size=32,
            file_stem_prefix="registry-detail-shard",
        )
        assert len(manifest) == count
        assert len(shards) == ((count + 31) // 32)
        assert sum(len(payload) for _filename, payload in shards) == count
        assert all(len(payload) <= 32 for _filename, payload in shards)


def test_render_registry_dashboard_generated_utc_stable_when_payload_unchanged(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0
    first_generated = _extract_generated_utc((tmp_path / "odylith" / "registry" / "registry-payload.v1.js").read_text(encoding="utf-8"))

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0
    second_generated = _extract_generated_utc((tmp_path / "odylith" / "registry" / "registry-payload.v1.js").read_text(encoding="utf-8"))

    assert first_generated == second_generated


def test_render_registry_dashboard_skips_noop_writes_when_bundle_is_unchanged(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    tracked_paths = [
        tmp_path / "odylith" / "registry" / "registry.html",
        tmp_path / "odylith" / "registry" / "registry-payload.v1.js",
        tmp_path / "odylith" / "registry" / "registry-app.v1.js",
        *sorted((tmp_path / "odylith" / "registry").glob("registry-detail-shard-*.v1.js")),
    ]
    first_mtimes = {path: path.stat().st_mtime_ns for path in tracked_paths}

    time.sleep(0.01)
    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    second_mtimes = {path: path.stat().st_mtime_ns for path in tracked_paths}
    assert second_mtimes == first_mtimes


def test_render_registry_dashboard_supports_odylith_chatter_component_contract(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    chatter_spec = tmp_path / "odylith" / "registry" / "source" / "components" / "odylith-chatter" / "CURRENT_SPEC.md"
    chatter_spec.parent.mkdir(parents=True, exist_ok=True)
    chatter_spec.write_text(
        (
            "# Odylith Chatter Component Spec\n\n"
            "Last updated: 2026-03-31\n\n"
            "## Ambient Signal Policy\n"
            "- Use explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels only when the point is strong enough to earn the interruption.\n\n"
            "## Closeout Policy\n"
            "- `Odylith Assist:` stays final-only.\n"
            "- Prefer `**Odylith Assist:**` when Markdown formatting is available.\n"
            "- Lead with the user win, not Odylith mechanics.\n"
            "- Link updated governance IDs inline only when they actually changed.\n"
            "- Name affected governance-contract IDs when no governed file moved.\n"
            "- Frame the edge against `odylith_off` or the broader unguided path when the evidence supports it.\n"
            "- Keep it crisp, authentic, clear, simple, insightful, soulful, friendly, free-flowing, human, and factual.\n"
            "- Use observed counts, measured deltas, or validation outcomes.\n\n"
            "## Feature History\n"
            "- 2026-03-31: Added the chatter contract component. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )

    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["components"].append(
        {
            "component_id": "odylith-chatter",
            "name": "Odylith Chatter",
            "kind": "runtime",
            "category": "governance_engine",
            "qualification": "curated",
            "aliases": ["commentary-contract"],
            "path_prefixes": ["AGENTS.md"],
            "workstreams": ["B-901"],
            "diagrams": [],
            "owner": "product",
            "status": "active",
            "what_it_is": "Narration policy.",
            "why_tracked": "Keeps Odylith by-name commentary governed.",
            "spec_ref": "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md",
            "product_layer": "agent_execution",
        }
    )
    for row in manifest_payload["components"]:
        if row["component_id"] == "odylith":
            row["subcomponents"] = ["radar", "odylith-chatter"]
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    payload = _load_registry_payload(tmp_path)
    chatter_summary = next(row for row in payload["components"] if row["component_id"] == "odylith-chatter")
    assert chatter_summary["product_layer"] == "agent_execution"

    chatter_detail = _extract_window_merge_payload(
        tmp_path / "odylith" / "registry" / payload["detail_manifest"]["odylith-chatter"]
    )["odylith-chatter"]
    assert "Odylith Assist:" in chatter_detail["spec_markdown"]
    assert "**Odylith Assist:**" in chatter_detail["spec_markdown"]
    assert "Odylith Insight:" in chatter_detail["spec_markdown"]
    assert "Lead with the user win" in chatter_detail["spec_markdown"]
    assert "Link updated governance IDs inline only when they actually changed." in chatter_detail["spec_markdown"]
    assert "Name affected governance-contract IDs when no governed file moved." in chatter_detail["spec_markdown"]
    assert "broader unguided path" in chatter_detail["spec_markdown"]
    assert "crisp, authentic, clear, simple, insightful" in chatter_detail["spec_markdown"]

    odylith_detail = _extract_window_merge_payload(
        tmp_path / "odylith" / "registry" / payload["detail_manifest"]["odylith"]
    )["odylith"]
    assert odylith_detail["subcomponents"] == ["radar", "odylith-chatter"]
    assert {"component_id": "odylith-chatter", "name": "Odylith Chatter"} in odylith_detail["subcomponent_details"]


def test_render_registry_dashboard_shows_workspace_activity_in_forensic_evidence(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    _init_git_repo(tmp_path)

    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "radar" / "CURRENT_SPEC.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8") + "\nRecent registry-style forensic test edit.\n",
        encoding="utf-8",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    html = _bundle_registry_text(tmp_path)
    assert "Recent workspace activity across tracked paths:" in html
    assert "workspace activity" in html.lower()


def test_render_registry_dashboard_maps_source_owned_bundle_mirror_activity_to_component_forensics(
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path)

    tribunal_spec = tmp_path / "odylith" / "registry" / "source" / "components" / "tribunal" / "CURRENT_SPEC.md"
    tribunal_spec.parent.mkdir(parents=True, exist_ok=True)
    tribunal_spec.write_text(
        (
            "# Tribunal Component Spec\n\n"
            "Last updated: 2026-03-29\n\n"
            "## Feature History\n"
            "- 2026-03-29: Added Tribunal forensic mirror fixture. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )
    canonical_doc = tmp_path / "odylith" / "runtime" / "odylith-tribunal-and-remediation-design.md"
    canonical_doc.parent.mkdir(parents=True, exist_ok=True)
    canonical_doc.write_text("# Tribunal Design\n\nCanonical source doc.\n", encoding="utf-8")
    mirror_doc = tmp_path / "src" / "odylith" / "bundle" / "assets" / "odylith" / "runtime" / "odylith-tribunal-and-remediation-design.md"
    mirror_doc.parent.mkdir(parents=True, exist_ok=True)
    mirror_doc.write_text("# Tribunal Design\n\nBundled source mirror.\n", encoding="utf-8")

    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["components"].append(
        {
            "component_id": "tribunal",
            "name": "Tribunal",
            "kind": "runtime",
            "category": "governance_engine",
            "qualification": "curated",
            "aliases": ["diagnosis-engine"],
            "path_prefixes": [
                "src/odylith/runtime/reasoning/tribunal_engine.py",
                "odylith/runtime/odylith-tribunal-and-remediation-design.md",
            ],
            "workstreams": ["B-901"],
            "diagrams": ["D-100"],
            "owner": "product",
            "status": "active",
            "what_it_is": "Diagnosis engine.",
            "why_tracked": "Fixture for source-mirror forensic coverage.",
            "spec_ref": "odylith/registry/source/components/tribunal/CURRENT_SPEC.md",
        }
    )
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
    (tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl").write_text("", encoding="utf-8")

    _init_git_repo(tmp_path)
    mirror_doc.write_text(
        mirror_doc.read_text(encoding="utf-8") + "\nMirror-only forensic activity.\n",
        encoding="utf-8",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    payload = _load_registry_payload(tmp_path)
    tribunal_detail = _extract_window_merge_payload(
        tmp_path / "odylith" / "registry" / payload["detail_manifest"]["tribunal"]
    )["tribunal"]
    assert tribunal_detail["forensic_coverage"]["status"] == "forensic_coverage_present"
    assert tribunal_detail["forensic_coverage"]["explicit_event_count"] == 0
    assert tribunal_detail["forensic_coverage"]["recent_path_match_count"] == 1
    assert any(event["kind"] == "workspace_activity" for event in tribunal_detail["timeline"])


def test_render_registry_dashboard_skips_cached_rebuild_before_payload_builder(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    _seed_repo(tmp_path)

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

    def _boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("registry payload should be skipped on a cache hit")

    monkeypatch.setattr(renderer, "_build_payload", _boom)

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/registry/registry.html"])
    assert rc == 0

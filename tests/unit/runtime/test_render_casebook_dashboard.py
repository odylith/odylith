from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import render_casebook_dashboard as renderer


def test_render_casebook_dashboard_splits_brief_from_agent_learnings(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-01-example-bug.md"
    bug_path.parent.mkdir(parents=True, exist_ok=True)
    bug_path.write_text("# Example bug\n", encoding="utf-8")

    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_bug_snapshot",
        lambda **kwargs: [
            {
                "bug_id": "CB-999",
                "bug_key": "odylith/casebook/bugs/2026-04-01-example-bug.md",
                "title": "Casebook detail repeats bug signals",
                "date": "2026-04-01",
                "severity": "P1",
                "severity_token": "p1",
                "status": "Open",
                "status_token": "open",
                "components": "`src/odylith/runtime/surfaces/render_casebook_dashboard.py`",
                "component_tokens": ["casebook"],
                "archive_bucket": "",
                "source_path": "odylith/casebook/bugs/2026-04-01-example-bug.md",
                "source_exists": True,
                "is_open": True,
                "is_open_critical": True,
                "workstreams": ["B-025"],
                "summary": "The same bug signals were rendered in multiple neighboring sections.",
                "fields": {
                    "Description": "The same bug signals were rendered in multiple neighboring sections.",
                    "Failure Signature": "The detail view kept repeating the same guidance and evidence.",
                    "Trigger Path": "Open the Casebook tab and select a bug.",
                    "Detected By": "Manual shell review.",
                    "Timeline": "Observed during product-repo refresh validation.",
                    "Impact": "The bug detail felt noisy and harder to scan.",
                    "Blast Radius": "Anyone using Casebook as the first readout.",
                    "Root Cause": "Human and agent-oriented material were mixed together without enough separation.",
                    "Solution": "Keep the top brief concise and move deeper context into Odylith Agent Learnings.",
                    "Workaround": "Ignore the repeated lower sections.",
                    "Rollback/Forward Fix": "Forward fix only.",
                    "Verification": "Render the surface and inspect the selected bug in a browser.",
                    "Agent Guardrails": "Do not repeat the same field content in the top brief and the lower learnings band.",
                    "Preflight Checks": "Inspect the selected bug detail in the rendered shell before shipping.",
                },
                "detail_sections": [
                    {"field": "Description", "value": "The same bug signals were rendered in multiple neighboring sections.", "kind": "primary"},
                    {"field": "Failure Signature", "value": "The detail view kept repeating the same guidance and evidence.", "kind": "extended"},
                    {"field": "Trigger Path", "value": "Open the Casebook tab and select a bug.", "kind": "extended"},
                    {"field": "Impact", "value": "The bug detail felt noisy and harder to scan.", "kind": "primary"},
                    {"field": "Blast Radius", "value": "Anyone using Casebook as the first readout.", "kind": "extended"},
                    {"field": "Root Cause", "value": "Human and agent-oriented material were mixed together without enough separation.", "kind": "primary"},
                    {"field": "Solution", "value": "Keep the top brief concise and move deeper context into Odylith Agent Learnings.", "kind": "primary"},
                    {"field": "Verification", "value": "Render the surface and inspect the selected bug in a browser.", "kind": "primary"},
                    {"field": "Agent Guardrails", "value": "Do not repeat the same field content in the top brief and the lower learnings band.", "kind": "extended"},
                    {"field": "Preflight Checks", "value": "Inspect the selected bug detail in the rendered shell before shipping.", "kind": "extended"},
                ],
                "code_refs": ["src/odylith/runtime/surfaces/render_casebook_dashboard.py"],
                "doc_refs": ["odylith/registry/source/components/casebook/CURRENT_SPEC.md"],
                "test_refs": ["tests/integration/runtime/test_surface_browser_deep.py"],
                "contract_refs": [],
                "component_matches": [],
                "diagram_refs": [],
                "related_bug_refs": [],
                "agent_guidance": {
                    "lessons": [],
                    "preflight_checks": [
                        "Inspect the selected bug detail in the rendered shell before shipping.",
                        "Keep the browser proof green.",
                    ],
                    "proof_paths": [
                        "src/odylith/runtime/surfaces/render_casebook_dashboard.py",
                        "tests/integration/runtime/test_surface_browser_deep.py",
                    ],
                },
                "intelligence_coverage": {
                    "present_fields": [
                        "Detected By",
                        "Failure Signature",
                        "Trigger Path",
                        "Timeline",
                        "Blast Radius",
                        "Workaround",
                        "Rollback/Forward Fix",
                        "Agent Guardrails",
                        "Preflight Checks",
                    ],
                    "missing_fields": ["Monitoring Updates"],
                    "required_missing_fields": ["Monitoring Updates"],
                    "captured_count": 9,
                    "total_fields": 23,
                    "critical_expectations": True,
                },
                "search_text": "casebook detail repeats bug signals",
            }
        ],
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/casebook/casebook.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "casebook" / "casebook.html").read_text(encoding="utf-8")
    app_js = (tmp_path / "odylith" / "casebook" / "casebook-app.v1.js").read_text(encoding="utf-8")
    assert "Failures, Impact, and Fix Context" in html
    assert "Track what broke, why it mattered, and what to do next from repo bug records and linked evidence." in html
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in html
    assert "minmax(220px, auto)" not in html
    assert "Repo Bug Knowledge View" not in html
    assert ".detail-section-agent {" in html
    assert "background: linear-gradient(180deg, #ffffff, #f5fbf8);" in html
    assert ".summary-facts {" in html
    assert "grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));" in html
    assert "padding: 10px 12px;" in html
    assert "Odylith Agent Learnings" in app_js
    assert "Human Readout" not in app_js
    assert "Nearby Change Guidance" not in app_js
    assert "Inspect Next" not in app_js
    assert ".component-subtitle, .ref-meta {" in html
    assert "font-size: var(--surface-identifier-font-size, 14px);" in html
    assert "font-weight: var(--surface-identifier-font-weight, 500);" in html
    assert ".bug-row-kicker {" in html
    assert ".bug-row-kicker, .detail-kicker {" not in html
    assert "text-transform: uppercase;" in html
    assert ".action-chip {" in html
    assert "padding: var(--surface-deep-link-button-padding, 4px 12px);" in html
    assert "font-size: var(--surface-deep-link-button-font-size, 11px);" in html
    assert "font-weight: var(--surface-deep-link-button-font-weight, 700);" in html
    assert 'data-summary-field="${escapeHtml(label)}"' in app_js
    assert '<div class="summary-facts" role="list">${summaryFacts}</div>' in app_js
    assert '["Bug ID", row.bug_id || "-"]' in app_js
    assert '${detail.bug_id ? `<p class="detail-kicker">${escapeHtml(detail.bug_id)}</p>` : ""}' not in app_js
    assert app_js.index('<div class="summary-facts" role="list">${summaryFacts}</div>') < app_js.index("${summary}")
    assert "function normalizeSearchToken(value)" in app_js
    assert "function canonicalizeBugIdToken(value)" in app_js
    assert "function bugSearchText(row)" in app_js
    assert "function bugExactMatch(row, term)" in app_js
    assert "if (bugExactMatch(row, term)) return true;" in app_js
    assert "return normalizeSearchToken(searchText).includes(normalizedNeedle);" in app_js
    assert "Evidence and references" in app_js
    assert "Direct proof links" in app_js
    assert "No bug matches the current filters." not in app_js
    assert "Loading selected bug…" not in app_js
    assert "No structured detail sections were parsed from this entry." not in app_js
    assert "No bugs match the current filters and search text." not in app_js


def test_casebook_payload_dedupes_overlapping_proof_links_from_evidence_refs(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-01-example-bug.md"
    bug_path.parent.mkdir(parents=True, exist_ok=True)
    bug_path.write_text("# Example bug\n", encoding="utf-8")

    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_bug_snapshot",
        lambda **kwargs: [
            {
                "bug_id": "CB-999",
                "bug_key": "odylith/casebook/bugs/2026-04-01-example-bug.md",
                "title": "Casebook proof links repeat nearby evidence",
                "date": "2026-04-01",
                "severity": "P1",
                "severity_token": "p1",
                "status": "Open",
                "status_token": "open",
                "components": "`src/odylith/runtime/surfaces/render_casebook_dashboard.py`",
                "component_tokens": ["casebook"],
                "archive_bucket": "",
                "source_path": "odylith/casebook/bugs/2026-04-01-example-bug.md",
                "source_exists": True,
                "is_open": True,
                "is_open_critical": True,
                "workstreams": ["B-025"],
                "summary": "Direct proof links and evidence rows were echoing the same paths.",
                "fields": {},
                "detail_sections": [],
                "code_refs": ["src/odylith/runtime/surfaces/render_casebook_dashboard.py"],
                "doc_refs": [],
                "test_refs": ["tests/unit/runtime/test_render_casebook_dashboard.py"],
                "contract_refs": [],
                "component_matches": [],
                "diagram_refs": [],
                "related_bug_refs": [],
                "agent_guidance": {
                    "lessons": [],
                    "preflight_checks": [],
                    "proof_paths": [
                        "src/odylith/runtime/surfaces/render_casebook_dashboard.py",
                        "tests/unit/runtime/test_render_casebook_dashboard.py",
                    ],
                },
                "intelligence_coverage": {},
                "search_text": "casebook proof links repeat nearby evidence",
            }
        ],
    )

    payload = renderer._build_payload(  # noqa: SLF001
        repo_root=tmp_path,
        output_path=tmp_path / "odylith" / "casebook" / "casebook.html",
        runtime_mode="standalone",
    )

    bug = payload["bugs"][0]
    assert bug["code_ref_links"]
    assert bug["test_ref_links"]
    assert bug["agent_guidance"]["proof_links"] == []


def test_casebook_payload_preserves_proof_state_contract_fields(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-08-proof-state.md"
    bug_path.parent.mkdir(parents=True, exist_ok=True)
    bug_path.write_text("# Proof state bug\n", encoding="utf-8")

    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_bug_snapshot",
        lambda **kwargs: [
            {
                "bug_id": "CB-077",
                "bug_key": "odylith/casebook/bugs/2026-04-08-proof-state.md",
                "bug_route": "CB-077",
                "title": "Proof state lane is visible in Casebook",
                "date": "2026-04-08",
                "severity": "P1",
                "severity_token": "p1",
                "status": "Open",
                "status_token": "open",
                "components": "`src/odylith/runtime/governance/proof_state/resolver.py`",
                "component_tokens": ["casebook"],
                "archive_bucket": "",
                "source_path": "odylith/casebook/bugs/2026-04-08-proof-state.md",
                "source_exists": True,
                "is_open": True,
                "is_open_critical": True,
                "summary": "Casebook should show the same blocker lane and truthful claim as the other surfaces.",
                "workstreams": ["B-062"],
                "workstream_links": [{"workstream": "B-062", "href": "../index.html?tab=radar&workstream=B-062"}],
                "fields": {},
                "detail_sections": [],
                "code_refs": [],
                "doc_refs": [],
                "test_refs": [],
                "contract_refs": [],
                "component_matches": [],
                "diagram_refs": [],
                "related_bug_refs": [],
                "agent_guidance": {"lessons": [], "preflight_checks": [], "proof_paths": []},
                "intelligence_coverage": {},
                "proof_state": {
                    "lane_id": "proof-state-control-plane",
                    "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                    "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                    "first_failing_phase": "manifests-deploy",
                    "frontier_phase": "manifests-deploy",
                    "clearance_condition": "Hosted SIM3 passes beyond manifests-deploy",
                    "proof_status": "fixed_in_code",
                    "evidence_tier": "code_only",
                    "allowed_next_work": ["primary fix", "validating test", "deploy instruction"],
                    "deprioritized_until_cleared": ["docs", "UX polish", "broader hardening"],
                    "linked_bug_id": "CB-077",
                    "deployment_truth": {
                        "local_head": "unknown",
                        "pushed_head": "abc123",
                        "published_source_commit": "unknown",
                        "runner_fingerprint": "runner-v3",
                        "last_live_failing_commit": "abc123",
                    },
                },
                "proof_state_resolution": {"state": "resolved", "lane_ids": ["proof-state-control-plane"]},
                "claim_guard": {
                    "highest_truthful_claim": "fixed in code",
                    "blocked_terms": ["fixed", "cleared", "resolved"],
                    "hosted_frontier_advanced": False,
                },
                "search_text": "proof state lane casebook",
            }
        ],
    )

    payload = renderer._build_payload(  # noqa: SLF001
        repo_root=tmp_path,
        output_path=tmp_path / "odylith" / "casebook" / "casebook.html",
        runtime_mode="standalone",
    )

    bug = payload["bugs"][0]
    assert bug["proof_state"]["lane_id"] == "proof-state-control-plane"
    assert bug["proof_state"]["current_blocker"] == "Lambda permission lifecycle on ecs-drift-monitor invoke"
    assert bug["proof_state_resolution"] == {"state": "resolved", "lane_ids": ["proof-state-control-plane"]}
    assert bug["claim_guard"]["highest_truthful_claim"] == "fixed in code"


def test_render_casebook_dashboard_emits_proof_control_panel_contract(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-08-proof-state.md"
    bug_path.parent.mkdir(parents=True, exist_ok=True)
    bug_path.write_text("# Proof state bug\n", encoding="utf-8")

    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_bug_snapshot",
        lambda **kwargs: [
            {
                "bug_id": "CB-077",
                "bug_key": "odylith/casebook/bugs/2026-04-08-proof-state.md",
                "bug_route": "CB-077",
                "title": "Proof state lane is visible in Casebook",
                "date": "2026-04-08",
                "severity": "P1",
                "severity_token": "p1",
                "status": "Open",
                "status_token": "open",
                "components": "`src/odylith/runtime/governance/proof_state/resolver.py`",
                "component_tokens": ["casebook"],
                "archive_bucket": "",
                "source_path": "odylith/casebook/bugs/2026-04-08-proof-state.md",
                "source_exists": True,
                "is_open": True,
                "is_open_critical": True,
                "summary": "Casebook should show the same blocker lane and truthful claim as the other surfaces.",
                "workstreams": ["B-062"],
                "workstream_links": [{"workstream": "B-062", "href": "../index.html?tab=radar&workstream=B-062"}],
                "fields": {},
                "detail_sections": [],
                "code_refs": [],
                "doc_refs": [],
                "test_refs": [],
                "contract_refs": [],
                "component_matches": [],
                "diagram_refs": [],
                "related_bug_refs": [],
                "agent_guidance": {"lessons": [], "preflight_checks": [], "proof_paths": []},
                "intelligence_coverage": {},
                "proof_state": {
                    "lane_id": "proof-state-control-plane",
                    "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                    "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                    "first_failing_phase": "manifests-deploy",
                    "frontier_phase": "manifests-deploy",
                    "clearance_condition": "Hosted SIM3 passes beyond manifests-deploy",
                    "proof_status": "fixed_in_code",
                    "evidence_tier": "code_only",
                    "allowed_next_work": ["primary fix", "validating test", "deploy instruction"],
                    "deprioritized_until_cleared": ["docs", "UX polish", "broader hardening"],
                    "linked_bug_id": "CB-077",
                    "warnings": [
                        "Recent activity is skewing away from the primary blocker while Lambda permission lifecycle on ecs-drift-monitor invoke is still open."
                    ],
                    "deployment_truth": {
                        "local_head": "unknown",
                        "pushed_head": "abc123",
                        "published_source_commit": "fedcba",
                        "runner_fingerprint": "runner-v3",
                        "last_live_failing_commit": "abc123",
                    },
                    "last_falsification": {
                        "recorded_at": "2026-04-08T18:42:00Z",
                        "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                        "frontier_phase": "manifests-deploy",
                    },
                },
                "proof_state_resolution": {"state": "resolved", "lane_ids": ["proof-state-control-plane"]},
                "claim_guard": {
                    "highest_truthful_claim": "fixed in code",
                    "blocked_terms": ["fixed", "cleared", "resolved"],
                    "hosted_frontier_advanced": False,
                },
                "search_text": "proof state lane casebook",
            }
        ],
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/casebook/casebook.html"])

    assert rc == 0
    app_js = (tmp_path / "odylith" / "casebook" / "casebook-app.v1.js").read_text(encoding="utf-8")
    payload_js = (tmp_path / "odylith" / "casebook" / "casebook-payload.v1.js").read_text(encoding="utf-8")
    assert "Proof Control Panel" in app_js
    assert "Pinned blocker, frontier, and proof tier for this bug lane." in app_js
    assert "No dominant proof lane is resolved for this bug yet." in app_js
    assert "Proof state is ambiguous across multiple blocker lanes" in app_js
    assert "Deployed vs local truth" in app_js
    assert "Highest truthful claim" in app_js
    assert '"proof_state"' in payload_js
    assert '"current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke"' in payload_js
    assert '"allowed_next_work": ["primary fix", "validating test", "deploy instruction"]' in payload_js
    assert '"highest_truthful_claim": "fixed in code"' in payload_js

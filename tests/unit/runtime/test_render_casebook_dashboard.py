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
    assert 'data-summary-field="${escapeHtml(label)}"' in app_js
    assert '<div class="summary-facts" role="list">${summaryFacts}</div>' in app_js
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

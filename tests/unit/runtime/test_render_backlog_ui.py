from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import render_backlog_ui


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_backlog_payload(root: Path) -> dict[str, object]:
    payload_js = (root / "odylith" / "radar" / "backlog-payload.v1.js").read_text(encoding="utf-8")
    return json.loads(payload_js.split(" = ", 1)[1].rsplit(";", 1)[0])


def _seed_backlog_render_repo(root: Path, *, product_repo: bool = True) -> None:
    if product_repo:
        (root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
        (root / "pyproject.toml").write_text(
            "[project]\nname = \"odylith\"\nversion = \"0.1.11\"\n",
            encoding="utf-8",
        )
    (root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        "{\"version\": \"v1\", \"components\": []}\n",
        encoding="utf-8",
    )
    (root / "odylith" / "technical-plans").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "technical-plans" / "INDEX.md").write_text("# Plan Index\n", encoding="utf-8")
    atlas_catalog = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    atlas_catalog.parent.mkdir(parents=True, exist_ok=True)
    atlas_catalog.write_text("{\"version\":\"v1\",\"diagrams\":[]}\n", encoding="utf-8")

    idea_path = root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-11-cached-render.md"
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text(
        (
            "status: queued\n\n"
            "idea_id: B-777\n\n"
            "title: Cached Radar Render\n\n"
            "date: 2026-04-11\n\n"
            "priority: P1\n\n"
            "commercial_value: 4\n\n"
            "product_impact: 4\n\n"
            "market_value: 4\n\n"
            "impacted_parts: radar\n\n"
            "sizing: M\n\n"
            "complexity: Medium\n\n"
            "ordering_score: 88\n\n"
            "ordering_rationale: prove cached radar render reuse\n\n"
            "confidence: high\n\n"
            "founder_override: no\n\n"
            "promoted_to_plan:\n\n"
            "workstream_type: standalone\n\n"
            "workstream_parent:\n\n"
            "workstream_children:\n\n"
            "workstream_depends_on:\n\n"
            "workstream_blocks:\n\n"
            "related_diagram_ids:\n\n"
            "workstream_reopens:\n\n"
            "workstream_reopened_by:\n\n"
            "workstream_split_from:\n\n"
            "workstream_split_into:\n\n"
            "workstream_merged_into:\n\n"
            "workstream_merged_from:\n\n"
            "supersedes:\n\n"
            "superseded_by:\n\n"
            "## Problem\nKeep no-op Radar rerenders fast.\n\n"
            "## Customer\nOperators running repeated syncs.\n\n"
            "## Opportunity\nAvoid redoing unchanged projection work.\n\n"
            "## Proposed Solution\nFingerprint the render input cone.\n\n"
            "## Scope\nRadar surface only.\n\n"
            "## Non-Goals\nChanging Radar truth.\n\n"
            "## Risks\nUnsound cache keys.\n\n"
            "## Dependencies\nNone.\n\n"
            "## Success Metrics\nNo-op render skips the expensive path.\n\n"
            "## Validation\nRender twice and compare outputs.\n\n"
            "## Rollout\nShip with unit coverage.\n\n"
            "## Why Now\nSync latency is dominated by redundant work.\n\n"
            "## Product View\nRadar should keep exact output bytes while skipping unchanged rebuilds.\n"
        ),
        encoding="utf-8",
    )
    index_path = root / "odylith" / "radar" / "source" / "INDEX.md"
    index_path.write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-04-11\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| 1 | B-777 | Cached Radar Render | P1 | 88 | 4 | 4 | 4 | M | Medium | queued | [cached-render]({idea_path.resolve().as_posix()}) |\n\n"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-777 (rank 1)\n"
            "- why now: make repeated render validation fast.\n"
            "- expected outcome: unchanged rebuilds become cheap.\n"
            "- tradeoff: cache keys must stay conservative.\n"
            "- deferred for now: daemonization.\n"
            "- ranking basis: score-led queue ordering.\n"
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize("text", [
    "See odylith/casebook/SPEC.md and scripts/compass_dashboard_runtime.py.",
    "Run `pytest -q tests/scripts/test_sync_workstream_artifacts.py`.",
    "Point maintainers to python -m scripts.run_clean_snapshot_strict_sync --repo-root . when needed.",
])
def test_render_section_body_preserves_authored_paths_and_commands(text: str) -> None:
    rendered = render_backlog_ui._render_section_body(repo_root=REPO_ROOT, lines=[text])
    root = ElementTree.fromstring("<div>" + rendered + "</div>")
    assert "".join(root.itertext()).strip() == text.replace("`", "")
    assert not hasattr(render_backlog_ui, "_rewrite_section_text")


def test_render_section_body_keeps_inline_numbered_prose_in_its_paragraph() -> None:
    html = render_backlog_ui._render_section_body(
        repo_root=REPO_ROOT,
        lines=[
            (
                "The first path is: 1. User opens the product and starts capture. "
                "2. User performs one bounded input. 3. User stops capture. "
                "4. The product shows the reviewed result. No broader automation is in scope yet."
            )
        ],
    )

    assert html.strip() == (
        "<p>The first path is: 1. User opens the product and starts capture. "
        "2. User performs one bounded input. 3. User stops capture. "
        "4. The product shows the reviewed result. No broader automation is in scope yet.</p>"
    )


def test_render_section_body_preserves_inline_numbered_prose_inside_a_bullet() -> None:
    html = render_backlog_ui._render_section_body(
        repo_root=REPO_ROOT,
        lines=[
            (
                "- Proof path: 1. User opens the product and starts capture. "
                "2. User performs one bounded input. 3. User stops capture. "
                "4. The product shows the reviewed result. If this fails, implementation should pause."
            )
        ],
    )

    assert "<ul>" in html
    root = ElementTree.fromstring(html)
    assert len(root.findall("li")) == 1
    assert root.find("li").text == (
        "Proof path: 1. User opens the product and starts capture. "
        "2. User performs one bounded input. 3. User stops capture. "
        "4. The product shows the reviewed result. If this fails, implementation should pause."
    )


def test_render_section_body_renders_authored_markdown_emphasis() -> None:
    html = render_backlog_ui._render_section_body(
        repo_root=REPO_ROOT,
        lines=["**Account owner:** wants a clean operational summary without raw emphasis tokens."],
    )

    assert "**" not in html
    assert "<p><strong>Account owner:</strong> wants a clean operational summary without raw emphasis tokens.</p>" in html


def test_extract_section_bodies_preserves_authored_emphasis_tokens(tmp_path: Path) -> None:
    idea = tmp_path / "idea.md"
    idea.write_text(
        "## Customer\n**Account owner:** wants clean UI text.\n\n## Problem\n__Raw emphasis__ leaks.\n",
        encoding="utf-8",
    )

    sections = dict(render_backlog_ui._extract_sections_with_body(idea))

    assert sections["Customer"] == ["**Account owner:** wants clean UI text.", ""]
    assert sections["Problem"] == ["__Raw emphasis__ leaks."]


def test_render_plan_html_preserves_authored_legacy_meta_row_paths(tmp_path: Path) -> None:
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

    assert "<code>scripts/render_compass_dashboard.py</code>" in html
    assert "<code>odylith/surfaces/DASHBOARD_SPEC.md</code> is stale and must not survive." in html
    assert "<code>python -m scripts.run_clean_snapshot_strict_sync --repo-root .</code> is retired." in html
    assert "<code>pytest -q tests/scripts/test_sync_workstream_artifacts.py</code>" in html


def test_render_plan_html_traceability_cards_are_repo_bounded_and_stateful(tmp_path: Path) -> None:
    repo_root = tmp_path
    plan_path = repo_root / "odylith" / "technical-plans" / "in-progress" / "2026-04-28-traceability.md"
    plan_path.parent.mkdir(parents=True)
    existing_doc = repo_root / "docs" / "runbooks" / "repair.md"
    existing_doc.parent.mkdir(parents=True)
    existing_doc.write_text("# Repair\n", encoding="utf-8")
    source_file = repo_root / "src" / "odylith" / "runtime" / "example.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    outside_file = tmp_path.parent / "outside-traceability.md"
    outside_file.write_text("# Outside\n", encoding="utf-8")
    plan_path.write_text(
        "\n".join(
            (
                "# Traceability Plan",
                "",
                "Status: In progress",
                "Created: 2026-04-28",
                "Updated: 2026-04-28",
                "",
                "## Traceability",
                "### runbooks:",
                "- [Repair](docs/runbooks/repair.md#operator-flow)",
                "- `../outside-traceability.md`",
                f"- `{outside_file}`",
                "### Code references",
                f"- `{source_file}:1`",
                "- `src/odylith/runtime/missing.py`",
                "",
                "## Goal",
                "Keep plan traceability visible without linking outside the repo.",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    html = render_backlog_ui._render_plan_html(
        repo_root=repo_root,
        index_output_path=repo_root / "odylith" / "radar" / "radar.html",
        entry={
            "idea_id": "B-998",
            "title": "Traceability Plan",
            "promoted_to_plan_file": "odylith/technical-plans/in-progress/2026-04-28-traceability.md",
        },
    )

    assert "No plan traceability section captured." not in html
    assert "docs/runbooks/repair.md#operator-flow" not in html
    assert "docs/runbooks/repair.md" in html
    assert "src/odylith/runtime/example.py:1" not in html
    assert "src/odylith/runtime/example.py" in html
    assert "src/odylith/runtime/missing.py" in html
    assert "trace-link-missing" in html
    assert "outside-traceability.md" not in html
    assert "Keep plan traceability visible without linking outside the repo." in html


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

    assert "<code>pytest -q tests/scripts/test_sync_workstream_artifacts.py</code>" in html
    assert "<code>python -m scripts.run_clean_snapshot_strict_sync --repo-root .</code>" in html


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


def test_render_idea_spec_html_preserves_inventory_and_rationale_source(tmp_path: Path) -> None:
    repo_root = tmp_path
    idea_path = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-08-blob-example.md"
    idea_path.parent.mkdir(parents=True)
    long_inventory = (
        "Make product-owned systems explicit: Input Normalization: Converts Long Source Records Into "
        "A Consistent Domain View, Candidate Scoring: Ranks Items By Recency, Duplicate Signals, "
        "Price Movement, and Optional User Context, Review Flow: Lets the User Inspect Evidence, "
        "Approve, Snooze, or Reject A Proposed Action, plus 2 more. Keep external systems separate: "
        "Provider feeds; external portals; identity and consent services. Preserve release proof: "
        "Every claim maps back to source evidence, reviewer action, state transition, validation output, "
        "deferred scope, and a clear implementation stop condition before broader planning proceeds."
    )
    rationale_bullets = [
        f"why now: {long_inventory}",
        "tradeoff: Define Boundary keeps sample product focused on one releaseable path while delaying scope not accepted in the confirmation.",
        "deferred for now: anything outside this proof boundary waits: broad unproven scope.",
        "ranking basis: Sample Product release readiness depends on preserving the confirmed product story, domain state, evidence, and proof boundary.",
    ]
    idea_path.write_text(
        "\n".join(
            (
                "---",
                "status: queued",
                "idea_id: B-997",
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
                "## Opportunity",
                long_inventory,
                "",
                "## Why Now",
                long_inventory,
            )
        )
        + "\n",
        encoding="utf-8",
    )

    html = render_backlog_ui._render_idea_spec_html(
        repo_root=repo_root,
        index_output_path=repo_root / "odylith" / "radar" / "radar.html",
        entry={
            "idea_id": "B-997",
            "title": "Example",
            "priority": "P1",
            "status": "queued",
            "ordering_score": 42,
            "idea_file": "odylith/radar/source/ideas/2026-04/2026-04-08-blob-example.md",
            "rationale_bullets": rationale_bullets,
        },
    )

    for title in ("Opportunity", "Why Now"):
        section = html.split(f"<h2>{title}</h2>", 1)[1].split("</section>", 1)[0]
        positions = []
        for sentence in long_inventory.split(". "):
            assert sentence in section, sentence
            positions.append(section.index(sentence))
        assert positions == sorted(positions)
    rationale = html.split("<h2>Decision Basis</h2>", 1)[1].split("</article>", 1)[0]
    rendered_items = ElementTree.fromstring(f"<div>{rationale}</div>").findall("./ul/li")
    assert [" ".join(" ".join(item.itertext()).split()) for item in rendered_items] == rationale_bullets
    assert "…" not in rationale


def test_render_section_body_preserves_dense_single_paragraph_prose() -> None:
    html = render_backlog_ui._render_section_body(
        repo_root=REPO_ROOT,
        lines=[
            "`v0.1.9` reached GA on 2026-04-07, but the release lane still carried several truths that should not become permanent operating posture.",
            "Fresh downstream sync feedback on 2026-04-07 added another trust slice: operator-facing sync behavior is stronger than its public surface suggests, but it still hides supported controls and can rewrite unchanged generated JSON artifacts in ways that make file mtimes disagree with embedded `generated_utc`.",
            "Another downstream packet the same day exposed a Compass refresh trust gap: bounded refresh behaved as designed, but Compass still advertised an older deeper rerender path that shared the same hard dashboard timeout.",
            "Release prep on 2026-04-08 exposed one more maintainer truth: PR `pytest` and `candidate-proof` still carried unit tests that silently depended on a live Codex host runtime or a local `codex` binary.",
        ],
    )

    assert html.count("<p>") == 1
    assert "<code>generated_utc</code>" in html
    assert "bounded refresh" in html
    assert "<code>pytest</code>" in html


@pytest.mark.parametrize("section_title", ["Problem", "Validation"])
def test_render_idea_spec_html_preserves_complete_late_constraints(
    tmp_path: Path, section_title: str,
) -> None:
    sentences = [
        "An operator reads every recorded observation before deciding whether an item can proceed to the next stage.",
        "The record retains the original measurement, its observer and its collection time so another person can review the same evidence.",
        "A separate reviewer checks the item against its recorded requirements and records any unresolved uncertainty without changing the original observation.",
        "The visible result includes the decision and the evidence that supports it, including the final restriction stated at the end of this paragraph.",
        "Do not publish the result until the independent reviewer has accepted the complete record.",
    ]
    final_paragraph = "A rejected item remains available for inspection. Rejection must never be presented as successful publication."
    checklist = [
        "Preserve the first observation and its original owner.",
        "Verify that the final result remains unpublished when its review is incomplete.",
    ]
    idea = tmp_path / "full-record.md"
    idea.write_text(
        "---\nidea_id: B-996\ntitle: Full record\nstatus: queued\n---\n\n"
        f"## {section_title}\n{' '.join(sentences)}\n\n{final_paragraph}\n\n"
        + "\n".join(f"- [ ] {item}" for item in checklist) + "\n",
        encoding="utf-8",
    )
    html = render_backlog_ui._render_idea_spec_html(
        repo_root=tmp_path, index_output_path=tmp_path / "radar.html",
        entry={"idea_id": "B-996", "title": "Full record", "idea_file": "full-record.md"},
    )
    section = html.split(f"<h2>{section_title}</h2>", 1)[1].split("</section>", 1)[0]
    expected = [*sentences, *final_paragraph.split(". "), *checklist]
    positions = []
    for text in expected:
        assert text in section, text
        positions.append(section.index(text))
    assert positions == sorted(positions)
    assert section.count('class="check-text"') == 2
    assert section.count('type="checkbox"') == 2
    assert "…" not in section


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
    items = ElementTree.fromstring(html).findall("li")
    assert len(items) == 2
    assert " ".join("".join(items[0].itertext()).split()) == "Primary: operators relying on doctor --repair or reinstall --latest to recover the repo in place."
    assert items[1].text == "Secondary: maintainers proving the release path."


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


def test_render_backlog_ui_id_chips_use_only_custom_tooltip_not_browser_title() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert 'class="chip chip-link entity-id-chip ${escapeHtml(tone)}"' in html
    assert 'data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}"' in html
    assert 'title="${escapeHtml(tooltip)}"' not in html
    assert 'title="${escapeHtml(token)}"' not in html
    assert 'title="${escapeHtml(row.idea_id)}"' not in html


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


def test_render_backlog_ui_explains_empty_source_and_filtered_results() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "Select a workstream from the ranked list." not in html
    assert "No workstreams yet" in html
    assert "No matching workstreams" in html
    assert "Change your search or filters" in html
    assert 'href="../index.html?tab=project" target="_top"' in html
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


def test_render_backlog_ui_uses_authored_decision_basis_without_inferred_labels() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "function humanizeToken(token)" in html
    assert 'function decisionBasisLabel' not in html
    assert 'function renderDecisionBasisLine' not in html
    assert "function compactNarrativeForDetail(value)" not in html
    assert 'row.rationale_html' in html
    assert "escapeHtml(line)" in html
    assert 'class="bullets decision-bullets"' in html
    assert "decision-basis-label" not in html
    assert "decision-basis-copy" not in html
    assert "grid-template-columns: minmax(128px, 178px) minmax(0, 1fr);" not in html


def test_render_backlog_ui_includes_release_filters_summary_cards_and_release_chips() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert 'function escapeHtml(value) {\n      return String(value ?? "")' in html
    assert '<select id="type">' in html
    assert '<option value="umbrella">Umbrella</option>' in html
    assert '<option value="child">Child</option>' in html
    assert 'type: "all",' in html
    assert 'type: document.getElementById("type"),' in html
    assert 'if (state.type !== "all" && workstreamTypeInfo(row).type !== state.type) return false;' in html
    assert 'el.type.value = state.type;' in html
    assert 'bind(el.type, "type");' in html
    assert "state.type = \"all\";" in html
    assert "grid-template-columns: minmax(220px, 1.8fr) repeat(7, minmax(0, 1fr));" in html
    assert ".controls input,\n    .controls select {\n      min-width: 0;\n    }" in html
    assert 'if (state.release !== "all" && workstreamActiveReleaseId(row) !== state.release) return false;' in html
    assert "seedSelect(\n      el.release," in html
    assert "Active target release for this workstream." in html
    assert 'const text = String(release.version || release.display_label || release.tag || release.effective_name || release.name || release.release_id || "").trim().replace(/\\s+/g, " ");' in html
    assert 'const match = /\\bv?(\\d+(?:\\.\\d+){1,3})\\b/i.exec(text);' in html
    assert "return text.length > 18 ?" in html
    assert 'escapeHtml(workstreamActiveReleaseLabel(row))' in html
    assert "Release ${workstreamActiveReleaseLabel(row)}" not in html
    assert "function releaseCardLabel(row)" in html
    assert 'statRows.push(statBlock("Target Release", releaseCardLabel(currentRelease), { releaseOnly: true }));' in html
    assert 'statRows.push(statBlock("", releaseCardLabel(currentRelease), { releaseOnly: true }));' not in html
    assert 'statRows.push(statBlock("Wave Programs"' not in html
    assert 'statRows.push(statBlock("Active Waves", activeWaves));' in html
    assert html.index('statRows.push(statBlock("Active Waves", activeWaves));') < html.index('statRows.push(statBlock("Target Release", releaseCardLabel(currentRelease), { releaseOnly: true }));')
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


def test_render_backlog_ui_panel_headers_use_quiet_title_case() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert '<aside class="list-panel" aria-label="Workstreams">' in html
    assert '<span class="panel-head-title">Workstreams</span>' in html
    assert '<section class="detail-panel" aria-label="Selected workstream">' in html
    assert '<span class="panel-head-title">Selected workstream</span>' in html
    assert "Delivery Pipeline · Parked · Idea Stage · Finished" not in html
    assert "Selected Workstream Detail" not in html
    assert ".panel-head-title {\n  margin: 0;\n  color: var(--ink);\n  font-size: 15px;" in html
    assert "  line-height: 1.35;\n  letter-spacing: 0em;\n  font-weight: 700;\n  text-transform: none;\n}" in html


def test_render_backlog_ui_hides_internal_index_source_path_from_meta_bar() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert 'el.meta.textContent = `Showing ${filtered.length} of ${all.length} workstreams`;' in html
    assert "Showing ${filtered.length} of ${all.length} workstreams · Source:" not in html
    assert "DATA.index_file" not in html


def test_render_backlog_ui_sorts_default_sections_by_scope_signal_rank() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "function scopeSignalRank(row)" in html
    assert 'if (a.section !== "finished" && state.sort === "rank") {' in html
    assert "const rankDelta = scopeSignalRank(b) - scopeSignalRank(a);" in html
    assert 'state.sort === "score"' in html
    assert 'state.sort === "date"' in html


def test_render_backlog_ui_defaults_to_date_sort() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert 'sort: "date",' in html
    assert '<option value="date" selected>Sort: Date</option>' in html
    assert "el.sort.value = state.sort;" in html
    assert "syncFilterControls();\n    render();" in html


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


def test_render_backlog_ui_routes_topology_diagram_ids_through_shared_identifier_chip_contract() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "class=\"chip chip-link entity-id-chip chip-topology-diagram\"" in html


def test_backlog_summary_entry_keeps_fail_closed_detail_fields() -> None:
    summary = render_backlog_ui._build_backlog_summary_entry(
        {
            "idea_id": "B-073",
            "title": "Runtime detail shape",
            "problem": "Runtime detail rows must expose renderer-ready problem text.",
            "customer": "Operators opening Radar detail for a populated workstream.",
            "opportunity": "Keep static summary data useful when runtime detail is unavailable.",
            "founder_pov": "Radar should never collapse populated source truth into hollow detail.",
            "success_metrics": "- B-073 renders its workstream details.\n- Fallback detail remains populated.",
            "impacted_parts": "radar, context-engine",
            "idea_file": "odylith/radar/source/ideas/2026-04/b-073.md",
            "idea_href": "source/ideas/2026-04/b-073.md",
            "idea_ui_file": "odylith/radar/radar.html",
            "idea_ui_href": "radar.html?view=spec&workstream=B-073",
            "promoted_to_plan": "odylith/technical-plans/in-progress/b-073.md",
            "promoted_to_plan_file": "odylith/technical-plans/in-progress/b-073.md",
            "promoted_to_plan_href": "technical-plans/in-progress/b-073.md",
            "promoted_to_plan_ui_file": "odylith/radar/radar.html",
            "promoted_to_plan_ui_href": "radar.html?view=plan&workstream=B-073",
            "registry_components": [{"component_id": "radar", "name": "Radar"}],
        }
    )

    assert summary["problem"] == "Runtime detail rows must expose renderer-ready problem text."
    assert summary["customer"] == "Operators opening Radar detail for a populated workstream."
    assert summary["opportunity"] == "Keep static summary data useful when runtime detail is unavailable."
    assert summary["founder_pov"] == "Radar should never collapse populated source truth into hollow detail."
    assert "- B-073 renders its workstream details." in str(summary["success_metrics"])
    assert summary["impacted_parts"] == "radar, context-engine"
    assert summary["idea_href"] == "source/ideas/2026-04/b-073.md"
    assert summary["idea_ui_href"] == "radar.html?view=spec&workstream=B-073"
    assert summary["promoted_to_plan"] == "odylith/technical-plans/in-progress/b-073.md"
    assert summary["promoted_to_plan_href"] == "technical-plans/in-progress/b-073.md"
    assert summary["promoted_to_plan_ui_href"] == "radar.html?view=plan&workstream=B-073"
    assert summary["registry_components"] == [{"component_id": "radar", "name": "Radar"}]
    assert "idea_file" not in summary
    assert "idea_ui_file" not in summary
    assert "promoted_to_plan_file" not in summary
    assert "promoted_to_plan_ui_file" not in summary


def test_render_backlog_ui_side_rail_keeps_only_core_row_chips() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert ".row-meta {" in html
    assert ".row-chips-end {" in html
    assert '<div class="row-meta">' in html
    assert '<div class="row-chips row-chips-end">' in html
    assert '<span class="chip">Age ${escapeHtml(ageLabel)}</span>' in html
    assert "${releaseChip}" in html
    assert "Exec ${escapeHtml(executionDays)}" not in html
    assert "const footerChips =" not in html
    assert "const waveChips = executionWaveRoleChips(row);" not in html


def test_render_backlog_ui_side_rail_projects_authored_story_block() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert 'function rowStorySummary(row)' in html
    assert 'row.story_text' in html
    assert 'row.story_source' in html
    assert 'Authored workstream summary' in html
    assert 'No authored workstream summary yet.' in html
    assert 'white-space: pre-wrap' in html
    assert 'LOW_VALUE_STORY_PATTERNS' not in html
    assert 'workstreamStoryParagraph' not in html
    assert 'titleNarrativeSentence' not in html


def test_render_backlog_ui_places_registry_components_inside_topology_board() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert 'title: "Registry Components"' in html
    assert "registryComponentLinksHtml" in html
    assert "registryComponentCount" in html
    assert "topology-component-strip" not in html
    assert "topology-component-strip-label" not in html
    assert '<span class="topology-component-strip-label">Components</span>' not in html
    assert '<p class="trace-subhead">Registry Components</p>' not in html


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
    assert ".detail-pair-grid {" not in html
    assert ".detail-pair-card {" not in html
    assert ".detail-copy ol {" in html
    assert ".detail-copy .inline-steps {" not in html


def test_render_backlog_ui_keeps_unknown_execution_wave_progress_unknown() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "const numericProgressOrNull = (value) => {" in html
    assert 'if (value === null || value === undefined || value === "") return null;' in html
    assert 'Object.prototype.hasOwnProperty.call(plan, "display_progress_ratio")' in html


def test_render_backlog_ui_runtime_fallback_preserves_blocks_without_sentence_reparsing() -> None:
    html = render_backlog_ui._render_html(payload={"entries": []})

    assert "function readableTextHtml(value" in html
    assert "function splitInlineOrderedSteps" not in html
    assert "function compactNarrativeForDetail" not in html
    assert "function structuredPairListHtml" not in html
    assert 'const rich = String(renderedHtml || "").trim();' in html
    assert 'return `<div class="detail-copy">${readableTextHtml(value, fallback)}</div>`;' in html
    assert 'return `<div class="detail-copy">${rich}</div>`;' in html
    assert 'return `<p class="source-text">${escapeHtml(text)}</p>`;' in html


def test_render_backlog_ui_skips_cached_rebuild_before_snapshot_load(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    _seed_backlog_render_repo(tmp_path)

    rc = render_backlog_ui.main(
        [
            "--repo-root",
            str(tmp_path),
            "--output",
            "odylith/radar/radar.html",
            "--runtime-mode",
            "standalone",
        ]
    )
    assert rc == 0

    def _boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("backlog snapshot loading should be skipped on a cache hit")

    monkeypatch.setattr(render_backlog_ui.contract, "load_backlog_index_snapshot", _boom)

    rc = render_backlog_ui.main(
        [
            "--repo-root",
            str(tmp_path),
            "--output",
            "odylith/radar/radar.html",
            "--runtime-mode",
            "standalone",
        ]
    )
    assert rc == 0


def test_render_backlog_ui_emits_runtime_contract(tmp_path: Path) -> None:
    _seed_backlog_render_repo(tmp_path)

    rc = render_backlog_ui.main(
        [
            "--repo-root",
            str(tmp_path),
            "--output",
            "odylith/radar/radar.html",
            "--runtime-mode",
            "standalone",
        ]
    )

    assert rc == 0
    payload = _load_backlog_payload(tmp_path)
    assert payload["runtime_contract"]["surface"] == "radar"
    assert payload["runtime_contract"]["cache_hit"] is False
    assert payload["runtime_contract"]["built_from"] == "surface_render"


def test_render_backlog_ui_payload_keeps_source_and_renders_emphasis_for_display(tmp_path: Path) -> None:
    _seed_backlog_render_repo(tmp_path)
    idea_path = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-11-cached-render.md"
    content = idea_path.read_text(encoding="utf-8")
    content = content.replace(
        "ordering_rationale: prove cached radar render reuse",
        "ordering_rationale: **prove cached radar render reuse**",
    )
    content = content.replace(
        "Operators running repeated syncs.",
        "**Operators:** running repeated syncs.",
    )
    idea_path.write_text(content, encoding="utf-8")

    rc = render_backlog_ui.main(
        [
            "--repo-root",
            str(tmp_path),
            "--output",
            "odylith/radar/radar.html",
            "--runtime-mode",
            "standalone",
        ]
    )

    assert rc == 0
    payload = _load_backlog_payload(tmp_path)
    entry = payload["entries"][0]
    assert entry["ordering_rationale"] == "**prove cached radar render reuse**"
    assert "<strong>prove cached radar render reuse</strong>" in entry["ordering_rationale_html"]
    assert entry["customer"] == "**Operators:** running repeated syncs."
    assert "<strong>Operators:</strong>" in entry["customer_html"]
    assert "**" not in entry["customer_html"]
    detail_shard = (tmp_path / "odylith" / "radar" / "backlog-detail-shard-001.v1.js").read_text(
        encoding="utf-8"
    )
    assert "**Operators" in detail_shard
    assert "<strong>Operators:</strong>" in detail_shard

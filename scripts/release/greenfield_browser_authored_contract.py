"""Browser contract for exact structured Greenfield authored facts."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    provisional_proof_assumption,
    require_provisional_proof_decision,
)
from odylith.runtime.domain_intelligence.greenfield_event_ordering import validate_source_precedence
from odylith.runtime.domain_intelligence.greenfield_provisional_design import validate_provisional_design


AUTHORED_STRUCTURE_EXPRESSION = """(node) => {
  const visible = (item) => Boolean(item?.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}));
  const text = (item) => String(item?.textContent || "").trim().replace(/\\s+/g, " ");
  const visibleText = (item) => visible(item)
    ? String(item.innerText || "").trim().replace(/\\s+/g, " ") : "";
  const eventRows = (selector) => Array.from(node.querySelectorAll(selector)).map((item) => ({
    order: Number(item.dataset.eventOrder || "0"), text: visibleText(item),
    quote_count: item.querySelectorAll(':scope > [data-authored-event-quote]').length,
    quote: visibleText(item.querySelector(':scope > [data-authored-event-quote]'))
  }));
  const firstPath = node.querySelector('[data-authored-fact-list="first_path"]');
  const firstPathCard = firstPath?.closest('[data-semantic-slot="first_path"]');
  const disclosures = Array.from(firstPathCard?.querySelectorAll('[data-authored-event-details]') || []);
  const capabilities = node.querySelector('[data-authored-fact-list="owned_capabilities"]');
  return {
    first_path: eventRows('[data-authored-fact-list="first_path"] [data-authored-fact-item]'),
    first_path_details: disclosures.map((item) => ({
      native: item.tagName === 'DETAILS' && item.querySelectorAll(':scope > summary').length === 1,
      open: Boolean(item.open), summary: visibleText(item.querySelector(':scope > summary'))
    })),
    first_path_evidence: Array.from(firstPathCard?.querySelectorAll('[data-authored-event-evidence]') || []).map((item) => ({
      order: Number(item.dataset.eventOrder || "0"),
      labels: Array.from(item.querySelectorAll('dt')).map(text),
      values: Array.from(item.querySelectorAll('dd')).map(text),
      actor_count: item.querySelectorAll('[data-authored-event-actor-value]').length,
      actor: text(item.querySelector('[data-authored-event-actor-value]')),
      in_disclosure: disclosures.length === 1 && disclosures[0].contains(item),
      visible: Array.from(item.querySelectorAll('dt, dd')).every(visible)
    })),
    first_path_authority: String(firstPath?.dataset.authorityKind || ""),
    first_path_label: visibleText(firstPath?.closest('[data-semantic-slot="first_path"]')
      ?.querySelector('[data-proposed-first-run-label]')),
    actors: Array.from(node.querySelectorAll("[data-authored-actor]")).map((card) => ({
      actor: visibleText(card.querySelector("h3")),
      source_name: String(card.dataset.authoredActor || "").trim()
    })),
    capabilities_authority: String(capabilities?.dataset.authorityKind || ""),
    capabilities_label: visibleText(node.querySelector('[data-provisional-design-label]')),
    capabilities: Array.from(capabilities?.querySelectorAll('[data-authored-fact-item]') || []).map((item) => ({
      owner: String(item.querySelector("[data-authored-owner]")?.innerText || "").trim(),
      responsibility: String(item.querySelector("[data-authored-responsibility]")?.innerText || "").trim()
    })),
    boundary_groups: Array.from(node.querySelectorAll("[data-authored-boundary-group]")).map((group) => ({
      key: String(group.dataset.boundaryKind || "").trim(),
      label: String(group.querySelector(":scope > strong")?.innerText || "").trim(),
      items: Array.from(group.querySelectorAll("[data-authored-fact-item]"))
        .map((item) => String(item.innerText || "").trim())
    })),
    deliveries: Array.from(node.querySelectorAll(".project-job-card")).map((card) => ({
      title: String(card.querySelector("h3")?.innerText || "").trim(),
      deliverable: String(card.querySelector(":scope > p")?.innerText || "").trim()
    }))
  };
}"""


def prove_authored_event_disclosure(root: Any, *, timeout_ms: int) -> tuple[Any, tuple[str, ...]]:
    """Read the closed contract, then prove native keyboard access to its evidence."""

    initial = root.evaluate(AUTHORED_STRUCTURE_EXPRESSION)
    if initial.get("first_path_details") != [
        {"native": True, "open": False, "summary": "Supporting details"}
    ]:
        return initial, ()  # The typed contract rejects the invalid initial disclosure.
    summary = root.locator('[data-authored-event-details] > summary')
    summary.focus(timeout=timeout_ms)
    summary.press("Enter", timeout=timeout_ms)
    opened = root.evaluate(AUTHORED_STRUCTURE_EXPRESSION)
    expected_details = [{"native": True, "open": True, "summary": "Supporting details"}]
    expected_evidence = [{**row, "visible": True} for row in initial["first_path_evidence"]]
    issues: list[str] = []
    if (opened.get("first_path_details") != expected_details
            or opened.get("first_path_evidence") != expected_evidence
            or opened.get("first_path") != initial.get("first_path")):
        issues.append("browser surface project supporting evidence is not visibly accessible by keyboard")
    if opened.get("first_path_details") == expected_details:
        summary.press("Space", timeout=timeout_ms)
    if root.evaluate(AUTHORED_STRUCTURE_EXPRESSION) != initial:
        issues.append("browser surface project supporting evidence did not close intact by keyboard")
    return initial, tuple(issues)

_GENERATED_TEXT_SUFFIXES = frozenset({".css", ".html", ".js", ".json", ".md", ".mmd", ".txt"})


def generated_tree_path_leak_issues(repo_root: Path) -> tuple[str, ...]:
    """Reject generated text that retains its simulation or prewrite root."""

    root = Path(repo_root).expanduser().resolve()
    generated_root = root / "odylith"
    if not generated_root.is_dir():
        return ("browser surface proof generated tree is unavailable",)
    root_tokens = tuple(dict.fromkeys((str(root), str(root).lstrip("/"), root.as_uri())))
    issues: list[str] = []
    for path in generated_root.rglob("*"):
        if not path.is_file() or path.is_symlink() or path.suffix.casefold() not in _GENERATED_TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if any(token and token in text for token in root_tokens):
            issues.append(
                f"generated text exposes its temporary repository root: {path.relative_to(root).as_posix()}"
            )
    return tuple(issues)


def story_rows_match_payload(
    rendered_rows: list[dict[str, Any]],
    payload_rows: list[dict[str, Any]],
    *,
    structured_slots: Iterable[str] = (),
) -> bool:
    """Compare rendered typed cards under browser whitespace rules."""

    if len(rendered_rows) != len(payload_rows):
        return False
    structured = {str(slot).strip() for slot in structured_slots if str(slot).strip()}
    for rendered, expected in zip(rendered_rows, payload_rows, strict=True):
        if str(rendered.get("label") or "").strip().casefold() != str(
            expected.get("label") or ""
        ).strip().casefold():
            return False
        if str(rendered.get("semantic_slot") or "").strip() != str(
            expected.get("semantic_slot") or ""
        ).strip():
            return False
        semantic_slot = str(expected.get("semantic_slot") or "").strip()
        if semantic_slot in structured:
            continue
        if _browser_visible_text(rendered.get("body")) != _browser_visible_text(expected.get("body")):
            return False
    return True


def project_state_assertion_issues(
    *,
    payload_origin: str,
    payload_prompt_count: int,
    empty_payload_prompts: int,
    rendered_prompt_count: int,
    has_prompt_grid: bool,
    has_blank_state: bool,
    has_implementation_prompts: bool,
    max_prompt_overflow: int,
    pane_overflow: int,
    rendered_story_body_count: int = 5,
    distinct_story_body_count: int = 5,
    clipped_text_count: int = 0,
    story_rows: Any = (),
    payload_story_rows: Any = (),
    authored_structure: Any = None,
    payload_authored_facts: Any = None,
) -> tuple[str, ...]:
    """Require persisted Project payload, layout, and exact authored-fact bindings."""

    issues: list[str] = []
    if payload_origin != AUTHORED_PROJECTION_ORIGIN:
        issues.append("browser surface project payload is not accepted greenfield project state")
    if payload_prompt_count < 5:
        issues.append("browser surface project payload exposes fewer than five implementation prompts")
    if empty_payload_prompts:
        issues.append("browser surface project payload contains empty implementation prompt text")
    if rendered_prompt_count < 5:
        issues.append("browser surface project rendered fewer than five implementation prompt cards")
    if not has_prompt_grid:
        issues.append("browser surface project did not render the implementation prompt grid")
    if has_blank_state:
        issues.append("browser surface project rendered the blank project state after commit-only create")
    if not has_implementation_prompts:
        issues.append("browser surface project did not render the expected implementation prompt labels")
    if max_prompt_overflow > 4:
        issues.append("browser surface project implementation prompt cards overflow their containers")
    if pane_overflow > 4:
        issues.append("browser surface project pane overflows horizontally")
    if rendered_story_body_count != 5:
        issues.append("browser surface project did not render all five Product Story bodies")
    if distinct_story_body_count != 5:
        issues.append("browser surface project repeats Product Story card bodies")
    rows = [row for row in story_rows if isinstance(row, dict)] if isinstance(story_rows, (list, tuple)) else []
    issues.extend(project_story_binding_issues(rows, authored_facts=payload_authored_facts))
    expected_rows = (
        [row for row in payload_story_rows if isinstance(row, dict)]
        if isinstance(payload_story_rows, (list, tuple))
        else []
    )
    structured_slots = (
        ("first_path", "product_boundary", "owned_capabilities")
        if isinstance(authored_structure, dict) and isinstance(payload_authored_facts, dict)
        else ()
    )
    if expected_rows and not story_rows_match_payload(rows, expected_rows, structured_slots=structured_slots):
        issues.append("browser surface project Product Story cards drifted from the sealed payload")
    if payload_origin == AUTHORED_PROJECTION_ORIGIN and (
        authored_structure is not None or payload_authored_facts is not None
    ):
        issues.extend(authored_structure_issues(authored_structure, payload_authored_facts))
    if clipped_text_count:
        issues.append("browser surface project clips visible text")
    return tuple(issues)


def project_story_binding_issues(
    rows: list[dict[str, Any]], *, authored_facts: Any = None
) -> tuple[str, ...]:
    """Check exact rendered card bindings without interpreting prose."""

    proof_label, proof_body = "Proof", None
    if authored_facts is not None:
        try:
            proof_label, proof_body = expected_proof_card(authored_facts)
        except ValueError as exc:
            return (f"greenfield Project Product Story has invalid proof authority: {exc}",)
    expected = {
        "user problem": ("User Problem", "user_problem"),
        "first path": ("First Path", "first_path"),
        "product boundary": ("Product Boundary", "product_boundary"),
        "proposed capabilities": ("Proposed Capabilities", "owned_capabilities"),
        proof_label.casefold(): (proof_label, "proof"),
    }
    issues: list[str] = []
    seen: set[str] = set()
    for row in rows:
        raw_label = str(row.get("label") or "").strip()
        label_key = raw_label.casefold()
        expected_row = expected.get(label_key)
        if expected_row is None:
            issues.append(f"greenfield Project Product Story card has an unexpected semantic label: `{raw_label}`")
            continue
        canonical_label, expected_slot = expected_row
        seen.add(label_key)
        actual_slot = str(row.get("semantic_slot") or "").strip()
        if actual_slot != expected_slot:
            issues.append(
                "greenfield Project Product Story card is bound to the wrong semantic slot: "
                f"`{canonical_label}` uses `{actual_slot}` instead of `{expected_slot}`"
            )
        body = str(row.get("body") or "").strip()
        if not body:
            issues.append(f"greenfield Project Product Story `{canonical_label}` card is empty")
        elif expected_slot == "proof" and proof_body is not None and (
            " ".join(body.split()) != " ".join(proof_body.split())
        ):
            issues.append("greenfield Project Product Story proof card drifted from typed authority")
    if rows:
        for key, (canonical_label, _slot) in expected.items():
            if key not in seen:
                issues.append(f"greenfield Project Product Story is missing its `{canonical_label}` card")
    return tuple(issues)


def _browser_visible_text(value: Any) -> str:
    """Apply only HTML-visible whitespace collapse; retain every content token."""

    return " ".join(str(value or "").split())


def expected_proof_card(authored_facts: Any) -> tuple[str, str]:
    """Select the sole proof label and body permitted by typed authority."""

    if not isinstance(authored_facts, dict):
        raise ValueError("Greenfield browser proof authority is unavailable")
    raw_events = authored_facts.get("first_path_relations")
    if not isinstance(raw_events, (list, tuple)) or not raw_events or any(
        not isinstance(row, dict)
        or not isinstance(row.get("visible_result_quote"), str)
        for row in raw_events
    ):
        raise ValueError("Greenfield browser proof authority has invalid source events")
    proof_boundary = authored_facts.get("proof_boundary")
    if not isinstance(proof_boundary, str) or (
        proof_boundary and not proof_boundary.strip()
    ):
        raise ValueError("Greenfield browser proof authority has an invalid proof boundary")
    proof_assumption = provisional_proof_assumption(
        authored_facts.get("assumptions", [])
    )
    require_provisional_proof_decision(authored_facts)
    visible_result = authored_facts.get("visible_result")
    if not isinstance(visible_result, str):
        raise ValueError("Greenfield browser proof authority has an invalid visible result")
    results = [row["visible_result_quote"] for row in raw_events if row["visible_result_quote"]]
    if proof_assumption:
        if results or visible_result:
            raise ValueError(
                "Greenfield provisional proof cannot carry a source result"
            )
        return "Proposed Proof Checkpoint", f"Assumption — {proof_assumption}"
    if len(results) != 1 or visible_result != results[0]:
        raise ValueError(
            "Greenfield source proof requires exactly one matching source result"
        )
    return "Observable result", proof_boundary


def authored_structure_issues(rendered: Any, authored_facts: Any) -> tuple[str, ...]:
    """Require rendered authored nodes to preserve typed fact count, order, and text."""

    if not isinstance(rendered, dict) or not isinstance(authored_facts, dict):
        return ("browser surface project authored fact structure is unavailable",)

    raw_events = authored_facts.get("source_event_relations" if authored_facts.get("authored_semantics_version") == "odylith.greenfield.authored-semantics.v19" else "first_path_relations")
    if not isinstance(raw_events, (list, tuple)):
        return ("browser surface project payload has no typed first-path relations",)
    if not raw_events or any(
        not isinstance(row, dict)
        or not isinstance(row.get("event_quote"), str) or not row["event_quote"].strip()
        or not isinstance(row.get("visible_result_quote"), str)
        for row in raw_events
    ):
        return ("browser surface project has invalid canonical source events",)
    event_orders = tuple(row.get("order") for row in raw_events)
    result_orders = [row.get("order") for row in raw_events if row["visible_result_quote"]]
    try:
        expected_proof_card(authored_facts)
    except ValueError as exc:
        return (f"browser surface project has invalid canonical proof authority: {exc}",)
    try:
        source_precedence = validate_source_precedence(
            authored_facts.get("source_precedence"), event_orders=event_orders,
            operational_constraints=authored_facts.get("operational_constraints"),
        )
        design = validate_provisional_design(
            authored_facts.get("provisional_design"), event_orders=event_orders,
            source_precedence=source_precedence,
            result_event_order=result_orders[0] if result_orders else None,
        )
    except ValueError as exc:
        return (f"browser surface project has invalid canonical provisional design: {exc}",)
    events_by_order = {row["order"]: row for row in raw_events}
    event_rows = [events_by_order[order] for order in design["first_run"]["event_orders"]]
    expected_events = [
        {
            "order": row["order"],
            "text": _browser_visible_text(row["event_quote"]),
            "quote_count": 1,
            "quote": _browser_visible_text(row["event_quote"]),
        }
        for row in event_rows
    ]
    issues: list[str] = []
    if rendered.get("first_path_details") != [
        {"native": True, "open": False, "summary": "Supporting details"}
    ]:
        issues.append("browser surface project first path requires one closed native supporting disclosure")
    expected_evidence = [
        {
            "order": row["order"], "labels": ["Actor", "Actor kind", "Source event"],
            "values": [_browser_visible_text(row["actor_fact_quote"]), row["actor_kind"],
                       _browser_visible_text(row["event_quote"])],
            "actor_count": 1, "actor": _browser_visible_text(row["actor_fact_quote"]),
            "in_disclosure": True, "visible": False,
        }
        for row in event_rows
    ]
    if rendered.get("first_path_evidence") != expected_evidence:
        issues.append("browser surface project supporting evidence does not preserve typed actor, kind, source and order")
    for surface in ("first_path",):
        actual = rendered.get(surface)
        if actual != expected_events:
            issues.append(
                f"browser surface project {surface.replace('_', ' ')} does not preserve typed event nodes"
            )
        if (
            rendered.get(f"{surface}_authority") != "provisional_design"
            or rendered.get(f"{surface}_label") != "Proposed first run:"
        ):
            issues.append(
                f"browser surface project {surface.replace('_', ' ')} lost its explicit proposed-first-run marker"
            )

    raw_human_actors = authored_facts.get("human_actors")
    human_actors = (
        [
            str(actor).strip()
            for actor in raw_human_actors
            if isinstance(actor, str) and actor.strip()
        ]
        if isinstance(raw_human_actors, (list, tuple))
        else []
    )
    expected_actors = [
        {"actor": _browser_visible_text(actor), "source_name": actor}
        for actor in human_actors
    ]
    if rendered.get("actors") != expected_actors:
        issues.append("browser surface project participants do not preserve all source-stated human names")

    expected_capabilities = [
        {
            "owner": _browser_visible_text(row["name"]),
            "responsibility": _browser_visible_text(row["responsibility"]),
        }
        for row in design["components"]
    ]
    if rendered.get("capabilities") != expected_capabilities:
        issues.append("browser surface project capability rows do not preserve canonical proposed responsibilities")
    if (
        rendered.get("capabilities_authority") != "provisional_design"
        or rendered.get("capabilities_label") != "Proposed capabilities"
    ):
        issues.append("browser surface project capabilities lost their explicit proposed-design marker")

    expected_boundary_groups = [{
        "key": "provisional_components",
        "label": "Proposed components:",
        "items": [_browser_visible_text(row["name"]) for row in design["components"]],
    }]
    for key, label, values in (
        ("source_product_systems", "Named systems:", authored_facts.get("internal_systems", ())),
        ("external_systems", "External systems:", authored_facts.get("external_systems", ())),
        ("non_goals", "Scope limits:", authored_facts.get("non_goals", ())),
    ):
        items = (
            [
                _browser_visible_text(value)
                for value in values
                if isinstance(value, str) and value.strip()
            ]
            if isinstance(values, (list, tuple))
            else []
        )
        if items:
            expected_boundary_groups.append({"key": key, "label": label, "items": items})
    if rendered.get("boundary_groups") != expected_boundary_groups:
        issues.append("browser surface project boundary groups conflate or alter proposed design and source context")
    expected_deliveries = [
        {"title": _browser_visible_text(row["title"]), "deliverable": _browser_visible_text(row["deliverable"])}
        for row in design["workstreams"]
    ]
    if rendered.get("deliveries") != expected_deliveries:
        issues.append("browser surface project delivery cards do not preserve canonical proposed deliverables")
    return tuple(issues)


def atlas_state_assertion_issues(
    *,
    diagram_count: int,
    stat_total_text: str,
    active_diagram: str,
    displayed_diagram: str,
    displayed_title: str,
    image_src: str,
    image_loaded: bool,
) -> tuple[str, ...]:
    """Require one selected Atlas item to be a loaded generated diagram."""

    issues: list[str] = []
    if diagram_count <= 0:
        issues.append("browser surface atlas rendered no generated diagram buttons")
    try:
        stat_total = max(0, int(str(stat_total_text or "").strip()))
    except ValueError:
        stat_total = 0
    if stat_total <= 0:
        issues.append("browser surface atlas rendered no generated diagram count")
    elif diagram_count > 0 and stat_total != diagram_count:
        issues.append("browser surface atlas generated diagram count disagrees with rendered list")
    active = str(active_diagram or "").strip()
    displayed = str(displayed_diagram or "").strip()
    if not active:
        issues.append("browser surface atlas has no active generated diagram")
    if not displayed:
        issues.append("browser surface atlas did not hydrate the selected diagram id")
    elif active and displayed.upper() != active.upper():
        issues.append("browser surface atlas selected diagram id disagrees with active list state")
    if len(str(displayed_title or "").strip().split()) < 2:
        issues.append("browser surface atlas did not hydrate a meaningful generated diagram title")
    parsed = urlparse(str(image_src or ""))
    if "/odylith/atlas/source/" not in (parsed.path or "") or not (parsed.path or "").endswith(
        (".svg", ".png")
    ):
        issues.append("browser surface atlas viewer did not load a generated diagram asset")
    if not image_loaded:
        issues.append("browser surface atlas generated diagram asset did not finish loading")
    return tuple(issues)


def atlas_diagram_coverage_issues(
    expected_diagrams: Iterable[str],
    visited_diagrams: Iterable[str],
) -> tuple[str, ...]:
    expected = tuple(str(value or "").strip() for value in expected_diagrams)
    visited = tuple(str(value or "").strip() for value in visited_diagrams)
    if expected and expected == visited and all(expected):
        return ()
    return ("browser surface atlas did not visit every emitted diagram in list order",)


def atlas_readability_assertion_issues(
    *,
    zoom_text: str,
    stage_tab_index: int,
    stage_focused: bool,
    displayed_diagram: str,
    expected_diagram: str,
    pan_input: str,
    pan_changed_transform: bool,
) -> tuple[str, ...]:
    """Require native-size reading and an input-appropriate pan interaction."""

    issues: list[str] = []
    if str(zoom_text or "").strip() != "Zoom 100%":
        issues.append("browser surface atlas diagram is not readable at native scale")
    input_token = str(pan_input or "").strip().casefold()
    if stage_tab_index != 0 or (input_token == "keyboard" and not stage_focused):
        issues.append("browser surface atlas native-size stage is not keyboard focused")
    if str(displayed_diagram or "").strip().upper() != str(expected_diagram or "").strip().upper():
        issues.append("browser surface atlas native-size reading changed diagram identity")
    if input_token not in {"keyboard", "touch-pointer"}:
        issues.append("browser surface atlas native-size proof has no supported interaction")
    elif not pan_changed_transform:
        issues.append(
            "browser surface atlas native-size stage is not touch draggable"
            if input_token == "touch-pointer"
            else "browser surface atlas native-size stage is not keyboard pannable"
        )
    return tuple(issues)


def atlas_degraded_state_assertion_issues(
    *,
    image_src: str,
    image_loaded: bool,
    fallback_applied: bool,
) -> tuple[str, ...]:
    parsed = urlparse(str(image_src or ""))
    if (
        image_loaded
        and fallback_applied
        and "/odylith/atlas/source/" in (parsed.path or "")
        and (parsed.path or "").endswith(".png")
    ):
        return ()
    return ("browser surface atlas degraded SVG did not recover with its readable PNG asset",)


def atlas_error_state_assertion_issues(
    *,
    alert_text: str,
    alert_role: str,
    alert_visible: bool,
    image_hidden: bool,
) -> tuple[str, ...]:
    expected_actions = ("prev", "next", "summary", "source links")
    normalized = str(alert_text or "").strip().casefold()
    if (
        alert_visible
        and image_hidden
        and str(alert_role or "").strip().casefold() == "alert"
        and all(action in normalized for action in expected_actions)
    ):
        return ()
    return ("browser surface atlas asset failure does not expose accessible recovery guidance",)


__all__ = [
    "AUTHORED_STRUCTURE_EXPRESSION",
    "atlas_degraded_state_assertion_issues",
    "atlas_diagram_coverage_issues",
    "atlas_error_state_assertion_issues",
    "atlas_readability_assertion_issues",
    "atlas_state_assertion_issues",
    "authored_structure_issues",
    "expected_proof_card",
    "generated_tree_path_leak_issues",
    "prove_authored_event_disclosure",
    "project_state_assertion_issues",
    "project_story_binding_issues",
    "story_rows_match_payload",
]

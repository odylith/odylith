"""Searchable agent-cheatsheet drawer content for the Odylith dashboard."""

from __future__ import annotations

import html
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentCheatsheetCard:
    card_id: str
    category_key: str
    category_label: str
    title: str
    summary: str
    agent_prompt: str
    cli_command: str
    secondary_label: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class AgentCheatsheetState:
    title: str
    note: str
    search_placeholder: str
    cards: tuple[AgentCheatsheetCard, ...]


def _slug(value: Any) -> str:
    token = str(value or "").strip().lower()
    token = re.sub(r"[^a-z0-9]+", "-", token)
    token = token.strip("-")
    return token or "general"


def _normalize_tags(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    seen: set[str] = set()
    tags: list[str] = []
    for raw_item in value:
        tag = str(raw_item or "").strip()
        if not tag:
            continue
        lowered = tag.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tags.append(tag)
    return tuple(tags)


def _card(
    *,
    card_id: str,
    category: str,
    title: str,
    summary: str,
    prompt: str,
    command: str,
    tags: Sequence[str],
    secondary_label: str = "CLI equivalent",
) -> AgentCheatsheetCard:
    return AgentCheatsheetCard(
        card_id=card_id,
        category_key=_slug(category),
        category_label=category,
        title=title,
        summary=summary,
        agent_prompt=prompt,
        cli_command=command,
        secondary_label=secondary_label,
        tags=_normalize_tags(tags),
    )


def _default_cards() -> tuple[AgentCheatsheetCard, ...]:
    return (
        _card(
            card_id="create-radar-item",
            category="Create",
            title="Create a Radar backlog item",
            summary="Start with a fully formed workstream brief so Odylith can create the backlog record without guessing the title, goal, dependencies, or success bar.",
            prompt=(
                'Create a Radar backlog item titled "Payments boundary cleanup". '
                "Make it about clarifying that checkout can call payments but does not own payment state. "
                "Include goals to update the Registry component boundary, refresh the Atlas diagram, and leave a Compass note once the change lands. "
                "Add success criteria for one Registry update, one Atlas refresh, and one validation pass before closeout."
            ),
            command="odylith/index.html?tab=radar",
            secondary_label="Shell route",
            tags=("radar", "create", "backlog", "workstream"),
        ),
        _card(
            card_id="create-registry-component",
            category="Create",
            title="Create a Registry component",
            summary="Use a concrete component contract so Odylith can capture purpose, ownership, dependencies, and boundaries in one pass.",
            prompt=(
                'Create a Registry component named "payments". '
                "Set its purpose to owning payment intent, provider routing, capture and refund state, and webhook reconciliation. "
                "Call out that checkout and orders depend on it, but payment state lives here. "
                "Include key interfaces for checkout requests, provider webhooks, and order-status updates."
            ),
            command="odylith/index.html?tab=registry",
            secondary_label="Shell route",
            tags=("registry", "create", "component", "ownership"),
        ),
        _card(
            card_id="create-atlas-diagram",
            category="Create",
            title="Create an Atlas diagram",
            summary="Describe the architecture you want to see so Odylith can draft a useful diagram instead of a vague map stub.",
            prompt=(
                'Create an Atlas diagram for the payments component. '
                "Show checkout sending payment requests to payments, payments calling the external PSP, PSP webhooks returning into payments, and payments publishing status back to orders. "
                "Mark the PSP as an external boundary and label webhooks as inbound traffic."
            ),
            command="odylith/index.html?tab=atlas",
            secondary_label="Shell route",
            tags=("atlas", "create", "diagram", "topology"),
        ),
        _card(
            card_id="create-casebook-bug",
            category="Create",
            title="Create a Casebook bug",
            summary="Give Odylith the failure signature, suspected area, and first checks so the bug record starts with actionable debugging context.",
            prompt=(
                'Create a Casebook bug titled "Duplicate payment capture after webhook retry". '
                "Record the symptom as two captures for one order after a delayed provider retry. "
                "Mark the suspected area as webhook idempotency in payments. "
                "Add first checks for provider event ids, retry logs, settlement records, and the exact order id that reproduced it."
            ),
            command="odylith/index.html?tab=casebook",
            secondary_label="Shell route",
            tags=("casebook", "create", "bug", "debugging"),
        ),
        _card(
            card_id="plan-release-target",
            category="Planning",
            title="Release planning: pick the ship target",
            summary="Use release planning when the question is which release one workstream should ship in. Example: add `B-067` to `0.1.11`. This does not decide umbrella sequencing or wave order.",
            prompt="Add B-067 to release 0.1.11.",
            command="odylith release add B-067 0.1.11 --repo-root .",
            tags=("release", "planning", "ship-target", "0.1.11"),
        ),
        _card(
            card_id="plan-program-waves",
            category="Planning",
            title="Program/wave planning: sequence umbrella execution",
            summary="Use program/wave planning when the question is how one umbrella effort should execute. Start with `odylith program next` so the agent gets one exact next command instead of hand-editing wave JSON. This does not choose the release; the same workstream can still target `0.1.11` separately.",
            prompt=(
                "For umbrella workstream B-021, create a 3-wave execution program. "
                "Make W1 the foundation wave, W2 the rollout wave, and W3 the hardening wave. "
                "Put B-045 in W1, carry B-048 into W2, and keep the gates tied to the bound plans."
            ),
            command="odylith program next B-021 --repo-root .",
            secondary_label="CLI",
            tags=("program", "waves", "umbrella", "execution-order"),
        ),
        _card(
            card_id="self-host-posture",
            category="Validate",
            title="Check self-host posture",
            summary="Verify whether this product repo is pinned or detached before you trust release or benchmark proof.",
            prompt="Check self-host posture before release proof.",
            command="odylith validate self-host-posture --repo-root .",
            tags=("self-host", "lane", "release-proof"),
        ),
        _card(
            card_id="surface-shell",
            category="Surfaces",
            title="Odylith Dashboard",
            summary="Your command center for Radar, Compass, Atlas, Registry, and Casebook in one place.",
            prompt="Open the Odylith dashboard.",
            command="odylith/index.html",
            secondary_label="Shell route",
            tags=("dashboard", "overview", "tabs"),
        ),
        _card(
            card_id="surface-radar",
            category="Surfaces",
            title="Radar",
            summary="See what should move next, why it matters, and which workstream deserves focus now.",
            prompt="Open Radar for workstream B-025.",
            command="odylith/index.html?tab=radar&workstream=B-025",
            secondary_label="Shell route",
            tags=("radar", "backlog", "workstream"),
        ),
        _card(
            card_id="surface-compass",
            category="Surfaces",
            title="Compass",
            summary="See live execution posture, timeline evidence, and the risks that can still slow delivery.",
            prompt="Open Compass for workstream B-025.",
            command="odylith/index.html?tab=compass&workstream=B-025",
            secondary_label="Shell route",
            tags=("compass", "timeline", "risks"),
        ),
        _card(
            card_id="surface-registry",
            category="Surfaces",
            title="Registry",
            summary="See component truth, ownership, and the contracts the repo is actually shipping.",
            prompt="Open Registry for the payments component.",
            command="odylith/index.html?tab=registry&component=payments",
            secondary_label="Shell route",
            tags=("registry", "components", "ownership"),
        ),
        _card(
            card_id="surface-atlas",
            category="Surfaces",
            title="Atlas",
            summary="See the architecture in one glance, jump to the right map, and catch stale diagrams before they mislead you.",
            prompt="Open Atlas for the payments component.",
            command="odylith/index.html?tab=atlas&component=payments",
            secondary_label="Shell route",
            tags=("atlas", "diagrams", "topology"),
        ),
        _card(
            card_id="surface-casebook",
            category="Surfaces",
            title="Casebook",
            summary="See repeat failures, proven fixes, and the bug history you can reuse instead of rediscovering.",
            prompt="Open Casebook for bug CB-001.",
            command="odylith/index.html?tab=casebook&bug=CB-001",
            secondary_label="Shell route",
            tags=("casebook", "bugs", "history"),
        ),
        _card(
            card_id="start-one-code-path",
            category="Start",
            title="Start from one real path",
            summary="Give Odylith one real path and it builds the right context around it before the work widens.",
            prompt="Start Odylith and ground me in src/payments/service.py.",
            command="odylith start --repo-root .",
            tags=("grounding", "bootstrap", "safe-first"),
        ),
        _card(
            card_id="narrow-to-slice",
            category="Start",
            title="Open a known component or workstream",
            summary="Use this when you already know the name, like the payments component or workstream B-025, and want the files, plans, bugs, and diagrams tied to it.",
            prompt="Show me the files and records for the payments component.",
            command="odylith context --repo-root . payments",
            tags=("context", "component", "workstream", "scope"),
        ),
        _card(
            card_id="search-governed-memory",
            category="Start",
            title="Search governed memory",
            summary="Search repo memory for the exact phrase, posture, or proof trail you want to recover fast.",
            prompt="Search Odylith for payment webhook idempotency.",
            command='odylith query --repo-root . "payment webhook idempotency"',
            tags=("query", "memory", "search"),
        ),
        _card(
            card_id="refresh-all-surfaces",
            category="Refresh",
            title="Refresh the full dashboard",
            summary="Rebuild the Odylith Dashboard from current repo truth in one pass.",
            prompt="Refresh the Odylith dashboard.",
            command="odylith dashboard refresh --repo-root . --surfaces tooling_shell,radar,compass,atlas,registry,casebook",
            tags=("dashboard", "render", "shell"),
        ),
        _card(
            card_id="refresh-compass-now",
            category="Refresh",
            title="Refresh Compass now",
            summary="Run the quick cache-first Compass rerender when you want updated runtime artifacts without waiting on brief settlement.",
            prompt="Refresh Compass now.",
            command="odylith compass refresh --repo-root .",
            tags=("compass", "refresh", "runtime"),
        ),
        _card(
            card_id="deep-refresh-compass",
            category="Refresh",
            title="Deep-refresh Compass",
            summary="Use the deep refresh Compass rerender when you want the same runtime refresh to wait for standup-brief settlement too.",
            prompt="Deep refresh Compass and wait for brief settlement.",
            command="odylith compass deep-refresh --repo-root .",
            tags=("compass", "refresh", "deep refresh", "brief", "settled"),
        ),
        _card(
            card_id="watch-transactions",
            category="Refresh",
            title="Keep Compass warm",
            summary="Run the change-driven watcher so Compass refreshes only when repo truth actually moves.",
            prompt="Start the Compass watcher and keep it change-driven while you work.",
            command="odylith compass watch-transactions --repo-root .",
            tags=("watch", "near-real-time", "refresh"),
        ),
        _card(
            card_id="refresh-atlas-with-sync",
            category="Refresh",
            title="Refresh Atlas maps",
            summary="Pull stale diagrams forward and rerender Atlas when the architecture story changed.",
            prompt="Refresh Atlas with diagram sync.",
            command="odylith dashboard refresh --repo-root . --surfaces atlas --atlas-sync",
            tags=("atlas", "mermaid", "diagram"),
        ),
        _card(
            card_id="edit-radar-update",
            category="Edit",
            title="Edit a Radar item",
            summary="Sharpen the scope, language, or success bar when a workstream needs a stronger brief.",
            prompt="Update Radar item B-001.",
            command="odylith/index.html?tab=radar",
            secondary_label="Shell route",
            tags=("radar", "edit", "update", "workstream"),
        ),
        _card(
            card_id="edit-radar-delete",
            category="Edit",
            title="Delete a Radar item",
            summary="Retire the wrong backlog record when the workstream should not stay on the board.",
            prompt="Delete Radar item B-001.",
            command="odylith/index.html?tab=radar",
            secondary_label="Shell route",
            tags=("radar", "delete", "drop", "cleanup"),
        ),
        _card(
            card_id="edit-registry-update",
            category="Edit",
            title="Edit a Registry component",
            summary="Tighten ownership, boundaries, or purpose when a component exists but the contract still feels soft.",
            prompt='Update Registry component "payments".',
            command="odylith/index.html?tab=registry",
            secondary_label="Shell route",
            tags=("registry", "edit", "update", "component"),
        ),
        _card(
            card_id="edit-registry-delete",
            category="Edit",
            title="Delete a Registry component",
            summary="Remove the wrong boundary when the component should live elsewhere or not exist at all.",
            prompt='Delete Registry component "payments".',
            command="odylith/index.html?tab=registry",
            secondary_label="Shell route",
            tags=("registry", "delete", "drop", "component"),
        ),
        _card(
            card_id="atlas-map-slice",
            category="Atlas",
            title="Map a component or workstream in Atlas",
            summary="Ask Atlas for the fastest boundary map around a component, path, or workstream you are touching.",
            prompt="Map the payments component in Atlas.",
            command="odylith/index.html?tab=atlas",
            secondary_label="Shell route",
            tags=("atlas", "boundary-map", "topology"),
        ),
        _card(
            card_id="atlas-find-best-diagram",
            category="Atlas",
            title="Find the best diagram for a workstream",
            summary="Jump straight to the map that explains the workstream without hunting through the full catalog.",
            prompt="Find the Atlas diagram for workstream B-025.",
            command="odylith/index.html?tab=atlas&workstream=B-025",
            secondary_label="Shell route",
            tags=("atlas", "diagram-hunt", "workstream"),
        ),
        _card(
            card_id="atlas-stale-gaps",
            category="Atlas",
            title="Find stale or missing diagram coverage",
            summary="Spot stale maps, missing topology coverage, and the places where architecture proof is thin.",
            prompt="Find stale Atlas diagrams.",
            command="odylith dashboard refresh --repo-root . --surfaces atlas --atlas-sync",
            tags=("atlas", "stale", "coverage"),
        ),
        _card(
            card_id="atlas-open-known-diagram",
            category="Atlas",
            title="Open a known diagram directly",
            summary="Jump straight to a known map when you already have the diagram id.",
            prompt="Open Atlas diagram D-002.",
            command="odylith/index.html?tab=atlas&diagram=D-002",
            secondary_label="Shell route",
            tags=("atlas", "diagram-id", "direct-open"),
        ),
        _card(
            card_id="edit-atlas-update",
            category="Edit",
            title="Edit an Atlas diagram",
            summary="Refresh a known map when the topology shifted and the current view is stale or misleading.",
            prompt="Update Atlas diagram D-002.",
            command="odylith/index.html?tab=atlas",
            secondary_label="Shell route",
            tags=("atlas", "edit", "update", "diagram"),
        ),
        _card(
            card_id="edit-atlas-delete",
            category="Edit",
            title="Delete an Atlas diagram",
            summary="Retire a map when the catalog points at dead architecture or the diagram should no longer ship.",
            prompt="Delete Atlas diagram D-002.",
            command="odylith/index.html?tab=atlas",
            secondary_label="Shell route",
            tags=("atlas", "delete", "drop", "diagram"),
        ),
        _card(
            card_id="edit-casebook-update",
            category="Edit",
            title="Edit a Casebook bug",
            summary="Sharpen symptoms, evidence, or fix notes when the record exists but still feels thin.",
            prompt="Update Casebook bug CB-001.",
            command="odylith/index.html?tab=casebook",
            secondary_label="Shell route",
            tags=("casebook", "edit", "update", "bug"),
        ),
        _card(
            card_id="edit-casebook-delete",
            category="Edit",
            title="Delete a Casebook bug",
            summary="Remove the wrong bug record when the issue was duplicated, misfiled, or no longer belongs here.",
            prompt="Delete Casebook bug CB-001.",
            command="odylith/index.html?tab=casebook",
            secondary_label="Shell route",
            tags=("casebook", "delete", "drop", "bug"),
        ),
        _card(
            card_id="compass-implementation-update",
            category="Compass",
            title="Log an implementation update to Compass",
            summary="Turn shipped work into visible execution proof the next session can trust.",
            prompt='Log this implementation to Compass: "Updated payments component boundaries."',
            command='odylith compass update --repo-root . --implementation "Implemented the shell cheatsheet drawer."',
            tags=("timeline", "implementation", "narrative"),
        ),
        _card(
            card_id="compass-decision-log",
            category="Compass",
            title="Log a decision in the timeline audit",
            summary="Capture the architectural call that future audits and handoffs still need to see.",
            prompt='Log this decision to Compass: "Clarified payments component boundaries."',
            command='odylith compass log --repo-root . --kind decision --summary "Locked the shell to short-prompt cheatsheet cards."',
            tags=("decision", "audit", "history"),
        ),
        _card(
            card_id="compass-state-forward",
            category="Compass",
            title="Carry current execution state forward",
            summary="Leave the next session a clean handoff instead of making it reconstruct your current component or workstream from scratch.",
            prompt='Carry this state forward in Compass: "Working the payments component docs and Atlas map."',
            command='odylith compass update --repo-root . --statement "Working the shell cheatsheet UX and Atlas guidance."',
            tags=("handoff", "statement", "session"),
        ),
        _card(
            card_id="edit-notes-create",
            category="Edit",
            title="Add a developer note",
            summary="Keep a short local truth visible between sessions without burying it in chat history.",
            prompt='Create a developer note titled "Compass refresh drift".',
            command="odylith/index.html",
            secondary_label="Shell route",
            tags=("developer-notes", "shell", "create", "add"),
        ),
        _card(
            card_id="edit-notes-update",
            category="Edit",
            title="Edit a developer note",
            summary="Refresh the note when the guidance changed but the record should stay the same.",
            prompt="Update developer note N-001.",
            command="odylith/index.html",
            secondary_label="Shell route",
            tags=("developer-notes", "shell", "edit", "update"),
        ),
        _card(
            card_id="edit-notes-delete",
            category="Edit",
            title="Delete a developer note",
            summary="Clear a stale note when the drawer is carrying old guidance into the next session.",
            prompt="Delete developer note N-001.",
            command="odylith/index.html",
            secondary_label="Shell route",
            tags=("developer-notes", "shell", "delete", "drop"),
        ),
        _card(
            card_id="sync-governance",
            category="Validate",
            title="Sync all governance surfaces",
            summary="Run the full governance pipeline — validates contracts, renders all surfaces, mirrors the bundle.",
            prompt="Sync the governance surfaces.",
            command="odylith sync --repo-root . --force",
            tags=("sync", "governance", "surfaces"),
        ),
        _card(
            card_id="validate-backlog",
            category="Validate",
            title="Validate the backlog",
            summary="Check workstreams for schema, traceability, plan bindings, and queue posture.",
            prompt="Validate the backlog.",
            command="odylith validate backlog-contract --repo-root .",
            tags=("validate", "backlog", "radar"),
        ),
        _card(
            card_id="validate-registry",
            category="Validate",
            title="Validate the registry",
            summary="Check components for shape, linkage, forensics, and policy.",
            prompt="Validate the registry.",
            command="odylith validate component-registry --repo-root .",
            tags=("validate", "registry", "components"),
        ),
        _card(
            card_id="plan-binding-check",
            category="Validate",
            title="Validate plan and workstream bindings",
            summary="Check that the implementation still points at the right governed records before you close out.",
            prompt="Validate plan bindings before closing workstream B-025.",
            command="odylith validate plan-workstream-binding --repo-root .",
            tags=("plan", "binding", "governance"),
        ),
        _card(
            card_id="trick-critical-risks",
            category="Tricks",
            title="Show the highest critical risks",
            summary="Jump straight to the risks most likely to slow or block delivery.",
            prompt="Show the critical risks for workstream B-025.",
            command="odylith/index.html?tab=compass&workstream=B-025",
            secondary_label="Shell route",
            tags=("risks", "compass", "triage"),
        ),
        _card(
            card_id="trick-next-workstream",
            category="Tricks",
            title="Ask what to touch next",
            summary="Let Odylith rank the next high-leverage move instead of making you scan the board by hand.",
            prompt="What should I work on next after workstream B-025?",
            command="odylith/index.html?tab=radar&workstream=B-025",
            secondary_label="Shell route",
            tags=("radar", "priority", "next-step"),
        ),
        _card(
            card_id="trick-bug-trail",
            category="Tricks",
            title="Check the bug trail first",
            summary="Jump to the nearest named failure and reuse what Odylith already learned before you debug from zero.",
            prompt="Open the bug trail for bug CB-001.",
            command="odylith/index.html?tab=casebook&bug=CB-001",
            secondary_label="Shell route",
            tags=("casebook", "history", "debugging"),
        ),
    )


def _coerce_card(raw_card: Mapping[str, Any], index: int) -> AgentCheatsheetCard | None:
    title = str(raw_card.get("title", "")).strip()
    summary = str(raw_card.get("summary", "")).strip()
    agent_prompt = str(raw_card.get("agent_prompt", "")).strip()
    cli_command = str(raw_card.get("cli_command", "")).strip()
    category_label = str(raw_card.get("category", "")).strip() or "General"
    secondary_label = str(raw_card.get("secondary_label", "")).strip() or "CLI equivalent"
    if not all((title, summary, agent_prompt, cli_command)):
        return None
    return AgentCheatsheetCard(
        card_id=str(raw_card.get("card_id", "")).strip() or f"card-{index:02d}",
        category_key=_slug(raw_card.get("category_key", category_label)),
        category_label=category_label,
        title=title,
        summary=summary,
        agent_prompt=agent_prompt,
        cli_command=cli_command,
        secondary_label=secondary_label,
        tags=_normalize_tags(raw_card.get("tags")),
    )


def build_agent_cheatsheet_state(payload: Mapping[str, Any]) -> AgentCheatsheetState:
    raw_state = dict(payload.get("agent_cheatsheet", {})) if isinstance(payload.get("agent_cheatsheet"), Mapping) else {}
    raw_cards = raw_state.get("cards")
    cards: list[AgentCheatsheetCard] = []
    if isinstance(raw_cards, Sequence) and not isinstance(raw_cards, (str, bytes, bytearray)):
        for index, raw_card in enumerate(raw_cards, start=1):
            if not isinstance(raw_card, Mapping):
                continue
            card = _coerce_card(raw_card, index)
            if card is not None:
                cards.append(card)
    if not cards:
        cards = list(_default_cards())
    return AgentCheatsheetState(
        title=str(raw_state.get("title", "")).strip() or "Odylith Dashboard Cheatsheet",
        note=(
            str(raw_state.get("note", "")).strip()
            or "Release planning picks the ship target for one workstream, like `B-067 -> 0.1.11`. Program/wave planning picks execution order under one umbrella, like `B-021 -> W1, W2, W3`. A workstream can belong to both. Replace the names and ids; when a prompt names a component like payments or a workstream id like B-025, Odylith scopes to the tied files and governed records."
        ),
        search_placeholder=(
            str(raw_state.get("search_placeholder", "")).strip()
            or "Search a surface, action, prompt, route, CLI, or Atlas win..."
        ),
        cards=tuple(cards),
    )


def _card_search_text(card: AgentCheatsheetCard) -> str:
    parts = (
        card.category_label,
        card.title,
        card.summary,
        card.agent_prompt,
        card.cli_command,
        card.secondary_label,
        " ".join(card.tags),
    )
    return " ".join(part.strip() for part in parts if part.strip()).lower()


def _secondary_copy_label(label: str) -> str:
    lowered = str(label or "").strip().lower()
    return "Copy route" if "route" in lowered else "Copy CLI"


def render_agent_cheatsheet_html(payload: Mapping[str, Any]) -> str:
    state = build_agent_cheatsheet_state(payload)
    counts = Counter(card.category_key for card in state.cards)
    labels = {card.category_key: card.category_label for card in state.cards}
    filter_order = tuple(dict.fromkeys(card.category_key for card in state.cards))
    filter_buttons = [
        (
            '<button type="button" class="cheatsheet-filter-chip is-active" '
            'data-cheatsheet-filter="all" data-cheatsheet-filter-label="All" aria-pressed="true">'
            f'<span>All</span><strong>{len(state.cards)}</strong>'
            "</button>"
        )
    ]
    for category_key in filter_order:
        filter_buttons.append(
            (
                '<button type="button" class="cheatsheet-filter-chip" '
                f'data-cheatsheet-filter="{html.escape(category_key, quote=True)}" '
                f'data-cheatsheet-filter-label="{html.escape(labels.get(category_key, "General"), quote=True)}" '
                'aria-pressed="false">'
                f'<span>{html.escape(labels.get(category_key, "General"))}</span><strong>{counts.get(category_key, 0)}</strong>'
                "</button>"
            )
        )

    cards_html = []
    for card in state.cards:
        tags_html = "".join(
            f'<span class="cheatsheet-tag">{html.escape(tag)}</span>'
            for tag in card.tags
        )
        cards_html.append(
            (
                '<article class="cheatsheet-card" '
                f'data-cheatsheet-card="true" '
                f'data-cheatsheet-category="{html.escape(card.category_key, quote=True)}" '
                f'data-cheatsheet-category-label="{html.escape(card.category_label, quote=True)}" '
                f'data-search-text="{html.escape(_card_search_text(card), quote=True)}">'
                '<div class="cheatsheet-card-head">'
                f'<span class="cheatsheet-card-category">{html.escape(card.category_label)}</span>'
                f'<div class="cheatsheet-tag-row">{tags_html}</div>'
                "</div>"
                f'<h3 class="cheatsheet-card-title">{html.escape(card.title)}</h3>'
                f'<p class="cheatsheet-card-summary">{html.escape(card.summary)}</p>'
                '<section class="cheatsheet-command-section">'
                '<p class="cheatsheet-command-label">Example prompt</p>'
                f'<pre class="cheatsheet-command-block"><code>{html.escape(card.agent_prompt)}</code></pre>'
                "</section>"
                '<section class="cheatsheet-command-section">'
                f'<p class="cheatsheet-command-label">{html.escape(card.secondary_label)}</p>'
                f'<pre class="cheatsheet-command-block cheatsheet-command-block-cli"><code>{html.escape(card.cli_command)}</code></pre>'
                "</section>"
                '<div class="cheatsheet-card-actions">'
                '<button type="button" class="brief-close cheatsheet-copy-button" '
                f'data-cheatsheet-copy-button="true" data-copy-text="{html.escape(card.agent_prompt, quote=True)}" '
                f'data-copy-success="{html.escape("Prompt copied.", quote=True)}">Copy prompt</button>'
                '<button type="button" class="brief-close cheatsheet-copy-button" '
                f'data-cheatsheet-copy-button="true" data-copy-text="{html.escape(card.cli_command, quote=True)}" '
                f'data-copy-success="{html.escape(f"{card.secondary_label} copied.", quote=True)}">{html.escape(_secondary_copy_label(card.secondary_label))}</button>'
                "</div>"
                "</article>"
            )
        )

    return (
        '<section class="agent-cheatsheet-shell" data-agent-cheatsheet="true">'
        '<div class="agent-cheatsheet-toolbar">'
        '<div class="agent-cheatsheet-toolbar-copy">'
        '<p class="agent-cheatsheet-kicker">Prompt + CLI quick path</p>'
        f'<p id="agentCheatsheetResults" class="agent-cheatsheet-results" aria-live="polite">{len(state.cards)} workflows ready</p>'
        "</div>"
        '<label class="agent-cheatsheet-search" for="agentCheatsheetSearch">'
        '<span class="agent-cheatsheet-search-label">Search workflows</span>'
        f'<input id="agentCheatsheetSearch" class="agent-cheatsheet-search-input" data-cheatsheet-search="true" type="search" placeholder="{html.escape(state.search_placeholder, quote=True)}" autocomplete="off" spellcheck="false" />'
        "</label>"
        f'<p id="agentCheatsheetCopyStatus" class="agent-cheatsheet-copy-status" aria-live="polite">{html.escape(state.note)}</p>'
        f'<div class="agent-cheatsheet-filter-row">{"".join(filter_buttons)}</div>'
        "</div>"
        f'<div id="agentCheatsheetCardList" class="agent-cheatsheet-card-list">{"".join(cards_html)}</div>'
        "</section>"
    )

"""Reusable tooling-shell routing and proof-link helpers.

These helpers are shared by shell-adjacent renderers and reasoning surfaces so
route semantics stay consistent without leaving link logic stranded inside one
dashboard renderer.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from odylith.runtime.governance import operator_readout
from odylith.runtime.surfaces import surface_path_helpers

_WORKSTREAM_RE = re.compile(r"\bB-\d{3,}\b")
_DIAGRAM_RE = re.compile(r"\bD-\d{3,}\b")
_PLAN_RE = re.compile(r"\bodylith/technical-plans/(?:in-progress|done/[0-9]{4}-[0-9]{2}|done/legacy)/[A-Za-z0-9._/\-]+\.md\b")
_SURFACE_RE = re.compile(r"\b(?:Registry|Casebook|Radar|Atlas|Compass)\b")
_ASSET_RE = re.compile(
    rf"{_PLAN_RE.pattern}|{_WORKSTREAM_RE.pattern}|{_DIAGRAM_RE.pattern}|{_SURFACE_RE.pattern}"
)
_SURFACE_TAB_MAP = {
    "Registry": "registry",
    "Casebook": "casebook",
    "Radar": "radar",
    "Atlas": "atlas",
    "Compass": "compass",
}


def shell_href(
    *,
    tab: str,
    workstream: str = "",
    component: str = "",
    diagram: str = "",
    bug: str = "",
    severity: str = "",
    status: str = "",
    view: str = "",
) -> str:
    """Return a tooling-shell relative href preserving per-surface query rules."""

    query: list[tuple[str, str]] = [("tab", str(tab).strip().lower() or "radar")]
    normalized_tab = query[0][1]
    if normalized_tab == "compass" and workstream:
        query.append(("scope", workstream))
    elif normalized_tab == "registry" and component:
        query.append(("component", component))
    elif normalized_tab == "casebook":
        if bug:
            query.append(("bug", bug))
        if severity:
            query.append(("severity", severity))
        if status:
            query.append(("status", status))
    elif workstream:
        query.append(("workstream", workstream))
    if normalized_tab == "radar" and str(view or "").strip():
        query.append(("view", str(view).strip()))
    if diagram:
        query.append(("diagram", diagram))
    token = urlencode(query)
    return f"?{token}" if token else ""


def radar_workstream_href(workstream: str, *, view: str = "") -> str:
    """Return the canonical shell route for one Radar workstream selection."""

    return shell_href(tab="radar", workstream=workstream, view=view)


def scope_lookup(
    source: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    scopes_key: str = "scopes",
) -> dict[str, dict[str, Any]]:
    """Normalize scope rows into a lookup keyed by `scope_key`."""

    rows = source.get(scopes_key, []) if isinstance(source, Mapping) else source
    if not isinstance(rows, Sequence):
        return {}
    return {
        str(row.get("scope_key", "")).strip(): dict(row)
        for row in rows
        if isinstance(row, Mapping) and str(row.get("scope_key", "")).strip()
    }


def _linked_tokens(evidence: Mapping[str, Any], key: str) -> list[str]:
    values = evidence.get(key, [])
    if not isinstance(values, Sequence):
        return []
    return [str(token).strip() for token in values if str(token).strip()]


def scope_href(scope_key: str, scope_lookup_map: Mapping[str, Mapping[str, Any]]) -> str:
    """Return the shell route for one delivery-intelligence scope key."""

    row = scope_lookup_map.get(str(scope_key or "").strip())
    if not isinstance(row, Mapping):
        return ""
    scope_type = str(row.get("scope_type", "")).strip().lower()
    scope_id = str(row.get("scope_id", "")).strip()
    evidence = row.get("evidence_context", {}) if isinstance(row.get("evidence_context"), Mapping) else {}
    linked_workstreams = _linked_tokens(evidence, "linked_workstreams")
    linked_components = _linked_tokens(evidence, "linked_components")
    linked_diagrams = _linked_tokens(evidence, "linked_diagrams")
    first_workstream = linked_workstreams[0] if linked_workstreams else ""
    first_component = linked_components[0] if linked_components else ""
    first_diagram = linked_diagrams[0] if linked_diagrams else ""
    if scope_type == "workstream":
        return shell_href(tab="radar", workstream=scope_id)
    if scope_type == "component":
        return shell_href(tab="registry", component=scope_id or first_component)
    if scope_type == "diagram":
        return shell_href(tab="atlas", workstream=first_workstream, diagram=scope_id or first_diagram)
    if scope_type != "surface":
        return ""

    surface_id = scope_id.lower()
    if surface_id == "atlas":
        return shell_href(tab="atlas", workstream=first_workstream, diagram=first_diagram)
    if surface_id == "compass":
        return shell_href(tab="compass", workstream=first_workstream)
    if surface_id == "registry":
        return shell_href(tab="registry", component=first_component)
    if surface_id == "casebook":
        return shell_href(tab="casebook")
    if surface_id == "radar":
        return shell_href(tab="radar", workstream=first_workstream)
    return ""


def surface_href(
    label: str,
    *,
    workstream: str = "",
    component: str = "",
    diagram: str = "",
) -> str:
    """Return the shell route for one named governed surface."""

    tab = _SURFACE_TAB_MAP.get(str(label).strip())
    if not tab:
        return ""
    if tab == "atlas":
        return shell_href(tab=tab, workstream=workstream, diagram=diagram)
    if tab == "compass":
        return shell_href(tab=tab, workstream=workstream)
    if tab == "registry":
        return shell_href(tab=tab, component=component)
    if tab == "casebook":
        return shell_href(tab=tab)
    return shell_href(tab=tab, workstream=workstream)


def _relative_href(output_path: Path, target: Path) -> str:
    return surface_path_helpers.relative_href(output_path=output_path, target=target)


def linkify_shell_text(
    text: str,
    *,
    repo_root: Path,
    output_path: Path,
    preferred_scope_key: str,
    scope_lookup_map: Mapping[str, Mapping[str, Any]] | None = None,
    scope_lookup: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """Link known workstream/diagram/surface tokens for shell-owned prose."""

    raw = str(text or "").strip()
    if not raw:
        return ""
    resolved_scope_lookup = scope_lookup_map or scope_lookup or {}
    preferred_scope = resolved_scope_lookup.get(str(preferred_scope_key or "").strip(), {})
    evidence = preferred_scope.get("evidence_context", {}) if isinstance(preferred_scope.get("evidence_context"), Mapping) else {}
    linked_workstreams = _linked_tokens(evidence, "linked_workstreams")
    linked_components = _linked_tokens(evidence, "linked_components")
    linked_diagrams = _linked_tokens(evidence, "linked_diagrams")
    inline_workstreams = _WORKSTREAM_RE.findall(raw)
    inline_diagrams = _DIAGRAM_RE.findall(raw)
    preferred_workstream = inline_workstreams[0] if inline_workstreams else (linked_workstreams[0] if linked_workstreams else "")
    preferred_component = linked_components[0] if linked_components else ""
    preferred_diagram = inline_diagrams[0] if inline_diagrams else (linked_diagrams[0] if linked_diagrams else "")
    parts: list[str] = []
    cursor = 0
    for match in _ASSET_RE.finditer(raw):
        start, end = match.span()
        if start > cursor:
            parts.append(html.escape(raw[cursor:start]))
        token = match.group(0)
        href = ""
        if _PLAN_RE.fullmatch(token):
            href = _relative_href(output_path, (repo_root / token).resolve())
        elif _WORKSTREAM_RE.fullmatch(token):
            href = shell_href(tab="radar", workstream=token)
        elif _DIAGRAM_RE.fullmatch(token):
            href = shell_href(tab="atlas", workstream=preferred_workstream, diagram=token)
        elif _SURFACE_RE.fullmatch(token):
            href = surface_href(
                token,
                workstream=preferred_workstream,
                component=preferred_component,
                diagram=preferred_diagram,
            )
        if href:
            parts.append(
                f'<a class="brief-inline-link" target="_top" href="{html.escape(href, quote=True)}">{html.escape(token)}</a>'
            )
        else:
            parts.append(html.escape(token))
        cursor = end
    if cursor < len(raw):
        parts.append(html.escape(raw[cursor:]))
    return "".join(parts)


def proof_href(row: Mapping[str, Any]) -> str:
    """Return the shell route for one proof reference."""

    surface = str(row.get("surface", "")).strip().lower()
    value = str(row.get("value", "")).strip()
    if surface == "casebook":
        return shell_href(tab="casebook", bug=value)
    if surface == "registry":
        return shell_href(tab="registry", component=value.replace("component:", ""))
    if surface == "atlas":
        return shell_href(tab="atlas", diagram=value)
    if surface == "compass":
        return shell_href(tab="compass", workstream=value)
    if surface == "radar":
        return shell_href(tab="radar", workstream=value)
    return shell_href(tab="radar", workstream=value)


def render_proof_refs_html(proof_refs: Sequence[Mapping[str, Any]]) -> str:
    """Render proof references as shell-owned links."""

    rows = [row for row in proof_refs if isinstance(row, Mapping)]
    if not rows:
        fallback = html.escape(operator_readout.DEFAULT_PROOF_FALLBACK)
        return f'<span class="operator-readout-copy">{fallback}</span>'
    parts: list[str] = []
    for row in rows[:4]:
        label = str(row.get("label", row.get("value", "Proof"))).strip() or "Proof"
        href = proof_href(row)
        parts.append(
            f'<a class="operator-readout-proof-link" target="_top" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        )
    return "".join(parts)

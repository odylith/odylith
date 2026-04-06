"""Shared Operator Readout contracts and guards.

This module centralizes the scenario taxonomy, action taxonomy, visibility
profiles, and validation used by the Odylith-centered operator-intelligence
flow. Delivery Intelligence, Odylith control state, and dashboard renderers all
consume this contract so the UI stays homogeneous across tools.

The readout is intentionally compact:
- it surfaces the hidden operator problem, not generic status repetition;
- it routes operators to proof instead of paraphrasing other panels;
- it supports deterministic fallback and LLM-authored findings equally.
"""

from __future__ import annotations

from copy import deepcopy
import html
import json
import re
from typing import Any, Mapping, Sequence


SCENARIO_PRIORITY: dict[str, int] = {
    "unsafe_closeout": 0,
    "cross_surface_conflict": 1,
    "orphan_activity": 2,
    "stale_authority": 3,
    "false_priority": 4,
    "clear_path": 5,
}
SEVERITY_RANK: dict[str, int] = {"blocker": 0, "watch": 1, "clear": 2}
ACTION_KINDS: frozenset[str] = frozenset(
    {
        "capture_checkpoint",
        "clear_closeout",
        "verify_closeout",
        "refresh_authority",
        "resolve_conflict",
        "rebind_scope",
        "defer_scope",
    }
)
NEXT_SURFACES: frozenset[str] = frozenset({"Registry", "Radar", "Atlas", "Compass", "Shell"})
READOUT_SOURCES: frozenset[str] = frozenset({"deterministic", "odylith-llm"})
SURFACE_VISIBILITY_PROFILES: dict[str, frozenset[str]] = {
    "registry": frozenset({"metadata", "topology", "spec", "forensic_evidence"}),
    "radar": frozenset({"workstream_spec", "topology", "warnings", "metrics"}),
    "atlas": frozenset({"diagram_freshness", "linked_workstreams", "engineering_context"}),
    "compass": frozenset({"current_workstreams", "digest", "timeline_audit"}),
    "shell": frozenset({"routing", "timeline", "policy", "recommendations", "approvals", "clearance"}),
}
RAW_PATH_RE = re.compile(
    r"(?:^|(?<=\s))(?:"
    r"/(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
    r"|(?:agents-guidelines|bin|configs|contracts|docker|docs|infra|mk|mocks|monitoring|odylith|app|policies|scripts|services|skills|tests)(?:/[A-Za-z0-9_.-]+)+"
    r"|[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.(?:md|py|json|jsonl|html|yaml|yml|toml|svg|png|mmd|txt|sh)"
    r")\b"
)
_WHITESPACE_RE = re.compile(r"\s+")
_SHELL_SCENARIO_SUMMARIES: dict[str, str] = {
    "unsafe_closeout": "Closeout is ahead of trusted proof.",
    "cross_surface_conflict": "Linked surfaces disagree on the current state.",
    "orphan_activity": "Recent activity is not anchored to a clear controlling scope.",
    "stale_authority": "The controlling checkpoint is behind current activity.",
    "false_priority": "A linked blocker matters more than the local urgency signal.",
    "clear_path": "No intervention is required right now.",
}
_SHELL_TEXT_COMPACTION_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"Latest workspace activity signal at [0-9T:+\-]+ is newer than the last explicit checkpoint at [0-9T:+\-]+\.",
            re.I,
        ),
        "Recent activity is newer than the last explicit checkpoint.",
    ),
    (
        re.compile(r"Finished workstream has newer activity than its last explicit checkpoint\.", re.I),
        "Finished scope has newer activity than its last explicit checkpoint.",
    ),
    (
        re.compile(r"Clearance state is pending\.", re.I),
        "Clearance is pending.",
    ),
    (
        re.compile(
            r"Clearance is marked cleared and .* has no newer activity than (?:its|the) last explicit checkpoint\.",
            re.I,
        ),
        "Clearance is marked cleared and no newer activity remains.",
    ),
    (
        re.compile(
            r"If ignored, .* can be closed against stale proof and force re-clearance later\.",
            re.I,
        ),
        "Ignoring this risks closeout against stale proof.",
    ),
)
_INTERVENTION_COPY: dict[str, dict[str, str]] = {
    "unsafe_closeout": {
        "title_singular": "Re-check completed work before closeout",
        "title_plural": "Re-check completed work before closeout",
        "summary_singular": "1 completed {noun_singular} changed after its last review.",
        "summary_plural": "{count} completed {noun_plural} changed after their last review.",
        "action": "Review the newest change on each affected item, then clear it again or reopen it.",
        "done": "Every affected item is re-cleared on its latest change or reopened.",
        "risk": "Otherwise completed work can close against stale evidence.",
    },
    "cross_surface_conflict": {
        "title_singular": "Resolve conflicting tool output",
        "title_plural": "Resolve conflicting tool output",
        "summary_singular": "Different surfaces disagree about this {noun_singular}.",
        "summary_plural": "Different surfaces disagree about {count} {noun_plural}.",
        "action": "Choose the source of truth, fix the conflicting surface, and restate the decision.",
        "done": "All linked surfaces agree on the same state.",
        "risk": "Otherwise different tools can drive different decisions.",
    },
    "orphan_activity": {
        "title_singular": "Assign work to a clear owner",
        "title_plural": "Assign work to a clear owner",
        "summary_singular": "Recent work on this {noun_singular} is not clearly attached to an owner or controlling scope.",
        "summary_plural": "Recent work on {count} {noun_plural} is not clearly attached to an owner or controlling scope.",
        "action": "Bind each affected item to the right owner and controlling scope.",
        "done": "Every affected item has a clear owner and controlling scope.",
        "risk": "Otherwise work can drift without review or clearance.",
    },
    "stale_authority": {
        "title_singular": "Refresh the trusted checkpoint",
        "title_plural": "Refresh the trusted checkpoint",
        "summary_singular": "This {noun_singular} has work newer than the recorded checkpoint.",
        "summary_plural": "{count} {noun_plural} have work newer than the recorded checkpoint.",
        "action": "Refresh the controlling checkpoint and restate the current source of truth.",
        "done": "The checkpoint is up to date with the latest relevant activity.",
        "risk": "Otherwise people make decisions from outdated evidence.",
    },
    "false_priority": {
        "title_singular": "Handle the higher-risk blocker first",
        "title_plural": "Handle the higher-risk blocker first",
        "summary_singular": "A different blocker matters more than the local urgency signal on this {noun_singular}.",
        "summary_plural": "A different blocker matters more than the local urgency signals on {count} {noun_plural}.",
        "action": "Handle the higher-risk blocker first, then return to the lower-priority item.",
        "done": "The higher-risk blocker is resolved or explicitly deferred.",
        "risk": "Otherwise effort goes to the wrong problem while the real blocker keeps growing.",
    },
    "clear_path": {
        "title_singular": "No intervention is needed right now",
        "title_plural": "No interventions are needed right now",
        "summary_singular": "The current evidence is aligned.",
        "summary_plural": "The current evidence is aligned.",
        "action": "Keep the latest checkpoint and proof current.",
        "done": "The latest checkpoint and proof remain current.",
        "risk": "",
    },
}
DEFAULT_ISSUE_FALLBACK = "Path is clear. Keep the latest checkpoint and proof current."
DEFAULT_WHY_HIDDEN_FALLBACK = "No hidden operator context is currently resolved."
DEFAULT_ACTION_FALLBACK = "No operator action is currently mapped."
DEFAULT_PROOF_FALLBACK = "No proof routes are currently mapped."
DEFAULT_WHY_NOW_FALLBACK = "No immediate operator forcing function is currently mapped."
DEFAULT_SUCCESS_CHECK_FALLBACK = "No explicit success check is currently mapped."
DEFAULT_HIGHLIGHT_FALLBACK = "No proof highlights are currently mapped."


def scenario_priority(value: str) -> int:
    """Return deterministic ordering rank for a scenario."""

    return int(SCENARIO_PRIORITY.get(str(value or "").strip(), 99))


def severity_rank(value: str) -> int:
    """Return deterministic ordering rank for readout severity."""

    return int(SEVERITY_RANK.get(str(value or "").strip(), 99))


def normalize_proof_ref(row: Mapping[str, Any]) -> dict[str, str]:
    """Normalize one proof route entry."""

    normalized = {
        "kind": str(row.get("kind", "")).strip(),
        "value": str(row.get("value", "")).strip(),
        "label": str(row.get("label", "")).strip(),
        "surface": str(row.get("surface", "")).strip(),
        "href": str(row.get("href", "")).strip(),
        "anchor": str(row.get("anchor", "")).strip(),
        "fact_tag": str(row.get("fact_tag", "")).strip(),
    }
    return {key: value for key, value in normalized.items() if value}


def build_proof_ref(
    *,
    kind: str,
    value: str,
    label: str,
    surface: str = "",
    href: str = "",
    anchor: str = "",
    fact_tag: str = "",
) -> dict[str, str]:
    """Create a normalized proof-route record."""

    return normalize_proof_ref(
        {
            "kind": kind,
            "value": value,
            "label": label,
            "surface": surface,
            "href": href,
            "anchor": anchor,
            "fact_tag": fact_tag,
        }
    )


def validate_operator_readout(readout: Mapping[str, Any]) -> list[str]:
    """Validate operator-readout shape and lead-text guardrails."""

    errors: list[str] = []
    scenario = str(readout.get("primary_scenario", "")).strip()
    if scenario not in SCENARIO_PRIORITY:
        errors.append("invalid primary_scenario")
    secondary = readout.get("secondary_scenarios", [])
    if not isinstance(secondary, list):
        errors.append("secondary_scenarios must be a list")
    else:
        for token in secondary:
            if str(token or "").strip() not in SCENARIO_PRIORITY:
                errors.append("invalid secondary scenario")
                break
        if len(secondary) > 2:
            errors.append("secondary_scenarios cannot exceed 2 entries")

    severity = str(readout.get("severity", "")).strip()
    if severity not in SEVERITY_RANK:
        errors.append("invalid severity")
    source = str(readout.get("source", "")).strip()
    if source not in READOUT_SOURCES:
        errors.append("invalid source")

    action_kind = str(readout.get("action_kind", "")).strip()
    if action_kind not in ACTION_KINDS:
        errors.append("invalid action_kind")

    for field in ("issue", "why_hidden", "action"):
        value = str(readout.get(field, "")).strip()
        if not value:
            errors.append(f"missing {field}")
            continue
        if RAW_PATH_RE.search(value):
            errors.append(f"raw path leaked into {field}")

    proof_refs = readout.get("proof_refs", [])
    if not isinstance(proof_refs, list) or not proof_refs:
        errors.append("proof_refs must contain at least one route")
    else:
        for row in proof_refs:
            if not isinstance(row, Mapping):
                errors.append("proof_ref must be an object")
                continue
            normalized = normalize_proof_ref(row)
            if not normalized.get("kind") or not normalized.get("value") or not normalized.get("label"):
                errors.append("proof_ref missing kind/value/label")
            if RAW_PATH_RE.search(normalized.get("label", "")):
                errors.append("proof_ref label leaked raw path")
    return errors


def _normalize_text_list(values: Any, *, limit: int) -> list[str]:
    rows: list[str] = []
    if not isinstance(values, list):
        return rows
    for raw in values:
        token = str(raw or "").strip()
        if not token:
            continue
        rows.append(token)
        if len(rows) >= limit:
            break
    return rows


def validate_operator_queue_item(item: Mapping[str, Any]) -> list[str]:
    """Validate the shared operator-queue contract."""

    errors = validate_operator_readout(item)
    rank = int(item.get("rank", 0) or 0)
    if rank < 1:
        errors.append("rank must be >= 1")
    scope_type = str(item.get("scope_type", "")).strip()
    if scope_type not in {"workstream", "component", "diagram"}:
        errors.append("invalid scope_type")
    scope_id = str(item.get("scope_id", "")).strip()
    if not scope_id:
        errors.append("missing scope_id")
    for field in ("id", "scope_key", "scope_label", "why_now", "success_check", "live_reason", "next_surface"):
        value = str(item.get(field, "")).strip()
        if not value:
            errors.append(f"missing {field}")
            continue
        if RAW_PATH_RE.search(value):
            errors.append(f"raw path leaked into {field}")
    next_surface = str(item.get("next_surface", "")).strip()
    if next_surface and next_surface not in NEXT_SURFACES:
        errors.append("invalid next_surface")
    highlights = _normalize_text_list(item.get("proof_highlights"), limit=4)
    if not highlights:
        errors.append("proof_highlights must contain at least one entry")
    elif any(RAW_PATH_RE.search(token) for token in highlights):
        errors.append("raw path leaked into proof_highlights")
    return errors


def suppress_visible_duplicates(
    *,
    readout: Mapping[str, Any],
    surface: str,
) -> dict[str, Any]:
    """Suppress proof-route duplication for a specific surface.

    The readout should remain the same operator finding everywhere, but proof
    routes that point back to facts already visible on the current surface are
    filtered so the panel keeps routing operators to the next best evidence
    surface instead of echoing what is already on screen.
    """

    clone = deepcopy(dict(readout))
    visible = SURFACE_VISIBILITY_PROFILES.get(str(surface or "").strip().lower(), frozenset())
    proof_refs = clone.get("proof_refs", [])
    if isinstance(proof_refs, list) and len(proof_refs) > 1:
        filtered = []
        for row in proof_refs:
            if not isinstance(row, Mapping):
                continue
            fact_tag = str(row.get("fact_tag", "")).strip()
            if fact_tag and fact_tag in visible:
                continue
            filtered.append(dict(row))
        if filtered:
            clone["proof_refs"] = filtered
    return clone


def compact_clear_path_issue(readout: Mapping[str, Any]) -> str:
    """Return one-line compact copy for clear-path states."""

    issue = str(readout.get("issue", "")).strip()
    if issue:
        return issue
    return DEFAULT_ISSUE_FALLBACK


def humanize_operator_readout_token(value: Any) -> str:
    """Return one shared human-readable label for readout enums/tokens."""

    token = _WHITESPACE_RE.sub(" ", re.sub(r"[_-]+", " ", str(value or "").strip())).strip()
    if not token:
        return ""
    parts: list[str] = []
    for raw in token.split(" "):
        lower = raw.lower()
        if lower == "llm":
            parts.append("LLM")
            continue
        parts.append(lower[:1].upper() + lower[1:])
    return " ".join(parts)


def render_operator_readout_meta_html(readout: Mapping[str, Any]) -> str:
    """Render the shared meta row for a readout article."""

    row = dict(readout)
    items = (
        ("Scenario", humanize_operator_readout_token(row.get("primary_scenario") or "clear_path") or "Clear Path", "operator-readout-meta-scenario"),
        ("Severity", humanize_operator_readout_token(row.get("severity") or "clear") or "Clear", "operator-readout-meta-severity"),
        ("Source", humanize_operator_readout_token(row.get("source") or "deterministic") or "Deterministic", "operator-readout-meta-source"),
    )
    return "".join(
        f'<span class="operator-readout-meta-item {tone}">{html.escape(f"{label}: {value}")}</span>'
        for label, value, tone in items
    )


def render_operator_readout_article_html(
    readout: Mapping[str, Any],
    *,
    proof_html: str,
    issue_fallback: str = DEFAULT_ISSUE_FALLBACK,
    why_hidden_fallback: str = DEFAULT_WHY_HIDDEN_FALLBACK,
    action_fallback: str = DEFAULT_ACTION_FALLBACK,
) -> str:
    """Render the shared Operator Readout article for static/server-side shells."""

    row = dict(readout)
    is_clear_path = str(row.get("primary_scenario", "")).strip() == "clear_path"
    issue_html = html.escape(str(row.get("issue") or issue_fallback).strip() or issue_fallback)
    why_hidden_html = html.escape(str(row.get("why_hidden") or why_hidden_fallback).strip() or why_hidden_fallback)
    action_html = html.escape(str(row.get("action") or action_fallback).strip() or action_fallback)
    if is_clear_path:
        details_html = (
            '<div class="operator-readout-details">'
            '<div class="operator-readout-section">'
            '<p class="operator-readout-label">Go To Proof</p>'
            f'<div class="operator-readout-proof">{proof_html}</div>'
            "</div>"
            "</div>"
        )
    else:
        details_html = (
            '<div class="operator-readout-details">'
            '<div class="operator-readout-section">'
            '<p class="operator-readout-label">Why Hidden</p>'
            f'<p class="operator-readout-copy">{why_hidden_html}</p>'
            "</div>"
            '<div class="operator-readout-section">'
            '<p class="operator-readout-label">Do This</p>'
            f'<p class="operator-readout-copy">{action_html}</p>'
            "</div>"
            '<div class="operator-readout-section">'
            '<p class="operator-readout-label">Go To Proof</p>'
            f'<div class="operator-readout-proof">{proof_html}</div>'
            "</div>"
            "</div>"
        )
    return (
        f'<article class="operator-readout{" is-clear" if is_clear_path else ""}">'
        f'<div class="operator-readout-meta">{render_operator_readout_meta_html(row)}</div>'
        '<div class="operator-readout-main">'
        '<p class="operator-readout-label">Issue</p>'
        f'<p class="operator-readout-copy">{issue_html}</p>'
        "</div>"
        f"{details_html}"
        "</article>"
    )


def render_operator_queue_meta_html(item: Mapping[str, Any]) -> str:
    """Render the shared meta row for an operator-queue item."""

    row = dict(item)
    rank = int(row.get("rank", 0) or 0)
    items = (
        ("Rank", f"#{rank}" if rank > 0 else "#-", "operator-readout-meta-rank"),
        ("Severity", humanize_operator_readout_token(row.get("severity") or "watch") or "Watch", "operator-readout-meta-severity"),
        ("Scenario", humanize_operator_readout_token(row.get("primary_scenario") or "clear_path") or "Clear Path", "operator-readout-meta-scenario"),
    )
    return "".join(
        f'<span class="operator-readout-meta-item {tone}">{html.escape(f"{label}: {value}")}</span>'
        for label, value, tone in items
    )


def _render_highlight_list_html(values: Sequence[str], *, empty_text: str) -> str:
    rows = [str(item or "").strip() for item in values if str(item or "").strip()]
    if not rows:
        return f'<span class="operator-readout-copy">{html.escape(empty_text)}</span>'
    return "".join(f'<span class="operator-readout-copy">{html.escape(token)}</span>' for token in rows)


def _compact_shell_text(value: Any, *, fallback: str = "", limit: int = 120) -> str:
    token = _WHITESPACE_RE.sub(" ", str(value or "").replace("`", "").strip())
    if not token:
        token = fallback
    for pattern, replacement in _SHELL_TEXT_COMPACTION_RULES:
        token = pattern.sub(replacement, token)
    token = _WHITESPACE_RE.sub(" ", token).strip()
    if len(token) <= limit:
        return token
    clipped = token[: max(0, limit - 3)].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return f"{clipped.rstrip(' .,:;')}..."


def _shell_issue_summary(item: Mapping[str, Any]) -> str:
    scenario = str(item.get("primary_scenario", "")).strip()
    fallback = _SHELL_SCENARIO_SUMMARIES.get(scenario, DEFAULT_ISSUE_FALLBACK)
    issue = _compact_shell_text(item.get("issue", ""), fallback="", limit=132)
    if issue and len(issue) <= 84:
        return issue
    return fallback


def _shell_scope_caption(item: Mapping[str, Any]) -> str:
    """Return a compact scope caption for shell triage cards."""

    scope_id = str(item.get("scope_id", "")).strip()
    scope_label = _WHITESPACE_RE.sub(" ", str(item.get("scope_label", "")).strip())
    if not scope_label and not scope_id:
        return "Linked scope"
    if scope_id and scope_label:
        if scope_label.startswith(f"{scope_id} "):
            return _compact_shell_text(scope_label, limit=88)
        return _compact_shell_text(f"{scope_id} · {scope_label}", limit=88)
    return _compact_shell_text(scope_label or scope_id, limit=88)


def _shell_signal_summaries(item: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    for raw in _normalize_text_list(item.get("proof_highlights"), limit=4):
        token = _compact_shell_text(raw, limit=84)
        if token and token not in rows:
            rows.append(token)
        if len(rows) >= 2:
            break
    if not rows:
        rows.append("Open Shell for proof and clearance details.")
    return rows


def _human_severity_label(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token == "blocker":
        return "Review now"
    if token == "watch":
        return "Watch"
    return "Clear"


def _scope_nouns(scope_type: str) -> tuple[str, str]:
    token = str(scope_type or "").strip().lower()
    if token == "workstream":
        return ("workstream", "workstreams")
    if token == "component":
        return ("component", "components")
    if token == "diagram":
        return ("diagram", "diagrams")
    return ("item", "items")


def _group_scope_nouns(items: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    scope_types = {
        str(item.get("scope_type", "")).strip().lower()
        for item in items
        if isinstance(item, Mapping) and str(item.get("scope_type", "")).strip()
    }
    if len(scope_types) == 1:
        return _scope_nouns(next(iter(scope_types)))
    return ("item", "items")


def _human_intervention_copy(
    scenario: str,
    *,
    count: int,
    noun_singular: str = "item",
    noun_plural: str = "items",
) -> dict[str, str]:
    template = _INTERVENTION_COPY.get(scenario, _INTERVENTION_COPY["clear_path"])
    title_key = "title_plural" if count != 1 else "title_singular"
    summary_key = "summary_plural" if count != 1 else "summary_singular"
    return {
        "title": str(template.get(title_key, "")).format(
            count=count,
            noun_singular=noun_singular,
            noun_plural=noun_plural,
        ).strip(),
        "summary": str(template.get(summary_key, "")).format(
            count=count,
            noun_singular=noun_singular,
            noun_plural=noun_plural,
        ).strip(),
        "action": str(template.get("action", DEFAULT_ACTION_FALLBACK)).strip() or DEFAULT_ACTION_FALLBACK,
        "done": str(template.get("done", DEFAULT_SUCCESS_CHECK_FALLBACK)).strip() or DEFAULT_SUCCESS_CHECK_FALLBACK,
        "risk": str(template.get("risk", "")).strip(),
    }


def _intervention_group_key(item: Mapping[str, Any]) -> str:
    scenario = str(item.get("primary_scenario", "")).strip() or "clear_path"
    action_kind = str(item.get("action_kind", "")).strip() or "none"
    severity = str(item.get("severity", "")).strip() or "watch"
    return f"{scenario}:{action_kind}:{severity}"


def _intervention_item_label(item: Mapping[str, Any], *, limit: int = 84) -> str:
    return _compact_shell_text(_shell_scope_caption(item), limit=limit)


def _intervention_short_label(item: Mapping[str, Any], *, limit: int = 36) -> str:
    scope_id = str(item.get("scope_id", "")).strip()
    if scope_id:
        return scope_id
    return _compact_shell_text(_shell_scope_caption(item), limit=limit)


def _format_label_series(labels: Sequence[str]) -> str:
    rows = [str(label or "").strip() for label in labels if str(label or "").strip()]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _group_start_here_text(
    preview_items: Sequence[Mapping[str, Any]],
    *,
    overflow_count: int,
    noun_singular: str,
    noun_plural: str,
    short: bool = False,
) -> str:
    label_key = "short_label" if short else "label"
    labels = [str(item.get(label_key, "")).strip() for item in preview_items if isinstance(item, Mapping)]
    label_series = _format_label_series(labels)
    if not label_series:
        return ""
    overflow_text = ""
    if overflow_count > 0:
        noun = noun_singular if overflow_count == 1 else noun_plural
        overflow_text = f" {overflow_count} more {noun} in the shell."
    return f"Start with {label_series}.{overflow_text}"


def _group_risk_text(items: Sequence[Mapping[str, Any]], *, fallback: str) -> str:
    for item in items:
        for raw in _normalize_text_list(item.get("proof_highlights"), limit=4):
            token = str(raw or "").strip()
            if not token or not token.lower().startswith("if ignored,"):
                continue
            return _compact_shell_text(token, limit=124)
    return fallback


def _group_proof_refs(items: Sequence[Mapping[str, Any]], *, max_refs: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    multi_item = len(items) > 1
    for item in items:
        scope_id = str(item.get("scope_id", "")).strip()
        for raw in item.get("proof_refs", []) if isinstance(item.get("proof_refs"), list) else []:
            if not isinstance(raw, Mapping):
                continue
            normalized = normalize_proof_ref(raw)
            label = str(normalized.get("label", "")).strip() or str(normalized.get("value", "")).strip() or "Proof"
            if multi_item and scope_id and not label.startswith(scope_id):
                normalized["label"] = f"{scope_id} {label}"
            key = (
                str(normalized.get("kind", "")).strip(),
                str(normalized.get("value", "")).strip(),
                str(normalized.get("label", "")).strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(normalized)
            if len(rows) >= max_refs:
                return rows
    return rows


def build_operator_intervention_groups(
    operator_queue: Sequence[Mapping[str, Any]],
    *,
    max_items_per_group: int = 5,
    max_signals_per_group: int = 4,
    max_proof_refs_per_group: int = 8,
) -> list[dict[str, Any]]:
    """Group machine-native queue items into human-readable interventions."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    ordered_keys: list[str] = []
    normalized_rows = [dict(row) for row in operator_queue if isinstance(row, Mapping)]
    normalized_rows.sort(
        key=lambda row: (
            int(row.get("rank", 0) or 0),
            severity_rank(row.get("severity", "")),
            scenario_priority(row.get("primary_scenario", "")),
            str(row.get("scope_key", "")).strip(),
        )
    )
    for row in normalized_rows:
        key = _intervention_group_key(row)
        if key not in grouped:
            grouped[key] = []
            ordered_keys.append(key)
        grouped[key].append(row)

    groups: list[dict[str, Any]] = []
    for index, key in enumerate(ordered_keys, start=1):
        items = grouped[key]
        representative = items[0]
        count = len(items)
        noun_singular, noun_plural = _group_scope_nouns(items)
        copy = _human_intervention_copy(
            str(representative.get("primary_scenario", "")).strip(),
            count=count,
            noun_singular=noun_singular,
            noun_plural=noun_plural,
        )
        preview_items = []
        for item in items[:max_items_per_group]:
            preview_items.append(
                {
                    "scope_key": str(item.get("scope_key", "")).strip(),
                    "scope_id": str(item.get("scope_id", "")).strip(),
                    "scope_type": str(item.get("scope_type", "")).strip(),
                    "label": _intervention_item_label(item),
                    "short_label": _intervention_short_label(item),
                    "reason": _compact_shell_text(item.get("why_now") or item.get("issue"), limit=96),
                }
            )
        overflow_count = max(0, count - len(preview_items))
        count_label = f"{count} {noun_singular if count == 1 else noun_plural}"
        start_here = _group_start_here_text(
            preview_items[:3],
            overflow_count=overflow_count,
            noun_singular=noun_singular,
            noun_plural=noun_plural,
        )
        start_here_short = _group_start_here_text(
            preview_items[:3],
            overflow_count=overflow_count,
            noun_singular=noun_singular,
            noun_plural=noun_plural,
            short=True,
        )
        signals: list[str] = []
        for item in items:
            for token in _shell_signal_summaries(item):
                if token in signals:
                    continue
                signals.append(token)
                if len(signals) >= max_signals_per_group:
                    break
            if len(signals) >= max_signals_per_group:
                break
        next_surface = next(
            (
                str(item.get("next_surface", "")).strip()
                for item in items
                if str(item.get("next_surface", "")).strip()
            ),
            "Shell",
        )
        groups.append(
            {
                "id": f"intervention-{index}",
                "group_key": key,
                "rank": int(representative.get("rank", 0) or 0),
                "severity": str(representative.get("severity", "")).strip() or "watch",
                "severity_label": _human_severity_label(representative.get("severity", "")),
                "primary_scenario": str(representative.get("primary_scenario", "")).strip() or "clear_path",
                "count": count,
                "count_label": count_label,
                "scope_noun_singular": noun_singular,
                "scope_noun_plural": noun_plural,
                "title": copy["title"],
                "summary": copy["summary"],
                "action": copy["action"],
                "success_check": copy["done"],
                "risk": _group_risk_text(items, fallback=copy["risk"]),
                "next_surface": next_surface,
                "requires_approval": any(bool(item.get("requires_approval")) for item in items),
                "primary_scope_key": str(representative.get("scope_key", "")).strip(),
                "primary_scope_id": str(representative.get("scope_id", "")).strip(),
                "scope_keys": [str(item.get("scope_key", "")).strip() for item in items if str(item.get("scope_key", "")).strip()],
                "scope_ids": [str(item.get("scope_id", "")).strip() for item in items if str(item.get("scope_id", "")).strip()],
                "affected_summary": start_here,
                "start_here": start_here,
                "start_here_short": start_here_short,
                "preview_items": preview_items,
                "overflow_count": overflow_count,
                "items": preview_items,
                "signals": signals,
                "proof_refs": _group_proof_refs(items, max_refs=max_proof_refs_per_group),
            }
        )
    return groups


def render_operator_queue_article_html(
    item: Mapping[str, Any],
    *,
    open_href: str = "",
    open_label: str = "Open in Shell",
    why_now_fallback: str = DEFAULT_WHY_NOW_FALLBACK,
    success_check_fallback: str = DEFAULT_SUCCESS_CHECK_FALLBACK,
    highlight_fallback: str = DEFAULT_HIGHLIGHT_FALLBACK,
) -> str:
    """Render the shared operator-inbox article."""

    row = dict(item)
    issue_html = html.escape(str(row.get("issue") or DEFAULT_ISSUE_FALLBACK).strip() or DEFAULT_ISSUE_FALLBACK)
    why_now_html = html.escape(str(row.get("why_now") or why_now_fallback).strip() or why_now_fallback)
    action_html = html.escape(str(row.get("action") or DEFAULT_ACTION_FALLBACK).strip() or DEFAULT_ACTION_FALLBACK)
    success_check_html = html.escape(str(row.get("success_check") or success_check_fallback).strip() or success_check_fallback)
    highlights_html = _render_highlight_list_html(
        _normalize_text_list(row.get("proof_highlights"), limit=4),
        empty_text=highlight_fallback,
    )
    open_section = ""
    if str(open_href or "").strip():
        open_section = (
            '<div class="operator-readout-section">'
            '<p class="operator-readout-label">Open in Shell</p>'
            f'<div class="operator-readout-proof"><a class="operator-readout-proof-link" href="{html.escape(open_href, quote=True)}" target="_top">{html.escape(open_label)}</a></div>'
            "</div>"
        )
    return (
        '<article class="operator-readout operator-inbox-item">'
        f'<div class="operator-readout-meta">{render_operator_queue_meta_html(row)}</div>'
        '<div class="operator-readout-main">'
        '<p class="operator-readout-label">Issue</p>'
        f'<p class="operator-readout-copy">{issue_html}</p>'
        "</div>"
        '<div class="operator-readout-details">'
        '<div class="operator-readout-section">'
        '<p class="operator-readout-label">Why Now</p>'
        f'<p class="operator-readout-copy">{why_now_html}</p>'
        "</div>"
        '<div class="operator-readout-section">'
        '<p class="operator-readout-label">Do This Now</p>'
        f'<p class="operator-readout-copy">{action_html}</p>'
        "</div>"
        '<div class="operator-readout-section">'
        '<p class="operator-readout-label">Success Check</p>'
        f'<p class="operator-readout-copy">{success_check_html}</p>'
        "</div>"
        '<div class="operator-readout-section">'
        '<p class="operator-readout-label">Proof Highlights</p>'
        f'<div class="operator-readout-proof">{highlights_html}</div>'
        "</div>"
        f"{open_section}"
        "</div>"
        "</article>"
    )


def render_shell_operator_queue_card_html(
    item: Mapping[str, Any],
    *,
    open_href: str = "",
    open_label: str = "Open in Shell",
    expanded: bool = False,
) -> str:
    """Render a compact shell-only summary card for one queue item."""

    row = dict(item)
    rank = int(row.get("rank", 0) or 0)
    severity = humanize_operator_readout_token(row.get("severity") or "watch") or "Watch"
    scenario = humanize_operator_readout_token(row.get("primary_scenario") or "clear_path") or "Clear Path"
    scope_caption = _shell_scope_caption(row)
    problem_title = _shell_issue_summary(row)
    why_now_text = _compact_shell_text(row.get("why_now", ""), fallback=DEFAULT_WHY_NOW_FALLBACK, limit=112)
    action_text = _compact_shell_text(row.get("action", ""), fallback=DEFAULT_ACTION_FALLBACK, limit=112)
    success_check_text = _compact_shell_text(
        row.get("success_check", ""),
        fallback=DEFAULT_SUCCESS_CHECK_FALLBACK,
        limit=108,
    )
    signal_html = "".join(
        f'<span class="operator-inbox-card-signal">{html.escape(token)}</span>'
        for token in _shell_signal_summaries(row)
    )
    open_html = ""
    if str(open_href or "").strip():
        open_html = (
            f'<a class="operator-inbox-card-link" href="{html.escape(open_href, quote=True)}" target="_top">'
            f"{html.escape(open_label)}"
            "</a>"
        )
    variant_class = " is-primary" if expanded else " is-secondary"
    problem_block = (
        f'<p class="operator-inbox-card-scope">{html.escape(scope_caption)}</p>'
        f'<h3 class="operator-inbox-card-title">{html.escape(problem_title)}</h3>'
    )
    if not expanded:
        return (
            f'<article class="operator-inbox-card{variant_class}">'
            '<div class="operator-inbox-card-head">'
            f'<span class="operator-inbox-card-chip operator-inbox-card-chip-rank">#{rank if rank > 0 else "-"}</span>'
            f'<span class="operator-inbox-card-chip operator-inbox-card-chip-severity">{html.escape(severity)}</span>'
            f'<span class="operator-inbox-card-chip operator-inbox-card-chip-scenario">{html.escape(scenario)}</span>'
            "</div>"
            f"{problem_block}"
            '<div class="operator-inbox-card-row operator-inbox-card-row-inline">'
            '<p class="operator-inbox-card-label">Do now</p>'
            f'<p class="operator-inbox-card-copy">{html.escape(action_text)}</p>'
            "</div>"
            f"{open_html}"
            "</article>"
        )
    return (
        f'<article class="operator-inbox-card{variant_class}">'
        '<div class="operator-inbox-card-head">'
        f'<span class="operator-inbox-card-chip operator-inbox-card-chip-rank">#{rank if rank > 0 else "-"}</span>'
        f'<span class="operator-inbox-card-chip operator-inbox-card-chip-severity">{html.escape(severity)}</span>'
        f'<span class="operator-inbox-card-chip operator-inbox-card-chip-scenario">{html.escape(scenario)}</span>'
        "</div>"
        f"{problem_block}"
        '<div class="operator-inbox-card-rows">'
        '<div class="operator-inbox-card-row">'
        '<p class="operator-inbox-card-label">Why now</p>'
        f'<p class="operator-inbox-card-copy">{html.escape(why_now_text)}</p>'
        "</div>"
        '<div class="operator-inbox-card-row">'
        '<p class="operator-inbox-card-label">Do now</p>'
        f'<p class="operator-inbox-card-copy">{html.escape(action_text)}</p>'
        "</div>"
        '<div class="operator-inbox-card-row">'
        '<p class="operator-inbox-card-label">Done when</p>'
        f'<p class="operator-inbox-card-copy">{html.escape(success_check_text)}</p>'
        "</div>"
        "</div>"
        '<div class="operator-inbox-card-row operator-inbox-card-row-signals">'
        '<p class="operator-inbox-card-label">Signals</p>'
        '<div class="operator-inbox-card-signals">'
        f"{signal_html}"
        "</div>"
        "</div>"
        f"{open_html}"
        "</article>"
    )


def render_shell_operator_group_card_html(
    group: Mapping[str, Any],
    *,
    open_href: str = "",
    open_label: str = "Open in Shell",
    expanded: bool = False,
) -> str:
    """Render one shell card for a grouped human intervention."""

    row = dict(group)
    count = int(row.get("count", 0) or 0)
    count_label = str(row.get("count_label", "")).strip() or (f"{count} items" if count != 1 else "1 item")
    severity_label = str(row.get("severity_label", "")).strip() or "Needs review"
    title = str(row.get("title", "")).strip() or DEFAULT_ISSUE_FALLBACK
    summary = str(row.get("summary", "")).strip() or DEFAULT_WHY_NOW_FALLBACK
    start_here = str(row.get("start_here_short") or row.get("start_here") or "").strip()
    open_html = ""
    if str(open_href or "").strip():
        open_html = (
            f'<a class="operator-inbox-card-link" href="{html.escape(open_href, quote=True)}" target="_top">'
            f"{html.escape(open_label)}"
            "</a>"
        )
    variant_class = " is-primary" if expanded else " is-secondary"
    if not expanded:
        return (
            f'<article class="operator-inbox-row{variant_class}">'
            '<div class="operator-inbox-row-main">'
            '<div class="operator-inbox-card-head">'
            f'<span class="operator-inbox-card-chip operator-inbox-card-chip-rank">{html.escape(count_label)}</span>'
            f'<span class="operator-inbox-card-chip operator-inbox-card-chip-severity">{html.escape(severity_label)}</span>'
            "</div>"
            f'<h3 class="operator-inbox-row-title">{html.escape(title)}</h3>'
            f'<p class="operator-inbox-row-summary">{html.escape(start_here or summary)}</p>'
            "</div>"
            f"{open_html}"
            "</article>"
        )
    return (
        f'<article class="operator-inbox-card{variant_class}">'
        '<div class="operator-inbox-card-head">'
        f'<span class="operator-inbox-card-chip operator-inbox-card-chip-rank">{html.escape(count_label)}</span>'
        f'<span class="operator-inbox-card-chip operator-inbox-card-chip-severity">{html.escape(severity_label)}</span>'
        "</div>"
        f'<h3 class="operator-inbox-card-title">{html.escape(title)}</h3>'
        f'<p class="operator-inbox-card-summary">{html.escape(summary)}</p>'
        '<div class="operator-inbox-card-preview">'
        '<p class="operator-inbox-card-label">Start here</p>'
        f'<p class="operator-inbox-card-copy">{html.escape(start_here)}</p>'
        "</div>"
        f"{open_html}"
        "</article>"
    )


def operator_readout_runtime_helpers_js() -> str:
    """Return shared browser-side helpers for Operator Readout rendering.

    Renderers still own proof-route resolution because each surface has
    different deep-link rules, but the article markup, fallback text, and token
    humanization should stay identical everywhere.
    """

    issue_fallback = json.dumps(DEFAULT_ISSUE_FALLBACK)
    why_hidden_fallback = json.dumps(DEFAULT_WHY_HIDDEN_FALLBACK)
    action_fallback = json.dumps(DEFAULT_ACTION_FALLBACK)
    proof_fallback = json.dumps(DEFAULT_PROOF_FALLBACK)
    why_now_fallback = json.dumps(DEFAULT_WHY_NOW_FALLBACK)
    success_check_fallback = json.dumps(DEFAULT_SUCCESS_CHECK_FALLBACK)
    highlight_fallback = json.dumps(DEFAULT_HIGHLIGHT_FALLBACK)
    scenario_summaries = json.dumps(_SHELL_SCENARIO_SUMMARIES, ensure_ascii=False)
    return f"""
function humanizeOperatorReadoutToken(value) {{
  const raw = String(value || "").replace(/[_-]+/g, " ").trim().replace(/\\s+/g, " ");
  if (!raw) return "";
  return raw.split(" ").map((segment) => {{
    const lower = String(segment || "").toLowerCase();
    if (!lower) return "";
    if (lower === "llm") return "LLM";
    return `${{lower.charAt(0).toUpperCase()}}${{lower.slice(1)}}`;
  }}).join(" ");
}}

const OPERATOR_SCENARIO_SUMMARIES = {scenario_summaries};

function compactOperatorText(value, options = {{}}) {{
  const fallback = String(options.fallback || "").trim();
  const limit = Number(options.limit || 120);
  let token = String(value || "").replace(/`/g, "").replace(/\\s+/g, " ").trim();
  if (!token) token = fallback;
  token = token
    .replace(/Latest workspace activity signal at [0-9T:+\\-]+ is newer than the last explicit checkpoint at [0-9T:+\\-]+\\./gi, "Recent activity is newer than the last explicit checkpoint.")
    .replace(/Finished workstream has newer activity than its last explicit checkpoint\\./gi, "Finished scope has newer activity than its last explicit checkpoint.")
    .replace(/Shell clearance state is pending\\./gi, "Shell clearance is pending.")
    .replace(/Clearance is marked cleared and .* has no newer activity than (?:its|the) last explicit checkpoint\\./gi, "Clearance is marked cleared and no newer activity remains.")
    .replace(/If ignored, .* can be closed against stale proof and force re-clearance later\\./gi, "Ignoring this risks closeout against stale proof.");
  token = token.replace(/\\s+/g, " ").trim();
  if (!limit || token.length <= limit) return token;
  let clipped = token.slice(0, Math.max(0, limit - 3)).trimEnd();
  const lastSpace = clipped.lastIndexOf(" ");
  if (lastSpace > 0) clipped = clipped.slice(0, lastSpace);
  return `${{clipped.replace(/[ .,:;]+$/g, "")}}...`;
}}

function operatorQueueProblemTitle(item) {{
  const row = item && typeof item === "object" ? item : {{}};
  const scenario = String(row.primary_scenario || "").trim();
  const fallback = String(OPERATOR_SCENARIO_SUMMARIES[scenario] || {issue_fallback}).trim() || {issue_fallback};
  const issue = compactOperatorText(row.issue, {{ fallback: "", limit: 132 }});
  if (issue && issue.length <= 88) return issue;
  return fallback;
}}

function operatorQueueScopeCaption(item, limit = 96) {{
  const row = item && typeof item === "object" ? item : {{}};
  const scopeId = String(row.scope_id || "").trim();
  const scopeLabel = String(row.scope_label || "").replace(/\\s+/g, " ").trim();
  if (!scopeId && !scopeLabel) return "Linked scope";
  if (scopeId && scopeLabel) {{
    if (scopeLabel.startsWith(`${{scopeId}} `)) return compactOperatorText(scopeLabel, {{ limit }});
    return compactOperatorText(`${{scopeId}} · ${{scopeLabel}}`, {{ limit }});
  }}
  return compactOperatorText(scopeLabel || scopeId, {{ limit }});
}}

function operatorQueueSignalSummaries(item, limit = 3) {{
  const rows = [];
  for (const raw of normalizeOperatorTextList(item && item.proof_highlights, 4)) {{
    const token = compactOperatorText(raw, {{ limit: 88 }});
    if (!token || rows.includes(token)) continue;
    rows.push(token);
    if (rows.length >= limit) break;
  }}
  if (!rows.length) rows.push("Open Shell for proof and clearance details.");
  return rows;
}}

function operatorQueueRiskText(item) {{
  const highlights = normalizeOperatorTextList(item && item.proof_highlights, 4);
  for (const raw of highlights) {{
    if (/^If ignored,/i.test(String(raw || "").trim())) {{
      return compactOperatorText(raw, {{ limit: 124 }});
    }}
  }}
  return "";
}}

function renderOperatorReadoutMeta(readout) {{
  const row = readout && typeof readout === "object" ? readout : {{}};
  const items = [
    {{ label: "Scenario", value: humanizeOperatorReadoutToken(row.primary_scenario || "clear_path") || "Clear Path", tone: "operator-readout-meta-scenario" }},
    {{ label: "Severity", value: humanizeOperatorReadoutToken(row.severity || "clear") || "Clear", tone: "operator-readout-meta-severity" }},
    {{ label: "Source", value: humanizeOperatorReadoutToken(row.source || "deterministic") || "Deterministic", tone: "operator-readout-meta-source" }},
  ];
  return items.map((item) => `<span class="operator-readout-meta-item ${{item.tone}}">${{escapeHtml(`${{item.label}}: ${{item.value}}`)}}</span>`).join("");
}}

function renderOperatorReadoutProofLinks(refs, hrefBuilder, emptyText = {proof_fallback}) {{
  const rows = Array.isArray(refs) ? refs.filter((row) => row && typeof row === "object") : [];
  if (!rows.length) {{
    return `<span class="operator-readout-copy">${{escapeHtml(String(emptyText || {proof_fallback}))}}</span>`;
  }}
  const resolver = typeof hrefBuilder === "function" ? hrefBuilder : (() => "#");
  return rows.map((row) => {{
    const label = String(row && row.label || row && row.value || "Proof").trim() || "Proof";
    const href = String(resolver(row) || "#").trim() || "#";
    return `<a class="operator-readout-proof-link" href="${{escapeHtml(href)}}" target="_top" data-tooltip="${{escapeHtml(label)}}" aria-label="${{escapeHtml(label)}}">${{escapeHtml(label)}}</a>`;
  }}).join("");
}}

function renderOperatorReadoutArticle(readout, options = {{}}) {{
  const row = readout && typeof readout === "object" ? readout : {{}};
  const isClearPath = String(row.primary_scenario || "").trim() === "clear_path";
  const issueText = String(row.issue || options.issueFallback || {issue_fallback}).trim() || {issue_fallback};
  const whyHiddenText = String(row.why_hidden || options.whyHiddenFallback || {why_hidden_fallback}).trim() || {why_hidden_fallback};
  const actionText = String(row.action || options.actionFallback || {action_fallback}).trim() || {action_fallback};
  const proofHtml = String(
    options.proofHtml
    || `<span class="operator-readout-copy">${{escapeHtml(String(options.proofFallback || {proof_fallback}))}}</span>`
  );
  const metaHtml = String(options.metaHtml || renderOperatorReadoutMeta(row));
  const detailsHtml = isClearPath
    ? `
      <div class="operator-readout-details">
        <div class="operator-readout-section">
          <p class="operator-readout-label">Go To Proof</p>
          <div class="operator-readout-proof">${{proofHtml}}</div>
        </div>
      </div>
    `
    : `
      <div class="operator-readout-details">
        <div class="operator-readout-section">
          <p class="operator-readout-label">Why Hidden</p>
          <p class="operator-readout-copy">${{escapeHtml(whyHiddenText)}}</p>
        </div>
        <div class="operator-readout-section">
          <p class="operator-readout-label">Do This</p>
          <p class="operator-readout-copy">${{escapeHtml(actionText)}}</p>
        </div>
        <div class="operator-readout-section">
          <p class="operator-readout-label">Go To Proof</p>
          <div class="operator-readout-proof">${{proofHtml}}</div>
        </div>
      </div>
    `;
  return `
    <article class="operator-readout${{isClearPath ? " is-clear" : ""}}">
      <div class="operator-readout-meta">${{metaHtml}}</div>
      <div class="operator-readout-main">
        <p class="operator-readout-label">Issue</p>
        <p class="operator-readout-copy">${{escapeHtml(issueText)}}</p>
      </div>
      ${{detailsHtml}}
    </article>
  `;
}}

function normalizeOperatorTextList(values, limit = 4) {{
  if (!Array.isArray(values)) return [];
  const rows = [];
  for (const raw of values) {{
    const token = String(raw || "").trim();
    if (!token) continue;
    rows.push(token);
    if (rows.length >= limit) break;
  }}
  return rows;
}}

function renderOperatorHighlightList(values, emptyText = {highlight_fallback}) {{
  const rows = normalizeOperatorTextList(values, 4);
  if (!rows.length) {{
    return `<span class="operator-readout-copy">${{escapeHtml(String(emptyText || {highlight_fallback}))}}</span>`;
  }}
  return rows.map((token) => `<span class="operator-readout-copy">${{escapeHtml(token)}}</span>`).join("");
}}

function renderOperatorQueueMeta(item) {{
  const row = item && typeof item === "object" ? item : {{}};
  const rank = Number(row.rank || 0);
  const items = [
    {{ label: "Rank", value: rank > 0 ? `#${{rank}}` : "#-", tone: "operator-readout-meta-rank" }},
    {{ label: "Severity", value: humanizeOperatorReadoutToken(row.severity || "watch") || "Watch", tone: "operator-readout-meta-severity" }},
    {{ label: "Scenario", value: humanizeOperatorReadoutToken(row.primary_scenario || "clear_path") || "Clear Path", tone: "operator-readout-meta-scenario" }},
  ];
  return items.map((item) => `<span class="operator-readout-meta-item ${{item.tone}}">${{escapeHtml(`${{item.label}}: ${{item.value}}`)}}</span>`).join("");
}}

function renderOperatorQueueItem(item, options = {{}}) {{
  const row = item && typeof item === "object" ? item : {{}};
  const issueText = String(row.issue || options.issueFallback || {issue_fallback}).trim() || {issue_fallback};
  const whyNowText = String(row.why_now || options.whyNowFallback || {why_now_fallback}).trim() || {why_now_fallback};
  const actionText = String(row.action || options.actionFallback || {action_fallback}).trim() || {action_fallback};
  const successCheckText = String(row.success_check || options.successCheckFallback || {success_check_fallback}).trim() || {success_check_fallback};
  const metaHtml = String(options.metaHtml || renderOperatorQueueMeta(row));
  const highlightsHtml = String(options.highlightsHtml || renderOperatorHighlightList(row.proof_highlights, options.highlightFallback || {highlight_fallback}));
  const openHref = String(options.openHref || "").trim();
  const openLabel = String(options.openLabel || "Open in Shell").trim() || "Open in Shell";
  const openSection = openHref
    ? `
      <div class="operator-readout-section">
        <p class="operator-readout-label">Open in Shell</p>
        <div class="operator-readout-proof">
          <a class="operator-readout-proof-link" href="${{escapeHtml(openHref)}}" target="_top">${{escapeHtml(openLabel)}}</a>
        </div>
      </div>
    `
    : "";
  return `
    <article class="operator-readout operator-inbox-item">
      <div class="operator-readout-meta">${{metaHtml}}</div>
      <div class="operator-readout-main">
        <p class="operator-readout-label">Issue</p>
        <p class="operator-readout-copy">${{escapeHtml(issueText)}}</p>
      </div>
      <div class="operator-readout-details">
        <div class="operator-readout-section">
          <p class="operator-readout-label">Why Now</p>
          <p class="operator-readout-copy">${{escapeHtml(whyNowText)}}</p>
        </div>
        <div class="operator-readout-section">
          <p class="operator-readout-label">Do This Now</p>
          <p class="operator-readout-copy">${{escapeHtml(actionText)}}</p>
        </div>
        <div class="operator-readout-section">
          <p class="operator-readout-label">Success Check</p>
          <p class="operator-readout-copy">${{escapeHtml(successCheckText)}}</p>
        </div>
        <div class="operator-readout-section">
          <p class="operator-readout-label">Proof Highlights</p>
          <div class="operator-readout-proof">${{highlightsHtml}}</div>
        </div>
        ${{openSection}}
      </div>
    </article>
  `;
}}

""".strip()


__all__ = [
    "ACTION_KINDS",
    "NEXT_SURFACES",
    "DEFAULT_ACTION_FALLBACK",
    "DEFAULT_HIGHLIGHT_FALLBACK",
    "DEFAULT_ISSUE_FALLBACK",
    "DEFAULT_PROOF_FALLBACK",
    "DEFAULT_SUCCESS_CHECK_FALLBACK",
    "DEFAULT_WHY_HIDDEN_FALLBACK",
    "DEFAULT_WHY_NOW_FALLBACK",
    "RAW_PATH_RE",
    "READOUT_SOURCES",
    "SCENARIO_PRIORITY",
    "SEVERITY_RANK",
    "SURFACE_VISIBILITY_PROFILES",
    "build_operator_intervention_groups",
    "build_proof_ref",
    "compact_clear_path_issue",
    "humanize_operator_readout_token",
    "normalize_proof_ref",
    "operator_readout_runtime_helpers_js",
    "render_operator_readout_article_html",
    "render_operator_readout_meta_html",
    "render_operator_queue_article_html",
    "render_operator_queue_meta_html",
    "render_shell_operator_group_card_html",
    "render_shell_operator_queue_card_html",
    "scenario_priority",
    "severity_rank",
    "suppress_visible_duplicates",
    "validate_operator_queue_item",
    "validate_operator_readout",
]

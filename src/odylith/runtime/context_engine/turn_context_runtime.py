"""Turn Context Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common.consumer_profile import load_consumer_profile
from odylith.runtime.common.repo_shape import PRODUCT_REPO_ROLE
from odylith.runtime.common.repo_shape import repo_role_from_local_shape
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime as projection_search_runtime

_FAST_LANE_LAYOUT_TERMS = (
    "align",
    "center",
    "column",
    "full width",
    "full-width",
    "height",
    "layout",
    "margin",
    "move",
    "next to",
    "padding",
    "position",
    "right of",
    "spacing",
    "stack",
    "truncate",
    "truncating",
    "width",
)
_FAST_LANE_COPY_TERMS = (
    "copy",
    "label",
    "rename",
    "text",
    "title",
    "typo",
    "wording",
)
_FAST_LANE_BINDING_TERMS = (
    "active item",
    "binding",
    "bound",
    "current item",
    "current release",
    "show the active",
    "showing the wrong",
    "stale",
    "wrong release",
    "wrong status",
)
_SURFACE_TARGET_MAP: dict[str, tuple[str, ...]] = {
    "compass": (
        "src/odylith/runtime/surfaces/templates/compass_dashboard/page.html.j2",
        "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js",
        "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-shared.v1.js",
        "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-base.v1.css",
        "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-execution-waves.v1.css",
    ),
    "radar": (
        "src/odylith/runtime/surfaces/render_backlog_ui.py",
        "src/odylith/runtime/surfaces/render_backlog_ui_payload_runtime.py",
        "src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py",
    ),
    "registry": (
        "src/odylith/runtime/surfaces/render_registry_dashboard.py",
    ),
    "casebook": (
        "src/odylith/runtime/surfaces/render_casebook_dashboard.py",
    ),
    "shell": (
        "src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2",
        "src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js",
        "src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css",
    ),
    "tooling_shell": (
        "src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2",
        "src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js",
        "src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css",
    ),
    "atlas": (
        "src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py",
        "src/odylith/runtime/surfaces/render_mermaid_catalog.py",
    ),
}
_QUOTE_SPAN_RE = re.compile(r"([\"'`])([^\"'`\n]{2,200})\1")
_VERSION_RE = re.compile(r"\b\d+\.\d+\.\d+\b")


def _string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _surface_token(value: Any) -> str:
    return _string(value).lower().replace("-", "_").replace(" ", "_")


def _quoted_literals(text: str) -> list[str]:
    return _dedupe([str(match.group(2)).strip() for match in _QUOTE_SPAN_RE.finditer(str(text or "")) if str(match.group(2)).strip()])


def _strip_quoted_literals(text: str) -> str:
    stripped = _QUOTE_SPAN_RE.sub(" ", str(text or ""))
    return _string(stripped)


def normalize_turn_context(
    *,
    intent: str = "",
    surfaces: Sequence[str] = (),
    visible_text: Sequence[str] = (),
    active_tab: str = "",
    user_turn_id: str = "",
    supersedes_turn_id: str = "",
) -> dict[str, Any]:
    normalized_intent = _string(intent)
    normalized_visible_text = _dedupe([_string(token) for token in visible_text if _string(token)])
    normalized_surfaces = _dedupe([_surface_token(token) for token in surfaces if _surface_token(token)])
    normalized_active_tab = _surface_token(active_tab)
    if normalized_active_tab and normalized_active_tab not in normalized_surfaces:
        normalized_surfaces.append(normalized_active_tab)
    operator_ask = _strip_quoted_literals(normalized_intent) or normalized_intent
    quoted_literals = _quoted_literals(normalized_intent)
    for token in normalized_visible_text:
        if token not in quoted_literals:
            quoted_literals.append(token)
    return {
        "intent": normalized_intent,
        "surfaces": normalized_surfaces,
        "visible_text": normalized_visible_text,
        "active_tab": normalized_active_tab,
        "user_turn_id": _string(user_turn_id),
        "supersedes_turn_id": _string(supersedes_turn_id),
        "operator_ask": operator_ask,
        "quoted_literals": quoted_literals,
    }


def compact_turn_context(turn_context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "intent": _string(turn_context.get("intent")),
            "surfaces": _dedupe([_surface_token(token) for token in turn_context.get("surfaces", [])])
            if isinstance(turn_context.get("surfaces"), list)
            else [],
            "visible_text": _dedupe([_string(token) for token in turn_context.get("visible_text", [])])
            if isinstance(turn_context.get("visible_text"), list)
            else [],
            "active_tab": _surface_token(turn_context.get("active_tab")),
            "user_turn_id": _string(turn_context.get("user_turn_id")),
            "supersedes_turn_id": _string(turn_context.get("supersedes_turn_id")),
        }.items()
        if value not in ("", [], {}, None)
    }


def operator_ask_text(turn_context: Mapping[str, Any]) -> str:
    return _string(turn_context.get("operator_ask")) or _strip_quoted_literals(_string(turn_context.get("intent")))


def anchor_literals(turn_context: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    if isinstance(turn_context.get("quoted_literals"), list):
        values.extend(_string(token) for token in turn_context.get("quoted_literals", []))
    if isinstance(turn_context.get("visible_text"), list):
        values.extend(_string(token) for token in turn_context.get("visible_text", []))
    intent = _string(turn_context.get("intent"))
    for token in _VERSION_RE.findall(intent):
        values.append(token)
    return _dedupe([token for token in values if token])


def infer_turn_family(turn_context: Mapping[str, Any]) -> str:
    ask = operator_ask_text(turn_context).lower()
    if not ask:
        return ""
    if any(token in ask for token in _FAST_LANE_LAYOUT_TERMS):
        return "ui_layout"
    if any(token in ask for token in _FAST_LANE_BINDING_TERMS):
        return "surface_binding"
    if any(token in ask for token in _FAST_LANE_COPY_TERMS):
        return "surface_copy"
    return ""


def derive_lane_targeting(repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    profile = load_consumer_profile(repo_root=root)
    write_policy = dict(profile.get("odylith_write_policy", {})) if isinstance(profile.get("odylith_write_policy"), Mapping) else {}
    allow_mutations = bool(write_policy.get("allow_odylith_mutations"))
    repo_role = repo_role_from_local_shape(repo_root=root)
    lane = "dev_maintainer" if repo_role == PRODUCT_REPO_ROLE and allow_mutations else "consumer"
    protected_roots = _dedupe(
        [str(token).strip().strip("/") for token in write_policy.get("protected_roots", []) if str(token).strip().strip("/")]
    )
    return {
        "lane": lane,
        "repo_role": repo_role,
        "write_policy": {
            "odylith_fix_mode": _string(write_policy.get("odylith_fix_mode")),
            "allow_odylith_mutations": allow_mutations,
            "protected_roots": protected_roots,
        },
    }


def derive_presentation_policy(turn_context: Mapping[str, Any]) -> dict[str, Any]:
    family = infer_turn_family(turn_context)
    fast_lane = family in {"ui_layout", "surface_copy", "surface_binding"}
    return {
        "commentary_mode": "task_first_minimal" if fast_lane else "task_first",
        "suppress_routing_receipts": fast_lane,
        "surface_fast_lane": fast_lane,
    }


def compact_presentation_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "commentary_mode": _string(policy.get("commentary_mode")),
            "suppress_routing_receipts": bool(policy.get("suppress_routing_receipts")),
            "surface_fast_lane": bool(policy.get("surface_fast_lane")),
        }.items()
        if value not in ("", [], {}, None, False)
    }


def _path_under_roots(path_ref: str, roots: Sequence[str]) -> bool:
    normalized = str(path_ref or "").strip().strip("/")
    if not normalized:
        return False
    return any(
        normalized == root or normalized.startswith(f"{root}/")
        for root in roots
        if str(root).strip()
    )


def _candidate_target(*, path_ref: str, source: str, reason: str, surface: str = "", writable: bool = True) -> dict[str, Any]:
    payload = {
        "path": str(path_ref).strip(),
        "source": _string(source),
        "reason": _string(reason),
        "surface": _surface_token(surface),
        "writable": bool(writable),
    }
    return {key: value for key, value in payload.items() if value not in ("", [], {}, None)}


def _diagnostic_anchor(
    *,
    kind: str,
    value: str,
    label: str = "",
    path_ref: str = "",
    surface: str = "",
    source: str = "",
) -> dict[str, Any]:
    payload = {
        "kind": _string(kind),
        "value": _string(value),
        "label": _string(label),
        "path": str(path_ref).strip(),
        "surface": _surface_token(surface),
        "source": _string(source),
    }
    return {key: value for key, value in payload.items() if value not in ("", [], {}, None)}


def _search_literal_matches(*, repo_root: Path, literal: str, runtime_mode: str) -> list[dict[str, Any]]:
    text = _string(literal)
    if len(text) < 3:
        return []
    try:
        payload = projection_search_runtime.search_entities_payload(
            repo_root=repo_root,
            query=text,
            limit=5,
            runtime_mode=runtime_mode,
        )
    except Exception:
        return []
    return [dict(row) for row in payload.get("results", []) if isinstance(row, Mapping)]


def _surface_candidate_paths(*, repo_root: Path, surfaces: Sequence[str]) -> list[str]:
    root = Path(repo_root).resolve()
    paths: list[str] = []
    for surface in surfaces:
        for path_ref in _SURFACE_TARGET_MAP.get(_surface_token(surface), ()):
            if (root / path_ref).exists():
                paths.append(path_ref)
    return _dedupe(paths)


def resolve_turn_targets(
    *,
    repo_root: Path,
    turn_context: Mapping[str, Any],
    changed_paths: Sequence[str] = (),
    explicit_paths: Sequence[str] = (),
    claimed_paths: Sequence[str] = (),
    inferred_workstream: str = "",
    runtime_mode: str = "auto",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    lane_targeting = derive_lane_targeting(root)
    lane = str(lane_targeting.get("lane", "")).strip() or "consumer"
    write_policy = dict(lane_targeting.get("write_policy", {}))
    protected_roots = [str(token).strip() for token in write_policy.get("protected_roots", []) if str(token).strip()]
    allow_mutations = bool(write_policy.get("allow_odylith_mutations"))
    surface_tokens = (
        [_surface_token(token) for token in turn_context.get("surfaces", []) if _surface_token(token)]
        if isinstance(turn_context.get("surfaces"), list)
        else []
    )
    surfaces = _dedupe(
        [
            *surface_tokens,
            _surface_token(turn_context.get("active_tab")),
        ]
    )
    diagnostic_anchors: list[dict[str, Any]] = []
    if inferred_workstream:
        diagnostic_anchors.append(
            _diagnostic_anchor(
                kind="workstream",
                value=inferred_workstream,
                label=inferred_workstream,
                source="inferred_workstream",
            )
        )
    for surface in surfaces:
        diagnostic_anchors.append(
            _diagnostic_anchor(kind="surface", value=surface, label=surface, surface=surface, source="turn_context")
        )
    for literal in anchor_literals(turn_context):
        for row in _search_literal_matches(repo_root=root, literal=literal, runtime_mode=runtime_mode):
            diagnostic_anchors.append(
                _diagnostic_anchor(
                    kind=str(row.get("kind", "")).strip() or "entity",
                    value=str(row.get("entity_id", row.get("path", literal))).strip() or literal,
                    label=str(row.get("title", row.get("display_label", literal))).strip() or literal,
                    path_ref=str(row.get("path", "")).strip(),
                    surface=surfaces[0] if surfaces else "",
                    source="literal_match",
                )
            )
    diagnostic_anchors = _dedupe_mappings(diagnostic_anchors, keys=("kind", "value", "path", "surface"))

    candidate_targets: list[dict[str, Any]] = []
    for path_ref in _dedupe([*map(str, changed_paths), *map(str, explicit_paths), *map(str, claimed_paths)]):
        if not path_ref.strip():
            continue
        writable = allow_mutations or not _path_under_roots(path_ref, protected_roots)
        candidate_targets.append(
            _candidate_target(
                path_ref=path_ref,
                source="path_scope",
                reason="Current turn already carries this path in scope.",
                surface=surfaces[0] if surfaces else "",
                writable=writable,
            )
        )
    if lane == "dev_maintainer":
        for path_ref in _surface_candidate_paths(repo_root=root, surfaces=surfaces):
            candidate_targets.append(
                _candidate_target(
                    path_ref=path_ref,
                    source="surface_map",
                    reason="Surface fast lane maps this UI turn to the owning Odylith renderer/template slice.",
                    surface=surfaces[0] if surfaces else "",
                    writable=True,
                )
            )
    candidate_targets = _dedupe_mappings(candidate_targets, keys=("path", "source", "surface"))
    has_writable_targets = any(bool(row.get("writable")) for row in candidate_targets)
    requires_more_consumer_context = lane == "consumer" and not has_writable_targets
    consumer_failover = ""
    if lane == "consumer" and not has_writable_targets and diagnostic_anchors:
        consumer_failover = "maintainer_ready_feedback_plus_bounded_narrowing"
    return {
        "lane": lane,
        "candidate_targets": candidate_targets,
        "diagnostic_anchors": diagnostic_anchors,
        "has_writable_targets": has_writable_targets,
        "requires_more_consumer_context": requires_more_consumer_context,
        "consumer_failover": consumer_failover,
    }


def compact_target_resolution(resolution: Mapping[str, Any]) -> dict[str, Any]:
    candidate_targets = [
        {
            "path": str(row.get("path", "")).strip(),
            **({"source": _string(row.get("source"))} if _string(row.get("source")) else {}),
            **({"reason": _string(row.get("reason"))} if _string(row.get("reason")) else {}),
            **({"surface": _surface_token(row.get("surface"))} if _surface_token(row.get("surface")) else {}),
            "writable": bool(row.get("writable")),
        }
        for row in resolution.get("candidate_targets", [])
        if isinstance(row, Mapping) and str(row.get("path", "")).strip()
    ]
    diagnostic_anchors = [
        {
            key: value
            for key, value in {
                "kind": _string(row.get("kind")),
                "value": _string(row.get("value")),
                "label": _string(row.get("label")),
                "path": str(row.get("path", "")).strip(),
                "surface": _surface_token(row.get("surface")),
                "source": _string(row.get("source")),
            }.items()
            if value not in ("", [], {}, None)
        }
        for row in resolution.get("diagnostic_anchors", [])
        if isinstance(row, Mapping) and _string(row.get("value"))
    ]
    compact: dict[str, Any] = {}
    lane = _string(resolution.get("lane"))
    if lane:
        compact["lane"] = lane
    if candidate_targets:
        compact["candidate_targets"] = candidate_targets[:4]
    if diagnostic_anchors:
        compact["diagnostic_anchors"] = diagnostic_anchors[:6]
    compact["has_writable_targets"] = bool(resolution.get("has_writable_targets"))
    compact["requires_more_consumer_context"] = bool(resolution.get("requires_more_consumer_context"))
    consumer_failover = _string(resolution.get("consumer_failover"))
    if consumer_failover:
        compact["consumer_failover"] = consumer_failover
    return compact


def _dedupe_mappings(rows: Sequence[Mapping[str, Any]], *, keys: Sequence[str]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    ordered: list[dict[str, Any]] = []
    for row in rows:
        key = tuple(_string(row.get(field)) for field in keys)
        if not any(key):
            continue
        if key in seen:
            continue
        seen.add(key)
        ordered.append(dict(row))
    return ordered


__all__ = [
    "anchor_literals",
    "compact_presentation_policy",
    "compact_target_resolution",
    "compact_turn_context",
    "derive_lane_targeting",
    "derive_presentation_policy",
    "infer_turn_family",
    "normalize_turn_context",
    "operator_ask_text",
    "resolve_turn_targets",
]

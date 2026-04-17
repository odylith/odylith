from __future__ import annotations
from pathlib import Path
import re
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import operator_readout
from odylith.runtime.governance import proof_state
from odylith.runtime.intervention_engine import claim_runtime
from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import delivery_runtime
from odylith.runtime.surfaces import dashboard_shell_links


_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_BUG_ID_RE = re.compile(r"^CB-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_COMPONENT_SPEC_RE = re.compile(
    r"^odylith/registry/source/components/(?P<component>[A-Za-z0-9._-]+)/CURRENT_SPEC\.md$"
)
_RADAR_IDEA_PREFIX = "odylith/radar/source/ideas/"
_PLAN_PREFIX = "odylith/technical-plans/"
_BUG_PREFIX = "odylith/casebook/bugs/"
_ATLAS_PREFIX = "odylith/atlas/source/"
_SUPPLEMENTAL_PRIORITY = ("risks", "insight", "history")
_EXPLICIT_SIGNAL_PRIORITY = ("risks", "insight", "history")
_RECURSIVE_PATH_KEYS = ("idea_file", "promoted_to_plan", "plan_path", "path", "source_path", "relative_path", "spec_ref", "bug_path", "diagram_path")
_RISK_BOOL_KEYS = {
    "plan_binding_required",
    "governed_surface_sync_required",
    "narrowing_required",
    "requires_widening",
}
_RISK_COUNT_KEYS = {
    "validation_obligation_count",
    "diagram_watch_gap_count",
    "unresolved_question_count",
    "operator_consequence_count",
}
_HISTORY_KEY_HINTS = ("history", "historical", "reopen", "reopened", "supersed", "linked_bug", "bug")
_MEANINGFUL_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}")
_TOKEN_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "into",
    "its",
    "just",
    "not",
    "now",
    "off",
    "one",
    "only",
    "out",
    "same",
    "so",
    "stay",
    "that",
    "the",
    "then",
    "this",
    "too",
    "use",
    "with",
    "work",
}
_VISIBILITY_PRODUCT_TOKENS = {
    "ambient",
    "assist",
    "intervention",
    "interventions",
    "observation",
    "observations",
    "odylith",
    "proposal",
    "proposals",
}
_VISIBILITY_DELIVERY_TOKENS = {
    "chat",
    "hook",
    "hooks",
    "output",
    "outputs",
    "see",
    "seen",
    "show",
    "showing",
    "shown",
    "surface",
    "surfaced",
    "surfacing",
    "visible",
    "visibility",
    "ux",
}


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace("-", "_").replace(" ", "_")


def _sequence_count(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len([item for item in value if _normalize_string(item)])
    return 1 if _normalize_string(value) else 0


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _first_present(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            if _normalize_string(value):
                return value
            continue
        if value is not None:
            return value
    return None


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    token = _normalize_token(value)
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"", "0", "false", "no", "off"}:
        return False
    return bool(value)


def _mapping_lookup(payload: Mapping[str, Any], key: str) -> Any:
    wanted = _normalize_token(key)
    for raw_key, raw_value in payload.items():
        if _normalize_token(raw_key) == wanted:
            return raw_value
    return None


def _nested_mapping(payload: Mapping[str, Any], *path: str) -> dict[str, Any]:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return {}
        current = _mapping_lookup(current, key)
    return dict(current) if isinstance(current, Mapping) else {}


def _count_phrase(count: int, singular: str, plural: str | None = None) -> str:
    noun = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {noun}"


def _join_phrases(parts: Sequence[str]) -> str:
    filtered = [_normalize_string(part) for part in parts if _normalize_string(part)]
    if not filtered:
        return ""
    if len(filtered) == 1:
        return filtered[0]
    if len(filtered) == 2:
        return f"{filtered[0]}, then {filtered[1]}"
    return ", ".join(filtered[:-1]) + f", and {filtered[-1]}"


def _join_items(parts: Sequence[str]) -> str:
    filtered = [_normalize_string(part) for part in parts if _normalize_string(part)]
    if not filtered:
        return ""
    if len(filtered) == 1:
        return filtered[0]
    if len(filtered) == 2:
        return f"{filtered[0]} and {filtered[1]}"
    return ", ".join(filtered[:-1]) + f", and {filtered[-1]}"


def _lower_sentence_start(value: str) -> str:
    token = _normalize_string(value)
    return token[:1].lower() + token[1:] if len(token) > 1 and token[:1].isalpha() else token


def _sentence_with_terminal_punctuation(value: str) -> str:
    token = _normalize_string(value)
    if not token:
        return ""
    return token if token.endswith(("!", "?", ".")) else f"{token}."


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = _normalize_string(raw)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _recursive_items(value: Any) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            rows.append((_normalize_token(key), nested))
            rows.extend(_recursive_items(nested))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            rows.extend(_recursive_items(nested))
    return rows


def _recursive_strings(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        rows: list[str] = []
        for nested in value.values():
            rows.extend(_recursive_strings(nested))
        return rows
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        rows: list[str] = []
        for nested in value:
            rows.extend(_recursive_strings(nested))
        return rows
    token = _normalize_string(value)
    return [token] if token else []


def _normalize_repo_paths(*, repo_root: Path | None, values: Sequence[str]) -> list[str]:
    if repo_root is not None:
        return governance.normalize_changed_paths(repo_root=repo_root, values=values)
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = _normalize_string(raw).lstrip("./")
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _label(kind: str, *, markdown: bool) -> str:
    title = {
        "assist": "Odylith Assist",
        "insight": "Odylith Insight",
        "history": "Odylith History",
        "risks": "Odylith Risks",
    }[kind]
    return f"**{title}:**" if markdown else f"{title}:"


def _artifact_kind(entity_id: str) -> str:
    if _WORKSTREAM_ID_RE.match(entity_id):
        return "workstream"
    if _BUG_ID_RE.match(entity_id):
        return "bug"
    if _DIAGRAM_ID_RE.match(entity_id):
        return "diagram"
    return "component"


def _artifact_href(kind: str, entity_id: str) -> str:
    if kind == "workstream":
        return dashboard_shell_links.shell_href(tab="radar", workstream=entity_id)
    if kind == "bug":
        return dashboard_shell_links.shell_href(tab="casebook", bug=entity_id)
    if kind == "diagram":
        return dashboard_shell_links.shell_href(tab="atlas", diagram=entity_id)
    return dashboard_shell_links.shell_href(tab="registry", component=entity_id)


def _artifact_ref(kind: str, entity_id: str, *, source_paths: Sequence[str] = ()) -> dict[str, Any]:
    href = _artifact_href(kind, entity_id)
    return {
        "kind": kind,
        "id": entity_id,
        "href": href,
        "markdown_ref": f"[{entity_id}]({href})" if href else entity_id,
        "plain_ref": entity_id,
        "source_paths": _dedupe_strings(source_paths),
    }


def _path_matches(path_ref: str, candidate: str) -> bool:
    path_token = _normalize_string(path_ref).lstrip("./")
    candidate_token = _normalize_string(candidate).lstrip("./")
    if not path_token or not candidate_token:
        return False
    return (
        path_token == candidate_token
        or path_token.endswith(candidate_token)
        or candidate_token.endswith(path_token)
    )


def _context_artifact_rows(*, repo_root: Path | None, value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            workstream_id = next(
                (
                    _normalize_string(node.get(key))
                    for key in ("idea_id", "workstream_id", "entity_id", "selected_id")
                    if _WORKSTREAM_ID_RE.match(_normalize_string(node.get(key)))
                ),
                "",
            )
            if workstream_id:
                paths = _normalize_repo_paths(
                    repo_root=repo_root,
                    values=[_normalize_string(node.get(key)) for key in _RECURSIVE_PATH_KEYS],
                )
                rows.append(_artifact_ref("workstream", workstream_id, source_paths=paths))

            bug_id = next(
                (
                    _normalize_string(node.get(key))
                    for key in ("bug_key", "bug_id", "entity_id")
                    if _BUG_ID_RE.match(_normalize_string(node.get(key)))
                ),
                "",
            )
            if bug_id:
                paths = _normalize_repo_paths(
                    repo_root=repo_root,
                    values=[_normalize_string(node.get(key)) for key in _RECURSIVE_PATH_KEYS],
                )
                rows.append(_artifact_ref("bug", bug_id, source_paths=paths))

            diagram_id = next(
                (
                    _normalize_string(node.get(key))
                    for key in ("diagram_id", "entity_id", "selected_id")
                    if _DIAGRAM_ID_RE.match(_normalize_string(node.get(key)))
                ),
                "",
            )
            if diagram_id:
                paths = _normalize_repo_paths(
                    repo_root=repo_root,
                    values=[_normalize_string(node.get(key)) for key in _RECURSIVE_PATH_KEYS],
                )
                rows.append(_artifact_ref("diagram", diagram_id, source_paths=paths))

            component_id = _normalize_string(node.get("component_id"))
            if component_id:
                paths = _normalize_repo_paths(
                    repo_root=repo_root,
                    values=[_normalize_string(node.get(key)) for key in _RECURSIVE_PATH_KEYS],
                )
                rows.append(_artifact_ref("component", component_id, source_paths=paths))

            for nested in node.values():
                walk(nested)
            return
        if isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for nested in node:
                walk(nested)

    walk(value)
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("kind")), str(row.get("id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _request_context_payload(request: Any) -> dict[str, Any]:
    payload = _field(request, "context_signals")
    return dict(payload) if isinstance(payload, Mapping) else {}


def _presentation_policy_snapshot(*, request: Any, adoption: Mapping[str, Any]) -> dict[str, Any]:
    context_payload = _request_context_payload(request)
    execution_engine_summary = _nested_mapping(context_payload, "execution_engine_summary")
    packet_summary = _nested_mapping(context_payload, "packet_summary")
    presentation_policy = _nested_mapping(context_payload, "presentation_policy")
    context_packet_presentation_policy = _nested_mapping(context_payload, "context_packet", "presentation_policy")
    return {
        "commentary_mode": _normalize_token(
            _first_present(
                adoption.get("execution_engine_commentary_mode"),
                _mapping_lookup(execution_engine_summary, "execution_engine_commentary_mode"),
                _mapping_lookup(context_payload, "execution_engine_commentary_mode"),
                _mapping_lookup(context_payload, "latest_execution_engine_commentary_mode"),
                _mapping_lookup(packet_summary, "presentation_policy_commentary_mode"),
                _mapping_lookup(presentation_policy, "commentary_mode"),
                _mapping_lookup(context_packet_presentation_policy, "commentary_mode"),
            )
        ),
        "suppress_routing_receipts": _bool_value(
            _first_present(
                adoption.get("execution_engine_suppress_routing_receipts"),
                _mapping_lookup(execution_engine_summary, "execution_engine_suppress_routing_receipts"),
                _mapping_lookup(context_payload, "execution_engine_suppress_routing_receipts"),
                _mapping_lookup(context_payload, "latest_execution_engine_suppress_routing_receipts"),
                _mapping_lookup(packet_summary, "presentation_policy_suppress_routing_receipts"),
                _mapping_lookup(presentation_policy, "suppress_routing_receipts"),
                _mapping_lookup(context_packet_presentation_policy, "suppress_routing_receipts"),
            )
        ),
        "surface_fast_lane": _bool_value(
            _first_present(
                adoption.get("execution_engine_surface_fast_lane"),
                _mapping_lookup(execution_engine_summary, "execution_engine_surface_fast_lane"),
                _mapping_lookup(context_payload, "execution_engine_surface_fast_lane"),
                _mapping_lookup(context_payload, "latest_execution_engine_surface_fast_lane"),
                _mapping_lookup(packet_summary, "presentation_policy_surface_fast_lane"),
                _mapping_lookup(presentation_policy, "surface_fast_lane"),
                _mapping_lookup(context_packet_presentation_policy, "surface_fast_lane"),
            )
        ),
    }


def _proof_ref_artifact(row: Mapping[str, Any]) -> dict[str, Any] | None:
    kind = _normalize_token(row.get("kind"))
    value = _normalize_string(row.get("value"))
    if kind == "workstream" and _WORKSTREAM_ID_RE.match(value):
        return _artifact_ref("workstream", value)
    if kind == "diagram" and _DIAGRAM_ID_RE.match(value):
        return _artifact_ref("diagram", value)
    if kind in {"component", "bug"}:
        token = value.split(":", 1)[-1] if ":" in value else value
        if kind == "component" and token:
            return _artifact_ref("component", token)
        if kind == "bug" and _BUG_ID_RE.match(token):
            return _artifact_ref("bug", token)
    return None
def _request_anchor_artifacts(*, request: Any, repo_root: Path | None, context_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(
        _artifact_ref("workstream", entity_id)
        for entity_id in _dedupe_strings(
            [
                _normalize_string(token)
                for token in _field(request, "workstreams") or []
                if _WORKSTREAM_ID_RE.match(_normalize_string(token))
            ]
        )
    )
    rows.extend(
        _artifact_ref("component", entity_id)
        for entity_id in _dedupe_strings(
            [_normalize_string(token) for token in _field(request, "components") or [] if _normalize_string(token)]
        )
    )
    seen = {(row["kind"], row["id"]) for row in rows}
    for row in context_rows:
        key = (str(row.get("kind")), str(row.get("id")))
        if key in seen:
            continue
        if key[0] not in {"workstream", "component", "diagram", "bug"}:
            continue
        rows.append(dict(row))
        seen.add(key)
    return rows[:4]
def _resolve_updated_artifacts(
    *,
    repo_root: Path | None,
    request: Any,
    final_changed_paths: Sequence[str],
    context_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    normalized_paths = _normalize_repo_paths(repo_root=repo_root, values=final_changed_paths)
    context_rows = list(context_rows) if context_rows is not None else _context_artifact_rows(repo_root=repo_root, value=_request_context_payload(request))
    request_workstreams = [
        _normalize_string(token)
        for token in _field(request, "workstreams") or []
        if _WORKSTREAM_ID_RE.match(_normalize_string(token))
    ]
    request_components = [
        _normalize_string(token)
        for token in _field(request, "components") or []
        if _normalize_string(token)
    ]
    request_diagrams = [row["id"] for row in context_rows if row["kind"] == "diagram"]
    request_bugs = [row["id"] for row in context_rows if row["kind"] == "bug"]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(row: dict[str, Any] | None) -> None:
        if not row:
            return
        key = (str(row.get("kind")), str(row.get("id")))
        if key in seen:
            return
        seen.add(key)
        rows.append(row)

    for path_ref in normalized_paths:
        component_match = _COMPONENT_SPEC_RE.match(path_ref)
        if component_match:
            add(_artifact_ref("component", component_match.group("component"), source_paths=[path_ref]))
            continue
        if path_ref.startswith((_RADAR_IDEA_PREFIX, _PLAN_PREFIX)):
            exact = next(
                (
                    dict(row)
                    for row in context_rows
                    if row.get("kind") == "workstream"
                    and any(_path_matches(path_ref, candidate) for candidate in row.get("source_paths", []))
                ),
                None,
            )
            if exact is not None:
                exact["source_paths"] = _dedupe_strings([*exact.get("source_paths", []), path_ref])
                add(exact)
                continue
            if len(request_workstreams) == 1:
                add(_artifact_ref("workstream", request_workstreams[0], source_paths=[path_ref]))
            continue
        if path_ref.startswith(_BUG_PREFIX):
            exact = next(
                (
                    dict(row)
                    for row in context_rows
                    if row.get("kind") == "bug"
                    and any(_path_matches(path_ref, candidate) for candidate in row.get("source_paths", []))
                ),
                None,
            )
            if exact is not None:
                exact["source_paths"] = _dedupe_strings([*exact.get("source_paths", []), path_ref])
                add(exact)
                continue
            if len(request_bugs) == 1:
                add(_artifact_ref("bug", request_bugs[0], source_paths=[path_ref]))
            continue
        if path_ref.startswith(_ATLAS_PREFIX):
            exact = next(
                (
                    dict(row)
                    for row in context_rows
                    if row.get("kind") == "diagram"
                    and any(_path_matches(path_ref, candidate) for candidate in row.get("source_paths", []))
                ),
                None,
            )
            if exact is not None:
                exact["source_paths"] = _dedupe_strings([*exact.get("source_paths", []), path_ref])
                add(exact)
                continue
            if len(request_diagrams) == 1:
                add(_artifact_ref("diagram", request_diagrams[0], source_paths=[path_ref]))
            continue
        if path_ref == "odylith/registry/source/component_registry.v1.json" and len(request_components) == 1:
            add(_artifact_ref("component", request_components[0], source_paths=[path_ref]))

    return rows[:4]


def _artifact_phrase(rows: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    if not rows:
        return "", ""
    markdown = _join_items([str(row.get("markdown_ref", "")).strip() for row in rows])
    plain = _join_items([str(row.get("plain_ref", "")).strip() for row in rows])
    return f"updating {markdown}", f"updating {plain}"


def _affected_contract_rows(
    *,
    updated_artifacts: Sequence[Mapping[str, Any]],
    request: Any,
    repo_root: Path | None,
    context_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    allowed_kinds = {"workstream", "component", "diagram", "bug"}

    def add(row: Mapping[str, Any]) -> None:
        kind = _normalize_token(row.get("kind"))
        entity_id = _normalize_string(row.get("id"))
        if kind not in allowed_kinds or not entity_id:
            return
        key = (kind, entity_id)
        if key in seen:
            return
        seen.add(key)
        rows.append(dict(row))

    for row in updated_artifacts:
        if isinstance(row, Mapping):
            add(row)
    for row in _request_anchor_artifacts(
        request=request,
        repo_root=repo_root,
        context_rows=context_rows,
    ):
        add(row)
    return rows[:4]


def _affected_contract_phrase(rows: Sequence[Mapping[str, Any]], *, verb: str) -> tuple[str, str]:
    if not rows:
        return "", ""
    markdown = _join_items([str(row.get("markdown_ref", "")).strip() for row in rows])
    plain = _join_items([str(row.get("plain_ref", "")).strip() for row in rows])
    return f"{verb} affected governance contracts {markdown}", f"{verb} affected governance contracts {plain}"


def _visibility_feedback_phrase(*, request: Any, assistant_summary: str = "") -> tuple[str, str]:
    """Detect product-feedback turns where Assist should not stay silent.

    This is deliberately narrow: a generic short turn still suppresses Assist,
    but explicit feedback about Odylith visibility, hooks, interventions,
    ambient highlights, Observations, Proposals, or Assist deserves a grounded
    closeout even when no files changed.
    """

    text = _normalize_string(
        " ".join(
            [
                str(_field(request, "prompt") or ""),
                str(assistant_summary or ""),
            ]
        )
    )
    if not text:
        return "", ""
    tokens = _meaningful_tokens(text)
    product_hits = tokens & _VISIBILITY_PRODUCT_TOKENS
    delivery_hits = tokens & _VISIBILITY_DELIVERY_TOKENS
    if not product_hits or not delivery_hits:
        return "", ""
    if "odylith" not in tokens and len(product_hits | delivery_hits) < 3:
        return "", ""
    phrase = "carrying the intervention visibility feedback into this closeout"
    return phrase, phrase


def _meaningful_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for match in _MEANINGFUL_TOKEN_RE.findall(_normalize_string(value)):
            token = match.casefold()
            if token in _TOKEN_STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def _signal_information_tokens(payload: Mapping[str, Any]) -> set[str]:
    rows: list[str] = []
    rows.extend(str(item) for item in payload.get("facts", []) or [])
    rows.extend(str(row.get("id", "")).strip() for row in payload.get("refs", []) or [] if isinstance(row, Mapping))
    rows.append(str(payload.get("plain_text", "")))
    return _meaningful_tokens(*rows)


def _assist_information_tokens(payload: Mapping[str, Any]) -> set[str]:
    rows: list[str] = [str(payload.get("plain_text", "")), str(payload.get("style", ""))]
    rows.extend(str(row.get("id", "")).strip() for row in payload.get("updated_artifacts", []) or [] if isinstance(row, Mapping))
    rows.extend(str(row.get("id", "")).strip() for row in payload.get("affected_contracts", []) or [] if isinstance(row, Mapping))
    return _meaningful_tokens(*rows)


def _signal_adds_new_information(*, signal: Mapping[str, Any], assist: Mapping[str, Any]) -> bool:
    if not signal.get("eligible"):
        return False
    if not assist.get("eligible"):
        return True
    assist_ref_ids = {
        str(row.get("id", "")).strip()
        for row in assist.get("updated_artifacts", []) or []
        if isinstance(row, Mapping) and str(row.get("id", "")).strip()
    }
    signal_ref_ids = {
        str(row.get("id", "")).strip()
        for row in signal.get("refs", []) or []
        if isinstance(row, Mapping) and str(row.get("id", "")).strip()
    }
    if signal_ref_ids and assist_ref_ids and signal_ref_ids.issubset(assist_ref_ids):
        if str(signal.get("kind", "")) in {"insight", "history"}:
            return False
    signal_tokens = _signal_information_tokens(signal)
    assist_tokens = _assist_information_tokens(assist)
    novel_tokens = signal_tokens - assist_tokens
    if str(signal.get("kind", "")) == "risks":
        return bool(novel_tokens) or str(signal.get("severity", "")).strip().lower() == "high"
    return len(novel_tokens) >= 2


def _suppressed_closeout_signal(payload: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    row = dict(payload)
    row["eligible"] = False
    row["text"] = ""
    row["plain_text"] = ""
    row["markdown_text"] = ""
    row["render_hint"] = "suppress"
    row["suppressed_reason"] = reason
    return row


def _evidence_metrics(
    *,
    request: Any,
    decision: Any,
    adoption: Mapping[str, Any],
) -> dict[str, Any]:
    presentation_policy = _presentation_policy_snapshot(request=request, adoption=adoption)
    candidate_path_count = _sequence_count(_field(request, "candidate_paths"))
    claimed_path_count = _sequence_count(_field(request, "claimed_paths"))
    workstream_count = _sequence_count(_field(request, "workstreams"))
    component_count = _sequence_count(_field(request, "components"))
    validation_count = _sequence_count(_field(request, "validation_commands"))
    delegated_leaf_count = _sequence_count(_field(decision, "subtasks"))
    main_thread_followup_count = _sequence_count(_field(decision, "main_thread_followups"))
    grounded = bool(adoption.get("grounded"))
    route_ready = bool(adoption.get("route_ready"))
    grounded_delegate = bool(adoption.get("grounded_delegate"))
    requires_widening = bool(adoption.get("requires_widening"))
    return {
        "candidate_path_count": candidate_path_count,
        "claimed_path_count": claimed_path_count,
        "focus_path_count": candidate_path_count or claimed_path_count,
        "workstream_count": workstream_count,
        "component_count": component_count,
        "governance_anchor_count": workstream_count + component_count,
        "validation_count": validation_count,
        "delegated_leaf_count": delegated_leaf_count,
        "main_thread_followup_count": main_thread_followup_count,
        "grounded": grounded,
        "route_ready": route_ready,
        "grounded_delegate": grounded_delegate,
        "requires_widening": requires_widening,
        "mode": _normalize_token(_field(decision, "mode")),
        "commentary_mode": str(presentation_policy.get("commentary_mode", "")).strip(),
        "suppress_routing_receipts": bool(presentation_policy.get("suppress_routing_receipts")),
        "surface_fast_lane": bool(presentation_policy.get("surface_fast_lane")),
    }


def _suppressed_assist_payload(
    *,
    metrics: Mapping[str, Any],
    reason: str,
    updated_artifacts: Sequence[Mapping[str, Any]],
    affected_contracts: Sequence[Mapping[str, Any]] = (),
    changed_path_source: str,
) -> dict[str, Any]:
    return {
        "eligible": False,
        "style": "",
        "label": _label("assist", markdown=False),
        "preferred_markdown_label": _label("assist", markdown=True),
        "text": "",
        "plain_text": "",
        "markdown_text": "",
        "user_win": "",
        "delta": "",
        "proof": "",
        "updated_artifacts": [dict(row) for row in updated_artifacts],
        "affected_contracts": [dict(row) for row in affected_contracts],
        "changed_path_source": changed_path_source,
        "suppressed_reason": reason,
        "metrics": dict(metrics),
    }


def _suppressed_signal_payload(
    *,
    kind: str,
    metrics: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "eligible": False,
        "label": _label(kind, markdown=False),
        "preferred_markdown_label": _label(kind, markdown=True),
        "text": "",
        "plain_text": "",
        "markdown_text": "",
        "facts": [],
        "refs": [],
        "render_hint": "suppress",
        "confidence": "",
        "severity": "",
        "suppressed_reason": reason,
        "metrics": dict(metrics),
    }


def _signal_payload(
    *,
    kind: str,
    metrics: Mapping[str, Any],
    markdown_text: str,
    plain_text: str,
    facts: Sequence[str],
    refs: Sequence[Mapping[str, Any]],
    render_hint: str,
    confidence: str = "",
    severity: str = "",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "eligible": True,
        "label": _label(kind, markdown=False),
        "preferred_markdown_label": _label(kind, markdown=True),
        "text": markdown_text,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "facts": _dedupe_strings(list(facts)),
        "refs": [dict(row) for row in refs],
        "render_hint": render_hint,
        "confidence": confidence,
        "severity": severity,
        "suppressed_reason": "",
        "metrics": dict(metrics),
    }


def _history_artifact_refs(
    *,
    request: Any,
    repo_root: Path | None,
    anchor_artifacts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    payload = _request_context_payload(request)
    rows: list[dict[str, Any]] = []
    anchor_ids = {str(row.get("id", "")).strip() for row in anchor_artifacts}
    for key, value in _recursive_items(payload):
        if not any(hint in key for hint in _HISTORY_KEY_HINTS):
            continue
        for token in _recursive_strings(value):
            entity_id = _normalize_string(token)
            if entity_id in anchor_ids:
                continue
            if _WORKSTREAM_ID_RE.match(entity_id):
                rows.append(_artifact_ref("workstream", entity_id))
            elif _BUG_ID_RE.match(entity_id):
                rows.append(_artifact_ref("bug", entity_id))
            elif _DIAGRAM_ID_RE.match(entity_id):
                rows.append(_artifact_ref("diagram", entity_id))
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("kind")), str(row.get("id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:3]


def _tribunal_signal_refs(
    *,
    tribunal_context: Mapping[str, Any],
    anchor_artifacts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [dict(row) for row in anchor_artifacts[:2]]
    seen = {(str(row.get("kind")), str(row.get("id"))) for row in rows}
    for scope in tribunal_context.get("scope_signals", []) or []:
        if not isinstance(scope, Mapping):
            continue
        candidates = [
            *(scope.get("operator_readout", {}).get("proof_refs", []) if isinstance(scope.get("operator_readout"), Mapping) else []),
            *(scope.get("evidence_refs", []) if isinstance(scope.get("evidence_refs"), list) else []),
        ]
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            ref = _proof_ref_artifact(candidate)
            if ref is None:
                continue
            key = (str(ref.get("kind")), str(ref.get("id")))
            if key in seen:
                continue
            seen.add(key)
            rows.append(ref)
            if len(rows) >= 3:
                return rows
    return rows


def _risk_summary(request: Any, adoption: Mapping[str, Any]) -> tuple[list[str], str]:
    payload = _request_context_payload(request)
    reasons: list[str] = []
    if bool(adoption.get("requires_widening")):
        reasons.append("the packet still wants widening")
    if bool(adoption.get("narrowing_required")):
        reasons.append("narrowing is still required")
    if bool(adoption.get("diagram_watch_gap_count")):
        reasons.append(_count_phrase(int(adoption.get("diagram_watch_gap_count") or 0), "diagram watch gap"))
    for key, value in _recursive_items(payload):
        if key in _RISK_BOOL_KEYS and bool(value):
            phrase = key.replace("_", " ")
            if phrase == "requires widening":
                phrase = "the packet still wants widening"
            elif phrase == "narrowing required":
                phrase = "narrowing is still required"
            reasons.append(phrase)
        if key in _RISK_COUNT_KEYS:
            try:
                count = int(value or 0)
            except (TypeError, ValueError):
                count = 0
            if count <= 0:
                continue
            if key == "validation_obligation_count":
                reasons.append(_count_phrase(count, "validation obligation"))
            elif key == "diagram_watch_gap_count":
                reasons.append(_count_phrase(count, "diagram watch gap"))
            elif key == "unresolved_question_count":
                reasons.append(_count_phrase(count, "unresolved question"))
            elif key == "operator_consequence_count":
                reasons.append(_count_phrase(count, "operator consequence"))
    reasons = _dedupe_strings(reasons)
    severity = "high" if any("widening" in reason or "narrowing" in reason for reason in reasons) else "medium"
    return reasons, severity


def _compose_insight_signal(
    *,
    metrics: Mapping[str, Any],
    anchor_artifacts: Sequence[Mapping[str, Any]],
    tribunal_context: Mapping[str, Any],
) -> dict[str, Any]:
    systemic_brief = tribunal_context.get("systemic_brief", {})
    if not isinstance(systemic_brief, Mapping):
        systemic_brief = {}
    latent_causes = _dedupe_strings([str(token) for token in systemic_brief.get("latent_causes", []) or []])
    if latent_causes and anchor_artifacts:
        refs = _tribunal_signal_refs(tribunal_context=tribunal_context, anchor_artifacts=anchor_artifacts)
        cause_phrase = _join_items(latent_causes[:2])
        markdown_refs = _join_items([str(row.get("markdown_ref", "")).strip() for row in refs[:2]])
        plain_refs = _join_items([str(row.get("plain_ref", "")).strip() for row in refs[:2]])
        markdown_text = f"{_label('insight', markdown=True)} the real pressure here smells more like {cause_phrase} than raw code spread, which is why {markdown_refs or 'the governed surfaces'} matter more than one more repo lap."
        plain_text = f"{_label('insight', markdown=False)} the real pressure here smells more like {cause_phrase} than raw code spread, which is why {plain_refs or 'the governed surfaces'} matter more than one more repo lap."
        return _signal_payload(kind="insight", metrics=metrics, markdown_text=markdown_text, plain_text=plain_text, facts=latent_causes[:2], refs=refs[:2], render_hint="explicit_label", confidence="high")
    if not anchor_artifacts:
        return _suppressed_signal_payload(kind="insight", metrics=metrics, reason="no_anchor_artifacts")
    if metrics["governance_anchor_count"] <= 0 and metrics["focus_path_count"] <= 0:
        return _suppressed_signal_payload(kind="insight", metrics=metrics, reason="no_non_obvious_anchor")
    refs = list(anchor_artifacts[:2])
    markdown_refs = _join_items([str(row.get("markdown_ref", "")).strip() for row in refs])
    plain_refs = _join_items([str(row.get("plain_ref", "")).strip() for row in refs])
    facts = [
        "the packet already carried governed anchors",
        "staying narrow changed the next move",
    ]
    if metrics["workstream_count"] > 0 and metrics["component_count"] > 0:
        markdown_text = (
            f"{_label('insight', markdown=True)} the center of gravity was already {markdown_refs}, "
            "so widening here would have been theater."
        )
        plain_text = (
            f"{_label('insight', markdown=False)} the center of gravity was already {plain_refs}, "
            "so widening here would have been theater."
        )
        return _signal_payload(
            kind="insight",
            metrics=metrics,
            markdown_text=markdown_text,
            plain_text=plain_text,
            facts=facts,
            refs=refs,
            render_hint="explicit_label",
            confidence="high",
        )
    markdown_text = (
        f"{_label('insight', markdown=True)} the governed anchors were already on the table, "
        "which is why this stayed smaller than it first looked."
    )
    plain_text = (
        f"{_label('insight', markdown=False)} the governed anchors were already on the table, "
        "which is why this stayed smaller than it first looked."
    )
    return _signal_payload(
        kind="insight",
        metrics=metrics,
        markdown_text=markdown_text,
        plain_text=plain_text,
        facts=facts,
        refs=refs,
        render_hint="ambient_inline",
        confidence="medium",
    )


def _compose_history_signal(
    *,
    metrics: Mapping[str, Any],
    history_refs: Sequence[Mapping[str, Any]],
    anchor_artifacts: Sequence[Mapping[str, Any]],
    tribunal_context: Mapping[str, Any],
) -> dict[str, Any]:
    if not history_refs:
        live_scope = next((row for row in tribunal_context.get("scope_signals", []) or [] if isinstance(row, Mapping) and row.get("case_refs")), None)
        if isinstance(live_scope, Mapping):
            refs = _tribunal_signal_refs(tribunal_context=tribunal_context, anchor_artifacts=anchor_artifacts)
            markdown_refs = _join_items([str(row.get("markdown_ref", "")).strip() for row in refs[:2]])
            plain_refs = _join_items([str(row.get("plain_ref", "")).strip() for row in refs[:2]])
            markdown_text = f"{_label('history', markdown=True)} {markdown_refs or 'this slice'} is already sitting in Odylith's diagnosed queue, so treat the next move as a continuation, not a cold start."
            plain_text = f"{_label('history', markdown=False)} {plain_refs or 'this slice'} is already sitting in Odylith's diagnosed queue, so treat the next move as a continuation, not a cold start."
            return _signal_payload(kind="history", metrics=metrics, markdown_text=markdown_text, plain_text=plain_text, facts=["Tribunal already has a live case on this scope"], refs=refs[:2], render_hint="explicit_label", confidence="medium")
    if not history_refs:
        return _suppressed_signal_payload(kind="history", metrics=metrics, reason="no_strong_prior")
    refs = list(history_refs[:2])
    markdown_refs = _join_items([str(row.get("markdown_ref", "")).strip() for row in refs])
    plain_refs = _join_items([str(row.get("plain_ref", "")).strip() for row in refs])
    facts = ["there is already history on this surface"]
    markdown_text = (
        f"{_label('history', markdown=True)} this slice already left tracks in {markdown_refs}, "
        "so treat the next move as a continuation, not a cold start."
    )
    plain_text = (
        f"{_label('history', markdown=False)} this slice already left tracks in {plain_refs}, "
        "so treat the next move as a continuation, not a cold start."
    )
    return _signal_payload(
        kind="history",
        metrics=metrics,
        markdown_text=markdown_text,
        plain_text=plain_text,
        facts=facts,
        refs=refs,
        render_hint="explicit_label",
        confidence="high",
    )


def _compose_risk_signal(
    *,
    request: Any,
    metrics: Mapping[str, Any],
    adoption: Mapping[str, Any],
    anchor_artifacts: Sequence[Mapping[str, Any]],
    tribunal_context: Mapping[str, Any],
) -> dict[str, Any]:
    tribunal_rows = [
        row for row in tribunal_context.get("scope_signals", []) or []
        if isinstance(row, Mapping)
        and operator_readout.scenario_priority(str(row.get("operator_readout", {}).get("primary_scenario", "")).strip()) < operator_readout.scenario_priority("clear_path")
    ]
    tribunal_rows.sort(
        key=lambda row: (
            operator_readout.scenario_priority(str(row.get("operator_readout", {}).get("primary_scenario", "")).strip()),
            operator_readout.severity_rank(str(row.get("operator_readout", {}).get("severity", "")).strip()),
        )
    )
    if tribunal_rows:
        scope = tribunal_rows[0]
        readout = dict(scope.get("operator_readout", {})) if isinstance(scope.get("operator_readout"), Mapping) else {}
        refs = _tribunal_signal_refs(tribunal_context=tribunal_context, anchor_artifacts=anchor_artifacts)
        scenario = str(operator_readout.humanize_operator_readout_token(readout.get("primary_scenario") or "clear_path") or "clear path").strip().lower()
        action = _lower_sentence_start(str(readout.get("action", "")).strip())
        issue = str(readout.get("issue", "")).strip()
        body = action or issue or "do not let polish outrun proof"
        markdown_text = _sentence_with_terminal_punctuation(
            f"{_label('risks', markdown=True)} Tribunal already has {scope.get('scope_label') or 'this slice'} in {scenario}, so {body}"
        )
        plain_text = _sentence_with_terminal_punctuation(
            f"{_label('risks', markdown=False)} Tribunal already has {scope.get('scope_label') or 'this slice'} in {scenario}, so {body}"
        )
        return _signal_payload(kind="risks", metrics=metrics, markdown_text=markdown_text, plain_text=plain_text, facts=[issue or scenario, action], refs=refs[:2], render_hint="explicit_label", severity=str(readout.get('severity', '')).strip() or "watch")
    reasons, severity = _risk_summary(request, adoption)
    if not reasons:
        return _suppressed_signal_payload(kind="risks", metrics=metrics, reason="no_material_risk")
    risk_phrase = _join_items(reasons[:3])
    refs = list(anchor_artifacts[:2])
    markdown_text = (
        f"{_label('risks', markdown=True)} {risk_phrase}, so keep the next move evidence-backed and do not let the polish outrun the proof."
    )
    plain_text = (
        f"{_label('risks', markdown=False)} {risk_phrase}, so keep the next move evidence-backed and do not let the polish outrun the proof."
    )
    return _signal_payload(
        kind="risks",
        metrics=metrics,
        markdown_text=markdown_text,
        plain_text=plain_text,
        facts=reasons,
        refs=refs,
        render_hint="explicit_label",
        severity=severity,
    )


def _claim_guard_from_tribunal_context(tribunal_context: Mapping[str, Any]) -> dict[str, Any]:
    for row in tribunal_context.get("scope_signals", []) if isinstance(tribunal_context.get("scope_signals"), list) else []:
        if not isinstance(row, Mapping):
            continue
        claim_guard = dict(row.get("claim_guard", {})) if isinstance(row.get("claim_guard"), Mapping) else {}
        if claim_guard:
            return claim_guard
    for row in tribunal_context.get("case_queue", []) if isinstance(tribunal_context.get("case_queue"), list) else []:
        if not isinstance(row, Mapping):
            continue
        claim_guard = dict(row.get("claim_guard", {})) if isinstance(row.get("claim_guard"), Mapping) else {}
        if claim_guard:
            return claim_guard
    return {}


def compose_closeout_assist(
    *,
    request: Any,
    decision: Any,
    adoption: Mapping[str, Any],
    repo_root: Path | None = None,
    final_changed_paths: Sequence[str] | None = None,
    changed_path_source: str = "",
    metrics: Mapping[str, Any] | None = None,
    context_rows: Sequence[Mapping[str, Any]] | None = None,
    assistant_summary: str = "",
) -> dict[str, Any]:
    metrics = dict(metrics) if isinstance(metrics, Mapping) else _evidence_metrics(request=request, decision=decision, adoption=adoption)
    effective_changed_paths = list(final_changed_paths or [])
    if not effective_changed_paths:
        effective_changed_paths = [
            *(_field(request, "candidate_paths") or []),
            *(_field(request, "claimed_paths") or []),
        ]
        changed_path_source = changed_path_source or "request_seed_paths"
    else:
        changed_path_source = changed_path_source or "supplied_changed_paths"
    updated_artifacts = _resolve_updated_artifacts(
        repo_root=repo_root,
        request=request,
        final_changed_paths=effective_changed_paths,
        context_rows=context_rows,
    )
    affected_contracts = _affected_contract_rows(
        updated_artifacts=updated_artifacts,
        request=request,
        repo_root=repo_root,
        context_rows=list(context_rows or []),
    )
    if not metrics["grounded"]:
        return _suppressed_assist_payload(
            metrics=metrics,
            reason="not_grounded",
            updated_artifacts=updated_artifacts,
            affected_contracts=affected_contracts,
            changed_path_source=changed_path_source,
        )
    if metrics["requires_widening"]:
        return _suppressed_assist_payload(
            metrics=metrics,
            reason="requires_widening",
            updated_artifacts=updated_artifacts,
            affected_contracts=affected_contracts,
            changed_path_source=changed_path_source,
        )
    if not metrics["route_ready"] and not metrics["grounded_delegate"]:
        return _suppressed_assist_payload(
            metrics=metrics,
            reason="not_route_ready",
            updated_artifacts=updated_artifacts,
            affected_contracts=affected_contracts,
            changed_path_source=changed_path_source,
        )

    focus_phrase = ""
    if metrics["focus_path_count"] > 0:
        focus_phrase = _count_phrase(metrics["focus_path_count"], "candidate path")
    governance_bits: list[str] = []
    if metrics["workstream_count"] > 0:
        governance_bits.append(_count_phrase(metrics["workstream_count"], "workstream"))
    if metrics["component_count"] > 0:
        governance_bits.append(_count_phrase(metrics["component_count"], "component"))
    governance_phrase = _join_items(governance_bits)
    validation_phrase = (
        _count_phrase(metrics["validation_count"], "focused check")
        if metrics["validation_count"] > 0
        else ""
    )
    leaf_phrase = (
        _count_phrase(metrics["delegated_leaf_count"], "bounded leaf", "bounded leaves")
        if metrics["delegated_leaf_count"] > 0
        else ""
    )
    bounded_execution_phrase = (
        f"keeping execution bounded across {_count_phrase(metrics['delegated_leaf_count'], 'focused slice')}"
        if metrics["delegated_leaf_count"] > 0
        else ""
    )
    artifact_markdown_phrase, artifact_plain_phrase = _artifact_phrase(updated_artifacts)
    updated_contracts = [
        row
        for row in affected_contracts
        if any(
            _normalize_token(row.get("kind")) == _normalize_token(updated.get("kind"))
            and _normalize_string(row.get("id")) == _normalize_string(updated.get("id"))
            for updated in updated_artifacts
            if isinstance(updated, Mapping)
        )
    ]
    contract_update_markdown_phrase, contract_update_plain_phrase = _affected_contract_phrase(
        updated_contracts,
        verb="updating",
    )
    contract_scope_markdown_phrase, contract_scope_plain_phrase = _affected_contract_phrase(
        affected_contracts,
        verb="staying inside",
    )
    visibility_markdown_phrase, visibility_plain_phrase = _visibility_feedback_phrase(
        request=request,
        assistant_summary=assistant_summary,
    )

    style = ""
    user_win = ""
    delta_markdown = ""
    delta_plain = ""
    proof_parts_markdown: list[str] = []
    proof_parts_plain: list[str] = []

    if metrics["grounded_delegate"] and metrics["delegated_leaf_count"] > 0 and focus_phrase:
        style = "grounded_bounded_execution"
        user_win = "kept the work moving"
        delta_markdown = "without turning the repo into the usual broader `odylith_off` scavenger hunt"
        delta_plain = "without turning the repo into the usual broader odylith_off scavenger hunt"
        if contract_update_markdown_phrase or artifact_markdown_phrase:
            proof_parts_markdown.append(contract_update_markdown_phrase or artifact_markdown_phrase)
            proof_parts_plain.append(contract_update_plain_phrase or artifact_plain_phrase)
        elif contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        proof_parts_markdown.append(f"keeping the slice to {focus_phrase}")
        proof_parts_plain.append(f"keeping the slice to {focus_phrase}")
        if metrics["suppress_routing_receipts"]:
            proof_parts_markdown.append(bounded_execution_phrase)
            proof_parts_plain.append(bounded_execution_phrase)
        else:
            proof_parts_markdown.append(f"routing {leaf_phrase}")
            proof_parts_plain.append(f"routing {leaf_phrase}")
        if validation_phrase:
            proof_parts_markdown.append(f"closing with {validation_phrase}")
            proof_parts_plain.append(f"closing with {validation_phrase}")
    elif governance_phrase:
        style = "governed_lane"
        user_win = "kept this change honest"
        delta_markdown = "instead of letting the code outrun the governed record"
        delta_plain = delta_markdown
        if contract_update_markdown_phrase or artifact_markdown_phrase:
            proof_parts_markdown.append(contract_update_markdown_phrase or artifact_markdown_phrase)
            proof_parts_plain.append(contract_update_plain_phrase or artifact_plain_phrase)
        elif contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        else:
            proof_parts_markdown.append(f"staying inside {governance_phrase}")
            proof_parts_plain.append(f"staying inside {governance_phrase}")
        if validation_phrase:
            proof_parts_markdown.append(f"closing with {validation_phrase}")
            proof_parts_plain.append(f"closing with {validation_phrase}")
        elif focus_phrase:
            proof_parts_markdown.append(f"keeping the slice to {focus_phrase}")
            proof_parts_plain.append(f"keeping the slice to {focus_phrase}")
    elif focus_phrase:
        style = "shortest_safe_path"
        user_win = "kept this on the shortest safe path"
        delta_markdown = "instead of cracking open an `odylith_off`-style repo sweep"
        delta_plain = "instead of cracking open an odylith_off-style repo sweep"
        if contract_update_markdown_phrase or artifact_markdown_phrase:
            proof_parts_markdown.append(contract_update_markdown_phrase or artifact_markdown_phrase)
            proof_parts_plain.append(contract_update_plain_phrase or artifact_plain_phrase)
        elif contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        proof_parts_markdown.append(f"grounding the work to {focus_phrase}")
        proof_parts_plain.append(f"grounding the work to {focus_phrase}")
        if validation_phrase:
            proof_parts_markdown.append(f"closing with {validation_phrase}")
            proof_parts_plain.append(f"closing with {validation_phrase}")
    elif validation_phrase:
        style = "focused_validation"
        user_win = "kept the proof tight"
        delta_markdown = "instead of widening just to feel busy"
        delta_plain = delta_markdown
        if contract_update_markdown_phrase or artifact_markdown_phrase:
            proof_parts_markdown.append(contract_update_markdown_phrase or artifact_markdown_phrase)
            proof_parts_plain.append(contract_update_plain_phrase or artifact_plain_phrase)
        elif contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        proof_parts_markdown.append(f"closing with {validation_phrase}")
        proof_parts_plain.append(f"closing with {validation_phrase}")
    elif visibility_markdown_phrase:
        style = "visibility_continuity"
        user_win = "kept the UX signal from disappearing"
        delta_markdown = "instead of treating quiet hooks as proof Odylith had nothing useful to say"
        delta_plain = delta_markdown
        if contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        proof_parts_markdown.append(visibility_markdown_phrase)
        proof_parts_plain.append(visibility_plain_phrase)

    proof_markdown = _join_phrases(proof_parts_markdown)
    proof_plain = _join_phrases(proof_parts_plain)
    if not style or not proof_markdown or not proof_plain:
        return _suppressed_assist_payload(
            metrics=metrics,
            reason="missing_user_facing_delta",
            updated_artifacts=updated_artifacts,
            affected_contracts=affected_contracts,
            changed_path_source=changed_path_source,
        )

    markdown_text = f"{_label('assist', markdown=True)} {user_win}"
    plain_text = f"{_label('assist', markdown=False)} {user_win}"
    if delta_markdown:
        markdown_text += f" {delta_markdown}"
    if delta_plain:
        plain_text += f" {delta_plain}"
    markdown_text += f" by {proof_markdown}."
    plain_text += f" by {proof_plain}."

    return {
        "eligible": True,
        "style": style,
        "label": _label("assist", markdown=False),
        "preferred_markdown_label": _label("assist", markdown=True),
        "text": markdown_text,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "user_win": user_win,
        "delta": delta_markdown,
        "proof": proof_markdown,
        "updated_artifacts": updated_artifacts,
        "affected_contracts": affected_contracts,
        "changed_path_source": changed_path_source,
        "suppressed_reason": "",
        "metrics": metrics,
    }


def compose_conversation_bundle(
    *,
    request: Any,
    decision: Any,
    adoption: Mapping[str, Any],
    repo_root: Path | None = None,
    final_changed_paths: Sequence[str] | None = None,
    changed_path_source: str = "",
    turn_phase: str = "",
    assistant_summary: str = "",
) -> dict[str, Any]:
    context_payload = _request_context_payload(request)
    metrics = _evidence_metrics(request=request, decision=decision, adoption=adoption)
    context_rows = _context_artifact_rows(repo_root=repo_root, value=context_payload)
    anchor_artifacts = _request_anchor_artifacts(
        request=request,
        repo_root=repo_root,
        context_rows=context_rows,
    )
    history_refs = _history_artifact_refs(
        request=request,
        repo_root=repo_root,
        anchor_artifacts=anchor_artifacts,
    )
    tribunal_context = delivery_runtime.tribunal_context(
        context_payload=context_payload,
        repo_root=repo_root,
        anchor_artifacts=anchor_artifacts,
    )
    claim_guard = _claim_guard_from_tribunal_context(tribunal_context)
    claim_lint = proof_state.build_claim_lint(claim_guard)
    risks = claim_runtime.enforce_payload(
        _compose_risk_signal(
            request=request,
            metrics=metrics,
            adoption=adoption,
            anchor_artifacts=anchor_artifacts,
            tribunal_context=tribunal_context,
        ),
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface="chatter_risks",
    )
    insight = claim_runtime.enforce_payload(
        _compose_insight_signal(
            metrics=metrics,
            anchor_artifacts=anchor_artifacts,
            tribunal_context=tribunal_context,
        ),
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface="chatter_insight",
    )
    history = claim_runtime.enforce_payload(
        _compose_history_signal(
            metrics=metrics,
            history_refs=history_refs,
            anchor_artifacts=anchor_artifacts,
            tribunal_context=tribunal_context,
        ),
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface="chatter_history",
    )
    selected_signal = ""
    selected_signals: list[str] = []
    for key in _EXPLICIT_SIGNAL_PRIORITY:
        payload = {"risks": risks, "insight": insight, "history": history}[key]
        if payload["eligible"] and payload["render_hint"] == "explicit_label":
            selected_signals.append(key)
    if selected_signals:
        selected_signal = selected_signals[0]
    assist = claim_runtime.enforce_payload(
        compose_closeout_assist(
            request=request,
            decision=decision,
            adoption=adoption,
            repo_root=repo_root,
            final_changed_paths=final_changed_paths,
            changed_path_source=changed_path_source,
            metrics=metrics,
            context_rows=context_rows,
            assistant_summary=assistant_summary,
        ),
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface="chatter_assist",
    )
    closeout_signals = {
        "risks": dict(risks),
        "insight": dict(insight),
        "history": dict(history),
    }
    for payload in closeout_signals.values():
        if payload.get("eligible"):
            payload["render_hint"] = "supplemental_line"
    selected_supplemental = ""
    if assist.get("eligible"):
        for key in _SUPPLEMENTAL_PRIORITY:
            payload = closeout_signals[key]
            if not payload["eligible"]:
                continue
            if not _signal_adds_new_information(signal=payload, assist=assist):
                closeout_signals[key] = _suppressed_closeout_signal(payload, reason="overlaps_assist")
                continue
            if payload["eligible"]:
                selected_supplemental = key
                break
    else:
        for key, payload in closeout_signals.items():
            if payload.get("eligible"):
                closeout_signals[key] = _suppressed_closeout_signal(payload, reason="assist_suppressed")
    closeout_markdown_lines = [assist["markdown_text"]] if assist.get("eligible") else []
    closeout_plain_lines = [assist["plain_text"]] if assist.get("eligible") else []
    if selected_supplemental:
        closeout_markdown_lines.append(closeout_signals[selected_supplemental]["markdown_text"])
        closeout_plain_lines.append(closeout_signals[selected_supplemental]["plain_text"])
    claim_enforcement = claim_runtime.build_claim_enforcement_summary(
        claim_lint=claim_lint,
        ambient_payloads={"risks": risks, "insight": insight, "history": history},
        assist_payload=assist,
        supplemental_payload=closeout_signals.get(selected_supplemental, {}) if selected_supplemental else {},
    )
    intervention_bundle: dict[str, Any] = {}
    live_ambient_signals: dict[str, Any] = {}
    if repo_root is not None:
        effective_turn_phase = _normalize_token(turn_phase) or ("post_edit_checkpoint" if final_changed_paths else "prompt_submit")
        packet_summary = {}
        if getattr(request, "workstreams", None):
            packet_summary["workstreams"] = list(getattr(request, "workstreams", []))
        if getattr(request, "components", None):
            packet_summary["components"] = list(getattr(request, "components", []))
        if isinstance(getattr(request, "context_signals", {}), Mapping):
            context_packet = request.context_signals.get("context_packet")
            if isinstance(context_packet, Mapping):
                for key in ("bugs", "diagrams", "workstreams", "components"):
                    value = context_packet.get(key)
                    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                        packet_summary[key] = [str(item).strip() for item in value if str(item).strip()]
        context_packet_summary = _nested_mapping(context_payload, "context_packet")
        execution_engine_summary = _nested_mapping(context_payload, "execution_engine_summary")
        memory_summary = _nested_mapping(context_payload, "memory_summary") or _nested_mapping(context_payload, "memory_snapshot")
        visibility_summary = _nested_mapping(context_payload, "visibility_summary") or _nested_mapping(context_payload, "delivery_ledger")
        delivery_snapshot = _nested_mapping(context_payload, "delivery_snapshot")
        live_bundle = conversation_surface.build_conversation_bundle(
            repo_root=Path(repo_root).expanduser().resolve(),
            observation={
                "host_family": (
                    str(getattr(request, "context_signals", {}).get("host_family", "")).strip()
                    if isinstance(getattr(request, "context_signals", {}), Mapping)
                    else ""
                ),
                "turn_phase": effective_turn_phase,
                "session_id": str(getattr(request, "session_id", "")).strip(),
                "prompt_excerpt": str(getattr(request, "prompt", "")).strip(),
                "assistant_summary": _normalize_string(assistant_summary)
                or str(closeout_signals.get(selected_supplemental, {}).get("plain_text", "")).strip(),
                "changed_paths": list(final_changed_paths or getattr(request, "candidate_paths", [])[:4]),
                "workstreams": getattr(request, "workstreams", []),
                "components": getattr(request, "components", []),
                "packet_summary": packet_summary,
                "context_packet_summary": context_packet_summary,
                "execution_engine_summary": execution_engine_summary,
                "memory_summary": memory_summary,
                "tribunal_summary": tribunal_context,
                "visibility_summary": visibility_summary,
                "delivery_snapshot": delivery_snapshot,
            },
        )
        intervention_bundle = dict(live_bundle.get("intervention_bundle", {}))
        live_ambient_signals = dict(live_bundle.get("ambient_signals", {}))

    return {
        "live_ambient_signals": live_ambient_signals,
        "ambient_signals": {
            "insight": insight,
            "history": history,
            "risks": risks,
            "claim_guard": claim_guard,
            "claim_lint": claim_lint,
            "claim_enforcement": claim_enforcement,
            "selected_signal": selected_signal,
            "selected_signals": selected_signals,
            "render_policy": {
                "ambient_by_default": True,
                "explicit_labels_rare": True,
                "one_signal_at_a_time": False,
                "max_signals_per_turn": 3,
                "dedupe_by_signal_kind": True,
                "dedupe_by_semantic_signature": True,
                "priority": list(_EXPLICIT_SIGNAL_PRIORITY),
                "claim_terms_require_lint": bool(claim_lint.get("blocked_terms")),
                "commentary_mode": str(metrics.get("commentary_mode", "")).strip(),
                "suppress_routing_receipts": bool(metrics.get("suppress_routing_receipts")),
                "surface_fast_lane": bool(metrics.get("surface_fast_lane")),
            },
        },
        "closeout_bundle": {
            "assist": assist,
            "insight": closeout_signals["insight"],
            "history": closeout_signals["history"],
            "risks": closeout_signals["risks"],
            "claim_guard": claim_guard,
            "claim_lint": claim_lint,
            "claim_enforcement": claim_enforcement,
            "selected_supplemental": selected_supplemental,
            "updated_artifacts": list(assist.get("updated_artifacts", [])),
            "plain_text": "\n".join(closeout_plain_lines),
            "markdown_text": "\n".join(closeout_markdown_lines),
            "render_policy": {
                "benchmark_safe": True,
                "ambient_by_default": True,
                "max_lines": 2,
                "supplemental_priority": list(_SUPPLEMENTAL_PRIORITY),
                "changed_path_source": assist.get("changed_path_source", ""),
                "claim_terms_require_lint": bool(claim_lint.get("blocked_terms")),
                "highest_truthful_claim": str(claim_lint.get("highest_truthful_claim", "")).strip(),
                "commentary_mode": str(metrics.get("commentary_mode", "")).strip(),
                "suppress_routing_receipts": bool(metrics.get("suppress_routing_receipts")),
                "surface_fast_lane": bool(metrics.get("surface_fast_lane")),
            },
        },
        "intervention_bundle": intervention_bundle,
    }

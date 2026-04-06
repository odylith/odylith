"""Transaction narrative helpers extracted from the Compass dashboard runtime."""

from __future__ import annotations

import datetime as dt
from functools import lru_cache
import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


def _host():
    from odylith.runtime.surfaces import compass_dashboard_runtime as host

    return host


def _transaction_scope_phrase(workstreams: Sequence[str]) -> str:
    rows = [str(token).strip() for token in workstreams if str(token).strip()]
    if len(rows) == 1:
        return f"for {rows[0]}"
    if len(rows) > 1:
        return f"across {len(rows)} workstreams"
    return ""


def _is_generated_narrative_file(path: str) -> bool:
    token = _host()._normalize_repo_token(path)
    return _is_generated_narrative_token(token)


def _is_generated_narrative_token(token: str) -> bool:
    normalized = str(token or "").strip().lower()
    if not normalized:
        return True
    if normalized.startswith("odylith/radar/source/") and not normalized.startswith("odylith/radar/source/ui/"):
        return False
    if normalized.startswith("odylith/atlas/source/"):
        if normalized.startswith("odylith/atlas/source/catalog/"):
            return True
        return normalized.endswith(".svg") or normalized.endswith(".png")
    return (
        normalized.startswith("odylith/radar/source/ui/")
        or normalized in {
            "odylith/radar/radar.html",
            "odylith/radar/backlog-payload.v1.js",
            "odylith/radar/backlog-app.v1.js",
            "odylith/radar/standalone-pages.v1.js",
            "odylith/radar/traceability-graph.v1.json",
            "odylith/radar/traceability-autofix-report.v1.json",
            "odylith/casebook/casebook.html",
            "odylith/casebook/casebook-payload.v1.js",
            "odylith/casebook/casebook-app.v1.js",
        }
        or normalized.startswith("odylith/casebook/")
        or normalized.startswith("odylith/compass/runtime/")
        or normalized in {
            "odylith/compass/compass.html",
            "odylith/index.html",
            "odylith/atlas/atlas.html",
            "odylith/atlas/mermaid-payload.v1.js",
            "odylith/atlas/mermaid-app.v1.js",
        }
    )


@lru_cache(maxsize=32768)
def _split_source_vs_generated_files_cached(files: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    source: list[str] = []
    generated: list[str] = []
    normalize_repo_token = _host()._normalize_repo_token
    for raw in files:
        token = normalize_repo_token(str(raw))
        if not token:
            continue
        if _is_generated_narrative_token(token):
            generated.append(token)
        else:
            source.append(token)
    return tuple(source), tuple(generated)


def _normalized_file_tuple(files: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(raw).strip() for raw in files if str(raw).strip())


def _split_source_vs_generated_files(files: Sequence[str]) -> tuple[list[str], list[str]]:
    source, generated = _split_source_vs_generated_files_cached(_normalized_file_tuple(files))
    return list(source), list(generated)


def _local_change_surface_label(path: str) -> str:
    token = _host()._normalize_repo_token(path)
    lower = token.lower()
    if not lower:
        return "code"

    exact_labels: dict[str, str] = {
        "odylith/technical-plans/index.md": "plan index",
        "odylith/radar/source/index.md": "backlog index",
        "odylith/casebook/bugs/index.md": "bugs index",
    }
    if lower in exact_labels:
        return exact_labels[lower]

    explicit_prefixes: tuple[tuple[str, str], ...] = (
        ("odylith/compass/", "Compass dashboard"),
        ("odylith/casebook/", "Casebook dashboard"),
        ("odylith/index.html", "Tooling dashboard shell"),
        ("odylith/radar/source/", "backlog source"),
        ("odylith/radar/", "Radar dashboard"),
        ("odylith/atlas/source/", "Mermaid source"),
        ("odylith/atlas/", "Mermaid catalog"),
        ("src/odylith/runtime/surfaces/render_compass_dashboard.py", "Compass renderer"),
        ("src/odylith/runtime/surfaces/render_backlog_ui.py", "Radar renderer"),
        ("src/odylith/runtime/surfaces/render_tooling_dashboard.py", "Tooling dashboard renderer"),
        ("src/odylith/runtime/surfaces/render_registry_dashboard.py", "Registry renderer"),
        ("src/odylith/runtime/surfaces/render_casebook_dashboard.py", "Casebook renderer"),
        ("src/odylith/runtime/surfaces/render_mermaid_catalog.py", "Atlas renderer"),
        ("src/odylith/runtime/surfaces/update_compass.py", "Compass update command"),
        ("src/odylith/runtime/common/log_compass_timeline_event.py", "Timeline logger"),
        ("src/odylith/runtime/governance/sync_workstream_artifacts.py", "Workstream sync pipeline"),
        ("src/odylith/runtime/surfaces/watch_prompt_transactions.py", "Prompt transaction watcher"),
        ("tests/unit/runtime/", "runtime tests"),
        ("tests/integration/", "integration tests"),
        ("tests/unit/", "unit tests"),
        ("odylith/technical-plans/", "implementation plan"),
        ("agents-guidelines/", "workflow docs"),
        ("skills/", "skills docs"),
    )
    for prefix, label in explicit_prefixes:
        if lower.startswith(prefix):
            return label

    head = lower.split("/", 1)[0]
    fallback: dict[str, str] = {
        "src": "product code",
        "tests": "tests",
        "odylith": "odylith artifacts",
        "docs": "docs",
        "infra": "infrastructure",
        "services": "services",
        "application": "platform runtime",
    }
    return fallback.get(head, f"{head} artifacts")


def _is_generated_only_local_change_event(row: Mapping[str, Any]) -> bool:
    if str(row.get("kind", "")).strip().lower() != "local_change":
        return False
    source_files, generated_files = _split_source_vs_generated_files(row.get("files", []))
    return not source_files and bool(generated_files)


def _is_generated_only_transaction(row: Mapping[str, Any]) -> bool:
    source_files, generated_files = _split_source_vs_generated_files(row.get("files", []))
    return not source_files and bool(generated_files)


def _local_change_headline_phrase(
    *,
    local_events: Sequence[Mapping[str, Any]],
    files_count: int,
) -> str:
    normalize_repo_token = _host()._normalize_repo_token
    file_tokens: list[str] = []
    action_tokens: list[str] = []
    for row in local_events:
        for value in row.get("files", []):
            token = normalize_repo_token(str(value))
            if token:
                file_tokens.append(token)
        summary = str(row.get("summary", "")).strip()
        if summary:
            action_tokens.append(summary.split(" ", 1)[0].lower())

    action_set = set(action_tokens)
    if action_set == {"added"}:
        verb = "Added"
    elif action_set == {"deleted"}:
        verb = "Removed"
    elif action_set == {"renamed"}:
        verb = "Renamed"
    else:
        verb = "Updated"

    if not file_tokens:
        if files_count > 0:
            return f"{verb} code"
        return "Code updates"

    labels: dict[str, int] = {}
    ordered_labels: list[str] = []
    for token in file_tokens:
        label = _local_change_surface_label(token)
        labels[label] = labels.get(label, 0) + 1
        if label not in ordered_labels:
            ordered_labels.append(label)
    label_priority: dict[str, int] = {
        "Compass dashboard": 0,
        "Radar dashboard": 0,
        "Tooling dashboard shell": 0,
        "Mermaid catalog": 0,
        "implementation plan": 1,
        "workflow docs": 1,
        "skills docs": 1,
        "Compass renderer": 2,
        "Radar renderer": 2,
        "Tooling dashboard renderer": 2,
        "Compass update command": 3,
        "Timeline logger": 3,
        "Workstream sync pipeline": 3,
        "Prompt transaction watcher": 3,
    }
    ranked_labels = sorted(
        ordered_labels,
        key=lambda label: (
            -labels.get(label, 0),
            label_priority.get(label, 99),
            ordered_labels.index(label),
            label,
        ),
    )
    primary = ranked_labels[0]
    if len(ranked_labels) == 1:
        return f"{verb} {primary}"
    if len(ranked_labels) == 2:
        return f"{verb} {ranked_labels[0]} + {ranked_labels[1]}"
    return f"{verb} {primary} and {len(ranked_labels) - 1} other areas"


def _is_generic_transaction_headline(text: str) -> bool:
    normalize_sentence = _host()._normalize_sentence
    token = normalize_sentence(text).strip().rstrip(".")
    if not token:
        return True
    return bool(_host()._GENERIC_TX_HEADLINE_RE.fullmatch(token.lower()))


def _select_transaction_headline_hint(tx_events: Sequence[Mapping[str, Any]]) -> str:
    narrative_excerpt = _host()._narrative_excerpt
    max_chars = _host()._TX_HEADLINE_MAX_CHARS
    for row in tx_events:
        hint = narrative_excerpt(
            str(row.get("headline_hint", "")).strip(),
            max_sentences=1,
            max_chars=max_chars,
        ).strip().rstrip(".")
        if not hint:
            continue
        if _is_generic_transaction_headline(hint):
            continue
        return hint
    return ""


def _plan_update_headline(*, summary: str, scope: str) -> str:
    host = _host()
    normalize_sentence = host._normalize_sentence
    plan_kickoff_re = host._PLAN_KICKOFF_RE
    plan_checklist_progress_re = host._PLAN_CHECKLIST_PROGRESS_RE

    token = normalize_sentence(summary).strip().rstrip(".")
    lowered = token.lower()
    if not token:
        return f"Plan updated {scope}".strip() if scope else "Plan updated"

    if plan_kickoff_re.search(lowered):
        return f"Plan kickoff {scope}".strip() if scope else "Plan kickoff"

    match = plan_checklist_progress_re.search(token)
    if match:
        done = int(str(match.group("done")).strip())
        total = int(str(match.group("total")).strip())
        if total > 0 and done >= total:
            label = "Plan checklist complete"
        elif total > 0 and done > 0:
            label = "Plan progress updated"
        else:
            label = "Plan status updated"
        return f"{label} {scope}".strip() if scope else label

    if any(marker in lowered for marker in ("in progress", "planning", "implementation")):
        label = "Plan status updated"
        return f"{label} {scope}".strip() if scope else label

    if any(marker in lowered for marker in ("completed", "done", "closed")):
        label = "Plan updated"
        return f"{label} {scope}".strip() if scope else label

    label = "Plan updated"
    return f"{label} {scope}".strip() if scope else label


def _lineage_transaction_headline(*, summaries: Sequence[str], scope: str) -> str:
    normalize_sentence = _host()._normalize_sentence
    lowered = " ".join(normalize_sentence(text).lower() for text in summaries if str(text).strip())
    if not lowered:
        return ""
    if any(token in lowered for token in ("reopen", "re-open", "reopened", "successor")):
        label = "Workstream lineage reopen update"
    elif any(token in lowered for token in ("split", "branch", "fork")):
        label = "Workstream lineage split update"
    elif any(token in lowered for token in ("merge", "merged", "consolidat")):
        label = "Workstream lineage merge update"
    else:
        return ""
    return f"{label} {scope}".strip() if scope else label


def _build_transaction_headline(
    *,
    tx_events: Sequence[Mapping[str, Any]],
    tx_context: str,
    workstreams: Sequence[str],
    files_count: int,
) -> str:
    host = _host()
    narrative_excerpt = host._narrative_excerpt
    max_chars = host._TX_HEADLINE_MAX_CHARS
    humanize_execution_event_summary = host._humanize_execution_event_summary
    clip_sentence = host._clip_sentence

    headline_hint = _select_transaction_headline_hint(tx_events)
    if headline_hint:
        return headline_hint

    context = narrative_excerpt(
        tx_context,
        max_sentences=1,
        max_chars=max_chars,
    ).strip().rstrip(".")
    if context:
        return context

    by_kind: dict[str, list[Mapping[str, Any]]] = {}
    for row in tx_events:
        kind = str(row.get("kind", "")).strip().lower()
        if not kind:
            continue
        by_kind.setdefault(kind, []).append(row)

    scope = _transaction_scope_phrase(workstreams)
    lineage_hint = _lineage_transaction_headline(
        summaries=[str(row.get("summary", "")).strip() for row in tx_events],
        scope=scope,
    )
    if lineage_hint:
        return lineage_hint

    def _summary_for(kind: str) -> str:
        rows = by_kind.get(kind, [])
        if not rows:
            return ""
        return humanize_execution_event_summary(
            kind=kind,
            summary=str(rows[0].get("summary", "")).strip(),
        ).strip().rstrip(".")

    implementation_summary = _summary_for("implementation")
    if implementation_summary:
        return clip_sentence(implementation_summary, limit=max_chars).rstrip(".")

    decision_summary = _summary_for("decision")
    if decision_summary:
        return clip_sentence(f"Decision: {decision_summary}", limit=max_chars).rstrip(".")

    statement_summary = _summary_for("statement")
    if statement_summary:
        return clip_sentence(statement_summary, limit=max_chars).rstrip(".")

    local_change_rows = by_kind.get("local_change", [])
    if local_change_rows:
        local_phrase = _local_change_headline_phrase(
            local_events=local_change_rows,
            files_count=files_count,
        )
        if local_phrase:
            if scope:
                return clip_sentence(
                    f"{local_phrase} {scope}",
                    limit=max_chars,
                ).rstrip(".")
            return clip_sentence(local_phrase, limit=max_chars).rstrip(".")
        local_summary = _summary_for("local_change")
        if local_summary:
            return clip_sentence(local_summary, limit=max_chars).rstrip(".")

    if by_kind.get("plan_completion"):
        if scope:
            return f"Plan milestone completed {scope}"
        return "Plan milestone completed"

    plan_update_summary = _summary_for("plan_update")
    if plan_update_summary:
        return _plan_update_headline(summary=plan_update_summary, scope=scope)

    commit_summary = _summary_for("commit")
    if commit_summary:
        return clip_sentence(commit_summary, limit=max_chars).rstrip(".")

    for bug_kind, bug_label in (
        ("bug_watch", "Critical bug watch"),
        ("bug_resolved", "Critical bug resolved"),
        ("bug_update", "Bug update"),
    ):
        if by_kind.get(bug_kind):
            if scope:
                return f"{bug_label} {scope}"
            return bug_label

    if files_count > 0:
        fallback = "Updated code"
        if scope:
            return f"{fallback} {scope}"
        return fallback

    if tx_events:
        fallback = humanize_execution_event_summary(
            kind=str(tx_events[0].get("kind", "")).strip(),
            summary=str(tx_events[0].get("summary", "")).strip(),
        ).strip()
        if fallback:
            return clip_sentence(fallback, limit=max_chars).rstrip(".")
    return "Execution update"


def _is_transaction_support_file(path: str, *, repo_root: Path | None = None) -> bool:
    token = _host()._normalize_repo_token(path, repo_root=repo_root)
    if not token:
        return False
    return (
        token.startswith("odylith/casebook/bugs/")
        or token.startswith("odylith/technical-plans/")
        or token.startswith("docs/")
        or token.startswith("odylith/radar/source/")
    )


def _transaction_shadow_facts(
    row: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    source_files, generated_files = _split_source_vs_generated_files(row.get("files", []))
    support_source_files = [path for path in source_files if _is_transaction_support_file(path, repo_root=repo_root)]
    core_source_files = [path for path in source_files if path not in support_source_files]

    kind_counts: dict[str, int] = {}
    raw_events = row.get("events", [])
    for event in raw_events if isinstance(raw_events, Sequence) else []:
        if not isinstance(event, Mapping):
            continue
        kind = str(event.get("kind", "")).strip().lower()
        if kind:
            kind_counts[kind] = kind_counts.get(kind, 0) + 1

    parse_iso_ts = _host()._parse_iso_ts
    tx_id = str(row.get("transaction_id", "")).strip()
    session_id = str(row.get("session_id", "")).strip()
    explicit_transaction = bool(tx_id and not tx_id.startswith("txn:"))
    auto_global = not session_id and tx_id.startswith("txn:global:auto-global-")
    end_ts = parse_iso_ts(str(row.get("end_ts_iso", "")).strip())
    workstreams = {
        str(token).strip()
        for token in row.get("workstreams", [])
        if str(token).strip()
    }
    implementation_signal_count = sum(
        int(kind_counts.get(kind, 0) or 0)
        for kind in ("implementation", "decision", "statement")
    )
    support_signal_count = sum(
        int(kind_counts.get(kind, 0) or 0)
        for kind in ("plan_update", "plan_completion", "bug_watch", "bug_update", "bug_resolved")
    )
    strength = (
        implementation_signal_count * 10
        + int(kind_counts.get("decision", 0) or 0) * 3
        + min(4, len(core_source_files))
        + (5 if session_id else 0)
        + (3 if explicit_transaction else 0)
        - (2 if auto_global else 0)
    )
    return {
        "workstreams": workstreams,
        "end_ts": end_ts,
        "source_files": set(source_files),
        "support_source_files": set(support_source_files),
        "core_source_files": set(core_source_files),
        "generated_files": set(generated_files),
        "implementation_signal_count": implementation_signal_count,
        "support_signal_count": support_signal_count,
        "session_id": session_id,
        "explicit_transaction": explicit_transaction,
        "auto_global": auto_global,
        "strength": strength,
    }


def _should_suppress_shadowed_auto_transaction_facts(
    candidate_facts: Mapping[str, Any],
    other_facts: Mapping[str, Any],
    *,
    proximity_minutes: int = 10,
) -> bool:
    if not candidate_facts["auto_global"]:
        return False
    if other_facts["auto_global"]:
        return False
    if not (other_facts["session_id"] or other_facts["explicit_transaction"]):
        return False
    if not candidate_facts["workstreams"] or not other_facts["workstreams"]:
        return False
    if not (candidate_facts["workstreams"] & other_facts["workstreams"]):
        return False

    candidate_end_ts = candidate_facts["end_ts"]
    other_end_ts = other_facts["end_ts"]
    if candidate_end_ts is None or other_end_ts is None:
        return False
    proximity = dt.timedelta(minutes=max(1, proximity_minutes))
    if abs(candidate_end_ts - other_end_ts) > proximity:
        return False

    candidate_core = set(candidate_facts["core_source_files"])
    other_core = set(other_facts["core_source_files"])
    if not candidate_core or not other_core:
        return False
    overlap = candidate_core & other_core
    smaller_core_count = min(len(candidate_core), len(other_core))
    min_overlap = 1 if smaller_core_count <= 1 else max(2, math.ceil(smaller_core_count * 0.6))
    if len(overlap) < min_overlap:
        return False

    if int(other_facts["implementation_signal_count"]) < int(candidate_facts["implementation_signal_count"]):
        return False
    if int(other_facts["strength"]) <= int(candidate_facts["strength"]):
        return False

    unique_candidate_core = candidate_core - overlap
    if len(unique_candidate_core) > 1:
        return False
    if not candidate_facts["support_source_files"] and int(candidate_facts["support_signal_count"]) == 0:
        return False
    return True


def _compact_shadowed_auto_transactions(
    payloads: Sequence[Mapping[str, Any]],
    *,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    suppressed_ids: set[str] = set()
    rows = [dict(row) for row in payloads]
    facts_by_id: dict[str, dict[str, Any]] = {}
    explicit_candidate_ids_by_workstream: dict[str, set[str]] = {}

    for row in rows:
        row_id = str(row.get("id", "")).strip()
        if not row_id:
            continue
        facts = _transaction_shadow_facts(row, repo_root=repo_root)
        facts_by_id[row_id] = facts
        if facts["auto_global"]:
            continue
        if not (facts["session_id"] or facts["explicit_transaction"]):
            continue
        if facts["end_ts"] is None or not facts["core_source_files"] or not facts["workstreams"]:
            continue
        for workstream_id in facts["workstreams"]:
            explicit_candidate_ids_by_workstream.setdefault(str(workstream_id), set()).add(row_id)

    for candidate in rows:
        candidate_id = str(candidate.get("id", "")).strip()
        if not candidate_id or candidate_id in suppressed_ids:
            continue
        candidate_facts = facts_by_id.get(candidate_id)
        if candidate_facts is None or not candidate_facts["auto_global"]:
            continue
        other_ids: set[str] = set()
        for workstream_id in candidate_facts["workstreams"]:
            other_ids.update(explicit_candidate_ids_by_workstream.get(str(workstream_id), set()))
        for other_id in other_ids:
            if other_id == candidate_id:
                continue
            other_facts = facts_by_id.get(other_id)
            if other_facts is None:
                continue
            if _should_suppress_shadowed_auto_transaction_facts(candidate_facts, other_facts):
                suppressed_ids.add(candidate_id)
                break
    return [row for row in rows if str(row.get("id", "")).strip() not in suppressed_ids]


def _build_prompt_transactions(
    *,
    events: Sequence[Mapping[str, Any]],
    inactivity_minutes: int = 2,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    if not events:
        return []

    host = _host()
    compass_tz = host._COMPASS_TZ
    parse_iso_ts = host._parse_iso_ts
    safe_iso = host._safe_iso
    event_public_payload = host._event_public_payload
    split_delta = dt.timedelta(minutes=max(1, inactivity_minutes))
    grouped: list[dict[str, Any]] = []
    explicit_index: dict[tuple[str, str], dict[str, Any]] = {}
    latest_by_session: dict[str, dict[str, Any]] = {}
    latest_global: dict[str, Any] | None = None
    auto_idx = 0

    def _tx_sort_key(row: Mapping[str, Any]) -> tuple[dt.datetime, int, str]:
        ts = row.get("ts")
        if not isinstance(ts, dt.datetime):
            ts = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
        seq_token = row.get("transaction_seq")
        seq = int(seq_token) if isinstance(seq_token, int) else 0
        return ts.astimezone(compass_tz), seq, str(row.get("id", "")).strip()

    def _new_group(*, session_id: str, transaction_id: str, ts: dt.datetime) -> dict[str, Any]:
        nonlocal auto_idx
        auto_idx += 1
        token = transaction_id or f"auto-{session_id or 'global'}-{auto_idx:04d}"
        group_id = f"txn:{session_id or 'global'}:{token}:{auto_idx:04d}"
        return {
            "group_id": group_id,
            "session_id": session_id,
            "transaction_id": transaction_id,
            "events": [],
            "workstreams": set(),
            "files": set(),
            "start_ts": ts,
            "end_ts": ts,
            "contexts": [],
            "explicit_start": False,
            "explicit_end": False,
            "created_order": auto_idx,
        }

    def _event_related_workstreams(row: Mapping[str, Any]) -> set[str]:
        ids = {
            str(token).strip()
            for token in row.get("workstreams", [])
            if re.fullmatch(r"B-\d{3,}", str(token).strip())
        }
        summary = " ".join(
            str(row.get(field, "")).strip()
            for field in ("summary", "context")
            if str(row.get(field, "")).strip()
        )
        for match in re.findall(r"\bB-\d{3,}\b", summary):
            ids.add(match)
        return ids

    def _event_signal_bucket(row: Mapping[str, Any]) -> str:
        kind = str(row.get("kind", "")).strip().lower()
        if kind == "plan_completion":
            return "closeout"
        if kind in {"implementation", "decision", "statement"}:
            return "implementation"
        if kind == "plan_update":
            summary = " ".join(
                str(row.get(field, "")).strip().lower()
                for field in ("summary", "context")
                if str(row.get(field, "")).strip()
            )
            if "in progress" in summary or "plan started" in summary or "started" in summary:
                return "implementation"
            return "plan"
        return ""

    def _should_split_anchor_boundary(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        left_bucket = str(left.get("bucket", "")).strip()
        right_bucket = str(right.get("bucket", "")).strip()
        if not left_bucket or not right_bucket:
            return False
        left_ids = {str(token).strip() for token in left.get("workstreams", set()) if str(token).strip()}
        right_ids = {str(token).strip() for token in right.get("workstreams", set()) if str(token).strip()}
        if not left_ids or not right_ids or left_ids & right_ids:
            return False
        if left_bucket == "closeout" and right_bucket == "closeout":
            return True
        return "closeout" in {left_bucket, right_bucket} and (
            "implementation" in {left_bucket, right_bucket} or "plan" in {left_bucket, right_bucket}
        )

    def _split_mixed_auto_group(group: Mapping[str, Any]) -> list[dict[str, Any]]:
        if str(group.get("transaction_id", "")).strip():
            return [dict(group)]
        raw_events = group.get("events", [])
        events_in_group = [row for row in raw_events if isinstance(row, Mapping)]
        if len(events_in_group) < 2:
            return [dict(group)]
        ordered_group_events = sorted(events_in_group, key=_tx_sort_key)
        anchors: list[dict[str, Any]] = []
        for idx, row in enumerate(ordered_group_events):
            bucket = _event_signal_bucket(row)
            if not bucket:
                continue
            anchors.append(
                {
                    "index": idx,
                    "bucket": bucket,
                    "workstreams": _event_related_workstreams(row),
                }
            )
        if len(anchors) < 2:
            return [dict(group)]

        split_points: set[int] = set()
        for left, right in zip(anchors, anchors[1:]):
            if _should_split_anchor_boundary(left, right):
                split_points.add(int(right.get("index", 0)))
        if not split_points:
            return [dict(group)]

        slices: list[list[Mapping[str, Any]]] = []
        current_slice: list[Mapping[str, Any]] = []
        for idx, row in enumerate(ordered_group_events):
            if idx in split_points and current_slice:
                slices.append(current_slice)
                current_slice = []
            current_slice.append(row)
        if current_slice:
            slices.append(current_slice)
        if len(slices) < 2:
            return [dict(group)]

        split_groups: list[dict[str, Any]] = []
        base_group_id = str(group.get("group_id", "")).strip()
        for split_index, slice_events in enumerate(slices, start=1):
            first_ts = slice_events[0].get("ts")
            last_ts = slice_events[-1].get("ts")
            if not isinstance(first_ts, dt.datetime) or not isinstance(last_ts, dt.datetime):
                continue
            split_group = {
                "group_id": f"{base_group_id}:split-{split_index:02d}",
                "session_id": str(group.get("session_id", "")).strip(),
                "transaction_id": "",
                "events": list(slice_events),
                "workstreams": set(),
                "files": set(),
                "start_ts": first_ts,
                "end_ts": last_ts,
                "contexts": [],
                "explicit_start": False,
                "explicit_end": False,
                "created_order": int(group.get("created_order", 0) or 0) * 100 + split_index,
            }
            for row in slice_events:
                for ws in row.get("workstreams", []):
                    token = str(ws).strip()
                    if token:
                        split_group["workstreams"].add(token)
                for file_token in row.get("files", []):
                    token = str(file_token).strip()
                    if token:
                        split_group["files"].add(token)
                context = str(row.get("context", "")).strip()
                if context and context not in split_group["contexts"]:
                    split_group["contexts"].append(context)
            split_groups.append(split_group)
        return split_groups or [dict(group)]

    ordered = sorted(events, key=_tx_sort_key)
    for event in ordered:
        ts = event.get("ts")
        if not isinstance(ts, dt.datetime):
            continue
        session_id = str(event.get("session_id", "")).strip()
        transaction_id = str(event.get("transaction_id", "")).strip()
        boundary = str(event.get("transaction_boundary", "")).strip().lower()
        context = str(event.get("context", "")).strip()

        group: dict[str, Any] | None = None
        if transaction_id:
            key = (session_id, transaction_id)
            group = explicit_index.get(key)
            if group is None:
                group = _new_group(session_id=session_id, transaction_id=transaction_id, ts=ts)
                explicit_index[key] = group
                grouped.append(group)
        else:
            candidate = latest_by_session.get(session_id) if session_id else latest_global
            force_new = boundary == "start"
            if candidate is None:
                force_new = True
            elif bool(candidate.get("explicit_end")):
                force_new = True
            else:
                last_ts = candidate.get("end_ts")
                if isinstance(last_ts, dt.datetime) and (ts - last_ts) > split_delta:
                    force_new = True
            if force_new:
                group = _new_group(session_id=session_id, transaction_id="", ts=ts)
                grouped.append(group)
            else:
                group = candidate

        if group is None:
            continue

        group["events"].append(event)
        start_ts = group.get("start_ts")
        if not isinstance(start_ts, dt.datetime) or ts < start_ts:
            group["start_ts"] = ts
        end_ts = group.get("end_ts")
        if not isinstance(end_ts, dt.datetime) or ts > end_ts:
            group["end_ts"] = ts

        for ws in event.get("workstreams", []):
            token = str(ws).strip()
            if token:
                group["workstreams"].add(token)
        for file_token in event.get("files", []):
            token = str(file_token).strip()
            if token:
                group["files"].add(token)
        if context and context not in group["contexts"]:
            group["contexts"].append(context)
        if boundary == "start":
            group["explicit_start"] = True
        elif boundary == "end":
            group["explicit_end"] = True

        if session_id:
            latest_by_session[session_id] = group
        else:
            latest_global = group

    normalized_groups: list[dict[str, Any]] = []
    for group in grouped:
        normalized_groups.extend(_split_mixed_auto_group(group))

    payloads: list[dict[str, Any]] = []
    for group in normalized_groups:
        tx_events = sorted(
            list(group.get("events", [])),
            key=_tx_sort_key,
            reverse=True,
        )
        if not tx_events:
            continue
        end_ts = group.get("end_ts")
        start_ts = group.get("start_ts")
        if not isinstance(end_ts, dt.datetime) or not isinstance(start_ts, dt.datetime):
            continue

        contexts = list(group.get("contexts", []))
        tx_context = next(
            (
                str(event.get("context", "")).strip()
                for event in tx_events
                if str(event.get("context", "")).strip()
            ),
            contexts[-1] if contexts else "",
        )
        workstreams = sorted(str(token) for token in group.get("workstreams", set()) if str(token).strip())
        files = sorted(str(token) for token in group.get("files", set()) if str(token).strip())
        headline = _build_transaction_headline(
            tx_events=tx_events,
            tx_context=tx_context,
            workstreams=workstreams,
            files_count=len(files),
        )
        tx_id = str(group.get("transaction_id", "")).strip() or str(group.get("group_id", "")).strip()
        payloads.append(
            {
                "id": str(group.get("group_id", "")).strip(),
                "transaction_id": tx_id,
                "session_id": str(group.get("session_id", "")).strip(),
                "start_ts_iso": safe_iso(start_ts),
                "end_ts_iso": safe_iso(end_ts),
                "headline": headline,
                "context": tx_context,
                "event_count": len(tx_events),
                "files_count": len(files),
                "workstreams": workstreams,
                "files": files,
                "explicit_open": bool(group.get("explicit_start")) and not bool(group.get("explicit_end")),
                "explicit_closed": bool(group.get("explicit_end")),
                "events": [event_public_payload(event) for event in tx_events],
            }
        )

    payloads = _compact_shadowed_auto_transactions(payloads, repo_root=repo_root)

    def _payload_sort_key(row: Mapping[str, Any]) -> tuple[dt.datetime, str]:
        parsed = parse_iso_ts(str(row.get("end_ts_iso", "")).strip())
        if parsed is None:
            parsed = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
        return parsed, str(row.get("id", "")).strip()

    payloads.sort(key=_payload_sort_key, reverse=True)
    return payloads

"""Payload and projection helpers extracted from the backlog renderer."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import plan_progress
from odylith.runtime.governance import validate_backlog_contract as contract
from odylith.runtime.governance.delivery import scope_signal_ladder
from odylith.runtime.governance import workstream_progress as workstream_progress_runtime
from odylith.runtime.governance import workstream_inference
from odylith.runtime.surfaces import backlog_render_support
from odylith.runtime.surfaces import dashboard_time


def _parse_iso_datetime(value: object) -> dt.datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _load_compass_transactions(
    *,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], int]:
    runtime_path = backlog_render_support._resolve_path(
        repo_root=repo_root,
        value="odylith/compass/runtime/current.v1.json",
    )
    if not runtime_path.is_file():
        return [], 15

    try:
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], 15
    if not isinstance(payload, Mapping):
        return [], 15

    focus_payload = payload.get("execution_focus")
    active_window_minutes = 15
    if isinstance(focus_payload, Mapping):
        raw_window = focus_payload.get("active_window_minutes")
        if isinstance(raw_window, int) and raw_window >= 1:
            active_window_minutes = raw_window

    transactions_raw = payload.get("timeline_transactions")
    if not isinstance(transactions_raw, list):
        return [], active_window_minutes

    transactions: list[dict[str, Any]] = []
    for row in transactions_raw:
        if not isinstance(row, Mapping):
            continue
        workstreams: list[str] = []
        raw_workstreams = row.get("workstreams")
        if isinstance(raw_workstreams, list):
            seen: set[str] = set()
            for token in raw_workstreams:
                ws_id = str(token or "").strip().upper()
                if not backlog_render_support._IDEA_ID_RE.fullmatch(ws_id) or ws_id in seen:
                    continue
                seen.add(ws_id)
                workstreams.append(ws_id)

        end_ts_iso = str(row.get("end_ts_iso", "")).strip()
        end_ts = _parse_iso_datetime(end_ts_iso)
        files: list[str] = []
        raw_files = row.get("files")
        if isinstance(raw_files, list):
            for token in raw_files:
                normalized = workstream_inference.normalize_repo_token(
                    str(token or ""),
                    repo_root=repo_root,
                )
                if normalized:
                    files.append(normalized)
        has_meaningful_files = any(
            not workstream_inference.is_generated_or_global_path(path)
            for path in files
        )
        transactions.append(
            {
                "id": str(row.get("id", "")).strip(),
                "transaction_id": str(row.get("transaction_id", "")).strip(),
                "session_id": str(row.get("session_id", "")).strip(),
                "end_ts_iso": end_ts_iso,
                "end_ts": end_ts,
                "workstreams": workstreams,
                "explicit_open": bool(row.get("explicit_open")),
                "has_meaningful_files": has_meaningful_files,
            }
        )

    transactions.sort(
        key=lambda row: (
            row.get("end_ts") if isinstance(row.get("end_ts"), dt.datetime) else dt.datetime.min.replace(tzinfo=dt.timezone.utc),
            str(row.get("id", "")),
        ),
        reverse=True,
    )
    return transactions, active_window_minutes


def _is_active_transaction(
    *,
    transaction: Mapping[str, Any],
    now_utc: dt.datetime,
    active_window_minutes: int,
) -> bool:
    if bool(transaction.get("explicit_open")):
        return True
    end_ts = transaction.get("end_ts")
    if not isinstance(end_ts, dt.datetime):
        return False
    window = dt.timedelta(minutes=max(1, int(active_window_minutes)))
    return (now_utc - end_ts) <= window


def _execution_overlay_for_status(
    *,
    status: str,
    has_active_transaction: bool,
) -> str:
    token = str(status or "").strip().lower()
    if token not in {"planning", "implementation"}:
        return "inactive"
    if token == "planning":
        return "planning_active" if has_active_transaction else "planned_only"
    if has_active_transaction:
        return "actively_executing"
    return "implementation_no_live_signal"


def _attach_execution_overlay(
    *,
    entries: list[dict[str, object]],
    repo_root: Path,
) -> None:
    transactions, active_window_minutes = _load_compass_transactions(repo_root=repo_root)
    by_workstream: dict[str, list[dict[str, Any]]] = {}
    for row in transactions:
        for ws_id in row.get("workstreams", []):
            by_workstream.setdefault(ws_id, []).append(row)

    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    for entry in entries:
        ws_id = str(entry.get("idea_id", "")).strip()
        candidates = by_workstream.get(ws_id, [])
        meaningful_candidates = [
            row for row in candidates if bool(row.get("has_meaningful_files"))
        ]
        latest = (
            meaningful_candidates[0]
            if meaningful_candidates
            else (candidates[0] if candidates else None)
        )
        active = (
            _is_active_transaction(
                transaction=latest,
                now_utc=now_utc,
                active_window_minutes=active_window_minutes,
            )
            if latest is not None
            else False
        )
        execution_state = _execution_overlay_for_status(
            status=str(entry.get("status", "")).strip(),
            has_active_transaction=active,
        )
        meta: dict[str, object] = {
            "active_window_minutes": active_window_minutes,
            "source_ts_iso": "",
            "transaction_id": "",
            "session_id": "",
            "transaction_ref": "",
        }
        if latest is not None:
            meta["source_ts_iso"] = str(latest.get("end_ts_iso", "")).strip()
            meta["transaction_id"] = str(latest.get("transaction_id", "")).strip()
            meta["session_id"] = str(latest.get("session_id", "")).strip()
            meta["transaction_ref"] = str(latest.get("id", "")).strip()

        entry["execution_state"] = execution_state
        entry["execution_state_meta"] = meta


def _attach_delivery_scope_signals(
    *,
    entries: list[dict[str, object]],
    repo_root: Path,
    runtime_mode: str,
) -> None:
    payload = odylith_context_engine_store.load_delivery_surface_payload(
        repo_root=repo_root,
        surface="radar",
        runtime_mode=runtime_mode,
        buckets=("workstreams",),
    )
    workstreams = payload.get("workstreams") if isinstance(payload, Mapping) else None
    if not isinstance(workstreams, Mapping):
        workstreams = {}

    for entry in entries:
        ws_id = str(entry.get("idea_id", "")).strip()
        snapshot = workstreams.get(ws_id, {}) if ws_id else {}
        scope_signal = snapshot.get("scope_signal", {}) if isinstance(snapshot, Mapping) else {}
        normalized_signal = dict(scope_signal) if isinstance(scope_signal, Mapping) else {}
        entry["scope_signal"] = normalized_signal
        entry["scope_signal_rank"] = scope_signal_ladder.scope_signal_rank(normalized_signal)
        entry["scope_signal_budget_class"] = str(normalized_signal.get("budget_class", "")).strip()
        entry["scope_signal_promoted_default"] = bool(normalized_signal.get("promoted_default", False))


def _component_catalog_rows(
    *,
    component_index: Mapping[str, component_registry.ComponentEntry],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for component_id in sorted(component_index):
        row = component_index[component_id]
        rows.append(
            {
                "component_id": component_id,
                "name": row.name or component_id,
            }
        )
    return rows


def _atlas_diagram_catalog_rows(*, repo_root: Path) -> list[dict[str, object]]:
    catalog_path = backlog_render_support._resolve_path(
        repo_root=repo_root,
        value="odylith/atlas/source/catalog/diagrams.v1.json",
    )
    if not catalog_path.is_file():
        return []
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = payload.get("diagrams")
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _load_component_index(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> Mapping[str, component_registry.ComponentEntry]:
    try:
        return odylith_context_engine_store.load_component_index(
            repo_root=repo_root,
            runtime_mode=runtime_mode,
        )
    except Exception:
        return {}


def _attach_component_registry_links(
    *,
    entries: list[dict[str, object]],
    component_index: Mapping[str, component_registry.ComponentEntry],
) -> None:
    for entry in entries:
        idea_id = component_registry.normalize_workstream_id(str(entry.get("idea_id", "")).strip())
        component_ids = (
            component_registry.component_ids_for_workstream(
                components=component_index,
                workstream_id=idea_id,
            )
            if idea_id and component_index
            else []
        )
        entry["registry_components"] = [
            {
                "component_id": component_id,
                "name": component_index[component_id].name or component_id,
            }
            for component_id in component_ids
            if component_id in component_index
        ]


def _parse_section_rows(
    *,
    index_content: str,
    section_title: str,
    expected_headers: tuple[str, ...],
    errors: list[str],
    index_path: Path,
) -> list[dict[str, str]]:
    headers, rows, err = contract._collect_section_table(index_content, section_title)
    if err is not None:
        errors.append(f"{index_path}: {err}")
        return []
    if tuple(headers) != expected_headers:
        errors.append(f"{index_path}: section `{section_title}` headers do not match backlog contract")
        return []

    payloads: list[dict[str, str]] = []
    for row in rows:
        if len(row) != len(expected_headers):
            errors.append(
                f"{index_path}: section `{section_title}` has malformed row with {len(row)} columns"
            )
            continue
        payloads.append(dict(zip(expected_headers, row, strict=True)))
    return payloads


def _parse_optional_section_rows(
    *,
    index_content: str,
    section_title: str,
    expected_headers: tuple[str, ...],
    errors: list[str],
    index_path: Path,
) -> list[dict[str, str]]:
    headers, rows, err = contract._collect_section_table(index_content, section_title)
    if err is not None:
        if str(err).startswith("missing section"):
            return []
        errors.append(f"{index_path}: {err}")
        return []
    if tuple(headers) != expected_headers:
        errors.append(f"{index_path}: section `{section_title}` headers do not match backlog contract")
        return []

    payloads: list[dict[str, str]] = []
    for row in rows:
        if len(row) != len(expected_headers):
            errors.append(
                f"{index_path}: section `{section_title}` has malformed row with {len(row)} columns"
            )
            continue
        payloads.append(dict(zip(expected_headers, row, strict=True)))
    return payloads


def _build_entry(
    *,
    repo_root: Path,
    output_path: Path,
    payload: dict[str, str],
    section: str,
    rationale_map: dict[str, list[str]],
    errors: list[str],
) -> dict[str, object] | None:
    idea_id = payload["idea_id"].strip()
    link_target = contract._parse_link_target(payload["link"])
    if link_target is None:
        errors.append(f"invalid link column for `{idea_id}`")
        return None
    idea_path = Path(link_target).resolve()
    if not idea_path.is_file():
        errors.append(f"idea markdown missing for `{idea_id}`: {idea_path}")
        return None

    section_text = backlog_render_support._extract_sections_from_markdown(idea_path)
    section_lines = backlog_render_support._extract_sections_with_body(idea_path)
    section_lookup: dict[str, list[str]] = {}
    for title, lines in section_lines:
        normalized_title = str(title or "").strip().lower()
        if normalized_title and normalized_title not in section_lookup:
            section_lookup[normalized_title] = list(lines)

    def _section_html(*titles: str) -> str:
        for title in titles:
            normalized_title = str(title or "").strip().lower()
            lines = section_lookup.get(normalized_title, [])
            if lines:
                return backlog_render_support._render_section_body(repo_root=repo_root, lines=lines)
        return ""

    spec = contract._parse_idea_spec(idea_path)
    metadata = spec.metadata
    promoted_to_plan = str(metadata.get("promoted_to_plan", "")).strip()
    promoted_to_plan_path: Path | None = None
    plan_created = ""
    plan_updated = ""
    plan_file_date = ""
    finished_sort_date = ""
    plan_data: dict[str, object] = {
        "created": "",
        "updated": "",
        "all_total_tasks": 0,
        "all_done_tasks": 0,
        "total_tasks": 0,
        "done_tasks": 0,
        "progress_ratio": 0.0,
        "progress_basis": "execution_checklist",
        "next_tasks": [],
    }
    if promoted_to_plan:
        promoted_to_plan_path = backlog_render_support._resolve_path(repo_root=repo_root, value=promoted_to_plan)
        plan_created, plan_updated, plan_file_date = backlog_render_support._extract_plan_dates(promoted_to_plan_path)
        plan_data = plan_progress.collect_plan_progress(promoted_to_plan_path)
        if section == "finished":
            finished_sort_date = (
                plan_updated
                or plan_file_date
                or str(metadata.get("date", "")).strip()
            )

    idea_date = str(metadata.get("date", "")).strip()
    idea_date_display = dashboard_time.pacific_display_date_from_utc_token(
        idea_date,
        default=idea_date if idea_date else "",
    )
    execution_start_date = (
        plan_created
        if section in {"execution", "finished"} and backlog_render_support._DATE_TOKEN_RE.fullmatch(plan_created or "")
        else ""
    )
    execution_start_date_display = dashboard_time.pacific_display_date_from_utc_token(
        execution_start_date,
        default=execution_start_date if execution_start_date else "",
    )
    execution_end_date = (
        (plan_updated or plan_file_date)
        if section == "finished"
        and backlog_render_support._DATE_TOKEN_RE.fullmatch((plan_updated or plan_file_date or ""))
        else ""
    )
    execution_end_date_display = dashboard_time.pacific_display_date_from_utc_token(
        execution_end_date,
        default=execution_end_date if execution_end_date else "",
    )
    finished_sort_date_display = dashboard_time.pacific_display_date_from_utc_token(
        finished_sort_date,
        default=finished_sort_date if finished_sort_date else "",
    )
    execution_start_calendar_date = dashboard_time.pacific_date_from_utc_token(execution_start_date)
    execution_end_calendar_date = dashboard_time.pacific_date_from_utc_token(execution_end_date)
    execution_duration_days = ""
    if execution_start_calendar_date and execution_end_calendar_date:
        delta = (execution_end_calendar_date - execution_start_calendar_date).days
        if delta >= 0:
            execution_duration_days = str(delta)
    execution_age_days = ""
    if execution_start_calendar_date:
        execution_anchor = execution_end_calendar_date or dashboard_time.dashboard_display_today()
        execution_delta = (execution_anchor - execution_start_calendar_date).days
        if execution_delta >= 0:
            execution_age_days = str(execution_delta)

    idea_age_days = ""
    idea_calendar_date = dashboard_time.pacific_date_from_utc_token(idea_date)
    if idea_calendar_date:
        if section == "finished":
            idea_anchor = (
                dashboard_time.pacific_date_from_utc_token(execution_end_date or finished_sort_date)
                or idea_calendar_date
            )
        else:
            idea_anchor = dashboard_time.dashboard_display_today()
        idea_delta = (idea_anchor - idea_calendar_date).days
        if idea_delta >= 0:
            idea_age_days = str(idea_delta)

    score = int(str(payload["ordering_score"]).strip())
    commercial = int(str(payload["commercial_value"]).strip())
    product = int(str(payload["product_impact"]).strip())
    market = int(str(payload["market_value"]).strip())
    opportunity = round((0.40 * commercial) + (0.35 * product) + (0.25 * market), 2)
    idea_ui_path = output_path
    plan_ui_path: Path | None = output_path if promoted_to_plan_path is not None and promoted_to_plan_path.is_file() else None
    progress_view = workstream_progress_runtime.derive_workstream_progress(
        status=str(payload["status"]).strip(),
        plan=plan_data,
    )

    return {
        "section": section,
        "rank": payload["rank"].strip(),
        "rank_num": 999 if payload["rank"].strip() == "-" else int(payload["rank"].strip()),
        "idea_id": idea_id,
        "title": payload["title"].strip(),
        "priority": payload["priority"].strip(),
        "ordering_score": score,
        "opportunity": opportunity,
        "commercial_value": commercial,
        "product_impact": product,
        "market_value": market,
        "sizing": payload["sizing"].strip(),
        "complexity": payload["complexity"].strip(),
        "status": payload["status"].strip(),
        "idea_file": backlog_render_support._as_repo_path(repo_root=repo_root, target=idea_path),
        "idea_href": backlog_render_support._as_relative_href(output_path=output_path, target=idea_path),
        "idea_ui_file": backlog_render_support._as_repo_path(repo_root=repo_root, target=idea_ui_path),
        "idea_ui_href": backlog_render_support._radar_route_href(
            source_output_path=output_path,
            target_output_path=idea_ui_path,
            workstream_id=idea_id,
            view="spec",
        ),
        "date": idea_date,
        "idea_date": idea_date,
        "idea_date_display": idea_date_display,
        "idea_age_days": idea_age_days,
        "execution_start_date": execution_start_date,
        "execution_start_date_display": execution_start_date_display,
        "execution_end_date": execution_end_date,
        "execution_end_date_display": execution_end_date_display,
        "execution_duration_days": execution_duration_days,
        "execution_age_days": execution_age_days,
        "finished_sort_date_display": finished_sort_date_display,
        "confidence": str(metadata.get("confidence", "")).strip(),
        "founder_override": str(metadata.get("founder_override", "no")).strip(),
        "ordering_rationale": str(metadata.get("ordering_rationale", "")).strip(),
        "implemented_summary": str(metadata.get("implemented_summary", "")).strip(),
        "rationale_bullets": rationale_map.get(idea_id, []),
        "rationale_text": " ".join(rationale_map.get(idea_id, [])).strip(),
        "impacted_parts": str(metadata.get("impacted_parts", "")).strip(),
        "problem": section_text.get("Problem", ""),
        "problem_html": _section_html("Problem"),
        "customer": section_text.get("Customer", ""),
        "customer_html": _section_html("Customer"),
        "opportunity": section_text.get("Opportunity", ""),
        "opportunity_html": _section_html("Opportunity"),
        "founder_pov": section_text.get("Product View", section_text.get("Founder POV", "")),
        "founder_pov_html": _section_html("Product View", "Founder POV"),
        "success_metrics": section_text.get("Success Metrics", section_text.get("Success Metric", "")),
        "success_metrics_html": _section_html("Success Metrics", "Success Metric"),
        "implemented_summary_html": (
            backlog_render_support._render_section_body(
                repo_root=repo_root,
                lines=[str(metadata.get("implemented_summary", "")).strip()],
            )
            if str(metadata.get("implemented_summary", "")).strip()
            else ""
        ),
        "promoted_to_plan": promoted_to_plan,
        "promoted_to_plan_file": (
            backlog_render_support._as_repo_path(repo_root=repo_root, target=promoted_to_plan_path)
            if promoted_to_plan_path is not None
            else ""
        ),
        "promoted_to_plan_href": (
            backlog_render_support._as_relative_href(output_path=output_path, target=promoted_to_plan_path)
            if promoted_to_plan_path is not None
            else ""
        ),
        "promoted_to_plan_ui_file": (
            backlog_render_support._as_repo_path(repo_root=repo_root, target=plan_ui_path)
            if plan_ui_path is not None
            else ""
        ),
        "promoted_to_plan_ui_href": (
            backlog_render_support._radar_route_href(
                source_output_path=output_path,
                target_output_path=plan_ui_path,
                workstream_id=idea_id,
                view="plan",
            )
            if plan_ui_path is not None
            else ""
        ),
        "plan_created_date": plan_created,
        "plan_updated_date": plan_updated,
        "plan_file_date": plan_file_date,
        "plan": {
            "created": str(plan_data.get("created", "")).strip(),
            "updated": str(plan_data.get("updated", "")).strip(),
            "all_total_tasks": int(plan_data.get("all_total_tasks", 0) or 0),
            "all_done_tasks": int(plan_data.get("all_done_tasks", 0) or 0),
            "total_tasks": int(plan_data.get("total_tasks", 0) or 0),
            "done_tasks": int(plan_data.get("done_tasks", 0) or 0),
            "progress_ratio": float(plan_data.get("progress_ratio", 0.0) or 0.0),
            "progress_basis": str(plan_data.get("progress_basis", "")).strip(),
            "display_progress_ratio": progress_view.get("display_progress_ratio"),
            "display_progress_label": str(progress_view.get("display_progress_label", "")).strip(),
            "display_progress_state": str(progress_view.get("display_progress_state", "")).strip(),
            "progress_classification": str(progress_view.get("classification", "")).strip(),
            "checklist_label": str(progress_view.get("checklist_label", "")).strip(),
            "next_tasks": [str(item) for item in plan_data.get("next_tasks", [])],
        },
        "finished_sort_date": finished_sort_date,
        "workstream_type": str(metadata.get("workstream_type", "")).strip().lower(),
        "workstream_parent": str(metadata.get("workstream_parent", "")).strip(),
        "workstream_children": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_children", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
        "workstream_depends_on": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_depends_on", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
        "workstream_blocks": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_blocks", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
        "related_diagram_ids": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("related_diagram_ids", "")),
            pattern=backlog_render_support._DIAGRAM_ID_RE,
        ),
        "workstream_reopens": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_reopens", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
        "workstream_reopened_by": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_reopened_by", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
        "workstream_split_from": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_split_from", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
        "workstream_split_into": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_split_into", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
        "workstream_merged_into": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_merged_into", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
        "workstream_merged_from": backlog_render_support._split_metadata_ids(
            value=str(metadata.get("workstream_merged_from", "")),
            pattern=backlog_render_support._IDEA_ID_RE,
        ),
    }


def _backlog_summary_search_text(entry: Mapping[str, object]) -> str:
    parts = [
        str(entry.get("idea_id", "")).strip(),
        str(entry.get("title", "")).strip(),
        str(entry.get("ordering_rationale", "")).strip(),
        str(entry.get("rationale_text", "")).strip(),
        " ".join(
            str(item).strip()
            for item in entry.get("rationale_bullets", [])
            if str(item).strip()
        )
        if isinstance(entry.get("rationale_bullets"), list)
        else "",
        str(entry.get("impacted_parts", "")).strip(),
        str(entry.get("founder_pov", "")).strip(),
        str(entry.get("success_metrics", "")).strip(),
    ]
    return " ".join(token for token in parts if token).strip()


def _build_backlog_summary_entry(entry: Mapping[str, object]) -> dict[str, object]:
    summary = dict(entry)
    summary["search_text"] = _backlog_summary_search_text(entry)
    for key in backlog_render_support._BACKLOG_SUMMARY_HEAVY_FIELDS:
        summary.pop(key, None)
    plan = entry.get("plan")
    if isinstance(plan, Mapping):
        summary["plan"] = {
            "created": str(plan.get("created", "")).strip(),
            "updated": str(plan.get("updated", "")).strip(),
            "all_total_tasks": int(plan.get("all_total_tasks", 0) or 0),
            "all_done_tasks": int(plan.get("all_done_tasks", 0) or 0),
            "total_tasks": int(plan.get("total_tasks", 0) or 0),
            "done_tasks": int(plan.get("done_tasks", 0) or 0),
            "progress_ratio": float(plan.get("progress_ratio", 0.0) or 0.0),
            "progress_basis": str(plan.get("progress_basis", "")).strip(),
            "display_progress_ratio": plan.get("display_progress_ratio"),
            "display_progress_label": str(plan.get("display_progress_label", "")).strip(),
            "display_progress_state": str(plan.get("display_progress_state", "")).strip(),
            "progress_classification": str(plan.get("progress_classification", "")).strip(),
            "checklist_label": str(plan.get("checklist_label", "")).strip(),
        }
    return summary


def _build_backlog_detail_entry(entry: Mapping[str, object]) -> dict[str, object]:
    detail = dict(entry)
    detail.pop("search_text", None)
    return detail


def _build_traceability_client_payload(traceability_graph: Mapping[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {}

    workstreams = traceability_graph.get("workstreams")
    if isinstance(workstreams, list):
        payload["workstreams"] = [dict(row) for row in workstreams if isinstance(row, Mapping)]

    edges = traceability_graph.get("edges")
    if isinstance(edges, list):
        payload["edges"] = [
            dict(edge)
            for edge in edges
            if isinstance(edge, Mapping)
            and str(edge.get("edge_type", "")).strip() in backlog_render_support._TRACEABILITY_INDEX_EDGE_TYPES
        ]

    releases = traceability_graph.get("releases")
    if isinstance(releases, list):
        payload["releases"] = [dict(row) for row in releases if isinstance(row, Mapping)]

    release_aliases = traceability_graph.get("release_aliases")
    if isinstance(release_aliases, Mapping):
        payload["release_aliases"] = {
            str(alias).strip(): dict(row)
            for alias, row in release_aliases.items()
            if str(alias).strip() and isinstance(row, Mapping)
        }

    current_release = traceability_graph.get("current_release")
    if isinstance(current_release, Mapping):
        payload["current_release"] = dict(current_release)

    next_release = traceability_graph.get("next_release")
    if isinstance(next_release, Mapping):
        payload["next_release"] = dict(next_release)

    release_summary = traceability_graph.get("release_summary")
    if isinstance(release_summary, Mapping):
        payload["release_summary"] = dict(release_summary)

    warning_items = traceability_graph.get("warning_items")
    if isinstance(warning_items, list):
        payload["warning_items"] = [dict(item) for item in warning_items if isinstance(item, Mapping)]

    warnings = traceability_graph.get("warnings")
    if isinstance(warnings, list):
        payload["warnings"] = [str(item or "").strip() for item in warnings if str(item or "").strip()]

    return payload

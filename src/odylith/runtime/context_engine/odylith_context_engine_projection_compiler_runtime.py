"""Projection compiler helpers extracted from the context engine store."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.common.casebook_bug_ids import BUG_ID_FIELD, resolve_casebook_bug_id


def _host():
    from odylith.runtime.context_engine import odylith_context_engine_store as host

    return host


def warm_projections(
    *,
    repo_root: Path,
    force: bool = False,
    reason: str = "manual",
    scope: str = "default",
) -> dict[str, Any]:
    """Build or refresh local projections and return a summary."""

    host = _host()
    runtime_root = host.runtime_root
    _projection_names_for_scope = host._projection_names_for_scope
    _projected_input_fingerprints = host._projected_input_fingerprints
    projection_input_fingerprint = host.projection_input_fingerprint
    read_runtime_state = host.read_runtime_state
    record_runtime_timing = host.record_runtime_timing
    load_runtime_timing_summary = host.load_runtime_timing_summary
    _empty_projection_tables = host._empty_projection_tables
    _load_backlog_projection = host._load_backlog_projection
    _load_release_projection = host._load_release_projection
    _load_idea_specs = host._load_idea_specs
    _WORKSTREAM_ID_RE = host._WORKSTREAM_ID_RE
    _parse_link_target = host._parse_link_target
    _normalize_repo_token = host._normalize_repo_token
    _safe_json = host._safe_json
    _projection_state_row = host._projection_state_row
    _load_plan_projection = host._load_plan_projection
    _raw_text = host._raw_text
    _load_bug_projection = host._load_bug_projection
    _bug_archive_bucket_from_link_target = host._bug_archive_bucket_from_link_target
    _load_diagram_projection = host._load_diagram_projection
    _load_codex_event_projection = host._load_codex_event_projection
    _load_traceability_projection = host._load_traceability_projection
    _load_component_match_rows_from_components = host._load_component_match_rows_from_components
    _load_engineering_notes = host._load_engineering_notes
    _load_code_graph = host._load_code_graph
    _load_test_graph = host._load_test_graph
    _json_dict = host._json_dict
    _ProjectionConnection = host._ProjectionConnection
    _utc_now = host._utc_now
    write_runtime_state = host.write_runtime_state
    append_runtime_event = host.append_runtime_event
    projection_snapshot_path = host.projection_snapshot_path
    preferred_watcher_backend = host.preferred_watcher_backend
    odylith_projection_bundle = host.odylith_projection_bundle
    odylith_projection_snapshot = host.odylith_projection_snapshot
    odylith_memory_backend = host.odylith_memory_backend
    odylith_context_cache = host.odylith_context_cache
    component_registry = host.component_registry
    delivery_intelligence_engine = host.delivery_intelligence_engine
    odylith_architecture_mode = host.odylith_architecture_mode
    SCHEMA_VERSION = host.SCHEMA_VERSION
    """Build or refresh local projections and return a summary."""

    def _compatible_projection_scopes(requested_scope: str) -> tuple[str, ...]:
        return odylith_memory_backend.compatible_projection_scopes(requested_scope=requested_scope)

    def _reusable_projection_candidate() -> tuple[str, str]:
        if force:
            return ("", "")
        for candidate_scope in _compatible_projection_scopes(scope_token):
            candidate_fingerprint = projection_input_fingerprint(repo_root=root, scope=candidate_scope)
            snapshot_matches = (
                bool(snapshot_manifest.get("ready"))
                and bool(snapshot_manifest.get("tables"))
                and str(snapshot_manifest.get("projection_fingerprint", "")).strip() == candidate_fingerprint
                and str(snapshot_manifest.get("projection_scope", "")).strip() == candidate_scope
            )
            compiler_matches = (
                bool(compiler_manifest.get("ready"))
                and str(compiler_manifest.get("projection_fingerprint", "")).strip() == candidate_fingerprint
                and str(compiler_manifest.get("projection_scope", "")).strip() == candidate_scope
            )
            backend_matches = (
                not odylith_memory_backend.backend_dependencies_available()
                or odylith_memory_backend.local_backend_ready_for_projection(
                    repo_root=root,
                    projection_fingerprint=candidate_fingerprint,
                    projection_scope=candidate_scope,
                )
            )
            if snapshot_matches and compiler_matches and backend_matches:
                return (candidate_scope, candidate_fingerprint)
        return ("", "")

    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    root_runtime = runtime_root(repo_root=root)
    root_runtime.mkdir(parents=True, exist_ok=True)
    scope_token = str(scope or "default").strip().lower() or "default"
    projection_names = set(_projection_names_for_scope(scope_token))
    requested_fingerprints = _projected_input_fingerprints(repo_root=root, scope=scope_token)
    projection_fingerprint = projection_input_fingerprint(repo_root=root, scope=scope_token)
    compiler_manifest = odylith_projection_bundle.load_bundle_manifest(repo_root=root)
    snapshot_manifest = odylith_projection_snapshot.load_snapshot(repo_root=root)
    backend_manifest = odylith_memory_backend.load_manifest(repo_root=root)
    runtime_state = read_runtime_state(repo_root=root)
    reusable_scope, reusable_fingerprint = _reusable_projection_candidate()
    if reusable_scope:
        total_duration_ms = (time.perf_counter() - started_at) * 1000.0
        record_runtime_timing(
            repo_root=root,
            category="runtime",
            operation="warm_projections",
            duration_ms=total_duration_ms,
            metadata={
                "force": False,
                "reason": str(reason).strip(),
                "scope": scope_token,
                "updated_projections": [],
                "reused": True,
                "reused_projection_scope": reusable_scope,
            },
        )
        summary = {
            "schema_version": SCHEMA_VERSION,
            "updated_utc": _utc_now(),
            "projection_fingerprint": reusable_fingerprint,
            "projection_scope": reusable_scope,
            "updated_projections": [],
            "watcher_backend": preferred_watcher_backend(repo_root=root),
            "duration_ms": round(total_duration_ms, 3),
            "timings": load_runtime_timing_summary(repo_root=root, limit=12),
            "odylith_compiler": dict(compiler_manifest),
            "odylith_memory_backend": dict(backend_manifest),
            "projection_snapshot_path": str(projection_snapshot_path(repo_root=root)),
        }
        write_runtime_state(repo_root=root, payload=summary)
        return summary

    with odylith_context_cache.advisory_lock(repo_root=root, key="odylith-context-engine-projections"):
        tables = _empty_projection_tables()
        updated_projections: list[str] = []
        timing_rows: list[dict[str, Any]] = []

        def _record_projection_timing(name: str, started: float, *, row_count: int = 0) -> None:
            timing_rows.append(
                {
                    "category": "projection",
                    "operation": name,
                    "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "metadata": {
                        "force": bool(force),
                        "reason": str(reason).strip(),
                        "scope": scope_token,
                        "row_count": int(row_count),
                    },
                }
            )

        release_projection = (
            _load_release_projection(repo_root=root)
            if {"workstreams", "releases"}.intersection(projection_names)
            else {"releases": [], "workstreams": {}, "current_release": {}, "next_release": {}, "summary": {}}
        )
        release_workstreams = (
            dict(release_projection.get("workstreams", {}))
            if isinstance(release_projection.get("workstreams"), Mapping)
            else {}
        )

        if "workstreams" in projection_names:
            projection_started = time.perf_counter()
            backlog_projection = _load_backlog_projection(repo_root=root)
            idea_specs = _load_idea_specs(repo_root=root)
            rows: list[dict[str, Any]] = []
            for section_name in ("active", "execution", "finished", "parked"):
                for row in backlog_projection.get(section_name, []):
                    if not isinstance(row, Mapping):
                        continue
                    idea_id = str(row.get("idea_id", "")).strip().upper()
                    if not _WORKSTREAM_ID_RE.fullmatch(idea_id):
                        continue
                    spec = idea_specs.get(idea_id)
                    idea_file = _parse_link_target(str(row.get("link", "")))
                    source_path = idea_file or (
                        str(spec.path.relative_to(root)) if spec is not None and spec.path.is_relative_to(root) else str(spec.path)
                    ) if spec is not None else idea_file
                    idea_title = str(row.get("title", "")).strip()
                    search_title = " ".join(token for token in (idea_id, idea_title) if token).strip()
                    search_body = _raw_text(root / idea_file) if idea_file else ""
                    normalized_plan = _normalize_repo_token(str(spec.metadata.get("promoted_to_plan", "")).strip(), repo_root=root) if spec is not None else ""
                    metadata = dict(spec.metadata) if spec is not None else {}
                    release_detail = (
                        dict(release_workstreams.get(idea_id, {}))
                        if isinstance(release_workstreams.get(idea_id), Mapping)
                        else {}
                    )
                    active_release = (
                        dict(release_detail.get("active_release", {}))
                        if isinstance(release_detail.get("active_release"), Mapping)
                        else {}
                    )
                    if normalized_plan:
                        metadata["promoted_to_plan"] = normalized_plan
                    if active_release:
                        metadata["active_release_id"] = str(release_detail.get("active_release_id", "")).strip()
                        metadata["active_release_label"] = str(active_release.get("display_label", "")).strip()
                        metadata["active_release_version"] = str(active_release.get("version", "")).strip()
                        metadata["active_release_tag"] = str(active_release.get("tag", "")).strip()
                        metadata["active_release_name"] = str(active_release.get("effective_name", "")).strip()
                        metadata["active_release_aliases"] = [
                            str(item).strip()
                            for item in active_release.get("aliases", [])
                            if str(item).strip()
                        ] if isinstance(active_release.get("aliases"), list) else []
                    history_summary = str(release_detail.get("release_history_summary", "")).strip()
                    if history_summary:
                        metadata["release_history_summary"] = history_summary
                    rows.append(
                        {
                            "idea_id": idea_id,
                            "title": idea_title,
                            "status": str(row.get("status", "")).strip(),
                            "section": section_name,
                            "rank": str(row.get("rank", "")).strip(),
                            "priority": str(row.get("priority", "")).strip(),
                            "ordering_score": int(str(row.get("ordering_score", "0") or "0")),
                            "idea_file": idea_file or "",
                            "promoted_to_plan": normalized_plan,
                            "archive_bucket": "",
                            "source_path": str(source_path or "").strip(),
                            "metadata_json": _safe_json(metadata),
                            "search_title": search_title,
                            "search_body": search_body,
                        }
                    )
            tables["workstreams"] = rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="workstreams",
                    fingerprint=requested_fingerprints["workstreams"],
                    row_count=len(rows),
                    payload={"updated_utc": backlog_projection.get("updated_utc", "")},
                )
            )
            updated_projections.append("workstreams")
            _record_projection_timing("workstreams", projection_started, row_count=len(rows))

        if "releases" in projection_names:
            projection_started = time.perf_counter()
            rows = [
                dict(row)
                for row in release_projection.get("releases", [])
                if isinstance(row, Mapping) and str(row.get("release_id", "")).strip()
            ] if isinstance(release_projection.get("releases"), list) else []
            tables["releases"] = rows
            current_release = (
                dict(release_projection.get("current_release", {}))
                if isinstance(release_projection.get("current_release"), Mapping)
                else {}
            )
            next_release = (
                dict(release_projection.get("next_release", {}))
                if isinstance(release_projection.get("next_release"), Mapping)
                else {}
            )
            release_summary = (
                dict(release_projection.get("summary", {}))
                if isinstance(release_projection.get("summary"), Mapping)
                else {}
            )
            tables["projection_state"].append(
                _projection_state_row(
                    name="releases",
                    fingerprint=requested_fingerprints["releases"],
                    row_count=len(rows),
                    payload={
                        "current_release_id": str(current_release.get("release_id", "")).strip(),
                        "next_release_id": str(next_release.get("release_id", "")).strip(),
                        "active_assignment_count": int(release_summary.get("active_assignment_count", 0) or 0),
                    },
                )
            )
            updated_projections.append("releases")
            _record_projection_timing("releases", projection_started, row_count=len(rows))

        if "plans" in projection_names:
            projection_started = time.perf_counter()
            plan_projection = _load_plan_projection(repo_root=root)
            rows: list[dict[str, Any]] = []
            for section_name in ("active", "parked", "done"):
                for row in plan_projection.get(section_name, []):
                    if not isinstance(row, Mapping):
                        continue
                    plan_path = str(row.get("Plan", "")).strip().strip("`")
                    if not plan_path:
                        continue
                    source_path = plan_path
                    search_body = _raw_text(root / plan_path) if (root / plan_path).is_file() else ""
                    rows.append(
                        {
                            "plan_path": plan_path,
                            "status": str(row.get("Status", "")).strip(),
                            "section": section_name,
                            "created": str(row.get("Created", "")).strip(),
                            "updated": str(row.get("Updated", "")).strip(),
                            "backlog": str(row.get("Backlog", "")).strip().strip("`"),
                            "archive_bucket": "",
                            "source_path": source_path,
                            "search_body": search_body,
                        }
                    )
            tables["plans"] = rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="plans",
                    fingerprint=requested_fingerprints["plans"],
                    row_count=len(rows),
                )
            )
            updated_projections.append("plans")
            _record_projection_timing("plans", projection_started, row_count=len(rows))

        if "bugs" in projection_names:
            projection_started = time.perf_counter()
            bug_rows = _load_bug_projection(repo_root=root)
            rows: list[dict[str, Any]] = []
            for row in bug_rows:
                if not isinstance(row, Mapping):
                    continue
                link_target = _parse_link_target(str(row.get("Link", "")))
                bug_id = resolve_casebook_bug_id(
                    explicit_bug_id=str(row.get(BUG_ID_FIELD, "")).strip(),
                    seed=link_target or f"{row.get('Date', '')}::{row.get('Title', '')}",
                )
                bug_key = link_target or f"{row.get('Date','')}::{row.get('Title','')}"
                archive_bucket = _bug_archive_bucket_from_link_target(link_target)
                bug_markdown = _raw_text(root / link_target) if link_target and (root / link_target).is_file() else ""
                search_body = "\n".join(token for token in (bug_id, bug_markdown) if token)
                rows.append(
                    {
                        "bug_id": bug_id,
                        "bug_key": bug_key,
                        "date": str(row.get("Date", "")).strip(),
                        "title": str(row.get("Title", "")).strip(),
                        "severity": str(row.get("Severity", "")).strip(),
                        "components": str(row.get("Components", "")).strip(),
                        "status": str(row.get("Status", "")).strip(),
                        "link_target": link_target or "",
                        "archive_bucket": archive_bucket,
                        "source_path": str(row.get("IndexPath", "")).strip() or "odylith/casebook/bugs/INDEX.md",
                        "search_body": search_body,
                    }
                )
            tables["bugs"] = rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="bugs",
                    fingerprint=requested_fingerprints["bugs"],
                    row_count=len(rows),
                )
            )
            updated_projections.append("bugs")
            _record_projection_timing("bugs", projection_started, row_count=len(rows))

        if "diagrams" in projection_names:
            projection_started = time.perf_counter()
            diagrams = _load_diagram_projection(repo_root=root)
            diagram_rows: list[dict[str, Any]] = []
            watch_rows: list[dict[str, Any]] = []
            for row in diagrams:
                if not isinstance(row, Mapping):
                    continue
                diagram_rows.append(
                    {
                        "diagram_id": str(row.get("diagram_id", "")).strip(),
                        "slug": str(row.get("slug", "")).strip(),
                        "title": str(row.get("title", "")).strip(),
                        "status": str(row.get("status", "")).strip(),
                        "owner": str(row.get("owner", "")).strip(),
                        "last_reviewed_utc": str(row.get("last_reviewed_utc", "")).strip(),
                        "source_mmd": str(row.get("source_mmd", "")).strip(),
                        "source_svg": str(row.get("source_svg", "")).strip(),
                        "source_png": str(row.get("source_png", "")).strip(),
                        "source_mmd_hash": str(row.get("source_mmd_hash", "")).strip(),
                        "summary": str(row.get("summary", "")).strip(),
                        "metadata_json": _safe_json(dict(row.get("metadata", {})) if isinstance(row.get("metadata"), Mapping) else {}),
                    }
                )
                for watch_path in row.get("watch_paths", []) if isinstance(row.get("watch_paths"), list) else []:
                    token = str(watch_path).strip()
                    if token:
                        watch_rows.append(
                            {
                                "diagram_id": str(row.get("diagram_id", "")).strip(),
                                "watch_path": token,
                            }
                        )
            tables["diagrams"] = diagram_rows
            tables["diagram_watch_paths"] = watch_rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="diagrams",
                    fingerprint=requested_fingerprints["diagrams"],
                    row_count=len(diagram_rows),
                )
            )
            updated_projections.append("diagrams")
            _record_projection_timing("diagrams", projection_started, row_count=len(diagram_rows) + len(watch_rows))

        component_rows_for_matching: list[dict[str, Any]] = []
        if "components" in projection_names:
            projection_started = time.perf_counter()
            report = component_registry.build_component_registry_report(repo_root=root)
            component_traceability = component_registry.build_component_traceability_index(
                repo_root=root,
                components=report.components,
            )
            component_rows: list[dict[str, Any]] = []
            spec_rows: list[dict[str, Any]] = []
            trace_rows: list[dict[str, Any]] = []
            registry_event_rows: list[dict[str, Any]] = []
            for component_id, entry in report.components.items():
                metadata = entry.as_dict()
                coverage = report.forensic_coverage.get(component_id)
                metadata["forensic_coverage"] = coverage.as_dict() if coverage is not None else {}
                spec_path = root / entry.spec_ref if entry.spec_ref else None
                if spec_path is not None and spec_path.is_file():
                    spec_snapshot = component_registry.load_component_spec_snapshot(spec_path=spec_path)
                    metadata["validation_playbook_commands"] = list(spec_snapshot.validation_playbook_commands)
                    metadata["spec_last_updated"] = spec_snapshot.last_updated
                    spec_rows.append(
                        {
                            "component_id": component_id,
                            "title": spec_snapshot.title,
                            "last_updated": spec_snapshot.last_updated,
                            "markdown": spec_snapshot.markdown,
                            "feature_history_json": _safe_json(spec_snapshot.feature_history),
                            "skill_trigger_tiers_json": _safe_json(spec_snapshot.skill_trigger_tiers),
                            "skill_trigger_structure": spec_snapshot.skill_trigger_structure,
                            "validation_playbook_commands_json": _safe_json(spec_snapshot.validation_playbook_commands),
                        }
                    )
                else:
                    metadata["validation_playbook_commands"] = []
                component_rows.append(
                    {
                        "component_id": component_id,
                        "name": entry.name,
                        "owner": entry.owner,
                        "status": entry.status,
                        "spec_ref": entry.spec_ref,
                        "aliases_json": _safe_json(entry.aliases),
                        "workstreams_json": _safe_json(entry.workstreams),
                        "diagrams_json": _safe_json(entry.diagrams),
                        "metadata_json": _safe_json(metadata),
                    }
                )
                for bucket in ("runbooks", "developer_docs", "code_references"):
                    for path_ref in component_traceability.get(component_id, {}).get(bucket, []):
                        trace_rows.append(
                            {
                                "component_id": component_id,
                                "bucket": str(bucket).strip(),
                                "path": str(path_ref).strip(),
                            }
                        )
            registry_event_rows = [
                {
                    "event_key": odylith_context_cache.fingerprint_payload(
                        {
                            "event_index": int(event.event_index),
                            "ts_iso": str(event.ts_iso),
                            "kind": str(event.kind),
                            "summary": str(event.summary),
                        }
                    ),
                    "event_index": int(event.event_index),
                    "ts_iso": str(event.ts_iso),
                    "kind": str(event.kind),
                    "summary": str(event.summary),
                    "workstreams_json": _safe_json(event.workstreams),
                    "artifacts_json": _safe_json(event.artifacts),
                    "explicit_components_json": _safe_json(event.explicit_components),
                    "mapped_components_json": _safe_json(event.mapped_components),
                    "confidence": str(event.confidence),
                    "meaningful": 1 if bool(event.meaningful) else 0,
                }
                for event in report.mapped_events
            ]
            tables["components"] = component_rows
            tables["component_specs"] = spec_rows
            tables["component_traceability"] = trace_rows
            tables["registry_events"] = registry_event_rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="components",
                    fingerprint=requested_fingerprints["components"],
                    row_count=len(component_rows),
                    payload={
                        "diagnostics": list(report.diagnostics),
                        "candidate_queue": list(report.candidate_queue),
                        "unmapped_meaningful_events": [row.as_dict() for row in report.unmapped_meaningful_events],
                    },
                )
            )
            component_rows_for_matching = component_rows
            updated_projections.append("components")
            _record_projection_timing(
                "components",
                projection_started,
                row_count=len(component_rows) + len(spec_rows) + len(trace_rows) + len(registry_event_rows),
            )

        if "codex_events" in projection_names:
            projection_started = time.perf_counter()
            event_rows = _load_codex_event_projection(repo_root=root)
            rows = [
                {
                    "event_id": row["event_id"],
                    "ts_iso": row["ts_iso"],
                    "kind": row["kind"],
                    "summary": row["summary"],
                    "workstreams_json": _safe_json(row["workstreams"]),
                    "artifacts_json": _safe_json(row["artifacts"]),
                    "components_json": _safe_json(row["components"]),
                    "metadata_json": _safe_json(row["metadata"]),
                }
                for row in event_rows
            ]
            tables["codex_events"] = rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="codex_events",
                    fingerprint=requested_fingerprints["codex_events"],
                    row_count=len(rows),
                )
            )
            updated_projections.append("codex_events")
            _record_projection_timing("codex_events", projection_started, row_count=len(rows))

        traceability_rows: list[dict[str, Any]] = []
        if "traceability" in projection_names:
            projection_started = time.perf_counter()
            trace_rows = _load_traceability_projection(repo_root=root)
            traceability_rows = [
                {
                    "edge_key": odylith_context_cache.fingerprint_payload(row),
                    "source_kind": row["source_kind"],
                    "source_id": row["source_id"],
                    "relation": row["relation"],
                    "target_kind": row["target_kind"],
                    "target_id": row["target_id"],
                    "source_path": row["source_path"],
                }
                for row in trace_rows
            ]
            tables["traceability_edges"] = traceability_rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="traceability",
                    fingerprint=requested_fingerprints["traceability"],
                    row_count=len(traceability_rows),
                )
            )
            updated_projections.append("traceability")
            _record_projection_timing("traceability", projection_started, row_count=len(traceability_rows))

        if "delivery" in projection_names:
            projection_started = time.perf_counter()
            payload = delivery_intelligence_engine.load_delivery_intelligence_artifact(repo_root=root)
            scope_rows = []
            for scope_row in payload.get("scopes", []) if isinstance(payload.get("scopes"), list) else []:
                if not isinstance(scope_row, Mapping):
                    continue
                scope_key = str(scope_row.get("scope_key", "")).strip()
                if not scope_key:
                    continue
                scope_rows.append(
                    {
                        "scope_key": scope_key,
                        "scope_type": str(scope_row.get("scope_type", "")).strip(),
                        "scope_id": str(scope_row.get("scope_id", "")).strip(),
                        "payload_json": _safe_json(dict(scope_row)),
                    }
                )
            surface_rows = []
            for surface in ("radar", "compass", "atlas", "registry", "tooling", "shell"):
                slice_payload = delivery_intelligence_engine.slice_delivery_intelligence_for_surface(
                    payload=payload,
                    surface=surface,
                )
                surface_rows.append(
                    {
                        "surface": surface,
                        "payload_json": _safe_json(slice_payload),
                    }
                )
            tables["delivery_scopes"] = scope_rows
            tables["delivery_surfaces"] = surface_rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="delivery",
                    fingerprint=requested_fingerprints["delivery"],
                    row_count=len(scope_rows),
                )
            )
            updated_projections.append("delivery")
            _record_projection_timing("delivery", projection_started, row_count=len(scope_rows))

        if "engineering_graph" in projection_names:
            projection_started = time.perf_counter()
            component_match_rows = _load_component_match_rows_from_components(component_rows_for_matching)
            notes = _load_engineering_notes(repo_root=root, component_rows=component_match_rows)
            note_rows = [
                {
                    "note_id": row["note_id"],
                    "note_kind": row["note_kind"],
                    "title": row["title"],
                    "status": row["status"],
                    "owner": row["owner"],
                    "source_path": row["source_path"],
                    "section": row["section"],
                    "summary": row["summary"],
                    "tags_json": _safe_json(row["tags"]),
                    "components_json": _safe_json(row["components"]),
                    "workstreams_json": _safe_json(row["workstreams"]),
                    "path_refs_json": _safe_json(row["path_refs"]),
                    "metadata_json": _safe_json(row["metadata"]),
                }
                for row in notes
            ]
            tables["engineering_notes"] = note_rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="engineering_graph",
                    fingerprint=requested_fingerprints["engineering_graph"],
                    row_count=len(note_rows),
                )
            )
            updated_projections.append("engineering_graph")
            _record_projection_timing("engineering_graph", projection_started, row_count=len(note_rows))

        code_artifacts: list[dict[str, Any]] = []
        if "code_graph" in projection_names:
            projection_started = time.perf_counter()
            if not traceability_rows:
                traceability_rows = [
                    {
                        "edge_key": odylith_context_cache.fingerprint_payload(row),
                        "source_kind": row["source_kind"],
                        "source_id": row["source_id"],
                        "relation": row["relation"],
                        "target_kind": row["target_kind"],
                        "target_id": row["target_id"],
                        "source_path": row["source_path"],
                    }
                    for row in _load_traceability_projection(repo_root=root)
                ]
            artifacts, edges = _load_code_graph(repo_root=root, trace_rows=traceability_rows)
            code_artifacts = [
                {
                    "path": row["path"],
                    "module_name": row["module_name"],
                    "layer": row["layer"],
                    "imports_json": _safe_json(row["imports"]),
                    "contract_refs_json": _safe_json(row["contract_refs"]),
                    "metadata_json": _safe_json(row["metadata"]),
                }
                for row in artifacts
            ]
            code_edges = [
                {
                    "edge_key": odylith_context_cache.fingerprint_payload(row),
                    "source_path": row["source_path"],
                    "relation": row["relation"],
                    "target_path": row["target_path"],
                    "metadata_json": _safe_json(row["metadata"]),
                }
                for row in edges
            ]
            tables["code_artifacts"] = code_artifacts
            tables["code_edges"] = code_edges
            tables["projection_state"].append(
                _projection_state_row(
                    name="code_graph",
                    fingerprint=requested_fingerprints["code_graph"],
                    row_count=len(code_artifacts),
                )
            )
            updated_projections.append("code_graph")
            _record_projection_timing("code_graph", projection_started, row_count=len(code_artifacts) + len(code_edges))

        if "test_graph" in projection_names:
            projection_started = time.perf_counter()
            if not code_artifacts:
                if tables["code_artifacts"]:
                    code_artifacts = [dict(row) for row in tables["code_artifacts"]]
                else:
                    artifacts, _edges = _load_code_graph(
                        repo_root=root,
                        trace_rows=traceability_rows or _load_traceability_projection(repo_root=root),
                    )
                    code_artifacts = [
                        {
                            "path": row["path"],
                            "module_name": row["module_name"],
                            "layer": row["layer"],
                            "imports_json": _safe_json(row["imports"]),
                            "contract_refs_json": _safe_json(row["contract_refs"]),
                            "metadata_json": _safe_json(row["metadata"]),
                        }
                        for row in artifacts
                    ]
            tests = _load_test_graph(repo_root=root, code_artifacts=code_artifacts)
            test_rows = [
                {
                    "test_id": row["test_id"],
                    "test_path": row["test_path"],
                    "test_name": row["test_name"],
                    "node_id": row["node_id"],
                    "markers_json": _safe_json(row["markers"]),
                    "target_paths_json": _safe_json(row["target_paths"]),
                    "metadata_json": _safe_json(row["metadata"]),
                }
                for row in tests
            ]
            history_rows: list[dict[str, Any]] = []
            for row in tests:
                metadata = row.get("metadata", {})
                history = metadata.get("history", {}) if isinstance(metadata, Mapping) else {}
                if not isinstance(history, Mapping):
                    continue
                sources = [
                    str(token).strip()
                    for token in history.get("sources", [])
                    if str(token).strip()
                ] if isinstance(history.get("sources"), list) else []
                for source in sources:
                    history_rows.append(
                        {
                            "history_key": odylith_context_cache.fingerprint_payload({"test_id": row["test_id"], "source": source}),
                            "test_id": row["test_id"],
                            "source": source,
                            "recent_failure": 1 if bool(history.get("recent_failure")) else 0,
                            "failure_count": int(history.get("failure_count", 0) or 0),
                            "last_seen_utc": str(history.get("last_seen_utc", "")).strip(),
                            "last_failure_utc": str(history.get("last_failure_utc", "")).strip(),
                            "metadata_json": _safe_json({"empirical_score": int(history.get("empirical_score", 0) or 0)}),
                        }
                    )
            tables["test_cases"] = test_rows
            tables["test_history"] = history_rows
            tables["projection_state"].append(
                _projection_state_row(
                    name="test_graph",
                    fingerprint=requested_fingerprints["test_graph"],
                    row_count=len(test_rows) + len(history_rows),
                )
            )
            updated_projections.append("test_graph")
            _record_projection_timing("test_graph", projection_started, row_count=len(test_rows) + len(history_rows))

        projection_state_summary = {
            str(row.get("name", "")).strip(): {
                "fingerprint": str(row.get("fingerprint", "")).strip(),
                "row_count": int(row.get("row_count", 0) or 0),
                "updated_utc": str(row.get("updated_utc", "")).strip(),
                "payload": _json_dict(row.get("payload_json")),
            }
            for row in tables["projection_state"]
            if str(row.get("name", "")).strip()
        }
        compiler_input_fingerprint = odylith_context_cache.fingerprint_payload(requested_fingerprints)
        compiler_started = time.perf_counter()
        snapshot_summary = odylith_projection_snapshot.write_snapshot(
            repo_root=root,
            projection_fingerprint=projection_fingerprint,
            projection_scope=scope_token,
            input_fingerprint=compiler_input_fingerprint,
            tables=tables,
            projection_state=projection_state_summary,
            updated_projections=updated_projections,
            source="projection_compile",
        )
        compiler_inputs = odylith_memory_backend.build_backend_materialization_inputs_from_projection_tables(tables=tables)
        compiler_summary = odylith_projection_bundle.write_bundle(
            repo_root=root,
            documents=list(compiler_inputs.get("documents", [])),
            edges=list(compiler_inputs.get("edges", [])),
            projection_fingerprint=projection_fingerprint,
            projection_scope=scope_token,
            input_fingerprint=str(compiler_inputs.get("input_fingerprint", "")).strip(),
            source="projection_snapshot_compile",
        )
        architecture_bundle_started = time.perf_counter()
        architecture_bundle_summary = odylith_architecture_mode.build_architecture_bundle(
            repo_root=root,
            tables=tables,
            projection_fingerprint=projection_fingerprint,
            projection_scope=scope_token,
            input_fingerprint=compiler_input_fingerprint,
            source="projection_snapshot_compile",
        )
        timing_rows.append(
            {
                "category": "projection",
                "operation": "odylith_compiler_bundle",
                "duration_ms": round((time.perf_counter() - compiler_started) * 1000.0, 3),
                "metadata": {
                    "force": bool(force),
                    "reason": str(reason).strip(),
                    "scope": scope_token,
                    "ready": bool(compiler_summary.get("ready", True)),
                    "document_count": int(compiler_summary.get("document_count", 0) or 0),
                    "edge_count": int(compiler_summary.get("edge_count", 0) or 0),
                },
            }
        )
        timing_rows.append(
            {
                "category": "projection",
                "operation": "odylith_architecture_bundle",
                "duration_ms": round((time.perf_counter() - architecture_bundle_started) * 1000.0, 3),
                "metadata": {
                    "force": bool(force),
                    "reason": str(reason).strip(),
                    "scope": scope_token,
                    "ready": bool(architecture_bundle_summary.get("ready", True)),
                    "component_count": int(dict(architecture_bundle_summary.get("counts", {})).get("components", 0) or 0),
                    "diagram_count": int(dict(architecture_bundle_summary.get("counts", {})).get("diagrams", 0) or 0),
                },
            }
        )

        odylith_backend_summary: dict[str, Any] = {}
        backend_started = time.perf_counter()
        try:
            odylith_backend_summary = odylith_memory_backend.materialize_local_backend(
                repo_root=root,
                connection=_ProjectionConnection(repo_root=root, snapshot=snapshot_summary),
                projection_fingerprint=projection_fingerprint,
                projection_scope=scope_token,
            )
        except Exception as exc:
            odylith_backend_summary = {
                "ready": False,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        timing_rows.append(
            {
                "category": "projection",
                "operation": "odylith_memory_backend",
                "duration_ms": round((time.perf_counter() - backend_started) * 1000.0, 3),
                "metadata": {
                    "force": bool(force),
                    "reason": str(reason).strip(),
                    "scope": scope_token,
                    "ready": bool(odylith_backend_summary.get("ready")),
                    "status": str(odylith_backend_summary.get("status", "")).strip(),
                    "document_count": int(odylith_backend_summary.get("document_count", 0) or 0),
                    "edge_count": int(odylith_backend_summary.get("edge_count", 0) or 0),
                },
            }
        )

        total_duration_ms = (time.perf_counter() - started_at) * 1000.0
        for row in timing_rows:
            record_runtime_timing(
                repo_root=root,
                category=str(row.get("category", "")).strip() or "projection",
                operation=str(row.get("operation", "")).strip() or "unknown",
                duration_ms=float(row.get("duration_ms", 0.0) or 0.0),
                metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), Mapping) else {},
            )
        record_runtime_timing(
            repo_root=root,
            category="runtime",
            operation="warm_projections",
            duration_ms=total_duration_ms,
            metadata={
                "force": bool(force),
                "reason": str(reason).strip(),
                "scope": scope_token,
                "updated_projections": list(updated_projections),
            },
        )
        timing_summary = load_runtime_timing_summary(repo_root=root, limit=12)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "updated_utc": _utc_now(),
            "projection_fingerprint": projection_fingerprint,
            "projection_scope": scope_token,
            "updated_projections": updated_projections,
            "watcher_backend": preferred_watcher_backend(repo_root=root),
            "duration_ms": round(total_duration_ms, 3),
            "timings": timing_summary,
            "odylith_compiler": compiler_summary,
            "odylith_memory_backend": odylith_backend_summary,
            "projection_snapshot_path": str(projection_snapshot_path(repo_root=root)),
        }
        write_runtime_state(repo_root=root, payload=summary)
        if updated_projections:
            append_runtime_event(
                repo_root=root,
                event_type="projection_update",
                payload={
                    "reason": reason,
                    "projection_fingerprint": projection_fingerprint,
                    "updated_projections": updated_projections,
                },
            )
        return summary

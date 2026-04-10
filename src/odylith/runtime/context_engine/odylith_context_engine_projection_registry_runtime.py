from __future__ import annotations

from typing import Any

from odylith.runtime.context_engine import odylith_context_engine_projection_runtime_bindings
from odylith.runtime.context_engine import odylith_context_engine_registry_detail_runtime

def bind(host: Any) -> None:
    odylith_context_engine_projection_runtime_bindings.bind_projection_runtime(globals(), host)

def _component_entry_from_runtime_row(row: Mapping[str, Any]) -> component_registry.ComponentEntry:
    metadata = json.loads(str(row["metadata_json"] or "{}"))
    payload = dict(metadata) if isinstance(metadata, Mapping) else {}
    if payload.get("component_id"):
        return component_registry.ComponentEntry(
            component_id=str(payload.get("component_id", "")).strip(),
            name=str(payload.get("name", "")).strip(),
            kind=str(payload.get("kind", "")).strip(),
            category=str(payload.get("category", "")).strip(),
            qualification=str(payload.get("qualification", "")).strip(),
            aliases=[str(token).strip() for token in payload.get("aliases", []) if str(token).strip()]
            if isinstance(payload.get("aliases"), list)
            else [],
            path_prefixes=[str(token).strip() for token in payload.get("path_prefixes", []) if str(token).strip()]
            if isinstance(payload.get("path_prefixes"), list)
            else [],
            workstreams=[str(token).strip() for token in payload.get("workstreams", []) if str(token).strip()]
            if isinstance(payload.get("workstreams"), list)
            else [],
            diagrams=[str(token).strip() for token in payload.get("diagrams", []) if str(token).strip()]
            if isinstance(payload.get("diagrams"), list)
            else [],
            owner=str(payload.get("owner", "")).strip(),
            status=str(payload.get("status", "")).strip(),
            what_it_is=str(payload.get("what_it_is", "")).strip(),
            why_tracked=str(payload.get("why_tracked", "")).strip(),
            spec_ref=str(payload.get("spec_ref", "")).strip(),
            sources=[str(token).strip() for token in payload.get("sources", []) if str(token).strip()]
            if isinstance(payload.get("sources"), list)
            else [],
            subcomponents=[str(token).strip() for token in payload.get("subcomponents", []) if str(token).strip()]
            if isinstance(payload.get("subcomponents"), list)
            else [],
            product_layer=str(payload.get("product_layer", "")).strip(),
        )
    return component_registry.ComponentEntry(
        component_id=str(row["component_id"]).strip(),
        name=str(row["name"]).strip(),
        kind=str(payload.get("kind", "")).strip(),
        category=str(payload.get("category", "")).strip(),
        qualification=str(payload.get("qualification", "")).strip(),
        aliases=_json_list(str(row["aliases_json"])),
        path_prefixes=[str(token).strip() for token in payload.get("path_prefixes", []) if str(token).strip()]
        if isinstance(payload.get("path_prefixes"), list)
        else [],
        workstreams=_json_list(str(row["workstreams_json"])),
        diagrams=_json_list(str(row["diagrams_json"])),
        owner=str(row["owner"]).strip(),
        status=str(row["status"]).strip(),
        what_it_is=str(payload.get("what_it_is", "")).strip(),
        why_tracked=str(payload.get("why_tracked", "")).strip(),
        spec_ref=str(row["spec_ref"]).strip(),
        sources=[str(token).strip() for token in payload.get("sources", []) if str(token).strip()]
        if isinstance(payload.get("sources"), list)
        else [],
        subcomponents=[str(token).strip() for token in payload.get("subcomponents", []) if str(token).strip()]
        if isinstance(payload.get("subcomponents"), list)
        else [],
        product_layer=str(payload.get("product_layer", "")).strip(),
    )

def load_component_index(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, component_registry.ComponentEntry]:
    root = Path(repo_root).resolve()
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="component_index"):
        connection = _connect(root)
        try:
            rows = connection.execute("SELECT * FROM components ORDER BY component_id").fetchall()
            component_index = {
                str(row["component_id"]).strip(): _component_entry_from_runtime_row(row)
                for row in rows
                if str(row["component_id"]).strip()
            }
            if _odylith_ablation_active(repo_root=root):
                return _apply_odylith_component_index_ablation(component_index)
            return component_index
        finally:
            connection.close()
    manifest_path = component_registry.default_manifest_path(repo_root=root)
    catalog_path = root / component_registry.DEFAULT_CATALOG_PATH
    ideas_root = root / component_registry.DEFAULT_IDEAS_ROOT
    if not manifest_path.is_file():
        return {}
    components, _alias_to_component, _diagnostics = component_registry.build_component_index(
        repo_root=root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
    )
    if _odylith_ablation_active(repo_root=root):
        return _apply_odylith_component_index_ablation(components)
    return components

def load_registry_list(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> list[dict[str, Any]]:
    components = load_component_index(repo_root=repo_root, runtime_mode=runtime_mode)
    rows: list[dict[str, Any]] = []
    for component_id in sorted(components):
        entry = components[component_id]
        rows.append(
            {
                "component_id": entry.component_id,
                "name": entry.name,
                "kind": entry.kind,
                "category": entry.category,
                "qualification": entry.qualification,
                "owner": entry.owner,
                "status": entry.status,
                "what_it_is": entry.what_it_is,
                "why_tracked": entry.why_tracked,
                "aliases": list(entry.aliases),
            }
        )
    return rows

def load_component_registry_snapshot(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    odylith_ablation_active = _odylith_ablation_active(repo_root=root)
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="component_registry_snapshot"):
        connection = _connect(root)
        try:
            component_rows = connection.execute("SELECT * FROM components ORDER BY component_id").fetchall()
            spec_rows = connection.execute("SELECT * FROM component_specs ORDER BY component_id").fetchall()
            trace_rows = connection.execute(
                "SELECT component_id, bucket, path FROM component_traceability ORDER BY component_id, bucket, path"
            ).fetchall()
            event_rows = connection.execute(
                """
                SELECT event_index, ts_iso, kind, summary, workstreams_json, artifacts_json,
                       explicit_components_json, mapped_components_json, confidence, meaningful
                FROM registry_events
                ORDER BY ts_iso DESC, event_index DESC
                """
            ).fetchall()
            state_row = connection.execute(
                "SELECT payload_json FROM projection_state WHERE name = 'components'"
            ).fetchone()
        finally:
            connection.close()
        components = {
            str(row["component_id"]).strip(): _component_entry_from_runtime_row(row)
            for row in component_rows
            if str(row["component_id"]).strip()
        }
        payload = json.loads(str(state_row["payload_json"] or "{}")) if state_row is not None else {}
        diagnostics = [str(item) for item in payload.get("diagnostics", []) if str(item).strip()] if isinstance(payload, Mapping) else []
        candidate_queue = [
            dict(item)
            for item in payload.get("candidate_queue", [])
            if isinstance(payload, Mapping) and isinstance(payload.get("candidate_queue"), list) and isinstance(item, Mapping)
        ] if isinstance(payload, Mapping) else []
        unmapped_meaningful_events = [
            component_registry.MappedEvent(
                event_index=int(item.get("event_index", 0) or 0),
                ts_iso=str(item.get("ts_iso", "")).strip(),
                kind=str(item.get("kind", "")).strip(),
                summary=str(item.get("summary", "")).strip(),
                workstreams=[str(token).strip() for token in item.get("workstreams", []) if str(token).strip()]
                if isinstance(item.get("workstreams"), list)
                else [],
                artifacts=[str(token).strip() for token in item.get("artifacts", []) if str(token).strip()]
                if isinstance(item.get("artifacts"), list)
                else [],
                explicit_components=[str(token).strip() for token in item.get("explicit_components", []) if str(token).strip()]
                if isinstance(item.get("explicit_components"), list)
                else [],
                mapped_components=[str(token).strip() for token in item.get("mapped_components", []) if str(token).strip()]
                if isinstance(item.get("mapped_components"), list)
                else [],
                confidence=str(item.get("confidence", "")).strip(),
                meaningful=bool(item.get("meaningful")),
            )
            for item in payload.get("unmapped_meaningful_events", [])
            if isinstance(payload, Mapping) and isinstance(payload.get("unmapped_meaningful_events"), list) and isinstance(item, Mapping)
        ] if isinstance(payload, Mapping) else []
        mapped_events = [
            component_registry.MappedEvent(
                event_index=int(row["event_index"] or 0),
                ts_iso=str(row["ts_iso"]).strip(),
                kind=str(row["kind"]).strip(),
                summary=str(row["summary"]).strip(),
                workstreams=_json_list(str(row["workstreams_json"])),
                artifacts=_json_list(str(row["artifacts_json"])),
                explicit_components=_json_list(str(row["explicit_components_json"])),
                mapped_components=_json_list(str(row["mapped_components_json"])),
                confidence=str(row["confidence"]).strip(),
                meaningful=bool(int(row["meaningful"] or 0)),
            )
            for row in event_rows
        ]
        report = component_registry.ComponentRegistryReport(
            components=components,
            mapped_events=mapped_events,
            unmapped_meaningful_events=unmapped_meaningful_events,
            candidate_queue=candidate_queue,
            forensic_coverage=component_registry.build_component_forensic_coverage(
                component_index=components,
                mapped_events=mapped_events,
                repo_root=repo_root,
            ),
            diagnostics=diagnostics,
        )
        spec_snapshots: dict[str, component_registry.ComponentSpecSnapshot] = {}
        for row in spec_rows:
            component_id = str(row["component_id"]).strip()
            if not component_id:
                continue
            feature_history_payload = json.loads(str(row["feature_history_json"] or "[]"))
            skill_tiers_payload = json.loads(str(row["skill_trigger_tiers_json"] or "{}"))
            playbook_payload = json.loads(str(row["validation_playbook_commands_json"] or "[]"))
            spec_snapshots[component_id] = component_registry.ComponentSpecSnapshot(
                title=str(row["title"]).strip(),
                last_updated=str(row["last_updated"]).strip(),
                feature_history=[dict(item) for item in feature_history_payload if isinstance(item, Mapping)]
                if isinstance(feature_history_payload, list)
                else [],
                markdown=str(row["markdown"] or ""),
                skill_trigger_tiers=dict(skill_tiers_payload) if isinstance(skill_tiers_payload, Mapping) else {},
                skill_trigger_structure=str(row["skill_trigger_structure"]).strip(),
                validation_playbook_commands=[dict(item) for item in playbook_payload if isinstance(item, Mapping)]
                if isinstance(playbook_payload, list)
                else [],
            )
        traceability: dict[str, dict[str, list[str]]] = {}
        for row in trace_rows:
            component_id = str(row["component_id"]).strip()
            bucket = str(row["bucket"]).strip()
            path = str(row["path"]).strip()
            if not component_id or not bucket or not path:
                continue
            traceability.setdefault(
                component_id,
                {"runbooks": [], "developer_docs": [], "code_references": []},
            ).setdefault(bucket, []).append(path)
        for component_id, buckets in traceability.items():
            for bucket, values in buckets.items():
                buckets[bucket] = _dedupe_strings(values)
        snapshot = {
            "report": report,
            "traceability": traceability,
            "spec_snapshots": spec_snapshots,
            "odylith_switch": _odylith_switch_snapshot(repo_root=root),
        }
        if odylith_ablation_active:
            return _apply_odylith_registry_snapshot_ablation(
                repo_root=root,
                report=report,
                traceability=traceability,
                spec_snapshots=spec_snapshots,
            )
        return snapshot

    manifest_path = component_registry.default_manifest_path(repo_root=root)
    catalog_path = root / component_registry.DEFAULT_CATALOG_PATH
    ideas_root = root / component_registry.DEFAULT_IDEAS_ROOT
    stream_path = root / component_registry.DEFAULT_STREAM_PATH
    report = component_registry.build_component_registry_report(
        repo_root=root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        stream_path=stream_path,
    )
    traceability = component_registry.build_component_traceability_index(
        repo_root=root,
        components=report.components,
    )
    spec_snapshots = {
        component_id: component_registry.load_component_spec_snapshot(spec_path=root / entry.spec_ref)
        for component_id, entry in report.components.items()
        if entry.spec_ref and (root / entry.spec_ref).is_file()
    }
    snapshot = {
        "report": report,
        "traceability": traceability,
        "spec_snapshots": spec_snapshots,
        "odylith_switch": _odylith_switch_snapshot(repo_root=root),
    }
    if odylith_ablation_active:
        return _apply_odylith_registry_snapshot_ablation(
            repo_root=root,
            report=report,
            traceability=traceability,
            spec_snapshots=spec_snapshots,
        )
    return snapshot

def load_registry_detail(
    *,
    repo_root: Path,
    component_id: str,
    runtime_mode: str = "auto",
    detail_level: str = "full",
) -> dict[str, Any] | None:
    token = str(component_id or "").strip().lower()
    if not token:
        return None
    root = Path(repo_root).resolve()
    normalized_detail_level = str(detail_level or "").strip().lower()
    if normalized_detail_level == "grounding_light" and not _odylith_ablation_active(repo_root=root):
        def _load_runtime_detail() -> dict[str, Any] | None:
            try:
                connection = _connect(root)
            except RuntimeError:
                return None
            try:
                component_row = connection.execute(
                    "SELECT * FROM components WHERE component_id = ? LIMIT 1",
                    (token,),
                ).fetchone()
                if component_row is None:
                    return None
                spec_row = connection.execute(
                    "SELECT * FROM component_specs WHERE component_id = ? LIMIT 1",
                    (token,),
                ).fetchone()
                trace_rows = connection.execute(
                    """
                    SELECT bucket, path
                    FROM component_traceability
                    WHERE component_id = ?
                    ORDER BY bucket, path
                    """,
                    (token,),
                ).fetchall()
                return odylith_context_engine_registry_detail_runtime.build_runtime_registry_detail(
                    entry=_component_entry_from_runtime_row(component_row),
                    spec_row=spec_row,
                    trace_rows=trace_rows,
                )
            finally:
                connection.close()

        cache_key = f"{root}:reasoning"
        if _PROCESS_WARM_CACHE_FINGERPRINTS.get(cache_key, ""):
            detail = _cached_projection_rows(
                repo_root=root,
                cache_name=f"registry_detail_grounding_light:{token}",
                loader=_load_runtime_detail,
                scope="reasoning",
            )
        else:
            detail = _load_runtime_detail()
        if isinstance(detail, Mapping):
            return dict(detail)
    snapshot = load_component_registry_snapshot(repo_root=repo_root, runtime_mode=runtime_mode)
    return odylith_context_engine_registry_detail_runtime.build_registry_detail(
        snapshot=snapshot,
        component_id=token,
        detail_level=detail_level,
    )

"""Odylith Context Engine Projection Backlog Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

def _store():
    from odylith.runtime.context_engine import odylith_context_engine_store as store

    return store


from typing import Any

from odylith.runtime.common.casebook_bug_ids import BUG_ID_FIELD, resolve_casebook_bug_id


def _projection_search():
    from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime as module

    return module


def _cached_projection_rows(**kwargs: object) -> Any:
    return _projection_search()._cached_projection_rows(**kwargs)


def _connect(root: Path):  # noqa: ANN201
    return _projection_search()._connect(root)


def _load_backlog_projection(**kwargs: object) -> dict[str, Any]:
    return dict(_projection_search()._load_backlog_projection(**kwargs))


def _warm_runtime(**kwargs: object) -> bool:
    return bool(_projection_search()._warm_runtime(**kwargs))


def _warm_cache_fingerprints():
    return _projection_search()._PROCESS_WARM_CACHE_FINGERPRINTS

def load_backlog_rows(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, Any]:
    root = _store().Path(repo_root).resolve()
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="backlog_rows"):
        def _load_runtime_rows() -> dict[str, Any]:
            connection = _connect(root)
            try:
                result: dict[str, Any] = {
                    "updated_utc": str(
                        _store().json.loads(
                            (
                                connection.execute(
                                    "SELECT payload_json FROM projection_state WHERE name = 'workstreams'"
                                ).fetchone() or {"payload_json": "{}"}
                            )["payload_json"]
                        ).get("updated_utc", "")
                    ).strip(),
                    "rationale_map": _load_backlog_projection(repo_root=root).get("rationale_map", {}),
                }
                for section in ("active", "execution", "finished", "parked"):
                    rows = connection.execute(
                        """
                        SELECT rank, idea_id, title, priority, ordering_score, metadata_json, idea_file
                        FROM workstreams
                        WHERE section = ?
                        ORDER BY
                            CASE
                                WHEN rank = '-' THEN 999999
                                WHEN rank GLOB '[0-9]*' THEN CAST(rank AS INTEGER)
                                ELSE 999999
                            END,
                            idea_id
                        """,
                        (section,),
                    ).fetchall()
                    values: list[dict[str, str]] = []
                    for row in rows:
                        metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
                        values.append(
                            {
                                "rank": str(row["rank"]),
                                "idea_id": str(row["idea_id"]),
                                "title": str(row["title"]),
                                "priority": str(row["priority"]),
                                "ordering_score": str(row["ordering_score"]),
                                "commercial_value": str(metadata.get("commercial_value", "")).strip(),
                                "product_impact": str(metadata.get("product_impact", "")).strip(),
                                "market_value": str(metadata.get("market_value", "")).strip(),
                                "sizing": str(metadata.get("sizing", "")).strip(),
                                "complexity": str(metadata.get("complexity", "")).strip(),
                                "status": str(metadata.get("status", "")).strip(),
                                "link": (
                                    f"[{_store().Path(str(row['idea_file'])).stem}]({str(row['idea_file'])})"
                                    if str(row["idea_file"]).strip()
                                    else ""
                                ),
                            }
                        )
                    result[section] = values
                return result
            finally:
                connection.close()

        return _cached_projection_rows(
            repo_root=root,
            cache_name="backlog_rows",
            loader=_load_runtime_rows,
            scope="default",
        )
    return _load_backlog_projection(repo_root=root)

def _markdown_section_bodies(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for raw_line in str(text or "").splitlines():
        match = _store()._HEADER_RE.match(raw_line)
        if match:
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = str(match.group(1) or "").strip()
            lines = []
            continue
        if current is not None:
            lines.append(raw_line.rstrip())
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


def _metadata_id_list(value: object, pattern) -> list[str]:  # noqa: ANN001
    values: list[str] = []
    seen: set[str] = set()
    for raw in str(value or "").replace(";", ",").split(","):
        token = str(raw or "").strip().upper()
        if not token or not pattern.fullmatch(token) or token in seen:
            continue
        seen.add(token)
        values.append(token)
    return values


def _normalize_backlog_detail_payload(
    *,
    idea_id: str,
    idea_file: str,
    metadata: Mapping[str, object],
    sections: Mapping[str, str],
    promoted_to_plan: str,
) -> dict[str, Any]:
    normalized_sections = {
        str(key).strip(): str(value).strip()
        for key, value in sections.items()
        if str(key).strip()
    }
    founder_pov = (
        str(normalized_sections.get("Product View", "")).strip()
        or str(normalized_sections.get("Founder POV", "")).strip()
    )
    payload: dict[str, Any] = {
        "idea_id": str(idea_id or "").strip().upper(),
        "idea_file": str(idea_file or "").strip(),
        "metadata": dict(metadata) if isinstance(metadata, _store().Mapping) else {},
        "sections": normalized_sections,
        "promoted_to_plan": str(promoted_to_plan or "").strip(),
        "title": str(metadata.get("title", "")).strip(),
        "priority": str(metadata.get("priority", "")).strip(),
        "ordering_score": str(metadata.get("ordering_score", "")).strip(),
        "commercial_value": str(metadata.get("commercial_value", "")).strip(),
        "product_impact": str(metadata.get("product_impact", "")).strip(),
        "market_value": str(metadata.get("market_value", "")).strip(),
        "sizing": str(metadata.get("sizing", "")).strip(),
        "complexity": str(metadata.get("complexity", "")).strip(),
        "status": str(metadata.get("status", "")).strip(),
        "confidence": str(metadata.get("confidence", "")).strip(),
        "founder_override": str(metadata.get("founder_override", "")).strip(),
        "ordering_rationale": str(metadata.get("ordering_rationale", "")).strip(),
        "impacted_parts": str(metadata.get("impacted_parts", "")).strip(),
        "implemented_summary": str(metadata.get("implemented_summary", "")).strip(),
        "workstream_type": str(metadata.get("workstream_type", "")).strip().lower(),
        "problem": str(normalized_sections.get("Problem", "")).strip(),
        "customer": str(normalized_sections.get("Customer", "")).strip(),
        "opportunity": str(normalized_sections.get("Opportunity", "")).strip(),
        "founder_pov": founder_pov,
        "success_metrics": (
            str(normalized_sections.get("Success Metrics", "")).strip()
            or str(normalized_sections.get("Success Metric", "")).strip()
        ),
        "workstream_parent": str(metadata.get("workstream_parent", "")).strip(),
        "workstream_children": _metadata_id_list(metadata.get("workstream_children", ""), _store()._WORKSTREAM_ID_RE),
        "workstream_depends_on": _metadata_id_list(metadata.get("workstream_depends_on", ""), _store()._WORKSTREAM_ID_RE),
        "workstream_blocks": _metadata_id_list(metadata.get("workstream_blocks", ""), _store()._WORKSTREAM_ID_RE),
        "related_diagram_ids": _metadata_id_list(metadata.get("related_diagram_ids", ""), _store()._DIAGRAM_ID_RE),
        "workstream_reopens": _metadata_id_list(metadata.get("workstream_reopens", ""), _store()._WORKSTREAM_ID_RE),
        "workstream_reopened_by": _metadata_id_list(metadata.get("workstream_reopened_by", ""), _store()._WORKSTREAM_ID_RE),
        "workstream_split_from": _metadata_id_list(metadata.get("workstream_split_from", ""), _store()._WORKSTREAM_ID_RE),
        "workstream_split_into": _metadata_id_list(metadata.get("workstream_split_into", ""), _store()._WORKSTREAM_ID_RE),
        "workstream_merged_into": _metadata_id_list(metadata.get("workstream_merged_into", ""), _store()._WORKSTREAM_ID_RE),
        "workstream_merged_from": _metadata_id_list(metadata.get("workstream_merged_from", ""), _store()._WORKSTREAM_ID_RE),
    }
    return payload


def _grounding_light_backlog_detail_payload(
    *,
    idea_id: str,
    idea_file: str,
    metadata: Mapping[str, object],
    promoted_to_plan: str,
) -> dict[str, Any]:
    return {
        "idea_id": str(idea_id or "").strip().upper(),
        "idea_file": str(idea_file or "").strip(),
        "metadata": dict(metadata) if isinstance(metadata, _store().Mapping) else {},
        "promoted_to_plan": str(promoted_to_plan or "").strip(),
    }

def load_backlog_list(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, Any]:
    return load_backlog_rows(repo_root=repo_root, runtime_mode=runtime_mode)

def _runtime_backlog_detail_rows(
    *,
    repo_root: Path,
) -> dict[str, dict[str, Any]]:
    root = _store().Path(repo_root).resolve()

    def _load() -> dict[str, dict[str, Any]]:
        connection = _connect(root)
        try:
            rows = connection.execute(
                """
                SELECT idea_id, metadata_json, idea_file
                FROM workstreams
                ORDER BY idea_id
                """
            ).fetchall()
        finally:
            connection.close()
        payload: dict[str, dict[str, Any]] = {}
        for row in rows:
            token = str(row["idea_id"] or "").strip().upper()
            if not _store()._WORKSTREAM_ID_RE.fullmatch(token):
                continue
            try:
                metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
            except _store().json.JSONDecodeError:
                metadata = {}
            payload[token] = {
                "metadata": dict(metadata) if isinstance(metadata, _store().Mapping) else {},
                "idea_file": str(row["idea_file"] or "").strip(),
            }
        return payload

    cache_key = f"{root}:default"
    if _warm_cache_fingerprints().get(cache_key, ""):
        rows = _cached_projection_rows(
            repo_root=root,
            cache_name="workstream_detail_rows",
            loader=_load,
            scope="default",
        )
    else:
        rows = _load()
    return dict(rows) if isinstance(rows, _store().Mapping) else {}

def _runtime_backlog_detail(
    *,
    repo_root: Path,
    workstream_id: str,
    detail_level: str = "full",
) -> dict[str, Any] | None:
    root = _store().Path(repo_root).resolve()
    row = _runtime_backlog_detail_rows(repo_root=root).get(str(workstream_id or "").strip().upper())
    if not isinstance(row, _store().Mapping):
        return None
    idea_token = str(row.get("idea_file", "")).strip()
    if not idea_token:
        return None
    idea_path = (root / idea_token).resolve() if not _store().Path(idea_token).is_absolute() else _store().Path(idea_token).resolve()
    if not idea_path.is_file():
        return None
    metadata = dict(row.get("metadata", {})) if isinstance(row.get("metadata"), _store().Mapping) else {}
    metadata.setdefault("idea_id", str(workstream_id or "").strip().upper())
    promoted_to_plan = str(metadata.get("promoted_to_plan", "")).strip()
    if promoted_to_plan:
        metadata["promoted_to_plan"] = _store()._normalize_repo_token(promoted_to_plan, repo_root=root)
    idea_file = str(idea_path.relative_to(root)) if idea_path.is_relative_to(root) else str(idea_path)
    if str(detail_level or "").strip().lower() == "grounding_light":
        return _grounding_light_backlog_detail_payload(
            idea_id=str(workstream_id or "").strip().upper(),
            idea_file=idea_file,
            metadata=metadata,
            promoted_to_plan=str(metadata.get("promoted_to_plan", "")).strip(),
        )
    raw_text = _store()._raw_text(idea_path)
    normalized = _normalize_backlog_detail_payload(
        idea_id=str(workstream_id or "").strip().upper(),
        idea_file=idea_file,
        metadata=metadata,
        sections=_markdown_section_bodies(raw_text),
        promoted_to_plan=str(metadata.get("promoted_to_plan", "")).strip(),
    )
    normalized["search_body"] = raw_text
    return normalized

def load_backlog_detail(
    *,
    repo_root: Path,
    workstream_id: str,
    runtime_mode: str = "auto",
    detail_level: str = "full",
) -> dict[str, Any] | None:
    root = _store().Path(repo_root).resolve()
    token = str(workstream_id or "").strip().upper()
    normalized_detail_level = str(detail_level or "full").strip().lower() or "full"
    if not _store()._WORKSTREAM_ID_RE.fullmatch(token):
        return None
    del runtime_mode
    if not _store()._odylith_ablation_active(repo_root=root):
        try:
            runtime_detail = _runtime_backlog_detail(
                repo_root=root,
                workstream_id=token,
                detail_level=normalized_detail_level,
            )
        except RuntimeError:
            runtime_detail = None
        if runtime_detail is not None:
            return runtime_detail
    spec = _store()._load_idea_specs(repo_root=root).get(token)
    if spec is None:
        return None
    metadata = dict(spec.metadata)
    if str(metadata.get("promoted_to_plan", "")).strip():
        metadata["promoted_to_plan"] = _store()._normalize_repo_token(str(metadata.get("promoted_to_plan", "")).strip(), repo_root=root)
    idea_file = str(spec.path.relative_to(root)) if spec.path.is_relative_to(root) else str(spec.path)
    if normalized_detail_level == "grounding_light":
        return _grounding_light_backlog_detail_payload(
            idea_id=token,
            idea_file=idea_file,
            metadata=metadata,
            promoted_to_plan=str(metadata.get("promoted_to_plan", "")).strip(),
        )
    raw_text = _store()._raw_text(spec.path)
    normalized = _normalize_backlog_detail_payload(
        idea_id=token,
        idea_file=idea_file,
        metadata=metadata,
        sections=_markdown_section_bodies(raw_text),
        promoted_to_plan=str(metadata.get("promoted_to_plan", "")).strip(),
    )
    normalized["search_body"] = raw_text
    return normalized

def load_backlog_document(
    *,
    repo_root: Path,
    workstream_id: str,
    view: str,
    runtime_mode: str = "auto",
) -> dict[str, Any] | None:
    del runtime_mode  # detail/document bodies are still sourced from markdown contracts today.
    root = _store().Path(repo_root).resolve()
    token = str(workstream_id or "").strip().upper()
    mode = str(view or "").strip().lower()
    detail = load_backlog_detail(repo_root=root, workstream_id=token)
    if detail is None:
        return None
    if mode == "spec":
        spec_token = str(detail.get("idea_file", "")).strip()
        spec_path = (root / spec_token).resolve() if spec_token and not _store().Path(spec_token).is_absolute() else _store().Path(spec_token).resolve()
        return {
            "idea_id": token,
            "view": "spec",
            "path": str(spec_path.relative_to(root)) if spec_path.is_relative_to(root) else str(spec_path),
            "markdown": _store()._raw_text(spec_path),
        }
    if mode == "plan":
        plan_token = str(detail.get("promoted_to_plan", "")).strip()
        if not plan_token:
            return None
        plan_path = (root / plan_token).resolve() if not _store().Path(plan_token).is_absolute() else _store().Path(plan_token).resolve()
        if not plan_path.is_file():
            return None
        return {
            "idea_id": token,
            "view": "plan",
            "path": str(plan_path.relative_to(root)) if plan_path.is_relative_to(root) else str(plan_path),
            "markdown": _store()._raw_text(plan_path),
        }
    return None

def load_plan_rows(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, list[dict[str, str]]]:
    root = _store().Path(repo_root).resolve()
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="plan_rows"):
        def _load_runtime_rows() -> dict[str, list[dict[str, str]]]:
            connection = _connect(root)
            try:
                result: dict[str, list[dict[str, str]]] = {}
                for section in ("active", "parked", "done"):
                    rows = connection.execute(
                        """
                        SELECT plan_path, status, created, updated, backlog
                        FROM plans
                        WHERE section = ?
                        ORDER BY updated DESC, plan_path
                        """,
                        (section,),
                    ).fetchall()
                    result[section] = [
                        {
                            "Plan": f"`{row['plan_path']}`",
                            "Status": str(row["status"]),
                            "Created": str(row["created"]),
                            "Updated": str(row["updated"]),
                            "Backlog": f"`{row['backlog']}`" if str(row["backlog"]) else "`-`",
                        }
                        for row in rows
                    ]
                return result
            finally:
                connection.close()

        return _cached_projection_rows(
            repo_root=root,
            cache_name="plan_rows",
            loader=_load_runtime_rows,
            scope="default",
        )
    return _store()._load_plan_projection(repo_root=root)

def load_bug_rows(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> list[dict[str, str]]:
    root = _store().Path(repo_root).resolve()
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="bug_rows"):
        def _load_runtime_rows() -> list[dict[str, str]]:
            connection = _connect(root)
            try:
                rows = connection.execute(
                    """
                    SELECT bug_id, date, title, severity, components, status, link_target, source_path
                    FROM bugs
                    ORDER BY date DESC, title
                    """
                ).fetchall()
                payload_rows: list[dict[str, str]] = []
                for row in rows:
                    source_path = str(row["source_path"] or "").strip()
                    index_path = (root / source_path).resolve() if source_path else root / "bugs" / "INDEX.md"
                    normalized_link = _store()._normalize_bug_link_target(
                        repo_root=root,
                        index_path=index_path,
                        link_target=str(row["link_target"] or "").strip(),
                    )
                    if normalized_link and not (root / normalized_link).is_file():
                        continue
                    bug_id = resolve_casebook_bug_id(
                        explicit_bug_id=str(row["bug_id"] or "").strip(),
                        seed=normalized_link or f"{row['date']}::{row['title']}",
                    )
                    payload = {
                        BUG_ID_FIELD: bug_id,
                        "Date": str(row["date"]),
                        "Title": str(row["title"]),
                        "Severity": str(row["severity"]),
                        "Components": str(row["components"]),
                        "Status": _store().canonicalize_bug_status(str(row["status"])),
                        "Link": f"[bug]({normalized_link})" if normalized_link else "",
                        "IndexPath": source_path or "odylith/casebook/bugs/INDEX.md",
                    }
                    if _store()._is_bug_placeholder_row(payload):
                        continue
                    payload_rows.append(payload)
                return payload_rows
            finally:
                connection.close()

        return _cached_projection_rows(
            repo_root=root,
            cache_name="bug_rows",
            loader=_load_runtime_rows,
            scope="default",
        )
    return _store()._load_bug_projection(repo_root=root)

def load_bug_snapshot(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> list[dict[str, Any]]:
    root = _store().Path(repo_root).resolve()
    rows = load_bug_rows(repo_root=root, runtime_mode=runtime_mode)
    bug_lookup = _store()._build_bug_reference_lookup(rows=rows, repo_root=root)
    component_index = _store().load_component_index(repo_root=root, runtime_mode=runtime_mode)
    component_rows = _store()._component_rows_from_index(component_index)
    diagram_lookup = {
        str(row.get("diagram_id", "")).strip().upper(): {
            "diagram_id": str(row.get("diagram_id", "")).strip().upper(),
            "title": str(row.get("title", "")).strip(),
            "slug": str(row.get("slug", "")).strip(),
        }
        for row in _store()._load_diagram_projection(repo_root=root)
        if str(row.get("diagram_id", "")).strip()
    }
    snapshot: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, _store().Mapping):
            continue
        if _store()._is_bug_placeholder_row(row):
            continue
        link_target = _store()._parse_link_target(str(row.get("Link", "")))
        bug_id = resolve_casebook_bug_id(
            explicit_bug_id=str(row.get(BUG_ID_FIELD, "")).strip(),
            seed=link_target or f"{row.get('Date', '')}::{row.get('Title', '')}",
        )
        bug_key = link_target or f"{row.get('Date', '')}::{row.get('Title', '')}"
        bug_path = (root / link_target).resolve() if link_target else None
        raw_text = _store()._raw_text(bug_path) if bug_path is not None else ""
        lines = raw_text.splitlines() if raw_text else []
        fields = _store()._parse_bug_entry_fields(lines) if lines else {}

        date = str(row.get("Date", "")).strip() or str(fields.get("Created", "")).strip()
        title = str(row.get("Title", "")).strip()
        severity = str(row.get("Severity", "")).strip() or str(fields.get("Severity", "")).strip()
        status = _store().canonicalize_bug_status(str(row.get("Status", "")).strip() or str(fields.get("Status", "")).strip())
        if status:
            fields["Status"] = status
        components_raw = str(row.get("Components", "")).strip() or str(fields.get("Components Affected", "")).strip()
        components = _store()._parse_component_tokens(components_raw)
        path_refs = _store()._extract_path_refs(
            text="\n".join(
                token
                for token in (
                    raw_text,
                    str(fields.get("Code References", "")).strip(),
                    str(fields.get("Runbook References", "")).strip(),
                    str(fields.get("Components Affected", "")).strip(),
                )
                if token
            ),
            repo_root=root,
        )
        ref_buckets = _store()._classify_bug_path_refs(path_refs)
        component_matches = _store()._component_matches_for_bug_paths(
            component_rows=component_rows,
            component_index=component_index,
            path_refs=path_refs,
        )
        diagram_refs = _store()._diagram_refs_for_bug_components(
            component_matches=component_matches,
            diagram_lookup=diagram_lookup,
        )
        workstreams = _store()._extract_workstream_refs(
            "\n".join(
                token
                for token in (
                    raw_text,
                    str(fields.get("Related Incidents/Bugs", "")).strip(),
                    str(fields.get("Config/Flags", "")).strip(),
                )
                if token
            )
        )
        related_bug_refs = _store()._related_bug_refs_from_text(
            text=str(fields.get("Related Incidents/Bugs", "")).strip(),
            bug_lookup=bug_lookup,
            repo_root=root,
        )
        agent_guidance = _store()._bug_agent_guidance(
            fields=fields,
            ref_buckets=ref_buckets,
            component_matches=component_matches,
            workstreams=workstreams,
            related_bug_refs=related_bug_refs,
        )
        detail_sections = _store()._ordered_bug_detail_sections(fields)
        search_text = "\n".join(
            token
            for token in (
                bug_id,
                title,
                severity,
                status,
                components_raw,
                raw_text,
                "\n".join(match.get("name", "") for match in component_matches),
                "\n".join(ref.get("title", "") for ref in related_bug_refs),
                "\n".join(
                    str(item.get("value", "")).strip()
                    for item in agent_guidance.get("lessons", [])
                    if isinstance(item, _store().Mapping)
                ),
                "\n".join(str(item).strip() for item in agent_guidance.get("preflight_checks", [])),
            )
            if token
        )
        is_open = _store()._bug_is_open(status)
        intelligence_coverage = _store()._bug_intelligence_coverage(fields=fields, severity=severity)
        snapshot.append(
            {
                "bug_id": bug_id,
                "bug_key": str(bug_key).strip(),
                "title": title,
                "date": date,
                "severity": severity,
                "severity_token": str(severity).strip().lower(),
                "status": status,
                "status_token": str(status).strip().lower(),
                "components": components_raw,
                "component_tokens": components,
                "archive_bucket": _store()._bug_archive_bucket_from_link_target(link_target),
                "source_path": link_target,
                "source_exists": bool(link_target and bug_path is not None and bug_path.is_file()),
                "is_open": is_open,
                "is_open_critical": is_open and str(severity).strip().lower() in _store()._BUG_CRITICAL_SEVERITIES,
                "workstreams": workstreams,
                "primary_workstream": workstreams[0] if workstreams else "",
                "summary": _store()._bug_summary_from_fields(fields, lines),
                "detail_sections": detail_sections,
                "fields": dict(fields),
                "path_refs": path_refs,
                "code_refs": ref_buckets["code"],
                "doc_refs": ref_buckets["docs"],
                "test_refs": ref_buckets["tests"],
                "contract_refs": ref_buckets["contracts"],
                "component_matches": component_matches,
                "diagram_refs": diagram_refs,
                "related_bug_refs": related_bug_refs,
                "agent_guidance": agent_guidance,
                "intelligence_coverage": intelligence_coverage,
                "search_text": search_text,
            }
        )
    if snapshot:
        from odylith.runtime.governance import proof_state as proof_state_runtime

        proof_scopes = [
            {
                "scope_key": f"bug:{str(row.get('bug_id') or row.get('source_path') or row.get('bug_key') or index)}",
                "scope_type": "bug",
                "scope_id": str(row.get("bug_id") or row.get("source_path") or row.get("bug_key") or "").strip(),
                "scope_label": str(row.get("title", "")).strip(),
                "evidence_context": {
                    "linked_workstreams": list(row.get("workstreams", []))
                    if isinstance(row.get("workstreams"), list)
                    else [],
                    "linked_bug_ids": [str(row.get("bug_id", "")).strip()] if str(row.get("bug_id", "")).strip() else [],
                    "linked_bug_paths": [
                        token
                        for token in (
                            str(row.get("source_path", "")).strip(),
                            str(row.get("bug_key", "")).strip(),
                        )
                        if token
                    ],
                },
            }
            for index, row in enumerate(snapshot)
        ]
        annotated_proof_scopes = proof_state_runtime.annotate_scopes_with_proof_state(
            repo_root=root,
            scopes=proof_scopes,
        )
        proof_lookup = {
            str(row.get("scope_key", "")).strip(): row
            for row in annotated_proof_scopes
            if isinstance(row, _store().Mapping) and str(row.get("scope_key", "")).strip()
        }
        for index, row in enumerate(snapshot):
            scope_key = f"bug:{str(row.get('bug_id') or row.get('source_path') or row.get('bug_key') or index)}"
            annotated = proof_lookup.get(scope_key, {})
            proof_payload = proof_state_runtime.normalize_proof_state(annotated.get("proof_state", {}))
            if proof_payload:
                row["proof_state"] = proof_payload
            proof_resolution = (
                dict(annotated.get("proof_state_resolution", {}))
                if isinstance(annotated.get("proof_state_resolution"), _store().Mapping)
                else {}
            )
            if proof_resolution:
                row["proof_state_resolution"] = proof_resolution
            claim_guard = dict(annotated.get("claim_guard", {})) if isinstance(annotated.get("claim_guard"), _store().Mapping) else {}
            if claim_guard:
                row["claim_guard"] = claim_guard
    return snapshot

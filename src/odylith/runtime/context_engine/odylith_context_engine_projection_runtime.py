"""Projection source loaders extracted from the context engine store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common.casebook_bug_ids import BUG_ID_FIELD, load_casebook_bug_id_from_markdown, resolve_casebook_bug_id


def _host():
    from odylith.runtime.context_engine import odylith_context_engine_store as host

    return host


def _archive_files(root: Path) -> list[Path]:
    host = _host()
    if not root.is_dir():
        return []
    return sorted(path for path in root.glob(host._ARCHIVE_GLOB) if path.is_file())  # noqa: SLF001


def _collect_markdown_sections(path: Path) -> dict[str, list[str]]:
    host = _host()
    if not path.is_file():
        return {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = host._HEADER_RE.match(raw)  # noqa: SLF001
        if match:
            current = str(match.group(1)).strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(raw)
    return sections


def _parse_markdown_table(lines: Sequence[str]) -> tuple[list[str], list[dict[str, str]]]:
    host = _host()
    headers: list[str] = []
    rows: list[dict[str, str]] = []
    started = False
    pending_row = ""
    for raw in lines:
        line = str(raw).strip()
        if pending_row:
            pending_row = f"{pending_row} {line}".strip()
            cells = [cell.strip() for cell in pending_row.split("|")[1:-1]]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells, strict=True)))
                pending_row = ""
            continue
        if not host._TABLE_ROW_RE.match(line):  # noqa: SLF001
            if started and line.startswith("|"):
                cells = [cell.strip() for cell in line.split("|")[1:-1]]
                if len(cells) != len(headers):
                    pending_row = line
                    continue
                rows.append(dict(zip(headers, cells, strict=True)))
                continue
            if started and rows:
                break
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if not cells:
            continue
        if all(host.re.fullmatch(r"-+", token or "") for token in cells):  # noqa: SLF001
            continue
        if not started:
            headers = cells
            started = True
            continue
        if len(cells) != len(headers):
            pending_row = line
            continue
        rows.append(dict(zip(headers, cells, strict=True)))
    return headers, rows


def _parse_link_target(cell: str) -> str:
    return _host().backlog_contract._parse_link_target(cell) or ""  # noqa: SLF001


def _load_idea_specs(*, repo_root: Path) -> dict[str, backlog_contract.IdeaSpec]:
    host = _host()
    ideas_root = host._radar_source_root(repo_root=repo_root) / "ideas"  # noqa: SLF001
    if not ideas_root.is_dir():
        return {}
    specs: dict[str, backlog_contract.IdeaSpec] = {}
    for path in sorted(ideas_root.rglob("*.md")):
        spec = host.backlog_contract._parse_idea_spec(path)  # noqa: SLF001
        idea_id = str(spec.metadata.get("idea_id", "")).strip().upper()
        if host._WORKSTREAM_ID_RE.fullmatch(idea_id):  # noqa: SLF001
            specs[idea_id] = spec
    return specs


def _load_backlog_projection(*, repo_root: Path) -> dict[str, Any]:
    host = _host()
    index_path = host._radar_source_root(repo_root=repo_root) / "INDEX.md"  # noqa: SLF001
    if index_path.is_file():
        snapshot = host.backlog_contract.load_backlog_index_snapshot(index_path)
    else:
        snapshot = {
            "updated_utc": "",
            "active": {"rows": []},
            "execution": {"rows": []},
            "finished": {"rows": []},
            "parked": {"rows": []},
            "reorder_sections": {},
        }
    archive_dir = index_path.parent / "archive"
    finished_rows = list(
        host.backlog_contract.rows_as_mapping(section=snapshot.get("finished", {}), expected_headers=host._BACKLOG_HEADERS)  # noqa: SLF001
    )
    parked_rows = list(
        host.backlog_contract.rows_as_mapping(section=snapshot.get("parked", {}), expected_headers=host._BACKLOG_HEADERS)  # noqa: SLF001
    )
    for archive_path in _archive_files(archive_dir):
        archive_snapshot = host.backlog_contract.load_backlog_index_snapshot(archive_path)
        finished_rows.extend(
            host.backlog_contract.rows_as_mapping(section=archive_snapshot.get("finished", {}), expected_headers=host._BACKLOG_HEADERS)  # noqa: SLF001
        )
        parked_rows.extend(
            host.backlog_contract.rows_as_mapping(section=archive_snapshot.get("parked", {}), expected_headers=host._BACKLOG_HEADERS)  # noqa: SLF001
        )
    rationale_map: dict[str, list[str]] = {}
    for key, payload in (snapshot.get("reorder_sections", {}) or {}).items():
        lines = payload.get("lines", []) if isinstance(payload, Mapping) else []
        bullets = [str(line).strip()[2:].strip() for line in lines if str(line).strip().startswith("- ")]
        rationale_map[str(key)] = bullets
    return {
        "updated_utc": str(snapshot.get("updated_utc", "")).strip(),
        "active": host.backlog_contract.rows_as_mapping(section=snapshot.get("active", {}), expected_headers=host._BACKLOG_HEADERS),  # noqa: SLF001
        "execution": host.backlog_contract.rows_as_mapping(section=snapshot.get("execution", {}), expected_headers=host._BACKLOG_HEADERS),  # noqa: SLF001
        "finished": finished_rows,
        "parked": parked_rows,
        "rationale_map": rationale_map,
    }


def _load_plan_projection(*, repo_root: Path) -> dict[str, list[dict[str, str]]]:
    host = _host()
    index_path = host._technical_plans_root(repo_root=repo_root) / "INDEX.md"  # noqa: SLF001
    sections = _collect_markdown_sections(index_path)
    active_rows: list[dict[str, str]] = []
    parked_rows: list[dict[str, str]] = []
    done_rows: list[dict[str, str]] = []
    for title, lines in sections.items():
        headers, rows = _parse_markdown_table(lines)
        if tuple(headers) != host._PLAN_HEADERS:  # noqa: SLF001
            continue
        normalized = title.strip().lower()
        if normalized == "active plans":
            active_rows.extend(rows)
        elif normalized == "parked plans":
            parked_rows.extend(rows)
        else:
            done_rows.extend(rows)
    return {
        "active": active_rows,
        "parked": parked_rows,
        "done": done_rows,
    }


def _load_bug_projection(*, repo_root: Path) -> list[dict[str, str]]:
    host = _host()
    rows: list[dict[str, str]] = []
    casebook_bugs_root = host._casebook_bugs_root(repo_root=repo_root)  # noqa: SLF001
    candidates = [casebook_bugs_root / "INDEX.md", *(_archive_files(casebook_bugs_root / "archive"))]
    for path in candidates:
        sections = _collect_markdown_sections(path)
        matched = False
        for _title, lines in sections.items():
            headers, section_rows = _parse_markdown_table(lines)
            if tuple(headers) in {host._BUG_HEADERS, host._BUG_LEGACY_HEADERS}:  # noqa: SLF001
                rows.extend(_normalize_bug_projection_rows(repo_root=repo_root, index_path=path, rows=section_rows))
                matched = True
        if not matched and path.is_file():
            headers, section_rows = _parse_markdown_table(path.read_text(encoding="utf-8").splitlines())
            if tuple(headers) in {host._BUG_HEADERS, host._BUG_LEGACY_HEADERS}:  # noqa: SLF001
                rows.extend(_normalize_bug_projection_rows(repo_root=repo_root, index_path=path, rows=section_rows))
    return rows


def _normalize_bug_projection_rows(
    *,
    repo_root: Path,
    index_path: Path,
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    host = _host()
    normalized: list[dict[str, str]] = []
    index_path_token = index_path.relative_to(repo_root).as_posix()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if _is_bug_placeholder_row(row):
            continue
        payload = {str(key): str(value) for key, value in row.items()}
        payload["Status"] = host.canonicalize_bug_status(payload.get("Status", ""))
        link_target = _parse_link_target(str(payload.get("Link", "")))
        normalized_link = _normalize_bug_link_target(
            repo_root=repo_root,
            index_path=index_path,
            link_target=link_target,
        )
        if normalized_link and not (repo_root / normalized_link).is_file():
            continue
        bug_id_seed = normalized_link or f"{index_path_token}::{payload.get('Date', '')}::{payload.get('Title', '')}"
        explicit_bug_id = str(payload.get(BUG_ID_FIELD, "")).strip()
        markdown_bug_id = (
            load_casebook_bug_id_from_markdown(repo_root / normalized_link)
            if normalized_link
            else ""
        )
        payload[BUG_ID_FIELD] = resolve_casebook_bug_id(
            explicit_bug_id=explicit_bug_id or markdown_bug_id,
            seed=bug_id_seed,
        )
        if normalized_link:
            payload["Link"] = f"[bug]({normalized_link})"
        payload["IndexPath"] = index_path_token
        normalized.append(payload)
    return normalized


def _normalize_bug_link_target(*, repo_root: Path, index_path: Path, link_target: str) -> str:
    host = _host()
    token = str(link_target or "").strip()
    if not token:
        return ""
    candidate = Path(token)
    repo_root_resolved = repo_root.resolve()
    bug_root = host.truth_root_path(repo_root=repo_root_resolved, key="casebook_bugs")
    try:
        bug_root_token = bug_root.relative_to(repo_root_resolved).as_posix()
    except ValueError:
        bug_root_token = ""
    candidate_token = candidate.as_posix()
    if bug_root_token and (candidate_token == bug_root_token or candidate_token.startswith(f"{bug_root_token}/")):
        return candidate_token
    if candidate.is_absolute():
        resolved = candidate
    else:
        repo_relative_candidate = (repo_root_resolved / candidate).resolve()
        index_relative_candidate = (index_path.parent / candidate).resolve()
        if repo_relative_candidate.exists():
            resolved = repo_relative_candidate
        else:
            resolved = index_relative_candidate
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _is_bug_placeholder_row(row: Mapping[str, Any]) -> bool:
    host = _host()
    date = str(row.get("Date", "")).strip()
    title = str(row.get("Title", "")).strip()
    severity = str(row.get("Severity", "")).strip()
    status = str(row.get("Status", "")).strip()
    link_target = _parse_link_target(str(row.get("Link", "")))
    if date and not host._BUG_DATE_RE.fullmatch(date):  # noqa: SLF001
        return True
    for token in (title, severity, status, link_target):
        if "<" in token and ">" in token:
            return True
    return False


def _safe_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _raw_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_codex_event_projection(*, repo_root: Path) -> list[dict[str, Any]]:
    host = _host()
    stream_path = host._compass_stream_path(repo_root=repo_root)  # noqa: SLF001
    if not stream_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for idx, raw in enumerate(stream_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            continue
        kind = str(payload.get("kind", "")).strip().lower()
        if kind == "update":
            kind = "statement"
        summary = " ".join(str(payload.get("summary", "")).split()).strip()
        ts_iso = str(payload.get("ts_iso", "")).strip()
        if kind not in {"decision", "implementation", "statement"} or not summary or not ts_iso:
            continue
        workstreams = [
            str(token).strip().upper()
            for token in payload.get("workstreams", [])
            if host._WORKSTREAM_ID_RE.fullmatch(str(token).strip().upper())  # noqa: SLF001
        ] if isinstance(payload.get("workstreams"), list) else []
        artifacts = [
            host._normalize_repo_token(str(token).strip(), repo_root=repo_root)  # noqa: SLF001
            for token in payload.get("artifacts", [])
            if host._normalize_repo_token(str(token).strip(), repo_root=repo_root)  # noqa: SLF001
        ] if isinstance(payload.get("artifacts"), list) else []
        components = [
            str(token).strip()
            for token in payload.get("components", [])
            if str(token).strip()
        ] if isinstance(payload.get("components"), list) else []
        rows.append(
            {
                "event_id": f"codex:{kind}:{idx}:{ts_iso}",
                "ts_iso": ts_iso,
                "kind": kind,
                "summary": summary,
                "workstreams": sorted(set(workstreams)),
                "artifacts": sorted(set(artifacts)),
                "components": sorted(set(components)),
                "metadata": {
                    "author": str(payload.get("author", "")).strip(),
                    "source": str(payload.get("source", "")).strip(),
                    "transaction_id": str(payload.get("transaction_id", "")).strip(),
                    "session_id": str(payload.get("session_id", "")).strip(),
                },
            }
        )
    return rows


def _load_traceability_projection(*, repo_root: Path) -> list[dict[str, str]]:
    host = _host()
    path = host._traceability_graph_path(repo_root=repo_root)  # noqa: SLF001
    payload = host.odylith_context_cache.read_json_object(path)
    rows: list[dict[str, str]] = []
    workstreams = payload.get("workstreams", []) if isinstance(payload.get("workstreams"), list) else []
    for workstream in workstreams:
        if not isinstance(workstream, Mapping):
            continue
        idea_id = str(workstream.get("idea_id", "")).strip().upper()
        if not host._WORKSTREAM_ID_RE.fullmatch(idea_id):  # noqa: SLF001
            continue
        plan_path = str(workstream.get("promoted_to_plan", "")).strip()
        if plan_path:
            rows.append(
                {
                    "source_kind": "workstream",
                    "source_id": idea_id,
                    "relation": "promoted_to_plan",
                    "target_kind": "plan",
                    "target_id": plan_path,
                    "source_path": str(workstream.get("idea_file", "")).strip(),
                }
            )
        for relation in (
            "workstream_parent",
            "workstream_reopens",
            "workstream_reopened_by",
            "workstream_split_from",
            "workstream_merged_into",
        ):
            token = str(workstream.get(relation, "")).strip().upper()
            if host._WORKSTREAM_ID_RE.fullmatch(token):  # noqa: SLF001
                rows.append(
                    {
                        "source_kind": "workstream",
                        "source_id": idea_id,
                        "relation": relation,
                        "target_kind": "workstream",
                        "target_id": token,
                        "source_path": str(workstream.get("idea_file", "")).strip(),
                    }
                )
        for relation in (
            "workstream_children",
            "workstream_depends_on",
            "workstream_blocks",
            "workstream_split_into",
            "workstream_merged_from",
            "related_diagram_ids",
        ):
            values = workstream.get(relation, [])
            if isinstance(values, str):
                values = [token.strip() for token in values.replace(";", ",").split(",") if token.strip()]
            if not isinstance(values, list):
                continue
            for raw in values:
                token = str(raw).strip()
                if relation == "related_diagram_ids":
                    if not host._DIAGRAM_ID_RE.fullmatch(token):  # noqa: SLF001
                        continue
                    target_kind = "diagram"
                else:
                    token = token.upper()
                    if not host._WORKSTREAM_ID_RE.fullmatch(token):  # noqa: SLF001
                        continue
                    target_kind = "workstream"
                rows.append(
                    {
                        "source_kind": "workstream",
                        "source_id": idea_id,
                        "relation": relation,
                        "target_kind": target_kind,
                        "target_id": token,
                        "source_path": str(workstream.get("idea_file", "")).strip(),
                    }
                )
        traceability = workstream.get("plan_traceability", {})
        if isinstance(traceability, Mapping):
            for bucket, target_kind in (
                ("runbooks", "runbook"),
                ("developer_docs", "doc"),
                ("code_references", "code"),
            ):
                values = traceability.get(bucket, [])
                if not isinstance(values, list):
                    continue
                for raw in values:
                    token = str(raw).strip()
                    if not token:
                        continue
                    rows.append(
                        {
                            "source_kind": "workstream",
                            "source_id": idea_id,
                            "relation": bucket,
                            "target_kind": target_kind,
                            "target_id": token,
                            "source_path": str(workstream.get("idea_file", "")).strip(),
                        }
                    )
    return rows


def _load_diagram_projection(*, repo_root: Path) -> list[dict[str, Any]]:
    host = _host()
    path = host._atlas_catalog_path(repo_root=repo_root)  # noqa: SLF001
    payload = host.odylith_context_cache.read_json_object(path)
    diagrams = payload.get("diagrams", [])
    rows: list[dict[str, Any]] = []
    if not isinstance(diagrams, list):
        return rows
    for item in diagrams:
        if not isinstance(item, Mapping):
            continue
        diagram_id = str(item.get("diagram_id", "")).strip().upper()
        if not host._DIAGRAM_ID_RE.fullmatch(diagram_id):  # noqa: SLF001
            continue
        source_mmd = str(item.get("source_mmd", "")).strip()
        source_mmd_path = repo_root / source_mmd if source_mmd and not Path(source_mmd).is_absolute() else Path(source_mmd)
        rows.append(
            {
                "diagram_id": diagram_id,
                "slug": str(item.get("slug", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "status": str(item.get("status", "")).strip(),
                "owner": str(item.get("owner", "")).strip(),
                "last_reviewed_utc": str(item.get("last_reviewed_utc", "")).strip(),
                "source_mmd": source_mmd,
                "source_svg": str(item.get("source_svg", "")).strip(),
                "source_png": str(item.get("source_png", "")).strip(),
                "source_mmd_hash": host.odylith_context_cache.fingerprint_paths([source_mmd_path.resolve()]) if source_mmd_path.is_file() else "",
                "summary": str(item.get("summary", "")).strip(),
                "watch_paths": [
                    str(token).strip()
                    for token in item.get("change_watch_paths", [])
                    if str(token).strip()
                ] if isinstance(item.get("change_watch_paths"), list) else [],
                "metadata": dict(item),
            }
        )
    return rows

"""Projection source loaders extracted from the context engine store."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.casebook_bug_ids import BUG_ID_FIELD, load_casebook_bug_id_from_markdown, resolve_casebook_bug_id


def _archive_files(root: Path) -> list[Path]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    if not root.is_dir():
        return []
    return sorted(
        path for path in root.glob(odylith_context_engine_store._ARCHIVE_GLOB) if path.is_file()  # noqa: SLF001
    )


def _collect_markdown_sections(path: Path) -> dict[str, list[str]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    if not path.is_file():
        return {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = odylith_context_engine_store._HEADER_RE.match(raw)  # noqa: SLF001
        if match:
            current = str(match.group(1)).strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(raw)
    return sections


def _parse_markdown_table(lines: Sequence[str]) -> tuple[list[str], list[dict[str, str]]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

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
        if not odylith_context_engine_store._TABLE_ROW_RE.match(line):  # noqa: SLF001
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
        if all(re.fullmatch(r"-+", token or "") for token in cells):
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
    from odylith.runtime.context_engine import odylith_context_engine_store

    return odylith_context_engine_store.backlog_contract._parse_link_target(cell) or ""  # noqa: SLF001


def _load_idea_specs(*, repo_root: Path) -> dict[str, backlog_contract.IdeaSpec]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    ideas_root = odylith_context_engine_store._radar_source_root(repo_root=repo_root) / "ideas"  # noqa: SLF001
    if not ideas_root.is_dir():
        return {}
    specs: dict[str, backlog_contract.IdeaSpec] = {}
    for path in sorted(ideas_root.rglob("*.md")):
        spec = odylith_context_engine_store.backlog_contract._parse_idea_spec(path)  # noqa: SLF001
        idea_id = str(spec.metadata.get("idea_id", "")).strip().upper()
        if odylith_context_engine_store._WORKSTREAM_ID_RE.fullmatch(idea_id):  # noqa: SLF001
            specs[idea_id] = spec
    return specs


def _load_backlog_projection(*, repo_root: Path) -> dict[str, Any]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    index_path = odylith_context_engine_store._radar_source_root(repo_root=repo_root) / "INDEX.md"  # noqa: SLF001
    if index_path.is_file():
        snapshot = odylith_context_engine_store.backlog_contract.load_backlog_index_snapshot(index_path)
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
        odylith_context_engine_store.backlog_contract.rows_as_mapping(  # noqa: SLF001
            section=snapshot.get("finished", {}),
            expected_headers=odylith_context_engine_store._BACKLOG_HEADERS,
        )
    )
    parked_rows = list(
        odylith_context_engine_store.backlog_contract.rows_as_mapping(  # noqa: SLF001
            section=snapshot.get("parked", {}),
            expected_headers=odylith_context_engine_store._BACKLOG_HEADERS,
        )
    )
    for archive_path in _archive_files(archive_dir):
        archive_snapshot = odylith_context_engine_store.backlog_contract.load_backlog_index_snapshot(archive_path)
        finished_rows.extend(
            odylith_context_engine_store.backlog_contract.rows_as_mapping(  # noqa: SLF001
                section=archive_snapshot.get("finished", {}),
                expected_headers=odylith_context_engine_store._BACKLOG_HEADERS,
            )
        )
        parked_rows.extend(
            odylith_context_engine_store.backlog_contract.rows_as_mapping(  # noqa: SLF001
                section=archive_snapshot.get("parked", {}),
                expected_headers=odylith_context_engine_store._BACKLOG_HEADERS,
            )
        )
    rationale_map: dict[str, list[str]] = {}
    for key, payload in (snapshot.get("reorder_sections", {}) or {}).items():
        lines = payload.get("lines", []) if isinstance(payload, Mapping) else []
        bullets = [str(line).strip()[2:].strip() for line in lines if str(line).strip().startswith("- ")]
        rationale_map[str(key)] = bullets
    return {
        "updated_utc": str(snapshot.get("updated_utc", "")).strip(),
        "active": odylith_context_engine_store.backlog_contract.rows_as_mapping(  # noqa: SLF001
            section=snapshot.get("active", {}),
            expected_headers=odylith_context_engine_store._BACKLOG_HEADERS,
        ),
        "execution": odylith_context_engine_store.backlog_contract.rows_as_mapping(  # noqa: SLF001
            section=snapshot.get("execution", {}),
            expected_headers=odylith_context_engine_store._BACKLOG_HEADERS,
        ),
        "finished": finished_rows,
        "parked": parked_rows,
        "rationale_map": rationale_map,
    }


def _load_plan_projection(*, repo_root: Path) -> dict[str, list[dict[str, str]]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    index_path = odylith_context_engine_store._technical_plans_root(repo_root=repo_root) / "INDEX.md"  # noqa: SLF001
    sections = _collect_markdown_sections(index_path)
    active_rows: list[dict[str, str]] = []
    parked_rows: list[dict[str, str]] = []
    done_rows: list[dict[str, str]] = []
    for title, lines in sections.items():
        headers, rows = _parse_markdown_table(lines)
        if tuple(headers) != odylith_context_engine_store._PLAN_HEADERS:  # noqa: SLF001
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
    from odylith.runtime.context_engine import odylith_context_engine_store

    rows: list[dict[str, str]] = []
    casebook_bugs_root = odylith_context_engine_store._casebook_bugs_root(repo_root=repo_root)  # noqa: SLF001
    candidates = [casebook_bugs_root / "INDEX.md", *(_archive_files(casebook_bugs_root / "archive"))]
    for path in candidates:
        sections = _collect_markdown_sections(path)
        matched = False
        for _title, lines in sections.items():
            headers, section_rows = _parse_markdown_table(lines)
            if tuple(headers) in {
                odylith_context_engine_store._BUG_HEADERS,
                odylith_context_engine_store._BUG_LEGACY_HEADERS,
            }:  # noqa: SLF001
                rows.extend(_normalize_bug_projection_rows(repo_root=repo_root, index_path=path, rows=section_rows))
                matched = True
        if not matched and path.is_file():
            headers, section_rows = _parse_markdown_table(path.read_text(encoding="utf-8").splitlines())
            if tuple(headers) in {
                odylith_context_engine_store._BUG_HEADERS,
                odylith_context_engine_store._BUG_LEGACY_HEADERS,
            }:  # noqa: SLF001
                rows.extend(_normalize_bug_projection_rows(repo_root=repo_root, index_path=path, rows=section_rows))
    return rows


def _normalize_bug_projection_rows(
    *,
    repo_root: Path,
    index_path: Path,
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    normalized: list[dict[str, str]] = []
    index_path_token = index_path.relative_to(repo_root).as_posix()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if _is_bug_placeholder_row(row):
            continue
        payload = {str(key): str(value) for key, value in row.items()}
        payload["Status"] = odylith_context_engine_store.canonicalize_bug_status(payload.get("Status", ""))
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
    from odylith.runtime.context_engine import odylith_context_engine_store

    token = str(link_target or "").strip()
    if not token:
        return ""
    candidate = Path(token)
    repo_root_resolved = repo_root.resolve()
    bug_root = odylith_context_engine_store.truth_root_path(repo_root=repo_root_resolved, key="casebook_bugs")
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
    from odylith.runtime.context_engine import odylith_context_engine_store

    date = str(row.get("Date", "")).strip()
    title = str(row.get("Title", "")).strip()
    severity = str(row.get("Severity", "")).strip()
    status = str(row.get("Status", "")).strip()
    link_target = _parse_link_target(str(row.get("Link", "")))
    if date and not odylith_context_engine_store._BUG_DATE_RE.fullmatch(date):  # noqa: SLF001
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
    from odylith.runtime.context_engine import odylith_context_engine_store

    stream_path = odylith_context_engine_store._compass_stream_path(repo_root=repo_root)  # noqa: SLF001
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
            if odylith_context_engine_store._WORKSTREAM_ID_RE.fullmatch(str(token).strip().upper())  # noqa: SLF001
        ] if isinstance(payload.get("workstreams"), list) else []
        artifacts = [
            odylith_context_engine_store._normalize_repo_token(str(token).strip(), repo_root=repo_root)  # noqa: SLF001
            for token in payload.get("artifacts", [])
            if odylith_context_engine_store._normalize_repo_token(str(token).strip(), repo_root=repo_root)  # noqa: SLF001
        ] if isinstance(payload.get("artifacts"), list) else []
        components = [
            str(token).strip()
            for token in payload.get("components", [])
            if str(token).strip()
        ] if isinstance(payload.get("components"), list) else []
        rows.append(
            {
                "event_id": agent_runtime_contract.timeline_event_id(
                    kind=kind,
                    index=idx,
                    ts_iso=ts_iso,
                ),
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
    from odylith.runtime.context_engine import odylith_context_engine_store

    path = odylith_context_engine_store._traceability_graph_path(repo_root=repo_root)  # noqa: SLF001
    payload = odylith_context_engine_store.odylith_context_cache.read_json_object(path)
    rows: list[dict[str, str]] = []
    workstreams = payload.get("workstreams", []) if isinstance(payload.get("workstreams"), list) else []
    for workstream in workstreams:
        if not isinstance(workstream, Mapping):
            continue
        idea_id = str(workstream.get("idea_id", "")).strip().upper()
        if not odylith_context_engine_store._WORKSTREAM_ID_RE.fullmatch(idea_id):  # noqa: SLF001
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
            if odylith_context_engine_store._WORKSTREAM_ID_RE.fullmatch(token):  # noqa: SLF001
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
                    if not odylith_context_engine_store._DIAGRAM_ID_RE.fullmatch(token):  # noqa: SLF001
                        continue
                    target_kind = "diagram"
                else:
                    token = token.upper()
                    if not odylith_context_engine_store._WORKSTREAM_ID_RE.fullmatch(token):  # noqa: SLF001
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
        active_release_id = str(workstream.get("active_release_id", "")).strip()
        if active_release_id:
            rows.append(
                {
                    "source_kind": "workstream",
                    "source_id": idea_id,
                    "relation": "active_release",
                    "target_kind": "release",
                    "target_id": active_release_id,
                    "source_path": str(workstream.get("idea_file", "")).strip(),
                }
            )
    return rows


def _load_release_projection(*, repo_root: Path) -> dict[str, Any]:
    from odylith.runtime.context_engine import odylith_context_engine_store
    from odylith.runtime.governance import release_truth_runtime

    release_view, workstream_status_by_id, _errors = release_truth_runtime.load_release_view_from_source(
        repo_root=repo_root,
    )
    releases = release_view.get("catalog", []) if isinstance(release_view.get("catalog"), list) else []
    aliases = release_view.get("aliases", {}) if isinstance(release_view.get("aliases"), Mapping) else {}
    workstreams = []
    for idea_id, status in workstream_status_by_id.items():
        release_metadata = (
            dict(release_view.get("workstreams", {}).get(idea_id, {}))
            if isinstance(release_view.get("workstreams"), Mapping)
            and isinstance(release_view.get("workstreams", {}).get(idea_id), Mapping)
            else {}
        )
        workstreams.append(
            {
                "idea_id": idea_id,
                "status": status,
                "active_release_id": str(release_metadata.get("active_release_id", "")).strip(),
                "active_release": (
                    dict(release_metadata.get("active_release", {}))
                    if isinstance(release_metadata.get("active_release"), Mapping)
                    else {}
                ),
                "release_history_summary": str(release_metadata.get("history_summary", "")).strip(),
            }
        )
    current_release = (
        release_view.get("current_release", {})
        if isinstance(release_view.get("current_release"), Mapping)
        else {}
    )
    next_release = (
        release_view.get("next_release", {})
        if isinstance(release_view.get("next_release"), Mapping)
        else {}
    )
    summary = (
        release_view.get("summary", {})
        if isinstance(release_view.get("summary"), Mapping)
        else {}
    )

    workstream_lookup: dict[str, dict[str, Any]] = {}
    for workstream in workstreams:
        if not isinstance(workstream, Mapping):
            continue
        idea_id = str(workstream.get("idea_id", "")).strip().upper()
        if not odylith_context_engine_store._WORKSTREAM_ID_RE.fullmatch(idea_id):  # noqa: SLF001
            continue
        active_release = workstream.get("active_release", {})
        active_release_aliases = (
            [
                str(item).strip()
                for item in active_release.get("aliases", [])
                if str(item).strip()
            ]
            if isinstance(active_release, Mapping) and isinstance(active_release.get("aliases"), list)
            else []
        )
        workstream_lookup[idea_id] = {
            "active_release_id": str(workstream.get("active_release_id", "")).strip(),
            "active_release": dict(active_release) if isinstance(active_release, Mapping) else {},
            "active_release_aliases": active_release_aliases,
            "release_history_summary": str(workstream.get("release_history_summary", "")).strip(),
        }

    rows: list[dict[str, Any]] = []
    for release in releases:
        if not isinstance(release, Mapping):
            continue
        release_id = str(release.get("release_id", "")).strip()
        if not release_id:
            continue
        active_workstreams = [
            str(item).strip().upper()
            for item in release.get("active_workstreams", [])
            if str(item).strip()
        ] if isinstance(release.get("active_workstreams"), list) else []
        aliases_for_release = [
            str(item).strip()
            for item in release.get("aliases", [])
            if str(item).strip()
        ] if isinstance(release.get("aliases"), list) else []
        metadata = dict(release)
        metadata["active_workstreams"] = active_workstreams
        metadata["aliases"] = aliases_for_release
        metadata["current_alias"] = "current" in aliases_for_release
        metadata["next_alias"] = "next" in aliases_for_release
        rows.append(
            {
                "release_id": release_id,
                "status": str(release.get("status", "")).strip(),
                "version": str(release.get("version", "")).strip(),
                "tag": str(release.get("tag", "")).strip(),
                "effective_name": str(release.get("effective_name", "")).strip(),
                "display_label": str(release.get("display_label", "")).strip() or release_id,
                "aliases_json": json.dumps(aliases_for_release, sort_keys=True),
                "active_workstreams_json": json.dumps(active_workstreams, sort_keys=True),
                "source_path": str(release.get("source_path", "")).strip() or "odylith/radar/source/releases/releases.v1.json",
                "metadata_json": json.dumps(metadata, sort_keys=True),
                "search_body": "\n".join(
                    token
                    for token in (
                        release_id,
                        str(release.get("version", "")).strip(),
                        str(release.get("tag", "")).strip(),
                        str(release.get("effective_name", "")).strip(),
                        str(release.get("notes", "")).strip(),
                        " ".join(aliases_for_release),
                        " ".join(active_workstreams),
                    )
                    if token
                ),
            }
        )
    return {
        "releases": rows,
        "aliases": dict(aliases),
        "workstreams": workstream_lookup,
        "current_release": dict(current_release),
        "next_release": dict(next_release),
        "summary": dict(summary),
    }


def _load_diagram_projection(*, repo_root: Path) -> list[dict[str, Any]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    path = odylith_context_engine_store._atlas_catalog_path(repo_root=repo_root)  # noqa: SLF001
    payload = odylith_context_engine_store.odylith_context_cache.read_json_object(path)
    diagrams = payload.get("diagrams", [])
    rows: list[dict[str, Any]] = []
    if not isinstance(diagrams, list):
        return rows
    for item in diagrams:
        if not isinstance(item, Mapping):
            continue
        diagram_id = str(item.get("diagram_id", "")).strip().upper()
        if not odylith_context_engine_store._DIAGRAM_ID_RE.fullmatch(diagram_id):  # noqa: SLF001
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
                "source_mmd_hash": (
                    odylith_context_engine_store.odylith_context_cache.fingerprint_paths([source_mmd_path.resolve()])  # noqa: SLF001
                    if source_mmd_path.is_file()
                    else ""
                ),
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

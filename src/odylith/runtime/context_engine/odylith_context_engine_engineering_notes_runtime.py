"""Engineering-note loaders extracted from the context engine store."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence


def _host():
    from odylith.runtime.context_engine import odylith_context_engine_store as host

    return host


def _load_adr_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    host = _host()
    path = repo_root / "agents-guidelines" / "DECISIONS.MD"
    rows: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for section, lines in host._collect_markdown_sections(path).items():  # noqa: SLF001
        heading = str(section).strip()
        if not heading.startswith("ADR-"):
            continue
        base_note_id = heading.split()[0]
        seen[base_note_id] = seen.get(base_note_id, 0) + 1
        note_id = base_note_id if seen[base_note_id] == 1 else f"{base_note_id}:{seen[base_note_id]}"
        fields = host._parse_markdown_fields(lines)  # noqa: SLF001
        summary = " ".join(
            token
            for token in (
                fields.get("Decision", ""),
                fields.get("Rationale", ""),
                fields.get("Consequences", ""),
            )
            if token
        ).strip()
        raw_text = "\n".join(lines)
        path_refs = host._extract_path_refs(text=raw_text, repo_root=repo_root)  # noqa: SLF001
        rows.append(
            {
                "note_id": note_id,
                "note_kind": "decision",
                "title": heading,
                "status": fields.get("Status", ""),
                "owner": "",
                "source_path": "agents-guidelines/DECISIONS.MD",
                "section": heading,
                "summary": summary or host._first_summary(lines),  # noqa: SLF001
                "tags": ["adr", "architecture", "decision"],
                "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                "workstreams": host._extract_workstream_refs(raw_text),  # noqa: SLF001
                "path_refs": path_refs,
                "metadata": {"references": path_refs},
            }
        )
    return rows


def _load_invariant_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    host = _host()
    path = repo_root / "agents-guidelines" / "INVARIANTS.MD"
    rows: list[dict[str, Any]] = []
    for section, lines in host._collect_markdown_sections(path).items():  # noqa: SLF001
        heading = str(section).strip()
        if heading.lower() == "source of truth":
            continue
        for index, raw in enumerate(lines, start=1):
            line = str(raw).strip()
            if not line.startswith("- "):
                continue
            body = line[2:].strip()
            path_refs = host._extract_path_refs(text=body, repo_root=repo_root)  # noqa: SLF001
            rows.append(
                {
                    "note_id": f"invariant:{heading.lower().replace(' ', '-')}:{index}",
                    "note_kind": "invariant",
                    "title": host._note_title(heading, body),  # noqa: SLF001
                    "status": "active",
                    "owner": "",
                    "source_path": "agents-guidelines/INVARIANTS.MD",
                    "section": heading,
                    "summary": body,
                    "tags": ["invariant", heading.lower()],
                    "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                    "workstreams": host._extract_workstream_refs(body),  # noqa: SLF001
                    "path_refs": path_refs,
                    "metadata": {},
                }
            )
    return rows


def _load_data_ownership_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    host = _host()
    path = repo_root / "agents-guidelines" / "DATA_OWNERSHIP.MD"
    rows: list[dict[str, Any]] = []
    sections = host._collect_markdown_sections(path)  # noqa: SLF001
    for section, lines in sections.items():
        heading = str(section).strip()
        headers, table_rows = host._parse_markdown_table(lines)  # noqa: SLF001
        if tuple(headers) == ("Area", "Owner", "Notes"):
            for row in table_rows:
                body = " ".join(str(row.get(key, "")).strip() for key in headers).strip()
                path_refs = host._extract_path_refs(text=body, repo_root=repo_root)  # noqa: SLF001
                rows.append(
                    {
                        "note_id": f"ownership:{str(row.get('Area', '')).strip().lower().replace(' ', '-')}",
                        "note_kind": "ownership",
                        "title": str(row.get("Area", "")).strip(),
                        "status": "active",
                        "owner": str(row.get("Owner", "")).strip(),
                        "source_path": "agents-guidelines/DATA_OWNERSHIP.MD",
                        "section": heading,
                        "summary": str(row.get("Notes", "")).strip(),
                        "tags": ["ownership"],
                        "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                        "workstreams": host._extract_workstream_refs(body),  # noqa: SLF001
                        "path_refs": path_refs,
                        "metadata": {"area": str(row.get("Area", "")).strip()},
                    }
                )
            continue
        for index, raw in enumerate(lines, start=1):
            line = str(raw).strip()
            if not line.startswith("- "):
                continue
            body = line[2:].strip()
            path_refs = host._extract_path_refs(text=body, repo_root=repo_root)  # noqa: SLF001
            rows.append(
                {
                    "note_id": f"ownership:{heading.lower().replace(' ', '-')}:bullet:{index}",
                    "note_kind": "ownership",
                    "title": host._note_title(heading, body),  # noqa: SLF001
                    "status": "active",
                    "owner": "",
                    "source_path": "agents-guidelines/DATA_OWNERSHIP.MD",
                    "section": heading,
                    "summary": body,
                    "tags": ["ownership", heading.lower()],
                    "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                    "workstreams": host._extract_workstream_refs(body),  # noqa: SLF001
                    "path_refs": path_refs,
                    "metadata": {},
                }
            )
    return rows


def _load_section_bullet_notes(
    *,
    repo_root: Path,
    rel_path: str,
    note_kind: str,
    component_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    host = _host()
    path = repo_root / rel_path
    rows: list[dict[str, Any]] = []
    for section, lines in host._collect_markdown_sections(path).items():  # noqa: SLF001
        heading = str(section).strip()
        bullet_index = 0
        for raw in lines:
            line = str(raw).strip()
            if not line.startswith("- "):
                continue
            bullet_index += 1
            body = line[2:].strip()
            path_refs = host._extract_path_refs(text=body, repo_root=repo_root)  # noqa: SLF001
            rows.append(
                {
                    "note_id": f"{note_kind}:{heading.lower().replace(' ', '-')}:{bullet_index}",
                    "note_kind": note_kind,
                    "title": host._note_title(heading, body),  # noqa: SLF001
                    "status": "active",
                    "owner": "",
                    "source_path": rel_path,
                    "section": heading,
                    "summary": body,
                    "tags": [note_kind, heading.lower()],
                    "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                    "workstreams": host._extract_workstream_refs(body),  # noqa: SLF001
                    "path_refs": path_refs,
                    "metadata": {},
                }
            )
        if bullet_index:
            continue
        summary = host._first_summary(lines)  # noqa: SLF001
        if not summary:
            continue
        path_refs = host._extract_path_refs(text="\n".join(lines), repo_root=repo_root)  # noqa: SLF001
        rows.append(
            {
                "note_id": f"{note_kind}:{heading.lower().replace(' ', '-')}",
                "note_kind": note_kind,
                "title": heading,
                "status": "active",
                "owner": "",
                "source_path": rel_path,
                "section": heading,
                "summary": summary,
                "tags": [note_kind, heading.lower()],
                "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                "workstreams": host._extract_workstream_refs("\n".join(lines)),  # noqa: SLF001
                "path_refs": path_refs,
                "metadata": {},
            }
        )
    return rows


def _markdown_title(*, lines: Sequence[str], fallback: str) -> str:
    for raw in lines:
        line = str(raw).strip()
        if line.startswith("# "):
            return line[2:].strip()
    return str(fallback).strip()


def _load_guidance_chunk_notes(
    *,
    repo_root: Path,
    component_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    host = _host()
    catalog = host.tooling_guidance_catalog.load_guidance_catalog(repo_root=repo_root)  # noqa: SLF001
    chunks = catalog.get("chunks", [])
    if not isinstance(chunks, list):
        return [], set()
    rows: list[dict[str, Any]] = []
    chunked_sources: set[str] = set()
    for item in chunks:
        if not isinstance(item, Mapping):
            continue
        chunk_id = str(item.get("chunk_id", "")).strip()
        note_kind = str(item.get("note_kind", "")).strip()
        canonical_source = host._normalize_repo_token(str(item.get("canonical_source", "")).strip(), repo_root=repo_root)  # noqa: SLF001
        chunk_path = host._normalize_repo_token(str(item.get("chunk_path", "")).strip(), repo_root=repo_root)  # noqa: SLF001
        if (
            not chunk_id
            or note_kind not in host._ENGINEERING_NOTE_KIND_SET  # noqa: SLF001
            or not canonical_source
            or not chunk_path
        ):
            continue
        path = repo_root / chunk_path
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        raw_text = "\n".join(lines)
        title = str(item.get("title", "")).strip() or _markdown_title(lines=lines, fallback=Path(chunk_path).stem)
        section = str(item.get("section", "")).strip() or title
        summary = str(item.get("summary", "")).strip() or host._first_summary(lines)  # noqa: SLF001
        if not summary:
            continue
        manifest_paths = [
            host._normalize_repo_token(token, repo_root=repo_root)  # noqa: SLF001
            for token in host._string_list(item.get("path_refs"))  # noqa: SLF001
            if host._normalize_repo_token(token, repo_root=repo_root)  # noqa: SLF001
        ]
        path_prefixes = [
            host._normalize_repo_token(token, repo_root=repo_root)  # noqa: SLF001
            for token in host._string_list(item.get("path_prefixes"))  # noqa: SLF001
            if host._normalize_repo_token(token, repo_root=repo_root)  # noqa: SLF001
        ]
        path_refs = host._dedupe_strings([*manifest_paths, *path_prefixes, *host._extract_path_refs(text=raw_text, repo_root=repo_root)])  # noqa: SLF001
        workstreams = host._dedupe_strings(  # noqa: SLF001
            [
                *[
                    token.upper()
                    for token in host._string_list(item.get("workstreams"))  # noqa: SLF001
                    if host._WORKSTREAM_ID_RE.fullmatch(token.upper())  # noqa: SLF001
                ],
                *host._extract_workstream_refs(raw_text),  # noqa: SLF001
            ]
        )
        task_families = host._dedupe_strings(host._string_list(item.get("task_families")))  # noqa: SLF001
        component_affinity = host._dedupe_strings(  # noqa: SLF001
            [
                *host._string_list(item.get("component_affinity")),  # noqa: SLF001
                *host._string_list(item.get("components")),  # noqa: SLF001
            ]
        )
        risk_class = str(item.get("risk_class", "")).strip()
        components = host._dedupe_strings(  # noqa: SLF001
            [
                *component_affinity,
                *host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
            ]
        )
        tags = host._dedupe_strings(  # noqa: SLF001
            [
                note_kind,
                "guidance_chunk",
                *task_families,
                *([risk_class] if risk_class else []),
                *host._string_list(item.get("tags")),  # noqa: SLF001
            ]
        )
        rows.append(
            {
                "note_id": f"{note_kind}:chunk:{chunk_id}",
                "note_kind": note_kind,
                "title": title,
                "status": str(item.get("status", "")).strip() or "active",
                "owner": str(item.get("owner", "")).strip(),
                "source_path": canonical_source,
                "section": section,
                "summary": summary,
                "tags": tags,
                "components": components,
                "workstreams": workstreams,
                "path_refs": path_refs,
                "metadata": {
                    "source_mode": "guidance_chunk",
                    "chunk_id": chunk_id,
                    "chunk_path": chunk_path,
                    "canonical_source": canonical_source,
                    "canonical_section": section,
                    "manifest_path": host.tooling_guidance_catalog.MANIFEST_PATH,  # noqa: SLF001
                    "task_families": task_families,
                    "path_prefixes": path_prefixes,
                    "risk_class": risk_class,
                    "component_affinity": component_affinity,
                },
            }
        )
        chunked_sources.add(canonical_source)
    return rows, chunked_sources


def _load_runbook_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    host = _host()
    rows: list[dict[str, Any]] = []
    runbooks_root = repo_root / "docs" / "runbooks"
    if not runbooks_root.is_dir():
        return rows
    for path in sorted(runbooks_root.rglob("*.md")):
        rel_path = path.relative_to(repo_root).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        title = ""
        for raw in lines:
            line = str(raw).strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break
        summary = host._first_summary(lines)  # noqa: SLF001
        path_refs = host._extract_path_refs(text="\n".join(lines), repo_root=repo_root)  # noqa: SLF001
        rows.append(
            {
                "note_id": f"runbook:{rel_path}",
                "note_kind": "runbook",
                "title": title or Path(rel_path).stem,
                "status": "active",
                "owner": "",
                "source_path": rel_path,
                "section": "",
                "summary": summary,
                "tags": ["runbook"],
                "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                "workstreams": host._extract_workstream_refs("\n".join(lines)),  # noqa: SLF001
                "path_refs": sorted(set([rel_path, *path_refs])),
                "metadata": {},
            }
        )
    return rows


def _load_schema_contract_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    host = _host()
    rows: list[dict[str, Any]] = []
    contracts_root = repo_root / "contracts"
    if not contracts_root.is_dir():
        return rows
    for path in sorted(contracts_root.rglob("*.json")):
        rel_path = path.relative_to(repo_root).as_posix()
        payload = host.odylith_context_cache.read_json_object(path)  # noqa: SLF001
        if not payload:
            continue
        title = str(payload.get("title", "")).strip() or path.stem
        summary = str(payload.get("description", "")).strip()
        path_refs = [rel_path]
        rows.append(
            {
                "note_id": f"schema:{rel_path}",
                "note_kind": "schema_contract",
                "title": title,
                "status": "active",
                "owner": "",
                "source_path": rel_path,
                "section": "",
                "summary": summary,
                "tags": ["schema", "contract"],
                "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                "workstreams": host._extract_workstream_refs(summary),  # noqa: SLF001
                "path_refs": path_refs,
                "metadata": {"schema_id": str(payload.get("$id", "")).strip()},
            }
        )
    return rows


def _load_make_target_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    host = _host()
    rows: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    candidates = [repo_root / "Makefile"]
    mk_root = repo_root / "mk"
    if mk_root.is_dir():
        candidates.extend(sorted(mk_root.rglob("*.mk")))
    for path in candidates:
        if not path.is_file():
            continue
        rel_path = path.relative_to(repo_root).as_posix()
        previous_comment = ""
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = str(raw).rstrip()
            stripped = line.strip()
            if not stripped:
                previous_comment = ""
                continue
            if stripped.startswith("#"):
                previous_comment = stripped.lstrip("#").strip()
                continue
            match = host._MAKE_TARGET_RE.match(line)  # noqa: SLF001
            if match is None:
                continue
            target = str(match.group(1)).strip()
            if target.startswith(".") or "%" in target or "/" in target:
                continue
            body = previous_comment or f"Make target `{target}` declared in `{rel_path}`."
            path_refs = sorted(set([rel_path, *host._extract_path_refs(text=body, repo_root=repo_root)]))  # noqa: SLF001
            base_note_id = f"make:{rel_path}:{target}"
            seen[base_note_id] = seen.get(base_note_id, 0) + 1
            note_id = base_note_id if seen[base_note_id] == 1 else f"{base_note_id}:{seen[base_note_id]}"
            rows.append(
                {
                    "note_id": note_id,
                    "note_kind": "make_target",
                    "title": target,
                    "status": "active",
                    "owner": "",
                    "source_path": rel_path,
                    "section": "",
                    "summary": body,
                    "tags": ["make", "target"],
                    "components": host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                    "workstreams": host._extract_workstream_refs(body),  # noqa: SLF001
                    "path_refs": path_refs,
                    "metadata": {},
                }
            )
            previous_comment = ""
    return rows


def _load_bug_learning_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    host = _host()
    rows: list[dict[str, Any]] = []
    for row in host._load_bug_projection(repo_root=repo_root):  # noqa: SLF001
        if not isinstance(row, Mapping):
            continue
        link_target = host._parse_link_target(str(row.get("Link", "")))  # noqa: SLF001
        if not link_target:
            continue
        bug_path = repo_root / link_target
        if not bug_path.is_file():
            continue
        lines = bug_path.read_text(encoding="utf-8").splitlines()
        fields = host._parse_bug_entry_fields(lines)  # noqa: SLF001
        summary = " ".join(
            token
            for token in (
                str(fields.get("Root Cause", "")).strip(),
                str(fields.get("Solution", "")).strip(),
                str(fields.get("Prevention", "")).strip(),
            )
            if token
        ).strip()
        raw_text = "\n".join(lines)
        path_refs = sorted(set([link_target, *host._extract_path_refs(text=raw_text, repo_root=repo_root)]))  # noqa: SLF001
        components = host._parse_component_tokens(str(row.get("Components", "")))  # noqa: SLF001
        rows.append(
            {
                "note_id": f"bug-learning:{link_target}",
                "note_kind": "bug_learning",
                "title": str(row.get("Title", "")).strip(),
                "status": str(row.get("Status", "")).strip(),
                "owner": "",
                "source_path": link_target,
                "section": "",
                "summary": summary or host._bug_summary_from_fields(fields, lines),  # noqa: SLF001
                "tags": ["bug", "learning", str(row.get("Severity", "")).strip().lower()],
                "components": sorted(
                    set(
                        [
                            *components,
                            *host._components_for_paths(component_rows=component_rows, path_refs=path_refs),  # noqa: SLF001
                        ]
                    )
                ),
                "workstreams": host._extract_workstream_refs(raw_text),  # noqa: SLF001
                "path_refs": path_refs,
                "metadata": {"severity": str(row.get("Severity", "")).strip()},
            }
        )
    return rows


def _load_engineering_notes(
    *,
    repo_root: Path,
    connection: Any | None = None,
    component_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    host = _host()
    if component_rows is None:
        if connection is None:
            raise RuntimeError("component rows or connection required for engineering note compilation")
        component_rows = host._load_component_match_rows(connection)  # noqa: SLF001
    rows: list[dict[str, Any]] = []
    rows.extend(_load_adr_notes(repo_root=repo_root, component_rows=component_rows))
    rows.extend(_load_invariant_notes(repo_root=repo_root, component_rows=component_rows))
    rows.extend(_load_data_ownership_notes(repo_root=repo_root, component_rows=component_rows))
    guidance_chunk_rows, chunked_sources = _load_guidance_chunk_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )
    rows.extend(guidance_chunk_rows)
    for note_kind, rel_path in host._SECTION_NOTE_SOURCES:  # noqa: SLF001
        if rel_path in chunked_sources:
            continue
        rows.extend(
            _load_section_bullet_notes(
                repo_root=repo_root,
                rel_path=rel_path,
                note_kind=note_kind,
                component_rows=component_rows,
            )
        )
    rows.extend(_load_runbook_notes(repo_root=repo_root, component_rows=component_rows))
    rows.extend(_load_schema_contract_notes(repo_root=repo_root, component_rows=component_rows))
    rows.extend(_load_make_target_notes(repo_root=repo_root, component_rows=component_rows))
    rows.extend(_load_bug_learning_notes(repo_root=repo_root, component_rows=component_rows))
    return rows

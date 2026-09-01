"""Diagram previews, id allocation, and Atlas writes for greenfield transactions."""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence.greenfield_authored_atlas_view import (
    AUTHORED_ATLAS_AUTHORITY_KEY,
    is_authored_atlas_view,
    validate_authored_atlas_view,
)
from odylith.runtime.domain_intelligence.proposal_validation import validated_mermaid_source
from odylith.runtime.surfaces import scaffold_mermaid_diagram


@dataclass(frozen=True)
class GreenfieldDiagramWriteResult:
    """Committed Atlas diagram rows and scaffold logs for a transaction write."""

    diagram_ids: tuple[str, ...]
    scaffold_logs: tuple[str, ...]


def allocated_diagram_ids(
    repo_root: Path,
    count: int,
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Allocate stable diagram ids while preserving existing catalog slug ids."""

    slug_ids = _catalog_diagram_ids_by_slug(repo_root)
    if rows is None:
        rows = ()
    first = int(_next_diagram_id(repo_root).split("-", 1)[1])
    next_number = first
    used = set(slug_ids.values())
    allocated: list[str] = []
    for index in range(max(0, count)):
        row = rows[index] if index < len(rows) else {}
        slug = str(row.get("slug", "")).strip() if isinstance(row, Mapping) else ""
        existing = slug_ids.get(slug)
        if existing:
            allocated.append(existing)
            continue
        while f"D-{next_number:03d}" in used:
            next_number += 1
        diagram_id = f"D-{next_number:03d}"
        used.add(diagram_id)
        allocated.append(diagram_id)
        next_number += 1
    return allocated


def render_prewrite_atlas_sources(proposal: Mapping[str, Any]) -> dict[str, str]:
    """Render Atlas Mermaid source files in memory for the completion gate."""

    sources: dict[str, str] = {}
    for row in proposal.get("diagrams", []):
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug", "")).strip() or slugify(str(row.get("title", "")).strip())
        if not slug:
            continue
        if is_authored_atlas_view(row):
            source = row.get("mermaid_source")
            if not isinstance(source, str):
                raise ValueError("authored Atlas row is missing its exact Mermaid source")
            validate_authored_atlas_view(row, source_text=source)
            sources[f"odylith/atlas/source/{slug}.mmd"] = source
        else:
            sources[f"odylith/atlas/source/{slug}.mmd"] = validated_mermaid_source(row).rstrip() + "\n"
    return sources


def atlas_review_date(prewrite_package: Any | None) -> str:
    if prewrite_package is not None:
        review_date = str(getattr(prewrite_package, "atlas_review_date", "") or "").strip()
        if not review_date:
            raise ValueError("compiled greenfield Atlas review date missing")
        return review_date
    return dt.date.today().isoformat()


def compiled_atlas_diagram_ids(
    prewrite_package: Any | None,
    *,
    expected_count: int,
) -> list[str]:
    raw_ids = prewrite_package.atlas_diagram_ids if prewrite_package is not None else ()
    diagram_ids = [str(item).strip().upper() for item in raw_ids if str(item).strip()]
    if len(diagram_ids) != expected_count:
        raise ValueError(
            "compiled greenfield Atlas diagram ids missing or incomplete "
            f"(expected {expected_count}, found {len(diagram_ids)})"
        )
    invalid = next((item for item in diagram_ids if not re.fullmatch(r"D-\d{3,}", item)), "")
    if invalid:
        raise ValueError(f"compiled greenfield Atlas diagram id is invalid: {invalid}")
    return diagram_ids


def render_prewrite_atlas_catalog_rows(
    *,
    root: Path,
    rows: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    traceability_plan: Any,
    review_date: str,
) -> tuple[dict[str, Any], ...]:
    """Compile Atlas catalog rows before confirmation."""

    if len(diagram_ids) != len(rows):
        raise ValueError(
            "compiled greenfield Atlas catalog rows missing diagram ids "
            f"(expected {len(rows)}, found {len(diagram_ids)})"
        )
    compiled_rows: list[dict[str, Any]] = []
    for row, diagram_id in zip(rows, diagram_ids, strict=False):
        slug = str(row.get("slug", "")).strip()
        if not slug:
            raise ValueError("compiled greenfield Atlas catalog row missing slug")
        entry = scaffold_mermaid_diagram.build_catalog_entry(
            diagram_id=str(diagram_id).strip().upper(),
            slug=slug,
            title=str(row.get("title", "")).strip(),
            kind=str(row.get("kind", "flowchart")).strip() or "flowchart",
            owner=str(row.get("owner", "repo")).strip() or "repo",
            summary=str(row.get("summary", "")).strip(),
            read_guide=str(row.get("read_guide", "")).strip(),
            components=_proposal_diagram_components(row),
            related_backlog=_repo_relative_backlog_paths(
                root=root,
                paths=_diagram_related_backlog(traceability_plan, str(diagram_id).strip().upper()),
            ),
            related_plans=[],
            related_docs=[],
            related_code=[],
            watch_paths=_existing_watch_paths(root, row),
            review_date=review_date,
        )
        link_state = str(row.get("link_state", "")).strip()
        if link_state:
            entry["link_state"] = link_state
        if is_authored_atlas_view(row):
            source = row.get("mermaid_source")
            if not isinstance(source, str):
                raise ValueError("authored Atlas row is missing its exact Mermaid source")
            authored_view = validate_authored_atlas_view(row, source_text=source)
            entry["projection_origin"] = row["projection_origin"]
            entry["diagram_boxes"] = authored_view["diagram_boxes"]
            entry[AUTHORED_ATLAS_AUTHORITY_KEY] = deepcopy(
                row[AUTHORED_ATLAS_AUTHORITY_KEY]
            )
            validate_authored_atlas_view(entry, source_text=source)
        compiled_rows.append(dict(entry))
    return tuple(compiled_rows)


def compiled_atlas_catalog_rows(
    prewrite_package: Any | None,
    *,
    expected_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Return catalog rows hash-bound to the prewrite package in expected id order."""

    expected = tuple(str(item).strip().upper() for item in expected_ids if str(item).strip())
    raw_rows = getattr(prewrite_package, "atlas_catalog_rows", ()) if prewrite_package is not None else ()
    return _compiled_atlas_catalog_rows_for_ids(raw_rows, expected)


def materialize_apply_diagrams(
    *,
    root: Path,
    rows: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    traceability_plan: Any,
    rendered_atlas_sources: Mapping[str, str],
    review_date: str,
    require_compiled_sources: bool,
    compiled_catalog_rows: Sequence[Mapping[str, Any]] | None = None,
) -> GreenfieldDiagramWriteResult:
    """Materialize Atlas source and catalog rows for greenfield apply/create."""

    atlas_scaffold_logs: list[str] = []
    diagrams_created: list[str] = []
    if require_compiled_sources:
        catalog_rows = _compiled_atlas_catalog_rows_for_ids(compiled_catalog_rows or (), diagram_ids)
        for catalog_row in catalog_rows:
            _materialize_compiled_proposal_diagram(
                root=root,
                catalog_row=catalog_row,
                atlas_scaffold_logs=atlas_scaffold_logs,
                starter_source=compiled_atlas_source(
                    catalog_row,
                    rendered_atlas_sources,
                    required=True,
                ),
            )
            diagrams_created.append(str(catalog_row.get("diagram_id", "")).strip().upper())
        return GreenfieldDiagramWriteResult(
            diagram_ids=tuple(diagrams_created),
            scaffold_logs=tuple(atlas_scaffold_logs),
        )

    for row, diagram_id in zip(rows, diagram_ids, strict=False):
        _scaffold_proposal_diagram(
            root=root,
            row=row,
            diagram_id=diagram_id,
            traceability_plan=traceability_plan,
            atlas_scaffold_logs=atlas_scaffold_logs,
            starter_source=prewrite_atlas_source(
                row,
                rendered_atlas_sources,
                required=require_compiled_sources,
            ),
            review_date=review_date,
        )
        diagrams_created.append(diagram_id)
    return GreenfieldDiagramWriteResult(
        diagram_ids=tuple(diagrams_created),
        scaffold_logs=tuple(atlas_scaffold_logs),
    )


def raise_for_greenfield_rendered_surface_custody(*, repo_root: Path, diagram_ids: Sequence[str]) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    issues: list[str] = []
    required_surfaces = (
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
    )
    for relative_path in required_surfaces:
        path = root / relative_path
        if not path.is_file() or path.stat().st_size <= 0:
            issues.append(f"missing rendered Atlas surface: {relative_path}")
    catalog_path = root / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog = _read_json_mapping(catalog_path)
    rows = catalog.get("diagrams") if isinstance(catalog.get("diagrams"), list) else []
    by_id = {
        str(row.get("diagram_id", "")).strip(): row
        for row in rows
        if isinstance(row, Mapping) and str(row.get("diagram_id", "")).strip()
    }
    checked_ids: list[str] = []
    for diagram_id in [str(value).strip() for value in diagram_ids if str(value).strip()]:
        checked_ids.append(diagram_id)
        row = by_id.get(diagram_id)
        if not isinstance(row, Mapping):
            issues.append(f"missing Atlas catalog entry for greenfield diagram: {diagram_id}")
            continue
        for field in ("source_svg", "source_png"):
            relative_asset = str(row.get(field, "")).strip()
            asset_path = root / relative_asset if relative_asset else None
            if not relative_asset or asset_path is None or not asset_path.is_file() or asset_path.stat().st_size <= 0:
                issues.append(f"{diagram_id}: missing rendered Atlas {field}: {relative_asset or '<empty>'}")
        if not str(row.get("render_source_fingerprint", "")).strip():
            issues.append(f"{diagram_id}: missing Atlas render_source_fingerprint")
        fingerprints = row.get("reviewed_watch_fingerprints")
        if not isinstance(fingerprints, Mapping) or not fingerprints:
            issues.append(f"{diagram_id}: missing Atlas reviewed_watch_fingerprints")
    if issues:
        detail = "\n".join(f"- {issue}" for issue in issues)
        raise RuntimeError(f"greenfield pre-confirm rendered surface custody failed with {len(issues)} issue(s):\n{detail}")
    return {
        "status": "passed",
        "atlas_surface_count": len(required_surfaces),
        "atlas_diagram_count": len(checked_ids),
    }


def actual_atlas_sources(*, root: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    sources: dict[str, str] = {}
    for row in rows:
        path = atlas_source_path_for_row(row)
        if not path:
            continue
        source_path = root / path
        if source_path.is_file():
            sources[path] = source_path.read_text(encoding="utf-8")
    return sources


def prewrite_atlas_source(
    row: Mapping[str, Any],
    rendered_atlas_sources: Mapping[str, str],
    *,
    required: bool = False,
) -> str:
    path = atlas_source_path_for_row(row)
    if not path:
        if required:
            raise ValueError("compiled greenfield Atlas source missing source path")
        return ""
    source = str(rendered_atlas_sources.get(path, "")).strip()
    if required and not source:
        raise ValueError(f"compiled greenfield Atlas source missing for {path}")
    return source


def compiled_atlas_source(
    catalog_row: Mapping[str, Any],
    rendered_atlas_sources: Mapping[str, str],
    *,
    required: bool = False,
) -> str:
    source_mmd = str(catalog_row.get("source_mmd", "")).strip()
    if not source_mmd:
        if required:
            raise ValueError("compiled greenfield Atlas catalog row missing source_mmd")
        return ""
    raw_source = rendered_atlas_sources.get(source_mmd, "")
    source = raw_source if isinstance(raw_source, str) else str(raw_source)
    if required and not source.strip():
        raise ValueError(f"compiled greenfield Atlas source missing for {source_mmd}")
    if source and is_authored_atlas_view(catalog_row):
        validate_authored_atlas_view(catalog_row, source_text=source)
        return source
    return source.strip()


def atlas_source_path_for_row(row: Mapping[str, Any]) -> str:
    slug = str(row.get("slug", "")).strip()
    if not slug:
        return ""
    return f"odylith/atlas/source/{slug}.mmd"


def _next_diagram_id(repo_root: Path) -> str:
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    max_id = 0
    if catalog.is_file():
        try:
            payload = json.loads(catalog.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        for row in payload.get("diagrams", []) if isinstance(payload, Mapping) else []:
            match = re.fullmatch(r"D-(\d{3,})", str(row.get("diagram_id", "")).strip())
            if match:
                max_id = max(max_id, int(match.group(1)))
    return f"D-{max_id + 1:03d}"


def _catalog_diagram_ids_by_slug(repo_root: Path) -> dict[str, str]:
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog.is_file():
        return {}
    try:
        payload = json.loads(catalog.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return {}
    result: dict[str, str] = {}
    for row in diagrams:
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug", "")).strip()
        diagram_id = str(row.get("diagram_id", "")).strip()
        if slug and re.fullmatch(r"D-\d{3,}", diagram_id):
            result.setdefault(slug, diagram_id)
    return result


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _compiled_atlas_catalog_rows_for_ids(
    rows: Sequence[Mapping[str, Any]],
    expected_ids: Sequence[str],
) -> list[dict[str, Any]]:
    expected = tuple(str(item).strip().upper() for item in expected_ids if str(item).strip())
    by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for raw_row in rows:
        if not isinstance(raw_row, Mapping):
            continue
        row = dict(raw_row)
        diagram_id = str(row.get("diagram_id", "")).strip().upper()
        if not diagram_id:
            continue
        if diagram_id in by_id:
            duplicates.append(diagram_id)
        row["diagram_id"] = diagram_id
        by_id[diagram_id] = row
    missing = [diagram_id for diagram_id in expected if diagram_id not in by_id]
    extra = [diagram_id for diagram_id in by_id if diagram_id not in set(expected)]
    if duplicates or missing or extra or len(by_id) != len(expected):
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"unexpected {', '.join(extra)}")
        if duplicates:
            details.append(f"duplicate {', '.join(dedupe_strings(duplicates))}")
        detail = f": {'; '.join(details)}" if details else ""
        raise ValueError(
            "compiled greenfield Atlas catalog rows missing or incomplete "
            f"(expected {len(expected)}, found {len(by_id)}){detail}"
        )
    return [by_id[diagram_id] for diagram_id in expected]


def _materialize_compiled_proposal_diagram(
    *,
    root: Path,
    catalog_row: Mapping[str, Any],
    atlas_scaffold_logs: list[str],
    starter_source: str,
) -> None:
    diagram_id = str(catalog_row.get("diagram_id", "")).strip().upper()
    slug = str(catalog_row.get("slug", "")).strip()
    source_mmd = str(catalog_row.get("source_mmd", "")).strip()
    if not diagram_id or not slug or not source_mmd:
        raise ValueError("compiled greenfield Atlas catalog row missing diagram_id, slug, or source_mmd")
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog_path.is_file():
        raise RuntimeError(f"compiled greenfield Atlas catalog baseline missing: {catalog_path}")
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"compiled greenfield Atlas catalog is malformed: {catalog_path}") from exc
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        raise RuntimeError(f"compiled greenfield Atlas catalog has no diagrams list: {catalog_path}")

    compiled_entry = json.loads(json.dumps(dict(catalog_row), ensure_ascii=True))
    entry = next(
        (
            item
            for item in diagrams
            if isinstance(item, dict)
            and (
                str(item.get("diagram_id", "")).strip().upper() == diagram_id
                or str(item.get("slug", "")).strip() == slug
            )
        ),
        None,
    )
    if entry is None:
        diagrams.append(compiled_entry)
    else:
        entry.update(compiled_entry)
    catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")

    source_path = _resolve_repo_path(root=root, token=source_mmd)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(starter_source.rstrip() + "\n", encoding="utf-8")
    atlas_scaffold_logs.append(f"materialized compiled diagram: {slug}")


def _resolve_repo_path(*, root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"compiled greenfield Atlas path escapes repo root: {resolved}") from exc
    return resolved


def _proposal_diagram_components(row: Mapping[str, Any]) -> list[dict[str, str]]:
    components: list[dict[str, str]] = []
    for component in row.get("components", []):
        if not isinstance(component, Mapping):
            continue
        name = str(component.get("name", "")).strip()
        description = str(component.get("description", "")).strip()
        if name and description:
            components.append({"name": name, "description": description})
    return components


def _diagram_related_backlog(traceability_plan: Any, diagram_id: str) -> list[str]:
    links = getattr(traceability_plan, "diagram_links", ())
    link = next(
        (
            item
            for item in links
            if str(getattr(item, "diagram_id", "")).strip().upper() == str(diagram_id).strip().upper()
        ),
        None,
    )
    return list(getattr(link, "related_backlog_paths", ())) if link is not None else []


def _repo_relative_backlog_paths(*, root: Path, paths: Sequence[str]) -> list[str]:
    """Keep compiled Atlas links portable between target and staging roots."""

    repo_root = root.resolve()
    relative_paths = [
        _resolve_repo_path(root=repo_root, token=str(path)).relative_to(repo_root).as_posix()
        for path in paths
        if str(path).strip()
    ]
    return dedupe_strings(relative_paths)


def _existing_watch_paths(root: Path, row: Mapping[str, Any]) -> list[str]:
    watch_paths: list[str] = []
    repo_root = Path(root).resolve()
    for path in row.get("watch_paths", []):
        token = str(path).strip()
        if not token:
            continue
        candidate = (repo_root / token).resolve() if not Path(token).is_absolute() else Path(token).resolve()
        try:
            candidate.relative_to(repo_root)
        except ValueError:
            continue
        if candidate.exists():
            watch_paths.append(token)
    return watch_paths


def _scaffold_proposal_diagram(
    *,
    root: Path,
    row: Mapping[str, Any],
    diagram_id: str,
    traceability_plan: Any,
    atlas_scaffold_logs: list[str],
    review_date: str,
    starter_source: str = "",
) -> None:
    components = _proposal_diagram_components(row)
    related_backlog = _diagram_related_backlog(traceability_plan, diagram_id)
    watch_paths = _existing_watch_paths(root, row)
    rc, log_lines = scaffold_mermaid_diagram.scaffold_diagram(
        repo_root=root,
        catalog="odylith/atlas/source/catalog/diagrams.v1.json",
        diagram_id=diagram_id,
        slug=str(row.get("slug", "")).strip(),
        title=str(row.get("title", "")).strip(),
        kind=str(row.get("kind", "flowchart")).strip() or "flowchart",
        owner=str(row.get("owner", "repo")).strip() or "repo",
        summary=str(row.get("summary", "")).strip(),
        read_guide=str(row.get("read_guide", "")).strip(),
        components=components,
        related_backlog=related_backlog,
        related_plans=[],
        related_docs=[],
        related_code=[],
        watch_paths=watch_paths,
        review_date=review_date,
        starter_source=starter_source or validated_mermaid_source(row),
        refresh=False,
    )
    log_text = "\n".join(log_lines).strip()
    if log_text:
        atlas_scaffold_logs.append(log_text)
    if rc != 0:
        if _upsert_existing_proposal_diagram(
            root=root,
            row=row,
            diagram_id=diagram_id,
            components=components,
            related_backlog=related_backlog,
            watch_paths=watch_paths,
            review_date=review_date,
            log_text=log_text,
            atlas_scaffold_logs=atlas_scaffold_logs,
            starter_source=starter_source,
        ):
            _update_scaffolded_diagram_link_state(
                root=root,
                slug=str(row.get("slug", "")).strip(),
                link_state=str(row.get("link_state", "")).strip(),
            )
            return
        detail = f": {log_text}" if log_text else ""
        raise RuntimeError(f"atlas scaffold failed for {row.get('slug')}{detail}")
    _update_scaffolded_diagram_link_state(
        root=root,
        slug=str(row.get("slug", "")).strip(),
        link_state=str(row.get("link_state", "")).strip(),
    )


def _upsert_existing_proposal_diagram(
    *,
    root: Path,
    row: Mapping[str, Any],
    diagram_id: str,
    components: list[dict[str, str]],
    related_backlog: list[str],
    watch_paths: list[str],
    review_date: str,
    log_text: str,
    atlas_scaffold_logs: list[str],
    starter_source: str = "",
) -> bool:
    if "already exists" not in log_text:
        return False
    slug = str(row.get("slug", "")).strip()
    if not slug and not diagram_id:
        return False
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog_path.is_file():
        return False
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return False
    entry = next(
        (
            item
            for item in diagrams
            if isinstance(item, dict)
            and (
                (slug and str(item.get("slug", "")).strip() == slug)
                or (diagram_id and str(item.get("diagram_id", "")).strip() == diagram_id)
            )
        ),
        None,
    )
    if entry is None:
        return False
    source_mmd = str(entry.get("source_mmd") or f"odylith/atlas/source/{slug}.mmd").strip()
    source_svg = str(entry.get("source_svg") or f"odylith/atlas/source/{slug}.svg").strip()
    source_png = str(entry.get("source_png") or f"odylith/atlas/source/{slug}.png").strip()
    entry.update(
        {
            "diagram_id": str(entry.get("diagram_id") or diagram_id).strip(),
            "slug": str(entry.get("slug") or slug).strip(),
            "title": str(row.get("title", "")).strip(),
            "kind": str(row.get("kind", "flowchart")).strip() or "flowchart",
            "owner": str(row.get("owner", "repo")).strip() or "repo",
            "last_reviewed_utc": review_date,
            "source_mmd": source_mmd,
            "source_svg": source_svg,
            "source_png": source_png,
            "summary": str(row.get("summary", "")).strip(),
            "read_guide": str(row.get("read_guide", "")).strip(),
            "components": components,
            "related_backlog": dedupe_strings(related_backlog),
            "change_watch_paths": dedupe_strings(watch_paths) or [source_mmd],
        }
    )
    catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    source_path = root / source_mmd
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text((starter_source or validated_mermaid_source(row)).rstrip() + "\n", encoding="utf-8")
    atlas_scaffold_logs.append(f"updated existing diagram: {entry['slug']}")
    return True


def _update_scaffolded_diagram_link_state(*, root: Path, slug: str, link_state: str) -> None:
    if not slug or not link_state:
        return
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog_path.is_file():
        return
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return
    changed = False
    for item in diagrams:
        if not isinstance(item, dict):
            continue
        if str(item.get("slug", "")).strip() != slug:
            continue
        if str(item.get("link_state", "")).strip() != link_state:
            item["link_state"] = link_state
            changed = True
    if changed:
        catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


__all__ = [
    "GreenfieldDiagramWriteResult",
    "actual_atlas_sources",
    "allocated_diagram_ids",
    "atlas_review_date",
    "atlas_source_path_for_row",
    "compiled_atlas_catalog_rows",
    "compiled_atlas_diagram_ids",
    "compiled_atlas_source",
    "materialize_apply_diagrams",
    "prewrite_atlas_source",
    "raise_for_greenfield_rendered_surface_custody",
    "render_prewrite_atlas_catalog_rows",
    "render_prewrite_atlas_sources",
]

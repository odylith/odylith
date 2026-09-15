"""Validate and atomically update explicit Atlas metadata patches, then refresh once."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_bytes
from odylith.runtime.governance import artifact_tribunal
from odylith.runtime.governance import component_registry_intelligence
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.surfaces import (
    atlas_box_explanations,
    render_mermaid_catalog,
    scaffold_mermaid_diagram,
)


_PATH_FIELDS = (
    "related_backlog",
    "related_plans",
    "related_docs",
    "related_code",
    "change_watch_paths",
)
_TEXT_FIELDS = ("title", "kind", "owner", "summary", "read_guide", "last_reviewed_utc")
_PATCH_FIELDS = frozenset((*_PATH_FIELDS, *_TEXT_FIELDS, "components", "diagram_boxes"))
_UPDATES_VERSION = "odylith.atlas.updates.v1"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith atlas update",
        description="Update existing Atlas catalog entries without replacing omitted fields",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--catalog",
        default="odylith/atlas/source/catalog/diagrams.v1.json",
        help="Catalog JSON path",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--diagram-id",
        help="Existing diagram ID (for example D-010)",
    )
    mode.add_argument(
        "--updates-file",
        help="JSON object with version 'odylith.atlas.updates.v1' and explicit updates",
    )
    parser.add_argument("--title", help="Replacement human-readable title")
    parser.add_argument("--kind", help="Replacement Mermaid kind")
    parser.add_argument("--owner", help="Replacement owning team/role")
    parser.add_argument("--summary", help="Replacement one-paragraph summary")
    parser.add_argument("--read-guide", help="Replacement diagram-specific reader guidance")
    parser.add_argument(
        "--component",
        action="append",
        default=None,
        help="Replacement component in format 'Name::Description' (repeatable)",
    )
    parser.add_argument(
        "--backlog",
        action="append",
        default=None,
        help="Replacement backlog path (repeatable)",
    )
    parser.add_argument(
        "--plan",
        action="append",
        default=None,
        help="Replacement plan path (repeatable)",
    )
    parser.add_argument(
        "--doc",
        action="append",
        default=None,
        help="Replacement doc path (repeatable)",
    )
    parser.add_argument(
        "--code",
        action="append",
        default=None,
        help="Replacement code path (repeatable)",
    )
    parser.add_argument(
        "--watch",
        action="append",
        default=None,
        help="Replacement change-watch path (repeatable)",
    )
    parser.add_argument("--review-date", help="Replacement review date in YYYY-MM-DD format")
    args = parser.parse_args(argv)
    single_fields = (
        "title", "kind", "owner", "summary", "read_guide", "component", "backlog",
        "plan", "doc", "code", "watch", "review_date",
    )
    if args.updates_file is not None and any(getattr(args, field) is not None for field in single_fields):
        parser.error("--updates-file cannot be combined with single-entry replacement flags")
    return args


def _repo_local_path(
    *,
    repo_root: Path,
    token: str,
    field: str,
    require_file: bool = False,
    allow_missing: bool = False,
) -> tuple[Path, str]:
    if not isinstance(token, str) or not token.strip():
        raise ValueError(f"{field} contains an empty path")
    raw = token
    path = Path(raw)
    if path.is_absolute():
        raise ValueError(f"{field} must be repository-relative: {raw}")
    target = (repo_root / path).resolve()
    try:
        normalized = target.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"{field} escapes the repository root: {raw}") from exc
    directory_reference = (
        field in _PATH_FIELDS and not require_file and not allow_missing
        and target.is_dir() and raw == normalized + "/"
    )
    if normalized == "." or (raw != normalized and not directory_reference):
        raise ValueError(f"{field} requires a canonical repository-relative path without symlink aliases: {raw}")
    if require_file and not target.is_file():
        raise ValueError(f"{field} file does not exist: {raw}")
    if allow_missing and target.exists() and not target.is_file():
        raise ValueError(f"{field} must be a regular file when present: {raw}")
    if not require_file and not allow_missing and not target.exists():
        raise ValueError(f"{field} path does not exist: {raw}")
    return target, raw


def _replacement_paths(
    *,
    repo_root: Path,
    field: str,
    values: list[str] | None,
) -> list[str] | None:
    if values is None:
        return None
    if not values:
        raise ValueError(f"{field} requires at least one path")
    normalized: list[str] = []
    for token in values:
        _target, repo_path = _repo_local_path(
            repo_root=repo_root,
            token=token,
            field=field,
        )
        if repo_path not in normalized:
            normalized.append(repo_path)
    return normalized


def _sequence(entry: dict[str, Any], field: str) -> list[Any]:
    values = entry.get(field)
    if not isinstance(values, list):
        raise ValueError(f"existing Atlas entry has malformed `{field}`")
    return list(values)


def _unique_patch_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """JSON patch objects must not silently overwrite an earlier field."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _read_updates(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_patch_fields)
    if not isinstance(payload, dict) or set(payload) != {"version", "updates"}:
        raise ValueError("updates file requires exactly version and updates fields")
    if payload["version"] != _UPDATES_VERSION:
        raise ValueError(f"updates file version must be {_UPDATES_VERSION}")
    updates = payload["updates"]
    if not isinstance(updates, list) or not updates:
        raise ValueError("updates must be a non-empty list of explicit entry patches")
    return updates


def _require_diagram_id(value: Any) -> str:
    if (
        not isinstance(value, str) or not value
        or component_registry_intelligence.normalize_diagram_id(value) != value
    ):
        raise ValueError("diagram_id must be an exact canonical D-### identifier")
    return value


def _validate_patch(patch: Any) -> str:
    if not isinstance(patch, dict) or set(patch) - {"diagram_id", *_PATCH_FIELDS}:
        raise ValueError("Atlas update contains unknown or immutable fields")
    diagram_id = _require_diagram_id(patch.get("diagram_id"))
    if len(patch) == 1:
        raise ValueError("atlas update requires at least one replacement field")
    for field, value in patch.items():
        if field in _TEXT_FIELDS and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{field} requires non-empty text")
        if field in _PATH_FIELDS and (
            not isinstance(value, list) or not value
            or any(not isinstance(path, str) or not path for path in value)
        ):
            raise ValueError(f"{field} requires a non-empty list of paths")
        if field in {"components", "diagram_boxes"}:
            fields = {"name", "description"} if field == "components" else {"label", "role", "description"}
            if not isinstance(value, list) or not value:
                raise ValueError(f"{field} requires a non-empty list")
            for row in value:
                if (
                    not isinstance(row, dict) or set(row) != fields
                    or any(not isinstance(item, str) or not item.strip() for item in row.values())
                ):
                    raise ValueError(f"{field} rows require exactly {', '.join(sorted(fields))} as non-empty text")
    return diagram_id


def _validated_boxes(repo_root: Path, source: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    errors: list[str] = []
    authored = atlas_box_explanations.normalize_catalog_diagram_boxes(
        raw_boxes=rows, context=source, errors=errors,
    )
    visible = atlas_box_explanations.extract_diagram_boxes_from_mermaid(
        (repo_root / source).read_text(encoding="utf-8"),
    )
    labels = set(atlas_box_explanations.diagram_box_labels(row.as_dict() for row in authored))
    expected = set(atlas_box_explanations.diagram_box_labels(row.as_dict() for row in visible))
    if labels != expected:
        errors.append(
            f"diagram_boxes must cover exact source labels; missing={sorted(expected - labels)}, "
            f"orphaned={sorted(labels - expected)}"
        )
    if errors:
        raise ValueError("; ".join(errors))
    return [{"label": row.label, "role": row.role, "description": row.description} for row in authored]


def update_diagram(
    *,
    repo_root: Path,
    catalog: str,
    diagram_id: str,
    title: str | None = None,
    kind: str | None = None,
    owner: str | None = None,
    summary: str | None = None,
    read_guide: str | None = None,
    components: list[dict[str, str]] | None = None,
    related_backlog: list[str] | None = None,
    related_plans: list[str] | None = None,
    related_docs: list[str] | None = None,
    related_code: list[str] | None = None,
    watch_paths: list[str] | None = None,
    review_date: str | None = None,
    diagram_boxes: list[dict[str, str]] | None = None,
    refresh: bool = True,
) -> tuple[int, list[str]]:
    """Replace only explicitly supplied metadata on one existing diagram."""
    supplied = {
        "title": title,
        "kind": kind,
        "owner": owner,
        "summary": summary,
        "read_guide": read_guide,
        "components": components,
        "related_backlog": related_backlog,
        "related_plans": related_plans,
        "related_docs": related_docs,
        "related_code": related_code,
        "change_watch_paths": watch_paths,
        "last_reviewed_utc": review_date,
        "diagram_boxes": diagram_boxes,
    }
    patch = {"diagram_id": diagram_id, **{key: value for key, value in supplied.items() if value is not None}}
    return update_diagrams(repo_root=repo_root, catalog=catalog, updates=[patch], refresh=refresh)


def _updated_entry(*, repo_root: Path, existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    diagram_id = _validate_patch(patch)
    candidate = {**existing, **patch}
    dt.date.fromisoformat(candidate["last_reviewed_utc"])
    paths = {
        field: _replacement_paths(repo_root=repo_root, field=field, values=patch.get(field))
        if field in patch else _sequence(existing, field)
        for field in _PATH_FIELDS
    }
    built = scaffold_mermaid_diagram.build_catalog_entry(
        diagram_id=diagram_id, slug=existing["slug"], title=candidate["title"],
        kind=candidate["kind"], owner=candidate["owner"], summary=candidate["summary"],
        read_guide=candidate.get("read_guide", ""), components=candidate["components"],
        related_backlog=paths["related_backlog"], related_plans=paths["related_plans"],
        related_docs=paths["related_docs"], related_code=paths["related_code"],
        watch_paths=paths["change_watch_paths"], review_date=candidate["last_reviewed_utc"],
    )
    tribunal = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="atlas_diagram", payload={**built, "watch_paths": built["change_watch_paths"]},
    )
    artifact_tribunal.raise_for_failed_artifact_tribunal(tribunal)
    if "diagram_boxes" in patch:
        _source, relative = _repo_local_path(
            repo_root=repo_root, token=existing["source_mmd"], field="source_mmd", require_file=True,
        )
        built["diagram_boxes"] = _validated_boxes(repo_root, relative, patch["diagram_boxes"])
    updated = dict(existing)
    updated.update({field: built[field] for field in patch if field != "diagram_id"})
    if set(patch) & {"related_backlog", "related_plans", "related_docs"}:
        updated["status"] = built["status"]
        if "link_state" in built:
            updated["link_state"] = built["link_state"]
        else:
            updated.pop("link_state", None)
    if "change_watch_paths" in patch:
        updated.pop("reviewed_watch_fingerprints", None)
    return updated


def _validate_candidate(*, repo_root: Path, catalog_path: Path, payload: dict[str, Any]) -> None:
    for entry in payload["diagrams"]:
        _require_diagram_id(entry.get("diagram_id"))
        for field in _PATH_FIELDS:
            for token in _sequence(entry, field):
                _repo_local_path(repo_root=repo_root, token=token, field=field)
        for field, suffix in (("source_mmd", "mmd"), ("source_svg", "svg"), ("source_png", "png")):
            _path, relative = _repo_local_path(
                repo_root=repo_root, token=entry.get(field), field=field,
                require_file=suffix == "mmd", allow_missing=suffix != "mmd",
            )
            if relative != f"odylith/atlas/source/{entry.get('slug')}.{suffix}":
                raise ValueError(f"existing `{field}` does not match immutable diagram slug")
    errors = render_mermaid_catalog.validate_catalog_metadata(
        repo_root=repo_root, catalog_path=catalog_path, payload=payload,
    )
    if errors:
        raise ValueError("; ".join(errors))


def update_diagrams(
    *, repo_root: Path, catalog: str, updates: list[dict[str, Any]], refresh: bool = True,
) -> tuple[int, list[str]]:
    """Validate the complete merged catalog before one atomic write and one refresh."""
    repo_root = Path(repo_root).resolve()
    try:
        catalog_path, _relative = _repo_local_path(
            repo_root=repo_root, token=catalog, field="catalog", require_file=True,
        )
        before = catalog_path.read_bytes()
        mode = stat.S_IMODE(catalog_path.stat().st_mode)
        payload = json.loads(before, object_pairs_hook=_unique_patch_fields)
        if not isinstance(payload, dict) or not isinstance(payload.get("diagrams"), list):
            raise ValueError(f"malformed catalog: {catalog_path}")
        diagrams = payload["diagrams"]
        indexes: dict[str, int] = {}
        for index, entry in enumerate(diagrams):
            if not isinstance(entry, dict):
                raise ValueError("malformed catalog row")
            diagram_id = _require_diagram_id(entry.get("diagram_id"))
            if diagram_id in indexes:
                raise ValueError(f"diagram_id is duplicated: {diagram_id}")
            indexes[diagram_id] = index
        if not isinstance(updates, list) or not updates:
            raise ValueError("updates must be a non-empty list")
        seen: set[str] = set()
        for patch in updates:
            diagram_id = _validate_patch(patch)
            if diagram_id in seen:
                raise ValueError(f"duplicate update for diagram_id: {diagram_id}")
            if diagram_id not in indexes:
                raise ValueError(f"diagram_id not found: {diagram_id}")
            seen.add(diagram_id)
            index = indexes[diagram_id]
            diagrams[index] = _updated_entry(repo_root=repo_root, existing=diagrams[index], patch=patch)
        _validate_candidate(repo_root=repo_root, catalog_path=catalog_path, payload=payload)
        encoded = (json.dumps(payload, indent=2, allow_nan=False) + "\n").encode("utf-8")
        if catalog_path.read_bytes() != before or stat.S_IMODE(catalog_path.stat().st_mode) != mode:
            raise ValueError("catalog changed during metadata validation")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return 2, [f"FAILED: {exc}"]
    try:
        atomic_write_bytes(catalog_path, encoded, mode=mode)
    except (OSError, ValueError) as exc:
        return 1, [f"FAILED: Atlas catalog write did not complete: {exc}"]
    logs = [
        f"catalog updated: {catalog_path}",
        *(
            f"updated diagram: {patch['diagram_id']} / {diagrams[indexes[patch['diagram_id']]]['slug']}"
            for patch in updates
        ),
        "validation gate: passed",
    ]
    if refresh:
        try:
            owned_surface_refresh.raise_for_failed_refresh(
                repo_root=repo_root,
                surface="atlas",
                operation_label="Atlas update",
            )
        except (OSError, RuntimeError, ValueError) as exc:
            logs.append(str(exc))
            logs.append(
                "Atlas metadata was written, but refresh failed; no recovery or publication success is claimed."
            )
            return 1, logs
    return 0, logs


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        components = (
            scaffold_mermaid_diagram.parse_components(list(args.component))
            if args.component is not None
            else None
        )
        updates = _read_updates(Path(args.updates_file)) if args.updates_file is not None else None
    except (OSError, ValueError) as exc:
        print(f"FAILED: {exc}")
        return 2
    if updates is not None:
        rc, logs = update_diagrams(repo_root=repo_root, catalog=str(args.catalog), updates=updates)
    else:
        rc, logs = update_diagram(
            repo_root=repo_root,
            catalog=str(args.catalog),
            diagram_id=str(args.diagram_id),
            title=args.title,
            kind=args.kind,
            owner=args.owner,
            summary=args.summary,
            read_guide=args.read_guide,
            components=components,
            related_backlog=args.backlog,
            related_plans=args.plan,
            related_docs=args.doc,
            related_code=args.code,
            watch_paths=args.watch,
            review_date=args.review_date,
        )
    for line in logs:
        print(line)
    if rc == 0:
        owned_surface_refresh.print_dashboard_handoff(surface="atlas", diagram=args.diagram_id or "")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

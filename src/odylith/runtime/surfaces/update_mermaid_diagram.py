"""Update one existing Atlas catalog entry without replacing omitted fields."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.governance import artifact_tribunal
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.surfaces import scaffold_mermaid_diagram


_PATH_FIELDS = (
    "related_backlog",
    "related_plans",
    "related_docs",
    "related_code",
    "change_watch_paths",
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith atlas update",
        description="Update one existing Atlas catalog entry",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--catalog",
        default="odylith/atlas/source/catalog/diagrams.v1.json",
        help="Catalog JSON path",
    )
    parser.add_argument(
        "--diagram-id",
        required=True,
        help="Existing diagram ID (for example D-010)",
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
    return parser.parse_args(argv)


def _repo_local_path(
    *,
    repo_root: Path,
    token: str,
    field: str,
    require_file: bool = False,
    allow_missing: bool = False,
) -> tuple[Path, str]:
    raw = str(token or "").strip()
    if not raw:
        raise ValueError(f"{field} contains an empty path")
    path = Path(raw)
    if path.is_absolute():
        raise ValueError(f"{field} must be repository-relative: {raw}")
    target = (repo_root / path).resolve()
    try:
        normalized = target.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"{field} escapes the repository root: {raw}") from exc
    if require_file and not target.is_file():
        raise ValueError(f"{field} file does not exist: {raw}")
    if not require_file and not allow_missing and not target.exists():
        raise ValueError(f"{field} path does not exist: {raw}")
    return target, normalized


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
    refresh: bool = True,
) -> tuple[int, list[str]]:
    """Replace only explicitly supplied metadata on one existing diagram."""

    repo_root = Path(repo_root).resolve()
    try:
        catalog_path, _catalog_repo_path = _repo_local_path(
            repo_root=repo_root,
            token=catalog,
            field="catalog",
            require_file=True,
        )
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return 2, [f"FAILED: {exc}"]
    diagrams = payload.get("diagrams") if isinstance(payload, dict) else None
    if not isinstance(diagrams, list):
        return 2, [f"FAILED: malformed catalog: {catalog_path}"]
    if any(not isinstance(item, dict) for item in diagrams):
        return 2, [f"FAILED: malformed catalog row: {catalog_path}"]

    diagram_id = str(diagram_id or "").strip()
    matches = [
        (index, item)
        for index, item in enumerate(diagrams)
        if isinstance(item, dict)
        and str(item.get("diagram_id", "")).strip() == diagram_id
    ]
    if len(matches) != 1:
        detail = "not found" if not matches else "is duplicated"
        return 2, [f"FAILED: diagram_id {detail}: {diagram_id}"]

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
    }
    if not any(value is not None for value in supplied.values()):
        return 2, ["FAILED: atlas update requires at least one replacement field"]

    index, existing = matches[0]
    try:
        candidate_review_date = str(
            review_date
            if review_date is not None
            else existing.get("last_reviewed_utc", "")
        ).strip()
        dt.date.fromisoformat(candidate_review_date)
        normalized_paths = {
            field: _replacement_paths(repo_root=repo_root, field=field, values=supplied[field])
            for field in _PATH_FIELDS
        }
        candidate_inputs = {
            field: normalized_paths[field] if normalized_paths[field] is not None else _sequence(existing, field)
            for field in _PATH_FIELDS
        }
        candidate_components = components if components is not None else _sequence(existing, "components")
        built = scaffold_mermaid_diagram.build_catalog_entry(
            diagram_id=diagram_id,
            slug=str(existing.get("slug", "")),
            title=str(title if title is not None else existing.get("title", "")),
            kind=str(kind if kind is not None else existing.get("kind", "")),
            owner=str(owner if owner is not None else existing.get("owner", "")),
            summary=str(summary if summary is not None else existing.get("summary", "")),
            read_guide=str(read_guide if read_guide is not None else existing.get("read_guide", "")),
            components=candidate_components,
            related_backlog=candidate_inputs["related_backlog"],
            related_plans=candidate_inputs["related_plans"],
            related_docs=candidate_inputs["related_docs"],
            related_code=candidate_inputs["related_code"],
            watch_paths=candidate_inputs["change_watch_paths"],
            review_date=candidate_review_date,
        )
        for source_field in ("source_mmd", "source_svg", "source_png"):
            _target, normalized_source = _repo_local_path(
                repo_root=repo_root,
                token=str(existing.get(source_field, "")),
                field=source_field,
                require_file=source_field == "source_mmd",
                allow_missing=source_field != "source_mmd",
            )
            if normalized_source != built[source_field]:
                raise ValueError(
                    f"existing `{source_field}` does not match immutable diagram slug"
                )
        tribunal = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="atlas_diagram",
            payload={
                "diagram_id": built["diagram_id"],
                "slug": built["slug"],
                "title": built["title"],
                "kind": built["kind"],
                "owner": built["owner"],
                "summary": built["summary"],
                "read_guide": built["read_guide"],
                "components": built["components"],
                "related_backlog": built["related_backlog"],
                "related_plans": built["related_plans"],
                "related_docs": built["related_docs"],
                "related_code": built["related_code"],
                "watch_paths": built["change_watch_paths"],
            },
        )
        artifact_tribunal.raise_for_failed_artifact_tribunal(tribunal)
    except (KeyError, TypeError, ValueError) as exc:
        return 2, [f"FAILED: {exc}"]

    updated = dict(existing)
    for field, value in supplied.items():
        if value is None:
            continue
        updated[field] = built[field]
    if any(supplied[field] is not None for field in ("related_backlog", "related_plans", "related_docs")):
        updated["status"] = built["status"]
        if "link_state" in built:
            updated["link_state"] = built["link_state"]
        else:
            updated.pop("link_state", None)
    if watch_paths is not None:
        updated.pop("reviewed_watch_fingerprints", None)
    diagrams[index] = updated
    catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    logs = [
        f"catalog updated: {catalog_path}",
        f"updated diagram: {diagram_id} / {updated.get('slug', '')}",
        f"validation gate: {tribunal.status}",
    ]
    if refresh:
        try:
            owned_surface_refresh.raise_for_failed_refresh(
                repo_root=repo_root,
                surface="atlas",
                operation_label="Atlas update",
            )
        except RuntimeError as exc:
            logs.append(str(exc))
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
    except ValueError as exc:
        print(f"FAILED: {exc}")
        return 2
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
        owned_surface_refresh.print_dashboard_handoff(surface="atlas", diagram=str(args.diagram_id).strip())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

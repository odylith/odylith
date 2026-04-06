"""Scaffold Mermaid diagram metadata + source using the Odylith catalog contract."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Sequence


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold Mermaid diagram metadata + source")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--catalog", default="odylith/atlas/source/catalog/diagrams.v1.json", help="Catalog JSON path")
    parser.add_argument("--diagram-id", required=True, help="Diagram ID (for example D-010)")
    parser.add_argument("--slug", required=True, help="Diagram slug (kebab-case)")
    parser.add_argument("--title", required=True, help="Human-readable title")
    parser.add_argument("--kind", required=True, help="Mermaid kind (flowchart, sequence, ...)")
    parser.add_argument("--owner", required=True, help="Owning team/role")
    parser.add_argument("--summary", required=True, help="One-paragraph summary")
    parser.add_argument("--component", action="append", default=[], help="Component in format 'Name::Description' (repeatable)")
    parser.add_argument("--backlog", action="append", default=[], help="Related backlog path (repeatable)")
    parser.add_argument("--plan", action="append", default=[], help="Related plan path (repeatable)")
    parser.add_argument("--doc", action="append", default=[], help="Related doc path (repeatable)")
    parser.add_argument("--code", action="append", default=[], help="Related code path (repeatable)")
    parser.add_argument(
        "--watch",
        action="append",
        default=[],
        help="Change-watch path (repeatable). If omitted, derived from doc/technical-plan/code.",
    )
    parser.add_argument(
        "--review-date",
        default=dt.date.today().isoformat(),
        help="Review date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--create-source-if-missing",
        action="store_true",
        help="Create odylith/atlas/source/<slug>.mmd from template if it does not exist",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token).strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _parse_components(tokens: list[str]) -> list[dict[str, str]]:
    components: list[dict[str, str]] = []
    for token in tokens:
        raw = str(token or "").strip()
        if not raw:
            continue
        if "::" not in raw:
            raise ValueError(f"invalid component `{raw}`; expected format 'Name::Description'")
        name, description = raw.split("::", 1)
        name = name.strip()
        description = description.strip()
        if not name or not description:
            raise ValueError(f"invalid component `{raw}`; name/description must be non-empty")
        components.append({"name": name, "description": description})
    if not components:
        components = [
            {
                "name": "Component Placeholder",
                "description": "Replace with concrete behavior component mapping.",
            }
        ]
    return components


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    catalog_path = _resolve(repo_root, args.catalog)

    if not catalog_path.is_file():
        print(f"FAILED: catalog not found: {catalog_path}")
        return 2

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    diagrams = payload.get("diagrams")
    if not isinstance(diagrams, list):
        print(f"FAILED: malformed catalog: {catalog_path}")
        return 2

    diagram_id = str(args.diagram_id).strip()
    slug = str(args.slug).strip()

    for item in diagrams:
        if str(item.get("diagram_id", "")).strip() == diagram_id:
            print(f"FAILED: diagram_id already exists: {diagram_id}")
            return 2
        if str(item.get("slug", "")).strip() == slug:
            print(f"FAILED: slug already exists: {slug}")
            return 2

    source_mmd = f"odylith/atlas/source/{slug}.mmd"
    source_svg = f"odylith/atlas/source/{slug}.svg"
    source_png = f"odylith/atlas/source/{slug}.png"

    components = _parse_components(args.component)
    related_backlog = _unique(args.backlog)
    related_plans = _unique(args.plan)
    related_docs = _unique(args.doc)
    related_code = _unique(args.code)

    if not related_backlog or not related_plans or not related_docs:
        print("FAILED: radar, technical-plan, and doc links are required (at least one each)")
        return 2

    watch_paths = _unique(args.watch)
    if not watch_paths:
        watch_paths = _unique(related_docs + related_plans + related_code)
    if not watch_paths:
        print("FAILED: change_watch_paths resolved empty; provide --watch or related links")
        return 2

    entry = {
        "diagram_id": diagram_id,
        "slug": slug,
        "title": str(args.title).strip(),
        "kind": str(args.kind).strip(),
        "status": "active",
        "owner": str(args.owner).strip(),
        "last_reviewed_utc": str(args.review_date).strip(),
        "source_mmd": source_mmd,
        "source_svg": source_svg,
        "source_png": source_png,
        "change_watch_paths": watch_paths,
        "summary": str(args.summary).strip(),
        "components": components,
        "related_backlog": related_backlog,
        "related_plans": related_plans,
        "related_docs": related_docs,
        "related_code": related_code,
    }
    diagrams.append(entry)

    catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    print(f"catalog updated: {catalog_path}")
    print(f"added: {diagram_id} ({slug})")

    if args.create_source_if_missing:
        source_path = _resolve(repo_root, source_mmd)
        if source_path.exists():
            print(f"source exists: {source_path}")
        else:
            template = (
                "flowchart TB\\n"
                '    start["TODO: Replace with real diagram"] --> done["Initial scaffold created"]\\n'
            )
            source_path.write_text(template, encoding="utf-8")
            print(f"source created: {source_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

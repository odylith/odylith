"""Scaffold Mermaid diagram metadata + source using the Odylith catalog contract."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Sequence

from odylith.runtime.governance import artifact_tribunal
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.surfaces import surface_path_helpers


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith atlas scaffold",
        description="Scaffold Mermaid diagram metadata + source",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--catalog", default="odylith/atlas/source/catalog/diagrams.v1.json", help="Catalog JSON path")
    parser.add_argument("--diagram-id", required=True, help="Diagram ID (for example D-010)")
    parser.add_argument("--slug", required=True, help="Diagram slug (kebab-case)")
    parser.add_argument("--title", required=True, help="Human-readable title")
    parser.add_argument("--kind", required=True, help="Mermaid kind (flowchart, sequence, ...)")
    parser.add_argument("--owner", required=True, help="Owning team/role")
    parser.add_argument("--summary", required=True, help="One-paragraph summary")
    parser.add_argument(
        "--read-guide",
        default="",
        help="Optional diagram-specific reader guidance shown in the Atlas detail pane.",
    )
    parser.add_argument("--component", action="append", default=[], help="Component in format 'Name::Description' (repeatable)")
    parser.add_argument("--backlog", action="append", default=[], help="Related backlog path (repeatable)")
    parser.add_argument("--plan", action="append", default=[], help="Related plan path (repeatable)")
    parser.add_argument("--doc", action="append", default=[], help="Related doc path (repeatable)")
    parser.add_argument("--code", action="append", default=[], help="Related code path (repeatable)")
    parser.add_argument(
        "--watch",
        action="append",
        default=[],
        help="Change-watch path (repeatable). If omitted, derived from doc/technical-plan/code or the new source.",
    )
    parser.add_argument(
        "--review-date",
        default=dt.date.today().isoformat(),
        help="Review date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--create-source-if-missing",
        action="store_true",
        help="Compatibility flag; Atlas scaffold now creates a starter source whenever it is missing.",
    )
    parser.add_argument(
        "--require-links",
        action="store_true",
        help="Fail unless at least one Radar, technical-plan, and doc link are provided.",
    )
    return parser.parse_args(argv)


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
        raise ValueError("atlas scaffold requires at least one concrete --component Name::Description")
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


def _wrapped_label_lines(value: str, *, width: int = 30) -> list[str]:
    words = " ".join(str(value or "").strip().split()).split()
    if not words:
        return ["Unspecified"]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _mermaid_label(value: str, *, width: int = 30) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        text = "Unspecified"
    wrapped = _wrapped_label_lines(text, width=width)
    return "<br/>".join(line.replace("\\", "\\\\").replace('"', "'") for line in wrapped)


def _starter_source(
    *,
    title: str,
    owner: str,
    components: list[dict[str, str]],
    watch_paths: list[str],
    related_backlog: list[str],
    related_plans: list[str],
    related_docs: list[str],
) -> str:
    lines = [
        "%% Atlas visual contract: neutral containers organize structure; semantic node classes carry state; labels stay wrapped.",
        "flowchart TB",
        '    subgraph intent_lane["Intent lane"]',
        "      direction TB",
        f'      diagram["{_mermaid_label(title, width=34)}"]',
        f'      owner["Owner<br/>{_mermaid_label(owner, width=26)}"]',
        "    end",
        "",
        '    subgraph component_lane["Component lane"]',
        "      direction LR",
    ]
    component_ids: list[str] = []
    for index, component in enumerate(components[:5], start=1):
        name = _mermaid_label(str(component.get("name", "")).strip(), width=26)
        description = _mermaid_label(str(component.get("description", "")).strip(), width=30)
        component_id = f"component_{index}"
        component_ids.append(component_id)
        lines.append(f'      {component_id}["{name}<br/>{description}"]')
    lines.extend(
        [
            "    end",
            "",
            '    subgraph evidence_lane["Evidence lane"]',
            "      direction TB",
        ]
    )
    evidence_ids: list[str] = []
    for index, path in enumerate(watch_paths[:4], start=1):
        watch_id = f"watch_{index}"
        evidence_ids.append(watch_id)
        lines.append(f'      {watch_id}["Watch<br/>{_mermaid_label(path, width=28)}"]')
    if not (related_backlog and related_plans and related_docs):
        evidence_ids.append("followup")
        lines.append('      followup["Link Radar, plan, and docs<br/>as governance matures"]')
    lines.extend(
        [
            "    end",
            "",
            "    diagram --> owner",
        ]
    )
    for component_id in component_ids:
        lines.append(f"    diagram --> {component_id}")
    if component_ids:
        for evidence_id in evidence_ids:
            lines.append(f"    {component_ids[0]} --> {evidence_id}")
    else:
        for evidence_id in evidence_ids:
            lines.append(f"    diagram --> {evidence_id}")
    lines.extend(
        [
            "",
            "    classDef neutral fill:#FBFDFF,stroke:#D8E5F4,color:#17233A,stroke-width:1px;",
            "    classDef primary fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
            "    classDef execution fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "    classDef governance fill:#F5F3FF,stroke:#DDD6FE,color:#17233A,stroke-width:1px;",
            "    classDef constraint fill:#FFF8E6,stroke:#F6D98B,color:#17233A,stroke-width:1px;",
            "    classDef invalid fill:#FFF1F0,stroke:#F7B4AE,color:#17233A,stroke-width:1px;",
            "    class diagram,owner primary;",
        ]
    )
    if component_ids:
        lines.append(f"    class {','.join(component_ids)} execution;")
    if evidence_ids:
        watch_ids = [value for value in evidence_ids if value != "followup"]
        if watch_ids:
            lines.append(f"    class {','.join(watch_ids)} execution;")
        if "followup" in evidence_ids:
            lines.append("    class followup constraint;")
    lines.extend(
        [
            "    style intent_lane fill:#FBFDFF,stroke:#BFD7FE,stroke-width:1px,color:#334155",
            "    style component_lane fill:#FBFDFF,stroke:#A7E9E3,stroke-width:1px,color:#334155",
            "    style evidence_lane fill:#FBFDFF,stroke:#A7E9E3,stroke-width:1px,color:#334155",
            "    linkStyle default stroke:#B9C7D8,stroke-width:1.25px",
        ]
    )
    return "\n".join(lines) + "\n"


def _default_read_guide(*, title: str, kind: str, components: list[dict[str, str]]) -> str:
    component_names = [
        str(component.get("name", "")).strip()
        for component in components[:3]
        if str(component.get("name", "")).strip()
    ]
    component_hint = ""
    if component_names:
        component_hint = f" Key owned boundaries: {', '.join(component_names)}."
    kind_token = str(kind or "").strip().lower()
    title_token = str(title or "").strip() or "this diagram"
    if "sequence" in kind_token:
        return (
            f"Read {title_token} as a first-path rehearsal. Start with the user or trigger, follow each handoff, "
            "and stop at proof, blocker, or recovery notes because those marks define what must be true before trust increases."
            f"{component_hint}"
        )
    if "state" in kind_token:
        return (
            f"Read {title_token} as the allowed lifecycle. States describe what can be true; arrows describe permitted movement; "
            f"blocked or rejected states mark conditions that need proof or owner action before advancement.{component_hint}"
        )
    return (
        f"Read {title_token} as a boundary map. Start with the people, inputs, or trigger, then follow the path into "
        f"product-owned responsibilities; outside boxes are dependencies, not first-release capabilities.{component_hint}"
    )


def build_catalog_entry(
    *,
    diagram_id: str,
    slug: str,
    title: str,
    kind: str,
    owner: str,
    summary: str,
    read_guide: str,
    components: list[dict[str, str]],
    related_backlog: list[str],
    related_plans: list[str],
    related_docs: list[str],
    related_code: list[str],
    watch_paths: list[str],
    review_date: str,
) -> dict[str, object]:
    """Return the canonical Atlas catalog row for a Mermaid diagram."""

    source_mmd = f"odylith/atlas/source/{str(slug).strip()}.mmd"
    source_svg = f"odylith/atlas/source/{str(slug).strip()}.svg"
    source_png = f"odylith/atlas/source/{str(slug).strip()}.png"
    related_backlog = _unique(related_backlog)
    related_plans = _unique(related_plans)
    related_docs = _unique(related_docs)
    related_code = _unique(related_code)
    has_governance_links = bool(related_backlog and related_plans and related_docs)
    watch_paths = _unique(watch_paths)
    if not watch_paths:
        watch_paths = _unique(related_docs + related_plans + related_code)
    if not watch_paths:
        watch_paths = [source_mmd]
    entry: dict[str, object] = {
        "diagram_id": str(diagram_id).strip(),
        "slug": str(slug).strip(),
        "title": str(title).strip(),
        "kind": str(kind).strip(),
        "status": "active" if has_governance_links else "draft",
        "owner": str(owner).strip(),
        "last_reviewed_utc": str(review_date).strip(),
        "source_mmd": source_mmd,
        "source_svg": source_svg,
        "source_png": source_png,
        "change_watch_paths": watch_paths,
        "summary": str(summary).strip(),
        "read_guide": str(read_guide).strip()
        or _default_read_guide(title=str(title).strip(), kind=str(kind).strip(), components=components),
        "components": components,
        "related_backlog": related_backlog,
        "related_plans": related_plans,
        "related_docs": related_docs,
        "related_code": related_code,
    }
    if not has_governance_links:
        entry["link_state"] = "atlas_first_draft"
    return entry


def scaffold_diagram(
    *,
    repo_root: Path,
    catalog: str,
    diagram_id: str,
    slug: str,
    title: str,
    kind: str,
    owner: str,
    summary: str,
    read_guide: str,
    components: list[dict[str, str]],
    related_backlog: list[str],
    related_plans: list[str],
    related_docs: list[str],
    related_code: list[str],
    watch_paths: list[str],
    review_date: str,
    require_links: bool = False,
    starter_source: str | None = None,
    refresh: bool = True,
) -> tuple[int, list[str]]:
    """Create one Atlas catalog entry and starter Mermaid source."""

    logs: list[str] = []
    repo_root = Path(repo_root).resolve()
    catalog_path = surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=catalog)
    if not catalog_path.is_file():
        return 2, [f"FAILED: catalog not found: {catalog_path}"]

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    diagrams = payload.get("diagrams")
    if not isinstance(diagrams, list):
        return 2, [f"FAILED: malformed catalog: {catalog_path}"]

    diagram_id = str(diagram_id).strip()
    slug = str(slug).strip()

    for item in diagrams:
        if str(item.get("diagram_id", "")).strip() == diagram_id:
            return 2, [f"FAILED: diagram_id already exists: {diagram_id}"]
        if str(item.get("slug", "")).strip() == slug:
            return 2, [f"FAILED: slug already exists: {slug}"]

    entry = build_catalog_entry(
        diagram_id=diagram_id,
        slug=slug,
        title=title,
        kind=kind,
        owner=owner,
        summary=summary,
        read_guide=read_guide,
        components=components,
        related_backlog=related_backlog,
        related_plans=related_plans,
        related_docs=related_docs,
        related_code=related_code,
        watch_paths=watch_paths,
        review_date=review_date,
    )
    if require_links and str(entry.get("status", "")).strip() != "active":
        return 2, ["FAILED: radar, technical-plan, and doc links are required (at least one each)"]
    source_mmd = str(entry["source_mmd"])
    watch_paths = [str(item) for item in entry.get("change_watch_paths", []) if str(item).strip()]
    related_backlog = [str(item) for item in entry.get("related_backlog", []) if str(item).strip()]
    related_plans = [str(item) for item in entry.get("related_plans", []) if str(item).strip()]
    related_docs = [str(item) for item in entry.get("related_docs", []) if str(item).strip()]
    related_code = [str(item) for item in entry.get("related_code", []) if str(item).strip()]
    tribunal = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="atlas_diagram",
        payload={
            "diagram_id": diagram_id,
            "slug": slug,
            "title": title,
            "kind": kind,
            "owner": owner,
            "summary": summary,
            "read_guide": str(read_guide).strip(),
            "components": components,
            "related_backlog": related_backlog,
            "related_plans": related_plans,
            "related_docs": related_docs,
            "related_code": related_code,
            "watch_paths": watch_paths,
        },
    )
    try:
        artifact_tribunal.raise_for_failed_artifact_tribunal(tribunal)
    except ValueError as exc:
        return 2, [f"FAILED: {exc}"]
    diagrams.append(entry)

    catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    logs.append(f"catalog updated: {catalog_path}")
    logs.append(f"added diagram: {diagram_id} / {slug}")
    logs.append(f"validation gate: {tribunal.status}")

    source_path = surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=source_mmd)
    if source_path.exists():
        logs.append(f"source exists: {source_path}")
    else:
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_text = str(starter_source or "").strip()
        if source_text:
            source_text = source_text.rstrip() + "\n"
        else:
            source_text = _starter_source(
                title=str(title).strip(),
                owner=str(owner).strip(),
                components=components,
                watch_paths=watch_paths,
                related_backlog=related_backlog,
                related_plans=related_plans,
                related_docs=related_docs,
            )
        source_path.write_text(source_text, encoding="utf-8")
        logs.append(f"source created: {source_path}")
    if refresh:
        try:
            owned_surface_refresh.raise_for_failed_refresh(
                repo_root=repo_root,
                surface="atlas",
                operation_label="Atlas scaffold",
            )
        except RuntimeError as exc:
            logs.append(str(exc))
            return 1, logs

    return 0, logs


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        components = _parse_components(args.component)
        rc, logs = scaffold_diagram(
            repo_root=repo_root,
            catalog=str(args.catalog),
            diagram_id=str(args.diagram_id),
            slug=str(args.slug),
            title=str(args.title),
            kind=str(args.kind),
            owner=str(args.owner),
            summary=str(args.summary),
            read_guide=str(args.read_guide),
            components=components,
            related_backlog=list(args.backlog),
            related_plans=list(args.plan),
            related_docs=list(args.doc),
            related_code=list(args.code),
            watch_paths=list(args.watch),
            review_date=str(args.review_date),
            require_links=bool(args.require_links),
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    for line in logs:
        print(line)
    if rc != 0:
        return rc

    owned_surface_refresh.print_dashboard_handoff(
        surface="atlas",
        diagram=str(args.diagram_id).strip(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

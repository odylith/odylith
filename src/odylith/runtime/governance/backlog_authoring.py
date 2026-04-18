from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common import repo_path_resolver
from odylith.runtime.governance import backlog_title_contract
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.governance import validate_backlog_contract as backlog_contract

_WORKSTREAM_RE = re.compile(r"^B-(\d{3,})$")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_DEFAULT_PRIORITY = "P1"
_DEFAULT_SIZING = "M"
_DEFAULT_COMPLEXITY = "Medium"
_DEFAULT_CONFIDENCE = "medium"
_RADAR_BACKLOG_INDEX_RELATIVE = Path("odylith/radar/source/INDEX.md")
_RADAR_IDEAS_ROOT_RELATIVE = Path("odylith/radar/source/ideas")


@dataclass(frozen=True)
class CreatedBacklogItem:
    idea_id: str
    title: str
    idea_path: Path
    ordering_score: int
    founder_override: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "idea_id": self.idea_id,
            "title": self.title,
            "idea_path": str(self.idea_path.resolve()),
            "ordering_score": self.ordering_score,
            "founder_override": self.founder_override,
        }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith backlog create",
        description=(
            "Create one or more queued backlog workstreams with grounded core detail "
            "and patch Radar INDEX.md automatically."
        ),
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--backlog-index", default="odylith/radar/source/INDEX.md")
    parser.add_argument("--ideas-root", default="odylith/radar/source/ideas")
    parser.add_argument("--title", action="append", dest="titles", required=True)
    parser.add_argument("--problem", required=True, help="Grounded Problem section text.")
    parser.add_argument("--customer", required=True, help="Grounded Customer section text.")
    parser.add_argument("--opportunity", required=True, help="Grounded Opportunity section text.")
    parser.add_argument("--product-view", required=True, help="Grounded Product View section text.")
    parser.add_argument("--success-metrics", required=True, help="Grounded Success Metrics section text.")
    parser.add_argument("--priority", default=_DEFAULT_PRIORITY)
    parser.add_argument("--commercial-value", type=int, default=3)
    parser.add_argument("--product-impact", type=int, default=3)
    parser.add_argument("--market-value", type=int, default=3)
    parser.add_argument("--impacted-lanes", default="", help=argparse.SUPPRESS)
    parser.add_argument("--impacted-parts", default="odylith")
    parser.add_argument("--sizing", default=_DEFAULT_SIZING)
    parser.add_argument("--complexity", default=_DEFAULT_COMPLEXITY)
    parser.add_argument("--ordering-score", type=int, default=None)
    parser.add_argument(
        "--ordering-rationale",
        default="Queued through `odylith backlog create` from the current maintainer lane.",
    )
    parser.add_argument("--confidence", default=_DEFAULT_CONFIDENCE)
    parser.add_argument("--founder-override", action="store_true")
    parser.add_argument("--override-note", default="")
    parser.add_argument("--override-review-date", default="")
    parser.add_argument(
        "--release",
        default="",
        help="Optional release selector such as `next` or `release-0-1-12` for the newly created queued records.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    return repo_path_resolver.resolve_repo_path(repo_root=repo_root, value=token)


def _repo_relative_posix(*, repo_root: Path, path: Path) -> str:
    return repo_path_resolver.display_repo_path(repo_root=repo_root, value=path)


def _backlog_link(*, repo_root: Path, path: Path, label: str) -> str:
    return f"[{str(label).strip()}]({_repo_relative_posix(repo_root=repo_root, path=path)})"


def _resolve_governed_radar_paths(
    *,
    repo_root: Path,
    backlog_index_path: Path,
    ideas_root: Path,
) -> tuple[Path, Path]:
    canonical_backlog_index = (repo_root / _RADAR_BACKLOG_INDEX_RELATIVE).resolve()
    canonical_ideas_root = (repo_root / _RADAR_IDEAS_ROOT_RELATIVE).resolve()
    resolved_backlog_index = Path(backlog_index_path).expanduser().resolve()
    resolved_ideas_root = Path(ideas_root).expanduser().resolve()
    if resolved_backlog_index != canonical_backlog_index:
        raise ValueError(
            f"--backlog-index must resolve to `{_RADAR_BACKLOG_INDEX_RELATIVE.as_posix()}` inside the repo root"
        )
    if resolved_ideas_root != canonical_ideas_root:
        raise ValueError(
            f"--ideas-root must resolve to `{_RADAR_IDEAS_ROOT_RELATIVE.as_posix()}` inside the repo root"
        )
    return resolved_backlog_index, resolved_ideas_root


def _slugify(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    token = token.strip("-")
    return token or "workstream"


def _next_workstream_id(ideas: Mapping[str, backlog_contract.IdeaSpec]) -> str:
    max_id = 0
    for idea_id in ideas:
        match = _WORKSTREAM_RE.fullmatch(str(idea_id).strip().upper())
        if not match:
            continue
        max_id = max(max_id, int(match.group(1)))
    return f"B-{max_id + 1:03d}"


def _parse_metadata_and_sections(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    metadata: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    in_metadata = True
    current_section: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        section_match = _SECTION_RE.match(raw_line)
        if section_match:
            in_metadata = False
            current_section = str(section_match.group(1)).strip()
            sections.setdefault(current_section, [])
            continue
        if in_metadata:
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
            continue
        if current_section is not None:
            sections.setdefault(current_section, []).append(raw_line)
    return metadata, {key: "\n".join(lines).strip() for key, lines in sections.items()}


def _render_idea_text(*, metadata: Mapping[str, str], sections: Mapping[str, str]) -> str:
    ordered_metadata_keys = (
        "status",
        "idea_id",
        "title",
        "date",
        "priority",
        "commercial_value",
        "product_impact",
        "market_value",
        "impacted_parts",
        "sizing",
        "complexity",
        "ordering_score",
        "ordering_rationale",
        "confidence",
        "founder_override",
        "promoted_to_plan",
        execution_wave_contract.EXECUTION_MODEL_FIELD,
        "workstream_type",
        "workstream_parent",
        "workstream_children",
        "workstream_depends_on",
        "workstream_blocks",
        "related_diagram_ids",
        "workstream_reopens",
        "workstream_reopened_by",
        "workstream_split_from",
        "workstream_split_into",
        "workstream_merged_into",
        "workstream_merged_from",
        "supersedes",
        "superseded_by",
    )
    lines: list[str] = []
    for key in ordered_metadata_keys:
        lines.append(f"{key}: {str(metadata.get(key, '')).strip()}")
        lines.append("")
    for section in backlog_contract._REQUIRED_SECTIONS:
        lines.append(f"## {section}")
        lines.append(str(sections.get(section, "")).strip() or "TBD.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _split_table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.split("|")[1:-1]]


def _format_table_row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(str(item).strip() for item in cells) + " |"


def _find_section_bounds(lines: list[str], title: str) -> tuple[int, int]:
    start = -1
    for index, line in enumerate(lines):
        if line.strip() == title:
            start = index
            break
    if start == -1:
        return -1, -1
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return start, end


def _collect_table_row_indexes(lines: list[str], *, section_start: int, section_end: int) -> list[int]:
    row_indexes: list[int] = []
    for index in range(section_start, section_end):
        stripped = lines[index].strip()
        if not stripped.startswith("|") or stripped.startswith("| ---"):
            continue
        cells = _split_table_cells(stripped)
        if len(cells) != len(backlog_contract._INDEX_COLS):
            continue
        if cells[0].lower() == "rank" and cells[1].lower() == "idea_id":
            continue
        row_indexes.append(index)
    return row_indexes


def _update_backlog_last_updated(content: str, *, today: dt.date) -> str:
    return re.sub(
        r"(?m)^Last updated \(UTC\):\s*\d{4}-\d{2}-\d{2}\s*$",
        f"Last updated (UTC): {today.isoformat()}",
        content,
        count=1,
    )


def _default_sections_for_title(title: str) -> dict[str, str]:
    return backlog_contract.default_section_boilerplate(title)


def _grounded_sections_for_title(*, title: str, args: argparse.Namespace) -> dict[str, str]:
    sections = dict(_default_sections_for_title(title))
    sections["Problem"] = str(args.problem).strip()
    sections["Customer"] = str(args.customer).strip()
    sections["Opportunity"] = str(args.opportunity).strip()
    sections["Product View"] = str(args.product_view).strip()
    sections["Success Metrics"] = str(args.success_metrics).strip()
    validation_errors = backlog_contract.core_detail_section_errors(
        title=title,
        sections=sections,
        path=Path("<generated>"),
    )
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    return sections


def _build_metadata(
    *,
    idea_id: str,
    title: str,
    today: dt.date,
    args: argparse.Namespace,
) -> dict[str, str]:
    payload = {
        "status": "queued",
        "idea_id": idea_id,
        "title": str(title).strip(),
        "date": today.isoformat(),
        "priority": str(args.priority).strip(),
        "commercial_value": str(int(args.commercial_value)),
        "product_impact": str(int(args.product_impact)),
        "market_value": str(int(args.market_value)),
        "impacted_parts": str(args.impacted_parts).strip(),
        "sizing": str(args.sizing).strip(),
        "complexity": str(args.complexity).strip(),
        "ordering_score": "",
        "ordering_rationale": str(args.ordering_rationale).strip(),
        "confidence": str(args.confidence).strip(),
        "founder_override": "yes" if bool(args.founder_override) else "no",
        "promoted_to_plan": "",
        execution_wave_contract.EXECUTION_MODEL_FIELD: execution_wave_contract.EXECUTION_MODEL_STANDARD,
        "workstream_type": "standalone",
        "workstream_parent": "",
        "workstream_children": "",
        "workstream_depends_on": "",
        "workstream_blocks": "",
        "related_diagram_ids": "",
        "workstream_reopens": "",
        "workstream_reopened_by": "",
        "workstream_split_from": "",
        "workstream_split_into": "",
        "workstream_merged_into": "",
        "workstream_merged_from": "",
        "supersedes": "",
        "superseded_by": "",
    }
    validation_errors: list[str] = []
    computed_score = backlog_contract._compute_score(payload, errors=validation_errors, path=Path("<generated>"))
    if validation_errors or computed_score is None:
        raise ValueError("; ".join(validation_errors) or "could not compute backlog ordering score")
    declared_score = int(args.ordering_score) if args.ordering_score is not None else int(computed_score)
    if declared_score != computed_score and not bool(args.founder_override):
        raise ValueError(
            f"ordering_score override `{declared_score}` requires --founder-override because the computed score is `{computed_score}`"
        )
    payload["ordering_score"] = str(declared_score)
    return payload


def _build_rationale_lines(
    *,
    item: CreatedBacklogItem,
    override_note: str,
    override_review_date: str,
) -> list[str]:
    cost_line = "- tradeoff: queued with sizing and complexity assumptions that should be validated when implementation begins."
    if item.founder_override:
        note = override_note or "Manual priority override applied to keep this workstream in a deliberate queue position."
        return [
            f"- why now: created as a new queued workstream for {item.title}.",
            "- expected outcome: clearer product truth and faster follow-on implementation planning.",
            cost_line,
            "- deferred for now: deeper scope decomposition waits until the implementation owner starts the workstream.",
            f"- ranking basis: {note} Review checkpoint: {override_review_date}.",
        ]
    return [
        f"- why now: created as a new queued workstream for {item.title}.",
        "- expected outcome: clearer product truth and faster follow-on implementation planning.",
        cost_line,
        "- deferred for now: deeper scope decomposition waits until the implementation owner starts the workstream.",
        "- ranking basis: score-based rank; no manual priority override.",
    ]


def _unique_idea_path(*, ideas_root: Path, title: str, today: dt.date, reserved: set[Path]) -> Path:
    month_dir = ideas_root / today.isoformat()[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    base_slug = _slugify(title)
    candidate = month_dir / f"{today.isoformat()}-{base_slug}.md"
    suffix = 2
    while candidate.exists() or candidate in reserved:
        candidate = month_dir / f"{today.isoformat()}-{base_slug}-{suffix}.md"
        suffix += 1
    return candidate


def _preserved_reorder_sections(
    snapshot: Mapping[str, Any],
    *,
    active_ids: set[str],
) -> list[tuple[str, str, list[str]]]:
    sections_payload = snapshot.get("reorder_sections", {})
    preserved: list[tuple[str, str, list[str]]] = []
    if not isinstance(sections_payload, Mapping):
        return preserved
    for key, value in sections_payload.items():
        if str(key) in active_ids or not isinstance(value, Mapping):
            continue
        preserved.append(
            (
                str(key),
                str(value.get("heading", "")).strip(),
                [str(line) for line in value.get("lines", [])] if isinstance(value.get("lines"), list) else [],
            )
        )
    return preserved


def _rewrite_active_backlog_section(
    *,
    backlog_index_path: Path,
    active_rows: Sequence[Sequence[str]],
    reorder_sections: Sequence[tuple[str, str, list[str]]],
    today: dt.date,
) -> str:
    lines = backlog_index_path.read_text(encoding="utf-8").splitlines()
    active_start, active_end = _find_section_bounds(lines, "## Ranked Active Backlog")
    if active_start == -1:
        raise ValueError("missing `## Ranked Active Backlog` section in odylith/radar/source/INDEX.md")
    row_indexes = _collect_table_row_indexes(lines, section_start=active_start, section_end=active_end)
    if row_indexes:
        first_row = row_indexes[0]
        del lines[first_row : row_indexes[-1] + 1]
        for offset, row in enumerate(active_rows):
            lines.insert(first_row + offset, _format_table_row(row))
    else:
        insert_at = active_start + 4
        for offset, row in enumerate(active_rows):
            lines.insert(insert_at + offset, _format_table_row(row))

    rationale_start, rationale_end = _find_section_bounds(lines, "## Reorder Rationale Log")
    if rationale_start == -1:
        raise ValueError("missing `## Reorder Rationale Log` section in odylith/radar/source/INDEX.md")
    replacement = ["## Reorder Rationale Log", ""]
    for _idea_id, heading, rationale_lines in reorder_sections:
        replacement.append(f"### {heading}")
        replacement.extend(
            rationale_lines
            or [
                "- why now: rationale missing.",
                "- expected outcome: TBD.",
                "- tradeoff: TBD.",
                "- deferred for now: TBD.",
                "- ranking basis: score-based rank; no manual priority override.",
            ]
        )
        replacement.append("")
    lines[rationale_start:rationale_end] = replacement

    content = "\n".join(lines)
    content = _update_backlog_last_updated(content, today=today)
    if not content.endswith("\n"):
        content += "\n"
    return content


def create_queued_backlog_items(
    *,
    repo_root: Path,
    backlog_index_path: Path,
    ideas_root: Path,
    titles: Sequence[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    backlog_index_path, ideas_root = _resolve_governed_radar_paths(
        repo_root=repo_root,
        backlog_index_path=backlog_index_path,
        ideas_root=ideas_root,
    )
    ideas, idea_errors = backlog_contract._validate_idea_specs(ideas_root, repo_root=repo_root)
    if idea_errors:
        raise ValueError("; ".join(idea_errors))
    _, _, _, _, _, index_errors = backlog_contract._validate_backlog_index(
        backlog_index=backlog_index_path,
        ideas=ideas,
        repo_root=repo_root,
    )
    if index_errors:
        raise ValueError("; ".join(index_errors))

    snapshot = backlog_contract.load_backlog_index_snapshot(backlog_index_path)
    active_rows = backlog_contract.rows_as_mapping(
        section=snapshot.get("active", {}),
        expected_headers=backlog_contract._INDEX_COLS,
    )
    today = dt.datetime.now(tz=dt.UTC).date()
    override_review_date = str(args.override_review_date or "").strip()
    if bool(args.founder_override) and not override_review_date:
        raise ValueError("--override-review-date is required when --founder-override is set")

    created_items: list[CreatedBacklogItem] = []
    new_text_by_path: dict[Path, str] = {}
    mutable_ideas = dict(ideas)
    reserved_paths: set[Path] = set()
    for raw_title in titles:
        title = backlog_title_contract.normalize_workstream_title(
            title=str(raw_title).strip(),
            repo_root=repo_root,
        )
        if not title:
            raise ValueError("backlog titles must be non-empty")
        idea_id = _next_workstream_id(mutable_ideas)
        metadata = _build_metadata(idea_id=idea_id, title=title, today=today, args=args)
        idea_path = _unique_idea_path(ideas_root=ideas_root, title=title, today=today, reserved=reserved_paths)
        reserved_paths.add(idea_path)
        sections = _grounded_sections_for_title(title=title, args=args)
        text = _render_idea_text(metadata=metadata, sections=sections)
        new_text_by_path[idea_path] = text
        item = CreatedBacklogItem(
            idea_id=idea_id,
            title=title,
            idea_path=idea_path,
            ordering_score=int(metadata["ordering_score"]),
            founder_override=bool(args.founder_override),
        )
        created_items.append(item)
        mutable_ideas[idea_id] = backlog_contract.IdeaSpec(
            path=idea_path,
            metadata=metadata,
            sections=set(sections),
            section_bodies=dict(sections),
        )

    row_records: list[dict[str, Any]] = []
    for ordinal, row in enumerate(active_rows):
        row_records.append(
            {
                "idea_id": str(row["idea_id"]).strip(),
                "title": str(row["title"]).strip(),
                "priority": str(row["priority"]).strip(),
                "ordering_score": int(str(row["ordering_score"]).strip()),
                "commercial_value": str(row["commercial_value"]).strip(),
                "product_impact": str(row["product_impact"]).strip(),
                "market_value": str(row["market_value"]).strip(),
                "sizing": str(row["sizing"]).strip(),
                "complexity": str(row["complexity"]).strip(),
                "status": "queued",
                "link": str(row["link"]).strip(),
                "existing_order": ordinal,
                "is_new": False,
            }
        )
    for ordinal, item in enumerate(created_items, start=len(row_records)):
        metadata = _build_metadata(idea_id=item.idea_id, title=item.title, today=today, args=args)
        row_records.append(
            {
                "idea_id": item.idea_id,
                "title": item.title,
                "priority": metadata["priority"],
                "ordering_score": int(metadata["ordering_score"]),
                "commercial_value": metadata["commercial_value"],
                "product_impact": metadata["product_impact"],
                "market_value": metadata["market_value"],
                "sizing": metadata["sizing"],
                "complexity": metadata["complexity"],
                "status": "queued",
                "link": _backlog_link(
                    repo_root=repo_root,
                    path=item.idea_path,
                    label=_slugify(item.title),
                ),
                "existing_order": ordinal,
                "is_new": True,
            }
        )
    row_records.sort(
        key=lambda row: (
            -int(row["ordering_score"]),
            1 if bool(row["is_new"]) else 0,
            int(row["existing_order"]),
            str(row["idea_id"]),
        )
    )
    formatted_rows: list[list[str]] = []
    active_ids = {str(row["idea_id"]).strip() for row in row_records}
    rationale_sections: list[tuple[str, str, list[str]]] = []
    existing_reorder = {
        str(key): (
            str(value.get("heading", "")).strip(),
            [str(line) for line in value.get("lines", [])] if isinstance(value, Mapping) and isinstance(value.get("lines"), list) else [],
        )
        for key, value in dict(snapshot.get("reorder_sections", {})).items()
        if isinstance(snapshot.get("reorder_sections"), Mapping) and isinstance(value, Mapping)
    }
    for rank, row in enumerate(row_records, start=1):
        idea_id = str(row["idea_id"]).strip()
        formatted_rows.append(
            [
                str(rank),
                idea_id,
                str(row["title"]).strip(),
                str(row["priority"]).strip(),
                str(row["ordering_score"]).strip(),
                str(row["commercial_value"]).strip(),
                str(row["product_impact"]).strip(),
                str(row["market_value"]).strip(),
                str(row["sizing"]).strip(),
                str(row["complexity"]).strip(),
                "queued",
                str(row["link"]).strip(),
            ]
        )
        if idea_id in existing_reorder:
            _existing_heading, existing_lines = existing_reorder[idea_id]
            rationale_sections.append((idea_id, f"{idea_id} (rank {rank})", existing_lines))
            continue
        created = next(item for item in created_items if item.idea_id == idea_id)
        rationale_sections.append(
            (
                idea_id,
                f"{idea_id} (rank {rank})",
                _build_rationale_lines(
                    item=created,
                    override_note=str(args.override_note or "").strip(),
                    override_review_date=override_review_date,
                ),
            )
        )
    rationale_sections.extend(_preserved_reorder_sections(snapshot, active_ids=active_ids))
    updated_index_text = _rewrite_active_backlog_section(
        backlog_index_path=backlog_index_path,
        active_rows=formatted_rows,
        reorder_sections=rationale_sections,
        today=today,
    )

    return {
        "created": [item.as_dict() for item in created_items],
        "backlog_index": str(backlog_index_path.resolve()),
        "backlog_index_text": updated_index_text,
        "idea_files": {str(path.resolve()): text for path, text in new_text_by_path.items()},
        "_candidate_idea_specs": mutable_ideas,
    }


def _release_assignment_note(*, selector: str) -> str:
    return (
        "Target newly created queued backlog record(s) from "
        f"`odylith backlog create --release {str(selector).strip()}`."
    )


def _refresh_status(*, surface: str, status: str, detail: str = "") -> dict[str, str]:
    payload = {"surface": surface, "status": status}
    if str(detail).strip():
        payload["detail"] = str(detail).strip()
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    release_selector = str(args.release or "").strip()
    try:
        backlog_index_path, ideas_root = _resolve_governed_radar_paths(
            repo_root=repo_root,
            backlog_index_path=_resolve(repo_root, str(args.backlog_index)),
            ideas_root=_resolve(repo_root, str(args.ideas_root)),
        )
        result = create_queued_backlog_items(
            repo_root=repo_root,
            backlog_index_path=backlog_index_path,
            ideas_root=ideas_root,
            titles=tuple(str(title) for title in args.titles),
            args=args,
        )
        release_targeting = None
        if release_selector:
            release_targeting = release_planning_authoring.add_workstreams_to_release(
                repo_root=repo_root,
                workstream_ids=[str(item["idea_id"]) for item in result["created"]],
                selector=release_selector,
                note=_release_assignment_note(selector=release_selector),
                idea_specs=result["_candidate_idea_specs"],
                dry_run=True,
            )
    except ValueError as exc:
        print(str(exc))
        return 2

    radar_refresh = _refresh_status(
        surface="radar",
        status="skipped" if bool(args.dry_run) else "pending",
        detail="dry-run" if bool(args.dry_run) else "",
    )
    compass_refresh = _refresh_status(
        surface="compass",
        status="skipped" if release_selector else "not_requested",
        detail="dry-run" if bool(args.dry_run) and release_selector else "",
    )

    if not bool(args.dry_run):
        for raw_path, text in result["idea_files"].items():
            Path(raw_path).write_text(str(text), encoding="utf-8")
        backlog_index_path.write_text(str(result["backlog_index_text"]), encoding="utf-8")
        if release_selector:
            try:
                release_targeting = release_planning_authoring.add_workstreams_to_release(
                    repo_root=repo_root,
                    workstream_ids=[str(item["idea_id"]) for item in result["created"]],
                    selector=release_selector,
                    note=_release_assignment_note(selector=release_selector),
                    idea_specs=result["_candidate_idea_specs"],
                    dry_run=False,
                )
            except ValueError as exc:
                print(f"Backlog create wrote queued records, but release targeting failed unexpectedly: {exc}")
                return 1
        try:
            owned_surface_refresh.raise_for_failed_refresh(
                repo_root=repo_root,
                surface="radar",
                operation_label="Backlog create",
            )
            radar_refresh = _refresh_status(surface="radar", status="passed")
        except RuntimeError as exc:
            print(str(exc))
            return 1
        if release_selector:
            try:
                owned_surface_refresh.raise_for_failed_refresh(
                    repo_root=repo_root,
                    surface="compass",
                    operation_label="Backlog create release targeting",
                )
                compass_refresh = _refresh_status(surface="compass", status="passed")
            except RuntimeError as exc:
                print(str(exc))
                return 1

    release_payload = {
        "selector": release_selector,
        "release_id": "none",
        "display_label": "none",
        "events": [],
    }
    if release_targeting is not None:
        release_row = release_targeting.get("release", {})
        release_payload = {
            "selector": release_selector,
            "release_id": str(release_row.get("release_id", "")).strip(),
            "display_label": str(release_row.get("display_label", "")).strip(),
            "events": release_targeting.get("events", []),
            "event_log_path": release_targeting.get("event_log_path", ""),
        }

    if bool(args.as_json):
        payload = {
            "created": result["created"],
            "created_ids": [str(item["idea_id"]) for item in result["created"]],
            "backlog_index": result["backlog_index"],
            "dry_run": bool(args.dry_run),
            "release_target": release_payload,
            "queued_status_preserved": True,
            "refresh": {
                "radar": radar_refresh,
                "compass": compass_refresh,
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        mode = "dry-run" if bool(args.dry_run) else "created"
        print(f"odylith backlog create {mode}")
        for item in result["created"]:
            print(f"- {item['idea_id']}: {item['title']} -> {item['idea_path']}")
        print(f"- backlog_index: {result['backlog_index']}")
        print(f"- created_ids: {', '.join(str(item['idea_id']) for item in result['created'])}")
        print(f"- release_target: {release_payload['release_id'] or 'none'}")
        print("- queued_status_preserved: yes")
        print(f"- radar_refresh: {radar_refresh['status']}")
        print(f"- compass_refresh: {compass_refresh['status']}")
    return 0

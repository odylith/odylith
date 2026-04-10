"""Reconcile odylith/technical-plans/workstream bindings for new or touched active plans.

This command is intentionally conservative and deterministic:
- scope is limited to touched/new active plans,
- queued links are promoted to planning and moved into execution table,
- finished links are rebound through a new successor workstream,
- all writes occur in canonical markdown sources.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.common import log_compass_timeline_event as timeline_logger
from odylith.runtime.governance import validate_backlog_contract as backlog_contract

_WORKSTREAM_RE = re.compile(r"^B-(\d{3,})$")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_BACKLOG_ROW_COL_COUNT = len(backlog_contract._INDEX_COLS)
_BACKLOG_STATUS_COL_INDEX = backlog_contract._INDEX_COLS.index("status")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Reconcile touched active plan bindings against workstream lifecycle rules.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--plan-index", default="odylith/technical-plans/INDEX.md")
    parser.add_argument("--backlog-index", default="odylith/radar/source/INDEX.md")
    parser.add_argument("--ideas-root", default="odylith/radar/source/ideas")
    parser.add_argument("--stream", default=agent_runtime_contract.AGENT_STREAM_PATH)
    parser.add_argument("--author", default="sync")
    parser.add_argument("--source", default="sync")
    parser.add_argument("changed_paths", nargs="*")
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _replace_metadata_value(text: str, *, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^(?P<key>{re.escape(key)}):\s*(?P<value>.*)$")

    def _replacement(match: re.Match[str]) -> str:
        return f"{match.group('key')}: {str(value).strip()}"

    updated, count = pattern.subn(_replacement, text, count=1)
    if count == 0:
        raise ValueError(f"missing metadata key `{key}`")
    return updated


def _split_ids(raw: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for token in str(raw or "").replace(";", ",").split(","):
        ws = token.strip().upper()
        if not ws or ws in {"NONE", "-"}:
            continue
        if not _WORKSTREAM_RE.fullmatch(ws):
            continue
        if ws in seen:
            continue
        seen.add(ws)
        values.append(ws)
    return values


def _join_ids(values: Sequence[str]) -> str:
    return ",".join(sorted(set(str(token).strip().upper() for token in values if str(token).strip())))


def _next_workstream_id(ideas: Mapping[str, backlog_contract.IdeaSpec]) -> str:
    max_id = 0
    for idea_id in ideas:
        match = _WORKSTREAM_RE.fullmatch(str(idea_id).strip().upper())
        if not match:
            continue
        max_id = max(max_id, int(match.group(1)))
    return f"B-{max_id + 1:03d}"


def _slugify(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    token = token.strip("-")
    return token or "workstream"


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

    normalized_sections = {
        key: "\n".join(lines).strip() for key, lines in sections.items()
    }
    return metadata, normalized_sections


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
        "execution_model",
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
        value = str(metadata.get(key, "")).strip()
        lines.append(f"{key}: {value}")
        lines.append("")

    required_sections = backlog_contract._REQUIRED_SECTIONS
    for section in required_sections:
        lines.append(f"## {section}")
        body = str(sections.get(section, "")).strip()
        lines.append(body or "TBD.")
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    return text


def _split_table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.split("|")[1:-1]]


def _format_table_row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(str(item).strip() for item in cells) + " |"


def _find_section_bounds(lines: list[str], title: str) -> tuple[int, int]:
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == title:
            start = idx
            break
    if start == -1:
        return -1, -1
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return start, end


def _collect_table_row_indexes(lines: list[str], *, section_start: int, section_end: int) -> list[int]:
    row_indexes: list[int] = []
    for idx in range(section_start, section_end):
        stripped = lines[idx].strip()
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("| ---"):
            continue
        cells = _split_table_cells(stripped)
        if len(cells) != _BACKLOG_ROW_COL_COUNT:
            continue
        if cells[0].lower() == "rank" and cells[1].lower() == "idea_id":
            continue
        row_indexes.append(idx)
    return row_indexes


def _update_backlog_last_updated(content: str, *, today: dt.date) -> str:
    return re.sub(
        r"(?m)^Last updated \(UTC\):\s*\d{4}-\d{2}-\d{2}\s*$",
        f"Last updated (UTC): {today.isoformat()}",
        content,
        count=1,
    )


def _append_execution_row(backlog_index_path: Path, *, row_cells: Sequence[str], today: dt.date) -> None:
    lines = backlog_index_path.read_text(encoding="utf-8").splitlines()
    exec_start, exec_end = _find_section_bounds(lines, "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)")
    if exec_start == -1:
        raise ValueError("missing execution section in odylith/radar/source/INDEX.md")

    row_indexes = _collect_table_row_indexes(lines, section_start=exec_start, section_end=exec_end)
    insert_at = exec_end
    if row_indexes:
        insert_at = row_indexes[-1] + 1
    line = _format_table_row(row_cells)
    lines.insert(insert_at, line)

    content = "\n".join(lines)
    content = backlog_authoring._update_backlog_last_updated(content, today=today)
    if not content.endswith("\n"):
        content += "\n"
    backlog_index_path.write_text(content, encoding="utf-8")


def _move_active_row_to_execution_status(
    backlog_index_path: Path,
    *,
    idea_id: str,
    status: str,
    today: dt.date,
) -> bool:
    normalized_status = str(status or "").strip().lower()
    if normalized_status not in {"planning", "implementation"}:
        raise ValueError(f"unsupported execution status `{status}`")

    lines = backlog_index_path.read_text(encoding="utf-8").splitlines()

    active_start, active_end = _find_section_bounds(lines, "## Ranked Active Backlog")
    exec_start, exec_end = _find_section_bounds(lines, "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)")
    if active_start == -1 or exec_start == -1:
        raise ValueError("missing required backlog index sections")

    active_rows = _collect_table_row_indexes(lines, section_start=active_start, section_end=active_end)
    target_idx = -1
    target_cells: list[str] = []
    for idx in active_rows:
        cells = _split_table_cells(lines[idx].strip())
        if len(cells) == _BACKLOG_ROW_COL_COUNT and cells[1] == idea_id:
            target_idx = idx
            target_cells = cells
            break
    if target_idx == -1:
        return False

    del lines[target_idx]

    # Recompute active rank sequence.
    active_start, active_end = _find_section_bounds(lines, "## Ranked Active Backlog")
    active_rows = _collect_table_row_indexes(lines, section_start=active_start, section_end=active_end)
    next_rank = 1
    for idx in active_rows:
        cells = _split_table_cells(lines[idx].strip())
        if len(cells) != _BACKLOG_ROW_COL_COUNT:
            continue
        cells[0] = str(next_rank)
        next_rank += 1
        lines[idx] = _format_table_row(cells)

    target_cells[0] = "-"
    target_cells[_BACKLOG_STATUS_COL_INDEX] = normalized_status

    exec_start, exec_end = _find_section_bounds(lines, "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)")
    exec_rows = _collect_table_row_indexes(lines, section_start=exec_start, section_end=exec_end)
    insert_at = exec_end
    if exec_rows:
        insert_at = exec_rows[-1] + 1
    lines.insert(insert_at, _format_table_row(target_cells))

    content = "\n".join(lines)
    content = backlog_authoring._update_backlog_last_updated(content, today=today)
    if not content.endswith("\n"):
        content += "\n"
    backlog_index_path.write_text(content, encoding="utf-8")
    return True


def _update_plan_index_backlog(plan_index_path: Path, *, plan_path: str, backlog_id: str) -> bool:
    lines = plan_index_path.read_text(encoding="utf-8").splitlines()
    active_start, active_end = _find_section_bounds(lines, "## Active Plans")
    if active_start == -1:
        raise ValueError("missing `## Active Plans` section in odylith/technical-plans/INDEX.md")

    changed = False
    for idx in range(active_start, active_end):
        stripped = lines[idx].strip()
        if not stripped.startswith("|") or stripped.startswith("| ---"):
            continue
        cells = _split_table_cells(stripped)
        if len(cells) != 5:
            continue
        if cells[0].strip("`").strip() != plan_path:
            continue
        if cells[4].strip("`").strip() == backlog_id:
            return False
        cells[4] = f"`{backlog_id}`"
        lines[idx] = _format_table_row(cells)
        changed = True
        break

    if changed:
        text = "\n".join(lines)
        text = backlog_authoring._update_backlog_last_updated(text, today=dt.datetime.now(dt.timezone.utc).date())
        if not text.endswith("\n"):
            text += "\n"
        plan_index_path.write_text(text, encoding="utf-8")
    return changed


def _build_successor_metadata(
    *,
    source_metadata: Mapping[str, str],
    source_id: str,
    successor_id: str,
    plan_path: str,
    today: dt.date,
) -> dict[str, str]:
    title = str(source_metadata.get("title", "")).strip() or source_id
    successor_title = f"{title} Successor Execution Continuation"

    metadata: dict[str, str] = {
        "status": "planning",
        "idea_id": successor_id,
        "title": successor_title,
        "date": today.isoformat(),
        "priority": str(source_metadata.get("priority", "P1")).strip() or "P1",
        "commercial_value": str(source_metadata.get("commercial_value", "3")).strip() or "3",
        "product_impact": str(source_metadata.get("product_impact", "3")).strip() or "3",
        "market_value": str(source_metadata.get("market_value", "3")).strip() or "3",
        "impacted_parts": str(source_metadata.get("impacted_parts", "")).strip(),
        "sizing": str(source_metadata.get("sizing", "M")).strip() or "M",
        "complexity": str(source_metadata.get("complexity", "Medium")).strip() or "Medium",
        "ordering_score": str(source_metadata.get("ordering_score", "0")).strip() or "0",
        "ordering_rationale": (
            "Successor continuation required for net-new implementation demand while preserving closed lineage context."
        ),
        "confidence": str(source_metadata.get("confidence", "medium")).strip() or "medium",
        "founder_override": str(source_metadata.get("founder_override", "no")).strip() or "no",
        "promoted_to_plan": plan_path,
        "execution_model": str(source_metadata.get("execution_model", "standard")).strip() or "standard",
        "workstream_type": str(source_metadata.get("workstream_type", "standalone")).strip() or "standalone",
        "workstream_parent": str(source_metadata.get("workstream_parent", "")).strip(),
        "workstream_children": "",
        "workstream_depends_on": _join_ids(
            [
                *_split_ids(str(source_metadata.get("workstream_depends_on", ""))),
                source_id,
            ]
        ),
        "workstream_blocks": "",
        "related_diagram_ids": str(source_metadata.get("related_diagram_ids", "")).strip(),
        "workstream_reopens": source_id,
        "workstream_reopened_by": "",
        "workstream_split_from": "",
        "workstream_split_into": "",
        "workstream_merged_into": "",
        "workstream_merged_from": "",
        "supersedes": "",
        "superseded_by": "",
    }
    return metadata


def _create_successor_workstream(
    *,
    repo_root: Path,
    ideas_root: Path,
    backlog_index_path: Path,
    source_spec: backlog_contract.IdeaSpec,
    successor_id: str,
    plan_path: str,
) -> governance.SuccessorCreationResult:
    today = dt.datetime.now(dt.timezone.utc).date()
    source_metadata, source_sections = backlog_authoring._parse_metadata_and_sections(source_spec.path)

    successor_metadata = _build_successor_metadata(
        source_metadata=source_metadata,
        source_id=source_spec.idea_id,
        successor_id=successor_id,
        plan_path=plan_path,
        today=today,
    )

    source_title = str(source_metadata.get("title", source_spec.idea_id)).strip()
    source_problem = str(source_sections.get("Problem", "")).strip()
    source_sections = dict(source_sections)
    source_sections["Problem"] = (
        f"{source_title} was closed but net-new execution demand requires successor continuation under a new workstream id."
        + (f"\n\n{source_problem}" if source_problem else "")
    )

    month_dir = ideas_root / today.isoformat()[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    base_slug = backlog_authoring._slugify(f"{source_title}-successor-execution-continuation")
    candidate = month_dir / f"{today.isoformat()}-{base_slug}.md"
    suffix = 2
    while candidate.exists():
        candidate = month_dir / f"{today.isoformat()}-{base_slug}-v{suffix}.md"
        suffix += 1

    candidate.write_text(
        backlog_authoring._render_idea_text(metadata=successor_metadata, sections=source_sections),
        encoding="utf-8",
    )

    source_text = source_spec.path.read_text(encoding="utf-8")
    existing_reopened_by = str(source_spec.metadata.get("workstream_reopened_by", "")).strip()
    if existing_reopened_by and existing_reopened_by != successor_id:
        raise ValueError(
            f"{source_spec.path}: existing `workstream_reopened_by` `{existing_reopened_by}` conflicts with successor `{successor_id}`"
        )
    source_updated = _replace_metadata_value(
        source_text,
        key="workstream_reopened_by",
        value=successor_id,
    )
    source_spec.path.write_text(source_updated, encoding="utf-8")

    row_cells = [
        "-",
        successor_id,
        successor_metadata["title"],
        successor_metadata["priority"],
        successor_metadata["ordering_score"],
        successor_metadata["commercial_value"],
        successor_metadata["product_impact"],
        successor_metadata["market_value"],
        successor_metadata["sizing"],
        successor_metadata["complexity"],
        "planning",
        backlog_authoring._backlog_link(
            repo_root=repo_root,
            path=candidate,
            label=backlog_authoring._slugify(base_slug),
        ),
    ]
    _append_execution_row(backlog_index_path, row_cells=row_cells, today=today)

    parent_id = str(successor_metadata.get("workstream_parent", "")).strip().upper()
    if _WORKSTREAM_RE.fullmatch(parent_id):
        parent_path: Path | None = None
        for path in ideas_root.rglob("*.md"):
            spec = backlog_contract._parse_idea_spec(path)
            if spec.idea_id == parent_id:
                parent_path = path
                break
        if parent_path is not None:
            parent_text = parent_path.read_text(encoding="utf-8")
            parent_spec = backlog_contract._parse_idea_spec(parent_path)
            children = _split_ids(str(parent_spec.metadata.get("workstream_children", "")))
            if successor_id not in children:
                children.append(successor_id)
                parent_text = _replace_metadata_value(
                    parent_text,
                    key="workstream_children",
                    value=_join_ids(children),
                )
                parent_path.write_text(parent_text, encoding="utf-8")

    return governance.SuccessorCreationResult(
        source_workstream=source_spec.idea_id,
        successor_workstream=successor_id,
        idea_path=str(candidate.resolve().as_posix()),
        linked_plan=plan_path,
    )


def reconcile_plan_workstream_binding(
    *,
    repo_root: Path,
    plan_index_path: Path,
    backlog_index_path: Path,
    ideas_root: Path,
    stream_path: Path,
    changed_paths: Sequence[str],
    author: str,
    source: str,
) -> tuple[list[governance.PlanBindingDecision], list[governance.SuccessorCreationResult]]:
    decisions: list[governance.PlanBindingDecision] = []
    successors: list[governance.SuccessorCreationResult] = []

    touched_plan_paths = governance.collect_touched_active_plan_paths(
        repo_root=repo_root,
        plan_index_path=plan_index_path,
        changed_paths=changed_paths,
    )
    if not touched_plan_paths:
        return decisions, successors

    active_rows = governance.parse_plan_active_rows(plan_index_path)
    rows_by_plan = {str(row.get("Plan", "")).strip(): row for row in active_rows}

    ideas, idea_errors = backlog_contract._validate_idea_specs(ideas_root)
    if idea_errors:
        raise ValueError("; ".join(idea_errors))

    today = dt.datetime.now(dt.timezone.utc).date()
    implementation_evidence_paths = governance.collect_implementation_evidence_paths(
        repo_root=repo_root,
        changed_paths=changed_paths,
        include_git=True,
    )
    has_implementation_evidence = bool(implementation_evidence_paths)

    for plan_path in touched_plan_paths:
        row = rows_by_plan.get(plan_path)
        if row is None:
            continue

        backlog_before = str(row.get("Backlog", "")).strip().strip("`")
        if backlog_before in {"", "-"}:
            decisions.append(
                governance.PlanBindingDecision(
                    plan_path=plan_path,
                    backlog_before=backlog_before or "-",
                    backlog_after=backlog_before or "-",
                    action="missing_backlog_binding",
                    details="Touched active plan row still has unbound backlog token.",
                )
            )
            continue

        if not _WORKSTREAM_RE.fullmatch(backlog_before):
            decisions.append(
                governance.PlanBindingDecision(
                    plan_path=plan_path,
                    backlog_before=backlog_before,
                    backlog_after=backlog_before,
                    action="invalid_backlog_binding",
                    details="Backlog token is not a valid workstream id.",
                )
            )
            continue

        spec = ideas.get(backlog_before)
        if spec is None:
            decisions.append(
                governance.PlanBindingDecision(
                    plan_path=plan_path,
                    backlog_before=backlog_before,
                    backlog_after=backlog_before,
                    action="missing_workstream",
                    details="Referenced workstream was not found in backlog ideas.",
                )
            )
            continue

        status = spec.status.lower()
        if status == "queued":
            next_status = "implementation" if has_implementation_evidence else "planning"
            text = spec.path.read_text(encoding="utf-8")
            text = _replace_metadata_value(text, key="status", value=next_status)
            text = _replace_metadata_value(text, key="promoted_to_plan", value=plan_path)
            spec.path.write_text(text, encoding="utf-8")
            _move_active_row_to_execution_status(
                backlog_index_path,
                idea_id=spec.idea_id,
                status=next_status,
                today=today,
            )
            action = "queued_to_implementation" if next_status == "implementation" else "queued_to_planning"
            decisions.append(
                governance.PlanBindingDecision(
                    plan_path=plan_path,
                    backlog_before=spec.idea_id,
                    backlog_after=spec.idea_id,
                    action=action,
                    details=(
                        "Promoted queued workstream to implementation from direct evidence."
                        if next_status == "implementation"
                        else "Promoted queued workstream to planning for touched active plan binding."
                    ),
                )
            )
            timeline_logger.append_event(
                repo_root=repo_root,
                stream_path=stream_path,
                kind="decision",
                summary=f"Plan binding: advanced {spec.idea_id} from queued to {next_status} for {plan_path}",
                workstream_values=[spec.idea_id],
                artifact_values=["odylith/radar/source/INDEX.md", str(spec.path), plan_path],
                component_values=[],
                author=author,
                source=source,
                context=(
                    f"Implementation evidence paths: {', '.join(implementation_evidence_paths[:4])}"
                    if next_status == "implementation"
                    else "Queued plan binding advanced into planning phase."
                ),
                headline_hint=f"Plan binding advanced {spec.idea_id}",
            )
            continue

        if status in {"planning", "implementation"}:
            promoted = str(spec.metadata.get("promoted_to_plan", "")).strip()
            if promoted != plan_path:
                text = spec.path.read_text(encoding="utf-8")
                text = _replace_metadata_value(text, key="promoted_to_plan", value=plan_path)
                spec.path.write_text(text, encoding="utf-8")
                decisions.append(
                    governance.PlanBindingDecision(
                        plan_path=plan_path,
                        backlog_before=spec.idea_id,
                        backlog_after=spec.idea_id,
                        action="rebound_promoted_plan",
                        details="Aligned `promoted_to_plan` to touched active plan path.",
                    )
                )
            continue

        if status == "finished":
            successor_id = backlog_authoring._next_workstream_id(ideas)
            successor = _create_successor_workstream(
                repo_root=repo_root,
                ideas_root=ideas_root,
                backlog_index_path=backlog_index_path,
                source_spec=spec,
                successor_id=successor_id,
                plan_path=plan_path,
            )
            successors.append(successor)
            _update_plan_index_backlog(plan_index_path, plan_path=plan_path, backlog_id=successor_id)
            decisions.append(
                governance.PlanBindingDecision(
                    plan_path=plan_path,
                    backlog_before=spec.idea_id,
                    backlog_after=successor_id,
                    action="finished_to_successor",
                    details="Created successor workstream and rebound touched active plan to maintain closed-workstream immutability.",
                )
            )
            timeline_logger.append_event(
                repo_root=repo_root,
                stream_path=stream_path,
                kind="decision",
                summary=f"Successor created: {successor_id} reopens {spec.idea_id} for active plan binding",
                workstream_values=[successor_id, spec.idea_id],
                artifact_values=[
                    "odylith/technical-plans/INDEX.md",
                    "odylith/radar/source/INDEX.md",
                    successor.idea_path,
                    str(spec.path),
                    plan_path,
                ],
                component_values=[],
                author=author,
                source=source,
                headline_hint=f"Created successor {successor_id}",
            )
            # refresh local idea map so repeated successors stay monotonic.
            ideas, _ = backlog_contract._validate_idea_specs(ideas_root)
            continue

        decisions.append(
            governance.PlanBindingDecision(
                plan_path=plan_path,
                backlog_before=spec.idea_id,
                backlog_after=spec.idea_id,
                action="unsupported_status",
                details=f"Workstream status `{status}` is not eligible for active plan binding.",
            )
        )

    return decisions, successors


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    plan_index_path = _resolve(repo_root, str(args.plan_index))
    backlog_index_path = _resolve(repo_root, str(args.backlog_index))
    ideas_root = _resolve(repo_root, str(args.ideas_root))
    stream_path = _resolve(repo_root, str(args.stream))

    try:
        decisions, successors = reconcile_plan_workstream_binding(
            repo_root=repo_root,
            plan_index_path=plan_index_path,
            backlog_index_path=backlog_index_path,
            ideas_root=ideas_root,
            stream_path=stream_path,
            changed_paths=tuple(args.changed_paths),
            author=str(args.author),
            source=str(args.source),
        )
    except ValueError as exc:
        print("odylith/technical-plans/workstream reconcile FAILED")
        print(f"- {exc}")
        return 2

    print("odylith/technical-plans/workstream reconcile completed")
    print(f"- decisions: {len(decisions)}")
    print(f"- successors_created: {len(successors)}")
    for row in decisions:
        if row.action in {"queued_to_planning", "queued_to_implementation", "finished_to_successor", "rebound_promoted_plan"}:
            print(f"- action: {row.action} ({row.backlog_before} -> {row.backlog_after}) plan={row.plan_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Compile graph-projected Radar records without prose-based admission rules."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import datetime as dt
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_traceability import (
    semantic_projection_workstream_rows,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_identifiers import (
    semantic_artifact_identifier,
)
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


SEMANTIC_RADAR_WRITE_VERSION = "odylith.greenfield.semantic-radar-write.v1"
_INDEX_COLUMNS = backlog_contract._INDEX_COLS
_METADATA_KEYS = (
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
_RADAR_INDEX = Path("odylith/radar/source/INDEX.md")
_RADAR_IDEAS = Path("odylith/radar/source/ideas")


def compile_semantic_radar_prewrite(
    *,
    repo_root: Path,
    backlog_index_path: Path,
    ideas_root: Path,
    proposal: Mapping[str, Any],
    policy: argparse.Namespace,
) -> dict[str, Any]:
    """Compile exact typed backlog rows into deterministic Radar source bytes."""

    root = Path(repo_root).expanduser().resolve()
    index_path = Path(backlog_index_path).expanduser().resolve()
    idea_root = Path(ideas_root).expanduser().resolve()
    _require_governed_paths(
        root=root,
        index_path=index_path,
        ideas_root=idea_root,
    )
    rows = _semantic_rows(proposal)
    today = dt.datetime.now(tz=dt.UTC).date()
    existing = _load_idea_specs(idea_root)
    active_rows, reorder_sections = _read_active_index(index_path)
    exact_ids = _exact_title_ids(existing)
    requested_titles = {str(row["title"]) for row in rows}
    next_number = max((_idea_number(value) or 0 for value in existing), default=0) + 1
    allocated: list[str] = []
    for row in rows:
        title = str(row["title"])
        existing_id = exact_ids.get(title)
        if existing_id:
            allocated.append(existing_id)
            continue
        allocated.append(f"B-{next_number:03d}")
        next_number += 1

    created: list[dict[str, Any]] = []
    idea_files: dict[str, str] = {}
    candidate_specs = dict(existing)
    reserved_paths: set[Path] = set()
    metadata_by_id: dict[str, dict[str, str]] = {}
    for row, idea_id in zip(rows, allocated, strict=True):
        metadata = _semantic_metadata(
            row=row,
            idea_id=idea_id,
            today=today,
            policy=policy,
        )
        sections = _semantic_sections(row)
        existing_spec = existing.get(idea_id)
        path = (
            existing_spec.path
            if existing_spec is not None
            else _unique_idea_path(
                ideas_root=idea_root,
                title=str(row["title"]),
                today=today,
                reserved=reserved_paths,
            )
        )
        reserved_paths.add(path)
        text = _render_idea_text(metadata=metadata, sections=sections)
        idea_files[str(path)] = text
        metadata_by_id[idea_id] = metadata
        candidate_specs[idea_id] = backlog_contract.IdeaSpec(
            path=path,
            metadata=metadata,
            sections=set(sections),
            section_bodies=dict(sections),
        )
        created.append(
            {
                **dict(row),
                "idea_id": idea_id,
                "idea_path": str(path),
                "ordering_score": int(metadata["ordering_score"]),
                "founder_override": False,
            }
        )

    selected_ids = set(allocated)
    stale_ids: list[str] = []
    stale_paths: list[str] = []
    retained_rows: list[dict[str, Any]] = []
    for ordinal, active in enumerate(active_rows):
        idea_id = str(active["idea_id"])
        title = str(active["title"])
        if idea_id in selected_ids:
            continue
        if title in requested_titles:
            stale = candidate_specs.pop(idea_id, None)
            if stale is not None:
                stale_ids.append(idea_id)
                stale_paths.append(str(stale.path))
            continue
        retained_rows.append({**active, "existing_order": ordinal, "is_new": False})
    for ordinal, created_row in enumerate(created, start=len(retained_rows)):
        metadata = metadata_by_id[str(created_row["idea_id"])]
        retained_rows.append(
            {
                "idea_id": str(created_row["idea_id"]),
                "title": str(created_row["title"]),
                "priority": metadata["priority"],
                "ordering_score": int(metadata["ordering_score"]),
                "commercial_value": metadata["commercial_value"],
                "product_impact": metadata["product_impact"],
                "market_value": metadata["market_value"],
                "sizing": metadata["sizing"],
                "complexity": metadata["complexity"],
                "status": "queued",
                "link": _backlog_link(root=root, path=Path(str(created_row["idea_path"]))),
                "existing_order": ordinal,
                "is_new": True,
            }
        )
    retained_rows.sort(
        key=lambda row: (
            -int(row["ordering_score"]),
            1 if bool(row["is_new"]) else 0,
            int(row["existing_order"]),
            str(row["idea_id"]),
        )
    )
    ranks = {str(row["idea_id"]): rank for rank, row in enumerate(retained_rows, 1)}
    rationale_by_id = {
        str(row["idea_id"]): _strings(row.get("rationale_lines"))
        for row in created
    }
    rationale_rows: list[tuple[str, list[str]]] = []
    active_ids = {str(row["idea_id"]) for row in retained_rows}
    for row in retained_rows:
        idea_id = str(row["idea_id"])
        rationale = rationale_by_id.get(idea_id, reorder_sections.get(idea_id, ()))
        rationale_rows.append((f"{idea_id} (rank {ranks[idea_id]})", list(rationale)))
    for idea_id, rationale in reorder_sections.items():
        if idea_id not in active_ids and idea_id not in set(stale_ids):
            rationale_rows.append((idea_id, list(rationale)))
    formatted_rows = [
        [
            str(rank),
            str(row["idea_id"]),
            str(row["title"]),
            str(row["priority"]),
            str(row["ordering_score"]),
            str(row["commercial_value"]),
            str(row["product_impact"]),
            str(row["market_value"]),
            str(row["sizing"]),
            str(row["complexity"]),
            "queued",
            str(row["link"]),
        ]
        for rank, row in enumerate(retained_rows, 1)
    ]
    return {
        "created": created,
        "backlog_index": str(index_path),
        "backlog_index_text": _rewrite_index(
            path=index_path,
            active_rows=formatted_rows,
            reorder_sections=rationale_rows,
            today=today,
        ),
        "idea_files": idea_files,
        "_candidate_idea_specs": candidate_specs,
        "existing_idea_files": {},
        "stale_idea_files": stale_paths,
        "stale_idea_ids": stale_ids,
        "validation_gate": {
            "status": "passed",
            "version": SEMANTIC_RADAR_WRITE_VERSION,
            "items": [
                {
                    "idea_id": str(row["idea_id"]),
                    "title": str(row["title"]),
                    "custody_state": str(row["custody_state"]),
                    "semantic_fact_refs": list(_strings(row.get("semantic_fact_refs"))),
                    "status": "passed",
                }
                for row in created
            ],
        },
    }


def _semantic_rows(proposal: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    rows = semantic_projection_workstream_rows(proposal)
    titles: set[str] = set()
    for row in rows:
        title = _required_text(row, "title")
        if title in titles:
            raise ValueError("verified semantic proposal repeats an exact Radar title")
        titles.add(title)
        for key in (
            "problem",
            "customer",
            "opportunity",
            "product_view",
            "recommended_first_slice",
            "custody_state",
            "evidence_tier",
        ):
            _required_text(row, key)
        for key in (
            "success_metrics",
            "validation",
            "risks",
            "rationale_lines",
            "semantic_fact_refs",
            "semantic_fact_custody",
        ):
            value = row.get(key)
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
                raise ValueError(f"verified semantic Radar row `{title}` lacks typed `{key}`")
    return rows


def _semantic_metadata(
    *,
    row: Mapping[str, Any],
    idea_id: str,
    today: dt.date,
    policy: argparse.Namespace,
) -> dict[str, str]:
    rationale = _strings(row.get("rationale_lines"))
    ranking_prefix = "- ranking basis: "
    if not rationale or not rationale[-1].startswith(ranking_prefix):
        raise ValueError("verified semantic Radar row lacks an exact ranking basis")
    metadata = {
        "status": "queued",
        "idea_id": idea_id,
        "title": _required_text(row, "title"),
        "date": today.isoformat(),
        "priority": str(row.get("priority") or "P1").strip(),
        "commercial_value": str(int(policy.commercial_value)),
        "product_impact": str(int(policy.product_impact)),
        "market_value": str(int(policy.market_value)),
        "impacted_parts": ", ".join(_strings(row.get("component_focus"))) or "odylith",
        "sizing": str(row.get("sizing") or "M").strip(),
        "complexity": str(row.get("complexity") or "Medium").strip(),
        "ordering_score": "",
        "ordering_rationale": rationale[-1][len(ranking_prefix):],
        "confidence": str(getattr(policy, "confidence", "medium") or "medium").strip(),
        "founder_override": "no",
        "promoted_to_plan": "",
        execution_wave_contract.EXECUTION_MODEL_FIELD: execution_wave_contract.EXECUTION_MODEL_STANDARD,
        "workstream_type": str(row.get("workstream_type") or "standalone").strip(),
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
    errors: list[str] = []
    score = backlog_contract._compute_score(metadata, errors=errors, path=Path("<semantic-radar>"))
    if errors or score is None:
        raise ValueError("; ".join(errors) or "verified semantic Radar score is invalid")
    metadata["ordering_score"] = str(score)
    return metadata


def _semantic_sections(row: Mapping[str, Any]) -> dict[str, str]:
    title = _required_text(row, "title")
    first_slice = _required_text(row, "recommended_first_slice")
    facts = _strings(row.get("semantic_fact_refs"))
    components = _strings(row.get("component_focus"))
    validation = _strings(row.get("validation"))
    metrics = _strings(row.get("success_metrics"))
    rationale = _strings(row.get("rationale_lines"))
    why_now = next(
        (line[len("- why now: "):] for line in rationale if line.startswith("- why now: ")),
        first_slice,
    )
    sections = {
        "Problem": _required_text(row, "problem"),
        "Customer": _required_text(row, "customer"),
        "Opportunity": _required_text(row, "opportunity"),
        "Proposed Solution": _required_text(row, "product_view"),
        "Scope": f"{first_slice}\n\nSemantic facts: {_csv(facts)}.",
        "Non-Goals": f"{title} does not add behavior outside its exact typed facts.",
        "Risks": _bullets(_strings(row.get("risks"))),
        "Dependencies": _bullets(_strings(row.get("dependencies"))) or "- None.",
        "Success Metrics": _bullets(metrics),
        "Validation": _bullets(validation),
        "Rollout": f"Promote {title} only after its typed validation obligations pass.",
        "Why Now": why_now,
        "Product View": _required_text(row, "product_view"),
        "Impacted Components": _bullets(components) or "- No component assigned.",
        "Interface Changes": _bullets(_strings(row.get("interfaces"))) or "- None.",
        "Migration/Compatibility": f"{title} adds no compatibility claim beyond the sealed release.",
        "Test Strategy": _bullets(validation),
        "Open Questions": f"Rebuild {title} only when new source evidence changes its typed graph.",
        "Semantic Custody": _semantic_custody(row),
    }
    missing = [section for section in backlog_contract._REQUIRED_SECTIONS if not sections.get(section, "").strip()]
    if missing:
        raise ValueError("verified semantic Radar row lacks sections: " + ", ".join(missing))
    return sections


def _semantic_custody(row: Mapping[str, Any]) -> str:
    payload = {
        "custody_state": _required_text(row, "custody_state"),
        "evidence_tier": _required_text(row, "evidence_tier"),
        "semantic_fact_custody": [
            dict(value)
            for value in row.get("semantic_fact_custody", ())
            if isinstance(value, Mapping)
        ],
        "semantic_fact_refs": list(_strings(row.get("semantic_fact_refs"))),
    }
    return "```json\n" + json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n```"


def _load_idea_specs(ideas_root: Path) -> dict[str, backlog_contract.IdeaSpec]:
    specs: dict[str, backlog_contract.IdeaSpec] = {}
    for path in sorted(ideas_root.rglob("*.md")):
        metadata, sections = _parse_idea_text(path.read_text(encoding="utf-8"))
        idea_id = str(metadata.get("idea_id") or "").strip().upper()
        if _idea_number(idea_id) is None:
            raise ValueError(f"Radar idea path has an invalid idea_id: {path}")
        if idea_id in specs:
            raise ValueError(f"Radar idea_id appears more than once: {idea_id}")
        specs[idea_id] = backlog_contract.IdeaSpec(
            path=path.resolve(),
            metadata=metadata,
            sections=set(sections),
            section_bodies=sections,
        )
    return specs


def _parse_idea_text(text: str) -> tuple[dict[str, str], dict[str, str]]:
    metadata: dict[str, str] = {}
    section_lines: dict[str, list[str]] = {}
    current = ""
    for raw in str(text).splitlines():
        if raw.startswith("## "):
            current = raw[3:].strip()
            if not current:
                raise ValueError("Radar idea contains an empty section heading")
            section_lines.setdefault(current, [])
            continue
        if current:
            section_lines[current].append(raw)
            continue
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, {
        key: "\n".join(lines).strip()
        for key, lines in section_lines.items()
    }


def _render_idea_text(
    *, metadata: Mapping[str, str], sections: Mapping[str, str]
) -> str:
    lines: list[str] = []
    for key in _METADATA_KEYS:
        lines.extend((f"{key}: {str(metadata.get(key, '')).strip()}", ""))
    required = set(backlog_contract._REQUIRED_SECTIONS)
    for section in backlog_contract._REQUIRED_SECTIONS:
        lines.extend((f"## {section}", str(sections[section]).strip(), ""))
    for section, body in sections.items():
        if section not in required:
            lines.extend((f"## {section}", str(body).strip(), ""))
    return "\n".join(lines).rstrip() + "\n"


def _read_active_index(
    path: Path,
) -> tuple[list[dict[str, str]], dict[str, tuple[str, ...]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start, end = _section_bounds(lines, "## Ranked Active Backlog")
    if start < 0:
        raise ValueError("Radar index lacks Ranked Active Backlog")
    rows: list[dict[str, str]] = []
    for line in lines[start:end]:
        cells = _table_cells(line)
        if not cells or tuple(cell.casefold() for cell in cells) == tuple(
            column.casefold() for column in _INDEX_COLUMNS
        ):
            continue
        if len(cells) == len(_INDEX_COLUMNS) and not all(set(cell) <= {"-"} for cell in cells):
            rows.append(dict(zip(_INDEX_COLUMNS, cells, strict=True)))
    rationale_start, rationale_end = _section_bounds(lines, "## Reorder Rationale Log")
    rationale: dict[str, tuple[str, ...]] = {}
    current = ""
    collected: list[str] = []
    for line in lines[rationale_start:rationale_end] if rationale_start >= 0 else ():
        if line.startswith("### "):
            if current:
                rationale[current] = tuple(value for value in collected if value.strip())
            current = line[4:].split(None, 1)[0].strip().upper()
            collected = []
        elif current:
            collected.append(line)
    if current:
        rationale[current] = tuple(value for value in collected if value.strip())
    return rows, rationale


def _rewrite_index(
    *,
    path: Path,
    active_rows: Sequence[Sequence[str]],
    reorder_sections: Sequence[tuple[str, Sequence[str]]],
    today: dt.date,
) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start, end = _section_bounds(lines, "## Ranked Active Backlog")
    table_indexes = [
        index
        for index in range(start, end)
        if len(_table_cells(lines[index])) == len(_INDEX_COLUMNS)
        and _table_cells(lines[index])[0].casefold() not in {"rank", "---"}
    ]
    rendered = [_table_row(row) for row in active_rows]
    if table_indexes:
        lines[table_indexes[0] : table_indexes[-1] + 1] = rendered
    else:
        lines[start + 4 : start + 4] = rendered
    reorder_start, reorder_end = _section_bounds(lines, "## Reorder Rationale Log")
    if reorder_start < 0:
        raise ValueError("Radar index lacks Reorder Rationale Log")
    replacement = ["## Reorder Rationale Log", ""]
    for heading, rationale in reorder_sections:
        replacement.extend((f"### {heading}", *rationale, ""))
    lines[reorder_start:reorder_end] = replacement
    updated = False
    for index, line in enumerate(lines):
        if line.startswith("Last updated (UTC):"):
            lines[index] = f"Last updated (UTC): {today.isoformat()}"
            updated = True
            break
    if not updated:
        raise ValueError("Radar index lacks its update stamp")
    return "\n".join(lines).rstrip() + "\n"


def _exact_title_ids(
    ideas: Mapping[str, backlog_contract.IdeaSpec],
) -> dict[str, str]:
    matches: dict[str, str] = {}
    for idea_id, spec in ideas.items():
        title = str(spec.metadata.get("title") or "").strip()
        if not title:
            continue
        current = matches.get(title)
        if current is None or (_idea_number(idea_id) or 0) < (_idea_number(current) or 0):
            matches[title] = idea_id
    return matches


def _unique_idea_path(
    *, ideas_root: Path, title: str, today: dt.date, reserved: set[Path]
) -> Path:
    month = ideas_root / today.isoformat()[:7]
    month.mkdir(parents=True, exist_ok=True)
    slug = semantic_artifact_identifier(title, fallback="workstream", max_length=96)
    path = month / f"{today.isoformat()}-{slug}.md"
    suffix = 2
    while path.exists() or path in reserved:
        path = month / f"{today.isoformat()}-{slug}-{suffix}.md"
        suffix += 1
    return path.resolve()


def _idea_number(value: str) -> int | None:
    token = str(value).strip().upper()
    digits = token[2:] if token.startswith("B-") else ""
    return int(digits) if len(digits) >= 3 and digits.isdigit() else None


def _require_governed_paths(*, root: Path, index_path: Path, ideas_root: Path) -> None:
    if index_path != (root / _RADAR_INDEX).resolve():
        raise ValueError("verified semantic Radar index path escaped governed source")
    if ideas_root != (root / _RADAR_IDEAS).resolve():
        raise ValueError("verified semantic Radar idea path escaped governed source")


def _section_bounds(lines: Sequence[str], title: str) -> tuple[int, int]:
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == title)
    except StopIteration:
        return -1, -1
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return start, end


def _table_cells(line: str) -> list[str]:
    stripped = str(line).strip()
    return [cell.strip() for cell in stripped.split("|")[1:-1]] if stripped.startswith("|") else []


def _table_row(values: Sequence[str]) -> str:
    return "| " + " | ".join(str(value).strip() for value in values) + " |"


def _backlog_link(*, root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(root).as_posix()
    return f"[{semantic_artifact_identifier(path.stem, fallback='workstream')}]({relative})"


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise ValueError(f"verified semantic Radar row lacks `{key}`")
    return value


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _bullets(values: Sequence[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def _csv(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "none"


__all__ = ["SEMANTIC_RADAR_WRITE_VERSION", "compile_semantic_radar_prewrite"]

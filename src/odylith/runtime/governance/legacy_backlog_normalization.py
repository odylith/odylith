from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from odylith.install.fs import atomic_write_text
from odylith.runtime.common.consumer_profile import truth_root_path
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.governance import validate_backlog_contract as backlog_contract

_REQUIRED_BULLETS = (
    "- why now:",
    "- expected outcome:",
    "- tradeoff:",
    "- deferred for now:",
    "- ranking basis:",
)


@dataclass(frozen=True)
class LegacyBacklogNormalizationResult:
    backlog_index: Path
    changed: bool
    added_sections: tuple[str, ...]
    normalized_sections: tuple[str, ...]


def normalize_legacy_backlog_index(*, repo_root: str | Path, today: dt.date | None = None) -> LegacyBacklogNormalizationResult:
    root = Path(repo_root).expanduser().resolve()
    backlog_index = truth_root_path(repo_root=root, key="radar_source") / "INDEX.md"
    idea_root = truth_root_path(repo_root=root, key="radar_source") / "ideas"
    if not backlog_index.is_file() or not idea_root.is_dir():
        return LegacyBacklogNormalizationResult(
            backlog_index=backlog_index,
            changed=False,
            added_sections=(),
            normalized_sections=(),
        )
    current_day = today or dt.date.today()
    ideas, _idea_errors = backlog_contract._validate_idea_specs(idea_root)  # noqa: SLF001
    snapshot = backlog_contract.load_backlog_index_snapshot(backlog_index)
    active_rows = _section_rows(snapshot.get("active", {}))
    execution_rows = _section_rows(snapshot.get("execution", {}))
    parked_rows = _section_rows(snapshot.get("parked", {}))
    finished_rows = _section_rows(snapshot.get("finished", {}))
    existing_sections_raw = snapshot.get("reorder_sections", {})
    existing_sections: dict[str, dict[str, Any]] = {}
    if isinstance(existing_sections_raw, Mapping):
        existing_sections = {
            str(key): {
                "heading": str(value.get("heading", "")).strip(),
                "lines": [str(line) for line in value.get("lines", [])] if isinstance(value, Mapping) else [],
            }
            for key, value in existing_sections_raw.items()
        }

    ordered_sections: list[tuple[str, str, list[str]]] = []
    changed_keys: list[str] = []
    added_keys: list[str] = []
    seen: set[str] = set()

    for rank, row in enumerate(active_rows, start=1):
        idea_id = str(row.get("idea_id", "")).strip()
        if not idea_id:
            continue
        seen.add(idea_id)
        title = str(row.get("title", "")).strip()
        spec = ideas.get(idea_id)
        existing = existing_sections.get(idea_id, {"heading": "", "lines": []})
        normalized_lines = _normalized_rationale_lines(
            idea_id=idea_id,
            title=title,
            existing_lines=list(existing.get("lines", [])),
            founder_override=bool(spec.founder_override) if spec is not None else False,
            today=current_day,
            require_all_bullets=True,
        )
        heading = f"{idea_id} (rank {rank})"
        ordered_sections.append((idea_id, heading, normalized_lines))
        if not existing.get("lines"):
            added_keys.append(idea_id)
        elif heading != str(existing.get("heading", "")).strip() or normalized_lines != list(existing.get("lines", [])):
            changed_keys.append(idea_id)

    extra_ids_in_order = [idea_id for idea_id in existing_sections if idea_id not in seen]
    override_ids = _founder_override_ids(ideas=ideas, rows=(execution_rows, parked_rows, finished_rows))
    for idea_id in extra_ids_in_order + [idea_id for idea_id in override_ids if idea_id not in seen and idea_id not in extra_ids_in_order]:
        spec = ideas.get(idea_id)
        existing = existing_sections.get(idea_id, {"heading": "", "lines": []})
        title = str(spec.metadata.get("title", "")).strip() if spec is not None else idea_id
        normalized_lines = _normalized_rationale_lines(
            idea_id=idea_id,
            title=title,
            existing_lines=list(existing.get("lines", [])),
            founder_override=bool(spec.founder_override) if spec is not None else False,
            today=current_day,
            require_all_bullets=bool(spec.founder_override) if spec is not None else False,
        )
        if not normalized_lines and not existing.get("lines"):
            continue
        heading = str(existing.get("heading", "")).strip() or idea_id
        ordered_sections.append((idea_id, heading, normalized_lines))
        if not existing.get("lines"):
            added_keys.append(idea_id)
        elif normalized_lines != list(existing.get("lines", [])):
            changed_keys.append(idea_id)

    content = backlog_index.read_text(encoding="utf-8")
    lines = content.splitlines()
    start, end = _section_bounds(lines, "## Reorder Rationale Log")
    replacement = ["## Reorder Rationale Log", ""]
    for _idea_id, heading, rationale_lines in ordered_sections:
        replacement.append(f"### {heading}")
        replacement.extend(rationale_lines)
        replacement.append("")
    lines[start:end] = replacement
    updated = _update_last_updated("\n".join(lines), today=current_day)
    if not updated.endswith("\n"):
        updated += "\n"
    changed = updated != content
    if changed:
        atomic_write_text(backlog_index, updated, encoding="utf-8")
    return LegacyBacklogNormalizationResult(
        backlog_index=backlog_index,
        changed=changed,
        added_sections=tuple(added_keys),
        normalized_sections=tuple(sorted(dict.fromkeys((*changed_keys, *added_keys)))),
    )


def collect_backlog_contract_errors(*, repo_root: str | Path) -> tuple[str, ...]:
    root = Path(repo_root).expanduser().resolve()
    idea_root = truth_root_path(repo_root=root, key="radar_source") / "ideas"
    backlog_index = truth_root_path(repo_root=root, key="radar_source") / "INDEX.md"
    plan_index = truth_root_path(repo_root=root, key="technical_plans") / "INDEX.md"
    errors: list[str] = []
    ideas, idea_errors = backlog_contract._validate_idea_specs(idea_root)  # noqa: SLF001
    errors.extend(idea_errors)
    errors.extend(backlog_contract._validate_topology_contract(ideas=ideas))  # noqa: SLF001
    errors.extend(backlog_contract._validate_lineage_contract(ideas=ideas))  # noqa: SLF001
    errors.extend(backlog_contract._validate_promotion_links(ideas=ideas, repo_root=root))  # noqa: SLF001
    _programs, program_errors = execution_wave_contract.collect_execution_programs(
        repo_root=root,
        idea_specs=ideas,
    )
    errors.extend(program_errors)
    active_ids, execution_ids, parked_ids, finished_ids, _active_ranks, backlog_errors = backlog_contract._validate_backlog_index(  # noqa: SLF001
        backlog_index=backlog_index,
        ideas=ideas,
        repo_root=root,
    )
    errors.extend(backlog_errors)
    errors.extend(backlog_contract._validate_execution_status_sync(execution_ids=execution_ids, ideas=ideas))  # noqa: SLF001
    errors.extend(backlog_contract._validate_parked_status_sync(parked_ids=parked_ids, ideas=ideas))  # noqa: SLF001
    errors.extend(
        backlog_contract._validate_plan_index(  # noqa: SLF001
            plan_index=plan_index,
            execution_ids=execution_ids,
            parked_ids=parked_ids,
            ideas=ideas,
            repo_root=root,
        )
    )
    del active_ids
    del finished_ids
    return tuple(errors)


def summarize_backlog_contract_errors(errors: Iterable[str], *, limit: int = 5) -> tuple[str, ...]:
    ordered_counts: dict[str, int] = {}
    for message in errors:
        normalized = str(message).strip()
        if not normalized:
            continue
        ordered_counts[normalized] = ordered_counts.get(normalized, 0) + 1
    summary: list[str] = []
    for index, (message, count) in enumerate(ordered_counts.items()):
        if index >= limit:
            break
        prefix = f"{count}x " if count > 1 else ""
        summary.append(f"{prefix}{message}")
    hidden = len(ordered_counts) - len(summary)
    if hidden > 0:
        summary.append(f"{hidden} more unique backlog-contract error(s) suppressed in the compact summary.")
    return tuple(summary)


def backlog_next_action(*, errors: Iterable[str]) -> str:
    messages = [str(message).lower() for message in errors]
    metadata_fix_tokens = (
        "ordering_score",
        "workstream_split_from",
        "missing reciprocal",
        "missing active plan row",
        "promoted_to_plan",
        "ranking score inversion",
        "execution ordering violation",
        "table status must be one of",
        "status must be one of",
    )
    if any(token in message for message in messages for token in metadata_fix_tokens):
        return (
            "Repair the reported backlog/workstream metadata, status, and plan bindings, "
            "then rerun `odylith sync --repo-root . --check-only`."
        )
    if any("reorder rationale" in message or "priority override idea" in message for message in messages):
        return "Finish the normalized rationale blocks in `odylith/radar/source/INDEX.md`, then rerun `odylith sync --repo-root . --force`."
    if any("missing from index" in message or "duplicate idea_id" in message for message in messages):
        return "Repair the ranked backlog tables in `odylith/radar/source/INDEX.md`, then rerun `odylith sync --repo-root . --force`."
    return "Run `odylith sync --repo-root . --check-only` after the reported backlog contract fixes to confirm the remaining blockers are gone."


def _section_rows(section: Any) -> list[dict[str, str]]:
    if not isinstance(section, Mapping):
        return []
    rows_raw = section.get("rows", [])
    if not isinstance(rows_raw, list):
        return []
    rows: list[dict[str, str]] = []
    for row in rows_raw:
        if not isinstance(row, list) or len(row) != len(backlog_contract._INDEX_COLS):  # noqa: SLF001
            continue
        rows.append(dict(zip(backlog_contract._INDEX_COLS, row, strict=True)))  # noqa: SLF001
    return rows


def _founder_override_ids(*, ideas: Mapping[str, backlog_contract.IdeaSpec], rows: Iterable[list[dict[str, str]]]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for section_rows in rows:
        for row in section_rows:
            idea_id = str(row.get("idea_id", "")).strip()
            spec = ideas.get(idea_id)
            if idea_id and spec is not None and spec.founder_override and idea_id not in seen:
                seen.add(idea_id)
                result.append(idea_id)
    return result


def _normalized_rationale_lines(
    *,
    idea_id: str,
    title: str,
    existing_lines: list[str],
    founder_override: bool,
    today: dt.date,
    require_all_bullets: bool,
) -> list[str]:
    defaults = _default_rationale_lines(
        idea_id=idea_id,
        title=title,
        founder_override=founder_override,
        today=today,
    )
    lines = list(existing_lines)
    bullet_indexes = {
        bullet: index
        for index, line in enumerate(lines)
        for bullet in _REQUIRED_BULLETS
        if str(line).strip().lower().startswith(bullet)
    }
    required = _REQUIRED_BULLETS if require_all_bullets else ("- ranking basis:",) if founder_override else ()
    for bullet in required:
        default_line = defaults[bullet]
        if bullet not in bullet_indexes:
            lines.append(default_line)
            continue
        current = lines[bullet_indexes[bullet]]
        lowered = str(current).lower()
        if bullet == "- ranking basis:" and founder_override:
            if "no manual priority override" in lowered or backlog_contract._REVIEW_DATE_RE.search(current) is None:  # noqa: SLF001
                lines[bullet_indexes[bullet]] = default_line
    if not lines and require_all_bullets:
        return list(defaults.values())
    return lines


def _default_rationale_lines(
    *,
    idea_id: str,
    title: str,
    founder_override: bool,
    today: dt.date,
) -> dict[str, str]:
    lines = backlog_authoring._build_rationale_lines(  # noqa: SLF001
        item=backlog_authoring.CreatedBacklogItem(
            idea_id=idea_id,
            title=title,
            idea_path=Path(
                f"odylith/radar/source/ideas/{today.isoformat()[:7]}/{today.isoformat()}-{idea_id.lower()}.md"
            ),
            ordering_score=0,
            founder_override=founder_override,
        ),
        override_note="",
        override_review_date=today.isoformat(),
    )
    return {
        next(
            bullet
            for bullet in _REQUIRED_BULLETS
            if line.lower().startswith(bullet)
        ): line
        for line in lines
    }


def _section_bounds(lines: list[str], title: str) -> tuple[int, int]:
    start = -1
    for index, line in enumerate(lines):
        if line.strip() == title:
            start = index
            break
    if start == -1:
        raise ValueError(f"missing `{title}` section in odylith/radar/source/INDEX.md")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return start, end


def _update_last_updated(content: str, *, today: dt.date) -> str:
    replacement = f"Last updated (UTC): {today.isoformat()}"
    match = backlog_contract._UPDATE_STAMP_RE.search(content)  # noqa: SLF001
    if match is None:
        return content
    return content[: match.start()] + replacement + content[match.end() :]

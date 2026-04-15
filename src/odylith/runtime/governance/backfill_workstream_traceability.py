"""Auto-backfill workstream traceability metadata in backlog idea specs.

This script is intentionally non-destructive by default:
- It only writes missing/empty topology fields.
- It does not overwrite explicit values unless `--force-overwrite` is set.
- It reports unresolved/ambiguous links as warnings.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.surfaces import generated_surface_cleanup
from odylith.runtime.common import stable_generated_utc
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


_IDEA_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_DEP_EDGE_RE = re.compile(
    r"(B-?\d{3,})(?:\[[^\]]*\])?\s*--?>+\s*(B-?\d{3,})(?:\[[^\]]*\])?"
)


_METADATA_ORDER: tuple[str, ...] = (
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

_LINEAGE_SINGLE_FIELDS: tuple[str, ...] = (
    "workstream_reopens",
    "workstream_reopened_by",
    "workstream_split_from",
    "workstream_merged_into",
)
_LINEAGE_MULTI_FIELDS: tuple[str, ...] = (
    "workstream_split_into",
    "workstream_merged_from",
)
_ID_SET_FIELDS: dict[str, re.Pattern[str]] = {
    "workstream_children": _IDEA_ID_RE,
    "workstream_depends_on": _IDEA_ID_RE,
    "workstream_blocks": _IDEA_ID_RE,
    "related_diagram_ids": _DIAGRAM_ID_RE,
    "workstream_split_into": _IDEA_ID_RE,
    "workstream_merged_from": _IDEA_ID_RE,
}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Auto-backfill missing workstream topology metadata in backlog idea specs.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ideas-root", default="odylith/radar/source/ideas")
    parser.add_argument("--catalog", default="odylith/atlas/source/catalog/diagrams.v1.json")
    parser.add_argument(
        "--dependency-map-glob",
        default="odylith/atlas/source/*dependency*.mmd",
        help="Glob used to extract B-xxx dependency edges from Mermaid sources.",
    )
    parser.add_argument(
        "--report",
        default="odylith/radar/traceability-autofix-report.v1.json",
        help="JSON report output path.",
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Allow inferred values to replace explicit metadata values.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and report changes without writing idea files.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, value: str) -> Path:
    token = str(value or "").strip()
    path = Path(token)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _as_repo_path(repo_root: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(target.resolve())


def _split_ids(raw: str, *, pattern: re.Pattern[str]) -> list[str]:
    values: list[str] = []
    for token in str(raw or "").replace(";", ",").split(","):
        normalized = token.strip()
        if not normalized:
            continue
        if not pattern.fullmatch(normalized):
            continue
        values.append(normalized)
    return sorted(set(values))


def _join_ids(values: Sequence[str]) -> str:
    deduped = sorted({str(v).strip() for v in values if str(v).strip()})
    return ",".join(deduped)


def _lineage_single(metadata: Mapping[str, str], field: str) -> str:
    values = _split_ids(str(metadata.get(field, "")), pattern=_IDEA_ID_RE)
    if not values:
        return ""
    return values[0]


def _lineage_multi(metadata: Mapping[str, str], field: str) -> set[str]:
    return set(_split_ids(str(metadata.get(field, "")), pattern=_IDEA_ID_RE))


def _required_topology_fields(metadata: Mapping[str, str]) -> set[str]:
    """Return topology fields that are structurally required for this workstream."""

    token = str(metadata.get("workstream_type", "")).strip().lower()
    required: set[str] = {"workstream_type"}
    if token == "child":
        required.add("workstream_parent")
    elif token == "umbrella":
        required.add("workstream_children")
    return required


def _normalized_field_id_set(field: str, raw: str) -> set[str] | None:
    pattern = _ID_SET_FIELDS.get(str(field or "").strip())
    if pattern is None:
        return None
    return set(_split_ids(str(raw or ""), pattern=pattern))


def _normalize_idea_token(token: str) -> str:
    raw = str(token or "").strip()
    if raw.startswith("B-"):
        return raw
    if raw.startswith("B") and raw[1:].isdigit():
        return f"B-{raw[1:]}"
    return raw


def _parse_catalog(*, catalog_path: Path, repo_root: Path) -> tuple[dict[str, set[str]], list[tuple[str, str]], list[str]]:
    """Return (idea->diagram_ids, dependency_edges, warnings)."""

    idea_to_diagrams: dict[str, set[str]] = {}
    dependency_edges: list[tuple[str, str]] = []
    warnings: list[str] = []

    if not catalog_path.is_file():
        warnings.append(f"missing catalog: {_as_repo_path(repo_root, catalog_path)}")
        return idea_to_diagrams, dependency_edges, warnings

    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warnings.append(f"invalid catalog json `{_as_repo_path(repo_root, catalog_path)}`: {exc}")
        return idea_to_diagrams, dependency_edges, warnings

    diagrams = payload.get("diagrams", [])
    if not isinstance(diagrams, list):
        warnings.append(f"catalog `diagrams` must be a list: {_as_repo_path(repo_root, catalog_path)}")
        return idea_to_diagrams, dependency_edges, warnings

    for entry in diagrams:
        if not isinstance(entry, dict):
            continue
        diagram_id = str(entry.get("diagram_id", "")).strip()
        if not _DIAGRAM_ID_RE.fullmatch(diagram_id):
            continue

        for workstream_id in entry.get("related_workstreams", []) or []:
            token = str(workstream_id or "").strip()
            if _IDEA_ID_RE.fullmatch(token):
                idea_to_diagrams.setdefault(token, set()).add(diagram_id)

        for backlog_path in entry.get("related_backlog", []) or []:
            token = str(backlog_path or "").strip()
            if not token:
                continue
            idea_path = _resolve(repo_root, token)
            if not idea_path.is_file():
                continue
            spec = backlog_contract._parse_idea_spec(idea_path)
            idea_id = spec.idea_id
            if _IDEA_ID_RE.fullmatch(idea_id):
                idea_to_diagrams.setdefault(idea_id, set()).add(diagram_id)

    return idea_to_diagrams, dependency_edges, warnings


def _parse_dependency_maps(*, repo_root: Path, glob_pattern: str) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (depends_on_map, blocks_map) using A-->B => B depends_on A and A blocks B."""

    depends_on: dict[str, set[str]] = {}
    blocks: dict[str, set[str]] = {}
    for source in sorted(repo_root.glob(glob_pattern)):
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        for upstream_raw, downstream_raw in _DEP_EDGE_RE.findall(text):
            upstream = _normalize_idea_token(upstream_raw)
            downstream = _normalize_idea_token(downstream_raw)
            if not (_IDEA_ID_RE.fullmatch(upstream) and _IDEA_ID_RE.fullmatch(downstream)):
                continue
            depends_on.setdefault(downstream, set()).add(upstream)
            blocks.setdefault(upstream, set()).add(downstream)
    return depends_on, blocks


def _build_metadata_block(*, metadata: dict[str, str]) -> str:
    keys: list[str] = []
    seen: set[str] = set()
    for key in _METADATA_ORDER:
        if key in metadata:
            keys.append(key)
            seen.add(key)
    for key in metadata:
        if key in seen:
            continue
        keys.append(key)

    chunks = [f"{key}: {str(metadata.get(key, '')).strip()}" for key in keys]
    return "\n\n".join(chunks).rstrip() + "\n\n"


def _rewrite_metadata(*, idea_path: Path, metadata: dict[str, str], dry_run: bool) -> None:
    lines = idea_path.read_text(encoding="utf-8").splitlines()
    section_start = len(lines)
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            section_start = idx
            break

    tail = "\n".join(lines[section_start:]).rstrip()
    head = _build_metadata_block(metadata=metadata)
    payload = head + (tail + "\n" if tail else "")
    if dry_run:
        return
    idea_path.write_text(payload, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    ideas_root = _resolve(repo_root, args.ideas_root)
    catalog_path = _resolve(repo_root, args.catalog)
    report_path = _resolve(repo_root, args.report)

    idea_specs, validate_errors = backlog_contract._validate_idea_specs(ideas_root)

    # Keep running even when validator reports issues; we only need parsable specs for backfill.
    warnings: list[str] = [f"validator: {message}" for message in validate_errors]

    idea_to_diagrams, _unused_dependency_edges, catalog_warnings = _parse_catalog(
        catalog_path=catalog_path,
        repo_root=repo_root,
    )
    warnings.extend(catalog_warnings)

    inferred_depends_on, inferred_blocks = _parse_dependency_maps(
        repo_root=repo_root,
        glob_pattern=str(args.dependency_map_glob),
    )

    # Gather parent candidates from reciprocal declarations and dependency-map hints.
    parent_candidates: dict[str, set[str]] = {}
    explicit_children: dict[str, set[str]] = {}
    declared_parent_links: dict[str, set[str]] = {}
    for idea_id, spec in idea_specs.items():
        parent = str(spec.metadata.get("workstream_parent", "")).strip()
        if _IDEA_ID_RE.fullmatch(parent):
            declared_parent_links.setdefault(idea_id, set()).add(parent)

        children = _split_ids(str(spec.metadata.get("workstream_children", "")), pattern=_IDEA_ID_RE)
        if children:
            explicit_children.setdefault(idea_id, set()).update(children)
            for child_id in children:
                parent_candidates.setdefault(child_id, set()).add(idea_id)
    for child_id, parents in declared_parent_links.items():
        if len(parents) == 1:
            parent_candidates.setdefault(child_id, set()).update(parents)
    for child_id, dependencies in inferred_depends_on.items():
        if len(dependencies) == 1:
            parent_candidates.setdefault(child_id, set()).update(dependencies)

    explicit_reopens: dict[str, str] = {}
    explicit_reopened_by: dict[str, str] = {}
    explicit_split_from: dict[str, str] = {}
    explicit_split_into: dict[str, set[str]] = {}
    explicit_merged_into: dict[str, str] = {}
    explicit_merged_from: dict[str, set[str]] = {}
    for idea_id, spec in idea_specs.items():
        reopens = _lineage_single(spec.metadata, "workstream_reopens")
        if reopens:
            explicit_reopens[idea_id] = reopens
        reopened_by = _lineage_single(spec.metadata, "workstream_reopened_by")
        if reopened_by:
            explicit_reopened_by[idea_id] = reopened_by
        split_from = _lineage_single(spec.metadata, "workstream_split_from")
        if split_from:
            explicit_split_from[idea_id] = split_from
        split_into = _lineage_multi(spec.metadata, "workstream_split_into")
        if split_into:
            explicit_split_into[idea_id] = set(split_into)
        merged_into = _lineage_single(spec.metadata, "workstream_merged_into")
        if merged_into:
            explicit_merged_into[idea_id] = merged_into
        merged_from = _lineage_multi(spec.metadata, "workstream_merged_from")
        if merged_from:
            explicit_merged_from[idea_id] = set(merged_from)

    changes: list[dict[str, Any]] = []
    modified_files: list[str] = []
    unresolved: list[dict[str, str]] = []
    conflicts: list[dict[str, Any]] = []

    for idea_id, spec in sorted(idea_specs.items()):
        metadata = dict(spec.metadata)
        path = spec.path
        file_changed = False

        def maybe_set(field: str, value: str, *, reason: str) -> None:
            nonlocal file_changed
            current = str(metadata.get(field, "")).strip()
            candidate = str(value or "").strip()
            if not candidate:
                return
            if current and not args.force_overwrite:
                current_ids = _normalized_field_id_set(field, current)
                candidate_ids = _normalized_field_id_set(field, candidate)
                if current_ids is not None and candidate_ids is not None:
                    # Keep explicit author intent when current metadata already
                    # includes all inferred IDs (for example curated diagram sets).
                    if current_ids.issuperset(candidate_ids):
                        return
                if current != candidate:
                    conflicts.append(
                        {
                            "idea_id": idea_id,
                            "field": field,
                            "current": current,
                            "candidate": candidate,
                            "reason": reason,
                        }
                    )
                return
            if current == candidate:
                return
            metadata[field] = candidate
            file_changed = True
            changes.append(
                {
                    "idea_id": idea_id,
                    "file": _as_repo_path(repo_root, path),
                    "field": field,
                    "value": candidate,
                    "reason": reason,
                }
            )

        # Infer parent where unambiguous.
        candidate_parents = sorted(parent_candidates.get(idea_id, set()))
        current_parent = str(metadata.get("workstream_parent", "")).strip()
        if current_parent:
            if candidate_parents and current_parent not in candidate_parents and not args.force_overwrite:
                conflicts.append(
                    {
                        "idea_id": idea_id,
                        "field": "workstream_parent",
                        "current": current_parent,
                        "candidate": ",".join(candidate_parents),
                        "reason": "explicit parent conflicts with inferred topology candidates",
                    }
                )
        else:
            if len(candidate_parents) == 1:
                maybe_set(
                    "workstream_parent",
                    candidate_parents[0],
                    reason="single parent candidate inferred from topology declarations",
                )
            elif len(candidate_parents) > 1:
                unresolved.append(
                    {
                        "idea_id": idea_id,
                        "field": "workstream_parent",
                        "reason": f"ambiguous parent candidates: {','.join(candidate_parents)}",
                    }
                )

        # Infer children from parent links and explicit child lists.
        known_children = set(explicit_children.get(idea_id, set()))
        for child_id, parents in declared_parent_links.items():
            if idea_id in parents:
                known_children.add(child_id)
        for child_id, parents in parent_candidates.items():
            if idea_id in parents:
                known_children.add(child_id)

        if known_children:
            maybe_set(
                "workstream_children",
                _join_ids(sorted(known_children)),
                reason="children inferred from reciprocal parent-child links",
            )

        # Infer dependency and blocking edges.
        depends_inferred = sorted(inferred_depends_on.get(idea_id, set()))
        if depends_inferred and not str(metadata.get("workstream_depends_on", "")).strip():
            maybe_set(
                "workstream_depends_on",
                _join_ids(depends_inferred),
                reason="inferred from dependency-map mermaid edges",
            )

        blocks_inferred = sorted(inferred_blocks.get(idea_id, set()))
        if blocks_inferred and not str(metadata.get("workstream_blocks", "")).strip():
            maybe_set(
                "workstream_blocks",
                _join_ids(blocks_inferred),
                reason="inferred from dependency-map inverse edges",
            )

        # Infer related diagrams.
        diagrams = sorted(idea_to_diagrams.get(idea_id, set()))
        if diagrams:
            maybe_set(
                "related_diagram_ids",
                _join_ids(diagrams),
                reason="inferred from Mermaid catalog related_backlog/related_workstreams",
            )

        # Infer lineage reciprocal fields when exactly one candidate exists.
        reopens_candidates = set()
        if idea_id in explicit_reopens:
            reopens_candidates.add(explicit_reopens[idea_id])
        reopens_candidates.update(
            target_id
            for target_id, source_id in explicit_reopened_by.items()
            if source_id == idea_id
        )
        if len(reopens_candidates) == 1:
            maybe_set(
                "workstream_reopens",
                next(iter(reopens_candidates)),
                reason="reciprocal lineage inferred from `workstream_reopened_by`",
            )
        elif len(reopens_candidates) > 1 and not str(metadata.get("workstream_reopens", "")).strip():
            unresolved.append(
                {
                    "idea_id": idea_id,
                    "field": "workstream_reopens",
                    "reason": f"ambiguous reciprocal candidates: {','.join(sorted(reopens_candidates))}",
                }
            )

        reopened_by_candidates = set()
        if idea_id in explicit_reopened_by:
            reopened_by_candidates.add(explicit_reopened_by[idea_id])
        reopened_by_candidates.update(
            source_id
            for source_id, target_id in explicit_reopens.items()
            if target_id == idea_id
        )
        if len(reopened_by_candidates) == 1:
            maybe_set(
                "workstream_reopened_by",
                next(iter(reopened_by_candidates)),
                reason="reciprocal lineage inferred from `workstream_reopens`",
            )
        elif len(reopened_by_candidates) > 1 and not str(metadata.get("workstream_reopened_by", "")).strip():
            unresolved.append(
                {
                    "idea_id": idea_id,
                    "field": "workstream_reopened_by",
                    "reason": f"ambiguous reciprocal candidates: {','.join(sorted(reopened_by_candidates))}",
                }
            )

        split_from_candidates = set()
        if idea_id in explicit_split_from:
            split_from_candidates.add(explicit_split_from[idea_id])
        split_from_candidates.update(
            parent_id
            for parent_id, children in explicit_split_into.items()
            if idea_id in children
        )
        if len(split_from_candidates) == 1:
            maybe_set(
                "workstream_split_from",
                next(iter(split_from_candidates)),
                reason="reciprocal lineage inferred from `workstream_split_into`",
            )
        elif len(split_from_candidates) > 1 and not str(metadata.get("workstream_split_from", "")).strip():
            unresolved.append(
                {
                    "idea_id": idea_id,
                    "field": "workstream_split_from",
                    "reason": f"ambiguous reciprocal candidates: {','.join(sorted(split_from_candidates))}",
                }
            )

        split_into_candidates = set(explicit_split_into.get(idea_id, set()))
        split_into_candidates.update(
            child_id
            for child_id, parent_id in explicit_split_from.items()
            if parent_id == idea_id
        )
        if split_into_candidates:
            maybe_set(
                "workstream_split_into",
                _join_ids(sorted(split_into_candidates)),
                reason="reciprocal lineage inferred from `workstream_split_from`",
            )

        merged_into_candidates = set()
        if idea_id in explicit_merged_into:
            merged_into_candidates.add(explicit_merged_into[idea_id])
        merged_into_candidates.update(
            target_id
            for target_id, sources in explicit_merged_from.items()
            if idea_id in sources
        )
        if len(merged_into_candidates) == 1:
            maybe_set(
                "workstream_merged_into",
                next(iter(merged_into_candidates)),
                reason="reciprocal lineage inferred from `workstream_merged_from`",
            )
        elif len(merged_into_candidates) > 1 and not str(metadata.get("workstream_merged_into", "")).strip():
            unresolved.append(
                {
                    "idea_id": idea_id,
                    "field": "workstream_merged_into",
                    "reason": f"ambiguous reciprocal candidates: {','.join(sorted(merged_into_candidates))}",
                }
            )

        merged_from_candidates = set(explicit_merged_from.get(idea_id, set()))
        merged_from_candidates.update(
            source_id
            for source_id, target_id in explicit_merged_into.items()
            if target_id == idea_id
        )
        if merged_from_candidates:
            maybe_set(
                "workstream_merged_from",
                _join_ids(sorted(merged_from_candidates)),
                reason="reciprocal lineage inferred from `workstream_merged_into`",
            )

        # Infer workstream type last.
        current_type = str(metadata.get("workstream_type", "")).strip().lower()
        if current_type not in {"umbrella", "child", "standalone"}:
            parent = str(metadata.get("workstream_parent", "")).strip()
            children = _split_ids(str(metadata.get("workstream_children", "")), pattern=_IDEA_ID_RE)
            inferred_type = "standalone"
            if children:
                inferred_type = "umbrella"
            elif parent:
                inferred_type = "child"
            maybe_set("workstream_type", inferred_type, reason="derived from parent/children topology")

        # Emit unresolved entries for still-empty required topology fields.
        status = str(metadata.get("status", "")).strip().lower()
        should_track_unresolved = status in {"planning", "implementation", "finished"}
        if should_track_unresolved:
            required_fields = _required_topology_fields(metadata)
            for field in sorted(required_fields):
                value = str(metadata.get(field, "")).strip()
                if field == "workstream_children":
                    if _split_ids(value, pattern=_IDEA_ID_RE):
                        continue
                elif value:
                    continue
                unresolved.append(
                    {
                        "idea_id": idea_id,
                        "field": field,
                        "reason": "required topology field is empty after inference",
                    }
                )

        if file_changed:
            _rewrite_metadata(idea_path=path, metadata=metadata, dry_run=bool(args.dry_run))
            modified_files.append(_as_repo_path(repo_root, path))

    report = {
        "repo_root": str(repo_root),
        "dry_run": bool(args.dry_run),
        "force_overwrite": bool(args.force_overwrite),
        "modified_files": sorted(set(modified_files)),
        "fields_filled": changes,
        "conflicts_skipped": conflicts,
        "fields_unresolved": unresolved,
        "warnings": warnings,
        "summary": {
            "ideas_seen": len(idea_specs),
            "files_modified": len(set(modified_files)),
            "fields_filled": len(changes),
            "conflicts": len(conflicts),
            "unresolved": len(unresolved),
            "warnings": len(warnings),
        },
    }
    try:
        existing_report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
    except (OSError, json.JSONDecodeError):
        existing_report = None
    if (
        isinstance(existing_report, dict)
        and not report["modified_files"]
        and not report["fields_filled"]
        and not report["conflicts_skipped"]
        and not report["fields_unresolved"]
    ):
        # Keep the previous persisted report stable when a rerun produces no
        # new autofix activity. This preserves the last meaningful report
        # snapshot instead of rewriting it into an all-zero no-op payload.
        preserved_report = dict(existing_report)
        preserved_report["repo_root"] = str(repo_root)
        preserved_report["dry_run"] = bool(args.dry_run)
        preserved_report["force_overwrite"] = bool(args.force_overwrite)
        report = preserved_report
    report["generated_utc"] = stable_generated_utc.resolve_for_json_file(
        output_path=report_path,
        payload=report,
    )

    wrote_report = odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=report_path,
        content=json.dumps(report, indent=2) + "\n",
        lock_key=str(report_path),
    )
    print("traceability autofix completed")
    print(f"- ideas_seen: {report['summary']['ideas_seen']}")
    print(f"- files_modified: {report['summary']['files_modified']}")
    print(f"- fields_filled: {report['summary']['fields_filled']}")
    print(f"- conflicts_skipped: {report['summary']['conflicts']}")
    print(f"- unresolved: {report['summary']['unresolved']}")
    print(f"- warnings: {report['summary']['warnings']}")
    print(f"- report_status: {'updated' if wrote_report else 'current'}")
    print(f"- report: {_as_repo_path(repo_root, report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

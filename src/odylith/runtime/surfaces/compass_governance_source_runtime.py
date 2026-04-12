from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.governance import execution_wave_view_model
from odylith.runtime.governance import release_planning_view_model
from odylith.runtime.governance import sync_session as governed_sync_session
from odylith.runtime.governance import validate_backlog_contract as backlog_contract

_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")


def _as_repo_path(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _normalized_token(value: Any) -> str:
    return str(value or "").strip()


def _csv_ids(value: Any, *, pattern: re.Pattern[str]) -> list[str]:
    if isinstance(value, list):
        raw_values = [_normalized_token(item) for item in value]
    else:
        raw_values = [
            token.strip()
            for token in str(value or "").replace(";", ",").split(",")
            if token.strip()
        ]
    deduped: list[str] = []
    seen: set[str] = set()
    for token in raw_values:
        if not pattern.fullmatch(token) or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _normalized_id_list(value: Any, *, pattern: re.Pattern[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    deduped: list[str] = []
    seen: set[str] = set()
    for raw in value:
        token = _normalized_token(raw)
        if not pattern.fullmatch(token) or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _build_live_governance_context_uncached(
    *,
    repo_root: Path,
    traceability_graph: Mapping[str, Any],
) -> dict[str, Any]:
    resolved_repo_root = Path(repo_root).resolve()
    ideas_root = (resolved_repo_root / "odylith" / "radar" / "source" / "ideas").resolve()
    idea_specs, idea_errors = backlog_contract._validate_idea_specs(ideas_root)  # noqa: SLF001
    release_payload, release_errors, _state = release_planning_view_model.build_release_view_from_repo(
        repo_root=resolved_repo_root,
        idea_specs=idea_specs,
    )
    execution_programs, execution_program_errors = execution_wave_contract.collect_execution_programs(
        repo_root=resolved_repo_root,
        idea_specs=idea_specs,
    )
    execution_wave_refs = execution_wave_contract.derive_workstream_wave_refs(execution_programs)

    source_rows = traceability_graph.get("workstreams", [])
    source_rows_by_id = (
        {
            _normalized_token(row.get("idea_id")): dict(row)
            for row in source_rows
            if isinstance(row, Mapping) and _normalized_token(row.get("idea_id"))
        }
        if isinstance(source_rows, list)
        else {}
    )

    release_workstreams = (
        dict(release_payload.get("workstreams", {}))
        if isinstance(release_payload.get("workstreams"), Mapping)
        else {}
    )

    workstream_rows: list[dict[str, Any]] = []
    for idea_id, spec in sorted(idea_specs.items()):
        metadata = spec.metadata
        source_row = dict(source_rows_by_id.get(idea_id, {}))
        release_row = (
            dict(release_workstreams.get(idea_id, {}))
            if isinstance(release_workstreams.get(idea_id), Mapping)
            else {}
        )
        active_release = (
            dict(release_row.get("active_release", {}))
            if isinstance(release_row.get("active_release"), Mapping)
            else {}
        )
        workstream_rows.append(
            {
                **source_row,
                "idea_id": idea_id,
                "title": _normalized_token(metadata.get("title")) or _normalized_token(source_row.get("title")) or idea_id,
                "status": _normalized_token(metadata.get("status")).lower() or _normalized_token(source_row.get("status")).lower(),
                "workstream_type": _normalized_token(metadata.get("workstream_type")).lower() or _normalized_token(source_row.get("workstream_type")).lower(),
                "workstream_parent": _normalized_token(metadata.get("workstream_parent")),
                "workstream_children": _csv_ids(metadata.get("workstream_children"), pattern=_WORKSTREAM_ID_RE),
                "workstream_depends_on": _csv_ids(metadata.get("workstream_depends_on"), pattern=_WORKSTREAM_ID_RE),
                "workstream_blocks": _csv_ids(metadata.get("workstream_blocks"), pattern=_WORKSTREAM_ID_RE),
                "workstream_reopens": _normalized_token(metadata.get("workstream_reopens")),
                "workstream_reopened_by": _normalized_token(metadata.get("workstream_reopened_by")),
                "workstream_split_from": _normalized_token(metadata.get("workstream_split_from")),
                "workstream_split_into": _csv_ids(metadata.get("workstream_split_into"), pattern=_WORKSTREAM_ID_RE),
                "workstream_merged_into": _normalized_token(metadata.get("workstream_merged_into")),
                "workstream_merged_from": _csv_ids(metadata.get("workstream_merged_from"), pattern=_WORKSTREAM_ID_RE),
                "related_diagram_ids": _csv_ids(metadata.get("related_diagram_ids"), pattern=_DIAGRAM_ID_RE)
                or _normalized_id_list(source_row.get("related_diagram_ids"), pattern=_DIAGRAM_ID_RE),
                "idea_file": _as_repo_path(repo_root=resolved_repo_root, path=spec.path),
                "promoted_to_plan": _normalized_token(metadata.get("promoted_to_plan")),
                "plan_traceability": (
                    dict(source_row.get("plan_traceability", {}))
                    if isinstance(source_row.get("plan_traceability"), Mapping)
                    else {"runbooks": [], "developer_docs": [], "code_references": []}
                ),
                "active_release_id": _normalized_token(release_row.get("active_release_id")),
                "active_release": active_release,
                "release_history": _mapping_list(release_row.get("history")),
                "release_history_summary": _normalized_token(release_row.get("history_summary")),
                "coverage": (
                    dict(source_row.get("coverage", {}))
                    if isinstance(source_row.get("coverage"), Mapping)
                    else {
                        "linked_plan_count": 1 if _normalized_token(metadata.get("promoted_to_plan")) else 0,
                        "linked_diagram_count": len(_csv_ids(metadata.get("related_diagram_ids"), pattern=_DIAGRAM_ID_RE)),
                        "runbook_count": 0,
                        "developer_doc_count": 0,
                        "code_reference_count": 0,
                    }
                ),
                "execution_wave_refs": _mapping_list(execution_wave_refs.get(idea_id)),
            }
        )

    release_summary = {
        "catalog": [
            dict(row)
            for row in release_payload.get("catalog", [])
            if isinstance(row, Mapping)
        ] if isinstance(release_payload.get("catalog"), list) else [],
        "current_release": (
            dict(release_payload.get("current_release", {}))
            if isinstance(release_payload.get("current_release"), Mapping)
            else {}
        ),
        "next_release": (
            dict(release_payload.get("next_release", {}))
            if isinstance(release_payload.get("next_release"), Mapping)
            else {}
        ),
        "summary": (
            dict(release_payload.get("summary", {}))
            if isinstance(release_payload.get("summary"), Mapping)
            else {}
        ),
    }
    live_traceability_graph = {
        **dict(traceability_graph),
        "workstreams": workstream_rows,
        "execution_programs": [program.to_dict() for program in execution_programs],
        "releases": list(release_summary["catalog"]),
        "current_release": dict(release_summary["current_release"]),
        "next_release": dict(release_summary["next_release"]),
        "release_summary": dict(release_summary["summary"]),
    }
    execution_waves = execution_wave_view_model.build_execution_wave_view_payload(live_traceability_graph)
    return {
        "traceability_graph": live_traceability_graph,
        "workstream_rows": workstream_rows,
        "execution_waves": execution_waves,
        "release_summary": release_summary,
        "release_workstreams": release_workstreams,
        "governance_errors": [*idea_errors, *release_errors, *execution_program_errors],
    }


def _traceability_fingerprint(
    *,
    traceability_graph: Mapping[str, Any],
    traceability_signature: str,
) -> str:
    provided = str(traceability_signature or "").strip()
    if provided:
        return provided
    return odylith_context_cache.fingerprint_payload(dict(traceability_graph))


def build_live_governance_context(
    *,
    repo_root: Path,
    traceability_graph: Mapping[str, Any],
    traceability_signature: str = "",
) -> dict[str, Any]:
    resolved_repo_root = Path(repo_root).resolve()
    session = governed_sync_session.active_sync_session()
    fingerprint = _traceability_fingerprint(
        traceability_graph=traceability_graph,
        traceability_signature=traceability_signature,
    )
    if session is None or session.repo_root != resolved_repo_root:
        return _build_live_governance_context_uncached(
            repo_root=resolved_repo_root,
            traceability_graph=traceability_graph,
        )

    cache_key = "\n".join(
        (
            "v2",
            f"generation={session.generation}",
            f"traceability={fingerprint}",
        )
    )
    built = False

    def _builder() -> dict[str, Any]:
        nonlocal built
        built = True
        return _build_live_governance_context_uncached(
            repo_root=resolved_repo_root,
            traceability_graph=traceability_graph,
        )

    context = session.get_or_compute(
        namespace="compass_governance_context",
        key=cache_key,
        builder=_builder,
    )
    session.record_cache_decision(
        category="compass_governance_context",
        cache_hit=not built,
        built_from="sync_session",
        details={
            "generation": session.generation,
            "traceability": fingerprint,
        },
    )
    if built:
        return context
    return copy.deepcopy(context)


__all__ = ["build_live_governance_context"]

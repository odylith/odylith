"""Build unified workstream traceability graph for Backlog Radar and Mermaid Atlas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

from odylith.runtime.common.consumer_profile import canonical_truth_token
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.surfaces import generated_surface_cleanup
from odylith.runtime.common import stable_generated_utc
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


_IDEA_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_TRACE_SECTIONS: tuple[str, ...] = ("Runbooks", "Developer Docs", "Code References")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_CHECKBOX_RE = re.compile(r"^\[(?:x|X| )\]\s*")
_DEFAULT_WARNING_SEVERITIES = {"warning", "error"}
_WARNING_AUDIENCES = {"operator", "maintainer"}
_WARNING_SURFACE_VISIBILITY = {"default", "diagnostics"}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Build odylith/radar/traceability-graph.v1.json from backlog, plans, and Mermaid catalog.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ideas-root", default="odylith/radar/source/ideas")
    parser.add_argument("--catalog", default="odylith/atlas/source/catalog/diagrams.v1.json")
    parser.add_argument("--output", default="odylith/radar/traceability-graph.v1.json")
    parser.add_argument(
        "--autofix-report",
        default="odylith/radar/traceability-autofix-report.v1.json",
        help="Optional autofix report path to include in warnings context.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    raw = str(token or "").strip()
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _as_repo_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


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


def _single_id(raw: str, *, pattern: re.Pattern[str]) -> str:
    values = _split_ids(raw, pattern=pattern)
    if not values:
        return ""
    return values[0]


def _normalize_path_token(*, repo_root: Path, token: str) -> str:
    raw = str(token or "").strip().strip(".,;:")
    if not raw or raw.startswith("http://") or raw.startswith("https://"):
        return ""
    if " " in raw or "<" in raw or ">" in raw:
        return ""
    path = Path(raw)
    if path.is_absolute():
        try:
            return canonical_truth_token(path.resolve().relative_to(repo_root.resolve()).as_posix(), repo_root=repo_root)
        except ValueError:
            return ""
    return canonical_truth_token(path.as_posix().lstrip("./"), repo_root=repo_root)


def _normalize_warning_policy(
    *,
    severity: str,
    audience: str = "operator",
    surface_visibility: str = "",
) -> tuple[str, str, str]:
    normalized_severity = str(severity or "warning").strip().lower() or "warning"
    normalized_audience = str(audience or "operator").strip().lower() or "operator"
    if normalized_audience not in _WARNING_AUDIENCES:
        normalized_audience = "operator"
    normalized_visibility = str(surface_visibility or "").strip().lower()
    if normalized_visibility not in _WARNING_SURFACE_VISIBILITY:
        if normalized_audience == "maintainer" or normalized_severity not in _DEFAULT_WARNING_SEVERITIES:
            normalized_visibility = "diagnostics"
        else:
            normalized_visibility = "default"
    return normalized_severity, normalized_audience, normalized_visibility


def _extract_sections(path: Path) -> dict[str, list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections.setdefault(current, []).append(line)
    return sections


def _collect_plan_traceability(*, plan_path: Path, repo_root: Path) -> dict[str, list[str]]:
    if not plan_path.is_file():
        return {}
    sections = _extract_sections(plan_path)
    trace_lines = sections.get("Traceability", [])
    grouped: dict[str, list[str]] = {name: [] for name in _TRACE_SECTIONS}
    bucket: str | None = None
    for raw in trace_lines:
        stripped = raw.strip()
        if stripped.startswith("### "):
            name = stripped[4:].strip()
            bucket = name if name in grouped else None
            continue
        if bucket is None or not stripped:
            continue
        if not stripped.lstrip().startswith("- "):
            continue
        body = _CHECKBOX_RE.sub("", stripped.lstrip()[2:].strip()).strip()
        candidates: list[str] = []
        candidates.extend(m.group(1).strip() for m in _MARKDOWN_LINK_RE.finditer(body) if m.group(1).strip())
        candidates.extend(m.group(1).strip() for m in _INLINE_CODE_RE.finditer(body) if m.group(1).strip())
        for candidate in candidates:
            normalized = _normalize_path_token(repo_root=repo_root, token=candidate)
            if normalized:
                grouped[bucket].append(normalized)
    collapsed: dict[str, list[str]] = {}
    for bucket_name, values in grouped.items():
        deduped = sorted(set(values))
        if deduped:
            collapsed[bucket_name] = deduped
    return collapsed


def _load_catalog(
    *,
    catalog_path: Path,
    repo_root: Path,
    idea_path_to_id: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]], list[str]]:
    warnings: list[str] = []
    diagrams_by_id: dict[str, dict[str, Any]] = {}
    workstream_to_diagrams: dict[str, set[str]] = {}

    if not catalog_path.is_file():
        warnings.append(f"missing catalog: {_as_repo_path(repo_root, catalog_path)}")
        return diagrams_by_id, workstream_to_diagrams, warnings

    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warnings.append(f"invalid catalog json `{_as_repo_path(repo_root, catalog_path)}`: {exc}")
        return diagrams_by_id, workstream_to_diagrams, warnings

    diagrams = payload.get("diagrams", [])
    if not isinstance(diagrams, list):
        warnings.append(f"catalog diagrams must be a list: {_as_repo_path(repo_root, catalog_path)}")
        return diagrams_by_id, workstream_to_diagrams, warnings

    for item in diagrams:
        if not isinstance(item, dict):
            continue
        diagram_id = str(item.get("diagram_id", "")).strip()
        if not _DIAGRAM_ID_RE.fullmatch(diagram_id):
            continue
        diagrams_by_id[diagram_id] = {
            "diagram_id": diagram_id,
            "title": str(item.get("title", "")).strip(),
            "slug": str(item.get("slug", "")).strip(),
            "file": str(item.get("source_mmd", "")).strip(),
            "related_workstreams": [],
        }

        related_workstreams: set[str] = set()
        for token in item.get("related_workstreams", []) or []:
            value = str(token or "").strip()
            if _IDEA_ID_RE.fullmatch(value):
                related_workstreams.add(value)

        for backlog_path in item.get("related_backlog", []) or []:
            raw = str(backlog_path or "").strip()
            if not raw:
                continue
            normalized = _normalize_path_token(repo_root=repo_root, token=raw)
            idea_id = idea_path_to_id.get(normalized)
            if idea_id:
                related_workstreams.add(idea_id)

        diagrams_by_id[diagram_id]["related_workstreams"] = sorted(related_workstreams)
        for idea_id in sorted(related_workstreams):
            workstream_to_diagrams.setdefault(idea_id, set()).add(diagram_id)

    return diagrams_by_id, workstream_to_diagrams, warnings


def _add_node(nodes: dict[str, dict[str, Any]], *, node_id: str, payload: dict[str, Any]) -> None:
    if node_id in nodes:
        return
    nodes[node_id] = payload


def _add_edge(edges: set[tuple[str, str, str]], *, source: str, target: str, edge_type: str) -> None:
    edges.add((source, target, edge_type))


def _iter_idea_specs(idea_specs: dict[str, backlog_contract.IdeaSpec]) -> Iterable[tuple[str, backlog_contract.IdeaSpec]]:
    for idea_id in sorted(idea_specs.keys()):
        yield idea_id, idea_specs[idea_id]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    ideas_root = _resolve(repo_root, args.ideas_root)
    catalog_path = _resolve(repo_root, args.catalog)
    output_path = _resolve(repo_root, args.output)
    autofix_report_path = _resolve(repo_root, args.autofix_report)

    idea_specs, idea_errors = backlog_contract._validate_idea_specs(ideas_root)
    warnings: list[str] = []
    warning_items: list[dict[str, Any]] = []

    idea_to_file: dict[str, str] = {
        idea_id: _as_repo_path(repo_root, spec.path)
        for idea_id, spec in idea_specs.items()
    }

    def _add_warning(
        message: str,
        *,
        idea_id: str = "",
        category: str = "general",
        severity: str = "warning",
        audience: str = "operator",
        surface_visibility: str = "",
        action: str = "",
        source: str = "",
    ) -> None:
        text = str(message or "").strip()
        if not text:
            return
        warnings.append(text)
        normalized_severity, normalized_audience, normalized_visibility = _normalize_warning_policy(
            severity=severity,
            audience=audience,
            surface_visibility=surface_visibility,
        )
        item: dict[str, Any] = {
            "severity": normalized_severity,
            "audience": normalized_audience,
            "surface_visibility": normalized_visibility,
            "category": str(category or "general").strip() or "general",
            "message": text,
        }
        candidate_idea = str(idea_id or "").strip()
        if candidate_idea and _IDEA_ID_RE.fullmatch(candidate_idea):
            item["idea_id"] = candidate_idea
        action_text = str(action or "").strip()
        if action_text:
            item["action"] = action_text
        source_text = str(source or "").strip()
        if source_text:
            item["source"] = source_text
        warning_items.append(item)

    for entry in idea_errors:
        _add_warning(
            f"idea-parse: {entry}",
            category="idea_parse",
            severity="error",
            action="Fix malformed idea metadata/sections so the renderer can index this workstream.",
            source=_as_repo_path(repo_root, ideas_root),
        )

    # Build idea path -> idea_id map for backlog linkage inference from catalog.
    idea_path_to_id: dict[str, str] = {}
    for idea_id, spec in idea_specs.items():
        idea_path_to_id[_as_repo_path(repo_root, spec.path)] = idea_id

    diagrams_by_id, workstream_to_diagrams, catalog_warnings = _load_catalog(
        catalog_path=catalog_path,
        repo_root=repo_root,
        idea_path_to_id=idea_path_to_id,
    )
    for warning in catalog_warnings:
        _add_warning(
            warning,
            category="catalog",
            severity="warning",
            action="Repair Mermaid catalog JSON/paths and rerun workstream sync.",
            source=_as_repo_path(repo_root, catalog_path),
        )

    execution_programs, execution_program_errors = execution_wave_contract.collect_execution_programs(
        repo_root=repo_root,
        idea_specs=idea_specs,
    )
    execution_wave_refs = execution_wave_contract.derive_workstream_wave_refs(execution_programs)
    for entry in execution_program_errors:
        _add_warning(
            entry,
            category="execution_program",
            severity="error",
            action=(
                "Fix umbrella execution wave metadata or companion program files under "
                "odylith/radar/source/programs/ and rerun workstream sync."
            ),
            source=execution_wave_contract.PROGRAMS_DIR.as_posix(),
        )

    if autofix_report_path.is_file():
        try:
            report_payload = json.loads(autofix_report_path.read_text(encoding="utf-8"))
            report_path = _as_repo_path(repo_root, autofix_report_path)
            unresolved_count = len(report_payload.get("fields_unresolved", []) or [])
            if unresolved_count:
                _add_warning(
                    f"autofix-report: {unresolved_count} unresolved topology fields in {report_path}",
                    category="autofix_summary",
                    severity="warning",
                    action=(
                        "Open the autofix report and populate missing topology metadata "
                        "(parent/children/depends_on/blocks/related_diagram_ids) in backlog idea specs."
                    ),
                    source=report_path,
                )
            unresolved_entries = report_payload.get("fields_unresolved", []) or []
            unresolved_by_idea: dict[str, set[str]] = {}
            for row in unresolved_entries:
                if not isinstance(row, dict):
                    continue
                idea_id = str(row.get("idea_id", "")).strip()
                field = str(row.get("field", "")).strip()
                if not idea_id or not field:
                    continue
                unresolved_by_idea.setdefault(idea_id, set()).add(field)
            for idea_id in sorted(unresolved_by_idea.keys()):
                fields = sorted(unresolved_by_idea[idea_id])
                _add_warning(
                    f"{idea_id}: missing topology metadata fields ({', '.join(fields)})",
                    idea_id=idea_id,
                    category="topology_missing_fields",
                    severity="warning",
                    action=(
                        f"Update {idea_to_file.get(idea_id, 'the idea spec')} with explicit values for "
                        f"{', '.join(fields)} (or set intentional empties with rationale)."
                    ),
                    source=report_path,
                )
            conflicts = report_payload.get("conflicts_skipped", []) or []
            for row in conflicts:
                if not isinstance(row, dict):
                    continue
                idea_id = str(row.get("idea_id", "")).strip()
                field = str(row.get("field", "")).strip()
                reason = str(row.get("reason", "")).strip()
                current = str(row.get("current", "")).strip()
                candidate = str(row.get("candidate", "")).strip()
                _add_warning(
                    f"{idea_id or 'unknown'}: autofix skipped `{field or 'field'}` due to metadata conflict",
                    idea_id=idea_id,
                    category="topology_conflict",
                    severity="info",
                    audience="maintainer",
                    surface_visibility="diagnostics",
                    action=(
                        f"Resolve explicitly in {idea_to_file.get(idea_id, 'the idea spec')}: "
                        f"current='{current}' candidate='{candidate}'. Reason: {reason or 'conflict'}."
                    ),
                    source=report_path,
                )
        except json.JSONDecodeError:
            _add_warning(
                f"autofix-report: invalid json `{_as_repo_path(repo_root, autofix_report_path)}`",
                category="autofix_report_parse",
                severity="error",
                action="Fix odylith/radar/traceability-autofix-report.v1.json serialization and rerun sync.",
                source=_as_repo_path(repo_root, autofix_report_path),
            )

    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()
    workstreams: list[dict[str, Any]] = []
    coverage: dict[str, dict[str, int]] = {}

    for idea_id, spec in _iter_idea_specs(idea_specs):
        metadata = spec.metadata
        title = str(metadata.get("title", "")).strip()
        status = str(metadata.get("status", "")).strip()
        idea_file = _as_repo_path(repo_root, spec.path)

        parent = str(metadata.get("workstream_parent", "")).strip()
        children = _split_ids(str(metadata.get("workstream_children", "")), pattern=_IDEA_ID_RE)
        depends_on = _split_ids(str(metadata.get("workstream_depends_on", "")), pattern=_IDEA_ID_RE)
        blocks = _split_ids(str(metadata.get("workstream_blocks", "")), pattern=_IDEA_ID_RE)
        related_diagrams = _split_ids(str(metadata.get("related_diagram_ids", "")), pattern=_DIAGRAM_ID_RE)
        workstream_reopens = _single_id(str(metadata.get("workstream_reopens", "")), pattern=_IDEA_ID_RE)
        workstream_reopened_by = _single_id(str(metadata.get("workstream_reopened_by", "")), pattern=_IDEA_ID_RE)
        workstream_split_from = _single_id(str(metadata.get("workstream_split_from", "")), pattern=_IDEA_ID_RE)
        workstream_split_into = _split_ids(str(metadata.get("workstream_split_into", "")), pattern=_IDEA_ID_RE)
        workstream_merged_into = _single_id(str(metadata.get("workstream_merged_into", "")), pattern=_IDEA_ID_RE)
        workstream_merged_from = _split_ids(str(metadata.get("workstream_merged_from", "")), pattern=_IDEA_ID_RE)
        inferred_diagrams = sorted(workstream_to_diagrams.get(idea_id, set()))
        merged_diagrams = sorted(set(related_diagrams) | set(inferred_diagrams))

        workstream_type = str(metadata.get("workstream_type", "")).strip().lower()
        if workstream_type not in {"umbrella", "child", "standalone"}:
            _add_warning(
                f"{idea_id}: missing/invalid `workstream_type` in {idea_file}",
                idea_id=idea_id,
                category="topology_workstream_type",
                severity="warning",
                action="Set `workstream_type` to umbrella, child, or standalone in the idea spec metadata.",
                source=idea_file,
            )

        if not parent and workstream_type == "child":
            _add_warning(
                f"{idea_id}: `workstream_type=child` but `workstream_parent` is empty",
                idea_id=idea_id,
                category="topology_parent_missing",
                severity="warning",
                action="Set `workstream_parent` to the umbrella idea ID for this child workstream.",
                source=idea_file,
            )

        promoted_plan = str(metadata.get("promoted_to_plan", "")).strip()
        plan_file = ""
        plan_traceability = {}
        if promoted_plan:
            target = _resolve(repo_root, promoted_plan)
            if target.is_file():
                plan_file = _as_repo_path(repo_root, target)
                plan_traceability = _collect_plan_traceability(plan_path=target, repo_root=repo_root)
            else:
                _add_warning(
                    f"{idea_id}: promoted plan path does not exist `{promoted_plan}`",
                    idea_id=idea_id,
                    category="plan_link_missing",
                    severity="warning",
                    action="Fix `promoted_to_plan` path or create the plan file.",
                    source=idea_file,
                )

        runbooks = sorted(set(plan_traceability.get("Runbooks", [])))
        devdocs = sorted(set(plan_traceability.get("Developer Docs", [])))
        code_refs = sorted(set(plan_traceability.get("Code References", [])))

        _add_node(
            nodes,
            node_id=idea_id,
            payload={
                "id": idea_id,
                "type": "workstream",
                "label": title or idea_id,
                "status": status,
                "file": idea_file,
            },
        )

        if parent:
            _add_edge(edges, source=parent, target=idea_id, edge_type="parent_child")
        for child_id in children:
            _add_edge(edges, source=idea_id, target=child_id, edge_type="parent_child")
        for dep in depends_on:
            _add_edge(edges, source=dep, target=idea_id, edge_type="depends_on")
        for blocked in blocks:
            _add_edge(edges, source=idea_id, target=blocked, edge_type="blocks")
        if workstream_reopens:
            _add_edge(edges, source=idea_id, target=workstream_reopens, edge_type="reopens")
        if workstream_reopened_by:
            _add_edge(edges, source=workstream_reopened_by, target=idea_id, edge_type="reopens")
        if workstream_split_from:
            _add_edge(edges, source=workstream_split_from, target=idea_id, edge_type="split")
        for split_target in workstream_split_into:
            _add_edge(edges, source=idea_id, target=split_target, edge_type="split")
        if workstream_merged_into:
            _add_edge(edges, source=idea_id, target=workstream_merged_into, edge_type="merge")
        for merge_source in workstream_merged_from:
            _add_edge(edges, source=merge_source, target=idea_id, edge_type="merge")

        if plan_file:
            plan_node = f"plan:{plan_file}"
            _add_node(
                nodes,
                node_id=plan_node,
                payload={
                    "id": plan_node,
                    "type": "plan",
                    "label": plan_file,
                    "file": plan_file,
                },
            )
            _add_edge(edges, source=idea_id, target=plan_node, edge_type="promoted_to_plan")

        for diagram_id in merged_diagrams:
            if diagram_id in diagrams_by_id:
                diagram = diagrams_by_id[diagram_id]
                diagram_node = f"diagram:{diagram_id}"
                _add_node(
                    nodes,
                    node_id=diagram_node,
                    payload={
                        "id": diagram_node,
                        "type": "diagram",
                        "label": diagram.get("title") or diagram_id,
                        "diagram_id": diagram_id,
                        "file": diagram.get("file", ""),
                    },
                )
                _add_edge(edges, source=idea_id, target=diagram_node, edge_type="diagram_linkage")
            else:
                _add_warning(
                    f"{idea_id}: related diagram `{diagram_id}` not found in catalog",
                    idea_id=idea_id,
                    category="diagram_link_missing",
                    severity="warning",
                    action="Add the diagram to odylith/atlas/source/catalog/diagrams.v1.json or remove stale diagram linkage.",
                    source=idea_file,
                )

        def _link_artifacts(values: list[str], *, bucket: str) -> None:
            for rel in values:
                artifact_node = f"artifact:{rel}"
                _add_node(
                    nodes,
                    node_id=artifact_node,
                    payload={
                        "id": artifact_node,
                        "type": "artifact",
                        "label": rel,
                        "bucket": bucket,
                        "file": rel,
                    },
                )
                _add_edge(edges, source=idea_id, target=artifact_node, edge_type=f"plan_traceability:{bucket}")

        _link_artifacts(runbooks, bucket="runbooks")
        _link_artifacts(devdocs, bucket="developer_docs")
        _link_artifacts(code_refs, bucket="code_references")

        coverage[idea_id] = {
            "linked_plan_count": 1 if plan_file else 0,
            "linked_diagram_count": len(merged_diagrams),
            "runbook_count": len(runbooks),
            "developer_doc_count": len(devdocs),
            "code_reference_count": len(code_refs),
        }

        workstreams.append(
            {
                "idea_id": idea_id,
                "title": title,
                "status": status,
                "workstream_type": workstream_type,
                "workstream_parent": parent,
                "workstream_children": children,
                "workstream_depends_on": depends_on,
                "workstream_blocks": blocks,
                "workstream_reopens": workstream_reopens,
                "workstream_reopened_by": workstream_reopened_by,
                "workstream_split_from": workstream_split_from,
                "workstream_split_into": workstream_split_into,
                "workstream_merged_into": workstream_merged_into,
                "workstream_merged_from": workstream_merged_from,
                "related_diagram_ids": merged_diagrams,
                "idea_file": idea_file,
                "promoted_to_plan": plan_file,
                "plan_traceability": {
                    "runbooks": runbooks,
                    "developer_docs": devdocs,
                    "code_references": code_refs,
                },
                "coverage": coverage[idea_id],
                "execution_wave_refs": execution_wave_refs.get(idea_id, []),
            }
        )

    edge_items = [
        {"source": src, "target": tgt, "edge_type": typ}
        for src, tgt, typ in sorted(edges)
    ]
    deduped_warning_items: list[dict[str, str]] = []
    seen_warning_items: set[tuple[str, str, str, str, str, str]] = set()
    for item in warning_items:
        key = (
            str(item.get("idea_id", "")).strip(),
            str(item.get("severity", "")).strip(),
            str(item.get("category", "")).strip(),
            str(item.get("message", "")).strip(),
            str(item.get("action", "")).strip(),
            str(item.get("source", "")).strip(),
        )
        if key in seen_warning_items:
            continue
        seen_warning_items.add(key)
        deduped_warning_items.append(item)
    warning_items = deduped_warning_items

    payload = {
        "version": "v1",
        "source": {
            "ideas_root": _as_repo_path(repo_root, ideas_root),
            "catalog": _as_repo_path(repo_root, catalog_path),
            "execution_programs_root": execution_wave_contract.PROGRAMS_DIR.as_posix(),
        },
        "workstreams": workstreams,
        "execution_programs": [program.to_dict() for program in execution_programs],
        "nodes": [nodes[key] for key in sorted(nodes)],
        "edges": edge_items,
        "coverage": coverage,
        "warning_items": warning_items,
        "warnings": sorted(set(warnings)),
        "summary": {
            "workstream_count": len(workstreams),
            "execution_program_count": len(execution_programs),
            "execution_wave_count": sum(len(program.waves) for program in execution_programs),
            "node_count": len(nodes),
            "edge_count": len(edge_items),
            "warning_count": len(set(warnings)),
            "warning_item_count": len(warning_items),
        },
    }
    payload["generated_utc"] = stable_generated_utc.resolve_for_json_file(
        output_path=output_path,
        payload=payload,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("traceability graph build passed")
    print(f"- output: {_as_repo_path(repo_root, output_path)}")
    print(f"- workstreams: {payload['summary']['workstream_count']}")
    print(f"- nodes: {payload['summary']['node_count']}")
    print(f"- edges: {payload['summary']['edge_count']}")
    print(f"- warnings: {payload['summary']['warning_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

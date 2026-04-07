"""Render the Component Registry dashboard.

Registry is the component-centric governance surface that complements
Radar/Atlas/Compass by organizing change narratives around tracked components.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import dashboard_ui_runtime_primitives
from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.surfaces import brand_assets
from odylith.runtime.governance import delivery_intelligence_engine
from odylith.runtime.governance import component_registry_intelligence as registry
from odylith.runtime.surfaces import dashboard_time
from odylith.runtime.governance import operator_readout
from odylith.runtime.common import stable_generated_utc
from odylith.runtime.common.consumer_profile import load_consumer_profile
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.context_engine import odylith_runtime_surface_summary
from odylith.runtime.governance import traceability_ui_lookup

_REGISTRY_DETAIL_SHARD_SIZE = 32
_REGISTRY_SUMMARY_HEAVY_FIELDS = frozenset(
    {
        "spec_ref",
        "spec_href",
        "spec_title",
        "spec_last_updated",
        "spec_feature_history",
        "spec_markdown",
        "spec_runbooks",
        "spec_developer_docs",
        "skill_trigger_tiers",
        "skill_trigger_structure",
        "workstreams",
        "diagrams",
        "diagram_details",
        "sources",
        "path_prefixes",
        "timeline",
    }
)
_REGISTRY_INTELLIGENCE_COMPONENT_FIELDS = (
    "confidence",
    "operator_readout",
    "posture_mode",
    "trajectory",
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Render odylith/registry/registry.html component registry dashboard.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="odylith/registry/registry.html")
    parser.add_argument("--manifest", default=registry.DEFAULT_MANIFEST_PATH)
    parser.add_argument("--catalog", default=registry.DEFAULT_CATALOG_PATH)
    parser.add_argument("--ideas-root", default=registry.DEFAULT_IDEAS_ROOT)
    parser.add_argument("--stream", default=registry.DEFAULT_STREAM_PATH)
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local runtime projection store when available for delivery-intelligence slices.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _as_href(output_path: Path, target: Path) -> str:
    rel = os.path.relpath(str(target), start=str(output_path.parent))
    return Path(rel).as_posix()


def _as_portable_href(output_path: Path, token: str) -> str:
    path = Path(str(token or "").strip())
    if not path:
        return ""
    rel = os.path.relpath(str(path), start=str(output_path.parent))
    return Path(rel).as_posix()


def _path_link(
    *,
    repo_root: Path,
    output_path: Path,
    token: str,
) -> dict[str, str]:
    target = _resolve(repo_root, token)
    href = _as_href(output_path, target) if target.exists() else _as_portable_href(output_path, token)
    return {
        "path": str(token or "").strip(),
        "href": href,
    }


def _path_links(
    *,
    repo_root: Path,
    output_path: Path,
    values: Sequence[str],
) -> list[dict[str, str]]:
    return [
        _path_link(repo_root=repo_root, output_path=output_path, token=token)
        for token in values
        if str(token or "").strip()
    ]


def _display_spec_markdown(markdown: str) -> str:
    lines = []
    for raw in str(markdown or "").replace("\r\n", "\n").split("\n"):
        token = raw.strip()
        if token.startswith("<!--") and token.endswith("-->"):
            continue
        lines.append(raw)
    return "\n".join(lines).strip()


def _build_feature_history_timeline_rows(
    *,
    spec_snapshot: registry.ComponentSpecSnapshot,
    spec_ref: str,
    spec_href: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    history = list(spec_snapshot.feature_history)
    ordered_history = sorted(
        enumerate(history),
        key=lambda row: (
            str((row[1] or {}).get("date", "")).strip(),
            int(row[0]),
        ),
        reverse=True,
    )
    artifacts = [{"path": spec_ref, "href": spec_href}] if spec_ref and spec_href else []
    for index, item in ordered_history:
        date_token = str((item or {}).get("date", "")).strip()
        summary = str((item or {}).get("summary", "")).strip()
        plan_refs = item.get("plan_refs", []) if isinstance(item, dict) else []
        workstreams = [
            str(ref.get("workstream_id", "")).strip()
            for ref in plan_refs
            if isinstance(ref, dict) and str(ref.get("workstream_id", "")).strip()
        ]
        rows.append(
            {
                "event_index": -int(index + 1),
                "ts_iso": f"{date_token}T00:00:00Z" if date_token else "",
                "kind": "feature_history",
                "summary": summary,
                "workstreams": workstreams,
                "artifacts": list(artifacts),
                "confidence": "high",
            }
        )
    return rows


def _build_payload(
    *,
    repo_root: Path,
    output_path: Path,
    manifest_path: Path,
    catalog_path: Path,
    ideas_root: Path,
    stream_path: Path,
    runtime_mode: str,
) -> dict[str, Any]:
    diagram_title_lookup: dict[str, str] = {}
    if catalog_path.is_file():
        try:
            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            catalog_payload = {}
        diagram_title_lookup = traceability_ui_lookup.build_diagram_title_lookup(
            diagrams=catalog_payload.get("diagrams", []) if isinstance(catalog_payload, dict) else [],
        )

    runtime_snapshot = odylith_context_engine_store.load_component_registry_snapshot(
        repo_root=repo_root,
        runtime_mode=runtime_mode,
    )
    report = runtime_snapshot.get("report") if isinstance(runtime_snapshot, dict) else None
    if not isinstance(report, registry.ComponentRegistryReport):
        report = registry.build_component_registry_report(
            repo_root=repo_root,
            manifest_path=manifest_path,
            catalog_path=catalog_path,
            ideas_root=ideas_root,
            stream_path=stream_path,
        )
    component_traceability = runtime_snapshot.get("traceability", {}) if isinstance(runtime_snapshot, dict) else {}
    if not isinstance(component_traceability, dict):
        component_traceability = registry.build_component_traceability_index(
            repo_root=repo_root,
            components=report.components,
        )
    spec_snapshot_lookup = runtime_snapshot.get("spec_snapshots", {}) if isinstance(runtime_snapshot, dict) else {}
    if not isinstance(spec_snapshot_lookup, dict):
        spec_snapshot_lookup = {}
    timelines = registry.build_component_timelines(
        component_index=report.components,
        mapped_events=report.mapped_events,
    )
    forensic_coverage = report.forensic_coverage

    rows: list[dict[str, Any]] = []
    by_category: dict[str, int] = {}
    by_qualification: dict[str, int] = {}
    for component_id in sorted(
        report.components,
        key=lambda token: (
            str(report.components[token].name or "").lower(),
            token,
        ),
    ):
        entry = report.components[component_id]
        coverage = forensic_coverage.get(
            component_id,
            registry.ComponentForensicCoverage(
                status="tracked_but_evidence_empty",
                timeline_event_count=0,
                explicit_event_count=0,
                recent_path_match_count=0,
                mapped_workstream_evidence_count=0,
                spec_history_event_count=0,
                empty_reasons=[
                    "no_explicit_event",
                    "no_recent_path_match",
                    "no_mapped_workstream_evidence",
                ],
            ),
        )
        spec_target = _resolve(repo_root, entry.spec_ref) if entry.spec_ref else None
        spec_href = (
            _as_href(output_path, spec_target)
            if spec_target is not None and spec_target.exists()
            else _as_portable_href(output_path, entry.spec_ref)
        )
        spec_snapshot = spec_snapshot_lookup.get(component_id)
        if not isinstance(spec_snapshot, registry.ComponentSpecSnapshot):
            spec_snapshot = (
                registry.load_component_spec_snapshot(spec_path=spec_target)
                if spec_target is not None and spec_target.exists()
                else registry.ComponentSpecSnapshot(title="", last_updated="", feature_history=[], markdown="")
            )
        timeline_rows: list[dict[str, Any]] = []
        for event in timelines.get(component_id, []):
            artifacts = _path_links(
                repo_root=repo_root,
                output_path=output_path,
                values=event.artifacts,
            )
            timeline_rows.append(
                {
                    "event_index": event.event_index,
                    "ts_iso": event.ts_iso,
                    "kind": event.kind,
                    "summary": event.summary,
                    "workstreams": list(event.workstreams),
                    "artifacts": artifacts,
                    "confidence": event.confidence,
                }
            )
        if not timeline_rows and str(coverage.status or "").strip().lower() == "baseline_forensic_only":
            timeline_rows = _build_feature_history_timeline_rows(
                spec_snapshot=spec_snapshot,
                spec_ref=entry.spec_ref,
                spec_href=spec_href,
            )

        rows.append(
            {
                "component_id": entry.component_id,
                "name": entry.name,
                "kind": entry.kind,
                "category": entry.category,
                "qualification": entry.qualification,
                "owner": entry.owner,
                "status": entry.status,
                "what_it_is": entry.what_it_is,
                "why_tracked": entry.why_tracked,
                "spec_ref": entry.spec_ref,
                "spec_href": spec_href,
                "spec_title": spec_snapshot.title,
                "spec_last_updated": spec_snapshot.last_updated,
                "spec_feature_history": list(spec_snapshot.feature_history),
                "spec_markdown": _display_spec_markdown(spec_snapshot.markdown),
                "spec_runbooks": _path_links(
                    repo_root=repo_root,
                    output_path=output_path,
                    values=component_traceability.get(component_id, {}).get("runbooks", []),
                ),
                "spec_developer_docs": _path_links(
                    repo_root=repo_root,
                    output_path=output_path,
                    values=component_traceability.get(component_id, {}).get("developer_docs", []),
                ),
                "skill_trigger_tiers": spec_snapshot.skill_trigger_tiers,
                "skill_trigger_structure": spec_snapshot.skill_trigger_structure,
                "aliases": list(entry.aliases),
                "path_prefixes": list(entry.path_prefixes),
                "workstreams": list(entry.workstreams),
                "diagrams": list(entry.diagrams),
                "subcomponents": list(entry.subcomponents),
                "subcomponent_details": [
                    {
                        "component_id": child_id,
                        "name": report.components.get(child_id).name if report.components.get(child_id) else child_id,
                    }
                    for child_id in entry.subcomponents
                ],
                "product_layer": entry.product_layer,
                "diagram_details": [
                    {
                        "diagram_id": diagram_id,
                        "title": diagram_title_lookup.get(diagram_id, diagram_id),
                    }
                    for diagram_id in entry.diagrams
                ],
                "sources": list(entry.sources),
                "timeline": timeline_rows,
                "timeline_count": len(timeline_rows),
                "forensic_coverage": coverage.as_dict(),
            }
        )
        by_category[entry.category] = int(by_category.get(entry.category, 0) or 0) + 1
        by_qualification[entry.qualification] = int(by_qualification.get(entry.qualification, 0) or 0) + 1

    payload: dict[str, Any] = {
        "title": "Component Registry",
        "subtitle": "Registry compatibility mode",
        "components": rows,
        "delivery_intelligence": _build_registry_delivery_intelligence_payload(
            repo_root=repo_root,
            runtime_mode=runtime_mode,
        ),
        "odylith_runtime": odylith_runtime_surface_summary.load_runtime_surface_summary(repo_root=repo_root),
        "counts": {
            "components": len(rows),
            "events": len(report.mapped_events),
            "meaningful_events": sum(1 for event in report.mapped_events if event.meaningful),
            "mapped_meaningful_events": sum(
                1 for event in report.mapped_events if event.meaningful and event.mapped_components
            ),
            "unmapped_meaningful_events": len(report.unmapped_meaningful_events),
            "forensic_coverage_present": sum(
                1
                for row in rows
                if str(row.get("forensic_coverage", {}).get("status", "")) == "forensic_coverage_present"
            ),
            "baseline_forensic_only": sum(
                1
                for row in rows
                if str(row.get("forensic_coverage", {}).get("status", "")) == "baseline_forensic_only"
            ),
            "tracked_but_evidence_empty": sum(
                1
                for row in rows
                if str(row.get("forensic_coverage", {}).get("status", "")) == "tracked_but_evidence_empty"
            ),
            "by_category": {key: by_category[key] for key in sorted(by_category)},
            "by_qualification": {key: by_qualification[key] for key in sorted(by_qualification)},
        },
        "diagnostics": list(report.diagnostics),
        "candidate_queue": list(report.candidate_queue),
        "consumer_truth_roots": dict(load_consumer_profile(repo_root=repo_root).get("truth_roots", {})),
    }
    return payload


def _build_registry_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    summary = dict(row)
    for key in _REGISTRY_SUMMARY_HEAVY_FIELDS:
        summary.pop(key, None)
    return summary


def _build_registry_detail_row(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row)


def _build_registry_delivery_intelligence_payload(
    *,
    repo_root: Path,
    runtime_mode: str,
) -> dict[str, Any]:
    payload = odylith_context_engine_store.load_delivery_surface_payload(
        repo_root=repo_root,
        surface="registry",
        runtime_mode=runtime_mode,
        buckets=("components",),
    )
    components = payload.get("components")
    if not isinstance(components, Mapping):
        return {}

    projected: dict[str, Any] = {}
    for component_id, snapshot in components.items():
        token = str(component_id or "").strip().lower()
        if not token or not isinstance(snapshot, Mapping):
            continue
        projected[token] = {
            field: snapshot.get(field)
            for field in _REGISTRY_INTELLIGENCE_COMPONENT_FIELDS
            if field in snapshot
        }
    return {"components": projected} if projected else {}


def _chunk_registry_items(
    *,
    items: dict[str, Any],
    shard_size: int,
    file_stem_prefix: str,
) -> tuple[dict[str, str], list[tuple[str, dict[str, Any]]]]:
    manifest: dict[str, str] = {}
    shards: list[tuple[str, dict[str, Any]]] = []
    ordered_items = sorted(
        ((str(key).strip(), value) for key, value in items.items() if str(key).strip()),
        key=lambda item: item[0],
    )
    for index in range(0, len(ordered_items), shard_size):
        shard_items = ordered_items[index : index + shard_size]
        filename = f"{file_stem_prefix}-{(index // shard_size) + 1:03d}.v1.js"
        payload: dict[str, Any] = {}
        for key, value in shard_items:
            manifest[key] = filename
            payload[key] = value
        shards.append((filename, payload))
    return manifest, shards


def _render_html(*, payload: dict[str, Any]) -> str:
    data_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    html = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Component Registry</title>
  __ODYLITH_BRAND_HEAD__
  <style>
    :root {
      --bg-a: #f0f9ff;
      --bg-b: #ecfeff;
      --ink: #0b1324;
      --ink-soft: #334155;
      --ink-muted: #64748b;
      --panel: #ffffff;
      --panel-soft: #f8fafc;
      --line: #c7d2fe;
      --line-strong: #94a3b8;
      --brand: #0f766e;
      --brand-2: #1d4ed8;
      --warn: #b45309;
      --ok: #166534;
      --focus: #2563eb;
      --muted: #64748b;
      --danger: #b42318;
      --warn-bg: #fff7e8;
      --warn-line: #f0d2a8;
      --action-border: #b9c7db;
      --action-bg: #f3f6fb;
      --action-text: #334155;
      --action-border-hover: #9aaec9;
      --action-bg-hover: #e8eef7;
      --action-text-hover: #1e293b;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      min-height: 100%;
      background:
        radial-gradient(circle at 8% -10%, #dbeafe 0%, transparent 42%),
        radial-gradient(circle at 94% 0%, #ccfbf1 0%, transparent 38%),
        linear-gradient(180deg, var(--bg-a), var(--bg-b));
    }
    __ODYLITH_REGISTRY_PAGE_BODY__
    .shell {
      max-width: 1320px;
      margin: 0 auto;
      padding: 22px 18px 34px;
      display: grid;
      gap: 12px;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      min-width: 0;
    }
    __ODYLITH_REGISTRY_HERO_PANEL__
    __ODYLITH_REGISTRY_HEADER_TYPOGRAPHY__
    __ODYLITH_REGISTRY_FILTER_SHELL__
    __ODYLITH_REGISTRY_STICKY_FILTER_BAR__
    .registry-controls {
      position: static;
      top: auto;
    }
    .registry-control {
      display: grid;
      gap: 5px;
      min-width: 0;
    }
    .registry-control-reset {
      display: grid;
      gap: 5px;
      width: fit-content;
      justify-self: end;
      align-self: end;
    }
    .kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 8px;
    }
    __ODYLITH_REGISTRY_KPI_CARD_SURFACE__
    __ODYLITH_KPI_TYPOGRAPHY__
    .kpi-card.warn .kpi-label,
    .kpi-card.warn .kpi-value {
      color: var(--danger);
    }
    __ODYLITH_REGISTRY_WORKSPACE_LAYOUT__
    .list-panel,
    .detail-panel {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      min-width: 0;
    }
    .list-panel {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      max-height: calc(100vh - 188px);
      overflow: hidden;
    }
    __ODYLITH_REGISTRY_LABEL_SURFACE__
    __ODYLITH_REGISTRY_LABEL_TYPOGRAPHY__
    __ODYLITH_REGISTRY_LABEL_TONES__
    .action-chip {
      --action-border: #b9c7db;
      --action-bg: #f3f6fb;
      --action-text: #334155;
      --action-border-hover: #9aaec9;
      --action-bg-hover: #e8eef7;
      --action-text-hover: #1e293b;
    }
    __ODYLITH_REGISTRY_ACTION_CHIP__
    .action-chip.active {
      border-color: #1d4a8f;
      background: #deebff;
      color: #1d4ed8;
    }
    __ODYLITH_REGISTRY_DETAIL_ACTION_CHIP__
    __ODYLITH_REGISTRY_DETAIL_LABEL_CHIP__
    __ODYLITH_REGISTRY_DETAIL_ACTION_TONES__
    .tone-gov {
      --action-border: #8cb8f4;
      --action-bg: #eaf3ff;
      --action-text: #1f4795;
      --action-border-hover: #68a0eb;
      --action-bg-hover: #deebff;
      --action-text-hover: #1d4ed8;
    }
    .tone-infra {
      --action-border: #7ddfd4;
      --action-bg: #e6fbf7;
      --action-text: #0f766e;
      --action-border-hover: #57ccc0;
      --action-bg-hover: #d8f7f1;
      --action-text-hover: #0f766e;
    }
    .tone-data {
      --action-border: #c8a4f8;
      --action-bg: #f4ecff;
      --action-text: #7e22ce;
      --action-border-hover: #b889f3;
      --action-bg-hover: #eddfff;
      --action-text-hover: #7e22ce;
    }
    .tone-engine {
      --action-border: #f3bf84;
      --action-bg: #fff3e2;
      --action-text: #b45309;
      --action-border-hover: #eeaa63;
      --action-bg-hover: #ffeacf;
      --action-text-hover: #b45309;
    }
    .pane-head {
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    __ODYLITH_REGISTRY_SECONDARY_TYPOGRAPHY__
    .search,
    .select {
      min-height: 38px;
      line-height: 1;
    }
    .select {
      font-weight: 700;
      color: #20456b;
    }
    __ODYLITH_REGISTRY_CONTROL_LABEL__
    .component-list {
      margin: 0;
      list-style: none;
      padding: 12px;
      max-height: none;
      min-height: 0;
      overflow: auto;
      display: grid;
      gap: 10px;
      background: linear-gradient(180deg, #ffffff, #fbfdff);
    }
    .list-spacer {
      list-style: none;
      pointer-events: none;
    }
    .group-head {
      padding: 0 2px;
    }
    .component-btn {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel-soft);
      text-align: left;
      padding: 10px 11px;
      cursor: pointer;
      display: grid;
      gap: 6px;
    }
    .component-btn:hover {
      border-color: #8fb2e6;
    }
    .component-btn.active {
      border-color: var(--line-strong);
      background: #eaf3ff;
    }
    .component-card-title {
      color: #22496f;
    }
    __ODYLITH_REGISTRY_DETAIL_IDENTITY_TYPOGRAPHY__
    .component-meta {
      margin: 0;
    }
    .inline {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }
    .component-btn .label {
      padding: 4px 7px;
    }
    .detail-shell {
      padding: 16px;
      display: grid;
      gap: 12px;
      border-bottom: 1px solid var(--line);
    }
    .summary-strip {
      border: 1px solid #d6e3f7;
      border-radius: 10px;
      background: linear-gradient(180deg, #f8fbff, #ffffff);
      padding: 9px 11px;
      display: grid;
      gap: 7px;
    }
    .summary-row {
      margin: 0;
    }
    .trigger-block {
      display: grid;
      gap: 4px;
    }
    .trigger-expand {
      border: 1px solid #d9e6fa;
      border-radius: 8px;
      background: #ffffff;
      overflow: hidden;
    }
    .trigger-expand > summary {
      list-style: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      padding: 8px 10px;
      transition: background-color 120ms ease;
    }
    .trigger-expand > summary:hover {
      background: #f7fbff;
    }
    .trigger-expand[open] > summary {
      border-bottom: 1px solid #e3ecf9;
      background: #f7fbff;
    }
    .trigger-list {
      margin: 0;
      padding: 0 10px 10px 28px;
      list-style: square;
      display: grid;
      gap: 4px;
      color: #2b4667;
    }
    .trigger-list li {
      margin: 0;
      line-height: 1.4;
    }
    .spec-expand {
      border: 1px solid #d6e3f7;
      border-radius: 10px;
      background: linear-gradient(180deg, #f9fcff, #ffffff);
      overflow: hidden;
    }
    .spec-expand > summary {
      list-style: none;
      cursor: pointer;
      padding: 10px 12px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
      border-bottom: 1px solid #e3ecf9;
      transition: background-color 120ms ease;
    }
    .spec-expand > summary:hover {
      background: #f3f8ff;
    }
    .spec-summary-main {
      margin: 0;
      display: flex;
      align-items: center;
    }
    .spec-summary-title {
    }
    .spec-summary-meta {
      display: inline-flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 6px;
      align-items: center;
    }
    .spec-expand[open] > summary {
      border-bottom-color: #d8e5f7;
    }
    .spec-expand-body {
      padding: 10px 12px;
      display: grid;
      gap: 10px;
    }
    .spec-links-block {
      display: grid;
      gap: 6px;
    }
    .spec-doc {
      border: 1px solid #e3ecf9;
      border-radius: 8px;
      background: #ffffff;
      padding: 10px;
      display: grid;
      gap: 8px;
    }
    .spec-doc h3,
    .spec-doc h4,
    .spec-doc h5 {
      margin: 0;
    }
    .spec-doc p {
      margin: 0;
      font-size: 13px;
      line-height: 1.4;
      color: #2d496a;
    }
    .spec-doc ul {
      margin: 0;
      padding-left: 18px;
      display: block;
      list-style: disc;
      color: #2d496a;
      font-size: 13px;
      line-height: 1.35;
    }
    .spec-doc li {
      margin: 0 0 4px;
    }
    .spec-doc li:last-child {
      margin-bottom: 0;
    }
    .spec-doc li > ul {
      margin-top: 4px;
      padding-left: 18px;
      list-style-type: circle;
    }
    .spec-doc li > ul > li > ul {
      list-style-type: square;
    }
    .spec-doc code {
      background: #f3f6fb;
      border: 1px solid #d9e6fa;
      border-radius: 4px;
      padding: 0 4px;
    }
    .spec-table-scroll {
      overflow-x: auto;
      border: 1px solid #dbe6f7;
      border-radius: 8px;
      background: #f8fbff;
    }
    .spec-table {
      width: 100%;
      min-width: 640px;
      border-collapse: collapse;
      font-size: 12px;
      line-height: 1.35;
      color: #2d496a;
      background: #ffffff;
    }
    .spec-table th,
    .spec-table td {
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
      border-bottom: 1px solid #dbe6f7;
      border-right: 1px solid #e3ecf9;
    }
    .spec-table th:last-child,
    .spec-table td:last-child {
      border-right: 0;
    }
    .spec-table thead th {
      background: #f1f6ff;
      color: #1f3b5b;
      font-weight: 700;
      white-space: nowrap;
    }
    .spec-table tbody tr:last-child td {
      border-bottom: 0;
    }
    __ODYLITH_REGISTRY_CODE_TYPOGRAPHY__
    .answers {
      border: 1px solid #dbeafe;
      border-radius: 14px;
      background: linear-gradient(180deg, #f8fbff, #ffffff);
      padding: 12px;
      display: grid;
      gap: 10px;
    }
    __ODYLITH_REGISTRY_BRIEF_LABELS__
    .answers-head {
      padding: 0 0 2px;
    }
    .answers-list {
      display: grid;
      gap: 10px;
    }
    __ODYLITH_REGISTRY_OPERATOR_READOUT_LAYOUT__
    __ODYLITH_REGISTRY_OPERATOR_READOUT_LABEL__
    __ODYLITH_REGISTRY_OPERATOR_READOUT_COPY__
    __ODYLITH_REGISTRY_OPERATOR_READOUT_META__
    .context-section {
      border: 1px solid #d6e3f7;
      border-radius: 14px;
      background: linear-gradient(180deg, #f8fbff, #ffffff);
      overflow: hidden;
    }
    .context-section > summary {
      cursor: pointer;
      list-style: none;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 11px 12px;
      background: #f3f8ff;
    }
    .context-section[open] > summary {
      border-bottom: 1px solid #d8e4f7;
    }
    .context-head {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }
    .context-head-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      justify-content: flex-end;
      align-items: center;
    }
    .context-body {
      display: grid;
    }
    .context-row {
      display: grid;
      grid-template-columns: 190px 56px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      padding: 10px 12px;
      border-top: 1px solid #e4ebf8;
    }
    .context-row:first-child { border-top: none; }
    .context-title {
      padding-top: 3px;
    }
    .context-count {
      text-align: right;
      line-height: 1;
      padding-top: 2px;
    }
    .context-values {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
      min-height: 26px;
    }
    .context-values.block {
      display: grid;
      gap: 6px;
    }
    .desc {
      margin: 0;
    }
    .empty {
      margin: 0;
    }
    .timeline-head {
      border-bottom: 1px solid var(--line);
      padding: 12px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .timeline {
      margin: 0;
      list-style: none;
      padding: 12px 14px 14px;
      display: grid;
      gap: 12px;
      background: linear-gradient(180deg, #ffffff, #fcfeff);
      min-width: 0;
    }
    .event {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #ffffff;
      padding: 11px;
      display: grid;
      gap: 8px;
      min-width: 0;
    }
    .event > * {
      min-width: 0;
    }
    .event-top {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
    }
    .event-summary {
      margin: 0;
      overflow-wrap: anywhere;
    }
    .artifact-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
      max-width: 100%;
    }
    .artifact {
      display: inline-flex;
      align-items: flex-start;
      border: 1px solid #d4e2f7;
      border-radius: 8px;
      min-height: 28px;
      padding: 6px 10px;
      text-decoration: none;
      background: #f5f9ff;
      box-sizing: border-box;
      min-width: 0;
      max-width: 100%;
      white-space: normal;
      overflow-wrap: anywhere;
      word-break: break-word;
      line-height: 1.3;
      flex: 0 1 auto;
    }
    .diagnostics {
      border: 1px solid var(--warn-line);
      border-radius: 10px;
      background: var(--warn-bg);
      overflow: hidden;
      display: inline-block;
      width: fit-content;
      max-width: 100%;
    }
    .diagnostics > summary {
      cursor: pointer;
      list-style: none;
      padding: 8px 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .diagnostics > summary::-webkit-details-marker { display: none; }
    .diag-list {
      margin: 0;
      list-style: none;
      padding: 0 10px 10px;
      display: grid;
      gap: 6px;
      max-height: 200px;
      overflow: auto;
      min-width: min(640px, calc(100vw - 72px));
    }
    .diag-item {
      border: 1px solid #f2dfc1;
      border-radius: 8px;
      background: #fff;
      padding: 7px 8px;
    }
    __ODYLITH_REGISTRY_TOOLTIP_SURFACE__
    __ODYLITH_REGISTRY_CONTEXT_HEADINGS__
    __ODYLITH_REGISTRY_AUX_BUTTON_TYPOGRAPHY__
    __ODYLITH_REGISTRY_AUX_COPY__
    __ODYLITH_REGISTRY_CONTENT_COPY__
    @media (max-width: 1080px) {
      .workspace {
        grid-template-columns: 1fr;
      }
      .registry-controls {
        grid-template-columns: 1fr 1fr;
      }
      .registry-control-search {
        grid-column: 1 / -1;
      }
      .registry-control-reset {
        justify-self: start;
      }
      .list-panel {
        max-height: min(48vh, 480px);
      }
      .component-list {
        max-height: none;
      }
    }
    @media (max-width: 760px) {
      .registry-controls {
        grid-template-columns: 1fr;
      }
      .registry-control-search {
        grid-column: auto;
      }
      .context-section > summary {
        grid-template-columns: 1fr;
      }
      .context-row {
        grid-template-columns: 1fr;
      }
      .context-count {
        text-align: left;
      }
      .context-head-actions {
        justify-content: flex-start;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="registry-hero">
      <p class="hero-overline">Component Ownership and Evidence Map</p>
      <h1 class="registry-title">Component Registry</h1>
      <p class="registry-subtitle">See what exists, who owns it, and which specs, workstreams, and diagrams back it.</p>
      <div class="kpis" id="kpis"></div>
    </section>

    <section class="registry-filters-shell">
      <div class="registry-controls">
        <div class="registry-control registry-control-search">
          <label class="control-title" for="search">Search</label>
          <input id="search" class="search" placeholder="Search component, alias, owner..." />
        </div>
        <div class="registry-control">
          <label class="control-title" for="categoryFilter">Category</label>
          <select id="categoryFilter" class="select"></select>
        </div>
        <div class="registry-control">
          <label class="control-title" for="qualificationFilter">Qualification</label>
          <select id="qualificationFilter" class="select"></select>
        </div>
        <div class="registry-control registry-control-reset">
          <span class="control-title">Filters</span>
          <button id="resetFilters" type="button" class="action-chip">Reset</button>
        </div>
      </div>
      <details id="diagnostics" class="diagnostics" hidden>
        <summary>Diagnostics</summary>
        <ul id="diagList" class="diag-list"></ul>
      </details>
    </section>

    <section class="workspace">
      <aside class="list-panel">
        <div class="pane-head">
          <span>Components</span>
        </div>
        <ul id="componentList" class="component-list"></ul>
      </aside>

        <section class="detail-panel">
          <div id="detail" class="detail-shell"></div>
        <div id="chronology-anchor" class="timeline-head">
          <span>Forensic Evidence</span>
          <span id="timelineCount">0 events</span>
        </div>
        <ul id="timeline" class="timeline"></ul>
      </section>
    </section>
  </main>

  <script id="registryData" type="application/json">__DATA__</script>
  <script>
    const DATA = JSON.parse(document.getElementById("registryData").textContent || "{}");
    const payload = DATA;
    const assetLoadCache = new Map();
    const listEl = document.getElementById("componentList");
    const detailEl = document.getElementById("detail");
    const timelineEl = document.getElementById("timeline");
    const timelineCountEl = document.getElementById("timelineCount");
    const searchEl = document.getElementById("search");
    const resetFiltersEl = document.getElementById("resetFilters");
    const kpisEl = document.getElementById("kpis");
    const qualificationFilterEl = document.getElementById("qualificationFilter");
    const categoryFilterEl = document.getElementById("categoryFilter");
    const diagnosticsEl = document.getElementById("diagnostics");
    const diagListEl = document.getElementById("diagList");

    const allComponents = Array.isArray(payload.components) ? payload.components.slice() : [];
    const REGISTRY_LIST_WINDOW_THRESHOLD = 160;
    const REGISTRY_LIST_OVERSCAN = 20;
    const REGISTRY_LIST_ROW_HEIGHT = 86;
    const REGISTRY_LIST_HEADER_HEIGHT = 30;
    let latestRenderedComponents = [];
    let latestListWindowKey = "";
    let listScrollFrame = 0;
    let activeQualification = "all";
    let activeCategory = "all";

    function loadScriptAsset(href) {
      const token = String(href || "").trim();
      if (!token) return Promise.resolve();
      const resolvedHref = new URL(token, window.location.href).toString();
      if (assetLoadCache.has(resolvedHref)) {
        return assetLoadCache.get(resolvedHref);
      }
      const promise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = resolvedHref;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`failed to load asset ${resolvedHref}`));
        document.head.appendChild(script);
      });
      assetLoadCache.set(resolvedHref, promise);
      return promise;
    }

    function detailManifest() {
      const manifest = payload.detail_manifest;
      return manifest && typeof manifest === "object" ? manifest : {};
    }

    async function loadDetailEntry(componentId) {
      const token = String(componentId || "").trim().toLowerCase();
      if (!token) return null;
      const loaded = window.__ODYLITH_REGISTRY_DETAIL_SHARDS__ || {};
      if (loaded[token] && typeof loaded[token] === "object") {
        return loaded[token];
      }
      const shardHref = String(detailManifest()[token] || "").trim();
      if (!shardHref) return null;
      await loadScriptAsset(shardHref);
      const resolved = window.__ODYLITH_REGISTRY_DETAIL_SHARDS__ || {};
      return resolved[token] && typeof resolved[token] === "object" ? resolved[token] : null;
    }

    async function loadRuntimePayload(path, params = {}) {
      const dataSource = payload.data_source && typeof payload.data_source === "object" ? payload.data_source : {};
      const base = String(dataSource.runtime_base_url || "").trim();
      const protocol = String(window.location.protocol || "").toLowerCase();
      if (!base || protocol === "file:") return null;
      try {
        const url = new URL(path.replace(/^\/+/, ""), base.endsWith("/") ? base : `${base}/`);
        Object.entries(params || {}).forEach(([key, value]) => {
          if (value === undefined || value === null || value === "") return;
          url.searchParams.set(key, String(value));
        });
        const response = await fetch(url.toString(), { headers: { "Accept": "application/json" } });
        if (!response.ok) return null;
        return await response.json();
      } catch (_error) {
        return null;
      }
    }

    function createStaticSnapshotRegistryDataSource() {
      return {
        backend: "staticSnapshot",
        async loadManifest() {
          return detailManifest();
        },
        async loadList(_params = {}) {
          return allComponents.slice();
        },
        async loadDetail(id) {
          return loadDetailEntry(id);
        },
        async loadDocument(_request = {}) {
          return null;
        },
        prefetch(id) {
          void loadDetailEntry(id);
        },
      };
    }

    function createRuntimeRegistryDataSource() {
      const fallback = createStaticSnapshotRegistryDataSource();
      return {
        backend: "runtime",
        async loadManifest() {
          const runtimePayload = await loadRuntimePayload("surfaces/registry/manifest");
          if (runtimePayload && typeof runtimePayload === "object") return runtimePayload;
          return fallback.loadManifest();
        },
        async loadList(params = {}) {
          const runtimePayload = await loadRuntimePayload("surfaces/registry/list", params);
          if (runtimePayload && Array.isArray(runtimePayload.components)) return runtimePayload.components;
          return fallback.loadList(params);
        },
        async loadDetail(id) {
          const runtimePayload = await loadRuntimePayload("surfaces/registry/detail", { component: id });
          if (runtimePayload && typeof runtimePayload === "object") return runtimePayload;
          return fallback.loadDetail(id);
        },
        async loadDocument(request = {}) {
          const runtimePayload = await loadRuntimePayload("surfaces/registry/document", request);
          if (runtimePayload && typeof runtimePayload === "object") return runtimePayload;
          return fallback.loadDocument(request);
        },
        prefetch(id) {
          void this.loadDetail(id);
        },
      };
    }

    function createRegistryDataSource() {
      const dataSource = payload.data_source && typeof payload.data_source === "object" ? payload.data_source : {};
      const preferred = String(dataSource.preferred_backend || "").trim();
      if (preferred === "runtime") {
        return createRuntimeRegistryDataSource();
      }
      return createStaticSnapshotRegistryDataSource();
    }

    const registryDataSource = createRegistryDataSource();

    __ODYLITH_REGISTRY_QUICK_TOOLTIP_RUNTIME__

    function escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function humanizeToken(token) {
      return String(token || "")
        .replace(/_/g, " ")
        .replace(/-/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .replace(/\b\w/g, (m) => m.toUpperCase()) || "Unknown";
    }

    function pluralize(count, singular, plural) {
      return Number(count) === 1 ? singular : plural;
    }

    function clipText(value, limit = 180) {
      const raw = String(value || "").replace(/\s+/g, " ").trim();
      if (!raw || raw.length <= limit) return raw;
      const hard = Math.max(16, limit - 3);
      const boundary = raw.lastIndexOf(" ", hard);
      const cut = boundary > Math.floor(hard * 0.6) ? boundary : hard;
      return `${raw.slice(0, cut).replace(/[ ,;:-]+$/, "")}...`;
    }

    function normalizedEventKind(event) {
      return String(event && event.kind || "").trim().toLowerCase();
    }

    function isWorkspaceActivityEvent(event) {
      return normalizedEventKind(event) === "workspace_activity";
    }

    function isBaselineTimelineEvent(event) {
      return normalizedEventKind(event) === "feature_history";
    }

    function isExplicitTimelineEvent(event) {
      const kind = normalizedEventKind(event);
      return Boolean(kind) && kind !== "workspace_activity" && kind !== "feature_history";
    }

    function isSyntheticTimelineEvent(event) {
      return isWorkspaceActivityEvent(event);
    }

    function ensureSentence(value, fallback = "") {
      const raw = String(value || "").replace(/\s+/g, " ").trim();
      if (!raw) return String(fallback || "").trim();
      return /[.!?]$/.test(raw) ? raw : `${raw}.`;
    }

    function naturalList(values) {
      const items = (Array.isArray(values) ? values : [])
        .map((value) => String(value || "").trim())
        .filter(Boolean);
      if (!items.length) return "";
      if (items.length === 1) return items[0];
      if (items.length === 2) return `${items[0]} and ${items[1]}`;
      return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
    }

    function forensicCoverageLabel(coverage) {
      const status = String(coverage && coverage.status || "").trim().toLowerCase();
      if (status === "forensic_coverage_present") return "Forensic coverage present";
      if (status === "baseline_forensic_only") return "Baseline forensic only";
      if (status === "tracked_but_evidence_empty") return "Tracked but evidence-empty";
      return "Forensic coverage unknown";
    }

    function forensicCoverageReasonLabel(reason) {
      const token = String(reason || "").trim().toLowerCase();
      if (token === "no_explicit_event") return "no explicit event";
      if (token === "no_recent_path_match") return "no recent path match";
      if (token === "no_mapped_workstream_evidence") return "no mapped workstream evidence";
      return humanizeToken(token);
    }

    function forensicCoverageSummary(coverage) {
      const row = coverage && typeof coverage === "object" ? coverage : {};
      const status = String(row.status || "").trim().toLowerCase();
      const label = forensicCoverageLabel(row);
      const emptyReasons = Array.isArray(row.empty_reasons) ? row.empty_reasons.map(forensicCoverageReasonLabel).filter(Boolean) : [];
      const specHistoryCount = Number(row.spec_history_event_count || 0);
      if (status === "tracked_but_evidence_empty") {
        return emptyReasons.length
          ? `${label}: ${ensureSentence(naturalList(emptyReasons))}`
          : `${label}: no mapped forensic evidence channels are currently attached.`;
      }
      if (status === "baseline_forensic_only") {
        const historySummary = `${specHistoryCount} documented spec history ${pluralize(specHistoryCount, "checkpoint", "checkpoints")}`;
        return emptyReasons.length
          ? `${label}: ${historySummary}. Live evidence gaps: ${ensureSentence(naturalList(emptyReasons))}`
          : `${label}: ${historySummary}.`;
      }
      const explicitCount = Number(row.explicit_event_count || 0);
      const recentPathMatchCount = Number(row.recent_path_match_count || 0);
      const mappedWorkstreamEvidenceCount = Number(row.mapped_workstream_evidence_count || 0);
      return `${label}: explicit events ${explicitCount} · recent path matches ${recentPathMatchCount} · mapped workstream evidence ${mappedWorkstreamEvidenceCount} · spec history checkpoints ${specHistoryCount}.`;
    }

    function intelligenceConfidence(explicitCount, syntheticCount, workstreamCount, baselineCount = 0) {
      const explicit = Number(explicitCount || 0);
      const synthetic = Number(syntheticCount || 0);
      const workstreams = Number(workstreamCount || 0);
      const baseline = Number(baselineCount || 0);
      if (explicit >= 2 && workstreams > 0) return "High";
      if (explicit >= 1) return "Medium";
      if (synthetic > 0 || workstreams > 0) return "Low";
      if (baseline > 0) return "Low";
      return "Low";
    }

    function intelligenceConfidenceBasis(confidence, explicitCount, syntheticCount, workstreamCount, baselineCount = 0) {
      const explicit = Number(explicitCount || 0);
      const synthetic = Number(syntheticCount || 0);
      const workstreams = Number(workstreamCount || 0);
      const baseline = Number(baselineCount || 0);
      if (confidence === "High") {
        return `High confidence because ${explicit} explicit checkpoint${explicit === 1 ? "" : "s"} and ${workstreams} linked workstream${workstreams === 1 ? "" : "s"} are present.`;
      }
      if (confidence === "Medium") {
        return `Medium confidence because explicit evidence exists, but the picture still relies on a limited checkpoint set${synthetic > 0 ? " mixed with inferred local change" : ""}.`;
      }
      if (synthetic > 0) {
        return "Low confidence because the read is driven mainly by inferred local change rather than explicit governance checkpoints.";
      }
      if (baseline > 0) {
        return `Low confidence because Registry currently has ${baseline} documented spec history ${pluralize(baseline, "checkpoint", "checkpoints")} but no live mapped forensic evidence yet.`;
      }
      return "Low confidence because Registry does not yet have enough mapped evidence to form a strong narrative.";
    }

    function latestExplicitEvent(events) {
      return (Array.isArray(events) ? events : []).find((event) => isExplicitTimelineEvent(event)) || null;
    }

    function basenamePath(value) {
      const raw = String(value || "").trim().replace(/\\/g, "/");
      if (!raw) return "";
      const parts = raw.split("/").filter(Boolean);
      return parts.length ? parts[parts.length - 1] : raw;
    }

    function truthRootToken(value) {
      return String(value || "").trim().replace(/\\/g, "/").replace(/^\.\//, "").replace(/\/+$/, "");
    }

    function workspaceArtifactLabel(path) {
      const raw = String(path || "").trim();
      const truthRoots = DATA.consumer_truth_roots && typeof DATA.consumer_truth_roots === "object"
        ? DATA.consumer_truth_roots
        : {};
      const componentSpecsRoot = truthRootToken(truthRoots.component_specs);
      const runbooksRoot = truthRootToken(truthRoots.runbooks);
      if (!raw) return "";
      if (raw.startsWith("contracts/") || raw.startsWith("odylith/runtime/contracts/")) return "contract artifacts";
      if (raw.startsWith("odylith/registry/source/components/") && raw.endsWith("/FORENSICS.v1.json")) return "component forensics";
      if (componentSpecsRoot && componentSpecsRoot !== "odylith" && raw.startsWith(`${componentSpecsRoot}/`)) return "component spec";
      if (raw.startsWith("odylith/registry/source/components/") && raw.endsWith("/CURRENT_SPEC.md")) return "component spec";
      if (raw.startsWith("odylith/") && (raw.endsWith("/SPEC.md") || raw.endsWith("_SPEC.md"))) return "component spec";
      if (runbooksRoot && runbooksRoot !== "odylith" && raw.startsWith(`${runbooksRoot}/`)) return "runbook";
      if (raw.startsWith("src/odylith/runtime/")) return "odylith product code";
      if (raw.startsWith("odylith/")) return "odylith artifacts";
      return basenamePath(raw);
    }

    function compactNarrativeSummary(value, limit = 110) {
      const raw = String(value || "").replace(/\s+/g, " ").trim();
      if (!raw) return "";
      const prefix = "Recent workspace activity across tracked paths:";
      if (!raw.toLowerCase().startsWith(prefix.toLowerCase())) {
        return clipText(raw, limit);
      }

      let remainder = raw.slice(prefix.length).trim();
      let moreCount = 0;
      const moreMatch = remainder.match(/\+\s*(\d+)\s+more$/i);
      if (moreMatch) {
        moreCount = Number(moreMatch[1] || 0);
        remainder = remainder.slice(0, moreMatch.index).trim().replace(/[,\s]+$/, "");
      }

      const rawPaths = remainder
        .split(",")
        .map((token) => String(token || "").trim())
        .filter(Boolean);
      const labels = [];
      const seen = new Set();
      rawPaths.forEach((path) => {
        const label = workspaceArtifactLabel(path);
        if (!label || seen.has(label)) return;
        seen.add(label);
        labels.push(label);
      });
      const preview = labels.slice(0, 3);
      if (!preview.length) {
        return moreCount > 0
          ? `tracked component artifacts changed (+${moreCount} more)`
          : "tracked component artifacts changed";
      }
      const overflow = Math.max(0, labels.length - preview.length) + moreCount;
      return overflow > 0
        ? `${naturalList(preview)} changed (+${overflow} more)`
        : `${naturalList(preview)} changed`;
    }

    function summarizeOperatingShift(context) {
      const componentName = String(context.componentName || "This component").trim() || "This component";
      const latestObservedSummary = compactNarrativeSummary(context.latestSummary || "", 120);
      const latestExplicitSummary = compactNarrativeSummary(
        context.latestExplicit && context.latestExplicit.summary || "",
        120,
      );
      const primaryWorkstream = String(context.primaryWorkstream || "").trim();
      if (!context.latestEvent) {
        return `No mapped signal exists yet for ${componentName}; Registry is still under-observing this component.`;
      }
      if (!context.explicitCount && context.syntheticCount > 0) {
        return `Execution is touching ${componentName}, but the decision trail is missing. Latest observed move: ${latestObservedSummary}`;
      }
      if (context.hasImplementationSignal && context.hasDecisionSignal) {
        return primaryWorkstream
          ? `${componentName} is in governed execution on ${primaryWorkstream}. Latest explicit move: ${latestExplicitSummary || latestObservedSummary}`
          : `${componentName} is in governed execution, but the active workstream binding is incomplete. Latest explicit move: ${latestExplicitSummary || latestObservedSummary}`;
      }
      if (context.hasImplementationSignal) {
        return primaryWorkstream
          ? `${componentName} has moved into implementation on ${primaryWorkstream}. Latest explicit move: ${latestExplicitSummary || latestObservedSummary}`
          : `${componentName} has moved into implementation, but Registry still lacks a clean workstream binding. Latest explicit move: ${latestExplicitSummary || latestObservedSummary}`;
      }
      if (context.hasDecisionSignal) {
        return primaryWorkstream
          ? `${componentName} is being reshaped by active governance decisions on ${primaryWorkstream}. Latest decision: ${latestExplicitSummary || latestObservedSummary}`
          : `${componentName} is being reshaped by governance decisions ahead of implementation. Latest decision: ${latestExplicitSummary || latestObservedSummary}`;
      }
      if (context.latestExplicit) {
        return `${componentName} is active through explicit execution checkpoints. Latest checkpoint: ${latestExplicitSummary || latestObservedSummary}`;
      }
      return `${componentName} has recent mapped activity, but Registry still lacks a clear operating narrative. Latest signal: ${latestObservedSummary}`;
    }

    function summarizeDeliveryImpact(context) {
      const whyTracked = ensureSentence(
        context.whyTracked,
        "This component is tracked for delivery governance accountability."
      );
      if (!context.latestEvent) {
        return whyTracked;
      }
      if (!context.explicitCount && context.syntheticCount > 0) {
        return `${whyTracked} Right now that impact is visible through execution churn rather than an explicit governance checkpoint.`;
      }
      if (context.primaryWorkstream) {
        return `${whyTracked} Current delivery pressure is concentrating on ${context.primaryWorkstream}${context.workstreamOverflow > 0 ? ` and ${context.workstreamOverflow} related workstream${context.workstreamOverflow === 1 ? "" : "s"}` : ""}.`;
      }
      return `${whyTracked} The impact is real, but the active workstream boundary is still weakly attached in the evidence trail.`;
    }

    function summarizeGovernancePosture(context) {
      if (!context.latestEvent) {
        return "No governance posture can be inferred yet because Registry has no mapped component evidence.";
      }
      if (!context.explicitCount && context.syntheticCount > 0) {
        return "Weak posture: active edits are present, but no explicit decision, implementation, or execution checkpoint is mapped yet.";
      }
      if (context.explicitCount > 0 && !context.allWorkstreams.length) {
        return "Partial posture: explicit checkpoints exist, but they are not bound to a workstream, so cross-surface traceability is incomplete.";
      }
      if (context.explicitCount > 0 && context.syntheticCount > context.explicitCount) {
        return "Mixed posture: explicit governance exists, but local change is still outrunning the clean decision trail.";
      }
      if (context.explicitCount > 0 && context.allWorkstreams.length) {
        return "Strong posture: explicit checkpoints, workstream linkage, and forensic evidence are aligned for this component.";
      }
      return "Mapped activity is present, but the governance picture is still incomplete.";
    }

    function summarizeCrossSurfaceImpact(context) {
      const surfaces = [];
      if (context.workstreamPreview.length) {
        surfaces.push(`Radar workstreams ${context.workstreamPreview.join(", ")}${context.workstreamOverflow > 0 ? ` (+${context.workstreamOverflow})` : ""}`);
      }
      if (context.diagramPreview.length) {
        surfaces.push(`Atlas diagrams ${context.diagramPreview.join(", ")}${context.diagramOverflow > 0 ? ` (+${context.diagramOverflow})` : ""}`);
      }
      if (context.timelineEvents.length) {
        surfaces.push("Compass-linked evidence");
      }
      if (context.specPath) {
        surfaces.push("Registry living spec");
      }
      if (context.specRunbooks.length) {
        surfaces.push("runbooks");
      }
      if (context.specDeveloperDocs.length) {
        surfaces.push("developer docs");
      }
      if (!surfaces.length) {
        return "Cross-surface traceability is still thin; this component currently resolves mainly inside Registry.";
      }
      return `This component currently propagates into ${naturalList(surfaces)}.`;
    }

    function summarizeNextMove(context) {
      if (!context.latestEvent) {
        return "Capture the first explicit component checkpoint before relying on Registry for delivery interpretation.";
      }
      if (!context.explicitCount && context.syntheticCount > 0) {
        return "Log an explicit Compass decision or implementation checkpoint and attach the correct workstream before treating this as governed progress.";
      }
      if (context.explicitCount > 0 && !context.allWorkstreams.length) {
        return "Bind the next explicit checkpoint to the active workstream so Radar, Atlas, and Registry stay aligned.";
      }
      if (
        context.hasImplementationSignal &&
        !context.hasDecisionSignal &&
        (context.categoryToken === "governance_surface" || context.categoryToken === "governance_engine" || context.categoryToken === "control_gate")
      ) {
        return "Backfill explicit rationale if this implementation changes operator workflow, policy behavior, or delivery boundaries.";
      }
      if (context.hasDecisionSignal && !context.hasImplementationSignal && context.syntheticCount > 0) {
        return "Close the gap between decision capture and active edits before this component drifts into unguided implementation.";
      }
      return "Keep explicit checkpoints current as work closes and use Forensic Evidence to verify the final delivery state.";
    }

    function deliveryIntelligencePayload() {
      const payload = DATA.delivery_intelligence;
      return payload && typeof payload === "object" ? payload : {};
    }

    function intelligenceScope(scopeType, scopeId) {
      const token = String(scopeId || "").trim();
      if (!token) return null;
      const payload = deliveryIntelligencePayload();
      const bucket = payload[`${scopeType}s`];
      if (!bucket || typeof bucket !== "object") return null;
      const row = bucket[token];
      return row && typeof row === "object" ? row : null;
    }

    function componentIntelligenceSnapshot(componentId) {
      return intelligenceScope("component", componentId);
    }

    function operatorReadout(snapshot) {
      const readout = snapshot && typeof snapshot.operator_readout === "object" ? snapshot.operator_readout : {};
      return readout && typeof readout === "object" ? readout : {};
    }

    __ODYLITH_REGISTRY_OPERATOR_READOUT_RUNTIME_JS__

    function proofHref(ref, componentId, primaryWorkstream) {
      const row = ref && typeof ref === "object" ? ref : {};
      const surface = String(row.surface || "").trim().toLowerCase();
      const value = String(row.value || "").trim();
      if (surface === "shell" || surface === "tooling") return "../index.html";
      if (surface === "compass") return hrefCompass(primaryWorkstream || value);
      if (surface === "atlas") return hrefAtlas(primaryWorkstream || "", value);
      if (surface === "radar") return hrefRadar(primaryWorkstream || value);
      if (surface === "registry") return hrefRegistry(componentId || value.replace(/^component:/, ""));
      return "../index.html?tab=registry";
    }

    function registryComponentHref(componentId) {
      const token = String(componentId || "").trim();
      if (!token) return "../index.html?tab=registry";
      return `../index.html?tab=registry&component=${encodeURIComponent(token)}`;
    }

    function renderProofRefs(refs, componentId, primaryWorkstream) {
      return renderOperatorReadoutProofLinks(
        refs,
        (row) => proofHref(row, componentId, primaryWorkstream),
      );
    }

    function toneClassForCategory(category) {
      const token = String(category || "").trim().toLowerCase();
      if (token === "governance_surface") return "tone-gov";
      if (token === "governance_engine" || token === "control_gate") return "tone-engine";
      if (token === "infrastructure") return "tone-infra";
      if (token === "data") return "tone-data";
      return "";
    }

    function categoryDescription(category) {
      const token = String(category || "").trim().toLowerCase();
      if (token === "governance_surface") return "User-facing governance surfaces for planning, architecture, execution, and registry views.";
      if (token === "governance_engine") return "Shared governance intelligence and orchestration logic used across surfaces.";
      if (token === "control_gate") return "Validation and policy gates that enforce fail-closed governance behavior.";
      if (token === "infrastructure") return "Underlying cloud/runtime systems that host and execute the platform.";
      if (token === "data") return "Data-plane entities such as topics and interface contracts.";
      return "Component category used for inventory grouping.";
    }

    function productLayerLabel(layer) {
      const token = String(layer || "").trim().toLowerCase();
      if (!token) return "Unspecified";
      if (token === "shell_host") return "Shell Host";
      if (token === "evidence_surface") return "Evidence Surface";
      if (token === "memory_retrieval") return "Memory / Retrieval";
      if (token === "intelligence") return "Intelligence";
      if (token === "agent_execution") return "Agent Execution";
      if (token === "cli_bootstrap") return "CLI / Bootstrap";
      if (token === "optional_remote_control_plane") return "Optional Remote Control Plane";
      if (token === "consumer_distro") return "Consumer Distro";
      return token.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
    }

    function productLayerDescription(layer) {
      const token = String(layer || "").trim().toLowerCase();
      if (token === "shell_host") return "Owns the top-level Odylith shell and host routing surface.";
      if (token === "evidence_surface") return "Owns one of the operator-facing evidence and inspection surfaces.";
      if (token === "memory_retrieval") return "Owns the derived local memory, sparse recall, packet compaction, and dense-context telemetry substrate.";
      if (token === "intelligence") return "Owns case-building, reasoning, or remediation intelligence inside Odylith.";
      if (token === "agent_execution") return "Owns bounded agent routing, orchestration, or host-execution behavior.";
      if (token === "cli_bootstrap") return "Owns install, bootstrap, or operator command-entry boundaries for Odylith.";
      if (token === "optional_remote_control_plane") return "Owns optional remote/public-admin control-plane behavior attached to Odylith.";
      if (token === "consumer_distro") return "Owns consumer-specific compatibility readers and distro behavior over the neutral Odylith core.";
      return "Odylith product-layer placement for this component.";
    }

    function qualificationDescription(token) {
      const normalized = String(token || "").trim().toLowerCase();
      if (normalized === "curated") return "Approved first-class component record in the manifest.";
      if (normalized === "candidate") return "Reviewed candidate awaiting final lifecycle qualification.";
      return "Component qualification level.";
    }

    function eventKindLabel(kind) {
      const token = String(kind || "").trim();
      const normalized = token.toLowerCase();
      if (normalized === "feature_history") return "Feature history";
      if (normalized === "workspace_activity") return "Workspace activity";
      return token || "event";
    }

    function componentSearchText(row) {
      const aliases = Array.isArray(row.aliases) ? row.aliases.join(" ") : "";
      return [
        row.component_id || "",
        row.name || "",
        row.kind || "",
        row.category || "",
        row.qualification || "",
        row.owner || "",
        row.what_it_is || "",
        row.why_tracked || "",
        aliases,
      ].join(" ").toLowerCase();
    }

    function componentExactMatch(row, needle) {
      const normalizedNeedle = String(needle || "").trim().toLowerCase();
      if (!normalizedNeedle) return false;
      const componentId = String(row.component_id || "").trim().toLowerCase();
      const name = String(row.name || "").trim().toLowerCase();
      if (componentId === normalizedNeedle || name === normalizedNeedle) return true;
      const aliases = Array.isArray(row.aliases) ? row.aliases : [];
      return aliases.some((alias) => String(alias || "").trim().toLowerCase() === normalizedNeedle);
    }

    function readState() {
      const params = new URLSearchParams(window.location.search || "");
      const component = String(params.get("component") || "").trim().toLowerCase();
      return { component };
    }

    function writeState(component) {
      const params = new URLSearchParams(window.location.search || "");
      params.delete("component");
      if (component) params.set("component", component);
      const query = params.toString();
      const suffix = query ? `?${query}` : "";
      const next = `${window.location.pathname}${suffix}`;
      if (next !== `${window.location.pathname}${window.location.search}`) {
        window.history.replaceState(null, "", next);
      }
      if (window.parent && window.parent !== window) {
        const state = { component };
        window.parent.postMessage({ type: "odylith-registry-navigate", state }, "*");
        window.parent.postMessage({ type: "odylith-registry-navigate", state }, "*");
      }
    }

    function countMapFromPayload(key) {
      const map = payload && payload.counts && payload.counts[key];
      if (!map || typeof map !== "object") return {};
      return map;
    }

    function sortedCategoryTokens() {
      const counts = countMapFromPayload("by_category");
      return Object.keys(counts).sort((a, b) => {
        const av = Number(counts[a] || 0);
        const bv = Number(counts[b] || 0);
        if (av !== bv) return bv - av;
        return a.localeCompare(b);
      });
    }

    function sortedQualificationTokens() {
      const counts = countMapFromPayload("by_qualification");
      return Object.keys(counts).sort((a, b) => {
        const av = Number(counts[a] || 0);
        const bv = Number(counts[b] || 0);
        if (av !== bv) return bv - av;
        return a.localeCompare(b);
      });
    }

    function generatedDateToken() {
      return String(payload.generated_local_date || "").trim() || "-";
    }

    function renderKpis(visibleCount) {
      const counts = payload.counts || {};
      const rows = [
        { label: "Registry Updated", value: generatedDateToken(), tooltip: "Generated date for this Registry view." },
        { label: "Visible Components", value: Number(visibleCount || 0), tooltip: "Components visible under current search and filters." },
        { label: "All Components", value: Number(counts.components || 0), tooltip: "Total first-class component inventory size." },
        { label: "Events", value: Number(counts.events || 0), tooltip: "Codex stream events visible to Registry." },
        { label: "Meaningful", value: Number(counts.meaningful_events || 0), tooltip: "Governance-relevant events." },
        { label: "Mapped Meaningful", value: Number(counts.mapped_meaningful_events || 0), tooltip: "Meaningful events with mapped components." },
      ];
      if (Number(counts.unmapped_meaningful_events || 0) > 0) {
        rows.push({
          label: "Unmapped Meaningful",
          value: Number(counts.unmapped_meaningful_events || 0),
          tooltip: "Meaningful events without mapped components.",
          warn: true,
        });
      }
      if (Number(counts.candidate_queue || 0) > 0) {
        rows.push({
          label: "Candidate Queue",
          value: Number(counts.candidate_queue || 0),
          tooltip: "Unresolved component tokens pending curated review.",
        });
      }
      kpisEl.innerHTML = rows
        .map((row) => (
          `<article class="kpi-card${row.warn ? " warn" : ""}" data-tooltip="${escapeHtml(row.tooltip || "")}">`
          + `<p class="kpi-label">${escapeHtml(row.label)}</p>`
          + `<p class="kpi-value">${escapeHtml(String(row.value))}</p>`
          + "</article>"
        ))
        .join("");
    }

    function renderDiagnostics() {
      const rows = Array.isArray(payload.diagnostics) ? payload.diagnostics.slice() : [];
      const candidates = Array.isArray(payload.candidate_queue) ? payload.candidate_queue : [];
      if (!rows.length && !candidates.length) {
        diagnosticsEl.hidden = true;
        return;
      }
      diagnosticsEl.hidden = false;
      diagnosticsEl.querySelector("summary").textContent = `Diagnostics (${rows.length + candidates.length})`;
      const items = [];
      rows.slice(0, 16).forEach((row) => {
        items.push(`<li class="diag-item">${escapeHtml(String(row || ""))}</li>`);
      });
      candidates.slice(0, 16).forEach((row) => {
        const token = String(row.token || "");
        const source = String(row.source || "");
        const context = String(row.context || "");
        items.push(
          `<li class="diag-item">candidate \`${escapeHtml(token)}\` from ${escapeHtml(source)}${context ? ` (${escapeHtml(context)})` : ""}</li>`
        );
      });
      diagListEl.innerHTML = items.join("");
    }

    function renderFilterControls() {
      const categoryCounts = countMapFromPayload("by_category");
      const qualificationCounts = countMapFromPayload("by_qualification");
      const categoryTokens = sortedCategoryTokens();
      const qualificationTokens = sortedQualificationTokens();

      if (!categoryTokens.includes(activeCategory)) activeCategory = "all";
      if (!qualificationTokens.includes(activeQualification)) activeQualification = "all";

      categoryFilterEl.innerHTML = [
        `<option value="all">All Categories (${allComponents.length})</option>`,
        ...categoryTokens.map((token) => `<option value="${escapeHtml(token)}">${escapeHtml(humanizeToken(token))} (${Number(categoryCounts[token] || 0)})</option>`),
      ].join("");
      categoryFilterEl.value = activeCategory;

      qualificationFilterEl.innerHTML = [
        `<option value="all">All Qualifications (${allComponents.length})</option>`,
        ...qualificationTokens.map((token) => `<option value="${escapeHtml(token)}">${escapeHtml(humanizeToken(token))} (${Number(qualificationCounts[token] || 0)})</option>`),
      ].join("");
      qualificationFilterEl.value = activeQualification;
    }

    function filteredComponents() {
      const needle = String(searchEl.value || "").trim().toLowerCase();
      const categoryFilterToken = String(activeCategory || "all").trim().toLowerCase();
      const qualificationFilterToken = String(activeQualification || "all").trim().toLowerCase();
      const scoped = allComponents
        .filter((row) => {
          const category = String(row.category || "").trim().toLowerCase();
          const qualification = String(row.qualification || "").trim().toLowerCase();
          if (categoryFilterToken !== "all" && category !== categoryFilterToken) return false;
          if (qualificationFilterToken !== "all" && qualification !== qualificationFilterToken) return false;
          return true;
        })
        .sort((left, right) => {
          const leftCategory = String(left.category || "");
          const rightCategory = String(right.category || "");
          if (leftCategory !== rightCategory) return leftCategory.localeCompare(rightCategory);
          const leftName = String(left.name || left.component_id || "");
          const rightName = String(right.name || right.component_id || "");
          return leftName.localeCompare(rightName);
        });
      if (!needle) return scoped;
      const exactIdMatches = scoped.filter((row) => String(row.component_id || "").trim().toLowerCase() === needle);
      if (exactIdMatches.length) return exactIdMatches;
      const exactNameMatches = scoped.filter((row) => String(row.name || "").trim().toLowerCase() === needle);
      if (exactNameMatches.length) return exactNameMatches;
      const exactAliasMatches = scoped.filter((row) => {
        const aliases = Array.isArray(row.aliases) ? row.aliases : [];
        return aliases.some((alias) => String(alias || "").trim().toLowerCase() === needle);
      });
      if (exactAliasMatches.length) return exactAliasMatches;
      return scoped.filter((row) => componentSearchText(row).includes(needle));
    }

    function groupedByCategory(items) {
      const groups = new Map();
      items.forEach((row) => {
        const category = String(row.category || "").trim().toLowerCase() || "uncategorized";
        if (!groups.has(category)) groups.set(category, []);
        groups.get(category).push(row);
      });
      return Array.from(groups.entries()).sort((left, right) => left[0].localeCompare(right[0]));
    }

    function selectDefault(items, requested) {
      if (!items.length) return "";
      const token = String(requested || "").trim().toLowerCase();
      if (token && items.some((row) => String(row.component_id || "").toLowerCase() === token)) {
        return token;
      }
      return String(items[0].component_id || "").trim().toLowerCase();
    }

    function registryListItemHeight(item) {
      return item && item.kind === "header" ? REGISTRY_LIST_HEADER_HEIGHT : REGISTRY_LIST_ROW_HEIGHT;
    }

    function buildRegistryListItems(items) {
      const renderItems = [];
      groupedByCategory(items).forEach(([category, rows]) => {
        renderItems.push({
          kind: "header",
          key: `header:${category}`,
          category,
          count: rows.length,
        });
        rows.forEach((row) => {
          renderItems.push({
            kind: "row",
            key: `row:${row.component_id}`,
            row,
          });
        });
      });
      return renderItems;
    }

    function registryListOffsetForIndex(items, index) {
      let offset = 0;
      for (let cursor = 0; cursor < index; cursor += 1) {
        offset += registryListItemHeight(items[cursor]);
      }
      return offset;
    }

    function ensureRegistrySelectionVisible(items, selectedId) {
      if (items.length <= REGISTRY_LIST_WINDOW_THRESHOLD) return;
      const selectedIndex = items.findIndex((item) => item.kind === "row" && String(item.row.component_id || "").toLowerCase() === selectedId);
      if (selectedIndex < 0) return;
      const viewportHeight = Math.max(1, Number(listEl.clientHeight || 640));
      const scrollTop = Number(listEl.scrollTop || 0);
      const top = registryListOffsetForIndex(items, selectedIndex);
      const bottom = top + REGISTRY_LIST_ROW_HEIGHT;
      if (top >= scrollTop && bottom <= (scrollTop + viewportHeight)) return;
      listEl.scrollTop = Math.max(0, top - Math.max(24, Math.round(viewportHeight * 0.3)));
    }

    function elementFullyVisibleWithinContainer(container, element) {
      if (!container || !element) return false;
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      return elementRect.top >= containerRect.top && elementRect.bottom <= containerRect.bottom;
    }

    function resolveRegistryListWindow(items) {
      if (items.length <= REGISTRY_LIST_WINDOW_THRESHOLD) {
        return { beforePx: 0, afterPx: 0, items, key: `all:${items.length}` };
      }
      const viewportHeight = Math.max(1, Number(listEl.clientHeight || 640));
      const scrollTop = Number(listEl.scrollTop || 0);
      const startPx = Math.max(0, scrollTop - (REGISTRY_LIST_OVERSCAN * REGISTRY_LIST_ROW_HEIGHT));
      const endPx = scrollTop + viewportHeight + (REGISTRY_LIST_OVERSCAN * REGISTRY_LIST_ROW_HEIGHT);
      let cursorPx = 0;
      let startIndex = 0;
      while (startIndex < items.length) {
        const nextPx = cursorPx + registryListItemHeight(items[startIndex]);
        if (nextPx >= startPx) break;
        cursorPx = nextPx;
        startIndex += 1;
      }
      const beforePx = cursorPx;
      let endIndex = startIndex;
      while (endIndex < items.length && cursorPx < endPx) {
        cursorPx += registryListItemHeight(items[endIndex]);
        endIndex += 1;
      }
      let afterPx = 0;
      for (let cursor = endIndex; cursor < items.length; cursor += 1) {
        afterPx += registryListItemHeight(items[cursor]);
      }
      return {
        beforePx,
        afterPx,
        items: items.slice(startIndex, endIndex),
        key: `${startIndex}:${endIndex}`,
      };
    }

    function renderList(items, selectedId, options = {}) {
      latestRenderedComponents = Array.isArray(items) ? items.slice() : [];
      if (!items.length) {
        listEl.innerHTML = "";
        latestListWindowKey = "empty";
        return;
      }
      const renderItems = buildRegistryListItems(items);
      if (!options.fromScroll && !options.preserveListScroll) {
        ensureRegistrySelectionVisible(renderItems, selectedId);
      }
      const windowed = resolveRegistryListWindow(renderItems);
      if (options.fromScroll && windowed.key === latestListWindowKey) {
        return;
      }
      latestListWindowKey = windowed.key;
      const blocks = [];
      if (windowed.beforePx > 0) {
        blocks.push(`<li class="list-spacer" aria-hidden="true" style="height:${windowed.beforePx}px"></li>`);
      }
      windowed.items.forEach((item) => {
        if (item.kind === "header") {
          blocks.push(`<li class="group-head">${escapeHtml(humanizeToken(item.category))} · ${item.count}</li>`);
          return;
        }
        const row = item.row;
          const categoryToken = String(row.category || "").trim().toLowerCase();
          const toneClass = toneClassForCategory(categoryToken);
          const coverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
        blocks.push(`
          <li>
            <button type="button" class="component-btn${row.component_id === selectedId ? " active" : ""}" data-component="${escapeHtml(row.component_id)}">
              <span class="component-card-title">${escapeHtml(row.name || row.component_id)}</span>
              <span class="component-meta">${escapeHtml(row.component_id)} · ${escapeHtml(humanizeToken(row.kind))} · ${escapeHtml(humanizeToken(row.status || "active"))} · ${escapeHtml(forensicCoverageLabel(coverage))} · ${escapeHtml(Number(row.timeline_count || 0))} events</span>
              <span class="inline">
                <span class="label ${escapeHtml(toneClass)}">${escapeHtml(humanizeToken(categoryToken))}</span>
                <span class="label">${escapeHtml(humanizeToken(row.qualification || "curated"))}</span>
              </span>
            </button>
          </li>
        `);
      });
      if (windowed.afterPx > 0) {
        blocks.push(`<li class="list-spacer" aria-hidden="true" style="height:${windowed.afterPx}px"></li>`);
      }
      listEl.innerHTML = blocks.join("");

      listEl.querySelectorAll("button[data-component]").forEach((node) => {
        node.addEventListener("click", () => {
          const id = String(node.getAttribute("data-component") || "").trim().toLowerCase();
          if (!id) return;
          const preserveListScroll = elementFullyVisibleWithinContainer(listEl, node);
          applyState(id, { push: true, preserveListScroll });
        });
        const id = String(node.getAttribute("data-component") || "").trim().toLowerCase();
        if (id) {
          node.addEventListener("mouseenter", () => {
            registryDataSource.prefetch(id);
          });
          node.addEventListener("focus", () => {
            registryDataSource.prefetch(id);
          });
        }
      });
    }

    function hrefRadar(workstream) {
      const token = String(workstream || "").trim();
      return token ? `../index.html?tab=radar&workstream=${encodeURIComponent(token)}` : "../index.html?tab=radar";
    }

    function hrefAtlas(workstream, diagram) {
      const params = new URLSearchParams();
      params.set("tab", "atlas");
      if (workstream) params.set("workstream", workstream);
      if (diagram) params.set("diagram", diagram);
      return `../index.html?${params.toString()}`;
    }

    function hrefCompass(workstream) {
      const token = String(workstream || "").trim();
      return token
        ? `../index.html?tab=compass&scope=${encodeURIComponent(token)}&date=live`
        : "../index.html?tab=compass&date=live";
    }

    const WORKSTREAM_RE = /^B-\d{3,}$/;
    const DIAGRAM_RE = /^D-\d{3,}$/;

    function linkChip({ label, href, tone, tooltip }) {
      const resolvedHref = String(href || "").trim();
      if (!resolvedHref) return `<span class="label">${escapeHtml(label)}</span>`;
      return `<a class="detail-action-chip ${escapeHtml(tone || "")}" target="_top" href="${escapeHtml(resolvedHref)}" data-tooltip="${escapeHtml(tooltip || "")}">${escapeHtml(label)}</a>`;
    }

    function staticLabel(label, tooltip) {
      return `<span class="label" data-tooltip="${escapeHtml(tooltip || "")}">${escapeHtml(label)}</span>`;
    }

    function artifactChip(item, tooltip, className = "artifact") {
      const path = String(item && item.path || "").trim();
      const href = String(item && item.href || path).trim();
      if (!path || !href) return "";
      return `<a class="${escapeHtml(className)}" href="${escapeHtml(href)}" target="_top" data-tooltip="${escapeHtml(tooltip || "Artifact evidence path.")}">${escapeHtml(path)}</a>`;
    }

    function renderSpecLinkGroup(title, items, emptyLabel, tooltip) {
      const rows = Array.isArray(items) ? items.filter(Boolean) : [];
      return `
        <div class="spec-links-block">
          <p class="summary-row"><strong>${escapeHtml(title)}:</strong></p>
          <div class="artifact-list">
            ${rows.length
              ? rows.map((item) => artifactChip(item, tooltip)).join("")
              : `<span class="label">${escapeHtml(emptyLabel)}</span>`}
          </div>
        </div>
      `;
    }

    function normalizeRepoRelativePath(value) {
      const parts = [];
      String(value || "").split("/").forEach((segment) => {
        const token = String(segment || "").trim();
        if (!token || token === ".") return;
        if (token === "..") {
          if (parts.length) parts.pop();
          return;
        }
        parts.push(token);
      });
      return parts.join("/");
    }

    function specInlineTooltipAttrs(tooltip, ariaLabel = "") {
      const text = String(tooltip || "").trim();
      if (!text) return "";
      const label = String(ariaLabel || text).trim() || text;
      return ` data-tooltip="${escapeHtml(text)}" aria-label="${escapeHtml(label)}"`;
    }

    function specInlineLinkWorkstream(href, label) {
      const labelToken = String(label || "").trim();
      if (WORKSTREAM_RE.test(labelToken)) return labelToken;
      const rawHref = String(href || "").trim();
      const queryIndex = rawHref.indexOf("?");
      if (queryIndex === -1) return "";
      const params = new URLSearchParams(rawHref.slice(queryIndex + 1));
      const token = String(params.get("workstream") || "").trim();
      return WORKSTREAM_RE.test(token) ? token : "";
    }

    function specInlineLinkDiagram(href, label) {
      const labelToken = String(label || "").trim();
      if (DIAGRAM_RE.test(labelToken)) return labelToken;
      const rawHref = String(href || "").trim();
      const queryIndex = rawHref.indexOf("?");
      if (queryIndex === -1) return "";
      const params = new URLSearchParams(rawHref.slice(queryIndex + 1));
      const token = String(params.get("diagram") || "").trim();
      return DIAGRAM_RE.test(token) ? token : "";
    }

    function specInlineLinkTooltip(label, href) {
      const rawLabel = String(label || "").trim();
      const rawHref = String(href || "").trim();
      const workstream = specInlineLinkWorkstream(rawHref, rawLabel);
      if (workstream) {
        return `Workstream ${workstream}. Open linked plan.`;
      }
      const diagram = specInlineLinkDiagram(rawHref, rawLabel);
      if (diagram) {
        return `Diagram ${diagram}. Open linked diagram.`;
      }
      if (/^#/i.test(rawHref)) {
        return rawLabel ? `Jump to linked section ${rawLabel}.` : "Jump to linked section.";
      }
      if (/^(?:https?:|mailto:)/i.test(rawHref)) {
        return rawLabel ? `Open external link ${rawLabel}.` : "Open external link.";
      }
      const normalizedLabel = normalizeRepoRelativePath(rawLabel);
      if (normalizedLabel.includes("/")) {
        return `Open linked repository path ${clipText(normalizedLabel, 72)}.`;
      }
      return rawLabel
        ? `Open linked artifact ${clipText(rawLabel, 72)}.`
        : "Open linked artifact.";
    }

    function specInlineCodeTooltip(value) {
      const token = String(value || "").trim();
      if (!token) return "";
      if (WORKSTREAM_RE.test(token)) return `Workstream ${token} referenced in this spec.`;
      if (DIAGRAM_RE.test(token)) return `Diagram ${token} referenced in this spec.`;
      if (/^(?:dev|test|staging|prod)$/i.test(token)) return `Environment literal in this spec.`;
      if (/^(?:python|pytest|make|app)\b/i.test(token)) return "Command literal in this spec.";
      if (
        /^(?:odylith|docs|scripts|contracts|infra|services|app|tests|agents-guidelines|skills|mk)\//.test(token)
        || (token.includes("/") && /\.[a-z0-9]+$/i.test(token))
      ) {
        return `Repository path in this spec: ${clipText(token, 72)}.`;
      }
      if (/^[a-z][a-z0-9-]*$/i.test(token) && token.includes("-")) {
        return `Spec identifier: ${clipText(token, 72)}.`;
      }
      return `Spec literal: ${clipText(token, 72)}.`;
    }

    function specInlineAriaLabel(value, tooltip) {
      const token = String(value || "").trim();
      const help = String(tooltip || "").trim();
      if (!token) return help;
      if (!help) return token;
      return help.toLowerCase().includes(token.toLowerCase()) ? help : `${token}. ${help}`;
    }

    function resolveSpecHref(baseSpecPath, href) {
      const rawHref = String(href || "").trim();
      if (!rawHref) return "";
      if (/^(?:https?:|mailto:|#)/i.test(rawHref)) return rawHref;
      if (/^(?:odylith|docs|src|contracts|tests|agents-guidelines|skills|scripts|mk|infra|services|app|\.odylith)\//.test(rawHref)) {
        return `../../${rawHref.replace(/^\.?\//, "")}`;
      }
      const specPath = normalizeRepoRelativePath(baseSpecPath);
      const specDir = specPath ? specPath.split("/").slice(0, -1) : [];
      const resolvedParts = specDir.slice();
      rawHref.split("/").forEach((segment) => {
        const token = String(segment || "").trim();
        if (!token || token === ".") return;
        if (token === "..") {
          if (resolvedParts.length) resolvedParts.pop();
          return;
        }
        resolvedParts.push(token);
      });
      const repoRelative = resolvedParts.join("/");
      if (!repoRelative) return rawHref;
      return `../../${repoRelative}`;
    }

    function renderInlineMarkdown(value, baseSpecPath = "") {
      const raw = String(value || "");
      const inlineTokens = [];
      let tokenized = raw.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, href) => {
        const resolvedHref = resolveSpecHref(baseSpecPath, href);
        const tooltip = specInlineLinkTooltip(label, resolvedHref || href);
        const ariaLabel = specInlineAriaLabel(label, tooltip);
        const attrs = specInlineTooltipAttrs(tooltip, ariaLabel);
        const html = resolvedHref
          ? `<a href="${escapeHtml(resolvedHref)}" target="_top"${attrs}>${escapeHtml(String(label || "").trim())}</a>`
          : escapeHtml(String(label || "").trim());
        const index = inlineTokens.push(html) - 1;
        return `@@REGISTRY_INLINE_${index}@@`;
      });
      tokenized = tokenized.replace(/`([^`]+)`/g, (_, code) => {
        const tooltip = specInlineCodeTooltip(code);
        const attrs = specInlineTooltipAttrs(tooltip, specInlineAriaLabel(code, tooltip));
        const html = `<code${attrs}>${escapeHtml(String(code || "").trim())}</code>`;
        const index = inlineTokens.push(html) - 1;
        return `@@REGISTRY_INLINE_${index}@@`;
      });

      let html = escapeHtml(tokenized);
      html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/@@REGISTRY_INLINE_(\d+)@@/g, (_, index) => inlineTokens[Number(index)] || "");
      return html;
    }

    function renderSpecMarkdown(markdown, baseSpecPath = "") {
      const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
      const chunks = [];
      let paragraph = [];
      let listDepth = 0;
      const listItemOpen = {};
      const parseMarkdownTableCells = (value) => {
        const raw = String(value || "").trim();
        if (!raw.includes("|")) return [];
        let body = raw;
        if (body.startsWith("|")) body = body.slice(1);
        if (body.endsWith("|")) body = body.slice(0, -1);
        return body.split("|").map((cell) => String(cell || "").trim());
      };
      const isMarkdownTableSeparator = (value) => {
        const cells = parseMarkdownTableCells(value);
        return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
      };
      const normalizeMarkdownTableCells = (cells, width) => {
        const normalized = Array.isArray(cells) ? cells.slice(0, width) : [];
        while (normalized.length < width) normalized.push("");
        return normalized;
      };

      const flushParagraph = () => {
        if (!paragraph.length) return;
        chunks.push(`<p>${renderInlineMarkdown(paragraph.join(" "), baseSpecPath)}</p>`);
        paragraph = [];
      };
      const closeOneListLevel = () => {
        if (listDepth <= 0) return;
        if (listItemOpen[listDepth]) {
          chunks.push("</li>");
          listItemOpen[listDepth] = false;
        }
        chunks.push("</ul>");
        delete listItemOpen[listDepth];
        listDepth -= 1;
      };
      const closeAllLists = () => {
        while (listDepth > 0) closeOneListLevel();
      };
      const ensureListDepth = (targetDepth) => {
        while (listDepth < targetDepth) {
          if (listDepth > 0 && !listItemOpen[listDepth]) {
            chunks.push("<li>");
            listItemOpen[listDepth] = true;
          }
          chunks.push("<ul>");
          listDepth += 1;
          listItemOpen[listDepth] = false;
        }
        while (listDepth > targetDepth) closeOneListLevel();
      };

      for (let index = 0; index < lines.length; index += 1) {
        const raw = String(lines[index] || "");
        const token = raw.trim();
        if (/^<!--.*-->$/.test(token)) {
          flushParagraph();
          continue;
        }
        if (!token) {
          flushParagraph();
          closeAllLists();
          continue;
        }
        if (token.startsWith("### ")) {
          flushParagraph();
          closeAllLists();
          chunks.push(`<h5>${escapeHtml(token.slice(4).trim())}</h5>`);
          continue;
        }
        if (token.startsWith("## ")) {
          flushParagraph();
          closeAllLists();
          chunks.push(`<h4>${escapeHtml(token.slice(3).trim())}</h4>`);
          continue;
        }
        if (token.startsWith("# ")) {
          flushParagraph();
          closeAllLists();
          chunks.push(`<h3>${escapeHtml(token.slice(2).trim())}</h3>`);
          continue;
        }
        const headerCells = parseMarkdownTableCells(token);
        if (headerCells.length && index + 1 < lines.length && isMarkdownTableSeparator(lines[index + 1])) {
          flushParagraph();
          closeAllLists();
          const normalizedHeader = normalizeMarkdownTableCells(headerCells, headerCells.length);
          const bodyRows = [];
          index += 2;
          for (; index < lines.length; index += 1) {
            const rowRaw = String(lines[index] || "");
            const rowToken = rowRaw.trim();
            if (!rowToken) break;
            const rowCells = parseMarkdownTableCells(rowToken);
            if (!rowCells.length) {
              index -= 1;
              break;
            }
            bodyRows.push(normalizeMarkdownTableCells(rowCells, normalizedHeader.length));
          }
          const headerHtml = normalizedHeader
            .map((cell) => `<th>${renderInlineMarkdown(cell, baseSpecPath)}</th>`)
            .join("");
          const bodyHtml = bodyRows
            .map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell, baseSpecPath)}</td>`).join("")}</tr>`)
            .join("");
          chunks.push(
            `<div class="spec-table-scroll"><table class="spec-table"><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`
          );
          continue;
        }
        const bulletMatch = raw.match(/^(\s*)[-*+]\s+(.*)$/);
        if (bulletMatch) {
          flushParagraph();
          const indentSpaces = String(bulletMatch[1] || "").replace(/\t/g, "  ").length;
          const targetDepth = Math.max(1, Math.floor(indentSpaces / 2) + 1);
          ensureListDepth(targetDepth);
          if (listItemOpen[listDepth]) {
            chunks.push("</li>");
            listItemOpen[listDepth] = false;
          }
          chunks.push(`<li>${renderInlineMarkdown(String(bulletMatch[2] || "").trim(), baseSpecPath)}`);
          listItemOpen[listDepth] = true;
          continue;
        }
        closeAllLists();
        paragraph.push(token);
      }

      flushParagraph();
      closeAllLists();
      if (!chunks.length) return '<p class="empty">No spec content.</p>';
      return chunks.join("");
    }

    function extractTriggerPhrases(markdown, triggerTiers) {
      const phrases = [];
      const seen = new Set();

      const appendPhrase = (value) => {
        const token = String(value || "").trim();
        if (!token || seen.has(token)) return;
        seen.add(token);
        phrases.push(token);
      };

      const appendTierPhrases = (value) => {
        if (!Array.isArray(value)) return;
        value.forEach((item) => {
          const phrasesRaw = Array.isArray(item && item.trigger_phrases) ? item.trigger_phrases : [];
          phrasesRaw.forEach((phrase) => {
            appendPhrase(phrase);
          });
        });
      };

      if (triggerTiers && typeof triggerTiers === "object") {
        appendTierPhrases(triggerTiers.baseline);
        appendTierPhrases(triggerTiers.deep);
      }
      if (phrases.length) return phrases;

      const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
      let inTriggers = false;
      lines.forEach((line) => {
        const trimmed = String(line || "").trim();
        if (!inTriggers) {
          if (/^##\s+skill triggers\b/i.test(trimmed)) inTriggers = true;
          return;
        }
        if (/^##\s+/.test(trimmed)) {
          inTriggers = false;
          return;
        }
        const nestedPhrase = trimmed.match(/^-\s+"([^"]+)"/);
        if (nestedPhrase) {
          appendPhrase(nestedPhrase[1]);
          return;
        }
        const inlineTrigger = trimmed.match(/^-\s*Trigger phrases:\s*(.+)$/i);
        if (!inlineTrigger) return;
        const quoted = String(inlineTrigger[1] || "").match(/"([^"]+)"/g) || [];
        quoted.forEach((token) => {
          appendPhrase(token.replace(/^"|"$/g, ""));
        });
      });
      return phrases;
    }

    function uniqueTimelineArtifacts(events, maxItems, predicate) {
      const rows = [];
      const seen = new Set();
      events.forEach((event) => {
        const artifacts = Array.isArray(event.artifacts) ? event.artifacts : [];
        artifacts.forEach((item) => {
          const path = String(item && item.path || "").trim();
          if (!path || seen.has(path)) return;
          if (typeof predicate === "function" && !predicate(path)) return;
          seen.add(path);
          rows.push(item);
        });
      });
      return rows.slice(0, maxItems);
    }

    function uniqueEventWorkstreams(events) {
      const tokens = [];
      const seen = new Set();
      events.forEach((event) => {
        const ws = Array.isArray(event.workstreams) ? event.workstreams : [];
        ws.forEach((token) => {
          const value = String(token || "").trim();
          if (!value || seen.has(value)) return;
          seen.add(value);
          tokens.push(value);
        });
      });
      return tokens;
    }

    function contextRow(title, count, bodyHtml, tooltip, block = false) {
      return `
        <div class="context-row">
          <div class="context-title" data-tooltip="${escapeHtml(tooltip || "")}">${escapeHtml(title)}</div>
          <div class="context-count">${escapeHtml(String(count))}</div>
          <div class="context-values${block ? " block" : ""}">${bodyHtml || ""}</div>
        </div>
      `;
    }

    function renderDetail(row) {
      if (!row) {
        detailEl.innerHTML = "";
        return;
      }
      const workstreams = Array.isArray(row.workstreams) ? row.workstreams : [];
      const diagrams = Array.isArray(row.diagrams) ? row.diagrams : [];
      const diagramDetails = Array.isArray(row.diagram_details) ? row.diagram_details : [];
      const subcomponents = Array.isArray(row.subcomponents) ? row.subcomponents : [];
      const subcomponentDetails = Array.isArray(row.subcomponent_details) ? row.subcomponent_details : [];
      const aliases = Array.isArray(row.aliases) ? row.aliases : [];
      const sources = Array.isArray(row.sources) ? row.sources : [];
      const pathPrefixes = Array.isArray(row.path_prefixes) ? row.path_prefixes : [];
      const productLayer = String(row.product_layer || "").trim();
      const timelineEvents = Array.isArray(row.timeline) ? row.timeline : [];
      const liveTimelineEvents = timelineEvents.filter((event) => !isBaselineTimelineEvent(event));
      const forensicCoverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
      const categoryToken = String(row.category || "").trim().toLowerCase();
      const toneClass = toneClassForCategory(categoryToken);
      const latestEvent = liveTimelineEvents[0] || (timelineEvents.length ? timelineEvents[0] : null);
      const latestSummary = latestEvent
        ? String(latestEvent.summary || "(no summary)").trim()
        : "No mapped component-change event is currently available for this component.";
      const allWorkstreams = uniqueEventWorkstreams(timelineEvents);
      const workstreamPreview = allWorkstreams.slice(0, 4);
      const workstreamOverflow = Math.max(0, allWorkstreams.length - workstreamPreview.length);
      const diagramPreview = diagrams.slice(0, 3);
      const diagramOverflow = Math.max(0, diagrams.length - diagramPreview.length);
      const EVENT_WINDOW_DAYS = 14;
      const latestEventTs = latestEvent && typeof latestEvent.ts_iso === "string" ? Date.parse(latestEvent.ts_iso) : NaN;
      const windowAnchorTs = Number.isFinite(latestEventTs) ? latestEventTs : Date.now();
      const windowStartTs = windowAnchorTs - (EVENT_WINDOW_DAYS * 24 * 60 * 60 * 1000);
      const windowEvents = timelineEvents.filter((event) => {
        const ts = Date.parse(String(event && event.ts_iso || ""));
        return Number.isFinite(ts) ? ts >= windowStartTs : true;
      });
      const hasImplementationSignal = liveTimelineEvents.some((event) => String(event && event.kind || "").toLowerCase() === "implementation");
      const hasDecisionSignal = liveTimelineEvents.some((event) => String(event && event.kind || "").toLowerCase() === "decision");
      const latestExplicit = latestExplicitEvent(timelineEvents);
      const explicitExecutiveEvents = windowEvents.filter((event) => isExplicitTimelineEvent(event));
      const syntheticExecutiveEvents = windowEvents.filter((event) => isSyntheticTimelineEvent(event));
      const baselineExecutiveEvents = windowEvents.filter((event) => isBaselineTimelineEvent(event));
      const primaryWorkstream = workstreamPreview[0] || "";
      const componentName = String(row.name || row.component_id || "This component").trim() || "This component";
      const confidence = intelligenceConfidence(
        explicitExecutiveEvents.length,
        syntheticExecutiveEvents.length,
        allWorkstreams.length,
        baselineExecutiveEvents.length,
      );
      const intelligenceContext = {
        latestEvent,
        latestSummary,
        latestExplicit,
        whyTracked: row.why_tracked,
        componentName,
        categoryToken,
        hasImplementationSignal,
        hasDecisionSignal,
        explicitCount: explicitExecutiveEvents.length,
        syntheticCount: syntheticExecutiveEvents.length,
        baselineCount: baselineExecutiveEvents.length,
        allWorkstreams,
        workstreamPreview,
        workstreamOverflow,
        primaryWorkstream,
        diagramPreview,
        diagramOverflow,
        diagrams,
        timelineEvents,
        specPath: String(row.spec_ref || "").trim(),
        specRunbooks: Array.isArray(row.spec_runbooks) ? row.spec_runbooks : [],
        specDeveloperDocs: Array.isArray(row.spec_developer_docs) ? row.spec_developer_docs : [],
      };
      const intelligenceSnapshot = componentIntelligenceSnapshot(row.component_id);
      const confidenceToken = String(intelligenceSnapshot && intelligenceSnapshot.confidence || confidence).trim() || confidence;
      const confidenceSummary = intelligenceConfidenceBasis(
        confidenceToken,
        explicitExecutiveEvents.length,
        syntheticExecutiveEvents.length,
        allWorkstreams.length,
        baselineExecutiveEvents.length,
      );
      const postureMode = humanizeToken(String(intelligenceSnapshot && intelligenceSnapshot.posture_mode || "converging"));
      const trajectory = humanizeToken(String(intelligenceSnapshot && intelligenceSnapshot.trajectory || "converging"));

      const metadata = [
        staticLabel(`Category: ${humanizeToken(row.category)}`, categoryDescription(row.category)),
        staticLabel(`Qualification: ${humanizeToken(row.qualification)}`, qualificationDescription(row.qualification)),
        staticLabel(`Kind: ${humanizeToken(row.kind)}`, "Component structure class."),
        staticLabel(`Owner: ${row.owner || "unknown"}`, "Declared ownership for governance routing."),
        staticLabel(`Status: ${humanizeToken(row.status || "unknown")}`, "Lifecycle state of this component record."),
      ].join("");

      const wsLinks = workstreams.length
        ? workstreams.map((ws) => linkChip({
            label: ws,
            href: hrefRadar(ws),
            tone: "tone-gov",
            tooltip: `Workstream ${ws}. Open Radar context.`,
          })).join("")
        : "";

      const diagramLinks = diagramDetails.length
        ? diagramDetails.map((item) => {
            const diagramId = String(item && item.diagram_id || "").trim();
            const diagramTitle = String(item && item.title || "").trim() || diagramId;
            if (!diagramId) return "";
            return linkChip({
              label: diagramId,
              href: hrefAtlas(workstreams[0] || "", diagramId),
              tooltip: `${diagramTitle}. Open Atlas context.`,
            });
          }).join("")
        : diagrams.length
        ? diagrams.map((dg) => linkChip({
            label: dg,
            href: hrefAtlas(workstreams[0] || "", dg),
            tooltip: `Diagram ${dg}. Open Atlas context.`,
          })).join("")
        : "";

      const aliasLabels = aliases.length
        ? aliases.map((token) => staticLabel(token, "Alias token used during component mapping.")).join("")
        : "";

      const sourceLabels = sources.length
        ? sources.map((token) => staticLabel(token, "Source that contributed this component linkage.")).join("")
        : "";

      const pathLabels = pathPrefixes.length
        ? pathPrefixes.map((token) => staticLabel(token, "Artifact prefix used for path-based mapping.")).join("")
        : "";
      const productLayerBody = productLayer
        ? `<p class="desc"><strong>${escapeHtml(productLayerLabel(productLayer))}.</strong> ${escapeHtml(productLayerDescription(productLayer))}</p>`
        : "";
      const subcomponentLinks = subcomponentDetails.length
        ? subcomponentDetails.map((item) => {
            const componentId = String(item && item.component_id || "").trim();
            const componentName = String(item && item.name || "").trim() || componentId;
            if (!componentId) return "";
            return linkChip({
              label: componentName,
              href: registryComponentHref(componentId),
              tooltip: `${componentId}. Open Registry component detail.`,
            });
          }).join("")
        : subcomponents.length
        ? subcomponents.map((componentId) => linkChip({
            label: componentId,
            href: registryComponentHref(componentId),
            tooltip: `${componentId}. Open Registry component detail.`,
          })).join("")
        : "";
      const emptyReasons = Array.isArray(forensicCoverage.empty_reasons)
        ? forensicCoverage.empty_reasons.map(forensicCoverageReasonLabel).filter(Boolean)
        : [];
      const forensicCoverageBody = String(forensicCoverage.status || "").trim().toLowerCase() === "tracked_but_evidence_empty"
        ? `<p class="desc">${escapeHtml(forensicCoverageLabel(forensicCoverage))}. ${escapeHtml(emptyReasons.length ? ensureSentence(naturalList(emptyReasons)) : "No mapped forensic evidence channels are currently attached.")}</p>`
        : `<p class="desc">${escapeHtml(forensicCoverageSummary(forensicCoverage))}</p>`;

      const rows = [
        contextRow("Forensic Coverage", Number(row.timeline_count || 0), forensicCoverageBody, "Registry coverage truth derived from explicit Compass events, recent path matches, and mapped workstream evidence.", true),
        contextRow("Metadata", 5, metadata, "Category, qualification, and ownership qualifiers."),
        contextRow("Product Layer", productLayer ? 1 : 0, productLayerBody, "Odylith product-layer placement for this component."),
        contextRow("Workstreams", workstreams.length, wsLinks, "Linked workstreams affecting this component."),
        contextRow("Diagrams", diagrams.length, diagramLinks, "Atlas diagrams that mention this component."),
        contextRow("Subcomponents", subcomponents.length, subcomponentLinks, "Explicit composed children for umbrella/platform components."),
        contextRow("Aliases", aliases.length, aliasLabels, "Alternate tokens used for resolution."),
        contextRow("Sources", sources.length, sourceLabels, "Inventory evidence sources."),
        contextRow("Path Prefixes", pathPrefixes.length, pathLabels, "Artifact prefixes used in event mapping."),
      ].join("");

      const displayName = String(row.name || row.component_id || "").trim();
      const fallbackToken = String(row.component_id || "").trim();
      const specPath = String(row.spec_ref || "").trim();
      const specLastUpdated = String(row.spec_last_updated || "").trim() || "Unknown";
      const specHistory = Array.isArray(row.spec_feature_history) ? row.spec_feature_history : [];
      const specMarkdown = String(row.spec_markdown || "").trim();
      const specRunbooks = Array.isArray(row.spec_runbooks) ? row.spec_runbooks : [];
      const specDeveloperDocs = Array.isArray(row.spec_developer_docs) ? row.spec_developer_docs : [];
      const triggerPhrases = extractTriggerPhrases(specMarkdown, row && row.skill_trigger_tiers);
      const specRendered = renderSpecMarkdown(specMarkdown, specPath);
      const triggerBlock = triggerPhrases.length
        ? `
          <details class="trigger-expand">
            <summary>
              <p class="summary-row trigger-summary-title"><strong>Triggers:</strong> ${escapeHtml(String(triggerPhrases.length))} phrase${triggerPhrases.length === 1 ? "" : "s"}</p>
            </summary>
            <div class="trigger-block">
              <ul class="trigger-list">
                ${triggerPhrases.map((phrase) => `<li>${escapeHtml(phrase)}</li>`).join("")}
              </ul>
            </div>
          </details>
        `
        : '<p class="summary-row"><strong>Triggers:</strong> No trigger phrases documented.</p>';

      detailEl.innerHTML = `
        <h2 class="component-name">${escapeHtml(displayName || fallbackToken)}</h2>
        <div class="summary-strip">
          <p class="summary-row"><strong>What it is:</strong> ${escapeHtml(row.what_it_is || "Not documented.")}</p>
          <p class="summary-row"><strong>Why tracked:</strong> ${escapeHtml(row.why_tracked || "Not documented.")}</p>
          ${productLayer ? `<p class="summary-row"><strong>Product layer:</strong> ${escapeHtml(productLayerLabel(productLayer))}</p>` : ""}
          <p class="summary-row"><strong>Forensic coverage:</strong> ${escapeHtml(forensicCoverageSummary(forensicCoverage))}</p>
          ${triggerBlock}
        </div>
        <details class="spec-expand">
          <summary>
            <div class="spec-summary-main">
              <p class="detail-disclosure-title spec-summary-title">Current Spec</p>
            </div>
            <span class="spec-summary-meta">
              <span class="label">Last updated ${escapeHtml(specLastUpdated)}</span>
              <span class="label">Feature entries ${escapeHtml(String(specHistory.length))}</span>
            </span>
          </summary>
          <div class="spec-expand-body">
            <p class="summary-row"><strong>Spec source:</strong> ${escapeHtml(specPath || "Not documented.")}</p>
            ${renderSpecLinkGroup(
              "Runbooks",
              specRunbooks,
              "No linked runbooks.",
              "Runbook linked to this component through workstream traceability."
            )}
            ${renderSpecLinkGroup(
              "Developer Docs",
              specDeveloperDocs,
              "No linked developer docs.",
              "Developer doc linked to this component through workstream traceability."
            )}
            <div class="spec-doc">${specRendered}</div>
          </div>
        </details>
        <details class="context-section">
          <summary>
            <div class="context-head">
              <span class="detail-disclosure-title context-toggle-label">Topology</span>
              <span class="detail-chip-label ${escapeHtml(toneClass)}" data-tooltip="${escapeHtml(categoryDescription(categoryToken))}">${escapeHtml(row.component_id)}</span>
            </div>
            <div class="context-head-actions">
              <span class="label" data-tooltip="Linked workstreams count.">Workstreams ${workstreams.length}</span>
              <span class="label" data-tooltip="Linked diagrams count.">Diagrams ${diagrams.length}</span>
              <span class="label" data-tooltip="Mapped timeline events for this component.">Events ${Number(row.timeline_count || 0)}</span>
            </div>
          </summary>
          <div class="context-body">
            ${rows}
          </div>
        </details>
      `;
    }

    function renderTimeline(row) {
      const events = row && Array.isArray(row.timeline) ? row.timeline : [];
      const forensicCoverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
      timelineCountEl.textContent = `${events.length} events`;
      if (!events.length) {
        timelineEl.innerHTML = "";
        return;
      }
      timelineEl.innerHTML = events.map((event) => {
        const workstreams = Array.isArray(event.workstreams) ? event.workstreams : [];
        const artifacts = Array.isArray(event.artifacts) ? event.artifacts : [];
        const wsPills = workstreams.length
          ? workstreams.map((ws) => linkChip({
              label: ws,
              href: hrefRadar(ws),
              tone: "tone-gov",
              tooltip: `Workstream ${ws}. Open Radar context.`,
            })).join("")
          : '<span class="label">No scope</span>';

        const artifactLinks = artifacts.length
          ? artifacts.map((item) => `<a class="artifact" href="${escapeHtml(item.href || item.path || "")}" target="_top" data-tooltip="Artifact evidence path for this event.">${escapeHtml(item.path || "artifact")}</a>`).join("")
          : '<span class="artifact">No artifacts</span>';

        return `
          <li class="event">
            <div class="event-top">
              <span class="label" data-tooltip="Codex stream event kind.">${escapeHtml(eventKindLabel(event.kind))}</span>
              <span class="label" data-tooltip="Component-link confidence for this event.">confidence: ${escapeHtml(event.confidence || "none")}</span>
              <span>${escapeHtml(event.ts_iso || "")}</span>
            </div>
            <p class="event-summary">${escapeHtml(event.summary || "(no summary)")}</p>
            <div class="inline">${wsPills}</div>
            <div class="artifact-list">${artifactLinks}</div>
          </li>
        `;
      }).join("");
    }

    async function renderSelectedComponent(selectedId, filtered) {
      const selectedSummary = filtered.find((row) => String(row.component_id || "").toLowerCase() === String(selectedId || "").toLowerCase()) || null;
      if (!selectedSummary) {
        detailEl.dataset.selectedComponent = "";
        renderDetail(null);
        renderTimeline(null);
        return;
      }
      const expectedSelected = String(selectedId || "").trim().toLowerCase();
      detailEl.dataset.selectedComponent = expectedSelected;
      detailEl.innerHTML = "";
      timelineCountEl.textContent = "";
      timelineEl.innerHTML = "";
      const loadedDetail = await registryDataSource.loadDetail(selectedId);
      if (String(detailEl.dataset.selectedComponent || "") !== expectedSelected) {
        return;
      }
      const selected = loadedDetail && typeof loadedDetail === "object"
        ? { ...selectedSummary, ...loadedDetail }
        : selectedSummary;
      renderDetail(selected);
      renderTimeline(selected);
    }

    function applyState(requestedId, options = {}) {
      renderFilterControls();
      const filtered = filteredComponents();
      renderKpis(filtered.length);
      const selectedId = selectDefault(filtered, requestedId);
      renderList(filtered, selectedId, { preserveListScroll: Boolean(options.preserveListScroll) });
      void renderSelectedComponent(selectedId, filtered);
      if (options.push) writeState(selectedId);
    }

    searchEl.addEventListener("input", () => {
      applyState(readState().component, { push: false });
    });
    listEl.addEventListener("scroll", () => {
      if (latestRenderedComponents.length <= REGISTRY_LIST_WINDOW_THRESHOLD) return;
      if (listScrollFrame) return;
      listScrollFrame = window.requestAnimationFrame(() => {
        listScrollFrame = 0;
        renderList(latestRenderedComponents, readState().component, { fromScroll: true });
      });
    });

    categoryFilterEl.addEventListener("change", () => {
      activeCategory = String(categoryFilterEl.value || "all").trim().toLowerCase() || "all";
      applyState(readState().component, { push: false });
    });

    qualificationFilterEl.addEventListener("change", () => {
      activeQualification = String(qualificationFilterEl.value || "all").trim().toLowerCase() || "all";
      applyState(readState().component, { push: false });
    });

    resetFiltersEl.addEventListener("click", () => {
      searchEl.value = "";
      activeCategory = "all";
      activeQualification = "all";
      applyState(readState().component, { push: false });
    });

    window.addEventListener("popstate", () => {
      applyState(readState().component, { push: false });
    });

    renderDiagnostics();
    applyState(readState().component, { push: false });
  </script>
</body>
</html>
"""
    header_typography_css = dashboard_ui_primitives.header_typography_css(
        kicker_selector=".hero-overline",
        title_selector=".registry-title",
        subtitle_selector=".registry-subtitle",
        subtitle_max_width="100%",
        mobile_breakpoint_px=760,
        mobile_title_size_px=22,
        mobile_subtitle_size_px=13,
    )
    hero_panel_css = dashboard_ui_primitives.hero_panel_css(
        container_selector=".registry-hero",
    )
    sticky_filter_shell_css = dashboard_ui_primitives.sticky_filter_shell_css(
        shell_selector=".registry-filters-shell",
        top_px=10,
    )
    sticky_filter_css = dashboard_ui_primitives.sticky_filter_bar_css(
        container_selector=".registry-controls",
        columns="minmax(260px, 1.35fr) minmax(180px, 1fr) minmax(190px, 1fr) auto",
        field_selector=".registry-controls input, .registry-controls select",
        focus_selector=".registry-controls input:focus, .registry-controls select:focus",
        top_px=10,
    )
    page_body_css = dashboard_ui_primitives.page_body_typography_css(
        selector="html, body",
    )
    control_label_css = dashboard_ui_primitives.control_label_css(
        selector=".control-title",
    )
    brief_section_label_css = dashboard_ui_primitives.control_label_css(
        selector=".answers-head",
        color="#1f4868",
        size_px=12,
        letter_spacing_em=0.06,
        line_height=1.2,
    )
    operator_readout_label_css = dashboard_ui_primitives.operator_readout_label_typography_css(
        selector=".operator-readout-label",
    )
    content_copy_css = dashboard_ui_primitives.content_copy_css(
        selectors=(
            ".trigger-list",
            ".trigger-list li",
            ".spec-doc p",
            ".spec-doc ul",
            ".spec-doc li",
            ".event-summary",
        ),
    )
    detail_identity_css = dashboard_ui_primitives.detail_identity_typography_css(
        title_selector=".component-name",
        subtitle_selector=".component-subtitle-unused",
        title_size_px=24,
        medium_title_size_px=22,
        small_title_size_px=19,
    )
    operator_readout_layout_css = "\n\n".join(
        (
            dashboard_ui_primitives.operator_readout_host_shell_css(
                shell_selector=".operator-readout-shell",
                heading_selector=".operator-readout-shell .operator-readout-shell-heading",
                body_selector=".operator-readout-shell .operator-readout-shell-body",
            ),
            dashboard_ui_primitives.operator_readout_host_heading_css(
                selector=".operator-readout-shell .operator-readout-shell-heading",
            ),
            dashboard_ui_primitives.operator_readout_layout_css(
                container_selector=".operator-readout",
                meta_selector=".operator-readout-meta",
                main_selector=".operator-readout-main",
                details_selector=".operator-readout-details",
                section_selector=".operator-readout-section",
                proof_selector=".operator-readout-proof",
                footnote_selector=".operator-readout-footnote",
            ),
        )
    )
    operator_readout_copy_css = dashboard_ui_primitives.operator_readout_copy_typography_css(
        selector=".operator-readout-copy",
        line_height=1.55,
        color="#27445e",
    )
    kpi_card_surface_css = dashboard_ui_primitives.kpi_card_surface_css(
        card_selector=".kpi-card",
    )
    kpi_typography_css = dashboard_ui_primitives.governance_kpi_label_value_css(
        label_selector=".kpi-label",
        value_selector=".kpi-value",
    )
    workspace_layout_css = dashboard_ui_primitives.split_detail_workspace_css(
        selector=".workspace",
    )
    label_surface_css = dashboard_ui_primitives.label_surface_css(
        selector=".label",
        min_height_px=0,
        padding="4px 10px",
        background="#f6faf7",
        border_color="#d6e2da",
        color="#334155",
        border_radius_px=4,
        border_width_px=1,
    )
    label_typography_css = dashboard_ui_primitives.label_badge_typography_css(
        selector=".label",
        color="#334155",
        size_px=11,
    )
    label_tone_css = dashboard_ui_primitives.subtle_label_tone_css(
        selector=".label.warn",
        background="#f8efe2",
        border_color="#ead3b6",
        color="#8a6137",
    )
    operator_readout_meta_css = "\n\n".join(
        (
            dashboard_ui_primitives.operator_readout_meta_pill_css(
                selector=".operator-readout-meta-item",
            ),
            dashboard_ui_primitives.operator_readout_meta_semantic_css(
                selector=".operator-readout-meta-item",
            ),
        )
    )
    summary_row_typography_css = dashboard_ui_primitives.inline_label_value_copy_css(
        row_selectors=(".summary-row",),
        label_selectors=(".summary-row strong",),
        size_px=15,
        line_height=1.55,
        color="#27445e",
        label_color="#22496f",
    )
    action_chip_css = dashboard_ui_primitives.detail_action_chip_css(
        selector=".action-chip",
        color="var(--action-text)",
        border_color="var(--action-border)",
        background="var(--action-bg)",
        hover_border_color="var(--action-border-hover)",
        hover_background="var(--action-bg-hover)",
        hover_color="var(--action-text-hover)",
    )
    detail_action_chip_css = dashboard_ui_primitives.detail_action_chip_css(
        selector=".detail-action-chip",
    )
    detail_label_chip_css = dashboard_ui_primitives.detail_label_chip_css(
        selector=".detail-chip-label",
        color="var(--label-text)",
    )
    detail_action_chip_semantic_css = "\n\n".join(
        (
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".detail-action-chip.tone-gov",
                border_color="#8cb8f4",
                background="#eaf3ff",
                color="#1f4795",
                hover_border_color="#68a0eb",
                hover_background="#deebff",
                hover_color="#1d4ed8",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".detail-action-chip.tone-infra",
                border_color="#7ddfd4",
                background="#e6fbf7",
                color="#0f766e",
                hover_border_color="#57ccc0",
                hover_background="#d8f7f1",
                hover_color="#0f766e",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".detail-action-chip.tone-data",
                border_color="#c8a4f8",
                background="#f4ecff",
                color="#7e22ce",
                hover_border_color="#b889f3",
                hover_background="#eddfff",
                hover_color="#7e22ce",
            ),
            dashboard_ui_primitives.subtle_link_label_tone_css(
                selector=".detail-action-chip.tone-engine",
                border_color="#f3bf84",
                background="#fff3e2",
                color="#b45309",
                hover_border_color="#eeaa63",
                hover_background="#ffeacf",
                hover_color="#b45309",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".detail-chip-label.tone-gov",
                background="#eaf3ff",
                border_color="#8cb8f4",
                color="#1f4795",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".detail-chip-label.tone-infra",
                background="#e6fbf7",
                border_color="#7ddfd4",
                color="#0f766e",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".detail-chip-label.tone-data",
                background="#f4ecff",
                border_color="#c8a4f8",
                color="#7e22ce",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".detail-chip-label.tone-engine",
                background="#fff3e2",
                border_color="#f3bf84",
                color="#b45309",
            ),
        )
    )
    registry_secondary_typography_css = "\n\n".join(
        (
            dashboard_ui_primitives.section_heading_css(
                selector=".pane-head",
                color="#2a5078",
                size_px=13,
                line_height=1.2,
                letter_spacing_em=0.045,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".group-head",
                color="#547196",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".component-card-title",
                color="#28496d",
                size_px=14,
                line_height=1.2,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.detail_disclosure_title_css(
                selector=".detail-disclosure-title",
                color="#22496f",
                size_px=15,
                line_height=1.55,
                weight=700,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.caption_typography_css(
                selector=".component-meta",
                color="var(--muted)",
                size_px=12,
                line_height=1.25,
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".context-count",
                color="#2f4563",
                size_px=13,
                line_height=1.0,
                letter_spacing_em=0.0,
                weight=800,
                margin="0",
            ),
            summary_row_typography_css,
            dashboard_ui_primitives.card_title_typography_css(
                selector=".spec-doc h3",
                color="#21466d",
                size_px=15,
                line_height=1.15,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".spec-doc h4",
                color="#21466d",
                size_px=14,
                line_height=1.15,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".spec-doc h5",
                color="#21466d",
                size_px=13,
                line_height=1.15,
                letter_spacing_em=0.0,
                margin="0",
            ),
        )
    )
    registry_code_typography_css = dashboard_ui_primitives.code_typography_css(
        selector=".spec-doc code",
        color="inherit",
        size_px=12,
        line_height=1.2,
        font_family='ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
    )
    context_heading_css = "\n\n".join(
        (
            dashboard_ui_primitives.section_heading_css(
                selector=".context-title",
                color="#4b6283",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.06,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".timeline-head",
                color="#34597f",
                size_px=11,
                line_height=1.0,
                letter_spacing_em=0.07,
                margin="0",
            ),
        )
    )
    auxiliary_button_css = "\n\n".join(
        (
            dashboard_ui_primitives.details_disclosure_caret_css(
                details_selector=".trigger-expand",
                label_selector=".trigger-summary-title",
                color="#64748b",
                size_px=11,
                gap_px=6,
            ),
            dashboard_ui_primitives.details_disclosure_caret_css(
                details_selector=".spec-expand",
                label_selector=".spec-summary-title",
                color="#64748b",
                size_px=11,
                gap_px=6,
            ),
            dashboard_ui_primitives.details_disclosure_caret_css(
                details_selector=".context-section",
                label_selector=".context-toggle-label",
                color="#64748b",
                size_px=11,
                gap_px=6,
            ),
            dashboard_ui_primitives.button_typography_css(
                selector=".artifact",
                color="#31547a",
                size_px=12,
                line_height=1.0,
            ),
            dashboard_ui_primitives.button_typography_css(
                selector=".diagnostics > summary",
                color="#8a4b00",
                size_px=12,
                line_height=1.35,
                letter_spacing_em=0.01,
            ),
        )
    )
    auxiliary_copy_css = "\n\n".join(
        (
            dashboard_ui_primitives.content_copy_css(
                selectors=(".desc",),
                size_px=13,
                line_height=1.45,
                color="#2b4667",
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".empty",
                color="var(--muted)",
                size_px=13,
                line_height=1.4,
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".event-top",
                color="var(--muted)",
                size_px=12,
                line_height=1.0,
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".diag-item",
                color="#7a4100",
                size_px=12,
                line_height=1.35,
            ),
        )
    )
    tooltip_surface_css, tooltip_runtime_js = dashboard_ui_runtime_primitives.quick_tooltip_bundle(
        excluded_closest_selectors=(".component-btn",),
    )
    return (
        html.replace("__ODYLITH_REGISTRY_PAGE_BODY__", page_body_css)
        .replace("__ODYLITH_REGISTRY_HERO_PANEL__", hero_panel_css)
        .replace("__ODYLITH_REGISTRY_HEADER_TYPOGRAPHY__", header_typography_css)
        .replace("__ODYLITH_REGISTRY_FILTER_SHELL__", sticky_filter_shell_css)
        .replace("__ODYLITH_REGISTRY_STICKY_FILTER_BAR__", sticky_filter_css)
        .replace("__ODYLITH_REGISTRY_CONTROL_LABEL__", control_label_css)
        .replace("__ODYLITH_REGISTRY_BRIEF_LABELS__", brief_section_label_css)
        .replace("__ODYLITH_REGISTRY_OPERATOR_READOUT_RUNTIME_JS__", operator_readout.operator_readout_runtime_helpers_js())
        .replace("__ODYLITH_REGISTRY_OPERATOR_READOUT_LAYOUT__", operator_readout_layout_css)
        .replace("__ODYLITH_REGISTRY_OPERATOR_READOUT_LABEL__", operator_readout_label_css)
        .replace("__ODYLITH_REGISTRY_OPERATOR_READOUT_COPY__", operator_readout_copy_css)
        .replace("__ODYLITH_REGISTRY_OPERATOR_READOUT_META__", operator_readout_meta_css)
        .replace("__ODYLITH_REGISTRY_WORKSPACE_LAYOUT__", workspace_layout_css)
        .replace("__ODYLITH_REGISTRY_DETAIL_IDENTITY_TYPOGRAPHY__", detail_identity_css)
        .replace("__ODYLITH_REGISTRY_KPI_CARD_SURFACE__", kpi_card_surface_css)
        .replace("__ODYLITH_KPI_TYPOGRAPHY__", kpi_typography_css)
        .replace("__ODYLITH_REGISTRY_LABEL_SURFACE__", label_surface_css)
        .replace("__ODYLITH_REGISTRY_LABEL_TYPOGRAPHY__", label_typography_css)
        .replace("__ODYLITH_REGISTRY_LABEL_TONES__", label_tone_css)
        .replace("__ODYLITH_REGISTRY_ACTION_CHIP__", action_chip_css)
        .replace("__ODYLITH_REGISTRY_DETAIL_ACTION_CHIP__", detail_action_chip_css)
        .replace("__ODYLITH_REGISTRY_DETAIL_LABEL_CHIP__", detail_label_chip_css)
        .replace("__ODYLITH_REGISTRY_DETAIL_ACTION_TONES__", detail_action_chip_semantic_css)
        .replace("__ODYLITH_REGISTRY_SECONDARY_TYPOGRAPHY__", registry_secondary_typography_css)
        .replace("__ODYLITH_REGISTRY_CODE_TYPOGRAPHY__", registry_code_typography_css)
        .replace("__ODYLITH_REGISTRY_CONTEXT_HEADINGS__", context_heading_css)
        .replace("__ODYLITH_REGISTRY_AUX_BUTTON_TYPOGRAPHY__", auxiliary_button_css)
        .replace("__ODYLITH_REGISTRY_AUX_COPY__", auxiliary_copy_css)
        .replace("__ODYLITH_REGISTRY_TOOLTIP_SURFACE__", tooltip_surface_css)
        .replace("__ODYLITH_REGISTRY_QUICK_TOOLTIP_RUNTIME__", tooltip_runtime_js)
        .replace("__ODYLITH_REGISTRY_CONTENT_COPY__", content_copy_css)
        .replace("__ODYLITH_BRAND_HEAD__", str(payload.get("brand_head_html", "")).strip())
        .replace("__DATA__", data_json)
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    output_path = _resolve(repo_root, str(args.output))

    manifest_token = str(args.manifest).strip()
    manifest_path = (
        registry.default_manifest_path(repo_root=repo_root)
        if manifest_token == registry.DEFAULT_MANIFEST_PATH
        else _resolve(repo_root, manifest_token)
    )
    catalog_path = _resolve(repo_root, str(args.catalog))
    ideas_root = _resolve(repo_root, str(args.ideas_root))
    stream_path = _resolve(repo_root, str(args.stream))

    payload = _build_payload(
        repo_root=repo_root,
        output_path=output_path,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        stream_path=stream_path,
        runtime_mode=str(args.runtime_mode),
    )
    bundle_paths = dashboard_surface_bundle.build_paths(output_path=output_path, asset_prefix="registry")
    component_rows = [
        row
        for row in payload.get("components", [])
        if isinstance(row, dict)
    ]
    detail_rows = {
        str(row.get("component_id", "")).strip().lower(): _build_registry_detail_row(row)
        for row in component_rows
        if str(row.get("component_id", "")).strip()
    }
    detail_manifest, detail_shards = _chunk_registry_items(
        items=detail_rows,
        shard_size=_REGISTRY_DETAIL_SHARD_SIZE,
        file_stem_prefix="registry-detail-shard",
    )
    payload["components"] = [_build_registry_summary_row(row) for row in component_rows]
    payload["detail_manifest"] = detail_manifest
    payload["brand_head_html"] = brand_assets.render_brand_head_html(repo_root=repo_root, output_path=output_path)
    payload["data_source"] = {
        "preferred_backend": (
            "runtime" if str(args.runtime_mode).strip().lower() != "standalone" else "staticSnapshot"
        ),
        "available_backends": ["runtime", "staticSnapshot"],
        "runtime_base_url": "",
    }
    payload["generated_utc"] = stable_generated_utc.resolve_for_js_assignment_file(
        output_path=bundle_paths.payload_js_path,
        global_name="__ODYLITH_REGISTRY_DATA__",
        payload=payload,
    )
    payload["generated_local_date"] = dashboard_time.pacific_display_date_from_utc_token(
        payload["generated_utc"],
        default="-",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bundled_html, payload_js, control_js = dashboard_surface_bundle.externalize_surface_bundle(
        html_text=_render_html(payload=payload),
        payload=payload,
        paths=bundle_paths,
        spec=dashboard_surface_bundle.standard_surface_bundle_spec(
            asset_prefix="registry",
            payload_global_name="__ODYLITH_REGISTRY_DATA__",
            embedded_json_script_id="registryData",
            bootstrap_binding_name="DATA",
            allow_missing_embedded_json=True,
            shell_tab="registry",
            shell_frame_id="frame-registry",
            query_passthrough=(
                ("component", ("component",)),
            ),
        ),
    )
    output_path.write_text(bundled_html, encoding="utf-8")
    bundle_paths.payload_js_path.write_text(payload_js, encoding="utf-8")
    bundle_paths.control_js_path.write_text(control_js, encoding="utf-8")
    active_detail_paths: set[Path] = set()
    for filename, shard_payload in detail_shards:
        shard_path = output_path.parent / filename
        shard_path.write_text(
            dashboard_surface_bundle.render_payload_merge_js(
                global_name="__ODYLITH_REGISTRY_DETAIL_SHARDS__",
                payload=shard_payload,
            ),
            encoding="utf-8",
        )
        active_detail_paths.add(shard_path.resolve())
    for stale_path in output_path.parent.glob("registry-detail-shard-*.v1.js"):
        if stale_path.resolve() in active_detail_paths:
            continue
        if stale_path.is_file():
            stale_path.unlink()

    print("registry dashboard render passed")
    print(f"- output: {output_path}")
    print(f"- components: {int(payload.get('counts', {}).get('components', 0) or 0)}")
    print(f"- events: {int(payload.get('counts', {}).get('events', 0) or 0)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

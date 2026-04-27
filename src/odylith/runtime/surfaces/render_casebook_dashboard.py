"""Render the Casebook bug knowledge surface.

Casebook is a shell-owned, read-only explorer over the repo bug knowledge base.
Markdown under ``odylith/casebook/bugs/`` remains authoritative; this renderer only projects a
searchable/filterable local view.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.governance import casebook_source_validation
from odylith.runtime.surfaces import brand_assets
from odylith.runtime.surfaces import dashboard_shell_links
from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.surfaces import dashboard_time
from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import dashboard_ui_runtime_primitives
from odylith.runtime.surfaces import generated_surface_refresh_guards
from odylith.runtime.surfaces import surface_path_helpers
from odylith.runtime.surfaces import source_bundle_mirror
from odylith.runtime.common import stable_generated_utc
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_store

_CASEBOOK_DETAIL_SHARD_SIZE = 32
_CASEBOOK_REFRESH_GUARD_KEY = "casebook-dashboard-render"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Render odylith/casebook/casebook.html from the bug knowledge base.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="odylith/casebook/casebook.html")
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local runtime projection store when available for bug rows.",
    )
    return parser.parse_args(argv)


def _refresh_guard_watched_paths() -> tuple[str, ...]:
    return (
        "odylith/casebook/bugs",
        "odylith/registry/source",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        *agent_runtime_contract.candidate_stream_tokens(),
        "src/odylith/runtime/common",
        "src/odylith/runtime/context_engine",
        "src/odylith/runtime/governance",
        "src/odylith/runtime/surfaces",
    )


def _chunk_casebook_items(
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


def _build_casebook_summary_row(row: Mapping[str, Any]) -> dict[str, Any]:
    coverage = row.get("intelligence_coverage")
    return {
        "bug_id": str(row.get("bug_id", "")).strip(),
        "bug_key": str(row.get("bug_key", "")).strip(),
        "bug_route": str(row.get("bug_route", "")).strip(),
        "bug_aliases": [str(token).strip() for token in row.get("bug_aliases", []) if str(token).strip()]
        if isinstance(row.get("bug_aliases"), list)
        else [],
        "title": str(row.get("title", "")).strip(),
        "date": str(row.get("date", "")).strip(),
        "severity": str(row.get("severity", "")).strip(),
        "severity_token": str(row.get("severity_token", "")).strip(),
        "status": str(row.get("status", "")).strip(),
        "status_token": str(row.get("status_token", "")).strip(),
        "components": str(row.get("components", "")).strip(),
        "archive_bucket": str(row.get("archive_bucket", "")).strip(),
        "source_path": str(row.get("source_path", "")).strip(),
        "source_href": str(row.get("source_href", "")).strip(),
        "source_exists": bool(row.get("source_exists")),
        "is_open": bool(row.get("is_open")),
        "is_open_critical": bool(row.get("is_open_critical")),
        "summary": str(row.get("summary", "")).strip(),
        "workstreams": [str(token).strip() for token in row.get("workstreams", []) if str(token).strip()]
        if isinstance(row.get("workstreams"), list)
        else [],
        "workstream_links": [dict(item) for item in row.get("workstream_links", []) if isinstance(item, Mapping)]
        if isinstance(row.get("workstream_links"), list)
        else [],
        "intelligence_coverage": dict(coverage) if isinstance(coverage, Mapping) else {},
        "proof_state": dict(row.get("proof_state", {})) if isinstance(row.get("proof_state"), Mapping) else {},
        "proof_state_resolution": (
            dict(row.get("proof_state_resolution", {}))
            if isinstance(row.get("proof_state_resolution"), Mapping)
            else {}
        ),
        "claim_guard": dict(row.get("claim_guard", {})) if isinstance(row.get("claim_guard"), Mapping) else {},
        "search_text": str(row.get("search_text", "")).strip(),
    }


def _build_casebook_detail_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in dict(row).items()
        if str(key) != "search_text"
    }


def _build_payload(
    *,
    repo_root: Path,
    output_path: Path,
    runtime_mode: str,
) -> dict[str, Any]:
    def _dedupe_rows_by_signature(
        rows: Sequence[Mapping[str, Any]],
        *,
        signature_fields: Sequence[str],
        normalizers: Mapping[str, object] | None = None,
    ) -> list[dict[str, Any]]:
        normalizers = normalizers or {}
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in rows:
            if not isinstance(item, Mapping):
                continue
            key_parts: list[str] = []
            for field in signature_fields:
                raw = str(item.get(field, "")).strip()
                normalizer = normalizers.get(field)
                if callable(normalizer):
                    raw = str(normalizer(raw)).strip()
                key_parts.append(f"{field}:{raw.casefold()}")
            key = "||".join(key_parts)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(dict(item))
        return deduped

    def _shell_href(tab: str, **params: str) -> str:
        return f"../index.html{dashboard_shell_links.shell_href(tab=tab, **params)}"

    def _path_links(paths: Sequence[Any]) -> list[dict[str, str]]:
        links = surface_path_helpers.path_links(
            repo_root=repo_root,
            output_path=output_path,
            values=[str(raw).strip() for raw in paths if str(raw).strip()],
        )
        return _dedupe_rows_by_signature(
            rows=links,
            signature_fields=("path", "href"),
            normalizers={
                "path": lambda token: str(token).strip(),
                "href": lambda token: str(token).strip(),
            },
        )

    def _link_signature(row: Mapping[str, Any]) -> str:
        path = str(row.get("path", "")).strip().casefold()
        href = str(row.get("href", "")).strip()
        return f"{path}||{href}"

    def _exclude_overlapping_links(
        rows: Sequence[Mapping[str, Any]],
        *,
        blocked: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        blocked_keys = {_link_signature(row) for row in blocked if isinstance(row, Mapping)}
        return [
            dict(row)
            for row in rows
            if isinstance(row, Mapping) and _link_signature(row) not in blocked_keys
        ]

    def _bug_aliases(*, bug_id: str, bug_key: str, source_path: str) -> list[str]:
        aliases: list[str] = []
        for raw in (bug_id, bug_key, source_path):
            token = str(raw or "").strip()
            if not token or token in aliases:
                continue
            aliases.append(token)
            path_token = Path(token).as_posix()
            if path_token not in aliases:
                aliases.append(path_token)
            name_token = Path(path_token).name
            if name_token and name_token not in aliases:
                aliases.append(name_token)
            if path_token.startswith("odylith/casebook/bugs/"):
                relative_token = path_token.removeprefix("odylith/casebook/bugs/")
                if relative_token and relative_token not in aliases:
                    aliases.append(relative_token)
        return aliases

    rows = odylith_context_engine_store.load_bug_snapshot(
        repo_root=repo_root,
        runtime_mode=runtime_mode,
    )
    payload_rows: list[dict[str, Any]] = []
    severity_tokens: set[str] = set()
    status_tokens: set[str] = set()
    for row in rows:
        source_path = str(row.get("source_path", "")).strip()
        bug_id = str(row.get("bug_id", "")).strip()
        bug_key = str(row.get("bug_key", "")).strip()
        source_href = ""
        if source_path:
            source_target = surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=source_path)
            source_href = (
                surface_path_helpers.relative_href(output_path=output_path, target=source_target)
                if source_target.is_file()
                else ""
            )
        workstreams = [str(token).strip() for token in row.get("workstreams", []) if str(token).strip()]
        deduped_workstreams: list[str] = []
        seen_workstreams: set[str] = set()
        for token in workstreams:
            normalized = token.casefold()
            if normalized in seen_workstreams:
                continue
            seen_workstreams.add(normalized)
            deduped_workstreams.append(token)
        workstreams = deduped_workstreams
        diagram_rows = [
            dict(diagram)
            for diagram in row.get("diagram_refs", [])
            if isinstance(diagram, dict) and str(diagram.get("diagram_id", "")).strip()
        ]
        diagram_title_map = {
            str(diagram.get("diagram_id", "")).strip().upper(): str(diagram.get("title", "")).strip()
            or str(diagram.get("diagram_id", "")).strip().upper()
            for diagram in diagram_rows
        }
        severity_token = str(row.get("severity_token", "")).strip().lower()
        status_token = str(row.get("status_token", "")).strip().lower()
        if severity_token:
            severity_tokens.add(severity_token)
        if status_token:
            status_tokens.add(status_token)
        component_links: list[dict[str, Any]] = []
        for match in row.get("component_matches", []):
            if not isinstance(match, dict):
                continue
            component_id = str(match.get("component_id", "")).strip()
            if not component_id:
                continue
            spec_ref = str(match.get("spec_ref", "")).strip()
            spec_href = ""
            if spec_ref:
                spec_target = surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=spec_ref)
                spec_href = (
                    surface_path_helpers.relative_href(output_path=output_path, target=spec_target)
                    if spec_target.is_file()
                    else ""
                )
            component_links.append(
                {
                    "component_id": component_id,
                    "name": str(match.get("name", "")).strip() or component_id,
                    "spec_ref": spec_ref,
                    "spec_href": spec_href,
                    "registry_href": _shell_href("registry", component=component_id),
                    "workstream_links": _dedupe_rows_by_signature(
                        (
                            {
                                "workstream": token,
                                "href": _shell_href("radar", workstream=token),
                            }
                            for token in match.get("workstreams", [])
                            if str(token).strip()
                        ),
                        signature_fields=("workstream", "href"),
                        normalizers={
                            "workstream": lambda token: str(token).strip().upper(),
                            "href": lambda token: str(token).strip(),
                        },
                    ),
                    "diagram_links": _dedupe_rows_by_signature(
                        (
                            {
                                "diagram_id": diagram_id,
                                "title": diagram_title_map.get(diagram_id, diagram_id),
                                "href": _shell_href("atlas", diagram=diagram_id),
                            }
                            for raw in match.get("diagrams", [])
                            for diagram_id in [str(raw).strip().upper()]
                            if diagram_id
                        ),
                        signature_fields=("diagram_id", "href"),
                        normalizers={
                            "diagram_id": lambda token: str(token).strip().upper(),
                            "href": lambda token: str(token).strip(),
                        },
                    ),
                }
            )
        component_links = _dedupe_rows_by_signature(
            component_links,
            signature_fields=("component_id",),
            normalizers={
                "component_id": lambda token: str(token).strip().casefold(),
            },
        )
        code_ref_links = _path_links(row.get("code_refs", []))
        doc_ref_links = _path_links(row.get("doc_refs", []))
        test_ref_links = _path_links(row.get("test_refs", []))
        contract_ref_links = _path_links(row.get("contract_refs", []))
        agent_guidance = dict(row.get("agent_guidance", {})) if isinstance(row.get("agent_guidance"), dict) else {}
        agent_guidance["proof_links"] = _exclude_overlapping_links(
            _path_links(agent_guidance.get("proof_paths", [])),
            blocked=[*code_ref_links, *doc_ref_links, *test_ref_links, *contract_ref_links],
        )
        payload_rows.append(
            {
                "bug_id": bug_id,
                "bug_key": bug_key,
                "bug_route": bug_id or source_path or bug_key,
                "bug_aliases": _bug_aliases(bug_id=bug_id, bug_key=bug_key, source_path=source_path),
                "title": str(row.get("title", "")).strip(),
                "date": str(row.get("date", "")).strip(),
                "severity": str(row.get("severity", "")).strip(),
                "severity_token": severity_token,
                "status": str(row.get("status", "")).strip(),
                "status_token": status_token,
                "components": str(row.get("components", "")).strip(),
                "component_tokens": [str(token).strip() for token in row.get("component_tokens", []) if str(token).strip()],
                "archive_bucket": str(row.get("archive_bucket", "")).strip(),
                "source_path": source_path,
                "source_href": source_href,
                "source_exists": bool(row.get("source_exists")),
                "is_open": bool(row.get("is_open")),
                "is_open_critical": bool(row.get("is_open_critical")),
                "summary": str(row.get("summary", "")).strip(),
                "workstreams": workstreams,
                "workstream_links": _dedupe_rows_by_signature(
                    (
                        {
                            "workstream": token,
                            "href": _shell_href("radar", workstream=token),
                        }
                        for token in workstreams
                        if str(token).strip()
                    ),
                    signature_fields=("workstream", "href"),
                    normalizers={
                        "workstream": lambda token: str(token).strip().upper(),
                        "href": lambda token: str(token).strip(),
                    },
                ),
                "fields": dict(row.get("fields", {})) if isinstance(row.get("fields"), dict) else {},
                "detail_sections": _dedupe_rows_by_signature(
                    (
                        {
                            "field": str(section.get("field", "")).strip(),
                            "value": str(section.get("value", "")).strip(),
                            "kind": str(section.get("kind", "")).strip(),
                        }
                        for section in row.get("detail_sections", [])
                        if isinstance(section, dict) and str(section.get("field", "")).strip()
                    ),
                    signature_fields=("field",),
                    normalizers={
                        "field": lambda token: str(token).strip().casefold(),
                        "value": lambda token: str(token).strip(),
                    },
                ),
                "code_ref_links": code_ref_links,
                "doc_ref_links": doc_ref_links,
                "test_ref_links": test_ref_links,
                "contract_ref_links": contract_ref_links,
                "component_links": component_links,
                "diagram_links": _dedupe_rows_by_signature(
                    (
                        {
                            "diagram_id": str(diagram.get("diagram_id", "")).strip(),
                            "title": str(diagram.get("title", "")).strip() or str(diagram.get("diagram_id", "")).strip(),
                            "slug": str(diagram.get("slug", "")).strip(),
                            "href": _shell_href("atlas", diagram=str(diagram.get("diagram_id", "")).strip()),
                        }
                        for diagram in diagram_rows
                        if str(diagram.get("diagram_id", "")).strip()
                    ),
                    signature_fields=("diagram_id", "href"),
                    normalizers={
                        "diagram_id": lambda token: str(token).strip().upper(),
                        "href": lambda token: str(token).strip(),
                    },
                ),
                "related_bug_links": [
                    {
                        "bug_id": str(related.get("bug_id", "")).strip(),
                        "bug_key": str(related.get("bug_key", "")).strip(),
                        "title": str(related.get("title", "")).strip(),
                        "date": str(related.get("date", "")).strip(),
                        "severity": str(related.get("severity", "")).strip(),
                        "status": str(related.get("status", "")).strip(),
                        "href": _shell_href(
                            "casebook",
                            bug=str(related.get("bug_id", "") or related.get("source_path", "") or related.get("bug_key", "")).strip(),
                        ),
                    }
                    for related in row.get("related_bug_refs", [])
                    if isinstance(related, dict) and str(related.get("bug_key", "")).strip()
                ],
                "agent_guidance": agent_guidance,
                "intelligence_coverage": (
                    dict(row.get("intelligence_coverage", {}))
                    if isinstance(row.get("intelligence_coverage"), dict)
                    else {}
                ),
                "proof_state": dict(row.get("proof_state", {})) if isinstance(row.get("proof_state"), Mapping) else {},
                "proof_state_resolution": (
                    dict(row.get("proof_state_resolution", {}))
                    if isinstance(row.get("proof_state_resolution"), Mapping)
                    else {}
                ),
                "claim_guard": dict(row.get("claim_guard", {})) if isinstance(row.get("claim_guard"), Mapping) else {},
                "search_text": str(row.get("search_text", "")).strip(),
            }
        )

    latest_case = payload_rows[0] if payload_rows else {}
    counts = {
        "total_cases": len(payload_rows),
        "open_total": sum(1 for row in payload_rows if bool(row.get("is_open"))),
        "open_critical": sum(1 for row in payload_rows if bool(row.get("is_open_critical"))),
        "latest_case_title": str(latest_case.get("title", "")).strip(),
        "latest_case_date": str(latest_case.get("date", "")).strip(),
    }
    return {
        "title": "Casebook",
        "subtitle": "Native bug-evidence surface over the repo bug knowledge base.",
        "bugs": payload_rows,
        "counts": counts,
        "filters": {
            "severity_tokens": sorted(severity_tokens),
            "status_tokens": sorted(status_tokens),
        },
    }


def _render_html(*, payload: dict[str, Any]) -> str:
    data_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    page_body_css = dashboard_ui_primitives.page_body_typography_css(selector="body")
    surface_shell_root_css = dashboard_ui_primitives.standard_surface_shell_root_css()
    surface_shell_css = dashboard_ui_primitives.standard_surface_shell_css(
        selector=".shell",
        display="grid",
        gap_px=12,
    )
    header_typography_css = dashboard_ui_primitives.header_typography_css(
        kicker_selector=".kicker",
        title_selector=".hero-title",
        subtitle_selector=".subtitle",
        subtitle_max_width="78ch",
        desktop_single_line_subtitle=False,
        mobile_breakpoint_px=760,
        mobile_title_size_px=22,
        mobile_subtitle_size_px=13,
    )
    hero_panel_css = dashboard_ui_primitives.hero_panel_css(
        container_selector=".hero",
        margin_bottom="0",
    )
    kpi_card_surface_css = dashboard_ui_primitives.kpi_card_surface_css(card_selector=".kpi-card")
    kpi_grid_css = dashboard_ui_primitives.kpi_grid_layout_css(container_selector=".kpis")
    kpi_typography_css = dashboard_ui_primitives.governance_kpi_label_value_css(
        label_selector=".kpi-label",
        value_selector=".kpi-value",
    )
    sticky_filter_shell_css = dashboard_ui_primitives.sticky_filter_shell_css(
        shell_selector=".filters-shell",
        top_px=10,
    )
    sticky_filter_bar_css = dashboard_ui_primitives.sticky_filter_bar_css(
        container_selector=".filters-bar",
        columns="repeat(4, minmax(0, 1fr))",
        field_selector=".filter-control",
        focus_selector=".filter-control:focus",
        top_px=10,
    )
    control_label_css = dashboard_ui_primitives.control_label_css(
        selector=".control-label",
        color="var(--ink-muted)",
        size_px=11,
        letter_spacing_em=0.04,
    )
    workspace_layout_css = dashboard_ui_primitives.split_detail_workspace_css(
        selector=".workspace",
        left_min_px=340,
        left_max_px=430,
    )
    panel_surface_css = ""
    row_surface_css = ""
    narrative_section_surface_css = dashboard_ui_primitives.panel_surface_css(
        selector=".empty-state",
        padding="12px 13px",
        radius_px=12,
        gap_px=8,
        shadow="none",
        background="linear-gradient(180deg, #ffffff, #fbfdff)",
    )
    label_surface_css = dashboard_ui_primitives.label_surface_css(
        selector=".meta-chip, .list-chip, .filter-chip",
        padding="4px 10px",
        background="#f6faf7",
        border_color="#dbe5df",
        color="#334155",
        border_radius_px=4,
        min_height_px=0,
    )
    label_typography_css = dashboard_ui_primitives.label_badge_typography_css(
        selector=".meta-chip, .list-chip, .filter-chip",
        color="#334155",
        size_px=11,
        line_height=1.0,
        letter_spacing_em=0.03,
    )
    label_tone_css = "\n\n".join(
        (
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".warn-chip",
                background="#fff7ed",
                border_color="#f3c58e",
                color="#9a3412",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".critical-chip",
                background="#fef2f2",
                border_color="#fecaca",
                color="#b91c1c",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".archive-chip",
                background="#eef2f7",
                border_color="#d7e0e9",
                color="#53687f",
            ),
        )
    )
    detail_action_chip_css = dashboard_ui_primitives.detail_action_chip_css(selector=".action-chip")
    identifier_typography_css = "\n\n".join(
        (
            dashboard_ui_primitives.surface_identifier_typography_css(
                selector=".component-subtitle, .ref-meta",
                color="var(--ink-muted)",
                line_height=1.45,
            ),
            dashboard_ui_primitives.surface_identifier_typography_css(
                selector=".bug-row-kicker",
                color="var(--ink-muted)",
                margin="0 0 4px",
                line_height=1.2,
                letter_spacing_em=0.08,
                text_transform="uppercase",
            ),
        )
    )
    tooltip_surface_css, tooltip_runtime_js = dashboard_ui_runtime_primitives.quick_tooltip_bundle(
        binding_guard_dataset_key="odylithCasebookTooltipBound",
        function_name="initCasebookQuickTooltips",
    )
    section_heading_css = "\n\n".join(
        (
            dashboard_ui_primitives.operator_readout_host_heading_css(
                selector=".section-heading",
                color="#27445e",
                size_px=12,
                letter_spacing_em=0.06,
                margin="0",
                line_height=1.2,
                weight=700,
            ),
            dashboard_ui_primitives.detail_disclosure_title_css(
                selector=".disclosure-title",
                color="#27445e",
                size_px=13,
                line_height=1.45,
                weight=700,
                letter_spacing_em=0.0,
                margin="0",
            ),
        )
    )
    secondary_heading_css = "\n\n".join(
        (
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".meta-label",
                color="var(--ink-muted)",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".bug-row-date",
                color="var(--ink-muted)",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".pivot-title",
                color="var(--ink-muted)",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.operator_readout_label_typography_css(
                selector=".signal-label, .inline-note-label",
            ),
        )
    )
    compact_fact_css = dashboard_ui_primitives.compact_label_value_typography_css(
        label_selector=".summary-fact-label",
        value_selector=".summary-fact-value",
        label_color="var(--ink-muted)",
        value_color="#16324f",
    )
    inline_row_css = dashboard_ui_primitives.inline_label_value_copy_css(
        row_selectors=(
            ".narrative-row",
            ".coverage-note",
            ".component-note",
            ".link-row-note",
        ),
        label_selectors=(),
        size_px=14,
        line_height=1.55,
        color="var(--ink-soft)",
    )
    card_title_css = "\n\n".join(
        (
            dashboard_ui_primitives.card_title_typography_css(
                selector=".bug-row-title",
                color="var(--ink)",
                size_px=16,
                line_height=1.3,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".detail-title",
                color="var(--ink)",
                size_px=26,
                line_height=1.1,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".component-context-name",
                color="var(--ink)",
                size_px=14,
                line_height=1.2,
                margin="0",
            ),
        )
    )
    copy_css = "\n\n".join(
        (
            dashboard_ui_primitives.content_copy_css(
                selectors=(".bug-row-summary", ".detail-summary", ".detail-copy", ".empty-state"),
                size_px=14,
                line_height=1.5,
                color="var(--ink-soft)",
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".meta-value, .summary-fallback",
                color="var(--ink-soft)",
                size_px=13,
                line_height=1.45,
            ),
        )
    )
    code_typography_css = dashboard_ui_primitives.code_typography_css(
        selector=".bug-row-summary code, .detail-copy code, .meta-value code",
        color="inherit",
        size_px=12,
        line_height=1.2,
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Casebook</title>
  __ODYLITH_BRAND_HEAD__
  <style>
    :root {{
      --bg-a: #f0f9ff;
      --bg-b: #ecfeff;
      --ink: #0b1324;
      --ink-soft: #334155;
      --ink-muted: #64748b;
      --line: #c7d2fe;
      --panel: #ffffff;
      --focus: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      min-height: 100%;
      background:
        radial-gradient(circle at 8% -10%, #dbeafe 0%, transparent 42%),
        radial-gradient(circle at 94% 0%, #ccfbf1 0%, transparent 38%),
        linear-gradient(180deg, var(--bg-a), var(--bg-b));
    }}
    __CASEBOOK_PAGE_BODY__
    __CASEBOOK_SURFACE_SHELL_ROOT__
    __CASEBOOK_SURFACE_SHELL__
    __CASEBOOK_HERO_PANEL__
    .hero {{
      display: grid;
      gap: 10px;
    }}
    .kicker,
    .hero-title,
    .subtitle {{
      margin: 0;
    }}
    __CASEBOOK_HEADER_TYPOGRAPHY__
    __CASEBOOK_KPI_GRID__
    __CASEBOOK_KPI_CARD__
    __CASEBOOK_KPI_TYPOGRAPHY__
    __CASEBOOK_FILTER_SHELL__
    __CASEBOOK_FILTER_BAR__
    __CASEBOOK_CONTROL_LABEL__
    __CASEBOOK_WORKSPACE__
    __CASEBOOK_PANEL_SURFACE__
    __CASEBOOK_ROW_SURFACE__
    __CASEBOOK_EMPTY_STATE_SURFACE__
    __CASEBOOK_LABEL_SURFACE__
    __CASEBOOK_LABEL_TYPOGRAPHY__
    __CASEBOOK_LABEL_TONES__
    __CASEBOOK_ACTION_CHIP__
    __CASEBOOK_SECTION_HEADING__
    __CASEBOOK_SECONDARY_HEADINGS__
    __CASEBOOK_CARD_TITLE__
    __CASEBOOK_COPY__
    __CASEBOOK_CODE_TYPOGRAPHY__
    __CASEBOOK_IDENTIFIER_TYPOGRAPHY__
    .filters-shell {{
      min-width: 0;
      width: 100%;
    }}
    .filters-bar {{
      align-items: end;
      width: 100%;
      justify-items: stretch;
    }}
    .control {{
      display: grid;
      gap: 6px;
      min-width: 0;
      min-inline-size: 0;
      overflow: hidden;
      width: 100%;
    }}
    .filter-control {{
      font-family: inherit;
      min-width: 0;
      min-inline-size: 0;
      inline-size: 100%;
      max-inline-size: 100%;
    }}
    .workspace {{
      min-height: 560px;
    }}
    .list-panel,
    .detail-panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
      overflow: hidden;
      min-width: 0;
    }}
    .panel-head {{
      padding: 12px 14px;
      border-bottom: 1px solid #e2e8f0;
      background: linear-gradient(180deg, #f8fafc, #ffffff);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .panel-head-title {{
      margin: 0;
      color: var(--ink);
      font-size: 12px;
      line-height: 1.2;
      letter-spacing: 0.06em;
      font-weight: 800;
      text-transform: uppercase;
    }}
    .panel-head-meta {{
      color: var(--ink-muted);
      font-size: 12px;
      line-height: 1.35;
      font-weight: 600;
    }}
    .list {{
      max-height: 640px;
      overflow: auto;
      padding: 6px;
      background: #f8fafc;
    }}
    .detail {{
      min-width: 0;
      padding: 18px 20px 22px;
      display: grid;
      gap: 18px;
      align-content: start;
    }}
    .bug-list {{
      display: grid;
      gap: 0;
      align-content: start;
    }}
    .bug-row {{
      width: 100%;
      text-align: left;
      border: 1px solid #d6dce8;
      border-radius: 12px;
      background: #ffffff;
      padding: 10px 10px 9px;
      margin-bottom: 8px;
      cursor: pointer;
      color: inherit;
      transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
    }}
    .bug-row:hover {{
      border-color: #93c5fd;
      box-shadow: 0 8px 18px rgba(15, 23, 42, 0.09);
      transform: translateY(-1px);
    }}
    .bug-row.active {{
      border-color: #1d4ed8;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.22);
    }}
    .bug-row-head {{
      display: flex;
      gap: 8px;
      align-items: flex-start;
      justify-content: space-between;
      min-width: 0;
      margin-bottom: 7px;
    }}
    .bug-row-head > *:first-child {{
      min-width: 0;
    }}
    .bug-row-date {{
      white-space: nowrap;
    }}
.bug-row-meta,
.detail-meta,
.detail-links {{
      display: flex;
      flex-wrap: nowrap;
      gap: 6px;
      align-items: center;
      overflow-x: auto;
      overflow-y: hidden;
      min-width: 0;
      scrollbar-width: none;
      -ms-overflow-style: none;
      scroll-behavior: auto;
}}
.detail-links {{
      align-items: flex-start;
}}
    .detail-head {{
      display: grid;
      gap: 12px;
      padding-bottom: 14px;
      border-bottom: 1px solid rgba(148, 163, 184, 0.18);
    }}
    .detail-headline {{
      display: grid;
      gap: 6px;
      max-width: 80ch;
    }}
    .detail-summary {{
      max-width: 80ch;
    }}
    .section-stack {{
      display: grid;
      gap: 0;
    }}
    .detail-section {{
      display: grid;
      gap: 10px;
      padding-top: 16px;
      border-top: 1px solid rgba(148, 163, 184, 0.18);
      min-width: 0;
    }}
    .detail-section:first-child {{ padding-top: 0; border-top: 0; }}
    .detail-section-agent {{
      margin-top: 16px;
      padding: 14px 15px;
      border: 1px solid rgba(148, 163, 184, 0.24);
      border-radius: 16px;
      background: linear-gradient(180deg, #ffffff, #f5fbf8);
      box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
    }}
    .detail-section-proof {{
      margin-top: 16px;
      padding: 14px 15px;
      border: 1px solid rgba(219, 234, 254, 0.95);
      border-radius: 16px;
      background: linear-gradient(180deg, #ffffff, #f8fbff);
      box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
    }}
    .section-lede {{
      margin: 0;
      color: var(--ink-muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .detail-disclosure {{
      display: block;
    }}
    .detail-disclosure > summary {{
      list-style: none;
      cursor: pointer;
    }}
    .detail-disclosure > summary:focus-visible {{
      outline: 2px solid rgba(191, 219, 254, 0.95);
      outline-offset: 3px;
      border-radius: 6px;
    }}
    .detail-disclosure > summary::-webkit-details-marker {{
      display: none;
    }}
    .detail-disclosure-body {{
      display: grid;
      gap: 10px;
      padding-top: 10px;
      min-width: 0;
    }}
    .signal-label {{
      margin: 0;
    }}
.summary-facts {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
      gap: 10px;
      min-width: 0;
}}
.summary-fact {{
      display: grid;
      gap: 4px;
      align-content: start;
      min-width: 0;
      padding: 10px 12px;
      border: 1px solid rgba(148, 163, 184, 0.22);
      border-radius: 12px;
      background: linear-gradient(180deg, #ffffff, #f8fbff);
      box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
}}
.summary-fact-label,
.summary-fact-value {{
      min-width: 0;
}}
    .brief-stack {{
      display: grid;
      gap: 12px;
    }}
    .brief-card {{
      display: grid;
      gap: 10px;
      padding: 13px 14px;
      border: 1px solid rgba(148, 163, 184, 0.24);
      border-radius: 14px;
      background: linear-gradient(180deg, #ffffff, #f8fbff);
      box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
      min-width: 0;
    }}
    .brief-card-head {{
      display: grid;
      gap: 4px;
    }}
    .brief-card-title,
    .agent-band-title {{
      margin: 0;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.2;
      font-weight: 700;
      letter-spacing: 0.01em;
    }}
    .brief-card-note {{
      margin: 0;
      color: var(--ink-muted);
      font-size: 12px;
      line-height: 1.4;
    }}
    .agent-band {{
      display: grid;
      gap: 14px;
    }}
    .agent-band-block {{
      display: grid;
      gap: 8px;
      min-width: 0;
    }}
    .proof-resolution-note {{
      margin: 0;
    }}
    .agent-disclosure {{
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px dashed rgba(148, 163, 184, 0.28);
    }}
    __CASEBOOK_COMPACT_FACT_TYPOGRAPHY__
    __CASEBOOK_INLINE_ROW_TYPOGRAPHY__
    .narrative-list,
    .link-rows,
    .component-listing {{
      display: grid;
      gap: 10px;
    }}
    .narrative-row,
    .link-row,
    .component-block {{
      min-width: 0;
      display: grid;
      gap: 6px;
      align-content: start;
    }}
    .component-block + .component-block {{
      padding-top: 10px;
      border-top: 1px dashed rgba(148, 163, 184, 0.28);
    }}
    .component-title-block {{
      display: grid;
      gap: 2px;
    }}
    .component-subtitle,
    .ref-meta {{
      margin: 0;
      color: var(--ink-muted);
      line-height: 1.45;
    }}
    .link-group,
    .detail-links,
    .detail-meta,
    .bug-row-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }}
    .detail-links {{
      align-items: flex-start;
    }}

    .bug-row-meta::-webkit-scrollbar,
    .detail-meta::-webkit-scrollbar,
    .detail-links::-webkit-scrollbar,
    .summary-facts::-webkit-scrollbar {{
      display: none;
    }}
    .detail-copy {{
      display: grid;
      gap: 8px;
    }}
    .coverage-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }}
    .agent-checks {{
      margin-top: 2px;
    }}
    .bug-row-title,
    .bug-row-summary,
    .detail-title,
    .detail-summary,
    .detail-copy,
    .summary-fact-value {{
      overflow-wrap: anywhere;
      min-width: 0;
    }}
    .bug-row-kicker,
    .detail-kicker {{
      margin: 0 0 4px;
      color: var(--ink-muted);
      line-height: 1.2;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .bug-row-summary {{
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 4;
      overflow: hidden;
    }}
    .detail-copy p {{
      margin: 0;
    }}
    .detail-copy ul {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 6px;
    }}
    .detail-list {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 6px;
    }}
    .reference-list {{
      margin: 0;
      padding-left: 0;
      list-style: none;
    }}
    .reference-list li {{
      display: grid;
      gap: 3px;
    }}
    .ref-link {{
      color: var(--ink);
      text-decoration: none;
      font-weight: 600;
    }}
    .ref-link:hover {{
      text-decoration: underline;
    }}
    .empty-state {{
      min-height: 84px;
      place-content: center;
    }}
    .muted {{
      color: var(--ink-muted);
    }}
    .action-chip {{
      text-decoration: none;
    }}
    __CASEBOOK_TOOLTIP_SURFACE__
    @media (max-width: 1180px) {{
      .filters-bar {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 1000px) {{
      .workspace {{
        grid-template-columns: 1fr;
      }}
      .rail {{
        max-height: none;
      }}
    }}
    @media (max-width: 760px) {{
      .shell {{
        padding: 18px 14px 28px;
      }}
      .filters-bar {{
        grid-template-columns: 1fr;
      }}
      .summary-chips {{
        min-height: 0;
      }}
      .bug-row-meta,
      .detail-meta,
      .detail-links {{
        flex-wrap: wrap;
      }}
      .summary-facts {{
        grid-template-columns: 1fr;
      }}
    }}
      .detail {{
        padding: 16px 14px 18px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <p class="kicker">Failures, Impact, and Fix Context</p>
      <h1 class="hero-title">Casebook</h1>
      <p class="subtitle">Track what broke, why it mattered, and what to do next from repo bug records and linked evidence.</p>
      <section class="kpis" aria-label="Casebook summary">
        <article class="kpi-card">
          <p class="kpi-label">Open Critical</p>
          <p class="kpi-value" id="kpiOpenCritical">0</p>
        </article>
        <article class="kpi-card">
          <p class="kpi-label">Open Total</p>
          <p class="kpi-value" id="kpiOpenTotal">0</p>
        </article>
        <article class="kpi-card">
          <p class="kpi-label">Total Cases</p>
          <p class="kpi-value" id="kpiTotalCases">0</p>
        </article>
        <article class="kpi-card">
          <p class="kpi-label">Latest Case</p>
          <p class="kpi-value" id="kpiLatestCase">-</p>
        </article>
      </section>
    </section>

    <section class="filters-shell" aria-label="Casebook filters">
      <div class="filters-bar">
        <label class="control" for="searchInput">
          <span class="control-label">Search</span>
          <input id="searchInput" class="filter-control" type="search" placeholder="Search title, components, or bug details" />
        </label>
        <label class="control" for="severityFilter">
          <span class="control-label">Severity</span>
          <select id="severityFilter" class="filter-control"></select>
        </label>
        <label class="control" for="statusFilter">
          <span class="control-label">Status</span>
          <select id="statusFilter" class="filter-control"></select>
        </label>
        <label class="control" for="sortFilter">
          <span class="control-label">Sort</span>
          <select id="sortFilter" class="filter-control"></select>
        </label>
      </div>
    </section>

    <section class="workspace" aria-live="polite">
      <aside class="list-panel" aria-label="Bug selector">
        <div class="panel-head">
          <p class="panel-head-title">Bug Cases</p>
          <span id="listMeta" class="panel-head-meta">Visible: 0</span>
        </div>
        <div class="list">
          <div id="bugList" class="bug-list"></div>
        </div>
      </aside>
      <section class="detail-panel" aria-label="Bug detail">
        <div class="panel-head">
          <p class="panel-head-title">Selected Bug Detail</p>
        </div>
        <section id="detailPane" class="detail" aria-label="Bug detail content"></section>
      </section>
    </section>
  </main>

  <script id="casebookData" type="application/json">{data_json}</script>
  <script>
    const DATA = JSON.parse(document.getElementById("casebookData").textContent || "{{}}");
    const bugSummaries = Array.isArray(DATA.bugs) ? DATA.bugs : [];
    const assetLoadCache = new Map();
    const searchInput = document.getElementById("searchInput");
    const severityFilter = document.getElementById("severityFilter");
    const statusFilter = document.getElementById("statusFilter");
    const sortFilter = document.getElementById("sortFilter");
    const bugList = document.getElementById("bugList");
    const detailPane = document.getElementById("detailPane");
    const listMeta = document.getElementById("listMeta");
    const kpiOpenCritical = document.getElementById("kpiOpenCritical");
    const kpiOpenTotal = document.getElementById("kpiOpenTotal");
    const kpiTotalCases = document.getElementById("kpiTotalCases");
    const kpiLatestCase = document.getElementById("kpiLatestCase");
    let detailRenderToken = 0;
    const BUG_ID_COMPACT_RE = /^(?:CB)?-?(\\d{{1,}})$/i;
    const SORT_DEFAULT = "newest";
    const SORT_OPTIONS = [
      {{ value: "newest", label: "Newest" }},
      {{ value: "oldest", label: "Oldest" }},
      {{ value: "bug-id", label: "Bug ID" }},
      {{ value: "priority", label: "Priority" }},
      {{ value: "status", label: "Status" }},
    ];
    const SORT_TOKENS = new Set(SORT_OPTIONS.map((option) => option.value));
    const HUMAN_SIGNAL_FIELDS = [
      "Failure Signature",
      "Trigger Path",
      "Detected By",
      "Timeline",
    ];
    const HUMAN_IMPACT_FIELDS = [
      "Impact",
      "Blast Radius",
      "Ownership",
      "Invariant Violated",
      "SLO/SLA Impact",
    ];
    const HUMAN_RESPONSE_FIELDS = [
      "Root Cause",
      "Solution",
      "Workaround",
      "Rollback/Forward Fix",
      "Verification",
    ];

    function loadScriptAsset(href) {{
      const token = String(href || "").trim();
      if (!token) return Promise.resolve();
      const resolvedHref = new URL(token, window.location.href).toString();
      if (assetLoadCache.has(resolvedHref)) {{
        return assetLoadCache.get(resolvedHref);
      }}
      const promise = new Promise((resolve, reject) => {{
        const script = document.createElement("script");
        script.src = resolvedHref;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Failed to load Casebook detail shard: ${{resolvedHref}}`));
        document.head.appendChild(script);
      }});
      assetLoadCache.set(resolvedHref, promise);
      return promise;
    }}

    function detailManifest() {{
      const manifest = DATA.detail_manifest;
      return manifest && typeof manifest === "object" ? manifest : {{}};
    }}

    async function loadDetailEntry(detailId) {{
      const token = String(detailId || "").trim();
      if (!token) return null;
      const loaded = window.__ODYLITH_CASEBOOK_DETAIL_SHARDS__ || {{}};
      if (loaded[token] && typeof loaded[token] === "object") {{
        return loaded[token];
      }}
      const shardHref = String(detailManifest()[token] || "").trim();
      if (!shardHref) return null;
      await loadScriptAsset(shardHref);
      const resolved = window.__ODYLITH_CASEBOOK_DETAIL_SHARDS__ || {{}};
      return resolved[token] && typeof resolved[token] === "object" ? resolved[token] : null;
    }}

    const casebookDataSource = {{
      async loadDetail(id) {{
        return loadDetailEntry(id);
      }},
      prefetch(id) {{
        void loadDetailEntry(id);
      }},
    }};

    function escapeHtml(value) {{
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function inlineCodeHtml(value) {{
      return escapeHtml(value).replace(/`([^`]+)`/g, "<code>$1</code>");
    }}

    function canonicalizeBugToken(value) {{
      const token = String(value || "").trim().replace(/^\\.\\//, "");
      if (!token) return "";
      if (token.includes("://")) return "";
      if (/^(?:[A-Za-z]:[\\\\/]|\\/)/.test(token)) return "";
      return token;
    }}

    function canonicalizeFilterToken(value) {{
      return String(value || "").trim().toLowerCase();
    }}

    function canonicalizeSortToken(value) {{
      const token = String(value || "").trim().toLowerCase();
      return SORT_TOKENS.has(token) ? token : SORT_DEFAULT;
    }}

    function normalizeSearchToken(value) {{
      return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "");
    }}

    function canonicalizeBugIdToken(value) {{
      const raw = canonicalizeBugToken(value || "");
      if (!raw) return "";
      const token = raw.toUpperCase();
      if (/^CB-\\d{{3,}}$/.test(token)) return token;
      const compact = token.match(BUG_ID_COMPACT_RE);
      if (!compact) return "";
      return `CB-${{compact[1].padStart(3, "0")}}`;
    }}

    function bugAliasTokens(row) {{
      const aliases = Array.isArray(row && row.bug_aliases) ? row.bug_aliases : [];
      const fallback = [row && row.bug_route, row && row.bug_id, row && row.bug_key, row && row.source_path];
      return [...aliases, ...fallback]
        .map((item) => canonicalizeBugToken(item || ""))
        .filter(Boolean);
    }}

    function bugSearchText(row) {{
      return [
        row && row.bug_id,
        row && row.title,
        row && row.summary,
        row && row.components,
        row && row.bug_key,
        row && row.source_path,
        row && row.search_text,
        ...(Array.isArray(row && row.component_tokens) ? row.component_tokens : []),
      ].join(" ").toLowerCase();
    }}

    function bugExactMatch(row, term) {{
      const lowered = canonicalizeBugToken(term || "").toLowerCase();
      const aliases = bugAliasTokens(row);
      if (lowered && aliases.some((alias) => alias.toLowerCase() === lowered)) return true;
      const canonicalBugId = canonicalizeBugIdToken(term || "");
      if (!canonicalBugId) return false;
      return aliases.some((alias) => canonicalizeBugIdToken(alias) === canonicalBugId);
    }}

    function resolveBugRoute(rows, token) {{
      const normalized = canonicalizeBugToken(token || "");
      if (!normalized) return "";
      const lowered = normalized.toLowerCase();
      const match = rows.find((row) => bugAliasTokens(row).some((alias) => alias.toLowerCase() === lowered));
      return match ? String(match.bug_route || "").trim() : "";
    }}

    function readState() {{
      const params = new URLSearchParams(window.location.search || "");
      return {{
        bug: canonicalizeBugToken(params.get("bug") || ""),
        severity: canonicalizeFilterToken(params.get("severity") || ""),
        status: canonicalizeFilterToken(params.get("status") || ""),
        sort: canonicalizeSortToken(params.get("sort") || SORT_DEFAULT),
      }};
    }}

    function writeState(state) {{
      const query = new URLSearchParams();
      if (state.bug) query.set("bug", state.bug);
      if (state.severity) query.set("severity", state.severity);
      if (state.status) query.set("status", state.status);
      if (canonicalizeSortToken(state.sort) !== SORT_DEFAULT) query.set("sort", canonicalizeSortToken(state.sort));
      const suffix = query.toString() ? `?${{query.toString()}}` : "";
      const next = `${{window.location.pathname}}${{suffix}}`;
      if (next !== `${{window.location.pathname}}${{window.location.search}}`) {{
        window.history.replaceState(null, "", next);
      }}
      if (window.parent && window.parent !== window) {{
        window.parent.postMessage({{
          type: "odylith-casebook-navigate",
          state: {{
            bug: state.bug || "",
            severity: state.severity || "",
            status: state.status || "",
            sort: canonicalizeSortToken(state.sort),
          }},
        }}, "*");
      }}
    }}

    function fillSelect(selectEl, values, current, allLabel) {{
      const rows = [`<option value="">${{escapeHtml(allLabel)}}</option>`];
      for (const token of values) {{
        rows.push(
          `<option value="${{escapeHtml(token)}}"${{token === current ? " selected" : ""}}>${{escapeHtml(token.toUpperCase())}}</option>`
        );
      }}
      selectEl.innerHTML = rows.join("");
    }}

    function fillSortSelect(current) {{
      const active = canonicalizeSortToken(current || SORT_DEFAULT);
      sortFilter.innerHTML = SORT_OPTIONS.map((option) => (
        `<option value="${{escapeHtml(option.value)}}"${{option.value === active ? " selected" : ""}}>${{escapeHtml(option.label)}}</option>`
      )).join("");
    }}

    function renderRichText(text) {{
      const raw = String(text || "").trim();
      if (!raw) return "<p>Not captured in this bug entry.</p>";
      const blocks = raw.split(/\\n\\s*\\n+/).map((item) => item.trim()).filter(Boolean);
      return blocks.map((block) => {{
        const lines = block.split(/\\n/).map((item) => item.replace(/\\s+$/g, "")).filter((item) => item.trim());
        if (!lines.length) return "";
        if (lines.every((line) => /^\\s*[-*]\\s+/.test(line))) {{
          const items = lines.map((line) => `<li>${{inlineCodeHtml(line.replace(/^\\s*[-*]\\s+/, ""))}}</li>`).join("");
          return `<ul>${{items}}</ul>`;
        }}
        return `<p>${{inlineCodeHtml(lines.join(" "))}}</p>`;
      }}).join("");
    }}

    function renderDelimitedList(text) {{
      const raw = String(text || "").trim();
      if (!raw || raw === "-") return "<p>Not captured in this bug entry.</p>";
      const tokens = raw.split(/\\s\\/\\s/).map((item) => item.trim()).filter(Boolean);
      if (tokens.length <= 1) {{
        return `<p>${{inlineCodeHtml(raw)}}</p>`;
      }}
      return `<ul class="detail-list">${{tokens.map((token) => `<li>${{inlineCodeHtml(token)}}</li>`).join("")}}</ul>`;
    }}

    function renderNarrativeFieldRows(fieldNames, fields, formatterMap = {{}}) {{
      const rows = fieldNames
        .map((field) => {{
          const value = String(fields[field] || "").trim();
          if (!value) return "";
          const formatter = typeof formatterMap[field] === "function" ? formatterMap[field] : renderRichText;
          return `
            <div class="narrative-row">
              <p class="signal-label narrative-label">${{escapeHtml(field)}}</p>
              <div class="detail-copy">${{formatter(value)}}</div>
            </div>
          `;
        }})
        .filter(Boolean)
        .join("");
      return rows ? `<div class="narrative-list">${{rows}}</div>` : "";
    }}

    function renderLabeledNarratives(items) {{
      if (!Array.isArray(items) || !items.length) return "";
      const rows = items
        .map((item) => {{
          const label = String(item && item.label || "").trim();
          const value = String(item && item.value || "").trim();
          if (!label || !value) return "";
          return `
            <div class="narrative-row">
              <p class="signal-label narrative-label">${{escapeHtml(label)}}</p>
              <div class="detail-copy">${{renderRichText(value)}}</div>
            </div>
          `;
        }})
        .filter(Boolean)
        .join("");
      return rows ? `<div class="narrative-list">${{rows}}</div>` : "";
    }}

    function actionChipHtml(label, href, tooltip = "") {{
      const text = String(label || "").trim();
      const target = String(href || "").trim();
      if (!text || !target) return "";
      const note = String(tooltip || "").trim();
      const tooltipAttrs = note
        ? ` data-tooltip="${{escapeHtml(note)}}" aria-label="${{escapeHtml(note)}}"`
        : "";
      return `<a class="action-chip" href="${{escapeHtml(target)}}" target="_top" rel="noreferrer"${{tooltipAttrs}}>${{escapeHtml(text)}}</a>`;
    }}

    function renderActionChips(items) {{
      if (!Array.isArray(items) || !items.length) return "";
      const seen = new Set();
      const chips = [];
      for (const item of items) {{
        const label = String(item && item.label || "").trim();
        const href = String(item && item.href || "").trim();
        if (!label || !href) continue;
        const key = `${{label}}::${{href}}`;
        if (seen.has(key)) continue;
        seen.add(key);
        chips.push(actionChipHtml(label, href, item && item.tooltip));
      }}
      return chips.join("");
    }}

    function renderActionChipGroup(items) {{
      const chips = renderActionChips(items);
      return chips ? `<div class="link-group">${{chips}}</div>` : "";
    }}

    function renderLinkRow(label, items) {{
      const chips = renderActionChipGroup(items);
      if (!chips) return "";
      return `
        <div class="link-row">
          <p class="signal-label link-row-label">${{escapeHtml(label)}}</p>
          ${{chips}}
        </div>
      `;
    }}

    function dedupeByField(items) {{
      if (!Array.isArray(items)) return [];
      const seen = new Set();
      const rows = [];
      for (const item of items) {{
        if (!item || typeof item !== "object") continue;
        const field = String(item.field || "").trim();
        if (!field) continue;
        const key = field.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        rows.push(item);
      }}
      return rows;
    }}

    function renderPathLinkList(items) {{
      if (!Array.isArray(items) || !items.length) return "";
      const rows = items
        .map((item) => {{
          const label = String(item.path || "").trim();
          if (!label) return "";
          const href = String(item.href || "").trim();
          const body = href
            ? `<a class="ref-link" href="${{escapeHtml(href)}}" target="_top" rel="noreferrer">${{inlineCodeHtml(label)}}</a>`
            : `<span>${{inlineCodeHtml(label)}}</span>`;
          return `<li>${{body}}</li>`;
        }})
        .filter(Boolean)
        .join("");
      return rows ? `<ul class="detail-list reference-list">${{rows}}</ul>` : "";
    }}

    function renderComponentNarratives(items) {{
      if (!Array.isArray(items) || !items.length) return "";
      const options = arguments.length > 1 && arguments[1] && typeof arguments[1] === "object" ? arguments[1] : {{}};
      const maxItems = Number.isFinite(Number(options.maxItems)) && Number(options.maxItems) > 0
        ? Number(options.maxItems)
        : Number.MAX_SAFE_INTEGER;
      const includeWorkstreams = Boolean(options.includeWorkstreams);
      const visibleItems = items.slice(0, maxItems);
      const rows = visibleItems
        .map((item) => {{
          const componentId = String(item && item.component_id || "").trim();
          if (!componentId) return "";
          const name = String(item && item.name || componentId).trim();
          const registryHref = String(item && item.registry_href || item && item.href || "").trim();
          const specHref = String(item && item.spec_href || "").trim();
          const specRef = String(item && item.spec_ref || "").trim();
          const registryChip = actionChipHtml("Registry", registryHref);
          const specChip = specHref ? actionChipHtml("Spec", specHref) : "";
          const radarChips = includeWorkstreams ? renderActionChips(
            Array.isArray(item && item.workstream_links)
              ? item.workstream_links.map((row) => ({{
                  label: String(row && row.workstream || "").trim(),
                  href: String(row && row.href || "").trim(),
                }}))
              : []
          ) : "";
          return `
            <div class="component-block">
              <div class="component-title-block">
                <p class="component-context-name">${{escapeHtml(name)}}</p>
                <p class="component-subtitle">${{escapeHtml(componentId)}}</p>
              </div>
              <div class="link-group">
                ${{registryChip}}
                ${{specChip}}
                ${{radarChips}}
              </div>
              ${{specRef && !specHref ? `<p class="component-note"><span class="inline-note-label">Spec ref:</span> ${{inlineCodeHtml(specRef)}}</p>` : ""}}
            </div>
          `;
        }})
        .filter(Boolean)
        .join("");
      if (!rows) return "";
      const overflowCount = Math.max(0, items.length - visibleItems.length);
      const overflowNote = overflowCount
        ? `<p class="component-note">${{overflowCount}} more linked component${{overflowCount === 1 ? "" : "s"}} retained in Registry context.</p>`
        : "";
      return `<div class="component-listing">${{rows}}</div>${{overflowNote}}`;
    }}

    function renderComponentLinkList(items) {{
      if (!Array.isArray(items) || !items.length) return "";
      const rows = items
        .map((item) => {{
          const componentId = String(item.component_id || "").trim();
          if (!componentId) return "";
          const name = String(item.name || componentId).trim();
          const href = String(item.href || "").trim();
          const body = href
            ? `<a class="ref-link" href="${{escapeHtml(href)}}" target="_top" rel="noreferrer">${{escapeHtml(name)}}</a>`
            : `<span>${{escapeHtml(name)}}</span>`;
          return `
            <li>
              ${{body}}
              <span class="ref-meta">${{escapeHtml(componentId)}}</span>
            </li>
          `;
        }})
        .filter(Boolean)
        .join("");
      return rows ? `<ul class="detail-list reference-list">${{rows}}</ul>` : "";
    }}

    function renderRelatedBugLinkList(items) {{
      if (!Array.isArray(items) || !items.length) return "";
      const rows = items
        .map((item) => {{
          const bugKey = String(item.bug_key || "").trim();
          if (!bugKey) return "";
          const title = String(item.title || bugKey).trim();
          const href = String(item.href || "").trim();
          const meta = [item.bug_id, item.date, item.severity, item.status]
            .map((value) => String(value || "").trim())
            .filter(Boolean)
            .join(" · ");
          const body = href
            ? `<a class="ref-link" href="${{escapeHtml(href)}}" target="_top" rel="noreferrer">${{escapeHtml(title)}}</a>`
            : `<span>${{escapeHtml(title)}}</span>`;
          return `
            <li>
              ${{body}}
              ${{meta ? `<span class="ref-meta">${{escapeHtml(meta)}}</span>` : ""}}
            </li>
          `;
        }})
        .filter(Boolean)
        .join("");
      return rows ? `<ul class="detail-list reference-list">${{rows}}</ul>` : "";
    }}

    function renderPlainList(items) {{
      if (!Array.isArray(items) || !items.length) return "";
      return `<ul class="detail-list">${{items.map((item) => `<li>${{escapeHtml(String(item || "").trim())}}</li>`).join("")}}</ul>`;
    }}

    function renderLimitedActionRow(label, items, maxItems, overflowLabel) {{
      if (!Array.isArray(items) || !items.length) return "";
      const limit = Number.isFinite(Number(maxItems)) && Number(maxItems) > 0 ? Number(maxItems) : items.length;
      const visibleItems = items.slice(0, limit);
      const chips = renderActionChipGroup(visibleItems);
      if (!chips) return "";
      const overflowCount = Math.max(0, items.length - visibleItems.length);
      const overflowNote = overflowCount
        ? `<p class="component-note">${{overflowCount}} more ${{escapeHtml(String(overflowLabel || "links"))}} retained in source context.</p>`
        : "";
      return `
        <div class="narrative-row">
          <p class="signal-label narrative-label">${{escapeHtml(label)}}</p>
          <div class="detail-copy">${{chips}}${{overflowNote}}</div>
        </div>
      `;
    }}

    function matchesSearch(row, term) {{
      if (!term) return true;
      const canonicalBugId = canonicalizeBugIdToken(term);
      if (canonicalBugId) {{
        return bugExactMatch(row, term);
      }}
      if (bugExactMatch(row, term)) return true;
      const searchText = bugSearchText(row);
      if (searchText.includes(term)) return true;
      const normalizedNeedle = normalizeSearchToken(term);
      if (!normalizedNeedle) return false;
      return normalizeSearchToken(searchText).includes(normalizedNeedle);
    }}

    function matchesFilters(row, state) {{
      if (state.severity && String(row.severity_token || "") !== state.severity) return false;
      if (state.status && String(row.status_token || "") !== state.status) return false;
      return true;
    }}

    function compareText(left, right) {{
      return String(left || "").localeCompare(String(right || ""), undefined, {{ numeric: true, sensitivity: "base" }});
    }}

    function compareDateDesc(left, right) {{
      return compareText(right && right.date, left && left.date);
    }}

    function compareDateAsc(left, right) {{
      return compareText(left && left.date, right && right.date);
    }}

    function bugIdNumber(row) {{
      const canonical = canonicalizeBugIdToken(row && row.bug_id);
      const match = canonical.match(/^CB-(\\d+)$/);
      return match ? Number(match[1]) : 0;
    }}

    function severityRank(row) {{
      const token = String(row && (row.severity_token || row.severity) || "").trim().toLowerCase();
      const match = token.match(/^p(\\d+)$/);
      return match ? Number(match[1]) : 99;
    }}

    function statusRank(row) {{
      const token = normalizeSearchToken(row && (row.status_token || row.status) || "");
      const ranks = {{
        open: 0,
        blocked: 1,
        inprogress: 2,
        resolved: 3,
        closed: 4,
      }};
      return Object.prototype.hasOwnProperty.call(ranks, token) ? ranks[token] : 50;
    }}

    function compareBugIdDesc(left, right) {{
      return bugIdNumber(right) - bugIdNumber(left);
    }}

    function compareBugIdAsc(left, right) {{
      return bugIdNumber(left) - bugIdNumber(right);
    }}

    function compareTitleAsc(left, right) {{
      return compareText(left && left.title, right && right.title);
    }}

    function firstNonZero(...values) {{
      return values.find((value) => Number(value) !== 0) || 0;
    }}

    function sortRows(rows, sortToken) {{
      const token = canonicalizeSortToken(sortToken);
      const sorted = [...rows];
      sorted.sort((left, right) => {{
        if (token === "oldest") {{
          return firstNonZero(compareDateAsc(left, right), compareBugIdAsc(left, right), compareTitleAsc(left, right));
        }}
        if (token === "bug-id") {{
          return firstNonZero(compareBugIdDesc(left, right), compareDateDesc(left, right), compareTitleAsc(left, right));
        }}
        if (token === "priority") {{
          return firstNonZero(
            severityRank(left) - severityRank(right),
            statusRank(left) - statusRank(right),
            compareDateDesc(left, right),
            compareBugIdDesc(left, right),
            compareTitleAsc(left, right)
          );
        }}
        if (token === "status") {{
          return firstNonZero(
            statusRank(left) - statusRank(right),
            compareDateDesc(left, right),
            severityRank(left) - severityRank(right),
            compareBugIdDesc(left, right),
            compareTitleAsc(left, right)
          );
        }}
        return firstNonZero(compareDateDesc(left, right), compareBugIdDesc(left, right), compareTitleAsc(left, right));
      }});
      return sorted;
    }}

    function visibleRows(state, searchTerm) {{
      return sortRows(
        bugSummaries.filter((row) => matchesFilters(row, state) && matchesSearch(row, searchTerm)),
        state.sort
      );
    }}

    function renderKpis() {{
      const counts = DATA.counts || {{}};
      kpiOpenCritical.textContent = String(Number(counts.open_critical || 0));
      kpiOpenTotal.textContent = String(Number(counts.open_total || 0));
      kpiTotalCases.textContent = String(Number(counts.total_cases || 0));
      kpiLatestCase.textContent = String(counts.latest_case_date || "-");
      kpiLatestCase.title = String(counts.latest_case_title || "").trim();
    }}

    function detailCoreRows(row) {{
      const fields = row.fields && typeof row.fields === "object" ? row.fields : {{}};
      return [
        ["Bug ID", row.bug_id || "-"],
        ["Date", row.date || "-"],
        ["Severity", row.severity || "-"],
        ["Status", row.status || "-"],
        ["Fixed", fields["Fixed"] || "-"],
      ].filter(([, value]) => String(value || "").trim() && String(value || "").trim() !== "-");
    }}

    function detailSupportingRows(row) {{
      const fields = row.fields && typeof row.fields === "object" ? row.fields : {{}};
      return [
        ["Type", fields["Type"] || "-"],
        ["Reproducibility", fields["Reproducibility"] || "-"],
      ].filter(([, value]) => String(value || "").trim() && String(value || "").trim() !== "-");
    }}

    function proofResolutionMessage(resolution) {{
      const value = resolution && typeof resolution === "object" ? resolution : {{}};
      const state = String(value.state || "").trim().toLowerCase();
      const laneIds = Array.isArray(value.lane_ids)
        ? value.lane_ids.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      if (state === "ambiguous") {{
        return `Proof state is ambiguous across multiple blocker lanes${{laneIds.length ? `: ${{laneIds.join(", ")}}` : ""}}.`;
      }}
      if (state === "none") {{
        return "No dominant proof lane is resolved for this bug yet.";
      }}
      return "";
    }}

    async function renderDetail(row) {{
      if (!row) {{
        detailRenderToken += 1;
        detailPane.innerHTML = ``;
        return;
      }}
      const renderToken = ++detailRenderToken;
      detailPane.innerHTML = ``;
      const detailKey = String(row.bug_route || row.bug_key || "").trim();
      const loadedDetail = detailKey ? await casebookDataSource.loadDetail(detailKey) : null;
      if (renderToken !== detailRenderToken) {{
        return;
      }}
      const detail = loadedDetail && typeof loadedDetail === "object"
        ? {{ ...row, ...loadedDetail }}
        : row;
      const fields = detail.fields && typeof detail.fields === "object" ? detail.fields : {{}};
      const proofState = detail.proof_state && typeof detail.proof_state === "object" ? detail.proof_state : {{}};
      const proofResolution = detail.proof_state_resolution && typeof detail.proof_state_resolution === "object"
        ? detail.proof_state_resolution
        : {{}};
      const claimGuard = detail.claim_guard && typeof detail.claim_guard === "object" ? detail.claim_guard : {{}};
      const coverage = detail.intelligence_coverage && typeof detail.intelligence_coverage === "object" ? detail.intelligence_coverage : {{}};
      const capturedCount = Number(coverage.captured_count || 0);
      const totalFields = Number(coverage.total_fields || 0);
      const missingFields = Array.isArray(coverage.missing_fields) ? coverage.missing_fields.map((item) => String(item || "").trim()).filter(Boolean) : [];
      const requiredMissingFields = Array.isArray(coverage.required_missing_fields)
        ? coverage.required_missing_fields.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const workstreamLinks = Array.isArray(detail.workstream_links)
        ? detail.workstream_links
            .map((item) => ({{
              label: String(item && item.workstream || "").trim(),
              href: String(item && item.href || "").trim(),
            }}))
            .filter((item) => item.label.trim() && item.href)
        : [];
      const atlasLinks = Array.isArray(detail.diagram_links)
        ? detail.diagram_links
            .map((item) => ({{
              label: String(item && item.diagram_id || "").trim().toUpperCase(),
              href: String(item && item.href || "").trim(),
              tooltip: `${{String(item && item.title || item && item.diagram_id || "").trim()}}. Open Atlas context.`,
            }}))
            .filter((item) => item.label.trim() && item.href)
        : [];
      const relatedBugLinks = Array.isArray(detail.related_bug_links)
        ? detail.related_bug_links
            .map((item) => ({{
              label: String(item && item.bug_id || item && item.title || item && item.bug_key || "").trim(),
              href: String(item && item.href || "").trim(),
            }}))
            .filter((item) => item.label.trim() && item.href)
        : [];
      const detailSectionRows = dedupeByField(Array.isArray(detail.detail_sections) ? detail.detail_sections : []);
      const detailSectionMap = new Map(
        detailSectionRows
          .map((section) => {{
            const field = String(section && section.field || "").trim();
            const value = String(section && section.value || "").trim();
            return [field.toLowerCase(), value];
          }})
          .filter(([field, value]) => field && value)
      );
      function detailFieldValue(fieldName) {{
        const token = String(fieldName || "").trim();
        if (!token) return "";
        const sectionValue = String(detailSectionMap.get(token.toLowerCase()) || "").trim();
        if (sectionValue) return sectionValue;
        return String(fields[token] || "").trim();
      }}
      function renderFocusedFieldRows(fieldNames, formatterMap = {{}}) {{
        const rows = fieldNames
          .map((fieldName) => {{
            const value = detailFieldValue(fieldName);
            if (!value) return "";
            const formatter = typeof formatterMap[fieldName] === "function" ? formatterMap[fieldName] : renderRichText;
            return `
              <div class="narrative-row">
                <p class="signal-label narrative-label">${{escapeHtml(fieldName)}}</p>
                <div class="detail-copy">${{formatter(value)}}</div>
              </div>
            `;
          }})
          .filter(Boolean)
          .join("");
        return rows ? `<div class="narrative-list">${{rows}}</div>` : "";
      }}
      function renderBriefCard(title, note, body) {{
        const cardTitle = String(title || "").trim();
        const cardBody = String(body || "").trim();
        if (!cardTitle || !cardBody) return "";
        const cardNote = String(note || "").trim();
        return `
          <article class="brief-card">
            <div class="brief-card-head">
              <p class="brief-card-title">${{escapeHtml(cardTitle)}}</p>
              ${{cardNote ? `<p class="brief-card-note">${{escapeHtml(cardNote)}}</p>` : ""}}
            </div>
            ${{cardBody}}
          </article>
        `;
      }}
      const chips = [];
      if (detail.severity) {{
        chips.push(`<span class="meta-chip ${{/^p[01]$/i.test(String(detail.severity || "")) ? "critical-chip" : ""}}">${{escapeHtml(detail.severity)}}</span>`);
      }}
      if (detail.status) {{
        chips.push(`<span class="meta-chip ${{String(detail.is_open) === "true" || detail.is_open ? "warn-chip" : ""}}">${{escapeHtml(detail.status)}}</span>`);
      }}
      if (detail.archive_bucket) {{
        chips.push(`<span class="meta-chip archive-chip">Archive: ${{escapeHtml(detail.archive_bucket)}}</span>`);
      }}
      if (totalFields) {{
        chips.push(`<span class="meta-chip ${{requiredMissingFields.length ? "warn-chip" : ""}}">Intel ${{capturedCount}}/${{totalFields}}</span>`);
      }}
      const sourceLink = detail.source_href
        ? actionChipHtml("Source markdown", detail.source_href)
        : `<span class="meta-chip muted">Source markdown missing</span>`;
      const summaryText = String(detail.summary || detailFieldValue("Description") || detailFieldValue("Impact") || "").trim();
      const summary = summaryText ? `<p class="detail-summary">${{escapeHtml(summaryText)}}</p>` : "";
      const summaryFacts = [...detailCoreRows(detail), ...detailSupportingRows(detail)]
        .map(([label, value]) => `
          <div class="summary-fact" data-summary-field="${{escapeHtml(label)}}" role="listitem">
            <p class="summary-fact-label">${{escapeHtml(label)}}</p>
            <p class="summary-fact-value">${{escapeHtml(value)}}</p>
          </div>
        `)
        .join("");
      const deploymentTruth = proofState.deployment_truth && typeof proofState.deployment_truth === "object"
        ? proofState.deployment_truth
        : {{}};
      const deploymentTruthRows = [
        ["Local HEAD", deploymentTruth.local_head],
        ["Pushed HEAD", deploymentTruth.pushed_head],
        ["Published source commit", deploymentTruth.published_source_commit],
        ["Runner fingerprint", deploymentTruth.runner_fingerprint],
        ["Last live failing commit", deploymentTruth.last_live_failing_commit],
      ]
        .filter(([, value]) => {{
          const token = String(value || "").trim();
          return token && token !== "unknown";
        }})
        .map(([label, value]) => ({{
          label,
          value: String(value || "").trim(),
        }}));
      const lastFalsification = proofState.last_falsification && typeof proofState.last_falsification === "object"
        ? proofState.last_falsification
        : {{}};
      const lastFalsificationBits = [
        String(lastFalsification.recorded_at || "").trim(),
        String(lastFalsification.failure_fingerprint || "").trim(),
        String(lastFalsification.frontier_phase || "").trim(),
      ].filter(Boolean);
      const proofRows = [
        proofState.lane_id ? {{ label: "Proof lane", value: String(proofState.lane_id || "").trim() }} : null,
        proofState.current_blocker ? {{ label: "Current blocker", value: String(proofState.current_blocker || "").trim() }} : null,
        proofState.failure_fingerprint ? {{ label: "Failure fingerprint", value: String(proofState.failure_fingerprint || "").trim() }} : null,
        proofState.first_failing_phase ? {{ label: "First failing phase", value: String(proofState.first_failing_phase || "").trim() }} : null,
        proofState.frontier_phase ? {{ label: "Frontier", value: String(proofState.frontier_phase || "").trim() }} : null,
        proofState.clearance_condition ? {{ label: "Clear only when", value: String(proofState.clearance_condition || "").trim() }} : null,
        proofState.proof_status ? {{ label: "Proof status", value: String(proofState.proof_status || "").trim().replace(/_/g, " ") }} : null,
        proofState.evidence_tier ? {{ label: "Evidence tier", value: String(proofState.evidence_tier || "").trim().replace(/_/g, " ") }} : null,
        claimGuard.highest_truthful_claim ? {{ label: "Highest truthful claim", value: String(claimGuard.highest_truthful_claim || "").trim() }} : null,
        lastFalsificationBits.length ? {{ label: "Last falsification", value: lastFalsificationBits.join(" / ") }} : null,
      ].filter(Boolean);
      const allowedNextWork = Array.isArray(proofState.allowed_next_work)
        ? proofState.allowed_next_work.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const deprioritizedWork = Array.isArray(proofState.deprioritized_until_cleared)
        ? proofState.deprioritized_until_cleared.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const proofWarnings = Array.isArray(proofState.warnings)
        ? proofState.warnings.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const proofResolutionText = proofResolutionMessage(proofResolution);
      const proofContextRows = [
        proofState.resolution_state === "inferred"
          ? {{ label: "Resolution source", value: "Inferred from live proof memory because tracked truth did not pin a single lane." }}
          : null,
        allowedNextWork.length ? {{ label: "Allowed next work", value: allowedNextWork.join(" / ") }} : null,
        deprioritizedWork.length ? {{ label: "Deprioritized until cleared", value: deprioritizedWork.join(" / ") }} : null,
      ].filter(Boolean);
      const proofOverview = renderLabeledNarratives(proofRows);
      const proofContext = renderLabeledNarratives(proofContextRows);
      const proofDeployment = renderLabeledNarratives(deploymentTruthRows);
      const proofWarningsHtml = proofWarnings.length
        ? `
          <div class="agent-band-block">
            <p class="agent-band-title">Proof drift warnings</p>
            <div class="detail-copy">${{renderPlainList(proofWarnings)}}</div>
          </div>
        `
        : "";
      const proofSection = (proofResolutionText || proofOverview || proofContext || proofDeployment || proofWarningsHtml)
        ? `
          <article class="detail-section detail-section-proof">
            <h2 class="section-heading">Proof Control Panel</h2>
            <p class="section-lede">Pinned blocker, frontier, and proof tier for this bug lane.</p>
            <div class="agent-band">
              ${{proofResolutionText ? `<div class="agent-band-block"><p class="coverage-note proof-resolution-note">${{escapeHtml(proofResolutionText)}}</p></div>` : ""}}
              ${{proofOverview ? `<div class="agent-band-block"><p class="agent-band-title">Primary blocker lane</p>${{proofOverview}}</div>` : ""}}
              ${{proofContext ? `<div class="agent-band-block"><p class="agent-band-title">Proof discipline</p>${{proofContext}}</div>` : ""}}
              ${{proofDeployment ? `<div class="agent-band-block"><p class="agent-band-title">Deployed vs local truth</p>${{proofDeployment}}</div>` : ""}}
              ${{proofWarningsHtml}}
            </div>
          </article>
        `
        : "";
      const componentNarrative = detail.components && String(detail.components).trim() && String(detail.components).trim() !== "-"
        ? `
          <div class="narrative-row">
            <p class="signal-label narrative-label">Reported components</p>
            <div class="detail-copy">${{renderDelimitedList(detail.components)}}</div>
          </div>
        `
        : "";
      const humanSignalBody = renderFocusedFieldRows(HUMAN_SIGNAL_FIELDS);
      const humanImpactBody = [renderFocusedFieldRows(HUMAN_IMPACT_FIELDS), componentNarrative].filter(Boolean).join("");
      const humanResponseBody = renderFocusedFieldRows(HUMAN_RESPONSE_FIELDS);
      const humanCards = [
        renderBriefCard("Signal", "How the bug showed up.", humanSignalBody),
        renderBriefCard("Impact", "Why the bug mattered.", humanImpactBody),
        renderBriefCard("Response", "What changed or should happen now.", humanResponseBody),
      ].filter(Boolean).join("");
      const humanSection = humanCards
        ? `
          <article class="detail-section detail-section-human" aria-label="Bug brief">
            <div class="brief-stack">${{humanCards}}</div>
          </article>
        `
        : "";
      const intelligenceSection = totalFields && (requiredMissingFields.length || missingFields.length)
        ? `
          <details class="detail-disclosure agent-disclosure">
            <summary class="disclosure-title">Capture Gaps</summary>
            <div class="detail-disclosure-body detail-copy">
              <div class="coverage-strip">
                <span class="meta-chip">${{capturedCount}} of ${{totalFields}} recommended fields captured</span>
                ${{requiredMissingFields.length ? `<span class="meta-chip warn-chip">Missing critical signals: ${{requiredMissingFields.length}}</span>` : ""}}
              </div>
              <p class="coverage-note">Casebook still renders this bug, but the record is missing some of the surrounding context that makes nearby implementation work easier and safer.</p>
              ${{requiredMissingFields.length ? `
                <div class="detail-copy">
                  <p class="signal-label">Missing critical signals</p>
                  ${{renderPlainList(requiredMissingFields)}}
                </div>
              ` : ""}}
              ${{missingFields.length ? `
                <div class="detail-copy">
                  <p class="signal-label">Missing intelligence fields</p>
                  ${{renderPlainList(missingFields)}}
                </div>
              ` : ""}}
            </div>
          </details>
        `
        : "";
      const agentGuidance = detail.agent_guidance && typeof detail.agent_guidance === "object" ? detail.agent_guidance : {{}};
      const agentChecks = Array.isArray(agentGuidance.preflight_checks)
        ? agentGuidance.preflight_checks.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const agentProofLinks = renderPathLinkList(Array.isArray(agentGuidance.proof_links) ? agentGuidance.proof_links : []);
      const guidanceSignals = renderFocusedFieldRows(agentChecks.length ? ["Agent Guardrails"] : ["Agent Guardrails", "Preflight Checks"]);
      const codeRefs = renderPathLinkList(detail.code_ref_links);
      const docRefs = renderPathLinkList(detail.doc_ref_links);
      const testRefs = renderPathLinkList(detail.test_ref_links);
      const contractRefs = renderPathLinkList(detail.contract_ref_links);
      const relatedBugPreview = Array.isArray(detail.related_bug_links) ? detail.related_bug_links.slice(0, 4) : [];
      const relatedBugList = renderRelatedBugLinkList(relatedBugPreview);
      const relatedBugOverflowCount = Array.isArray(detail.related_bug_links)
        ? Math.max(0, detail.related_bug_links.length - relatedBugPreview.length)
        : 0;
      const evidenceRows = [
        codeRefs ? `<div class="narrative-row"><p class="signal-label narrative-label">Code references</p><div class="detail-copy">${{codeRefs}}</div></div>` : "",
        docRefs ? `<div class="narrative-row"><p class="signal-label narrative-label">Runbooks and docs</p><div class="detail-copy">${{docRefs}}</div></div>` : "",
        testRefs ? `<div class="narrative-row"><p class="signal-label narrative-label">Regression tests</p><div class="detail-copy">${{testRefs}}</div></div>` : "",
        contractRefs ? `<div class="narrative-row"><p class="signal-label narrative-label">Contracts and schemas</p><div class="detail-copy">${{contractRefs}}</div></div>` : "",
        relatedBugList
          ? `<div class="narrative-row"><p class="signal-label narrative-label">Related bug records</p><div class="detail-copy">${{relatedBugList}}${{relatedBugOverflowCount ? `<p class="component-note">${{relatedBugOverflowCount}} more related bug record${{relatedBugOverflowCount === 1 ? "" : "s"}} retained in source context.</p>` : ""}}</div></div>`
          : "",
      ].filter(Boolean).join("");
      const relatedContextRows = [
        detail.component_links && Array.isArray(detail.component_links) && detail.component_links.length
          ? `<div class="narrative-row"><p class="signal-label narrative-label">Linked components</p><div class="detail-copy">${{renderComponentNarratives(detail.component_links, {{ maxItems: 3, includeWorkstreams: false }})}}</div></div>`
          : "",
        renderLimitedActionRow("Atlas diagrams", atlasLinks, 4, "Atlas diagram links"),
      ].filter(Boolean).join("");
      const consumedFieldKeys = new Set(
        [...HUMAN_SIGNAL_FIELDS, ...HUMAN_IMPACT_FIELDS, ...HUMAN_RESPONSE_FIELDS, "Description", "Agent Guardrails", "Preflight Checks"]
          .map((fieldName) => String(fieldName || "").trim().toLowerCase())
          .filter(Boolean)
      );
      const remainingDetailRows = detailSectionRows
        .filter((section) => !consumedFieldKeys.has(String(section && section.field || "").trim().toLowerCase()))
        .map((section) => `
          <div class="narrative-row">
            <p class="signal-label narrative-label">${{escapeHtml(section.field || "")}}</p>
            <div class="detail-copy">${{renderRichText(section.value || "")}}</div>
          </div>
        `)
        .join("");
      const remainingDetailSections = remainingDetailRows
        ? `
          <details class="detail-disclosure agent-disclosure">
            <summary class="disclosure-title">Additional Captured Detail</summary>
            <div class="detail-disclosure-body narrative-list">${{remainingDetailRows}}</div>
          </details>
        `
        : "";
      const agentBlocks = [
        guidanceSignals
          ? `<div class="agent-band-block"><p class="agent-band-title">Guardrails</p>${{guidanceSignals}}</div>`
          : "",
        agentChecks.length
          ? `
            <div class="agent-band-block">
              <p class="agent-band-title">Before coding nearby</p>
              <div class="detail-copy agent-checks">
                ${{renderPlainList(agentChecks)}}
              </div>
            </div>
          `
          : "",
        agentProofLinks
          ? `
            <div class="agent-band-block">
              <p class="agent-band-title">Direct proof links</p>
              <div class="detail-copy">${{agentProofLinks}}</div>
            </div>
          `
          : "",
        evidenceRows
          ? `
            <div class="agent-band-block">
              <p class="agent-band-title">Evidence and references</p>
              <div class="narrative-list">${{evidenceRows}}</div>
            </div>
          `
          : "",
        relatedContextRows
          ? `
            <div class="agent-band-block">
              <p class="agent-band-title">Related context</p>
              <div class="narrative-list">${{relatedContextRows}}</div>
            </div>
          `
          : "",
      ].filter(Boolean).join("");
      const agentSection = agentBlocks || remainingDetailSections || intelligenceSection
        ? `
          <article class="detail-section detail-section-agent">
            <h2 class="section-heading">Odylith Agent Learnings</h2>
            <p class="section-lede">Deeper guardrails, evidence, and nearby context for future Odylith-assisted changes.</p>
            ${{agentBlocks ? `<div class="agent-band">${{agentBlocks}}</div>` : ""}}
            ${{remainingDetailSections}}
            ${{intelligenceSection}}
          </article>
        `
        : "";
      const sectionBlocks = [
        humanSection,
        proofSection,
        agentSection,
      ].filter(Boolean).join("");
      detailPane.innerHTML = `
        <section class="detail-head">
          <div class="detail-headline">
            <h1 class="detail-title">${{escapeHtml(detail.title || detail.bug_key || "Bug detail")}}</h1>
          </div>
          ${{summaryFacts ? `<div class="summary-facts" role="list">${{summaryFacts}}</div>` : ""}}
          ${{summary}}
          <div class="detail-meta">${{chips.join("")}}</div>
          <div class="detail-links">
            ${{sourceLink}}
            ${{workstreamLinks.length ? renderActionChipGroup(workstreamLinks) : ""}}
          </div>
        </section>
        <section class="section-stack">
          ${{sectionBlocks}}
        </section>
      `;
    }}

    function renderList(state, rows) {{
      if (!rows.length) {{
        bugList.innerHTML = ``;
        listMeta.textContent = "Visible: 0";
        renderDetail(null);
        return;
      }}
      const selectedRoute = resolveBugRoute(rows, state.bug) || String(rows[0].bug_route || "");
      const selected = rows.find((row) => row.bug_route === selectedRoute) || rows[0];
      bugList.innerHTML = rows.map((row) => {{
        const coverage = row.intelligence_coverage && typeof row.intelligence_coverage === "object" ? row.intelligence_coverage : {{}};
        const capturedCount = Number(coverage.captured_count || 0);
        const totalFields = Number(coverage.total_fields || 0);
        const requiredMissingFields = Array.isArray(coverage.required_missing_fields)
          ? coverage.required_missing_fields.map((item) => String(item || "").trim()).filter(Boolean)
          : [];
        const active = row.bug_route === selectedRoute;
        const chips = [
          row.severity ? `<span class="list-chip ${{/^p[01]$/i.test(String(row.severity || "")) ? "critical-chip" : ""}}">${{escapeHtml(row.severity)}}</span>` : "",
          row.status ? `<span class="list-chip">${{escapeHtml(row.status)}}</span>` : "",
          row.archive_bucket ? `<span class="list-chip archive-chip">${{escapeHtml(row.archive_bucket)}}</span>` : "",
          totalFields ? `<span class="list-chip ${{requiredMissingFields.length ? "warn-chip" : ""}}">Intel ${{capturedCount}}/${{totalFields}}</span>` : "",
        ].filter(Boolean).join("");
        return `
          <button type="button" class="bug-row${{active ? " active" : ""}}" data-bug="${{escapeHtml(row.bug_route || "")}}">
            <div class="bug-row-head">
              <div>
                ${{row.bug_id ? `<p class="bug-row-kicker">${{escapeHtml(row.bug_id)}}</p>` : ""}}
                <p class="bug-row-title">${{escapeHtml(row.title || row.bug_key || "Bug")}}</p>
              </div>
              <span class="bug-row-date">${{escapeHtml(row.date || "-")}}</span>
            </div>
            <p class="bug-row-summary">${{escapeHtml(row.summary || row.components || "No summary available.")}}</p>
            <div class="bug-row-meta">${{chips}}</div>
          </button>
        `;
      }}).join("");
      listMeta.textContent = `Visible: ${{rows.length}}`;
      for (const button of bugList.querySelectorAll(".bug-row")) {{
        button.addEventListener("click", () => {{
          const bug = canonicalizeBugToken(button.getAttribute("data-bug") || "");
          const next = {{ ...readState(), bug }};
          writeState(next);
          render();
        }});
        const bug = canonicalizeBugToken(button.getAttribute("data-bug") || "");
        if (bug) {{
          button.addEventListener("mouseenter", () => {{
            casebookDataSource.prefetch(bug);
          }});
          button.addEventListener("focus", () => {{
            casebookDataSource.prefetch(bug);
          }});
        }}
      }}
      if (selectedRoute !== state.bug) {{
        writeState({{ ...state, bug: selectedRoute }});
      }}
      rows.slice(0, Math.min(6, rows.length)).forEach((row) => {{
        const bug = String(row.bug_route || row.bug_key || "").trim();
        if (bug) {{
          casebookDataSource.prefetch(bug);
        }}
      }});
      void renderDetail(selected);
    }}

    function render() {{
      const state = readState();
      const searchTerm = String(searchInput.value || "").trim().toLowerCase();
      const rows = visibleRows(state, searchTerm);
      renderList(state, rows);
    }}

    fillSelect(
      severityFilter,
      Array.isArray(DATA.filters && DATA.filters.severity_tokens) ? DATA.filters.severity_tokens : [],
      readState().severity,
      "All severities"
    );
    fillSelect(
      statusFilter,
      Array.isArray(DATA.filters && DATA.filters.status_tokens) ? DATA.filters.status_tokens : [],
      readState().status,
      "All statuses"
    );
    fillSortSelect(readState().sort);
    renderKpis();
    searchInput.addEventListener("input", () => render());
    severityFilter.addEventListener("change", () => {{
      const state = readState();
      writeState({{ ...state, severity: canonicalizeFilterToken(severityFilter.value || ""), bug: state.bug }});
      render();
    }});
    statusFilter.addEventListener("change", () => {{
      const state = readState();
      writeState({{ ...state, status: canonicalizeFilterToken(statusFilter.value || ""), bug: state.bug }});
      render();
    }});
    sortFilter.addEventListener("change", () => {{
      const state = readState();
      writeState({{ ...state, sort: canonicalizeSortToken(sortFilter.value || SORT_DEFAULT), bug: state.bug }});
      render();
    }});
    window.addEventListener("popstate", () => {{
      fillSelect(
        severityFilter,
        Array.isArray(DATA.filters && DATA.filters.severity_tokens) ? DATA.filters.severity_tokens : [],
        readState().severity,
        "All severities"
      );
      fillSelect(
        statusFilter,
        Array.isArray(DATA.filters && DATA.filters.status_tokens) ? DATA.filters.status_tokens : [],
        readState().status,
        "All statuses"
      );
      fillSortSelect(readState().sort);
      render();
    }});
    render();
    __CASEBOOK_QUICK_TOOLTIP_RUNTIME__
  </script>
</body>
</html>
""".replace("__ODYLITH_BRAND_HEAD__", str(payload.get("brand_head_html", "")).strip()).replace("__CASEBOOK_PAGE_BODY__", page_body_css).replace("__CASEBOOK_SURFACE_SHELL_ROOT__", surface_shell_root_css).replace("__CASEBOOK_SURFACE_SHELL__", surface_shell_css).replace("__CASEBOOK_HERO_PANEL__", hero_panel_css).replace("__CASEBOOK_HEADER_TYPOGRAPHY__", header_typography_css).replace("__CASEBOOK_KPI_GRID__", kpi_grid_css).replace("__CASEBOOK_KPI_CARD__", kpi_card_surface_css).replace("__CASEBOOK_KPI_TYPOGRAPHY__", kpi_typography_css).replace("__CASEBOOK_FILTER_SHELL__", sticky_filter_shell_css).replace("__CASEBOOK_FILTER_BAR__", sticky_filter_bar_css).replace("__CASEBOOK_CONTROL_LABEL__", control_label_css).replace("__CASEBOOK_WORKSPACE__", workspace_layout_css).replace("__CASEBOOK_PANEL_SURFACE__", panel_surface_css).replace("__CASEBOOK_ROW_SURFACE__", row_surface_css).replace("__CASEBOOK_EMPTY_STATE_SURFACE__", narrative_section_surface_css).replace("__CASEBOOK_LABEL_SURFACE__", label_surface_css).replace("__CASEBOOK_LABEL_TYPOGRAPHY__", label_typography_css).replace("__CASEBOOK_LABEL_TONES__", label_tone_css).replace("__CASEBOOK_ACTION_CHIP__", detail_action_chip_css).replace("__CASEBOOK_SECTION_HEADING__", section_heading_css).replace("__CASEBOOK_SECONDARY_HEADINGS__", secondary_heading_css).replace("__CASEBOOK_COMPACT_FACT_TYPOGRAPHY__", compact_fact_css).replace("__CASEBOOK_INLINE_ROW_TYPOGRAPHY__", inline_row_css).replace("__CASEBOOK_CARD_TITLE__", card_title_css).replace("__CASEBOOK_COPY__", copy_css).replace("__CASEBOOK_TOOLTIP_SURFACE__", tooltip_surface_css).replace("__CASEBOOK_QUICK_TOOLTIP_RUNTIME__", tooltip_runtime_js).replace("__CASEBOOK_CODE_TYPOGRAPHY__", code_typography_css).replace("__CASEBOOK_IDENTIFIER_TYPOGRAPHY__", identifier_typography_css)
    return html


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).resolve()
    output_path = surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=str(args.output))
    validation = casebook_source_validation.validate_casebook_sources(repo_root=repo_root)
    if not validation.passed:
        casebook_source_validation.print_casebook_source_validation_report(validation)
        return 2
    skip_rebuild, input_fingerprint, cached_metadata, bundle_paths, _output_paths = (
        generated_surface_refresh_guards.should_skip_surface_rebuild(
            repo_root=repo_root,
            output_path=output_path,
            asset_prefix="casebook",
            key=_CASEBOOK_REFRESH_GUARD_KEY,
            watched_paths=_refresh_guard_watched_paths(),
            live_globs=("casebook-detail-shard-*.v1.js",),
            extra={"runtime_mode": str(args.runtime_mode).strip().lower() or "auto"},
        )
    )
    if skip_rebuild:
        counts = dict(cached_metadata.get("counts", {})) if isinstance(cached_metadata, Mapping) else {}
        print("casebook dashboard render passed")
        print(f"- output: {output_path}")
        print(f"- total_cases: {int(counts.get('total_cases', 0) or 0)}")
        print(f"- open_total: {int(counts.get('open_total', 0) or 0)}")
        return 0
    payload = _build_payload(
        repo_root=repo_root,
        output_path=output_path,
        runtime_mode=str(args.runtime_mode),
    )
    payload["brand_head_html"] = brand_assets.render_brand_head_html(repo_root=repo_root, output_path=output_path)
    payload["generated_utc"] = stable_generated_utc.resolve_for_js_assignment_file(
        output_path=bundle_paths.payload_js_path,
        global_name="__ODYLITH_CASEBOOK_DATA__",
        payload=payload,
    )
    payload["generated_local_date"] = dashboard_time.pacific_display_date_from_utc_token(
        payload["generated_utc"],
        default="-",
    )
    bug_rows = [
        row
        for row in payload.get("bugs", [])
        if isinstance(row, dict)
    ]
    detail_rows = {
        str(row.get("bug_route", "")).strip(): _build_casebook_detail_row(row)
        for row in bug_rows
        if str(row.get("bug_route", "")).strip()
    }
    detail_manifest, detail_shards = _chunk_casebook_items(
        items=detail_rows,
        shard_size=_CASEBOOK_DETAIL_SHARD_SIZE,
        file_stem_prefix="casebook-detail-shard",
    )
    payload["bugs"] = [_build_casebook_summary_row(row) for row in bug_rows]
    payload["detail_manifest"] = detail_manifest
    payload["data_source"] = {
        "preferred_backend": "staticSnapshot",
        "available_backends": ["staticSnapshot"],
        "runtime_base_url": "",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bundled_html, payload_js, control_js = dashboard_surface_bundle.externalize_surface_bundle(
        html_text=_render_html(payload=payload),
        payload=payload,
        paths=bundle_paths,
        spec=dashboard_surface_bundle.standard_surface_bundle_spec(
            asset_prefix="casebook",
            payload_global_name="__ODYLITH_CASEBOOK_DATA__",
            embedded_json_script_id="casebookData",
            bootstrap_binding_name="DATA",
            allow_missing_embedded_json=True,
            shell_tab="casebook",
            shell_frame_id="frame-casebook",
            query_passthrough=(
                ("bug", ("bug",)),
                ("severity", ("severity",)),
                ("status", ("status",)),
                ("sort", ("sort",)),
            ),
        ),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=output_path,
        content=bundled_html,
        lock_key=str(output_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=bundle_paths.payload_js_path,
        content=payload_js,
        lock_key=str(bundle_paths.payload_js_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=bundle_paths.control_js_path,
        content=control_js,
        lock_key=str(bundle_paths.control_js_path),
    )
    active_detail_paths: set[Path] = set()
    for filename, shard_payload in detail_shards:
        shard_path = output_path.parent / filename
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=shard_path,
            content=dashboard_surface_bundle.render_payload_merge_js(
                global_name="__ODYLITH_CASEBOOK_DETAIL_SHARDS__",
                payload=shard_payload,
            ),
            lock_key=str(shard_path),
        )
        active_detail_paths.add(shard_path.resolve())
    for stale_path in output_path.parent.glob("casebook-detail-shard-*.v1.js"):
        if stale_path.resolve() in active_detail_paths:
            continue
        if stale_path.is_file():
            stale_path.unlink()
    source_bundle_mirror.sync_live_paths(
        repo_root=repo_root,
        live_paths=(output_path, bundle_paths.payload_js_path, bundle_paths.control_js_path),
    )
    source_bundle_mirror.sync_live_glob(
        repo_root=repo_root,
        live_dir=output_path.parent,
        pattern="casebook-detail-shard-*.v1.js",
    )
    counts = payload.get("counts", {}) if isinstance(payload, dict) else {}
    if input_fingerprint:
        _bundle_paths, current_output_paths = generated_surface_refresh_guards.surface_output_paths(
            repo_root=repo_root,
            output_path=output_path,
            asset_prefix="casebook",
            live_globs=("casebook-detail-shard-*.v1.js",),
        )
        generated_surface_refresh_guards.record_surface_rebuild(
            repo_root=repo_root,
            key=_CASEBOOK_REFRESH_GUARD_KEY,
            input_fingerprint=input_fingerprint,
            output_paths=current_output_paths,
            metadata={
                "counts": {
                    "total_cases": int(counts.get("total_cases", 0) or 0),
                    "open_total": int(counts.get("open_total", 0) or 0),
                }
            },
        )
    print("casebook dashboard render passed")
    print(f"- output: {output_path}")
    print(f"- total_cases: {int(counts.get('total_cases', 0) or 0)}")
    print(f"- open_total: {int(counts.get('open_total', 0) or 0)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Render a local UX view for the backlog.

Source of truth remains markdown:
- odylith/radar/source/INDEX.md
- odylith/radar/source/ideas/YYYY-MM/*.md

This renderer produces a deterministic, read-only HTML view.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.surfaces import brand_assets
from odylith.runtime.surfaces import dashboard_time
from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import dashboard_ui_runtime_primitives
from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.surfaces import backlog_detail_pages
from odylith.runtime.surfaces import execution_wave_ui_runtime_primitives
from odylith.runtime.surfaces import generated_surface_refresh_guards
from odylith.runtime.surfaces import render_backlog_ui_payload_runtime
from odylith.runtime.surfaces import render_backlog_ui_html_runtime
from odylith.runtime.surfaces import source_bundle_mirror
from odylith.runtime.governance import execution_wave_view_model
from odylith.runtime.surfaces import generated_surface_cleanup
from odylith.runtime.governance import plan_progress
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.governance import traceability_ui_lookup
from odylith.runtime.governance import validate_backlog_contract as contract
from odylith.runtime.governance import workstream_inference

_EXECUTION_SECTION_TITLES: tuple[str, ...] = (
    "In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)",
    "In Planning/Implementation (Linked to `odylith/technical-plans/in-progress` or an active parent wave)",
    "Promoted (In `odylith/technical-plans/in-progress`)",
)
_PARKED_SECTION_TITLE = contract._PARKED_SECTION_TITLE
_FINISHED_SECTION_TITLE = "Finished (Linked to `odylith/technical-plans/done`)"
_DATE_TOKEN_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PLAN_UPDATED_RE = re.compile(r"(?im)^Updated:\s*(\d{4}-\d{2}-\d{2})\s*$")
_PLAN_CREATED_RE = re.compile(r"(?im)^Created:\s*(\d{4}-\d{2}-\d{2})\s*$")
_PLAN_FILENAME_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_CHECKBOX_LINE_RE = re.compile(r"^\[(?P<mark>[xX ])\]\s+(?P<body>.+)$")
_TRACEABILITY_SECTION_NAME = "Traceability"
_TRACEABILITY_BUCKETS: tuple[str, ...] = (
    "Runbooks",
    "Developer Docs",
    "Code References",
)
_TRACEABILITY_PATH_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
_TRACEABILITY_PATH_CODE_RE = re.compile(r"`([^`\n]+)`")
_TRACEABILITY_CHECKBOX_PREFIX_RE = re.compile(r"^\[(?:x|X| )\]\s*")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_SCRIPT_DIR = "scr" + "ipts"
_TESTS_DIR = "te" + "sts"
_RAW_REPO_ROOT_PATTERN = "|".join(("docs", _SCRIPT_DIR, _TESTS_DIR, "contracts", "plan", "odylith"))
_RAW_REPO_TOKEN_RE = re.compile(
    rf"(?P<token>(?:\./)?(?:{_RAW_REPO_ROOT_PATTERN})/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*(?:/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)*)"
)
_RAW_LEGACY_TEST_COMMAND_RE = re.compile(
    rf"pytest(?:\s+-q)?\s+{_TESTS_DIR}/{_SCRIPT_DIR}/test_(?P<module>[a-z0-9_]+)\.py"
)
_IDEA_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_DEFAULT_ACTIVE_WINDOW_MINUTES = 15
_COMPASS_RUNTIME_PATH = "odylith/compass/runtime/current.v1.json"
_BACKLOG_DETAIL_SHARD_SIZE = 48
_BACKLOG_DOCUMENT_SHARD_SIZE = 32
_BACKLOG_SUMMARY_HEAVY_FIELDS = frozenset(
    {
        "problem",
        "customer",
        "opportunity",
        "founder_pov",
        "success_metrics",
        "impacted_parts",
        "idea_file",
        "idea_href",
        "idea_ui_file",
        "idea_ui_href",
        "promoted_to_plan",
        "promoted_to_plan_file",
        "promoted_to_plan_href",
        "promoted_to_plan_ui_file",
        "promoted_to_plan_ui_href",
        "registry_components",
    }
)
_TRACEABILITY_INDEX_EDGE_TYPES = frozenset(
    {
        "parent_child",
        "depends_on",
        "blocks",
        "reopens",
        "split",
        "merged",
    }
)
_LEGACY_COMMAND_PREFIX_ALIASES: tuple[tuple[str, str], ...] = (
    ("python -m " + "scr" + "ipts.sync_workstream_artifacts", "odylith sync"),
    ("python -m " + "scr" + "ipts.sync_component_spec_requirements", "odylith governance sync-component-spec-requirements"),
    ("python -m " + "scr" + "ipts.validate_backlog_contract", "odylith validate backlog-contract"),
    ("python -m " + "scr" + "ipts.validate_component_registry_contract", "odylith validate component-registry"),
    ("python -m " + "scr" + "ipts.validate_plan_risk_mitigation_contract", "odylith validate plan-risk-mitigation"),
    ("python -m " + "scr" + "ipts.validate_plan_traceability_contract", "odylith validate plan-traceability"),
    ("python -m " + "scr" + "ipts.validate_plan_workstream_binding", "odylith validate plan-workstream-binding"),
    ("python -m " + "scr" + "ipts.odylith_context_engine", "odylith context-engine"),
    ("python -m " + "scr" + "ipts.subagent_router", "odylith subagent-router"),
    ("python -m " + "scr" + "ipts.subagent_orchestrator", "odylith subagent-orchestrator"),
    ("python -m " + "scr" + "ipts.update_compass", "odylith compass update"),
    ("python -m " + "scr" + "ipts.log_compass_timeline_event", "odylith compass log"),
    ("python -m " + "scr" + "ipts.watch_prompt_transactions", "odylith compass watch-transactions"),
    ("python -m " + "scr" + "ipts.render_mermaid_catalog", "odylith atlas render"),
    (
        "python -m " + "scr" + "ipts.run_clean_snapshot_strict_sync",
        "odylith sync --check-only --check-clean --runtime-mode standalone",
    ),
)
_BACKLOG_REFRESH_GUARD_KEY = "backlog-dashboard-render"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render odylith/radar/radar.html from backlog markdown")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--index", default="odylith/radar/source/INDEX.md", help="Backlog index markdown path")
    parser.add_argument("--output", default="odylith/radar/radar.html", help="Rendered HTML output path")
    parser.add_argument(
        "--standalone-pages",
        default="odylith/radar/standalone-pages.v1.js",
        help="Generated JS map containing Radar spec/plan standalone page routes.",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local runtime projection store when available for fast local rendering.",
    )
    return parser.parse_args(argv)


def _resolve_path(*, repo_root: Path, value: str) -> Path:
    token = str(value or "").strip()
    path = Path(token)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _refresh_guard_watched_paths(*, index_path: Path) -> tuple[Path | str, ...]:
    return (
        index_path,
        "odylith/radar/source/ideas",
        "odylith/technical-plans",
        "odylith/registry/source",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        _COMPASS_RUNTIME_PATH,
        *agent_runtime_contract.candidate_stream_tokens(),
        "src/odylith/runtime/common",
        "src/odylith/runtime/context_engine",
        "src/odylith/runtime/governance",
        "src/odylith/runtime/surfaces",
    )


def _as_relative_href(*, output_path: Path, target: Path) -> str:
    try:
        rel = target.relative_to(output_path.parent)
    except ValueError:
        rel = Path(target)
    return rel.as_posix()


def _as_portable_relative_href(*, output_path: Path, target: Path) -> str:
    try:
        rel = os.path.relpath(str(target), start=str(output_path.parent))
        return Path(rel).as_posix()
    except ValueError:
        return str(target)


def _slug_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return token or "idea"


def _radar_route_href(
    *,
    source_output_path: Path,
    target_output_path: Path,
    workstream_id: str,
    view: str | None = None,
) -> str:
    base_href = _as_portable_relative_href(output_path=source_output_path, target=target_output_path)
    workstream = str(workstream_id or "").strip()
    if not workstream:
        return base_href
    query_bits = [f"workstream={quote(workstream, safe='')}"]
    if view:
        query_bits.insert(0, f"view={quote(str(view).strip(), safe='')}")
    return f"{base_href}?{'&'.join(query_bits)}"


def _extract_sections_with_body(path: Path) -> list[tuple[str, list[str]]]:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, current_lines))
            current_title = line[3:].strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, current_lines))
    return sections


def _rewrite_legacy_inline_command(text: str) -> str:
    command = str(text or "")
    for legacy_prefix, replacement in _LEGACY_COMMAND_PREFIX_ALIASES:
        if legacy_prefix in command:
            command = command.replace(legacy_prefix, replacement)
    return command


def _legacy_test_command(module_name: str) -> str:
    module = str(module_name or "").strip()
    if not module:
        return ""
    specific: dict[str, str] = {
        "render_backlog_ui": "odylith sync --repo-root . --check-only --runtime-mode standalone",
        "validate_backlog_contract": "odylith validate backlog-contract --repo-root .",
        "build_traceability_graph": "odylith validate plan-traceability --repo-root .",
        "backfill_workstream_traceability": "odylith validate plan-traceability --repo-root .",
        "reconcile_plan_workstream_binding": "odylith validate plan-workstream-binding --repo-root .",
        "normalize_plan_risk_mitigation": "odylith validate plan-risk-mitigation --repo-root .",
        "validate_plan_risk_mitigation_contract": "odylith validate plan-risk-mitigation --repo-root .",
        "validate_plan_traceability_contract": "odylith validate plan-traceability --repo-root .",
        "validate_plan_workstream_binding": "odylith validate plan-workstream-binding --repo-root .",
        "component_registry_intelligence": "odylith validate component-registry --repo-root .",
        "sync_component_spec_requirements": "odylith governance sync-component-spec-requirements --repo-root .",
        "validate_component_registry_contract": "odylith validate component-registry --repo-root .",
        "render_registry_dashboard": "odylith sync --repo-root . --check-only --runtime-mode standalone",
        "render_mermaid_catalog": "odylith atlas render --repo-root .",
        "auto_update_mermaid_diagrams": "odylith atlas render --repo-root .",
        "install_mermaid_autosync_hook": "odylith atlas render --repo-root .",
        "scaffold_mermaid_diagram": "odylith atlas render --repo-root .",
        "render_compass_dashboard": "odylith compass refresh --repo-root . --wait",
        "compass_refresh_runtime": "odylith compass refresh --repo-root . --wait",
        "compass_dashboard_base": "odylith compass refresh --repo-root . --wait",
        "compass_dashboard_runtime": "odylith compass refresh --repo-root . --wait",
        "compass_dashboard_shell": "odylith compass refresh --repo-root . --wait",
        "compass_standup_brief_narrator": "odylith compass refresh --repo-root . --wait",
        "log_compass_timeline_event": "odylith compass log --repo-root . --help",
        "watch_prompt_transactions": "odylith compass watch-transactions --repo-root . --once --runtime-mode standalone",
        "odylith_context_engine": "odylith context-engine --repo-root . status",
        "odylith_context_engine_store": "odylith context-engine --repo-root . status",
        "odylith_context_cache": "odylith context-engine --repo-root . status",
        "odylith_memory_backend": "odylith context-engine --repo-root . status",
        "odylith_projection_bundle": "odylith context-engine --repo-root . status",
        "odylith_projection_snapshot": "odylith context-engine --repo-root . status",
        "odylith_remote_retrieval": "odylith context-engine --repo-root . status",
        "tooling_context_budgeting": "odylith context-engine --repo-root . status",
        "tooling_context_packet_builder": "odylith context-engine --repo-root . status",
        "tooling_context_quality": "odylith context-engine --repo-root . status",
        "tooling_context_retrieval": "odylith context-engine --repo-root . status",
        "tooling_context_routing": "odylith context-engine --repo-root . status",
        "tooling_memory_contracts": "odylith context-engine --repo-root . status",
        "subagent_router": "odylith subagent-router --help",
        "subagent_orchestrator": "odylith subagent-orchestrator --help",
        "sync_workstream_artifacts": "odylith sync --repo-root . --check-only --runtime-mode standalone",
        "update_compass": "odylith compass update --repo-root .",
    }
    return specific.get(module, "odylith sync --repo-root . --check-only --runtime-mode standalone")


def _rewrite_plain_text_tokens(*, repo_root: Path, text: str) -> str:
    rewritten = _rewrite_legacy_inline_command(text)

    def _replace_pytest(match: re.Match[str]) -> str:
        replacement = _legacy_test_command(str(match.group("module") or "").strip())
        return replacement or match.group(0)

    rewritten = _RAW_LEGACY_TEST_COMMAND_RE.sub(_replace_pytest, rewritten)

    def _replace_token(match: re.Match[str]) -> str:
        token = str(match.group("token") or "")
        normalized = _normalize_inline_repo_token(repo_root=repo_root, token=token)
        return normalized or token

    return _RAW_REPO_TOKEN_RE.sub(_replace_token, rewritten)


def _normalize_inline_repo_token(*, repo_root: Path, token: str) -> str:
    return render_backlog_ui_html_runtime._normalize_inline_repo_token(
        repo_root=repo_root,
        token=token,
    )


def _rewrite_section_text(*, repo_root: Path, text: str) -> str:
    def _replace_code(match: re.Match[str]) -> str:
        body = str(match.group(1) or "")
        rewritten = _rewrite_plain_text_tokens(repo_root=repo_root, text=body)
        return f"`{rewritten}`" if rewritten != body else match.group(0)

    def _replace_link(match: re.Match[str]) -> str:
        label = str(match.group(1) or "")
        target = str(match.group(2) or "")
        normalized = _normalize_inline_repo_token(repo_root=repo_root, token=target)
        if normalized:
            return f"[{label}]({normalized})"
        return match.group(0)

    rewritten = _INLINE_LINK_RE.sub(_replace_link, str(text or ""))
    rewritten = _INLINE_CODE_RE.sub(_replace_code, rewritten)
    return _rewrite_plain_text_tokens(repo_root=repo_root, text=rewritten)


def _render_section_body(*, repo_root: Path, lines: list[str]) -> str:
    return render_backlog_ui_html_runtime._render_section_body(
        repo_root=repo_root,
        lines=lines,
    )


def _extract_traceability_path_tokens(text: str) -> list[str]:
    return render_backlog_ui_html_runtime._extract_traceability_path_tokens(text)


def _normalize_traceability_path(*, repo_root: Path, token: str) -> str:
    return render_backlog_ui_html_runtime._normalize_traceability_path(
        repo_root=repo_root,
        token=token,
    )


def _collect_plan_traceability_paths(
    *,
    repo_root: Path,
    sections: list[tuple[str, list[str]]],
) -> dict[str, list[str]]:
    return render_backlog_ui_html_runtime._collect_plan_traceability_paths(
        repo_root=repo_root,
        sections=sections,
    )


def _as_repo_path(*, repo_root: Path, target: Path) -> str:
    try:
        rel = target.relative_to(repo_root)
        return rel.as_posix()
    except ValueError:
        return str(target)


def _extract_sections_from_markdown(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        sections[current].append(line)

    normalized: dict[str, str] = {}
    for key, raw_lines in sections.items():
        merged = " ".join(token.strip() for token in raw_lines if token.strip())
        normalized[key] = merged.strip()
    return normalized


def _split_metadata_ids(*, value: str, pattern: re.Pattern[str]) -> list[str]:
    values: list[str] = []
    for raw in str(value or "").replace(";", ",").split(","):
        token = raw.strip()
        if not token:
            continue
        if not pattern.fullmatch(token):
            continue
        values.append(token)
    return sorted(set(values))


def _extract_plan_dates(plan_path: Path) -> tuple[str, str, str]:
    """Return `(created_date, updated_date, filename_date)` from plan metadata."""

    filename_date = ""
    filename_match = _PLAN_FILENAME_DATE_RE.search(plan_path.name)
    if filename_match is not None:
        token = str(filename_match.group(1)).strip()
        if _DATE_TOKEN_RE.fullmatch(token):
            filename_date = token

    if not plan_path.is_file():
        return "", "", filename_date

    content = plan_path.read_text(encoding="utf-8")
    created = ""
    created_match = _PLAN_CREATED_RE.search(content)
    if created_match is not None:
        token = str(created_match.group(1)).strip()
        if _DATE_TOKEN_RE.fullmatch(token):
            created = token

    updated_match = _PLAN_UPDATED_RE.search(content)
    if updated_match is not None:
        updated = str(updated_match.group(1)).strip()
        if _DATE_TOKEN_RE.fullmatch(updated):
            return created, updated, filename_date

    return created, "", filename_date


def _parse_iso_datetime(value: object) -> dt.datetime | None:
    return render_backlog_ui_payload_runtime._parse_iso_datetime(value)


def _load_compass_transactions(
    *,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], int]:
    return render_backlog_ui_payload_runtime._load_compass_transactions(repo_root=repo_root)


def _is_active_transaction(
    *,
    transaction: Mapping[str, Any],
    now_utc: dt.datetime,
    active_window_minutes: int,
) -> bool:
    return render_backlog_ui_payload_runtime._is_active_transaction(
        transaction=transaction,
        now_utc=now_utc,
        active_window_minutes=active_window_minutes,
    )


def _execution_overlay_for_status(
    *,
    status: str,
    has_active_transaction: bool,
) -> str:
    return render_backlog_ui_payload_runtime._execution_overlay_for_status(
        status=status,
        has_active_transaction=has_active_transaction,
    )


def _attach_execution_overlay(
    *,
    entries: list[dict[str, object]],
    repo_root: Path,
) -> None:
    render_backlog_ui_payload_runtime._attach_execution_overlay(
        entries=entries,
        repo_root=repo_root,
    )


def _component_catalog_rows(
    *,
    component_index: Mapping[str, component_registry.ComponentEntry],
) -> list[dict[str, str]]:
    return render_backlog_ui_payload_runtime._component_catalog_rows(component_index=component_index)


def _atlas_diagram_catalog_rows(*, repo_root: Path) -> list[dict[str, object]]:
    return render_backlog_ui_payload_runtime._atlas_diagram_catalog_rows(repo_root=repo_root)


def _load_component_index(
    *,
    repo_root: Path,
) -> Mapping[str, component_registry.ComponentEntry]:
    return render_backlog_ui_payload_runtime._load_component_index(repo_root=repo_root)


def _attach_component_registry_links(
    *,
    entries: list[dict[str, object]],
    component_index: Mapping[str, component_registry.ComponentEntry],
) -> None:
    render_backlog_ui_payload_runtime._attach_component_registry_links(
        entries=entries,
        component_index=component_index,
    )


def _parse_section_rows(
    *,
    index_content: str,
    section_title: str,
    expected_headers: tuple[str, ...],
    errors: list[str],
    index_path: Path,
) -> list[dict[str, str]]:
    return render_backlog_ui_payload_runtime._parse_section_rows(
        index_content=index_content,
        section_title=section_title,
        expected_headers=expected_headers,
        errors=errors,
        index_path=index_path,
    )


def _parse_optional_section_rows(
    *,
    index_content: str,
    section_title: str,
    expected_headers: tuple[str, ...],
    errors: list[str],
    index_path: Path,
) -> list[dict[str, str]]:
    return render_backlog_ui_payload_runtime._parse_optional_section_rows(
        index_content=index_content,
        section_title=section_title,
        expected_headers=expected_headers,
        errors=errors,
        index_path=index_path,
    )


def _build_entry(
    *,
    repo_root: Path,
    output_path: Path,
    payload: dict[str, str],
    section: str,
    rationale_map: dict[str, list[str]],
    errors: list[str],
) -> dict[str, object] | None:
    return render_backlog_ui_payload_runtime._build_entry(
        repo_root=repo_root,
        output_path=output_path,
        payload=payload,
        section=section,
        rationale_map=rationale_map,
        errors=errors,
    )


def _render_idea_spec_html(
    *,
    repo_root: Path,
    index_output_path: Path,
    entry: dict[str, object],
    destination_output_path: Path | None = None,
) -> str:
    return backlog_detail_pages._render_idea_spec_html(
        repo_root=repo_root,
        index_output_path=index_output_path,
        entry=entry,
        destination_output_path=destination_output_path,
    )


def _extract_plan_metadata(path: Path) -> dict[str, str]:
    return backlog_detail_pages._extract_plan_metadata(path)


def _render_plan_html(
    *,
    repo_root: Path,
    index_output_path: Path,
    entry: dict[str, object],
    destination_output_path: Path | None = None,
) -> str:
    return backlog_detail_pages._render_plan_html(
        repo_root=repo_root,
        index_output_path=index_output_path,
        entry=entry,
        destination_output_path=destination_output_path,
    )


def _render_standalone_pages_js(
    *,
    repo_root: Path,
    index_output_path: Path,
    entries: Sequence[dict[str, object]],
) -> str:
    """Render a single JS payload that maps Radar single-page routes to full HTML docs.

    Radar's operator UI is already a single-page surface. The legacy generator wrote one
    standalone HTML mirror per workstream spec and per linked plan, which bloated the
    generated artifact tree and created a misleading topology. This sidecar JS bundle keeps
    those route targets available through the same single HTML entrypoint without changing
    their standalone layouts.
    """

    pages: dict[str, str] = {}
    for entry in entries:
        idea_id = str(entry.get("idea_id", "")).strip()
        if not idea_id:
            continue
        pages[f"spec:{idea_id}"] = _render_idea_spec_html(
            repo_root=repo_root,
            index_output_path=index_output_path,
            entry=entry,
            destination_output_path=index_output_path,
        )
        if str(entry.get("promoted_to_plan_file", "")).strip():
            pages[f"plan:{idea_id}"] = _render_plan_html(
                repo_root=repo_root,
                index_output_path=index_output_path,
                entry=entry,
                destination_output_path=index_output_path,
            )
    data_blob = json.dumps(pages, ensure_ascii=True, separators=(",", ":"))
    return (
        "window.__ODYLITH_BACKLOG_STANDALONE_PAGES__ = "
        f"{data_blob};\n"
    )


def _backlog_summary_search_text(entry: Mapping[str, object]) -> str:
    return render_backlog_ui_payload_runtime._backlog_summary_search_text(entry)


def _build_backlog_summary_entry(entry: Mapping[str, object]) -> dict[str, object]:
    return render_backlog_ui_payload_runtime._build_backlog_summary_entry(entry)


def _build_backlog_detail_entry(entry: Mapping[str, object]) -> dict[str, object]:
    return render_backlog_ui_payload_runtime._build_backlog_detail_entry(entry)


def _build_traceability_client_payload(traceability_graph: Mapping[str, object]) -> dict[str, object]:
    return render_backlog_ui_payload_runtime._build_traceability_client_payload(traceability_graph)


def _chunk_backlog_items(
    *,
    items: Mapping[str, object],
    shard_size: int,
    file_stem_prefix: str,
) -> tuple[dict[str, str], list[tuple[str, dict[str, object]]]]:
    manifest: dict[str, str] = {}
    shards: list[tuple[str, dict[str, object]]] = []
    ordered_items = sorted(
        ((str(key).strip(), value) for key, value in items.items() if str(key).strip()),
        key=lambda item: item[0],
    )
    for index in range(0, len(ordered_items), shard_size):
        shard_items = ordered_items[index : index + shard_size]
        filename = f"{file_stem_prefix}-{(index // shard_size) + 1:03d}.v1.js"
        payload: dict[str, object] = {}
        for key, value in shard_items:
            manifest[key] = filename
            payload[key] = value
        shards.append((filename, payload))
    return manifest, shards


def _render_html(*, payload: dict[str, object]) -> str:
    return render_backlog_ui_html_runtime._render_html(payload=payload)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    index_path = _resolve_path(repo_root=repo_root, value=args.index)
    output_path = _resolve_path(repo_root=repo_root, value=args.output)
    standalone_pages_path = _resolve_path(repo_root=repo_root, value=args.standalone_pages)
    skip_rebuild, input_fingerprint, cached_metadata, bundle_paths, _output_paths = (
        generated_surface_refresh_guards.should_skip_surface_rebuild(
            repo_root=repo_root,
            output_path=output_path,
            asset_prefix="backlog",
            key=_BACKLOG_REFRESH_GUARD_KEY,
            watched_paths=_refresh_guard_watched_paths(index_path=index_path),
            extra_live_paths=(standalone_pages_path,),
            live_globs=("backlog-detail-shard-*.v1.js", "backlog-document-shard-*.v1.js"),
            extra={"runtime_mode": str(args.runtime_mode).strip().lower() or "auto"},
        )
    )
    if skip_rebuild:
        print("backlog ui render passed")
        print(f"- output: {output_path}")
        print(f"- standalone_pages: {standalone_pages_path}")
        print(f"- ideas: {int(cached_metadata.get('idea_count', 0) or 0)}")
        return 0

    errors: list[str] = []
    if not index_path.is_file():
        print(f"missing backlog index: {index_path}")
        return 2

    snapshot = contract.load_backlog_index_snapshot(index_path)
    index_updated = str(snapshot.get("updated_utc", "")).strip()
    if not index_updated:
        errors.append(f"{index_path}: missing `Last updated (UTC): YYYY-MM-DD` stamp")
    active_rows = contract.rows_as_mapping(
        section=snapshot.get("active", {}),
        expected_headers=contract._INDEX_COLS,
    )
    if not active_rows:
        active_error = str((snapshot.get("active", {}) or {}).get("error", "")).strip()
        if active_error:
            errors.append(f"{index_path}: {active_error}")
        elif tuple((snapshot.get("active", {}) or {}).get("headers", [])) != contract._INDEX_COLS:
            errors.append(f"{index_path}: section `Ranked Active Backlog` headers do not match backlog contract")

    execution_rows = contract.rows_as_mapping(
        section=snapshot.get("execution", {}),
        expected_headers=contract._INDEX_COLS,
    )
    if not execution_rows:
        execution_section = snapshot.get("execution", {}) or {}
        execution_error = str(execution_section.get("error", "")).strip()
        if execution_error:
            errors.append(f"{index_path}: {execution_error}")
        elif tuple(execution_section.get("headers", [])) != contract._INDEX_COLS:
            errors.append(f"{index_path}: execution section headers do not match backlog contract")

    finished_rows = contract.rows_as_mapping(
        section=snapshot.get("finished", {}),
        expected_headers=contract._INDEX_COLS,
    )
    if not finished_rows:
        finished_section = snapshot.get("finished", {}) or {}
        finished_error = str(finished_section.get("error", "")).strip()
        if finished_error:
            errors.append(f"{index_path}: {finished_error}")
        elif tuple(finished_section.get("headers", [])) != contract._INDEX_COLS:
            errors.append(f"{index_path}: section `{_FINISHED_SECTION_TITLE}` headers do not match backlog contract")

    parked_rows = contract.rows_as_mapping(
        section=snapshot.get("parked", {}),
        expected_headers=contract._INDEX_COLS,
    )
    parked_section = snapshot.get("parked", {}) or {}
    parked_error = str(parked_section.get("error", "")).strip()
    if parked_error and not parked_error.startswith("missing section"):
        errors.append(f"{index_path}: {parked_error}")
    elif tuple(parked_section.get("headers", [])) not in {(), contract._INDEX_COLS}:
        errors.append(f"{index_path}: section `{_PARKED_SECTION_TITLE}` headers do not match backlog contract")

    rationale_errors = snapshot.get("reorder_errors", [])
    errors.extend([f"{index_path}: {message}" for message in rationale_errors if str(message).strip()])
    rationale_map: dict[str, list[str]] = {}
    rationale_sections = snapshot.get("reorder_sections", {}) or {}
    for key, payload in rationale_sections.items():
        lines = payload.get("lines", []) if isinstance(payload, Mapping) else []
        bullets: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            bullets.append(stripped[2:].strip())
        rationale_map[key] = bullets

    if str(args.runtime_mode).strip().lower() != "standalone":
        projection = odylith_context_engine_store.load_backlog_list(
            repo_root=repo_root,
            runtime_mode=str(args.runtime_mode),
        )
        active_rows = list(projection.get("active", active_rows))
        execution_rows = list(projection.get("execution", execution_rows))
        finished_rows = list(projection.get("finished", finished_rows))
        parked_rows = list(projection.get("parked", parked_rows))
        if isinstance(projection.get("rationale_map"), Mapping):
            rationale_map = {
                str(key): [str(item) for item in value]
                for key, value in projection.get("rationale_map", {}).items()
                if isinstance(value, list)
            }

    entries: list[dict[str, object]] = []
    for payload in active_rows:
        entry = _build_entry(
            repo_root=repo_root,
            output_path=output_path,
            payload=payload,
            section="active",
            rationale_map=rationale_map,
            errors=errors,
        )
        if entry is not None:
            entries.append(entry)
    for payload in execution_rows:
        entry = _build_entry(
            repo_root=repo_root,
            output_path=output_path,
            payload=payload,
            section="execution",
            rationale_map=rationale_map,
            errors=errors,
        )
        if entry is not None:
            entries.append(entry)
    for payload in finished_rows:
        entry = _build_entry(
            repo_root=repo_root,
            output_path=output_path,
            payload=payload,
            section="finished",
            rationale_map=rationale_map,
            errors=errors,
        )
        if entry is not None:
            entries.append(entry)
    for payload in parked_rows:
        entry = _build_entry(
            repo_root=repo_root,
            output_path=output_path,
            payload=payload,
            section="parked",
            rationale_map=rationale_map,
            errors=errors,
        )
        if entry is not None:
            entries.append(entry)

    if errors:
        print("backlog ui render FAILED")
        for message in errors:
            print(f"- {message}")
        return 2

    component_index = _load_component_index(repo_root=repo_root)
    _attach_component_registry_links(entries=entries, component_index=component_index)
    _attach_execution_overlay(entries=entries, repo_root=repo_root)
    render_backlog_ui_payload_runtime._attach_delivery_scope_signals(
        entries=entries,
        repo_root=repo_root,
        runtime_mode=str(args.runtime_mode),
    )

    detail_entries = {
        str(entry.get("idea_id", "")).strip(): _build_backlog_detail_entry(entry)
        for entry in entries
        if str(entry.get("idea_id", "")).strip()
    }
    detail_manifest, detail_shards = _chunk_backlog_items(
        items=detail_entries,
        shard_size=_BACKLOG_DETAIL_SHARD_SIZE,
        file_stem_prefix="backlog-detail-shard",
    )

    document_entries: dict[str, object] = {}
    for entry in entries:
        idea_id = str(entry.get("idea_id", "")).strip()
        if not idea_id:
            continue
        document_entries[f"spec:{idea_id}"] = _render_idea_spec_html(
            repo_root=repo_root,
            index_output_path=output_path,
            entry=entry,
            destination_output_path=output_path,
        )
        if str(entry.get("promoted_to_plan_file", "")).strip():
            document_entries[f"plan:{idea_id}"] = _render_plan_html(
                repo_root=repo_root,
                index_output_path=output_path,
                entry=entry,
                destination_output_path=output_path,
            )
    document_manifest, document_shards = _chunk_backlog_items(
        items=document_entries,
        shard_size=_BACKLOG_DOCUMENT_SHARD_SIZE,
        file_stem_prefix="backlog-document-shard",
    )
    analytics_path = output_path.parent / "backlog-analytics.v1.js"
    summary_entries = [_build_backlog_summary_entry(entry) for entry in entries]

    traceability_graph_path = (output_path.parent / "traceability-graph.v1.json").resolve()
    traceability_graph: dict[str, object] = {}
    if traceability_graph_path.is_file():
        try:
            traceability_graph = json.loads(traceability_graph_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            traceability_graph = {}
    execution_waves = execution_wave_view_model.build_execution_wave_view_payload(traceability_graph)
    traceability_index = _build_traceability_client_payload(traceability_graph)

    data = {
        "index_file": _as_repo_path(repo_root=repo_root, target=index_path),
        "index_updated": index_updated,
        "index_updated_display": dashboard_time.pacific_display_date_from_utc_token(index_updated, default="-"),
        "entries": summary_entries,
        "detail_manifest": detail_manifest,
        "standalone_manifest_href": standalone_pages_path.name,
        "data_source": {
            "preferred_backend": (
                "runtime" if str(args.runtime_mode).strip().lower() != "standalone" else "staticSnapshot"
            ),
            "available_backends": ["runtime", "staticSnapshot"],
            "runtime_base_url": "",
        },
        "traceability_graph_file": (
            _as_repo_path(repo_root=repo_root, target=traceability_graph_path)
            if traceability_graph_path.is_file()
            else ""
        ),
        "traceability_index": traceability_index,
        "execution_waves": execution_waves,
        "brand_head_html": brand_assets.render_brand_head_html(repo_root=repo_root, output_path=output_path),
        "tooltip_lookup": traceability_ui_lookup.build_tooltip_lookup_payload(
            entries=entries,
            diagrams=_atlas_diagram_catalog_rows(repo_root=repo_root),
            components=_component_catalog_rows(component_index=component_index),
            traceability_graph=traceability_graph,
        ),
    }
    html = _render_html(payload=data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bundled_html, payload_js, control_js = dashboard_surface_bundle.externalize_surface_bundle(
        html_text=html,
        payload=data,
        paths=bundle_paths,
        spec=dashboard_surface_bundle.standard_surface_bundle_spec(
            asset_prefix="backlog",
            payload_global_name="__ODYLITH_BACKLOG_DATA__",
            embedded_json_script_id="backlogData",
            bootstrap_binding_name="DATA",
            shell_tab="radar",
            shell_frame_id="frame-radar",
            query_passthrough=(
                ("view", ("view",)),
                ("workstream", ("workstream",)),
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
    standalone_pages_path.parent.mkdir(parents=True, exist_ok=True)
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=standalone_pages_path,
        content=dashboard_surface_bundle.render_payload_js(
            global_name="__ODYLITH_BACKLOG_STANDALONE_MANIFEST__",
            payload=document_manifest,
        ),
        lock_key=str(standalone_pages_path),
    )
    active_shard_outputs: set[Path] = {
        standalone_pages_path.resolve(),
    }
    for filename, shard_payload in detail_shards:
        shard_path = output_path.parent / filename
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=shard_path,
            content=dashboard_surface_bundle.render_payload_merge_js(
                global_name="__ODYLITH_BACKLOG_DETAIL_SHARDS__",
                payload=shard_payload,
            ),
            lock_key=str(shard_path),
        )
        active_shard_outputs.add(shard_path.resolve())
    for filename, shard_payload in document_shards:
        shard_path = output_path.parent / filename
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=shard_path,
            content=dashboard_surface_bundle.render_payload_merge_js(
                global_name="__ODYLITH_BACKLOG_DOCUMENT_SHARDS__",
                payload=shard_payload,
            ),
            lock_key=str(shard_path),
        )
        active_shard_outputs.add(shard_path.resolve())
    for pattern in ("backlog-detail-shard-*.v1.js", "backlog-document-shard-*.v1.js"):
        for stale_path in output_path.parent.glob(pattern):
            if stale_path.resolve() in active_shard_outputs:
                continue
            if stale_path.is_file():
                stale_path.unlink()
    if analytics_path.is_file():
        analytics_path.unlink()
    source_bundle_mirror.sync_live_paths(
        repo_root=repo_root,
        live_paths=(
            output_path,
            bundle_paths.payload_js_path,
            bundle_paths.control_js_path,
            standalone_pages_path,
        ),
    )
    source_bundle_mirror.sync_live_glob(
        repo_root=repo_root,
        live_dir=output_path.parent,
        pattern="backlog-detail-shard-*.v1.js",
    )
    source_bundle_mirror.sync_live_glob(
        repo_root=repo_root,
        live_dir=output_path.parent,
        pattern="backlog-document-shard-*.v1.js",
    )
    if input_fingerprint:
        _bundle_paths, current_output_paths = generated_surface_refresh_guards.surface_output_paths(
            repo_root=repo_root,
            output_path=output_path,
            asset_prefix="backlog",
            extra_live_paths=(standalone_pages_path,),
            live_globs=("backlog-detail-shard-*.v1.js", "backlog-document-shard-*.v1.js"),
        )
        generated_surface_refresh_guards.record_surface_rebuild(
            repo_root=repo_root,
            key=_BACKLOG_REFRESH_GUARD_KEY,
            input_fingerprint=input_fingerprint,
            output_paths=current_output_paths,
            metadata={
                "idea_count": len(entries),
                "detail_shards": len(detail_shards),
                "document_shards": len(document_shards),
            },
        )

    legacy_ui_root = (repo_root / "backlog" / "ui").resolve()
    generated_surface_cleanup.remove_legacy_generated_paths(
        active_outputs=(
            output_path,
            bundle_paths.payload_js_path,
            bundle_paths.control_js_path,
            standalone_pages_path,
            traceability_graph_path,
            *[Path(path) for path in active_shard_outputs],
        ),
        legacy_paths=(
            legacy_ui_root / "index.html",
            legacy_ui_root / "traceability-graph.v1.json",
            legacy_ui_root / "traceability-autofix-report.v1.json",
            legacy_ui_root / "ideas",
            legacy_ui_root / "plans",
            output_path.parent / "ideas",
            output_path.parent / "plans",
        ),
    )
    generated_surface_cleanup.remove_empty_directory(legacy_ui_root)

    print("backlog ui render passed")
    print(f"- output: {output_path}")
    print(f"- standalone_pages: {standalone_pages_path}")
    print(f"- ideas: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

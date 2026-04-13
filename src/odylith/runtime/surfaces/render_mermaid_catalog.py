"""Render a bright, interactive Mermaid diagram catalog with linked engineering context.

Source of truth:
- odylith/atlas/source/catalog/diagrams.v1.json

Generated artifact:
- odylith/atlas/atlas.html
"""

from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import replace
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance.delivery import scope_signal_ladder
from odylith.runtime.surfaces import brand_assets
from odylith.runtime.surfaces import dashboard_shell_links
from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import dashboard_ui_runtime_primitives
from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.governance import delivery_intelligence_engine  # Backward-compatible test monkeypatch surface.
from odylith.runtime.surfaces import generated_surface_cleanup
from odylith.runtime.surfaces import source_bundle_mirror
from odylith.runtime.common import diagram_freshness
from odylith.runtime.common import generated_refresh_guard
from odylith.runtime.common.repo_path_resolver import RepoPathResolver
from odylith.runtime.common.repo_shape import CONSUMER_REPO_ROLE, repo_role_from_local_shape
from odylith.runtime.common import stable_generated_utc
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.governance import traceability_ui_lookup


_SVG_VIEWBOX_RE = re.compile(r"viewBox\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-(\d{3,})$")
_DIAGRAM_COMPACT_RE = re.compile(r"^D(\d{3,})$")
_ATLAS_RENDER_GUARD_NAMESPACE = "generated-refresh-guards"
_ATLAS_RENDER_GUARD_KEY = "atlas-render"


def _extract_svg_viewbox_dimensions(svg_path: Path) -> tuple[float, float] | None:
    """Best-effort extraction of SVG viewBox width/height."""

    if not svg_path.is_file():
        return None
    try:
        text = svg_path.read_text(encoding="utf-8")
    except OSError:
        return None

    match = _SVG_VIEWBOX_RE.search(text)
    if match is None:
        return None
    raw = str(match.group(1)).strip()
    if not raw:
        return None

    parts = [token for token in re.split(r"[\s,]+", raw) if token]
    if len(parts) != 4:
        return None
    try:
        width = float(parts[2])
        height = float(parts[3])
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render odylith/atlas/atlas.html from catalog metadata")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--catalog",
        default="odylith/atlas/source/catalog/diagrams.v1.json",
        help="Diagram catalog metadata path",
    )
    parser.add_argument("--output", default="odylith/atlas/atlas.html", help="HTML output path")
    parser.add_argument(
        "--traceability-graph",
        default="odylith/radar/traceability-graph.v1.json",
        help="Shared workstream traceability graph JSON path.",
    )
    parser.add_argument(
        "--max-review-age-days",
        type=int,
        default=21,
        help="Maximum allowed age for `last_reviewed_utc` before diagram is marked stale",
    )
    parser.add_argument(
        "--fail-on-stale",
        action="store_true",
        help="Fail with non-zero exit when one or more diagrams are stale",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate catalog + freshness without writing odylith/atlas/atlas.html.",
    )
    parser.add_argument(
        "--diagram-id",
        action="append",
        default=[],
        help="Optional diagram id to scope freshness failure checks (repeatable).",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local runtime projection store when available for fast local rendering.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, value: str) -> Path:
    raw = str(value or "").strip()
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _as_repo_path(repo_root: Path, target: Path) -> str:
    try:
        return target.relative_to(repo_root).as_posix()
    except ValueError:
        return str(target)


def _as_href(output_path: Path, target: Path) -> str:
    rel = os.path.relpath(str(target), start=str(output_path.parent))
    return Path(rel).as_posix()


def _load_component_index(
    *,
    repo_root: Path,
) -> Mapping[str, component_registry.ComponentEntry]:
    manifest_path = component_registry.default_manifest_path(repo_root=repo_root)
    if not manifest_path.is_file():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload.get("components") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list):
        return {}
    components: dict[str, component_registry.ComponentEntry] = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        entry = component_registry._component_entry_from_payload(raw)  # noqa: SLF001
        component_id = component_registry.normalize_component_id(entry.component_id)
        if not component_id or not str(entry.name).strip():
            continue
        components[component_id] = replace(
            entry,
            component_id=component_id,
            aliases=[
                normalized
                for token in entry.aliases
                for normalized in [component_registry.normalize_component_id(token)]
                if normalized
            ],
            workstreams=[
                normalized
                for token in entry.workstreams
                for normalized in [component_registry.normalize_workstream_id(token)]
                if normalized
            ],
        )
    return components


def _load_delivery_surface_payload(
    *,
    repo_root: Path,
    surface: str,
) -> dict[str, Any]:
    try:
        payload = delivery_intelligence_engine.load_delivery_intelligence_artifact(repo_root=repo_root)
    except Exception:
        payload = {}
    if isinstance(payload, Mapping):
        try:
            return delivery_intelligence_engine.slice_delivery_intelligence_for_surface(
                payload=payload,
                surface=surface,
            )
        except Exception:
            return {}
    return {}


def _component_catalog_rows(
    *,
    component_index: Mapping[str, component_registry.ComponentEntry],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for component_id in sorted(component_index):
        row = component_index[component_id]
        rows.append(
            {
                "component_id": component_id,
                "name": row.name or component_id,
            }
        )
    return rows


def _surface_links_for_diagram(
    *,
    tooling_shell_href: str,
    related_workstreams: list[str],
    related_component_ids: set[str],
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    primary_workstream = related_workstreams[0] if related_workstreams else ""
    registry_component = ""
    if related_component_ids:
        registry_component = sorted(related_component_ids)[0]

    if primary_workstream:
        links.append(
            {
                "file": f"Radar ({primary_workstream})",
                "href": f"{tooling_shell_href}{dashboard_shell_links.radar_workstream_href(primary_workstream)}",
                "target": "_top",
            }
        )
        links.append(
            {
                "file": f"Compass ({primary_workstream})",
                "href": f"{tooling_shell_href}?tab=compass&scope={primary_workstream}&date=live",
                "target": "_top",
            }
        )
    if registry_component:
        links.append(
            {
                "file": f"Registry ({registry_component})",
                "href": f"{tooling_shell_href}?tab=registry&component={registry_component}",
                "target": "_top",
            }
        )
    return links


def _assert_non_empty(*, name: str, value: Any, errors: list[str], context: str) -> str:
    text = str(value or "").strip()
    if not text:
        errors.append(f"{context}: missing `{name}`")
    return text


def _parse_review_date(*, value: str, errors: list[str], context: str) -> dt.date | None:
    token = str(value or "").strip()
    if not token:
        errors.append(f"{context}: missing `last_reviewed_utc`")
        return None
    try:
        return dt.date.fromisoformat(token)
    except ValueError:
        errors.append(f"{context}: `last_reviewed_utc` must be YYYY-MM-DD, got `{token}`")
        return None


def _validate_related_paths(
    *,
    repo_root: Path,
    values: list[Any],
    field: str,
    context: str,
    errors: list[str],
    required: bool,
    resolve_path: Callable[[str], Path] | None = None,
    repo_path_for: Callable[[str | Path], str] | None = None,
) -> list[str]:
    resolved: list[str] = []
    for raw in values:
        token = str(raw or "").strip()
        if not token:
            errors.append(f"{context}: `{field}` contains empty path value")
            continue
        target = resolve_path(token) if resolve_path is not None else _resolve(repo_root, token)
        if not target.exists():
            errors.append(f"{context}: `{field}` path does not exist: {token}")
            continue
        if repo_path_for is not None:
            resolved.append(repo_path_for(target))
        else:
            resolved.append(_as_repo_path(repo_root, target))

    if required and not resolved:
        errors.append(f"{context}: `{field}` must contain at least one valid path")
    return resolved


def _read_backlog_front_matter_fields(
    *,
    path: Path,
    field_names: Sequence[str],
    cache: dict[str, dict[str, str]] | None = None,
) -> dict[str, str]:
    target = Path(path).resolve()
    cache_key = str(target)
    if cache is not None and cache_key in cache:
        return dict(cache[cache_key])

    wanted = {str(name).strip() for name in field_names if str(name).strip()}
    metadata = {name: "" for name in wanted}
    if not wanted or not target.is_file():
        if cache is not None:
            cache[cache_key] = dict(metadata)
        return metadata

    try:
        with target.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if line.startswith("## "):
                    break
                if not line or line in {"---", "..."} or line.startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                normalized_key = key.strip()
                if normalized_key not in wanted or metadata[normalized_key]:
                    continue
                metadata[normalized_key] = value.strip()
                if all(metadata[name] for name in wanted):
                    break
    except OSError:
        metadata = {name: "" for name in wanted}

    if cache is not None:
        cache[cache_key] = dict(metadata)
    return metadata


def _stored_watch_fingerprints(item: Mapping[str, Any]) -> dict[str, str]:
    raw = item.get("reviewed_watch_fingerprints", {})
    if not isinstance(raw, Mapping):
        return {}
    return {str(key).strip(): str(value).strip() for key, value in raw.items() if str(key).strip() and str(value).strip()}


def _max_mtime(path: Path, *, cache: dict[str, float] | None = None) -> float:
    cache_key = str(path.resolve())
    if cache is not None and cache_key in cache:
        return cache[cache_key]
    try:
        if path.is_file():
            value = path.stat().st_mtime
            if cache is not None:
                cache[cache_key] = value
            return value
        if path.is_dir():
            newest = path.stat().st_mtime
            for node in path.rglob("*"):
                try:
                    if node.is_file():
                        newest = max(newest, node.stat().st_mtime)
                except OSError:
                    continue
            if cache is not None:
                cache[cache_key] = newest
            return newest
    except OSError:
        if cache is not None:
            cache[cache_key] = 0.0
        return 0.0
    if cache is not None:
        cache[cache_key] = 0.0
    return 0.0


def _newest_watch_path(
    *,
    repo_root: Path,
    watch_paths: list[str],
    mtime_cache: dict[str, float] | None = None,
    resolve_path: Callable[[str], Path] | None = None,
    repo_path_for: Callable[[str | Path], str] | None = None,
) -> tuple[float, str]:
    newest_time = 0.0
    newest_path = ""
    for raw in watch_paths:
        target = resolve_path(raw) if resolve_path is not None else _resolve(repo_root, raw)
        score = _max_mtime(target, cache=mtime_cache)
        if score > newest_time:
            newest_time = score
            if repo_path_for is not None:
                newest_path = repo_path_for(target)
            else:
                newest_path = _as_repo_path(repo_root, target)
    return newest_time, newest_path


def _normalize_workstream_id(value: str) -> str:
    token = str(value or "").strip().upper()
    if _WORKSTREAM_ID_RE.fullmatch(token):
        return token
    return ""


def _normalize_diagram_id(value: str) -> str:
    token = str(value or "").strip().upper()
    if token.startswith("DIAGRAM:"):
        token = token[len("DIAGRAM:") :].strip()
    matched = _DIAGRAM_ID_RE.fullmatch(token)
    if matched is not None:
        return f"D-{matched.group(1)}"
    compact = _DIAGRAM_COMPACT_RE.fullmatch(token)
    if compact is not None:
        return f"D-{compact.group(1)}"
    return ""


def _load_catalog(
    *,
    repo_root: Path,
    catalog_path: Path,
    output_path: Path,
    max_review_age_days: int,
    component_index: Mapping[str, component_registry.ComponentEntry],
) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    errors: list[str] = []
    stats = {"total": 0, "fresh": 0, "stale": 0}
    if not catalog_path.is_file():
        return [], [f"catalog missing: {catalog_path}"], stats

    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"invalid json: {catalog_path}: {exc}"], stats

    diagrams = payload.get("diagrams", [])
    if not isinstance(diagrams, list):
        return [], [f"{catalog_path}: `diagrams` must be a list"], stats
    if not diagrams:
        if repo_role_from_local_shape(repo_root=repo_root) == CONSUMER_REPO_ROLE:
            return [], [], stats
        return [], [f"{catalog_path}: `diagrams` list is empty"], stats

    today = dt.date.today()
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    rendered: list[dict[str, Any]] = []
    path_resolver = RepoPathResolver(repo_root=repo_root, output_path=output_path)
    tooling_shell_href = path_resolver.href("odylith/index.html")
    watch_path_mtime_cache: dict[str, float] = {}
    watch_path_content_cache = diagram_freshness.ContentFingerprintCache()
    backlog_metadata_cache: dict[str, dict[str, str]] = {}

    for idx, item in enumerate(diagrams):
        context = f"{catalog_path}: diagrams[{idx}]"
        stats["total"] += 1
        if not isinstance(item, dict):
            errors.append(f"{context}: entry must be an object")
            continue

        diagram_id = _assert_non_empty(name="diagram_id", value=item.get("diagram_id"), errors=errors, context=context)
        normalized_diagram_id = _normalize_diagram_id(diagram_id)
        if not normalized_diagram_id:
            errors.append(f"{context}: invalid `diagram_id` `{diagram_id}` (expected `D-###`)")
            continue
        diagram_id = normalized_diagram_id
        slug = _assert_non_empty(name="slug", value=item.get("slug"), errors=errors, context=context)
        title = _assert_non_empty(name="title", value=item.get("title"), errors=errors, context=context)
        kind = _assert_non_empty(name="kind", value=item.get("kind"), errors=errors, context=context)
        status = _assert_non_empty(name="status", value=item.get("status"), errors=errors, context=context)
        owner = _assert_non_empty(name="owner", value=item.get("owner"), errors=errors, context=context)
        summary = _assert_non_empty(name="summary", value=item.get("summary"), errors=errors, context=context)
        source_mmd = _assert_non_empty(name="source_mmd", value=item.get("source_mmd"), errors=errors, context=context)
        source_svg = _assert_non_empty(name="source_svg", value=item.get("source_svg"), errors=errors, context=context)
        source_png = str(item.get("source_png", "")).strip()
        initial_view_fit_factor = 0.0
        raw_initial_view_fit_factor = item.get("initial_view_fit_factor")
        if raw_initial_view_fit_factor not in (None, ""):
            try:
                initial_view_fit_factor = float(raw_initial_view_fit_factor)
            except (TypeError, ValueError):
                errors.append(
                    f"{context}: `initial_view_fit_factor` must be numeric when present"
                )
            else:
                if initial_view_fit_factor <= 0 or initial_view_fit_factor > 1.5:
                    errors.append(
                        f"{context}: `initial_view_fit_factor` must be within (0, 1.5], got `{initial_view_fit_factor}`"
                    )
                    initial_view_fit_factor = 0.0
        review_date = _parse_review_date(value=item.get("last_reviewed_utc", ""), errors=errors, context=context)

        raw_watch = item.get("change_watch_paths", [])
        if not isinstance(raw_watch, list) or not raw_watch:
            errors.append(f"{context}: `change_watch_paths` must be a non-empty list")
            watch_paths: list[str] = []
        else:
            watch_paths = [str(token or "").strip() for token in raw_watch if str(token or "").strip()]
            if not watch_paths:
                errors.append(f"{context}: `change_watch_paths` contains no usable paths")

        if diagram_id in seen_ids:
            errors.append(f"{context}: duplicate diagram_id `{diagram_id}`")
        seen_ids.add(diagram_id)
        if slug:
            if slug in seen_slugs:
                errors.append(f"{context}: duplicate slug `{slug}`")
            seen_slugs.add(slug)

        mmd_path = path_resolver.resolve(source_mmd) if source_mmd else None
        svg_path = path_resolver.resolve(source_svg) if source_svg else None
        png_path = path_resolver.resolve(source_png) if source_png else None

        if mmd_path is not None and not mmd_path.is_file():
            errors.append(f"{context}: source_mmd does not exist: {source_mmd}")
        if svg_path is not None and not svg_path.is_file():
            errors.append(f"{context}: source_svg does not exist: {source_svg}")
        if source_png and png_path is not None and not png_path.is_file():
            errors.append(f"{context}: source_png does not exist: {source_png}")

        for watch in watch_paths:
            target = path_resolver.resolve(watch)
            if not target.exists():
                errors.append(f"{context}: change_watch_paths entry does not exist: {watch}")

        raw_components = item.get("components", [])
        if not isinstance(raw_components, list) or not raw_components:
            errors.append(f"{context}: `components` must be a non-empty list")
            components: list[dict[str, str]] = []
        else:
            components = []
            for comp_idx, comp in enumerate(raw_components):
                if not isinstance(comp, dict):
                    errors.append(f"{context}: components[{comp_idx}] must be an object")
                    continue
                comp_name = str(comp.get("name", "")).strip()
                comp_desc = str(comp.get("description", "")).strip()
                if not comp_name or not comp_desc:
                    errors.append(
                        f"{context}: components[{comp_idx}] requires non-empty `name` and `description`"
                    )
                    continue
                components.append({"name": comp_name, "description": comp_desc})

        related_backlog = _validate_related_paths(
            repo_root=repo_root,
            values=item.get("related_backlog", []),
            field="related_backlog",
            context=context,
            errors=errors,
            required=True,
            resolve_path=path_resolver.resolve,
            repo_path_for=path_resolver.repo_path,
        )
        related_plans = _validate_related_paths(
            repo_root=repo_root,
            values=item.get("related_plans", []),
            field="related_plans",
            context=context,
            errors=errors,
            required=True,
            resolve_path=path_resolver.resolve,
            repo_path_for=path_resolver.repo_path,
        )
        related_docs = _validate_related_paths(
            repo_root=repo_root,
            values=item.get("related_docs", []),
            field="related_docs",
            context=context,
            errors=errors,
            required=True,
            resolve_path=path_resolver.resolve,
            repo_path_for=path_resolver.repo_path,
        )
        related_code = _validate_related_paths(
            repo_root=repo_root,
            values=item.get("related_code", []),
            field="related_code",
            context=context,
            errors=errors,
            required=False,
            resolve_path=path_resolver.resolve,
            repo_path_for=path_resolver.repo_path,
        )
        raw_related_workstreams = item.get("related_workstreams", [])
        related_workstreams: list[str] = []
        if raw_related_workstreams and not isinstance(raw_related_workstreams, list):
            errors.append(f"{context}: `related_workstreams` must be a list when present")
        elif isinstance(raw_related_workstreams, list):
            for token in raw_related_workstreams:
                value = _normalize_workstream_id(str(token or ""))
                if not value:
                    raw_value = str(token or "").strip()
                    if raw_value:
                        errors.append(f"{context}: invalid related_workstreams entry `{raw_value}`")
                    continue
                related_workstreams.append(value)
        backlog_workstreams: list[str] = []
        related_backlog_entries: list[dict[str, str]] = []
        for backlog_rel in related_backlog:
            metadata = _read_backlog_front_matter_fields(
                path=path_resolver.resolve(backlog_rel),
                field_names=("idea_id", "title"),
                cache=backlog_metadata_cache,
            )
            inferred = _normalize_workstream_id(metadata.get("idea_id", ""))
            if inferred:
                backlog_workstreams.append(inferred)
            related_backlog_entries.append(
                {
                    "file": backlog_rel,
                    "href": path_resolver.href(backlog_rel),
                    "idea_id": inferred,
                    "title": str(metadata.get("title", "")).strip(),
                }
            )
        related_workstreams = sorted(set(related_workstreams))
        context_workstreams = sorted(set(related_workstreams) | set(backlog_workstreams))
        related_component_ids: set[str] = set()
        if component_index:
            for component_row in components:
                component_id = component_registry.component_id_for_token(
                    token=str(component_row.get("name", "")),
                    components=component_index,
                )
                if component_id:
                    related_component_ids.add(component_id)
            for workstream_id in context_workstreams:
                related_component_ids.update(
                    component_registry.component_ids_for_workstream(
                        components=component_index,
                        workstream_id=workstream_id,
                    )
                )
        related_registry = [
            {
                "file": (
                    f"{component_index[component_id].name or component_id} ({component_id})"
                    if component_id in component_index
                    else component_id
                ),
                "href": f"{tooling_shell_href}?tab=registry&component={component_id}",
                "target": "_top",
            }
            for component_id in sorted(related_component_ids)
        ]
        related_surfaces = _surface_links_for_diagram(
            tooling_shell_href=tooling_shell_href,
            related_workstreams=context_workstreams,
            related_component_ids=related_component_ids,
        )

        if mmd_path is None or svg_path is None or review_date is None:
            continue

        viewbox_dims = _extract_svg_viewbox_dimensions(svg_path)
        viewbox_width = float(viewbox_dims[0]) if viewbox_dims else 0.0
        viewbox_height = float(viewbox_dims[1]) if viewbox_dims else 0.0

        stale_reasons: list[str] = []
        current_watch_fingerprints = diagram_freshness.watched_path_fingerprints(
            repo_root=repo_root,
            watched_paths=watch_paths,
            resolve_path=path_resolver.resolve,
            cache=watch_path_content_cache,
        )
        stored_watch_fingerprints = _stored_watch_fingerprints(item)

        if stored_watch_fingerprints:
            changed_watch_paths = [
                token
                for token in watch_paths
                if stored_watch_fingerprints.get(token, "") != current_watch_fingerprints.get(token, "")
            ]
            if changed_watch_paths:
                stale_reasons.append(
                    f"Linked implementation changed after diagram source update ({changed_watch_paths[0]})."
                )
        else:
            mmd_mtime = _max_mtime(mmd_path)
            newest_watch_mtime, newest_watch_path = _newest_watch_path(
                repo_root=repo_root,
                watch_paths=watch_paths,
                mtime_cache=watch_path_mtime_cache,
                resolve_path=path_resolver.resolve,
                repo_path_for=path_resolver.repo_path,
            )
            if newest_watch_mtime > (mmd_mtime + 0.0001):
                stale_reasons.append(
                    f"Linked implementation changed after diagram source update ({newest_watch_path})."
                )

        review_age_days = (today - review_date).days
        if review_age_days > max_review_age_days:
            stale_reasons.append(
                f"Last review is {review_age_days} days old (limit {max_review_age_days})."
            )

        freshness = "stale" if stale_reasons else "fresh"
        if freshness == "stale":
            stats["stale"] += 1
        else:
            stats["fresh"] += 1

        rendered.append(
            {
                "diagram_id": diagram_id,
                "slug": slug,
                "title": title,
                "kind": kind,
                "status": status,
                "owner": owner,
                "summary": summary,
                "last_reviewed_utc": review_date.isoformat(),
                "review_age_days": review_age_days,
                "freshness": freshness,
                "stale_reasons": stale_reasons,
                "source_mmd_file": path_resolver.repo_path(mmd_path),
                "source_svg_file": path_resolver.repo_path(svg_path),
                "source_png_file": path_resolver.repo_path(png_path) if png_path else "",
                "source_mmd_href": path_resolver.href(mmd_path),
                "source_svg_href": path_resolver.href(svg_path),
                "source_png_href": path_resolver.href(png_path) if png_path else "",
                "svg_viewbox_width": viewbox_width,
                "svg_viewbox_height": viewbox_height,
                "initial_view_fit_factor": initial_view_fit_factor,
                "components": components,
                "related_backlog": related_backlog_entries,
                "related_plans": [
                    {
                        "file": path,
                        "href": path_resolver.href(path),
                    }
                    for path in related_plans
                ],
                "related_docs": [
                    {
                        "file": path,
                        "href": path_resolver.href(path),
                    }
                    for path in related_docs
                ],
                "related_code": [
                    {
                        "file": path,
                        "href": path_resolver.href(path),
                    }
                    for path in related_code
                ],
                "related_registry": related_registry,
                "related_surfaces": related_surfaces,
                "related_workstreams": related_workstreams,
            }
        )

    return rendered, errors, stats


def _merge_related_workstreams_from_traceability(
    *,
    diagrams: list[dict[str, Any]],
    traceability_graph: Mapping[str, Any],
) -> dict[str, set[str]]:
    """Return traceability-derived diagram-to-workstream references."""

    graph_rows = traceability_graph.get("workstreams", []) if isinstance(traceability_graph, Mapping) else []
    if not isinstance(graph_rows, list):
        return {}

    by_diagram: dict[str, set[str]] = {}
    for row in graph_rows:
        if not isinstance(row, Mapping):
            continue
        workstream = _normalize_workstream_id(str(row.get("idea_id", "")))
        if not workstream:
            continue
        diagram_values = row.get("related_diagram_ids", [])
        if not isinstance(diagram_values, list):
            continue
        for raw_id in diagram_values:
            diagram_id = _normalize_diagram_id(str(raw_id or ""))
            if not diagram_id:
                continue
            by_diagram.setdefault(diagram_id, set()).add(workstream)
    return by_diagram


def _delivery_workstream_rows(
    *,
    delivery_intelligence: Mapping[str, Any],
) -> list[tuple[str, Mapping[str, Any]]]:
    workstreams = (
        delivery_intelligence.get("workstreams", [])
        if isinstance(delivery_intelligence.get("workstreams"), list)
        else delivery_intelligence.get("workstreams", {})
    )
    rows: list[tuple[str, Mapping[str, Any]]] = []
    if isinstance(workstreams, Mapping):
        for scope_id, snapshot in workstreams.items():
            if isinstance(snapshot, Mapping):
                rows.append((str(scope_id), snapshot))
    elif isinstance(workstreams, list):
        for snapshot in workstreams:
            if isinstance(snapshot, Mapping):
                rows.append((str(snapshot.get("scope_id", "")), snapshot))
    return rows


def _meaningful_active_diagram_touches(
    *,
    delivery_intelligence: Mapping[str, Any],
) -> dict[str, set[str]]:
    """Return workstreams with recent meaningful evidence for each diagram.

    Atlas needs a narrower notion of "active touches" than the broad
    traceability graph. We only surface workstreams here when the delivery
    intelligence slice says the scope both links to the diagram and still has
    meaningful recent evidence worth operator attention.
    """

    by_diagram: dict[str, set[str]] = {}
    for raw_scope_id, snapshot in _delivery_workstream_rows(delivery_intelligence=delivery_intelligence):
        workstream_id = _normalize_workstream_id(raw_scope_id) or _normalize_workstream_id(
            str(snapshot.get("scope_id", ""))
        )
        if not workstream_id:
            continue

        evidence_context = (
            snapshot.get("evidence_context", {})
            if isinstance(snapshot.get("evidence_context"), Mapping)
            else {}
        )
        linked_diagrams = {
            diagram_id
            for token in evidence_context.get("linked_diagrams", [])
            if isinstance(evidence_context.get("linked_diagrams"), list)
            for diagram_id in [_normalize_diagram_id(str(token or ""))]
            if diagram_id
        }
        if not linked_diagrams:
            continue

        scope_signal = snapshot.get("scope_signal", {}) if isinstance(snapshot.get("scope_signal"), Mapping) else {}
        if scope_signal:
            if scope_signal_ladder.scope_signal_rank(scope_signal) < scope_signal_ladder.DEFAULT_PROMOTED_DEFAULT_RANK:
                continue
            if not bool(scope_signal.get("promoted_default", False)):
                continue
        else:
            diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
            change_vector = snapshot.get("change_vector", {}) if isinstance(snapshot.get("change_vector"), Mapping) else {}
            evidence_bundle = (
                snapshot.get("evidence_bundle", {})
                if isinstance(snapshot.get("evidence_bundle"), Mapping)
                else {}
            )

            live_actionable = bool(diagnostics.get("live_actionable", False))
            status = str(diagnostics.get("status", "")).strip().lower()
            latest_event = str(evidence_context.get("latest_event_ts_iso", "")).strip()
            latest_explicit = str(evidence_context.get("latest_explicit_ts_iso", "")).strip()
            has_recent_delta = bool(latest_event and (not latest_explicit or latest_event > latest_explicit))
            has_meaningful_change = any(
                int(change_vector.get(bucket, 0) or 0) > 0
                for bucket in ("build_ci", "cli", "contract", "policy", "renderer", "runtime", "spec", "runbook")
            )
            if not has_meaningful_change:
                has_meaningful_change = bool(evidence_bundle.get("code_references")) or bool(
                    evidence_bundle.get("changed_artifacts")
                )

            if not has_meaningful_change:
                continue

            if status in {"planning", "implementation"}:
                qualifies_as_active = True
            elif status == "parked":
                qualifies_as_active = live_actionable or has_recent_delta
            else:
                qualifies_as_active = False

            if not qualifies_as_active:
                continue

        for diagram_id in linked_diagrams:
            by_diagram.setdefault(diagram_id, set()).add(workstream_id)
    return by_diagram


def _workstream_title_entries(
    *,
    repo_root: Path,
    diagrams: list[dict[str, Any]],
    delivery_intelligence: Mapping[str, Any],
) -> list[dict[str, str]]:
    lookup: dict[str, str] = {}
    path_resolver = RepoPathResolver(repo_root=repo_root)

    def remember(*, workstream_id: str, title: str) -> None:
        normalized_id = _normalize_workstream_id(workstream_id)
        text = str(title or "").strip()
        if not normalized_id or not text:
            return
        lookup[normalized_id] = text

    for raw_scope_id, snapshot in _delivery_workstream_rows(delivery_intelligence=delivery_intelligence):
        remember(
            workstream_id=str(raw_scope_id or snapshot.get("scope_id", "")),
            title=str(snapshot.get("scope_label") or snapshot.get("title") or snapshot.get("label") or ""),
        )

    backlog_metadata_cache: dict[str, dict[str, str]] = {}
    for diagram in diagrams:
        related_backlog = diagram.get("related_backlog", [])
        if not isinstance(related_backlog, list):
            continue
        for item in related_backlog:
            if not isinstance(item, Mapping):
                continue
            raw_path = str(item.get("file", "")).strip()
            metadata = {
                "idea_id": str(item.get("idea_id", "")).strip(),
                "title": str(item.get("title", "")).strip(),
            }
            if not metadata["idea_id"] or not metadata["title"]:
                metadata = _read_backlog_front_matter_fields(
                    path=path_resolver.resolve(raw_path),
                    field_names=("idea_id", "title"),
                    cache=backlog_metadata_cache,
                )
            remember(
                workstream_id=str(metadata.get("idea_id", "")),
                title=str(metadata.get("title", "")),
            )

    return [
        {"idea_id": workstream_id, "title": lookup[workstream_id]}
        for workstream_id in sorted(lookup)
    ]


def _attach_diagram_workstream_relationships(
    *,
    diagrams: list[dict[str, Any]],
    traceability_graph: Mapping[str, Any],
    delivery_intelligence: Mapping[str, Any],
) -> None:
    """Split diagram workstreams into owners, active touches, and historical references."""

    traceability_refs = _merge_related_workstreams_from_traceability(
        diagrams=diagrams,
        traceability_graph=traceability_graph,
    )
    active_refs = _meaningful_active_diagram_touches(delivery_intelligence=delivery_intelligence)

    for diagram in diagrams:
        diagram_id = _normalize_diagram_id(str(diagram.get("diagram_id", "")))
        if not diagram_id:
            continue
        traceability_workstreams = set(traceability_refs.get(diagram_id, set()))
        owners = {
            workstream
            for token in diagram.get("related_workstreams", [])
            if isinstance(diagram.get("related_workstreams"), list)
            for workstream in [_normalize_workstream_id(str(token or ""))]
            if workstream
        }
        # Fail closed on Atlas "active touch" noise: only promote active workstreams
        # that already have authored traceability to the diagram instead of letting
        # broad delivery-intelligence linkage invent new diagram associations.
        active_touches = (set(active_refs.get(diagram_id, set())) & traceability_workstreams) - owners
        historical_refs = traceability_workstreams - owners - active_touches
        diagram["owner_workstreams"] = sorted(owners)
        diagram["active_workstreams"] = sorted(active_touches)
        diagram["historical_workstreams"] = sorted(historical_refs)
        diagram["related_workstreams"] = sorted(owners)


def _render_html(
    *,
    diagrams: list[dict[str, Any]],
    stats: dict[str, int],
    max_review_age_days: int,
    tooltip_lookup: dict[str, dict[str, str]],
    generated_utc: str,
    brand_head_html: str,
    tooling_base_href: str,
) -> str:
    payload = {
        "generated_utc": generated_utc,
        "max_review_age_days": max_review_age_days,
        "stats": stats,
        "diagrams": diagrams,
        "tooltip_lookup": tooltip_lookup,
    }
    payload_json = json.dumps(payload, indent=2)
    page_body_css = dashboard_ui_primitives.page_body_typography_css(
        selector="body",
        color="var(--ink)",
    )
    atlas_header_css = dashboard_ui_primitives.header_typography_css(
        kicker_selector=".eyebrow",
        title_selector=".title",
        subtitle_selector=".subtitle",
        subtitle_max_width="100%",
        desktop_single_line_subtitle=False,
        mobile_breakpoint_px=760,
        mobile_title_size_px=22,
        mobile_subtitle_size_px=13,
    )
    display_title_css = dashboard_ui_primitives.detail_identity_typography_css(
        title_selector=".hero-title",
        subtitle_selector=".hero-title-subtitle-unused",
        title_margin="0",
        title_size_px=26,
        medium_title_size_px=23,
        small_title_size_px=20,
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
    operator_readout_label_css = dashboard_ui_primitives.operator_readout_label_typography_css(
        selector=".operator-readout-label",
    )
    operator_readout_copy_css = dashboard_ui_primitives.operator_readout_copy_typography_css(
        selector=".operator-readout-copy",
        color="#27445e",
        line_height=1.55,
    )
    readable_copy_css = dashboard_ui_primitives.content_copy_css(
        selectors=(
            ".summary",
            ".component-card p",
        ),
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
    atlas_compact_button_css = dashboard_ui_primitives.detail_action_chip_css(
        selector=".chip, .tool-btn, .source-link",
    )
    sidebar_close_button_css = dashboard_ui_primitives.button_typography_css(
        selector=".sidebar-close",
        color="#144261",
        size_px=20,
        line_height=1.0,
    )
    atlas_label_css = dashboard_ui_primitives.label_badge_typography_css(
        selector=".tag, .meta-pill",
        color="#334155",
        size_px=11,
    )
    atlas_fact_typography_css = dashboard_ui_primitives.compact_label_value_typography_css(
        label_selector=".diagram-fact-label",
        value_selector=".diagram-fact-value",
        label_color="#64748b",
        value_color="#16324f",
    )
    atlas_stat_typography_css = dashboard_ui_primitives.kpi_typography_css(
        label_selector=".stat .l",
        value_selector=".stat .k",
        label_size_px=11,
        label_line_height=1.15,
        label_letter_spacing_em=0.08,
        value_size_px=18,
        value_line_height=1.0,
        value_letter_spacing_em=0.0,
    )
    artifact_label_css = dashboard_ui_primitives.auxiliary_heading_css(
        selector=".artifact-label",
        color="#4b647d",
        size_px=11,
        letter_spacing_em=0.07,
        margin="0 0 6px 0",
    )
    atlas_secondary_typography_css = "\n\n".join(
        (
            dashboard_ui_primitives.card_title_typography_css(
                selector=".diagram-name",
                color="#12324c",
                size_px=14,
                line_height=1.25,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".diagram-owner",
                color="#516a83",
                size_px=12,
                line_height=1.35,
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".alert",
                color="#8a2d06",
                size_px=13,
                line_height=1.45,
            ),
            dashboard_ui_primitives.section_heading_css(
                selector=".section h3",
                color="#1f4868",
                size_px=14,
                line_height=1.2,
                letter_spacing_em=0.09,
                margin="0 0 9px 0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".component-card strong",
                color="#163f5d",
                size_px=13,
                line_height=1.35,
                letter_spacing_em=0.0,
                margin="0 0 4px 0",
            ),
            dashboard_ui_primitives.section_heading_css(
                selector=".context-tag",
                color="#36566f",
                size_px=10,
                line_height=1.0,
                letter_spacing_em=0.04,
                margin="0",
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".empty-note",
                color="#6c8298",
                size_px=12,
                line_height=1.35,
            ),
            dashboard_ui_primitives.caption_typography_css(
                selector=".artifact-list a",
                color="#0d4468",
                size_px=13,
                line_height=1.35,
            ),
        )
    )
    workstream_pill_button_css = dashboard_ui_primitives.surface_workstream_button_chip_css(
        selector=".artifact-list a.workstream-pill-link",
        border_color="#8cb8f4",
        background="#eaf3ff",
        color="#1f4795",
        hover_border_color="#68a0eb",
        hover_background="#deebff",
        hover_color="#1d4ed8",
    )
    tooltip_surface_css, tooltip_runtime_js = dashboard_ui_runtime_primitives.quick_tooltip_bundle(
        border_color="rgba(191, 219, 254, 0.48)",
    )

    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Atlas</title>
  __ODYLITH_BRAND_HEAD__
  <style>
    :root {
      --canvas-a: #f7f4ea;
      --canvas-b: #eef7ff;
      --canvas-c: #fefaf0;
      --surface: rgba(255, 255, 255, 0.82);
      --surface-strong: rgba(255, 255, 255, 0.95);
      --ink: #1f2937;
      --ink-soft: #4b5563;
      --accent: #0ea5a3;
      --accent-2: #0369a1;
      --danger: #b42318;
      --ok: #027a48;
      --warning: #b54708;
      --border: rgba(15, 23, 42, 0.12);
      --shadow: 0 18px 46px rgba(15, 23, 42, 0.10);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background:
        radial-gradient(1100px 660px at 8% -8%, #d7efe9 0%, transparent 55%),
        radial-gradient(1200px 740px at 110% 0%, #d9ebfb 0%, transparent 56%),
        linear-gradient(170deg, var(--canvas-a) 0%, var(--canvas-b) 52%, var(--canvas-c) 100%);
      min-height: 100vh;
    }
    __ODYLITH_ATLAS_PAGE_BODY__

    .layout {
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 16px;
      max-width: 1580px;
      margin: 0 auto;
      padding: 20px;
    }

    body.sidebar-collapsed .layout {
      grid-template-columns: 1fr;
    }

    body.sidebar-collapsed .sidebar {
      display: none;
    }

    .panel {
      border: 1px solid var(--border);
      border-radius: 22px;
      background: var(--surface);
      backdrop-filter: blur(10px);
      box-shadow: var(--shadow);
    }

    .sidebar {
      padding: 16px;
      position: sticky;
      top: 12px;
      height: calc(100vh - 24px);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .sidebar-header {
      position: relative;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      padding-right: 46px;
    }

    .sidebar-close {
      position: absolute;
      top: 0;
      right: 0;
      border: 1px solid rgba(3, 105, 161, 0.25);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.92);
      width: 34px;
      height: 34px;
      cursor: pointer;
      flex: 0 0 auto;
    }
    __ODYLITH_ATLAS_SIDEBAR_CLOSE_TYPOGRAPHY__

    .sidebar-close:hover {
      border-color: rgba(14, 165, 163, 0.65);
      color: #0b645f;
    }

    .eyebrow {
      margin: 0;
    }

    .title {
      margin: 4px 0 0 0;
      color: var(--ink);
    }

    .subtitle {
      margin: 8px 0 0 0;
      color: var(--ink-soft);
    }
    __ODYLITH_ATLAS_HEADER_TYPOGRAPHY__

    .search {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: var(--surface-strong);
      padding: 10px 12px;
      color: var(--ink);
    }

    .search:focus {
      outline: 2px solid rgba(14, 165, 163, 0.35);
      border-color: rgba(14, 165, 163, 0.45);
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
    }

    .chip {
      --chip-link-border: rgba(3, 105, 161, 0.18);
      --chip-link-bg: rgba(255, 255, 255, 0.88);
      --chip-link-text: #214968;
      --chip-link-border-hover: rgba(14, 165, 163, 0.4);
      --chip-link-bg-hover: rgba(240, 253, 250, 0.98);
      --chip-link-text-hover: #0b645f;
    }
    __ODYLITH_ATLAS_COMPACT_BUTTON_CONTRACT__

    .chip.active {
      --chip-link-bg: #0ea5a3;
      --chip-link-text: white;
      --chip-link-border: #0ea5a3;
      --chip-link-border-hover: #0b938f;
      --chip-link-bg-hover: #0b938f;
      --chip-link-text-hover: white;
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }

    .stat {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.78);
      padding: 8px 10px;
    }

    .stat p {
      margin: 0;
    }

    .stat .k {
      color: #12324c;
    }

    .stat .l {
      margin-top: 2px;
      color: #48627a;
    }
    __ODYLITH_ATLAS_STAT_TYPOGRAPHY__

    .diagram-list {
      list-style: none;
      margin: 0;
      padding: 0;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 9px;
    }

    .diagram-item {
      border: 1px solid rgba(3, 105, 161, 0.16);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.74);
      transition: transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
    }

    .diagram-item:hover {
      transform: translateY(-1px);
      border-color: rgba(14, 165, 163, 0.42);
      box-shadow: 0 10px 20px rgba(14, 116, 144, 0.08);
    }

    .diagram-item.active {
      border-color: rgba(14, 165, 163, 0.68);
      background: linear-gradient(170deg, rgba(229, 255, 252, 0.95), rgba(245, 250, 255, 0.92));
    }

    .diagram-btn {
      border: 0;
      padding: 10px;
      width: 100%;
      background: transparent;
      text-align: left;
      cursor: pointer;
      color: inherit;
    }

    .diagram-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      flex-wrap: wrap;
    }

    .tag {
      --label-bg: rgba(255, 255, 255, 0.9);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 0;
      border-radius: 0;
      padding: 4px 8px;
      white-space: nowrap;
      color: #334155;
      background: var(--label-bg);
    }

    .tag.stale {
      --label-bg: #b42318;
      color: white;
    }

    .diagram-name {
    }

    .diagram-owner {
      margin-top: 3px;
    }

    .main {
      padding: 16px;
      display: grid;
      gap: 13px;
      grid-template-rows: auto auto auto 1fr;
      min-height: calc(100vh - 40px);
    }

    .hero {
      display: grid;
      gap: 10px;
      min-width: 0;
    }

    __ODYLITH_ATLAS_DISPLAY_TITLE__

    .hero-copy {
      display: grid;
      gap: 10px;
      min-width: 0;
      width: 100%;
    }

    .diagram-facts {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 10px;
      min-width: 0;
    }

    .diagram-fact {
      display: grid;
      gap: 4px;
      align-content: start;
      min-width: 0;
      padding: 10px 12px;
      border: 1px solid rgba(148, 163, 184, 0.22);
      border-radius: 12px;
      background: linear-gradient(180deg, #ffffff, #f8fbff);
      box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
    }

    .diagram-fact.ok {
      border-color: rgba(2, 122, 72, 0.22);
      background: linear-gradient(180deg, #ffffff, #f3fbf6);
    }

    .diagram-fact.warn {
      border-color: rgba(181, 71, 8, 0.24);
      background: linear-gradient(180deg, #ffffff, #fff7ed);
    }

    .diagram-fact-label,
    .diagram-fact-value {
      min-width: 0;
    }

    .diagram-fact-value {
      overflow-wrap: anywhere;
    }

    __ODYLITH_ATLAS_FACT_TYPOGRAPHY__

    .meta-pill {
      --label-bg: rgba(255, 255, 255, 0.9);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 0;
      border-radius: 0;
      background: var(--label-bg);
      padding: 4px 8px;
      white-space: nowrap;
      color: #334155;
    }
    __ODYLITH_ATLAS_LABEL_TYPOGRAPHY__

    .meta-pill.ok {
      --label-bg: #027a48;
      color: white;
    }

    .meta-pill.warn {
      --label-bg: #b54708;
      color: white;
    }

    .source-links {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .source-links-wrap {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: flex-start;
      width: 100%;
      min-width: 0;
    }

    .source-link {
      text-decoration: none;
      --chip-link-border: rgba(3, 105, 161, 0.25);
      --chip-link-bg: rgba(255, 255, 255, 0.9);
      --chip-link-text: #0d4366;
      --chip-link-border-hover: rgba(14, 165, 163, 0.6);
      --chip-link-bg-hover: rgba(240, 253, 250, 0.98);
      --chip-link-text-hover: #0b645f;
    }

    .alert {
      border-radius: 12px;
      border: 1px solid rgba(181, 71, 8, 0.36);
      background: rgba(255, 244, 234, 0.95);
      padding: 10px 12px;
      display: none;
    }

    .alert.visible {
      display: block;
    }

    .viewer-shell {
      border-radius: 16px;
      border: 1px solid var(--border);
      background: #ffffff;
      overflow: hidden;
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 660px;
    }

    .viewer-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      padding: 9px 10px;
      border-bottom: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.92);
    }

    .viewer-toolbar-left {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }

    .viewer-toolbar-right {
      display: inline-flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .tool-btn {
      --chip-link-border: rgba(3, 105, 161, 0.24);
      --chip-link-bg: white;
      --chip-link-text: #144261;
      --chip-link-border-hover: rgba(14, 165, 163, 0.65);
      --chip-link-bg-hover: rgba(240, 253, 250, 0.98);
      --chip-link-text-hover: #0b645f;
    }

    .viewer-stage {
      position: relative;
      overflow: hidden;
      min-height: 560px;
      touch-action: none;
      cursor: grab;
      background: #ffffff;
    }

    .viewer-stage.dragging {
      cursor: grabbing;
    }

    .viewer-image {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) scale(1);
      transform-origin: 50% 50%;
      max-width: none;
      max-height: none;
      pointer-events: none;
      user-select: none;
    }

    .details-grid {
      display: grid;
      gap: 12px;
      grid-template-columns: 1.2fr 0.8fr;
    }

    .section {
      border: 1px solid var(--border);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.88);
      padding: 12px;
    }

    .section h3 {
    }

    .summary {
      margin: 0;
    }

    .component-list {
      margin-top: 11px;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
      gap: 10px;
    }

    .component-card {
      border: 1px solid rgba(3, 105, 161, 0.17);
      border-radius: 10px;
      padding: 9px 10px;
      background: rgba(255, 255, 255, 0.95);
    }

    .component-card strong {
      display: block;
    }

    .component-card p {
      margin: 0;
    }
    __ODYLITH_ATLAS_READABLE_COPY__

    __ODYLITH_ATLAS_OPERATOR_READOUT_LAYOUT__
    __ODYLITH_ATLAS_OPERATOR_READOUT_LABEL__
    __ODYLITH_ATLAS_OPERATOR_READOUT_COPY__
    __ODYLITH_ATLAS_OPERATOR_READOUT_META__

    .artifact-group {
      margin-bottom: 10px;
    }

    .artifact-group:last-child {
      margin-bottom: 0;
    }

    .artifact-label {
      margin: 0 0 6px 0;
    }
    __ODYLITH_ATLAS_ARTIFACT_LABEL_TYPOGRAPHY__

    .artifact-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .workstream-context-list {
      flex-direction: row;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .atlas-context-disclosure {
      border: 1px solid rgba(3, 105, 161, 0.16);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.94);
      overflow: hidden;
    }

    .atlas-context-disclosure > summary {
      cursor: pointer;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.96);
    }

    .atlas-context-disclosure > summary::-webkit-details-marker {
      display: none;
    }

    .atlas-context-disclosure > summary::before {
      content: "▸";
      color: #5d7389;
    }

    .atlas-context-disclosure[open] > summary::before {
      content: "▾";
    }

    .atlas-context-disclosure[open] > summary {
      border-bottom: 1px solid rgba(3, 105, 161, 0.16);
    }

    .atlas-context-disclosure .artifact-list {
      padding: 10px;
    }

    .context-link-item {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .context-tags {
      display: inline-flex;
      flex-wrap: wrap;
      gap: 5px;
    }

    .context-tag {
      display: inline-flex;
      align-items: center;
      --label-bg: rgba(255, 255, 255, 0.92);
      border: 0;
      background: var(--label-bg);
      color: #36566f;
      border-radius: 0;
      padding: 2px 7px;
    }

    .artifact-list a {
      text-decoration: none;
      border-bottom: 1px dotted rgba(13, 68, 104, 0.38);
      width: fit-content;
    }

    .artifact-list a:hover {
      color: #0a8a84;
      border-bottom-color: rgba(10, 138, 132, 0.62);
    }

    .artifact-list a.workstream-pill-link {
      border-bottom: 0;
      width: auto;
    }
    __ODYLITH_ATLAS_WORKSTREAM_PILL_TYPOGRAPHY__

    .artifact-list a.workstream-pill-link:hover {
      border-bottom: 0;
    }

    __ODYLITH_ATLAS_SECONDARY_TYPOGRAPHY__
    __ODYLITH_ATLAS_TOOLTIP_SURFACE__

    .empty-note {
      margin: 0;
    }

    @media (max-width: 1180px) {
      .layout {
        grid-template-columns: 1fr;
      }

      .sidebar {
        position: static;
        height: auto;
      }

      .details-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 760px) {
      .diagram-facts {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="layout">
    <aside id="sidebarPanel" class="panel sidebar">
      <div class="sidebar-header">
        <div>
          <p class="eyebrow">Live Architecture Maps</p>
          <h1 class="title">Atlas</h1>
          <p class="subtitle">Browse diagrams tied to components, workstreams, and freshness.</p>
        </div>
        <button id="sidebarClose" class="sidebar-close" type="button" aria-label="Close Atlas panel">×</button>
      </div>

      <input id="search" class="search" placeholder="Search title, summary, component, owner..." />

      <div>
        <p class="eyebrow">Kind Filter</p>
        <div id="kindFilters" class="chip-row"></div>
      </div>

      <div>
        <p class="eyebrow">Workstream Filter</p>
        <select id="workstreamFilter" class="search">
          <option value="all">All Workstreams</option>
        </select>
      </div>

      <div>
        <p class="eyebrow">Freshness</p>
        <div class="chip-row">
          <button class="chip active" data-freshness="all">All</button>
          <button class="chip" data-freshness="fresh">Fresh</button>
          <button class="chip" data-freshness="stale">Needs Update</button>
        </div>
      </div>

      <div class="stats">
        <div class="stat"><p class="k" id="statTotal">0</p><p class="l">Total</p></div>
        <div class="stat"><p class="k" id="statFresh">0</p><p class="l">Fresh</p></div>
        <div class="stat"><p class="k" id="statStale">0</p><p class="l">Needs Update</p></div>
      </div>

      <ul id="diagramList" class="diagram-list"></ul>
    </aside>

    <main class="panel main">
      <section class="hero">
        <div class="hero-copy">
          <h2 id="diagramTitle" class="hero-title"></h2>
          <div class="diagram-facts" role="list">
            <div class="diagram-fact" data-fact="diagram-id" role="listitem">
              <p class="diagram-fact-label">Diagram ID</p>
              <p id="diagramId" class="diagram-fact-value"></p>
            </div>
            <div class="diagram-fact" data-fact="kind" role="listitem">
              <p class="diagram-fact-label">Kind</p>
              <p id="diagramKind" class="diagram-fact-value"></p>
            </div>
            <div class="diagram-fact" data-fact="status" role="listitem">
              <p class="diagram-fact-label">Status</p>
              <p id="diagramStatus" class="diagram-fact-value"></p>
            </div>
            <div class="diagram-fact" data-fact="owner" role="listitem">
              <p class="diagram-fact-label">Owner</p>
              <p id="diagramOwner" class="diagram-fact-value"></p>
            </div>
            <div class="diagram-fact" data-fact="reviewed" role="listitem">
              <p class="diagram-fact-label">Reviewed</p>
              <p id="diagramReviewed" class="diagram-fact-value"></p>
            </div>
            <div id="diagramFreshnessCard" class="diagram-fact" data-fact="freshness" role="listitem">
              <p class="diagram-fact-label">Freshness</p>
              <p id="diagramFreshness" class="diagram-fact-value"></p>
            </div>
          </div>
        </div>
        <div class="source-links-wrap">
          <button id="sidebarToggle" class="tool-btn" type="button" aria-controls="sidebarPanel" aria-expanded="true">Hide Panel</button>
          <div id="sourceLinks" class="source-links"></div>
        </div>
      </section>

      <section id="staleAlert" class="alert"></section>

      <article class="section">
        <h3>Connected Workstream Context</h3>
        <div class="artifact-group">
          <p class="artifact-label">Owners</p>
          <ul id="ownerWorkstreamLinks" class="artifact-list workstream-context-list"></ul>
        </div>
        <div class="artifact-group">
          <p class="artifact-label">Active Touches</p>
          <ul id="activeWorkstreamLinks" class="artifact-list workstream-context-list"></ul>
        </div>
        <div id="historicalWorkstreamGroup" class="artifact-group" hidden>
          <p class="artifact-label">Historical References</p>
          <details id="historicalWorkstreamDisclosure" class="atlas-context-disclosure">
            <summary id="historicalWorkstreamSummary"></summary>
            <ul id="historicalWorkstreamLinks" class="artifact-list workstream-context-list"></ul>
          </details>
        </div>
      </article>

      <section class="viewer-shell">
        <div class="viewer-toolbar">
          <div class="viewer-toolbar-left">
            <span id="zoomReadout" class="meta-pill">Zoom 100%</span>
            <span class="meta-pill">Pinch: zoom</span>
            <span class="meta-pill">Drag: pan</span>
            <span class="meta-pill">Shortcuts: + - 0 f ↑ ↓</span>
          </div>
          <div class="viewer-toolbar-right">
            <button id="prevDiagram" class="tool-btn" type="button">Prev</button>
            <button id="nextDiagram" class="tool-btn" type="button">Next</button>
            <button id="zoomIn" class="tool-btn" type="button">Zoom +</button>
            <button id="zoomOut" class="tool-btn" type="button">Zoom -</button>
            <button id="fit" class="tool-btn" type="button">Fit</button>
            <button id="reset" class="tool-btn" type="button">Reset</button>
          </div>
        </div>
        <div id="viewerStage" class="viewer-stage">
          <img id="viewerImage" class="viewer-image" alt="diagram visualization" draggable="false" />
        </div>
      </section>

      <section class="details-grid">
        <article class="section">
          <h3>What This Diagram Constitutes</h3>
          <p id="diagramSummary" class="summary"></p>
          <div id="componentList" class="component-list"></div>
        </article>

        <article class="section">
          <h3>Linked Engineering Context</h3>
          <div class="artifact-group">
            <p class="artifact-label">Backlog</p>
            <ul id="backlogLinks" class="artifact-list"></ul>
          </div>
          <div class="artifact-group">
            <p class="artifact-label">Plans</p>
            <ul id="planLinks" class="artifact-list"></ul>
          </div>
          <div class="artifact-group">
            <p class="artifact-label">Developer Docs</p>
            <ul id="docLinks" class="artifact-list"></ul>
          </div>
          <div class="artifact-group">
            <p class="artifact-label">Implementation Code</p>
            <ul id="codeLinks" class="artifact-list"></ul>
          </div>
          <div class="artifact-group">
            <p class="artifact-label">Registry Components</p>
            <ul id="registryLinks" class="artifact-list"></ul>
          </div>
          <div class="artifact-group">
            <p class="artifact-label">Operator Surfaces</p>
            <ul id="surfaceLinks" class="artifact-list"></ul>
          </div>
        </article>
      </section>
    </main>
  </div>

  <script id="catalogData" type="application/json">__DATA__</script>
  <script>
    const payload = JSON.parse(document.getElementById("catalogData").textContent);
    const allDiagrams = payload.diagrams || [];
    const tooltipLookup = payload.tooltip_lookup && typeof payload.tooltip_lookup === "object"
      ? payload.tooltip_lookup
      : {};

    function sanitizeLookupObject(value) {
      const lookup = Object.create(null);
      if (!value || typeof value !== "object") return lookup;
      Object.entries(value).forEach(([keyRaw, valueRaw]) => {
        const key = String(keyRaw || "").trim();
        const text = String(valueRaw || "").trim();
        if (!key || !text) return;
        lookup[key] = text;
      });
      return lookup;
    }

    const workstreamTitleLookup = sanitizeLookupObject(tooltipLookup.workstream_titles);
    const diagramTitleLookup = sanitizeLookupObject(tooltipLookup.diagram_titles);

    const searchEl = document.getElementById("search");
    const kindFiltersEl = document.getElementById("kindFilters");
    const workstreamFilterEl = document.getElementById("workstreamFilter");
    const listEl = document.getElementById("diagramList");

    const statTotalEl = document.getElementById("statTotal");
    const statFreshEl = document.getElementById("statFresh");
    const statStaleEl = document.getElementById("statStale");

    const titleEl = document.getElementById("diagramTitle");
    const idEl = document.getElementById("diagramId");
    const kindEl = document.getElementById("diagramKind");
    const statusEl = document.getElementById("diagramStatus");
    const ownerEl = document.getElementById("diagramOwner");
    const reviewedEl = document.getElementById("diagramReviewed");
    const freshnessEl = document.getElementById("diagramFreshness");
    const freshnessCardEl = document.getElementById("diagramFreshnessCard");

    const sourceLinksEl = document.getElementById("sourceLinks");
    const sidebarToggleEl = document.getElementById("sidebarToggle");
    const sidebarCloseEl = document.getElementById("sidebarClose");
    const staleAlertEl = document.getElementById("staleAlert");
    const summaryEl = document.getElementById("diagramSummary");
    const componentListEl = document.getElementById("componentList");

    const backlogLinksEl = document.getElementById("backlogLinks");
    const planLinksEl = document.getElementById("planLinks");
    const docLinksEl = document.getElementById("docLinks");
    const codeLinksEl = document.getElementById("codeLinks");
    const registryLinksEl = document.getElementById("registryLinks");
    const surfaceLinksEl = document.getElementById("surfaceLinks");
    const ownerWorkstreamLinksEl = document.getElementById("ownerWorkstreamLinks");
    const activeWorkstreamLinksEl = document.getElementById("activeWorkstreamLinks");
    const historicalWorkstreamGroupEl = document.getElementById("historicalWorkstreamGroup");
    const historicalWorkstreamDisclosureEl = document.getElementById("historicalWorkstreamDisclosure");
    const historicalWorkstreamSummaryEl = document.getElementById("historicalWorkstreamSummary");
    const historicalWorkstreamLinksEl = document.getElementById("historicalWorkstreamLinks");

    const stageEl = document.getElementById("viewerStage");
    const imageEl = document.getElementById("viewerImage");
    const zoomReadoutEl = document.getElementById("zoomReadout");

    let activeList = allDiagrams.slice();
    let activeIndex = 0;
    let selectedDiagramId = "";
    let kindFilter = "all";
    let freshnessFilter = "all";
    let workstreamFilter = "all";
    let activeDiagram = null;

    let scale = 1;
    let offsetX = 0;
    let offsetY = 0;
    let dragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let panPointerId = null;
    let pinchState = null;
    const activePointers = new Map();

    const MIN_SCALE = 0.05;
    const MAX_SCALE = 5;
    const WORKSTREAM_ID_RE = /^B-\\d{3,}$/;
    const DIAGRAM_ID_RE = /^D-\\d{3,}$/;
    const DIAGRAM_COMPACT_RE = /^D(\\d{3,})$/;
    const SIDEBAR_PREF_KEY = "mermaid.sidebar.collapsed";
    const TOOLING_BASE_HREF = __ODYLITH_TOOLING_BASE_HREF__;
    __ODYLITH_ATLAS_QUICK_TOOLTIP_RUNTIME__

    function normalizeSearchToken(value) {
      return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "");
    }

    function escapeHtml(value) {
      return String(value || "").replace(/[&<>"']/g, (token) => {
        if (token === "&") return "&amp;";
        if (token === "<") return "&lt;";
        if (token === ">") return "&gt;";
        if (token === '"') return "&quot;";
        return "&#39;";
      });
    }

    function canonicalizeDiagramId(value) {
      let token = String(value || "").trim().toUpperCase();
      if (!token) return "";
      if (token.startsWith("DIAGRAM:")) {
        token = token.slice("DIAGRAM:".length).trim();
      }
      if (DIAGRAM_ID_RE.test(token)) {
        return token;
      }
      const compact = token.match(DIAGRAM_COMPACT_RE);
      if (compact) {
        return `D-${compact[1]}`;
      }
      return "";
    }

    function ownerWorkstreamsForDiagram(diagram) {
      const values = new Set();
      const listed = Array.isArray(diagram && diagram.related_workstreams)
        ? diagram.related_workstreams
        : [];
      listed.forEach((token) => {
        const workstream = String(token || "").trim();
        if (WORKSTREAM_ID_RE.test(workstream)) {
          values.add(workstream);
        }
      });
      return Array.from(values).sort();
    }

    function activeWorkstreamsForDiagram(diagram) {
      const values = new Set();
      const listed = Array.isArray(diagram && diagram.active_workstreams)
        ? diagram.active_workstreams
        : [];
      listed.forEach((token) => {
        const workstream = String(token || "").trim();
        if (WORKSTREAM_ID_RE.test(workstream)) {
          values.add(workstream);
        }
      });
      return Array.from(values).sort();
    }

    function historicalWorkstreamsForDiagram(diagram) {
      const values = new Set();
      const listed = Array.isArray(diagram && diagram.historical_workstreams)
        ? diagram.historical_workstreams
        : [];
      listed.forEach((token) => {
        const workstream = String(token || "").trim();
        if (WORKSTREAM_ID_RE.test(workstream)) {
          values.add(workstream);
        }
      });
      return Array.from(values).sort();
    }

    function relatedWorkstreamsForDiagram(diagram) {
      const values = new Set();
      ownerWorkstreamsForDiagram(diagram).forEach((workstream) => values.add(workstream));
      activeWorkstreamsForDiagram(diagram).forEach((workstream) => values.add(workstream));
      return Array.from(values).sort();
    }

    function allWorkstreamReferencesForDiagram(diagram) {
      const values = new Set();
      relatedWorkstreamsForDiagram(diagram).forEach((workstream) => values.add(workstream));
      historicalWorkstreamsForDiagram(diagram).forEach((workstream) => values.add(workstream));
      return Array.from(values).sort();
    }

    function diagramMatchesWorkstream(diagram, workstreamId) {
      const normalized = normalizeWorkstreamId(workstreamId);
      if (!normalized) return true;
      return relatedWorkstreamsForDiagram(diagram).includes(normalized);
    }

    function normalizeSelectedDiagramWorkstreamFilter() {
      const selectedToken = canonicalizeDiagramId(selectedDiagramId);
      if (!selectedToken || workstreamFilter === "all") {
        return;
      }
      const selectedDiagram = allDiagrams.find(
        (diagram) => canonicalizeDiagramId(diagram.diagram_id) === selectedToken
      );
      if (!selectedDiagram) {
        return;
      }
      if (diagramMatchesWorkstream(selectedDiagram, workstreamFilter)) {
        return;
      }
      workstreamFilter = "all";
      workstreamFilterEl.value = "all";
    }

    function setSidebarCollapsed(collapsed) {
      document.body.classList.toggle("sidebar-collapsed", collapsed);
      sidebarToggleEl.textContent = collapsed ? "Show Panel" : "Hide Panel";
      sidebarToggleEl.setAttribute("aria-expanded", String(!collapsed));
    }

    function currentAtlasNavigationState() {
      const rawWorkstream = workstreamFilter === "all" ? "" : String(workstreamFilter || "").trim();
      const workstream = WORKSTREAM_ID_RE.test(rawWorkstream) ? rawWorkstream : "";
      const diagram = canonicalizeDiagramId(activeDiagram && activeDiagram.diagram_id);
      return { workstream, diagram };
    }

    function syncAtlasNavigation(options = {}) {
      const state = currentAtlasNavigationState();
      const query = new URLSearchParams(window.location.search);
      query.delete("workstream");
      query.delete("diagram");
      if (state.workstream) query.set("workstream", state.workstream);
      if (state.diagram) query.set("diagram", state.diagram);

      const nextSearch = query.toString();
      const currentSearch = String(window.location.search || "").replace(/^\\?/, "");
      if (nextSearch !== currentSearch) {
        const suffix = nextSearch ? `?${nextSearch}` : "";
        window.history.replaceState(null, "", `${window.location.pathname}${suffix}`);
      }

      if (options.notifyParent === false) return;
      try {
        if (window.parent && window.parent !== window) {
          window.parent.postMessage(
            {
              type: "odylith-atlas-navigate",
              state: {
                tab: "atlas",
                workstream: state.workstream,
                diagram: state.diagram,
              },
            },
            "*",
          );
        }
      } catch (_error) {
        // Fall open: local URL remains canonical for direct Atlas browsing.
      }
    }

    function clamp(value, low, high) {
      return Math.min(high, Math.max(low, value));
    }

    function applyTransform() {
      imageEl.style.transform = `translate(calc(-50% + ${offsetX}px), calc(-50% + ${offsetY}px)) scale(${scale})`;
      zoomReadoutEl.textContent = `Zoom ${Math.round(scale * 100)}%`;
    }

    function resetView() {
      scale = 1;
      offsetX = 0;
      offsetY = 0;
      applyTransform();
    }

    function diagramDimensions(diagram) {
      const vbw = Number(diagram && diagram.svg_viewbox_width ? diagram.svg_viewbox_width : 0);
      const vbh = Number(diagram && diagram.svg_viewbox_height ? diagram.svg_viewbox_height : 0);
      if (Number.isFinite(vbw) && Number.isFinite(vbh) && vbw > 0 && vbh > 0) {
        return { width: vbw, height: vbh };
      }
      const iw = imageEl.naturalWidth || 0;
      const ih = imageEl.naturalHeight || 0;
      if (!iw || !ih) {
        return null;
      }
      return { width: iw, height: ih };
    }

    function applyImageBoxSizing(diagram) {
      const dims = diagramDimensions(diagram);
      if (!dims) {
        imageEl.style.width = "";
        imageEl.style.height = "";
        return;
      }
      // SVGs that declare percentage sizing report tiny intrinsic dimensions in
      // <img>. Keep the image box aligned with Atlas's viewBox-based fit math.
      imageEl.style.width = `${dims.width}px`;
      imageEl.style.height = `${dims.height}px`;
    }

    function computedFitScale(diagram) {
      const dims = diagramDimensions(diagram);
      if (!dims) {
        return null;
      }
      const sw = stageEl.clientWidth || 1;
      const sh = stageEl.clientHeight || 1;
      return Math.min(sw / dims.width, sh / dims.height);
    }

    function applyInitialView(diagram) {
      const dims = diagramDimensions(diagram);
      if (!dims) {
        resetView();
        return;
      }
      const rawFitScale = computedFitScale(diagram);
      if (rawFitScale === null) {
        resetView();
        return;
      }

      // Start near the full-bounds fit with a small safety margin so diagrams
      // feel snug on first paint without clipping at the edges.
      let initialFactor = 0.98;
      const MIN_INITIAL_FIT_FACTOR = 0.94;

      const rawOverrideFactor = Number(diagram && diagram.initial_view_fit_factor ? diagram.initial_view_fit_factor : 0);
      if (Number.isFinite(rawOverrideFactor) && rawOverrideFactor > 0) {
        initialFactor = clamp(rawOverrideFactor, MIN_INITIAL_FIT_FACTOR, initialFactor);
      }

      const target = rawFitScale * initialFactor;
      scale = clamp(target, MIN_SCALE, 1);
      offsetX = 0;
      offsetY = 0;
      applyTransform();
    }

    function fitView() {
      const rawFitScale = computedFitScale(activeDiagram);
      if (rawFitScale === null) {
        resetView();
        return;
      }
      scale = clamp(rawFitScale, MIN_SCALE, MAX_SCALE);
      offsetX = 0;
      offsetY = 0;
      applyTransform();
    }

    function zoomBy(factor, centerX, centerY) {
      zoomTo(scale * factor, centerX, centerY);
    }

    function zoomTo(targetScale, centerX, centerY) {
      const oldScale = scale;
      const newScale = clamp(targetScale, MIN_SCALE, MAX_SCALE);
      if (newScale === oldScale) {
        return;
      }
      const px = centerX - stageEl.clientWidth / 2;
      const py = centerY - stageEl.clientHeight / 2;
      offsetX = px - ((px - offsetX) / oldScale) * newScale;
      offsetY = py - ((py - offsetY) / oldScale) * newScale;
      scale = newScale;
      applyTransform();
    }

    function clearNode(node) {
      while (node.firstChild) {
        node.removeChild(node.firstChild);
      }
    }

    function renderLinkList(node, links) {
      clearNode(node);
      if (!links || !links.length) {
        return;
      }
      links.forEach((item) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = item.href;
        const target = String(item && item.target ? item.target : "_blank").trim() || "_blank";
        a.target = target;
        if (target === "_blank") {
          a.rel = "noreferrer";
        }
        a.textContent = item.file;
        li.appendChild(a);
        node.appendChild(li);
      });
    }

    function workstreamTitleForId(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) return "";
      const explicit = String(workstreamTitleLookup[token] || "").trim();
      if (explicit) return explicit;
      return token;
    }

    function diagramButtonTooltip(diagram) {
      const diagramId = canonicalizeDiagramId(diagram.diagram_id) || String(diagram.diagram_id || "").trim();
      const mapped = String(diagramTitleLookup[diagramId] || "").trim();
      if (mapped) return mapped;
      const title = String(diagram.title || "").trim();
      if (title) return title;
      return diagramId || "Diagram";
    }

    function normalizeWorkstreamId(value) {
      const token = String(value || "").trim();
      return WORKSTREAM_ID_RE.test(token) ? token : "";
    }

    function renderWorkstreamList(node, ids) {
      clearNode(node);
      if (!ids.length) {
        return;
      }

      ids.forEach((id) => {
        const li = document.createElement("li");
        li.className = "context-link-item";

        const a = document.createElement("a");
        a.className = "workstream-pill-link";
        a.href = `${TOOLING_BASE_HREF}?tab=radar&workstream=${encodeURIComponent(id)}`;
        a.textContent = id;
        const tooltip = workstreamTitleForId(id);
        a.setAttribute("data-tooltip", tooltip);
        a.setAttribute("aria-label", tooltip);
        a.target = "_top";
        li.appendChild(a);
        node.appendChild(li);
      });
    }

    function renderWorkstreamContext(diagram) {
      const ownerIds = ownerWorkstreamsForDiagram(diagram);
      const activeIds = activeWorkstreamsForDiagram(diagram);
      const historicalIds = historicalWorkstreamsForDiagram(diagram);

      renderWorkstreamList(ownerWorkstreamLinksEl, ownerIds);
      renderWorkstreamList(activeWorkstreamLinksEl, activeIds);

      if (!historicalIds.length) {
        historicalWorkstreamGroupEl.hidden = true;
        historicalWorkstreamDisclosureEl.open = false;
        historicalWorkstreamSummaryEl.textContent = "";
        clearNode(historicalWorkstreamLinksEl);
        return;
      }

      historicalWorkstreamGroupEl.hidden = false;
      historicalWorkstreamSummaryEl.textContent =
        historicalIds.length === 1
          ? "1 historical reference"
          : `${historicalIds.length} historical references`;
      renderWorkstreamList(historicalWorkstreamLinksEl, historicalIds);
    }

    function renderSourceLinks(diagram) {
      clearNode(sourceLinksEl);
      const sources = [
        { label: "Mermaid Source", href: diagram.source_mmd_href },
        { label: "SVG", href: diagram.source_svg_href },
      ];
      if (diagram.source_png_href) {
        sources.push({ label: "PNG", href: diagram.source_png_href });
      }
      sources.forEach((source) => {
        const a = document.createElement("a");
        a.className = "source-link";
        a.href = source.href;
        a.textContent = source.label;
        a.target = "_blank";
        a.rel = "noreferrer";
        sourceLinksEl.appendChild(a);
      });
    }

    function renderComponents(diagram) {
      clearNode(componentListEl);
      (diagram.components || []).forEach((component) => {
        const card = document.createElement("article");
        card.className = "component-card";

        const heading = document.createElement("strong");
        heading.textContent = component.name;

        const body = document.createElement("p");
        body.textContent = component.description;

        card.appendChild(heading);
        card.appendChild(body);
        componentListEl.appendChild(card);
      });
    }

    function renderAlert(diagram) {
      if (diagram.freshness === "stale" && (diagram.stale_reasons || []).length) {
        staleAlertEl.classList.add("visible");
        staleAlertEl.innerHTML = `<strong>Update Required:</strong> ${diagram.stale_reasons.join(" ")}`;
      } else {
        staleAlertEl.classList.remove("visible");
        staleAlertEl.textContent = "";
      }
    }

    function clearActiveDiagram() {
      activeDiagram = null;
      titleEl.textContent = "";
      idEl.textContent = "";
      kindEl.textContent = "";
      statusEl.textContent = "";
      ownerEl.textContent = "";
      reviewedEl.textContent = "";
      freshnessEl.textContent = "";
      freshnessCardEl?.classList.remove("ok", "warn");
      summaryEl.textContent = "";
      clearNode(sourceLinksEl);
      clearNode(componentListEl);
      clearNode(backlogLinksEl);
      clearNode(planLinksEl);
      clearNode(docLinksEl);
      clearNode(codeLinksEl);
      clearNode(registryLinksEl);
      clearNode(surfaceLinksEl);
      clearNode(ownerWorkstreamLinksEl);
      clearNode(activeWorkstreamLinksEl);
      clearNode(historicalWorkstreamLinksEl);
      historicalWorkstreamGroupEl.hidden = true;
      historicalWorkstreamDisclosureEl.open = false;
      historicalWorkstreamSummaryEl.textContent = "";
      staleAlertEl.classList.remove("visible");
      staleAlertEl.textContent = "";
      imageEl.removeAttribute("src");
      imageEl.dataset.fallbackApplied = "";
    }

    function applyMeta(diagram) {
      activeDiagram = diagram;
      titleEl.textContent = diagram.title;
      idEl.textContent = diagram.diagram_id;
      kindEl.textContent = diagram.kind;
      statusEl.textContent = diagram.status;
      ownerEl.textContent = diagram.owner;
      reviewedEl.textContent = diagram.last_reviewed_utc;
      freshnessEl.textContent = diagram.freshness === "stale" ? "Needs Update" : "Fresh";
      freshnessCardEl?.classList.toggle("warn", diagram.freshness === "stale");
      freshnessCardEl?.classList.toggle("ok", diagram.freshness !== "stale");

      summaryEl.textContent = diagram.summary;

      imageEl.onload = () => applyInitialView(diagram);
      imageEl.onerror = () => {
        const fallback = String(diagram.source_png_href || "").trim();
        if (!fallback) return;
        if (imageEl.dataset.fallbackApplied === "1") return;
        imageEl.dataset.fallbackApplied = "1";
        imageEl.src = fallback;
      };
      imageEl.dataset.fallbackApplied = "";
      applyImageBoxSizing(diagram);
      imageEl.src = diagram.source_svg_href;

      renderSourceLinks(diagram);
      renderComponents(diagram);
      renderAlert(diagram);

      renderLinkList(backlogLinksEl, diagram.related_backlog);
      renderLinkList(planLinksEl, diagram.related_plans);
      renderLinkList(docLinksEl, diagram.related_docs);
      renderLinkList(codeLinksEl, diagram.related_code);
      renderLinkList(registryLinksEl, diagram.related_registry);
      renderLinkList(surfaceLinksEl, diagram.related_surfaces);
      renderWorkstreamContext(diagram);
    }

    function setActive(index) {
      if (!activeList.length) {
        selectedDiagramId = "";
        clearActiveDiagram();
        syncAtlasNavigation();
        return;
      }
      activeIndex = clamp(index, 0, activeList.length - 1);
      const diagram = activeList[activeIndex];
      selectedDiagramId = canonicalizeDiagramId(diagram.diagram_id) || String(diagram.diagram_id || "").trim();
      applyMeta(diagram);

      const allItems = listEl.querySelectorAll(".diagram-item");
      allItems.forEach((node, nodeIndex) => {
        node.classList.toggle("active", nodeIndex === activeIndex);
      });
      syncAtlasNavigation();
    }

    function updateStats(sourceList) {
      const total = sourceList.length;
      let fresh = 0;
      let stale = 0;
      sourceList.forEach((item) => {
        if (item.freshness === "stale") {
          stale += 1;
        } else {
          fresh += 1;
        }
      });
      statTotalEl.textContent = String(total);
      statFreshEl.textContent = String(fresh);
      statStaleEl.textContent = String(stale);
    }

    function renderList() {
      clearNode(listEl);
      if (!activeList.length) {
        selectedDiagramId = "";
        clearActiveDiagram();
        syncAtlasNavigation();
        return;
      }

      activeList.forEach((diagram, idx) => {
        const li = document.createElement("li");
        li.className = "diagram-item";

        const button = document.createElement("button");
        button.className = "diagram-btn";
        button.type = "button";
        button.setAttribute("data-diagram", diagram.diagram_id);
        const tooltip = diagramButtonTooltip(diagram);
        button.setAttribute("data-tooltip", tooltip);
        button.setAttribute("aria-label", tooltip);

        const freshnessTag = diagram.freshness === "stale" ? '<span class="tag stale">Needs Update</span>' : '<span class="tag">Fresh</span>';
        button.innerHTML = `
          <div class="diagram-meta">
            <span class="tag">${diagram.diagram_id} · ${diagram.kind}</span>
            ${freshnessTag}
          </div>
          <div class="diagram-name">${diagram.title}</div>
          <div class="diagram-owner">${diagram.owner}</div>
        `;

        button.addEventListener("click", () => setActive(idx));
        li.appendChild(button);
        listEl.appendChild(li);
      });

      setActive(Math.min(activeIndex, activeList.length - 1));
    }

    function buildKindFilters() {
      clearNode(kindFiltersEl);
      const kinds = [...new Set(allDiagrams.map((item) => item.kind))].sort();
      const all = ["all", ...kinds];
      all.forEach((kindToken) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip" + (kindToken === kindFilter ? " active" : "");
        chip.textContent = kindToken;
        chip.addEventListener("click", () => {
          kindFilter = kindToken;
          buildKindFilters();
          applyFilters();
        });
        kindFiltersEl.appendChild(chip);
      });
    }

    function buildWorkstreamFilter() {
      const values = new Set();
      allDiagrams.forEach((diagram) => {
        relatedWorkstreamsForDiagram(diagram).forEach((id) => {
          if (id) values.add(id);
        });
      });
      const options = ["all", ...Array.from(values).sort()];
      clearNode(workstreamFilterEl);
      options.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value === "all" ? "All Workstreams" : value;
        if (value === workstreamFilter) {
          option.selected = true;
        }
        workstreamFilterEl.appendChild(option);
      });
    }

    function applyFilters() {
      const needle = String(searchEl.value || "").trim().toLowerCase();
      const normalizedNeedle = normalizeSearchToken(needle);
      normalizeSelectedDiagramWorkstreamFilter();
      const selectedToken = canonicalizeDiagramId(selectedDiagramId);
      activeList = allDiagrams.filter((diagram) => {
        const diagramToken = canonicalizeDiagramId(diagram.diagram_id);
        if (kindFilter !== "all" && diagram.kind !== kindFilter) {
          return false;
        }
        if (freshnessFilter !== "all" && diagram.freshness !== freshnessFilter) {
          return false;
        }
        if (workstreamFilter !== "all") {
          const related = relatedWorkstreamsForDiagram(diagram);
          if (!related.includes(workstreamFilter)) {
            return false;
          }
        }

        if (!needle) {
          return true;
        }

        const textParts = [
          diagram.diagram_id,
          diagramToken,
          diagram.title,
          diagram.summary,
          diagram.kind,
          diagram.owner,
          diagram.status,
          diagram.last_reviewed_utc,
          ...allWorkstreamReferencesForDiagram(diagram),
          ...(diagram.components || []).map((item) => `${item.name} ${item.description}`),
        ];
        const text = textParts.join(" ").toLowerCase();
        if (text.includes(needle)) {
          return true;
        }
        if (!normalizedNeedle) {
          return false;
        }
        const normalizedText = normalizeSearchToken(textParts.join(" "));
        return normalizedText.includes(normalizedNeedle);
      });

      if (!activeList.length && selectedToken) {
        const fallback = allDiagrams.find(
          (diagram) => canonicalizeDiagramId(diagram.diagram_id) === selectedToken
        );
        if (fallback) {
          if (workstreamFilter !== "all" && !diagramMatchesWorkstream(fallback, workstreamFilter)) {
            workstreamFilter = "all";
            workstreamFilterEl.value = "all";
            applyFilters();
            return;
          }
          activeList = [fallback];
        }
      }

      const selectedIndex = selectedToken
        ? activeList.findIndex((diagram) => canonicalizeDiagramId(diagram.diagram_id) === selectedToken)
        : -1;
      activeIndex = selectedIndex >= 0 ? selectedIndex : 0;
      updateStats(activeList);
      renderList();
    }

    function moveSelection(delta) {
      if (!activeList.length) {
        return;
      }
      setActive(clamp(activeIndex + delta, 0, activeList.length - 1));
    }

    function pointerRecord(event) {
      return {
        x: event.clientX,
        y: event.clientY,
        type: event.pointerType,
      };
    }

    function touchPointers() {
      return [...activePointers.values()].filter((item) => item.type === "touch");
    }

    function distance(a, b) {
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      return Math.sqrt((dx * dx) + (dy * dy));
    }

    function center(a, b) {
      return {
        x: (a.x + b.x) / 2,
        y: (a.y + b.y) / 2,
      };
    }

    function beginPan(event) {
      dragging = true;
      panPointerId = event.pointerId;
      dragStartX = event.clientX - offsetX;
      dragStartY = event.clientY - offsetY;
      stageEl.classList.add("dragging");
    }

    function endPan() {
      dragging = false;
      panPointerId = null;
      stageEl.classList.remove("dragging");
    }

    document.querySelectorAll("[data-freshness]").forEach((chip) => {
      chip.addEventListener("click", () => {
        freshnessFilter = chip.getAttribute("data-freshness") || "all";
        document.querySelectorAll("[data-freshness]").forEach((node) => node.classList.remove("active"));
        chip.classList.add("active");
        applyFilters();
      });
    });

    sidebarToggleEl.addEventListener("click", () => {
      const next = !document.body.classList.contains("sidebar-collapsed");
      setSidebarCollapsed(next);
      try {
        localStorage.setItem(SIDEBAR_PREF_KEY, next ? "1" : "0");
      } catch (err) {
        // no-op
      }
    });

    sidebarCloseEl.addEventListener("click", () => {
      setSidebarCollapsed(true);
      try {
        localStorage.setItem(SIDEBAR_PREF_KEY, "1");
      } catch (err) {
        // no-op
      }
    });

    searchEl.addEventListener("input", applyFilters);
    workstreamFilterEl.addEventListener("change", () => {
      workstreamFilter = workstreamFilterEl.value || "all";
      applyFilters();
      syncAtlasNavigation();
    });

    document.getElementById("zoomIn").addEventListener("click", () => {
      zoomBy(1.14, stageEl.clientWidth / 2, stageEl.clientHeight / 2);
    });

    document.getElementById("zoomOut").addEventListener("click", () => {
      zoomBy(0.88, stageEl.clientWidth / 2, stageEl.clientHeight / 2);
    });

    document.getElementById("fit").addEventListener("click", fitView);
    document.getElementById("reset").addEventListener("click", resetView);
    document.getElementById("prevDiagram").addEventListener("click", () => moveSelection(-1));
    document.getElementById("nextDiagram").addEventListener("click", () => moveSelection(1));

    stageEl.addEventListener("pointerdown", (event) => {
      activePointers.set(event.pointerId, pointerRecord(event));
      stageEl.setPointerCapture(event.pointerId);

      const touches = touchPointers();
      if (touches.length >= 2) {
        endPan();
        const a = touches[0];
        const b = touches[1];
        pinchState = {
          startDistance: Math.max(1, distance(a, b)),
          startScale: scale,
        };
        return;
      }

      if (!pinchState) {
        beginPan(event);
      }
    });

    stageEl.addEventListener("pointermove", (event) => {
      if (activePointers.has(event.pointerId)) {
        activePointers.set(event.pointerId, pointerRecord(event));
      }

      const touches = touchPointers();
      if (touches.length >= 2) {
        if (!pinchState) {
          const a = touches[0];
          const b = touches[1];
          pinchState = {
            startDistance: Math.max(1, distance(a, b)),
            startScale: scale,
          };
        }
        const a = touches[0];
        const b = touches[1];
        const rect = stageEl.getBoundingClientRect();
        const midpoint = center(a, b);
        const ratio = distance(a, b) / Math.max(1, pinchState.startDistance);
        zoomTo(pinchState.startScale * ratio, midpoint.x - rect.left, midpoint.y - rect.top);
        return;
      }

      if (pinchState) {
        pinchState = null;
      }

      if (dragging && event.pointerId === panPointerId) {
        offsetX = event.clientX - dragStartX;
        offsetY = event.clientY - dragStartY;
        applyTransform();
      }
    });

    function stopPointer(event) {
      activePointers.delete(event.pointerId);
      if (event.pointerId === panPointerId) {
        endPan();
      }

      if (touchPointers().length < 2) {
        pinchState = null;
      }

      try {
        stageEl.releasePointerCapture(event.pointerId);
      } catch (err) {
        // no-op
      }
    }

    stageEl.addEventListener("pointerup", stopPointer);
    stageEl.addEventListener("pointercancel", stopPointer);

    // Desktop trackpad pinch commonly arrives as wheel+ctrlKey.
    // Accept only that path; plain wheel scrolling must not zoom.
    stageEl.addEventListener("wheel", (event) => {
      if (!event.ctrlKey) {
        return;
      }
      event.preventDefault();
      const rect = stageEl.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      zoomBy(event.deltaY < 0 ? 1.08 : 0.92, x, y);
    }, { passive: false });

    window.addEventListener("keydown", (event) => {
      const key = event.key;
      if (key === "+" || key === "=") {
        zoomBy(1.14, stageEl.clientWidth / 2, stageEl.clientHeight / 2);
      } else if (key === "-") {
        zoomBy(0.88, stageEl.clientWidth / 2, stageEl.clientHeight / 2);
      } else if (key === "0") {
        resetView();
      } else if (key.toLowerCase() === "f") {
        fitView();
      } else if (key === "ArrowUp") {
        moveSelection(-1);
      } else if (key === "ArrowDown") {
        moveSelection(1);
      }
    });

    window.addEventListener("resize", () => fitView());

    let sidebarCollapsed = false;
    try {
      sidebarCollapsed = localStorage.getItem(SIDEBAR_PREF_KEY) === "1";
    } catch (err) {
      sidebarCollapsed = false;
    }
    setSidebarCollapsed(sidebarCollapsed);

    const params = new URLSearchParams(window.location.search);
    const paramWorkstream = (params.get("workstream") || "").trim();
    const paramDiagram = (params.get("diagram") || "").trim();
    if (WORKSTREAM_ID_RE.test(paramWorkstream)) {
      workstreamFilter = paramWorkstream;
    }
    const normalizedParamDiagram = canonicalizeDiagramId(paramDiagram);
    if (normalizedParamDiagram) {
      selectedDiagramId = normalizedParamDiagram;
    } else if (paramDiagram) {
      selectedDiagramId = paramDiagram;
    }

    buildKindFilters();
    buildWorkstreamFilter();
    applyFilters();
  </script>
</body>
</html>
"""

    return (
        template.replace("__ODYLITH_BRAND_HEAD__", brand_head_html.strip())
        .replace("__ODYLITH_ATLAS_PAGE_BODY__", page_body_css)
        .replace("__ODYLITH_ATLAS_HEADER_TYPOGRAPHY__", atlas_header_css)
        .replace("__ODYLITH_ATLAS_COMPACT_BUTTON_CONTRACT__", atlas_compact_button_css)
        .replace("__ODYLITH_ATLAS_SIDEBAR_CLOSE_TYPOGRAPHY__", sidebar_close_button_css)
        .replace("__ODYLITH_ATLAS_LABEL_TYPOGRAPHY__", atlas_label_css)
        .replace("__ODYLITH_ATLAS_FACT_TYPOGRAPHY__", atlas_fact_typography_css)
        .replace("__ODYLITH_ATLAS_STAT_TYPOGRAPHY__", atlas_stat_typography_css)
        .replace("__ODYLITH_ATLAS_ARTIFACT_LABEL_TYPOGRAPHY__", artifact_label_css)
        .replace("__ODYLITH_ATLAS_SECONDARY_TYPOGRAPHY__", atlas_secondary_typography_css)
        .replace("__ODYLITH_ATLAS_WORKSTREAM_PILL_TYPOGRAPHY__", workstream_pill_button_css)
        .replace("__ODYLITH_ATLAS_TOOLTIP_SURFACE__", tooltip_surface_css)
        .replace("__ODYLITH_ATLAS_QUICK_TOOLTIP_RUNTIME__", tooltip_runtime_js)
        .replace("__ODYLITH_ATLAS_DISPLAY_TITLE__", display_title_css)
        .replace("__ODYLITH_ATLAS_OPERATOR_READOUT_LAYOUT__", "")
        .replace("__ODYLITH_ATLAS_OPERATOR_READOUT_LABEL__", "")
        .replace("__ODYLITH_ATLAS_OPERATOR_READOUT_COPY__", "")
        .replace("__ODYLITH_ATLAS_OPERATOR_READOUT_META__", "")
        .replace("__ODYLITH_ATLAS_OPERATOR_READOUT_RUNTIME_JS__", "")
        .replace("__ODYLITH_ATLAS_READABLE_COPY__", readable_copy_css)
        .replace("__ODYLITH_TOOLING_BASE_HREF__", json.dumps(str(tooling_base_href or "").strip()))
        .replace("__DATA__", payload_json)
    )


def _selected_freshness_gate(
    *,
    diagrams: Sequence[Mapping[str, Any]],
    selected_ids: Sequence[str],
) -> dict[str, int] | None:
    normalized = {
        str(token).strip().upper()
        for token in selected_ids
        if str(token).strip()
    }
    if not normalized:
        return None
    selected_rows = [
        row
        for row in diagrams
        if str(row.get("diagram_id", "")).strip().upper() in normalized
    ]
    if not selected_rows:
        return {"selected": 0, "stale": 0}
    stale_count = sum(1 for row in selected_rows if str(row.get("freshness", "")).strip() == "stale")
    return {"selected": len(selected_rows), "stale": stale_count}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    catalog_path = _resolve(repo_root, args.catalog)
    output_path = _resolve(repo_root, args.output)
    traceability_graph_path = _resolve(repo_root, args.traceability_graph)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_paths = dashboard_surface_bundle.build_paths(output_path=output_path, asset_prefix="mermaid")
    output_paths = [
        output_path,
        bundle_paths.payload_js_path,
        bundle_paths.control_js_path,
    ]
    if source_bundle_mirror.source_bundle_root(repo_root=repo_root).is_dir():
        for live_path in tuple(output_paths):
            output_paths.append(source_bundle_mirror.bundle_mirror_path(repo_root=repo_root, live_path=live_path))
    input_fingerprint = ""
    if not args.check_only and not args.diagram_id:
        skip_rebuild, input_fingerprint, cached_metadata = generated_refresh_guard.should_skip_rebuild(
            repo_root=repo_root,
            namespace=_ATLAS_RENDER_GUARD_NAMESPACE,
            key=_ATLAS_RENDER_GUARD_KEY,
            watched_paths=(
                "odylith/atlas/source",
                "odylith/radar/traceability-graph.v1.json",
                "odylith/runtime/delivery_intelligence.v4.json",
                "odylith/registry/source",
                "src/odylith/runtime/surfaces",
                "src/odylith/runtime/governance",
                "src/odylith/runtime/common",
            ),
            output_paths=tuple(output_paths),
            extra={
                "max_review_age_days": int(args.max_review_age_days),
                "runtime_mode": str(args.runtime_mode),
            },
        )
        if skip_rebuild:
            print("mermaid catalog render passed")
            print(f"- output: {output_path}")
            if cached_metadata:
                print(f"- diagrams: {int(cached_metadata.get('diagram_count', 0) or 0)}")
                print(f"- fresh: {int(cached_metadata.get('fresh_count', 0) or 0)}")
                print(f"- stale: {int(cached_metadata.get('stale_count', 0) or 0)}")
                stale_count = int(cached_metadata.get("stale_count", 0) or 0)
            else:
                stale_count = 0
            if args.fail_on_stale and stale_count > 0:
                print("mermaid catalog freshness FAILED")
                print("- at least one diagram is stale; update diagram source/metadata and rerun")
                return 3
            return 0
    component_index = _load_component_index(repo_root=repo_root)

    diagrams, errors, stats = _load_catalog(
        repo_root=repo_root,
        catalog_path=catalog_path,
        output_path=output_path,
        max_review_age_days=args.max_review_age_days,
        component_index=component_index,
    )

    if errors:
        print("mermaid catalog render FAILED")
        for err in errors:
            print(f"- {err}")
        return 2

    traceability_graph: dict[str, Any] = {}
    if traceability_graph_path.is_file():
        try:
            traceability_graph = json.loads(traceability_graph_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"invalid json: {traceability_graph_path}")
    if errors:
        print("mermaid catalog render FAILED")
        for err in errors:
            print(f"- {err}")
        return 2

    delivery_intelligence = _load_delivery_surface_payload(
        repo_root=repo_root,
        surface="atlas",
    )

    _attach_diagram_workstream_relationships(
        diagrams=diagrams,
        traceability_graph=traceability_graph,
        delivery_intelligence=delivery_intelligence,
    )

    tooltip_lookup = traceability_ui_lookup.build_tooltip_lookup_payload(
        entries=_workstream_title_entries(
            repo_root=repo_root,
            diagrams=diagrams,
            delivery_intelligence=delivery_intelligence,
        ),
        diagrams=diagrams,
        components=_component_catalog_rows(component_index=component_index),
        traceability_graph=traceability_graph,
    )

    html_payload = {
        "max_review_age_days": args.max_review_age_days,
        "stats": stats,
        "diagrams": diagrams,
        "tooltip_lookup": tooltip_lookup,
    }
    generated_utc = stable_generated_utc.resolve_for_js_assignment_file(
        output_path=bundle_paths.payload_js_path,
        global_name="__ODYLITH_MERMAID_DATA__",
        payload=html_payload,
    )
    brand_head_html = brand_assets.render_brand_head_html(repo_root=repo_root, output_path=output_path)

    if not args.check_only:
        tooling_base_href = _as_href(output_path, _resolve(repo_root, "odylith/index.html"))
        html = _render_html(
            diagrams=diagrams,
            stats=stats,
            max_review_age_days=args.max_review_age_days,
            tooltip_lookup=tooltip_lookup,
            generated_utc=generated_utc,
            brand_head_html=brand_head_html,
            tooling_base_href=tooling_base_href,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html_payload["generated_utc"] = generated_utc
        bundled_html, payload_js, control_js = dashboard_surface_bundle.externalize_surface_bundle(
            html_text=html,
            payload=html_payload,
            paths=bundle_paths,
            spec=dashboard_surface_bundle.standard_surface_bundle_spec(
                asset_prefix="mermaid",
                payload_global_name="__ODYLITH_MERMAID_DATA__",
                embedded_json_script_id="catalogData",
                bootstrap_binding_name="payload",
                shell_tab="atlas",
                shell_frame_id="frame-atlas",
                query_passthrough=(
                    ("workstream", ("workstream",)),
                    ("diagram", ("diagram",)),
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
        source_bundle_mirror.sync_live_paths(
            repo_root=repo_root,
            live_paths=(output_path, bundle_paths.payload_js_path, bundle_paths.control_js_path),
        )
        generated_surface_cleanup.remove_legacy_generated_paths(
            active_outputs=(output_path,),
            legacy_paths=((repo_root / "mermaid" / "index.html").resolve(),),
        )
        if input_fingerprint:
            generated_refresh_guard.record_rebuild(
                repo_root=repo_root,
                namespace=_ATLAS_RENDER_GUARD_NAMESPACE,
                key=_ATLAS_RENDER_GUARD_KEY,
                input_fingerprint=input_fingerprint,
                output_paths=tuple(output_paths),
                metadata={
                    "diagram_count": len(diagrams),
                    "fresh_count": int(stats["fresh"]),
                    "stale_count": int(stats["stale"]),
                },
            )

    print("mermaid catalog render passed")
    print(f"- output: {output_path}")
    print(f"- diagrams: {len(diagrams)}")
    print(f"- fresh: {stats['fresh']}")
    print(f"- stale: {stats['stale']}")
    selected_gate = _selected_freshness_gate(diagrams=diagrams, selected_ids=args.diagram_id)
    if selected_gate is not None:
        print(f"- selected_diagrams: {selected_gate['selected']}")
        print(f"- selected_stale: {selected_gate['stale']}")
        if selected_gate["selected"] == 0:
            print("mermaid catalog render FAILED")
            print("- no selected diagram ids resolved in the catalog")
            return 2

    stale_gate_count = selected_gate["stale"] if selected_gate is not None else int(stats["stale"])
    if args.fail_on_stale and stale_gate_count > 0:
        print("mermaid catalog freshness FAILED")
        if selected_gate is not None:
            print("- at least one selected diagram is stale; update diagram source/metadata and rerun")
        else:
            print("- at least one diagram is stale; update diagram source/metadata and rerun")
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

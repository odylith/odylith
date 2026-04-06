"""Shared workstream inference helpers for dashboard and promotion tooling.

This module centralizes path normalization + workstream mapping invariants so
Compass, Radar/Atlas renderers, and phase-promotion logic cannot drift.

Key contracts:
- Generic/global coordination artifacts are never used as strong workstream
  evidence (for example generated dashboard shells and runtime snapshots).
- Source paths can still match nested references (prefix match semantics).
- Absolute paths are normalized into repository-relative tokens whenever
  possible for deterministic matching across processes.
"""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from odylith.runtime.common.consumer_profile import canonical_truth_token
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


GLOBAL_COORDINATION_EXACT_PATHS: set[str] = {
    "odylith/technical-plans/index.md",
    "odylith/casebook/bugs/index.md",
    "odylith/radar/source/index.md",
    "mermaid/index.html",
    "odylith/compass/compass.html",
    "odylith/compass/compass-payload.v1.js",
    "odylith/compass/compass-app.v1.js",
    "odylith/registry/registry.html",
    "odylith/registry/registry-payload.v1.js",
    "odylith/registry/registry-app.v1.js",
    "odylith/casebook/casebook.html",
    "odylith/casebook/casebook-payload.v1.js",
    "odylith/casebook/casebook-app.v1.js",
    "odylith/index.html",
    "odylith/tooling-payload.v1.js",
    "odylith/tooling-app.v1.js",
    "odylith/radar/radar.html",
    "odylith/radar/backlog-payload.v1.js",
    "odylith/radar/backlog-app.v1.js",
    "odylith/radar/standalone-pages.v1.js",
    "odylith/radar/traceability-graph.v1.json",
    "odylith/radar/traceability-autofix-report.v1.json",
    "odylith/atlas/atlas.html",
    "odylith/atlas/mermaid-payload.v1.js",
    "odylith/atlas/mermaid-app.v1.js",
}
GLOBAL_COORDINATION_PREFIXES: tuple[str, ...] = (
    "odylith/radar/source/ui/",
    "odylith/radar/backlog-detail-shard-",
    "odylith/radar/backlog-document-shard-",
    "odylith/casebook/",
    "odylith/compass/runtime/",
    "odylith/registry/registry-detail-shard-",
    "odylith/runtime/",
    "odylith/atlas/source/catalog/",
)


def normalize_repo_token(token: str, *, repo_root: Path | None = None) -> str:
    """Return a normalized repo-style path token.

    Relative paths are returned as-is (without leading ``./``). Absolute paths
    are converted to repo-relative paths when ``repo_root`` is supplied and the
    path is inside the repository tree.
    """

    raw = str(token or "").strip()
    resolved_repo_root: Path | None = None
    if repo_root is not None:
        resolved_repo_root = repo_root.resolve()
    else:
        default_root_token = _default_repo_root_token_for_cwd(os.getcwd())
        if default_root_token:
            resolved_repo_root = Path(default_root_token)
    root_token = str(resolved_repo_root) if resolved_repo_root is not None else ""
    return _normalize_repo_token_cached(raw, root_token)


@lru_cache(maxsize=32)
def _default_repo_root_token_for_cwd(cwd_token: str) -> str:
    token = str(cwd_token or "").strip()
    if not token:
        return ""
    cwd = Path(token).resolve()
    if (cwd / "AGENTS.md").is_file() and ((cwd / ".odylith").exists() or (cwd / "odylith").exists() or (cwd / "src" / "odylith").is_dir()):
        return str(cwd)
    return ""


@lru_cache(maxsize=262144)
def _normalize_repo_token_cached(raw: str, repo_root_token: str) -> str:
    token = str(raw or "").strip()
    if not token:
        return ""
    if token.startswith("./"):
        token = token[2:]
    if not token:
        return ""
    if not os.path.isabs(token):
        return canonical_truth_token(
            _resolve_closed_plan_token(token.replace("\\", "/"), repo_root_token=repo_root_token),
            repo_root=Path(repo_root_token) if repo_root_token else None,
        )

    resolved = Path(token).resolve()
    if repo_root_token:
        repo_root = Path(repo_root_token)
        try:
            return canonical_truth_token(
                _resolve_closed_plan_token(resolved.relative_to(repo_root).as_posix(), repo_root_token=repo_root_token),
                repo_root=repo_root,
            )
        except ValueError:
            return resolved.as_posix()
    return resolved.as_posix()


def _resolve_closed_plan_token(token: str, *, repo_root_token: str) -> str:
    normalized = str(token or "").strip().replace("\\", "/").strip("/")
    if not normalized or not normalized.startswith("odylith/technical-plans/in-progress/") or not normalized.endswith(".md") or not repo_root_token:
        return normalized
    repo_root = Path(repo_root_token)
    if (repo_root / normalized).is_file():
        return normalized
    done_root = repo_root / "plan" / "done"
    if not done_root.is_dir():
        return normalized
    matches = sorted(
        path.relative_to(repo_root).as_posix()
        for path in done_root.glob(f"**/{Path(normalized).name}")
        if path.is_file()
    )
    if len(matches) == 1:
        return matches[0]
    return normalized


def _normalized_path_matches(normalized_changed_path: str, normalized_ref_path: str) -> bool:
    if not normalized_changed_path or not normalized_ref_path:
        return False
    if normalized_changed_path == normalized_ref_path:
        return True
    return normalized_changed_path.startswith(f"{normalized_ref_path}/")


def path_matches(changed_path: str, ref_path: str) -> bool:
    """Return ``True`` when changed path equals or nests under ``ref_path``."""

    left = normalize_repo_token(changed_path)
    right = normalize_repo_token(ref_path)
    return _normalized_path_matches(left, right)


def is_global_coordination_path(path: str) -> bool:
    """Return ``True`` when a path belongs to global coordination artifacts."""

    token = normalize_repo_token(path).lower()
    if not token:
        return False
    if token in GLOBAL_COORDINATION_EXACT_PATHS:
        return True
    return any(token.startswith(prefix) for prefix in GLOBAL_COORDINATION_PREFIXES)


def is_generated_or_global_path(path: str) -> bool:
    """Return ``True`` for generated artifacts or global coordination files."""

    token = normalize_repo_token(path).lower()
    if not token:
        return True
    if is_global_coordination_path(token):
        return True
    return token.endswith(".svg") or token.endswith(".png")


def collect_workstream_path_index_from_specs(
    *,
    repo_root: Path,
    idea_specs: Mapping[str, backlog_contract.IdeaSpec],
) -> dict[str, set[str]]:
    """Build path-reference index from validated idea specs."""

    index: dict[str, set[str]] = {}
    for idea_id, spec in idea_specs.items():
        refs: set[str] = {normalize_repo_token(str(spec.path), repo_root=repo_root)}
        plan_token = str(spec.metadata.get("promoted_to_plan", "")).strip()
        if plan_token:
            refs.add(normalize_repo_token(plan_token, repo_root=repo_root))
        index[idea_id] = {ref for ref in refs if ref}
    return index


def collect_workstream_path_index_from_traceability(
    *,
    repo_root: Path,
    traceability_graph: Mapping[str, Any],
    mermaid_catalog: Mapping[str, Any],
) -> dict[str, set[str]]:
    """Build path-reference index from traceability graph + Mermaid catalog."""

    index: dict[str, set[str]] = {}

    workstreams = traceability_graph.get("workstreams", [])
    if isinstance(workstreams, list):
        for row in workstreams:
            if not isinstance(row, Mapping):
                continue
            idea_id = str(row.get("idea_id", "")).strip()
            if not idea_id:
                continue
            index.setdefault(idea_id, set())

            for token in (row.get("idea_file"), row.get("promoted_to_plan")):
                normalized = normalize_repo_token(str(token or ""), repo_root=repo_root)
                if normalized:
                    index[idea_id].add(normalized)

            plan_trace = row.get("plan_traceability", {})
            if isinstance(plan_trace, Mapping):
                for bucket in ("runbooks", "developer_docs", "code_references"):
                    values = plan_trace.get(bucket, [])
                    if not isinstance(values, list):
                        continue
                    for token in values:
                        normalized = normalize_repo_token(str(token or ""), repo_root=repo_root)
                        if normalized:
                            index[idea_id].add(normalized)

    diagrams = mermaid_catalog.get("diagrams", [])
    if isinstance(diagrams, list):
        for row in diagrams:
            if not isinstance(row, Mapping):
                continue
            related_workstreams = row.get("related_workstreams", [])
            ws_ids: list[str] = []
            if isinstance(related_workstreams, list):
                ws_ids = [str(item).strip() for item in related_workstreams if str(item).strip()]

            if not ws_ids:
                related_backlog = row.get("related_backlog", [])
                if isinstance(related_backlog, list):
                    for token in related_backlog:
                        raw = str(token or "").strip()
                        if not raw:
                            continue
                        idea_path = Path(repo_root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
                        if not idea_path.is_file():
                            continue
                        spec = backlog_contract._parse_idea_spec(idea_path)
                        idea_id = str(spec.idea_id or "").strip()
                        if idea_id:
                            ws_ids.append(idea_id)

            if not ws_ids:
                continue

            refs: list[str] = []
            for field in ("source_mmd", "source_svg", "source_png"):
                token = str(row.get(field, "")).strip()
                if token:
                    refs.append(token)

            for field in (
                "change_watch_paths",
                "related_backlog",
                "related_plans",
                "related_docs",
                "related_code",
            ):
                values = row.get(field, [])
                if isinstance(values, list):
                    refs.extend(str(item or "").strip() for item in values if str(item or "").strip())

            normalized_refs: list[str] = []
            for item in refs:
                normalized = normalize_repo_token(item, repo_root=repo_root)
                if normalized:
                    normalized_refs.append(normalized)
            for ws_id in ws_ids:
                index.setdefault(ws_id, set()).update(normalized_refs)

    return index


def map_paths_to_workstreams(
    paths: Iterable[str],
    ws_path_index: Mapping[str, set[str]],
    *,
    skip_generated_or_global: bool = True,
) -> list[str]:
    """Map changed paths to matching workstream IDs via the path-reference index."""

    matched: set[str] = set()
    for path in paths:
        normalized = normalize_repo_token(path)
        if not normalized:
            continue
        if skip_generated_or_global and is_generated_or_global_path(normalized):
            continue
        for ws_id, refs in ws_path_index.items():
            if any(_normalized_path_matches(normalized, ref) for ref in refs):
                matched.add(ws_id)
    return sorted(matched)

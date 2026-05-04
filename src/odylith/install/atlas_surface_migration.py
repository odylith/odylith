"""Migrate Atlas rendered diagram surfaces to the v0.1.14 render contract."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from odylith.install.fs import atomic_write_text, display_path
from odylith.install.versioning import is_at_least, is_before, normalize_version
from odylith.runtime.governance import build_traceability_graph
from odylith.runtime.governance import topology_integrity
from odylith.runtime.common import diagram_freshness
from odylith.runtime.surfaces import auto_update_mermaid_diagrams
from odylith.runtime.surfaces import render_mermaid_catalog
from odylith.runtime.surfaces import surface_path_helpers

MIGRATION_ID = "v0.1.14-atlas-render-surface-polish"
MIGRATION_SCHEMA_VERSION = "odylith-atlas-render-surface-polish-migration.v1"
TARGET_VERSION = "0.1.14"
CATALOG_RELATIVE_PATH = Path("odylith/atlas/source/catalog/diagrams.v1.json")
TRACEABILITY_GRAPH_RELATIVE_PATH = Path("odylith/radar/traceability-graph.v1.json")
ATLAS_SURFACE_REQUIRED_PATHS = (
    Path("odylith/atlas/atlas.html"),
    Path("odylith/atlas/mermaid-payload.v1.js"),
    Path("odylith/atlas/mermaid-app.v1.js"),
)
_OLD_VIEWER_BACKGROUND_TOKENS = (
    ".viewer-stage::before",
    "background-size: 42px 42px",
    "background-size: 100% 100%, 42px 42px",
    "linear-gradient(90deg, rgba(20, 184, 166",
    "linear-gradient(rgba(15, 23, 42, 0.06)",
)
_POLISHED_CLUSTER_FILLS = frozenset(
    {"#effcf9", "#f1f7ff", "#fff8e8", "#f2fbef", "#fbf7ff"}
)
_POLISHED_NODE_FILLS = frozenset(
    {"#e8fbf7", "#eaf3ff", "#fff4dc", "#f4ebff", "#ebf9e8", "#f5f8fb"}
)
_LEGACY_CLUSTER_STYLE_TOKENS = (
    "style=\"\"",
    "fill:#fbfdff",
    "stroke:#c7d7e8",
    "fill:#f7fdfb",
    "fill:#f8fbff",
    "fill:#fffaf0",
    "fill:#f9fdf6",
    "fill:#fcf9ff",
    "stroke:#b8e1db",
    "stroke:#c9dafa",
    "stroke:#ebd0a0",
    "stroke:#cbe4c3",
    "stroke:#dccbf4",
)
_LEGACY_NODE_STYLE_TOKENS = (
    "fill:#eafbf7",
    "fill:#eef5ff",
    "fill:#fff6e3",
    "fill:#f5efff",
    "fill:#f0faed",
    "fill:#f7fafc",
    "stroke:#78c9bd",
    "stroke:#91b9f4",
    "stroke:#e7b96f",
    "stroke:#bea5ea",
    "stroke:#95cf8c",
    "stroke:#cbd7e4",
)


@dataclass(frozen=True)
class _SvgStyleInspection:
    """One-pass rendered SVG style evidence for Atlas migration decisions."""

    lowered_text: str
    cluster_blocks: tuple[str, ...]
    node_blocks: tuple[str, ...]


@dataclass(frozen=True)
class AtlasSurfaceMigrationInspection:
    """Read-only evidence used to plan the v0.1.14 Atlas surface migration."""

    migration_id: str
    previous_version: str
    target_version: str
    target_in_window: bool
    previous_requires_migration: bool
    atlas_catalog_exists: bool
    diagram_count: int
    render_paths_needing_migration: tuple[str, ...]
    generated_surface_violations: tuple[str, ...]
    ledger_exists: bool
    ledger_valid: bool
    ledger_stale_reason: str
    ledger_path: str
    planned_paths: tuple[str, ...]

    @property
    def verification_passed(self) -> bool:
        """Return whether the ledger and current Atlas render state still verify."""
        return self.ledger_valid and not self.render_paths_needing_migration and not self.generated_surface_violations

    @property
    def migration_required(self) -> bool:
        """Return whether applying the migration would write or record local state."""
        if not self.target_in_window:
            return False
        if not self.atlas_catalog_exists and not self.generated_surface_violations:
            return False
        if self.render_paths_needing_migration or self.generated_surface_violations:
            return True
        return self.previous_requires_migration and not self.ledger_exists

    def as_dict(self) -> dict[str, Any]:
        """Return the inspection as a JSON-serializable payload."""
        return {
            "migration_id": self.migration_id,
            "previous_version": self.previous_version,
            "target_version": self.target_version,
            "target_in_window": self.target_in_window,
            "previous_requires_migration": self.previous_requires_migration,
            "atlas_catalog_exists": self.atlas_catalog_exists,
            "diagram_count": self.diagram_count,
            "render_paths_needing_migration": list(self.render_paths_needing_migration),
            "generated_surface_violations": list(self.generated_surface_violations),
            "ledger_exists": self.ledger_exists,
            "ledger_valid": self.ledger_valid,
            "ledger_stale_reason": self.ledger_stale_reason,
            "ledger_path": self.ledger_path,
            "planned_paths": list(self.planned_paths),
            "verification_passed": self.verification_passed,
            "migration_required": self.migration_required,
        }


@dataclass(frozen=True)
class AtlasSurfaceMigrationResult:
    """Result payload for the v0.1.14 Atlas rendered-surface migration."""

    migration_id: str
    applied: bool
    previous_version: str
    target_version: str
    written_paths: tuple[str, ...] = ()
    removed_paths: tuple[str, ...] = ()
    skipped_reason: str = ""
    ledger_path: str = ""
    verification_result: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the migration result as a JSON-serializable payload."""
        return {
            "schema_version": MIGRATION_SCHEMA_VERSION,
            "migration_id": self.migration_id,
            "applied": bool(self.applied),
            "previous_version": self.previous_version,
            "target_version": self.target_version,
            "written_paths": list(self.written_paths),
            "removed_paths": list(self.removed_paths),
            "skipped_reason": self.skipped_reason,
            "ledger_path": self.ledger_path,
            "verification_result": dict(self.verification_result or {}),
        }


def _ledger_path(*, repo_root: Path) -> Path:
    return repo_root / ".odylith" / "state" / "migrations" / f"{MIGRATION_ID}.v1.json"


def _read_ledger(*, repo_root: Path) -> tuple[bool, str]:
    path = _ledger_path(repo_root=repo_root)
    if not path.is_file():
        return False, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"unreadable ledger: {exc.__class__.__name__}"
    if not isinstance(payload, Mapping):
        return False, "ledger payload is not an object"
    if str(payload.get("migration_id") or "").strip() != MIGRATION_ID:
        return False, "ledger migration_id mismatch"
    if str(payload.get("schema_version") or "").strip() != MIGRATION_SCHEMA_VERSION:
        return False, "ledger schema_version mismatch"
    verification = payload.get("verification_result")
    if not isinstance(verification, Mapping) or str(verification.get("status") or "").strip() != "passed":
        return False, "ledger verification_result did not pass"
    return True, ""


def _write_ledger(
    *,
    repo_root: Path,
    previous_version: str,
    target_version: str,
    written_paths: Iterable[str],
    removed_paths: Iterable[str],
    verification_result: Mapping[str, Any],
) -> str:
    path = _ledger_path(repo_root=repo_root)
    payload = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "migration_id": MIGRATION_ID,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "previous_version": previous_version,
        "target_version": target_version,
        "written_paths": list(written_paths),
        "removed_paths": list(removed_paths),
        "verification_result": dict(verification_result),
        "notes": (
            "v0.1.14 migrates Atlas generated diagram assets and the Atlas "
            "dashboard to the pure-white viewer background plus the darker "
            "managed cluster and semantic node color contract. Source Mermaid "
            "remains topology truth; the migration regenerates derived render "
            "surfaces, rebuilds the shared topology traceability graph, and "
            "records verified fingerprints plus topology integrity evidence."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return display_path(repo_root=repo_root, path=path)


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atlas_path_fingerprints(*, repo_root: Path) -> dict[str, str]:
    roots = (repo_root / "odylith" / "atlas",)
    fingerprints: dict[str, str] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                fingerprints[display_path(repo_root=repo_root, path=path)] = _file_digest(path)
    traceability_graph = repo_root / TRACEABILITY_GRAPH_RELATIVE_PATH
    if traceability_graph.is_file():
        fingerprints[display_path(repo_root=repo_root, path=traceability_graph)] = _file_digest(traceability_graph)
    return fingerprints


def _changed_paths(before: Mapping[str, str], after: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(sorted(path for path, content in after.items() if before.get(path) != content))


def _removed_paths(before: Mapping[str, str], after: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(sorted(path for path in before if path not in after))


def _load_catalog(repo_root: Path) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    path = repo_root / CATALOG_RELATIVE_PATH
    if not path.is_file():
        return None, ()
    rel = display_path(repo_root=repo_root, path=path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, (f"{rel}: unreadable Atlas catalog: {exc.__class__.__name__}",)
    if not isinstance(payload, dict):
        return None, (f"{rel}: Atlas catalog payload is not an object",)
    diagrams = payload.get("diagrams")
    if not isinstance(diagrams, list):
        return None, (f"{rel}: Atlas catalog diagrams list is missing or invalid",)
    return payload, ()


def _diagram_items(payload: Mapping[str, Any] | None) -> tuple[dict[str, Any], ...]:
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return ()
    return tuple(dict(item) for item in diagrams if isinstance(item, Mapping))


def _resolve_repo_path(repo_root: Path, token: str) -> Path:
    return surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=token)


def _diagram_id(item: Mapping[str, Any]) -> str:
    return str(item.get("diagram_id", "") or item.get("slug", "") or "unknown-diagram").strip()


def _source_tokens(item: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        PurePosixPath(str(item.get("source_mmd", "")).strip()).as_posix(),
        PurePosixPath(str(item.get("source_svg", "")).strip()).as_posix(),
        PurePosixPath(str(item.get("source_png", "")).strip()).as_posix(),
    )


def _svg_style_inspection(path: Path) -> _SvgStyleInspection | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    lowered_text = text.lower()
    class_blocks = _svg_class_blocks(text)
    cluster_blocks = class_blocks.get("cluster", ())
    if not cluster_blocks:
        cluster_blocks = tuple(
            block.lower()
            for block in re.findall(r"<g\b[^>]*class=[\"'][^\"']*cluster[^\"']*[\"'][\s\S]*?</g>", text)
        )
    return _SvgStyleInspection(
        lowered_text=lowered_text,
        cluster_blocks=cluster_blocks,
        node_blocks=class_blocks.get("node", ()),
    )


def _svg_cluster_needs_polish(path: Path) -> bool:
    inspection = _svg_style_inspection(path)
    return _svg_cluster_needs_polish_from_inspection(inspection) if inspection else False


def _svg_cluster_needs_polish_from_inspection(inspection: _SvgStyleInspection) -> bool:
    if "cluster" not in inspection.lowered_text:
        return False
    cluster_blocks = inspection.cluster_blocks
    if not cluster_blocks:
        return any(token in inspection.lowered_text for token in _LEGACY_CLUSTER_STYLE_TOKENS)
    for block in cluster_blocks:
        if any(token in block for token in _LEGACY_CLUSTER_STYLE_TOKENS):
            return True
        if any(fill in block for fill in _POLISHED_CLUSTER_FILLS):
            continue
        return True
    return False


def _svg_class_blocks(text: str) -> dict[str, tuple[str, ...]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return {}
    matches: dict[str, list[str]] = {"cluster": [], "node": []}
    for element in root.iter():
        class_names = set(str(element.attrib.get("class", "")).split())
        for class_name in matches:
            if class_name in class_names:
                matches[class_name].append(ET.tostring(element, encoding="unicode").lower())
    return {class_name: tuple(blocks) for class_name, blocks in matches.items()}


def _svg_node_needs_polish(path: Path) -> bool:
    inspection = _svg_style_inspection(path)
    return _svg_node_needs_polish_from_inspection(inspection) if inspection else False


def _svg_node_needs_polish_from_inspection(inspection: _SvgStyleInspection) -> bool:
    if "node" not in inspection.lowered_text:
        return False
    node_blocks = inspection.node_blocks
    if node_blocks:
        for block in node_blocks:
            if any(token in block for token in _LEGACY_NODE_STYLE_TOKENS):
                return True
            if any(fill in block for fill in _POLISHED_NODE_FILLS):
                continue
            return True
        return False
    if any(token in inspection.lowered_text for token in _LEGACY_NODE_STYLE_TOKENS):
        return True
    if any(fill in inspection.lowered_text for fill in _POLISHED_NODE_FILLS):
        return False
    return True


def _svg_needs_polish(path: Path) -> bool:
    inspection = _svg_style_inspection(path)
    if inspection is None:
        return False
    return (
        _svg_cluster_needs_polish_from_inspection(inspection)
        or _svg_node_needs_polish_from_inspection(inspection)
    )


def _render_paths_needing_migration(
    *,
    repo_root: Path,
    items: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    cache = diagram_freshness.ContentFingerprintCache()
    needing: list[str] = []
    for item in items:
        diagram_id = _diagram_id(item)
        source_mmd, source_svg, source_png = _source_tokens(item)
        if not source_mmd or not source_svg or not source_png:
            needing.append(f"{diagram_id}: missing source_mmd/source_svg/source_png")
            continue
        source_mmd_path = _resolve_repo_path(repo_root, source_mmd)
        source_svg_path = _resolve_repo_path(repo_root, source_svg)
        source_png_path = _resolve_repo_path(repo_root, source_png)
        if not source_mmd_path.is_file():
            needing.append(f"{diagram_id}: missing source Mermaid {source_mmd}")
            continue
        current_fingerprint = cache.mermaid_render_fingerprint(source_mmd_path)
        stored_fingerprint = str(item.get("render_source_fingerprint", "")).strip()
        if stored_fingerprint != current_fingerprint:
            needing.append(display_path(repo_root=repo_root, path=source_mmd_path))
            continue
        if not source_svg_path.is_file() or not source_png_path.is_file():
            needing.append(display_path(repo_root=repo_root, path=source_mmd_path))
            continue
        if _svg_needs_polish(source_svg_path):
            needing.append(display_path(repo_root=repo_root, path=source_mmd_path))
    return tuple(dict.fromkeys(needing))


def _generated_surface_violations(*, repo_root: Path, catalog_exists: bool) -> tuple[str, ...]:
    if not catalog_exists:
        return ()
    missing = [
        display_path(repo_root=repo_root, path=repo_root / path)
        for path in ATLAS_SURFACE_REQUIRED_PATHS
        if not (repo_root / path).is_file()
    ]
    violations = [f"missing generated Atlas surface: {path}" for path in missing]
    html_path = repo_root / "odylith" / "atlas" / "atlas.html"
    if html_path.is_file():
        rel = display_path(repo_root=repo_root, path=html_path)
        try:
            html = html_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            violations.append(f"{rel}: unreadable generated Atlas surface: {exc.__class__.__name__}")
        else:
            if any(token in html for token in _OLD_VIEWER_BACKGROUND_TOKENS):
                violations.append(f"{rel}: Atlas viewer still contains ruled or split background styling")
            if ".viewer-stage" in html and "background: #ffffff;" not in html:
                violations.append(f"{rel}: Atlas viewer stage is not explicitly pure white")
    return tuple(dict.fromkeys(violations))


def _topology_integrity_violations(*, repo_root: Path, catalog_exists: bool) -> tuple[str, ...]:
    if not catalog_exists:
        return ()
    graph_path = repo_root / TRACEABILITY_GRAPH_RELATIVE_PATH
    rel = display_path(repo_root=repo_root, path=graph_path)
    if not graph_path.is_file():
        return (f"missing generated topology traceability graph: {rel}",)
    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (f"{rel}: unreadable topology traceability graph: {exc.__class__.__name__}",)
    if not isinstance(payload, Mapping):
        return (f"{rel}: topology traceability graph payload is not an object",)
    report = topology_integrity.evaluate_topology_integrity(payload)
    error_count = int(report.get("severity_counts", {}).get("error", 0) or 0)
    score = int(report.get("score", 0) or 0)
    if error_count or score < 90:
        return (f"{rel}: topology integrity {report.get('quality', 'failed')} score {score}/100",)
    return ()


def _planned_paths(*, repo_root: Path) -> tuple[str, ...]:
    payload, _violations = _load_catalog(repo_root)
    paths: list[Path] = [
        repo_root / CATALOG_RELATIVE_PATH,
        repo_root / TRACEABILITY_GRAPH_RELATIVE_PATH,
        *[repo_root / token for token in ATLAS_SURFACE_REQUIRED_PATHS],
    ]
    for item in _diagram_items(payload):
        _source_mmd, source_svg, source_png = _source_tokens(item)
        if source_svg:
            paths.append(_resolve_repo_path(repo_root, source_svg))
        if source_png:
            paths.append(_resolve_repo_path(repo_root, source_png))
    paths.append(_ledger_path(repo_root=repo_root))
    return tuple(dict.fromkeys(display_path(repo_root=repo_root, path=path) for path in paths))


def inspect_atlas_surface_migration(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
) -> AtlasSurfaceMigrationInspection:
    """Inspect the v0.1.14 Atlas render-surface migration state without writing."""
    root = Path(repo_root).expanduser().resolve()
    previous = normalize_version(previous_version)
    target = normalize_version(target_version)
    ledger_valid, ledger_stale_reason = _read_ledger(repo_root=root)
    ledger = _ledger_path(repo_root=root)
    payload, catalog_violations = _load_catalog(root)
    items = _diagram_items(payload)
    atlas_catalog_exists = (root / CATALOG_RELATIVE_PATH).is_file()
    render_violations = _render_paths_needing_migration(repo_root=root, items=items) if payload is not None else ()
    generated_violations = (
        *catalog_violations,
        *_generated_surface_violations(repo_root=root, catalog_exists=atlas_catalog_exists),
        *_topology_integrity_violations(repo_root=root, catalog_exists=atlas_catalog_exists),
    )
    return AtlasSurfaceMigrationInspection(
        migration_id=MIGRATION_ID,
        previous_version=previous,
        target_version=target,
        target_in_window=is_at_least(target, TARGET_VERSION),
        previous_requires_migration=not previous or is_before(previous, TARGET_VERSION),
        atlas_catalog_exists=atlas_catalog_exists,
        diagram_count=len(items),
        render_paths_needing_migration=render_violations,
        generated_surface_violations=tuple(dict.fromkeys(generated_violations)),
        ledger_exists=ledger.is_file(),
        ledger_valid=ledger_valid,
        ledger_stale_reason="" if ledger_valid or not ledger.is_file() else ledger_stale_reason,
        ledger_path=display_path(repo_root=root, path=ledger),
        planned_paths=_planned_paths(repo_root=root),
    )


def atlas_surface_decision_state(
    *,
    repo_scenario: str,
    inspection: AtlasSurfaceMigrationInspection,
) -> tuple[str, str]:
    """Return the migration-runtime state and reason for the Atlas surface migration."""
    scenario = str(repo_scenario or "").strip()
    if scenario == "legacy_odyssey":
        if inspection.target_in_window:
            return "selected", "Atlas render-surface migration runs after the legacy root migration"
        return "skipped", "target version is not in target window for the v0.1.14 Atlas render-surface migration"
    if scenario == "detached_source_local":
        return "blocked", "release migrations are blocked while the product repo is in detached source-local posture"
    if scenario == "product_repo_pinned_dogfood":
        return (
            "skipped",
            "product repo Atlas source truth is validated by maintainer release gates, not consumer migration apply",
        )
    if not inspection.target_in_window:
        return "skipped", "target version is not in target window for the v0.1.14 Atlas render-surface migration"
    if inspection.ledger_exists and not inspection.ledger_valid:
        return "ledger_stale", f"migration ledger is stale: {inspection.ledger_stale_reason}"
    if inspection.verification_passed:
        return "skipped", "ledger and verification already satisfy the v0.1.14 Atlas render-surface migration"
    if not inspection.atlas_catalog_exists and not inspection.generated_surface_violations:
        return "skipped", "repo has no Atlas catalog to migrate"
    if inspection.migration_required:
        return "selected", "Atlas render fingerprints or generated Atlas surfaces require automatic migration"
    return "skipped", "migration predicates do not require local Atlas render-surface changes"


def _render_jobs(
    *,
    repo_root: Path,
    items: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, str], ...]:
    cache = diagram_freshness.ContentFingerprintCache()
    jobs: list[dict[str, str]] = []
    for item in items:
        diagram_id = _diagram_id(item)
        source_mmd, source_svg, source_png = _source_tokens(item)
        if not source_mmd or not source_svg or not source_png:
            raise RuntimeError(f"{diagram_id}: missing Atlas source paths")
        source_mmd_path = _resolve_repo_path(repo_root, source_mmd)
        source_svg_path = _resolve_repo_path(repo_root, source_svg)
        source_png_path = _resolve_repo_path(repo_root, source_png)
        if not source_mmd_path.is_file():
            raise RuntimeError(f"{diagram_id}: source mmd missing: {source_mmd}")
        current_fingerprint = cache.mermaid_render_fingerprint(source_mmd_path)
        if (
            str(item.get("render_source_fingerprint", "")).strip() == current_fingerprint
            and source_svg_path.is_file()
            and source_png_path.is_file()
            and not _svg_cluster_needs_polish(source_svg_path)
            and not _svg_node_needs_polish(source_svg_path)
        ):
            continue
        jobs.append(
            {
                "diagram_id": diagram_id,
                "source_mmd": source_mmd,
                "source_svg": source_svg,
                "source_png": source_png,
            }
        )
    return tuple(jobs)


def _update_catalog_render_metadata(*, repo_root: Path, payload: dict[str, Any], jobs: Sequence[Mapping[str, str]]) -> None:
    if not jobs:
        return
    by_id = {str(job.get("diagram_id", "")).strip(): job for job in jobs}
    today = date.today().isoformat()
    cache = diagram_freshness.ContentFingerprintCache()
    diagrams = payload.get("diagrams")
    if not isinstance(diagrams, list):
        raise RuntimeError("Atlas catalog diagrams list is missing after render")
    for item in diagrams:
        if not isinstance(item, dict):
            continue
        diagram_id = _diagram_id(item)
        if diagram_id not in by_id:
            continue
        source_mmd = str(item.get("source_mmd", "")).strip()
        source_mmd_path = _resolve_repo_path(repo_root, source_mmd)
        watch_paths = [
            PurePosixPath(str(token or "").strip()).as_posix()
            for token in item.get("change_watch_paths", [])
            if str(token or "").strip()
        ]
        item["reviewed_watch_fingerprints"] = auto_update_mermaid_diagrams._current_watch_fingerprints(
            repo_root=repo_root,
            watch_paths=watch_paths,
            cache=cache,
        )
        item["render_source_fingerprint"] = cache.mermaid_render_fingerprint(source_mmd_path)
        item["last_reviewed_utc"] = today


def _render_atlas_dashboard(*, repo_root: Path) -> None:
    rc = render_mermaid_catalog.main(
        [
            "--repo-root",
            str(repo_root),
            "--runtime-mode",
            "standalone",
        ]
    )
    if rc != 0:
        raise RuntimeError("Atlas dashboard render failed during v0.1.14 Atlas surface migration")


def _build_traceability_graph(*, repo_root: Path) -> None:
    rc = build_traceability_graph.main(["--repo-root", str(repo_root)])
    if rc != 0:
        raise RuntimeError("Topology traceability graph build failed during v0.1.14 Atlas surface migration")


def _topology_integrity_report(*, repo_root: Path) -> dict[str, Any]:
    graph_path = repo_root / TRACEABILITY_GRAPH_RELATIVE_PATH
    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "failed",
            "error": f"unreadable topology traceability graph: {exc.__class__.__name__}",
        }
    if not isinstance(payload, Mapping):
        return {"status": "failed", "error": "topology traceability graph payload is not an object"}
    report = topology_integrity.evaluate_topology_integrity(payload)
    error_count = int(report.get("severity_counts", {}).get("error", 0) or 0)
    score = int(report.get("score", 0) or 0)
    return {
        "status": "passed" if not error_count and score >= 90 else "failed",
        "algorithm": report.get("algorithm", ""),
        "quality": report.get("quality", ""),
        "score": score,
        "severity_counts": dict(report.get("severity_counts", {})),
        "connectivity": dict(report.get("connectivity", {})),
    }


def migrate_atlas_surface_polish(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
    mermaid_cli_version: str = "11.12.0",
) -> AtlasSurfaceMigrationResult:
    """Apply the v0.1.14 Atlas rendered-surface migration when in scope."""
    root = Path(repo_root).expanduser().resolve()
    previous = normalize_version(previous_version)
    target = normalize_version(target_version)
    inspection = inspect_atlas_surface_migration(
        repo_root=root,
        previous_version=previous,
        target_version=target,
    )
    if not inspection.target_in_window:
        return AtlasSurfaceMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="target_not_in_v0_1_14_migration_window",
            ledger_path=inspection.ledger_path,
        )
    if inspection.verification_passed:
        return AtlasSurfaceMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="ledger_and_atlas_surfaces_already_verify",
            ledger_path=inspection.ledger_path,
            verification_result={"status": "passed", "mode": "already_verified"},
        )
    if not inspection.atlas_catalog_exists and not inspection.generated_surface_violations:
        return AtlasSurfaceMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="no_atlas_catalog",
            ledger_path=inspection.ledger_path,
            verification_result={"status": "skipped", "mode": "no_atlas_catalog"},
        )
    payload, catalog_violations = _load_catalog(root)
    if payload is None:
        raise RuntimeError("; ".join(catalog_violations) or "Atlas catalog is missing or invalid")
    before = _atlas_path_fingerprints(repo_root=root)
    items = _diagram_items(payload)
    jobs = _render_jobs(repo_root=root, items=items)
    auto_update_mermaid_diagrams._render_diagrams_batch(
        repo_root=root,
        render_jobs=jobs,
        cli_version=mermaid_cli_version,
    )
    _update_catalog_render_metadata(repo_root=root, payload=payload, jobs=jobs)
    if jobs:
        catalog_path = root / CATALOG_RELATIVE_PATH
        atomic_write_text(catalog_path, f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    _render_atlas_dashboard(repo_root=root)
    _build_traceability_graph(repo_root=root)
    after = _atlas_path_fingerprints(repo_root=root)
    verification = inspect_atlas_surface_migration(
        repo_root=root,
        previous_version=previous,
        target_version=target,
    )
    topology_report = _topology_integrity_report(repo_root=root)
    verification_result = {
        "status": "passed"
        if not verification.render_paths_needing_migration and not verification.generated_surface_violations
        and topology_report.get("status") == "passed"
        else "failed",
        "render_paths_needing_migration": list(verification.render_paths_needing_migration),
        "generated_surface_violations": list(verification.generated_surface_violations),
        "diagram_count": verification.diagram_count,
        "topology_integrity": topology_report,
    }
    if verification_result["status"] != "passed":
        raise RuntimeError("Atlas render-surface migration did not verify after apply")
    written = _changed_paths(before, after)
    removed = _removed_paths(before, after)
    ledger_path = _write_ledger(
        repo_root=root,
        previous_version=previous,
        target_version=target,
        written_paths=written,
        removed_paths=removed,
        verification_result=verification_result,
    )
    return AtlasSurfaceMigrationResult(
        migration_id=MIGRATION_ID,
        applied=True,
        previous_version=previous,
        target_version=target,
        written_paths=written,
        removed_paths=removed,
        ledger_path=ledger_path,
        verification_result=verification_result,
    )


def atlas_surface_migration_ledger_path(*, repo_root: str | Path) -> str:
    """Return the repo-relative v0.1.14 Atlas render-surface ledger path."""
    root = Path(repo_root).expanduser().resolve()
    return display_path(repo_root=root, path=_ledger_path(repo_root=root))


__all__ = [
    "ATLAS_SURFACE_REQUIRED_PATHS",
    "CATALOG_RELATIVE_PATH",
    "MIGRATION_ID",
    "MIGRATION_SCHEMA_VERSION",
    "TARGET_VERSION",
    "AtlasSurfaceMigrationInspection",
    "AtlasSurfaceMigrationResult",
    "atlas_surface_decision_state",
    "atlas_surface_migration_ledger_path",
    "inspect_atlas_surface_migration",
    "migrate_atlas_surface_polish",
]

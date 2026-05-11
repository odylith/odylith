"""Migrate Atlas browser surfaces to the v0.1.15 box-explanation contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from odylith.install.fs import atomic_write_text, display_path
from odylith.install.versioning import is_at_least, is_before, normalize_version
from odylith.runtime.governance import build_traceability_graph
from odylith.runtime.governance import topology_integrity
from odylith.runtime.surfaces import atlas_box_explanations
from odylith.runtime.surfaces import render_mermaid_catalog

MIGRATION_ID = "v0.1.15-atlas-box-explanation-contract"
MIGRATION_SCHEMA_VERSION = "odylith-atlas-box-explanation-migration.v1"
TARGET_VERSION = "0.1.15"
CATALOG_RELATIVE_PATH = Path("odylith/atlas/source/catalog/diagrams.v1.json")
TRACEABILITY_GRAPH_RELATIVE_PATH = Path("odylith/radar/traceability-graph.v1.json")
ATLAS_SURFACE_REQUIRED_PATHS = (
    Path("odylith/atlas/atlas.html"),
    Path("odylith/atlas/mermaid-payload.v1.js"),
    Path("odylith/atlas/mermaid-app.v1.js"),
)


@dataclass(frozen=True)
class AtlasBoxExplanationMigrationInspection:
    """Read-only evidence for the v0.1.15 Atlas box-explanation migration."""

    migration_id: str
    previous_version: str
    target_version: str
    target_in_window: bool
    previous_requires_migration: bool
    atlas_catalog_exists: bool
    diagram_count: int
    expected_box_count: int
    box_inventory_violations: tuple[str, ...]
    generated_surface_violations: tuple[str, ...]
    ledger_exists: bool
    ledger_valid: bool
    ledger_stale_reason: str
    ledger_path: str
    planned_paths: tuple[str, ...]

    @property
    def verification_passed(self) -> bool:
        """Return whether current generated surfaces and ledger satisfy the contract."""
        return (
            self.ledger_valid
            and not self.box_inventory_violations
            and not self.generated_surface_violations
        )

    @property
    def migration_required(self) -> bool:
        """Return whether applying this migration should write generated state."""
        if not self.target_in_window or not self.atlas_catalog_exists:
            return False
        if self.box_inventory_violations or self.generated_surface_violations:
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
            "expected_box_count": self.expected_box_count,
            "box_inventory_violations": list(self.box_inventory_violations),
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
class AtlasBoxExplanationMigrationResult:
    """Result payload for the v0.1.15 Atlas box-explanation migration."""

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


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atlas_path_fingerprints(*, repo_root: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    atlas_root = repo_root / "odylith" / "atlas"
    if atlas_root.is_dir():
        for path in atlas_root.rglob("*"):
            if path.is_file():
                fingerprints[display_path(repo_root=repo_root, path=path)] = _file_digest(path)
    graph_path = repo_root / TRACEABILITY_GRAPH_RELATIVE_PATH
    if graph_path.is_file():
        fingerprints[display_path(repo_root=repo_root, path=graph_path)] = _file_digest(graph_path)
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
    if not isinstance(payload.get("diagrams"), list):
        return None, (f"{rel}: Atlas catalog diagrams list is missing or invalid",)
    return payload, ()


def _diagram_items(payload: Mapping[str, Any] | None) -> tuple[dict[str, Any], ...]:
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return ()
    return tuple(dict(item) for item in diagrams if isinstance(item, Mapping))


def _expected_boxes_by_diagram(*, repo_root: Path, items: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    expected: list[dict[str, Any]] = []
    for item in items:
        diagram_id = str(item.get("diagram_id") or item.get("slug") or "unknown-diagram").strip()
        source_mmd = str(item.get("source_mmd") or "").strip()
        if not source_mmd:
            continue
        source_path = repo_root / source_mmd
        if not source_path.is_file():
            continue
        try:
            source_text = source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        labels = atlas_box_explanations.diagram_box_labels(
            box.as_dict()
            for box in atlas_box_explanations.extract_diagram_boxes_from_mermaid(source_text)
        )
        if labels:
            expected.append({"diagram_id": diagram_id, "labels": labels})
    return tuple(expected)


def _catalog_box_inventory_violations(*, repo_root: Path, items: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    violations: list[str] = []
    for idx, item in enumerate(items):
        context = f"{display_path(repo_root=repo_root, path=repo_root / CATALOG_RELATIVE_PATH)}: diagrams[{idx}]"
        errors: list[str] = []
        atlas_box_explanations.normalize_catalog_diagram_boxes(
            raw_boxes=item.get("diagram_boxes", []),
            context=context,
            errors=errors,
        )
        violations.extend(errors)
    return tuple(violations)


def _read_payload_diagrams(repo_root: Path) -> tuple[dict[str, Any], ...] | None:
    payload_path = repo_root / "odylith" / "atlas" / "mermaid-payload.v1.js"
    if not payload_path.is_file():
        return None
    try:
        text = payload_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if "=" not in text:
        return None
    raw_json = text.split("=", 1)[1].strip().rstrip(";")
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return None
    return tuple(dict(item) for item in diagrams if isinstance(item, Mapping))


def _generated_surface_violations(
    *,
    repo_root: Path,
    catalog_exists: bool,
    expected_boxes: Iterable[Mapping[str, Any]],
) -> tuple[str, ...]:
    if not catalog_exists:
        return ()
    violations = [
        f"missing generated Atlas surface: {display_path(repo_root=repo_root, path=repo_root / path)}"
        for path in ATLAS_SURFACE_REQUIRED_PATHS
        if not (repo_root / path).is_file()
    ]
    html_path = repo_root / "odylith" / "atlas" / "atlas.html"
    if html_path.is_file():
        try:
            html_text = html_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            violations.append(f"{display_path(repo_root=repo_root, path=html_path)}: unreadable Atlas HTML: {exc.__class__.__name__}")
        else:
            if ".diagram-box-section[hidden]" not in html_text:
                violations.append("Atlas detail layout does not hide empty diagram-box sections")
            if "renderDiagramBoxes" not in html_text and not (repo_root / "odylith/atlas/mermaid-app.v1.js").is_file():
                violations.append("Atlas detail runtime does not render diagram-box explanations")
    payload_diagrams = _read_payload_diagrams(repo_root)
    if payload_diagrams is None:
        violations.append("Atlas Mermaid payload is missing or unreadable")
        return tuple(dict.fromkeys(violations))
    payload_by_id = {str(item.get("diagram_id") or "").strip(): item for item in payload_diagrams}
    for row in expected_boxes:
        diagram_id = str(row.get("diagram_id") or "").strip()
        expected_labels = set(str(label) for label in row.get("labels", ()) if str(label))
        if not diagram_id or not expected_labels:
            continue
        payload_row = payload_by_id.get(diagram_id)
        if not payload_row:
            violations.append(f"{diagram_id}: missing from generated Atlas payload")
            continue
        actual_labels = set(atlas_box_explanations.diagram_box_labels(payload_row.get("diagram_boxes", [])))
        missing = sorted(expected_labels - actual_labels)
        if missing:
            violations.append(f"{diagram_id}: generated payload is missing {len(missing)} diagram-box explanations")
    return tuple(dict.fromkeys(violations))


def _topology_integrity_report(*, repo_root: Path) -> dict[str, Any]:
    graph_path = repo_root / TRACEABILITY_GRAPH_RELATIVE_PATH
    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "failed", "error": f"unreadable topology traceability graph: {exc.__class__.__name__}"}
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
    }


def _planned_paths(*, repo_root: Path) -> tuple[str, ...]:
    paths = [
        repo_root / TRACEABILITY_GRAPH_RELATIVE_PATH,
        *[repo_root / token for token in ATLAS_SURFACE_REQUIRED_PATHS],
        _ledger_path(repo_root=repo_root),
    ]
    return tuple(dict.fromkeys(display_path(repo_root=repo_root, path=path) for path in paths))


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
            "v0.1.15 regenerates Atlas browser surfaces with the diagram-box "
            "explanation contract. Mermaid source is scanned for containers and "
            "inner boxes, catalog-authored copy must be clear complete sentences, "
            "and generated payloads expose the full box inventory without rewriting "
            "repo-owned Atlas source truth."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return display_path(repo_root=repo_root, path=path)


def inspect_atlas_box_explanation_migration(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
) -> AtlasBoxExplanationMigrationInspection:
    """Inspect the v0.1.15 Atlas box-explanation migration state without writing."""
    root = Path(repo_root).expanduser().resolve()
    previous = normalize_version(previous_version)
    target = normalize_version(target_version)
    ledger_valid, ledger_stale_reason = _read_ledger(repo_root=root)
    payload, catalog_violations = _load_catalog(root)
    items = _diagram_items(payload)
    expected_boxes = _expected_boxes_by_diagram(repo_root=root, items=items)
    box_violations = (
        *catalog_violations,
        *_catalog_box_inventory_violations(repo_root=root, items=items),
    )
    generated_violations = _generated_surface_violations(
        repo_root=root,
        catalog_exists=(root / CATALOG_RELATIVE_PATH).is_file(),
        expected_boxes=expected_boxes,
    )
    return AtlasBoxExplanationMigrationInspection(
        migration_id=MIGRATION_ID,
        previous_version=previous,
        target_version=target,
        target_in_window=is_at_least(target, TARGET_VERSION),
        previous_requires_migration=not previous or is_before(previous, TARGET_VERSION),
        atlas_catalog_exists=(root / CATALOG_RELATIVE_PATH).is_file(),
        diagram_count=len(items),
        expected_box_count=sum(len(row.get("labels", ())) for row in expected_boxes),
        box_inventory_violations=tuple(dict.fromkeys(box_violations)),
        generated_surface_violations=generated_violations,
        ledger_exists=_ledger_path(repo_root=root).is_file(),
        ledger_valid=ledger_valid,
        ledger_stale_reason="" if ledger_valid or not _ledger_path(repo_root=root).is_file() else ledger_stale_reason,
        ledger_path=display_path(repo_root=root, path=_ledger_path(repo_root=root)),
        planned_paths=_planned_paths(repo_root=root),
    )


def atlas_box_explanation_decision_state(
    *,
    repo_scenario: str,
    inspection: AtlasBoxExplanationMigrationInspection,
) -> tuple[str, str]:
    """Return the migration-runtime decision for the Atlas box-explanation contract."""
    scenario = str(repo_scenario or "").strip()
    if scenario == "legacy_odyssey":
        if inspection.target_in_window:
            return "selected", "Atlas box-explanation migration runs after the legacy root migration"
        return "skipped", "target version is not in target window for the v0.1.15 Atlas box-explanation migration"
    if scenario == "detached_source_local":
        return "blocked", "release migrations are blocked while the product repo is in detached source-local posture"
    if scenario == "product_repo_pinned_dogfood":
        return (
            "skipped",
            "product repo Atlas source truth is validated by maintainer release gates, not consumer migration apply",
        )
    if not inspection.target_in_window:
        return "skipped", "target version is not in target window for the v0.1.15 Atlas box-explanation migration"
    if inspection.ledger_exists and not inspection.ledger_valid:
        return "ledger_stale", f"migration ledger is stale: {inspection.ledger_stale_reason}"
    if inspection.verification_passed:
        return "skipped", "ledger and verification already satisfy the v0.1.15 Atlas box-explanation migration"
    if not inspection.atlas_catalog_exists:
        return "skipped", "repo has no Atlas catalog to migrate"
    if inspection.migration_required:
        return "selected", "Atlas generated surfaces require the v0.1.15 box-explanation contract"
    return "skipped", "migration predicates do not require local Atlas box-explanation changes"


def migrate_atlas_box_explanation_contract(
    *,
    repo_root: str | Path,
    previous_version: str = "",
    target_version: str = "",
) -> AtlasBoxExplanationMigrationResult:
    """Apply the v0.1.15 Atlas box-explanation migration when in scope."""
    root = Path(repo_root).expanduser().resolve()
    previous = normalize_version(previous_version)
    target = normalize_version(target_version)
    inspection = inspect_atlas_box_explanation_migration(
        repo_root=root,
        previous_version=previous,
        target_version=target,
    )
    if not inspection.target_in_window:
        return AtlasBoxExplanationMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="target_not_in_v0_1_15_migration_window",
            ledger_path=inspection.ledger_path,
        )
    if inspection.verification_passed:
        return AtlasBoxExplanationMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="ledger_and_atlas_box_explanations_already_verify",
            ledger_path=inspection.ledger_path,
            verification_result={"status": "passed", "mode": "already_verified"},
        )
    if not inspection.atlas_catalog_exists:
        return AtlasBoxExplanationMigrationResult(
            migration_id=MIGRATION_ID,
            applied=False,
            previous_version=previous,
            target_version=target,
            skipped_reason="no_atlas_catalog",
            ledger_path=inspection.ledger_path,
            verification_result={"status": "skipped", "mode": "no_atlas_catalog"},
        )
    before = _atlas_path_fingerprints(repo_root=root)
    if render_mermaid_catalog.main(["--repo-root", str(root), "--runtime-mode", "standalone"]) != 0:
        raise RuntimeError("Atlas dashboard render failed during v0.1.15 Atlas box-explanation migration")
    if build_traceability_graph.main(["--repo-root", str(root)]) != 0:
        raise RuntimeError("Topology traceability graph build failed during v0.1.15 Atlas box-explanation migration")
    after = _atlas_path_fingerprints(repo_root=root)
    verification = inspect_atlas_box_explanation_migration(
        repo_root=root,
        previous_version=previous,
        target_version=target,
    )
    topology_report = _topology_integrity_report(repo_root=root)
    verification_result = {
        "status": "passed"
        if not verification.box_inventory_violations
        and not verification.generated_surface_violations
        and topology_report.get("status") == "passed"
        else "failed",
        "box_inventory_violations": list(verification.box_inventory_violations),
        "generated_surface_violations": list(verification.generated_surface_violations),
        "diagram_count": verification.diagram_count,
        "expected_box_count": verification.expected_box_count,
        "topology_integrity": topology_report,
    }
    if verification_result["status"] != "passed":
        raise RuntimeError("Atlas box-explanation migration did not verify after apply")
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
    return AtlasBoxExplanationMigrationResult(
        migration_id=MIGRATION_ID,
        applied=True,
        previous_version=previous,
        target_version=target,
        written_paths=written,
        removed_paths=removed,
        ledger_path=ledger_path,
        verification_result=verification_result,
    )


def atlas_box_explanation_migration_ledger_path(*, repo_root: str | Path) -> str:
    """Return the repo-relative v0.1.15 Atlas box-explanation ledger path."""
    root = Path(repo_root).expanduser().resolve()
    return display_path(repo_root=root, path=_ledger_path(repo_root=root))


__all__ = [
    "ATLAS_SURFACE_REQUIRED_PATHS",
    "MIGRATION_ID",
    "MIGRATION_SCHEMA_VERSION",
    "TARGET_VERSION",
    "AtlasBoxExplanationMigrationInspection",
    "AtlasBoxExplanationMigrationResult",
    "atlas_box_explanation_decision_state",
    "atlas_box_explanation_migration_ledger_path",
    "inspect_atlas_box_explanation_migration",
    "migrate_atlas_box_explanation_contract",
]

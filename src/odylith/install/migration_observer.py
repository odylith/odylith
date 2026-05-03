"""Detect installed-consumer impact for maintainer release gates.

The observer is intentionally conservative: it does not decide that a surface
change is unsafe, but it does require an explicit, completed migration
assessment record before release gates can pass. That keeps already-installed
consumer repos in view when maintainers change dashboards, managed guidance,
skills, operator CLI contracts, public docs, or install-managed assets.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from odylith.install.versioning import normalize_version

OBSERVER_SCHEMA_VERSION = "odylith.surface-migration-observer.v1"
MARKER_PREFIX = "migration-observer"
_COMPLETED_STATES = {"finished"}
_RADAR_IDEAS_ROOT = Path("odylith/radar/source/ideas")
_MARKER_RE = re.compile(
    r"\bmigration-observer:[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+(?::[A-Fa-f0-9]{12})?\b"
)
_CACHE_BUSTER_RE = re.compile(r"\?v=[A-Fa-f0-9]{12}\b")
_GENERATED_SURFACE_PREFIXES = (
    "odylith/atlas/",
    "odylith/casebook/",
    "odylith/compass/",
    "odylith/radar/",
    "odylith/registry/",
    "src/odylith/bundle/assets/odylith/atlas/",
    "src/odylith/bundle/assets/odylith/casebook/",
    "src/odylith/bundle/assets/odylith/compass/",
    "src/odylith/bundle/assets/odylith/radar/",
    "src/odylith/bundle/assets/odylith/registry/",
)
_SURFACE_SOURCE_PREFIXES = (
    "odylith/atlas/source/",
    "odylith/casebook/bugs/",
    "odylith/registry/source/",
)
_GENERATED_DERIVATIVE_EXACT_PATHS = {
    "odylith/atlas/source/catalog/diagrams.v1.json",
}
_GENERATED_DERIVATIVE_PREFIXES = (
    "odylith/runtime/delivery_intelligence.v",
)


@dataclass(frozen=True)
class SurfaceClassifier:
    need_id: str
    label: str
    prefixes: tuple[str, ...]
    substrings: tuple[str, ...] = ()

    def matches(self, path: str) -> bool:
        token = _normalize_path(path)
        prefix_match = any(
            token == prefix or token.startswith(f"{prefix}/")
            for prefix in self.prefixes
        )
        substring_match = any(part in token for part in self.substrings)
        return prefix_match or substring_match


@dataclass(frozen=True)
class SurfaceMigrationNeed:
    need_id: str
    label: str
    changed_paths: tuple[str, ...]
    governance_marker: str
    marker_family: str
    change_fingerprint: str
    governance_prompt: str

    def as_dict(self) -> dict[str, object]:
        return {
            "need_id": self.need_id,
            "label": self.label,
            "changed_paths": list(self.changed_paths),
            "governance_marker": self.governance_marker,
            "marker_family": self.marker_family,
            "change_fingerprint": self.change_fingerprint,
            "governance_prompt": self.governance_prompt,
        }


@dataclass(frozen=True)
class SurfaceMigrationRecord:
    workstream_id: str
    title: str
    status: str
    path: str
    markers: tuple[str, ...]

    def completed(self) -> bool:
        return self.status.strip().lower() in _COMPLETED_STATES

    def as_dict(self) -> dict[str, object]:
        return {
            "workstream_id": self.workstream_id,
            "title": self.title,
            "status": self.status,
            "path": self.path,
            "markers": list(self.markers),
            "completed": self.completed(),
        }


@dataclass(frozen=True)
class SurfaceMigrationObserverReport:
    ok: bool
    target_version: str
    changed_paths: tuple[str, ...]
    needs: tuple[SurfaceMigrationNeed, ...]
    records: tuple[SurfaceMigrationRecord, ...]
    blocked_need_ids: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": OBSERVER_SCHEMA_VERSION,
            "ok": self.ok,
            "target_version": self.target_version,
            "changed_paths": list(self.changed_paths),
            "needs": [need.as_dict() for need in self.needs],
            "records": [record.as_dict() for record in self.records],
            "blocked_need_ids": list(self.blocked_need_ids),
            "notes": list(self.notes),
        }


_CLASSIFIERS = (
    SurfaceClassifier(
        need_id="guidance-and-skills",
        label="managed guidance and skill surfaces",
        prefixes=(
            "AGENTS.md",
            ".agents/skills",
            ".claude/skills",
            "odylith/AGENTS.md",
            "odylith/agents-guidelines",
            "odylith/skills",
            "src/odylith/bundle/assets/project-root/.agents/skills",
            "src/odylith/bundle/assets/project-root/.claude/skills",
            "src/odylith/bundle/assets/odylith/agents-guidelines",
            "src/odylith/bundle/assets/odylith/skills",
        ),
    ),
    SurfaceClassifier(
        need_id="operator-cli-contracts",
        label="operator CLI and host command contracts",
        prefixes=(
            "src/odylith/cli.py",
            "src/odylith/runtime/commands",
            "src/odylith/runtime/governance",
            "src/odylith/bundle/assets/project-root/.codex",
            "src/odylith/bundle/assets/project-root/.claude",
            "src/odylith/bundle/assets/project-root/.agents",
        ),
    ),
    SurfaceClassifier(
        need_id="public-docs-and-release-guidance",
        label="public docs and release guidance",
        prefixes=(
            "README.md",
            "docs",
            "odylith/README.md",
            "odylith/CLAUDE.md",
            "odylith/runtime",
            "src/odylith/bundle/assets/odylith/README.md",
            "src/odylith/bundle/assets/odylith/CLAUDE.md",
            "src/odylith/bundle/assets/odylith/runtime",
        ),
    ),
    SurfaceClassifier(
        need_id="browser-surfaces",
        label="browser-rendered governance surfaces",
        prefixes=(
            "odylith/atlas",
            "odylith/casebook",
            "odylith/compass",
            "odylith/radar",
            "odylith/registry",
            "odylith/surfaces",
            "src/odylith/bundle/assets/odylith/atlas",
            "src/odylith/bundle/assets/odylith/casebook",
            "src/odylith/bundle/assets/odylith/compass",
            "src/odylith/bundle/assets/odylith/radar",
            "src/odylith/bundle/assets/odylith/registry",
            "src/odylith/runtime/surfaces",
        ),
    ),
    SurfaceClassifier(
        need_id="install-managed-assets",
        label="install-managed project and bundle assets",
        prefixes=(
            "src/odylith/bundle/assets",
            "src/odylith/install",
        ),
    ),
)


def observe_surface_migration_needs(
    *,
    repo_root: str | Path,
    target_version: str = "",
    changed_paths: Sequence[str] | None = None,
) -> SurfaceMigrationObserverReport:
    """Return maintainer release-gate obligations for changed product surfaces."""
    root = Path(repo_root).expanduser().resolve()
    target = normalize_version(target_version) or "current"
    source_paths = changed_paths if changed_paths is not None else _git_changed_paths(root)
    paths = tuple(_normalize_path(path) for path in source_paths)
    relevant_paths = tuple(path for path in paths if path and not _ignored_path(path))
    records = _observer_records(repo_root=root)
    needs = tuple(
        _need_for(
            repo_root=root,
            classifier=classifier,
            target_version=target,
            changed_paths=relevant_paths,
        )
        for classifier in _CLASSIFIERS
        if any(classifier.matches(path) for path in relevant_paths)
    )
    blocked = tuple(
        need.need_id
        for need in needs
        if not _completed_record_exists(
            records=records,
            marker=need.governance_marker,
        )
    )
    notes = (
        "Surface changes are migration-observed because consumer repos may already carry older installed assets.",
        "Generated dashboard refresh is still not a release migration, but changed rendered surfaces must have a completed migration assessment.",
    )
    return SurfaceMigrationObserverReport(
        ok=not blocked,
        target_version=target,
        changed_paths=relevant_paths,
        needs=needs,
        records=records,
        blocked_need_ids=blocked,
        notes=notes,
    )


def _need_for(
    *,
    repo_root: Path,
    classifier: SurfaceClassifier,
    target_version: str,
    changed_paths: Sequence[str],
) -> SurfaceMigrationNeed:
    paths = tuple(path for path in changed_paths if classifier.matches(path))
    marker_family = f"{MARKER_PREFIX}:{target_version}:{classifier.need_id}"
    fingerprint = _change_fingerprint(repo_root=repo_root, paths=paths)
    marker = f"{marker_family}:{fingerprint}"
    return SurfaceMigrationNeed(
        need_id=classifier.need_id,
        label=classifier.label,
        changed_paths=paths,
        governance_marker=marker,
        marker_family=marker_family,
        change_fingerprint=fingerprint,
        governance_prompt=(
            "Create or complete a Radar migration-assessment workstream with "
            f"`{marker}` after assessing existing consumer installs for {classifier.label}. "
            "The fingerprint binds the assessment to the observed changed path contents."
        ),
    )


def _completed_record_exists(*, records: Sequence[SurfaceMigrationRecord], marker: str) -> bool:
    return any(record.completed() and marker in record.markers for record in records)


def _change_fingerprint(*, repo_root: Path, paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        token = _normalize_path(path)
        digest.update(token.encode("utf-8"))
        digest.update(b"\0")
        absolute = repo_root / token
        try:
            if absolute.is_symlink():
                digest.update(b"symlink\0")
                digest.update(os.readlink(absolute).encode("utf-8", errors="surrogateescape"))
            elif absolute.is_file():
                if _generated_surface_asset(token) or _generated_derivative_asset(token):
                    digest.update(b"generated-surface-asset\0")
                else:
                    digest.update(b"file\0")
                    digest.update(_fingerprintable_file_digest(absolute).encode("ascii"))
            elif absolute.exists():
                digest.update(b"present-non-file\0")
            else:
                digest.update(b"missing\0")
        except OSError as exc:
            digest.update(b"unreadable\0")
            digest.update(type(exc).__name__.encode("ascii", errors="ignore"))
    return digest.hexdigest()[:12]


def _generated_surface_asset(path: str) -> bool:
    token = _normalize_path(path)
    if any(token.startswith(prefix) for prefix in _SURFACE_SOURCE_PREFIXES):
        return False
    return any(token.startswith(prefix) for prefix in _GENERATED_SURFACE_PREFIXES)


def _generated_derivative_asset(path: str) -> bool:
    token = _normalize_path(path)
    if token in _GENERATED_DERIVATIVE_EXACT_PATHS:
        return True
    if any(token.startswith(prefix) and token.endswith(".json") for prefix in _GENERATED_DERIVATIVE_PREFIXES):
        return True
    return token.startswith("odylith/registry/source/components/") and token.endswith("/FORENSICS.v1.json")


def _fingerprintable_file_digest(path: Path) -> str:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        payload = raw
    else:
        normalized = _MARKER_RE.sub(
            "migration-observer:<version>:<surface>:<fingerprint>",
            text,
        )
        normalized = _CACHE_BUSTER_RE.sub("?v=<fingerprint>", normalized)
        payload = normalized.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _observer_records(*, repo_root: Path) -> tuple[SurfaceMigrationRecord, ...]:
    records: list[SurfaceMigrationRecord] = []
    ideas_root = repo_root / _RADAR_IDEAS_ROOT
    if not ideas_root.is_dir():
        return ()
    for path in sorted(ideas_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        markers = tuple(sorted(set(_MARKER_RE.findall(text))))
        if not markers:
            continue
        records.append(
            SurfaceMigrationRecord(
                workstream_id=_field(text, "idea_id"),
                title=_field(text, "title"),
                status=_field(text, "status"),
                path=path.relative_to(repo_root).as_posix(),
                markers=markers,
            )
        )
    return tuple(records)


def _field(text: str, name: str) -> str:
    prefix = f"{name}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _git_changed_paths(repo_root: Path) -> tuple[str, ...]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return ()
    if result.returncode != 0:
        return ()
    paths: list[str] = []
    for line in result.stdout.splitlines():
        token = line[3:].strip()
        if " -> " in token:
            token = token.rsplit(" -> ", 1)[-1].strip()
        if token:
            paths.append(token)
    return tuple(paths)


def _ignored_path(path: str) -> bool:
    token = _normalize_path(path)
    return (
        token.startswith("odylith/radar/source/ideas/")
        or token.startswith("odylith/radar/source/releases/")
        or token == "odylith/radar/source/INDEX.md"
    )


def _normalize_path(path: str) -> str:
    token = str(path or "").strip().replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    return token


__all__ = [
    "MARKER_PREFIX",
    "OBSERVER_SCHEMA_VERSION",
    "SurfaceMigrationNeed",
    "SurfaceMigrationObserverReport",
    "SurfaceMigrationRecord",
    "observe_surface_migration_needs",
]

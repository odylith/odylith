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
import stat
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
_MARKER_PLACEHOLDER = "migration-observer:<version>:<surface>:<fingerprint>"
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
    scope_kind: str = "explicit_paths"
    base_commit: str = ""
    candidate_commit: str = ""
    scope_error: str = ""

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
            "scope": {
                "kind": self.scope_kind,
                "base_commit": self.base_commit,
                "candidate_commit": self.candidate_commit,
                "error": self.scope_error,
                "assessment_status": (
                    "unproven" if self.scope_error else
                    "not_applicable" if not self.needs else
                    "passed" if self.ok else "failed"
                ),
            },
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
    base_ref: str = "",
    require_release_scope: bool = False,
) -> SurfaceMigrationObserverReport:
    """Return maintainer release-gate obligations for changed product surfaces."""
    root = Path(repo_root).expanduser().resolve()
    target = normalize_version(target_version) or "current"
    scope_kind = "explicit_paths"
    base_commit = candidate_commit = scope_error = ""
    try:
        if base_ref and changed_paths is not None:
            raise ValueError("Release comparison cannot be narrowed by explicit changed paths.")
        if require_release_scope and not base_ref:
            raise ValueError("Release comparison requires --base-ref for the verified previous published release.")
        if changed_paths is None:
            candidate_commit = _git_output(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
            git_root = Path(os.fsdecode(_git_output(root, "rev-parse", "--show-toplevel")).rstrip("\n"))
            if git_root.resolve() != root:
                raise ValueError("Migration comparison requires the repository root, not a nested directory.")
            if base_ref:
                base_commit = _git_output(
                    root, "rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}",
                ).decode().strip()
            source_paths = _git_changed_paths(root, base_commit, candidate_commit)
            scope_kind = "release_comparison" if base_ref else "working_tree"
            if _git_output(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip() != candidate_commit:
                raise ValueError("Candidate commit changed during migration comparison; rerun on a frozen tree.")
        else:
            source_paths = changed_paths
    except ValueError as exc:
        source_paths = ()
        scope_kind = "unavailable"
        scope_error = str(exc)
    paths = tuple(_normalize_path(path) for path in source_paths)
    relevant_paths = tuple(path for path in paths if path and not _ignored_path(path))
    records = _observer_records(repo_root=root)
    needs = tuple(
        _need_for(
            repo_root=root,
            classifier=classifier,
            target_version=target,
            changed_paths=relevant_paths,
            base_commit=base_commit,
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
        ok=not blocked and not scope_error,
        target_version=target,
        changed_paths=relevant_paths,
        needs=needs,
        records=records,
        blocked_need_ids=blocked,
        notes=notes,
        scope_kind=scope_kind,
        base_commit=base_commit,
        candidate_commit=candidate_commit,
        scope_error=scope_error,
    )


def _need_for(
    *,
    repo_root: Path,
    classifier: SurfaceClassifier,
    target_version: str,
    changed_paths: Sequence[str],
    base_commit: str = "",
) -> SurfaceMigrationNeed:
    paths = tuple(path for path in changed_paths if classifier.matches(path))
    marker_family = f"{MARKER_PREFIX}:{target_version}:{classifier.need_id}"
    fingerprint = _change_fingerprint(repo_root=repo_root, paths=paths, base_commit=base_commit)
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
            "The fingerprint binds the assessment to the comparison base, paths, modes and contents."
        ),
    )


def _completed_record_exists(*, records: Sequence[SurfaceMigrationRecord], marker: str) -> bool:
    return any(record.completed() and marker in record.markers for record in records)


def _change_fingerprint(*, repo_root: Path, paths: Sequence[str], base_commit: str = "") -> str:
    digest = hashlib.sha256()
    if base_commit:
        digest.update(b"release-base\0")
        digest.update(base_commit.encode("ascii"))
        digest.update(b"\0")
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
                digest.update(f"mode:{stat.S_IMODE(absolute.stat().st_mode):o}\0".encode("ascii"))
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
        normalized = _MARKER_RE.sub(_MARKER_PLACEHOLDER, text)
        normalized = _CACHE_BUSTER_RE.sub("?v=<fingerprint>", normalized)
        normalized = _drop_observer_marker_lines(normalized)
        payload = normalized.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _drop_observer_marker_lines(text: str) -> str:
    return "".join(line for line in text.splitlines(keepends=True) if _MARKER_PLACEHOLDER not in line)


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


def _git_output(repo_root: Path, *args: str) -> bytes:
    """Git discovery failure is missing proof, never an empty successful scope."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"Migration comparison Git discovery failed: {type(exc).__name__}.") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Migration comparison Git discovery failed: {detail or result.returncode}")
    return result.stdout


def _git_changed_paths(repo_root: Path, base_commit: str, candidate_commit: str) -> tuple[str, ...]:
    # Query exactly the declared consumer-surface families. Unrelated repository
    # content (including evaluation corpora) does not belong in migration scope.
    pathspecs = tuple(f":(literal){path}" for path in sorted({
        prefix for classifier in _CLASSIFIERS for prefix in classifier.prefixes
    }))
    tracked = _git_output(repo_root, "ls-files", "-v", "-z", "--", *pathspecs)
    if any(entry[:1] == b"S" or entry[:1].islower() for entry in tracked.split(b"\0") if entry):
        raise ValueError(
            "Migration comparison cannot verify hidden tracked consumer surfaces. "
            "Materialize the checkout and clear skip-worktree or assume-unchanged flags before assessment."
        )
    diff = ("diff", "--no-ext-diff", "--no-textconv", "--name-only", "--no-renames", "-z")
    commands = [
        (*diff, "--cached", candidate_commit, "--", *pathspecs),
        (*diff, "--", *pathspecs),
        ("ls-files", "--others", "--exclude-standard", "-z", "--", *pathspecs),
    ]
    if base_commit:
        commands.append((*diff, base_commit, candidate_commit, "--", *pathspecs))
    return tuple(sorted({
        os.fsdecode(path)
        for command in commands
        for path in _git_output(repo_root, *command).split(b"\0")
        if path
    }))


def _ignored_path(path: str) -> bool:
    token = _normalize_path(path)
    return (
        token.startswith("odylith/radar/source/ideas/")
        or token.startswith("odylith/radar/source/releases/")
        or token == "odylith/radar/source/INDEX.md"
    )


def _normalize_path(path: str) -> str:
    token = str(path or "")
    if os.sep != "/":
        token = token.replace(os.sep, "/")
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

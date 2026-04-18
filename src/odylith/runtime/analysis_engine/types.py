"""Shared types for the Odylith analysis engine."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Any


_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Convert free-form text into a lowercase slug suitable for ids."""
    return _SLUGIFY_RE.sub("-", str(value or "").strip().lower()).strip("-") or "component"


def humanize(value: str) -> str:
    """Convert a slug-like token into title-style display text."""
    token = str(value or "").strip().replace("-", " ").replace("_", " ")
    return " ".join(w.capitalize() for w in token.split()) if token else ""


def progress(msg: str) -> None:
    """Emit interactive progress output only when stderr is a TTY."""
    if not sys.stderr.isatty():
        return
    print(f"  {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkstreamSuggestion:
    """Suggested Radar workstream extracted from analysis-engine results."""

    title: str
    description: str


@dataclass(frozen=True)
class ComponentSuggestion:
    """Suggested logical Registry component boundary."""

    component_id: str
    label: str
    path: str
    description: str
    n_modules: int = 0
    n_inbound: int = 0
    n_outbound: int = 0
    member_paths: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiagramSuggestion:
    """Suggested Atlas diagram candidate."""

    slug: str
    title: str
    description: str


@dataclass(frozen=True)
class IssueSuggestion:
    """Suggested Casebook issue candidate."""

    title: str
    detail: str
    severity: str = "medium"


@dataclass(frozen=True)
class ComponentPosture:
    """Governance posture summary for one candidate component."""

    component_id: str
    posture_mode: str
    governance_lag: int
    blast_radius: str
    blast_severity: int
    evidence_quality: str


@dataclass
class RepoIdentity:
    """High-level identity and topology summary for the scanned repository."""

    name: str = ""
    description: str = ""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_manager: str = ""
    monorepo: bool = False
    workspace_dirs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ImportArtifact:
    """One scanned source artifact and the imports it declares."""

    path: str
    module_name: str
    language: str
    imports: tuple[str, ...]


@dataclass(frozen=True)
class ImportEdge:
    """Directed edge between two scanned import artifacts."""

    source_path: str
    target_path: str


@dataclass
class ScanContext:
    """Side-channel data collected during single-pass file scanning."""
    todos: list[tuple[str, str]] = field(default_factory=list)
    test_files: set[str] = field(default_factory=set)
    file_count: int = 0
    language_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class ShowResult:
    """Top-level analysis-engine result used by `odylith show` surfaces."""

    identity: RepoIdentity = field(default_factory=RepoIdentity)
    workstreams: list[WorkstreamSuggestion] = field(default_factory=list)
    components: list[ComponentSuggestion] = field(default_factory=list)
    component_postures: dict[str, ComponentPosture] = field(default_factory=dict)
    diagrams: list[DiagramSuggestion] = field(default_factory=list)
    issues: list[IssueSuggestion] = field(default_factory=list)
    already_governed: dict[str, bool] = field(default_factory=dict)
    scan_context: ScanContext = field(default_factory=ScanContext)
    total_modules: int = 0

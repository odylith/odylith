"""Freshness guard for the generated Radar traceability graph."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


TRACEABILITY_SOURCE_VERSION = "traceability-source-v1"

_TRACEABILITY_SOURCE_TOKENS: tuple[str, ...] = (
    "odylith/radar/source/INDEX.md",
    "odylith/radar/source/ideas",
    "odylith/radar/source/programs",
    "odylith/radar/source/releases",
    "odylith/technical-plans/INDEX.md",
    "odylith/technical-plans/in-progress",
    "odylith/technical-plans/done",
    "odylith/technical-plans/parked",
    "odylith/atlas/source/catalog/diagrams.v1.json",
    "odylith/registry/source/component_registry.v1.json",
    "odylith/registry/source/components",
)


@dataclass(frozen=True)
class TraceabilitySourceFingerprint:
    """Content-backed fingerprint for source truth consumed by traceability."""

    version: str
    algorithm: str
    digest: str
    file_count: int
    source_paths: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "algorithm": self.algorithm,
            "digest": self.digest,
            "file_count": self.file_count,
            "source_paths": list(self.source_paths),
        }


def _iter_source_files(repo_root: Path) -> Iterable[tuple[str, Path]]:
    root = Path(repo_root).resolve()
    for token in _TRACEABILITY_SOURCE_TOKENS:
        candidate = (root / token).resolve()
        if candidate.is_file():
            yield token, candidate
            continue
        if not candidate.is_dir():
            continue
        for path in sorted(node for node in candidate.rglob("*") if node.is_file()):
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            yield rel, path


def traceability_source_fingerprint(*, repo_root: Path) -> TraceabilitySourceFingerprint:
    digest = hashlib.sha256()
    paths: list[str] = []
    for rel, path in _iter_source_files(repo_root):
        paths.append(rel)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"<unreadable>")
        digest.update(b"\0")
    digest.update(TRACEABILITY_SOURCE_VERSION.encode("utf-8"))
    return TraceabilitySourceFingerprint(
        version=TRACEABILITY_SOURCE_VERSION,
        algorithm="sha256-content",
        digest=digest.hexdigest(),
        file_count=len(paths),
        source_paths=tuple(paths),
    )


def _payload_fingerprint(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = payload.get("source_fingerprint")
    return dict(raw) if isinstance(raw, Mapping) else {}


def traceability_graph_is_fresh(*, repo_root: Path, graph_path: Path) -> bool:
    target = Path(graph_path)
    if not target.is_file():
        return False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, Mapping):
        return False
    current = traceability_source_fingerprint(repo_root=repo_root)
    stored = _payload_fingerprint(payload)
    return (
        str(stored.get("version", "")).strip() == current.version
        and str(stored.get("algorithm", "")).strip() == current.algorithm
        and str(stored.get("digest", "")).strip() == current.digest
        and int(stored.get("file_count", -1) or -1) == current.file_count
    )


def ensure_traceability_graph_fresh(*, repo_root: Path, graph_path: Path) -> bool:
    """Regenerate the traceability graph when source truth moved ahead of it."""

    root = Path(repo_root).resolve()
    target = Path(graph_path).resolve()
    if traceability_graph_is_fresh(repo_root=root, graph_path=target):
        return False
    from odylith.runtime.governance import build_traceability_graph

    try:
        output = target.relative_to(root).as_posix()
    except ValueError:
        output = str(target)
    rc = build_traceability_graph.main(["--repo-root", str(root), "--output", output])
    if rc != 0:
        raise RuntimeError(f"traceability graph refresh failed with exit code {rc}")
    return True


__all__ = [
    "TRACEABILITY_SOURCE_VERSION",
    "TraceabilitySourceFingerprint",
    "ensure_traceability_graph_fresh",
    "traceability_graph_is_fresh",
    "traceability_source_fingerprint",
]

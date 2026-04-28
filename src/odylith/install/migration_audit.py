"""Migration audit records for install and upgrade flows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import subprocess

from odylith.install.fs import atomic_write_text

_LEGACY_NEEDLE = "odyssey"
_TEXT_FILE_SUFFIXES = frozenset(
    {
        "",
        ".css",
        ".html",
        ".js",
        ".json",
        ".jsonl",
        ".md",
        ".mjs",
        ".mmd",
        ".py",
        ".sh",
        ".svg",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
_EXCLUDED_PREFIXES = (
    ".git/",
    ".odylith/cache/",
    ".odylith/locks/",
    ".odylith/logs/",
    ".odylith/runtime/",
    ".odylith/state/migration/",
    ".odylith/state/migrations/",
    ".cache/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "__pycache__/",
    "build/",
    "dist/",
    "node_modules/",
    "scratch/",
    "temp/",
    "tmp/",
    "venv/",
)
_GENERATED_SURFACE_EXACT_PATHS = frozenset(
    {
        "odylith/index.html",
        "odylith/tooling-app.v1.js",
        "odylith/tooling-payload.v1.js",
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-app.v1.js",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/casebook/casebook-app.v1.js",
        "odylith/casebook/casebook-payload.v1.js",
        "odylith/casebook/casebook.html",
        "odylith/compass/compass-app.v1.js",
        "odylith/compass/compass-payload.v1.js",
        "odylith/compass/compass.html",
        "odylith/compass/compass-runtime-truth.v1.js",
        "odylith/radar/backlog-app.v1.js",
        "odylith/radar/backlog-payload.v1.js",
        "odylith/radar/radar.html",
        "odylith/radar/standalone-pages.v1.js",
        "odylith/radar/traceability-autofix-report.v1.json",
        "odylith/radar/traceability-graph.v1.json",
        "odylith/registry/registry-app.v1.js",
        "odylith/registry/registry-payload.v1.js",
        "odylith/registry/registry.html",
    }
)
_GENERATED_SURFACE_PREFIXES = (
    "odylith/atlas/source/catalog/",
    "odylith/casebook/casebook-detail-shard-",
    "odylith/compass/runtime/",
    "odylith/radar/backlog-detail-shard-",
    "odylith/radar/backlog-document-shard-",
    "odylith/radar/source/ui/",
    "odylith/registry/registry-detail-shard-",
    "odylith/runtime/",
)


@dataclass(frozen=True)
class LegacyReferenceAudit:
    report_path: Path
    file_count: int
    hit_count: int
    sample_paths: tuple[str, ...]


def audit_legacy_odyssey_references(*, repo_root: str | Path) -> LegacyReferenceAudit:
    root = Path(repo_root).expanduser().resolve()
    hits: list[tuple[str, int, str]] = []
    files_with_hits: list[str] = []
    for relative_path in _tracked_text_paths(root):
        path = root / relative_path
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        matched = False
        for line_number, line in enumerate(lines, start=1):
            if _LEGACY_NEEDLE not in line.lower():
                continue
            hits.append((relative_path, line_number, line.strip()))
            matched = True
        if matched:
            files_with_hits.append(relative_path)
    report_dir = root / ".odylith" / "state" / "migration"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "stale-odyssey-reference-audit.md"
    atomic_write_text(report_path, _render_report(root=root, hits=hits), encoding="utf-8")
    sample_paths = tuple(files_with_hits[:5])
    return LegacyReferenceAudit(
        report_path=report_path,
        file_count=len(files_with_hits),
        hit_count=len(hits),
        sample_paths=sample_paths,
    )


def _tracked_text_paths(repo_root: Path) -> tuple[str, ...]:
    if (repo_root / ".git").exists():
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-z"],
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            return tuple(
                relative_path
                for relative_path in (
                    token.decode("utf-8", errors="ignore")
                    for token in completed.stdout.split(b"\0")
                    if token
                )
                if _include_candidate(relative_path)
            )
    discovered: list[str] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative_path = path.relative_to(repo_root).as_posix()
        if _include_candidate(relative_path):
            discovered.append(relative_path)
    return tuple(discovered)


def _include_candidate(relative_path: str) -> bool:
    normalized = str(relative_path or "").strip()
    if not normalized:
        return False
    if any(normalized == prefix[:-1] or normalized.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
        return False
    if _is_generated_surface_path(normalized):
        return False
    suffix = Path(normalized).suffix.lower()
    return suffix in _TEXT_FILE_SUFFIXES


def _is_generated_surface_path(relative_path: str) -> bool:
    normalized = str(relative_path or "").strip().strip("/").lower()
    if normalized in _GENERATED_SURFACE_EXACT_PATHS:
        return True
    return any(normalized.startswith(prefix) for prefix in _GENERATED_SURFACE_PREFIXES)


def _render_report(*, root: Path, hits: Iterable[tuple[str, int, str]]) -> str:
    hit_rows = list(hits)
    lines = [
        "# Stale `odyssey` Reference Audit",
        "",
        f"- Repo root: {root}",
        f"- Generated (UTC): {datetime.now(UTC).isoformat()}",
        f"- Matches: {len(hit_rows)}",
        "",
    ]
    if not hit_rows:
        lines.append(
            "No stale `odyssey` references were found in tracked text files "
            "outside managed runtime, cache, generated, and vendor trees."
        )
        lines.append("")
        return "\n".join(lines)
    current_path = ""
    for relative_path, line_number, line in hit_rows:
        if relative_path != current_path:
            if current_path:
                lines.append("")
            current_path = relative_path
            lines.append(f"## {relative_path}")
        lines.append(f"- L{line_number}: {line}")
    lines.append("")
    return "\n".join(lines)

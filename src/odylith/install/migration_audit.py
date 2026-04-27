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
    ".odylith/runtime/",
    ".odylith/state/migration/",
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
    suffix = Path(normalized).suffix.lower()
    return suffix in _TEXT_FILE_SUFFIXES


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
        lines.append("No stale `odyssey` references were found in tracked text files outside managed runtime and cache trees.")
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

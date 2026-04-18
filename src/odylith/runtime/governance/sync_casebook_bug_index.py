from __future__ import annotations

import argparse
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from odylith.runtime.common.casebook_bug_ids import BUG_ID_FIELD, normalize_casebook_bug_id, resolve_casebook_bug_id
from odylith.runtime.common.consumer_profile import truth_root_path
from odylith.runtime.governance import casebook_source_validation


_BUG_METADATA_LINE_RE = re.compile(r"^-?\s*([A-Za-z0-9/() _.-]+):\s*(.*)$")
_BUG_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLUG_DATE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<title>.+)$")
_EXPLICIT_CASEBOOK_BUG_ID_RE = re.compile(r"^CB-(?P<number>\d{3,})$")
_CANONICAL_STATUS = {
    "open": "Open",
    "mitigated": "Mitigated",
    "monitoring": "Monitoring",
    "fixed": "Closed",
    "closed": "Closed",
}


@dataclass(frozen=True)
class BugIndexRow:
    """One rendered row in the authoritative Casebook bug index."""

    bug_id: str
    date: str
    title: str
    severity: str
    components: str
    status: str
    link: str


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Casebook bug-index synchronization."""
    parser = argparse.ArgumentParser(
        prog="odylith governance sync-casebook-bug-index",
        description="Rebuild the Casebook bug index from authoritative markdown bug files.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.set_defaults(migrate_bug_ids=True)
    parser.add_argument(
        "--migrate-bug-ids",
        dest="migrate_bug_ids",
        action="store_true",
        help="Force Bug ID backfill for legacy Casebook bug markdown before rebuilding the index.",
    )
    parser.add_argument(
        "--skip-bug-id-migration",
        dest="migrate_bug_ids",
        action="store_false",
        help="Skip automatic Bug ID backfill while rebuilding the index.",
    )
    return parser.parse_args(argv)


def _canonical_status(value: str) -> str:
    """Normalize raw bug status text onto the canonical index labels."""
    token = str(value or "").strip()
    if not token:
        return "Open"
    return _CANONICAL_STATUS.get(token.lower(), token)


def _slug_to_title(slug: str) -> str:
    """Derive a display title from the markdown filename slug."""
    token = str(slug).strip().removesuffix(".md")
    match = _SLUG_DATE_RE.match(token)
    if match is not None:
        token = match.group("title")
    title = token.replace("-", " ").strip()
    return title[:1].upper() + title[1:] if title else "Untitled bug"


def _parse_bug_fields(path: Path) -> dict[str, str]:
    """Parse the metadata fields from one Casebook markdown bug file."""
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("#"):
            if current_key is not None:
                fields[current_key] = "\n".join(line.rstrip() for line in current_lines).strip()
                current_key = None
                current_lines = []
            continue
        match = _BUG_METADATA_LINE_RE.fullmatch(stripped)
        if match is not None:
            if current_key is not None:
                fields[current_key] = "\n".join(line.rstrip() for line in current_lines).strip()
            current_key = str(match.group(1)).strip()
            initial = str(match.group(2)).rstrip()
            current_lines = [initial] if initial else []
            continue
        if current_key is None:
            continue
        current_lines.append(raw.rstrip())
    if current_key is not None:
        fields[current_key] = "\n".join(line.rstrip() for line in current_lines).strip()
    return fields


def _should_skip_bug_markdown(*, bug_root: Path, path: Path) -> bool:
    """Return whether a markdown path should be skipped by the bug-index scan."""
    rel = path.relative_to(bug_root).as_posix()
    if rel in {"AGENTS.md", "CLAUDE.md", "INDEX.md"}:
        return True
    return any(part.startswith(".") for part in path.relative_to(bug_root).parts)


def _bug_files(bug_root: Path) -> list[Path]:
    """Return the authoritative markdown bug files that feed the index."""
    if not bug_root.is_dir():
        return []
    rows: list[Path] = []
    for path in bug_root.rglob("*.md"):
        if _should_skip_bug_markdown(bug_root=bug_root, path=path):
            continue
        rows.append(path)
    return sorted(rows)


def _build_bug_row(*, bug_root: Path, path: Path) -> BugIndexRow:
    """Build one index row from a markdown bug record."""
    rel = path.relative_to(bug_root).as_posix()
    fields = _parse_bug_fields(path)
    match = _SLUG_DATE_RE.match(path.name.removesuffix(".md"))
    date = str(fields.get("Created", "")).strip()
    if not _BUG_DATE_RE.fullmatch(date):
        date = match.group("date") if match is not None else ""
    return BugIndexRow(
        bug_id=resolve_casebook_bug_id(
            explicit_bug_id=str(fields.get(BUG_ID_FIELD, "")).strip(),
            seed=rel,
        ),
        date=date,
        title=_slug_to_title(path.name),
        severity=str(fields.get("Severity", "")).strip() or "Unknown",
        components=(
            str(fields.get("Components Affected", "")).strip()
            or str(fields.get("Ownership", "")).strip()
            or "Unspecified"
        ),
        status=_canonical_status(str(fields.get("Status", "")).strip()),
        link=rel,
    )


def load_bug_rows_from_source(*, repo_root: Path) -> list[BugIndexRow]:
    """Load and normalize all Casebook bug rows from markdown source."""
    bug_root = truth_root_path(repo_root=repo_root, key="casebook_bugs")
    rows = [_build_bug_row(bug_root=bug_root, path=path) for path in _bug_files(bug_root)]
    _assert_unique_bug_ids(rows=rows)
    return rows


def _assert_unique_bug_ids(*, rows: Sequence[BugIndexRow]) -> None:
    """Fail closed when two markdown bug records claim the same Bug ID."""
    seen: dict[str, str] = {}
    for row in rows:
        bug_id = str(row.bug_id).strip()
        if not bug_id:
            continue
        prior = seen.get(bug_id)
        if prior is None:
            seen[bug_id] = row.link
            continue
        raise ValueError(
            f"duplicate Casebook bug ID {bug_id!r} in {prior!r} and {row.link!r}"
        )


def _render_bug_text_with_bug_id(*, text: str, bug_id: str) -> str:
    """Insert or replace the Bug ID field in markdown bug text."""
    rendered: list[str] = []
    inserted = False
    replaced = False
    lines = str(text).splitlines()
    for raw in lines:
        stripped = raw.strip()
        if not replaced and stripped.lower().startswith("- bug id:"):
            rendered.append(f"- Bug ID: {bug_id}")
            replaced = True
            inserted = True
            continue
        if not inserted and _BUG_METADATA_LINE_RE.fullmatch(stripped):
            rendered.extend([f"- Bug ID: {bug_id}", ""])
            inserted = True
        rendered.append(raw)
    if not inserted:
        insert_at = 0
        while insert_at < len(rendered) and (
            not str(rendered[insert_at]).strip() or str(rendered[insert_at]).lstrip().startswith("#")
        ):
            insert_at += 1
        rendered[insert_at:insert_at] = [f"- Bug ID: {bug_id}", ""]
    return "\n".join(rendered).rstrip() + "\n"


def migrate_casebook_bug_ids(*, repo_root: Path) -> list[Path]:
    """Backfill missing Casebook Bug IDs while preserving existing numbering."""
    root = Path(repo_root).resolve()
    bug_root = truth_root_path(repo_root=root, key="casebook_bugs")
    files = _bug_files(bug_root)
    existing_numeric_ids: list[int] = []
    missing: list[Path] = []
    for path in files:
        fields = _parse_bug_fields(path)
        bug_id = normalize_casebook_bug_id(str(fields.get(BUG_ID_FIELD, "")).strip())
        match = _EXPLICIT_CASEBOOK_BUG_ID_RE.fullmatch(bug_id)
        if match is not None:
            existing_numeric_ids.append(int(match.group("number")))
            continue
        if bug_id:
            continue
        missing.append(path)
    next_number = max(existing_numeric_ids, default=0) + 1
    updated: list[Path] = []
    for path in missing:
        bug_id = f"CB-{next_number:03d}"
        next_number += 1
        original = path.read_text(encoding="utf-8")
        rendered = _render_bug_text_with_bug_id(text=original, bug_id=bug_id)
        if original != rendered:
            path.write_text(rendered, encoding="utf-8")
            updated.append(path)
    return updated


def _render_table(rows: Iterable[BugIndexRow]) -> list[str]:
    """Render a bug-index markdown table for one status section."""
    ordered = list(rows)
    if not ordered:
        return ["None."]
    lines = [
        "| Bug ID | Date | Title | Severity | Components | Status | Link |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in ordered:
        lines.append(
            f"| {row.bug_id} | {row.date} | {row.title} | {row.severity} | {row.components} | {row.status} | "
            f"[{row.link}]({row.link}) |"
        )
    return lines


def render_bug_index(*, repo_root: Path) -> str:
    """Render the authoritative markdown Casebook bug index from source files."""
    rows = load_bug_rows_from_source(repo_root=repo_root)
    open_rows = sorted(
        [row for row in rows if row.status != "Closed"],
        key=lambda row: (row.date, row.title.lower()),
        reverse=True,
    )
    closed_rows = sorted(
        [row for row in rows if row.status == "Closed"],
        key=lambda row: (row.date, row.title.lower()),
        reverse=True,
    )
    return "\n".join(
        [
            "# Bug Index",
            "",
            f"Last updated (UTC): {dt.datetime.now(dt.UTC).date().isoformat()}",
            "",
            "## Open Bugs",
            "",
            *_render_table(open_rows),
            "",
            "## Closed Bugs",
            "",
            *_render_table(closed_rows),
            "",
        ]
    )


def sync_casebook_bug_index(*, repo_root: Path, migrate_bug_ids: bool = True) -> Path:
    """Rebuild the Casebook bug index from markdown source records."""
    root = Path(repo_root).resolve()
    bug_root = truth_root_path(repo_root=root, key="casebook_bugs")
    bug_root.mkdir(parents=True, exist_ok=True)
    if migrate_bug_ids:
        migrate_casebook_bug_ids(repo_root=root)
    validation = casebook_source_validation.validate_casebook_sources(repo_root=root)
    if not validation.passed:
        first_issue = validation.issues[0]
        raise ValueError(
            "Casebook source validation failed before index refresh; "
            f"{first_issue.render(repo_root=validation.repo_root)}. "
            "Run `odylith casebook validate --repo-root .`."
        )
    index_path = bug_root / "INDEX.md"
    rendered = render_bug_index(repo_root=root)
    if not index_path.is_file() or index_path.read_text(encoding="utf-8") != rendered:
        index_path.write_text(rendered, encoding="utf-8")
    return index_path


def _print_casebook_cli_failure(*, repo_root: Path, error: ValueError) -> int:
    """Render the most useful CLI failure for bug-index sync errors."""
    result = casebook_source_validation.validate_casebook_sources(repo_root=repo_root)
    if not result.passed:
        casebook_source_validation.print_casebook_source_validation_report(result)
        return 2
    print(f"error: {error}")
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for Casebook bug-index synchronization."""
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        sync_casebook_bug_index(
            repo_root=repo_root,
            migrate_bug_ids=bool(args.migrate_bug_ids),
        )
    except ValueError as exc:
        return _print_casebook_cli_failure(repo_root=repo_root, error=exc)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

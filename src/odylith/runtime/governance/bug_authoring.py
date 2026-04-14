"""CLI backend for `odylith bug capture` — create a Casebook bug record.

Creates a new bug file in `odylith/casebook/bugs/` with a properly assigned
CB-### ID and patches the INDEX.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

_CASEBOOK_BUGS_RELATIVE = Path("odylith/casebook/bugs")
_BUG_ID_RE = re.compile(r"^CB-(\d{3,})$")
_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    token = _SLUGIFY_RE.sub("-", str(value or "").strip().lower()).strip("-")
    return token[:80] if token else "bug"


@dataclass(frozen=True)
class CreatedBug:
    bug_id: str
    title: str
    bug_path: Path
    severity: str
    component: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "title": self.title,
            "bug_path": str(self.bug_path),
            "severity": self.severity,
            "component": self.component,
        }


def _next_bug_id(bugs_dir: Path) -> str:
    """Scan existing bug files and return the next CB-### ID."""
    max_id = 0
    if not bugs_dir.is_dir():
        return "CB-001"
    try:
        for entry in bugs_dir.iterdir():
            if not entry.is_file() or entry.suffix != ".md":
                continue
            try:
                text = entry.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in text.splitlines()[:5]:
                stripped = line.strip().lstrip("- ").strip()
                if stripped.startswith("Bug ID:"):
                    token = stripped.split(":", 1)[1].strip()
                    match = _BUG_ID_RE.fullmatch(token)
                    if match:
                        max_id = max(max_id, int(match.group(1)))
    except OSError:
        pass
    return f"CB-{max_id + 1:03d}"


def _build_bug_text(
    *,
    bug_id: str,
    title: str,
    severity: str,
    component: str,
    today: dt.date,
) -> str:
    return f"""- Bug ID: {bug_id}

- Status: Open

- Created: {today.isoformat()}

- Severity: {severity}

- Reproducibility: TBD

- Type: Product

- Description: {title}

- Impact: TBD — describe the user-facing consequences.

- Components Affected: {component or "TBD"}

- Environment(s): TBD

- Root Cause: TBD — analyze the root cause during investigation.

- Solution: TBD — describe the fix once identified.

- Verification: TBD — describe how to verify the fix.

- Prevention: TBD — describe what prevents recurrence.

- Detected By: `odylith show`

- Failure Signature: TBD

- Trigger Path: TBD

- Ownership: product

- Timeline: Captured {today.isoformat()} through `odylith bug capture`.

- Blast Radius: TBD

- SLO/SLA Impact: TBD

- Data Risk: TBD

- Security/Compliance: TBD

- Invariant Violated: TBD
"""


def _update_bug_index(
    *,
    index_path: Path,
    bug_id: str,
    title: str,
    severity: str,
    component: str,
    bug_filename: str,
    today: dt.date,
) -> str:
    """Patch the bug INDEX.md with the new entry and return the updated text."""
    if not index_path.is_file():
        # Create a fresh index
        return _fresh_index(
            bug_id=bug_id,
            title=title,
            severity=severity,
            component=component,
            bug_filename=bug_filename,
            today=today,
        )

    content = index_path.read_text(encoding="utf-8")
    row = _format_index_row(
        bug_id=bug_id,
        title=title,
        severity=severity,
        component=component,
        bug_filename=bug_filename,
        today=today,
    )

    # Find the Open Bugs table and append
    lines = content.splitlines()
    insert_at = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith("| --- |") or line.strip().startswith("| ---"):
            # Insert after the separator line — but after any existing rows
            insert_at = idx + 1
            # Advance past existing rows
            while insert_at < len(lines) and lines[insert_at].strip().startswith("|"):
                insert_at += 1
            break

    if insert_at >= 0:
        lines.insert(insert_at, row)
    else:
        # Fallback: append at end
        lines.append("")
        lines.append(row)

    # Update last updated date
    updated = "\n".join(lines)
    updated = re.sub(
        r"(?m)^Last updated \(UTC\):\s*\d{4}-\d{2}-\d{2}\s*$",
        f"Last updated (UTC): {today.isoformat()}",
        updated,
        count=1,
    )
    if not updated.endswith("\n"):
        updated += "\n"
    return updated


def _format_index_row(
    *,
    bug_id: str,
    title: str,
    severity: str,
    component: str,
    bug_filename: str,
    today: dt.date,
) -> str:
    return (
        f"| {bug_id} | {today.isoformat()} | {title} | {severity} | "
        f"`{component}` | Open | [{bug_filename}]({bug_filename}) |"
    )


def _fresh_index(
    *,
    bug_id: str,
    title: str,
    severity: str,
    component: str,
    bug_filename: str,
    today: dt.date,
) -> str:
    row = _format_index_row(
        bug_id=bug_id,
        title=title,
        severity=severity,
        component=component,
        bug_filename=bug_filename,
        today=today,
    )
    return f"""# Bug Index

Last updated (UTC): {today.isoformat()}

## Open Bugs

| Bug ID | Date | Title | Severity | Components | Status | Link |
| --- | --- | --- | --- | --- | --- | --- |
{row}
"""


def capture_bug(
    *,
    repo_root: Path,
    title: str,
    component: str,
    severity: str,
    dry_run: bool = False,
) -> CreatedBug:
    """Create a new bug record in Casebook."""
    bugs_dir = (repo_root / _CASEBOOK_BUGS_RELATIVE).resolve()
    index_path = bugs_dir / "INDEX.md"
    today = dt.datetime.now(tz=dt.UTC).date()

    bug_id = _next_bug_id(bugs_dir)
    slug = _slugify(title)
    filename = f"{today.isoformat()}-{slug}.md"
    bug_path = bugs_dir / filename

    # Avoid collision
    suffix = 2
    while bug_path.exists():
        filename = f"{today.isoformat()}-{slug}-{suffix}.md"
        bug_path = bugs_dir / filename
        suffix += 1

    bug_text = _build_bug_text(
        bug_id=bug_id,
        title=title,
        severity=severity,
        component=component,
        today=today,
    )

    index_text = _update_bug_index(
        index_path=index_path,
        bug_id=bug_id,
        title=title,
        severity=severity,
        component=component,
        bug_filename=filename,
        today=today,
    )

    if not dry_run:
        bugs_dir.mkdir(parents=True, exist_ok=True)
        bug_path.write_text(bug_text, encoding="utf-8")
        index_path.write_text(index_text, encoding="utf-8")

    return CreatedBug(
        bug_id=bug_id,
        title=title,
        bug_path=bug_path,
        severity=severity,
        component=component,
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith bug capture",
        description="Capture a new bug record in the Odylith Casebook.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--title", required=True, help="Bug title.")
    parser.add_argument("--component", default="", help="Affected component ID.")
    parser.add_argument("--severity", default="P2", help="Severity (P0-P5, default P2).")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()

    try:
        result = capture_bug(
            repo_root=repo_root,
            title=str(args.title).strip(),
            component=str(args.component).strip(),
            severity=str(args.severity).strip(),
            dry_run=bool(args.dry_run),
        )
    except ValueError as exc:
        print(str(exc))
        return 2

    mode = "dry-run" if args.dry_run else "captured"
    if args.as_json:
        print(json.dumps({"mode": mode, **result.as_dict()}, indent=2))
    else:
        print(f"odylith bug capture {mode}")
        print(f"  bug_id: {result.bug_id}")
        print(f"  title: {result.title}")
        print(f"  severity: {result.severity}")
        print(f"  component: {result.component}")
        print(f"  path: {result.bug_path}")
    return 0

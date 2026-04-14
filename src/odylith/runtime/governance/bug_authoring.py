"""CLI backend for `odylith bug capture` — create a Casebook bug record.

Creates a new bug file in `odylith/casebook/bugs/` with a properly assigned
CB-### ID, rebuilds `INDEX.md` from markdown source, and rerenders the
Casebook surface so the new bug is immediately visible.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import sync_casebook_bug_index

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


def _refresh_casebook_surface(*, repo_root: Path) -> int:
    return owned_surface_refresh.refresh_owned_surface(repo_root=repo_root, surface="casebook")


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


def capture_bug(
    *,
    repo_root: Path,
    title: str,
    component: str,
    severity: str,
    dry_run: bool = False,
) -> CreatedBug:
    """Create a new bug record in Casebook and refresh the Casebook surface."""
    bugs_dir = (repo_root / _CASEBOOK_BUGS_RELATIVE).resolve()
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

    created_bug = CreatedBug(
        bug_id=bug_id,
        title=title,
        bug_path=bug_path,
        severity=severity,
        component=component,
    )

    if not dry_run:
        bugs_dir.mkdir(parents=True, exist_ok=True)
        bug_path.write_text(bug_text, encoding="utf-8")
        sync_casebook_bug_index.sync_casebook_bug_index(
            repo_root=repo_root,
            migrate_bug_ids=False,
        )
        refresh_rc = _refresh_casebook_surface(repo_root=repo_root)
        if refresh_rc != 0:
            raise RuntimeError(
                "Bug record captured but Casebook-only refresh failed; "
                f"bug_id={created_bug.bug_id} path={created_bug.bug_path}. "
                "Retry with `./.odylith/bin/odylith casebook refresh --repo-root .`."
            )

    return created_bug


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
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 2 if isinstance(exc, ValueError) else 1

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

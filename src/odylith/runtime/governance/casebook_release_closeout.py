"""Automated Casebook closeout for shipped release targets."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common import casebook_metadata
from odylith.runtime.governance import casebook_source_validation
from odylith.runtime.governance import github_issue_casebook
from odylith.runtime.governance import sync_casebook_bug_index
from odylith.runtime.governance.github_issue_references import normalize_version

_RELEASED_STATES = frozenset({"shipped", "closed"})
_PENDING_GITHUB_STATUSES = frozenset({"fixed_pending_release"})
_RELEASED_GITHUB_STATUSES = frozenset({"fixed_released", "closed"})


class CasebookReleaseCloseoutError(RuntimeError):
    """Raised when release closeout cannot safely mutate Casebook truth."""


@dataclass(frozen=True)
class CasebookCloseoutItem:
    """One Casebook record considered by release closeout."""

    bug_id: str
    path: str
    status: str
    fixed: str
    fixed_in: str
    github_status: str
    validation_evidence: bool
    eligibility: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "path": self.path,
            "status": self.status,
            "fixed": self.fixed,
            "fixed_in": self.fixed_in,
            "github_status": self.github_status,
            "validation_evidence": self.validation_evidence,
            "eligibility": self.eligibility,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CasebookReleaseCloseoutPlan:
    """Release-scoped Casebook closeout decision."""

    release: str
    fixed_version: str
    release_tag: str
    release_state: str
    shipped_utc: str
    closed_utc: str
    pending: tuple[CasebookCloseoutItem, ...]
    closable: tuple[CasebookCloseoutItem, ...]
    blocked: tuple[CasebookCloseoutItem, ...]
    already_closed: tuple[CasebookCloseoutItem, ...]
    changed_paths: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.blocked

    def with_changed_paths(self, paths: Sequence[Path], *, repo_root: Path) -> "CasebookReleaseCloseoutPlan":
        rendered = tuple(_display_path(repo_root=repo_root, path=path) for path in paths)
        return CasebookReleaseCloseoutPlan(
            release=self.release,
            fixed_version=self.fixed_version,
            release_tag=self.release_tag,
            release_state=self.release_state,
            shipped_utc=self.shipped_utc,
            closed_utc=self.closed_utc,
            pending=self.pending,
            closable=self.closable,
            blocked=self.blocked,
            already_closed=self.already_closed,
            changed_paths=rendered,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "odylith.casebook-release-closeout.v1",
            "ok": self.ok,
            "release": self.release,
            "fixed_version": self.fixed_version,
            "release_tag": self.release_tag,
            "release_state": self.release_state,
            "shipped_utc": self.shipped_utc,
            "closed_utc": self.closed_utc,
            "pending": [item.as_dict() for item in self.pending],
            "closable": [item.as_dict() for item in self.closable],
            "blocked": [item.as_dict() for item in self.blocked],
            "already_closed": [item.as_dict() for item in self.already_closed],
            "changed_paths": list(self.changed_paths),
        }


def build_casebook_release_closeout_plan(
    *,
    repo_root: Path,
    release: str,
    release_state_override: str = "",
) -> CasebookReleaseCloseoutPlan:
    """Build the Casebook closeout plan for one release selector."""
    root = Path(repo_root).resolve()
    release_info = github_issue_casebook.resolve_release(repo_root=root, release=release)
    release_state = str(release_state_override or release_info.status).strip()
    pending: list[CasebookCloseoutItem] = []
    closable: list[CasebookCloseoutItem] = []
    blocked: list[CasebookCloseoutItem] = []
    already_closed: list[CasebookCloseoutItem] = []
    for record in github_issue_casebook.iter_casebook_records(root):
        if normalize_version(record.fields.get("Fixed In", "")) != normalize_version(release_info.version):
            continue
        item = _classify_record(repo_root=root, record=record, release_state=release_state)
        if item.eligibility == "already_closed":
            already_closed.append(item)
        elif item.eligibility == "closable":
            closable.append(item)
        elif item.eligibility == "blocked":
            blocked.append(item)
        else:
            pending.append(item)
    return CasebookReleaseCloseoutPlan(
        release=release_info.release_id,
        fixed_version=release_info.version,
        release_tag=release_info.tag,
        release_state=release_state,
        shipped_utc=release_info.shipped_utc,
        closed_utc=release_info.closed_utc,
        pending=tuple(pending),
        closable=tuple(closable),
        blocked=tuple(blocked),
        already_closed=tuple(already_closed),
    )


def apply_casebook_release_closeout(
    *,
    repo_root: Path,
    release: str,
) -> CasebookReleaseCloseoutPlan:
    """Close eligible FixedPendingRelease Casebook records for a shipped release."""
    root = Path(repo_root).resolve()
    plan = build_casebook_release_closeout_plan(repo_root=root, release=release)
    if plan.blocked:
        blocked_ids = ", ".join(item.bug_id for item in plan.blocked)
        raise CasebookReleaseCloseoutError(
            "Casebook release closeout blocked; missing validation evidence for "
            f"{blocked_ids}"
        )
    if not plan.closable:
        return plan

    changed: list[Path] = []
    preimages: dict[Path, str] = {}
    try:
        for item in plan.closable:
            path = (root / item.path).resolve()
            text = path.read_text(encoding="utf-8")
            preimages[path] = text
            updated = github_issue_casebook.set_casebook_fields(text, _released_fields(text))
            if updated != text:
                path.write_text(updated, encoding="utf-8")
                changed.append(path)
        validation = casebook_source_validation.validate_casebook_sources(repo_root=root)
        if not validation.passed:
            first = validation.issues[0]
            raise CasebookReleaseCloseoutError(
                "Casebook release closeout failed validation: "
                + first.render(repo_root=validation.repo_root)
            )
        index_path = sync_casebook_bug_index.sync_casebook_bug_index(repo_root=root, migrate_bug_ids=False)
        if changed and index_path not in changed:
            changed.append(index_path)
    except Exception:
        for path, preimage in preimages.items():
            path.write_text(preimage, encoding="utf-8")
        raise
    return plan.with_changed_paths(changed, repo_root=root)


def _classify_record(
    *,
    repo_root: Path,
    record: github_issue_casebook.CasebookRecord,
    release_state: str,
) -> CasebookCloseoutItem:
    status = casebook_metadata.canonical_casebook_status(record.fields.get("Status", ""))
    fixed = casebook_metadata.canonical_casebook_fixed(record.fields.get("Fixed", ""))
    github_status = str(record.fields.get("GitHub Status", "")).strip().casefold()
    evidence = github_issue_casebook.has_validation_evidence(record)
    rel_path = _display_path(repo_root=repo_root, path=record.path)
    if status == "Closed" or github_status in _RELEASED_GITHUB_STATUSES:
        return _item(
            record=record,
            path=rel_path,
            status=status,
            fixed=fixed,
            github_status=github_status,
            validation_evidence=evidence,
            eligibility="already_closed",
            reason="already released or closed",
        )
    if status != "FixedPendingRelease" and github_status not in _PENDING_GITHUB_STATUSES:
        return _item(
            record=record,
            path=rel_path,
            status=status,
            fixed=fixed,
            github_status=github_status,
            validation_evidence=evidence,
            eligibility="pending",
            reason="record is not FixedPendingRelease",
        )
    if release_state not in _RELEASED_STATES:
        return _item(
            record=record,
            path=rel_path,
            status=status,
            fixed=fixed,
            github_status=github_status,
            validation_evidence=evidence,
            eligibility="pending",
            reason=f"release is {release_state or 'unknown'}, not shipped",
        )
    if not evidence:
        return _item(
            record=record,
            path=rel_path,
            status=status,
            fixed=fixed,
            github_status=github_status,
            validation_evidence=evidence,
            eligibility="blocked",
            reason="missing validation evidence",
        )
    return _item(
        record=record,
        path=rel_path,
        status=status,
        fixed=fixed,
        github_status=github_status,
        validation_evidence=evidence,
        eligibility="closable",
        reason="release is shipped and validation evidence exists",
    )


def _item(
    *,
    record: github_issue_casebook.CasebookRecord,
    path: str,
    status: str,
    fixed: str,
    github_status: str,
    validation_evidence: bool,
    eligibility: str,
    reason: str,
) -> CasebookCloseoutItem:
    return CasebookCloseoutItem(
        bug_id=record.bug_id,
        path=path,
        status=status,
        fixed=fixed,
        fixed_in=str(record.fields.get("Fixed In", "")).strip(),
        github_status=github_status,
        validation_evidence=validation_evidence,
        eligibility=eligibility,
        reason=reason,
    )


def _released_fields(text: str) -> Mapping[str, str]:
    fields = github_issue_casebook.parse_casebook_fields(text)
    updates: dict[str, str] = {
        "Status": "Closed",
        "Fixed": "Released",
    }
    if str(fields.get("GitHub Status", "")).strip():
        updates["GitHub Status"] = "fixed_released"
    if str(fields.get("Public Response", "")).strip():
        updates["Public Response"] = "closed"
    return updates


def _display_path(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith release casebook-closeout",
        description="Close FixedPendingRelease Casebook records after a release is shipped.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--release", default="current", help="Release selector, version, or release id.")
    parser.add_argument("--apply", action="store_true", help="Apply eligible Casebook source updates.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output.")
    return parser.parse_args(argv)


def _print_summary(plan: CasebookReleaseCloseoutPlan, *, applied: bool) -> None:
    mode = "applied" if applied else "dry-run"
    print(
        f"Casebook release closeout: {plan.release} {mode} "
        f"pending={len(plan.pending)} closable={len(plan.closable)} "
        f"blocked={len(plan.blocked)} already_closed={len(plan.already_closed)}"
    )
    if plan.changed_paths:
        print("- changed paths:")
        for path in plan.changed_paths:
            print(f"  - {path}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        plan = (
            apply_casebook_release_closeout(repo_root=repo_root, release=args.release)
            if bool(args.apply)
            else build_casebook_release_closeout_plan(repo_root=repo_root, release=args.release)
        )
    except (CasebookReleaseCloseoutError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if bool(args.as_json):
        payload = plan.as_dict()
        payload["applied"] = bool(args.apply)
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_summary(plan, applied=bool(args.apply))
    return 0 if plan.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

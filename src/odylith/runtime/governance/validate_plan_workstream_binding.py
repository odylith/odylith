"""Validate strict plan-to-workstream binding for new/touched active plans.

This validator is intentionally fail-closed for execution engine:
- New/touched active plans cannot keep `Backlog = -`.
- Bound workstreams must exist and remain in active execution statuses.
- `promoted_to_plan` must point back to the active plan path.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Sequence

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import validate_backlog_contract as backlog_contract

_WORKSTREAM_RE = re.compile(r"^B-\d{3,}$")
_ALLOWED_STATUSES: set[str] = {"planning", "implementation"}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Fail closed when new/touched active plans are not correctly bound to workstreams.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--plan-index", default="odylith/technical-plans/INDEX.md")
    parser.add_argument("--ideas-root", default="odylith/radar/source/ideas")
    parser.add_argument("changed_paths", nargs="*")
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def validate_plan_workstream_binding(
    *,
    repo_root: Path,
    plan_index_path: Path,
    ideas_root: Path,
    changed_paths: Sequence[str],
) -> list[str]:
    errors: list[str] = []

    active_rows = governance.parse_plan_active_rows(plan_index_path)
    if not active_rows:
        return errors

    touched_plan_paths = governance.collect_touched_active_plan_paths(
        repo_root=repo_root,
        plan_index_path=plan_index_path,
        changed_paths=changed_paths,
    )
    if not touched_plan_paths:
        return errors

    rows_by_plan = {
        str(row.get("Plan", "")).strip().strip("`"): row
        for row in active_rows
    }

    ideas, idea_errors = backlog_contract._validate_idea_specs(ideas_root)
    for entry in idea_errors:
        errors.append(f"idea-parse: {entry}")

    for plan_path in touched_plan_paths:
        row = rows_by_plan.get(plan_path)
        if row is None:
            # Closing an active plan moves it out of `odylith/technical-plans/in-progress`; tolerate that move.
            plan_file = _resolve(repo_root, plan_path)
            # If the plan path still exists under in-progress but is absent from active table, fail closed.
            if plan_path.startswith("odylith/technical-plans/in-progress/") and plan_file.is_file():
                errors.append(
                    f"{plan_index_path}: touched active plan `{plan_path}` is missing from `## Active Plans`"
                )
            continue

        backlog_id = str(row.get("Backlog", "")).strip().strip("`")
        if backlog_id in {"", "-"}:
            errors.append(
                f"{plan_index_path}: touched active plan `{plan_path}` must set Backlog to a workstream id (got `{backlog_id or '-'}`)"
            )
            continue
        if not _WORKSTREAM_RE.fullmatch(backlog_id):
            errors.append(
                f"{plan_index_path}: touched active plan `{plan_path}` has invalid Backlog token `{backlog_id}`"
            )
            continue

        spec = ideas.get(backlog_id)
        if spec is None:
            errors.append(
                f"{plan_index_path}: touched active plan `{plan_path}` references missing workstream `{backlog_id}`"
            )
            continue

        status = spec.status.lower()
        if status not in _ALLOWED_STATUSES:
            errors.append(
                f"{spec.path}: workstream `{backlog_id}` bound to active plan `{plan_path}` must be in {_ALLOWED_STATUSES}, got `{status}`"
            )

        promoted = str(spec.metadata.get("promoted_to_plan", "")).strip()
        if promoted != plan_path:
            errors.append(
                f"{spec.path}: `promoted_to_plan` must match active plan `{plan_path}`, got `{promoted or '<empty>'}`"
            )

        plan_file = _resolve(repo_root, plan_path)
        if not plan_file.is_file():
            errors.append(f"{plan_index_path}: active plan path does not exist `{plan_path}`")

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    plan_index_path = _resolve(repo_root, str(args.plan_index))
    ideas_root = _resolve(repo_root, str(args.ideas_root))

    errors = validate_plan_workstream_binding(
        repo_root=repo_root,
        plan_index_path=plan_index_path,
        ideas_root=ideas_root,
        changed_paths=tuple(args.changed_paths),
    )
    if errors:
        print("odylith/technical-plans/workstream binding contract FAILED")
        for item in errors:
            print(f"- {item}")
        return 2

    touched = governance.collect_touched_active_plan_paths(
        repo_root=repo_root,
        plan_index_path=plan_index_path,
        changed_paths=tuple(args.changed_paths),
    )
    print("odylith/technical-plans/workstream binding contract passed")
    print(f"- touched_active_plans_checked: {len(touched)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

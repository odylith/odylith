"""Validate Risk -> Mitigation nesting contract across plan markdown files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from odylith.runtime.governance import normalize_plan_risk_mitigation as normalizer


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description=(
            "Fail closed when any plan file has non-normalized `## Risks & Mitigations` structure."
        ),
    )
    parser.add_argument("--repo-root", default=".")
    return parser.parse_args(argv)


def validate_plan_risk_mitigation_contract(
    *, repo_root: Path, plan_paths: Sequence[Path] | None = None,
) -> list[str]:
    _, changed = normalizer.normalize_plan_risk_mitigation(
        repo_root=repo_root,
        check_only=True,
        plan_paths=plan_paths,
    )
    return [
        (
            f"{path}: invalid Risk -> Mitigation nesting; "
            "run `odylith sync --repo-root . --force` after normalizing the plan risk section"
        )
        for path in changed
    ]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    plan_root = repo_root / "odylith" / "technical-plans"
    if not any((plan_root / scope).is_dir() for scope in ("in-progress", "done")):
        print("plan risk/mitigation contract FAILED")
        print(f"- missing active/completed plan directories under: {plan_root}")
        return 2

    plan_paths = normalizer._list_plan_files(repo_root=repo_root)
    if not plan_paths:
        print("plan risk/mitigation contract not applicable")
        print(f"- no active or completed Markdown plan files under: {plan_root}")
        print("- plans validated: 0")
        return 0

    errors = validate_plan_risk_mitigation_contract(repo_root=repo_root, plan_paths=plan_paths)
    if errors:
        print("plan risk/mitigation contract FAILED")
        print(f"- plans validated: {len(plan_paths)}")
        for item in errors:
            print(f"- {item}")
        return 2

    print("plan risk/mitigation contract passed")
    print(f"- plans validated: {len(plan_paths)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

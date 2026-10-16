"""Command-line adapter for draft-first GitHub issue intake."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance.github_issue_pipeline import IssueIntakePlan
from odylith.runtime.governance.github_issue_pipeline import apply_github_plan
from odylith.runtime.governance.github_issue_pipeline import apply_governance_plan
from odylith.runtime.governance.github_issue_pipeline import build_release_closeout_plan
from odylith.runtime.governance.github_issue_pipeline import build_triage_plan
from odylith.runtime.governance.github_issue_pipeline import parse_issue_reference
from odylith.runtime.governance.github_issue_transport import GitHubPipelineError
from odylith.runtime.governance.github_issue_transport import GitHubTransport
from odylith.runtime.governance.github_issue_transport import build_transport

_DEFAULT_REPO = "odylith/odylith"
_DEFAULT_RELEASE = "0.1.12"


def _print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _render_plan_summary(plan: IssueIntakePlan) -> str:
    labels = ", ".join(plan.recommended_github_mutation.labels_to_add) or "none"
    casebook = plan.recommended_governance_mutation.casebook_id or "blocked"
    return "\n".join(
        [
            f"GitHub issue triage: {plan.issue['repo']}#{plan.issue['number']}",
            f"- severity: {plan.severity}",
            f"- type: {', '.join(plan.issue_types)}",
            f"- component: {plan.suspected_component}",
            f"- Casebook: {casebook}",
            f"- planned labels: {labels}",
            "- public GitHub writes: draft only unless --apply-github is set",
        ]
    )


def _refresh_casebook_if_changed(*, repo_root: Path, changed_paths: Sequence[Path], operation_label: str) -> None:
    if not changed_paths:
        return
    owned_surface_refresh.raise_for_failed_refresh(
        repo_root=repo_root,
        surface="casebook",
        operation_label=operation_label,
    )


def _cmd_triage(args: argparse.Namespace, transport: GitHubTransport) -> int:
    repo_root = Path(args.repo_root).resolve()
    ref = parse_issue_reference(args.issue, default_repo=args.repo)
    issue = transport.get_issue(repo=ref.repo, number=ref.number)
    labels = transport.list_labels(repo=ref.repo)
    plan = build_triage_plan(
        issue=issue,
        repo_root=repo_root,
        repo=ref.repo,
        existing_labels=labels,
        fixed_version=args.fixed_version,
    )
    applied: dict[str, Any] = {"governance": False, "github": False}
    if args.apply_governance:
        governance_paths = apply_governance_plan(repo_root=repo_root, plan=plan)
        _refresh_casebook_if_changed(
            repo_root=repo_root,
            changed_paths=governance_paths,
            operation_label="GitHub issue governance apply",
        )
        applied["governance_paths"] = [str(path) for path in governance_paths]
        applied["governance"] = True
    if args.apply_github:
        apply_github_plan(
            repo=ref.repo,
            issue_number=ref.number,
            plan=plan.recommended_github_mutation,
            transport=transport,
        )
        applied["github"] = True
    if args.as_json:
        _print_json({"plan": plan.as_dict(), "applied": applied})
    else:
        print(_render_plan_summary(plan))
    return 0


def _cmd_sweep(args: argparse.Namespace, transport: GitHubTransport) -> int:
    repo_root = Path(args.repo_root).resolve()
    issues = sorted(
        transport.list_issues(repo=args.repo, state=args.state),
        key=lambda item: int(item.get("number", 0)),
    )
    labels = transport.list_labels(repo=args.repo)
    plans = [
        build_triage_plan(
            issue=issue,
            repo_root=repo_root,
            repo=args.repo,
            existing_labels=labels,
            fixed_version=args.fixed_version,
        )
        for issue in issues
    ]
    if args.apply_governance:
        governance_paths: list[Path] = []
        for plan in plans:
            governance_paths.extend(apply_governance_plan(repo_root=repo_root, plan=plan))
        _refresh_casebook_if_changed(
            repo_root=repo_root,
            changed_paths=governance_paths,
            operation_label="GitHub issue sweep governance apply",
        )
    if args.apply_github:
        for plan in plans:
            apply_github_plan(
                repo=args.repo,
                issue_number=int(plan.issue["number"]),
                plan=plan.recommended_github_mutation,
                transport=transport,
            )
    payload = {"count": len(plans), "plans": [plan.as_dict() for plan in plans]}
    if args.as_json:
        _print_json(payload)
    else:
        print(f"GitHub issue sweep: {args.repo} {args.state} issues={len(plans)}")
    return 0


def _cmd_release_closeout(args: argparse.Namespace, transport: GitHubTransport) -> int:
    plan = build_release_closeout_plan(
        repo_root=Path(args.repo_root).resolve(),
        release=args.release,
        repo=args.repo,
        transport=transport,
    )
    if args.apply_github:
        for item in (*plan.pending, *plan.closable):
            ref = parse_issue_reference(item.issue, default_repo=args.repo)
            apply_github_plan(
                repo=ref.repo,
                issue_number=ref.number,
                plan=item.github_mutation,
                transport=transport,
            )
    if args.as_json:
        _print_json(plan.as_dict())
    else:
        print(
            f"GitHub release closeout: {plan.release} pending={len(plan.pending)} "
            f"closable={len(plan.closable)} blocked={len(plan.blocked)} already_closed={len(plan.already_closed)}"
        )
    return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith github",
        description="Draft-first GitHub issue intake and release closeout.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    subparsers = parser.add_subparsers(dest="domain", required=True)
    issue = subparsers.add_parser("issue", help="Handle GitHub issue intake and release closeout.")
    issue_subparsers = issue.add_subparsers(dest="issue_command", required=True)

    triage = issue_subparsers.add_parser("triage", help="Fetch one issue and draft governance/GitHub mutations.")
    triage.add_argument("issue", help="Issue URL, owner/repo#number, or number with --repo.")
    triage.add_argument("--repo", default=_DEFAULT_REPO, help="GitHub repository for numeric issue references.")
    triage.add_argument("--fixed-version", default=_DEFAULT_RELEASE, help="Fixed-in version to plan for confirmed bugs.")
    triage.add_argument("--apply-governance", action="store_true", help="Apply Casebook-only governance updates.")
    triage.add_argument("--apply-github", action="store_true", help="Apply public GitHub labels/comments.")
    triage.add_argument("--json", action="store_true", dest="as_json", help="Emit the issue intake plan as JSON.")

    sweep = issue_subparsers.add_parser("sweep", help="Process matching issues into deterministic intake plans.")
    sweep.add_argument("--repo", default=_DEFAULT_REPO, help="GitHub repository.")
    sweep.add_argument("--state", default="open", choices=("open", "closed", "all"), help="Issue state to scan.")
    sweep.add_argument("--fixed-version", default=_DEFAULT_RELEASE, help="Fixed-in version to plan for confirmed bugs.")
    sweep.add_argument("--apply-governance", action="store_true", help="Apply Casebook-only governance updates.")
    sweep.add_argument("--apply-github", action="store_true", help="Apply public GitHub labels/comments.")
    sweep.add_argument("--json", action="store_true", dest="as_json", help="Emit sweep output as JSON.")

    closeout = issue_subparsers.add_parser("release-closeout", help="Plan public issue comments/closure for a release.")
    closeout.add_argument("--repo", default=_DEFAULT_REPO, help="GitHub repository.")
    closeout.add_argument("--release", default="current", help="Release selector, version, or release id.")
    closeout.add_argument("--apply-github", action="store_true", help="Apply public GitHub comments/labels/closures.")
    closeout.add_argument("--json", action="store_true", dest="as_json", help="Emit closeout output as JSON.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    transport = build_transport()
    try:
        if args.domain == "issue" and args.issue_command == "triage":
            return _cmd_triage(args, transport)
        if args.domain == "issue" and args.issue_command == "sweep":
            return _cmd_sweep(args, transport)
        if args.domain == "issue" and args.issue_command == "release-closeout":
            return _cmd_release_closeout(args, transport)
    except (GitHubPipelineError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2 if isinstance(exc, (GitHubPipelineError, ValueError)) else 1
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

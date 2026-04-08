from __future__ import annotations

import argparse


DEFAULT_SYNC_COMPASS_REFRESH_PROFILE = "shell-safe"
DEFAULT_SYNC_OVERLAP_GATE_THRESHOLD = 50

_SYNC_DESCRIPTION = "Sync backlog workstream validation + rendered UI artifacts."
_SYNC_EPILOG = (
    "Structured sync evidence currently lives in generated report artifacts; "
    "`odylith sync` does not yet expose a pure terminal `--json` mode."
)


def configure_sync_parser(
    parser: argparse.ArgumentParser,
    *,
    include_repo_root: bool = True,
) -> argparse.ArgumentParser:
    parser.description = _SYNC_DESCRIPTION
    parser.epilog = _SYNC_EPILOG
    if include_repo_root:
        parser.add_argument("--repo-root", default=".", help="Consumer repository root.")
    parser.add_argument(
        "--odylith-mode",
        default="",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run sync workflow even when changed paths are not matched.",
    )
    parser.add_argument(
        "--impact-mode",
        choices=("selective", "full"),
        default="selective",
        help="Dashboard rendering mode: selective impact render (default) or full render.",
    )
    clean_gate_group = parser.add_mutually_exclusive_group()
    clean_gate_group.add_argument(
        "--check-clean",
        action="store_true",
        help="Fail closed if generated workstream UI files remain dirty after sync, including staged changes.",
    )
    clean_gate_group.add_argument(
        "--check-commit-ready",
        action="store_true",
        help=(
            "Fail closed if generated workstream UI files do not match the staged commit payload. "
            "Staged-only generated outputs are allowed; unstaged and untracked drift is not."
        ),
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help=(
            "Run non-mutating validation gates only (no reconcile/autofix/render writes). "
            "Intended for pre-commit enforcement."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the sync mutation plan and dirty-worktree overlap without writing files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show the full dirty-overlap listing instead of the compact summary.",
    )
    parser.add_argument(
        "--proceed-with-overlap",
        action="store_true",
        help=(
            "Acknowledge write-mode sync when "
            f"{DEFAULT_SYNC_OVERLAP_GATE_THRESHOLD}+ local worktree entries overlap the mutation plan."
        ),
    )
    parser.add_argument(
        "--no-traceability-autofix",
        action="store_true",
        help="Skip automatic traceability metadata backfill before validation/render.",
    )
    parser.add_argument(
        "--traceability-autofix-report",
        default="odylith/radar/traceability-autofix-report.v1.json",
        help="Output report path for traceability metadata autofix.",
    )
    parser.add_argument(
        "--policy-mode",
        choices=("advisory", "enforce-critical"),
        default="",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--registry-policy-mode",
        choices=("advisory", "enforce-critical"),
        default="enforce-critical",
        help="Policy mode used by component-registry validator.",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help=(
            "Execution mode for local upkeep commands. `auto` prefers the local runtime-backed "
            "fast path with standalone fallback, `standalone` preserves subprocess-only strict "
            "behavior, and `daemon` requires runtime-backed execution."
        ),
    )
    parser.add_argument(
        "--compass-refresh-profile",
        choices=("full", "shell-safe"),
        default=DEFAULT_SYNC_COMPASS_REFRESH_PROFILE,
        help=(
            "Compass refresh profile for sync/render steps. "
            "`shell-safe` defers live AI narration so sync stays bounded."
        ),
    )
    deep_skill_group = parser.add_mutually_exclusive_group()
    deep_skill_group.add_argument(
        "--enforce-deep-skills",
        dest="enforce_deep_skills",
        action="store_true",
        help="Fail closed on critical deep-skill policy findings in validator path.",
    )
    deep_skill_group.add_argument(
        "--no-enforce-deep-skills",
        dest="enforce_deep_skills",
        action="store_false",
        help="Disable critical deep-skill policy enforcement for ad-hoc local refreshes.",
    )
    parser.set_defaults(enforce_deep_skills=True)
    parser.add_argument(
        "--once",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--max-interval-seconds",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "changed_paths",
        nargs="*",
        help="Changed paths (pre-commit passes these automatically).",
    )
    return parser


def namespace_to_argv(args: argparse.Namespace, *, include_repo_root: bool = True) -> list[str]:
    argv: list[str] = []
    if include_repo_root:
        argv.extend(["--repo-root", str(args.repo_root)])
    if str(getattr(args, "odylith_mode", "")).strip():
        argv.extend(["--odylith-mode", str(args.odylith_mode)])
    if bool(getattr(args, "force", False)):
        argv.append("--force")
    if str(getattr(args, "impact_mode", "selective")).strip() != "selective":
        argv.extend(["--impact-mode", str(args.impact_mode)])
    if bool(getattr(args, "check_only", False)):
        argv.append("--check-only")
    if bool(getattr(args, "check_clean", False)):
        argv.append("--check-clean")
    if bool(getattr(args, "check_commit_ready", False)):
        argv.append("--check-commit-ready")
    if bool(getattr(args, "dry_run", False)):
        argv.append("--dry-run")
    if bool(getattr(args, "verbose", False)):
        argv.append("--verbose")
    if bool(getattr(args, "proceed_with_overlap", False)):
        argv.append("--proceed-with-overlap")
    if bool(getattr(args, "no_traceability_autofix", False)):
        argv.append("--no-traceability-autofix")
    if str(getattr(args, "traceability_autofix_report", "")).strip() != "odylith/radar/traceability-autofix-report.v1.json":
        argv.extend(["--traceability-autofix-report", str(args.traceability_autofix_report)])
    if str(getattr(args, "policy_mode", "")).strip():
        argv.extend(["--policy-mode", str(args.policy_mode)])
    if str(getattr(args, "registry_policy_mode", "enforce-critical")).strip() != "enforce-critical":
        argv.extend(["--registry-policy-mode", str(args.registry_policy_mode)])
    if str(getattr(args, "runtime_mode", "auto")).strip() != "auto":
        argv.extend(["--runtime-mode", str(args.runtime_mode)])
    if str(getattr(args, "compass_refresh_profile", DEFAULT_SYNC_COMPASS_REFRESH_PROFILE)).strip() != DEFAULT_SYNC_COMPASS_REFRESH_PROFILE:
        argv.extend(["--compass-refresh-profile", str(args.compass_refresh_profile)])
    if bool(getattr(args, "enforce_deep_skills", True)) is False:
        argv.append("--no-enforce-deep-skills")
    if bool(getattr(args, "once", False)):
        argv.append("--once")
    if bool(getattr(args, "no_render", False)):
        argv.append("--no-render")
    if int(getattr(args, "interval_seconds", 0) or 0) != 0:
        argv.extend(["--interval-seconds", str(args.interval_seconds)])
    if int(getattr(args, "max_interval_seconds", 0) or 0) != 0:
        argv.extend(["--max-interval-seconds", str(args.max_interval_seconds)])
    argv.extend([str(token) for token in getattr(args, "changed_paths", ())])
    return argv


__all__ = [
    "DEFAULT_SYNC_COMPASS_REFRESH_PROFILE",
    "DEFAULT_SYNC_OVERLAP_GATE_THRESHOLD",
    "configure_sync_parser",
    "namespace_to_argv",
]

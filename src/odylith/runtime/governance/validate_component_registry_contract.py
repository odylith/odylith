"""Validate component-registry contracts.

This validator is fail-closed for component inventory integrity and meaningful
agent-event coverage.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from odylith.runtime.governance import component_registry_intelligence as registry
from odylith.runtime.governance.component_registry_review_policy import (
    should_emit_deep_skill_policy_warning,
)


_WARN_ONLY_PREFIXES: tuple[str, ...] = (
    "missing stream path:",
    "suppressed unresolved idea component tokens:",
    "candidate components pending review:",
    "include_idea_candidates is deprecated:",
)
_POLICY_MODE_CHOICES: tuple[str, str] = ("advisory", "enforce-critical")
_DEFAULT_DEEP_SKILL_COMPONENTS: tuple[str, str] = ("kafka-topic", "msk")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith validate component-registry",
        description="Validate component registry inventory and meaningful event mapping contracts.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", default=registry.DEFAULT_MANIFEST_PATH)
    parser.add_argument("--catalog", default=registry.DEFAULT_CATALOG_PATH)
    parser.add_argument("--ideas-root", default=registry.DEFAULT_IDEAS_ROOT)
    parser.add_argument("--stream", default=registry.DEFAULT_STREAM_PATH)
    parser.add_argument(
        "--max-unmapped-meaningful",
        type=int,
        default=0,
        help="Maximum allowed meaningful events without component linkage.",
    )
    parser.add_argument(
        "--policy-mode",
        choices=_POLICY_MODE_CHOICES,
        default="advisory",
        help="Policy reporting mode for deep-skill and trigger-tier checks.",
    )
    parser.add_argument(
        "--enforce-deep-skills",
        action="store_true",
        help="Fail closed on critical deep-skill policy findings.",
    )
    parser.add_argument(
        "--deep-skill-components",
        default=",".join(_DEFAULT_DEEP_SKILL_COMPONENTS),
        help="Comma-separated component IDs requiring deep-skill policy evaluation.",
    )
    parser.add_argument(
        "--deep-skill-min-meaningful-events",
        type=int,
        default=1,
        help="Minimum meaningful mapped events needed to satisfy churn gate.",
    )
    parser.add_argument(
        "--deep-skill-min-gates",
        type=int,
        default=2,
        help="Minimum satisfied gates (risk/churn/workflow) before deep skills are required.",
    )
    parser.add_argument(
        "--deep-skill-active-statuses",
        default="planning,implementation",
        help="Comma-separated backlog statuses considered active for workflow gate.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _parse_csv(value: str) -> list[str]:
    rows: list[str] = []
    for raw in str(value or "").split(","):
        token = str(raw or "").strip()
        if token:
            rows.append(token)
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()

    manifest_token = str(args.manifest or "").strip()
    manifest_path = (
        registry.default_manifest_path(repo_root=repo_root)
        if manifest_token == registry.DEFAULT_MANIFEST_PATH
        else _resolve(repo_root, manifest_token)
    )
    catalog_path = _resolve(repo_root, str(args.catalog))
    ideas_root = _resolve(repo_root, str(args.ideas_root))
    stream_path = _resolve(repo_root, str(args.stream))

    report = registry.build_component_registry_report(
        repo_root=repo_root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        stream_path=stream_path,
    )
    report_cache_path, _fingerprint = registry._cached_component_registry_report_payload(  # noqa: SLF001
        repo_root=repo_root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        stream_path=stream_path,
        workspace_activity_window_hours=registry.DEFAULT_WORKSPACE_ACTIVITY_WINDOW_HOURS,
    )
    try:
        report_cache_display = str(report_cache_path.relative_to(repo_root))
    except ValueError:
        report_cache_display = str(report_cache_path)

    warnings: list[str] = []
    errors: list[str] = []
    for row in report.diagnostics:
        token = str(row or "").strip()
        if not token:
            continue
        if any(token.startswith(prefix) for prefix in _WARN_ONLY_PREFIXES):
            warnings.append(token)
            continue
        errors.append(token)

    unmapped = report.unmapped_meaningful_events
    max_unmapped = max(0, int(args.max_unmapped_meaningful))
    if len(unmapped) > max_unmapped:
        errors.append(
            "meaningful events missing component linkage: "
            f"{len(unmapped)} (allowed {max_unmapped})"
        )

    policy_mode = str(args.policy_mode or "advisory").strip().lower()
    if policy_mode not in _POLICY_MODE_CHOICES:
        policy_mode = "advisory"
    deep_skill_components = _parse_csv(str(args.deep_skill_components))
    deep_skill_results = registry.evaluate_deep_skill_policy(
        repo_root=repo_root,
        components=report.components,
        mapped_events=report.mapped_events,
        ideas_root=_resolve(repo_root, str(args.ideas_root)),
        target_components=deep_skill_components,
        active_statuses=_parse_csv(str(args.deep_skill_active_statuses)),
        min_meaningful_events=int(args.deep_skill_min_meaningful_events),
        min_gate_count=int(args.deep_skill_min_gates),
    )
    policy_warnings: list[str] = []
    policy_errors: list[str] = []
    for row in deep_skill_results:
        component_id = str(row.get("component_id", "")).strip() or "unknown"
        missing = [str(token or "").strip() for token in row.get("missing", []) if str(token or "").strip()]
        if not missing:
            continue
        if not should_emit_deep_skill_policy_warning(row):
            continue
        required = bool(row.get("required", False))
        gate_count = int(row.get("gate_count", 0) or 0)
        message = (
            f"deep-skill policy `{component_id}` missing={','.join(missing)} "
            f"required={'yes' if required else 'no'} gates={gate_count}"
        )
        if required and bool(args.enforce_deep_skills) and policy_mode == "enforce-critical":
            policy_errors.append(message)
        else:
            policy_warnings.append(message)

    print("component registry contract report")
    print(f"- components: {len(report.components)}")
    print(f"- events: {len(report.mapped_events)}")
    print(f"- meaningful_events: {sum(1 for row in report.mapped_events if row.meaningful)}")
    print(
        "- mapped_meaningful_events: "
        f"{sum(1 for row in report.mapped_events if row.meaningful and row.mapped_components)}"
    )
    print(f"- unmapped_meaningful_events: {len(unmapped)}")
    print(f"- policy_mode: {policy_mode}")
    print(f"- deep_skill_checks: {len(deep_skill_results)}")

    if warnings:
        print("component registry contract warnings")
        for token in warnings[:32]:
            print(f"- {token}")
        print(f"- report: {report_cache_display}")
    if policy_warnings:
        print("component policy warnings")
        for token in policy_warnings[:32]:
            print(f"- {token}")
        if not warnings:
            print(f"- report: {report_cache_display}")

    if unmapped:
        print("unmapped meaningful events")
        for row in unmapped[:32]:
            summary = str(row.summary or "").strip() or "(no summary)"
            print(
                "- "
                f"line={row.event_index} kind={row.kind or 'unknown'} "
                f"workstreams={','.join(row.workstreams) or '-'} summary={summary}"
            )

    if errors:
        print("component registry contract FAILED")
        for token in errors[:64]:
            print(f"- {token}")
        return 2

    if policy_errors:
        print("component registry policy FAILED")
        for token in policy_errors[:64]:
            print(f"- {token}")
        return 2

    print("component registry contract passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

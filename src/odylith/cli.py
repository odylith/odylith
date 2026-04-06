from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Sequence

from odylith import __version__
from odylith.bundle import bundle_root
import odylith.install as install_api
from odylith.install.state import (
    AUTHORITATIVE_RELEASE_REPO,
    clear_upgrade_spotlight,
    install_state_path,
    write_upgrade_spotlight,
)
from odylith.runtime.common.command_surface import (
    ensure_nested_subcommand_repo_root_args,
    ensure_repo_root_args,
)
from odylith.runtime.common import log_compass_timeline_event
from odylith.runtime.context_engine import odylith_context_engine
from odylith.runtime.evaluation import benchmark_compare
from odylith.runtime.governance import sync_workstream_artifacts
from odylith.runtime.governance import auto_promote_workstream_phase
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import backfill_workstream_traceability
from odylith.runtime.governance import maintainer_lane_status
from odylith.runtime.governance import normalize_plan_risk_mitigation
from odylith.runtime.governance import reconcile_plan_workstream_binding
from odylith.runtime.governance import sync_component_spec_requirements
from odylith.runtime.governance import validate_guidance_portability
from odylith.runtime.governance import validate_backlog_contract
from odylith.runtime.governance import validate_component_registry_contract
from odylith.runtime.governance import validate_plan_risk_mitigation_contract
from odylith.runtime.governance import validate_self_host_posture
from odylith.runtime.governance import validate_plan_traceability_contract
from odylith.runtime.governance import validate_plan_workstream_binding
from odylith.runtime.governance import version_truth
from odylith.runtime.orchestration import subagent_orchestrator
from odylith.runtime.orchestration import subagent_router
from odylith.runtime.surfaces import install_mermaid_autosync_hook
from odylith.runtime.surfaces import auto_update_mermaid_diagrams
from odylith.runtime.surfaces import render_mermaid_catalog
from odylith.runtime.surfaces import restore_compass_history
from odylith.runtime.surfaces import scaffold_mermaid_diagram
from odylith.runtime.surfaces import shell_onboarding
from odylith.runtime.surfaces import update_compass
from odylith.runtime.surfaces import watch_prompt_transactions

_CONTEXT_ENGINE_FEATURE_PACK_COMMANDS = {"warmup", "serve", "benchmark", "odylith-remote-sync"}
_CONTEXT_ENGINE_SHORTCUTS = (
    ("bootstrap", "bootstrap-session", "Build a compact fresh-session bootstrap packet."),
    ("session-brief", "session-brief", "Build one dirty-session delta packet."),
    ("context", "context", "Resolve one repo entity/path into a local context dossier."),
    ("impact", "impact", "Resolve architecture impact for one or more changed paths."),
    ("architecture", "architecture", "Resolve plane/stack topology grounding and diagram-watch gaps."),
    ("governance-slice", "governance-slice", "Build a compact governance and delivery-truth packet."),
    ("query", "query", "Search the local projection store when concrete anchors already exist."),
)
_CONTEXT_ENGINE_SHORTCUT_TARGETS = {command: target for command, target, _help_text in _CONTEXT_ENGINE_SHORTCUTS}
_EXPLICIT_CONTEXT_ENGINE_SHORTCUTS = frozenset({"bootstrap", "context", "query"})
_FIRST_RUN_SURFACE_OUTPUTS = (
    Path("odylith/index.html"),
    Path("odylith/radar/radar.html"),
    Path("odylith/atlas/atlas.html"),
    Path("odylith/compass/compass.html"),
    Path("odylith/registry/registry.html"),
    Path("odylith/casebook/casebook.html"),
)
_DEFAULT_DASHBOARD_REFRESH_SURFACES = ("tooling_shell", "radar", "compass")
_DEFAULT_DASHBOARD_REFRESH_SURFACES_CSV = ",".join(_DEFAULT_DASHBOARD_REFRESH_SURFACES)


def doctor_bundle(*args, **kwargs):
    return install_api.doctor_bundle(*args, **kwargs)


def evaluate_start_preflight(*args, **kwargs):
    return install_api.evaluate_start_preflight(*args, **kwargs)


def ensure_context_engine_pack(*args, **kwargs):
    return install_api.ensure_context_engine_pack(*args, **kwargs)


def install_bundle(*args, **kwargs):
    return install_api.install_bundle(*args, **kwargs)


def migrate_legacy_install(*args, **kwargs):
    return install_api.migrate_legacy_install(*args, **kwargs)


def plan_install_lifecycle(*args, **kwargs):
    return install_api.plan_install_lifecycle(*args, **kwargs)


def plan_reinstall_lifecycle(*args, **kwargs):
    return install_api.plan_reinstall_lifecycle(*args, **kwargs)


def plan_upgrade_lifecycle(*args, **kwargs):
    return install_api.plan_upgrade_lifecycle(*args, **kwargs)


def preferred_repair_entrypoint(*args, **kwargs):
    return install_api.preferred_repair_entrypoint(*args, **kwargs)


def product_repo_role(*args, **kwargs):
    return install_api.product_repo_role(*args, **kwargs)


def reinstall_install(*args, **kwargs):
    return install_api.reinstall_install(*args, **kwargs)


def rollback_install(*args, **kwargs):
    return install_api.rollback_install(*args, **kwargs)


def set_agents_integration(*args, **kwargs):
    return install_api.set_agents_integration(*args, **kwargs)


def uninstall_bundle(*args, **kwargs):
    return install_api.uninstall_bundle(*args, **kwargs)


def upgrade_install(*args, **kwargs):
    return install_api.upgrade_install(*args, **kwargs)


def version_status(*args, **kwargs):
    return install_api.version_status(*args, **kwargs)


def _extract_repo_root(argv: Sequence[str]) -> tuple[str, list[str]]:
    repo_root = "."
    forwarded: list[str] = []
    index = 0
    tokens = [str(token) for token in argv]
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            forwarded.extend(tokens[index:])
            break
        if token == "--repo-root":
            if index + 1 >= len(tokens):
                raise SystemExit("--repo-root requires a value")
            repo_root = tokens[index + 1]
            if not str(repo_root).strip():
                raise SystemExit("--repo-root requires a value")
            index += 2
            continue
        if token.startswith("--repo-root="):
            repo_root = token.partition("=")[2]
            if not str(repo_root).strip():
                raise SystemExit("--repo-root requires a value")
            index += 1
            continue
        forwarded.append(token)
        index += 1
    return repo_root, forwarded


def _maybe_stage_context_engine_pack(*, repo_root: str, forwarded: Sequence[str]) -> None:
    command = str(forwarded[0]).strip() if forwarded else ""
    if command not in _CONTEXT_ENGINE_FEATURE_PACK_COMMANDS:
        return
    status = version_status(repo_root=repo_root)
    if status.context_engine_pack_installed is not False:
        return
    if status.runtime_source != "pinned_runtime":
        return
    changed, message = ensure_context_engine_pack(repo_root=repo_root, release_repo=AUTHORITATIVE_RELEASE_REPO)
    if changed and message:
        print(message)


def _dispatch_context_engine_shortcut(*, repo_root: str, target_command: str, forwarded: Sequence[str]) -> int:
    _maybe_stage_context_engine_pack(repo_root=repo_root, forwarded=[target_command, *list(forwarded)])
    return odylith_context_engine.main(
        ["--repo-root", str(Path(repo_root).expanduser().resolve()), target_command, *list(forwarded)]
    )


def _current_git_branch(*, repo_root: str | Path) -> str:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(Path(repo_root).expanduser().resolve()),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return ""
    return str(completed.stdout or "").strip()


def _product_repo_main_branch_write_block(*, repo_root: str | Path) -> str:
    root = Path(repo_root).expanduser().resolve()
    if product_repo_role(repo_root=root) != "product_repo":
        return ""
    branch = _current_git_branch(repo_root=root)
    if branch != "main":
        return ""
    year = datetime.now(UTC).year
    return (
        "Maintainer authoring on `main` is forbidden in this repo. "
        f"Create and switch to a work branch first, for example `git switch -c {year}/freedom/<tag>`."
    )


def _guard_product_repo_main_branch(*, repo_root: str | Path) -> int:
    message = _product_repo_main_branch_write_block(repo_root=repo_root)
    if not message:
        return 0
    print(message, file=sys.stderr)
    return 2


def _forwarded_has_flag(forwarded: Sequence[str], flag: str) -> bool:
    needle = str(flag or "").strip()
    if not needle:
        return False
    for token in (str(token).strip() for token in forwarded):
        if token == "--":
            break
        if token == needle:
            return True
    return False


def _help_requested(tokens: Sequence[str]) -> bool:
    for token in (str(token).strip() for token in tokens):
        if token == "--":
            break
        if token in {"-h", "--help"}:
            return True
    return False


def _missing_first_run_surfaces(*, repo_root: Path) -> list[Path]:
    root = Path(repo_root).expanduser().resolve()
    return [root / relative_path for relative_path in _FIRST_RUN_SURFACE_OUTPUTS if not (root / relative_path).is_file()]


def _bootstrap_first_run_surfaces(*, repo_root: Path) -> int:
    resolved_repo_root = Path(repo_root).expanduser().resolve()
    render_rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=resolved_repo_root,
        surfaces=("tooling_shell",),
        runtime_mode="auto",
        atlas_sync=False,
    )
    remaining_missing = _missing_first_run_surfaces(repo_root=resolved_repo_root)
    if remaining_missing:
        full_sync_rc = sync_workstream_artifacts.main(
            [
                "--repo-root",
                str(resolved_repo_root),
                "--force",
                "--impact-mode",
                "full",
            ]
        )
        if full_sync_rc == 0:
            return 0
        return full_sync_rc
    return render_rc


def _is_first_install(*, repo_root: Path) -> bool:
    return not install_state_path(repo_root=repo_root).is_file()


def _env_flag_enabled(name: str) -> bool:
    token = str(os.environ.get(name) or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def _interactive_browser_launch_possible() -> bool:
    if _env_flag_enabled("ODYLITH_NO_BROWSER"):
        return False
    if _env_flag_enabled("CI") or _env_flag_enabled("GITHUB_ACTIONS") or _env_flag_enabled("BUILD_BUILDID"):
        return False
    if any(str(os.environ.get(name) or "").strip() for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY")):
        return False
    if not (sys.stdout.isatty() or sys.stderr.isatty()):
        return False
    if sys.platform.startswith("linux") and not any(
        str(os.environ.get(name) or "").strip() for name in ("DISPLAY", "WAYLAND_DISPLAY")
    ):
        return False
    return True


def _maybe_open_dashboard_in_browser(*, dashboard_path: Path, enabled: bool) -> tuple[bool, str]:
    if not enabled:
        return False, ""
    if not _interactive_browser_launch_possible():
        return False, ""
    try:
        opened = bool(webbrowser.open(dashboard_path.resolve().as_uri(), new=2))
    except Exception as exc:
        return False, f"Odylith could not open the local shell automatically: {exc}"
    if opened:
        return True, ""
    return False, "Odylith could not open the local shell automatically. Open `odylith/index.html` manually."


def _format_bold(text: str) -> str:
    token = str(text)
    return f"\033[1m{token}\033[0m" if sys.stdout.isatty() else token


def _format_release_published_at(value: object) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    normalized = token.replace("Z", "+00:00")
    try:
        published = datetime.fromisoformat(normalized)
    except ValueError:
        return token
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    return published.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _print_release_highlights(summary: object) -> None:
    release_url = str(getattr(summary, "release_url", "") or "").strip()
    release_published_at = _format_release_published_at(getattr(summary, "release_published_at", ""))
    release_highlights = tuple(
        str(item).strip()
        for item in getattr(summary, "release_highlights", ()) or ()
        if str(item).strip()
    )
    if release_url:
        print(f"Release: {release_url}")
    if release_published_at:
        print(f"Published: {release_published_at}")
    if release_highlights:
        print("What changed:")
        for item in release_highlights[:3]:
            print(f"- {item}")


def _print_grounding_quickstart() -> None:
    print(
        "First repo turn: `./.odylith/bin/odylith start --repo-root .`."
    )
    print(
        "Exact ref shortcut: `./.odylith/bin/odylith context --repo-root . <ref>`; "
        "lexical recall after anchors exist: `./.odylith/bin/odylith query --repo-root . \"<terms>\"`."
    )


def _print_lifecycle_plan(plan: object, *, dry_run: bool) -> None:
    command = str(getattr(plan, "command", "") or "").strip() or "odylith"
    headline = str(getattr(plan, "headline", "") or "").strip()
    steps = tuple(getattr(plan, "steps", ()) or ())
    dirty_overlap = tuple(getattr(plan, "dirty_overlap", ()) or ())
    notes = tuple(getattr(plan, "notes", ()) or ())
    print(f"{command} {'dry-run' if dry_run else 'plan'}")
    if headline:
        print(f"- summary: {headline}")
    for index, step in enumerate(steps, start=1):
        label = str(getattr(step, "label", "") or "").strip()
        mutation_classes = ", ".join(str(token).strip() for token in getattr(step, "mutation_classes", ()) or () if str(token).strip())
        paths = [str(token).strip() for token in getattr(step, "paths", ()) or () if str(token).strip()]
        detail = str(getattr(step, "detail", "") or "").strip()
        print(f"- step {index}/{len(steps)}: {label}")
        if mutation_classes:
            print(f"  mutation_classes: {mutation_classes}")
        if paths:
            preview = ", ".join(paths[:4])
            suffix = "" if len(paths) <= 4 else f", +{len(paths) - 4} more"
            print(f"  paths: {preview}{suffix}")
        if detail:
            print(f"  detail: {detail}")
    if dirty_overlap:
        print("- dirty_overlap:")
        for line in dirty_overlap:
            print(f"  {line}")
    if notes:
        print("- notes:")
        for note in notes:
            print(f"  {note}")
    if dry_run:
        print("dry-run mode: no files written")


def _start_bootstrap_payload(args: argparse.Namespace) -> dict[str, object]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    return odylith_context_engine_store.build_session_bootstrap(
        repo_root=Path(args.repo_root).expanduser().resolve(),
        use_working_tree=bool(args.working_tree),
        working_tree_scope=str(args.working_tree_scope),
    )


def _single_line_error(exc: Exception) -> str:
    return " ".join(str(exc).strip().split()) or exc.__class__.__name__


def _bootstrap_failure_guidance(*, repo_root: str | Path) -> tuple[str, str]:
    hosted_install_command = "curl -fsSL https://github.com/odylith/odylith/releases/latest/download/install.sh | bash"
    repair_command = preferred_repair_entrypoint(repo_root=repo_root) or hosted_install_command
    if repair_command == hosted_install_command:
        followup = "./.odylith/bin/odylith start --repo-root ."
    else:
        followup = "./.odylith/bin/odylith bootstrap --repo-root . --no-working-tree"
    return repair_command, followup


def _prepare_consumer_upgrade_spotlight(*, repo_root: Path, summary: object, source_repo: str) -> bool:
    active_version = str(getattr(summary, "active_version", "") or "").strip()
    previous_version = str(getattr(summary, "previous_version", "") or "").strip()
    repo_role = str(getattr(summary, "repo_role", "") or "").strip()
    if source_repo or repo_role == "product_repo" or not active_version or not previous_version or previous_version == active_version:
        clear_upgrade_spotlight(repo_root=repo_root)
        return False
    write_upgrade_spotlight(
        repo_root=repo_root,
        from_version=previous_version,
        to_version=active_version,
        release_tag=str(getattr(summary, "release_tag", "") or "").strip(),
        release_url=str(getattr(summary, "release_url", "") or "").strip(),
        release_published_at=str(getattr(summary, "release_published_at", "") or "").strip(),
        release_body=str(getattr(summary, "release_body", "") or "").strip(),
        highlights=tuple(
            str(item).strip()
            for item in getattr(summary, "release_highlights", ()) or ()
            if str(item).strip()
        ),
    )
    return True


def _refresh_dashboard_after_upgrade(*, repo_root: Path) -> tuple[bool, str]:
    print("Refreshing Odylith dashboard surfaces so the local shell reflects the new release.")
    render_rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=repo_root,
        surfaces=_DEFAULT_DASHBOARD_REFRESH_SURFACES,
        runtime_mode="auto",
        atlas_sync=False,
    )
    if render_rc != 0:
        return (
            False,
            "Odylith upgrade succeeded, but dashboard refresh failed. Retry with `./.odylith/bin/odylith dashboard refresh --repo-root .`.",
    )
    return True, "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."


def _print_legacy_migration_summary(summary: object) -> None:
    migration = getattr(summary, "migration", None)
    if migration is None or bool(getattr(migration, "already_migrated", False)):
        return
    print("Migrated legacy repo roots into the Odylith layout before continuing.")
    moved_paths = tuple(str(item).strip() for item in getattr(migration, "moved_paths", ()) if str(item).strip())
    removed_paths = tuple(str(item).strip() for item in getattr(migration, "removed_paths", ()) if str(item).strip())
    if moved_paths:
        print("Carried forward:")
        for item in moved_paths:
            print(f"- {item}")
    if removed_paths:
        print("Purged legacy volatile state:")
        for item in removed_paths:
            print(f"- {item}")


def _cmd_install_common(
    args: argparse.Namespace,
    *,
    adopt_latest_default: bool = False,
) -> int:
    requested_repo_root = Path(args.repo_root).expanduser().resolve()
    first_install = _is_first_install(repo_root=requested_repo_root)
    adopt_latest = bool(adopt_latest_default or getattr(args, "adopt_latest", False))
    release_repo = str(getattr(args, "release_repo", AUTHORITATIVE_RELEASE_REPO) or AUTHORITATIVE_RELEASE_REPO).strip()
    target_version = str(getattr(args, "target_version", "") or "").strip()
    lifecycle_plan = plan_install_lifecycle(
        repo_root=requested_repo_root,
        adopt_latest=adopt_latest,
        target_version=target_version,
    )
    _print_lifecycle_plan(lifecycle_plan, dry_run=bool(getattr(args, "dry_run", False)))
    if bool(getattr(args, "dry_run", False)):
        return 0
    summary = install_bundle(repo_root=args.repo_root, bundle_root=bundle_root(), version=args.version or __version__)
    _print_legacy_migration_summary(summary)
    final_version = str(summary.version or "").strip() or __version__
    final_launcher_path = summary.launcher_path
    missing_surfaces = _missing_first_run_surfaces(repo_root=summary.repo_root)
    if missing_surfaces:
        if first_install:
            print("Rendering first-run Odylith surfaces so the local shell is immediately usable.")
        else:
            print("Refreshing missing Odylith surfaces so the local shell stays usable.")
        render_rc = _bootstrap_first_run_surfaces(repo_root=summary.repo_root)
        remaining_missing = _missing_first_run_surfaces(repo_root=summary.repo_root)
        if render_rc != 0 or remaining_missing:
            print("Odylith runtime install succeeded, but the first-run Odylith shell is incomplete.", file=sys.stderr)
            for path in remaining_missing:
                print(f"- missing surface: {path}", file=sys.stderr)
            print(
                "Retry with `./.odylith/bin/odylith sync --repo-root . --force --impact-mode full`, or repair with `./.odylith/bin/odylith doctor --repo-root . --repair`.",
                file=sys.stderr,
            )
            return render_rc or 1
    if adopt_latest:
        try:
            upgrade_summary = upgrade_install(
                repo_root=args.repo_root,
                release_repo=release_repo,
                version=target_version,
                write_pin=True,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        final_version = str(upgrade_summary.active_version or final_version).strip() or final_version
        final_launcher_path = Path(getattr(upgrade_summary, "launcher_path", final_launcher_path))
        if first_install:
            clear_upgrade_spotlight(repo_root=requested_repo_root)
        else:
            _prepare_consumer_upgrade_spotlight(
                repo_root=requested_repo_root,
                summary=upgrade_summary,
                source_repo="",
            )
        _refreshed, refresh_message = _refresh_dashboard_after_upgrade(repo_root=summary.repo_root)
        print(refresh_message)
    dashboard_path = summary.repo_root / "odylith" / "index.html"
    if first_install:
        print(f"Odylith {final_version} is ready in {summary.repo_root / 'odylith'}.")
    elif adopt_latest:
        if target_version:
            print(f"Odylith was reinstalled on verified release {final_version} and the repo pin was updated to match.")
        else:
            print(f"Odylith was reinstalled on the latest verified release: {final_version}. Repo pin updated to match.")
    else:
        print(f"Odylith is already installed here on {final_version}.")
    print(f"Launcher: {final_launcher_path}")
    print(f"Dashboard: {dashboard_path}")
    if summary.repo_guidance_created:
        print(f"Created root AGENTS.md at {summary.repo_root / 'AGENTS.md'}.")
    if getattr(summary, "gitignore_updated", False):
        print("Added `/.odylith/` to the root `.gitignore` so Odylith runtime state stays untracked.")
    if not summary.git_repo_present:
        print("This folder is not backed by Git yet. Odylith still installs here, but Git-aware features stay limited until `.git` exists.")
        print("That means working-tree intelligence, background autospawn, and git-fsmonitor watcher help stay reduced for now.")
    print(
        "Repo-root AGENTS now activates Odylith guidance, skills, and the Codex-native spawn path for most grounded work."
    )
    print(
        "Full Odylith is installed by default. Delivery is layered under the hood so Odylith can reuse unchanged runtime payloads during later repairs and upgrades."
    )
    print(
        "No extra shell setup is required. Odylith is used through an AI coding agent such as Codex or Claude Code; the agent is the execution interface and `odylith/index.html` is the operating surface that keeps intent, constraints, topology, and execution state visible."
    )
    if adopt_latest:
        print("This reinstall flow keeps the managed runtime and the tracked repo pin aligned in one step.")
    print(
        "Next: open the repo in Codex or Claude Code, paste this starter prompt, and use `odylith/index.html` as the first-run Odylith launchpad."
    )
    _print_grounding_quickstart()
    print("Starter prompt:")
    print(_format_bold(shell_onboarding.STARTER_PROMPT))
    opened_dashboard, open_message = _maybe_open_dashboard_in_browser(
        dashboard_path=dashboard_path,
        enabled=first_install and not bool(args.no_open),
    )
    if opened_dashboard:
        print("Opened `odylith/index.html` in your browser.")
    elif open_message:
        print(open_message)
    print(
        "Use `./.odylith/bin/odylith version --repo-root .` anytime to inspect posture, or `./.odylith/bin/odylith doctor --repo-root . --repair` if the local tree ever drifts."
    )
    print(
        "If `./.odylith/bin/odylith` is missing, use `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair` to restore the repo-local launcher."
    )
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    return _cmd_install_common(args)


def _cmd_reinstall(args: argparse.Namespace) -> int:
    requested_repo_root = Path(args.repo_root).expanduser().resolve()
    first_install = _is_first_install(repo_root=requested_repo_root)
    target_version = str(args.target_version or "").strip()
    lifecycle_plan = plan_reinstall_lifecycle(
        repo_root=requested_repo_root,
        target_version=target_version,
    )
    _print_lifecycle_plan(lifecycle_plan, dry_run=bool(getattr(args, "dry_run", False)))
    if bool(getattr(args, "dry_run", False)):
        return 0
    try:
        summary = reinstall_install(
            repo_root=args.repo_root,
            release_repo=args.release_repo,
            version=target_version,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_legacy_migration_summary(summary)

    _prepare_consumer_upgrade_spotlight(
        repo_root=requested_repo_root,
        summary=summary,
        source_repo="",
    )

    if _missing_first_run_surfaces(repo_root=requested_repo_root):
        if first_install:
            print("Rendering first-run Odylith surfaces so the local shell is immediately usable.")
        else:
            print("Refreshing missing Odylith surfaces so the local shell stays usable.")
        render_rc = _bootstrap_first_run_surfaces(repo_root=requested_repo_root)
        remaining_missing = _missing_first_run_surfaces(repo_root=requested_repo_root)
        if render_rc != 0 or remaining_missing:
            print("Odylith runtime reinstall succeeded, but the first-run Odylith shell is incomplete.", file=sys.stderr)
            for path in remaining_missing:
                print(f"- missing surface: {path}", file=sys.stderr)
            print(
                "Retry with `./.odylith/bin/odylith sync --repo-root . --force --impact-mode full`, or repair with `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair`.",
                file=sys.stderr,
            )
            return render_rc or 1
    else:
        _refreshed, refresh_message = _refresh_dashboard_after_upgrade(repo_root=requested_repo_root)
        print(refresh_message)

    active_version = str(summary.active_version or "").strip()
    previous_version = str(summary.previous_version or "").strip()
    pinned_version = str(summary.pinned_version or "").strip()
    repaired = bool(getattr(summary, "repaired", False))
    if first_install:
        print(f"Odylith {active_version} is ready in {requested_repo_root / 'odylith'}.")
    elif previous_version and previous_version != active_version:
        print(f"Reinstalled Odylith from {previous_version} to {active_version} and adopted the verified repo pin.")
    elif repaired:
        print(f"Reinstalled Odylith {active_version} and repaired the local runtime in place.")
    else:
        print(f"Odylith is already on the latest verified release: {active_version}. Reaffirmed the repo pin and local runtime.")
    if summary.pin_changed:
        print(f"Repo pin updated to {pinned_version}.")
    else:
        print(f"Repo pin remains {pinned_version}.")
    _print_release_highlights(summary)
    print(f"Repo-local launcher: {summary.launcher_path}")
    print(
        "If `./.odylith/bin/odylith` is missing, use `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair` to restore the repo-local launcher."
    )
    print("Odylith keeps the active runtime and one rollback target locally.")
    return 0


def _cmd_upgrade(args: argparse.Namespace) -> int:
    requested_repo_root = Path(args.repo_root).expanduser().resolve()
    lifecycle_plan = plan_upgrade_lifecycle(
        repo_root=requested_repo_root,
        version=str(args.target_version or "").strip(),
        source_repo=args.source_repo or None,
        write_pin=bool(args.write_pin),
    )
    _print_lifecycle_plan(lifecycle_plan, dry_run=bool(getattr(args, "dry_run", False)))
    if bool(getattr(args, "dry_run", False)):
        return 0
    try:
        summary = upgrade_install(
            repo_root=args.repo_root,
            release_repo=args.release_repo,
            version=args.target_version,
            source_repo=args.source_repo or None,
            write_pin=bool(args.write_pin),
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_legacy_migration_summary(summary)

    source_repo = str(args.source_repo or "").strip()
    repo_role = str(getattr(summary, "repo_role", "") or "").strip()
    followed_latest = bool(getattr(summary, "followed_latest", False))
    active_version = str(summary.active_version or "").strip()
    previous_version = str(summary.previous_version or "").strip()
    pinned_version = str(summary.pinned_version or "").strip()

    if source_repo:
        print(f"Odylith is now running from local source repo {Path(str(args.source_repo)).expanduser().resolve()}.")
    else:
        if previous_version and previous_version != active_version:
            if summary.pin_changed and pinned_version == active_version:
                print(f"Upgraded Odylith from {previous_version} to {active_version} and advanced the repo pin.")
            else:
                print(f"Upgraded Odylith from {previous_version} to {active_version}.")
        else:
            if summary.pin_changed and pinned_version == active_version:
                if followed_latest and repo_role != "product_repo":
                    print(f"Odylith is already on the latest verified release: {active_version}. Advanced the repo pin to match.")
                else:
                    print(f"Odylith is already on {active_version}. Advanced the repo pin to match.")
            elif followed_latest and repo_role != "product_repo":
                print(f"Odylith is already on the latest verified release: {active_version}.")
            elif not str(args.target_version or "").strip() and repo_role == "product_repo":
                print(f"Odylith is already on the tracked self-host pin: {active_version}.")
            else:
                print(f"Odylith is already on {active_version}.")
        if not (summary.pin_changed and pinned_version == active_version):
            if summary.pin_changed:
                print(f"Repo pin updated to {pinned_version}.")
            else:
                print(f"Repo pin remains {pinned_version}.")
        _print_release_highlights(summary)
    print(f"Repo-local launcher: {summary.launcher_path}")
    _prepare_consumer_upgrade_spotlight(
        repo_root=requested_repo_root,
        summary=summary,
        source_repo=source_repo,
    )
    _refreshed, message = _refresh_dashboard_after_upgrade(repo_root=requested_repo_root)
    print(message)
    print("Odylith keeps the active runtime and one rollback target locally.")
    return 0


def _cmd_rollback(args: argparse.Namespace) -> int:
    if not args.previous:
        print("rollback currently requires --previous.", file=sys.stderr)
        return 2
    try:
        summary = rollback_install(repo_root=args.repo_root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Odylith rolled back from {summary.previous_version or 'unknown'} to {summary.active_version}.")
    if summary.diverged_from_pin:
        print(f"Active version now diverges from repo pin {summary.pinned_version}.")
    else:
        print(f"Active version matches repo pin {summary.pinned_version}.")
    print(f"Repo-local launcher: {summary.launcher_path}")
    return 0


def _cmd_version(args: argparse.Namespace) -> int:
    status = version_status(repo_root=args.repo_root)
    available = ", ".join(status.available_versions) if status.available_versions else "(none)"
    context_engine_pack = (
        "n/a"
        if status.context_engine_pack_installed is None
        else "installed" if status.context_engine_pack_installed else "not installed"
    )
    release_eligible = (
        "n/a"
        if status.release_eligible is None
        else "yes" if status.release_eligible else "no"
    )
    print(f"Repo root: {status.repo_root}")
    print(f"Repo role: {status.repo_role}")
    print(f"Posture: {status.posture}")
    print(f"Runtime source: {status.runtime_source}")
    if status.runtime_source == "pinned_runtime":
        print("Runtime interpreter: Odylith is using the managed Odylith Python runtime.")
    elif status.runtime_source == "source_checkout":
        print("Runtime interpreter: Odylith is running from a detached source checkout.")
    elif status.runtime_source == "verified_runtime":
        print("Runtime interpreter: Odylith is using a verified local runtime that is not the tracked pin.")
    else:
        print("Runtime interpreter: Odylith could not confirm a pinned managed runtime from the current posture.")
    print("Repo-code validation: use the repo's own project toolchain for application tests, builds, and linting.")
    print(f"Release eligible: {release_eligible}")
    print(f"Context engine mode: {status.context_engine_mode}")
    print(f"Context engine pack: {context_engine_pack}")
    print(f"Pinned: {status.pinned_version or 'unknown'}")
    print(f"Active: {status.active_version or 'unknown'}")
    print(f"Last known good: {status.last_known_good_version or 'unknown'}")
    print(f"Detached: {'yes' if status.detached else 'no'}")
    print(f"Diverged from pin: {'yes' if status.diverged_from_pin else 'no'}")
    print(f"Available: {available}")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    if args.reset_local_state and not args.repair:
        print("--reset-local-state requires --repair.", file=sys.stderr)
        return 2
    healthy, message = doctor_bundle(
        repo_root=args.repo_root,
        bundle_root=bundle_root(),
        repair=bool(args.repair),
        reset_local_state=bool(args.reset_local_state),
    )
    stream = sys.stdout if healthy else sys.stderr
    try:
        status = version_status(repo_root=args.repo_root)
    except Exception:
        status = None
    if status is not None:
        release_eligible = (
            "n/a"
            if status.release_eligible is None
            else "yes" if status.release_eligible else "no"
        )
        print(f"Repo role: {status.repo_role}", file=stream)
        print(f"Posture: {status.posture}", file=stream)
        print(f"Runtime source: {status.runtime_source}", file=stream)
        print(f"Release eligible: {release_eligible}", file=stream)
        print(f"Context engine mode: {status.context_engine_mode}", file=stream)
        print(
            "Context engine pack: "
            + (
                "n/a"
                if status.context_engine_pack_installed is None
                else "installed" if status.context_engine_pack_installed else "not installed"
            ),
            file=stream,
        )
    print(message, file=stream)
    return 0 if healthy else 1


def _cmd_migrate_legacy_install(args: argparse.Namespace) -> int:
    summary = migrate_legacy_install(repo_root=args.repo_root)
    if summary.already_migrated:
        print("No legacy install layout was detected. Odylith is already the active layout.")
        print("Next: `./.odylith/bin/odylith start --repo-root .`")
        return 0
    print(f"Migrated legacy install state into `{summary.state_root}`.")
    if summary.moved_paths:
        print("Moved:")
        for item in summary.moved_paths:
            print(f"- {item}")
    if summary.removed_paths:
        print("Purged volatile Odylith state:")
        for item in summary.removed_paths:
            print(f"- {item}")
    print(f"Launcher: {summary.launcher_path}")
    print("Next: `./.odylith/bin/odylith start --repo-root .`")
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    preflight = evaluate_start_preflight(
        repo_root=args.repo_root,
        status_only=bool(args.status_only),
    )
    print("odylith start")
    if preflight.lane == "status":
        print(f"- lane: {preflight.lane}")
        print(f"- reason: {preflight.reason}")
        print(f"- next: {preflight.next_command}")
        return _cmd_version(argparse.Namespace(repo_root=args.repo_root))
    if preflight.lane in {"install", "repair"}:
        print(f"- lane: {preflight.lane}")
        print(f"- reason: {preflight.reason}")
        print(f"- next: {preflight.next_command}")
        return 1
    try:
        payload = _start_bootstrap_payload(args)
    except Exception as exc:
        next_command, next_followup = _bootstrap_failure_guidance(repo_root=args.repo_root)
        print("- lane: fallback")
        print(f"- reason: bootstrap packet build failed: {_single_line_error(exc)}")
        print(f"- next: {next_command}")
        print(f"- followup: {next_followup}")
        return 1
    narrowing_guidance = (
        dict(payload.get("narrowing_guidance", {}))
        if isinstance(payload.get("narrowing_guidance"), dict)
        else {}
    )
    fallback_required = bool(narrowing_guidance.get("required"))
    final_lane = "fallback" if fallback_required else "bootstrap"
    final_reason = str(narrowing_guidance.get("reason", "")).strip() if fallback_required else preflight.reason
    print(f"- lane: {final_lane}")
    print(f"- reason: {final_reason or preflight.reason}")
    if fallback_required:
        next_command = str(narrowing_guidance.get("next_fallback_command", "")).strip()
        next_followup = str(narrowing_guidance.get("next_fallback_followup", "")).strip()
        if next_command:
            print(f"- next: {next_command}")
        if next_followup:
            print(f"- followup: {next_followup}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if fallback_required else 0


def _cmd_uninstall(args: argparse.Namespace) -> int:
    uninstall_bundle(repo_root=args.repo_root)
    print("Odylith runtime integration was detached.")
    print("Customer-owned `odylith/` truth and local `.odylith/` state were preserved.")
    return 0


def _cmd_on(args: argparse.Namespace) -> int:
    enabled, message = set_agents_integration(repo_root=args.repo_root, enabled=True)
    print(message, file=sys.stdout if enabled else sys.stderr)
    if enabled:
        print("Repo guidance is active again. Start from the repo-local Odylith entrypoint before default repo-scan behavior.")
        _print_grounding_quickstart()
    return 0 if enabled else 1


def _cmd_off(args: argparse.Namespace) -> int:
    enabled, message = set_agents_integration(repo_root=args.repo_root, enabled=False)
    print(message, file=sys.stdout if enabled else sys.stderr)
    if enabled:
        print(
            "Repo guidance is detached. Codex falls back to the surrounding repo's default behavior until `./.odylith/bin/odylith on --repo-root .` restores it."
        )
        print("The local Odylith runtime and `odylith/` context stay installed.")
    return 0 if enabled else 1


def _cmd_sync(args: argparse.Namespace) -> int:
    if not _forwarded_has_flag(args.forwarded, "--check-only"):
        blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
        if blocked:
            return blocked
    return sync_workstream_artifacts.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_dashboard_refresh(args: argparse.Namespace) -> int:
    blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
    if blocked:
        return blocked
    try:
        surfaces_value = str(args.surfaces or "").strip() or ",".join(_DEFAULT_DASHBOARD_REFRESH_SURFACES)
        surfaces = sync_workstream_artifacts.normalize_dashboard_surfaces([surfaces_value])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=Path(args.repo_root).expanduser().resolve(),
        surfaces=surfaces,
        runtime_mode=str(args.runtime_mode),
        atlas_sync=bool(args.atlas_sync),
        dry_run=bool(args.dry_run),
    )


def _cmd_governance(args: argparse.Namespace) -> int:
    blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
    if blocked:
        return blocked
    target = {
        "normalize-plan-risk-mitigation": normalize_plan_risk_mitigation.main,
        "backfill-workstream-traceability": backfill_workstream_traceability.main,
        "reconcile-plan-workstream-binding": reconcile_plan_workstream_binding.main,
        "auto-promote-workstream-phase": auto_promote_workstream_phase.main,
        "sync-component-spec-requirements": sync_component_spec_requirements.main,
        "version-truth": lambda argv: version_truth.main([*argv, "check"]),
        "validate-guidance-portability": validate_guidance_portability.main,
        "validate-plan-traceability": validate_plan_traceability_contract.main,
    }[args.governance_command]
    return target(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_backlog(args: argparse.Namespace) -> int:
    blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
    if blocked:
        return blocked
    target = {
        "create": backlog_authoring.main,
    }[args.backlog_command]
    return target(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_validate(args: argparse.Namespace) -> int:
    if args.validate_command == "version-truth":
        forwarded = ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded)
        return version_truth.main([*forwarded, "check"])
    target = {
        "backlog-contract": validate_backlog_contract.main,
        "component-registry": validate_component_registry_contract.main,
        "component-registry-contract": validate_component_registry_contract.main,
        "guidance-portability": validate_guidance_portability.main,
        "plan-risk-mitigation": validate_plan_risk_mitigation_contract.main,
        "plan-risk-mitigation-contract": validate_plan_risk_mitigation_contract.main,
        "self-host-posture": validate_self_host_posture.main,
        "plan-traceability": validate_plan_traceability_contract.main,
        "plan-workstream-binding": validate_plan_workstream_binding.main,
    }[args.validate_command]
    return target(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_bootstrap(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    if bool(args.working_tree):
        forwarded.append("--working-tree")
        if str(args.working_tree_scope) != "session":
            forwarded.extend(["--working-tree-scope", str(args.working_tree_scope)])
    try:
        return _dispatch_context_engine_shortcut(
            repo_root=args.repo_root,
            target_command="bootstrap-session",
            forwarded=[*forwarded, *list(args.forwarded)],
        )
    except Exception as exc:
        next_command, next_followup = _bootstrap_failure_guidance(repo_root=args.repo_root)
        print("odylith bootstrap")
        print(f"- reason: Odylith bootstrap failed: {_single_line_error(exc)}")
        print(f"- next: {next_command}")
        print(f"- followup: {next_followup}")
        return 1


def _cmd_context_shortcut(args: argparse.Namespace) -> int:
    return _dispatch_context_engine_shortcut(
        repo_root=args.repo_root,
        target_command="context",
        forwarded=[str(args.ref), *list(args.forwarded)],
    )


def _cmd_query_shortcut(args: argparse.Namespace) -> int:
    return _dispatch_context_engine_shortcut(
        repo_root=args.repo_root,
        target_command="query",
        forwarded=[str(args.text), *list(args.forwarded)],
    )


def _cmd_context_engine(args: argparse.Namespace) -> int:
    _maybe_stage_context_engine_pack(repo_root=args.repo_root, forwarded=args.forwarded)
    return odylith_context_engine.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_benchmark(args: argparse.Namespace) -> int:
    forwarded = list(args.forwarded)
    if forwarded and str(forwarded[0]).strip() == "compare":
        parser = argparse.ArgumentParser(
            prog="odylith benchmark compare",
            description="Compare the latest benchmark report against a stored baseline.",
        )
        parser.add_argument("--repo-root", default=args.repo_root)
        parser.add_argument("--baseline", default="last-shipped")
        parser.add_argument("--json", action="store_true", dest="as_json")
        parsed = parser.parse_args(forwarded[1:])
        result = benchmark_compare.compare_latest_to_baseline(
            repo_root=parsed.repo_root,
            baseline=parsed.baseline,
        )
        if parsed.as_json:
            print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        else:
            print(benchmark_compare.render_compare_text(result))
        if result.status == "fail":
            return 2
        if result.status == "unavailable":
            return 1
        return 0
    _maybe_stage_context_engine_pack(repo_root=args.repo_root, forwarded=["benchmark"])
    return odylith_context_engine.main(
        ["--repo-root", str(Path(args.repo_root).expanduser().resolve()), "benchmark", *forwarded]
    )


def _cmd_lane_status(args: argparse.Namespace) -> int:
    forwarded: list[str] = ["--repo-root", str(Path(args.repo_root).expanduser().resolve())]
    if bool(args.as_json):
        forwarded.append("--json")
    return maintainer_lane_status.main(forwarded)


def _cmd_compass_log(args: argparse.Namespace) -> int:
    return log_compass_timeline_event.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_compass_update(args: argparse.Namespace) -> int:
    blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
    if blocked:
        return blocked
    return update_compass.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_compass_watch_transactions(args: argparse.Namespace) -> int:
    return watch_prompt_transactions.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_compass_restore_history(args: argparse.Namespace) -> int:
    return restore_compass_history.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_subagent_router(args: argparse.Namespace) -> int:
    return subagent_router.main(ensure_nested_subcommand_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_subagent_orchestrator(args: argparse.Namespace) -> int:
    return subagent_orchestrator.main(
        ensure_nested_subcommand_repo_root_args(repo_root=args.repo_root, argv=args.forwarded)
    )


def _cmd_atlas_render(args: argparse.Namespace) -> int:
    blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
    if blocked:
        return blocked
    return render_mermaid_catalog.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_atlas_auto_update(args: argparse.Namespace) -> int:
    blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
    if blocked:
        return blocked
    return auto_update_mermaid_diagrams.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_atlas_scaffold(args: argparse.Namespace) -> int:
    blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
    if blocked:
        return blocked
    return scaffold_mermaid_diagram.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def _cmd_atlas_install_autosync_hook(args: argparse.Namespace) -> int:
    blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
    if blocked:
        return blocked
    return install_mermaid_autosync_hook.main(ensure_repo_root_args(repo_root=args.repo_root, argv=args.forwarded))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="odylith", description="Odylith install, grounding, sync, runtime, and repair tooling.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser(
        "start",
        help="Choose the safest first Odylith turn-start path: status, repair, install guidance, or bootstrap grounding.",
    )
    start.add_argument("--repo-root", default=".", help="Consumer repository root.")
    start.add_argument(
        "--status-only",
        action="store_true",
        help="Report the chosen start posture without building a bootstrap packet.",
    )
    start.add_argument(
        "--no-working-tree",
        action="store_false",
        dest="working_tree",
        default=True,
        help="Skip auto-including meaningful changed paths from the git working tree on the bootstrap path.",
    )
    start.add_argument(
        "--working-tree-scope",
        choices=("repo", "session"),
        default="session",
        help="When working-tree grounding is included, use the full repo dirty set or only this session's scoped paths.",
    )

    lane = subparsers.add_parser("lane", help="Inspect maintainer lane posture and next action.")
    lane_subparsers = lane.add_subparsers(dest="lane_command", required=True)
    lane_status = lane_subparsers.add_parser(
        "status",
        help="Show maintainer lane posture, release session, version drift, and the exact next command.",
    )
    lane_status.add_argument("--repo-root", default=".", help="Consumer repository root.")
    lane_status.add_argument("--json", action="store_true", dest="as_json", help="Render lane status as JSON.")

    install = subparsers.add_parser("install", help="Install or rematerialize Odylith into the current repository.")
    install.add_argument("--repo-root", default=".", help="Consumer repository root.")
    install.add_argument("--version", default="", help="Optional bundle version override.")
    install.add_argument(
        "--adopt-latest",
        action="store_true",
        help="After rematerializing the local install, adopt the latest verified release and update the repo pin in the same step.",
    )
    install.add_argument("--release-repo", default=AUTHORITATIVE_RELEASE_REPO, help=argparse.SUPPRESS)
    install.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the install mutation plan without writing files.",
    )
    install.add_argument(
        "--no-open",
        action="store_true",
        help="Do not auto-open `odylith/index.html` in a browser after a successful first local install.",
    )

    reinstall = subparsers.add_parser(
        "reinstall",
        help="Reinstall Odylith and adopt a verified pinned runtime in one step.",
    )
    reinstall.add_argument("--repo-root", default=".", help="Consumer repository root.")
    reinstall.add_argument("--version", default="", help=argparse.SUPPRESS)
    reinstall.add_argument("--release-repo", default=AUTHORITATIVE_RELEASE_REPO, help=argparse.SUPPRESS)
    reinstall.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the reinstall mutation plan without writing files.",
    )
    reinstall.add_argument(
        "--to",
        dest="target_version",
        default="",
        help="Explicit verified release to reinstall and pin. Defaults to the latest verified release.",
    )
    reinstall.add_argument(
        "--latest",
        action="store_true",
        help="Reinstall onto the latest verified release. This is the default when `--to` is not provided.",
    )
    reinstall.add_argument(
        "--no-open",
        action="store_true",
        help="Do not auto-open `odylith/index.html` in a browser after a successful first local install.",
    )

    upgrade = subparsers.add_parser("upgrade", help="Stage and activate the pinned Odylith runtime without rewriting repo-owned truth.")
    upgrade.add_argument("--repo-root", default=".", help="Consumer repository root.")
    upgrade.add_argument("--release-repo", default=AUTHORITATIVE_RELEASE_REPO, help="GitHub release repository.")
    upgrade.add_argument("--to", dest="target_version", default="", help="Explicit target version. Requires --write-pin when it differs from the repo pin.")
    upgrade.add_argument("--version", dest="target_version", help=argparse.SUPPRESS)
    upgrade.add_argument("--write-pin", action="store_true", help="Maintainer workflow: write the requested version into odylith/runtime/source/product-version.v1.json.")
    upgrade.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the upgrade mutation plan without writing files.",
    )
    upgrade.add_argument(
        "--source-repo",
        default="",
        help="Optional local Odylith source checkout for development-only source-local activation.",
    )

    rollback = subparsers.add_parser("rollback", help="Atomically return to the previous verified local Odylith runtime.")
    rollback.add_argument("--repo-root", default=".", help="Consumer repository root.")
    rollback.add_argument("--previous", action="store_true", help="Rollback to the previously active verified runtime.")

    version = subparsers.add_parser("version", help="Show pinned, active, and locally available Odylith product versions.")
    version.add_argument("--repo-root", default=".", help="Consumer repository root.")

    doctor = subparsers.add_parser("doctor", help="Verify the current Odylith install and optionally repair it.")
    doctor.add_argument("--repo-root", default=".", help="Consumer repository root.")
    doctor.add_argument("--repair", action="store_true", help="Repair the current install in place.")
    doctor.add_argument(
        "--reset-local-state",
        action="store_true",
        help="Clear local-only cache, tuning, and derived runtime state before repair.",
    )
    migrate = subparsers.add_parser(
        "migrate-legacy-install",
        help="Rewrite a legacy install into the Odylith root layout and purge volatile Odylith state.",
    )
    migrate.add_argument("--repo-root", default=".", help="Consumer repository root.")

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help="Build the default fresh-session Odylith bootstrap packet for a grounded turn start.",
    )
    bootstrap.add_argument("--repo-root", default=".", help="Consumer repository root.")
    bootstrap.add_argument(
        "--no-working-tree",
        action="store_false",
        dest="working_tree",
        default=True,
        help="Skip auto-including meaningful changed paths from the git working tree.",
    )
    bootstrap.add_argument(
        "--working-tree-scope",
        choices=("repo", "session"),
        default="session",
        help="When working-tree grounding is included, use the full repo dirty set or only this session's scoped paths.",
    )
    bootstrap.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    context_shortcut = subparsers.add_parser(
        "context",
        help="Resolve one exact repo entity or path into an Odylith context dossier.",
    )
    context_shortcut.add_argument("--repo-root", default=".", help="Consumer repository root.")
    context_shortcut.add_argument("ref", help="Entity id, component name, or repo-relative path.")
    context_shortcut.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    query_shortcut = subparsers.add_parser(
        "query",
        help="Search the local Odylith projection store from the top-level CLI.",
    )
    query_shortcut.add_argument("--repo-root", default=".", help="Consumer repository root.")
    query_shortcut.add_argument("text", help="Query text.")
    query_shortcut.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    for command, _target, help_text in _CONTEXT_ENGINE_SHORTCUTS:
        if command in _EXPLICIT_CONTEXT_ENGINE_SHORTCUTS:
            continue
        shortcut = subparsers.add_parser(command, help=help_text)
        shortcut.add_argument("--repo-root", default=".", help="Consumer repository root.")
        shortcut.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    uninstall = subparsers.add_parser(
        "uninstall",
        help="Remove Odylith runtime integration while leaving the odylith/ context tree in place.",
    )
    uninstall.add_argument("--repo-root", default=".", help="Consumer repository root.")

    on = subparsers.add_parser(
        "on",
        help="Restore Odylith-first guidance so coding agents use Odylith as the default first path in this repository.",
    )
    on.add_argument("--repo-root", default=".", help="Consumer repository root.")

    off = subparsers.add_parser(
        "off",
        help="Detach Odylith-first guidance so coding agents fall back to the repository's default behavior without uninstalling Odylith.",
    )
    off.add_argument("--repo-root", default=".", help="Consumer repository root.")

    sync = subparsers.add_parser("sync", help="Run the Odylith governance and surface sync pipeline.")
    sync.add_argument("--repo-root", default=".", help="Consumer repository root.")
    sync.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    dashboard = subparsers.add_parser("dashboard", help="Refresh local Odylith dashboard surfaces without a full governance sync.")
    dashboard_subparsers = dashboard.add_subparsers(dest="dashboard_command", required=True)
    dashboard_refresh = dashboard_subparsers.add_parser(
        "refresh",
        help="Refresh selected local dashboard surfaces without Registry or plan reconciliation churn.",
    )
    dashboard_refresh.add_argument("--repo-root", default=".", help="Consumer repository root.")
    dashboard_refresh.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the dashboard refresh plan without writing files.",
    )
    dashboard_refresh.add_argument(
        "--surfaces",
        default=_DEFAULT_DASHBOARD_REFRESH_SURFACES_CSV,
        help="Comma-separated surfaces to refresh: tooling_shell, radar, compass, atlas, registry, casebook.",
    )
    dashboard_refresh.add_argument(
        "--atlas-sync",
        action="store_true",
        help="When Atlas is selected, also rerender stale Mermaid source diagrams before refreshing the Atlas dashboard.",
    )
    dashboard_refresh.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help=(
            "Execution mode for the render helpers. `auto` prefers the local runtime-backed fast path, "
            "`standalone` stays subprocess-only, and `daemon` requires runtime-backed execution."
        ),
    )

    governance = subparsers.add_parser("governance", help="Run Odylith governance maintenance helpers.")
    governance_subparsers = governance.add_subparsers(dest="governance_command", required=True)
    for command, help_text in (
        ("normalize-plan-risk-mitigation", "Normalize technical-plan risk/mitigation sections."),
        ("backfill-workstream-traceability", "Backfill Radar idea traceability metadata."),
        ("reconcile-plan-workstream-binding", "Reconcile active plan to Radar workstream bindings."),
        ("auto-promote-workstream-phase", "Promote planning workstreams to implementation from live evidence."),
        ("sync-component-spec-requirements", "Sync mapped Compass requirement evidence into component living specs."),
        ("version-truth", "Validate that generated Odylith version files match pyproject."),
        (
            "validate-guidance-portability",
            "Validate maintained guidance for portable Python and pytest invocation patterns.",
        ),
        ("validate-plan-traceability", "Validate technical-plan traceability bindings."),
    ):
        child_parser = governance_subparsers.add_parser(command, help=help_text)
        child_parser.add_argument("--repo-root", default=".", help="Consumer repository root.")
        child_parser.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    backlog = subparsers.add_parser("backlog", help="Create and maintain Radar backlog records.")
    backlog_subparsers = backlog.add_subparsers(dest="backlog_command", required=True)
    backlog_create = backlog_subparsers.add_parser(
        "create",
        help="Create one or more queued backlog workstreams and patch Radar INDEX.md automatically.",
    )
    backlog_create.add_argument("--repo-root", default=".", help="Consumer repository root.")
    backlog_create.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    validate = subparsers.add_parser("validate", help="Run Odylith governance and contract validators.")
    validate_subparsers = validate.add_subparsers(dest="validate_command", required=True)
    for command, help_text in (
        ("backlog-contract", "Validate Radar backlog and plan linkage contracts."),
        ("component-registry", "Validate Registry component inventory contracts."),
        ("component-registry-contract", "Validate Registry component inventory contracts."),
        ("guidance-portability", "Validate maintained guidance for portable Python and pytest invocation patterns."),
        ("plan-risk-mitigation", "Validate technical-plan risk and mitigation sections."),
        ("plan-risk-mitigation-contract", "Validate technical-plan risk and mitigation sections."),
        ("self-host-posture", "Validate Odylith product-repo self-host posture and release gating invariants."),
        ("plan-traceability", "Validate technical-plan traceability bindings."),
        ("plan-workstream-binding", "Validate active-plan workstream bindings."),
        ("version-truth", "Validate that generated Odylith version files match pyproject."),
    ):
        child_parser = validate_subparsers.add_parser(command, help=help_text)
        child_parser.add_argument("--repo-root", default=".", help="Consumer repository root.")
        child_parser.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    context_engine = subparsers.add_parser("context-engine", help="Run Odylith Context Engine commands.")
    context_engine.add_argument("--repo-root", default=".", help="Consumer repository root.")
    context_engine.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    benchmark = subparsers.add_parser("benchmark", help="Run the Odylith benchmark harness.")
    benchmark.add_argument("--repo-root", default=".", help="Consumer repository root.")
    benchmark.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    compass = subparsers.add_parser("compass", help="Log or refresh Compass runtime events.")
    compass_subparsers = compass.add_subparsers(dest="compass_command", required=True)
    compass_log = compass_subparsers.add_parser("log", help="Append one Compass timeline event.")
    compass_log.add_argument("--repo-root", default=".", help="Consumer repository root.")
    compass_log.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    compass_update = compass_subparsers.add_parser("update", help="Append Compass updates and refresh the surface.")
    compass_update.add_argument("--repo-root", default=".", help="Consumer repository root.")
    compass_update.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    compass_restore_history = compass_subparsers.add_parser(
        "restore-history",
        help="Restore archived Compass daily history into the active calendar.",
    )
    compass_restore_history.add_argument("--repo-root", default=".", help="Consumer repository root.")
    compass_restore_history.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    compass_watch_transactions = compass_subparsers.add_parser(
        "watch-transactions",
        help="Watch Compass/Radar prompt-transaction inputs and refresh on change.",
    )
    compass_watch_transactions.add_argument("--repo-root", default=".", help="Consumer repository root.")
    compass_watch_transactions.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    subagent_router_parser = subparsers.add_parser("subagent-router", help="Run Odylith bounded leaf-routing commands.")
    subagent_router_parser.add_argument("--repo-root", default=".", help="Consumer repository root.")
    subagent_router_parser.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    subagent_orchestrator_parser = subparsers.add_parser(
        "subagent-orchestrator",
        help="Run Odylith prompt-level orchestration commands.",
    )
    subagent_orchestrator_parser.add_argument("--repo-root", default=".", help="Consumer repository root.")
    subagent_orchestrator_parser.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    atlas = subparsers.add_parser("atlas", help="Render or maintain Atlas diagram assets.")
    atlas_subparsers = atlas.add_subparsers(dest="atlas_command", required=True)
    atlas_render = atlas_subparsers.add_parser("render", help="Render Atlas from the Mermaid catalog.")
    atlas_render.add_argument("--repo-root", default=".", help="Consumer repository root.")
    atlas_render.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    atlas_auto_update = atlas_subparsers.add_parser(
        "auto-update",
        help="Refresh Atlas diagrams from change-watch metadata.",
    )
    atlas_auto_update.add_argument("--repo-root", default=".", help="Consumer repository root.")
    atlas_auto_update.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the Atlas auto-update mutation plan without writing files.",
    )
    atlas_auto_update.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    atlas_scaffold = atlas_subparsers.add_parser("scaffold", help="Scaffold one Atlas diagram metadata entry and source.")
    atlas_scaffold.add_argument("--repo-root", default=".", help="Consumer repository root.")
    atlas_scaffold.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    atlas_hook = atlas_subparsers.add_parser(
        "install-autosync-hook",
        help="Install the optional Atlas auto-sync pre-commit hook.",
    )
    atlas_hook.add_argument("--repo-root", default=".", help="Consumer repository root.")
    atlas_hook.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> int:
    tokens = [str(token) for token in (argv or sys.argv[1:])]
    if tokens:
        if tokens[0] in _CONTEXT_ENGINE_SHORTCUT_TARGETS and tokens[0] not in _EXPLICIT_CONTEXT_ENGINE_SHORTCUTS:
            repo_root, forwarded = _extract_repo_root(tokens[1:])
            return _dispatch_context_engine_shortcut(
                repo_root=repo_root,
                target_command=_CONTEXT_ENGINE_SHORTCUT_TARGETS[tokens[0]],
                forwarded=forwarded,
            )
        if tokens[0] == "sync":
            repo_root, forwarded = _extract_repo_root(tokens[1:])
            if _help_requested(forwarded):
                parser = build_parser()
                args = parser.parse_args(tokens)
                return _cmd_sync(args)
            return _cmd_sync(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
        if tokens[0] == "governance" and len(tokens) >= 2:
            repo_root, forwarded = _extract_repo_root(tokens[2:])
            if tokens[1] in {
                "normalize-plan-risk-mitigation",
                "backfill-workstream-traceability",
                "reconcile-plan-workstream-binding",
                "auto-promote-workstream-phase",
                "sync-component-spec-requirements",
                "version-truth",
                "validate-guidance-portability",
                "validate-plan-traceability",
            }:
                if _help_requested(forwarded):
                    parser = build_parser()
                    args = parser.parse_args(tokens)
                    return _cmd_governance(args)
                return _cmd_governance(
                    argparse.Namespace(
                        repo_root=repo_root,
                        governance_command=tokens[1],
                        forwarded=forwarded,
                    )
                )
        if tokens[0] == "backlog" and len(tokens) >= 2:
            repo_root, forwarded = _extract_repo_root(tokens[2:])
            if tokens[1] == "create":
                if _help_requested(forwarded):
                    parser = build_parser()
                    args = parser.parse_args(tokens)
                    return _cmd_backlog(args)
                return _cmd_backlog(
                    argparse.Namespace(
                        repo_root=repo_root,
                        backlog_command="create",
                        forwarded=forwarded,
                    )
                )
        if tokens[0] == "validate" and len(tokens) >= 2:
            repo_root, forwarded = _extract_repo_root(tokens[2:])
            if tokens[1] == "version-truth":
                if _help_requested(forwarded):
                    parser = build_parser()
                    args = parser.parse_args(tokens)
                    return _cmd_validate(args)
                return version_truth.main(["--repo-root", repo_root, *forwarded, "check"])
            if _help_requested(forwarded):
                parser = build_parser()
                args = parser.parse_args(tokens)
                return _cmd_validate(args)
            target = {
                "backlog-contract": validate_backlog_contract.main,
                "component-registry": validate_component_registry_contract.main,
                "component-registry-contract": validate_component_registry_contract.main,
                "guidance-portability": validate_guidance_portability.main,
                "plan-risk-mitigation": validate_plan_risk_mitigation_contract.main,
                "plan-risk-mitigation-contract": validate_plan_risk_mitigation_contract.main,
                "self-host-posture": validate_self_host_posture.main,
                "plan-traceability": validate_plan_traceability_contract.main,
                "plan-workstream-binding": validate_plan_workstream_binding.main,
            }.get(tokens[1])
            if target is not None:
                return target(["--repo-root", repo_root, *forwarded])
        if tokens[0] == "lane" and len(tokens) >= 2 and tokens[1] == "status":
            repo_root, forwarded = _extract_repo_root(tokens[2:])
            if _help_requested(forwarded):
                parser = build_parser()
                args = parser.parse_args(tokens)
                return _cmd_lane_status(args)
            return maintainer_lane_status.main(["--repo-root", repo_root, *forwarded])
        if tokens[0] == "context-engine":
            repo_root, forwarded = _extract_repo_root(tokens[1:])
            if _help_requested(forwarded):
                parser = build_parser()
                args = parser.parse_args(tokens)
                return _cmd_context_engine(args)
            return odylith_context_engine.main(["--repo-root", repo_root, *forwarded])
        if tokens[0] == "benchmark":
            repo_root, forwarded = _extract_repo_root(tokens[1:])
            if _help_requested(forwarded):
                parser = build_parser()
                args = parser.parse_args(tokens)
                return _cmd_benchmark(args)
            if forwarded and str(forwarded[0]).strip() == "compare":
                return _cmd_benchmark(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
            return odylith_context_engine.main(["--repo-root", repo_root, "benchmark", *forwarded])
        if tokens[0] == "compass" and len(tokens) >= 2 and tokens[1] in {"log", "update", "restore-history", "watch-transactions"}:
            repo_root, forwarded = _extract_repo_root(tokens[2:])
            compass_command = tokens[1]
            if _help_requested(forwarded):
                parser = build_parser()
                args = parser.parse_args(tokens)
                if compass_command == "log":
                    return _cmd_compass_log(args)
                if compass_command == "update":
                    return _cmd_compass_update(args)
                if compass_command == "restore-history":
                    return _cmd_compass_restore_history(args)
                return _cmd_compass_watch_transactions(args)
            if compass_command == "log":
                return _cmd_compass_log(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
            if compass_command == "update":
                return _cmd_compass_update(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
            if compass_command == "restore-history":
                return _cmd_compass_restore_history(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
            return _cmd_compass_watch_transactions(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
        if tokens[0] == "subagent-router":
            repo_root, forwarded = _extract_repo_root(tokens[1:])
            return subagent_router.main(ensure_nested_subcommand_repo_root_args(repo_root=repo_root, argv=forwarded))
        if tokens[0] == "subagent-orchestrator":
            repo_root, forwarded = _extract_repo_root(tokens[1:])
            return subagent_orchestrator.main(
                ensure_nested_subcommand_repo_root_args(repo_root=repo_root, argv=forwarded)
            )
        if tokens[0] == "atlas" and len(tokens) >= 2 and tokens[1] in {"render", "auto-update", "scaffold", "install-autosync-hook"}:
            repo_root, forwarded = _extract_repo_root(tokens[2:])
            atlas_command = tokens[1]
            if _help_requested(forwarded):
                parser = build_parser()
                args = parser.parse_args(tokens)
                if atlas_command == "render":
                    return _cmd_atlas_render(args)
                if atlas_command == "auto-update":
                    return _cmd_atlas_auto_update(args)
                if atlas_command == "scaffold":
                    return _cmd_atlas_scaffold(args)
                return _cmd_atlas_install_autosync_hook(args)
            if atlas_command == "render":
                return _cmd_atlas_render(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
            if atlas_command == "auto-update":
                return _cmd_atlas_auto_update(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
            if atlas_command == "scaffold":
                return _cmd_atlas_scaffold(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))
            return _cmd_atlas_install_autosync_hook(argparse.Namespace(repo_root=repo_root, forwarded=forwarded))

    parser = build_parser()
    args = parser.parse_args(tokens)
    if args.command == "start":
        return _cmd_start(args)
    if args.command == "lane" and args.lane_command == "status":
        return _cmd_lane_status(args)
    if args.command == "install":
        return _cmd_install(args)
    if args.command == "reinstall":
        return _cmd_reinstall(args)
    if args.command == "upgrade":
        if bool(getattr(args, "write_pin", False)):
            blocked = _guard_product_repo_main_branch(repo_root=args.repo_root)
            if blocked:
                return blocked
        return _cmd_upgrade(args)
    if args.command == "rollback":
        return _cmd_rollback(args)
    if args.command == "version":
        return _cmd_version(args)
    if args.command == "doctor":
        return _cmd_doctor(args)
    if args.command == "migrate-legacy-install":
        return _cmd_migrate_legacy_install(args)
    if args.command == "bootstrap":
        return _cmd_bootstrap(args)
    if args.command == "context":
        return _cmd_context_shortcut(args)
    if args.command == "query":
        return _cmd_query_shortcut(args)
    if args.command in _CONTEXT_ENGINE_SHORTCUT_TARGETS:
        return _dispatch_context_engine_shortcut(
            repo_root=args.repo_root,
            target_command=_CONTEXT_ENGINE_SHORTCUT_TARGETS[args.command],
            forwarded=args.forwarded,
        )
    if args.command == "uninstall":
        return _cmd_uninstall(args)
    if args.command == "on":
        return _cmd_on(args)
    if args.command == "off":
        return _cmd_off(args)
    if args.command == "sync":
        return _cmd_sync(args)
    if args.command == "dashboard" and args.dashboard_command == "refresh":
        return _cmd_dashboard_refresh(args)
    if args.command == "backlog":
        return _cmd_backlog(args)
    if args.command == "governance":
        return _cmd_governance(args)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "context-engine":
        return _cmd_context_engine(args)
    if args.command == "benchmark":
        return _cmd_benchmark(args)
    if args.command == "compass" and args.compass_command == "log":
        return _cmd_compass_log(args)
    if args.command == "compass" and args.compass_command == "update":
        return _cmd_compass_update(args)
    if args.command == "compass" and args.compass_command == "restore-history":
        return _cmd_compass_restore_history(args)
    if args.command == "compass" and args.compass_command == "watch-transactions":
        return _cmd_compass_watch_transactions(args)
    if args.command == "subagent-router":
        return _cmd_subagent_router(args)
    if args.command == "subagent-orchestrator":
        return _cmd_subagent_orchestrator(args)
    if args.command == "atlas" and args.atlas_command == "render":
        return _cmd_atlas_render(args)
    if args.command == "atlas" and args.atlas_command == "auto-update":
        return _cmd_atlas_auto_update(args)
    if args.command == "atlas" and args.atlas_command == "scaffold":
        return _cmd_atlas_scaffold(args)
    if args.command == "atlas" and args.atlas_command == "install-autosync-hook":
        return _cmd_atlas_install_autosync_hook(args)
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

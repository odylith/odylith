"""Auto-update Mermaid diagrams when implementation files touch watched paths.

Workflow:
1) Detect changed files (git or explicit list).
2) Match changed files to diagram `change_watch_paths`.
3) Re-render impacted diagrams (SVG + PNG).
4) Refresh `last_reviewed_utc` for impacted diagrams.
5) Regenerate `odylith/atlas/atlas.html` and enforce freshness gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import dataclass
import json
import os
from pathlib import PurePosixPath, Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

from odylith.runtime.common import diagram_freshness
from odylith.runtime.common import generated_refresh_guard
from odylith.runtime.surfaces import mermaid_worker_session as _mermaid_worker_session
from odylith.runtime.surfaces.mermaid_worker_session import MermaidDiagramValidationError
from odylith.runtime.surfaces.mermaid_worker_session import _MermaidWorkerSession

select = _mermaid_worker_session.select
_ATLAS_AUTO_UPDATE_GUARD_NAMESPACE = "generated-refresh-guards"
_ATLAS_AUTO_UPDATE_GUARD_KEY = "atlas-auto-update"


@dataclass(frozen=True)
class AtlasExecutionStep:
    label: str
    mutation_classes: tuple[str, ...]
    paths: tuple[str, ...]


@dataclass(frozen=True)
class AtlasExecutionPlan:
    headline: str
    steps: tuple[AtlasExecutionStep, ...]
    dirty_overlap: tuple[str, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AtlasImpactClassification:
    impacted_items: tuple[dict[str, Any], ...]
    render_jobs: tuple[dict[str, str], ...]
    render_ids: tuple[str, ...]
    review_only_ids: tuple[str, ...]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith atlas auto-update",
        description="Auto-sync Mermaid diagrams from changed implementation files",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--catalog", default="odylith/atlas/source/catalog/diagrams.v1.json", help="Catalog JSON path")
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="Explicit changed path (repeatable, repository-relative)",
    )
    parser.add_argument(
        "--from-git-head",
        action="store_true",
        help="Include files changed vs HEAD (`git diff --name-only HEAD`)",
    )
    parser.add_argument(
        "--from-git-staged",
        action="store_true",
        help="Include staged files (`git diff --name-only --cached`)",
    )
    parser.add_argument(
        "--from-git-working-tree",
        action="store_true",
        help="Include unstaged files (`git diff --name-only`)",
    )
    parser.add_argument(
        "--mermaid-cli-version",
        default="11.12.0",
        help="Pinned Mermaid CLI version for rendering",
    )
    parser.add_argument(
        "--skip-render-catalog",
        action="store_true",
        help="Skip catalog render after updates",
    )
    parser.add_argument(
        "--fail-on-stale",
        action="store_true",
        help="Pass fail-on-stale to catalog renderer",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local runtime projection store when available for fast diagram selection.",
    )
    parser.add_argument(
        "--all-stale",
        action="store_true",
        help="Refresh every globally stale diagram selected by the Mermaid catalog freshness contract.",
    )
    parser.add_argument(
        "--max-review-age-days",
        type=int,
        default=21,
        help="Maximum allowed review age when `--all-stale` is used.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report impacted diagrams without writing")
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    raw = str(token or "").strip()
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _command_env() -> dict[str, str]:
    env = os.environ.copy()
    raw_pythonpath = str(env.get("PYTHONPATH", "")).strip()
    if raw_pythonpath:
        cwd = Path.cwd()
        env["PYTHONPATH"] = os.pathsep.join(
            str((cwd / token).resolve()) if token and not Path(token).is_absolute() else token
            for token in raw_pythonpath.split(os.pathsep)
        )
    return env


def _as_repo_path(repo_root: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(target.resolve())


def _git_changed_paths(*, repo_root: Path, args: list[str]) -> list[str]:
    cmd = ["git", *args]
    try:
        out = subprocess.run(
            cmd,
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{exc.stderr}") from exc
    result: list[str] = []
    for line in out.splitlines():
        token = line.strip()
        if token:
            result.append(PurePosixPath(token).as_posix())
    return result


def _normalize_paths(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        token = str(raw or "").strip()
        if not token:
            continue
        norm = PurePosixPath(token).as_posix()
        if norm in seen:
            continue
        seen.add(norm)
        result.append(norm)
    return result


def _dirty_overlap_for_paths(*, repo_root: Path, paths: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(token).strip() for token in paths if str(token).strip()))
    if not normalized or not (repo_root / ".git").exists():
        return ()
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *normalized,
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        return ()
    return tuple(line.rstrip() for line in str(completed.stdout or "").splitlines() if line.strip())


def _build_execution_plan(
    *,
    repo_root: Path,
    catalog_repo_path: str,
    render_catalog: bool,
    classification: AtlasImpactClassification,
) -> AtlasExecutionPlan:
    rendered_paths = tuple(
        dict.fromkeys(
            path
            for job in classification.render_jobs
            for path in (
                str(job.get("source_svg", "")).strip(),
                str(job.get("source_png", "")).strip(),
            )
            if path
        )
    )
    steps = [
        AtlasExecutionStep(
            label="Refresh catalog review markers and freshness fingerprints for the selected diagrams.",
            mutation_classes=("repo_owned_truth",),
            paths=(catalog_repo_path,),
        ),
    ]
    notes: list[str] = [
        "Dry-run previews repo-owned Atlas truth updates separately from generated diagram outputs.",
    ]
    if rendered_paths:
        steps.append(
            AtlasExecutionStep(
                label="Render the selected Mermaid diagram assets.",
                mutation_classes=("generated_surfaces",),
                paths=rendered_paths,
            )
        )
    elif classification.review_only_ids:
        notes.append(
            "Selected diagrams are review-only; Atlas will refresh freshness fingerprints without regenerating SVG or PNG assets."
        )
    if render_catalog:
        steps.append(
            AtlasExecutionStep(
                label="Rerender the Atlas dashboard and payload bundle from the updated catalog.",
                mutation_classes=("generated_surfaces",),
                paths=("odylith/atlas/atlas.html", "odylith/atlas/mermaid-payload.v1.js", "odylith/atlas/mermaid-app.v1.js"),
            )
        )
    all_paths = [path for step in steps for path in step.paths]
    return AtlasExecutionPlan(
        headline=(
            "Refresh "
            f"{len(classification.impacted_items)} impacted Atlas diagram(s) "
            f"({len(classification.render_jobs)} render, {len(classification.review_only_ids)} review-only)."
        ),
        steps=tuple(steps),
        dirty_overlap=_dirty_overlap_for_paths(repo_root=repo_root, paths=all_paths),
        notes=tuple(notes),
    )


def _print_execution_plan(plan: AtlasExecutionPlan, *, dry_run: bool) -> None:
    print(f"atlas auto-update {'dry-run' if dry_run else 'plan'}")
    print(f"- summary: {plan.headline}")
    for index, step in enumerate(plan.steps, start=1):
        print(f"- step {index}/{len(plan.steps)}: {step.label}")
        print(f"  mutation_classes: {', '.join(step.mutation_classes)}")
        if step.paths:
            preview = ", ".join(step.paths[:4])
            suffix = "" if len(step.paths) <= 4 else f", +{len(step.paths) - 4} more"
            print(f"  paths: {preview}{suffix}")
    if plan.dirty_overlap:
        print("- dirty_overlap:")
        for line in plan.dirty_overlap:
            print(f"  {line}")
    if plan.notes:
        print("- notes:")
        for note in plan.notes:
            print(f"  {note}")
    if dry_run:
        print("dry-run mode: no files written")


def _touches_watch(*, changed_path: str, watch_path: str) -> bool:
    changed = PurePosixPath(changed_path)
    watch = PurePosixPath(watch_path)
    if changed == watch:
        return True
    changed_parts = changed.parts
    watch_parts = watch.parts
    if len(changed_parts) >= len(watch_parts) and changed_parts[: len(watch_parts)] == watch_parts:
        return True
    if len(watch_parts) >= len(changed_parts) and watch_parts[: len(changed_parts)] == changed_parts:
        return True
    return False


def _parse_review_date(value: str) -> dt.date | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        return dt.date.fromisoformat(token)
    except ValueError:
        return None


def _stored_watch_fingerprints(item: Mapping[str, Any]) -> dict[str, str]:
    raw = item.get("reviewed_watch_fingerprints", {})
    if not isinstance(raw, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        token = PurePosixPath(str(key or "").strip()).as_posix()
        fingerprint = str(value or "").strip()
        if token and fingerprint:
            result[token] = fingerprint
    return result


def _max_mtime(path: Path, *, cache: dict[str, float]) -> float:
    key = str(path.resolve())
    if key in cache:
        return cache[key]
    try:
        if path.is_file():
            value = path.stat().st_mtime
        elif path.is_dir():
            value = path.stat().st_mtime
            for child in path.rglob("*"):
                with_child = child.stat().st_mtime
                if with_child > value:
                    value = with_child
        else:
            value = 0.0
    except OSError:
        value = 0.0
    cache[key] = value
    return value


def _current_watch_fingerprints(
    *,
    repo_root: Path,
    watch_paths: Sequence[str],
    cache: diagram_freshness.ContentFingerprintCache,
) -> dict[str, str]:
    return diagram_freshness.watched_path_fingerprints(
        repo_root=repo_root,
        watched_paths=tuple(watch_paths),
        resolve_path=lambda token: _resolve(repo_root, token),
        cache=cache,
    )


def _newest_watch_path(*, repo_root: Path, watch_paths: Sequence[str], cache: dict[str, float]) -> tuple[float, str]:
    newest_mtime = 0.0
    newest_path = ""
    for raw in watch_paths:
        token = str(raw or "").strip()
        if not token:
            continue
        target = _resolve(repo_root, token)
        current_mtime = _max_mtime(target, cache=cache)
        if current_mtime > newest_mtime:
            newest_mtime = current_mtime
            newest_path = token
    return newest_mtime, newest_path


def _git_paths_tracked_and_clean(*, repo_root: Path, paths: Sequence[str]) -> bool:
    normalized = tuple(dict.fromkeys(str(token or "").strip() for token in paths if str(token or "").strip()))
    if not normalized or not (repo_root / ".git").exists():
        return False
    status = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--untracked-files=all", "--", *normalized],
        capture_output=True,
        check=False,
        text=True,
    )
    if status.returncode != 0 or str(status.stdout or "").strip():
        return False
    tracked = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", "--", *normalized],
        capture_output=True,
        check=False,
        text=True,
    )
    return tracked.returncode == 0


def _diagram_needs_render(
    *,
    repo_root: Path,
    item: Mapping[str, Any],
    fingerprint_cache: diagram_freshness.ContentFingerprintCache,
) -> bool:
    source_mmd = str(item.get("source_mmd", "")).strip()
    source_svg = str(item.get("source_svg", "")).strip()
    source_png = str(item.get("source_png", "")).strip()
    if not source_mmd or not source_svg or not source_png:
        return True
    source_mmd_path = _resolve(repo_root, source_mmd)
    source_svg_path = _resolve(repo_root, source_svg)
    source_png_path = _resolve(repo_root, source_png)
    if not source_mmd_path.is_file() or not source_svg_path.is_file() or not source_png_path.is_file():
        return True
    current_render_fingerprint = fingerprint_cache.mermaid_render_fingerprint(source_mmd_path)
    stored_render_fingerprint = str(item.get("render_source_fingerprint", "")).strip()
    if stored_render_fingerprint:
        return stored_render_fingerprint != current_render_fingerprint
    if _git_paths_tracked_and_clean(
        repo_root=repo_root,
        paths=(source_mmd, source_svg, source_png),
    ):
        item["render_source_fingerprint"] = current_render_fingerprint
        return False
    return True


def _classify_diagram_items(
    *,
    repo_root: Path,
    items: Sequence[dict[str, Any]],
    fingerprint_cache: diagram_freshness.ContentFingerprintCache,
) -> AtlasImpactClassification:
    render_jobs: list[dict[str, str]] = []
    impacted_items: list[dict[str, Any]] = []
    render_ids: list[str] = []
    review_only_ids: list[str] = []
    for item in items:
        diagram_id = str(item.get("diagram_id", "")).strip() or "unknown-diagram"
        source_mmd = str(item.get("source_mmd", "")).strip()
        source_svg = str(item.get("source_svg", "")).strip()
        source_png = str(item.get("source_png", "")).strip()
        if not source_mmd or not source_svg or not source_png:
            raise RuntimeError(f"{diagram_id}: missing source paths (mmd/svg/png)")
        source_mmd_path = _resolve(repo_root, source_mmd)
        if not source_mmd_path.is_file():
            raise RuntimeError(f"{diagram_id}: source mmd missing: {source_mmd}")
        impacted_items.append(item)
        if _diagram_needs_render(repo_root=repo_root, item=item, fingerprint_cache=fingerprint_cache):
            render_jobs.append(
                {
                    "diagram_id": diagram_id,
                    "source_mmd": source_mmd,
                    "source_svg": source_svg,
                    "source_png": source_png,
                }
            )
            render_ids.append(diagram_id)
            continue
        review_only_ids.append(diagram_id)
    return AtlasImpactClassification(
        impacted_items=tuple(impacted_items),
        render_jobs=tuple(render_jobs),
        render_ids=tuple(render_ids),
        review_only_ids=tuple(review_only_ids),
    )


def _select_stale_diagram_indexes(
    *,
    repo_root: Path,
    diagrams: Sequence[object],
    max_review_age_days: int,
) -> list[int]:
    today = dt.date.today()
    mtime_cache: dict[str, float] = {}
    content_fingerprint_cache = diagram_freshness.ContentFingerprintCache()
    selected: list[int] = []
    for idx, raw_item in enumerate(diagrams):
        if not isinstance(raw_item, dict):
            continue
        source_mmd = str(raw_item.get("source_mmd", "")).strip()
        review_date = _parse_review_date(str(raw_item.get("last_reviewed_utc", "")).strip())
        watch_paths = [
            PurePosixPath(str(token or "").strip()).as_posix()
            for token in raw_item.get("change_watch_paths", [])
            if str(token or "").strip()
        ]
        if review_date is None:
            selected.append(idx)
            continue
        review_age_days = (today - review_date).days
        stale_for_review_age = review_age_days > max(0, int(max_review_age_days))
        stale_for_watch_change = False
        current_watch_fingerprints = _current_watch_fingerprints(
            repo_root=repo_root,
            watch_paths=watch_paths,
            cache=content_fingerprint_cache,
        )
        stored_watch_fingerprints = _stored_watch_fingerprints(raw_item)
        if stored_watch_fingerprints:
            stale_for_watch_change = any(
                stored_watch_fingerprints.get(path, "") != current_watch_fingerprints.get(path, "")
                for path in watch_paths
            )
        elif source_mmd:
            source_mmd_path = _resolve(repo_root, source_mmd)
            mmd_mtime = _max_mtime(source_mmd_path, cache=mtime_cache)
            newest_watch_mtime, _newest_watch_path_token = _newest_watch_path(
                repo_root=repo_root,
                watch_paths=watch_paths,
                cache=mtime_cache,
            )
            stale_for_watch_change = newest_watch_mtime > (mmd_mtime + 0.0001)
        if stale_for_review_age or stale_for_watch_change:
            selected.append(idx)
    return selected


def _render_diagram(*, repo_root: Path, source_mmd: str, source_svg: str, source_png: str, cli_version: str) -> None:
    for output in (source_svg, source_png):
        cmd = [
            "npx",
            "-y",
            f"@mermaid-js/mermaid-cli@{cli_version}",
            "-i",
            source_mmd,
            "-o",
            output,
        ]
        subprocess.run(cmd, cwd=str(repo_root), check=True)


def _render_job_label(job: Mapping[str, str]) -> str:
    return str(job.get("diagram_id", "")).strip() or str(job.get("source_mmd", "")).strip() or "unknown-diagram"


def _validate_diagrams_batch(
    *,
    repo_root: Path,
    validation_jobs: Sequence[Mapping[str, str]],
    cli_version: str,
) -> None:
    if not validation_jobs:
        return
    print(f"- validate Mermaid syntax ({len(validation_jobs)} diagram(s))")
    try:
        with _MermaidWorkerSession(repo_root=repo_root, cli_version=cli_version) as worker:
            worker.validate_many(jobs=validation_jobs)
        return
    except MermaidDiagramValidationError as exc:
        if "DOMPurify.addHook is not a function" not in str(exc.detail):
            raise
        print(
            "warning: Mermaid syntax preflight hit a Node parser contract drift; "
            "rerunning validation in browser-backed scratch mode"
        )
    except Exception as exc:
        if "DOMPurify.addHook is not a function" not in str(exc):
            raise
        print(
            "warning: Mermaid syntax preflight hit a Node parser contract drift; "
            "rerunning validation in browser-backed scratch mode"
        )
    with tempfile.TemporaryDirectory(prefix="odylith-mermaid-validate-") as scratch_dir_token:
        scratch_dir = Path(scratch_dir_token)
        with _MermaidWorkerSession(repo_root=repo_root, cli_version=cli_version) as worker:
            for index, job in enumerate(validation_jobs, start=1):
                label = _render_job_label(job)
                browser_job = dict(job)
                browser_job["source_svg"] = str(scratch_dir / f"{index:04d}.svg")
                browser_job["source_png"] = str(scratch_dir / f"{index:04d}.png")
                print(f"- validate {label} ({index}/{len(validation_jobs)}) [browser]")
                worker.render_one(job=browser_job, label=f"{label} syntax preflight")


def _render_diagrams_batch(
    *,
    repo_root: Path,
    render_jobs: Sequence[Mapping[str, str]],
    cli_version: str,
) -> None:
    if not render_jobs:
        return
    degraded_jobs: list[Mapping[str, str]] = []
    degraded_start = 1
    try:
        with _MermaidWorkerSession(repo_root=repo_root, cli_version=cli_version) as worker:
            for index, job in enumerate(render_jobs, start=1):
                label = _render_job_label(job)
                print(f"- render {label} ({index}/{len(render_jobs)})")
                worker.render_one(job=job)
        return
    except MermaidDiagramValidationError:
        raise
    except Exception as exc:
        degraded_start = index if "index" in locals() else 1
        degraded_jobs = list(render_jobs[degraded_start - 1 :]) if "index" in locals() else list(render_jobs)
        degraded_labels = [_render_job_label(job) for job in degraded_jobs]
        blocking_label = degraded_labels[0] if degraded_labels else "unknown-diagram"
        print(
            "warning: Mermaid worker unavailable while rendering "
            f"{blocking_label}; falling back to one-shot renders for {', '.join(degraded_labels)} ({exc})"
        )
    fallback_failures: list[str] = []
    for offset, job in enumerate(degraded_jobs, start=degraded_start):
        label = _render_job_label(job)
        print(f"- render {label} ({offset}/{len(render_jobs)}) [one-shot]")
        try:
            _render_diagram(
                repo_root=repo_root,
                source_mmd=str(job.get("source_mmd", "")).strip(),
                source_svg=str(job.get("source_svg", "")).strip(),
                source_png=str(job.get("source_png", "")).strip(),
                cli_version=cli_version,
            )
        except Exception as fallback_exc:
            fallback_failures.append(label)
            print(f"warning: one-shot Mermaid render failed for {label} ({fallback_exc})")
    if degraded_jobs:
        print(
            "Mermaid worker degraded on "
            f"{len(degraded_jobs)} diagram(s): {', '.join(_render_job_label(job) for job in degraded_jobs)}"
        )
    if fallback_failures:
        raise RuntimeError(
            "Mermaid render failed after worker fallback. Blocking diagram ids: "
            + ", ".join(fallback_failures)
        )


def _render_catalog(*, repo_root: Path, fail_on_stale: bool, runtime_mode: str) -> None:
    if str(runtime_mode) != "standalone":
        from odylith.runtime.surfaces import render_mermaid_catalog_refresh

        argv = ["--repo-root", str(repo_root), "--runtime-mode", str(runtime_mode)]
        if fail_on_stale:
            argv.append("--fail-on-stale")
        rc = render_mermaid_catalog_refresh.main(argv)
        if rc != 0:
            raise subprocess.CalledProcessError(
                returncode=rc,
                cmd=[
                    sys.executable,
                    "-m",
                    "odylith.runtime.surfaces.render_mermaid_catalog_refresh",
                    "--repo-root",
                    str(repo_root),
                    "--runtime-mode",
                    str(runtime_mode),
                ],
            )
        return
    cmd = [sys.executable, "-m", "odylith.runtime.surfaces.render_mermaid_catalog_refresh", "--repo-root", "."]
    if fail_on_stale:
        cmd.append("--fail-on-stale")
    cmd.extend(["--runtime-mode", str(runtime_mode)])
    subprocess.run(cmd, cwd=str(repo_root), env=_command_env(), check=True)


def _print_failure_summary(*, elapsed: float, error: Exception) -> None:
    print("atlas auto-update failed")
    print("- outcome: failed")
    print(f"- elapsed_seconds: {elapsed:.1f}")
    print(f"- error: {error}")
    if isinstance(error, MermaidDiagramValidationError):
        if error.line_context:
            print(f"- line_context: {error.line_context}")
        if error.detail:
            print(f"- detail: {error.detail}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    catalog_path = _resolve(repo_root, args.catalog)

    if not catalog_path.is_file():
        print(f"FAILED: catalog missing: {catalog_path}")
        return 2

    changed: list[str] = []
    changed.extend(args.changed_path)
    if args.from_git_head:
        changed.extend(_git_changed_paths(repo_root=repo_root, args=["diff", "--name-only", "HEAD"]))
    if args.from_git_staged:
        changed.extend(_git_changed_paths(repo_root=repo_root, args=["diff", "--name-only", "--cached"]))
    if args.from_git_working_tree:
        changed.extend(_git_changed_paths(repo_root=repo_root, args=["diff", "--name-only"]))

    changed = _normalize_paths(changed)
    if not changed and not bool(args.all_stale):
        print("no changed paths provided; nothing to sync")
        return 0

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    diagrams = payload.get("diagrams")
    if not isinstance(diagrams, list):
        print(f"FAILED: malformed catalog diagrams list: {catalog_path}")
        return 2

    stale_indexes: list[int] = []
    if bool(args.all_stale):
        stale_indexes = _select_stale_diagram_indexes(
            repo_root=repo_root,
            diagrams=diagrams,
            max_review_age_days=max(0, int(args.max_review_age_days)),
        )
    provisional_impacted_indexes = list(stale_indexes)
    for idx, item in enumerate(diagrams):
        if not isinstance(item, dict):
            continue
        watch_paths = [
            PurePosixPath(str(token or "").strip()).as_posix()
            for token in item.get("change_watch_paths", [])
            if str(token or "").strip()
        ]
        if not watch_paths:
            continue
        if any(_touches_watch(changed_path=changed_path, watch_path=watch_path) for changed_path in changed for watch_path in watch_paths):
            provisional_impacted_indexes.append(idx)
    provisional_impacted_indexes = list(dict.fromkeys(provisional_impacted_indexes))
    today = dt.date.today().isoformat()
    provisional_items = [
        dict(diagrams[idx])
        for idx in provisional_impacted_indexes
        if isinstance(diagrams[idx], dict)
    ]
    provisional_classification = _classify_diagram_items(
        repo_root=repo_root,
        items=provisional_items,
        fingerprint_cache=diagram_freshness.ContentFingerprintCache(),
    )
    if provisional_impacted_indexes and not args.dry_run and not (bool(args.all_stale) and bool(stale_indexes)):
        watched_paths = [
            *changed,
            *(
                str(item.get("source_mmd", "")).strip()
                for item in provisional_classification.impacted_items
                if str(item.get("source_mmd", "")).strip()
            ),
            str(_as_repo_path(repo_root, catalog_path)).strip(),
            "src/odylith/runtime/surfaces",
            "src/odylith/runtime/common",
        ]
        output_paths = [
            catalog_path,
            *(
                _resolve(repo_root, str(path).strip())
                for item in provisional_classification.impacted_items
                for path in (
                    str(item.get("source_svg", "")).strip(),
                    str(item.get("source_png", "")).strip(),
                )
                if str(path).strip()
            ),
        ]
        if not args.skip_render_catalog:
            output_paths.extend(
                (
                    _resolve(repo_root, "odylith/atlas/atlas.html"),
                    _resolve(repo_root, "odylith/atlas/mermaid-payload.v1.js"),
                    _resolve(repo_root, "odylith/atlas/mermaid-app.v1.js"),
                )
            )
        skip_rebuild, _input_fingerprint, _cached = generated_refresh_guard.should_skip_rebuild(
            repo_root=repo_root,
            namespace=_ATLAS_AUTO_UPDATE_GUARD_NAMESPACE,
            key=_ATLAS_AUTO_UPDATE_GUARD_KEY,
            watched_paths=tuple(watched_paths),
            output_paths=tuple(output_paths),
            extra={
                "changed_paths": changed,
                "diagram_ids": [str(item.get("diagram_id", "")).strip() for item in provisional_items],
                "all_stale": bool(args.all_stale),
                "skip_render_catalog": bool(args.skip_render_catalog),
                "runtime_mode": str(args.runtime_mode),
            },
        )
        if skip_rebuild:
            if changed:
                print(f"changed paths: {len(changed)}")
            if bool(args.all_stale):
                print(f"stale diagrams selected: {len(stale_indexes)}")
            print(f"impacted diagrams: {len(provisional_impacted_indexes)}")
            plan = _build_execution_plan(
                repo_root=repo_root,
                catalog_repo_path=_as_repo_path(repo_root, catalog_path),
                render_catalog=not bool(args.skip_render_catalog),
                classification=provisional_classification,
            )
            _print_execution_plan(plan, dry_run=False)
            print("atlas auto-update completed")
            print("- outcome: passed")
            print("- elapsed_seconds: 0.0")
            return 0

    impacted_indexes = list(provisional_impacted_indexes)

    if bool(args.all_stale):
        impacted_indexes.extend(stale_indexes)

    impacted_indexes = list(dict.fromkeys(impacted_indexes))

    if not impacted_indexes:
        if bool(args.all_stale):
            print("no stale diagrams found")
        else:
            print("no impacted diagrams from changed paths")
        return 0

    if changed:
        print(f"changed paths: {len(changed)}")
    if bool(args.all_stale):
        print(f"stale diagrams selected: {len(stale_indexes)}")
    print(f"impacted diagrams: {len(impacted_indexes)}")

    impacted_items = [
        dict(diagrams[idx])
        for idx in impacted_indexes
        if isinstance(diagrams[idx], dict)
    ]
    dry_run_classification = _classify_diagram_items(
        repo_root=repo_root,
        items=impacted_items,
        fingerprint_cache=diagram_freshness.ContentFingerprintCache(),
    )
    plan = _build_execution_plan(
        repo_root=repo_root,
        catalog_repo_path=_as_repo_path(repo_root, catalog_path),
        render_catalog=not bool(args.skip_render_catalog),
        classification=dry_run_classification,
    )
    _print_execution_plan(plan, dry_run=bool(args.dry_run))
    if args.dry_run:
        return 0
    watched_paths = [
        *changed,
        *(
            str(item.get("source_mmd", "")).strip()
            for item in dry_run_classification.impacted_items
            if str(item.get("source_mmd", "")).strip()
        ),
        str(_as_repo_path(repo_root, catalog_path)).strip(),
        "src/odylith/runtime/surfaces",
        "src/odylith/runtime/common",
    ]
    content_fingerprint_cache = diagram_freshness.ContentFingerprintCache()
    started_at = time.perf_counter()
    try:
        reviewed_items = [
            diagrams[idx]
            for idx in impacted_indexes
            if isinstance(diagrams[idx], dict)
        ]
        classification = _classify_diagram_items(
            repo_root=repo_root,
            items=reviewed_items,
            fingerprint_cache=content_fingerprint_cache,
        )
        if classification.review_only_ids:
            print(f"review-only diagrams: {len(classification.review_only_ids)}")
        if classification.render_ids:
            print(f"render-needed diagrams: {len(classification.render_ids)}")
        output_paths = [
            catalog_path,
            *(
                _resolve(repo_root, str(path).strip())
                for item in classification.impacted_items
                for path in (
                    str(item.get("source_svg", "")).strip(),
                    str(item.get("source_png", "")).strip(),
                )
                if str(path).strip()
            ),
        ]
        if not args.skip_render_catalog:
            output_paths.extend(
                (
                    _resolve(repo_root, "odylith/atlas/atlas.html"),
                    _resolve(repo_root, "odylith/atlas/mermaid-payload.v1.js"),
                    _resolve(repo_root, "odylith/atlas/mermaid-app.v1.js"),
                )
            )
        for item in classification.impacted_items:
            diagram_id = str(item.get("diagram_id", "")).strip() or "unknown-diagram"
            source_mmd = str(item.get("source_mmd", "")).strip()
            print(f"- sync {diagram_id}: {source_mmd}")
        if classification.render_jobs:
            _render_diagrams_batch(
                repo_root=repo_root,
                render_jobs=classification.render_jobs,
                cli_version=args.mermaid_cli_version,
            )
        for item in classification.impacted_items:
            source_mmd_path = _resolve(repo_root, str(item.get("source_mmd", "")).strip())
            watch_paths = [
                PurePosixPath(str(token or "").strip()).as_posix()
                for token in item.get("change_watch_paths", [])
                if str(token or "").strip()
            ]
            item["reviewed_watch_fingerprints"] = _current_watch_fingerprints(
                repo_root=repo_root,
                watch_paths=watch_paths,
                cache=content_fingerprint_cache,
            )
            item["render_source_fingerprint"] = content_fingerprint_cache.mermaid_render_fingerprint(source_mmd_path)
            item["last_reviewed_utc"] = today

        catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
        print(f"catalog updated: {_as_repo_path(repo_root, catalog_path)}")

        if not args.skip_render_catalog:
            _render_catalog(
                repo_root=repo_root,
                fail_on_stale=args.fail_on_stale,
                runtime_mode=str(args.runtime_mode),
            )
        final_fingerprint = generated_refresh_guard.compute_input_fingerprint(
            repo_root=repo_root,
            watched_paths=tuple(watched_paths),
            extra={
                "changed_paths": changed,
                "diagram_ids": [str(item.get("diagram_id", "")).strip() for item in classification.impacted_items],
                "all_stale": bool(args.all_stale),
                "skip_render_catalog": bool(args.skip_render_catalog),
                "runtime_mode": str(args.runtime_mode),
            },
        )
        generated_refresh_guard.record_rebuild(
            repo_root=repo_root,
            namespace=_ATLAS_AUTO_UPDATE_GUARD_NAMESPACE,
            key=_ATLAS_AUTO_UPDATE_GUARD_KEY,
            input_fingerprint=final_fingerprint,
            output_paths=tuple(output_paths),
            metadata={
                "impacted_count": len(classification.impacted_items),
                "changed_count": len(changed),
            },
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        _print_failure_summary(elapsed=elapsed, error=exc)
        return 1

    elapsed = time.perf_counter() - started_at
    print("atlas auto-update completed")
    print("- outcome: passed")
    print(f"- elapsed_seconds: {elapsed:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

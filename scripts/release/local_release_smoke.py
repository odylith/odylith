"""Exercise a local hosted-release install flow against a temporary repo."""

from __future__ import annotations

import argparse
import errno
import gzip
import http.server
import json
import os
from pathlib import Path
import shutil
import socketserver
import subprocess
import tempfile
import threading
import time
from urllib import error as urllib_error

from odylith.install.release_assets import fetch_release
from odylith.install.state import AUTHORITATIVE_RELEASE_REPO

REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMP_ROOT_CLEANUP_RETRY_COUNT = 5
_TEMP_ROOT_CLEANUP_RETRY_DELAY_SECONDS = 0.2
_TEMP_ROOT_CLEANUP_RETRYABLE_ERRNOS = {errno.EACCES, errno.EBUSY, errno.ENOTEMPTY, errno.EPERM}
_COMMAND_TIMEOUT_SECONDS = 300


def _run(*, cwd: Path, env: dict[str, str], command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        raise RuntimeError(
            "\n".join(
                [
                    f"command timed out after {_COMMAND_TIMEOUT_SECONDS}s: {' '.join(command)}",
                    f"cwd: {cwd}",
                    stdout.strip(),
                    stderr.strip(),
                ]
            ).strip()
        ) from exc
    if completed.returncode != 0:
        raise RuntimeError(
            "\n".join(
                [
                    f"command failed: {' '.join(command)}",
                    f"cwd: {cwd}",
                    completed.stdout.strip(),
                    completed.stderr.strip(),
                ]
            ).strip()
        )
    return completed


def _repo_root(base_dir: Path, name: str) -> Path:
    repo_root = base_dir / name
    repo_root.mkdir(parents=True, exist_ok=True)
    _write_release_smoke_agents(repo_root=repo_root)
    return repo_root


def _write_release_smoke_agents(*, repo_root: Path) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo Root\n\nLocal release smoke repo.\n", encoding="utf-8")


def _semver_previous(version: str) -> str:
    major, minor, patch = (int(token) for token in version.split(".", 2))
    if patch == 0:
        return ""
    return f"{major}.{minor}.{patch - 1}"


def _previous_release_is_published(*, version: str) -> bool:
    try:
        fetch_release(repo_root=REPO_ROOT, repo=AUTHORITATIVE_RELEASE_REPO, version=version)
    except urllib_error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise
    except ValueError as exc:
        if "HTTP Error 404" in str(exc):
            return False
        raise
    return True


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        del format, args


def _serve_directory(directory: Path) -> tuple[socketserver.TCPServer, str]:
    handler = lambda *args, **kwargs: _QuietHandler(*args, directory=str(directory), **kwargs)  # noqa: E731
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def _cleanup_smoke_temp_root(path: Path) -> None:
    target = Path(path)
    last_error: OSError | None = None
    for attempt in range(_TEMP_ROOT_CLEANUP_RETRY_COUNT + 1):
        try:
            shutil.rmtree(target)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            if exc.errno not in _TEMP_ROOT_CLEANUP_RETRYABLE_ERRNOS:
                break
            if attempt >= _TEMP_ROOT_CLEANUP_RETRY_COUNT:
                break
            time.sleep(_TEMP_ROOT_CLEANUP_RETRY_DELAY_SECONDS)
    if last_error is not None:
        shutil.rmtree(target, ignore_errors=True)


def _local_release_env(*, base_url: str, version: str) -> dict[str, str]:
    env = dict(os.environ)
    env["ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST"] = "1"
    env["ODYLITH_RELEASE_BASE_URL"] = base_url
    env["ODYLITH_RELEASE_MAINTAINER_ROOT"] = str(REPO_ROOT)
    env["ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY"] = "1"
    env = _force_deterministic_reasoning_env(env)
    env["ODYLITH_VERSION"] = version
    return env


def _force_deterministic_reasoning_env(env: dict[str, str]) -> dict[str, str]:
    # Release smoke must stay deterministic even on maintainer machines that
    # have a local reasoning provider available or exported in the shell.
    env["ODYLITH_REASONING_MODE"] = "disabled"
    env["ODYLITH_REASONING_PROVIDER"] = "auto-local"
    env["ODYLITH_REASONING_TIMEOUT_SECONDS"] = "1"
    env["ODYLITH_REASONING_CODEX_BIN"] = "/usr/bin/false"
    env["ODYLITH_REASONING_CLAUDE_BIN"] = "/usr/bin/false"
    env["ODYLITH_COMPASS_STANDUP_BACKGROUND_DISABLE"] = "1"
    env["ODYLITH_NO_BROWSER"] = "1"
    return env


def _install_cwd(repo_root: Path) -> Path:
    nested = repo_root / "workspace" / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    return nested


def _require_output_contains(*, output: str, expected: str, label: str) -> None:
    if expected not in output:
        raise RuntimeError(f"{label} missing expected text: {expected!r}")


_GREENFIELD_SCHEMA_LOOP_TOKENS = (
    "must be non-empty",
    "greenfield proposal validation failed",
    "greenfield proposal Tribunal failed",
    "host-side schema repair",
)
_GREENFIELD_GUIDANCE_FILES = (
    "AGENTS.md",
    "odylith/AGENTS.md",
    "odylith/skills/odylith-greenfield-governance/SKILL.md",
    "odylith/skills/odylith-show-me/SKILL.md",
)
_STALE_GREENFIELD_GUIDANCE_TOKENS = (
    "host drafts backlog",
    "host model drafts",
    "active host model authors the project-specific proposal in chat",
    "greenfield apply --repo-root . --proposal-file <proposal.json>",
)
_GREENFIELD_MANUAL_JSON_GUARDS = (
    "host authors",
    "host-authored proposal JSON",
    "proposal JSON from the confirmed intent",
    "proposal JSON from the confirmed product shape",
)
_GREENFIELD_PROJECT_FIRST_GUARDS = (
    "project-first",
    "product story",
    "coding-readiness gates",
    "direction options",
)
_GREENFIELD_NO_SOURCE_SPELUNKING_GUARDS = (
    "Do not inspect Odylith source",
    "do not inspect Odylith source",
    "Do not search `src/odylith`",
    "do not search Odylith source",
    "rather than searching Odylith source",
)


def _require_no_greenfield_schema_loop(*, output: str, label: str) -> None:
    for token in _GREENFIELD_SCHEMA_LOOP_TOKENS:
        if token in output:
            raise RuntimeError(f"{label} exposed a schema repair loop: {token}")


def _require_greenfield_surfaces(*, repo_root: Path, label: str) -> None:
    for relative_path in (
        "odylith/radar/radar.html",
        "odylith/registry/registry.html",
        "odylith/atlas/atlas.html",
        "odylith/compass/compass.html",
    ):
        if not (repo_root / relative_path).is_file():
            raise RuntimeError(f"{label} did not render {relative_path}")


def _require_greenfield_guidance_uses_host_apply(*, repo_root: Path, label: str) -> None:
    for relative_path in _GREENFIELD_GUIDANCE_FILES:
        path = repo_root / relative_path
        if not path.is_file():
            raise RuntimeError(f"{label} did not install greenfield guidance file: {relative_path}")
        text = path.read_text(encoding="utf-8")
        compact_text = " ".join(text.split())
        if "greenfield apply" not in text:
            raise RuntimeError(f"{label} guidance omits host-authored greenfield apply path: {relative_path}")
        if "Product Intent Confirmation" not in text:
            raise RuntimeError(f"{label} guidance omits live Product Intent confirmation path: {relative_path}")
        if not any(token in compact_text for token in _GREENFIELD_MANUAL_JSON_GUARDS):
            raise RuntimeError(f"{label} guidance omits manual proposal JSON guard: {relative_path}")
        if not any(token in compact_text for token in _GREENFIELD_PROJECT_FIRST_GUARDS):
            raise RuntimeError(f"{label} guidance omits project-first greenfield guard: {relative_path}")
        if not any(token in text for token in _GREENFIELD_NO_SOURCE_SPELUNKING_GUARDS):
            raise RuntimeError(f"{label} guidance omits post-confirmation no-source-spelunking guard: {relative_path}")
        for token in _STALE_GREENFIELD_GUIDANCE_TOKENS:
            if token in text:
                raise RuntimeError(f"{label} guidance still teaches stale greenfield schema-repair flow: {relative_path}: {token}")


def _seed_legacy_compass_archive_fixture(*, repo_root: Path) -> None:
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    history_dir = runtime_dir / "history"
    archive_dir = history_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stale_active_day = "2020-01-01"
    archived_day = "2020-01-02"
    payload = {
        "version": "v1",
        "generated_utc": "2026-04-14T20:20:00Z",
        "history": {
            "retention_days": 15,
            "dates": [stale_active_day],
            "restored_dates": [],
            "archive": {
                "compressed": True,
                "path": "archive",
                "count": 1,
                "dates": [archived_day],
                "newest_date": archived_day,
                "oldest_date": archived_day,
            },
        },
    }
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (runtime_dir / "current.v1.js").write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (history_dir / f"{stale_active_day}.v1.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (archive_dir / f"{archived_day}.v1.json.gz").write_bytes(
        gzip.compress((json.dumps(payload, indent=2) + "\n").encode("utf-8"), compresslevel=9)
    )
    (history_dir / "restore-pins.v1.json").write_text(
        json.dumps({"version": "v1", "generated_utc": "2026-04-14T20:20:00Z", "dates": [archived_day]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (history_dir / "index.v1.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-14T20:20:00Z",
                "retention_days": 15,
                "dates": [stale_active_day],
                "restored_dates": [],
                "archive": payload["history"]["archive"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (history_dir / "embedded.v1.js").write_text(
        "window.__ODYLITH_COMPASS_HISTORY__ = "
        + json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-14T20:20:00Z",
                "retention_days": 15,
                "dates": [stale_active_day],
                "restored_dates": [],
                "archive": payload["history"]["archive"],
                "snapshots": {archived_day: payload},
            },
            separators=(",", ":"),
        )
        + ";\n",
        encoding="utf-8",
    )


def _require_compass_history_layout(*, repo_root: Path) -> None:
    history_dir = repo_root / "odylith" / "compass" / "runtime" / "history"
    index_path = history_dir / "index.v1.json"
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if int(payload.get("retention_days") or 0) != 15:
        raise RuntimeError("Compass history retention_days must stay at 15")
    archive = payload.get("archive")
    if not isinstance(archive, dict) or int(archive.get("count") or 0) != 0:
        raise RuntimeError("Compass history archive metadata was not cleared")
    if archive.get("dates") not in ([], None):
        raise RuntimeError("Compass history archive dates were not cleared")
    if (history_dir / "archive").exists():
        raise RuntimeError("legacy Compass history archive directory still exists")
    if (history_dir / "restore-pins.v1.json").exists():
        raise RuntimeError("legacy Compass restore pins still exist")


def _install_and_smoke(*, repo_root: Path, install_script: Path, env: dict[str, str]) -> None:
    _run(cwd=_install_cwd(repo_root), env=env, command=["bash", str(install_script)])
    _require_greenfield_guidance_uses_host_apply(repo_root=repo_root, label="fresh install")
    odylith = repo_root / ".odylith" / "bin" / "odylith"
    version = _run(cwd=repo_root, env=env, command=[str(odylith), "version", "--repo-root", "."]).stdout
    _require_output_contains(output=version, expected=f"Active: {env['ODYLITH_VERSION']}", label="odylith version")
    _require_output_contains(output=version, expected="Context engine pack: installed", label="odylith version")
    doctor = _run(cwd=repo_root, env=env, command=[str(odylith), "doctor", "--repo-root", "."]).stdout
    _require_output_contains(output=doctor, expected="Context engine mode: full_local_memory", label="odylith doctor")
    _require_output_contains(output=doctor, expected="Context engine pack: installed", label="odylith doctor")
    _greenfield_propose_apply_smoke(repo_root=repo_root, odylith=odylith, env=env)
    _run(cwd=repo_root, env=env, command=[str(odylith), "sync", "--repo-root", ".", "--force"])


def _greenfield_propose_apply_smoke(*, repo_root: Path, odylith: Path, env: dict[str, str]) -> None:
    show = _run(cwd=repo_root, env=env, command=[str(odylith), "show", "--repo-root", "."]).stdout
    _require_output_contains(output=show, expected="Odylith read this repo", label="odylith show")
    intent = _run(
        cwd=repo_root,
        env=env,
        command=[
            str(odylith),
            "greenfield",
            "propose",
            "--repo-root",
            ".",
            "--prompt",
            "robot swarm logistics app",
            "--format",
            "json",
        ],
    ).stdout
    _require_output_contains(
        output=intent,
        expected='"mode": "product_intent_reasoning_request"',
        label="greenfield intent json",
    )
    _require_output_contains(
        output=intent,
        expected='"write_policy": "host_reason_product_intent_before_greenfield_proposal"',
        label="greenfield intent json",
    )
    _require_output_contains(output=intent, expected='"host_reasoning_task"', label="greenfield intent json")
    _require_output_contains(output=intent, expected='"must_not"', label="greenfield intent json")

    proposal = _run(
        cwd=repo_root,
        env=env,
        command=[
            str(odylith),
            "greenfield",
            "propose",
            "--repo-root",
            ".",
            "--prompt",
            "robot swarm logistics app",
            "--confirm-intent",
            "--format",
            "json",
        ],
    ).stdout
    _require_output_contains(
        output=proposal,
        expected='"mode": "host_reasoned_proposal_request"',
        label="greenfield propose json",
    )
    _require_output_contains(output=proposal, expected='"reasoning_contract"', label="greenfield propose json")
    _require_output_contains(output=proposal, expected='"host_instruction"', label="greenfield propose json")
    if any(token in proposal for token in ('"backlog": [', '"components": [', '"diagrams": [')):
        raise RuntimeError("greenfield propose contract generated governance artifacts before host-authored proposal")
    _require_no_greenfield_schema_loop(output=proposal, label="greenfield propose json")
    refresh = _run(cwd=repo_root, env=env, command=[str(odylith), "dashboard", "refresh", "--repo-root", "."]).stdout
    _require_output_contains(output=refresh, expected="dashboard refresh completed", label="greenfield dashboard refresh")
    _require_output_contains(output=refresh, expected="outcome: passed", label="greenfield dashboard refresh")
    _require_greenfield_surfaces(repo_root=repo_root, label="greenfield propose contract smoke")


def _install_previous_release(*, repo_root: Path, install_script: Path, previous_version: str) -> None:
    hosted_previous_env = _force_deterministic_reasoning_env(dict(os.environ))
    hosted_previous_env["ODYLITH_VERSION"] = previous_version
    _run(cwd=_install_cwd(repo_root), env=hosted_previous_env, command=["bash", str(install_script)])


def _install_clean_previous_release(*, repo_root: Path, install_script: Path, previous_version: str) -> None:
    for relative_path in (".odylith", "odylith", ".agents", ".claude"):
        shutil.rmtree(repo_root / relative_path, ignore_errors=True)
    _write_release_smoke_agents(repo_root=repo_root)
    _install_previous_release(
        repo_root=repo_root,
        install_script=install_script,
        previous_version=previous_version,
    )


def _dist_manifest_requires_migration(*, install_script: Path) -> bool:
    manifest_path = install_script.parent / "release-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(manifest.get("migration_required"))


def _run_upgrade_rehearsal(
    *,
    repo_root: Path,
    install_script: Path,
    target_version: str,
    local_env: dict[str, str],
) -> None:
    odylith = repo_root / ".odylith" / "bin" / "odylith"
    if _dist_manifest_requires_migration(install_script=install_script):
        _run(cwd=_install_cwd(repo_root), env=local_env, command=["bash", str(install_script)])
        return
    _run(
        cwd=repo_root,
        env=local_env,
        command=[str(odylith), "upgrade", "--repo-root", ".", "--to", target_version, "--write-pin"],
    )


def _upgrade_cycle(
    *,
    repo_root: Path,
    install_script: Path,
    previous_version: str,
    target_version: str,
    local_env: dict[str, str],
) -> None:
    _install_clean_previous_release(
        repo_root=repo_root,
        install_script=install_script,
        previous_version=previous_version,
    )
    _seed_legacy_compass_archive_fixture(repo_root=repo_root)
    _run_upgrade_rehearsal(
        repo_root=repo_root,
        install_script=install_script,
        target_version=target_version,
        local_env=local_env,
    )
    odylith = repo_root / ".odylith" / "bin" / "odylith"
    _run(cwd=repo_root, env=local_env, command=[str(odylith), "dashboard", "refresh", "--repo-root", "."])
    _require_compass_history_layout(repo_root=repo_root)
    _install_clean_previous_release(
        repo_root=repo_root,
        install_script=install_script,
        previous_version=previous_version,
    )
    _seed_legacy_compass_archive_fixture(repo_root=repo_root)
    _run(cwd=_install_cwd(repo_root), env=local_env, command=["bash", str(install_script)])
    _run(cwd=repo_root, env=local_env, command=[str(odylith), "dashboard", "refresh", "--repo-root", "."])
    _require_compass_history_layout(repo_root=repo_root)
    _install_clean_previous_release(
        repo_root=repo_root,
        install_script=install_script,
        previous_version=previous_version,
    )
    _seed_legacy_compass_archive_fixture(repo_root=repo_root)
    _run_upgrade_rehearsal(
        repo_root=repo_root,
        install_script=install_script,
        target_version=target_version,
        local_env=local_env,
    )
    odylith = repo_root / ".odylith" / "bin" / "odylith"
    _run(cwd=repo_root, env=local_env, command=[str(odylith), "dashboard", "refresh", "--repo-root", "."])
    _require_compass_history_layout(repo_root=repo_root)


def _stale_uninstall_residue_cycle(
    *,
    repo_root: Path,
    install_script: Path,
    previous_version: str,
    target_version: str,
    local_env: dict[str, str],
) -> None:
    _install_clean_previous_release(
        repo_root=repo_root,
        install_script=install_script,
        previous_version=previous_version,
    )
    shutil.rmtree(repo_root / "odylith", ignore_errors=True)
    migration_dir = repo_root / ".odylith" / "state" / "migrations"
    migration_dir.mkdir(parents=True, exist_ok=True)
    (migration_dir / "v0.1.11-visible-intervention-value-engine.v1.json").write_text(
        json.dumps(
            {
                "schema_version": "odylith-value-engine-migration.v1",
                "migration_id": "v0.1.11-visible-intervention-value-engine",
                "applied": True,
                "previous_version": previous_version,
                "target_version": target_version,
                "written_paths": ["odylith/runtime/source/intervention-value-adjudication-corpus.v1.json"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _run(cwd=_install_cwd(repo_root), env=local_env, command=["bash", str(install_script)])
    odylith = repo_root / ".odylith" / "bin" / "odylith"
    version = _run(cwd=repo_root, env=local_env, command=[str(odylith), "version", "--repo-root", "."]).stdout
    _require_output_contains(output=version, expected=f"Active: {target_version}", label="stale residue version")
    if not (repo_root / "odylith" / "AGENTS.md").is_file():
        raise RuntimeError("stale uninstall residue install did not restore odylith/ governed source truth")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local Odylith release smoke tests against generated assets.")
    parser.add_argument("--version", required=True, help="Release version, for example 0.1.0.")
    parser.add_argument("--dist-dir", default="dist", help="Directory containing generated release assets.")
    parser.add_argument(
        "--previous-version",
        action="append",
        default=[],
        help=(
            "Published previous version to rehearse into the local target. "
            "May be repeated; defaults to the immediate semver predecessor."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dist_dir = Path(args.dist_dir).expanduser().resolve()
    install_script = dist_dir / "install.sh"
    if not install_script.is_file():
        raise ValueError(f"install script missing: {install_script}")

    server, base_url = _serve_directory(dist_dir)
    temp_root = Path(tempfile.mkdtemp(prefix="odylith-release-smoke-")).resolve()
    try:
        local_env = _local_release_env(base_url=base_url, version=args.version)
        fresh_repo = _repo_root(temp_root, "fresh-install")
        _install_and_smoke(repo_root=fresh_repo, install_script=install_script, env=local_env)
        # Prompt-only create is intentionally disabled; the install smoke covers
        # the no-write intent and proposal-contract path.

        previous_versions = tuple(str(version).strip() for version in args.previous_version if str(version).strip())
        if not previous_versions:
            immediate_previous = _semver_previous(args.version)
            previous_versions = (immediate_previous,) if immediate_previous else ()
        for previous_version in previous_versions:
            if previous_version and _previous_release_is_published(version=previous_version):
                suffix = previous_version.replace(".", "-")
                lifecycle_repo = _repo_root(temp_root, f"upgrade-cycle-{suffix}")
                _upgrade_cycle(
                    repo_root=lifecycle_repo,
                    install_script=install_script,
                    previous_version=previous_version,
                    target_version=args.version,
                    local_env=local_env,
                )
                stale_residue_repo = _repo_root(temp_root, f"stale-uninstall-residue-{suffix}")
                _stale_uninstall_residue_cycle(
                    repo_root=stale_residue_repo,
                    install_script=install_script,
                    previous_version=previous_version,
                    target_version=args.version,
                    local_env=local_env,
                )
    finally:
        server.shutdown()
        server.server_close()
        _cleanup_smoke_temp_root(temp_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

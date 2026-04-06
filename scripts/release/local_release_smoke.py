from __future__ import annotations

import argparse
import http.server
import os
from pathlib import Path
import socketserver
import subprocess
import tempfile
import threading
from urllib import error as urllib_error

from odylith.install.release_assets import fetch_release
from odylith.install.state import AUTHORITATIVE_RELEASE_REPO

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(*, cwd: Path, env: dict[str, str], command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
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
    (repo_root / "AGENTS.md").write_text("# Repo Root\n\nLocal release smoke repo.\n", encoding="utf-8")
    return repo_root


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


def _local_release_env(*, base_url: str, version: str) -> dict[str, str]:
    env = dict(os.environ)
    env["ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST"] = "1"
    env["ODYLITH_RELEASE_BASE_URL"] = base_url
    env["ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY"] = "1"
    env = _force_deterministic_reasoning_env(env)
    env["ODYLITH_VERSION"] = version
    return env


def _force_deterministic_reasoning_env(env: dict[str, str]) -> dict[str, str]:
    # Release smoke must stay deterministic even on maintainer machines that
    # have a local reasoning provider available or exported in the shell.
    env["ODYLITH_REASONING_MODE"] = "disabled"
    env["ODYLITH_REASONING_PROVIDER"] = "auto-local"
    return env


def _install_cwd(repo_root: Path) -> Path:
    nested = repo_root / "workspace" / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    return nested


def _require_output_contains(*, output: str, expected: str, label: str) -> None:
    if expected not in output:
        raise RuntimeError(f"{label} missing expected text: {expected!r}")


def _install_and_smoke(*, repo_root: Path, install_script: Path, env: dict[str, str]) -> None:
    _run(cwd=_install_cwd(repo_root), env=env, command=["bash", str(install_script)])
    odylith = repo_root / ".odylith" / "bin" / "odylith"
    version = _run(cwd=repo_root, env=env, command=[str(odylith), "version", "--repo-root", "."]).stdout
    _require_output_contains(output=version, expected=f"Active: {env['ODYLITH_VERSION']}", label="odylith version")
    _require_output_contains(output=version, expected="Context engine pack: installed", label="odylith version")
    doctor = _run(cwd=repo_root, env=env, command=[str(odylith), "doctor", "--repo-root", "."]).stdout
    _require_output_contains(output=doctor, expected="Context engine mode: full_local_memory", label="odylith doctor")
    _require_output_contains(output=doctor, expected="Context engine pack: installed", label="odylith doctor")
    _run(cwd=repo_root, env=env, command=[str(odylith), "sync", "--repo-root", ".", "--force"])


def _upgrade_cycle(
    *,
    repo_root: Path,
    install_script: Path,
    previous_version: str,
    target_version: str,
    local_env: dict[str, str],
) -> None:
    hosted_previous_env = _force_deterministic_reasoning_env(dict(os.environ))
    hosted_previous_env["ODYLITH_VERSION"] = previous_version
    _run(cwd=_install_cwd(repo_root), env=hosted_previous_env, command=["bash", str(install_script)])
    odylith = repo_root / ".odylith" / "bin" / "odylith"
    _run(
        cwd=repo_root,
        env=local_env,
        command=[str(odylith), "upgrade", "--repo-root", ".", "--to", target_version, "--write-pin"],
    )
    _run(cwd=repo_root, env=local_env, command=[str(odylith), "rollback", "--repo-root", ".", "--previous"])
    _run(
        cwd=repo_root,
        env=local_env,
        command=[str(odylith), "upgrade", "--repo-root", ".", "--to", target_version, "--write-pin"],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local Odylith release smoke tests against generated assets.")
    parser.add_argument("--version", required=True, help="Release version, for example 0.1.0.")
    parser.add_argument("--dist-dir", default="dist", help="Directory containing generated release assets.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dist_dir = Path(args.dist_dir).expanduser().resolve()
    install_script = dist_dir / "install.sh"
    if not install_script.is_file():
        raise ValueError(f"install script missing: {install_script}")

    server, base_url = _serve_directory(dist_dir)
    try:
        local_env = _local_release_env(base_url=base_url, version=args.version)
        with tempfile.TemporaryDirectory(prefix="odylith-release-smoke-") as tmpdir:
            temp_root = Path(tmpdir)
            fresh_repo = _repo_root(temp_root, "fresh-install")
            _install_and_smoke(repo_root=fresh_repo, install_script=install_script, env=local_env)

            previous_version = _semver_previous(args.version)
            if previous_version and _previous_release_is_published(version=previous_version):
                lifecycle_repo = _repo_root(temp_root, "upgrade-cycle")
                _upgrade_cycle(
                    repo_root=lifecycle_repo,
                    install_script=install_script,
                    previous_version=previous_version,
                    target_version=args.version,
                    local_env=local_env,
                )
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the exact installed Greenfield matrix preamble as a bounded diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any
import uuid


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from greenfield_preconfirm_matrix import COMMAND_TIMEOUT_SECONDS
from greenfield_preconfirm_matrix import _cleanup_smoke_temp_root
from greenfield_preconfirm_matrix import _local_release_env
from greenfield_preconfirm_matrix import _run
from greenfield_preconfirm_matrix import _serve_directory


_SENSITIVE_ENVIRONMENT_FRAGMENTS = ("AUTH", "CREDENTIAL", "KEY", "PASSWORD", "SECRET", "TOKEN")


def run_probe(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    output_json: Path | None = None,
    install_timeout_seconds: float = COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Execute one server, `git init`, and the matrix's helper-wrapped installer."""

    timeout_seconds = _finite_timeout(install_timeout_seconds)
    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    artifact_sha256 = _directory_sha256(release_dir)
    root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-exact-preamble-{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=False)
    server = None
    payload: dict[str, Any] | None = None
    try:
        repo_root = root / "matrix-first-case"
        repo_root.mkdir()
        server, base_url = _serve_directory(release_dir)
        environment = _local_release_env(base_url=base_url, version=version)
        payload = {
            "version": "greenfield-exact-matrix-preamble-probe-v1",
            "scope": "one_server_git_init_group_timeout_install",
            "status": "running",
            "artifact_sha256": artifact_sha256,
            "environment_sha256": _environment_sha256(environment),
            "release_environment": _release_environment(environment),
            "server_base_url": base_url,
            "install_timeout_seconds": timeout_seconds,
            "git_init": _started_command_observation(["git", "init"]),
            "install": _started_command_observation(["bash", str(install_script)], status="pending"),
        }
        _persist_payload(output_json, payload)
        git_started = time.monotonic()
        git_init = _run(
            cwd=repo_root,
            env=environment,
            command=["git", "init"],
            timeout=60,
            on_started=_command_start_recorder(payload, "git_init", output_json),
        )
        payload["git_init"] = _command_observation(
            command=["git", "init"],
            result=git_init,
            elapsed_seconds=time.monotonic() - git_started,
            started=payload["git_init"],
        )
        _persist_payload(output_json, payload)
        install_started = time.monotonic()
        install = _run(
            cwd=repo_root,
            env=environment,
            command=["bash", str(install_script)],
            timeout=timeout_seconds,
            on_started=_command_start_recorder(payload, "install", output_json),
        )
        payload["install"] = _command_observation(
            command=["bash", str(install_script)],
            result=install,
            elapsed_seconds=time.monotonic() - install_started,
            started=payload["install"],
        )
        payload["status"] = "passed" if git_init.returncode == 0 and install.returncode == 0 else "failed"
    except Exception as exc:
        if payload is None:
            payload = {
                "version": "greenfield-exact-matrix-preamble-probe-v1",
                "scope": "one_server_git_init_group_timeout_install",
                "artifact_sha256": artifact_sha256,
            }
        payload["status"] = "harness_error"
        payload["harness_error"] = f"{type(exc).__name__}: {exc}"[:800]
    finally:
        cleanup_errors = _cleanup_server(server)
        _cleanup_smoke_temp_root(root)
        if root.exists():
            cleanup_errors.append(f"temporary root was not removed: {root}")
        if payload is not None:
            if cleanup_errors:
                payload["cleanup_errors"] = cleanup_errors
                if payload["status"] == "passed":
                    payload["status"] = "harness_error"
            _persist_payload(output_json, payload)
    return payload


def _command_observation(
    *,
    command: list[str],
    result: Any,
    elapsed_seconds: float | None,
    started: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stdout = _as_bytes(getattr(result, "stdout", ""))
    stderr = _as_bytes(getattr(result, "stderr", ""))
    process_identity = {
        key: started[key]
        for key in ("pid", "pgid")
        if started is not None and key in started
    }
    observation = {
        **process_identity,
        "status": "completed",
        "argv": command,
        "returncode": int(getattr(result, "returncode", 1)),
        "elapsed_seconds": round(float(elapsed_seconds or 0.0), 3),
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
    }
    termination_observation = getattr(result, "termination_observation", None)
    if termination_observation is not None:
        observation["termination_observation"] = str(termination_observation)
    return observation


def _started_command_observation(command: list[str], *, status: str = "running") -> dict[str, Any]:
    return {"status": status, "argv": command}


def _command_start_recorder(
    payload: dict[str, Any],
    key: str,
    output_json: Path | None,
) -> Any:
    def record(pid: int, pgid: int) -> None:
        payload[key].update({"pid": pid, "pgid": pgid, "status": "running"})
        _persist_payload(output_json, payload)

    return record


def _cleanup_server(server: Any) -> list[str]:
    if server is None:
        return []
    errors: list[str] = []
    try:
        server.shutdown()
    except Exception as exc:
        errors.append(f"server shutdown failed: {type(exc).__name__}: {exc}"[:800])
    try:
        server.server_close()
    except Exception as exc:
        errors.append(f"server close failed: {type(exc).__name__}: {exc}"[:800])
    return errors


def _directory_sha256(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in directory.rglob("*") if candidate.is_file()):
        digest.update(str(path.relative_to(directory)).encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _environment_sha256(environment: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for key, value in sorted(environment.items()):
        if any(fragment in key.upper() for fragment in _SENSITIVE_ENVIRONMENT_FRAGMENTS):
            continue
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _release_environment(environment: dict[str, str]) -> dict[str, str]:
    keys = (
        "ODYLITH_RELEASE_BASE_URL",
        "ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST",
        "ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY",
        "ODYLITH_RELEASE_MAINTAINER_ROOT",
        "ODYLITH_VERSION",
    )
    return {key: str(environment.get(key, "")) for key in keys}


def _as_bytes(value: str | bytes | None) -> bytes:
    return value if isinstance(value, bytes) else str(value or "").encode("utf-8")


def _finite_timeout(value: float) -> float:
    timeout = float(value)
    if not math.isfinite(timeout) or timeout < 1.0:
        raise ValueError("install timeout must be a finite number of at least one second")
    return timeout


def _finite_timeout_argument(value: str) -> float:
    try:
        return _finite_timeout(float(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _persist_payload(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the exact Greenfield matrix install preamble diagnostic.")
    parser.add_argument("--dist-dir", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--temp-parent", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--install-timeout-seconds", type=_finite_timeout_argument, default=COMMAND_TIMEOUT_SECONDS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = run_probe(
        dist_dir=Path(args.dist_dir),
        version=str(args.version),
        temp_parent=Path(args.temp_parent),
        output_json=Path(args.output_json),
        install_timeout_seconds=float(args.install_timeout_seconds),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

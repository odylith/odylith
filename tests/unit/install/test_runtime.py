from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

from odylith.install import runtime, runtime_integrity
from odylith.install.managed_runtime import (
    MANAGED_RUNTIME_SCHEMA_VERSION,
    MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
    MANAGED_PYTHON_VERSION,
    managed_runtime_platform_by_slug,
    supported_managed_runtime_platforms,
)


def _repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return repo_root


def _make_runtime(repo_root: Path) -> Path:
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    python = version_root / "bin" / "python"
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    python.chmod(0o755)
    (version_root / "pyvenv.cfg").write_text("version = 3.13.12\n", encoding="utf-8")
    return version_root


def _seed_managed_runtime(
    version_root: Path,
    *,
    version: str = "1.2.3",
    platform_slug: str = "darwin-arm64",
    wheel_name: str = "odylith-1.2.3-py3-none-any.whl",
    verification: dict[str, object] | None = None,
) -> None:
    bin_dir = version_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name in ("python", "python3", "odylith"):
        executable = bin_dir / name
        executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
    (version_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
                "version": version,
                "platform": platform_slug,
                "python_version": MANAGED_PYTHON_VERSION,
                "source_wheel": wheel_name,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime.runtime_verification_path(version_root).write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
                "version": "0.1.1",
                "verification": {"wheel_sha256": "wheel-0.1.1"},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if verification is not None:
        runtime.runtime_verification_path(version_root).write_text(
            json.dumps(
                {
                    "schema_version": MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
                    "version": version,
                    "verification": verification,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        _trust_managed_runtime(version_root)


def _trust_managed_runtime(version_root: Path) -> None:
    repo_root: Path | None = None
    for candidate in version_root.parents:
        if candidate.name == ".odylith":
            repo_root = candidate.parent
            break
    if repo_root is None:  # pragma: no cover - test helper misuse
        raise ValueError(f"could not resolve repo root for runtime: {version_root}")
    runtime.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=version_root,
        verification=runtime.runtime_verification_evidence(version_root),
    )


def test_ensure_launcher_points_at_repo_local_runtime(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = _make_runtime(repo_root)

    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    launcher = runtime.ensure_launcher(repo_root=repo_root, fallback_python=version_root / "bin" / "python")
    bootstrap = repo_root / ".odylith" / "bin" / "odylith-bootstrap"

    assert launcher == repo_root / ".odylith" / "bin" / "odylith"
    assert launcher.is_file()
    assert bootstrap.is_file()
    text = launcher.read_text(encoding="utf-8")
    bootstrap_text = bootstrap.read_text(encoding="utf-8")
    assert "runtime/current/bin/python" in text
    assert '-I -m odylith.cli "$@"' in text
    assert "unset VIRTUAL_ENV" in text
    assert "unset PYTHONPATH" in text
    assert "export PYTHONNOUSERSITE=1" in text
    assert 'fallback_source_root=""' in text
    assert "odylith_upgrade_bootstrap_required" in text
    assert "Odylith is bootstrapping a safe upgrade path for this older consumer install." in text
    assert "runtime/current/bin/python" in bootstrap_text
    assert "Odylith bootstrap could not find a trusted repo-local runtime." in bootstrap_text
    assert runtime._launcher_fallback_python(bootstrap) == (version_root / "bin" / "python").resolve()  # noqa: SLF001


def test_legacy_consumer_launcher_bootstraps_plain_upgrade_via_installer(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "0.1.1"
    bin_dir = version_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name in ("python", "python3"):
        executable = bin_dir / name
        executable.write_text(f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        executable.chmod(0o755)
    (version_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
                "version": "0.1.1",
                "platform": "darwin-arm64",
                "python_version": MANAGED_PYTHON_VERSION,
                "source_wheel": "odylith-0.1.1-py3-none-any.whl",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime.runtime_verification_path(version_root).write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
                "version": "0.1.1",
                "verification": {"wheel_sha256": "wheel-0.1.1"},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    launcher = runtime.ensure_launcher(repo_root=repo_root, fallback_python=version_root / "bin" / "python")

    fake_install = tmp_path / "fake-install.sh"
    fake_install.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "${ODYLITH_VERSION:-}" > "$PWD/bootstrap-version.txt"',
                'mkdir -p "$PWD/.odylith/bin"',
                'cat > "$PWD/.odylith/bin/odylith" <<'"'"'EOF'"'"'',
                "#!/usr/bin/env bash",
                'set -euo pipefail',
                'script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
                'repo_root="$(cd "$script_dir/../.." && pwd)"',
                'printf "%s\\n" "${ODYLITH_LAUNCHER_BOOTSTRAPPED:-}" > "$repo_root/bootstrap-guard.txt"',
                'printf "%s\\n" "$*" > "$repo_root/bootstrap-final-args.txt"',
                "exit 0",
                "EOF",
                'chmod +x "$PWD/.odylith/bin/odylith"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_install.chmod(0o755)

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'destination=""',
                'while (($#)); do',
                '  case "$1" in',
                '    -o)',
                '      destination="$2"',
                "      shift 2",
                "      ;;",
                "    *)",
                "      shift",
                "      ;;",
                "  esac",
                "done",
                'cp "$FAKE_INSTALL_SH" "$destination"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
    env["FAKE_INSTALL_SH"] = str(fake_install)

    completed = subprocess.run(
        [str(launcher), "upgrade"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "bootstrapping a safe upgrade path" in completed.stderr
    assert (repo_root / "bootstrap-version.txt").read_text(encoding="utf-8").strip() == "latest"
    assert (repo_root / "bootstrap-guard.txt").read_text(encoding="utf-8").strip() == "1"
    assert (repo_root / "bootstrap-final-args.txt").read_text(encoding="utf-8").strip() == "upgrade"


def test_legacy_consumer_launcher_keeps_explicit_target_upgrade_on_runtime_path(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "0.1.1"
    bin_dir = version_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    runtime_python = bin_dir / "python"
    runtime_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'repo_root="$PWD"',
                'printf "%s\\n" "$*" > "$repo_root/runtime-invocation.txt"',
                "exit 0",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime_python.chmod(0o755)
    (bin_dir / "python3").write_text(f'#!/usr/bin/env bash\nexec "{runtime_python}" "$@"\n', encoding="utf-8")
    (bin_dir / "python3").chmod(0o755)
    (version_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
                "version": "0.1.1",
                "platform": "darwin-arm64",
                "python_version": MANAGED_PYTHON_VERSION,
                "source_wheel": "odylith-0.1.1-py3-none-any.whl",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime.runtime_verification_path(version_root).write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
                "version": "0.1.1",
                "verification": {"wheel_sha256": "wheel-0.1.1"},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    launcher = runtime.ensure_launcher(repo_root=repo_root, fallback_python=runtime_python)

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text("#!/usr/bin/env bash\nexit 91\n", encoding="utf-8")
    fake_curl.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    completed = subprocess.run(
        [str(launcher), "upgrade", "--to", "0.1.2", "--write-pin"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert not (repo_root / "bootstrap-version.txt").exists()
    assert "upgrade --to 0.1.2 --write-pin" in (repo_root / "runtime-invocation.txt").read_text(encoding="utf-8")


def test_bootstrap_launcher_runs_repo_local_runtime_when_primary_launcher_is_missing(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    _seed_managed_runtime(version_root, verification={"wheel_sha256": "wheel-1.2.3"})
    runtime_python = version_root / "bin" / "python"
    runtime_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "$*" > "$PWD/bootstrap-runtime-invocation.txt"',
                "exit 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    runtime_python.chmod(0o755)
    _trust_managed_runtime(version_root)

    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    runtime.ensure_launcher(repo_root=repo_root, fallback_python=runtime_python)
    (repo_root / ".odylith" / "bin" / "odylith").unlink()

    completed = subprocess.run(
        [str(repo_root / ".odylith" / "bin" / "odylith-bootstrap"), "doctor", "--repo-root", ".", "--repair"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert (repo_root / "bootstrap-runtime-invocation.txt").read_text(encoding="utf-8").strip() == (
        "-I -m odylith.cli doctor --repo-root . --repair"
    )


def test_launcher_runs_current_managed_runtime_via_current_symlink(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    _seed_managed_runtime(version_root, verification={"wheel_sha256": "wheel-1.2.3"})
    runtime_python = version_root / "bin" / "python"
    runtime_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "$*" > "$PWD/runtime-invocation.txt"',
                "exit 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    runtime_python.chmod(0o755)
    _trust_managed_runtime(version_root)

    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    runtime.ensure_launcher(repo_root=repo_root, fallback_python=runtime_python)

    completed = subprocess.run(
        [str(repo_root / ".odylith" / "bin" / "odylith"), "version", "--repo-root", "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert (repo_root / "runtime-invocation.txt").read_text(encoding="utf-8").strip() == (
        "-I -m odylith.cli version --repo-root ."
    )


def test_launcher_error_guidance_does_not_execute_bootstrap_command_substitution(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    _seed_managed_runtime(version_root, verification={"wheel_sha256": "wheel-1.2.3"})
    fallback_python = version_root / "bin" / "python"

    runtime.ensure_launcher(repo_root=repo_root, fallback_python=fallback_python)
    (repo_root / ".odylith" / "trust" / "managed-runtime-trust" / "1.2.3.env").unlink()
    bootstrap_marker = repo_root / "bootstrap-recursed.txt"
    bootstrap = repo_root / ".odylith" / "bin" / "odylith-bootstrap"
    bootstrap.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "recursed\\n" > "$PWD/bootstrap-recursed.txt"',
                "exit 99",
                "",
            ]
        ),
        encoding="utf-8",
    )
    bootstrap.chmod(0o755)

    completed = subprocess.run(
        [str(repo_root / ".odylith" / "bin" / "odylith"), "version", "--repo-root", "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert not bootstrap_marker.exists()
    assert "Odylith launcher detected untrusted or unhealthy runtime state." in completed.stderr
    assert "odylith-bootstrap doctor --repo-root . --repair" in completed.stderr


def test_managed_runtime_integrity_ignores_generated_python_bytecode(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    _seed_managed_runtime(version_root, verification={"wheel_sha256": "wheel-1.2.3"})

    pycache = version_root / "lib" / "python3.13" / "__pycache__"
    pycache.mkdir(parents=True, exist_ok=True)
    (pycache / "_colorize.cpython-313.pyc").write_bytes(b"bytecode")

    reasons = runtime_integrity.managed_runtime_integrity_reasons(repo_root=repo_root, runtime_root=version_root)

    assert reasons == []


def test_bootstrap_launcher_skips_unverified_managed_runtime_candidates(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)

    bad_root = repo_root / ".odylith" / "runtime" / "versions" / "0.9.9"
    bad_python = bad_root / "bin" / "python"
    bad_python.parent.mkdir(parents=True, exist_ok=True)
    bad_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "bad\\n" > "$PWD/bootstrap-bad-candidate.txt"',
                "exit 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    bad_python.chmod(0o755)
    (bad_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
                "version": "0.9.9",
                "platform": "darwin-arm64",
                "python_version": MANAGED_PYTHON_VERSION,
                "source_wheel": "odylith-0.9.9-py3-none-any.whl",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    good_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    _seed_managed_runtime(good_root, verification={"wheel_sha256": "wheel-1.2.3"})
    good_python = good_root / "bin" / "python"
    good_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "good\\n" > "$PWD/bootstrap-good-candidate.txt"',
                "exit 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    good_python.chmod(0o755)
    _trust_managed_runtime(good_root)

    bootstrap = repo_root / ".odylith" / "bin" / "odylith-bootstrap"
    bootstrap.parent.mkdir(parents=True, exist_ok=True)
    bootstrap.write_text(
        runtime._bootstrap_launcher_script(fallback_python=tmp_path / "missing-python"),  # noqa: SLF001
        encoding="utf-8",
    )
    bootstrap.chmod(0o755)

    completed = subprocess.run(
        [str(bootstrap), "doctor", "--repo-root", ".", "--repair"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 0
    assert (repo_root / "bootstrap-good-candidate.txt").read_text(encoding="utf-8").strip() == "good"
    assert not (repo_root / "bootstrap-bad-candidate.txt").exists()


def test_repo_launcher_falls_back_from_self_referential_current_wrapper_without_hanging(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    source_root = tmp_path / "source"
    (source_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (source_root / "pyproject.toml").write_text("[project]\nname = 'odylith'\nversion = '1.2.3'\n", encoding="utf-8")

    managed_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    _seed_managed_runtime(managed_root, verification={"wheel_sha256": "wheel-1.2.3"})
    managed_python = managed_root / "bin" / "python"
    managed_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "$*" > "$PWD/launcher-fallback-invocation.txt"',
                "exit 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    managed_python.chmod(0o755)
    _trust_managed_runtime(managed_root)

    launcher = runtime.ensure_launcher(
        repo_root=repo_root,
        fallback_python=managed_python,
        fallback_source_root=source_root,
        allow_host_python_fallback=True,
    )

    broken_root = repo_root / ".odylith" / "runtime" / "versions" / "source-local"
    broken_python = broken_root / "bin" / "python"
    broken_python.parent.mkdir(parents=True, exist_ok=True)
    broken_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f'export PYTHONPATH="{source_root / "src"}${{PYTHONPATH:+:$PYTHONPATH}}"',
                f'exec "{repo_root / ".odylith" / "runtime" / "current" / "bin" / "python"}" "$@"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    broken_python.chmod(0o755)
    runtime.switch_runtime(repo_root=repo_root, target=broken_root)

    completed = subprocess.run(
        [str(launcher), "version", "--repo-root", "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 0
    assert (repo_root / "launcher-fallback-invocation.txt").read_text(encoding="utf-8").strip() == (
        "-m odylith.cli version --repo-root ."
    )


def test_repo_launcher_falls_back_to_repo_local_source_python_when_recorded_fallback_is_stale(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    (repo_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text("[project]\nname = 'odylith'\nversion = '1.2.3'\n", encoding="utf-8")
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text('{"version":"v1","components":[]}\n', encoding="utf-8")
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog\n", encoding="utf-8")

    repo_python = repo_root / ".venv" / "bin" / "python"
    repo_python.parent.mkdir(parents=True, exist_ok=True)
    repo_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "$*" > "$PWD/repo-source-fallback-invocation.txt"',
                "exit 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    repo_python.chmod(0o755)

    launcher = repo_root / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        runtime._launcher_script(  # noqa: SLF001
            fallback_python=tmp_path / "missing" / "python",
            fallback_source_root=repo_root,
        ),
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    completed = subprocess.run(
        [str(launcher), "version", "--repo-root", "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 0
    assert (repo_root / "repo-source-fallback-invocation.txt").read_text(encoding="utf-8").strip() == (
        "-m odylith.cli version --repo-root ."
    )


def test_doctor_runtime_accepts_product_repo_launchers_when_recorded_fallbacks_are_stale(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    (repo_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text("[project]\nname = 'odylith'\nversion = '1.2.3'\n", encoding="utf-8")
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        '{"version":"v1","components":[]}\n',
        encoding="utf-8",
    )
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog\n", encoding="utf-8")

    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    _seed_managed_runtime(version_root, verification={"wheel_sha256": "wheel-1.2.3"})
    runtime.switch_runtime(repo_root=repo_root, target=version_root)

    launcher = repo_root / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        runtime._launcher_script(  # noqa: SLF001
            fallback_python=tmp_path / "missing" / "python",
            fallback_source_root=repo_root,
        ),
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    bootstrap = repo_root / ".odylith" / "bin" / "odylith-bootstrap"
    bootstrap.write_text(
        runtime._bootstrap_launcher_script(  # noqa: SLF001
            fallback_python=tmp_path / "missing" / "python",
            fallback_source_root=repo_root,
        ),
        encoding="utf-8",
    )
    bootstrap.chmod(0o755)

    healthy, reasons = runtime.doctor_runtime(repo_root=repo_root, repair=False)

    assert healthy is True
    assert reasons == []


def test_ensure_launcher_rejects_host_python_fallback_without_opt_in(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)

    try:
        runtime.ensure_launcher(repo_root=repo_root, fallback_python=Path("/usr/bin/python3"))
    except ValueError as exc:
        assert "launcher fallback python must stay inside" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected untrusted host-python fallback to be rejected")


def test_ensure_launcher_accepts_repo_local_legacy_venv_python_symlink(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "0.1.0"
    bin_dir = version_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    host_root = tmp_path / "host-python"
    host_root.mkdir()
    host_python = host_root / "python3.13"
    host_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    host_python.chmod(0o755)

    (bin_dir / "python3.13").symlink_to(host_python)
    (bin_dir / "python").symlink_to("python3.13")
    (bin_dir / "python3").symlink_to("python3.13")
    (version_root / "pyvenv.cfg").write_text("version = 3.13.12\n", encoding="utf-8")

    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    launcher = runtime.ensure_launcher(repo_root=repo_root, fallback_python=version_root / "bin" / "python")

    text = launcher.read_text(encoding="utf-8")
    assert str(version_root / "bin" / "python") in text
    assert str(host_python) not in text


def test_ensure_wrapped_runtime_preserves_host_venv_python_path(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    source_root = tmp_path / "source"
    (source_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (source_root / "pyproject.toml").write_text("[project]\nname = 'odylith'\nversion = '1.2.3'\n", encoding="utf-8")

    host_root = tmp_path / "host-python"
    host_root.mkdir()
    host_python = host_root / "python3.13"
    host_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    host_python.chmod(0o755)

    venv_root = tmp_path / "host-venv"
    venv_bin = venv_root / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    (venv_bin / "python3.13").symlink_to(host_python)
    (venv_bin / "python").symlink_to("python3.13")

    version_root = runtime.ensure_wrapped_runtime(
        repo_root=repo_root,
        version="repaired-local",
        fallback_python=venv_bin / "python",
        source_root=source_root,
        allow_host_python_fallback=True,
    )

    text = (version_root / "bin" / "python").read_text(encoding="utf-8")
    assert str(venv_bin / "python") in text
    assert str(host_python) not in text
    assert str(source_root / "src") in text


def test_ensure_wrapped_runtime_normalizes_current_runtime_symlink_fallback(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    source_root = tmp_path / "source"
    (source_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (source_root / "pyproject.toml").write_text("[project]\nname = 'odylith'\nversion = '1.2.3'\n", encoding="utf-8")

    managed_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    managed_python = managed_root / "bin" / "python"
    managed_python.parent.mkdir(parents=True, exist_ok=True)
    managed_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    managed_python.chmod(0o755)
    runtime.switch_runtime(repo_root=repo_root, target=managed_root)

    wrapped_root = runtime.ensure_wrapped_runtime(
        repo_root=repo_root,
        version="source-local",
        fallback_python=repo_root / ".odylith" / "runtime" / "current" / "bin" / "python",
        source_root=source_root,
    )

    text = (wrapped_root / "bin" / "python").read_text(encoding="utf-8")
    assert str(managed_root / "bin" / "python") in text
    assert "runtime/current/bin/python" not in text
    assert str(source_root / "src") in text


def test_ensure_launcher_preserves_host_venv_python_path_when_source_root_is_provided(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    source_root = tmp_path / "source"
    (source_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (source_root / "pyproject.toml").write_text("[project]\nname = 'odylith'\nversion = '1.2.3'\n", encoding="utf-8")

    host_root = tmp_path / "host-python"
    host_root.mkdir()
    host_python = host_root / "python3.13"
    host_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    host_python.chmod(0o755)

    venv_root = tmp_path / "host-venv"
    venv_bin = venv_root / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    (venv_bin / "python3.13").symlink_to(host_python)
    (venv_bin / "python").symlink_to("python3.13")

    launcher = runtime.ensure_launcher(
        repo_root=repo_root,
        fallback_python=venv_bin / "python",
        fallback_source_root=source_root,
        allow_host_python_fallback=True,
    )

    text = launcher.read_text(encoding="utf-8")
    assert str(venv_bin / "python") in text
    assert str(host_python) not in text
    assert str(source_root / "src") in text


def test_doctor_runtime_repairs_missing_launcher(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = _make_runtime(repo_root)
    runtime.switch_runtime(repo_root=repo_root, target=version_root)

    healthy, reasons = runtime.doctor_runtime(repo_root=repo_root, repair=False)
    assert healthy is False
    assert "repo launcher missing" in reasons

    repaired, repaired_reasons = runtime.doctor_runtime(repo_root=repo_root, repair=True)
    assert repaired is True
    assert repaired_reasons == []
    assert (repo_root / ".odylith" / "bin" / "odylith").is_file()


def test_doctor_runtime_repairs_missing_bootstrap_launcher(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = _make_runtime(repo_root)
    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    runtime.ensure_launcher(repo_root=repo_root, fallback_python=version_root / "bin" / "python")
    (repo_root / ".odylith" / "bin" / "odylith-bootstrap").unlink()

    healthy, reasons = runtime.doctor_runtime(repo_root=repo_root, repair=False)
    assert healthy is False
    assert "bootstrap launcher missing" in reasons

    repaired, repaired_reasons = runtime.doctor_runtime(repo_root=repo_root, repair=True)
    assert repaired is True
    assert repaired_reasons == []
    assert (repo_root / ".odylith" / "bin" / "odylith-bootstrap").is_file()


def test_doctor_runtime_repairs_self_referential_source_local_wrapper(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    source_root = tmp_path / "source"
    (source_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)

    managed_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    managed_python = managed_root / "bin" / "python"
    managed_python.parent.mkdir(parents=True, exist_ok=True)
    managed_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    managed_python.chmod(0o755)

    runtime.ensure_launcher(
        repo_root=repo_root,
        fallback_python=managed_python,
        fallback_source_root=source_root,
        allow_host_python_fallback=True,
    )

    broken_root = repo_root / ".odylith" / "runtime" / "versions" / "source-local"
    broken_python = broken_root / "bin" / "python"
    broken_python.parent.mkdir(parents=True, exist_ok=True)
    broken_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f'export PYTHONPATH="{source_root / "src"}${{PYTHONPATH:+:$PYTHONPATH}}"',
                f'exec "{repo_root / ".odylith" / "runtime" / "current" / "bin" / "python"}" "$@"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    broken_python.chmod(0o755)
    runtime.switch_runtime(repo_root=repo_root, target=broken_root)

    healthy, reasons = runtime.doctor_runtime(repo_root=repo_root, repair=False)
    assert healthy is False
    assert any("loops back into itself" in reason for reason in reasons)

    repaired, repaired_reasons = runtime.doctor_runtime(repo_root=repo_root, repair=True)
    assert repaired is True
    assert repaired_reasons == []
    assert (repo_root / ".odylith" / "runtime" / "current").resolve() == broken_root

    repaired_text = broken_python.read_text(encoding="utf-8")
    assert str(managed_root / "bin" / "python") in repaired_text
    assert "runtime/current/bin/python" not in repaired_text


def test_doctor_runtime_repair_ignores_untrusted_launcher_fallback(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    managed_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    _seed_managed_runtime(managed_root, verification={"wheel_sha256": "wheel-1.2.3"})

    evil_root = tmp_path / "evil"
    evil_root.mkdir()
    evil_python = evil_root / "python"
    evil_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    evil_python.chmod(0o755)

    launcher = repo_root / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        runtime._launcher_script(fallback_python=evil_python),  # noqa: SLF001
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    repaired, repaired_reasons = runtime.doctor_runtime(
        repo_root=repo_root,
        repair=True,
        allow_host_python_fallback=True,
    )

    assert repaired is True
    assert repaired_reasons == []
    assert (repo_root / ".odylith" / "runtime" / "current").resolve() == managed_root
    repaired_launcher = launcher.read_text(encoding="utf-8")
    assert str(evil_python) not in repaired_launcher
    assert str(managed_root / "bin" / "python") in repaired_launcher


def test_doctor_runtime_repairs_missing_current_runtime_from_existing_version(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = _make_runtime(repo_root)
    runtime.ensure_launcher(repo_root=repo_root, fallback_python=version_root / "bin" / "python")

    repaired, repaired_reasons = runtime.doctor_runtime(repo_root=repo_root, repair=True)

    assert repaired is True
    assert repaired_reasons == []
    assert (repo_root / ".odylith" / "runtime" / "current").is_symlink()
    assert (repo_root / ".odylith" / "runtime" / "current").resolve() == version_root


def test_current_runtime_root_rejects_symlink_outside_versions(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    outside_root = tmp_path / "outside-runtime"
    outside_root.mkdir()
    current = repo_root / ".odylith" / "runtime" / "current"
    current.parent.mkdir(parents=True, exist_ok=True)
    current.symlink_to(outside_root)

    assert runtime.current_runtime_root(repo_root=repo_root) is None


def test_switch_runtime_rejects_target_outside_versions(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    outside_root = tmp_path / "outside-runtime"
    outside_root.mkdir()

    try:
        runtime.switch_runtime(repo_root=repo_root, target=outside_root)
    except ValueError as exc:
        assert "runtime target must stay inside" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected switch_runtime to reject targets outside runtime versions")


def test_supported_managed_runtime_platforms_pin_upstream_sha256() -> None:
    for runtime_platform in supported_managed_runtime_platforms():
        assert len(runtime_platform.upstream_asset_sha256) == 64


def test_install_release_runtime_reuses_existing_verified_runtime(monkeypatch, tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    verification = {
        "manifest_sha256": "manifest",
        "provenance_sha256": "provenance",
        "runtime_bundle_platform": "darwin-arm64",
        "runtime_bundle_sha256": "runtime",
        "sbom_sha256": "sbom",
        "signer_identity": "signer",
        "wheel_sha256": "wheel",
    }
    wheel_path = tmp_path / "odylith-1.2.3-py3-none-any.whl"
    wheel_path.write_bytes(b"wheel")
    _seed_managed_runtime(version_root, verification=verification)

    monkeypatch.setattr(
        runtime,
        "download_verified_release",
        lambda **_: SimpleNamespace(
            version="1.2.3",
            manifest={"repo_schema_version": 1},
            runtime_bundle_path=tmp_path / "runtime.tar.gz",
            runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
            wheel_path=wheel_path,
            verification=verification,
        ),
    )
    monkeypatch.setattr(
        runtime,
        "_extract_runtime_bundle",
        lambda **_: (_ for _ in ()).throw(AssertionError("existing verified runtime should be reused")),
    )

    staged = runtime.install_release_runtime(repo_root=repo_root, repo="odylith/odylith", version="1.2.3", activate=False)

    assert staged.root == version_root
    assert staged.python == version_root / "bin" / "python"
    assert runtime.load_runtime_verification(version_root)["verification"] == verification


def test_install_release_runtime_reextracts_untrusted_existing_runtime(monkeypatch, tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    wheel_path = tmp_path / "odylith-1.2.3-py3-none-any.whl"
    wheel_path.write_bytes(b"wheel")
    expected_verification = {
        "manifest_sha256": "manifest",
        "provenance_sha256": "provenance",
        "runtime_bundle_platform": "darwin-arm64",
        "runtime_bundle_sha256": "runtime",
        "sbom_sha256": "sbom",
        "signer_identity": "signer",
        "wheel_sha256": "wheel",
    }
    _seed_managed_runtime(version_root, verification={"runtime_bundle_sha256": "stale"})
    extracted: list[Path] = []

    monkeypatch.setattr(
        runtime,
        "download_verified_release",
        lambda **_: SimpleNamespace(
            version="1.2.3",
            manifest={"repo_schema_version": 1},
            runtime_bundle_path=tmp_path / "runtime.tar.gz",
            runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
            wheel_path=wheel_path,
            verification=expected_verification,
        ),
    )

    def _fake_extract_runtime_bundle(*, bundle_path: Path, destination: Path) -> None:
        del bundle_path
        extracted.append(destination)
        _seed_managed_runtime(destination, verification=None)

    monkeypatch.setattr(runtime, "_extract_runtime_bundle", _fake_extract_runtime_bundle)

    staged = runtime.install_release_runtime(repo_root=repo_root, repo="odylith/odylith", version="1.2.3", activate=False)

    assert len(extracted) == 1
    assert extracted[0].name == version_root.name
    assert extracted[0].parent.name.startswith(f".{version_root.name}.stage-")
    assert staged.root == version_root
    assert runtime.load_runtime_verification(version_root)["verification"] == expected_verification


def test_install_release_runtime_preserves_existing_runtime_when_restage_fails(monkeypatch, tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    wheel_path = tmp_path / "odylith-1.2.3-py3-none-any.whl"
    wheel_path.write_bytes(b"wheel")
    _seed_managed_runtime(version_root, verification={"runtime_bundle_sha256": "stale"})

    monkeypatch.setattr(
        runtime,
        "download_verified_release",
        lambda **_: SimpleNamespace(
            version="1.2.3",
            manifest={"repo_schema_version": 1},
            runtime_bundle_path=tmp_path / "runtime.tar.gz",
            runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
            wheel_path=wheel_path,
            verification={"runtime_bundle_sha256": "fresh"},
        ),
    )
    monkeypatch.setattr(
        runtime,
        "_extract_runtime_bundle",
        lambda **_: (_ for _ in ()).throw(RuntimeError("extract failed")),
    )

    try:
        runtime.install_release_runtime(repo_root=repo_root, repo="odylith/odylith", version="1.2.3", activate=False)
    except RuntimeError as exc:
        assert "extract failed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected restage failure to surface")

    assert version_root.is_dir()
    assert (version_root / "bin" / "python").is_file()
    assert runtime.load_runtime_verification(version_root)["verification"] == {"runtime_bundle_sha256": "stale"}


def test_extract_runtime_bundle_accepts_in_tree_relative_symlink(tmp_path: Path) -> None:
    bundle_path = tmp_path / "runtime.tar.gz"
    metadata_bytes = json.dumps(
        {
            "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
            "version": "1.2.3",
            "platform": "darwin-arm64",
            "python_version": MANAGED_PYTHON_VERSION,
            "source_wheel": "odylith-1.2.3-py3-none-any.whl",
        }
    ).encode("utf-8")
    with tarfile.open(bundle_path, "w:gz") as archive:
        for name, payload in {
            "runtime/bin/python": b"",
            "runtime/bin/python3": b"",
            "runtime/bin/odylith": b"",
            "runtime/runtime-metadata.json": metadata_bytes,
            "runtime/lib/terminfo-target": b"ok",
        }.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        link = tarfile.TarInfo(name="runtime/share/terminfo/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../lib/terminfo-target"
        archive.addfile(link)

    destination = tmp_path / "runtime-root"
    runtime._extract_runtime_bundle(bundle_path=bundle_path, destination=destination)  # noqa: SLF001

    assert destination.is_dir()
    assert (destination / "share" / "terminfo" / "link").is_symlink()

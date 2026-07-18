from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "greenfield_matrix_exact_preamble_probe",
        SCRIPTS_ROOT / "greenfield_matrix_exact_preamble_probe.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_exact_preamble_probe_writes_sanitized_observation_before_cleaning_temp_root(tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    install_script = dist_dir / "install.sh"
    install_script.write_text("#!/usr/bin/env bash\nprintf 'installed\\n'\n", encoding="utf-8")
    install_script.chmod(0o755)
    output_json = tmp_path / "evidence" / "probe.json"

    payload = module.run_probe(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path / "temp",
        output_json=output_json,
        install_timeout_seconds=5,
    )

    persisted = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload == persisted
    assert payload["status"] == "passed"
    assert payload["scope"] == "one_server_git_init_group_timeout_install"
    assert payload["git_init"]["status"] == "completed"
    assert payload["git_init"]["returncode"] == 0
    assert payload["git_init"]["pid"] > 0
    assert payload["install"]["returncode"] == 0
    assert payload["install"]["stdout_bytes"] == len("installed\n")
    assert not list((tmp_path / "temp").glob("odylith-greenfield-exact-preamble-*"))


def test_exact_preamble_probe_invokes_installer_after_git_init_failure(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    install_script = dist_dir / "install.sh"
    install_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    output_json = tmp_path / "evidence" / "probe.json"
    commands: list[list[str]] = []
    start_snapshots: list[dict] = []

    class Server:
        def shutdown(self) -> None:
            return None

        def server_close(self) -> None:
            return None

    def fake_run(*, command, on_started, **_kwargs):  # noqa: ANN001
        commands.append(command)
        on_started(101, 101)
        start_snapshots.append(json.loads(output_json.read_text(encoding="utf-8")))
        return subprocess.CompletedProcess(command, 1 if command[0] == "git" else 0, stdout="", stderr="")

    monkeypatch.setattr(module, "_serve_directory", lambda _dist_dir: (Server(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_run", fake_run)

    payload = module.run_probe(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path / "temp",
        output_json=output_json,
        install_timeout_seconds=5,
    )

    assert commands == [["git", "init"], ["bash", str(install_script)]]
    assert payload["status"] == "failed"
    assert payload["git_init"]["returncode"] == 1
    assert payload["install"]["returncode"] == 0
    assert payload["install"]["pid"] == 101
    assert start_snapshots[0]["git_init"] == {"argv": ["git", "init"], "pgid": 101, "pid": 101, "status": "running"}
    assert start_snapshots[1]["install"] == {"argv": ["bash", str(install_script)], "pgid": 101, "pid": 101, "status": "running"}
    assert json.loads(output_json.read_text(encoding="utf-8"))["install"]["pid"] == 101


def test_command_observation_records_unverified_timeout_cleanup() -> None:
    module = _module()
    result = subprocess.CompletedProcess(["bash", "install.sh"], 124, stdout="", stderr="timeout")
    result.termination_observation = "output_pipes_still_open_after_sigkill"

    observation = module._command_observation(command=["bash", "install.sh"], result=result, elapsed_seconds=6.1)

    assert observation["returncode"] == 124
    assert observation["termination_observation"] == "output_pipes_still_open_after_sigkill"


@pytest.mark.parametrize("timeout", (0, float("inf"), float("nan")))
def test_exact_preamble_probe_rejects_invalid_install_timeout_before_creating_a_temp_root(tmp_path: Path, timeout: float) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="finite number"):
        module.run_probe(
            dist_dir=dist_dir,
            version="0.1.15",
            temp_parent=tmp_path / "temp",
            install_timeout_seconds=timeout,
        )

    assert not (tmp_path / "temp").exists()


def test_exact_preamble_probe_cli_rejects_non_finite_install_timeout() -> None:
    module = _module()

    with pytest.raises(SystemExit) as exc_info:
        module.main(["--dist-dir", "/missing", "--version", "0.1.15", "--temp-parent", "/tmp", "--output-json", "/tmp/probe.json", "--install-timeout-seconds", "inf"])

    assert exc_info.value.code == 2


def test_exact_preamble_probe_records_install_failure_without_leaking_temp_root(tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    install_script = dist_dir / "install.sh"
    install_script.write_text("#!/usr/bin/env bash\nprintf 'failed\\n' >&2\nexit 7\n", encoding="utf-8")
    install_script.chmod(0o755)
    output_json = tmp_path / "evidence" / "probe.json"

    payload = module.run_probe(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path / "temp",
        output_json=output_json,
        install_timeout_seconds=5,
    )

    assert payload["status"] == "failed"
    assert payload["install"]["returncode"] == 7
    assert payload["install"]["stderr_bytes"] == len("failed\n")
    assert json.loads(output_json.read_text(encoding="utf-8"))["status"] == "failed"
    assert not list((tmp_path / "temp").glob("odylith-greenfield-exact-preamble-*"))


def test_exact_preamble_probe_records_server_cleanup_failure_and_removes_temp_root(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    install_script = dist_dir / "install.sh"
    install_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    install_script.chmod(0o755)
    output_json = tmp_path / "evidence" / "probe.json"
    closed: list[bool] = []

    class Server:
        def shutdown(self) -> None:
            raise RuntimeError("shutdown fault")

        def server_close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(module, "_serve_directory", lambda _dist_dir: (Server(), "http://127.0.0.1:8123"))

    payload = module.run_probe(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path / "temp",
        output_json=output_json,
        install_timeout_seconds=5,
    )

    assert payload["status"] == "harness_error"
    assert payload["cleanup_errors"] == ["server shutdown failed: RuntimeError: shutdown fault"]
    assert closed == [True]
    assert json.loads(output_json.read_text(encoding="utf-8"))["status"] == "harness_error"
    assert not list((tmp_path / "temp").glob("odylith-greenfield-exact-preamble-*"))

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(SCRIPTS_ROOT / "greenfield_process.py", "greenfield_process")


def test_run_command_with_group_timeout_terminates_process_group(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    popen_kwargs: dict[str, object] = {}
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 4242
        returncode = -15

        def __init__(self) -> None:
            self.calls = 0

        def communicate(self, timeout=None):  # noqa: ANN001
            self.calls += 1
            if self.calls == 1:
                raise module.subprocess.TimeoutExpired(
                    ["bash", "install.sh"],
                    timeout,
                    output="partial stdout",
                    stderr="partial stderr",
                )
            return "final stdout", "final stderr"

    fake_process = FakeProcess()

    def fake_popen(*_args, **kwargs):  # noqa: ANN001
        popen_kwargs.update(kwargs)
        return fake_process

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    result = module.run_command_with_group_timeout(
        cwd=tmp_path,
        env={},
        command=["bash", "install.sh"],
        timeout=0.01,
    )

    assert result.returncode == 124
    assert popen_kwargs["start_new_session"] is True
    assert killed == [(4242, module.signal.SIGTERM)]
    assert "partial stdout" in result.stdout
    assert "partial stderr" in result.stderr
    assert "process group was terminated" in result.stderr

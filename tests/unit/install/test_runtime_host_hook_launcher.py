from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from odylith.install import runtime
from odylith.install.managed_runtime import MANAGED_PYTHON_VERSION


_MANAGED_SITE_PACKAGES_PYTHON_DIR = "python" + ".".join(MANAGED_PYTHON_VERSION.split(".")[:2])


def _write_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return repo_root


def _runtime_python(repo_root: Path) -> Path:
    return repo_root / ".odylith" / "runtime" / "versions" / "1.2.3" / "bin" / "python"


def _write_launcher(repo_root: Path, fallback_python: Path, *, source_root: Path | None = None) -> Path:
    launcher = repo_root / ".odylith" / "bin" / "odylith"
    _write_executable(
        launcher,
        runtime._launcher_script(  # noqa: SLF001
            fallback_python=fallback_python,
            fallback_source_root=source_root,
        ),
    )
    return launcher


def _write_fake_host_python(path: Path) -> Path:
    _write_executable(
        path,
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "$*" >> "$PWD/python-calls.txt"',
                'case "$*" in',
                '  "-I -m odylith.runtime.surfaces.claude_host_prompt_bundle"*)',
                '    printf "%s\\n" "unexpected direct prompt-bundle dispatch" >&2',
                "    exit 42",
                "    ;;",
                '  "-I -m odylith.cli claude prompt-context --repo-root ."*)',
                """    printf '%s' '{"hookSpecificOutput":{"additionalContext":"legacy context"}}'""",
                "    exit 0",
                "    ;;",
                '  "-I -m odylith.cli claude prompt-teaser --repo-root ."*)',
                """    printf '%s' 'legacy teaser'""",
                "    exit 0",
                "    ;;",
                '  "-I - "*)',
                f'    exec "{sys.executable}" "$@"',
                "    ;;",
                '  "-m odylith.runtime.surfaces.claude_host_prompt_bundle"*)',
                """    printf '%s' '{"systemMessage":"source direct"}'""",
                "    exit 0",
                "    ;;",
                "esac",
                'printf "%s\\n" "unexpected invocation: $*" >&2',
                "exit 43",
                "",
            ]
        ),
    )
    return path


def test_launcher_legacy_claude_prompt_bundle_help_does_not_require_new_runtime_module(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    fake_python = _write_fake_host_python(_runtime_python(repo_root))
    launcher = _write_launcher(repo_root, fake_python)

    completed = subprocess.run(
        [str(launcher), "claude", "prompt-bundle", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 0
    assert "usage: odylith claude prompt-bundle" in completed.stdout
    assert not (repo_root / "python-calls.txt").exists()


def test_launcher_merges_legacy_claude_prompt_bundle_when_runtime_module_is_missing(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    fake_python = _write_fake_host_python(_runtime_python(repo_root))
    launcher = _write_launcher(repo_root, fake_python)

    completed = subprocess.run(
        [str(launcher), "claude", "prompt-bundle", "--repo-root", "."],
        cwd=repo_root,
        input='{"prompt":"why is odylith silent?"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["hookSpecificOutput"]["additionalContext"] == "legacy context"
    assert payload["systemMessage"] == "legacy teaser"
    calls = (repo_root / "python-calls.txt").read_text(encoding="utf-8")
    assert "odylith.cli claude prompt-context" in calls
    assert "odylith.cli claude prompt-teaser" in calls
    assert "odylith.runtime.surfaces.claude_host_prompt_bundle" not in calls


def test_launcher_direct_dispatches_claude_prompt_bundle_when_module_file_exists(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    fake_python = _runtime_python(repo_root)
    _write_executable(
        fake_python,
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "$*" > "$PWD/python-calls.txt"',
                """printf '%s' '{"systemMessage":"direct"}'""",
                "",
            ]
        ),
    )
    module_path = (
        fake_python.parent.parent
        / "lib"
        / _MANAGED_SITE_PACKAGES_PYTHON_DIR
        / "site-packages"
        / "odylith"
        / "runtime"
        / "surfaces"
        / "claude_host_prompt_bundle.py"
    )
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("# present\n", encoding="utf-8")
    launcher = _write_launcher(repo_root, fake_python)

    completed = subprocess.run(
        [str(launcher), "claude", "prompt-bundle", "--repo-root", "."],
        cwd=repo_root,
        input='{"prompt":"status"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["systemMessage"] == "direct"
    assert (repo_root / "python-calls.txt").read_text(encoding="utf-8").strip() == (
        "-I -m odylith.runtime.surfaces.claude_host_prompt_bundle --repo-root ."
    )


def test_launcher_detects_source_pythonpath_prompt_bundle_module(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    source_root = tmp_path / "source"
    module_path = source_root / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_prompt_bundle.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("# present\n", encoding="utf-8")
    (source_root / "pyproject.toml").write_text("[project]\nname = 'odylith'\nversion = '1.2.3'\n", encoding="utf-8")
    fake_python = _write_fake_host_python(_runtime_python(repo_root))
    launcher = _write_launcher(repo_root, fake_python, source_root=source_root)

    completed = subprocess.run(
        [str(launcher), "claude", "prompt-bundle", "--repo-root", "."],
        cwd=repo_root,
        input='{"prompt":"status"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["systemMessage"] == "source direct"
    assert (repo_root / "python-calls.txt").read_text(encoding="utf-8").strip() == (
        "-m odylith.runtime.surfaces.claude_host_prompt_bundle --repo-root ."
    )

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_write_audit import audited_program
from greenfield_matrix_write_audit import begin_installed_write_audit


def test_write_audit_accepts_read_only_process(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "evidence.txt").write_text("evidence only\n", encoding="utf-8")

    completed, evidence = _run_audited(
        repo_root,
        "from pathlib import Path\nassert Path('evidence.txt').read_text(encoding='utf-8') == 'evidence only\\n'",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    assert evidence.write_attempts == ()
    assert evidence.subprocess_attempts == ()
    assert evidence.error == ""


def test_write_audit_detects_same_user_write_and_restore(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target = repo_root / "odylith/radar/source/workstreams.v1.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"records": []}\n', encoding="utf-8")
    original = target.read_bytes()
    original_mode = target.stat().st_mode

    completed, evidence = _run_audited(
        repo_root,
        "\n".join(
            (
                "import os",
                "from pathlib import Path",
                "target = Path('odylith/radar/source/workstreams.v1.json')",
                "original = target.read_bytes()",
                "mode = target.stat().st_mode",
                "os.chmod(target, mode | 0o200)",
                "target.write_text('{\\\"records\\\": [\\\"transient\\\"]}\\n', encoding='utf-8')",
                "target.write_bytes(original)",
                "os.chmod(target, mode)",
            )
        ),
    )

    assert completed.returncode == 0, completed.stderr
    assert target.read_bytes() == original
    assert target.stat().st_mode == original_mode
    assert evidence.active is True
    assert any(attempt.startswith("os.chmod:") for attempt in evidence.write_attempts)
    assert "open:dir-fd" in evidence.write_attempts


def test_write_audit_keeps_real_events_when_child_forges_a_clean_record(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target = repo_root / "odylith/radar/source/workstreams.v1.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"records": []}\n', encoding="utf-8")
    original = target.read_bytes()

    completed, evidence = _run_audited(
        repo_root,
        "\n".join(
            (
                "import json, os",
                "from pathlib import Path",
                "target = Path('odylith/radar/source/workstreams.v1.json')",
                "original = target.read_bytes()",
                "target.write_text('{\\\"records\\\": [\\\"transient\\\"]}\\n', encoding='utf-8')",
                "target.write_bytes(original)",
                "os.write(int(os.environ['ODYLITH_GREENFIELD_WRITE_AUDIT_FD']), b'{\\\"event\\\":\\\"ready\\\",\\\"kind\\\":\\\"ready\\\"}\\n')",
            )
        ),
    )

    assert completed.returncode == 0, completed.stderr
    assert target.read_bytes() == original
    assert evidence.active is True
    assert "open:dir-fd" in evidence.write_attempts


def test_write_audit_detects_child_process_escape(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "import subprocess, sys\nsubprocess.run([sys.executable, '-c', 'pass'], check=True)",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    assert evidence.subprocess_attempts == ("subprocess.Popen",)


def test_write_audit_fails_closed_for_relative_write_path_with_directory_fd(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target = repo_root / "odylith/radar/source/workstreams.v1.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"records": []}\n', encoding="utf-8")
    original = target.read_bytes()

    completed, evidence = _run_audited(
        repo_root,
        "\n".join(
            (
                "import os",
                "directory = os.open('odylith/radar', os.O_RDONLY)",
                "descriptor = os.open('source/workstreams.v1.json', os.O_WRONLY | os.O_TRUNC, dir_fd=directory)",
                "os.write(descriptor, b'{\\\"records\\\": [\\\"transient\\\"]}\\n')",
                "os.close(descriptor)",
                "descriptor = os.open('source/workstreams.v1.json', os.O_WRONLY | os.O_TRUNC, dir_fd=directory)",
                f"os.write(descriptor, {original!r})",
                "os.close(descriptor)",
                "os.close(directory)",
            )
        ),
    )

    assert completed.returncode == 0, completed.stderr
    assert target.read_bytes() == original
    assert evidence.active is True
    assert "open:dir-fd" in evidence.write_attempts


def test_write_audit_fails_closed_when_the_child_never_activates_it(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    audit = begin_installed_write_audit(repo_root=repo_root)

    evidence = audit.finish()

    assert evidence.active is False
    assert evidence.error == "installed write audit did not activate"


def _run_audited(repo_root: Path, program: str) -> tuple[subprocess.CompletedProcess[str], object]:
    audit = begin_installed_write_audit(repo_root=repo_root)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", audited_program(program)],
            cwd=repo_root,
            env={**os.environ, **audit.environment()},
            pass_fds=audit.pass_fds,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        evidence = audit.finish()
    return completed, evidence

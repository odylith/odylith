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
    assert "open:odylith/radar/source/workstreams.v1.json" in evidence.write_attempts


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
    assert "open:odylith/radar/source/workstreams.v1.json" in evidence.write_attempts


def test_write_audit_records_child_process_diagnostic(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "import subprocess, sys\nsubprocess.run([sys.executable, '-c', 'pass'], check=True)",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    assert evidence.subprocess_attempts == ("subprocess.Popen",)


def test_write_audit_detects_relative_governed_write_with_directory_fd(tmp_path: Path) -> None:
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
    assert evidence.write_attempts == (
        "open:odylith/radar/source/workstreams.v1.json",
        "open:odylith/radar/source/workstreams.v1.json",
    )


def test_write_audit_ignores_relative_scratch_writes_outside_greenfield_ownership(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "from pathlib import Path\ntarget = Path('scratch.tmp')\ntarget.write_text('temporary')\ntarget.unlink()",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    assert evidence.write_attempts == ()


def test_write_audit_ignores_directory_fd_write_outside_greenfield_ownership(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch = repo_root / "scratch"
    scratch.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "\n".join(
            (
                "import os",
                "directory = os.open('scratch', os.O_RDONLY)",
                "descriptor = os.open('transient.txt', os.O_WRONLY | os.O_CREAT, dir_fd=directory)",
                "os.close(descriptor)",
                "os.remove('transient.txt', dir_fd=directory)",
                "os.close(directory)",
            )
        ),
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    assert evidence.write_attempts == ()


def test_write_audit_detects_pending_transaction_mutation(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "\n".join(
            (
                "from pathlib import Path",
                "target = Path('.odylith/runtime/greenfield/pending/hash/transaction.json')",
                "target.parent.mkdir(parents=True)",
                "target.write_text('{}')",
            )
        ),
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    assert "open:.odylith/runtime/greenfield/pending/hash/transaction.json" in evidence.write_attempts


def test_write_audit_detects_candidate_evidence_mutation(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "\n".join(
            (
                "from pathlib import Path",
                "target = Path('.odylith/runtime/greenfield/candidate-evidence.v1.json')",
                "target.parent.mkdir(parents=True)",
                "target.write_text('{}')",
            )
        ),
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    assert "open:.odylith/runtime/greenfield/candidate-evidence.v1.json" in evidence.write_attempts


def test_write_audit_fails_closed_for_malformed_trace(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "import os\nos.write(int(os.environ['ODYLITH_GREENFIELD_WRITE_AUDIT_FD']), b'not-json\\n')",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is False
    assert evidence.error.startswith("invalid write-audit trace line")


def test_write_audit_fails_closed_for_unresolvable_descriptor_target(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "import os\ntry:\n    os.truncate(987654, 0)\nexcept OSError:\n    pass",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is False
    assert evidence.write_attempts == ()
    assert evidence.error == (
        "installed write audit could not resolve a write target: os.truncate:unresolved-fd"
    )


def test_write_audit_ignores_non_filesystem_pipe_descriptors(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "import os\nread_fd, write_fd = os.pipe()\nwith os.fdopen(write_fd, 'wb') as stream:\n    stream.write(b'proof')\nos.close(read_fd)",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    assert evidence.write_attempts == ()
    assert evidence.error == ""


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

from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_write_audit import audited_program
from greenfield_matrix_write_audit import begin_installed_write_audit
import greenfield_matrix_write_audit as write_audit


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


@pytest.mark.parametrize("close_fds", [True, False])
def test_write_audit_records_child_process_diagnostic(tmp_path: Path, record_property, close_fds: bool) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "import subprocess, sys\n"
        f"subprocess.run([sys.executable, '-c', 'pass'], check=True, close_fds={close_fds!r})",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    record_property("subprocess_attempts", evidence.subprocess_attempts)
    record_property("audit_platform", sys.platform)
    record_property("close_fds", close_fds)
    # Popen may also emit its native spawn event; neither event is filtered.
    assert evidence.subprocess_attempts in (
        ("subprocess.Popen",),
        ("subprocess.Popen", "os.posix_spawn"),
    )


@pytest.mark.skipif(not hasattr(os, "posix_spawn"), reason="os.posix_spawn is unavailable")
def test_write_audit_records_direct_posix_spawn(tmp_path: Path, record_property) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed, evidence = _run_audited(
        repo_root,
        "import os, sys\n"
        "pid = os.posix_spawn(sys.executable, [sys.executable, '-c', 'pass'], os.environ)\n"
        "_, status = os.waitpid(pid, 0)\n"
        "assert os.waitstatus_to_exitcode(status) == 0",
    )

    assert completed.returncode == 0, completed.stderr
    assert evidence.active is True
    record_property("subprocess_attempts", evidence.subprocess_attempts)
    record_property("audit_platform", sys.platform)
    assert evidence.subprocess_attempts == ("os.posix_spawn",)
    assert evidence.write_attempts == ()
    assert evidence.error == ""


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


@pytest.mark.parametrize("spawn_child", [False, True])
def test_write_audit_drains_beyond_pipe_capacity_before_finish(
    tmp_path: Path, spawn_child: bool
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    paths = ("odylith/radar/source/first.json", "odylith/radar/source/second.json")
    for path in paths:
        target = repo_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}", encoding="utf-8")
    count = 4096
    program = (
        "import os, subprocess, sys\n"
        f"paths = {paths!r}\n"
        f"for index in range({count}):\n    os.chmod(paths[index % 2], 0o600)\n"
        + ("subprocess.run([sys.executable, '-c', 'pass'], check=True)\n" if spawn_child else "")
        + "print('child finished before audit.finish')\n"
    )
    audit = begin_installed_write_audit(repo_root=repo_root)
    descriptors = (audit.read_fd, audit.write_fd)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", audited_program(program)],
            cwd=repo_root,
            env={**os.environ, **audit.environment()},
            pass_fds=audit.pass_fds,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout == "child finished before audit.finish\n"
    finally:
        evidence = audit.finish()

    expected = tuple(f"os.chmod:{paths[index % 2]}" for index in range(count))
    assert sum(len(event) for event in expected) > 65536
    assert evidence.active is True
    assert evidence.error == ""
    assert evidence.write_attempts == expected
    if spawn_child:
        assert evidence.subprocess_attempts in (
            ("subprocess.Popen",), ("subprocess.Popen", "os.posix_spawn")
        )
    else:
        assert evidence.subprocess_attempts == ()
    _assert_retired(audit, descriptors)
    assert audit.finish() is evidence


def test_write_audit_preserves_failed_child_trace_and_retires_reader(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target = repo_root / "odylith/radar/source/record.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")
    audit = begin_installed_write_audit(repo_root=repo_root)
    descriptors = (audit.read_fd, audit.write_fd)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", audited_program(
                "import os, sys\nos.chmod('odylith/radar/source/record.json', 0o600)\n"
                "print('controlled child failure', file=sys.stderr)\nsys.exit(17)"
            )],
            cwd=repo_root,
            env={**os.environ, **audit.environment()},
            pass_fds=audit.pass_fds,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    finally:
        evidence = audit.finish()

    assert completed.returncode == 17
    assert completed.stderr == "controlled child failure\n"
    assert evidence.active is True
    assert evidence.write_attempts == ("os.chmod:odylith/radar/source/record.json",)
    assert evidence.subprocess_attempts == ()
    assert evidence.error == ""
    _assert_retired(audit, descriptors)
    assert audit.finish() is evidence


def test_write_audit_reader_failure_retains_prefix_and_fails_closed(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    original_read = os.read
    read_once = False

    def controlled_read(descriptor: int, count: int) -> bytes:
        nonlocal read_once
        if threading.current_thread().name == "greenfield-write-audit":
            if read_once:
                raise OSError("controlled reader failure")
            read_once = True
        return original_read(descriptor, count)

    monkeypatch.setattr(write_audit.os, "read", controlled_read)
    audit = begin_installed_write_audit(repo_root=repo_root)
    descriptors = (audit.read_fd, audit.write_fd)
    os.write(audit.write_fd, (
        b'{"kind":"ready","event":"ready"}\n'
        b'{"kind":"write","event":"open","path":"odylith/radar/source/record.json"}\n'
    ))
    evidence = audit.finish()

    assert evidence.active is False
    assert evidence.write_attempts == ("open:odylith/radar/source/record.json",)
    assert evidence.subprocess_attempts == ()
    assert evidence.error == "installed write audit reader failed: OSError: controlled reader failure"
    _assert_retired(audit, descriptors)
    assert audit.finish() is evidence


def test_write_audit_reader_failure_retains_complete_rows_before_partial_record(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    prefix = (
        b'{"kind":"ready","event":"ready"}\n'
        b'{"kind":"write","event":"open","path":"odylith/radar/source/kept.json"}\n'
        b'{"kind":"subprocess","event":"subprocess.Popen"}\n'
    )
    last_record = b'{"kind":"write","event":"open","path":"odylith/radar/source/incomplete.json"}\n'
    cap = len(prefix) + 20
    original_read = os.read
    first_read = None

    def controlled_read(descriptor: int, count: int) -> bytes:
        nonlocal first_read
        if threading.current_thread().name == "greenfield-write-audit":
            if first_read is not None:
                raise OSError("controlled reader failure after partial record")
            first_read = original_read(descriptor, min(count, cap))
            return first_read
        return original_read(descriptor, count)

    monkeypatch.setattr(write_audit.os, "read", controlled_read)
    audit = begin_installed_write_audit(repo_root=repo_root)
    descriptors = (audit.read_fd, audit.write_fd)
    os.write(audit.write_fd, prefix + last_record)
    evidence = audit.finish()

    assert first_read == (prefix + last_record)[:cap]
    assert evidence.active is False
    assert evidence.write_attempts == ("open:odylith/radar/source/kept.json",)
    assert evidence.subprocess_attempts == ("subprocess.Popen",)
    assert evidence.error == (
        "installed write audit reader failed: OSError: controlled reader failure after partial record"
    )
    _assert_retired(audit, descriptors)
    assert audit.finish() is evidence


def test_write_audit_normal_eof_partial_record_remains_malformed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    audit = begin_installed_write_audit(repo_root=repo_root)
    descriptors = (audit.read_fd, audit.write_fd)
    os.write(audit.write_fd, (
        b'{"kind":"ready","event":"ready"}\n'
        b'{"kind":"write","event":"open","path":"odylith/radar/source/kept.json"}\n'
        b'{"kind":"write","event":"open","path":"odylith/radar/source/incomplete'
    ))
    evidence = audit.finish()

    assert evidence.active is False
    assert evidence.error.startswith("invalid write-audit trace line 3:")
    assert "reader failed" not in evidence.error
    _assert_retired(audit, descriptors)
    assert audit.finish() is evidence


@pytest.mark.parametrize("fail_at", ["construction", "start"])
def test_write_audit_reader_start_failure_closes_both_descriptors(
    tmp_path: Path, monkeypatch, fail_at: str
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    original_pipe = os.pipe
    descriptors: tuple[int, int] = ()

    def owned_pipe() -> tuple[int, int]:
        nonlocal descriptors
        descriptors = original_pipe()
        return descriptors

    def fail_start(*_args, **_kwargs) -> None:
        raise RuntimeError("controlled reader start failure")

    monkeypatch.setattr(write_audit.os, "pipe", owned_pipe)
    if fail_at == "construction":
        monkeypatch.setattr(write_audit.threading, "Thread", fail_start)
    else:
        monkeypatch.setattr(write_audit.threading.Thread, "start", fail_start)
    with pytest.raises(RuntimeError, match="controlled reader start failure"):
        begin_installed_write_audit(repo_root=repo_root)
    for descriptor in descriptors:
        with pytest.raises(OSError) as error:
            os.fstat(descriptor)
        assert error.value.errno == errno.EBADF


def _assert_retired(audit, descriptors: tuple[int, int]) -> None:
    assert not audit._reader.is_alive()
    assert audit._trace_chunks == []
    assert audit.read_fd == audit.write_fd == -1
    for descriptor in descriptors:
        with pytest.raises(OSError) as error:
            os.fstat(descriptor)
        assert error.value.errno == errno.EBADF


def _run_audited(
    repo_root: Path, program: str, *, dashboard_opener=None,
) -> tuple[subprocess.CompletedProcess[str], object]:
    audit = begin_installed_write_audit(repo_root=repo_root, dashboard_opener=dashboard_opener)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", audited_program(program)],
            cwd=repo_root,
            env={**os.environ, **audit.environment()},
            pass_fds=audit.pass_fds,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    finally:
        evidence = audit.finish()
    return completed, evidence


@pytest.fixture
def closed_dashboard(tmp_path: Path, monkeypatch):
    from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store as pending
    from odylith.runtime.domain_intelligence import greenfield_post_confirm_handoff as handoff
    from odylith.runtime.surfaces import greenfield_host_confirmation as confirmation
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction
    import webbrowser

    repo = tmp_path / "repo"
    repo.mkdir()
    transaction = _transaction(repo_root=repo)
    path = pending.stage_pending_transaction(repo_root=repo, transaction=transaction)
    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")
    result = confirmation.handle_greenfield_decision(
        repo_root=repo, command="CONFIRM", transaction_hash=transaction.transaction_hash,
    )
    assert result["status"] == "CLOSED"
    journal = repo / ".odylith/runtime/greenfield/create-journal" / transaction.transaction_hash / "state.v1.json"
    record = json.loads(journal.read_bytes())
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    binding = {
        "repo_root": str(repo.resolve()),
        "transaction_hash": transaction.transaction_hash,
        "write_set_hash": record["repository_write_set_hash"],
        "publication_sha256": digest(repo / "odylith/index.html"),
        "navigation_source_sha256": digest(handoff.__file__),
        "confirmation_source_sha256": digest(confirmation.__file__),
        "webbrowser_source_sha256": digest(webbrowser.__file__),
        "os_source_sha256": digest(os.__file__),
        "shell_sha256": digest("/bin/sh"),
        "osascript_sha256": digest("/usr/bin/osascript") if sys.platform == "darwin" else "",
    }
    return repo, path, journal, binding


def _opener_program(path, binding, *, mutation="", process_event=""):
    # Genuine CLOSED fixture and canonical callback/stdlib code; replace only the
    # final OS spawn to observe its event without opening the operator's browser.
    return f'''
import io, subprocess, webbrowser
from odylith.runtime.surfaces import greenfield_host_confirmation as confirmation
from odylith.runtime.domain_intelligence import greenfield_post_confirm_handoff as handoff
for name in ("ODYLITH_NO_BROWSER", "CI", "GITHUB_ACTIONS", "BUILD_BUILDID", "BROWSER"):
    os.environ.pop(name, None)
os.environ["PATH"] = "/usr/bin:/bin"
class ObservedSpawn:
    def __init__(self, *args, **kwargs):
        self.stdin = io.StringIO()
        sys.audit("subprocess.Popen", "/bin/sh", ["/bin/sh", "-c", "osascript"], None, None)
        {process_event or 'pass'}
    def wait(self):
        return 0
subprocess.Popen = ObservedSpawn
webbrowser.register("audit-browser", None, webbrowser.MacOSXOSAScript("default"), preferred=True)
{mutation}
response = confirmation._confirm_pending_transaction(
    root=_root, transaction_path=Path({str(path)!r}), transaction_hash={binding['transaction_hash']!r})
assert response["status"] == "CLOSED", response
'''


@pytest.mark.skipif(sys.platform != "darwin", reason="only declared macOS opener is qualified")
def test_dashboard_opener_retains_process_count_from_real_closed_callback(closed_dashboard):
    repo, path, _journal, binding = closed_dashboard
    completed, evidence = _run_audited(repo, _opener_program(path, binding), dashboard_opener=binding)

    assert completed.returncode == 0, completed.stderr
    assert evidence.subprocess_attempts == ("subprocess.Popen",)
    assert write_audit.dashboard_opener_issues(evidence, expected=binding) == ()
    assert write_audit.dashboard_opener_issues(evidence)
    fact = evidence.process_observations[0]
    assert fact["argv"] == ["/bin/sh", "-c", "osascript"]
    assert fact["transaction_hash"] == binding["transaction_hash"]
    assert fact["journal_state"] == "closed" and fact["lifecycle_state"] == "CLOSED"
    assert fact["project_url"].endswith("/repository/odylith/index.html?tab=project")


@pytest.mark.skipif(sys.platform != "darwin", reason="only declared macOS opener is qualified")
@pytest.mark.parametrize("failure", ["not_closed", "wrong_source", "wrong_url", "missing_context", "extra_process", "secret_argv", "wrong_hash", "wrong_publication", "pin_race"])
def test_dashboard_opener_refuses_incomplete_or_other_process_work(closed_dashboard, failure):
    repo, path, journal, binding = closed_dashboard
    actual_binding = dict(binding)
    mutation = process_event = ""
    if failure == "wrong_source":
        binding = {**binding, "navigation_source_sha256": "0" * 64}
    if failure == "wrong_hash":
        binding = {**binding, "transaction_hash": "0" * 64}
    if failure == "wrong_publication":
        binding = {**binding, "publication_sha256": "0" * 64}
    if failure == "pin_race":
        mutation = f'''from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
original_pin=GreenfieldCommitJournal.pin_reviewed_generation
def changed_pin(**kwargs):
    pinned=original_pin(**kwargs)
    p=Path({str(journal)!r});p.write_bytes(p.read_bytes()+b" ")
    return pinned
GreenfieldCommitJournal.pin_reviewed_generation=changed_pin
'''
    if failure in {"not_closed", "wrong_url", "missing_context"}:
        record = json.loads(journal.read_bytes())
        navigation = {
            "dashboard_path": str(repo / ".odylith/runtime/greenfield/generations" / binding["write_set_hash"] / "repository/odylith/index.html"),
            "project_url": (repo / ".odylith/runtime/greenfield/generations" / binding["write_set_hash"] / "repository/odylith/index.html").as_uri() + "?tab=project",
        }
        mutation = f'saved_result=json.loads(Path({str(journal)!r}).read_bytes())["commit_result"]\nconfirmation.greenfield_create_commit.commit_greenfield_create_transaction = lambda **kw: saved_result\nhandoff.post_confirm_navigation = lambda *a, **kw: {navigation!r}\n'
        if failure == "not_closed":
            mutation += f'p=Path({str(journal)!r}); record=json.loads(p.read_bytes()); record["state"]="published"; p.write_text(json.dumps(record))\n'
        elif failure == "wrong_url":
            mutation += 'original=handoff.post_confirm_navigation\nhandoff.post_confirm_navigation=lambda *a,**kw: {{**original(), "project_url":"file:///wrong.html"}}\n'.replace('{{','{').replace('}}','}')
        else:
            mutation += 'handoff.open_committed_dashboard=lambda navigation: webbrowser.open(navigation["project_url"]) and {"status":"opened"}\n'
    if failure == "extra_process":
        process_event = 'sys.audit("subprocess.Popen", "/bin/sh", ["/bin/sh", "-c", "osascript"], None, None)'
    if failure == "secret_argv":
        process_event = 'sys.audit("subprocess.Popen", "/bad", ["/bad", "secret-must-not-leak"], None, {"TOKEN":"env-must-not-leak"})'
    completed, evidence = _run_audited(repo, _opener_program(path, actual_binding, mutation=mutation, process_event=process_event), dashboard_opener=binding)

    assert completed.returncode == 0, completed.stderr
    assert evidence.subprocess_attempts
    assert write_audit.dashboard_opener_issues(evidence)
    retained = repr(evidence)
    assert "secret-must-not-leak" not in retained and "env-must-not-leak" not in retained


def test_process_details_do_not_allow_unknown_real_subprocess(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    completed, evidence = _run_audited(tmp_path, "import subprocess,sys\nsubprocess.run([sys.executable,'-c','pass'],check=True)")
    assert completed.returncode == 0, completed.stderr
    assert write_audit.dashboard_opener_issues(evidence)
    assert evidence.process_observations[0]["classification"] == "unattributed"


def test_process_summary_failure_cannot_erase_real_popen_attempt(tmp_path):
    completed, evidence = _run_audited(tmp_path, '''
import subprocess, sys
class UnprintableExecutable:
    def __fspath__(self):
        return sys.executable
    def __repr__(self):
        raise ValueError("controlled argument summary failure")
try:
    child = subprocess.Popen([UnprintableExecutable(), "-c", "pass"])
    child.wait()
except ValueError:
    pass
''')
    assert completed.returncode == 0, completed.stderr
    assert evidence.active and not evidence.error
    assert evidence.subprocess_attempts[0] == "subprocess.Popen"
    assert len(evidence.process_observations) == len(evidence.subprocess_attempts)
    assert evidence.process_observations[0]["classification"] == "unattributed"
    assert write_audit.dashboard_opener_issues(evidence)


def test_process_details_fail_closed_for_missing_malformed_or_extra_rows():
    from dataclasses import replace
    evidence = write_audit._read_trace(b'{"kind":"ready"}\n{"kind":"subprocess","event":"subprocess.Popen"}\n')
    assert write_audit.dashboard_opener_issues(evidence)
    assert write_audit.dashboard_opener_issues(replace(evidence, process_observations=()))
    malformed = write_audit._read_trace(b'{"kind":"ready"}\n{"kind":"subprocess","process":"invalid"}\n')
    assert not malformed.active and malformed.error.startswith("invalid process detail")

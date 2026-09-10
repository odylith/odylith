"""Worker lifecycle and request retry contract characterization."""

from __future__ import annotations

import datetime as dt
import ctypes
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence.greenfield_repository_lock import greenfield_repository_lock
from odylith.runtime.surfaces import compass_standup_brief_maintenance_worker as worker
from odylith.runtime.surfaces import compass_standup_brief_maintenance as maintenance


def test_worker_env_absolutizes_relative_pythonpath(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", worker.os.pathsep.join(["src", "vendor", "/absolute/path"]))

    env = worker.worker_env()  # noqa: SLF001

    assert env["PYTHONPATH"].split(worker.os.pathsep) == [
        str(tmp_path / "src"),
        str(tmp_path / "vendor"),
        "/absolute/path",
    ]


def test_running_worker_records_loaded_epoch_not_later_source_epoch(tmp_path, monkeypatch):
    loaded = worker.LOADED_WORKER_EPOCH
    monkeypatch.setattr(worker.odylith_context_cache, "path_signature", lambda _path: {"changed": True})
    assert worker.current_worker_epoch() != loaded
    maintenance.run_pending_request(repo_root=tmp_path)
    state = worker.load_state(repo_root=tmp_path)
    assert state["worker_epoch"] == loaded
    assert not worker.worker_matches_current(state=state, python_bin=worker.worker_python_bin())


@pytest.mark.parametrize("dependency", [
    "compass_standup_brief_runtime_patch.py",
    "greenfield_managed_mutation_boundary.py",
    "greenfield_generation_store.py",
    "greenfield_repository_write_set.py",
    "greenfield_commit_journal.py",
])
def test_worker_epoch_tracks_loaded_publication_dependencies(monkeypatch, dependency):
    original = worker.current_worker_epoch()
    signature = worker.odylith_context_cache.path_signature
    monkeypatch.setattr(worker.odylith_context_cache, "path_signature",
                        lambda path: {"changed": True} if path.name == dependency else signature(path))
    assert worker.current_worker_epoch() != original


def test_request_completion_is_compare_current_not_newer_slot_pruning(tmp_path):
    original = {"version": "v1", "generated_utc": "old", "runtime_input_fingerprint": "old-input",
                "global": {"24h": {"fingerprint": "same-facts", "fact_packet": {"facts": [1]}}}}
    newer = {**original, "generated_utc": "new", "runtime_input_fingerprint": "new-input"}
    worker.replace_request(repo_root=tmp_path, payload=original)
    worker.replace_request(repo_root=tmp_path, payload=newer)
    assert worker.finish_request(repo_root=tmp_path, request=original, pending={}) == newer
    assert json.loads(worker.maintenance_request_path(repo_root=tmp_path).read_text()) == newer


def test_worker_discovery_requires_exact_module_and_repository_argument(tmp_path, monkeypatch):
    argv = (worker.worker_python_bin(), "-m", worker._WORKER_MODULE, "--repo-root", str(tmp_path))
    candidates = {
        201: argv,
        202: (*argv[:4], str(tmp_path) + "-other"),
        203: (argv[0], "-m", worker._WORKER_MODULE + "_extra", *argv[3:]),
        204: (argv[0], "unrelated.py", " ".join(argv)),
        205: (*argv, "--unrelated-option"),
    }
    output = "\n".join(f"{pid} {' '.join(args)}" for pid, args in candidates.items())
    monkeypatch.setattr(worker.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=output))
    monkeypatch.setattr(worker, "_native_process_argv", candidates.get)
    assert worker.maintenance_worker_pids(repo_root=tmp_path) == [201]

@pytest.mark.parametrize("command_matches", [False, True])
def test_worker_replacement_requires_confirmed_owned_process_exit(tmp_path, monkeypatch, command_matches):
    argv = (worker.worker_python_bin(), "-m", worker._WORKER_MODULE, "--repo-root",
            str(tmp_path) + ("" if command_matches else "-other"))
    monkeypatch.setattr(worker, "_native_process_argv", lambda _pid: argv)
    monkeypatch.setattr(worker, "pid_alive", lambda _pid: True)
    times = iter([0.0, 2.0])
    monkeypatch.setattr(worker.time, "monotonic", lambda: next(times))
    signals = []
    monkeypatch.setattr(worker.os, "kill", lambda pid, sig: signals.append((pid, sig)))
    assert worker.terminate_worker(201, repo_root=tmp_path) is False
    assert signals == ([(201, worker.signal.SIGTERM)] if command_matches else [])

def test_maybe_spawn_does_not_replace_an_owned_worker_that_has_not_exited(tmp_path, monkeypatch):
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    worker.replace_request(repo_root=tmp_path, payload={
        "global": {"24h": {"fingerprint": "facts", "fact_packet": {"facts": [1]}}},
    })
    monkeypatch.setattr(worker, "maintenance_worker_pids", lambda **_kwargs: [201])
    monkeypatch.setattr(worker, "terminate_worker", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("overlapping replacement"))
    assert worker.maybe_spawn_background(repo_root=tmp_path) == 0
    assert worker.maintenance_request_path(repo_root=tmp_path).exists()


def test_stale_state_pid_without_matching_actor_is_never_terminated(tmp_path, monkeypatch):
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    worker.replace_request(repo_root=tmp_path, payload={
        "global": {"24h": {"fingerprint": "facts", "fact_packet": {"facts": [1]}}},
    })
    worker.write_state(repo_root=tmp_path, state={"active_pid": 201})
    monkeypatch.setattr(worker, "pid_alive", lambda _pid: False)
    monkeypatch.setattr(worker, "maintenance_worker_pids", lambda **_kwargs: [])
    monkeypatch.setattr(worker, "terminate_worker", lambda *_args, **_kwargs: pytest.fail("unrelated PID"))
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *_args, **_kwargs: SimpleNamespace(pid=202))
    assert worker.maybe_spawn_background(repo_root=tmp_path) == 202


@pytest.mark.parametrize("failure", ["nonzero", "oserror"])
def test_unavailable_inventory_cannot_authorize_replacement(tmp_path, monkeypatch, failure):
    worker.replace_request(repo_root=tmp_path, payload={
        "global": {"24h": {"fingerprint": "facts", "fact_packet": {"facts": [1]}}},
    })
    worker.write_state(repo_root=tmp_path, state={"active_pid": 910001, "worker_epoch": "old"})
    request_bytes = worker.maintenance_request_path(repo_root=tmp_path).read_bytes()
    state_bytes = worker.maintenance_state_path(repo_root=tmp_path).read_bytes()
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    monkeypatch.setattr(worker, "pid_alive", lambda _pid: True)

    def unavailable(*_args, **_kwargs):
        if failure == "oserror":
            raise OSError("process inventory unavailable")
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(worker.subprocess, "run", unavailable)
    monkeypatch.setattr(worker, "terminate_worker", lambda *_args, **_kwargs: pytest.fail("unverified termination"))
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("unverified replacement"))
    assert worker.maybe_spawn_background(repo_root=tmp_path) == 0
    assert worker.maintenance_request_path(repo_root=tmp_path).read_bytes() == request_bytes
    assert worker.maintenance_state_path(repo_root=tmp_path).read_bytes() == state_bytes


def test_live_recorded_actor_missing_from_inventory_blocks_replacement(tmp_path, monkeypatch):
    worker.replace_request(repo_root=tmp_path, payload={
        "global": {"24h": {"fingerprint": "facts", "fact_packet": {"facts": [1]}}},
    })
    worker.write_state(repo_root=tmp_path, state={"active_pid": 201})
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    monkeypatch.setattr(worker, "pid_alive", lambda _pid: True)
    monkeypatch.setattr(worker, "maintenance_worker_pids", lambda **_kwargs: [])
    monkeypatch.setattr(worker, "terminate_worker", lambda *_args, **_kwargs: pytest.fail("unverified termination"))
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("unverified replacement"))
    assert worker.maybe_spawn_background(repo_root=tmp_path) == 0


@pytest.mark.parametrize("spaced_part", ["interpreter", "repository"])
def test_known_native_argv_preserves_spaced_paths(tmp_path, monkeypatch, spaced_part):
    interpreter = str(tmp_path / "runtime directory" / "python") if spaced_part == "interpreter" else worker.worker_python_bin()
    repo = tmp_path / "repository with spaces" if spaced_part == "repository" else tmp_path
    monkeypatch.setattr(worker, "worker_python_bin", lambda: interpreter)
    argv = (interpreter, "-m", worker._WORKER_MODULE, "--repo-root", str(repo))
    assert worker._matches_worker_argv(argv, repo_root=repo)


def test_unknown_executable_cannot_impersonate_worker_module(tmp_path):
    argv = ("/usr/bin/unrelated-program", "-m", worker._WORKER_MODULE, "--repo-root", str(tmp_path))
    assert not worker._matches_worker_argv(argv, repo_root=tmp_path)

def test_previous_interpreter_identity_reaches_inventory_and_stop_revalidation(tmp_path, monkeypatch):
    previous = str(tmp_path / "previous runtime" / "bin" / "python")
    argv = (previous, "-m", worker._WORKER_MODULE, "--repo-root", str(tmp_path))
    assert not worker._matches_worker_argv(argv, repo_root=tmp_path)
    assert worker._matches_worker_argv(argv, repo_root=tmp_path, previous_python_bin=previous)
    worker.replace_request(repo_root=tmp_path, payload={
        "global": {"24h": {"fingerprint": "facts", "fact_packet": {"facts": [1]}}},
    })
    worker.write_state(repo_root=tmp_path, state={
        "active_pid": 201, "worker_python_bin": previous, "worker_epoch": "previous-code",
    })
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    native_queries = []
    monkeypatch.setattr(worker.subprocess, "run",
                        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=f"201 {' '.join(argv)}"))

    def native_query(pid):
        native_queries.append(pid)
        return argv

    alive = [True]
    events = []
    monkeypatch.setattr(worker, "_native_process_argv", native_query)
    monkeypatch.setattr(worker, "pid_alive", lambda _pid: alive[0])

    def terminate(pid, sig):
        events.append((pid, sig))
        alive[0] = False

    def spawn(*_args, **_kwargs):
        assert alive[0] is False
        events.append("spawn")
        return SimpleNamespace(pid=202)

    monkeypatch.setattr(worker.os, "kill", terminate)
    monkeypatch.setattr(worker.subprocess, "Popen", spawn)
    assert worker.maybe_spawn_background(repo_root=tmp_path) == 202
    assert events == [(201, signal.SIGTERM), "spawn"]
    assert native_queries == [201, 201]

@pytest.mark.parametrize("suffix", ["-other", " --unknown", " --emit-output --unknown"])
def test_spaced_known_launch_still_rejects_other_roots_and_options(tmp_path, suffix):
    repo = tmp_path / "repository with spaces"
    argv = (worker.worker_python_bin(), "-m", worker._WORKER_MODULE, "--repo-root", str(repo))
    assert worker._matches_worker_argv((*argv, "--emit-output"), repo_root=repo)
    invalid = (*argv[:4], str(repo) + suffix) if suffix == "-other" else (*argv, *suffix.split())
    assert not worker._matches_worker_argv(invalid, repo_root=repo)

def test_successfully_empty_inventory_differs_from_unavailable_inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(worker.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=""))
    assert worker.maintenance_worker_pids(repo_root=tmp_path) == []
    monkeypatch.setattr(worker.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""))
    assert worker.maintenance_worker_pids(repo_root=tmp_path) is None


def _mock_macos_procargs(monkeypatch, raw, *, failure_call=0, advertised_size=None):
    calls = []

    class Query:
        def __call__(self, mib, count, output, size_pointer, new_value, new_size):
            calls.append(output is None)
            assert tuple(mib) == (1, 49, 201)
            assert count == 3 and new_value is None and new_size == 0
            if len(calls) == failure_call:
                return -1
            size = ctypes.cast(size_pointer, ctypes.POINTER(ctypes.c_size_t))
            if output is None:
                size.contents.value = len(raw) if advertised_size is None else advertised_size
            else:
                ctypes.memmove(output, raw, min(len(raw), size.contents.value))
                size.contents.value = len(raw)
            return 0

    monkeypatch.setattr(worker.ctypes, "CDLL", lambda *_args, **_kwargs: SimpleNamespace(sysctl=Query()))
    return calls


def _procargs_buffer(arguments, *, trailing=b"", argc=None):
    count = len(arguments) if argc is None else argc
    return (count.to_bytes(ctypes.sizeof(ctypes.c_int), sys.byteorder, signed=True)
            + b"/executable/path\0\0\0" + b"\0".join(arguments) + b"\0" + trailing)


def test_macos_sysctl_decodes_only_argc_and_never_trailing_environment(monkeypatch):
    arguments = (b"/runtime directory/python", b"-m", worker._WORKER_MODULE.encode(),
                 b"--repo-root", b"/repository --emit-output")
    raw = _procargs_buffer(arguments, trailing=b"SENSITIVE_ENV=do-not-decode\0opaque tail\xff")
    calls = _mock_macos_procargs(monkeypatch, raw)
    decoded = []

    def decode(value):
        decoded.append(value)
        return value.decode()

    monkeypatch.setattr(worker.os, "fsdecode", decode)
    assert worker._macos_process_argv(201) == tuple(value.decode() for value in arguments)
    assert decoded == list(arguments)
    assert calls == [True, False]


@pytest.mark.parametrize("raw", [
    b"\0", _procargs_buffer((b"python",), argc=0),
    _procargs_buffer((b"python",), argc=-1), _procargs_buffer((b"python",), argc=4097),
    (1).to_bytes(ctypes.sizeof(ctypes.c_int), sys.byteorder) + b"unterminated-executable",
    _procargs_buffer((b"python", b"-m"))[:-1],
])
def test_macos_malformed_procargs_is_unknown(monkeypatch, raw):
    _mock_macos_procargs(monkeypatch, raw)
    assert worker._macos_process_argv(201) is None


@pytest.mark.parametrize("failure_call,advertised_size", [
    (1, None), (2, None), (0, 0), (0, 1024 * 1024 + 1),
])
def test_macos_sysctl_failure_or_unbounded_size_is_unknown(monkeypatch, failure_call, advertised_size):
    _mock_macos_procargs(monkeypatch, _procargs_buffer((b"python",)),
                        failure_call=failure_call, advertised_size=advertised_size)
    assert worker._macos_process_argv(201) is None


@pytest.mark.parametrize("raw,expected", [
    (b"/runtime directory/python\0-m\0module\0--repo-root\0/repository --emit-output\0",
     ("/runtime directory/python", "-m", "module", "--repo-root", "/repository --emit-output")),
    (b"", None), (b"unterminated", None), (b"x" * (1024 * 1024 + 1), None),
])
def test_linux_nul_argv_reader_mocked_on_current_host(monkeypatch, raw, expected):
    original_open = Path.open
    reads = []

    class BoundedStream(io.BytesIO):
        def read(self, size):
            reads.append(size)
            return super().read(size)

    monkeypatch.setattr(worker.sys, "platform", "linux")
    monkeypatch.setattr(Path, "open", lambda path, *args, **kwargs:
                        BoundedStream(raw) if str(path) == "/proc/201/cmdline" else original_open(path, *args, **kwargs))
    assert worker._native_process_argv(201) == expected
    assert reads == [worker._MAX_PROCESS_ARGS_BYTES + 1]


def test_linux_unreadable_cmdline_and_unsupported_platform_are_unknown(monkeypatch):
    original_open = Path.open

    def open_path(path, *args, **kwargs):
        if str(path) == "/proc/201/cmdline":
            raise PermissionError("not observable")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_path)
    monkeypatch.setattr(worker.sys, "platform", "linux")
    assert worker._native_process_argv(201) is None
    monkeypatch.setattr(worker.sys, "platform", "unsupported")
    assert worker._native_process_argv(201) is None


def test_unknown_native_candidate_blocks_discovery_and_signal(tmp_path, monkeypatch):
    monkeypatch.setattr(worker.subprocess, "run", lambda *_args, **_kwargs:
                        SimpleNamespace(returncode=0, stdout=f"201 python -m {worker._WORKER_MODULE}"))
    monkeypatch.setattr(worker, "_native_process_argv", lambda _pid: None)
    monkeypatch.setattr(worker, "pid_alive", lambda _pid: True)
    monkeypatch.setattr(worker.os, "kill", lambda *_args: pytest.fail("signal without native argv"))
    assert worker.maintenance_worker_pids(repo_root=tmp_path) is None
    assert worker.terminate_worker(201, repo_root=tmp_path) is False


def test_native_identity_change_before_sigterm_blocks_replacement(tmp_path, monkeypatch):
    argv = (worker.worker_python_bin(), "-m", worker._WORKER_MODULE, "--repo-root", str(tmp_path))
    worker.replace_request(repo_root=tmp_path, payload={
        "global": {"24h": {"fingerprint": "facts", "fact_packet": {"facts": [1]}}},
    })
    observations = iter([argv, (*argv[:4], str(tmp_path) + " --emit-output")])
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    monkeypatch.setattr(worker.subprocess, "run", lambda *_args, **_kwargs:
                        SimpleNamespace(returncode=0, stdout=f"201 {' '.join(argv)}"))
    monkeypatch.setattr(worker, "_native_process_argv", lambda _pid: next(observations))
    monkeypatch.setattr(worker, "pid_alive", lambda pid: pid > 0)
    monkeypatch.setattr(worker.os, "kill", lambda *_args: pytest.fail("identity changed before signal"))
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("old worker unverified"))
    assert worker.maybe_spawn_background(repo_root=tmp_path) == 0


@pytest.mark.parametrize("root_contains_flag", [False, True])
def test_actual_child_with_spaced_executable_and_repository_is_identified_and_stopped(tmp_path, monkeypatch, root_contains_flag):
    from tests.unit.runtime.test_compass_maintenance_custody import _cache, _fixture

    plain_root = tmp_path / "repository with spaces"
    suffixed_root = tmp_path / "repository with spaces --emit-output"
    repo, other = (suffixed_root, plain_root) if root_contains_flag else (plain_root, suffixed_root)
    executable = tmp_path / "runtime directory" / "python"
    executable.parent.mkdir()
    executable.symlink_to(sys.executable)
    request, brief = _fixture(repo)
    _cache(repo, request, brief)
    monkeypatch.setattr(worker, "worker_python_bin", lambda: str(executable))
    with greenfield_repository_lock(repo):
        child = subprocess.Popen(
            [str(executable), "-m", "odylith.runtime.surfaces.compass_standup_brief_maintenance",
             "--repo-root", str(repo)] + ([] if root_contains_flag else ["--emit-output"]),
            env=worker.worker_env(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 5.0
            state = {}
            while time.monotonic() < deadline and child.poll() is None:
                state = worker.load_state(repo_root=repo)
                if state.get("entries", {}).get("global:24h", {}).get("status") == "ready":
                    break
                time.sleep(0.02)
            assert child.poll() is None
            assert state["active_pid"] == child.pid
            observed = worker._native_process_argv(child.pid)
            assert observed is not None
            assert observed[4] == str(repo)
            assert worker._matches_worker_argv(observed, repo_root=repo)
            assert not worker._matches_worker_argv(observed, repo_root=other)
            assert worker.terminate_worker(child.pid, repo_root=other) is False
            assert child.poll() is None
            # Only this private child is polled and reaped by its owning parent.
            monkeypatch.setattr(worker, "pid_alive", lambda pid: pid == child.pid and child.poll() is None)
            assert worker.terminate_worker(child.pid, repo_root=repo)
            assert child.wait(timeout=2) == -signal.SIGTERM
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=2)
    assert json.loads(worker.maintenance_request_path(repo_root=repo).read_text()) == request


@pytest.mark.parametrize("status,delay,change_at,expected_next_run", [
    ("changed", 3600.0, None, 3600.0),
    ("unchanged", 3600.0, 10.0, 10.0),
    ("busy", 5.0, None, 5.0),
])
def test_main_polls_request_cheaply_until_retry_due_or_foreground_change(
    tmp_path, monkeypatch, status, delay, change_at, expected_next_run,
):
    request = {"global": {"24h": {"fingerprint": "facts", "fact_packet": {"facts": [1]}}}}
    worker.replace_request(repo_root=tmp_path, payload=request)
    elapsed = [0.0]
    runs = []

    def run(**_kwargs):
        runs.append(elapsed[0])
        return {"request_retained": len(runs) == 1, "next_retry_delay_seconds": delay,
                "publication_status": status,
                "request_identity": worker.odylith_context_cache.fingerprint_payload(request)}

    def sleep(seconds):
        assert seconds <= 5.0
        elapsed[0] += seconds
        if change_at is not None and elapsed[0] == change_at:
            worker.replace_request(repo_root=tmp_path, payload={**request, "generated_utc": "newer"})

    monkeypatch.setattr(maintenance, "run_pending_request", run)
    monkeypatch.setattr(maintenance.time, "monotonic", lambda: elapsed[0])
    monkeypatch.setattr(maintenance.time, "sleep", sleep)
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: pytest.fail("provider poll"))
    assert maintenance.main(["--repo-root", str(tmp_path)]) == 0
    assert runs == [0.0, expected_next_run]


def test_maybe_spawn_background_stays_quiet_under_pytest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request_path = worker.maintenance_request_path(repo_root=tmp_path)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-09T00:00:00Z",
                "runtime_input_fingerprint": "runtime-fp",
                "global": {"24h": {"fingerprint": "global-fp", "fact_packet": {}}},
                "scoped": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/unit/runtime/test_compass.py::test_example (call)")

    assert worker.maybe_spawn_background(repo_root=tmp_path) == 0
    assert not worker.maintenance_state_path(repo_root=tmp_path).exists()


def test_pending_request_delay_seconds_waits_until_retry_window(tmp_path: Path) -> None:
    state_entries = {
        "scoped:24h:B-021": {
            "fingerprint": "scope-fp",
            "status": "failed",
            "next_retry_utc": "2099-01-01T00:05:00Z",
        }
    }
    request = {
        "version": "v1",
        "generated_utc": "2026-04-09T00:00:00Z",
        "runtime_input_fingerprint": "runtime-fp",
        "scoped": {
            "24h": {
                "B-021": {
                    "fingerprint": "scope-fp",
                    "fact_packet": {"scope_id": "B-021"},
                }
            }
        },
    }

    delay = worker.pending_request_delay_seconds(  # noqa: SLF001
        request=request,
        state_entries=state_entries,
    )

    assert delay is not None
    assert delay > 0


def test_pending_request_payload_keeps_all_unresolved_scoped_entries() -> None:
    request = {
        "version": "v1",
        "generated_utc": "2026-04-09T00:00:00Z",
        "runtime_input_fingerprint": "runtime-fp",
        "scoped": {
            "24h": {
                "B-001": {
                    "fingerprint": "fp-B-001",
                    "fact_packet": {"scope_id": "B-001"},
                },
                "B-002": {
                    "fingerprint": "fp-B-002",
                    "fact_packet": {"scope_id": "B-002"},
                },
                "B-003": {
                    "fingerprint": "fp-B-003",
                    "fact_packet": {"scope_id": "B-003"},
                },
                "B-004": {
                    "fingerprint": "fp-B-004",
                    "fact_packet": {"scope_id": "B-004"},
                },
                "B-005": {
                    "fingerprint": "fp-B-005",
                    "fact_packet": {"scope_id": "B-005"},
                },
                "B-006": {
                    "fingerprint": "fp-B-006",
                    "fact_packet": {"scope_id": "B-006"},
                },
            }
        },
    }
    state_entries = {
        "scoped:24h:B-006": {
            "fingerprint": "stale-B-006",
            "status": "failed",
            "attempt_count": 2,
        }
    }

    payload = worker.pending_request_payload(  # noqa: SLF001
        request=request,
        state_entries=state_entries,
    )

    assert list(payload["scoped"]["24h"]) == ["B-001", "B-002", "B-003", "B-004", "B-005", "B-006"]


def test_maybe_spawn_background_starts_worker_once(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    repo_root = tmp_path
    request_path = worker.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "global": {
                    "24h": {
                        "fingerprint": "global-fp",
                        "fact_packet": {"scope_id": "global-24h"},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    class _FakePopen:
        def __init__(self, command: list[str]) -> None:
            self.pid = 4321
            calls.append(command)

    monkeypatch.setattr(
        worker.subprocess,
        "Popen",
        lambda command, **_kwargs: _FakePopen(list(command)),
    )
    monkeypatch.setattr(worker, "maintenance_worker_pids", lambda **_kwargs: [])

    pid = worker.maybe_spawn_background(repo_root=repo_root)
    state = json.loads(worker.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))

    assert pid == 4321
    assert calls and "odylith.runtime.surfaces.compass_standup_brief_maintenance" in calls[0]
    assert state["active_pid"] == 4321
    assert state["worker_epoch"]
    assert state["worker_python_bin"]


def test_maybe_spawn_background_restarts_stale_worker_when_worker_epoch_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    repo_root = tmp_path
    request_path = worker.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "global": {
                    "24h": {
                        "fingerprint": "global-fp",
                        "fact_packet": {"scope_id": "global-24h"},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    worker.maintenance_state_path(repo_root=repo_root).write_text(
        json.dumps(
            {
                "version": "v1",
                "active_pid": 1111,
                "worker_epoch": "stale-epoch",
                "worker_python_bin": "/tmp/old-python",
                "entries": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(worker, "pid_alive", lambda pid: int(pid) == 1111)
    terminated: list[int] = []
    monkeypatch.setattr(worker, "terminate_worker", lambda pid, **_kwargs: terminated.append(int(pid)) or True)
    monkeypatch.setattr(worker, "current_worker_epoch", lambda **_kwargs: "fresh-epoch")
    monkeypatch.setattr(worker, "worker_python_bin", lambda: "/tmp/fresh-python")

    calls: list[list[str]] = []

    class _FakePopen:
        def __init__(self, command: list[str]) -> None:
            self.pid = 4321
            calls.append(command)

    monkeypatch.setattr(
        worker.subprocess,
        "Popen",
        lambda command, **_kwargs: _FakePopen(list(command)),
    )
    monkeypatch.setattr(worker, "maintenance_worker_pids", lambda **_kwargs: [1111])

    pid = worker.maybe_spawn_background(repo_root=repo_root)
    state = json.loads(worker.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))

    assert pid == 4321
    assert terminated == [1111]
    assert calls and calls[0][0] == "/tmp/fresh-python"
    assert state["active_pid"] == 4321
    assert state["worker_epoch"] == "fresh-epoch"
    assert state["worker_python_bin"] == "/tmp/fresh-python"


def test_maybe_spawn_background_terminates_orphan_worker_before_spawning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    repo_root = tmp_path
    request_path = worker.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "global": {
                    "24h": {
                        "fingerprint": "global-fp",
                        "fact_packet": {"scope_id": "global-24h"},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(worker, "maintenance_worker_pids", lambda **_kwargs: [1111])
    monkeypatch.setattr(worker, "current_worker_epoch", lambda **_kwargs: "fresh-epoch")
    monkeypatch.setattr(worker, "worker_python_bin", lambda: "/tmp/fresh-python")

    terminated: list[int] = []
    monkeypatch.setattr(worker, "terminate_worker", lambda pid, **_kwargs: terminated.append(int(pid)) or True)

    calls: list[list[str]] = []

    class _FakePopen:
        def __init__(self, command: list[str]) -> None:
            self.pid = 4321
            calls.append(command)

    monkeypatch.setattr(
        worker.subprocess,
        "Popen",
        lambda command, **_kwargs: _FakePopen(list(command)),
    )

    pid = worker.maybe_spawn_background(repo_root=repo_root)
    state = json.loads(worker.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))

    assert pid == 4321
    assert terminated == [1111]
    assert calls and calls[0][0] == "/tmp/fresh-python"
    assert state["active_pid"] == 4321


def test_maybe_spawn_background_ignores_empty_or_malformed_requests(tmp_path: Path) -> None:
    repo_root = tmp_path
    request_path = worker.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "global": {"24h": {}},
                "scoped": {"24h": {"B-021": {"fingerprint": "", "fact_packet": {}}}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert worker.maybe_spawn_background(repo_root=repo_root) == 0

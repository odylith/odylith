from __future__ import annotations

import contextlib
import io
import json
import signal
import socket
import threading
from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine as engine
from odylith.runtime.context_engine import odylith_context_engine_store as store


def test_read_daemon_transport_rejects_dead_owner(tmp_path: Path, monkeypatch) -> None:
    socket_path = engine.store.socket_path(repo_root=tmp_path)
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.write_text(
        json.dumps(
            {
                "transport": "tcp",
                "host": "127.0.0.1",
                "port": 43123,
                "pid": 321,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pid_path = engine.store.pid_path(repo_root=tmp_path)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("321\n", encoding="utf-8")
    monkeypatch.setattr(engine, "_pid_alive", lambda pid: False)

    assert engine._read_daemon_transport(repo_root=tmp_path) is None  # noqa: SLF001


def test_read_daemon_transport_rejects_non_loopback_tcp_host(tmp_path: Path, monkeypatch) -> None:
    socket_path = engine.store.socket_path(repo_root=tmp_path)
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.write_text(
        json.dumps(
            {
                "transport": "tcp",
                "host": "10.0.0.8",
                "port": 43123,
                "pid": 321,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pid_path = engine.store.pid_path(repo_root=tmp_path)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("321\n", encoding="utf-8")
    monkeypatch.setattr(engine, "_pid_alive", lambda pid: True)

    assert engine._read_daemon_transport(repo_root=tmp_path) is None  # noqa: SLF001


def test_store_runtime_daemon_transport_rejects_non_loopback_tcp_host(tmp_path: Path, monkeypatch) -> None:
    socket_path = store.socket_path(repo_root=tmp_path)
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.write_text(
        json.dumps(
            {
                "transport": "tcp",
                "host": "192.168.1.5",
                "port": 8123,
                "pid": 5150,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pid_path = store.pid_path(repo_root=tmp_path)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("5150\n", encoding="utf-8")
    monkeypatch.setattr(store, "_runtime_daemon_pid_alive", lambda pid: True)

    assert store.runtime_daemon_transport(repo_root=tmp_path) is None


def test_spawn_daemon_background_waits_for_existing_starting_daemon(tmp_path: Path, monkeypatch) -> None:
    availability = iter([False, False, True])
    monkeypatch.setattr(engine.odylith_context_cache, "advisory_lock", lambda **kwargs: contextlib.nullcontext())
    monkeypatch.setattr(engine, "_daemon_socket_available", lambda **kwargs: next(availability))
    monkeypatch.setattr(engine, "_daemon_owner_pid", lambda **kwargs: 4242)
    monkeypatch.setattr(engine, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(engine.time, "sleep", lambda _: None)
    monkeypatch.setattr(engine.store, "record_runtime_timing", lambda **kwargs: None)

    def _unexpected_popen(*args, **kwargs):  # noqa: ANN001, ANN202
        raise AssertionError("autospawn should not launch a second daemon when one is already alive")

    monkeypatch.setattr(engine.subprocess, "Popen", _unexpected_popen)

    assert engine._spawn_daemon_background(repo_root=tmp_path, scope="full") is True  # noqa: SLF001


def test_spawn_daemon_background_reaps_failed_startup_process(tmp_path: Path, monkeypatch) -> None:
    class _FakeProcess:
        def __init__(self) -> None:
            self.pid = 5150
            self._alive = True

        def poll(self) -> int | None:
            return None if self._alive else 0

        def wait(self, timeout: float | None = None) -> int:
            _ = timeout
            if self._alive:
                raise engine.subprocess.TimeoutExpired(cmd="odylith context-engine", timeout=2)
            return 0

        def terminate(self) -> None:
            self._alive = False

        def kill(self) -> None:
            self._alive = False

    process = _FakeProcess()
    kill_calls: list[tuple[int, int]] = []
    clear_calls: list[Path] = []
    runtime_timing: list[dict[str, object]] = []

    monkeypatch.setattr(engine.odylith_context_cache, "advisory_lock", lambda **kwargs: contextlib.nullcontext())
    monkeypatch.setattr(engine, "_daemon_socket_available", lambda **kwargs: False)
    monkeypatch.setattr(engine, "_daemon_owner_pid", lambda **kwargs: None)
    monkeypatch.setattr(engine.time, "sleep", lambda _: None)
    monkeypatch.setattr(engine.store, "record_runtime_timing", lambda **kwargs: runtime_timing.append(kwargs))
    monkeypatch.setattr(engine, "_clear_stale_daemon_artifacts", lambda **kwargs: clear_calls.append(kwargs["repo_root"]))
    monkeypatch.setattr(engine.subprocess, "Popen", lambda *args, **kwargs: process)

    def _fake_killpg(pid: int, sig: int) -> None:
        kill_calls.append((pid, sig))
        process._alive = False

    monkeypatch.setattr(engine.os, "killpg", _fake_killpg)

    assert engine._spawn_daemon_background(repo_root=tmp_path, scope="full") is False  # noqa: SLF001
    assert clear_calls == [tmp_path, tmp_path]
    assert kill_calls == [(5150, signal.SIGTERM)]
    assert runtime_timing[-1]["metadata"]["startup_reaped"] is True


def test_daemon_request_includes_auth_token_for_socket_transport(tmp_path: Path, monkeypatch) -> None:
    class _FakeSocket:
        def __init__(self) -> None:
            self.sent = b""
            self.target = None
            self._responses = [
                json.dumps({"ok": True, "payload": {"status": "ok"}}).encode("utf-8"),
                b"",
            ]

        def settimeout(self, _value: float) -> None:
            return None

        def connect(self, target) -> None:  # noqa: ANN001
            self.target = target

        def sendall(self, data: bytes) -> None:
            self.sent += data

        def shutdown(self, _how: int) -> None:
            return None

        def recv(self, _size: int) -> bytes:
            return self._responses.pop(0)

        def close(self) -> None:
            return None

    fake_socket = _FakeSocket()
    monkeypatch.setattr(engine, "_read_daemon_transport", lambda **kwargs: {"transport": "tcp", "host": "127.0.0.1", "port": 8123})
    monkeypatch.setattr(engine, "_read_daemon_metadata", lambda **kwargs: {"auth_token": "secret-token"})
    monkeypatch.setattr(engine.store, "record_runtime_timing", lambda **kwargs: None)
    monkeypatch.setattr(engine.socket, "socket", lambda *args, **kwargs: fake_socket)

    payload = engine._daemon_request(  # noqa: SLF001
        repo_root=tmp_path,
        command="status",
        payload={"check": True},
        required=True,
    )

    assert payload == {"status": "ok"}
    rendered = json.loads(fake_socket.sent.decode("utf-8").strip())
    assert rendered["auth_token"] == "secret-token"
    assert rendered["command"] == "status"
    assert rendered["payload"] == {"check": True}


def test_store_daemon_request_includes_auth_token_for_socket_transport(tmp_path: Path, monkeypatch) -> None:
    class _FakeSocket:
        def __init__(self) -> None:
            self.sent = b""
            self.target = None
            self._responses = [
                json.dumps({"ok": True, "payload": {"status": "ok"}}).encode("utf-8"),
                b"",
            ]

        def settimeout(self, _value: float) -> None:
            return None

        def connect(self, target) -> None:  # noqa: ANN001
            self.target = target

        def sendall(self, data: bytes) -> None:
            self.sent += data

        def shutdown(self, _how: int) -> None:
            return None

        def recv(self, _size: int) -> bytes:
            return self._responses.pop(0)

        def close(self) -> None:
            return None

    fake_socket = _FakeSocket()
    monkeypatch.setattr(
        store,
        "runtime_daemon_transport",
        lambda **kwargs: {"transport": "tcp", "host": "127.0.0.1", "port": 8123, "pid": 5150},
    )
    monkeypatch.setattr(store, "_read_runtime_daemon_metadata", lambda **kwargs: {"auth_token": "secret-token"})
    monkeypatch.setattr(store, "record_runtime_timing", lambda **kwargs: None)
    monkeypatch.setattr(
        store,
        "runtime_request_namespace_from_payload",
        lambda **kwargs: {
            "workspace_key": "workspace",
            "request_namespace": "request-ns",
            "session_namespaced": False,
            "session_namespace": "",
            "working_tree_scope": "repo",
            "session_id_present": False,
            "claim_path_count": 0,
            "changed_path_count": 0,
        },
    )
    monkeypatch.setattr(store.socket, "socket", lambda *args, **kwargs: fake_socket)

    payload = store.request_runtime_daemon(
        repo_root=tmp_path,
        command="status",
        payload={"check": True},
        required=True,
    )

    assert payload == (
        {"status": "ok"},
        {
            "source": "workspace_daemon",
            "transport": "tcp",
            "workspace_daemon_reused": True,
            "workspace_key": "workspace",
            "request_namespace": "request-ns",
            "session_namespaced": False,
            "session_namespace": "",
            "working_tree_scope": "repo",
            "session_id_present": False,
            "claim_path_count": 0,
            "changed_path_count": 0,
        },
    )
    rendered = json.loads(fake_socket.sent.decode("utf-8").strip())
    assert rendered["auth_token"] == "secret-token"
    assert rendered["command"] == "status"
    assert rendered["payload"] == {"check": True}


def test_runtime_request_handler_ignores_broken_pipe_on_response_write(tmp_path: Path, monkeypatch) -> None:
    handler = engine._RuntimeRequestHandler.__new__(engine._RuntimeRequestHandler)  # noqa: SLF001
    handler.rfile = io.BytesIO(
        (json.dumps({"command": "status", "payload": {"check": True}, "auth_token": "secret-token"}) + "\n").encode(
            "utf-8"
        )
    )

    class _BrokenPipeWriter:
        def write(self, _data: bytes) -> None:
            raise BrokenPipeError("client disconnected")

    handler.wfile = _BrokenPipeWriter()
    handler.server = type("_Server", (), {"repo_root": tmp_path, "auth_token": "secret-token"})()

    dispatched: list[dict[str, object]] = []
    monkeypatch.setattr(
        engine,
        "_dispatch_daemon_command",
        lambda **kwargs: dispatched.append(dict(kwargs)) or {"status": "ok"},  # noqa: ANN001
    )

    handler.handle()

    assert dispatched == [
        {
            "repo_root": tmp_path,
            "command": "status",
            "payload": {"check": True},
        }
    ]


def test_runtime_request_handler_rejects_invalid_auth_token(tmp_path: Path) -> None:
    server = engine._RuntimeTcpRequestServer(  # noqa: SLF001
        repo_root=tmp_path,
        host="127.0.0.1",
        port=0,
        auth_token="expected-token",
    )
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        with socket.create_connection(server.server_address, timeout=2) as sock:
            sock.sendall(
                json.dumps(
                    {
                        "command": "status",
                        "payload": {},
                        "auth_token": "wrong-token",
                    }
                ).encode("utf-8")
                + b"\n"
            )
            sock.shutdown(socket.SHUT_WR)
            response = json.loads(sock.recv(65536).decode("utf-8"))
    finally:
        server.server_close()
        thread.join(timeout=2)

    assert response["ok"] is False
    assert "invalid auth token" in response["error"]


def test_run_stop_escalates_if_daemon_survives_sigterm(tmp_path: Path, monkeypatch, capsys) -> None:  # noqa: ANN001
    alive = {"value": True}
    kill_calls: list[int] = []
    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)

    monkeypatch.setattr(engine, "_read_pid", lambda path: 5150)
    monkeypatch.setattr(engine, "_pid_alive", lambda pid: bool(alive["value"]))
    monkeypatch.setattr(engine.time, "sleep", lambda _: None)
    monkeypatch.setattr(engine.odylith_context_cache, "write_text_if_changed", lambda **kwargs: None)
    monkeypatch.setattr(engine, "_clear_stale_daemon_artifacts", lambda **kwargs: None)

    def _fake_kill(pid: int, sig: int) -> None:
        kill_calls.append(sig)
        if sig == kill_signal:
            alive["value"] = False

    monkeypatch.setattr(engine.os, "kill", _fake_kill)

    rc = engine._run_stop(repo_root=tmp_path)  # noqa: SLF001

    assert rc == 0
    assert kill_calls[0] == signal.SIGTERM
    assert kill_calls[-1] == kill_signal
    assert "stop requested for pid 5150" in capsys.readouterr().out


def test_watchman_runtime_watcher_close_kills_stubborn_process() -> None:
    class _FakeProcess:
        def __init__(self) -> None:
            self.stdin = io.StringIO()
            self.stdout = io.StringIO()
            self.stderr = io.StringIO()
            self._alive = True
            self.terminated = False
            self.killed = False

        def poll(self) -> int | None:
            return None if self._alive else 0

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float | None = None) -> int:
            _ = timeout
            if self._alive:
                raise engine.subprocess.TimeoutExpired(cmd="watchman", timeout=2)
            return 0

        def kill(self) -> None:
            self.killed = True
            self._alive = False

    watcher = engine._WatchmanRuntimeWatcher.__new__(engine._WatchmanRuntimeWatcher)  # noqa: SLF001
    watcher._watch_root = "/tmp/repo"  # type: ignore[attr-defined]
    watcher._subscription = "sub-1"  # type: ignore[attr-defined]
    watcher._process = _FakeProcess()  # type: ignore[attr-defined]

    watcher.close()

    assert watcher._process.terminated is True  # type: ignore[attr-defined]
    assert watcher._process.killed is True  # type: ignore[attr-defined]

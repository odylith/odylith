"""Run one cancellable schema-constrained semantic host stage."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Event
import time
from typing import Any


class HostStageCancelled(RuntimeError):
    """Raised when an upstream typed decision makes a host stage unnecessary."""


class HostStageTimeout(RuntimeError):
    """Raised when a host stage exhausts its explicit execution budget."""


def run_structured_host(
    *, schema: Mapping[str, Any], prompt: str, model: str, reasoning_effort: str,
    budget_seconds: int, temporary_prefix: str, cancel_event: Event | None = None,
    host_profile: str = "codex", host_binary: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Run one isolated provider turn with exact timeout and cancellation."""

    host = str(host_profile or "").strip()
    if host not in {"codex", "claude"}:
        raise RuntimeError("unsupported Greenfield semantic host profile")
    binary = str(host_binary or shutil.which(host) or "").strip()
    if not binary:
        raise RuntimeError(f"{host.title()} host binary is unavailable")
    started_ns = time.monotonic_ns()
    with tempfile.TemporaryDirectory(prefix=temporary_prefix) as temporary:
        working_root = Path(temporary)
        schema_path = working_root / "output-schema.json"
        stdout_path = working_root / "stdout.jsonl"
        stderr_path = working_root / "stderr.txt"
        schema_path.write_text(_json(schema), encoding="utf-8")
        command = _host_command(
            host_profile=host,
            binary=binary,
            working_root=working_root,
            schema_path=schema_path,
            schema=schema,
            prompt=prompt,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_file:
            process = subprocess.Popen(
                command,
                cwd=working_root,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
            )
            _wait(process, budget_seconds=budget_seconds, cancel_event=cancel_event)
        stdout = stdout_path.read_text(encoding="utf-8")
        stderr = stderr_path.read_text(encoding="utf-8")
    wall_ms = elapsed_ms(started_ns)
    if process.returncode != 0:
        raise RuntimeError(
            f"{host.title()} host failed with exit {process.returncode}: "
            f"{_host_failure(host, stdout, stderr)}"
        )
    candidate, usage = (
        _codex_result(stdout) if host == "codex" else _claude_result(stdout)
    )
    return candidate, usage, wall_ms


def _host_command(
    *, host_profile: str, binary: str, working_root: Path, schema_path: Path,
    schema: Mapping[str, Any], prompt: str, model: str, reasoning_effort: str,
) -> list[str]:
    if host_profile == "claude":
        return [
            binary,
            "--print",
            "--safe-mode",
            "--disable-slash-commands",
            "--tools",
            "",
            "--no-session-persistence",
            "--permission-mode",
            "dontAsk",
            "--model",
            model,
            "--effort",
            reasoning_effort,
            "--json-schema",
            _json(schema),
            "--output-format",
            "json",
            prompt,
        ]
    return [
        binary,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--cd",
        str(working_root),
        "--model",
        model,
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
        "--json",
        "--output-schema",
        str(schema_path),
        prompt,
    ]


def _wait(process: subprocess.Popen[str], *, budget_seconds: int, cancel_event: Event | None) -> None:
    deadline = time.monotonic() + budget_seconds
    while process.poll() is None:
        if cancel_event is not None and cancel_event.wait(timeout=0.05):
            _stop(process)
            raise HostStageCancelled("semantic host stage cancelled by upstream typed decision")
        if time.monotonic() >= deadline:
            _stop(process)
            raise HostStageTimeout(
                f"host exceeded its {budget_seconds}-second stage budget"
            )
        if cancel_event is None:
            time.sleep(0.05)


def _stop(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def _codex_result(stdout: str) -> tuple[dict[str, Any], dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    usage: dict[str, Any] | None = None
    for line in stdout.splitlines():
        if not line.strip():
            continue
        event = _mapping(json.loads(line), "Codex event")
        event_type = str(event.get("type") or "")
        if event_type == "item.completed":
            item = _mapping(event.get("item"), "Codex item")
            if item.get("type") == "agent_message":
                messages.append(_mapping(json.loads(str(item.get("text") or "")), "candidate"))
            elif item.get("type") != "reasoning":
                raise RuntimeError("Codex host emitted a forbidden event")
        elif event_type == "turn.completed":
            usage = _mapping(event.get("usage"), "Codex usage")
        elif event_type in {"thread.started", "turn.started", "item.started", "item.updated"}:
            continue
        elif event_type in {"error", "turn.failed"}:
            raise RuntimeError(f"Codex host emitted {event_type}: {_json(event)}")
        else:
            raise RuntimeError(f"Codex host emitted unsupported event: {event_type}")
    if len(messages) != 1 or usage is None:
        raise RuntimeError("Codex host did not emit one candidate and usage receipt")
    return messages[0], usage


def _claude_result(stdout: str) -> tuple[dict[str, Any], dict[str, Any]]:
    envelope = _mapping(json.loads(stdout), "Claude result envelope")
    if envelope.get("is_error") is True or envelope.get("subtype") not in {
        None,
        "success",
    }:
        detail = str(envelope.get("result") or "unsuccessful structured result").strip()
        raise RuntimeError(f"Claude host returned an unsuccessful result: {detail}")
    return (
        _mapping(envelope.get("structured_output"), "Claude structured output"),
        _mapping(envelope.get("usage"), "Claude usage receipt"),
    )


def _codex_failure(stdout: str, stderr: str) -> str:
    for line in reversed(stdout.splitlines()):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, Mapping) and event.get("type") in {"error", "turn.failed"}:
            return _json(event)
    return stderr.strip() or "host exited without a structured failure receipt"


def _host_failure(host_profile: str, stdout: str, stderr: str) -> str:
    if host_profile == "codex":
        return _codex_failure(stdout, stderr)
    try:
        envelope = _mapping(json.loads(stdout), "Claude result envelope")
    except (json.JSONDecodeError, RuntimeError):
        return stderr.strip() or stdout.strip() or "host exited without a structured failure receipt"
    return str(envelope.get("result") or "").strip() or stderr.strip() or _json(envelope)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def elapsed_ms(started_ns: int) -> int:
    """Return positive elapsed milliseconds from a monotonic start receipt."""

    return max(1, (time.monotonic_ns() - started_ns + 999_999) // 1_000_000)


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


__all__ = [
    "HostStageCancelled", "HostStageTimeout", "elapsed_ms", "run_structured_host",
]

"""In-process projection change waiting for the Odylith context daemon."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import threading
import time


@dataclass
class _ProjectionChangeGate:
    condition: threading.Condition = field(default_factory=threading.Condition)
    projection_fingerprint: str = ""
    version: int = 0


_GATES_LOCK = threading.Lock()
_GATES: dict[str, _ProjectionChangeGate] = {}


def _gate(repo_root: Path) -> _ProjectionChangeGate:
    key = str(Path(repo_root).resolve())
    with _GATES_LOCK:
        gate = _GATES.get(key)
        if gate is None:
            gate = _ProjectionChangeGate()
            _GATES[key] = gate
        return gate


def record_projection_fingerprint(*, repo_root: Path, projection_fingerprint: str) -> None:
    gate = _gate(repo_root)
    normalized = str(projection_fingerprint or "").strip()
    with gate.condition:
        if normalized == gate.projection_fingerprint:
            return
        gate.projection_fingerprint = normalized
        gate.version += 1
        gate.condition.notify_all()


def wait_for_projection_change(
    *,
    repo_root: Path,
    since_fingerprint: str,
    current_fingerprint: str,
    timeout_seconds: float,
) -> dict[str, object]:
    gate = _gate(repo_root)
    baseline = str(since_fingerprint or "").strip()
    observed = str(current_fingerprint or "").strip()
    timeout = max(0.0, float(timeout_seconds))
    deadline = time.monotonic() + timeout
    with gate.condition:
        if observed and observed != gate.projection_fingerprint:
            gate.projection_fingerprint = observed
            gate.version += 1
            gate.condition.notify_all()
        if gate.projection_fingerprint and gate.projection_fingerprint != baseline:
            return {
                "changed": True,
                "projection_fingerprint": gate.projection_fingerprint,
            }
        baseline_version = gate.version
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {
                    "changed": False,
                    "projection_fingerprint": gate.projection_fingerprint,
                }
            gate.condition.wait(timeout=remaining)
            if gate.version == baseline_version:
                continue
            if gate.projection_fingerprint and gate.projection_fingerprint != baseline:
                return {
                    "changed": True,
                    "projection_fingerprint": gate.projection_fingerprint,
                }
            baseline_version = gate.version


__all__ = [
    "record_projection_fingerprint",
    "wait_for_projection_change",
]

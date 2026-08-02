"""Supersede an active Greenfield view only after a successful managed CLI write."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set


_READ_ONLY_COMMANDS = frozenset(
    {
        "architecture",
        "benchmark",
        "bootstrap",
        "capabilities",
        "context",
        "context-engine",
        "discipline",
        "governance-slice",
        "impact",
        "lane",
        "plan",
        "query",
        "session-brief",
        "show",
        "subagent-orchestrator",
        "subagent-router",
        "turn-gate",
        "validate",
        "version",
    }
)


class GreenfieldManagedMutationBusyError(RuntimeError):
    """A supported later writer could not enter the managed mutation boundary."""


def command_may_mutate_greenfield_managed_paths(tokens: Sequence[str]) -> bool:
    """Conservatively classify supported CLI commands; unknown commands are writers."""

    command = tuple(str(token).strip() for token in tokens if str(token).strip())
    if not command or any(token in {"-h", "--help"} for token in command):
        return False
    top = command[0]
    if top in _READ_ONLY_COMMANDS or top in {"greenfield", "uninstall"}:
        return False
    if len(command) > 1 and (
        (top == "codex" and command[1] == "prompt-context")
        or (top == "claude" and command[1] == "prompt-bundle")
    ):
        # These adapters enter the Greenfield decision lock themselves.
        return False
    if top == "doctor" and "--repair" not in command:
        return False
    if top == "casebook" and len(command) > 1 and command[1] == "validate":
        return False
    if top == "atlas" and len(command) > 1 and command[1] == "render" and "--check-only" in command:
        return False
    if top == "release" and len(command) > 1 and command[1] in {"list", "show", "migration-gate"}:
        return False
    return True


def run_with_greenfield_managed_mutation_boundary(
    *,
    repo_root: Path,
    command_tokens: Sequence[str],
    operation: Callable[[], int],
) -> int:
    """Run one supported writer and supersede only after successful changed readback."""

    root = Path(repo_root).expanduser().resolve()
    if not command_may_mutate_greenfield_managed_paths(command_tokens):
        return operation()
    state = greenfield_generation_state.read_active_generation_state(root)
    if state is None or str(state.get("status") or "") != greenfield_generation_state.ACTIVE:
        return operation()
    try:
        with greenfield_repository_lock.greenfield_repository_lock(root):
            pinned = greenfield_generation_store.pin_active_greenfield_generation(root)
            result = operation()
            if result != 0:
                return result
            expected = {str(key): str(value) for key, value in dict(pinned.manifest["after_fingerprints"]).items()}
            actual = greenfield_repository_write_set.greenfield_managed_fingerprints(root)
            if actual != expected:
                greenfield_generation_state.supersede_active_generation(
                    repo_root=root,
                    expected_transaction_hash=pinned.transaction_hash,
                )
            return result
    except greenfield_repository_lock.GreenfieldRepositoryBusyError as exc:
        raise GreenfieldManagedMutationBusyError(
            "BUSY_NO_WRITE: another governed repository transaction is in progress"
        ) from exc


__all__ = [
    "GreenfieldManagedMutationBusyError",
    "command_may_mutate_greenfield_managed_paths",
    "run_with_greenfield_managed_mutation_boundary",
]

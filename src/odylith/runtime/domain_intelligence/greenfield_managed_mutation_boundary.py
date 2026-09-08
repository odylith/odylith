"""Publish complete immutable successors for successful managed CLI writes."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
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
    operation: Callable[[int | None], int],
) -> int:
    """Keep the previous complete view selected until a successful successor is sealed."""

    root = Path(repo_root).expanduser().resolve()
    if not command_may_mutate_greenfield_managed_paths(command_tokens):
        return operation(None)
    try:
        with greenfield_repository_lock.greenfield_repository_lock(root) as descriptor:
            GreenfieldCommitJournal.recover_pending_journals(repo_root=root)
            state = greenfield_generation_state.read_active_publication(root)
            pinned = greenfield_generation_store.require_greenfield_working_generation(root) if state else None
            active = greenfield_generation_state.active_generation_identity(root)
            result = operation(descriptor)
            if result != 0:
                return result
            if pinned is None:
                # A first install can activate, then perform further managed writes.
                if greenfield_generation_state.read_active_publication(root) is None:
                    return result
                pinned = greenfield_generation_store.pin_active_greenfield_generation(root)
                active = greenfield_generation_state.active_generation_identity(root)
            expected = dict(pinned.manifest["after_fingerprints"])
            actual = greenfield_repository_write_set.greenfield_managed_fingerprints(root)
            if actual != expected:
                write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
                    source_root=pinned.repository_root,
                    staged_root=root,
                    publication_precondition=active,
                )
                manifest = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
                generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
                    repo_root=root, write_set=write_set, manifest_text=manifest,
                )
                publication = greenfield_generation_state.compile_greenfield_publication_entry(
                    write_set_hash=generation.write_set_hash,
                    generation_manifest_sha256=generation.manifest_sha256,
                )
                greenfield_repository_write_set.require_greenfield_repository_after_state(
                    repo_root=root, write_set=write_set,
                )
                greenfield_generation_store.publish_greenfield_generation(
                    repo_root=root,
                    generation=generation,
                    write_set=write_set,
                    publication_entry_text=publication,
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

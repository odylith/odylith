"""Generation-boundary evidence for installed Greenfield recovery proof."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SIGKILL_FAULT = """
import os
from pathlib import Path
import signal
import sys

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_repository_write_set

original = greenfield_repository_write_set.transaction_atomic_write_bytes
root = Path.cwd().resolve()


def is_live_governed_path(value):
    try:
        relative = Path(value).resolve().relative_to(root).as_posix()
    except (OSError, ValueError):
        return False
    return relative == "odylith" or relative.startswith("odylith/") or relative.startswith(
        "src/odylith/bundle/assets/odylith/"
    )


def crash_after_first_sealed_write(*args, **kwargs):
    result = original(*args, **kwargs)
    path = args[1] if len(args) > 1 else kwargs.get("path")
    if path is not None and is_live_governed_path(path):
        os.kill(os.getpid(), signal.SIGKILL)
    return result


greenfield_repository_write_set.transaction_atomic_write_bytes = crash_after_first_sealed_write
raise SystemExit(cli.main(sys.argv[1:]))
"""

FSYNC_FAILURE_FAULT = """
import sys

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary

original_write = greenfield_repository_write_set.transaction_atomic_write_bytes
original_fsync = greenfield_transaction_path_boundary.os.fsync
armed = False
fired = False


def arm_first_sealed_write(*args, **kwargs):
    global armed
    armed = True
    return original_write(*args, **kwargs)


def fail_armed_fsync(*args, **kwargs):
    global fired
    if armed and not fired:
        fired = True
        raise OSError("injected installed Greenfield fsync failure")
    return original_fsync(*args, **kwargs)


greenfield_repository_write_set.transaction_atomic_write_bytes = arm_first_sealed_write
greenfield_transaction_path_boundary.os.fsync = fail_armed_fsync
raise SystemExit(cli.main(sys.argv[1:]))
"""

GENERATION_OBSERVATION_SCRIPT = """
import json
from pathlib import Path
import sys

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store

root = Path.cwd().resolve()
transaction_hash = sys.argv[1]
transaction_path = Path(sys.argv[2]).expanduser()
if not transaction_path.is_absolute():
    transaction_path = root / transaction_path
transaction_payload = json.loads(transaction_path.read_text(encoding="utf-8"))
write_set = transaction_payload["prewrite_package"]["repository_write_set"]
identity = greenfield_generation_state.active_generation_identity(root)
payload = {
    "active_identity": identity,
    "active_pin_status": "none",
    "active_pin_transaction_hash": "",
    "transaction_generation_status": "missing",
    "transaction_generation_manifest_sha256": "",
    "transaction_generation_write_set_hash": "",
    "transaction_generation_readback_status": "missing",
}
generation = None
generation_path = greenfield_generation_store.generation_root(root, transaction_hash)
if generation_path.exists():
    payload["transaction_generation_status"] = "invalid"
    payload["transaction_generation_readback_status"] = "invalid"
try:
    generation = greenfield_generation_store.pin_greenfield_generation(
        repo_root=root,
        transaction_hash=transaction_hash,
        expected_write_set=write_set,
    )
except (RuntimeError, ValueError):
    pass
else:
    payload["transaction_generation_status"] = "present"
    payload["transaction_generation_manifest_sha256"] = generation.manifest_sha256
    payload["transaction_generation_write_set_hash"] = generation.write_set_hash
    payload["transaction_generation_readback_status"] = "passed"
if identity.get("status") == greenfield_generation_state.ACTIVE:
    active = (
        generation
        if generation is not None and generation.transaction_hash == identity.get("transaction_hash")
        else greenfield_generation_store.pin_active_greenfield_generation(root)
    )
    payload["active_pin_status"] = "active"
    payload["active_pin_transaction_hash"] = active.transaction_hash
print(json.dumps(payload, sort_keys=True))
"""


def generation_observation_issues(facts: Mapping[str, Any]) -> list[str]:
    """Return missing or contradictory installed-generation evidence."""

    issues: list[str] = []
    sigkill = _mapping(facts.get("sigkill_generation_observations"))
    before = _mapping(sigkill.get("before"))
    crashed = _mapping(sigkill.get("after_crash"))
    recovered = _mapping(sigkill.get("after_recovery"))
    if not before or not crashed or not recovered:
        issues.append("installed recovery proof did not retain SIGKILL generation observations")
    elif _mapping(before.get("active_identity")) != _mapping(crashed.get("active_identity")):
        issues.append("installed SIGKILL changed the active-generation pointer before publication")
    elif crashed.get("active_pin_status") != before.get("active_pin_status"):
        issues.append("installed SIGKILL changed the canonical generation read before publication")
    elif crashed.get("transaction_generation_status") != "present":
        issues.append("installed SIGKILL did not retain the sealed immutable generation")
    elif crashed.get("transaction_generation_readback_status") != "passed":
        issues.append("installed SIGKILL immutable generation failed sealed after-image readback")
    elif recovered.get("active_pin_status") != "active":
        issues.append("installed SIGKILL recovery did not publish an active canonical generation")

    conflict = _mapping(facts.get("operator_conflict_generation_observations"))
    conflict_before = _mapping(conflict.get("before"))
    conflict_after = _mapping(conflict.get("after_conflict"))
    if not conflict_before or not conflict_after:
        issues.append("installed recovery proof did not retain operator-conflict generation observations")
    elif _mapping(conflict_before.get("active_identity")) != _mapping(conflict_after.get("active_identity")):
        issues.append("installed operator-conflict recovery changed the active-generation pointer")
    elif conflict_after.get("active_pin_status") != conflict_before.get("active_pin_status"):
        issues.append("installed operator-conflict recovery changed the canonical generation read")

    fsync = _mapping(facts.get("fsync_generation_observations"))
    fsync_before = _mapping(fsync.get("before"))
    failed = _mapping(fsync.get("after_failure"))
    retried = _mapping(fsync.get("after_retry"))
    if not fsync_before or not failed or not retried:
        issues.append("installed recovery proof did not retain fsync generation observations")
    elif _mapping(fsync_before.get("active_identity")) != _mapping(failed.get("active_identity")):
        issues.append("installed fsync rollback changed the active-generation pointer")
    elif failed.get("active_pin_status") != fsync_before.get("active_pin_status"):
        issues.append("installed fsync rollback changed the canonical generation read")
    elif failed.get("transaction_generation_status") != "missing":
        issues.append("installed fsync rollback retained an unpublished immutable generation")
    elif retried.get("active_pin_status") != "active":
        issues.append("installed fsync retry did not publish an active canonical generation")
    for label, observation in (("SIGKILL recovery", recovered), ("fsync retry", retried)):
        active_identity = _mapping(observation.get("active_identity"))
        if observation and observation.get("transaction_generation_readback_status") != "passed":
            issues.append(f"installed {label} published generation failed sealed after-image readback")
        if (
            observation
            and str(active_identity.get("transaction_hash") or "")
            != str(observation.get("active_pin_transaction_hash") or "")
        ):
            issues.append(f"installed {label} active pointer and canonical read disagree")
    return issues


def require_prepublication_generation_boundary(
    *,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    write_set_hash: str,
    label: str,
) -> None:
    """Require an immutable generation without changing the canonical read."""

    if _mapping(before.get("active_identity")) != _mapping(after.get("active_identity")):
        raise RuntimeError(f"installed {label} changed the active-generation pointer before publication")
    if before.get("active_pin_status") != after.get("active_pin_status"):
        raise RuntimeError(f"installed {label} changed the canonical generation read before publication")
    if after.get("transaction_generation_status") != "present":
        raise RuntimeError(f"installed {label} did not retain the sealed immutable generation")
    if after.get("transaction_generation_readback_status") != "passed":
        raise RuntimeError(f"installed {label} immutable generation failed sealed after-image readback")
    if str(after.get("transaction_generation_write_set_hash") or "") != write_set_hash:
        raise RuntimeError(f"installed {label} immutable generation does not match the sealed write set")


def require_journal_generation_binding(
    *,
    journal: Mapping[str, Any],
    observation: Mapping[str, Any],
) -> None:
    """Require the recovery journal to identify the stranded generation."""

    journal_manifest = str(journal.get("generation_manifest_sha256") or "")
    observed_manifest = str(observation.get("transaction_generation_manifest_sha256") or "")
    if not journal_manifest or journal_manifest != observed_manifest:
        raise RuntimeError("installed projecting journal does not identify the stranded immutable generation")


def require_published_generation_boundary(
    *,
    observation: Mapping[str, Any],
    transaction_hash: str,
    write_set_hash: str,
    label: str,
) -> None:
    """Require active pointer, canonical pin, and generation identity to agree."""

    identity = _mapping(observation.get("active_identity"))
    if str(identity.get("status") or "") != "active":
        raise RuntimeError(f"installed {label} did not publish an active-generation pointer")
    if str(identity.get("transaction_hash") or "") != transaction_hash:
        raise RuntimeError(f"installed {label} active pointer identifies the wrong transaction")
    if str(identity.get("write_set_hash") or "") != write_set_hash:
        raise RuntimeError(f"installed {label} active pointer identifies the wrong write set")
    if observation.get("active_pin_status") != "active":
        raise RuntimeError(f"installed {label} did not expose the active canonical generation")
    if str(observation.get("active_pin_transaction_hash") or "") != transaction_hash:
        raise RuntimeError(f"installed {label} canonical read identifies the wrong transaction")
    if observation.get("transaction_generation_status") != "present":
        raise RuntimeError(f"installed {label} published generation is missing")
    if observation.get("transaction_generation_readback_status") != "passed":
        raise RuntimeError(f"installed {label} published generation failed sealed after-image readback")
    manifest = str(observation.get("transaction_generation_manifest_sha256") or "")
    if not manifest or manifest != str(identity.get("generation_manifest_sha256") or ""):
        raise RuntimeError(f"installed {label} active pointer identifies the wrong generation manifest")


def require_aborted_generation_boundary(
    *,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    label: str,
) -> None:
    """Require an aborted attempt to leave no active or staged generation."""

    if _mapping(before.get("active_identity")) != _mapping(after.get("active_identity")):
        raise RuntimeError(f"installed {label} changed the active-generation pointer")
    if before.get("active_pin_status") != after.get("active_pin_status"):
        raise RuntimeError(f"installed {label} changed the canonical generation read")
    if after.get("transaction_generation_status") != "missing":
        raise RuntimeError(f"installed {label} retained an unpublished immutable generation")


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "FSYNC_FAILURE_FAULT",
    "GENERATION_OBSERVATION_SCRIPT",
    "SIGKILL_FAULT",
    "generation_observation_issues",
    "require_aborted_generation_boundary",
    "require_journal_generation_binding",
    "require_prepublication_generation_boundary",
    "require_published_generation_boundary",
]

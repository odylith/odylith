"""Append-once custody for a canonical Compass log's unfinished surface refresh.

Only a writer admitted before its append can create this authority. Unrecorded
render interruption is deliberately not recoverable through this command.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

import odylith
from odylith.install.fs import atomic_write_text, fsync_directory, fsync_file
from odylith.install.runtime import runtime_verification_path
from odylith.runtime.common import agent_runtime_contract, generated_refresh_guard
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_lock as leases
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets
from odylith.runtime.governance import owned_surface_refresh, sync_generated_outputs
from odylith.runtime.surfaces import compass_dashboard_frontend_contract, source_bundle_mirror
from odylith.runtime.surfaces.compass_refresh_runtime import REFRESH_STATE_SCHEMA_VERSION


RECEIPT_PATH = ".odylith/runtime/compass-log-continuation.v1.json"
STREAM_PATH = agent_runtime_contract.AGENT_STREAM_PATH
_REQUEST_PATH = "odylith/compass/runtime/refresh-state.v1.json"
_VERSION = "odylith.compass-log-continuation.v1"
_PHASES = {"prepared", "appended", "rendering", "failed", "rendered", "sealed"}


class CompassLogContinuationError(generations.GreenfieldWorkingGenerationDriftError):
    """No exact canonical-log continuation was admitted."""


def _refuse(reason: str) -> CompassLogContinuationError:
    return CompassLogContinuationError(
        "RECOVERY_REQUIRED: Compass log completion refused: " + reason
        + "; no append was replayed. Preserve the existing event and recovery evidence."
    )


def completion_requested(tokens: Sequence[str]) -> bool:
    return tuple(tokens[:2]) == ("compass", "log") and "--complete" in tokens[2:]


def completion_repo_argument(argv: Sequence[str]) -> str:
    """Accept exactly the payload-free public invocation, without abbreviations."""
    remaining = list(argv)
    seen: set[str] = set()
    root = "."
    while remaining:
        option = remaining.pop(0)
        if option in seen or option not in {"--complete", "--repo-root"}:
            raise ValueError("--complete permits only one --repo-root and no append arguments")
        seen.add(option)
        if option == "--repo-root":
            if not remaining or remaining[0].startswith("--"):
                raise ValueError("--repo-root requires a repository path")
            root = remaining.pop(0)
    if "--complete" not in seen:
        raise ValueError("--complete is required")
    return root


def _safe_path(root: Path, token: str) -> Path:
    path = root
    for part in Path(token).parts:
        path /= part
        if path.is_symlink():
            raise _refuse(f"unsafe symlink: {token}")
    return path


def _file_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode):
        raise _refuse(f"non-regular file: {path.name}")
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "mode": stat.S_IMODE(mode)}


def _runtime_identity(root: Path) -> dict[str, Any]:
    package = Path(odylith.__file__).resolve().parent
    code = sorted(path for path in package.rglob("*") if path.is_file()
                  and "__pycache__" not in path.parts and path.suffix != ".pyc"
                  and not (package == root / "src/odylith"
                           and path.is_relative_to(package / "bundle/assets/odylith")))
    executable = Path(sys.executable).resolve()
    activation = [_safe_path(root, token) for token in (
        ".odylith/install.json", ".odylith/bin/odylith", "odylith/runtime/source/product-version.v1.json",
    )]
    current = _safe_path(root, ".odylith/runtime") / "current"
    if current.exists() and not current.is_symlink():
        raise _refuse("runtime selection is not a symlink")
    if current.is_symlink():
        activation.append(runtime_verification_path(current.resolve(strict=True)))
    watched = (*code, executable, *activation)
    return {
        "executable": str(executable), "package": str(package),
        "selection": str(current.readlink()) if current.is_symlink() else None,
        "resolved_selection": str(current.resolve(strict=True)) if current.is_symlink() else None,
        "code": generated_refresh_guard.compute_input_fingerprint(
            repo_root=root, watched_paths=watched,
            extra={"modes": [stat.S_IMODE(path.stat().st_mode) if path.exists() else None for path in watched]},
        ),
    }


def _anchors(root: Path) -> dict[str, Any]:
    identity = root.stat()
    return {"repository": [str(root), identity.st_dev, identity.st_ino], "runtime": _runtime_identity(root)}


def _quiescent_request(root: Path) -> dict[str, Any] | None:
    path = _safe_path(root, _REQUEST_PATH)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text())
        if (not isinstance(value, dict) or value.get("schema_version") != REFRESH_STATE_SCHEMA_VERSION
                or value.get("status") not in {"passed", "failed"}
                or not isinstance(value.get("request_id"), str) or not value["request_id"]
                or type(value.get("pid")) is not int or type(value.get("rc")) is not int):
            raise ValueError("active or unknown request")
        return value
    except (OSError, ValueError) as exc:
        raise _refuse("Compass request is active, malformed, or unknown") from exc


def _derived_paths(root: Path) -> set[str]:
    # The pinned root has a portable layout, so this inventory stays logical
    # even when the working shell is physically stored as tooling-shell.html.
    paths = set(sync_generated_outputs.surface_render_outputs("compass", repo_root=root))
    paths.update(sync_generated_outputs.surface_render_outputs("tooling_shell", repo_root=root))
    paths.update("odylith/compass/" + asset.output_name for asset in (
        *compass_dashboard_frontend_contract.compass_shell_style_assets(),
        *compass_dashboard_frontend_contract.compass_shell_support_js_assets(),
    ))
    paths.update({"odylith/compass/compass-source-truth.v1.json", _REQUEST_PATH,
                  "odylith/compass/runtime/current.v1.json", "odylith/compass/runtime/current.v1.js",
                  "odylith/compass/runtime/history/index.v1.json", "odylith/compass/runtime/history/embedded.v1.js"})
    # The existing refresh creates these prerequisites only when missing.
    # An existing authored index or graph must never be rewritten on retry.
    paths.update(token for token in ("odylith/casebook/bugs/INDEX.md", "odylith/radar/traceability-graph.v1.json")
                 if not (root / token).exists())
    paths.update("src/odylith/bundle/assets/" + token for token in tuple(paths)
                 if source_bundle_mirror.is_consumer_safe_bundle_relative_path(token.removeprefix("odylith/")))
    return paths


def _derived(token: str, exact: set[str]) -> bool:
    if token in exact:
        return True
    path = Path(token)
    if path.parent.as_posix() != "odylith/compass/runtime/history" or not path.name.endswith(".v1.json"):
        return False
    from datetime import date

    try:
        return date.fromisoformat(path.name.removesuffix(".v1.json")).isoformat() == path.name.removesuffix(".v1.json")
    except ValueError:
        return False


def _working_state(root: Path, baseline: Path) -> dict[str, Any]:
    # The public write-set compiler owns logical layout, symlink checks, modes,
    # and managed-path inventory. Do not duplicate its recursive file walker.
    image = write_sets.compile_greenfield_repository_write_set(source_root=root, staged_root=root)["after_image"]
    exact = _derived_paths(baseline)
    authored = {row["path"]: [row["sha256"], row["mode"]] for row in image["files"]
                if row["path"] != STREAM_PATH and not _derived(row["path"], exact)}
    derived_parents = {str(parent) for token in exact | {STREAM_PATH} for parent in Path(token).parents}
    authored["directories"] = sorted(row["path"] for row in image["directories"]
                                      if row["path"] not in derived_parents
                                      and row["path"] != "odylith/compass/runtime/history")
    return {"fingerprints": write_sets.greenfield_managed_fingerprints(root), "authored": authored}


def _save(root: Path, receipt: Mapping[str, Any]) -> None:
    atomic_write_text(_safe_path(root, RECEIPT_PATH), json.dumps(receipt, sort_keys=True) + "\n")


def _load(root: Path) -> dict[str, Any]:
    try:
        raw = _safe_path(root, RECEIPT_PATH).read_text()
        value = json.loads(raw)
        if (not isinstance(value, dict) or value.get("version") != _VERSION
                or value.get("phase") not in _PHASES or raw != json.dumps(value, sort_keys=True) + "\n"
                or set(value) != {"version", "phase", "anchors", "publication", "event", "before_stream",
                                 "after_stream", "authored", "working", "successor"}):
            raise ValueError("invalid receipt")
        if (not isinstance(value["event"], str) or not value["event"]
                or value["event"] != json.dumps(json.loads(value["event"]), sort_keys=True) + "\n"
                or not isinstance(value["anchors"], dict) or not isinstance(value["authored"], dict)
                or not isinstance(value["working"], dict)
                or set(value["working"]) != set(write_sets.GREENFIELD_REPOSITORY_WRITE_PATHS)):
            raise ValueError("invalid admission fields")
        for field in ("before_stream", "after_stream"):
            state = value[field]
            if field == "before_stream" and state is None:
                continue
            if (not isinstance(state, dict) or set(state) != {"sha256", "size", "mode"}
                    or not isinstance(state["sha256"], str) or len(state["sha256"]) != 64
                    or type(state["size"]) is not int or state["size"] < 0
                    or type(state["mode"]) is not int or not 0 <= state["mode"] <= 0o777):
                raise ValueError("invalid stream state")
        if publication.require_active_generation_identity(value["publication"]) != value["publication"]:
            raise ValueError("invalid publication")
        if value["publication"]["status"] != "active":
            raise ValueError("missing active publication")
        if value["phase"] == "sealed":
            if (publication.require_active_generation_identity(value["successor"]) != value["successor"]
                    or value["successor"]["status"] != "active"):
                raise ValueError("invalid successor")
        elif value["successor"] is not None:
            raise ValueError("premature successor")
        return value
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise _refuse("the original admitted log receipt is unavailable or invalid") from exc


def _require_lease(root: Path, descriptor: int | None) -> None:
    if descriptor is None:
        raise _refuse("completion requires the admitted repository lease")
    try:
        with leases.inherited_greenfield_repository_lock(root, os.dup(descriptor)):
            pass
    except (OSError, leases.GreenfieldRepositoryLockError) as exc:
        raise _refuse("the admitted repository lease is unavailable") from exc


@dataclass
class CompassLogContinuation:
    root: Path
    receipt: dict[str, Any]
    pinned: generations.PinnedGreenfieldGeneration
    repository_lock_fd: int

    def require_anchors(self, *, before_append: bool = False) -> None:
        _require_lease(self.root, self.repository_lock_fd)
        if _anchors(self.root) != self.receipt["anchors"]:
            raise _refuse("repository or runtime identity changed")
        if publication.active_generation_identity(self.root) != self.receipt["publication"]:
            raise _refuse("published base changed")
        stream = _safe_path(self.root, STREAM_PATH)
        expected_stream = self.receipt["before_stream"] if before_append else self.receipt["after_stream"]
        if _file_state(stream) != expected_stream:
            raise _refuse("the exact durable append or stream mode changed")
        if not before_append:
            data, event = stream.read_bytes(), self.receipt["event"].encode("utf-8")
            before = self.receipt["before_stream"]
            prefix = data[:-len(event)]
            if (not data.endswith(event) or (before is None and prefix)
                    or (before is not None and (len(prefix) != before["size"]
                                                or hashlib.sha256(prefix).hexdigest() != before["sha256"]))):
                raise _refuse("the recorded event or pre-append tail changed")
        if _working_state(self.root, self.pinned.repository_root)["authored"] != self.receipt["authored"]:
            raise _refuse("authored inputs changed")
        _quiescent_request(self.root)

    def render(self) -> int:
        self.require_anchors()
        if write_sets.greenfield_managed_fingerprints(self.root) != self.receipt["working"]:
            raise _refuse("the recorded working state changed")
        if self.receipt["phase"] in {"rendered", "sealed"}:
            return 0
        if self.receipt["phase"] not in {"appended", "failed"}:
            raise _refuse("append or rendering ended without an exact terminal checkpoint")
        before_request = _quiescent_request(self.root)
        results: list[Mapping[str, Any]] = []

        def record_results(observed: Sequence[Mapping[str, Any]]) -> None:
            results.extend(deepcopy(observed))

        self.receipt["phase"] = "rendering"
        _save(self.root, self.receipt)
        try:
            owned_surface_refresh.raise_for_failed_refresh(
                repo_root=self.root, surface="compass", operation_label="Compass timeline append",
                retry_command=("compass", "log", "--repo-root", ".", "--complete"),
                on_results=record_results,
            )
        except Exception:
            self._record_render_result("failed", before_request, results)
            raise
        self._record_render_result("rendered", before_request, results)
        return 0

    def _record_render_result(
        self, phase: str, before_request: dict[str, Any] | None, results: Sequence[Mapping[str, Any]],
    ) -> None:
        self.require_anchors()
        request = _quiescent_request(self.root)
        if results:
            if len(results) != 1 or not isinstance(results[0], Mapping) or results[0].get("surface") != "compass":
                raise _refuse("refresh has ambiguous surface results")
            actions = results[0].get("action_results")
            if not isinstance(actions, list) or len(actions) != 1 or not isinstance(actions[0], Mapping):
                raise _refuse("refresh has no exact originating action result")
            action = actions[0]
            if (type(results[0].get("rc")) is not int or results[0]["rc"] != action.get("rc")
                    or results[0].get("status") != action.get("status")):
                raise _refuse("surface result differs from its originating action")
            if any(key in action for key in ("request_id", "state", "coalesced")):
                request_id = action.get("request_id")
                if (action.get("coalesced") is not False or not isinstance(request_id, str) or not request_id
                        or request is None or request_id != request.get("request_id")
                        or (before_request is not None and request_id == before_request.get("request_id"))
                        or action.get("state") != request or action.get("status") != request.get("status")
                        or type(action.get("rc")) is not int or action["rc"] != request.get("rc")):
                    raise _refuse("refresh did not return its own exact non-coalesced terminal request")
                if phase == "rendered" and (request["status"] != "passed" or request["rc"] != 0):
                    raise _refuse("refresh did not return a successful owned request")
                if request["status"] == "passed" and request["rc"] == 0:
                    # Delivered terminal success precedes capture teardown;
                    # a later teardown failure must not replay this render.
                    phase = "rendered"
            elif (phase != "failed" or type(action.get("rc")) is not int or action["rc"] == 0
                  or request != before_request):
                raise _refuse("pre-request failure changed request state or claimed success")
        elif phase != "failed" or request != before_request:
            raise _refuse("refresh ended without originating request evidence")
        self.receipt.update(phase=phase, working=write_sets.greenfield_managed_fingerprints(self.root))
        _save(self.root, self.receipt)

    def mark_sealed(self, generation: generations.PinnedGreenfieldGeneration) -> None:
        self.require_anchors()
        if self.receipt["phase"] not in {"rendered", "sealed"}:
            raise _refuse("surface refresh did not complete")
        if (write_sets.greenfield_managed_fingerprints(self.root) != self.receipt["working"]
                or generation.manifest["after_fingerprints"] != self.receipt["working"]):
            raise _refuse("the successor differs from completed working bytes")
        entry = publication.compile_greenfield_publication_entry(
            write_set_hash=generation.write_set_hash, generation_manifest_sha256=generation.manifest_sha256,
        )
        successor = {"status": "active", **publication.require_sealed_greenfield_publication_entry(
            entry, write_set_hash=generation.write_set_hash, generation_manifest_sha256=generation.manifest_sha256,
        )}
        if self.receipt["successor"] is not None and self.receipt["successor"] != successor:
            raise _refuse("the recorded successor changed")
        self.receipt.update(phase="sealed", successor=successor)
        _save(self.root, self.receipt)

    def retire(self) -> None:
        _require_lease(self.root, self.repository_lock_fd)
        if (_anchors(self.root) != self.receipt["anchors"]
                or publication.active_generation_identity(self.root) != self.receipt["successor"]):
            raise _refuse("published completion identity changed")
        generation = generations.require_greenfield_working_generation(self.root)
        if generation.manifest["after_fingerprints"] != self.receipt["working"]:
            raise _refuse("published completion bytes changed")
        path = _safe_path(self.root, RECEIPT_PATH)
        path.unlink()
        fsync_directory(path.parent)


def prepare_append(*, repo_root: Path, event: bytes, repository_lock_fd: int) -> CompassLogContinuation:
    root = Path(repo_root).resolve()
    _require_lease(root, repository_lock_fd)
    if _safe_path(root, RECEIPT_PATH).exists():
        raise _refuse("a previous canonical log still needs explicit completion")
    pinned = generations.require_greenfield_working_generation(root)
    _quiescent_request(root)
    stream = _safe_path(root, STREAM_PATH)
    before = stream.read_bytes() if stream.exists() else b""
    before_state = _file_state(stream)
    if before and not before.endswith(b"\n"):
        raise _refuse("the existing stream has a partial final event")
    # Event construction belongs to the log owner; preserve its exact serialized
    # bytes, including its timestamp, rather than preparing it again on retry.
    try:
        decoded = event.decode("utf-8")
        if not isinstance(json.loads(decoded), dict) or event != (json.dumps(json.loads(decoded), sort_keys=True) + "\n").encode():
            raise ValueError("noncanonical event")
    except ValueError as exc:
        raise _refuse("event bytes are not one canonical JSONL record") from exc
    working = _working_state(root, pinned.repository_root)
    receipt = {"version": _VERSION, "phase": "prepared", "anchors": _anchors(root),
               "publication": publication.active_generation_identity(root), "event": decoded,
               "before_stream": before_state,
               "after_stream": {"sha256": hashlib.sha256(before + event).hexdigest(), "size": len(before + event),
                                "mode": before_state["mode"] if before_state else 0o600},
               "authored": working["authored"], "working": working["fingerprints"], "successor": None}
    _save(root, receipt)
    return CompassLogContinuation(root, receipt, pinned, repository_lock_fd)


def append_prepared(continuation: CompassLogContinuation) -> None:
    root, receipt = continuation.root, continuation.receipt
    if receipt["phase"] != "prepared":
        raise _refuse("append was already attempted")
    continuation.require_anchors(before_append=True)
    if write_sets.greenfield_managed_fingerprints(root) != receipt["working"]:
        raise _refuse("working state changed before append")
    stream = _safe_path(root, STREAM_PATH)
    if _file_state(stream) != receipt["before_stream"]:
        raise _refuse("stream changed before append")
    stream.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(stream, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600), "ab") as handle:
        handle.write(receipt["event"].encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(stream.parent)
    continuation.require_anchors()
    receipt.update(phase="appended", working=write_sets.greenfield_managed_fingerprints(root))
    _save(root, receipt)


def require_completion(*, repo_root: Path, repository_lock_fd: int | None) -> CompassLogContinuation:
    root = Path(repo_root).resolve()
    _require_lease(root, repository_lock_fd)
    receipt = _load(root)
    pinned = generations.pin_greenfield_generation(repo_root=root, write_set_hash=receipt["publication"]["write_set_hash"])
    if pinned.manifest_sha256 != receipt["publication"]["generation_manifest_sha256"]:
        raise _refuse("recorded publication binding changed")
    if (_file_state(pinned.repository_root / STREAM_PATH) != receipt["before_stream"]
            or _working_state(pinned.repository_root, pinned.repository_root)["authored"] != receipt["authored"]):
        raise _refuse("recorded admission differs from its immutable base")
    continuation = CompassLogContinuation(root, receipt, pinned, repository_lock_fd)
    if receipt["phase"] == "sealed" and publication.active_generation_identity(root) == receipt["successor"]:
        continuation.retire()
        return continuation
    continuation.require_anchors()
    if receipt["phase"] == "prepared":
        # A fully fsynced append may precede the appended-phase receipt write.
        delta = write_sets.compile_greenfield_repository_write_set(source_root=pinned.repository_root, staged_root=root)
        if (any(row["path"] != STREAM_PATH for row in delta["writes"]) or delta["deletes"]
                or delta["directory_deletes"]
                or any(row["path"] not in {str(path) for path in Path(STREAM_PATH).parents}
                       for row in delta["directories"])):
            raise _refuse("prepared append contains unrecorded derived writes")
        state = _working_state(root, pinned.repository_root)
        if state["authored"] != receipt["authored"]:
            raise _refuse("prepared append has unrelated changes")
        fsync_file(_safe_path(root, STREAM_PATH))
        fsync_directory((root / STREAM_PATH).parent)
        receipt.update(phase="appended", working=state["fingerprints"])
        _save(root, receipt)
    if receipt["phase"] not in {"appended", "failed", "rendered", "sealed"}:
        raise _refuse("rendering was interrupted before terminal custody was recorded")
    if write_sets.greenfield_managed_fingerprints(root) != receipt["working"]:
        raise _refuse("recorded failed working bytes changed")
    return continuation


def pending_for_publication(*, repo_root: Path, command_tokens: Sequence[str], repository_lock_fd: int) -> CompassLogContinuation | None:
    if tuple(command_tokens[:2]) != ("compass", "log") or not _safe_path(repo_root, RECEIPT_PATH).exists():
        return None
    if _load(repo_root)["phase"] not in {"rendered", "sealed"}:
        return None
    return require_completion(repo_root=repo_root, repository_lock_fd=repository_lock_fd)

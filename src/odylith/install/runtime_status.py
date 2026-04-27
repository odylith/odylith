"""Install and runtime status models exposed to operators."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from odylith.install import runtime as runtime_module

PINNED_RUNTIME_SOURCE = "pinned_runtime"
SOURCE_CHECKOUT_RUNTIME_SOURCE = "source_checkout"
VERIFIED_RUNTIME_SOURCE = "verified_runtime"
WRAPPED_RUNTIME_SOURCE = "wrapped_runtime"
INSTALL_STATE_ONLY_RUNTIME_SOURCE = "install_state_only"
MISSING_RUNTIME_SOURCE = "missing_runtime"
_SOURCE_LOCAL_VERSION = "source-local"


@dataclass(frozen=True)
class RuntimeSourceStatus:
    source: str
    detail: str
    trust_degraded: bool
    trust_reasons: tuple[str, ...] = ()


def inspect_runtime_source(
    *,
    repo_root: str | Path,
    active_version: str,
    pinned_version: str,
    runtime_root: Path | None,
    verification: Mapping[str, object] | None,
) -> RuntimeSourceStatus:
    normalized_active = str(active_version or "").strip()
    normalized_pinned = str(pinned_version or "").strip()
    if runtime_root is None:
        if normalized_active:
            return RuntimeSourceStatus(
                source=INSTALL_STATE_ONLY_RUNTIME_SOURCE,
                detail="Install state still points at an active version, but the live runtime symlink is missing or invalid.",
                trust_degraded=True,
                trust_reasons=("active runtime symlink missing or invalid",),
            )
        return RuntimeSourceStatus(
            source=MISSING_RUNTIME_SOURCE,
            detail="No active Odylith runtime is currently staged.",
            trust_degraded=False,
        )
    if normalized_active == _SOURCE_LOCAL_VERSION or runtime_root.name == _SOURCE_LOCAL_VERSION:
        return RuntimeSourceStatus(
            source=SOURCE_CHECKOUT_RUNTIME_SOURCE,
            detail="Odylith is running from the detached source-local maintainer runtime.",
            trust_degraded=False,
        )

    managed_runtime = (runtime_root / "runtime-metadata.json").is_file()
    if managed_runtime:
        trust_reasons = tuple(
            runtime_module._managed_runtime_health_reasons(repo_root=repo_root, runtime_root=runtime_root)  # noqa: SLF001
        )
        if not trust_reasons:
            if normalized_active and normalized_pinned and normalized_active == normalized_pinned:
                return RuntimeSourceStatus(
                    source=PINNED_RUNTIME_SOURCE,
                    detail="Odylith is using the pinned managed runtime with live trust evidence.",
                    trust_degraded=False,
                )
            if normalized_active:
                return RuntimeSourceStatus(
                    source=VERIFIED_RUNTIME_SOURCE,
                    detail="Odylith is using a verified managed runtime that differs from the tracked repo pin.",
                    trust_degraded=False,
                )
        return RuntimeSourceStatus(
            source=WRAPPED_RUNTIME_SOURCE,
            detail=f"Managed runtime trust is degraded: {trust_reasons[0]}",
            trust_degraded=True,
            trust_reasons=trust_reasons,
        )

    runtime_python = runtime_module._runtime_python(runtime_root)  # noqa: SLF001
    exec_target = runtime_module._runtime_wrapper_exec_target(runtime_python) if runtime_python is not None else None  # noqa: SLF001
    if exec_target is not None:
        unwrapped = runtime_module._unwrap_runtime_wrapper_python(repo_root=repo_root, python=runtime_python)  # noqa: SLF001
        unwrapped_root = (
            runtime_module._runtime_root_for_python(repo_root=repo_root, python=unwrapped)  # noqa: SLF001
            if unwrapped is not None
            else None
        )
        if unwrapped_root is not None and (unwrapped_root / "runtime-metadata.json").is_file():
            trust_reasons = tuple(
                runtime_module._managed_runtime_health_reasons(repo_root=repo_root, runtime_root=unwrapped_root)  # noqa: SLF001
            )
            if trust_reasons:
                return RuntimeSourceStatus(
                    source=WRAPPED_RUNTIME_SOURCE,
                    detail=f"Managed runtime trust is degraded behind the active wrapper: {trust_reasons[0]}",
                    trust_degraded=True,
                    trust_reasons=trust_reasons,
                )
        return RuntimeSourceStatus(
            source=WRAPPED_RUNTIME_SOURCE,
            detail=f"Odylith is running through a local wrapper around {exec_target}.",
            trust_degraded=False,
        )

    verified_runtime = bool(verification)
    if normalized_active and normalized_pinned and normalized_active == normalized_pinned and verified_runtime:
        return RuntimeSourceStatus(
            source=PINNED_RUNTIME_SOURCE,
            detail="Odylith is using the pinned managed runtime recorded in install state.",
            trust_degraded=False,
        )
    if normalized_active and verified_runtime:
        return RuntimeSourceStatus(
            source=VERIFIED_RUNTIME_SOURCE,
            detail="Odylith is using a managed runtime recorded as verified in install state.",
            trust_degraded=False,
        )
    if normalized_active:
        return RuntimeSourceStatus(
            source=WRAPPED_RUNTIME_SOURCE,
            detail="The live runtime does not expose managed trust metadata, so Odylith is treating it as a local wrapped runtime.",
            trust_degraded=False,
        )
    return RuntimeSourceStatus(
        source=MISSING_RUNTIME_SOURCE,
        detail="No active Odylith runtime is currently staged.",
        trust_degraded=False,
    )


def trust_only_runtime_failure(
    *,
    runtime_reasons: Sequence[str],
    trust_reasons: Sequence[str],
    trust_degraded: bool,
) -> bool:
    if not trust_degraded:
        return False
    normalized_trust_reasons = {str(reason).strip() for reason in trust_reasons if str(reason).strip()}
    if not normalized_trust_reasons:
        return False
    observed_runtime_reasons = [str(reason).strip() for reason in runtime_reasons if str(reason).strip()]
    if not observed_runtime_reasons:
        return False
    for reason in observed_runtime_reasons:
        normalized_reason = reason.removeprefix("repo launcher ").removeprefix("bootstrap launcher ").strip()
        if normalized_reason in normalized_trust_reasons:
            continue
        if normalized_reason.startswith("active runtime wrapper targets unverified managed runtime:"):
            continue
        return False
    return True

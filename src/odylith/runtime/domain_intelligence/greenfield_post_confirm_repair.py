"""Read-only post-confirm package inspection.

Rendered artifact drafts are transaction outputs, not repair substrates. This
module keeps the old compatibility function names for callers and tests, but
the functions no longer mutate package content. Source repair must happen in
SemanticModelIR or ArtifactPlanIR before projections are rendered.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionReport
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_package_report


_DEFAULT_PACKAGE_REPAIR_PASSES = 4


@dataclass(frozen=True)
class GreenfieldPackageRepairResult:
    package: GreenfieldCompletionPackage
    initial_report: GreenfieldCompletionReport
    report: GreenfieldCompletionReport
    passes: int
    changed: bool


def inspect_greenfield_package(
    package: GreenfieldCompletionPackage,
) -> GreenfieldPackageRepairResult:
    """Return package quality results without mutating rendered outputs."""

    report = build_greenfield_package_report(package)
    return GreenfieldPackageRepairResult(
        package=package,
        initial_report=report,
        report=report,
        passes=0,
        changed=False,
    )


def repair_greenfield_package_until_clean(
    package: GreenfieldCompletionPackage,
    *,
    max_passes: int = _DEFAULT_PACKAGE_REPAIR_PASSES,
) -> GreenfieldPackageRepairResult:
    """Compatibility wrapper; rendered package repair is intentionally disabled."""

    _ = max_passes
    return inspect_greenfield_package(package)


def repair_greenfield_package_once(
    package: GreenfieldCompletionPackage,
    *,
    patchset_request: Mapping[str, Any] | None = None,
) -> GreenfieldCompletionPackage:
    """Compatibility wrapper; rendered package repair is intentionally disabled."""

    _ = patchset_request
    return package


__all__ = [
    "GreenfieldPackageRepairResult",
    "inspect_greenfield_package",
    "repair_greenfield_package_once",
    "repair_greenfield_package_until_clean",
]

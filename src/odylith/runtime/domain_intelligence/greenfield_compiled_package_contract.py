"""Graph-native completeness contract for sealed Greenfield packages."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_completion_types import (
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_package_validation import (
    require_verified_semantic_package,
)


def require_complete_compiled_greenfield_package(
    prewrite_package: GreenfieldCompletionPackage,
    *,
    release_selector: str,
) -> None:
    """Reject any package that is not an exact verified graph projection."""

    require_verified_semantic_package(
        prewrite_package,
        release_selector=release_selector,
    )


__all__ = ["require_complete_compiled_greenfield_package"]

"""Path alias helpers for Registry component artifact ownership.

Registry component inventories intentionally point at canonical product-owned
paths such as ``odylith/...`` and ``src/odylith/...``. In the Odylith product
repo, some of those canonical assets are mirrored into the bundled install tree
under ``src/odylith/bundle/assets/odylith/...``. For forensic mapping, those
source-owned mirrors should count as the same component-owned artifact rather
than as unrelated churn.
"""

from __future__ import annotations

from odylith.runtime.governance import workstream_inference

_PRODUCT_BUNDLE_SOURCE_MIRROR_PREFIX = "src/odylith/bundle/assets/odylith/"


def equivalent_component_artifact_tokens(*tokens: str) -> list[str]:
    """Return stable equivalent artifact tokens for component ownership checks."""

    rows: list[str] = []
    seen: set[str] = set()
    for raw in tokens:
        normalized = workstream_inference.normalize_repo_token(str(raw or "")).lstrip("./")
        if not normalized:
            continue
        candidates = [normalized]
        if normalized.startswith(_PRODUCT_BUNDLE_SOURCE_MIRROR_PREFIX):
            suffix = normalized.removeprefix(_PRODUCT_BUNDLE_SOURCE_MIRROR_PREFIX).strip("/")
            if suffix:
                candidates.append(f"odylith/{suffix}")
        for token in candidates:
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(token)
    return rows


__all__ = ["equivalent_component_artifact_tokens"]

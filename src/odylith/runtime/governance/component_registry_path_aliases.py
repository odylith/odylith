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


def canonical_component_artifact_token(token: str) -> str:
    """Return the stable canonical token for component-owned artifact paths."""

    normalized = workstream_inference.normalize_repo_token(str(token or "")).lstrip("./")
    if not normalized:
        return ""
    if normalized.startswith(_PRODUCT_BUNDLE_SOURCE_MIRROR_PREFIX):
        suffix = normalized.removeprefix(_PRODUCT_BUNDLE_SOURCE_MIRROR_PREFIX).strip("/")
        if suffix:
            return f"odylith/{suffix}"
    return normalized


def equivalent_component_artifact_tokens(*tokens: str) -> list[str]:
    """Return stable equivalent artifact tokens for component ownership checks."""

    rows: list[str] = []
    seen: set[str] = set()
    for raw in tokens:
        normalized = workstream_inference.normalize_repo_token(str(raw or "")).lstrip("./")
        if not normalized:
            continue
        canonical = canonical_component_artifact_token(normalized)
        candidates = [normalized]
        if canonical and canonical != normalized:
            candidates.append(canonical)
        for token in candidates:
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(token)
    return rows


__all__ = ["canonical_component_artifact_token", "equivalent_component_artifact_tokens"]

"""Shared projection-contract versions for runtime fingerprints.

These versions intentionally sit outside the heavy projection store so hot
render paths and the full store can invalidate stale compiled projections when
parser or shaping semantics change, even if the underlying source files do not.
"""

from __future__ import annotations


_PROJECTION_CONTRACT_VERSIONS = {
    "workstreams": "v1",
    "releases": "v1",
    "plans": "v1",
    "bugs": "v3_casebook_bug_ids",
    "diagrams": "v1",
    "components": "v1",
    "codex_events": "v1",
    "traceability": "v1",
    "delivery": "v1",
    "engineering_graph": "v1",
    "code_graph": "v1",
}


def projection_contract_version(name: str) -> str:
    token = str(name or "").strip()
    return _PROJECTION_CONTRACT_VERSIONS.get(token, "v1")


__all__ = ["projection_contract_version"]

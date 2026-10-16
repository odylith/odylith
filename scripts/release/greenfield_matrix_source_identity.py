"""Identity and metamorphic-pair rules for Greenfield source records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse


def source_uri_identity(value: str) -> str:
    """Canonicalize a source URI without treating its fragment as source identity."""

    parsed = urlparse(value)
    return parsed._replace(
        scheme=parsed.scheme.casefold(),
        netloc=parsed.netloc.casefold(),
        fragment="",
    ).geturl()


def complete_metamorphic_groups(groups: Mapping[str, Sequence[Any]]) -> dict[str, list[str]]:
    """Return only two-case source-preserving metamorphic groups."""

    complete: dict[str, list[str]] = {}
    for group, cases in sorted(groups.items()):
        transforms = {
            str(getattr(case, "metamorphic_transform", "") or "").strip()
            for case in cases
            if str(getattr(case, "metamorphic_transform", "") or "").strip()
        }
        provenances = [getattr(case, "provenance", None) for case in cases]
        artifact_hashes = [_text(provenance, "source_artifact_sha256") for provenance in provenances]
        source_ids = [_text(provenance, "source_id") for provenance in provenances]
        source_uris = [source_uri_identity(_text(provenance, "source_uri")) for provenance in provenances]
        spans = [_text(provenance, "source_span") for provenance in provenances]
        if (
            len(cases) == 2
            and len(transforms) == 2
            and all(artifact_hashes)
            and len(set(artifact_hashes)) == 1
            and all(source_ids)
            and len(set(source_ids)) == 1
            and all(source_uris)
            and len(set(source_uris)) == 1
            and all(spans)
            and len(set(spans)) == 2
        ):
            complete[group] = sorted(transforms)
    return complete


def is_explicit_metamorphic_pair(cases: Sequence[Any]) -> bool:
    """Require repeated source identity to be exactly one complete pair."""

    if len(cases) != 2:
        return False
    groups = {str(getattr(case, "metamorphic_group", "") or "").strip() for case in cases}
    if not groups or "" in groups or len(groups) != 1:
        return False
    return bool(complete_metamorphic_groups({next(iter(groups)): cases}))


def source_identity_label(identity: tuple[str, str, str]) -> str:
    """Render bounded identity context for a provenance failure."""

    source_id, source_uri, artifact = identity
    return f"source_id `{source_id}`, source_uri `{source_uri}`, artifact `{artifact}`"


def _text(provenance: Any, field: str) -> str:
    return str(getattr(provenance, field, "") or "").strip()


__all__ = [
    "complete_metamorphic_groups",
    "is_explicit_metamorphic_pair",
    "source_identity_label",
    "source_uri_identity",
]

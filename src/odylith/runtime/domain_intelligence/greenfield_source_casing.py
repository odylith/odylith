"""Source-token casing custody for greenfield projected artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import restore_source_token_casing
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_text import text_values


_STRUCTURAL_KEY_EXACT = frozenset(
    {
        "anchor",
        "anchors",
        "backlog_index",
        "catalog",
        "checksum",
        "component_focus",
        "component_id",
        "component_ids",
        "component_sequence",
        "diagram_id",
        "diagram_ids",
        "fingerprint",
        "fingerprints",
        "hash",
        "href",
        "id",
        "ids",
        "key",
        "kind",
        "path",
        "paths",
        "release_id",
        "repo_root",
        "route",
        "schema_version",
        "selector",
        "sha",
        "slug",
        "source_mmd",
        "source_path",
        "source_png",
        "source_svg",
        "spec_path",
        "status",
        "target_path",
        "url",
        "version",
    }
)
_STRUCTURAL_KEY_SUFFIXES = (
    "_fingerprint",
    "_fingerprints",
    "_hash",
    "_href",
    "_id",
    "_ids",
    "_path",
    "_paths",
    "_route",
    "_sha",
    "_slug",
    "_slugs",
    "_url",
)


def proposal_source_casing_text(proposal: Mapping[str, Any]) -> str:
    """Return accepted source text that owns acronym and mixed-case spelling."""

    accepted_source = " ".join(
        text_values(
            {
                "intent": proposal.get("intent"),
                "confirmed_intent": proposal.get("confirmed_intent"),
            }
        )
    )
    if _has_source_casing_token(accepted_source):
        return accepted_source
    return " ".join(
        text_values(
            {
                "intent": proposal.get("intent"),
                "semantic_model": proposal.get("semantic_model"),
                "confirmed_intent": proposal.get("confirmed_intent"),
            }
        )
    )


def restore_source_casing_in_public_copy(value: Any, *, source_text: str, key: str = "") -> Any:
    """Restore source-owned casing in public copy while leaving IDs and paths stable."""

    if not source_text:
        return value
    if isinstance(value, str):
        return value if _structural_key(key) else restore_source_token_casing(value, source_text)
    if isinstance(value, Mapping):
        return {
            item_key: restore_source_casing_in_public_copy(
                item_value,
                source_text=source_text,
                key=str(item_key),
            )
            for item_key, item_value in value.items()
        }
    if isinstance(value, tuple):
        return tuple(restore_source_casing_in_public_copy(item, source_text=source_text, key=key) for item in value)
    if isinstance(value, list):
        return [restore_source_casing_in_public_copy(item, source_text=source_text, key=key) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [restore_source_casing_in_public_copy(item, source_text=source_text, key=key) for item in value]
    return value


def restore_source_casing_in_text_mapping_values(
    value: Mapping[str, str] | None,
    *,
    source_text: str,
) -> dict[str, str]:
    """Restore source casing in rendered artifact text values without rewriting map keys."""

    return {
        str(item_key): str(restore_source_casing_in_public_copy(item_value, source_text=source_text, key="text") or "")
        for item_key, item_value in dict(value or {}).items()
    }


def package_with_source_casing(package: GreenfieldCompletionPackage) -> GreenfieldCompletionPackage:
    """Return a completion package whose visible copy preserves accepted source casing."""

    proposal = package.proposal if isinstance(package.proposal, Mapping) else {}
    source_text = proposal_source_casing_text(proposal)
    if not source_text:
        return package
    restored_proposal = restore_source_casing_in_public_copy(proposal, source_text=source_text)
    return replace(
        package,
        proposal=restored_proposal,
        rendered_component_specs=restore_source_casing_in_text_mapping_values(
            package.rendered_component_specs,
            source_text=source_text,
        ),
        rendered_atlas_sources=restore_source_casing_in_text_mapping_values(
            package.rendered_atlas_sources,
            source_text=source_text,
        ),
        component_registry_preview=tuple(
            restore_source_casing_in_public_copy(row, source_text=source_text)
            for row in package.component_registry_preview
        ),
        project_brief_preview=restore_source_casing_in_public_copy(package.project_brief_preview, source_text=source_text),
        project_brief_record_text=str(
            restore_source_casing_in_public_copy(package.project_brief_record_text, source_text=source_text, key="text")
            or ""
        ),
        tribunal_preview=restore_source_casing_in_public_copy(package.tribunal_preview, source_text=source_text),
        accepted_project_preview=restore_source_casing_in_public_copy(package.accepted_project_preview, source_text=source_text),
        project_dashboard_preview=restore_source_casing_in_public_copy(package.project_dashboard_preview, source_text=source_text),
        compass_memory_preview=restore_source_casing_in_public_copy(package.compass_memory_preview, source_text=source_text),
        next_steps_preview=restore_source_casing_in_public_copy(package.next_steps_preview, source_text=source_text),
        backlog_result=restore_source_casing_in_public_copy(package.backlog_result, source_text=source_text),
        program_result=restore_source_casing_in_public_copy(package.program_result, source_text=source_text),
        prewrite_safety_preview=restore_source_casing_in_public_copy(package.prewrite_safety_preview, source_text=source_text),
        release_target_result=restore_source_casing_in_public_copy(package.release_target_result, source_text=source_text),
        release_assignment_result=restore_source_casing_in_public_copy(
            package.release_assignment_result,
            source_text=source_text,
        ),
    )


def _structural_key(key: str) -> bool:
    token = str(key or "").strip().casefold()
    return bool(token and (token in _STRUCTURAL_KEY_EXACT or token.endswith(_STRUCTURAL_KEY_SUFFIXES)))


def _has_source_casing_token(value: str) -> bool:
    return bool(
        re.search(
            r"\b[A-Z]{2,}(?:[/-][A-Za-z0-9]+)*\b|"
            r"\b[A-Za-z][A-Za-z0-9_/-]*[A-Z][A-Za-z0-9_/-]*\b",
            value,
        )
    )


__all__ = [
    "package_with_source_casing",
    "proposal_source_casing_text",
    "restore_source_casing_in_public_copy",
    "restore_source_casing_in_text_mapping_values",
]

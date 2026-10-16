"""Schema-owned semantic patch target registry for greenfield repair."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token


@dataclass(frozen=True)
class SemanticPatchTarget:
    """One sanctioned SemanticModelIR fact that may be patched before rerender."""

    target_id: str
    value_kind: str
    operation_kind: str
    canonical_path: str
    semantic_node_id: str
    replacement_keys: tuple[str, ...]
    address_aliases: tuple[str, ...]
    intent_key: str
    source_mirror_paths: tuple[str, ...] = ()
    affected_projections: tuple[str, ...] = ()
    completion_required: bool = False


def semantic_patch_target_for_operation(operation: Mapping[str, Any]) -> SemanticPatchTarget | None:
    """Resolve a PatchSet operation to an exact semantic target."""

    target = semantic_patch_target_for_kind(operation.get("operation_kind"))
    if target:
        return target
    for key in ("target_path", "semantic_node_id"):
        target = semantic_patch_target_for_address(operation.get(key))
        if target:
            return target
    return None


def semantic_patch_target_for_kind(value: Any) -> SemanticPatchTarget | None:
    """Return a semantic target for a formal operation kind."""

    return _TARGET_BY_OPERATION_KIND.get(normalize_token(value))


def semantic_patch_target_for_address(value: Any) -> SemanticPatchTarget | None:
    """Return a semantic target for an exact PatchSet path or node id."""

    return _TARGET_BY_ADDRESS.get(_address_token(value))


def semantic_patch_operation_kind(*, target_path: Any = "", semantic_node_id: Any = "") -> str:
    """Return the formal operation kind for a semantic PatchSet address."""

    for value in (target_path, semantic_node_id):
        target = semantic_patch_target_for_address(value)
        if target:
            return target.operation_kind
    return ""


def semantic_replacement_leaf_key(*, operation_kind: Any = "", target_path: Any = "") -> str:
    """Return the canonical replacement_fact key for a semantic target."""

    target = semantic_patch_target_for_kind(operation_kind) or semantic_patch_target_for_address(target_path)
    return target.replacement_keys[0] if target and target.replacement_keys else ""


def semantic_list_replacement_keys() -> frozenset[str]:
    """Return replacement_fact keys that intentionally allow empty lists."""

    return frozenset(target.replacement_keys[0] for target in _TARGETS if target.value_kind == "list")


def _target(
    target_id: str,
    *,
    value_kind: str,
    replacement_keys: tuple[str, ...],
    canonical_path: str,
    semantic_node_id: str,
    intent_key: str = "",
    aliases: tuple[str, ...] = (),
    source_mirror_paths: tuple[str, ...] = (),
    affected_projections: tuple[str, ...] = (),
    completion_required: bool = False,
) -> SemanticPatchTarget:
    operation_kind = f"semantic_{target_id}"
    return SemanticPatchTarget(
        target_id=target_id,
        value_kind=value_kind,
        operation_kind=operation_kind,
        canonical_path=canonical_path,
        semantic_node_id=semantic_node_id,
        replacement_keys=replacement_keys,
        address_aliases=tuple(
            dict.fromkeys(
                (
                    canonical_path,
                    semantic_node_id,
                    canonical_path.removeprefix("semantic_model.domain_ontology."),
                    f"proposal.{canonical_path}",
                    f"SemanticModelIR.{canonical_path.removeprefix('semantic_model.')}",
                    *aliases,
                )
            )
        ),
        intent_key=intent_key or target_id,
        source_mirror_paths=source_mirror_paths,
        affected_projections=affected_projections,
        completion_required=completion_required,
    )


def _address_token(value: Any) -> str:
    return normalize_string(value).casefold()


_TEXT_REPLACEMENT_KEYS = ("corrected_interpretation", "replacement", "text")
_LIST_REPLACEMENT_KEYS = ("corrected_interpretation", "replacement")

_TARGETS = (
    _target(
        "first_path",
        value_kind="first_path",
        replacement_keys=("first_path", "raw_path", *_TEXT_REPLACEMENT_KEYS),
        canonical_path="semantic_model.first_path_contract.raw_path",
        semantic_node_id="SemanticModelIR.first_path_contract.raw_path",
        intent_key="first_path",
        aliases=(
            "semantic_model.first_path_contract",
            "proposal.semantic_model.first_path_contract",
            "SemanticModelIR.first_path_contract",
        ),
        completion_required=True,
    ),
    _target(
        "proof_boundary",
        value_kind="text",
        replacement_keys=("proof_boundary", "release_boundary", *_TEXT_REPLACEMENT_KEYS),
        canonical_path="semantic_model.domain_ontology.proof_boundary",
        semantic_node_id="SemanticModelIR.domain_ontology.proof_boundary",
    ),
    _target(
        "state_object",
        value_kind="text",
        replacement_keys=("state_object", "state", *_TEXT_REPLACEMENT_KEYS),
        canonical_path="semantic_model.domain_ontology.state_object",
        semantic_node_id="SemanticModelIR.domain_ontology.state_object",
    ),
    _target(
        "human_actors",
        value_kind="list",
        replacement_keys=("human_actors", "actors", "actor", *_LIST_REPLACEMENT_KEYS),
        canonical_path="semantic_model.domain_ontology.human_actors",
        semantic_node_id="SemanticModelIR.domain_ontology.human_actors",
        aliases=("semantic_model.human_actors",),
    ),
    _target(
        "external_systems",
        value_kind="list",
        replacement_keys=("external_systems", "systems", "system", *_LIST_REPLACEMENT_KEYS),
        canonical_path="semantic_model.domain_ontology.external_systems",
        semantic_node_id="SemanticModelIR.domain_ontology.external_systems",
        aliases=("semantic_model.external_systems",),
    ),
    _target(
        "internal_systems",
        value_kind="list",
        replacement_keys=("internal_systems", "systems", "system", *_LIST_REPLACEMENT_KEYS),
        canonical_path="semantic_model.domain_ontology.internal_systems",
        semantic_node_id="SemanticModelIR.domain_ontology.internal_systems",
        aliases=("semantic_model.internal_systems",),
    ),
    _target(
        "non_goals",
        value_kind="list",
        replacement_keys=("non_goals", "deferred_scope", "out_of_scope", *_LIST_REPLACEMENT_KEYS),
        canonical_path="semantic_model.domain_ontology.non_goals",
        semantic_node_id="SemanticModelIR.domain_ontology.non_goals",
        aliases=("semantic_model.non_goals",),
        source_mirror_paths=("non_goals",),
        affected_projections=("radar", "atlas", "project_brief"),
    ),
)

_TARGET_BY_OPERATION_KIND = {target.operation_kind: target for target in _TARGETS}
_TARGET_BY_ADDRESS = {
    _address_token(address): target
    for target in _TARGETS
    for address in target.address_aliases
    if _address_token(address)
}


__all__ = [
    "SemanticPatchTarget",
    "semantic_list_replacement_keys",
    "semantic_patch_operation_kind",
    "semantic_patch_target_for_address",
    "semantic_patch_target_for_kind",
    "semantic_patch_target_for_operation",
    "semantic_replacement_leaf_key",
]

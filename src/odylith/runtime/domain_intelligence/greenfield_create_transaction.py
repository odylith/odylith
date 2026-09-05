"""Precompiled create transactions for confirmed greenfield writes."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from dataclasses import is_dataclass
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_text
from odylith.runtime.common.value_coercion import mapping_copy
from odylith.runtime.domain_intelligence import greenfield_compiled_package_contract
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
    canonical_product_create_transaction_receipt_bytes,
)
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
    build_product_create_transaction_compiler_identity,
)
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
    require_product_create_transaction_compiler_provenance_payload,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import PRODUCT_CREATE_TRANSACTION_COMPILER
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_REPOSITORY_CONTEXT_POLICY,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import PRODUCT_CREATE_TRANSACTION_VERSION
from odylith.runtime.domain_intelligence.greenfield_create_contract import POST_CONFIRM_ALLOWED_OPERATIONS
from odylith.runtime.domain_intelligence.greenfield_create_contract import POST_CONFIRM_FORBIDDEN_OPERATIONS
from odylith.runtime.domain_intelligence.greenfield_create_manifest import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_create_manifest import PRECONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    require_relation_authority_parity,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    MAX_GREENFIELD_SEMANTIC_CALLS,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    greenfield_model_profile_observation_issues,
    model_profile_id_for_repair_tier,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_FACTS_HASH_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_facts_hash
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    require_product_intent_authority,
)
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


_VOLATILE_HASH_KEYS = {
    "elapsed_seconds",
    "whole_project_elapsed_seconds",
    "create_elapsed_seconds",
}
_PRODUCT_CREATE_TRANSACTION_COMPILER_ATTESTATION = object()

@dataclass(frozen=True)
class ProductCreateTransaction:
    """Validated package that post-confirm code may only verify and commit."""

    version: str
    release_selector: str
    proposal: Mapping[str, Any]
    validation_gate: Mapping[str, Any]
    prewrite_package: GreenfieldCompletionPackage
    backlog_result: Mapping[str, Any]
    intent_authority: Mapping[str, Any]
    quality_manifest: Mapping[str, Any]
    compiler_provenance: Mapping[str, Any]
    transaction_hash: str
    _compiler_attestation: object | None = field(default=None, repr=False, compare=False)

    @property
    def verified(self) -> bool:
        if self._compiler_attestation is not _PRODUCT_CREATE_TRANSACTION_COMPILER_ATTESTATION:
            return False
        try:
            require_product_create_transaction_hash_verified(self)
        except ValueError:
            return False
        return True

    def summary(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "transaction_hash": self.transaction_hash,
            "verified": self.verified,
            **_product_create_transaction_commit_summary(self),
        }


def _product_create_transaction_commit_summary(transaction: ProductCreateTransaction) -> dict[str, Any]:
    """Return pre-confirm reporting bytes without the transaction hash."""

    write_set = (
        transaction.prewrite_package.repository_write_set
        if isinstance(transaction.prewrite_package.repository_write_set, Mapping)
            else {}
        )
    return {
        "release_selector": transaction.release_selector,
        "quality_status": str(transaction.quality_manifest.get("status", "")).strip(),
        "validation_status": str(transaction.quality_manifest.get("validation_status", "")).strip(),
        "compiler": str(transaction.compiler_provenance.get("compiler", "")).strip(),
        "compiler_phase": str(transaction.compiler_provenance.get("phase", "")).strip(),
        "product_facts_sha256": str(transaction.intent_authority.get("product_facts_sha256", "")).strip(),
        "intent_authority_version": str(transaction.intent_authority.get("version", "")).strip(),
        "surface_refresh_preview": _json_ready(transaction.prewrite_package.surface_refresh_preview or {}),
        "repository_write_set_hash": str(write_set.get("write_set_hash", "")).strip(),
        "repository_write_count": int(write_set.get("write_count", 0) or 0),
        "repository_delete_count": int(write_set.get("delete_count", 0) or 0),
        "repository_directory_delete_count": int(write_set.get("directory_delete_count", 0) or 0),
    }


def build_product_create_transaction(
    *,
    proposal: Mapping[str, Any],
    release_selector: str,
    validation_gate: Mapping[str, Any],
    prewrite_package: GreenfieldCompletionPackage,
    backlog_result: Mapping[str, Any],
    intent_authority: Mapping[str, Any] | None = None,
    quality_manifest: Mapping[str, Any],
    repo_root: Path,
) -> ProductCreateTransaction:
    """Build a hash-bound transaction from an already validated prewrite package."""

    authority = dict(intent_authority) if isinstance(intent_authority, Mapping) else _authority_from_proposal(proposal)
    require_product_intent_authority(authority)
    authored_projection_verified = _require_proposal_intent_authority_binding(
        proposal,
        authority,
    )
    release_text = str(release_selector or "").strip()
    greenfield_compiled_package_contract.require_complete_compiled_greenfield_package(
        prewrite_package,
        release_selector=release_text,
    )
    _require_prewrite_package_proposal_binding(
        proposal=proposal,
        prewrite_package=prewrite_package,
        authority=authority,
    )
    require_product_create_transaction_quality_approved(
        quality_manifest,
        authored_projection_verified=authored_projection_verified,
    )
    transaction = ProductCreateTransaction(
        version=PRODUCT_CREATE_TRANSACTION_VERSION,
        release_selector=release_text,
        proposal=proposal,
        validation_gate=validation_gate,
        prewrite_package=prewrite_package,
        backlog_result=backlog_result,
        intent_authority=authority,
        quality_manifest=quality_manifest,
        compiler_provenance=build_product_create_transaction_provenance(
            quality_manifest=quality_manifest,
        ),
        transaction_hash="",
        _compiler_attestation=_PRODUCT_CREATE_TRANSACTION_COMPILER_ATTESTATION,
    )
    return replace(transaction, transaction_hash=product_create_transaction_hash(transaction))


def _authority_from_proposal(proposal: Mapping[str, Any]) -> Mapping[str, Any]:
    authority = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if isinstance(authority, Mapping):
        return dict(authority)
    raise ValueError("ProductCreateTransaction is missing confirmed Product Intent authority")


def _require_prewrite_package_proposal_binding(
    *,
    proposal: Mapping[str, Any],
    prewrite_package: GreenfieldCompletionPackage,
    authority: Mapping[str, Any],
) -> None:
    """Require the compiled package to carry the exact authority-bound proposal."""

    package_proposal = prewrite_package.proposal
    if not isinstance(package_proposal, Mapping):
        raise ValueError("ProductCreateTransaction compiled package is missing its proposal")
    try:
        proposal_bytes = json.dumps(
            proposal,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        package_bytes = json.dumps(
            package_proposal,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ValueError("ProductCreateTransaction proposal must be canonical JSON data") from exc
    if proposal_bytes != package_bytes:
        raise ValueError(
            "ProductCreateTransaction compiled package proposal does not match its reviewed proposal"
        )
    _require_proposal_intent_authority_binding(package_proposal, authority)


def require_product_create_transaction_quality_approved(
    quality_manifest: Mapping[str, Any],
    *,
    authored_projection_verified: bool | None = None,
) -> None:
    """Require every product-quality decision before a transaction can be confirmed."""

    manifest = dict(quality_manifest)
    quality_status = str(manifest.get("status", "")).strip()
    validation_status = str(manifest.get("validation_status", "")).strip()
    hard_blocker = manifest.get("hard_blocker")
    issue_count = int(manifest.get("issue_count", 0) or 0)
    write_transaction = manifest.get("write_transaction")
    write_transaction = write_transaction if isinstance(write_transaction, Mapping) else {}
    pre_confirm_write_sealed = (
        str(manifest.get("version", "")).strip() == PRECONFIRM_QUALITY_MANIFEST_VERSION
        and str(manifest.get("engine", "")).strip() == PRECONFIRM_ENGINE_VERSION
        and str(write_transaction.get("status", "")).strip() == "not_started"
        and str(write_transaction.get("rollback_guard", "")).strip() == "enabled"
        and write_transaction.get("prewrite_clean_before_commit") is True
        and "commit_only" not in write_transaction
    )
    requested_tier = str(manifest.get("requested_repair_tier", "")).strip()
    active_tier = str(manifest.get("repair_tier", "")).strip()
    try:
        elapsed_seconds = float(manifest.get("elapsed_seconds"))
        budget_seconds = float(manifest.get("budget_seconds"))
        selected_profile = get_greenfield_model_profile(
            model_profile_id_for_repair_tier(requested_tier)
        )
    except (TypeError, ValueError):
        elapsed_seconds = math.inf
        budget_seconds = -1.0
        selected_profile = None
    tier_route_approved = bool(
        selected_profile is not None
        and active_tier == selected_profile.repair_tier
    )
    timing_approved = (
        tier_route_approved
        and selected_profile is not None
        and budget_seconds == selected_profile.consumer_budget_seconds
        and math.isfinite(elapsed_seconds)
        and 0.0 <= elapsed_seconds < budget_seconds
    )
    semantic_compiler = manifest.get("semantic_compiler")
    semantic_compiler = semantic_compiler if isinstance(semantic_compiler, Mapping) else {}
    raw_model_authoring = manifest.get("model_authoring")
    model_authoring = raw_model_authoring if isinstance(raw_model_authoring, Mapping) else {}
    manifest_claims_authored = str(semantic_compiler.get("semantic_owner", "")).strip() == (
        "validated_model_authored_intent"
    )
    authored_projection = (
        manifest_claims_authored
        if authored_projection_verified is None
        else authored_projection_verified
    )
    authored_manifest_matches_projection = (
        manifest_claims_authored == authored_projection
        and ("model_authoring" in manifest) == authored_projection
    )
    model_authoring_approved = not authored_projection or (
        str(semantic_compiler.get("version", "")).strip()
        == "odylith.greenfield.authored-semantic-validation.v2"
        and str(semantic_compiler.get("status", "")).strip() == "passed"
        and str(model_authoring.get("authoring_version", "")).strip()
        == GREENFIELD_INTENT_AUTHORING_VERSION
        and _semantic_model_call_count_approved(
            model_authoring.get("semantic_model_call_count")
        )
        and _model_authoring_profile_approved(
            model_authoring,
            requested_repair_tier=requested_tier,
        )
        and semantic_compiler.get("post_authoring_interpretation_calls") == 0
    )
    if (
        quality_status == "passed"
        and validation_status in {"", "passed"}
        and not hard_blocker
        and issue_count == 0
        and pre_confirm_write_sealed
        and timing_approved
        and authored_manifest_matches_projection
        and model_authoring_approved
    ):
        return
    raise ValueError(
        "pre-confirm ProductCreateTransaction quality manifest is not approved; "
        "repair or clarify before showing CONFIRM"
    )


def _semantic_model_call_count_approved(value: Any) -> bool:
    return type(value) is int and 1 <= value <= MAX_GREENFIELD_SEMANTIC_CALLS


def _model_authoring_profile_approved(
    model_authoring: Mapping[str, Any],
    *,
    requested_repair_tier: str,
) -> bool:
    raw_observation = model_authoring.get("model_profile")
    observation = raw_observation if isinstance(raw_observation, Mapping) else {}
    if set(observation) != {
        "profile_id",
        "provider",
        "model",
        "reasoning_effort",
        "effective_timeout_seconds",
        "authoring_tier",
    }:
        return False
    profile_id = str(observation.get("profile_id") or "").strip()
    authoring_tier = str(model_authoring.get("tier") or "").strip().casefold()
    if str(observation.get("authoring_tier") or "").strip().casefold() != authoring_tier:
        return False
    try:
        profile = get_greenfield_model_profile(profile_id)
        expected_profile_id = model_profile_id_for_repair_tier(requested_repair_tier)
        observation_issues = greenfield_model_profile_observation_issues(
            profile_id=profile_id,
            provider=str(observation.get("provider") or ""),
            model=str(observation.get("model") or ""),
            reasoning_effort=str(observation.get("reasoning_effort") or ""),
            effective_timeout_seconds=observation.get("effective_timeout_seconds"),
            authoring_tier=str(observation.get("authoring_tier") or ""),
        )
    except (TypeError, ValueError):
        return False
    return (
        profile_id == expected_profile_id
        and authoring_tier == profile.repair_tier
        and not observation_issues
    )


def require_product_create_transaction_verified(transaction: ProductCreateTransaction) -> None:
    """Fail closed when a commit request does not match the compiled package hash."""

    if transaction._compiler_attestation is not _PRODUCT_CREATE_TRANSACTION_COMPILER_ATTESTATION:
        raise ValueError(
            "ProductCreateTransaction was not accepted by the pre-confirm compiler; "
            "compile the transaction before committing governed records"
        )
    require_product_create_transaction_hash_verified(transaction)


def require_product_create_transaction_hash_verified(transaction: ProductCreateTransaction) -> None:
    """Verify serialized transaction integrity without granting compiler custody."""

    require_product_intent_authority(transaction.intent_authority)
    _require_proposal_intent_authority_binding(transaction.proposal, transaction.intent_authority)
    _require_prewrite_package_proposal_binding(
        proposal=transaction.proposal,
        prewrite_package=transaction.prewrite_package,
        authority=transaction.intent_authority,
    )
    expected = product_create_transaction_hash(transaction)
    if transaction.transaction_hash != expected:
        raise ValueError(
            "ProductCreateTransaction hash mismatch; rebuild the transaction before committing governed records"
        )


def _require_proposal_intent_authority_binding(
    proposal: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> bool:
    """Require the sealed facts hash to describe the transaction's typed intent."""

    intent = proposal.get("intent") if isinstance(proposal, Mapping) else None
    if not isinstance(intent, Mapping):
        raise ValueError("ProductCreateTransaction proposal is missing typed Product Intent")
    expected = product_facts_hash(intent)
    actual = str(authority.get(PRODUCT_FACTS_HASH_KEY, "")).strip()
    if actual != expected:
        raise ValueError(
            "ProductCreateTransaction proposal facts do not match its sealed Product Intent authority; "
            "rebuild the transaction before showing CONFIRM"
        )
    relations = require_relation_authority_parity(intent, authority)
    projection_authored = proposal.get("projection_origin") == AUTHORED_PROJECTION_ORIGIN
    if bool(relations) != projection_authored:
        raise ValueError(
            "ProductCreateTransaction authored projection origin does not match sealed relation authority"
        )
    return projection_authored


def build_product_create_transaction_provenance(
    *,
    quality_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "compiler": PRODUCT_CREATE_TRANSACTION_COMPILER,
        "transaction_version": PRODUCT_CREATE_TRANSACTION_VERSION,
        "phase": "pre_confirm_compile",
        "commit_policy": PRODUCT_CREATE_TRANSACTION_COMMIT_POLICY,
        "repository_context_policy": PRODUCT_CREATE_TRANSACTION_REPOSITORY_CONTEXT_POLICY,
        "quality_manifest_version": str(quality_manifest.get("version", "")).strip(),
        "quality_manifest_engine": str(quality_manifest.get("engine", "")).strip(),
        "compiler_identity": product_create_transaction_compiler_identity(),
        "post_confirm_allowed_operations": list(POST_CONFIRM_ALLOWED_OPERATIONS),
        "post_confirm_forbidden_operations": list(POST_CONFIRM_FORBIDDEN_OPERATIONS),
    }


def product_create_transaction_compiler_identity() -> dict[str, Any]:
    return build_product_create_transaction_compiler_identity()


def require_product_create_transaction_compiler_provenance(
    transaction: ProductCreateTransaction,
) -> None:
    provenance = transaction.compiler_provenance if isinstance(transaction.compiler_provenance, Mapping) else {}
    require_product_create_transaction_compiler_provenance_payload(
        provenance,
        quality_manifest=transaction.quality_manifest,
    )


def require_product_create_transaction_intent_authority(
    transaction: ProductCreateTransaction,
    *,
    repo_root: Path,
) -> None:
    """Verify the typed Product Intent custody sealed inside the transaction.

    The post-confirm commit path must not reread mutable confirmation Markdown
    or sidecar JSON. Edits after compilation are new evidence for rebuilding a
    transaction; they are not live authority for an already confirmed hash.
    """

    _ = repo_root
    require_product_intent_authority(transaction.intent_authority)


def product_create_transaction_to_dict(transaction: ProductCreateTransaction) -> dict[str, Any]:
    """Return the persisted transaction payload that a commit-only create can trust."""

    payload = _transaction_hash_payload(transaction)
    payload["transaction_hash"] = str(transaction.transaction_hash or "").strip()
    return payload


def product_create_transaction_from_dict(payload: Mapping[str, Any]) -> ProductCreateTransaction:
    """Rehydrate hash-bound data without granting compiler custody."""

    if not isinstance(payload, Mapping):
        raise ValueError("ProductCreateTransaction payload must be a JSON object")
    version = str(payload.get("version", "")).strip()
    if version != PRODUCT_CREATE_TRANSACTION_VERSION:
        raise ValueError(
            f"unsupported ProductCreateTransaction version {version!r}; expected {PRODUCT_CREATE_TRANSACTION_VERSION}"
        )
    transaction = ProductCreateTransaction(
        version=version,
        release_selector=str(payload.get("release_selector", "")).strip(),
        proposal=mapping_copy(payload.get("proposal")),
        validation_gate=mapping_copy(payload.get("validation_gate")),
        prewrite_package=_completion_package_from_payload(mapping_copy(payload.get("prewrite_package"))),
        backlog_result=_backlog_result_from_payload(mapping_copy(payload.get("backlog_result"))),
        intent_authority=mapping_copy(payload.get("intent_authority")),
        quality_manifest=mapping_copy(payload.get("quality_manifest")),
        compiler_provenance=mapping_copy(payload.get("compiler_provenance")),
        transaction_hash=str(payload.get("transaction_hash", "")).strip(),
    )
    require_product_create_transaction_hash_verified(transaction)
    return transaction


def product_create_transaction_receipt_path(path: Path) -> Path:
    target = Path(path).expanduser()
    return target.with_name(target.name + ".compiler-receipt.v1.json")


def write_compiled_product_create_transaction_file(
    path: Path,
    transaction: ProductCreateTransaction,
) -> Path:
    """Persist a compiled transaction and its detached local-integrity receipt."""

    require_product_create_transaction_verified(transaction)
    target = Path(path).expanduser()
    payload_text = json.dumps(product_create_transaction_to_dict(transaction), indent=2, sort_keys=True) + "\n"
    atomic_write_text(target, payload_text, encoding="utf-8")
    receipt = {
        "version": PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION,
        "transaction_hash": transaction.transaction_hash,
        "transaction_file_sha256": hashlib.sha256(payload_text.encode("utf-8")).hexdigest(),
        "post_confirm_runtime_identity": product_create_transaction_compiler_identity(),
    }
    atomic_write_text(
        product_create_transaction_receipt_path(target),
        canonical_product_create_transaction_receipt_bytes(receipt).decode("utf-8"),
        encoding="utf-8",
    )
    return target


def load_compiled_product_create_transaction_file(path: Path) -> ProductCreateTransaction:
    """Load a transaction whose local receipt still matches its pre-confirm bytes.

    The receipt protects the normal trusted-workspace flow from stale or
    accidental file drift. It is not authentication against the local machine
    owner, who can write the repository without invoking Odylith.
    """

    target = Path(path).expanduser()
    receipt_path = product_create_transaction_receipt_path(target)
    if target.is_symlink() or receipt_path.is_symlink():
        raise ValueError("ProductCreateTransaction file and compiler receipt must not be symlinks")
    try:
        payload_bytes = target.read_bytes()
        receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(
            "ProductCreateTransaction is missing its pre-confirm compiler receipt; "
            "rebuild it with greenfield propose"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "environment/IO failure while reading the pre-confirm ProductCreateTransaction; "
            "no governed records were written"
        ) from exc
    if not isinstance(receipt_payload, Mapping):
        raise ValueError("ProductCreateTransaction compiler receipt must be a JSON object")
    if str(receipt_payload.get("version", "")).strip() != PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION:
        raise ValueError("ProductCreateTransaction compiler receipt has an unsupported version")
    actual_file_hash = hashlib.sha256(payload_bytes).hexdigest()
    if str(receipt_payload.get("transaction_file_sha256", "")).strip() != actual_file_hash:
        raise ValueError("ProductCreateTransaction file does not match its pre-confirm compiler receipt")
    payload = json.loads(payload_bytes.decode("utf-8"))
    transaction = product_create_transaction_from_dict(payload)
    if str(receipt_payload.get("transaction_hash", "")).strip() != transaction.transaction_hash:
        raise ValueError("ProductCreateTransaction hash does not match its pre-confirm compiler receipt")
    attested = replace(
        transaction,
        _compiler_attestation=_PRODUCT_CREATE_TRANSACTION_COMPILER_ATTESTATION,
    )
    require_product_create_transaction_verified(attested)
    return attested


def product_create_transaction_hash(transaction: ProductCreateTransaction) -> str:
    payload = _transaction_hash_payload(transaction)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _transaction_hash_payload(transaction: ProductCreateTransaction) -> dict[str, Any]:
    return {
        "version": transaction.version,
        "release_selector": transaction.release_selector,
        "proposal": _json_ready(transaction.proposal),
        "validation_gate": _json_ready(transaction.validation_gate),
        "prewrite_package": _json_ready(transaction.prewrite_package),
        "backlog_result": _json_ready(transaction.backlog_result),
        "intent_authority": _json_ready(transaction.intent_authority),
        "quality_manifest": _json_ready(transaction.quality_manifest),
        "compiler_provenance": _json_ready(transaction.compiler_provenance),
        "commit_summary": _product_create_transaction_commit_summary(transaction),
    }


def _json_ready(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_ready({field.name: getattr(value, field.name) for field in fields(value)})
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value, key=lambda item: str(item)):
            key_text = str(key)
            if key_text in _VOLATILE_HASH_KEYS:
                continue
            result[key_text] = _json_ready(value[key])
        return result
    if isinstance(value, set):
        return sorted(_json_ready(item) for item in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return _json_ready(value.as_dict())
    if hasattr(value, "__dict__") and value.__class__.__module__.startswith("odylith."):
        return _json_ready(vars(value))
    return value


def _backlog_result_from_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    result = dict(payload)
    candidate_specs = result.get("_candidate_idea_specs")
    if isinstance(candidate_specs, Mapping):
        result["_candidate_idea_specs"] = {
            str(idea_id): _idea_spec_from_payload(spec)
            for idea_id, spec in candidate_specs.items()
            if isinstance(spec, Mapping)
        }
    return result


def _idea_spec_from_payload(payload: Mapping[str, Any]) -> backlog_contract.IdeaSpec:
    return backlog_contract.IdeaSpec(
        path=Path(str(payload.get("path", ""))),
        metadata={str(key): str(value) for key, value in mapping_copy(payload.get("metadata")).items()},
        sections={str(value) for value in _sequence(payload.get("sections"))},
        section_bodies={str(key): str(value) for key, value in mapping_copy(payload.get("section_bodies")).items()},
    )


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else ()


def _completion_package_from_payload(payload: Mapping[str, Any]) -> GreenfieldCompletionPackage:
    allowed = {field.name for field in fields(GreenfieldCompletionPackage)}
    kwargs = {key: payload[key] for key in allowed if key in payload}
    for tuple_key in (
        "component_registry_preview",
        "atlas_diagram_ids",
        "atlas_catalog_rows",
        "release_workstream_ids",
    ):
        if tuple_key in kwargs and isinstance(kwargs[tuple_key], list):
            kwargs[tuple_key] = tuple(kwargs[tuple_key])
    if isinstance(kwargs.get("traceability_plan"), Mapping):
        kwargs["traceability_plan"] = greenfield_traceability.traceability_plan_from_payload(
            kwargs["traceability_plan"]
        )
    if isinstance(kwargs.get("backlog_result"), Mapping):
        kwargs["backlog_result"] = _backlog_result_from_payload(kwargs["backlog_result"])
    return GreenfieldCompletionPackage(**kwargs)


__all__ = [
    "PRODUCT_CREATE_TRANSACTION_VERSION",
    "PRODUCT_CREATE_TRANSACTION_COMPILER",
    "PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION",
    "PRODUCT_CREATE_TRANSACTION_RECEIPT_VERSION",
    "ProductCreateTransaction",
    "build_product_create_transaction",
    "build_product_create_transaction_provenance",
    "product_create_transaction_compiler_identity",
    "product_create_transaction_from_dict",
    "product_create_transaction_receipt_path",
    "product_create_transaction_hash",
    "product_create_transaction_to_dict",
    "require_product_create_transaction_quality_approved",
    "require_product_create_transaction_compiler_provenance",
    "require_product_create_transaction_intent_authority",
    "require_product_create_transaction_verified",
    "load_compiled_product_create_transaction_file",
    "write_compiled_product_create_transaction_file",
]

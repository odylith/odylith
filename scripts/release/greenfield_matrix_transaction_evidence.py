"""Capture the sealed pre-confirm transaction that an installed matrix case commits."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace
from typing import Any


DRY_RUN_RECEIPT_VERSION = "odylith.greenfield.matrix.dry-run-receipt.v1"
POST_CONFIRM_NAVIGATION = {
    "project": "odylith/index.html?tab=project",
    "radar": "odylith/index.html?tab=radar",
    "registry": "odylith/index.html?tab=registry",
    "atlas": "odylith/index.html?tab=atlas",
    "compass": "odylith/index.html?tab=compass&date=live",
}
SEMANTIC_FACT_KEYS = (
    "product_story",
    "state_object",
    "first_path",
    "proof_boundary",
    "problem",
    "customer",
    "opportunity",
    "product_view",
    "success_metrics",
    "component_responsibilities",
    "human_actors",
    "external_systems",
    "internal_systems",
    "assumptions",
    "ambiguities",
    "non_goals",
    "evidence_requirements",
    "operational_constraints",
)


@dataclass(frozen=True)
class CompiledCreateExecution:
    """The commit result and immutable transaction facts captured before that commit."""

    create: Any
    create_seconds: float
    dry_run_receipt: Mapping[str, Any]
    proposal_payload: Mapping[str, Any]


def commit_precompiled_transaction(
    *,
    repo_root: Path,
    proposed: Any,
    invoke_create: Callable[[Sequence[str]], Any],
) -> CompiledCreateExecution:
    """Validate a proposed transaction receipt before invoking commit-only create."""

    try:
        proposal_returncode = int(getattr(proposed, "returncode", 1))
    except (TypeError, ValueError):
        proposal_returncode = 1
    proposed_payload = _json_mapping(getattr(proposed, "stdout", ""))
    if proposal_returncode != 0:
        return CompiledCreateExecution(proposed, 0.0, _receipt(status="proposal_failed"), proposed_payload)
    proposal_mode = str(proposed_payload.get("mode") or "").strip()
    if proposal_mode == "clarification_required":
        return CompiledCreateExecution(
            SimpleNamespace(
                returncode=2,
                stdout=getattr(proposed, "stdout", ""),
                stderr="greenfield proposal requires a material clarification before compiling a transaction",
            ),
            0.0,
            _receipt(status="clarification_required", proposal_mode=proposal_mode),
            proposed_payload,
        )
    summary = _mapping(proposed_payload.get("product_create_transaction"))
    transaction_hash = str(summary.get("transaction_hash") or "").strip()
    transaction_file = str(proposed_payload.get("transaction_file") or "").strip()
    if proposal_mode != "product_create_transaction" or not transaction_hash or not transaction_file:
        return CompiledCreateExecution(
            _error_result("greenfield propose did not return a ProductCreateTransaction hash and transaction file"),
            0.0,
            _receipt(status="proposal_contract_failed", proposal_mode=proposal_mode),
            proposed_payload,
        )
    receipt, issues = _sealed_dry_run_receipt(
        repo_root=repo_root,
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
        proposal_mode=proposal_mode,
    )
    if issues:
        return CompiledCreateExecution(
            _error_result("greenfield propose returned an invalid pre-confirm transaction: " + "; ".join(issues)),
            0.0,
            receipt,
            proposed_payload,
        )
    started = time.perf_counter()
    create = invoke_create(
        (
            "./.odylith/bin/odylith",
            "greenfield",
            "create",
            "--repo-root",
            ".",
            "--transaction-file",
            transaction_file,
            "--transaction-hash",
            transaction_hash,
            "--confirm",
            "--json",
        )
    )
    return CompiledCreateExecution(create, round(time.perf_counter() - started, 3), receipt, proposed_payload)


def confirmation_preview_issues(*, proposal_payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Require a readable, hash-bound decision rail before the matrix commits it."""

    transaction = _mapping(proposal_payload.get("product_create_transaction"))
    transaction_hash = str(transaction.get("transaction_hash") or "").strip()
    confirmation = _mapping(proposal_payload.get("confirmation"))
    choices = confirmation.get("choices")
    issues: list[str] = []
    if str(proposal_payload.get("mode") or "").strip() != "product_create_transaction":
        issues.append("pre-confirm payload did not expose a ProductCreateTransaction")
    if not _is_sha256(transaction_hash):
        issues.append("pre-confirm payload is missing a valid transaction hash")
    if not str(proposal_payload.get("transaction_file") or "").strip():
        issues.append("pre-confirm payload is missing its transaction file")
    if str(confirmation.get("command_rule") or "").strip() != (
        "Use exactly one hash-bound command: CONFIRM, EDIT, or REJECT."
    ):
        issues.append("pre-confirm payload does not state the one-command decision rule")
    if not isinstance(choices, list):
        issues.append("pre-confirm payload is missing the CONFIRM, EDIT, and REJECT choices")
        return tuple(issues)
    expected_commands = [
        f"CONFIRM {transaction_hash}",
        f"EDIT {transaction_hash} <corrections>",
        f"REJECT {transaction_hash}",
    ]
    commands = [str(_mapping(choice).get("command") or "").strip() for choice in choices]
    if commands != expected_commands:
        issues.append("pre-confirm payload does not present CONFIRM, EDIT, and REJECT as distinct ordered choices")
        return tuple(issues)
    choice_by_command = {str(_mapping(choice).get("command") or "").strip(): _mapping(choice) for choice in choices}
    confirm = choice_by_command[expected_commands[0]]
    edit = choice_by_command[expected_commands[1]]
    reject = choice_by_command[expected_commands[2]]
    commit_command = str(confirm.get("commit_command") or "").strip()
    if transaction_hash not in commit_command or "--confirm" not in commit_command:
        issues.append("CONFIRM does not name the exact hash-bound commit command")
    if "exact validated package" not in str(confirm.get("description") or "").casefold():
        issues.append("CONFIRM does not explain that it commits the validated package")
    edit_text = " ".join(str(edit.get(key) or "") for key in ("description",))
    if "new evidence" not in edit_text.casefold() or "rebuild" not in edit_text.casefold():
        issues.append("EDIT does not explain that corrections are rebuilt as new evidence")
    if "no governed records" not in str(reject.get("description") or "").casefold():
        issues.append("REJECT does not clearly promise no governed writes")
    contract = str(confirmation.get("post_confirm_contract") or "").casefold()
    for required_phrase in ("hash", "compiler receipt", "repo preconditions", "sealed bytes", "rollback", "readback"):
        if required_phrase not in contract:
            issues.append(f"pre-confirm post-confirm contract omits `{required_phrase}`")
    return tuple(issues)


def post_confirm_navigation_issues(
    *,
    create_payload: Mapping[str, Any],
    repo_root: Path,
    transaction_hash: str,
) -> tuple[str, ...]:
    """Require committed navigation plus hash-bound reviewed-generation audit routes."""

    navigation = _mapping(create_payload.get("post_confirm_navigation"))
    missing = [key for key, value in POST_CONFIRM_NAVIGATION.items() if navigation.get(key) != value]
    root = Path(repo_root).expanduser().resolve()
    committed_dashboard = (root / "odylith/index.html").resolve()
    reviewed_generation = (
        root
        / ".odylith/runtime/greenfield/generations"
        / transaction_hash
    ).resolve()
    reviewed_dashboard = (
        reviewed_generation
        / "repository/odylith/index.html"
    ).resolve()
    expected = {
        "dashboard_path": str(committed_dashboard),
        "project_url": f"{committed_dashboard.as_uri()}?tab=project",
        "view_status": "committed_repository",
        "compatibility_dashboard_path": str(committed_dashboard),
        "generation_transaction_hash": transaction_hash,
        "reviewed_generation_path": str(reviewed_generation),
        "reviewed_generation_dashboard_path": str(reviewed_dashboard),
        "reviewed_generation_project_url": f"{reviewed_dashboard.as_uri()}?tab=project",
    }
    missing.extend(key for key, value in expected.items() if navigation.get(key) != value)
    if not committed_dashboard.is_file():
        missing.append("dashboard_target")
    if not reviewed_dashboard.is_file():
        missing.append("reviewed_generation_dashboard_target")
    if missing:
        return (
            "post-confirm response does not expose committed workspace and reviewed-generation audit routes: "
            + ", ".join(dict.fromkeys(missing)),
        )
    return ()


def dry_run_commit_issues(*, receipt: Mapping[str, Any], create_payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Require the successful create readback to match the receipt captured before confirmation."""

    if str(receipt.get("status") or "") != "compiled":
        return ("pre-confirm dry-run receipt was not compiled before commit",)
    expected = str(receipt.get("transaction_hash") or "").strip()
    if not _is_sha256(expected):
        return ("pre-confirm dry-run receipt is missing a valid transaction hash",)
    manifest = _mapping(create_payload.get("commit_manifest"))
    write_transaction = _mapping(manifest.get("write_transaction"))
    manifest_transaction = _mapping(manifest.get("product_create_transaction"))
    observed = (
        str(write_transaction.get("product_create_transaction_hash") or "").strip(),
        str(manifest_transaction.get("transaction_hash") or "").strip(),
    )
    issues = [
        "commit readback does not match the pre-confirm transaction hash"
        for value in observed
        if value != expected
    ]
    return tuple(dict.fromkeys(issues))


def _sealed_dry_run_receipt(
    *,
    repo_root: Path,
    transaction_file: str,
    transaction_hash: str,
    proposal_mode: str,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    receipt = _receipt(
        status="invalid",
        proposal_mode=proposal_mode,
        transaction_file=transaction_file,
        transaction_hash=transaction_hash,
    )
    transaction_path, path_issue = _repo_path(repo_root, transaction_file)
    if path_issue:
        return receipt, (path_issue,)
    compiler_receipt_path = transaction_path.with_name(transaction_path.name + ".compiler-receipt.v1.json")
    try:
        transaction_bytes = transaction_path.read_bytes()
        compiler_receipt_bytes = compiler_receipt_path.read_bytes()
    except OSError as error:
        return receipt, (f"pre-confirm transaction receipt is unavailable: {error}",)
    transaction = _json_mapping(transaction_bytes)
    compiler_receipt = _json_mapping(compiler_receipt_bytes)
    transaction_file_sha256 = hashlib.sha256(transaction_bytes).hexdigest()
    compiler_receipt_sha256 = hashlib.sha256(compiler_receipt_bytes).hexdigest()
    quality_manifest = _mapping(transaction.get("quality_manifest"))
    semantic_snapshot = _semantic_snapshot(transaction)
    receipt.update(
        {
            "transaction_file": str(transaction_path.relative_to(Path(repo_root).resolve())),
            "transaction_file_sha256": transaction_file_sha256,
            "compiler_receipt_file": str(compiler_receipt_path.relative_to(Path(repo_root).resolve())),
            "compiler_receipt_sha256": compiler_receipt_sha256,
            "compiler_receipt_transaction_hash": str(compiler_receipt.get("transaction_hash") or "").strip(),
            "preconfirm_quality_status": str(quality_manifest.get("status") or "").strip(),
            "preconfirm_validation_status": str(quality_manifest.get("validation_status") or "").strip(),
            "semantic_snapshot": semantic_snapshot,
            "semantic_snapshot_sha256": _sha256_json(semantic_snapshot) if semantic_snapshot else "",
        }
    )
    issues: list[str] = []
    declared_transaction_hash = str(transaction.get("transaction_hash") or "").strip()
    body_transaction_hash = _sha256_json(
        {
            key: value
            for key, value in transaction.items()
            if key != "transaction_hash"
        }
    )
    if declared_transaction_hash != transaction_hash:
        issues.append("transaction file hash does not match the propose response")
    if declared_transaction_hash != body_transaction_hash:
        issues.append("transaction body does not match its declared transaction hash")
    if str(compiler_receipt.get("transaction_hash") or "").strip() != transaction_hash:
        issues.append("compiler receipt hash does not match the propose response")
    if str(compiler_receipt.get("transaction_file_sha256") or "").strip() != transaction_file_sha256:
        issues.append("compiler receipt file digest does not match the transaction bytes")
    if receipt["preconfirm_quality_status"] != "passed":
        issues.append("pre-confirm transaction quality is not passed")
    if receipt["preconfirm_validation_status"] != "passed":
        issues.append("pre-confirm transaction validation is not passed")
    if not semantic_snapshot:
        issues.append("pre-confirm transaction does not expose canonical semantic facts")
    if issues:
        return receipt, tuple(issues)
    receipt["status"] = "compiled"
    return receipt, ()


def _receipt(*, status: str, **values: Any) -> dict[str, Any]:
    return {"version": DRY_RUN_RECEIPT_VERSION, "status": status, **values}


def _semantic_snapshot(transaction: Mapping[str, Any]) -> dict[str, Any]:
    proposal = _mapping(transaction.get("proposal"))
    intent = _mapping(proposal.get("intent"))
    facts = {
        key: intent[key]
        for key in SEMANTIC_FACT_KEYS
        if key in intent and _has_semantic_value(intent.get(key))
    }
    if not all(key in facts for key in ("product_story", "state_object", "first_path", "proof_boundary")):
        return {}
    authority = _mapping(transaction.get("intent_authority"))
    material_fields = _mapping(authority.get("material_fields"))
    atomic_facts = [dict(row) for row in authority.get("atomic_facts", ()) if isinstance(row, Mapping)]
    custody = {
        key: {
            "custody_state": str(_mapping(value).get("custody_state") or "").strip(),
            "entailment_relationship": str(_mapping(value).get("entailment_relationship") or "").strip(),
        }
        for key, value in sorted(material_fields.items())
        if isinstance(value, Mapping)
    }
    return {
        "facts": facts,
        "material_custody": custody,
        "atomic_facts": atomic_facts,
        "atomic_custody_sha256": str(authority.get("atomic_custody_sha256") or "").strip(),
        "product_facts_sha256": str(authority.get("product_facts_sha256") or "").strip(),
    }


def _has_semantic_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value)
    return isinstance(value, Mapping) and bool(value)


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _repo_path(repo_root: Path, token: str) -> tuple[Path, str]:
    root = Path(repo_root).resolve()
    candidate = (root / token).resolve() if not Path(token).is_absolute() else Path(token).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return candidate, "pre-confirm transaction path escapes the case repository"
    return candidate, ""


def _error_result(message: str) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=2,
        stdout=json.dumps({"mode": "error", "error": message}, sort_keys=True),
        stderr="",
    )


def _json_mapping(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8") if isinstance(value, bytes) else str(value or ""))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return _mapping(parsed)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


__all__ = [
    "DRY_RUN_RECEIPT_VERSION",
    "SEMANTIC_FACT_KEYS",
    "CompiledCreateExecution",
    "commit_precompiled_transaction",
    "dry_run_commit_issues",
]

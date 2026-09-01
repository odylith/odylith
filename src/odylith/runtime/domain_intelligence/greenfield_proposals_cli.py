"""CLI adapter for confirmed greenfield proposal commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import replace
import json
from pathlib import Path
import shlex
import time
from typing import Any, Mapping

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import GreenfieldClarificationRequired
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    require_product_create_transaction_quality_approved,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    require_product_create_transaction_verified,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import materialize_model_authored_intent
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import render_product_intent_preview
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    model_profile_id_for_repair_tier,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import MAX_EVIDENCE_BYTES
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import GreenfieldPreconfirmEngineError
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_REPAIR_TIERS
from odylith.runtime.project_intelligence.intent_confirmation import format_confirmation_choice_lines
from odylith.runtime.reasoning import odylith_reasoning


_PUBLIC_INTENT_AUTHORITY_SUMMARY_VERSION = "odylith.product-intent-authority-summary.v1"
_PUBLIC_INTENT_AUTHORITY_SUMMARY_KEYS = (
    "product_facts_sha256",
    "source_format",
    "materiality_status",
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith greenfield",
        description="Preview and commit confirmation-gated greenfield product records.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser("propose", help="Preview a confirmation-gated greenfield product proposal.")
    propose.add_argument("--repo-root", default=".")
    propose.add_argument("--prompt", required=True)
    propose.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    propose.add_argument(
        "--edit",
        default="",
        help="New product evidence after EDIT. It rebuilds a staged transaction and never writes governed records.",
    )
    propose.add_argument(
        "--edit-evidence",
        default="",
        help="Path to Markdown or text edit evidence. The contents are untrusted evidence, not product truth.",
    )
    propose.add_argument(
        "--detail",
        choices=("brief", "full"),
        default="brief",
        help="Reserved preview depth selector. `propose` always compiles the full staged transaction before the final rail.",
    )
    propose.add_argument(
        "--repair-tier",
        choices=PRECONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_PRECONFIRM_REPAIR_TIER,
        help=(
            "Proposal budget: auto/standard use the pinned under-60s profile; rescue and deep are explicit "
            "pinned under-90s and under-120s profiles."
        ),
    )
    propose.add_argument(
        "--evidence-language",
        choices=("en",),
        default="en",
        help="Declared language of prompt and EDIT evidence. Greenfield v3 currently supports English evidence.",
    )
    propose.add_argument(
        "--confirm-intent",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    propose.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help=argparse.SUPPRESS,
    )
    apply = subparsers.add_parser(
        "apply",
        help="Legacy proposal apply is disabled; use propose, then hash-bound create.",
        description="Legacy proposal apply is disabled; use propose, then hash-bound create.",
    )
    apply.add_argument("--repo-root", default=".")
    apply.add_argument("--proposal-file", default="")
    apply.add_argument("--proposal-json", default="")
    apply.add_argument("--confirm", action="store_true")
    apply.add_argument("--release", default="")
    apply.add_argument(
        "--repair-tier",
        choices=PRECONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_PRECONFIRM_REPAIR_TIER,
        help=(
            "Create-transaction compiler budget: auto/standard use the pinned under-60s profile; rescue and "
            "deep are explicit pinned under-90s and under-120s profiles."
        ),
    )
    apply.add_argument("--json", action="store_true", dest="as_json")
    compile_transaction = subparsers.add_parser(
        "compile-transaction",
        help="Compile a no-write ProductCreateTransaction for controlled tooling; normal product flow uses propose.",
    )
    compile_transaction.add_argument("--repo-root", default=".")
    compile_transaction.add_argument("--prompt", required=True)
    compile_transaction.add_argument("--edit", default="", help=argparse.SUPPRESS)
    compile_transaction.add_argument("--edit-evidence", default="", help=argparse.SUPPRESS)
    compile_transaction.add_argument(
        "--evidence-language",
        choices=("en",),
        default="en",
        help=argparse.SUPPRESS,
    )
    compile_transaction.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help=argparse.SUPPRESS,
    )
    compile_transaction.add_argument("--release", default="")
    compile_transaction.add_argument(
        "--repair-tier",
        choices=PRECONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_PRECONFIRM_REPAIR_TIER,
        help=(
            "Create-transaction compiler budget: auto/standard use the pinned under-60s profile; rescue and "
            "deep are explicit pinned under-90s and under-120s profiles."
        ),
    )
    compile_transaction.add_argument(
        "--output",
        default="",
        help="Optional path for the compiled transaction JSON. Omit to print only the confirmation view.",
    )
    compile_transaction.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    return parser.parse_args(argv)


def _legacy_apply_disabled_error() -> str:
    return (
        "greenfield apply is disabled for confirmed writes. Confirm now commits only an already compiled "
        "ProductCreateTransaction. Run `odylith greenfield propose --repo-root . --prompt <request>`, then run `odylith greenfield create "
        "--repo-root . --transaction-file .odylith/runtime/greenfield/pending/<hash>/product-create-transaction.v1.json "
        "--transaction-hash <hash> --confirm`. No governed records were written."
    )


def _transaction_confirmation_payload(
    *,
    transaction: Any,
    output_path: str = "",
) -> dict[str, Any]:
    summary = transaction.summary()
    transaction_hash = str(summary["transaction_hash"])
    transaction_ref = shlex.quote(output_path or "<compiled-transaction.json>")
    commit_command = (
        "odylith greenfield create --repo-root . "
        f"--transaction-file {transaction_ref} "
        f"--transaction-hash {summary['transaction_hash']} --confirm"
    )
    return {
        "command_rule": "Use exactly one hash-bound command: CONFIRM, EDIT, or REJECT.",
        "first_word_rule": "The transaction hash is part of the command and binds the decision to these reviewed bytes.",
        "edit_rule": "For EDIT, put corrections after the hash so Odylith can rebuild from the new evidence.",
        "post_confirm_contract": (
            "CONFIRM commits only this hash-bound transaction; commit-only create verifies the hash, "
            "compiler receipt, and repo preconditions, writes only sealed bytes under the rollback "
            "guard, validates readback, and reports success or environment/IO failure."
        ),
        "choices": [
            {
                "command": f"CONFIRM {transaction_hash}",
                "description": "Commit this exact validated package now. Odylith verifies the hash and repo "
                "preconditions, writes the sealed bytes, and validates readback. No product reinterpretation, "
                "repair, or generation runs after CONFIRM.",
                "commit_command": commit_command,
            },
            {
                "command": f"EDIT {transaction_hash} <corrections>",
                "description": "Do not commit. Replace <corrections> with your changes; Odylith treats them as new "
                "evidence, rebuilds the package, and uses the new hash.",
            },
            {
                "command": f"REJECT {transaction_hash}",
                "description": "Stop this exact pending package. No governed records are written.",
            },
        ],
        "confirm": f"CONFIRM {transaction_hash}",
        "edit": f"EDIT {transaction_hash} <corrections>",
        "reject": f"REJECT {transaction_hash}",
    }


def _transaction_confirmation_text(
    *,
    transaction: Any,
    output_path: str = "",
) -> str:
    summary = transaction.summary()
    manifest = transaction.quality_manifest if isinstance(transaction.quality_manifest, Mapping) else {}
    intent_authority = transaction.intent_authority if isinstance(transaction.intent_authority, Mapping) else {}
    package = transaction.prewrite_package
    backlog_result = package.backlog_result if isinstance(package.backlog_result, Mapping) else {}
    created = backlog_result.get("created") if isinstance(backlog_result.get("created"), list) else []
    components = package.component_registry_preview if isinstance(package.component_registry_preview, tuple) else ()
    diagrams = package.rendered_atlas_sources if isinstance(package.rendered_atlas_sources, Mapping) else {}
    confirmation = _transaction_confirmation_payload(transaction=transaction, output_path=output_path)
    lines = [
        "ProductCreateTransaction ready for final command",
        f"- transaction hash: {summary['transaction_hash']}",
        f"- product facts hash: {intent_authority.get('product_facts_sha256', '')}",
        f"- quality gate: {summary.get('quality_status') or manifest.get('status', 'unknown')}",
        f"- validation gate: {summary.get('validation_status') or manifest.get('validation_status', 'unknown')}",
        f"- governed package: {len(created)} workstreams, {len(components)} component previews, {len(diagrams)} Atlas previews",
        f"- sealed commit: {summary.get('repository_write_count', 0)} exact file writes, "
        f"{summary.get('repository_delete_count', 0)} deletions, and hashed repo preconditions",
        "- commands below include this exact transaction hash; copy CONFIRM or REJECT unchanged, or replace the "
        "EDIT corrections placeholder",
        "",
        *format_confirmation_choice_lines(
            tuple(
                (
                    str(choice["command"]),
                    (
                        f"{choice['description']} Run `{choice['commit_command']}`"
                        if str(choice["command"]).startswith("CONFIRM ")
                        else str(choice["description"])
                    ),
                )
                for choice in confirmation["choices"]
            )
        ),
    ]
    if output_path:
        lines.insert(1, f"- transaction file: {output_path}")
    return "\n".join(lines).rstrip() + "\n"


def _print_greenfield_error(exc: Exception, *, as_json: bool) -> None:
    if as_json:
        payload: dict[str, Any] = {"mode": "error", "error": str(exc)}
        if isinstance(exc, GreenfieldPreconfirmEngineError):
            payload["commit_manifest"] = exc.manifest
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(str(exc))


def _print_greenfield_clarification(exc: GreenfieldClarificationRequired, *, as_json: bool) -> None:
    clarification = {
        "question": exc.question,
        "required_fields": list(exc.required_fields),
    }
    model_profile = exc.authoring_receipt.get("model_profile")
    if isinstance(model_profile, Mapping):
        clarification["model_profile"] = dict(model_profile)
    consistency = exc.authoring_receipt.get("consistency_assessment")
    if isinstance(consistency, Mapping):
        clarification["consistency_assessment"] = dict(consistency)
    if as_json:
        print(json.dumps({"mode": "clarification_required", "clarification": clarification}, indent=2, sort_keys=True))
        return
    print("Odylith needs one product decision.")
    print(exc.question)
    print("Reply with one plain-language sentence. No transaction or governed records were created.")


def _transaction_output_path(*, repo_root: Path, output_path: str) -> Path | None:
    value = str(output_path or "").strip()
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else repo_root / path


def _finish_clarification(
    *,
    exc: GreenfieldClarificationRequired,
    as_json: bool,
) -> int:
    _print_greenfield_clarification(exc, as_json=as_json)
    return 0


def _edit_evidence_from_args(args: argparse.Namespace, *, repo_root: Path) -> str:
    inline = str(getattr(args, "edit", "") or "").strip()
    evidence_file = str(getattr(args, "edit_evidence", "") or "").strip()
    if inline and evidence_file:
        raise ValueError("use either --edit or --edit-evidence, not both")
    if not evidence_file:
        return inline
    path = Path(evidence_file).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    try:
        with path.open("rb") as handle:
            payload = handle.read(MAX_EVIDENCE_BYTES + 1)
    except OSError as exc:
        raise RuntimeError("environment/IO failure while reading EDIT evidence") from exc
    if len(payload) > MAX_EVIDENCE_BYTES:
        raise ValueError("Greenfield EDIT evidence exceeds the declared model-input bound")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Greenfield EDIT evidence must be valid UTF-8 text") from exc


def _compile_prompt_evidence_transaction(
    *,
    repo_root: Path,
    prompt: str,
    edit_evidence: str,
    release_selector: str,
    repair_tier: str = "",
    source_language: str = "en",
    started_at: float | None = None,
    clock: Callable[[], float] | None = None,
) -> tuple[dict[str, Any], Any, Path]:
    now = clock or time.perf_counter
    started = now() if started_at is None else float(started_at)
    requested_tier = str(repair_tier or greenfield_proposals.DEFAULT_PRECONFIRM_REPAIR_TIER).strip().casefold()
    prepared_evidence = prepare_model_authoring_evidence(
        prompt=prompt,
        edit_evidence=edit_evidence,
        source_language=source_language,
    )
    profile_id = model_profile_id_for_repair_tier(requested_tier)
    profile = get_greenfield_model_profile(profile_id)
    if profile.model_timeout_seconds - max(0.0, now() - started) < 1.0:
        raise RuntimeError(
            "Greenfield proposal exhausted its shared time budget while reading evidence; no records were created."
        )
    provider_result = _greenfield_authoring_provider(
        repo_root=repo_root,
        profile_id=profile_id,
    )
    provider = provider_result[0]
    model = profile.model
    reasoning_effort = profile.reasoning_effort
    authoring_timeout_seconds = profile.model_timeout_seconds - max(0.0, now() - started)
    if authoring_timeout_seconds < 1.0:
        raise RuntimeError(
            "Greenfield proposal exhausted its shared time budget during provider setup; no records were created."
        )
    authoring_receipt: dict[str, Any] = {}
    candidate_intent = materialize_model_authored_intent(
        prompt=prompt,
        repo_root=repo_root,
        edit_evidence=edit_evidence,
        authoring_provider=provider,
        authoring_timeout_seconds=authoring_timeout_seconds,
        authoring_model=model,
        authoring_reasoning_effort=reasoning_effort,
        authoring_profile_id=profile_id,
        source_language=source_language,
        prepared_evidence=prepared_evidence,
        authoring_receipt=authoring_receipt,
    )
    authoring_tier = str(authoring_receipt.get("tier") or "").strip()
    if authoring_tier not in {"standard", "rescue", "deep"}:
        raise RuntimeError(
            "Greenfield did not receive a valid source-cited authoring receipt; no records were created."
        )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=repo_root,
        prompt=prompt,
        confirmed_intent=candidate_intent,
        require_completion_ready=False,
    )
    candidate_authority = candidate_intent.get("product_intent_authority")
    if not isinstance(candidate_authority, Mapping):
        raise RuntimeError("pre-confirm typed Product Intent authority is missing")
    proposal = dict(proposal)
    proposal["product_intent_authority"] = candidate_authority
    elapsed_before_preconfirm_seconds = max(0.0, now() - started)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=repo_root,
        proposal=proposal,
        release_selector=release_selector,
        proposal_ready=True,
        preconfirm_elapsed_seconds=elapsed_before_preconfirm_seconds,
        model_authoring_tier=authoring_tier,
        model_authoring_receipt=authoring_receipt,
        **({"repair_tier": repair_tier} if repair_tier else {}),
    )
    candidate_intent = dict(transaction.proposal.get("intent") or {})
    candidate_intent["product_intent_authority"] = transaction.intent_authority
    candidate_authority = candidate_intent.get("product_intent_authority")
    transaction_authority = transaction.intent_authority if isinstance(transaction.intent_authority, Mapping) else {}
    if not isinstance(candidate_authority, Mapping) or (
        str(candidate_authority.get("product_facts_sha256", "")).strip()
        != str(transaction_authority.get("product_facts_sha256", "")).strip()
    ):
        raise RuntimeError(
            "pre-confirm compiler produced a transaction whose product facts do not match the visible typed preview"
        )
    quality_manifest = dict(transaction.quality_manifest)
    quality_manifest["elapsed_seconds"] = round(max(0.0, now() - started), 3)
    transaction = replace(transaction, quality_manifest=quality_manifest)
    require_product_create_transaction_quality_approved(transaction.quality_manifest)
    require_product_create_transaction_verified(transaction)
    transaction_path = _stage_pending_transaction_with_deadline(
        repo_root=repo_root,
        transaction=transaction,
        started_at=started,
        clock=now,
    )
    return candidate_intent, transaction, transaction_path


def _stage_pending_transaction_with_deadline(
    *,
    repo_root: Path,
    transaction: Any,
    started_at: float,
    clock: Callable[[], float],
) -> Path:
    """Publish only while the sealed consumer deadline remains valid."""

    budget_seconds = float(transaction.quality_manifest.get("budget_seconds") or 0.0)
    if max(0.0, clock() - started_at) >= budget_seconds:
        raise RuntimeError("Greenfield proposal exceeded its sealed repair-tier time budget; no records were created.")
    pending_directory = greenfield_pending_transaction_store.pending_transaction_directory(
        repo_root,
        transaction.transaction_hash,
    )
    pending_preexisted = pending_directory.exists()
    transaction_path = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=repo_root,
        transaction=transaction,
    )
    final_elapsed_seconds = max(0.0, clock() - started_at)
    if final_elapsed_seconds >= budget_seconds:
        if not pending_preexisted:
            try:
                greenfield_pending_transaction_store.discard_pending_transaction(
                    repo_root=repo_root,
                    transaction_hash=transaction.transaction_hash,
                )
            except (OSError, RuntimeError, ValueError) as exc:
                raise RuntimeError(
                    "Greenfield proposal exceeded its sealed repair-tier time budget and its pending transaction could not be retired; do not confirm it."
                ) from exc
        raise RuntimeError("Greenfield proposal exceeded its sealed repair-tier time budget; no records were created.")
    return transaction_path


def _greenfield_authoring_provider(*, repo_root: Path, profile_id: str) -> tuple[Any, str, str]:
    """Resolve the single semantic authoring call for a Greenfield proposal.

    Greenfield never falls back to lexical inference when this provider is not
    available. The generic reasoning layer owns host selection; this adapter
    only pins the authoring request to its declared single-call budget.
    """

    profile = get_greenfield_model_profile(profile_id)
    configured = odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    config = replace(
        configured,
        provider=profile.provider,
        model=profile.model,
        codex_reasoning_effort=profile.reasoning_effort,
    )
    provider = odylith_reasoning.provider_from_config(
        config,
        repo_root=repo_root,
        require_auto_mode=True,
        allow_implicit_local_provider=True,
    )
    if provider is None:
        raise RuntimeError(
            "A verified source-cited Greenfield package could not be produced because model authoring is unavailable; "
            "no records were created."
        )
    return provider, profile.model, profile.reasoning_effort


def _public_intent_hypothesis(candidate_intent: Mapping[str, Any]) -> dict[str, Any]:
    """Return typed Product Intent without exposing the private custody receipt."""

    visible = dict(candidate_intent)
    authority = visible.pop("product_intent_authority", None)
    if isinstance(authority, Mapping):
        visible["product_intent_authority_summary"] = {
            "schema_version": _PUBLIC_INTENT_AUTHORITY_SUMMARY_VERSION,
            "authority_version": str(authority.get("version", "")).strip(),
            **{
                key: authority[key]
                for key in _PUBLIC_INTENT_AUTHORITY_SUMMARY_KEYS
                if str(authority.get(key, "")).strip()
            },
        }
    return visible


def _retired_intent_file_message() -> str:
    return (
        "The separate Product Intent confirmation flow is retired. `propose` now compiles the typed evidence and "
        "full ProductCreateTransaction before it shows the only CONFIRM rail. Use `--edit` or `--edit-evidence` "
        "to rebuild from corrections; edited Markdown is evidence, never a confirmed product source."
    )


def main(argv: Sequence[str] | None = None) -> int:
    tokens = [str(token) for token in (argv or ())]
    if tokens[:1] == ["create"]:
        from odylith.runtime.domain_intelligence.greenfield_create_cli import main as create_main

        return create_main(tokens)
    args = _parse_args(tokens)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if args.command == "propose":
        if bool(args.confirm_intent) or str(args.intent_file or "").strip():
            _print_greenfield_error(ValueError(_retired_intent_file_message()), as_json=args.output_format == "json")
            return 2
        try:
            started_at = time.perf_counter()
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            candidate_intent, transaction, transaction_path = _compile_prompt_evidence_transaction(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector="",
                edit_evidence=edit_evidence,
                repair_tier=str(args.repair_tier),
                source_language=str(args.evidence_language),
                started_at=started_at,
            )
        except GreenfieldClarificationRequired as exc:
            return _finish_clarification(exc=exc, as_json=args.output_format == "json")
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        if args.output_format == "json":
            print(json.dumps({
                "mode": "product_create_transaction",
                "intent_hypothesis": _public_intent_hypothesis(candidate_intent),
                "product_create_transaction": transaction.summary(),
                "transaction_file": str(transaction_path.relative_to(repo_root)),
                "confirmation": _transaction_confirmation_payload(
                    transaction=transaction,
                    output_path=str(transaction_path.relative_to(repo_root)),
                ),
            }, indent=2, sort_keys=True))
        else:
            preview = render_product_intent_preview(candidate_intent).rstrip()
            print(
                f"{preview}\n\n{_transaction_confirmation_text(transaction=transaction, output_path=str(transaction_path.relative_to(repo_root)))}",
                end="",
            )
        return 0
    if args.command == "apply":
        message = _legacy_apply_disabled_error()
        if args.as_json:
            print(json.dumps({"mode": "error", "error": message}, indent=2, sort_keys=True))
        else:
            print(message)
        return 2
    if args.command == "compile-transaction":
        if str(args.intent_file or "").strip():
            _print_greenfield_error(ValueError(_retired_intent_file_message()), as_json=args.output_format == "json")
            return 2
        try:
            started_at = time.perf_counter()
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            candidate_intent, transaction, staged_path = _compile_prompt_evidence_transaction(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector=str(args.release),
                edit_evidence=edit_evidence,
                repair_tier=str(args.repair_tier),
                source_language=str(args.evidence_language),
                started_at=started_at,
            )
            output_path = str(args.output or "").strip()
            if output_path:
                path = _transaction_output_path(repo_root=repo_root, output_path=output_path)
                assert path is not None
                greenfield_proposals.write_product_create_transaction_file(path, transaction)
                output_path = str(path)
            else:
                output_path = str(staged_path)
            if args.output_format == "json":
                summary = transaction.summary()
                payload = {
                    "mode": "product_create_transaction",
                    "intent_hypothesis": _public_intent_hypothesis(candidate_intent),
                    "product_create_transaction": summary,
                    "transaction": greenfield_proposals.product_create_transaction_to_dict(transaction),
                    "confirmation": _transaction_confirmation_payload(
                        transaction=transaction,
                        output_path=output_path,
                    ),
                }
                if output_path:
                    payload["transaction_file"] = output_path
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                preview = render_product_intent_preview(candidate_intent).rstrip()
                print(f"{preview}\n\n{_transaction_confirmation_text(transaction=transaction, output_path=output_path)}", end="")
        except GreenfieldClarificationRequired as exc:
            return _finish_clarification(
                exc=exc,
                as_json=args.output_format == "json",
            )
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        return 0
    return 2
